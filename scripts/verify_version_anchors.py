#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""四锚点一致性机检（只读、零网络、幂等、stdlib-only）。

票 100 把「版本号四处登记必须一致」从人工逐条核对变成会红的断言。

四处发版锚点（票 52 R4 / references/ops.md「发版锚点四处齐改」）：

    1. SKILL.md            frontmatter  metadata.version
    2. contracts/rules.json            version
    3. README.md                       「本次发布升版到 **X**」
    4. references/ops.md               「**当前核验**：适用版本 X」

为什么必须机检：这四处靠人眼对账，而人眼漏看是**静默**的——entries 里写着一个
旧版本号，读者看到的却是一个已经作废的版本。历史实测：rule_contract.py 只校验
rules.json 的 version，发现不了 SKILL.md 不一致，此处在票 100 之前**没有任何
机检兜底**。

为什么每处都断言「恰好命中 1 次」：正则写窄了会一条都不匹配，而「0 次匹配」
很容易被写成「没有不匹配 → 通过」——那是假绿。同理，锚点重复出现在多处时，
替换改一处会留下第二处旧值，判据仍看着绿。所以每处都要求 hits == 1。

用法：
    python -B scripts/verify_version_anchors.py
    python -B scripts/verify_version_anchors.py --selftest
退出码：0 一致；1 不一致或锚点缺失/重复；2 用法错误。
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
import ltw_exit  # noqa: E402  三态退出码唯一定义处（票 106）

SKILL_MD = "SKILL.md"
CONTRACT = "contracts/rules.json"
README = "README.md"
OPS = "references/ops.md"

# 每处锚点一条正则；必须恰好命中一次。
ANCHORS = (
    ("SKILL.md metadata.version", SKILL_MD,
     re.compile(r"(?m)^\s{2}version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$")),
    ("contracts/rules.json version", CONTRACT,
     re.compile(r'"version"\s*:\s*"([0-9]+\.[0-9]+\.[0-9]+)"')),
    ("README.md 发版行", README,
     re.compile(r"本次发布升版到\s*\*\*([0-9]+\.[0-9]+\.[0-9]+)\*\*")),
    ("references/ops.md 当前核验", OPS,
     re.compile(r"\*\*当前核验\*\*：适用版本\s*([0-9]+\.[0-9]+\.[0-9]+)")),
)


def collect(root: Path):
    """返回 (values, errors)。values: {锚点名: 版本}；errors: [(锚点名, 原因)]。"""
    values, errors = {}, []
    for name, rel, rx in ANCHORS:
        path = root / rel
        if not path.is_file():
            errors.append((name, "文件不存在：%s" % rel))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append((name, "不可读：%s（%s）" % (rel, exc)))
            continue
        hits = rx.findall(text)
        if len(hits) == 0:
            # 0 次匹配不等于通过：正则写窄了或锚点被删了都会到这里。
            errors.append((name, "锚点未命中（0 处）——正则写窄或锚点被删，不得当作通过"))
        elif len(hits) > 1:
            errors.append((name, "锚点命中 %d 处（要求恰好 1 处）：%s" % (len(hits), hits)))
        else:
            values[name] = hits[0]
    return values, errors


def check(root: Path):
    """返回 (ok, values, errors)。"""
    values, errors = collect(root)
    if not errors and values:
        uniq = set(values.values())
        if len(uniq) > 1:
            detail = "；".join("%s=%s" % (k, v) for k, v in values.items())
            errors.append(("四锚点", "取值不一致：%s" % detail))
    return (not errors and len(values) == len(ANCHORS)), values, errors


def _selftest() -> int:
    """内置用例：正例 + 每种失效各一条反例。"""
    failures = []

    def case(name, files, expect_ok):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel, body in files.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body, encoding="utf-8")
            ok, _v, errs = check(root)
            if ok != expect_ok:
                failures.append("%s：期望 ok=%s，实得 ok=%s（%s）"
                                % (name, expect_ok, ok, errs))

    def good(version="9.21.19"):
        return {
            SKILL_MD: "---\nmetadata:\n  version: %s\n---\n" % version,
            CONTRACT: '{\n "version": "%s"\n}\n' % version,
            README: "本次发布升版到 **%s**（SKILL.md 与契约一致）。\n" % version,
            OPS: "**当前核验**：适用版本 %s；核验日期 2026-11-15；依赖 stdlib。\n" % version,
        }

    case("四处同值", good(), True)

    bad = good(); bad[CONTRACT] = '{\n "version": "9.21.18"\n}\n'
    case("契约落后一格", bad, False)

    bad = good(); bad[SKILL_MD] = "---\nmetadata:\n  version: 9.21.18\n---\n"
    case("SKILL.md 落后一格", bad, False)

    bad = good(); bad[README] = "本次发布升版到 **9.21.18**。\n"
    case("README 落后一格", bad, False)

    bad = good(); bad[OPS] = "**当前核验**：适用版本 9.21.18；核验日期 2026-11-15。\n"
    case("ops.md 落后一格", bad, False)

    # 锚点被删：0 次匹配必须红，不能当成「没有不一致」
    bad = good(); bad[OPS] = "当前核验：见别处。\n"
    case("ops.md 锚点被删（0 命中）", bad, False)

    # 锚点重复：改一处会留下第二处旧值
    bad = good(); bad[README] = bad[README] + "本次发布升版到 **9.21.18**。\n"
    case("README 锚点重复（2 命中）", bad, False)

    # 文件缺失：fail closed
    bad = good(); del bad[OPS]
    case("ops.md 缺失", bad, False)

    for f in failures:
        print("FAIL " + f)
    print("%s 四锚点一致性：%d 个用例" % ("PASS" if not failures else "FAIL", 8))
    return 0 if not failures else 1


def main(argv=None) -> int:
    ap = ltw_exit.UsageParser(description="四锚点版本一致性机检")
    ap.add_argument("--selftest", action="store_true", help="跑内置用例再检查真实树")
    ap.add_argument("--root", default=None, help="技能根（默认脚本所在仓库）")
    args = ap.parse_args(argv)

    if args.selftest:
        rc = _selftest()
        if rc:
            return rc

    root = Path(args.root) if args.root else skill_root()
    rc_root = ltw_exit.require_root(root)
    if rc_root is not None:
        return rc_root
    ok, values, errors = check(root)
    if errors:
        for name, why in errors:
            print("FAIL [E-VERSION-ANCHOR] %s :: %s" % (name, why))
        return ltw_exit.EXIT_VIOLATION
    if not ok:
        print("FAIL [E-VERSION-ANCHOR] 四锚点未全部取到值")
        return ltw_exit.EXIT_VIOLATION
    version = next(iter(values.values()))
    print("PASS 四锚点一致：%s（%d 处）" % (version, len(values)))
    return ltw_exit.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
