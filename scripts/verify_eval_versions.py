#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""评测账本版本降级机检（只读、零网络、幂等、stdlib-only）。

票 101 把「判据一改，旧证据自动作废」从一句口头承诺变成机器能执行的事。

背景：`evals/evals.json` 里 20 条证据的 verdict 曾是「通过」，但它们证明的是
v9.12.2 / v9.13.x 的制品，而账本的 applies_to_version 早已前进。没有字段标记这件事，
旧证据就能一直挂在「通过」栏里——它证明的那个版本早就不存在了。

覆盖范围（票 101 收尾缺口：三块证据，不只 cases）：

    cases               场景清单（顶层 list）
    redline_regression  红线盲回放（redline_regression.cases）
    trigger_eval        触发率用例（trigger_eval.cases）

判据（四条，互相独立）：

    E-EVAL-BLOCK-MISSING     某个证据块缺失、不是 list 或为空
    E-EVAL-VERSION-MISSING   某条证据没有 decided_against_version（结构缺失）
    E-EVAL-VERSION-INVALID   取值不是 x.y.z 形态也不是 "unknown"
    E-EVAL-VERDICT-INVALID   verdict 不在 {通过, 未通过, 未验证} 三态内

降级规则（**不是**错误，rc 仍为 0）：

    decided_against_version != applies_to_version  ⇒  该条视作「未验证」，
    不计入「通过」计数。

为什么降级不是失败：它有两种成因——① 证据是旧版本做的（本来就只证明旧版本）；
② 版本前进了而证据没重跑。两种都不构成「这条规则不成立」的证据，所以它是**第三态**：
既不是通过，也不是失败。把降级当失败会让版本一升就满屏红，最后只能把闸口关掉；
把降级当通过则正是本票要消灭的那个假绿。

为什么降级必须机械：旧实现靠 `_cases 的版本说明` 这一整段自然语言说明「这 19 条只
证明当时的版本」——那是**靠人读一段话记住**，不是机器能拦的。版本一多、证据一多，
总会有一条被漏掉，而且漏掉时没有任何信号。此脚本让「漏掉」变成可见的计数。

为什么三块都要覆盖：`redline_regression` 的 11 条与 `trigger_eval` 的 20 条同样是证据，
只读 `cases` 会让它们绕过降级——规则一改，它们照样挂在「通过」栏里，正是本票要消灭的
假绿。块缺失、不是 list 或为空一律判红（fail closed），不允许「没读到就当没有」。

用法：
    python -B scripts/verify_eval_versions.py
    python -B scripts/verify_eval_versions.py --selftest
    python -B scripts/verify_eval_versions.py --json      # 机器可读输出
退出码：0 结构合规（含全部降级）；1 结构缺失或非法；2 用法错误。
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

EVALS = "evals/evals.json"
VERDICTS = ("通过", "未通过", "未验证")
PASS = "通过"
DEMOTED = "未验证"
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
UNKNOWN = "unknown"

# 三块证据：(块名, 用例列表所在键；None = 块本身就是 list)
BLOCKS = (
    ("cases", None),
    ("redline_regression", "cases"),
    ("trigger_eval", "cases"),
)


def _valid_version(v):
    """x.y.z 或 unknown 合法；其余（含 null、空串、v 前缀）非法。"""
    return isinstance(v, str) and (v == UNKNOWN or bool(VERSION_RE.match(v)))


def _block_cases(doc, name, nested):
    """取出一个证据块的用例列表；返回 (list|None, 说明)。None 表示该块不可用。"""
    if nested is None:
        path = name
        node = doc.get(name)
    else:
        path = "%s.%s" % (name, nested)
        holder = doc.get(name)
        if not isinstance(holder, dict):
            return None, "%s 缺失或不是对象（该块的用例无从枚举）" % name
        node = holder.get(nested)
    if not isinstance(node, list) or not node:
        return None, "%s 缺失或为空——没有证据的块不能当作「全过」" % path
    return node, path


def audit(doc):
    """返回 (errors, stats)。stats 里 pass/demoted/unverified 都按「降级后」口径计，且按块分列。"""
    errors = []
    applies = doc.get("applies_to_version")
    if not _valid_version(applies):
        errors.append(("applies_to_version", "取值非法或缺失：%r" % (applies,)))

    blocks = {}
    n_pass = n_demoted = n_unverified = n_fail = 0
    demoted_ids = []

    for name, nested in BLOCKS:
        cases, where = _block_cases(doc, name, nested)
        if cases is None:
            errors.append((name, where))
            blocks[name] = {"total": 0, "pass": 0, "demoted": 0,
                            "unverified": 0, "failed": 0}
            continue

        b_pass = b_demoted = b_unverified = b_fail = 0
        for i, c in enumerate(cases):
            if not isinstance(c, dict):
                errors.append(("%s[%d]" % (where, i), "用例不是对象：%r" % (type(c).__name__,)))
                continue
            cid = c.get("id") or "%s[%d]" % (where, i)
            if "decided_against_version" not in c:
                errors.append((cid, "缺 decided_against_version（无法判断它证明的是哪个版本）"))
                continue
            dv = c["decided_against_version"]
            if not _valid_version(dv):
                errors.append((cid, "decided_against_version 非法：%r" % (dv,)))
                continue
            verdict = c.get("verdict")
            if verdict not in VERDICTS:
                errors.append((cid, "verdict 非法：%r（只允许 %s）" % (verdict, "/".join(VERDICTS))))
                continue

            # 降级判定：版本不相等（含 unknown）即视作未验证。
            if dv != applies:
                if verdict == PASS:
                    b_demoted += 1
                    demoted_ids.append(cid)
                else:
                    b_unverified += 1
                continue
            if verdict == PASS:
                b_pass += 1
            elif verdict == "未通过":
                b_fail += 1
            else:
                b_unverified += 1

        blocks[name] = {"total": len(cases), "pass": b_pass, "demoted": b_demoted,
                        "unverified": b_unverified, "failed": b_fail}
        n_pass += b_pass
        n_demoted += b_demoted
        n_unverified += b_unverified
        n_fail += b_fail

    stats = {
        "applies_to_version": applies,
        "blocks": blocks,
        "total": sum(b["total"] for b in blocks.values()),
        "pass": n_pass,
        "demoted": n_demoted,
        "unverified": n_unverified,
        "failed": n_fail,
        "demoted_ids": demoted_ids,
    }
    return errors, stats


def load(path: Path):
    """读账本；不可读/非 JSON 返回 (None, 原因)。"""
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, "账本不存在：%s" % path
    except (OSError, json.JSONDecodeError) as exc:
        return None, "账本不可读或不是合法 JSON：%s" % exc


def _selftest() -> int:
    """内置用例：三块覆盖 + 结构缺失 + 降级语义（通过→未验证，不是失败）。"""
    failures = []
    total_cases = [0]

    def case(name, doc, expect_ok, expect_demoted=None, expect_pass=None):
        total_cases[0] += 1
        errs, st = audit(doc)
        ok = not errs
        if ok != expect_ok:
            failures.append("%s：期望 ok=%s，实得 ok=%s（%s）" % (name, expect_ok, ok, errs))
            return
        if expect_demoted is not None and st.get("demoted") != expect_demoted:
            failures.append("%s：期望降级 %d 条，实得 %s" % (name, expect_demoted, st.get("demoted")))
        if expect_pass is not None and st.get("pass") != expect_pass:
            failures.append("%s：期望通过 %d 条，实得 %s" % (name, expect_pass, st.get("pass")))

    def c(cid, verdict, dv):
        return {"id": cid, "verdict": verdict, "decided_against_version": dv}

    def doc(applies, cases=None, rl=None, tr=None):
        """三块齐全的账本。未指定的块用「同版本、非通过」占位，不污染通过计数。"""
        return {
            "applies_to_version": applies,
            "cases": cases if cases is not None else [c("BASE", "通过", applies)],
            "redline_regression": {
                "cases": rl if rl is not None else [c("RL", "未验证", applies)]},
            "trigger_eval": {
                "cases": tr if tr is not None else [c("TR", "未验证", applies)]},
        }

    case("同版本通过计入通过",
         doc("9.21.19", [c("A", "通过", "9.21.19")]), True, 0, 1)
    case("旧版本通过被降级",
         doc("9.21.19", [c("A", "通过", "9.12.2")]), True, 1, 0)
    case("unknown 被降级",
         doc("9.21.19", [c("A", "通过", "unknown")]), True, 1, 0)
    case("旧版本未通过不算降级（它本来就不在通过栏）",
         doc("9.21.19", [c("A", "未通过", "9.12.2")]), True, 0, 0)
    case("缺字段即红",
         doc("9.21.19", [{"id": "A", "verdict": "通过"}]), False)
    case("版本形态非法即红",
         doc("9.21.19", [c("A", "通过", "v9.12.2")]), False)
    case("verdict 非法即红",
         doc("9.21.19", [c("A", "过了", "9.21.19")]), False)
    case("空 cases 块即红",
         doc("9.21.19", []), False)
    case("混合：1 通过 + 2 降级",
         doc("9.21.19", [c("A", "通过", "9.21.19"),
                        c("B", "通过", "9.12.2"), c("C", "通过", "9.13.1")]),
         True, 2, 1)

    # ── 三块覆盖（票 101 收尾缺口）：红线块与触发块必须同样受检 ──
    case("红线块缺版本字段即红",
         doc("9.21.19", rl=[{"id": "RL-01", "verdict": "通过"}]), False)
    case("触发块缺版本字段即红",
         doc("9.21.19", tr=[{"id": "TR-01", "verdict": "未验证"}]), False)
    case("红线块旧版本通过被降级",
         doc("9.21.19", rl=[c("RL-01", "通过", "9.19.2")]), True, 1, 1)
    case("触发块旧版本通过被降级",
         doc("9.21.19", tr=[c("TR-01", "通过", "9.19.2")]), True, 1, 1)

    missing_block = doc("9.21.19")
    del missing_block["trigger_eval"]
    case("触发块整块缺失即红", missing_block, False)

    not_object = doc("9.21.19")
    not_object["trigger_eval"] = []
    case("触发块不是对象即红", not_object, False)

    empty_rl = doc("9.21.19")
    empty_rl["redline_regression"] = {"cases": []}
    case("红线块为空即红", empty_rl, False)

    for f in failures:
        print("FAIL " + f)
    print("%s 评测账本版本降级：%d 个用例" % ("PASS" if not failures else "FAIL", total_cases[0]))
    return 0 if not failures else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="评测账本版本降级机检")
    ap.add_argument("--selftest", action="store_true", help="跑内置用例再检查真实账本")
    ap.add_argument("--root", default=None, help="技能根（默认脚本所在仓库）")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="输出机器可读 JSON")
    args = ap.parse_args(argv)

    if args.selftest:
        rc = _selftest()
        if rc:
            return rc

    root = Path(args.root) if args.root else skill_root()
    path = root / EVALS
    doc, why = load(path)
    if doc is None:
        print("FAIL [E-EVAL-LEDGER] %s" % why)
        return 1

    errors, stats = audit(doc)
    if args.as_json:
        print(json.dumps({"ok": not errors, "errors": errors, "stats": stats},
                         ensure_ascii=False, indent=1))
    if errors:
        for where, detail in errors:
            print("FAIL [E-EVAL-VERSION] %s :: %s" % (where, detail))
        return 1
    if not args.as_json:
        print("PASS 评测账本：基准版本 %s；共 %d 条——通过 %d / 已降级 %d / 未验证 %d / 未通过 %d"
              % (stats["applies_to_version"], stats["total"], stats["pass"],
                 stats["demoted"], stats["unverified"], stats["failed"]))
        for name, b in stats["blocks"].items():
            print("  %-18s 共 %d 条——通过 %d / 已降级 %d / 未验证 %d / 未通过 %d"
                  % (name, b["total"], b["pass"], b["demoted"],
                     b["unverified"], b["failed"]))
        if stats["demoted_ids"]:
            print("  已降级（旧版本证据，第三态：既非通过也非失败）：%s"
                  % "、".join(stats["demoted_ids"][:8])
                  + ("…" if len(stats["demoted_ids"]) > 8 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
