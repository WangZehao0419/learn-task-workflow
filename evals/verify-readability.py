#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-readability.py - 读者版可读性行为测试（stdlib-only、只读）。

只验证 `verify_explanation.py --reader` 在夹具与典型回退上的行为，不再另写一套
版面规则，也不再扫描文档措辞。语义效果仍由真人冷读与延迟迁移验证。
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SAMPLE_REL = "evals/fixtures/reader-layout/L1-机会成本-读者版样板.md"
PROCEDURE_REL = "evals/fixtures/reader-layout/procedure/L1-二分法-程序型样板.md"
DESIGN_REL = "evals/fixtures/reader-layout/design/L1-备份方案-设计型样板.md"
SVG_REL = "evals/fixtures/reader-layout/assets/01-机会成本判定流程.svg"


class Checker:
    def __init__(self):
        self.ok = 0
        self.fail = 0

    def check(self, name, cond, detail=""):
        passed = bool(cond)
        self.ok += passed
        self.fail += not passed
        line = f"[{'OK' if passed else 'FAIL'}] {name}"
        if detail and not passed:
            line += f"（{detail}）"
        print(line)


def read(path: Path):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def run_reader(root: Path, target: Path):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [sys.executable, str(root / "scripts" / "verify_explanation.py"), str(target), "--reader"]
    proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True,
                          encoding="utf-8", env=env)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def run_mutation(root: Path, mutate):
    src = root / "evals" / "fixtures" / "reader-layout"
    if not src.is_dir():
        return 1, "缺少夹具目录：{}".format(src)
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "fixture"
        shutil.copytree(src, dst)
        mutate(dst)
        return run_reader(root, dst)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="读者版可读性行为测试（只读）")
    parser.add_argument("--skill-root", default=None)
    args = parser.parse_args(argv)
    root = (Path(args.skill_root).resolve() if args.skill_root
            else Path(__file__).resolve().parent.parent)
    c = Checker()

    # 1. 合格样板：--reader 通过且无 W-READER
    for label, rel in (("读者版样板", SAMPLE_REL), ("程序型样板", PROCEDURE_REL),
                       ("设计型样板", DESIGN_REL)):
        rc, out = run_reader(root, root / rel)
        c.check("1.x " + label + "通过 --reader", rc == 0 and "W-READER" not in out, (rc, out[-300:]))

    l3 = root / "evals" / "fixtures" / "handout-l1-l3" / "L3-机会成本-检索版要点卡.md"
    rc, out = run_reader(root, l3)
    c.check("1.y L3 检索卡无 W-READER", rc == 0 and "W-READER" not in out, (rc, out[-300:]))

    l1 = root / "evals" / "fixtures" / "handout-l1-l3" / "L1-机会成本.md"
    rc, out = run_reader(root, l1)
    codes = set(re.findall(r"W-READER-[A-Z]+", out))
    c.check("1.z L1 短节仅提示可省速览", rc == 0 and codes == {"W-READER-OVERVIEW"}, (rc, out[-300:]))

    # 2. mutation：每个回退都必须被 --reader 抓到
    def mut_remove_overview(d):
        p = d / Path(SAMPLE_REL).name
        p.write_text(read(p).replace("## 本节速览", "## 本节概览"), encoding="utf-8")

    def mut_remove_conclusion(d):
        p = d / Path(SAMPLE_REL).name
        p.write_text(read(p).replace("- 一句话结论：", "- 结论："), encoding="utf-8")

    def mut_wide_table(d):
        p = d / Path(SAMPLE_REL).name
        p.write_text(read(p).replace(
            "| 要解决的问题 | 一句话结论 | 用在哪 |\n|---|---|---|",
            "| 要解决的问题 | 一句话结论 | 用在哪 | 备注 | 来源 |\n|---|---|---|---|---|"),
            encoding="utf-8")

    def mut_empty_alt(d):
        p = d / Path(SAMPLE_REL).name
        p.write_text(read(p).replace(
            "![机会成本判定流程示意：先删不可行项，再按净收益排序取次优，最后排除沉没成本]",
            "![]"), encoding="utf-8")

    def mut_heading_skip(d):
        p = d / Path(SAMPLE_REL).name
        p.write_text(read(p).replace(
            "## 概念 1 · 机会成本【本节最小必需】",
            "#### 概念 1 · 机会成本【本节最小必需】"), encoding="utf-8")

    def mut_svg_viewbox(d):
        p = d / "assets" / Path(SVG_REL).name
        p.write_text(read(p).replace(' viewBox="0 0 640 240"', ""), encoding="utf-8")

    def mut_bad_encoding(d):
        p = d / Path(SAMPLE_REL).name
        p.write_bytes(b"\xff\xfe\xfa")

    mutations = (
        ("本节速览被删", mut_remove_overview, "W-READER-OVERVIEW"),
        ("一句话结论被删", mut_remove_conclusion, "W-READER-CONCLUSION"),
        ("表格变成 5 列", mut_wide_table, "W-READER-TABLE"),
        ("图片 alt 变空", mut_empty_alt, "W-READER-ALT"),
        ("标题跳级", mut_heading_skip, "W-READER-HEADING"),
        ("SVG 缺 viewBox", mut_svg_viewbox, "W-READER-SVG"),
    )
    for name, fn, code in mutations:
        rc, out = run_mutation(root, fn)
        c.check("2.x --reader 抓到：" + name, code in out, (rc, out[-300:]))

    rc, out = run_mutation(root, mut_bad_encoding)
    c.check("2.y 非法 UTF-8 结构化失败", rc == 1 and "E-READ-FILE" in out, (rc, out[-300:]))

    total = c.ok + c.fail
    print(f"verify-readability: {total} checks, {c.ok} OK, {c.fail} FAIL")
    return 1 if c.fail else 0


if __name__ == "__main__":
    sys.exit(main())
