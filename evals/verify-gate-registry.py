#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-gate-registry.py - 验收清单登记表机检（stdlib-only、只读、零网络、可重复）。

判据（第一性）：一条验收命令只有在**能失败**时才叫闸口；一个模块只有在**被登记过**
时才进得了清单。登记表是 `contracts/scripts-contract.json`——本评估把它从「文档」
变成「可判的闸口」，四条检查：

  G1 分区完备    scripts/*.py 的每个文件在 scripts_contract 或 internal_modules 中
                 恰好出现一次；不重、不漏、不指向不存在的文件。
  G2 分类自证    登记为 CLI 的脚本，喂一个**必败参数**必须 rc≠0（真的会拒绝坏参数）；
                 登记为内部模块的，喂同一个必败参数必须 rc=0（真的没有 CLI）。
                 「有没有 CLI」不是声称，是实测。
  G3 清单可执行  verification.selftest 的每条命令都必须 rc=0。
  G4 清单同源    verification.selftest 覆盖的脚本集合必须与 scripts_contract 相等。

为什么 G2 是核心：`ltw_parse.py` / `ltw_typography.py` 这类无 `__main__` 的模块对
**任何**参数都 rc=0（`--selftest` 与 `--this-flag-does-not-exist` 一视同仁）。把它们
放进 `for s in scripts/*.py` 这类循环，循环永远绿、永远抓不到「模块没 CLI」这件事
（票 65）。把分类写成**可实测的断言**之后，新模块无论补不补 CLI 都必须先登记，登
记错就被 G2 当场打红——这是本评估存在的原因。

用法：python -B evals/verify-gate-registry.py [--selftest]
退出码：0 全过；1 有失败；2 参数/环境错误。
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
CONTRACT = SKILL_ROOT / "contracts" / "scripts-contract.json"

# 必败参数：任何正经 argparse 入口都会以 rc=2 拒绝它。
# 对无 CLI 的模块它什么也不触发——这正是我们要区分的两种形态。
BOGUS_FLAG = "--this-flag-does-not-exist"


class Checker:
    def __init__(self):
        self.ok = 0
        self.fail = 0

    def check(self, name, cond, detail=""):
        passed = bool(cond)
        self.ok += passed
        self.fail += not passed
        line = "[{}] {}".format("OK" if passed else "FAIL", name)
        if detail and not passed:
            line += "（{}）".format(detail)
        print(line)


def load_contract():
    try:
        return json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print("E-CONTRACT-INVALID：无法读取 {}（{}）".format(CONTRACT.name, exc), file=sys.stderr)
        raise SystemExit(2)


def child_env():
    env = dict(os.environ)
    # 本仓踩过 GBK 控制台的坑：子进程统一按 UTF-8 输出，避免把编码崩溃误判成判据失败
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def run_script(script, args):
    cmd = [sys.executable, "-B", str(SKILL_ROOT / "scripts" / script)] + list(args)
    proc = subprocess.run(cmd, cwd=str(SKILL_ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=child_env())
    return proc.returncode


def run_cmd(line):
    argv = [sys.executable, "-B"] + shlex.split(line)[2:]
    proc = subprocess.run(argv, cwd=str(SKILL_ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=child_env())
    return proc.returncode


def script_of(line):
    for token in shlex.split(line):
        if token.endswith(".py"):
            return Path(token).name
    return None


def main():
    ap = argparse.ArgumentParser(description="验收清单登记表机检（G1-G4）")
    ap.add_argument("--selftest", action="store_true",
                    help="幂等开关：本评估无状态，带与不带行为相同")
    ap.parse_args()

    data = load_contract()
    cli = [s.get("script", "") for s in data.get("scripts_contract", [])]
    internal = [m.get("script", "") for m in data.get("internal_modules", [])]
    selftest = list(data.get("verification", {}).get("selftest", []))
    on_disk = {p.name for p in (SKILL_ROOT / "scripts").glob("*.py")}
    cli_set, int_set = set(cli), set(internal)
    c = Checker()

    # ── G1 分区完备 ────────────────────────────────────────────────
    c.check("G1 不重名：scripts_contract 与 internal_modules 无交集",
            not (cli_set & int_set), "重复登记 {}".format(sorted(cli_set & int_set)))
    c.check("G1 不遗漏：scripts/ 下每个 .py 都已登记（命令行或内部模块）",
            on_disk <= (cli_set | int_set), "未登记 {}".format(sorted(on_disk - (cli_set | int_set))))
    c.check("G1 无幽灵：登记的每个脚本都真实存在",
            (cli_set | int_set) <= on_disk, "不存在 {}".format(sorted((cli_set | int_set) - on_disk)))

    # ── G2 分类自证：结论靠实测，不靠声称 ──────────────────────────
    for name in cli:
        if name not in on_disk:
            continue
        rc = run_script(name, [BOGUS_FLAG])
        c.check("G2 命令行自证：{} 拒绝坏参数".format(name), rc != 0,
                "rc={}，应为非 0——对任何参数都返回 0 的「脚本」不构成闸口".format(rc))
    for name in internal:
        if name not in on_disk:
            continue
        rc = run_script(name, [BOGUS_FLAG])
        c.check("G2 内部模块自证：{} 确无 CLI".format(name), rc == 0,
                "rc={}，应为 0——它有 CLI 就必须登记进 scripts_contract 并进 selftest 清单".format(rc))

    # ── G3 清单可执行 ──────────────────────────────────────────────
    for line in selftest:
        rc = run_cmd(line)
        c.check("G3 可执行：{}".format(line), rc == 0, "rc={}".format(rc))

    # ── G4 清单同源：selftest 与脚本契约必须逐项对上 ────────────────
    covered = {s for s in (script_of(x) for x in selftest) if s}
    c.check("G4 同源：verification.selftest 覆盖集合 == scripts_contract",
            covered == cli_set,
            "契约缺 {} / 清单多 {}".format(sorted(cli_set - covered), sorted(covered - cli_set)))

    print()
    print("G1-G4 汇总：{} 过 / {} 败；scripts/ {} 个文件 = {} 命令行 + {} 内部模块；"
          "selftest 清单 {} 条".format(c.ok, c.fail, len(on_disk), len(cli), len(internal), len(selftest)))
    return 1 if c.fail else 0


if __name__ == "__main__":
    sys.exit(main())
