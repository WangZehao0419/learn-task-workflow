#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学科层单点扇出机检（只读、零网络、幂等、stdlib-only）。

票 95 把「加一门学科只动一个文件」从一句承诺变成会红的断言。三条判据：

    E-SUBJ-FANOUT-MISSING    扇出表与磁盘双向相等：少一行、多一个文件都红
    E-SUBJ-FANOUT-ROW        每行只挂一个文件，且「管什么」「何时读」两栏非空
    E-SUBJ-ENTRY-SCATTERED   入口 SKILL.md 对学科层的指针收敛为一条

为什么必须**双向**：只查「表里每行都有对应文件」会放过漏登记——新加一个学科包没
写进表，表自己照样自洽、全绿，而漏登记正是这张票要消灭的东西（加一门学科要牵动
整个文档集）。反向也必须查：表里写了文件但文件不存在，等于把读者送去空指针。

为什么「收敛为一条」要机检：入口文档对学科层的指针散开时，加一门学科就要在每个散
点各加一条；散点越多，漏改一处越难被发现，而入口失准是**静默**的——读者按入口找，
找不到就自己翻目录，没人报错。判据钉成「SKILL.md 里指向学科层的路径只允许
references/subjects-index.md 一个取值」，散开即红；且它必须挂在「加载路由」表内
可达——藏在「参考文件」列表里，读者仍然不知道什么时候该读它。

AC「新增一门学科只需加一个文件 + 该册一行」的证明在 --selftest 的 demo 用例里：
临时根里加一个 disciplines 包 → 红；再补一行 → 绿，全程只动「一个文件 + 一行」。

用法：
    python -B scripts/verify_subject_fanout.py              # 检查真实树
    python -B scripts/verify_subject_fanout.py --selftest   # 自测 + 真实树
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rule_contract import skill_root  # noqa: E402
import ltw_exit  # noqa: E402  三态退出码唯一定义处（票 106）

BT = chr(96)
CONTRACT = "contracts/rules.json"
SKILL_MD = "SKILL.md"
INDEX = "references/subjects-index.md"
FANOUT_HEAD = "## 学科层扇出表"
TABLE_COLS = ("文件", "管什么", "何时读")
ROUTE_HEAD = "## 加载路由"

# 入口文档里指向学科层的路径：references/subjects-<任意>（含通配写法）与
# references/disciplines/<任意>。唯一允许的取值是学科层入口册本身。
SUBJECT_PTR_RE = re.compile(
    BT + "(references/(?:subjects-[^" + BT + "]*|disciplines/[^" + BT + "]*))" + BT)
ALLOWED_TARGET = INDEX

# 扇出表一行的文件指针：只认 references/ 下的 .md。
ROW_PATH_RE = re.compile(BT + "(references/[^" + BT + "]+?\.md)" + BT)


def fanout_section(text: str):
    """取「学科层扇出表」节正文；节不存在返回 None（调用方按红处理）。

    边界必须按**任意层级**的标题切，不能只认二级：本册在扇出表之后接的是
    `# 学科层总则` 这类一级标题，只认 `\n## ` 会让本节的边界一路吃到文末，
    把后面「学科 → 学科群」「SOLO 观察表」两张表也吸进来当扇出行——那会让判据
    数出 19 行之外的假行，红得莫名其妙，或者更糟：把真缺口盖住。
    """
    i = text.find(FANOUT_HEAD)
    if i < 0:
        return None
    rest = text[i + len(FANOUT_HEAD):]
    m = re.search(r"^#{1,6} ", rest, re.M)
    return text[i:] if m is None else text[i:i + len(FANOUT_HEAD) + m.start()]


def table_rows(section: str):
    """返回 (表头, [(该行文件指针列表, 各栏文本)])；表头与分隔行不算数据行。"""
    head, rows = None, []
    for raw in section.split("\n"):
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if head is None:
            head = cells
            continue
        if cells and all(set(c) <= set("-: ") for c in cells):
            continue
        rows.append((ROW_PATH_RE.findall(line), cells))
    return head, rows


def disk_subject_files(root: Path):
    """磁盘上的**学科文件**全集：七本群切片 + 十二个学科包。

    刻意排除本册自己（`references/subjects-index.md`）：它是扇出的**发起方**，
    不是被扇出的学科文件。把它写进自己的表里，一来是自指指针（verify-doc-pointers
    的 W-PTR-SELF 目标项），二来会让「扇出行数 == 学科文件数」这个等式失去意义
    ——本册永远在，于是表永远至少有一行是对的。
    """
    subs = sorted(p.relative_to(root).as_posix()
                  for p in root.glob("references/subjects-*.md")
                  if p.name != "subjects-index.md")
    disc = sorted(p.relative_to(root).as_posix()
                  for p in root.glob("references/disciplines/*.md"))
    return subs + disc


def check(root: Path) -> list:
    """返回违规列表；空列表 = 全绿。任何锚点缺失都计入违规（fail closed）。"""
    problems = []

    try:
        text = (root / INDEX).read_text(encoding="utf-8")
    except OSError as e:
        problems.append("E-SUBJ-FANOUT-MISSING: %s 不可读（%s）" % (INDEX, e))
        return problems

    section = fanout_section(text)
    if section is None:
        problems.append(
            "E-SUBJ-FANOUT-MISSING: %s 里找不到「%s」节——扇出表不在，学科文件就"
            "重新变成散装指针，按红处理（当绿等于删掉整张票）"
            % (INDEX, FANOUT_HEAD.lstrip("# ")))
    else:
        head, rows = table_rows(section)
        if head != list(TABLE_COLS):
            problems.append("E-SUBJ-FANOUT-ROW: 表头必须是 %r，实际 %r"
                            % (list(TABLE_COLS), head))

        listed = []
        for paths, cells in rows:
            if len(paths) != 1:
                problems.append(
                    "E-SUBJ-FANOUT-ROW: 一行只挂一个文件，实际 %d 个：%r"
                    % (len(paths), paths))
                continue
            listed.append(paths[0])
            if len(cells) != 3 or not cells[1] or not cells[2]:
                problems.append(
                    "E-SUBJ-FANOUT-ROW: %s 的「管什么」「何时读」两栏都必填（实际 %r）"
                    % (paths[0], cells))

        dupes = sorted({p for p in listed if listed.count(p) > 1})
        if dupes:
            problems.append("E-SUBJ-FANOUT-ROW: 扇出表有重复行：%s" % "、".join(dupes))

        disk = disk_subject_files(root)
        missing = sorted(set(disk) - set(listed))
        extra = sorted(set(listed) - set(disk))
        if missing:
            problems.append(
                "E-SUBJ-FANOUT-MISSING: 磁盘上有 %d 个学科文件没进扇出表：%s——"
                "新增学科必须「加一个文件 + 该册一行」两件事一起做，只做一半即红"
                % (len(missing), "、".join(missing)))
        if extra:
            problems.append(
                "E-SUBJ-FANOUT-MISSING: 扇出表有 %d 行指向不存在的文件：%s"
                % (len(extra), "、".join(extra)))

    # 七个学科族的中文名 → 目录名，正本在契约里；群切片文件名必须跟着它走。
    # 刻意**不**要求 disciplines 目录与契约 discipline_slugs 相等：加一门学科只该动
    # 「一个文件 + 一行」，再要求同步改契约就变成三处，反而违背本票的 AC。
    try:
        obj = json.loads((root / CONTRACT).read_text(encoding="utf-8"))
        gs = obj["constants"]["group_slugs"]
    except (OSError, KeyError, TypeError, ValueError) as e:
        problems.append("E-SUBJ-CONTRACT: %s 读不到 constants.group_slugs（%s）"
                        % (CONTRACT, e))
        gs = None
    if isinstance(gs, dict):
        for cn, slug in sorted(gs.items()):
            rel = "references/subjects-%s.md" % slug
            if not (root / rel).exists():
                problems.append("E-SUBJ-GROUP-MISSING: 学科族「%s」的群切片 %s 不存在"
                                % (cn, rel))

    # 入口文档对学科层的指针收敛为一条。
    try:
        skill = (root / SKILL_MD).read_text(encoding="utf-8")
    except OSError as e:
        problems.append("E-SUBJ-SKILL: %s 不可读（%s）" % (SKILL_MD, e))
        return problems

    hits = SUBJECT_PTR_RE.findall(skill)
    scattered = sorted({h for h in hits if h != ALLOWED_TARGET})
    if scattered:
        problems.append(
            "E-SUBJ-ENTRY-SCATTERED: %s 里指向学科层的路径有 %d 个取值（%s），"
            "只允许 %s 一个——散开后加一门学科要在每个散点各加一条，漏改一处无人发觉"
            % (SKILL_MD, len(scattered), "、".join(scattered), ALLOWED_TARGET))

    if ALLOWED_TARGET not in hits:
        problems.append(
            "E-SUBJ-ENTRY-UNREACHABLE: %s 里没有一条指针指到 %s——入口不可达，"
            "学科层就等于不存在" % (SKILL_MD, ALLOWED_TARGET))
    else:
        route = skill.find(ROUTE_HEAD)
        if route < 0:
            problems.append("E-SUBJ-ENTRY-UNREACHABLE: %s 缺「%s」节"
                            % (SKILL_MD, ROUTE_HEAD.lstrip("# ")))
        else:
            stop = skill.find("\n## ", route + 1)
            body = skill[route:] if stop < 0 else skill[route:stop]
            if ALLOWED_TARGET not in body:
                problems.append(
                    "E-SUBJ-ENTRY-UNREACHABLE: %s 的加载路由表里没有 %s——入口册必须在"
                    "路由表内可达；只写在「参考文件」列表里，读者仍不知道什么时候读它"
                    % (SKILL_MD, ALLOWED_TARGET))
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

    GROUPS = ("math", "science", "language", "computing", "humanities",
              "medicine", "skill")
    DISCS = ("calculus", "physics", "chemistry", "biology", "geography", "chinese",
             "english", "computing-theory", "history", "law", "medicine",
             "economics-psychology")

    def table_text(paths):
        lines = [FANOUT_HEAD, "", "| " + " | ".join(TABLE_COLS) + " |",
                 "|---|---|---|"]
        for p in paths:
            lines.append("| " + BT + p + BT + " | 管什么的说明 | 何时读的说明 |")
        return "\n".join(lines) + "\n"

    def build(td, paths=None, extra=(), skill=None):
        """造一个最小合规根：磁盘文件集 + 扇出表 + 入口 + 契约。"""
        root = Path(td)
        disk = (["references/subjects-%s.md" % g for g in GROUPS]
                + ["references/disciplines/%s.md" % d for d in DISCS])
        for rel in list(disk) + list(extra):
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text("# x\n", encoding="utf-8")
        listed = disk if paths is None else paths
        (root / INDEX).write_text("# 学科层入口 正本册\n\n> 导读句。\n\n"
                                  + table_text(listed), encoding="utf-8")
        # 本册自己不在扇出表里，但必须真实存在（它就是被检查的那本册）。
        (root / INDEX).touch()
        (root / CONTRACT).parent.mkdir(parents=True, exist_ok=True)
        (root / CONTRACT).write_text(
            json.dumps({"constants": {"group_slugs": {g: g for g in GROUPS}}},
                       ensure_ascii=False), encoding="utf-8")
        route = (ROUTE_HEAD + "\n\n| 你在做什么 | 读这一册 |\n|---|---|\n"
                 "| 已认到具体学科 | " + BT + INDEX + BT + " |\n\n")
        rest = "## 参考文件\n\n- " + BT + INDEX + BT + " —— 学科层唯一入口。\n"
        (root / SKILL_MD).write_text("# t\n\n" + (route + rest if skill is None else skill),
                                    encoding="utf-8")
        return root

    def green_baseline():
        with tempfile.TemporaryDirectory() as td:
            probs = check(build(td))
            assert not probs, probs
        return True
    case("绿：扇出表与磁盘一一对上、入口收敛为一条", green_baseline)

    def mut_drop_row():
        with tempfile.TemporaryDirectory() as td:
            root = build(td)
            text = (root / INDEX).read_text(encoding="utf-8")
            row = "| " + BT + "references/disciplines/law.md" + BT + " |"
            assert text.count(row) == 1, "变异锚点不唯一：law 行"
            (root / INDEX).write_text(
                "\n".join(ln for ln in text.split("\n") if not ln.startswith(row)),
                encoding="utf-8")
            probs = check(root)
            assert any("FANOUT-MISSING" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            assert not check(build(td)), "还原后应绿"
        return True
    case("变异：扇出表删一行 → 红，还原 → 绿", mut_drop_row)

    def mut_add_file():
        with tempfile.TemporaryDirectory() as td:
            probs = check(build(td, extra=["references/disciplines/music-theory.md"]))
            assert any("FANOUT-MISSING" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            assert not check(build(td)), "还原后应绿"
        return True
    case("变异：加一个表里没有的学科文件 → 红，还原 → 绿", mut_add_file)

    def demo_new_discipline():
        """AC 的实证：新增一门学科 = 一个文件 + 一行，两步到位即绿。"""
        with tempfile.TemporaryDirectory() as td:
            root = build(td)
            (root / "references/disciplines/music-theory.md").write_text(
                "# 乐理\n", encoding="utf-8")
            assert any("FANOUT-MISSING" in x for x in check(root)), "只加文件必须红"
            text = (root / INDEX).read_text(encoding="utf-8").rstrip("\n")
            (root / INDEX).write_text(
                text + "\n| " + BT + "references/disciplines/music-theory.md" + BT
                + " | 管什么 | 何时读 |\n", encoding="utf-8")
            probs = check(root)
            assert not probs, ("补一行后应绿——这就是 AC 说的「一个文件 + 一行」", probs)
        return True
    case("AC 实证：新增一门学科 = 加一个文件 + 该册一行（两步到位即绿）",
         demo_new_discipline)

    def mut_row_thin():
        with tempfile.TemporaryDirectory() as td:
            root = build(td)
            text = (root / INDEX).read_text(encoding="utf-8")
            full = "| " + BT + "references/disciplines/law.md" + BT + " | 管什么的说明 | 何时读的说明 |"
            assert text.count(full) == 1, "变异锚点不唯一：law 整行"
            (root / INDEX).write_text(
                text.replace(full, "| " + BT + "references/disciplines/law.md" + BT
                             + " |  |  |"), encoding="utf-8")
            probs = check(root)
            assert any("FANOUT-ROW" in x for x in probs), probs
        return True
    case("变异：某行「管什么/何时读」留空 → 红（表不能退化成一串裸文件名）",
         mut_row_thin)

    def mut_scatter_entry():
        bad = (ROUTE_HEAD + "\n\n| 你在做什么 | 读这一册 |\n|---|---|\n"
               "| 取学科切片 | " + BT + "references/subjects-math.md" + BT + " |\n\n"
               "## 参考文件\n\n- " + BT + INDEX + BT + " —— 入口。\n"
               "- " + BT + "references/disciplines/" + BT + " —— 包目录。\n")
        with tempfile.TemporaryDirectory() as td:
            probs = check(build(td, skill=bad))
            assert any("ENTRY-SCATTERED" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            assert not check(build(td)), "还原后应绿"
        return True
    case("变异：入口重新散成具体群切片/包目录 → 红，还原 → 绿", mut_scatter_entry)

    def mut_entry_unreachable():
        nowhere = (ROUTE_HEAD + "\n\n| 你在做什么 | 读这一册 |\n|---|---|\n| 空 | 空 |\n\n"
                   "## 参考文件\n\n- 无。\n")
        with tempfile.TemporaryDirectory() as td:
            probs = check(build(td, skill=nowhere))
            assert any("ENTRY-UNREACHABLE" in x for x in probs), probs
        only_ref = (ROUTE_HEAD + "\n\n| 你在做什么 | 读这一册 |\n|---|---|\n| 空 | 空 |\n\n"
                    "## 参考文件\n\n- " + BT + INDEX + BT + " —— 学科层唯一入口。\n")
        with tempfile.TemporaryDirectory() as td:
            probs = check(build(td, skill=only_ref))
            assert any("ENTRY-UNREACHABLE" in x for x in probs), probs
        return True
    case("变异：入口册从路由表消失 / 只在「参考文件」里提 → 红", mut_entry_unreachable)

    def anchor_missing():
        with tempfile.TemporaryDirectory() as td:
            root = build(td)
            (root / INDEX).write_text("# 学科层入口\n\n> 导读。\n", encoding="utf-8")
            probs = check(root)
            assert any("FANOUT-MISSING" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            root = build(td)
            (root / CONTRACT).write_text("{}", encoding="utf-8")
            probs = check(root)
            assert any("E-SUBJ-CONTRACT" in x for x in probs), probs
        with tempfile.TemporaryDirectory() as td:
            root = build(td)
            (root / SKILL_MD).unlink()
            probs = check(root)
            assert any("E-SUBJ-SKILL" in x for x in probs), probs
        return True
    case("fail closed：扇出表锚点缺失 / 契约缺 group_slugs / 入口缺失 都变红",
         anchor_missing)

    # ── 真实制品变异：拷真身到临时根再改，绝不改被测文件本身 ──────────────
    # 夹具变异只证明判据逻辑对，证明不了真实册子的表真被这条判据咬住。
    def real_tree_mutations():
        real = skill_root()
        base_index = (real / INDEX).read_text(encoding="utf-8")
        base_skill = (real / SKILL_MD).read_text(encoding="utf-8")
        base_contract = (real / CONTRACT).read_text(encoding="utf-8")
        disk = disk_subject_files(real)

        def materialize(td, index_text, skill_text=None, extra=()):
            root = Path(td)
            for rel in list(disk) + list(extra):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                src = real / rel
                if src.exists():
                    (root / rel).write_bytes(src.read_bytes())
                else:
                    (root / rel).write_text("# 新学科\n", encoding="utf-8")
            (root / INDEX).write_text(index_text, encoding="utf-8")
            (root / SKILL_MD).write_text(
                base_skill if skill_text is None else skill_text, encoding="utf-8")
            (root / CONTRACT).parent.mkdir(parents=True, exist_ok=True)
            (root / CONTRACT).write_text(base_contract, encoding="utf-8")
            return root

        with tempfile.TemporaryDirectory() as td:
            assert not check(materialize(td, base_index)), "真身副本应绿"

        # 变异 A：从真实扇出表删掉一行。
        section = fanout_section(base_index)
        assert section is not None, "真实册里找不到扇出表"
        _head, rows = table_rows(section)
        disc_rows = [r for r in rows if r[0] and r[0][0].startswith("references/disciplines/")]
        assert disc_rows, "真实扇出表里没有 disciplines 行"
        victim = disc_rows[0][0][0]
        dropped = "\n".join(ln for ln in base_index.split("\n") if victim not in ln)
        with tempfile.TemporaryDirectory() as td:
            probs = check(materialize(td, dropped))
            assert any("FANOUT-MISSING" in x for x in probs), probs

        # 变异 B：磁盘上多一个学科文件，表里没有。
        with tempfile.TemporaryDirectory() as td:
            probs = check(materialize(td, base_index,
                                      extra=["references/disciplines/_probe-new.md"]))
            assert any("FANOUT-MISSING" in x for x in probs), probs

        # 变异 C：入口重新散开成具体群切片。
        scattered = base_skill.replace(BT + INDEX + BT,
                                       BT + "references/subjects-math.md" + BT, 1)
        assert scattered != base_skill, "真实 SKILL.md 里找不到可替换的入口指针"
        with tempfile.TemporaryDirectory() as td:
            probs = check(materialize(td, base_index, skill_text=scattered))
            assert any("ENTRY-SCATTERED" in x for x in probs), probs

        with tempfile.TemporaryDirectory() as td:
            assert not check(materialize(td, base_index)), "还原后应绿"
        return True
    case("真实制品变异：删一行 / 加一个未登记文件 / 入口散开 → 红，还原 → 绿",
         real_tree_mutations)

    def real_tree():
        probs = check(skill_root())
        assert not probs, probs
        return True
    case("真实树：扇出表与磁盘双向相等、入口收敛为一条", real_tree)

    if failures:
        return ltw_exit.EXIT_VIOLATION
    print("PASS 学科层单点扇出机检：%d 个用例" % ran[0])
    return ltw_exit.EXIT_OK


def main(argv=None) -> int:
    ap = ltw_exit.UsageParser(description="学科层单点扇出机检（只读）")
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
    print("PASS 学科层单点扇出：扇出表与磁盘双向相等、入口收敛为一条")
    return ltw_exit.EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
