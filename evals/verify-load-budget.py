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
        rows.append({
            "scene": sid,
            "files": n_files,
            "chars": chars,
            "chars_max": chars_max,
            "over_files": over_files,
            "over_chars": over_chars,
            "missing": missing,
            "issues": issues,
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
        issues.extend(r["issues"])
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
