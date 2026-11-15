#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三态退出码的唯一定义处（stdlib-only、无 CLI；被命令行脚本与评估脚本导入）。

判据（第一性）：退出码只回答一个问题——判据有没有跑起来、跑出了什么。它不回答
「哪里坏了」。所以码只有三档，外加一个「没进入判据」的调用错误：

    0  EXIT_OK         判据跑完，通过
    1  EXIT_VIOLATION  判据跑完，查出违规（判据生效）
    2  EXIT_ENV        未测：环境/输入不可用，判据没有跑起来
    3  EXIT_USAGE      调用错误（参数非法）——不是第四态，是「没进入判据」

为什么 2 不能继续兼作「用法错误」（9.21.26 之前全仓就是这样）：
    如果参数写错也返回 2，那么「喂一个环境不可用夹具必须 rc=2」这条机检会被
    「喂一个必败参数」直接满足——闸口看着全绿，而它证明的只是 argparse 会拒绝坏参数，
    不是脚本分得清「没测」与「没通过」。三态只有在 2 与 3 分开之后才有判据力。
    这条理由必须留在代码旁边：它是「为什么多一个码」的唯一答案。

为什么 2 也不能是 1：rc=1 的含义是「判据生效了」。环境炸了却报 1，等于用一次
    从未发生的检查去指控制品；反过来，任何「跳过（未校验）」打印完仍 rc=0，等于用
    一次从未发生的检查去放行制品。两者都是假绿/假红，本仓历史上反复吃过
    （票 66 的「通过」假绿、票 65 的恒绿自测、票 106 的原始缺陷）。

为什么 2 必须在输出层留痕：只改退出码，调用方仍看不出「没测」与「没通过」的差别，
    机检也没法证明「环境不可用」真的走了另一条分支——它只能看到一个数字 2。
    所以 env_error() 一律在 stderr 打一行结构化 JSON（ok=false / verdict=untested /
    untested=true / code / message），机检按 code 前缀或 untested 标记判定。

本模块自己没有 CLI：喂任何参数都不触发判据（由 evals/verify-gate-registry.py 的
G2「内部模块自证」实测）。它只提供常量、两处结构化失败与一个拒绝坏参数的 parser 基类。
"""

from __future__ import annotations

import argparse
import json
import sys

# 三态（判据轴）+ 调用错误（未进入判据轴）。数字本身是契约，不得在调用侧写死。
EXIT_OK = 0
EXIT_VIOLATION = 1
EXIT_ENV = 2
EXIT_USAGE = 3

# 结构化码：环境不可用与调用错误各一个通用码，具体原因进 message。
# 两者都登记在 contracts/rules.json 的 constants.errors 里，并由 references/registry.md
# 双向对拍——新增退出码语义却不登记错误码，等于又开一条「文档落后于代码」的口子。
ENV_CODE = "E-ENV-UNAVAILABLE"
USAGE_CODE = "E-USAGE"

# 口径版本。**它只有一处读取者**：scripts/verify_exit_tristate.py 的 selftest 断言
# 契约 contracts/scripts-contract.json 的 exit_tristate.schema 与它相等——「文档写一个版本、
# 代码写另一个」正是本仓 schema 漂移过的形态（票 91）。没有这个读取者，这行就是一句
# 无人核对的承诺，所以读取与断言一起落地，不留空话。
SCHEMA = "ltw-exit/1"

VERDICT_UNTESTED = "untested"
VERDICT_USAGE = "usage"


def require_root(root) -> int | None:
    """技能根/数据根不存在或不是目录时，返回 EXIT_ENV；可用时返回 None。

    为什么把这条单独抽出来（票 106 的 AC3）：`--root` 指向一个不存在的目录时，
    「读不到制品」与「制品违规」在旧实现里都落成 rc=1，于是七个脚本的环境分支
    根本没被改到——它们看起来都「有退出码」，但没有一个能分清未测与违规。
    抽成一处之后，新脚本只要调它一次就自动符合，不会再漏。
    """
    from pathlib import Path
    p = Path(root)
    if p.exists() and p.is_dir():
        return None
    return env_error("根目录不存在或不是目录：" + str(p))


def emit(payload: dict) -> None:
    """把一条结构化结果打到 stderr；单行 JSON，便于调用方逐行解析。

    为什么固定 stderr 而不给调用方选流：三态标记是**诊断通道**，stdout 留给正常结果。
    留一个 stream 参数只会让某个调用方把标记写进 stdout，然后消费端把它当成正常输出解析。
    """
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)


def env_error(message: str, *, code: str = ENV_CODE, extra: dict | None = None) -> int:
    """环境/输入不可用：判据没有跑起来。

    返回值就是 EXIT_ENV，调用方一律写成 return ltw_exit.env_error(...)——
    不在调用侧再写一个 2，也不在调用侧另拼一份 JSON：同一份口径只有一个定义处。
    """
    payload = {"ok": False, "verdict": VERDICT_UNTESTED, "untested": True,
               "code": code, "message": message}
    if extra:
        payload.update(extra)
    emit(payload)
    return EXIT_ENV


def usage_error(message: str, *, code: str = USAGE_CODE, parser=None) -> int:
    """调用错误：参数非法，判据没有进入。

    parser 给定时先打 usage（与 argparse 原生行为一致），再打结构化 JSON——
    「人看 usage、机器看 code」，两者都不省。
    """
    if parser is not None:
        parser.print_usage(sys.stderr)
    emit({"ok": False, "verdict": VERDICT_USAGE, "code": code, "message": message})
    return EXIT_USAGE


class UsageParser(argparse.ArgumentParser):
    """argparse 的用法错误默认 exit 2（与「环境不可用」撞码），这里改判 3。

    子类化而不是在每个脚本里 catch SystemExit：后者要写 18 遍，且新脚本一定会漏；
    基类一处收口，新增脚本只要用 UsageParser 就自动符合三态。
    """

    def error(self, message):  # noqa: D401 - argparse 约定签名
        self.print_usage(sys.stderr)
        emit({"ok": False, "verdict": VERDICT_USAGE, "code": USAGE_CODE,
              "message": message})
        raise SystemExit(EXIT_USAGE)
