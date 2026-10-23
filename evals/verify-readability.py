#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-readability.py - v6.7.3 读者版可读性/图表契约（stdlib-only、只读）。

检查三件事：
1. `lecture-styles.md` / `handout-design.md` / `methodology.md` / `SKILL.md`
   是否写入「读者路径、段落/标题/版式、图解语法、证据边界」规则；
2. `evals/fixtures/reader-layout/` 的读者版样板是否满足可静态判定的版面条款，
   并确认 `verify_explanation.py --reader` 在样板与典型回退上按预期工作；
3. mutation：删掉关键规则/结构后，检查器必须报错。

语义执行（是否真的更易读、图是否讲对）仍由模型/人工评审负责；本脚本只证明
「规则在场 + 样板结构合格」，不能替代真人冷读与延迟迁移验证。
"""

import argparse
import json
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
GENERIC_ALT = {"图", "图片", "示意图", "图像", "figure", "image", "diagram"}


class Checker:
    def __init__(self):
        self.ok = 0
        self.fail = 0

    def check(self, name, cond, detail=""):
        if cond:
            self.ok += 1
            print("[OK] " + name)
        else:
            self.fail += 1
            print("[FAIL] " + name + (("：" + str(detail)) if detail else ""))


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def table_groups(lines):
    groups = []
    buf = []
    for line in lines:
        if line.strip().startswith("|"):
            buf.append(line.rstrip())
        elif buf:
            groups.append(buf)
            buf = []
    if buf:
        groups.append(buf)
    return groups


def split_row(row):
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    return cells


def is_separator(row):
    cells = split_row(row)
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c or "") for c in cells)


def table_problems(text):
    problems = []
    lines = text.splitlines()
    for group in table_groups(lines):
        if len(group) < 2 or not is_separator(group[1]):
            problems.append("表格缺表头分隔行")
            continue
        cols = len(split_row(group[0]))
        if cols < 2 or cols > 4:
            problems.append("表格列数 {}（应为 2–4 列）".format(cols))
        if any(not c for c in split_row(group[0])):
            problems.append("表格表头存在空列名")
    return problems


def svg_problems(path):
    problems = []
    text = read(path)
    if not text:
        return ["SVG 读取失败"]
    root_tag = re.search(r"<svg\b[^>]*>", text, re.I)
    if not root_tag or "viewBox=" not in root_tag.group(0):
        problems.append("SVG 根元素缺 viewBox")
    if not root_tag or not re.search(r"role\s*=\s*[\"']img[\"']", root_tag.group(0)):
        problems.append("SVG 根元素缺 role=\"img\"")
    if "<title" not in text:
        problems.append("SVG 缺 <title>")
    if "<desc" not in text:
        problems.append("SVG 缺 <desc>")
    if "<script" in text.lower():
        problems.append("SVG 含 script")
    if re.search(r"(?:href|xlink:href)\s*=\s*[\"']https?://", text, re.I):
        problems.append("SVG 含外部引用")
    for raw in re.findall(r"font-size\s*=\s*[\"']([0-9.]+)", text):
        if float(raw) < 14:
            problems.append("SVG 字号 {} < 14".format(raw))
    for raw in re.findall(r"stroke-width\s*=\s*[\"']([0-9.]+)", text):
        if float(raw) < 1.5:
            problems.append("SVG 线宽 {} < 1.5".format(raw))
    return problems


def layout_problems(text, base_dir):
    problems = []
    lines = text.splitlines()

    # 1. 节首导读三行
    head = text.split("\n## ", 1)[0]
    for key in ("本节目标", "前置", "预计"):
        if key not in head:
            problems.append("头部缺「{}」".format(key))

    # 2. 标题层级不跳级
    prev = 0
    for line in lines:
        m = re.match(r"^(#{1,6})\s+", line)
        if not m:
            continue
        level = len(m.group(1))
        if prev and level > prev + 1:
            problems.append("标题层级跳级 H{}→H{}".format(prev, level))
        prev = level

    # 3. 本节速览：3 列、1–3 行数据
    if "## 本节速览" not in text:
        problems.append("缺 ## 本节速览")
    else:
        start = lines.index("## 本节速览")
        first_unit = next((i for i, l in enumerate(lines) if re.match(r"^##\s*概念\s*\d+", l)),
                          len(lines))
        if start > first_unit:
            problems.append("本节速览应在第一个概念单元之前")
        group = []
        for line in lines[start + 1:]:
            if line.startswith("## "):
                break
            if line.strip().startswith("|"):
                group.append(line.rstrip())
            elif group:
                break
        if len(group) < 2:
            problems.append("本节速览表缺失或不完整")
        else:
            cols = len(split_row(group[0]))
            if cols != 3:
                problems.append("本节速览应为 3 列，实际 {}".format(cols))
            data_rows = len(group) - 2
            if not 1 <= data_rows <= 3:
                problems.append("本节速览数据行 {}（应为 1–3）".format(data_rows))

    # 4. 回看索引：存在 + 三行关键词 + 位于答案区之后
    if "## 回看索引" not in text:
        problems.append("缺 ## 回看索引")
    else:
        idx = lines.index("## 回看索引")
        tail = "\n".join(lines[idx:])
        for key in ("核心一句话", "最容易错", "下一步"):
            if key not in tail:
                problems.append("回看索引缺「{}」".format(key))
        ans_idx = max((i for i, l in enumerate(lines)
                        if l.startswith("## ") and "答案" in l), default=-1)
        if ans_idx >= 0 and idx <= ans_idx:
            problems.append("回看索引应在答案区之后")
        for later in ("## 待解决问题", "## 扩展（选读）"):
            if later in text and text.index(later) < text.index("## 回看索引"):
                problems.append("回看索引应在{}之前".format(later))

    # 5. 概念单元首行一句话结论
    concept_starts = [i for i, l in enumerate(lines) if re.match(r"^##\s*概念\s*\d+", l)]
    if not concept_starts:
        problems.append("未找到 ## 概念 N 单元")
    for start in concept_starts:
        body = [l.strip() for l in lines[start + 1:] if l.strip()]
        if not body or not re.match(r"^(?:-\s*)?一句话结论[：:]", body[0]):
            problems.append("概念单元首行缺「一句话结论：」")

    # 6. 连续两段不都用加粗抢重点（术语密集段可例外）
    prev_emphasis = False
    for line in lines:
        if not line.strip() or line.lstrip().startswith(("#", "|", ">", "```")):
            prev_emphasis = False
            continue
        count = len(re.findall(r"\*\*[^*]+\*\*", line))
        if count >= 2 and prev_emphasis:
            problems.append("连续两段都用了加粗抢重点")
        prev_emphasis = count >= 2

    # 7. 表格结构
    problems.extend(table_problems(text))

    # 8. 图片 alt / 路径 / SVG 技术项
    for alt, target in re.findall(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", text):
        if not alt.strip() or alt.strip().lower() in GENERIC_ALT:
            problems.append("图片 alt 为空或过于笼统")
        if re.match(r"^[a-z]+:", target, re.I):
            continue
        path = (Path(base_dir) / target).resolve()
        if not path.exists():
            problems.append("图片路径不存在：{}".format(target))
        elif path.suffix.lower() == ".svg":
            problems.extend(svg_problems(path))

    # 9. 扩展区必须是最后一个 ## 区
    if "## 扩展（选读）" in text:
        pos = text.index("## 扩展（选读）")
        if re.search(r"^##\s+", text[pos + len("## 扩展（选读）"):], re.M):
            problems.append("扩展（选读）之后仍有 ## 区")
    return problems


def doc_problems(skill, lecture, handout, methodology, evals_text, deps_text=""):
    problems = []
    checks = (
        ("lecture 读者版契约", lecture, "## 读者版可读性契约（所有风格共用）"),
        ("lecture 默认不变量", lecture, "默认不变量（所有新讲义，不因 P1 豁免）"),
        ("lecture 支持级变体", lecture, "支持级与类型变体"),
        ("lecture 读者验证四问", lecture, "读者验证四问（人工，定稿前）"),
        ("lecture 三遍路径", lecture, "### 1. 三遍路径"),
        ("lecture 一段一义", lecture, "### 2. 一段一义，先结论后展开"),
        ("lecture 标题强调", lecture, "### 3. 标题、强调与留白"),
        ("lecture 图解语法", lecture, "### 4. 图解语法"),
        ("lecture 5 问自检", lecture, "### 5. 可读性自检（5 问，定稿前）"),
        ("lecture 30 秒", lecture, "30 秒扫读"),
        ("lecture 10 分钟", lecture, "10 分钟精读"),
        ("lecture 2 分钟", lecture, "2 分钟回看"),
        ("lecture 一段一义关键词", lecture, "一段一义"),
        ("lecture 强调配额", lecture, "连续两段不要都用加粗"),
        ("lecture 一句一判断", lecture, "一句一判断"),
        ("lecture 无障碍语义", lecture, "### 6. 无障碍语义（默认不变量）"),
        ("lecture 链接文字", lecture, "链接文字"),
        ("lecture viewBox", lecture, "viewBox"),
        ("lecture role=img", lecture, 'role="img"'),
        ("lecture title", lecture, "<title>"),
        ("lecture desc", lecture, "<desc>"),
        ("lecture 对比 4.5:1", lecture, "4.5:1"),
        ("lecture 对比 3:1", lecture, "3:1"),
        ("lecture 节点预算", lecture, "≤7±2"),
        ("lecture 行长下限", lecture, "25–40"),
        ("lecture 行长上限", lecture, "48"),
        ("handout 10.10", handout, "### 10.10 读者路径与三层速览"),
        ("handout 10.11", handout, "### 10.11 图表系统与视觉一致性"),
        ("handout 默认不变量", handout, "默认不变量（标题导航/段落/图解语法）"),
        ("handout 强调配额", handout, "连续两段不都用加粗抢重点"),
        ("handout 读者验证四问结果", handout, "读者验证四问结果"),
        ("handout 字号下限", handout, "max(14px, 0.8×正文主题字号)"),
        ("handout 本节速览", handout, "## 本节速览"),
        ("handout 回看索引", handout, "## 回看索引"),
        ("handout 本章速览", handout, "## 本章速览"),
        ("handout 本章回看", handout, "## 本章回看"),
        ("handout 黑白窄屏", handout, "黑白/窄屏"),
        ("handout coherence", handout, "coherence"),
        ("methodology 读者版", methodology, "读者版可读性"),
        ("methodology Mayer", methodology, "Mayer 2017"),
        ("methodology Noetel", methodology, "Noetel et al. 2021"),
        ("methodology Cromley", methodology, "Cromley & Chen 2025"),
        ("methodology clreq", methodology, "W3C clreq"),
        ("methodology WCAG", methodology, "WCAG 2.1"),
        ("methodology Delgado", methodology, "Delgado et al. 2018"),
        ("methodology Bisra", methodology, "Bisra et al. 2018"),
        ("methodology 行长冲突", methodology, "76 字/行"),
        ("methodology 保守区间", methodology, "25–40"),
        ("SKILL 读者版", skill, "读者版可读性"),
        ("SKILL 图解语法", skill, "图解语法"),
        ("SKILL 图表系统", skill, "图表系统"),
        ("SKILL 读者路径", skill, "读者路径与三层速览"),
        ("SKILL --reader", skill, "--reader"),
        ("deps --reader", deps_text, "--reader"),
    )
    for label, text, phrase in checks:
        if phrase not in text:
            problems.append(label)
    try:
        data = json.loads(evals_text)
    except (TypeError, ValueError):
        data = {}
    ids = {c.get("id") for c in data.get("cases", []) if isinstance(c, dict)}
    for cid in ("E129", "E130", "E131", "E132", "E133", "E134"):
        if cid not in ids:
            problems.append("evals 缺 " + cid)
    if "verify-readability.py" not in str(data.get("machine_evidence_ref", "")):
        problems.append("evals machine_evidence_ref 未登记 verify-readability.py")
    return problems


def run_verify_explanation(root, fixture_dir, reader=False):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [sys.executable, str(root / "scripts" / "verify_explanation.py"), str(fixture_dir)]
    if reader:
        cmd.append("--reader")
    proc = subprocess.run(
        cmd, cwd=str(root), capture_output=True, text=True, encoding="utf-8", env=env,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def mutate_fixture(root, mutate):
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "fixture"
        shutil.copytree(root / "evals" / "fixtures" / "reader-layout", dst)
        mutate(dst)
        sample = dst / Path(SAMPLE_REL).name
        probs = layout_problems(read(sample), dst)
        return probs


def reader_output_for_mutation(root, mutate):
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "fixture"
        shutil.copytree(root / "evals" / "fixtures" / "reader-layout", dst)
        mutate(dst)
        return run_verify_explanation(root, dst, reader=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="v6.7.3 读者版可读性/图表契约（只读）")
    parser.add_argument("--skill-root", default=None)
    args = parser.parse_args(argv)
    root = (Path(args.skill_root).resolve() if args.skill_root
            else Path(__file__).resolve().parent.parent)

    skill = read(root / "SKILL.md")
    lecture = read(root / "references" / "lecture-styles.md")
    handout = read(root / "references" / "handout-design.md")
    methodology = read(root / "references" / "methodology.md")
    deps_text = read(root / "skill-dependencies.json")
    evals_text = read(root / "evals" / "evals.json")

    c = Checker()
    doc = doc_problems(skill, lecture, handout, methodology, evals_text, deps_text)
    c.check("1.1 文档契约齐全", not doc, doc)

    sample_path = root / SAMPLE_REL
    sample_text = read(sample_path)
    layout = layout_problems(sample_text, sample_path.parent)
    c.check("2.1 读者版样板版面合格", not layout, layout)

    rc, out = run_verify_explanation(root, sample_path.parent)
    c.check("2.2 样板通过 verify_explanation.py", rc == 0 and "通过" in out, (rc, out[-300:]))
    rc_r, out_r = run_verify_explanation(root, sample_path.parent, reader=True)
    c.check("2.3 样板通过 --reader 检查", rc_r == 0 and "W-READER" not in out_r,
            (rc_r, out_r[-300:]))
    l1 = root / "evals" / "fixtures" / "handout-l1-l3" / "L1-机会成本.md"
    rc_l1, out_l1 = run_verify_explanation(root, l1, reader=True)
    c.check("2.4 L1 短节样板无 W-READER", rc_l1 == 0 and "W-READER" not in out_l1,
            (rc_l1, out_l1[-300:]))
    l3 = root / "evals" / "fixtures" / "handout-l1-l3" / "L3-机会成本-检索版要点卡.md"
    rc_l3, out_l3 = run_verify_explanation(root, l3, reader=True)
    c.check("2.5 L3 检索卡无 W-READER", rc_l3 == 0 and "W-READER" not in out_l3,
            (rc_l3, out_l3[-300:]))

    for label, rel in (("程序型样板", PROCEDURE_REL), ("设计型样板", DESIGN_REL)):
        p = root / rel
        probs = layout_problems(read(p), p.parent)
        c.check("2.x " + label + "版面合格", not probs, probs)
        rc_t, out_t = run_verify_explanation(root, p, reader=True)
        c.check("2.x " + label + "通过 --reader", rc_t == 0 and "W-READER" not in out_t,
                (rc_t, out_t[-300:]))

    # mutation：每个改动都必须被 layout_problems 抓到
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

    def mut_remove_index(d):
        p = d / Path(SAMPLE_REL).name
        p.write_text(read(p).replace("## 回看索引", "## 回看"), encoding="utf-8")

    def mut_svg_viewbox(d):
        p = d / "assets" / Path(SVG_REL).name
        p.write_text(read(p).replace(' viewBox="0 0 640 240"', ""), encoding="utf-8")

    mutations = (
        ("本节速览被删", mut_remove_overview),
        ("一句话结论被删", mut_remove_conclusion),
        ("表格变成 5 列", mut_wide_table),
        ("图片 alt 变空", mut_empty_alt),
        ("标题跳级", mut_heading_skip),
        ("回看索引被删", mut_remove_index),
        ("SVG 缺 viewBox", mut_svg_viewbox),
    )
    for name, fn in mutations:
        probs = mutate_fixture(root, fn)
        c.check("3.x mutation 能抓到：" + name, bool(probs), probs)

    # --reader 运行时检查必须能抓到两个典型回退
    rc_w, out_w = reader_output_for_mutation(root, mut_wide_table)
    c.check("3.y --reader 能抓到 5 列表格", rc_w == 0 and "W-READER-TABLE" in out_w,
            (rc_w, out_w[-300:]))
    rc_a, out_a = reader_output_for_mutation(root, mut_empty_alt)
    c.check("3.z --reader 能抓到空 alt", rc_a == 0 and "W-READER-ALT" in out_a,
            (rc_a, out_a[-300:]))

    # mutation：删掉文档规则也必须被抓到
    c.check("4.1 删读者版契约被抓到",
            bool(doc_problems(skill, lecture.replace("## 读者版可读性契约（所有风格共用）", ""),
                              handout, methodology, evals_text, deps_text)))
    c.check("4.2 删 10.10 被抓到",
            bool(doc_problems(skill, lecture, handout.replace("### 10.10 读者路径与三层速览", ""),
                              methodology, evals_text, deps_text)))
    c.check("4.3 删 Mayer 证据被抓到",
            bool(doc_problems(skill, lecture, handout, methodology.replace("Mayer 2017", ""),
                              evals_text, deps_text)))

    print("verify-readability: {} checks, {} OK, {} FAIL".format(c.ok + c.fail, c.ok, c.fail))
    return 0 if c.fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
