#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""触发率与 baseline 对照资产的结构校验（只读、零网络、幂等）。

只校验**资产是否可用**，不跑触发、不打分：
- 触发率用例数量、正负例覆盖、train/validation 拆分
- **证据诚实性**：未跑用例不得带运行证据，也不得标「通过」
- 阈值口径是否写明且不含「索引机检」
- 官方规范符合度是否只作报告项
"""
import argparse
import json
import sys
from pathlib import Path

MIN_CASES = 20
REQUIRED = ("id", "prompt", "expect_trigger", "split", "runs_required", "verdict")


class Checker:
    def __init__(self):
        self.ok = 0
        self.fail = 0

    def check(self, name, cond, detail=""):
        if cond:
            self.ok += 1
            print("[OK] %s" % name)
        else:
            self.fail += 1
            print("[FAIL] %s%s" % (name, (" :: " + detail) if detail else ""))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="触发率与 baseline 资产校验（只读）")
    ap.add_argument("--evals", default=None)
    args = ap.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    path = Path(args.evals) if args.evals else root / "evals" / "evals.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    te = d.get("trigger_eval") or {}
    cases = te.get("cases") or []

    c = Checker()
    c.check("1.1 触发率用例 >= %d 条" % MIN_CASES, len(cases) >= MIN_CASES, "实际 %d" % len(cases))

    pos = [x for x in cases if x.get("expect_trigger") is True]
    neg = [x for x in cases if x.get("expect_trigger") is False]
    c.check("1.2 含应触发正例", len(pos) > 0, "正例 %d" % len(pos))
    c.check("1.3 含近邻不应触发负例", len(neg) > 0, "负例 %d" % len(neg))

    ids = [x.get("id") for x in cases]
    c.check("1.4 用例 id 唯一", len(ids) == len(set(ids)))

    missing = []
    for x in cases:
        for f in REQUIRED:
            if f not in x:
                missing.append("%s.%s" % (x.get("id", "?"), f))
    c.check("1.5 每条用例字段齐全", not missing, str(missing[:5]))

    splits = {x.get("split") for x in cases}
    c.check("1.6 train/validation 双拆分都存在",
            splits == {"train", "validation"}, str(sorted(splits)))

    multi = [x.get("id") for x in cases if (x.get("runs_required") or 0) < 2]
    c.check("1.7 每条用例要求多次运行", not multi, str(multi[:5]))

    # 证据诚实性
    dirty = [x.get("id") for x in cases
             if x.get("verdict") == "未验证" and x.get("evidence")]
    c.check("2.1 未验证用例不得携带运行证据", not dirty, str(dirty[:5]))

    bare = [x.get("id") for x in cases
            if x.get("verdict") == "通过" and not x.get("evidence")]
    c.check("2.2 标「通过」的用例必须有证据", not bare, str(bare[:5]))

    # 阈值口径
    th = te.get("阈值口径") or {}
    c.check("3.1 阈值口径写明正例触发率", "正例触发率" in th)
    c.check("3.2 阈值口径写明负例误触发率", "负例误触发率" in th)
    c.check("3.3 触发率明确为前置门槛",
            "前置门槛" in str(te.get("定位", "")), str(te.get("定位", ""))[:50])

    # 权重
    w = d.get("acceptance_weights") or {}
    gate = str(w.get("前置门槛", ""))
    c.check("4.1 触发率与 baseline 均列为前置门槛",
            "触发率" in gate and "baseline" in gate, gate[:60])
    report = str(w.get("报告项", ""))
    c.check("4.2 官方规范符合度只作报告项", "官方" in report and "不设闸" in report)
    nogate = str(w.get("明确不作闸口", ""))
    c.check("4.3 索引机检不列为闸口", "索引机检" in nogate)

    total = c.ok + c.fail
    print("verify-trigger-assets: %d checks, %d OK, %d FAIL" % (total, c.ok, c.fail))
    return 0 if c.fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
