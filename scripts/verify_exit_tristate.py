#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三态退出码机检（票 106）：0 = 通过 / 1 = 查出违规 / 2 = 未测 / 3 = 调用错误。

判据（第一性）：退出码只回答一个问题——**判据有没有跑起来、跑出了什么**。它不回答
「哪里坏了」。所以：

    0  判据跑完，通过
    1  判据跑完，查出违规（判据生效）
    2  未测：环境/输入不可用，判据没有跑起来
    3  调用错误：参数非法，判据没有进入（不是第四态，是「没有结果」的另一种）

为什么这条机检必须存在（票 106 的原始缺陷）：10.0.6 之前 **rc=1 既可能是「查出违规」
也可能是「环境炸了」**。两者不可区分，所以任何「跑绿了就算过」的验收都是假绿——你没法
证明那次 rc=1 是判据在起作用，还是 Python 没装。CI（票 107）的前置正是这一条。

四条判据，各自独立、各自能单独证红：

    E-TRISTATE-ENV-NOT-2     喂「环境不可用」夹具，脚本必须 rc=2（不得 0/1/3）
    E-TRISTATE-ENV-NO-MARK    rc=2 时 stderr 必须有结构化 untested 标记（只改数字不算分开）
    E-TRISTATE-VIOLATION-1   喂「查出违规」夹具，必须 rc=1（判据真的生效）
    E-TRISTATE-USAGE-3       喂「必败参数」，必须 rc=3（不得与「未测」撞码 2）

为什么「只改退出码」不够、还要查输出层标记：调用方读一个数字 2 无法区分「没测」与
「没通过」，而机检也只能看到一个数字——它证明不了「环境不可用」真的走了另一条分支。
所以 env_error() 一律在 stderr 打一行结构化 JSON（ok=false / verdict=untested /
untested=true），本机检按它判定。

为什么必须做**变异测试**：把某个脚本的环境分支改回 rc=1，本机检必须变红。否则「全绿」
只证明脚本现在恰好都对，证明不了这条闸口咬得住——本仓反复吃过的恒绿自测就是这种形态。

夹具口径：每个脚本的「环境不可用」都是真实可构造的（不存在的路径 / 不可读的清单 /
坏掉的账本），不 mock、不打桩——打桩会把「脚本怎么判定环境」这件事从被测范围里拿掉，
而那正是本票要验的东西。

用法：
    python -B scripts/verify_exit_tristate.py              # 检查真实树
    python -B scripts/verify_exit_tristate.py --selftest   # 自测 + 真实树
退出码：0 全过；1 有脚本不符合三态；2 本机检自身无法判定（解释器/环境不可用）。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ltw_exit  # noqa: E402  三态退出码唯一定义处（票 106）
from rule_contract import skill_root  # noqa: E402


def child_env():
    env = dict(os.environ)
    # 本仓踩过 GBK 控制台的坑：子进程统一按 UTF-8 输出，避免编码崩溃被误判成判据失败。
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def run(root: Path, rel: str, args) -> tuple:
    """跑一个脚本，返回 (rc, stdout, stderr)。"""
    cmd = [sys.executable, "-B", str(root / rel)] + list(args)
    proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=child_env())
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def untested_marked(stderr: str) -> bool:
    """stderr 里是否有一行结构化「未测」标记。

    逐行解析而不是子串匹配：这类子串在正常输出里也可能出现（比如本机检自己的报告），
    只有**独立一行的 JSON 对象**才算脚本自己的标记。
    """
    for line in stderr.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict) and (obj.get("untested") is True
                                     or obj.get("verdict") == "untested"):
            return True
    return False


# ── 夹具表 ────────────────────────────────────────────────────────────────
# 每个条目：(脚本相对路径, [环境不可用参数], 说明)。
# 夹具必须是**真实的**环境不可用，不是 mock：不存在的路径、不可读的清单、坏掉的账本。
ENV_CASES = [
    ("scripts/task_index.py", ["--root", "__no_such_root__"], "数据根不存在"),
    ("scripts/scheduler.py", ["due-queue", "--root", "__no_such_root__",
                              "--today", "2026-01-01"], "数据根不存在"),
    ("scripts/scheduler.py", ["calibration", "--root", "__no_such_root__"], "数据根不存在"),
    ("scripts/scheduler.py", ["day-streak", "--root", "__no_such_root__",
                              "--today", "2026-01-01"], "数据根不存在"),
    ("scripts/kp_sort.py", ["__no_such_list__.md"], "清单文件不存在"),
    ("scripts/verify_explanation.py", ["__no_such_path__"], "路径不存在"),
    ("scripts/prereq_check.py", ["--list", "__no_such_list__.md",
                                 "--scan", "__no_such_scan__.md"], "清单文件不存在"),
    ("scripts/progress_check.py", ["__no_such_task__"], "任务目录缺 progress.md"),
    ("scripts/verify_effect_report.py", ["__no_such_task__"], "任务目录不存在"),
    ("scripts/verify_eval_versions.py", ["--root", "__no_such_root__"], "账本不可读"),
    # 以下七个脚本的「环境」是 --root 指向的仓根：不存在时必须 rc=2，而不是
    # 把「读不到制品」记成「制品违规」。票 106 首轮实测它们全部落成 rc=1——那正是
    # 本票要消灭的缺陷形态，所以每个都留一条夹具钉住。
    ("scripts/verify-doc-pointers.py", ["--root", "__no_such_root__"], "仓根不存在"),
    ("scripts/verify_version_anchors.py", ["--root", "__no_such_root__"], "仓根不存在"),
    ("scripts/verify_volume_budget.py", ["--root", "__no_such_root__"], "仓根不存在"),
    ("scripts/verify_content_ledger.py", ["--root", "__no_such_root__"], "仓根不存在"),
    ("scripts/verify_admission.py", ["--root", "__no_such_root__"], "仓根不存在"),
    ("scripts/verify_entry_budget.py", ["--root", "__no_such_root__"], "仓根不存在"),
    ("scripts/verify_subject_fanout.py", ["--root", "__no_such_root__"], "仓根不存在"),
]

# 查出违规夹具：(脚本, [参数], 说明)。判据必须真的生效并报 rc=1。
# 这里用**必然违规的最小制品**，不是真实仓内文件——真实文件随时可能变绿。
VIOLATION_CASES = [
    ("scripts/verify_explanation.py", ["{bad_handout}"], "讲义缺五要素"),
    ("scripts/kp_sort.py", ["{bad_list}"], "清单畸形行"),
]


def write_bad_handout(td: Path) -> str:
    """造一份**必然 E 级违规**的讲义：图引用死链。

    为什么用死链而不是「缺五要素」：五要素检查对**不像讲义**的文本会整份跳过并打印
    「已跳过（未校验）」，那不是违规、rc=0 是对的（票 66 语义：跳过 ≠ 通过，也不等于
    失败）。拿它当「查出违规」夹具，会把一条正确的跳过语义误判成闸口失效。
    死链（E-IMG-DEADLINK）对任何含图文本都生效、不受 gate 约束，是稳定的 E 级违规源。
    """
    p = td / "bad-handout.md"
    p.write_text("# 讲义\n\n图：assets/definitely-missing.svg\n", encoding="utf-8")
    return str(p)


def write_bad_list(td: Path) -> str:
    p = td / "bad-list.md"
    # 目行缺段 → 畸形（kp_sort 判 rc=1）。
    p.write_text("# 课程体系\n- KP-01-01 ｜ 只有两段\n", encoding="utf-8")
    return str(p)


def check(root: Path, cases_env=None, cases_viol=None) -> list:
    """返回违规列表；空 = 全绿。"""
    problems = []
    cases_env = ENV_CASES if cases_env is None else cases_env
    cases_viol = VIOLATION_CASES if cases_viol is None else cases_viol

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # 夹具路径解析：{bad_handout} / {bad_list} 指向临时目录里的坏制品。
        made = {}

        def resolve_args(args):
            out = []
            for a in args:
                if a == "{bad_handout}":
                    made.setdefault("bad_handout", write_bad_handout(td))
                    out.append(made["bad_handout"])
                elif a == "{bad_list}":
                    made.setdefault("bad_list", write_bad_list(td))
                    out.append(made["bad_list"])
                else:
                    out.append(a)
            return out

        for rel, args, why in cases_env:
            rc, _out, err = run(root, rel, resolve_args(args))
            if rc != ltw_exit.EXIT_ENV:
                problems.append(("E-TRISTATE-ENV-NOT-2",
                                 "%s（%s）应 rc=2（未测），实得 rc=%d" % (rel, why, rc)))
                continue
            if not untested_marked(err):
                problems.append(("E-TRISTATE-ENV-NO-MARK",
                                 "%s（%s）rc=2 但 stderr 没有 untested 结构化标记"
                                 % (rel, why)))

        for rel, args, why in cases_viol:
            rc, _out, _err = run(root, rel, resolve_args(args))
            if rc != ltw_exit.EXIT_VIOLATION:
                problems.append(("E-TRISTATE-VIOLATION-1",
                                 "%s（%s）应 rc=1（查出违规），实得 rc=%d" % (rel, why, rc)))

    return problems


CONTRACT = "contracts/scripts-contract.json"


def cli_scripts(root: Path) -> list:
    """命令行脚本名单，**从登记表读**，不 glob。

    为什么不能用 glob：scripts/ 下还有无 CLI 的内部模块（ltw_parse / ltw_typography /
    ltw_exit），它们对任何参数都 rc=0 是对的（G2「内部模块自证」正是这么断言的）。
    用 glob 会把它们拉进「必败参数必须 rc=3」的检查里，然后得出「闸口失效」的错误结论
    ——那不是脚本错了，是检查范围错了。名单的唯一正本是登记表的 scripts_contract 分区。
    """
    try:
        data = json.loads((root / CONTRACT).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return ["scripts/" + s.get("script", "") for s in data.get("scripts_contract", [])
            if s.get("script")]


def check_usage(root: Path) -> list:
    """必败参数必须 rc=3：证明「调用错误」与「环境不可用」没有撞码。"""
    problems = []
    scripts = cli_scripts(root)
    if not scripts:
        problems.append(("E-TRISTATE-NO-MANIFEST",
                         "%s 读不到 scripts_contract，命令行名单为空——名单为空时"
                         "「全部合规」不构成证据" % CONTRACT))
        return problems
    for rel in scripts:
        rc, _out, _err = run(root, rel, ["--this-flag-does-not-exist"])
        if rc != ltw_exit.EXIT_USAGE:
            problems.append(("E-TRISTATE-USAGE-3",
                             "%s 喂必败参数应 rc=3，实得 rc=%d" % (rel, rc)))
    return problems


def _copy_tree(real: Path, root: Path) -> None:
    """把真实仓的 scripts/contracts/references/evals 拷到临时根（变异测试用）。"""
    for sub in ("scripts", "contracts", "references", "evals"):
        src = real / sub
        if not src.is_dir():
            continue
        dst = root / sub
        dst.mkdir(parents=True)
        for p in src.rglob("*"):
            if p.is_file() and p.suffix in (".py", ".json", ".md"):
                target = dst / p.relative_to(src)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(p.read_bytes())


def _selftest() -> int:
    """自测：夹具变异（改回 rc=1 必须红）+ 真实树检查。"""
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

    def bad_handout_rc_is_1():
        with tempfile.TemporaryDirectory() as td:
            rc, _o, _e = run(skill_root(), "scripts/verify_explanation.py",
                             [write_bad_handout(Path(td))])
            assert rc == ltw_exit.EXIT_VIOLATION, \
                "坏讲义应 rc=1（判据生效），实得 rc=%d" % rc
    case("违规夹具：坏讲义 rc=1（判据真的生效）", bad_handout_rc_is_1)

    def env_case_rc_is_2():
        with tempfile.TemporaryDirectory() as td:
            rc, _o, err = run(skill_root(), "scripts/task_index.py",
                              ["--root", str(Path(td) / "__no_such__")])
            assert rc == ltw_exit.EXIT_ENV, "环境不可用应 rc=2，实得 rc=%d" % rc
            assert untested_marked(err), "rc=2 时缺 untested 标记"
    case("环境夹具：数据根不存在 rc=2 且带 untested 标记", env_case_rc_is_2)

    def usage_rc_is_3():
        rc, _o, _e = run(skill_root(), "scripts/rule_contract.py",
                         ["--this-flag-does-not-exist"])
        assert rc == ltw_exit.EXIT_USAGE, "必败参数应 rc=3，实得 rc=%d" % rc
    case("调用错误：必败参数 rc=3（不与未测撞码）", usage_rc_is_3)

    # ── 变异测试：把环境分支改回 rc=1，机检必须变红 ──────────────────────────
    # 这是本票 AC 的硬要求：「把某脚本的环境错误改回 rc=1，机检必须变红」。
    # 做法：拷一份真身到临时根，把 ltw_exit.EXIT_ENV 的取值改成 1，再跑同一条夹具。
    def mutation_env_to_1_turns_red():
        """变异 A：把**某个脚本自己**的环境分支改回 rc=1。

        为什么改脚本而不是改 ltw_exit 常量：改常量只证明「机检读得到那个数字」，
        证明不了「某个脚本把环境失败真的走成了 2」。本票 AC 的原话是「把某脚本的
        环境错误改回 rc=1，机检必须变红」——所以变异必须落在**脚本**上。
        """
        real = skill_root()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _copy_tree(real, root)
            # 挑一个真实走 env_error 的脚本，把它的调用改回裸 return 1。
            target = root / "scripts" / "task_index.py"
            text = target.read_text(encoding="utf-8")
            anchor = "        return ltw_exit.env_error(\n            \"数据根不存在或不是目录"
            assert text.count(anchor) == 1, \
                "变异锚点必须唯一：task_index.py 里匹配到 %d 处" % text.count(anchor)
            mutated = text.replace(
                anchor, "        return 1  # 变异：环境失败改回 rc=1\n            \"数据根不存在或不是目录", 1)
            assert mutated != text, "变异未生效"
            target.write_text(mutated, encoding="utf-8")
            probs = check(root)
            assert any(code == "E-TRISTATE-ENV-NOT-2" for code, _ in probs), \
                "把某脚本的环境分支改回 rc=1 后机检仍是绿的（闸口咬不住）：%s" % (probs[:2],)
    case("变异：某脚本的环境分支改回 rc=1 → 机检变红", mutation_env_to_1_turns_red)

    def mutation_usage_to_2_turns_red():
        """变异 B：把 UsageParser 的用法错误码改回 2（旧 argparse 默认），与「未测」撞码。"""
        real = skill_root()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _copy_tree(real, root)
            mod = root / "scripts" / "ltw_exit.py"
            text = mod.read_text(encoding="utf-8")
            anchor = "raise SystemExit(EXIT_USAGE)"
            assert text.count(anchor) == 1, \
                "变异锚点必须唯一：ltw_exit.py 里匹配到 %d 处" % text.count(anchor)
            mutated = text.replace(anchor, "raise SystemExit(2)  # 变异：撞回未测的码", 1)
            assert mutated != text, "变异未生效"
            mod.write_text(mutated, encoding="utf-8")
            probs = check_usage(root)
            assert any(code == "E-TRISTATE-USAGE-3" for code, _ in probs), \
                "把调用错误改回 rc=2 后机检仍是绿的：%s" % (probs[:2],)
    case("变异：调用错误改回 rc=2 → 机检变红", mutation_usage_to_2_turns_red)

    def contract_schema_matches_module():
        """契约 exit_tristate.schema 必须等于 ltw_exit.SCHEMA（票 91 的 schema 漂移形态）。"""
        data = json.loads((skill_root() / CONTRACT).read_text(encoding="utf-8"))
        block = data.get("exit_tristate") or {}
        assert block.get("schema") == ltw_exit.SCHEMA, \
            "契约 exit_tristate.schema=%r ≠ ltw_exit.SCHEMA=%r" % (
                block.get("schema"), ltw_exit.SCHEMA)
        assert block.get("definition") == "scripts/ltw_exit.py", \
            "唯一定义处必须登记为 scripts/ltw_exit.py，实际 %r" % block.get("definition")
    case("契约 exit_tristate.schema == ltw_exit.SCHEMA（两处副本不得漂移）",
         contract_schema_matches_module)

    def real_tree():
        probs = check(skill_root())
        assert not probs, probs
        probs2 = check_usage(skill_root())
        assert not probs2, probs2
    case("真实树：环境夹具全 rc=2、违规夹具全 rc=1、必败参数全 rc=3", real_tree)

    if failures:
        for f in failures:
            print("FAIL " + f)
        return ltw_exit.EXIT_VIOLATION
    print("PASS 三态退出码：%d 个用例" % total[0])
    return ltw_exit.EXIT_OK


def main(argv=None) -> int:
    ap = ltw_exit.UsageParser(description="三态退出码机检（票 106）")
    ap.add_argument("--selftest", action="store_true", help="跑内置用例再检查真实树")
    ap.add_argument("--root", default=None, help="技能根（默认脚本所在仓库）")
    args = ap.parse_args(argv)

    if args.selftest:
        rc = _selftest()
        if rc:
            return rc

    root = Path(args.root) if args.root else skill_root()
    probs = check(root) + check_usage(root)
    for code, detail in probs:
        print("FAIL [%s] %s" % (code, detail))
    if probs:
        return ltw_exit.EXIT_VIOLATION
    print("PASS 三态退出码：环境夹具全 rc=2（带 untested 标记）、违规夹具全 rc=1、"
          "必败参数全 rc=3")
    return ltw_exit.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
