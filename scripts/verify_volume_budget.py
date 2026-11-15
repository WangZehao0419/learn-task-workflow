#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分册字节上限与册首导读句机检（只读、零网络、幂等、stdlib-only）。

票 100 的两条机检，合并成一个只读入口：

    E-VOLUME-OVERSIZE   单册字节 > 上限（默认 35,000）
    E-VOLUME-NO-INTRO   加载路由目标册的第 3 行不是「> …时读本册。」导读句

为什么上限是 35,000：宿主单次读取有上限，分册按「一册 = 一个动作的一次完整读取」
设计，超过上限就会被**静默截断**——读者以为读完了整册，实际只读到一半，而缺的那
一半不会报错。35,000 是宿主上限的一半，留出余量。

为什么导读句要机检：加载路由表按「动作 → 一册」组织，而「这一册什么时候该读」写在
册顶第 3 行（第 1 行标题、第 2 行空行）。导读句缺失时，路由表把读者送到册前，读者
却不知道这一册管不管他现在要做的事——只能整册通读，或干脆不读。这是**静默**的失准。

范围口径（两条判据各有自己的适用域，不混）：

  字节上限  —— 对 references/ 下**全部** .md 生效（含学科群切片与学科包）。超限就会被
               宿主静默截断，与其是不是动作册无关。
  导读句    —— 只对**加载路由表里出现的目标**生效。理由：学科群切片（subjects-*.md）与
               学科包（disciplines/*.md）不是从路由表直接进入的，它们由
               references/subjects-index.md「学科层扇出表」按需扇出，而扇出表本身就带
               「何时读」一栏（票 95 的 verify_subject_fanout.py 已咬住这一栏非空）。若把
               这两类也要求「册顶导读句」，等于把同一条信息在两处各写一次，两处一旦不一致
               反而更难判断谁对——那不是更严格，是把耦合度做大。

判定顺序是「先解析路由表得到目标集合，再逐目标查第 3 行」。新增一册却没接进路由表时
不会被判导读句缺失——但那本身是另一个问题（该册还没有入口），本脚本不越界去猜「这册
本应该挂在哪一行」。

用法：
    python -B scripts/verify_volume_budget.py
    python -B scripts/verify_volume_budget.py --selftest
退出码：0 全合规；1 有超限或缺导读句；2 用法错误。
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rule_contract import skill_root  # noqa: E402
import ltw_exit  # noqa: E402  三态退出码唯一定义处（票 106）

BT = chr(96)
LIMIT = 35000
REFS = "references"
INTRO_SUFFIX = "时读本册"
ROUTE_HEAD = "## 加载路由"
ROUTE_NEXT = "## 调度协议"
ROUTE_PTR_RE = re.compile(BT + r"(references/[^" + BT + r"]+?\.md)" + BT)


def all_volumes(root: Path):
    """字节上限的适用域：references/ 下全部 .md（含 disciplines）。"""
    base = root / REFS
    if not base.is_dir():
        return []
    out = sorted(p for p in base.rglob("*.md") if p.is_file())
    return [p.relative_to(root) for p in out]


def route_targets(root: Path):
    """加载路由表里出现的 references 目标集合。表缺失返回 None。"""
    path = root / "SKILL.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    i = text.find(ROUTE_HEAD)
    if i < 0:
        return None
    j = text.find(ROUTE_NEXT, i + len(ROUTE_HEAD))
    sec = text[i:j] if j > 0 else text[i:]
    return set(ROUTE_PTR_RE.findall(sec))


def intro_ok(text: str) -> bool:
    """第 3 行必须是非空 blockquote，且以「时读本册」收尾。

    允许句末标点（。）；不接受「读本册」「本册」这类缺「时」的写法——缺了「时」，
    读者拿到的是「读这一册」，不是「什么时候读这一册」，条件语义丢失。
    """
    lines = text.splitlines()
    if len(lines) < 3:
        return False
    third = lines[2].strip()
    if not third.startswith(">"):
        return False
    body = third.lstrip("> ").strip()
    if not body:
        return False
    # 导读句后面允许再接一句补充说明（现有册有三种写法：以「时读本册。」收尾、
    # 以「时读本册」不收尾、以及「时读本册；<补充说明>」）。判据是「含『时读本册』
    # 这个条件句式」，不是「整行必须止于此」——后者会把合法写法判红，逼人删掉
    # 有用的补充说明来迁就正则。
    return INTRO_SUFFIX in body


def check(root: Path, limit: int = LIMIT):
    """返回 (oversize, no_intro, n_volumes, n_route)。"""
    oversize, no_intro = [], []
    vols = all_volumes(root)
    for rel in vols:
        path = root / rel
        try:
            raw = path.read_bytes()
        except OSError as exc:
            oversize.append((str(rel), "不可读：%s" % exc))
            continue
        if len(raw) > limit:
            oversize.append((str(rel), "%d B > %d B" % (len(raw), limit)))

    targets = route_targets(root)
    if targets is None:
        no_intro.append(("SKILL.md", "找不到「%s」表——路由表缺失，导读句无从判定" % ROUTE_HEAD))
        return oversize, no_intro, len(vols), 0

    for rel in sorted(targets):
        path = root / rel
        if not path.is_file():
            no_intro.append((rel, "路由表指向的文件不存在"))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            no_intro.append((rel, "不可读：%s" % exc))
            continue
        if not intro_ok(text):
            lines = text.splitlines()
            third = lines[2] if len(lines) >= 3 else "（无第 3 行）"
            no_intro.append((rel, "第 3 行不是导读句：%r" % third.strip()[:60]))
    return oversize, no_intro, len(vols), len(targets)


def _selftest() -> int:
    """内置用例：正例 + 超限 + 缺导读句 + 导读句写错。"""
    failures = []
    route = ("## 加载路由\n\n| 做什么 | 读 |\n|---|---|\n| 做甲事 | "
             + BT + "references/a.md" + BT + " |\n\n## 调度协议\n")

    def case(name, files, expect_ok, limit=LIMIT):
        data = {"SKILL.md": route}
        data.update(files)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel, body in data.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(body.encode("utf-8"))
            over, nointro, _n, _r = check(root, limit=limit)
            ok = not over and not nointro
            if ok != expect_ok:
                failures.append("%s：期望 ok=%s，实得 ok=%s（over=%s nointro=%s）"
                                % (name, expect_ok, ok, over, nointro))

    good = "# 册名\n\n> 要做某事时读本册。\n\n正文\n"
    case("路由目标有导读句", {"references/a.md": good}, True)
    case("超限", {"references/a.md": good + "x" * 200}, False, limit=100)
    case("路由目标缺导读句", {"references/a.md": "# 册名\n\n正文直接开始\n"}, False)
    case("第 3 行非 blockquote", {"references/a.md": "# 册名\n\n要做某事时读本册。\n"}, False)
    case("导读句缺「时」", {"references/a.md": "# 册名\n\n> 要做事就读本册。\n"}, False)
    case("空 blockquote", {"references/a.md": "# 册名\n\n>\n正文\n"}, False)
    case("路由目标指向不存在的文件", {}, False)
    case("非路由册不要求导读句",
         {"references/other.md": "# 别的册\n\n\n正文\n", "references/a.md": good}, True)

    for f in failures:
        print("FAIL " + f)
    print("%s 分册预算与导读句：%d 个用例" % ("PASS" if not failures else "FAIL", 8))
    return 0 if not failures else 1


def main(argv=None) -> int:
    ap = ltw_exit.UsageParser(description="分册字节上限与册首导读句机检")
    ap.add_argument("--selftest", action="store_true", help="跑内置用例再检查真实树")
    ap.add_argument("--root", default=None, help="技能根（默认脚本所在仓库）")
    ap.add_argument("--limit", type=int, default=LIMIT, help="单册字节上限（默认 35000）")
    args = ap.parse_args(argv)

    if args.selftest:
        rc = _selftest()
        if rc:
            return rc

    root = Path(args.root) if args.root else skill_root()
    rc_root = ltw_exit.require_root(root)
    if rc_root is not None:
        return rc_root
    over, nointro, total, nroute = check(root, args.limit)
    rc = ltw_exit.EXIT_OK
    for rel, why in over:
        print("FAIL [E-VOLUME-OVERSIZE] %s :: %s" % (rel, why))
        rc = ltw_exit.EXIT_VIOLATION
    for rel, why in nointro:
        print("FAIL [E-VOLUME-NO-INTRO] %s :: %s" % (rel, why))
        rc = ltw_exit.EXIT_VIOLATION
    if rc == ltw_exit.EXIT_OK:
        print("PASS 分册预算：%d 册全部 ≤%d B；加载路由 %d 个目标导读句齐备"
              % (total, args.limit, nroute))
    return rc


if __name__ == "__main__":
    sys.exit(main())
