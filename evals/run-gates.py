#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""闸口总驱动（只读、零网络、幂等、stdlib-only）。

判据（第一性）：只要「README 一份清单、CI 一份清单、本地一份清单」各写各的，
三份必然漂移——本仓已经吃过一次：「基线文档宣称 21/21 全绿，实际 16/21」。
所以命令清单只留**一处正本**：`contracts/scripts-contract.json` 的
`verification.selftest`（21 条脚本自测）+ `verification.evals`（9 条行为机检/登记表机检）。
本地跑 `python -B evals/run-gates.py`，CI 跑**同一条命令**，不存在第二套口径。

三态退出码（票 106）在这里是**分流器**，不是装饰：

    0  全部闸口通过
    1  有闸口查出违规（判据生效）；或清单里某条命令自己参数非法（那是清单坏了）
    2  有闸口未测（环境/输入不可用），且没有任何闸口查出违规
    3  本驱动自身参数非法

为什么 2 必须与 1 分开：CI 的黄灯（check run 的 `neutral`）**只能**由 rc=2 触发。
把「环境炸了」并进 1，CI 只能标红；红多了就没人看红，那正是本票要消灭的假红。
反过来把 2 并进 0，就是本仓反复吃过的假绿。

为什么本驱动不登记进 `verification` 清单：它是**清单的消费者**。把自己写进清单，
`--run` 会递归调用自己。清单正本与消费者分离，递归就不可能发生。

用法：
    python -B evals/run-gates.py                # 跑全部闸口，按三态退出
    python -B evals/run-gates.py --selftest     # 分类器自测（夹具证明它真的会红/黄）
    python -B evals/run-gates.py --json out.json  # 另存机器可读汇总
    python -B evals/run-gates.py --list         # 只打印将要跑的命令，不执行
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ltw_exit  # noqa: E402  三态退出码唯一定义处（票 106）

SKILL_ROOT = Path(__file__).resolve().parent.parent
CONTRACT = SKILL_ROOT / "contracts" / "scripts-contract.json"

VERDICT_OK = "ok"
VERDICT_VIOLATION = "violation"
VERDICT_UNTESTED = "untested"
VERDICT_USAGE = "usage"


def load_commands(path=None):
    """从登记表读命令清单。读不到 = 判据没跑起来（rc=2），不是「查出违规」。"""
    p = Path(path) if path else CONTRACT
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise SystemExit(ltw_exit.env_error(
            "无法读取登记表 %s（%s）" % (p.name, exc), code="E-CONTRACT-INVALID"))
    verification = data.get("verification") or {}
    selftest = list(verification.get("selftest") or [])
    evals = list(verification.get("evals") or [])
    return selftest, evals


def child_env():
    env = dict(os.environ)
    # 本仓踩过 GBK 控制台的坑：子进程统一 UTF-8，避免把编码崩溃误判成判据失败
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def classify(rc):
    """退出码 → 三态。3 是「没进入判据」，对清单来说就是清单坏了，按违规处理。"""
    if rc == ltw_exit.EXIT_OK:
        return VERDICT_OK
    if rc == ltw_exit.EXIT_ENV:
        return VERDICT_UNTESTED
    if rc == ltw_exit.EXIT_VIOLATION:
        return VERDICT_VIOLATION
    return VERDICT_USAGE


def aggregate(verdicts):
    """汇总：违规优先于未测。没有违规时才允许「未测」这一档单独成立。"""
    if any(v in (VERDICT_VIOLATION, VERDICT_USAGE) for v in verdicts):
        return VERDICT_VIOLATION
    if any(v == VERDICT_UNTESTED for v in verdicts):
        return VERDICT_UNTESTED
    return VERDICT_OK


def run_line(line, root=None):
    """按清单原文跑一条命令：`python -B xxx.py args` → 用当前解释器执行。"""
    argv = shlex.split(line)
    if len(argv) < 3 or argv[0] != "python" or argv[1] != "-B":
        return ltw_exit.EXIT_USAGE, "清单条目必须以 `python -B` 开头：%s" % line
    cmd = [sys.executable, "-B"] + argv[2:]
    proc = subprocess.run(cmd, cwd=str(root or SKILL_ROOT), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=child_env())
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()
    return proc.returncode, (tail[-1][:200] if tail else "")


def run_all(commands, root=None, verbose=True):
    rows = []
    for line in commands:
        rc, detail = run_line(line, root=root)
        verdict = classify(rc)
        rows.append({"command": line, "rc": rc, "verdict": verdict, "detail": detail})
        if verbose:
            print("[%-9s] rc=%d  %s" % (verdict, rc, line))
            if verdict != VERDICT_OK and detail:
                print("            %s" % detail)
    return rows


def summarize(rows):
    counts = {k: 0 for k in (VERDICT_OK, VERDICT_VIOLATION, VERDICT_UNTESTED, VERDICT_USAGE)}
    for row in rows:
        counts[row["verdict"]] += 1
    return {
        "verdict": aggregate([r["verdict"] for r in rows]),
        "total": len(rows),
        "counts": counts,
        "commands": rows,
    }


def emit_summary(summary):
    c = summary["counts"]
    print()
    print("汇总：%d 条 = 通过 %d / 违规 %d / 未测 %d / 调用错误 %d → %s"
          % (summary["total"], c[VERDICT_OK], c[VERDICT_VIOLATION],
             c[VERDICT_UNTESTED], c[VERDICT_USAGE], summary["verdict"]))


def _selftest():
    """分类器自测：夹具证明它真的会红、会黄，不是永远绿。

    为什么必须有：一个「永远返回通过」的汇总器，比没有汇总器更糟——它把 21 条闸口
    的结论压成一个绿字。下面三个夹具分别喂 rc=1 / rc=2 / rc=3，逐个断言分档正确，
    再断言汇总优先级（违规压过未测）。
    """
    failures = []
    total = [0]

    def case(name, fn):
        total[0] += 1
        try:
            fn()
            print("PASS", name)
        except AssertionError as exc:
            failures.append("%s：%s" % (name, exc))
            print("FAIL", name, "::", exc)

    def _fixture(code):
        """造一个只按指定码退出的脚本，返回能喂给 run_line 的清单行。"""
        td = tempfile.mkdtemp()
        script = Path(td) / "fixture.py"
        script.write_text("import sys\nsys.exit(%d)\n" % code, encoding="utf-8")
        # 必须用 posix 形式：shlex.split 在 Windows 上会把反斜杠当转义符吃掉，
        # 路径被拼接成 "C:\UsersZehaoAppData..."，夹具于是「文件不存在」→ rc=2。
        # 这个坑是自测自己抓到的（第一次跑 5/8 红），不是猜的。
        return "python -B '%s'" % script.as_posix()

    def violation_is_red():
        rows = run_all([_fixture(1)], verbose=False)
        assert rows[0]["verdict"] == VERDICT_VIOLATION, rows[0]
        assert summarize(rows)["verdict"] == VERDICT_VIOLATION
    case("夹具：rc=1 → 违规（判据生效）", violation_is_red)

    def env_is_untested():
        rows = run_all([_fixture(2)], verbose=False)
        assert rows[0]["verdict"] == VERDICT_UNTESTED, rows[0]
        assert summarize(rows)["verdict"] == VERDICT_UNTESTED, \
            "只有未测时必须汇总成未测，不能塌成通过或违规"
    case("夹具：rc=2 → 未测（不塌成通过）", env_is_untested)

    def usage_is_not_ok():
        rows = run_all([_fixture(3)], verbose=False)
        assert rows[0]["verdict"] == VERDICT_USAGE, rows[0]
        assert summarize(rows)["verdict"] == VERDICT_VIOLATION, \
            "清单条目自己参数非法，是清单坏了，必须红"
    case("夹具：rc=3 → 调用错误（清单坏了，判红）", usage_is_not_ok)

    def violation_beats_untested():
        rows = run_all([_fixture(2), _fixture(1)], verbose=False)
        assert summarize(rows)["verdict"] == VERDICT_VIOLATION, \
            "同时有违规与未测时，必须报违规——未测不能掩盖真实的红"
    case("汇总优先级：违规压过未测", violation_beats_untested)

    def ok_only_is_ok():
        rows = run_all([_fixture(0), _fixture(0)], verbose=False)
        assert summarize(rows)["verdict"] == VERDICT_OK
    case("夹具：全 0 → 通过", ok_only_is_ok)

    def bad_contract_is_env():
        try:
            load_commands(Path(tempfile.mkdtemp()) / "__no_such__.json")
        except SystemExit as exc:
            assert exc.code == ltw_exit.EXIT_ENV, "登记表读不到应 rc=2，实得 %r" % (exc.code,)
            return
        raise AssertionError("登记表读不到却当成通过")
    case("环境夹具：登记表读不到 → rc=2（不塌成绿）", bad_contract_is_env)

    def real_contract_parses():
        selftest, evals = load_commands()
        assert len(selftest) >= 20, "真实登记表 selftest 条目异常：%d" % len(selftest)
        assert len(evals) >= 8, "真实登记表 evals 条目异常：%d" % len(evals)
        for line in selftest + evals:
            assert line.startswith("python -B "), "清单条目格式不合约定：%s" % line
    case("真实登记表：两份清单可解析且格式合规", real_contract_parses)

    def bad_line_is_usage():
        rc, detail = run_line("python -m http.server")
        assert rc == ltw_exit.EXIT_USAGE, "非约定格式的条目应判调用错误，实得 rc=%r" % rc
        assert detail, "调用错误必须带一句原因"
    case("清单条目格式不合约定 → rc=3", bad_line_is_usage)

    if failures:
        print("\n失败 %d / %d" % (len(failures), total[0]))
        for f in failures:
            print(" -", f)
        return ltw_exit.EXIT_VIOLATION
    print("\n全部 %d 个用例通过" % total[0])
    return ltw_exit.EXIT_OK


def main(argv=None):
    ap = ltw_exit.UsageParser(description="闸口总驱动（本地与 CI 同一条命令）")
    ap.add_argument("--selftest", action="store_true", help="分类器自测（不跑真实闸口清单）")
    ap.add_argument("--list", action="store_true", help="只打印将要跑的命令，不执行")
    ap.add_argument("--json", metavar="PATH", default=None, help="把机器可读汇总写到该路径")
    ap.add_argument("--root", metavar="PATH", default=None, help="技能根（默认本文件上一级）")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    selftest, evals = load_commands()
    commands = selftest + evals
    if not commands:
        return ltw_exit.env_error("登记表没有 verification.selftest / verification.evals 条目",
                                  code="E-CONTRACT-INVALID")
    if args.list:
        for line in commands:
            print(line)
        return ltw_exit.EXIT_OK

    root = Path(args.root) if args.root else None
    rows = run_all(commands, root=root)
    summary = summarize(rows)
    emit_summary(summary)
    if args.json:
        Path(args.json).write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n",
                                   encoding="utf-8")
    return {"ok": ltw_exit.EXIT_OK, "violation": ltw_exit.EXIT_VIOLATION,
            "untested": ltw_exit.EXIT_ENV, "usage": ltw_exit.EXIT_USAGE}[summary["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
