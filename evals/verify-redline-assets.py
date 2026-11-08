#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""红线回归与冷读资产的结构校验（只读、零网络、幂等）。

只校验**资产本身是否可用**，绝不校验「通过与否」：
- 十一条红线是否每条都有用例
- 每条用例是否有 prompt / fixture / pass_condition
- **证据诚实性**：未运行的用例不得携带运行证据，也不得标「通过」
- 冷读清单是否写全
- 权重口径是否把「索引机检」列为闸口（列为闸口即失败）

这个脚本不跑红线、不打分——执行与评分是人和独立 verifier 的事。
"""
import argparse
import json
import sys
from pathlib import Path

REDLINE_COUNT = 11
REQUIRED_CASE_FIELDS = ("id", "redline", "prompt", "fixture", "pass_condition", "verdict")
EVIDENCE_FIELDS = ("actual_output", "run_id", "scores", "reviewer")
VERDICTS = ("通过", "未通过", "未验证")


class Checker:
    def __init__(self):
        self.ok = 0
        self.fail = 0
        self.notes = []

    def check(self, name, cond, detail=""):
        if cond:
            self.ok += 1
            print("[OK] %s" % name)
        else:
            self.fail += 1
            print("[FAIL] %s%s" % (name, (" :: " + detail) if detail else ""))


def check_cases(reg, c):
    cases = reg.get("cases") or []
    c.check("1.1 红线用例数量 == 11", len(cases) == REDLINE_COUNT, "实际 %d" % len(cases))

    covered = sorted({x.get("redline") for x in cases if isinstance(x.get("redline"), int)})
    c.check("1.2 十一条红线编号全覆盖 1..11",
            covered == list(range(1, REDLINE_COUNT + 1)), "覆盖 %s" % covered)

    ids = [x.get("id") for x in cases]
    c.check("1.3 用例 id 唯一", len(ids) == len(set(ids)))

    missing = []
    for x in cases:
        for f in REQUIRED_CASE_FIELDS:
            if f not in x or (f != "verdict" and not str(x.get(f, "")).strip()):
                missing.append("%s.%s" % (x.get("id", "?"), f))
    c.check("1.4 每条用例字段齐全且非空", not missing, str(missing[:5]))

    bad = [x.get("id") for x in cases if x.get("verdict") not in VERDICTS]
    c.check("1.5 verdict 取值合法", not bad, str(bad[:5]))


def check_evidence_honesty(reg, c):
    """未运行的用例不得携带运行证据；标「通过」必须有证据。"""
    cases = reg.get("cases") or []

    dirty = []
    for x in cases:
        if x.get("verdict") == "未验证":
            for f in EVIDENCE_FIELDS:
                v = x.get(f)
                if v not in ("", None, {}, []):
                    dirty.append("%s.%s" % (x.get("id"), f))
    c.check("2.1 未验证用例不得携带运行证据", not dirty, str(dirty[:5]))

    bare = []
    for x in cases:
        if x.get("verdict") == "通过":
            for f in EVIDENCE_FIELDS:
                if x.get(f) in ("", None, {}, []):
                    bare.append("%s.%s" % (x.get("id"), f))
    c.check("2.2 标「通过」的用例必须有完整证据", not bare, str(bare[:5]))


def check_protocol(reg, c):
    proto = reg.get("执行协议") or {}
    c.check("3.1 声明执行者不读 pass_condition",
            "不读" in str(proto.get("执行者", "")), str(proto.get("执行者", ""))[:60])
    c.check("3.2 声明执行与评分分离",
            "独立" in str(proto.get("评分者", "")), str(proto.get("评分者", ""))[:60])
    c.check("3.3 通过标准为 11/11 且任一违规即 P0",
            "11/11" in str(proto.get("通过标准", "")) and "P0" in str(proto.get("通过标准", "")))
    c.check("3.4 分册是否被读到只作辅助观测",
            "不作硬断言" in str(proto.get("不作硬断言", "")) or
            "辅助" in str(proto.get("不作硬断言", "")))


def check_coldread(cr, c):
    c.check("4.1 冷读对象清单非空", bool(cr.get("冷读对象")))
    c.check("4.2 冷读问题清单非空", bool(cr.get("冷读问题（逐条回答，不许跳过）")))
    c.check("4.3 声明未做的冷读不得记为通过",
            "不得记为通过" in str(cr.get("记录口径", "")))


def check_weights(w, c):
    p0 = str(w.get("P0 主证据", ""))
    c.check("5.1 P0 主证据含红线回归", "红线" in p0)
    c.check("5.2 P0 主证据含真人冷读", "冷读" in p0)
    nogate = str(w.get("明确不作闸口", ""))
    c.check("5.3 索引机检明确不作闸口", "索引机检" in nogate)
    report = str(w.get("报告项", ""))
    c.check("5.4 官方规范符合度只作报告项", "官方" in report and "不设闸" in report)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="红线回归与冷读资产结构校验（只读）")
    ap.add_argument("--evals", default=None)
    args = ap.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    path = Path(args.evals) if args.evals else root / "evals" / "evals.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    c = Checker()
    check_cases(data.get("redline_regression") or {}, c)
    check_evidence_honesty(data.get("redline_regression") or {}, c)
    check_protocol(data.get("redline_regression") or {}, c)
    check_coldread(data.get("human_cold_read") or {}, c)
    check_weights(data.get("acceptance_weights") or {}, c)

    total = c.ok + c.fail
    print("verify-redline-assets: %d checks, %d OK, %d FAIL" % (total, c.ok, c.fail))
    return 0 if c.fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
