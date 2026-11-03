#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""加载场景预算验收（只读、零网络、幂等）。

对 contracts/rules.json 的 scenes 逐场景计算「展开后文件字符总量」与文件数，
对照 constants.scenes_budget（files_max/chars_max）与场景级 chars_max 覆盖项；
并计算轮级最坏加载（常驻 SKILL.md+triggers + 主场景 core + persist core
+ 补读全文件 + 单个最大叠加场景 core）与同轮叠加总和（stack_sum），
对照 round_chars_max / stack_sum_chars_max（契约缺省键则跳过该项检查）。
超预算 → E-LOAD-BUDGET，exit 1；场景用量 ≥98% 打 TIGHT 预警（report-only，不改退出码）。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from rule_contract import (  # noqa: E402
    TOKEN_KEYS, _token_names, load, skill_root)


def _size(p: Path) -> int:
    return len(p.read_text(encoding="utf-8", errors="replace")) if p.exists() else 0


def scene_stats(root: Path, data: dict) -> list:
    token_names = _token_names(data)
    budget = data["constants"]["scenes_budget"]
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
        chars, missing, issues = 0, [], []
        for f in static:
            p = root / f
            if p.exists():
                chars += _size(p)
            else:
                missing.append(f)

        toks_used = {t for _, ts in tpls for t in ts}
        if len(toks_used) > 1:
            issues.append("E-LOAD-BUDGET: 场景 %s 同时使用多个令牌 %s"
                          % (sid, sorted(toks_used)))
        elif toks_used:
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

        files_max = budget.get("files_max")
        chars_max = sc.get("chars_max", budget.get("chars_max"))
        over_files = files_max is not None and n_files > files_max
        over_chars = chars_max is not None and chars > chars_max
        tight = (chars_max is not None and not over_chars and chars_max > 0
                 and chars >= 0.98 * chars_max)
        rows.append({
            "scene": sid,
            "files": n_files,
            "chars": chars,
            "chars_max": chars_max,
            "over_files": over_files,
            "over_chars": over_chars,
            "tight": tight,
            "missing": missing,
            "issues": issues,
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


def pointer_stats(root: Path, data: dict) -> list:
    """补读/叠加报告：core + supplements + stack_max；补读超软上限只 warning。"""
    budget = data["constants"]["scenes_budget"]
    supp_files_max = budget.get("supplement_files_max", 4)
    supp_chars_max = budget.get("supplement_chars_max", 20000)
    rows = []
    for sid, sc in data["scenes"].items():
        supp_files = sorted({x.get("file") for x in sc.get("supplements", []) if x.get("file")})
        supp_chars = sum(_size(root / f) for f in supp_files)
        stack = [x.get("scene") for x in sc.get("stack", []) if x.get("scene") in data["scenes"]]
        stack_chars = max((_chars(root, data["scenes"][s]["files"], data) for s in stack), default=0)
        warnings = []
        if len(supp_files) > supp_files_max:
            warnings.append("supplement_files=%d > %d" % (len(supp_files), supp_files_max))
        if supp_chars > supp_chars_max:
            warnings.append("supplement_chars=%d > %d" % (supp_chars, supp_chars_max))
        rows.append({
            "scene": sid,
            "core_chars": _chars(root, sc["files"], data),
            "supplement_files": len(supp_files),
            "supplement_chars": supp_chars,
            "stack_scenes": len(stack),
            "stack_chars_max": stack_chars,
            "warnings": warnings,
        })
    return rows


def round_stats(root: Path, data: dict) -> list:
    """轮级最坏加载（v9.11.7）：常驻（SKILL.md + routing/triggers.md）
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

    def over_budget():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.md").write_text("x" * 100, encoding="utf-8")
            data = {
                "constants": {
                    "scenes_budget": {"files_max": 17, "chars_max": 100},
                    "group_slugs": {},
                    "discipline_slugs": [],
                },
                "scenes": {"s": {"files": ["a.md"], "chars_max": 10}},
            }
            rows = scene_stats(root, data)
            assert rows[0]["over_chars"] and not rows[0]["missing"], rows

    chk("over budget detected", over_budget)

    def missing_file():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = {
                "constants": {
                    "scenes_budget": {"files_max": 17, "chars_max": 100},
                    "group_slugs": {},
                    "discipline_slugs": [],
                },
                "scenes": {"s": {"files": ["missing.md"], "chars_max": 100}},
            }
            rows = scene_stats(root, data)
            assert rows[0]["missing"], rows

    chk("missing file detected", missing_file)

    def round_over_budget():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.md").write_text("x" * 100, encoding="utf-8")
            data = {
                "constants": {
                    "scenes_budget": {"files_max": 17, "chars_max": 1000},
                    "group_slugs": {},
                    "discipline_slugs": [],
                },
                "scenes": {"s": {"files": ["a.md"]}},
            }
            rows = round_stats(root, data)
            assert rows[0]["round_chars"] == 100, rows
            assert rows[0]["round_chars"] > 50, rows  # 50 作假想 round_chars_max

    chk("round budget detected", round_over_budget)

    def stack_sum_detected():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.md").write_text("x" * 40, encoding="utf-8")
            (root / "b.md").write_text("y" * 40, encoding="utf-8")
            data = {
                "constants": {
                    "scenes_budget": {"files_max": 17, "chars_max": 1000},
                    "group_slugs": {},
                    "discipline_slugs": [],
                },
                "scenes": {
                    "base": {"files": ["a.md"], "stack": [{"scene": "extra", "when": "按能力触发"}]},
                    "extra": {"files": ["b.md"]},
                },
            }
            rows = round_stats(root, data)
            assert rows[0]["stack_sum_chars"] == 40, rows
            assert rows[0]["round_chars"] == 80, rows  # 常驻 0 + 主 40 + 叠加最大 40

    chk("stack sum detected", stack_sum_detected)

    def tight_budget_warned():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.md").write_text("x" * 99, encoding="utf-8")
            data = {
                "constants": {
                    "scenes_budget": {"files_max": 17, "chars_max": 100},
                    "group_slugs": {},
                    "discipline_slugs": [],
                },
                "scenes": {"s": {"files": ["a.md"], "chars_max": 100}},
            }
            rows = scene_stats(root, data)
            assert rows[0]["tight"] and not rows[0]["over_chars"], rows

    chk("tight budget warned", tight_budget_warned)

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
    parser = argparse.ArgumentParser(description="加载场景预算验收（只读）")
    parser.add_argument("--skill-root", default=None)
    parser.add_argument("--pointers", action="store_true",
                        help="额外报告每场景补读文件数与叠加场景最坏字符")
    parser.add_argument("--selftest", action="store_true", help="运行只读负例自检")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    root = Path(args.skill_root).resolve() if args.skill_root else skill_root()
    data = load()
    rows = scene_stats(root, data)
    issues = []
    for r in rows:
        issues.extend(r["issues"])
        if r["missing"]:
            issues.append("E-LOAD-BUDGET: 场景 %s 文件缺失 %s" % (r["scene"], r["missing"]))
        if r["over_files"]:
            issues.append("E-LOAD-BUDGET: 场景 %s 文件数 %d 超预算" % (r["scene"], r["files"]))
        if r["over_chars"]:
            issues.append("E-LOAD-BUDGET: 场景 %s 字符 %d > %s"
                          % (r["scene"], r["chars"], r["chars_max"]))
    tight = ["场景 %s 用量 %d/%s（≥98%%，加规则先拆场景）" % (r["scene"], r["chars"], r["chars_max"])
             for r in rows if r["tight"]]
    pointer_rows = pointer_stats(root, data) if args.pointers else []
    pointer_warnings = [w for r in pointer_rows for w in r["warnings"]]
    budget = data["constants"]["scenes_budget"]
    round_max = budget.get("round_chars_max")
    stack_sum_max = budget.get("stack_sum_chars_max")
    round_rows = round_stats(root, data)
    for r in round_rows:
        if round_max is not None and r["round_chars"] > round_max:
            issues.append("E-LOAD-BUDGET: 轮级 %s 最坏加载 %d > round_chars_max %s"
                          % (r["scene"], r["round_chars"], round_max))
        if stack_sum_max is not None and r["stack_sum_chars"] > stack_sum_max:
            issues.append("E-LOAD-BUDGET: 场景 %s 叠加总和 %d > stack_sum_chars_max %s"
                          % (r["scene"], r["stack_sum_chars"], stack_sum_max))
    round_worst = max(round_rows, key=lambda r: r["round_chars"]) if round_rows else None
    print(json.dumps({
        "ok": not issues,
        "scenes": len(rows),
        "worst": max(rows, key=lambda r: r["chars"])["scene"] if rows else None,
        "round_worst": round_worst,
        "issues": issues,
        "tight_warnings": tight,
        "pointers": pointer_rows,
        "pointer_warnings": pointer_warnings,
    }, ensure_ascii=False))
    for r in rows:
        flag = "OVER" if (r["over_chars"] or r["over_files"] or r["missing"]) else ("TIGHT" if r["tight"] else "ok")
        print("  [%s] %-12s files=%d chars=%d (max %s)" % (flag, r["scene"], r["files"], r["chars"], r["chars_max"]))
    for r in pointer_rows:
        print("  [ptr] %-12s core=%d supp=%d/%d stack_max=%d/%d%s"
              % (r["scene"], r["core_chars"], r["supplement_files"], r["supplement_chars"],
                 r["stack_scenes"], r["stack_chars_max"],
                 (" WARN " + "; ".join(r["warnings"])) if r["warnings"] else ""))
    for r in round_rows:
        print("  [rnd] %-18s round=%d/%s stack_sum=%d/%s"
              % (r["scene"], r["round_chars"], round_max, r["stack_sum_chars"], stack_sum_max))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
