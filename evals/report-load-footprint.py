#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""加载足迹报告（只读、零网络、幂等）。

逐场景计算「展开后文件字符总量」与文件数，并计算轮级加载量
（常驻 SKILL.md+triggers + 主场景 core + persist core + 补读全文件
+ 单个最大叠加场景 core）与同轮叠加总和（stack_sum）。
**不做任何预算比较**：全部数字只用于观察加载成本，永不改变退出码。

--check 只校验结构正确性（与预算无关）：场景文件存在、同一场景不混用多个
令牌、补读小节能在目标文件解析到标题。有结构问题才 rc=1。
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from rule_contract import (  # noqa: E402
    TOKEN_KEYS, _resolve_heading, _token_names, load, skill_root)


def _size(p: Path) -> int:
    return len(p.read_text(encoding="utf-8", errors="replace")) if p.exists() else 0


def scene_stats(root: Path, data: dict) -> list:
    token_names = _token_names(data)
    rows = []
    for sid, sc in data["scenes"].items():
        static, tpls = [], []
        for f in sc["files"]:
            toks = [t for t in TOKEN_KEYS if t in f]
            if toks:
                tpls.append((f, toks))
            else:
                static.append(f)

        n_files = len(static)
        chars, missing = 0, []
        for f in static:
            p = root / f
            if p.exists():
                chars += _size(p)
            else:
                missing.append(f)

        toks_used = {t for _, ts in tpls for t in ts}
        multi_token = sorted(toks_used) if len(toks_used) > 1 else []
        if len(toks_used) == 1:
            tok = next(iter(toks_used))
            n_files += len(tpls)
            # 同一场景里同令牌的多条模板：按「同一实例求和、跨实例取最大」计
            per_name = []
            for name in token_names[tok]:
                total = 0
                for tpl, _ in tpls:
                    path = tpl.replace(tok, name)
                    p = root / path
                    if p.exists():
                        total += _size(p)
                    else:
                        missing.append(path)
                per_name.append(total)
            chars += max(per_name) if per_name else 0

        rows.append({
            "scene": sid,
            "files": n_files,
            "chars": chars,
            "multi_token": multi_token,
            "missing": missing,
        })
    return rows


def _chars(root: Path, files: list, data: dict) -> int:
    """核心文件字符数；模板按同令牌取最大实例。"""
    static = [f for f in files if "{" not in f]
    tpls = [f for f in files if "{" in f]
    chars = sum(_size(root / f) for f in static)
    token_names = _token_names(data)
    for tok, names in token_names.items():
        group = [f for f in tpls if tok in f]
        if not group:
            continue
        per = [sum(_size(root / f.replace(tok, name)) for f in group) for name in names]
        chars += max(per) if per else 0
    return chars


def supplement_stats(root: Path, data: dict) -> list:
    """每场景的补读文件数/字符与叠加场景最坏字符（纯报告）。"""
    rows = []
    for sid, sc in data["scenes"].items():
        supp_files = sorted({x.get("file") for x in sc.get("supplements", []) if x.get("file")})
        supp_chars = sum(_size(root / f) for f in supp_files)
        stack = [x.get("scene") for x in sc.get("stack", []) if x.get("scene") in data["scenes"]]
        stack_chars = max((_chars(root, data["scenes"][s]["files"], data) for s in stack), default=0)
        rows.append({
            "scene": sid,
            "core_chars": _chars(root, sc["files"], data),
            "supplement_files": len(supp_files),
            "supplement_chars": supp_chars,
            "stack_scenes": len(stack),
            "stack_chars_peak": stack_chars,
        })
    return rows


def round_stats(root: Path, data: dict) -> list:
    """轮级加载量：常驻（SKILL.md + routing/triggers.md）
    + 主场景 core + persist core + 补读全文件 + 单个最大叠加场景 core；
    stack_sum = 同轮全部叠加场景 core 之和。entry 的 core 即 triggers.md，
    已计入常驻，不重复计；persist 自身轮不重复计 persist。"""
    base = _size(root / "SKILL.md") + _size(root / "references" / "routing" / "triggers.md")
    persist_files = data["scenes"].get("persist", {}).get("files", [])
    persist_chars = _chars(root, persist_files, data) if persist_files else 0
    rows = []
    for sid, sc in data["scenes"].items():
        supp_files = sorted({x.get("file") for x in sc.get("supplements", []) if x.get("file")})
        supp_chars = sum(_size(root / f) for f in supp_files)
        stack = [x.get("scene") for x in sc.get("stack", []) if x.get("scene") in data["scenes"]]
        stack_chars = [_chars(root, data["scenes"][s]["files"], data) for s in stack]
        main = 0 if sid == "entry" else _chars(root, sc["files"], data)
        pers = 0 if sid == "persist" else persist_chars
        rows.append({
            "scene": sid,
            "round_chars": base + main + pers + supp_chars + (max(stack_chars) if stack_chars else 0),
            "stack_sum_chars": sum(stack_chars),
        })
    return rows


def check_structure(root: Path, data: dict) -> list:
    """结构正确性（与预算无关）：文件存在、单令牌、补读小节可解析。"""
    issues = []
    for r in scene_stats(root, data):
        if r["missing"]:
            issues.append("E-LOAD-STRUCT: 场景 %s 文件缺失 %s" % (r["scene"], r["missing"]))
        if r["multi_token"]:
            issues.append("E-LOAD-STRUCT: 场景 %s 同时使用多个令牌 %s"
                          % (r["scene"], r["multi_token"]))
    for sid, sc in data["scenes"].items():
        for s in sc.get("supplements", []):
            f = s.get("file")
            if not f:
                continue
            p = root / f
            if not p.exists():
                issues.append("E-LOAD-STRUCT: 场景 %s 补读文件缺失 %s" % (sid, f))
                continue
            if not _resolve_heading(root, f, s.get("section", "")):
                issues.append("E-LOAD-STRUCT: 场景 %s 补读小节不存在 %s「%s」"
                              % (sid, f, s.get("section", "")))
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

    def counts_chars():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.md").write_text("x" * 100, encoding="utf-8")
            data = {
                "constants": {"group_slugs": {}, "discipline_slugs": []},
                "scenes": {"s": {"files": ["a.md"]}},
            }
            rows = scene_stats(root, data)
            assert rows[0]["chars"] == 100 and rows[0]["files"] == 1, rows
            assert not rows[0]["missing"], rows

    chk("scene chars counted", counts_chars)

    def missing_file():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = {
                "constants": {"group_slugs": {}, "discipline_slugs": []},
                "scenes": {"s": {"files": ["missing.md"]}},
            }
            rows = scene_stats(root, data)
            assert rows[0]["missing"], rows

    chk("missing file detected", missing_file)

    def token_instances_use_max():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "p.md").write_text("a" * 40, encoding="utf-8")
            (root / "q.md").write_text("b" * 90, encoding="utf-8")
            data = {
                "constants": {"group_slugs": {}, "discipline_slugs": ["p", "q"]},
                "scenes": {"s": {"files": ["{discipline}.md"]}},
            }
            rows = scene_stats(root, data)
            assert rows[0]["chars"] == 90, rows  # 跨实例取最大
            assert rows[0]["files"] == 1, rows

    chk("token instance takes max", token_instances_use_max)

    def round_counts_base_and_stack():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "SKILL.md").write_text("s" * 10, encoding="utf-8")
            (root / "references" / "routing").mkdir(parents=True)
            (root / "references" / "routing" / "triggers.md").write_text("t" * 5, encoding="utf-8")
            (root / "a.md").write_text("x" * 40, encoding="utf-8")
            (root / "b.md").write_text("y" * 40, encoding="utf-8")
            data = {
                "constants": {"group_slugs": {}, "discipline_slugs": []},
                "scenes": {
                    "base": {"files": ["a.md"], "stack": [{"scene": "extra", "when": "按能力触发"}]},
                    "extra": {"files": ["b.md"]},
                },
            }
            rows = round_stats(root, data)
            got = {r["scene"]: r for r in rows}
            assert got["base"]["round_chars"] == 15 + 40 + 40, got["base"]  # 常驻 15 + 主 40 + 叠加 40
            assert got["base"]["stack_sum_chars"] == 40, got["base"]

    chk("round counts base and stack", round_counts_base_and_stack)

    def structure_flags_multi_token():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "p.md").write_text("a", encoding="utf-8")
            data = {
                "constants": {"group_slugs": {"x": "p"}, "discipline_slugs": ["p"]},
                "scenes": {"s": {"files": ["{group}.md", "{discipline}.md"]}},
            }
            issues = check_structure(root, data)
            assert any("多个令牌" in i for i in issues), issues

    chk("structure flags multi token", structure_flags_multi_token)

    def structure_flags_bad_section():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.md").write_text("# 标题\n\n正文\n", encoding="utf-8")
            data = {
                "constants": {"group_slugs": {}, "discipline_slugs": []},
                "scenes": {"s": {"files": ["a.md"],
                                 "supplements": [{"file": "a.md", "section": "不存在的节",
                                                  "when": "x", "intent": "local"}]}},
            }
            issues = check_structure(root, data)
            assert any("补读小节不存在" in i for i in issues), issues

    chk("structure flags bad section", structure_flags_bad_section)

    if failures:
        print("SELFTEST FAILED:", ", ".join(failures))
        return 1
    print("SELFTEST OK")
    return 0


def main(argv=None) -> int:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="加载足迹报告（只读，无预算判定）")
    parser.add_argument("--skill-root", default=None)
    parser.add_argument("--check", action="store_true",
                        help="只校验结构正确性（文件存在/单令牌/补读小节可解析），不看数值")
    parser.add_argument("--selftest", action="store_true", help="运行只读自检")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    root = Path(args.skill_root).resolve() if args.skill_root else skill_root()
    data = load()
    issues = check_structure(root, data)
    if args.check:
        print(json.dumps({"ok": not issues, "issues": issues}, ensure_ascii=False))
        return 1 if issues else 0

    rows = scene_stats(root, data)
    supp_rows = supplement_stats(root, data)
    round_rows = round_stats(root, data)
    round_worst = max(round_rows, key=lambda r: r["round_chars"]) if round_rows else None
    print(json.dumps({
        "ok": not issues,
        "scenes": len(rows),
        "worst": max(rows, key=lambda r: r["chars"])["scene"] if rows else None,
        "round_worst": round_worst,
        "issues": issues,
        "supplements": supp_rows,
    }, ensure_ascii=False))
    for r in rows:
        flag = "MISS" if r["missing"] else ("TOK?" if r["multi_token"] else "ok")
        print("  [%s] %-20s files=%d chars=%d" % (flag, r["scene"], r["files"], r["chars"]))
    for r in supp_rows:
        print("  [sup] %-20s core=%d supp=%d/%d stack_max=%d"
              % (r["scene"], r["core_chars"], r["supplement_files"], r["supplement_chars"],
                 r["stack_chars_peak"]))
    for r in round_rows:
        print("  [rnd] %-20s round=%d stack_sum=%d"
              % (r["scene"], r["round_chars"], r["stack_sum_chars"]))
    # 报告工具：数值永远不改变退出码；只有结构问题才非 0
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
