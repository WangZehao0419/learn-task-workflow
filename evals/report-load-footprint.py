#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""加载足迹报告（只读、零网络、幂等）。

按 SKILL.md「加载分册（过渡指针）」的两张表统计：每个动作读多少字符、叠加多少。
**不做任何预算比较**：全部数字只用于观察加载成本，永不改变退出码。

--check 只校验结构正确性：指针目标文件存在。有结构问题才 rc=1。
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from rule_contract import load, skill_root  # noqa: E402

POINTER_RE = re.compile(r"`((?:references|scripts|evals|contracts)/[^`]+?\.(?:md|py|json))`")


def _size(p: Path) -> int:
    return len(p.read_text(encoding="utf-8", errors="replace")) if p.exists() else 0


def _expand(tok: str, names: list) -> list:
    return [tok.replace("{group}", n) if "{group}" in tok else tok.replace("{discipline}", n)
            for n in names]


def parse_skill_tables(text: str):
    """从 SKILL.md 的两张指针表解析出 [(行标题, [指针...])]。"""
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if set(cells[0]) <= set("-: ") or cells[0] in ("你在做什么", "命中条件"):
            continue
        ptrs = POINTER_RE.findall(cells[-1])
        if ptrs:
            rows.append((cells[0].strip("`"), ptrs))
    return rows


def expand_all(ptrs: list, consts: dict) -> list:
    groups = list(consts["group_slugs"].values())
    discs = list(consts["discipline_slugs"])
    out = []
    for p in ptrs:
        if "{group}" in p:
            out.extend(_expand(p, groups))
        elif "{discipline}" in p:
            out.extend(_expand(p, discs))
        else:
            out.append(p)
    return out


def build_rows(root: Path, consts: dict):
    text = (root / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    rows = []
    for label, ptrs in parse_skill_tables(text):
        files = sorted(set(expand_all(ptrs, consts)))
        missing = [f for f in files if not (root / f).exists()]
        chars = sum(_size(root / f) for f in files)
        rows.append({"action": label, "files": len(files), "chars": chars,
                     "missing": missing})
    return rows


def check_structure(root: Path, rows: list) -> list:
    issues = []
    for r in rows:
        if r["missing"]:
            issues.append("E-LOAD-STRUCT: 「%s」指针目标缺失 %s"
                          % (r["action"], r["missing"]))
    return issues


def _selftest() -> int:
    import tempfile

    failures = []

    def chk(name, fn):
        try:
            fn()
            print("PASS", name)
        except Exception as e:
            failures.append(name)
            print("FAIL", name, "::", e)

    def parse_two_tables():
        text = ("| 你在做什么 | 读这些 |\n|---|---|\n"
                "| 讲授 | `references/a.md` · `references/b.md` |\n"
                "| 命中条件 | 加读 |\n|---|---|\n"
                "| 公式 | `references/c.md` |\n")
        rows = parse_skill_tables(text)
        assert len(rows) == 2, rows
        assert rows[0][0] == "讲授", rows
        assert rows[0][1] == ["references/a.md", "references/b.md"], rows

    def expand_group():
        c = {"group_slugs": {"a": "math", "b": "sci"}, "discipline_slugs": ["x"]}
        got = expand_all(["references/subjects-{group}.md"], c)
        assert got == ["references/subjects-math.md",
                       "references/subjects-sci.md"], got

    def expand_discipline():
        c = {"group_slugs": {}, "discipline_slugs": ["p", "q"]}
        got = expand_all(["references/disciplines/{discipline}.md"], c)
        assert got == ["references/disciplines/p.md",
                       "references/disciplines/q.md"], got

    def missing_detected():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.md").write_text("x", encoding="utf-8")
            rows = [{"action": "t", "files": 2, "chars": 1, "missing": ["b.md"]}]
            assert check_structure(root, rows), "缺失未被报出"

    chk("两张表可解析", parse_two_tables)
    chk("group 令牌展开", expand_group)
    chk("discipline 令牌展开", expand_discipline)
    chk("缺失目标被抓到", missing_detected)

    if failures:
        return 1
    print("PASS 加载足迹 4/4")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="加载足迹报告（只读）")
    ap.add_argument("--skill-root")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    root = Path(args.skill_root).resolve() if args.skill_root else skill_root()
    consts = load()["constants"]
    rows = build_rows(root, consts)

    if args.check:
        issues = check_structure(root, rows)
        print(json.dumps({"ok": not issues, "issues": issues}, ensure_ascii=False))
        return 0 if not issues else 1

    for r in sorted(rows, key=lambda x: -x["chars"]):
        print("%-28s files=%-3d chars=%d" % (r["action"][:28], r["files"], r["chars"]))
    print(json.dumps({"rows": len(rows),
                      "max_chars": max((r["chars"] for r in rows), default=0),
                      "skill_md_chars": _size(root / "SKILL.md")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())