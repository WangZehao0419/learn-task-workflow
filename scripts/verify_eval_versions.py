#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""评测账本版本降级机检（只读、零网络、幂等、stdlib-only）。

票 101 把「判据一改，旧证据自动作废」从一句口头承诺变成机器能执行的事。

背景：`evals/evals.json` 里 20 条证据的 verdict 曾是「通过」，但它们证明的是
v9.12.2 / v9.13.x 的制品，而账本的 applies_to_version 早已前进。没有字段标记这件事，
旧证据就能一直挂在「通过」栏里——它证明的那个版本早就不存在了。

判据（三条，互相独立）：

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


def _valid_version(v):
    """x.y.z 或 unknown 合法；其余（含 null、空串、v 前缀）非法。"""
    return isinstance(v, str) and (v == UNKNOWN or bool(VERSION_RE.match(v)))


def audit(doc):
    """返回 (errors, stats)。stats 里 pass/demoted/unverified 都按「降级后」口径计。"""
    errors = []
    applies = doc.get("applies_to_version")
    if not _valid_version(applies):
        errors.append(("applies_to_version", "取值非法或缺失：%r" % (applies,)))

    cases = doc.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append(("cases", "缺失或为空——没有证据的账本不能当作「全过」"))
        return errors, {}

    n_pass = n_demoted = n_unverified = n_fail = 0
    demoted_ids = []
    for i, c in enumerate(cases):
        cid = c.get("id") or "cases[%d]" % i
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
                n_demoted += 1
                demoted_ids.append(cid)
            else:
                n_unverified += 1
            continue
        if verdict == PASS:
            n_pass += 1
        elif verdict == "未通过":
            n_fail += 1
        else:
            n_unverified += 1

    stats = {
        "applies_to_version": applies,
        "total": len(cases),
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
    """内置用例：正例 + 三种结构缺失 + 降级语义（通过→未验证，不是失败）。"""
    failures = []

    def case(name, doc, expect_ok, expect_demoted=None, expect_pass=None):
        errs, st = audit(doc)
        ok = not errs
        if ok != expect_ok:
            failures.append("%s：期望 ok=%s，实得 ok=%s（%s）" % (name, expect_ok, ok, errs))
            return
        if expect_demoted is not None and st.get("demoted") != expect_demoted:
            failures.append("%s：期望降级 %d 条，实得 %s" % (name, expect_demoted, st.get("demoted")))
        if expect_pass is not None and st.get("pass") != expect_pass:
            failures.append("%s：期望通过 %d 条，实得 %s" % (name, expect_pass, st.get("pass")))

    def doc(applies, cases):
        return {"applies_to_version": applies, "cases": cases}

    def c(cid, verdict, dv):
        return {"id": cid, "verdict": verdict, "decided_against_version": dv}

    case("同版本通过计入通过",
         doc("10.0.0", [c("A", "通过", "10.0.0")]), True, 0, 1)
    case("旧版本通过被降级",
         doc("10.0.0", [c("A", "通过", "9.12.2")]), True, 1, 0)
    case("unknown 被降级",
         doc("10.0.0", [c("A", "通过", "unknown")]), True, 1, 0)
    case("旧版本未通过不算降级（它本来就不在通过栏）",
         doc("10.0.0", [c("A", "未通过", "9.12.2")]), True, 0, 0)
    case("缺字段即红",
         doc("10.0.0", [{"id": "A", "verdict": "通过"}]), False)
    case("版本形态非法即红",
         doc("10.0.0", [c("A", "通过", "v9.12.2")]), False)
    case("verdict 非法即红",
         doc("10.0.0", [c("A", "过了", "10.0.0")]), False)
    case("空账本即红",
         doc("10.0.0", []), False)
    case("混合：1 通过 + 2 降级",
         doc("10.0.0", [c("A", "通过", "10.0.0"),
                        c("B", "通过", "9.12.2"), c("C", "通过", "9.13.1")]),
         True, 2, 1)

    for f in failures:
        print("FAIL " + f)
    print("%s 评测账本版本降级：%d 个用例" % ("PASS" if not failures else "FAIL", 9))
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
        if stats["demoted_ids"]:
            print("  已降级（旧版本证据，第三态：既非通过也非失败）：%s"
                  % "、".join(stats["demoted_ids"][:8])
                  + ("…" if len(stats["demoted_ids"]) > 8 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
