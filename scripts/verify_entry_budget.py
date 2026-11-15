#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""入口预算机检（只读、零网络、幂等、stdlib-only）。

票 102 把「压缩后入口还能用」从文档里的三句话变成会红的断言：

    E-ENTRY-REDLINE-OVERRUN      红线节结束字节必须 < 压缩砍点下界常量
    E-ENTRY-FIRSTTWO-OVER        前两段（一句话纪律 + 加载路由）合计必须 ≤ 6000 B
    E-ENTRY-ROUTE-AFTER-REDLINE  加载路由表必须整体早于红线节

为什么砍点必须**读常量**而不是写当前实测值：写死当前值，断言就永远跟着自己转——
红线节哪天被压缩砍掉 3,000 B，「当前实测值」跟着变小，断言照样绿，而这次重排的全部
意义（压缩触发时手里还剩得下路由与红线）正是被砍掉的那部分。常量的唯一正本是
contracts/rules.json 的 constants.budget.context_compress_cutoff_lower_bound；
「把常量改小必须变红」由变异用例单独打红，证明断言真在读它。

为什么「红线节」用**字节**而 rule_contract.py 用**字符**：两者是两个不同的验收轴。
字符轴管「判据自身体量」（票 42 Q7 的 5,000 字符），字节轴管「压缩砍点落在哪」（票 48 ④
的下界按字节给）。同一段正文在两个轴上余量不同，混用任一轴都会放过一次真实的越界。

锚点缺失一律按红处理（fail closed）：找不到锚点不是「没有越界」，而是「无从检查」。
把它当绿，等于让改一次标题就静默摘掉闸口。

用法：
    python -B scripts/verify_entry_budget.py              # 检查真实树
    python -B scripts/verify_entry_budget.py --selftest   # 自测 + 真实树
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rule_contract import REDLINE_SECTION_HEAD, skill_root  # noqa: E402
import ltw_exit  # noqa: E402  三态退出码唯一定义处（票 106）

# 压缩砍点下界的唯一正本在契约里，这里只声明「去哪个键取」。
BUDGET_KEY = "context_compress_cutoff_lower_bound"
BUDGET_PATH = ("constants", "budget")
CONTRACT = "contracts/rules.json"
SKILL_MD = "SKILL.md"

# 规格要求的前两段：一句话纪律与加载路由。
DISCIPLINE_RE = re.compile(r"^> \*\*一句话纪律\*\*", re.M)
ROUTE_HEAD = "## 加载路由"
FIRST_TWO_MAX = 6000
# 表内指针：一行只指一册是「动作 → 一册」的机器判据。
PTR_RE = re.compile(r"`((?:references|scripts|evals|contracts)/[^`]+?\.(?:md|py|json))`")

H2_RE = re.compile(r"^## .*$", re.M)


def boff(text: str, idx: int) -> int:
    """字符下标 → UTF-8 字节偏移（本文件的三个预算都是字节口径）。"""
    return len(text[:idx].encode("utf-8"))


def h2_sections(text: str) -> list:
    return [{"head": m.group(0).strip(), "idx": m.start(),
             "line": text[:m.start()].count("\n") + 1}
            for m in H2_RE.finditer(text)]


def section_span(text: str, secs: list, i: int) -> tuple:
    """第 i 个二级节的内容区间 [起, 止)，止于下一个二级标题之前。"""
    stop = secs[i + 1]["idx"] if i + 1 < len(secs) else len(text)
    return secs[i]["idx"], stop


def read_cutoff(root: Path, problems: list):
    """读压缩砍点下界常量。读不到即 fail closed。"""
    p = root / CONTRACT
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except OSError as e:
        problems.append("E-ENTRY-CUTOFF-MISSING: %s 不可读（%s）" % (CONTRACT, e))
        return None
    except json.JSONDecodeError as e:
        problems.append("E-ENTRY-CUTOFF-INVALID: %s JSON 非法（%s）" % (CONTRACT, e))
        return None
    cur = data
    for part in BUDGET_PATH:
        cur = cur.get(part) if isinstance(cur, dict) else None
    val = cur.get(BUDGET_KEY) if isinstance(cur, dict) else None
    if val is None:
        problems.append(
            "E-ENTRY-CUTOFF-MISSING: %s 缺 constants.budget.%s（砍点必须有唯一正本，"
            "不许散写数字）" % (CONTRACT, BUDGET_KEY))
        return None
    if not isinstance(val, int) or isinstance(val, bool) or val <= 0:
        problems.append(
            "E-ENTRY-CUTOFF-INVALID: constants.budget.%s 必须是正整数（实际 %r）"
            % (BUDGET_KEY, val))
        return None
    return val


def check(root: Path) -> list:
    """返回违规列表；空列表 = 全绿。任何锚点缺失都计入违规。"""
    problems = []
    cutoff = read_cutoff(root, problems)

    p = root / SKILL_MD
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        problems.append("E-ENTRY-SKILL-UNREADABLE: %s 不可读（%s）" % (SKILL_MD, e))
        return problems

    secs = h2_sections(text)

    def find_head(prefix):
        for i, s in enumerate(secs):
            if s["head"].startswith(prefix):
                return i
        return None

    # ── 判据一：红线节结束字节 < 砍点下界 ────────────────────────────────
    ri = find_head(REDLINE_SECTION_HEAD)
    redline_line = None
    if ri is None:
        problems.append(
            "E-ENTRY-REDLINE-ANCHOR-MISSING: 找不到「%s」——锚点不存在即无从检查，"
            "按红处理（当绿等于改个标题就摘掉闸口）" % REDLINE_SECTION_HEAD)
    else:
        a, z = section_span(text, secs, ri)
        redline_end_byte = boff(text, z)
        redline_line = secs[ri]["line"]
        if cutoff is not None and not redline_end_byte < cutoff:
            problems.append(
                "E-ENTRY-REDLINE-OVERRUN: 红线节结束于字节 %d，不得 ≥ 压缩砍点下界 %d"
                "（差 %d B）——超出即压缩触发时红线被静默砍掉，且全程无报错"
                % (redline_end_byte, cutoff, redline_end_byte - cutoff))

    # ── 判据二：前两段（一句话纪律 + 加载路由）合计 ≤ 6000 B ──────────────
    dm = DISCIPLINE_RE.search(text)
    ui = find_head(ROUTE_HEAD)
    if dm is None:
        problems.append("E-ENTRY-DISCIPLINE-ANCHOR-MISSING: 找不到「一句话纪律」引用块")
    if ui is None:
        problems.append(
            "E-ENTRY-ROUTE-ANCHOR-MISSING: 找不到「%s」节" % ROUTE_HEAD)
    if dm is not None and ui is not None:
        if not dm.start() < secs[ui]["idx"]:
            problems.append(
                "E-ENTRY-FIRSTTWO-ORDER: 一句话纪律必须在加载路由之前"
                "（前两段的定义依赖这个顺序）")
        else:
            _, route_stop = section_span(text, secs, ui)
            first_two = boff(text, route_stop) - boff(text, dm.start())
            if first_two > FIRST_TWO_MAX:
                problems.append(
                    "E-ENTRY-FIRSTTWO-OVER: 前两段合计 %d B，上限 %d B（超 %d B）"
                    % (first_two, FIRST_TWO_MAX, first_two - FIRST_TWO_MAX))

    # ── 判据三：加载路由表整体早于红线节 ──────────────────────────────────
    if ui is not None and ri is not None:
        a, z = section_span(text, secs, ui)
        rows = []
        line = secs[ui]["line"]
        for raw_line in text[a:z].split("\n"):
            if raw_line.lstrip().startswith("|"):
                rows.append((line, raw_line))
            line += 1
        if not rows:
            problems.append("E-ENTRY-ROUTE-TABLE-MISSING: 加载路由节内没有表格行")
        late = [(ln, t) for ln, t in rows if ln >= redline_line]
        if late:
            problems.append(
                "E-ENTRY-ROUTE-AFTER-REDLINE: 加载路由表有 %d 行不早于红线节"
                "（红线节在第 %d 行）：压缩砍掉尾部时路由随之消失"
                % (len(late), redline_line))

        # 一行只指一册（票 102 AC「加载表改为动作 → 一册」的机器判据）。
        multi = [(ln, len(PTR_RE.findall(t))) for ln, t in rows
                 if len(PTR_RE.findall(t)) >= 2]
        if multi:
            problems.append(
                "E-ENTRY-ROUTE-MULTI-BOOKLET: 加载路由有 %d 行指了不止一册"
                "（行号 %s）——一行一册，叠加读的条件下沉到册顶导读句"
                % (len(multi), "、".join(str(x[0]) for x in multi)))
    return problems


def _selftest() -> int:
    """自测：每条判据都要有「改坏会红、还原会绿」，且变异锚点断言唯一。"""
    failures = []
    ran = [0]

    def case(name, fn):
        ran[0] += 1
        try:
            fn()
            print("PASS", name)
        except Exception as e:  # noqa: BLE001
            failures.append((name, repr(e)))
            print("FAIL", name, "::", repr(e))

    CUTOFF = 15733
    BT = chr(96)
    FRONT = "---\nname: t\n---\n\n# 标题\n\n导语。\n\n"
    DISC = "> **一句话纪律**：闸口未达标，绝不进入下一阶段。\n\n"
    ROUTE = ("## 加载路由\n\n"
             "| 你在做什么 | 读这一册 |\n|---|---|\n"
             "| 判请求该不该进 | " + BT + "references/routing.md" + BT + " |\n"
             "| S3 讲授 | " + BT + "references/lessons.md" + BT + " |\n\n")
    DISPATCH = "## 调度协议\n\n1. 入口路由。\n\n"
    # 红线节按真实体量撑——夹具太小会让「常量改小」与「前部插填充」两个变异**一次都打不中**，
    # 于是它们变成恒绿的死断言（本仓踩过的坑：夹具没覆盖到目标分支）。
    REDLINE = "## 十一条教学红线\n\n" + "判" * 2900 + "\n\n"
    REST = "## 阶段速查\n\n内容。\n"

    def build(td, skill_text, cutoff=CUTOFF, contract=True):
        root = Path(td)
        (root / "SKILL.md").write_text(skill_text, encoding="utf-8")
        if contract:
            (root / "contracts").mkdir(exist_ok=True)
            (root / "contracts" / "rules.json").write_text(
                json.dumps({"constants": {"budget": {BUDGET_KEY: cutoff}}},
                           ensure_ascii=False), encoding="utf-8")
        return root

    def good_text():
        return FRONT + DISC + ROUTE + DISPATCH + REDLINE + REST

    def ok_green():
        with tempfile.TemporaryDirectory() as td:
            probs = check(build(td, good_text()))
            assert not probs, probs
            return True
    case("绿：合规入口通过（红线结束 < 砍点）", ok_green)

    def mut_route_after_redline():
        t = good_text()
        assert t.count(ROUTE) == 1, "变异锚点不唯一：加载路由节"
        t2 = t.replace(ROUTE, "").replace(REST, REST + ROUTE)
        with tempfile.TemporaryDirectory() as td:
            probs = check(build(td, t2))
            assert any("ROUTE-AFTER-REDLINE" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            assert not check(build(td, good_text()))
        return True
    case("变异：加载表挪回红线之后 → 红，还原 → 绿", mut_route_after_redline)

    def mut_first_two_fat():
        pad = "补" * (FIRST_TWO_MAX // 3 + 100)
        t2 = (FRONT + DISC
              + ROUTE.replace("\n\n", "\n\n" + pad + "\n\n", 1)
              + DISPATCH + REDLINE + REST)
        with tempfile.TemporaryDirectory() as td:
            probs = check(build(td, t2))
            assert any("FIRSTTWO-OVER" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            assert not check(build(td, good_text()))
        return True
    case("变异：前两段撑爆 >6000 B → 红，还原 → 绿", mut_first_two_fat)

    def mut_cutoff_shrunk():
        with tempfile.TemporaryDirectory() as td:
            probs = check(build(td, good_text(), cutoff=5000))
            assert any("REDLINE-OVERRUN" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            assert not check(build(td, good_text(), cutoff=CUTOFF))
        return True
    case("变异：砍点常量改小到 5000 → 红，还原 → 绿", mut_cutoff_shrunk)

    def mut_pad_before_redline():
        t = good_text()
        assert t.count(DISPATCH) == 1, "变异锚点不唯一：调度协议节"
        # 填充量按砍点算，不写死：红线节已贴近砍点，任何向前溢出的插入都必须打红。
        t2 = t.replace(DISPATCH, DISPATCH + "填" * 3000 + "\n\n")
        with tempfile.TemporaryDirectory() as td:
            probs = check(build(td, t2))
            assert any("REDLINE-OVERRUN" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            assert not check(build(td, good_text()))
        return True
    case("变异：红线节前插填充 → 红，还原 → 绿", mut_pad_before_redline)

    def anchor_missing():
        with tempfile.TemporaryDirectory() as td:
            probs = check(build(td, FRONT + DISC + ROUTE + DISPATCH + REST))
            assert any("REDLINE-ANCHOR-MISSING" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            probs = check(build(td, good_text().replace(ROUTE, "")))
            assert any("ROUTE-ANCHOR-MISSING" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            probs = check(build(td, good_text().replace(DISC, "")))
            assert any("DISCIPLINE-ANCHOR-MISSING" in x for x in probs), probs
        return True
    case("fail closed：红线/路由/纪律三个锚点缺失都变红", anchor_missing)

    def contract_missing():
        with tempfile.TemporaryDirectory() as td:
            probs = check(build(td, good_text(), contract=False))
            assert any("CUTOFF-MISSING" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            root = build(td, good_text())
            (root / "contracts" / "rules.json").write_text(
                json.dumps({"constants": {"budget": {}}}), encoding="utf-8")
            probs = check(root)
            assert any("CUTOFF-MISSING" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            probs = check(build(td, good_text(), cutoff="15733"))
            assert any("CUTOFF-INVALID" in x for x in probs), probs
        return True
    case("fail closed：常量缺失/缺键/非整数都变红", contract_missing)

    def empty_table():
        with tempfile.TemporaryDirectory() as td:
            t = good_text().replace(ROUTE, ROUTE.split("|")[0])
            probs = check(build(td, t))
            assert any("ROUTE-TABLE-MISSING" in x for x in probs), probs
        return True
    case("路由节里没有表行 → 红（表消失不许静默变绿）", empty_table)

    def real_tree():
        probs = check(skill_root())
        assert not probs, probs
        return True
    case("真实 SKILL.md 过三条入口预算判据", real_tree)

    # ── 真实制品上的变异：拷一份真身到临时根再改，绝不改被测文件本身 ──────────
    # 夹具变异只能证明「判据逻辑对」，证明不了「真实 SKILL.md 的字节真被这条判据咬住」。
    # 所以把真身复制出去打变异：副本改坏必须红、还原必须绿。
    # 不在原地改：中间态一旦被别的进程读到就是事故（rule_contract.py 同口径）。
    def real_tree_mutations():
        real = skill_root()
        base_skill = (real / SKILL_MD).read_text(encoding="utf-8")
        base_rules = (real / CONTRACT).read_text(encoding="utf-8")
        route_head = ROUTE_HEAD
        redline_head = REDLINE_SECTION_HEAD
        phase_head = "## 阶段速查"
        assert base_skill.count(route_head) == 1, "真实 SKILL.md 加载路由锚点不唯一"
        assert base_skill.count(redline_head) == 1, "真实 SKILL.md 红线节锚点不唯一"
        assert base_skill.count(phase_head) == 1, "真实 SKILL.md 阶段速查锚点不唯一"

        def materialize(td, skill_text, rules_text):
            root = Path(td)
            (root / "contracts").mkdir(exist_ok=True)
            (root / SKILL_MD).write_text(skill_text, encoding="utf-8")
            (root / CONTRACT).write_text(rules_text, encoding="utf-8")
            return root

        a = base_skill.index(route_head)
        z = base_skill.index("\n## ", a + 1) + 1
        route_block = base_skill[a:z]

        # 变异 A：把加载表挪回红线之后。
        moved = base_skill[:a] + base_skill[z:]
        idx = moved.index(phase_head)
        moved = moved[:idx] + route_block + moved[idx:]
        with tempfile.TemporaryDirectory() as td:
            probs = check(materialize(td, moved, base_rules))
            assert any("ROUTE-AFTER-REDLINE" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            assert not check(materialize(td, base_skill, base_rules)), "还原后应绿"

        # 变异 B：红线节前插填充（把红线整体推过砍点）。
        padded = base_skill.replace(redline_head, "填" * 3000 + "\n\n" + redline_head, 1)
        with tempfile.TemporaryDirectory() as td:
            probs = check(materialize(td, padded, base_rules))
            assert any("REDLINE-OVERRUN" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            assert not check(materialize(td, base_skill, base_rules)), "还原后应绿"

        # 变异 C：砍点常量改小（证明断言真在读常量，不是在算当前实测值）。
        obj = json.loads(base_rules)
        assert BUDGET_KEY in obj["constants"]["budget"], "真实契约缺砍点常量"
        obj["constants"]["budget"][BUDGET_KEY] = 5000
        shrunk = json.dumps(obj, ensure_ascii=False, indent=1)
        with tempfile.TemporaryDirectory() as td:
            probs = check(materialize(td, base_skill, shrunk))
            assert any("REDLINE-OVERRUN" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            assert not check(materialize(td, base_skill, base_rules)), "还原后应绿"

        # 变异 D：把两册塞进同一行（回到「一行多册」）。
        BT = chr(96)
        row = route_block.split("\n")
        hit = [i for i, ln in enumerate(row) if ln.startswith("| S3 逐目推进")]
        assert len(hit) == 1, "真实加载表里找不到唯一的目标行"
        row[hit[0]] = row[hit[0]].rstrip()[:-1] + " · " + BT + "references/assessment.md" + BT + " |"
        fat_route = "\n".join(row)
        two_books = base_skill[:a] + fat_route + base_skill[z:]
        with tempfile.TemporaryDirectory() as td:
            probs = check(materialize(td, two_books, base_rules))
            assert any("ROUTE-MULTI-BOOKLET" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            assert not check(materialize(td, base_skill, base_rules)), "还原后应绿"
        return True
    case("真实制品变异：挪表/插填充/改小常量/一行两册 → 红，还原 → 绿",
         real_tree_mutations)

    if failures:
        return ltw_exit.EXIT_VIOLATION
    print("PASS 入口预算机检：%d 个用例" % ran[0])
    return ltw_exit.EXIT_OK


def main(argv=None) -> int:
    ap = ltw_exit.UsageParser(description="入口预算机检（只读）")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--root", default=None, help="技能根（默认脚本所在仓库）")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    root = Path(args.root) if args.root else skill_root()
    rc_root = ltw_exit.require_root(root)
    if rc_root is not None:
        return rc_root
    probs = check(root)
    for x in probs:
        print(x)
    if probs:
        return ltw_exit.EXIT_VIOLATION
    print("PASS 入口预算：红线节结束 < 砍点下界、前两段 ≤%d B、加载路由早于红线"
          % FIRST_TWO_MAX)
    return ltw_exit.EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
