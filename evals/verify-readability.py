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

    def mut_long_line(d):
        p = d / Path(SAMPLE_REL).name
        p.write_text(read(p) + "这" * 260 + "\n", encoding="utf-8")

    def mut_deep_nest(d):
        p = d / Path(SAMPLE_REL).name
        p.write_text(read(p) + "- 甲\n  - 乙\n    - 丙\n      - 丁\n", encoding="utf-8")

    def mut_bad_encoding(d):
        p = d / Path(SAMPLE_REL).name
        p.write_bytes(b"\xff\xfe\xfa")

    def mut_heading_no_body(d):
        p = d / Path(SAMPLE_REL).name
        p.write_text(read(p).replace(
            "- 一句话结论：机会成本是放弃的可行选项中次优选择的价值。",
            "- 甲\n- 乙", 1), encoding="utf-8")

    def mut_missing_caption(d):
        p = d / Path(SAMPLE_REL).name
        p.write_text(read(p).replace(
            "- 图注：机会成本只看可行选项中的次优价值；不可行项和沉没成本先排除（流程示意）。\n",
            ""), encoding="utf-8")

    def mut_generic_link(d):
        p = d / Path(SAMPLE_REL).name
        p.write_text(read(p) + "[点击这里](https://example.com)\n", encoding="utf-8")

    def mut_table_align(d):
        p = d / Path(SAMPLE_REL).name
        p.write_text(read(p) + "| 项 | 数值 |\n|---|---|\n| a | 1 |\n| b | 2 |\n", encoding="utf-8")

    mutations = (
        ("本节速览被删", mut_remove_overview, "W-READER-OVERVIEW"),
        ("一句话结论被删", mut_remove_conclusion, "W-READER-CONCLUSION"),
        ("表格变成 5 列", mut_wide_table, "W-READER-TABLE"),
        ("图片 alt 变空", mut_empty_alt, "W-READER-ALT"),
        ("标题跳级", mut_heading_skip, "W-READER-HEADING"),
        ("SVG 缺 viewBox", mut_svg_viewbox, "W-READER-SVG"),
        ("超长正文行", mut_long_line, "W-READER-LONGLINE"),
        ("列表嵌套 4 层", mut_deep_nest, "W-READER-DEEPNEST"),
        ("标题后无正文", mut_heading_no_body, "W-READER-HEADING-BODY"),
        ("图缺图注", mut_missing_caption, "W-READER-CAPTION"),
        ("泛称链接文字", mut_generic_link, "W-READER-LINKTEXT"),
        ("数值列未右对齐", mut_table_align, "W-READER-TABLE-ALIGN"),
    )
    for name, fn, code in mutations:
        rc, out = run_mutation(root, fn)
        c.check("2.x --reader 抓到：" + name, code in out, (rc, out[-300:]))

    rc, out = run_mutation(root, mut_bad_encoding)
    c.check("2.y 非法 UTF-8 结构化失败", rc == 1 and "E-READ-FILE" in out, (rc, out[-300:]))

    # 3. ltw_typography 直跑闸口（ops/layout.md E/W 级；独立于 --reader）
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    HARD_REL = "evals/fixtures/layout-hard/健康样板.md"

    def run_layout_cli(mutate=None, raw_bytes=None):
        src = root / HARD_REL
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "sample.md"
            if raw_bytes is not None:
                dst.write_bytes(raw_bytes)
            else:
                text = read(src)
                if mutate:
                    text = mutate(text)
                dst.write_text(text, encoding="utf-8")
            cmd = [sys.executable, "-B", str(root / "scripts" / "ltw_typography.py"),
                   str(dst)]
            proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True,
                                  encoding="utf-8", env=env)
            return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    rc, out = run_layout_cli()
    c.check("3.a 健康样板零 E/W", rc == 0 and "LAYOUT" not in out, (rc, out[-300:]))

    rc, out = run_layout_cli(lambda t: t.replace("1. 写出", "1.（题 1）写出"))
    c.check("3.b 抓到：列表标记后无空格",
            rc == 1 and "E-LAYOUT-LIST-SPACE" in out, (rc, out[-300:]))

    rc, out = run_layout_cli(lambda t: t + "台" * 401 + "\n")
    c.check("3.c 抓到：单行超硬上限",
            rc == 1 and "E-LAYOUT-LONGLINE" in out, (rc, out[-300:]))

    rc, out = run_layout_cli(lambda t: t + "残行 ightarrow$ v2.0\n")
    c.check("3.d 抓到：行内 $ 不成对",
            rc == 1 and "E-LAYOUT-MATH-UNPAIRED" in out, (rc, out[-300:]))

    rc, out = run_layout_cli(lambda t: t.replace("### 题 1", "#### 题 1"))
    c.check("3.e 抓到：标题跳级",
            rc == 1 and "E-LAYOUT-HEADING-SKIP" in out, (rc, out[-300:]))

    rc, out = run_layout_cli(lambda t: t + "| a | b | c | d | e |\n|---|---|---|---|---|\n| 1 | 2 | 3 | 4 | 5 |\n")
    c.check("3.f 抓到：表格超宽",
            rc == 1 and "E-LAYOUT-TABLE-WIDE" in out, (rc, out[-300:]))

    rc, out = run_layout_cli(lambda t: t + "---\n" * 4)
    c.check("3.g 抓到：分隔线超量（W 不拦截）",
            rc == 0 and "W-LAYOUT-SEPARATOR" in out, (rc, out[-300:]))

    rc, out = run_layout_cli(lambda t: t + "主语 $\\rightarrow$ 直接宾语\n")
    c.check("3.h 抓到：非公式语境 LaTeX 箭头（W 不拦截）",
            rc == 0 and "W-LAYOUT-LATEX-ARROW" in out, (rc, out[-300:]))

    rc, out = run_layout_cli(raw_bytes="# 题\r\n\r\n正文一句。\n".encode("utf-8"))
    c.check("3.i 抓到：行尾混用（W 不拦截）",
            rc == 0 and "W-LAYOUT-LINE-ENDING" in out, (rc, out[-300:]))

    rc, out = run_layout_cli(lambda t: t + "## 使用注意\n\n" + "注" * 350 + "\n")
    c.check("3.j 抓到：整节零加粗（强调清零）",
            rc == 0 and "W-LAYOUT-EMPHASIS-FLOOR" in out, (rc, out[-300:]))

    rc, out = run_layout_cli(raw_bytes=b"\xff\xfe\xfa")
    c.check("3.k 非法 UTF-8 结构化失败", rc == 1 and "E-READ-FILE" in out, (rc, out[-300:]))

    cmd = [sys.executable, "-B", str(root / "scripts" / "ltw_typography.py"), "--selftest"]
    proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True,
                          encoding="utf-8", env=env)
    c.check("3.l ltw_typography --selftest 通过",
            proc.returncode == 0 and "0 FAIL" in (proc.stdout or ""), (proc.returncode, (proc.stdout or "")[-200:]))

    rc, out = run_layout_cli(lambda t: t + "\n" + "词" * 210 + "，**关键判断**在此。\n\n" + "词" * 210 + "，收束一句。\n")
    c.check("3.m 抓到：连续正文无视觉锚点（W 不拦截）",
            rc == 0 and "W-LAYOUT-ANCHOR-GAP" in out, (rc, out[-300:]))

    total = c.ok + c.fail
    print(f"verify-readability: {total} checks, {c.ok} OK, {c.fail} FAIL")
    return 1 if c.fail else 0


if __name__ == "__main__":
    sys.exit(main())
