#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""with-skill vs baseline 对照汇总（只读、零网络、幂等）。

把**已经跑出来的**结果汇总成可比 delta：通过率 / 耗时 / token。
本脚本不跑任何用例、不打任何分——它只做算术与呈现。

输入是一个结果文件（JSON），格式：
{
  "label": "with-skill" | "baseline",
  "cases": [{"id": "...", "verdict": "通过"|"未通过", "elapsed_ms": 1234, "tokens": 5678}, ...]
}
没有结果文件时，只报告「尚无对照数据」，绝不编造数字。

--check 只校验结果文件结构；--selftest 验证汇总逻辑本身。
"""
import argparse
import json
import sys
from pathlib import Path


def summarize(result):
    cases = result.get("cases") or []
    n = len(cases)
    if n == 0:
        return {"label": result.get("label", "?"), "n": 0, "pass_rate": None,
                "elapsed_ms_avg": None, "tokens_avg": None}
    passed = sum(1 for c in cases if c.get("verdict") == "通过")
    ms = [c["elapsed_ms"] for c in cases if isinstance(c.get("elapsed_ms"), (int, float))]
    tk = [c["tokens"] for c in cases if isinstance(c.get("tokens"), (int, float))]
    return {
        "label": result.get("label", "?"),
        "n": n,
        "pass_rate": round(passed / n, 4),
        "elapsed_ms_avg": round(sum(ms) / len(ms), 1) if ms else None,
        "tokens_avg": round(sum(tk) / len(tk), 1) if tk else None,
    }


def delta(a, b):
    """b 相对 a 的变化；任一为 None 则该项为 None（不猜）。"""
    out = {}
    for k in ("pass_rate", "elapsed_ms_avg", "tokens_avg"):
        if a.get(k) is None or b.get(k) is None:
            out[k] = None
        else:
            out[k] = round(b[k] - a[k], 4)
    return out


def check_structure(result):
    issues = []
    if not isinstance(result, dict):
        return ["结果文件顶层必须是对象"]
    if "label" not in result:
        issues.append("缺 label")
    cases = result.get("cases")
    if not isinstance(cases, list):
        issues.append("cases 必须是数组")
        return issues
    for i, c in enumerate(cases):
        if not isinstance(c, dict):
            issues.append("cases[%d] 必须是对象" % i)
            continue
        if "id" not in c:
            issues.append("cases[%d] 缺 id" % i)
        if c.get("verdict") not in ("通过", "未通过"):
            issues.append("cases[%d] verdict 必须是 通过/未通过" % i)
    return issues


def _selftest():
    fails = []

    def chk(name, cond):
        if cond:
            print("PASS", name)
        else:
            fails.append(name)
            print("FAIL", name)

    r = summarize({"label": "with-skill", "cases": [
        {"id": "a", "verdict": "通过", "elapsed_ms": 100, "tokens": 1000},
        {"id": "b", "verdict": "未通过", "elapsed_ms": 300, "tokens": 3000},
    ]})
    chk("通过率 = 1/2", r["pass_rate"] == 0.5)
    chk("耗时均值 = 200", r["elapsed_ms_avg"] == 200.0)
    chk("token 均值 = 2000", r["tokens_avg"] == 2000.0)

    empty = summarize({"label": "x", "cases": []})
    chk("空结果不编造比率", empty["pass_rate"] is None)

    d = delta({"pass_rate": 0.5, "elapsed_ms_avg": 200, "tokens_avg": 2000},
              {"pass_rate": 0.8, "elapsed_ms_avg": 150, "tokens_avg": 1800})
    chk("通过率 delta = +0.3", d["pass_rate"] == 0.3)
    chk("耗时 delta = -50", d["elapsed_ms_avg"] == -50)

    d2 = delta({"pass_rate": 0.5, "elapsed_ms_avg": None, "tokens_avg": 2000},
               {"pass_rate": 0.8, "elapsed_ms_avg": 150, "tokens_avg": 1800})
    chk("缺失项不猜，返回 None", d2["elapsed_ms_avg"] is None)

    bad = check_structure({"label": "x", "cases": [{"id": "a", "verdict": "未验证"}]})
    chk("非法 verdict 被抓到", any("verdict" in i for i in bad))

    if fails:
        return 1
    print("PASS 对照汇总 6/6")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="with-skill vs baseline 对照汇总（只读）")
    ap.add_argument("--with-skill", help="with-skill 结果 JSON")
    ap.add_argument("--baseline", help="baseline 结果 JSON")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    def load(p):
        return json.loads(Path(p).read_text(encoding="utf-8"))

    if args.check:
        issues = []
        for label, p in (("with-skill", args.with_skill), ("baseline", args.baseline)):
            if p:
                issues += ["%s: %s" % (label, i) for i in check_structure(load(p))]
        print(json.dumps({"ok": not issues, "issues": issues}, ensure_ascii=False))
        return 0 if not issues else 1

    if not args.with_skill and not args.baseline:
        print(json.dumps({"status": "no-data",
                          "message": "尚无对照数据。本脚本不跑用例、不编造数字；",
                          "next": "由独立 verifier 跑完 with-skill 与 baseline 后传入两个结果文件。"},
                         ensure_ascii=False))
        return 0

    ws = summarize(load(args.with_skill)) if args.with_skill else None
    bl = summarize(load(args.baseline)) if args.baseline else None
    out = {"with_skill": ws, "baseline": bl}
    if ws and bl:
        out["delta"] = delta(bl, ws)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
