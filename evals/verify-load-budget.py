#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""加载场景预算验收（只读、零网络、幂等）。

对 contracts/rules.json 的 scenes 逐场景计算「展开后文件字符总量」与文件数，
对照 constants.scenes_budget（files_max/chars_max）与场景级 chars_max 覆盖项。
超预算 → E-LOAD-BUDGET，exit 1。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from rule_contract import (  # noqa: E402
    FAMILY_TOKEN, load, skill_root, _subject_family_files, _expand_files)


def scene_stats(root: Path, data: dict) -> list:
    family_files = _subject_family_files(data["files"])
    family_sizes = {}
    for f in family_files:
        p = root / f
        family_sizes[f] = len(p.read_text(encoding="utf-8", errors="replace")) if p.exists() else 0

    budget = data["constants"]["scenes_budget"]
    rows = []
    for sid, sc in data["scenes"].items():
        # 运行时口径：{family} 只载当前任务的一个族文件 → 文件数记 1、字符取族文件最大值
        static = [f for f in sc["files"] if FAMILY_TOKEN not in f]
        has_family = len(static) != len(sc["files"])
        n_files = len(static) + (1 if has_family else 0)
        chars = 0
        missing = []
        for f in static:
            p = root / f
            if p.exists():
                chars += len(p.read_text(encoding="utf-8", errors="replace"))
            else:
                missing.append(f)
        if has_family:
            if family_sizes and max(family_sizes.values()) > 0:
                chars += max(family_sizes.values())
            else:
                missing.extend(family_files)
        files_max = budget.get("files_max")
        chars_max = sc.get("chars_max", budget.get("chars_max"))
        over_files = files_max is not None and n_files > files_max
        over_chars = chars_max is not None and chars > chars_max
        rows.append({
            "scene": sid,
            "files": n_files,
            "chars": chars,
            "chars_max": chars_max,
            "over_files": over_files,
            "over_chars": over_chars,
            "missing": missing,
        })
    return rows


def main(argv=None) -> int:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="加载场景预算验收（只读）")
    parser.add_argument("--skill-root", default=None)
    args = parser.parse_args(argv)
    root = Path(args.skill_root).resolve() if args.skill_root else skill_root()
    data = load()
    rows = scene_stats(root, data)
    issues = []
    for r in rows:
        if r["missing"]:
            issues.append("E-LOAD-BUDGET: 场景 %s 文件缺失 %s" % (r["scene"], r["missing"]))
        if r["over_files"]:
            issues.append("E-LOAD-BUDGET: 场景 %s 文件数 %d 超预算" % (r["scene"], r["files"]))
        if r["over_chars"]:
            issues.append("E-LOAD-BUDGET: 场景 %s 字符 %d > %s"
                          % (r["scene"], r["chars"], r["chars_max"]))
    print(json.dumps({
        "ok": not issues,
        "scenes": len(rows),
        "worst": max(rows, key=lambda r: r["chars"])["scene"] if rows else None,
        "issues": issues,
    }, ensure_ascii=False))
    for r in rows:
        flag = "OVER" if (r["over_chars"] or r["over_files"] or r["missing"]) else "ok"
        print("  [%s] %-12s files=%d chars=%d (max %s)" % (flag, r["scene"], r["files"], r["chars"], r["chars_max"]))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
