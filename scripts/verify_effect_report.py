#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""效果报告机检（W-EFFECT-*；stdlib-only、只读、零网络、幂等）。

判据（第一性）：效果报告是**评审证据**，不是学员证据。progress_check.py 只枚举
exercises/，从不读 materials/——报告写得再诚实也没有消费者。本脚本就是那条消费
通道，只验**完整性 + 指针闭合**，不重算得分率（在脚本里重算等于同一批数据两套
算法，改一处两处打架）。

四条判据（票 73 拍板，票 64 定「只告警不拦停」）：
  1. 四个 ## 小节硬必填：结课绝对水平 / 延迟保持 / 元认知校准 / 证据指针。
     段落硬必填、值可为「未测」——结课当天报告即「完整」，第 30 天只回填该段。
     机检验「有没有这一栏」，不验「做没做」；把两者混进一个判据会得出「没做第
     30 天测量 = 报告不完整」这种把诚实判成违规的结论。
  2. 每段一行三态判定，判定词钉死两串：判定：已测 / 判定：未测（理由：…）；
     理由禁占位词（无 / 略 / 待补 / 同上）。
  3. 指针按段定粒度：结课绝对水平 → exercises/99-… 存在且含「目标线：」行；
     延迟保持 → exercises/88-… 存在且**不含** lesson_id=（写了会顶掉节验收证据，
     整节报 E-ALL-FAILED + E-GATE-THRESHOLD + E-NO-RESTATEMENT）；元认知校准 →
     指到「信心=」行或 progress.md。一律不验内容一致性。
  4. 报告不存在 = 打印「跳过」且 rc=0，**不得打印「通过」**——没查 ≠ 查过没问题
     （票 66 语义）。

只告警不拦停：W- 不进任何 ok，脚本恒 rc=0（用法/路径错误除外）。

用法：python -B scripts/verify_effect_report.py <任务目录> [--selftest]
退出码：0 已校验（可有 W）或报告不存在（跳过）；2 用法/路径错误。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

MATERIALS = "materials"
REPORT_GLOB = "效果报告-*.md"

# 四个硬必填小节（票 73 Q1）。名字写死：机检没法验一个没写死的清单。
REQUIRED_SECTIONS = ("结课绝对水平", "延迟保持", "元认知校准", "证据指针")

HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")
# 标题归一化：去尾随全角/半角冒号与括注。本仓其它判据普遍容忍括注（TARGET_RE、
# doc 指针的去编号前缀），标题精确相等会把「## 结课绝对水平（2026-11-20）」这种
# 正常写法判成缺段——那是假阳性，不是判据强度。
TRAILING_PAREN_RE = re.compile(r"\s*[（(][^（）()]*[）)]\s*$")
TRAILING_PUNCT_RE = re.compile(r"[\s：:]+$")
VERDICT_RE = re.compile(r"^\s*(?:[-*]\s*)?判定\s*[：:]\s*(.*?)\s*$")
MEASURED = "已测"
UNMEASURED_RE = re.compile(r"^未测\s*[（(]\s*理由\s*[：:]\s*(.*?)\s*[）)]\s*$")
PLACEHOLDER_REASONS = ("", "无", "略", "待补", "同上", "—", "-", "－")

# 指针：只认 exercises/ 与 materials/ 下的 .md，中文文件名要能吃掉。
POINTER_RE = re.compile(r"((?:exercises|materials)/[^\s\u300c\u300d\u300e\u300f（）()、，。；：|]+?\.md)")
PROGRESS_PTR_RE = re.compile(r"progress\.md")
CONFIDENCE_RE = re.compile(r"信心\s*=")
TARGET_LINE_RE = re.compile(r"目标线\s*[：:]")
LESSON_ID_RE = re.compile(r"lesson_id\s*=")

# 报告不写「键=值」（票 73 ⑤）：字段行形态会撞 META_KEYS 白名单。只认
# 「行首列表项 + 键=」的字段行形态；行文里提到「信心=」不算字段。
META_FIELD_RE = re.compile(
    r"^\s*[-*]\s*(?:S|D|last|due|信心|evt|attempt_id|子类|错因|级|顺延)\s*=")


def read_text(path: Path):
    """读文件；失败返回 None（不把读取失败伪装成通过）。"""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def find_report(task_dir: Path):
    """返回 (报告路径或 None, 全部命中列表)。"""
    mat = task_dir / MATERIALS
    if not mat.is_dir():
        return None, []
    hits = sorted(p for p in mat.glob(REPORT_GLOB) if p.is_file())
    if not hits:
        return None, []
    return hits[0], hits


def normalize_heading(name: str) -> str:
    """标题归一化：去尾随冒号与括注（可叠多层，最多 3 轮）。"""
    s = (name or "").strip()
    for _ in range(3):
        prev = s
        s = TRAILING_PAREN_RE.sub("", s)
        s = TRAILING_PUNCT_RE.sub("", s)
        if s == prev:
            break
    return s


def split_sections(text: str) -> dict:
    """按 ## 切段，返回 {归一化段名: [(行号, 行)]}。同名（归一化后）并进同一键。"""
    sections: dict = {}
    current = None
    for lineno, line in enumerate(text.splitlines(), 1):
        m = HEADING_RE.match(line)
        if m:
            current = normalize_heading(m.group(1))
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append((lineno, line))
    return sections


def parse_verdict(lines):
    """解析段内判定行，返回 (行号, 状态, 理由)；状态 ∈ 已测/未测/非法/None。"""
    for lineno, line in lines:
        m = VERDICT_RE.match(line)
        if not m:
            continue
        raw = m.group(1).strip()
        if raw == MEASURED:
            return lineno, "已测", ""
        um = UNMEASURED_RE.match(raw)
        if um:
            return lineno, "未测", um.group(1).strip()
        return lineno, "非法", raw
    return None, None, None


def collect_pointers(sections: dict):
    """收集全报告的指针，返回 [(行号, 相对路径)]。"""
    out = []
    for _name, lines in sections.items():
        for lineno, line in lines:
            for m in POINTER_RE.finditer(line):
                out.append((lineno, m.group(1)))
    return out


def _add(findings, code, where, message):
    item = {"code": code, "where": where, "message": message}
    if item not in findings:
        findings.append(item)


def check_report(task_dir: Path, report: Path):
    """返回 findings（只含 W- 级）。报告不可读时按 W-EFFECT-MARKER 报。"""
    findings: list = []
    text = read_text(report)
    if text is None:
        _add(findings, "W-EFFECT-MARKER", report.name, "效果报告不可读，无法校验")
        return findings

    sections = split_sections(text)
    name = report.name

    # 判据 1+2：四段必填 + 每段一行三态判定
    verdicts = {}
    for sec in REQUIRED_SECTIONS:
        if sec not in sections:
            _add(findings, "W-EFFECT-MARKER", name, "缺必填小节：## " + sec)
            continue
        lineno, state, reason = parse_verdict(sections[sec])
        verdicts[sec] = state
        if state is None:
            _add(findings, "W-EFFECT-MARKER", name,
                 "「%s」缺判定行（须写「判定：已测」或「判定：未测（理由：…）」）" % sec)
            continue
        if state == "非法":
            _add(findings, "W-EFFECT-MARKER", "%s:%d" % (name, lineno),
                 "「%s」判定行不合体例（只认「判定：已测」与「判定：未测（理由：…）」）：%s"
                 % (sec, reason))
            continue
        if state == "未测" and reason in PLACEHOLDER_REASONS:
            _add(findings, "W-EFFECT-MARKER", "%s:%d" % (name, lineno),
                 "「%s」未测理由为空或占位词（禁：无 / 略 / 待补 / 同上）" % sec)

    # 报告不得写「键=值」字段行
    for lineno, line in enumerate(text.splitlines(), 1):
        if META_FIELD_RE.match(line):
            _add(findings, "W-EFFECT-MARKER", "%s:%d" % (name, lineno),
                 "效果报告不得写「键=值」字段行（撞 META_KEYS 白名单）：" + line.strip()[:40])

    pointers = collect_pointers(sections)

    # 判据 3：按段定粒度的指针闭合
    if verdicts.get("结课绝对水平") == "已测":
        cand = [p for _l, p in pointers if Path(p).name.startswith("99-")]
        if not cand:
            _add(findings, "W-EFFECT-LEVEL", name,
                 "「结课绝对水平」判定为已测，但报告未给出 exercises/99- 结课综合测验指针")
        for p in cand:
            fp = task_dir / p
            if not fp.is_file():
                _add(findings, "W-EFFECT-LEVEL", name, "结课卷不存在：" + p)
                continue
            body = read_text(fp)
            if body is None:
                _add(findings, "W-EFFECT-LEVEL", name, "结课卷不可读：" + p)
            elif not TARGET_LINE_RE.search(body):
                _add(findings, "W-EFFECT-LEVEL", name,
                     "结课卷缺「目标线：」行（达标线机器可读入口）：" + p)

    if verdicts.get("延迟保持") == "已测":
        cand = [p for _l, p in pointers if Path(p).name.startswith("88-")]
        if not cand:
            _add(findings, "W-EFFECT-RETENTION", name,
                 "「延迟保持」判定为已测，但报告未给出 exercises/88- 延迟测量指针")
        for p in cand:
            fp = task_dir / p
            if not fp.is_file():
                _add(findings, "W-EFFECT-RETENTION", name, "延迟测量文件不存在：" + p)
                continue
            body = read_text(fp)
            if body is None:
                _add(findings, "W-EFFECT-RETENTION", name, "延迟测量文件不可读：" + p)
            elif LESSON_ID_RE.search(body):
                _add(findings, "W-EFFECT-RETENTION", name,
                     "延迟测量文件写了 lesson_id=（会顶掉节验收证据）：" + p)

    if verdicts.get("元认知校准") == "已测":
        # 两条都按全文找，不按段：与文档写明的「已知宽口」一致（指针按全文找）。
        # 「见 progress.md」这种裸写必须算——它是最自然的写法，判成缺失是假阳性。
        has_conf = CONFIDENCE_RE.search(text) is not None
        has_progress = PROGRESS_PTR_RE.search(text) is not None
        if not (has_conf or has_progress):
            _add(findings, "W-EFFECT-CALIBRATION", name,
                 "「元认知校准」判定为已测，但既未指到「信心=」行也未指到 progress.md")

    # 证据指针段：列出来的每个指针都必须真的存在
    for lineno, p in pointers:
        if not (task_dir / p).is_file():
            _add(findings, "W-EFFECT-POINTER", "%s:%d" % (name, lineno),
                 "证据指针指向的文件不存在：" + p)

    return findings


def _selftest() -> int:
    ok = True

    def chk(name, cond, detail=""):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name + ("" if cond or not detail else " :: " + detail))
        ok = ok and cond

    CLEAN = (
        "# 效果报告：测试课程\n"
        "\n"
        "## 结课绝对水平\n"
        "- 判定：已测\n"
        "- 得分 8/10。\n"
        "\n"
        "## 延迟保持\n"
        "- 判定：未测（理由：第 30 天尚未到）\n"
        "\n"
        "## 元认知校准\n"
        "- 判定：已测\n"
        "- 见下方指针记录的 信心=4 行。\n"
        "\n"
        "## 证据指针\n"
        "- 判定：已测\n"
        "- exercises/99-结课综合测验-2026-11-20.md\n"
    )
    FINAL_OK = "## 作答与判分\n- 题 1：作答「…」｜正确性=对\n\n目标线：8/10\n"
    RETENTION_88 = "## 延迟测量\n- 题 1：作答「…」｜正确性=对\n"

    def build(report_text, final_text=FINAL_OK, retention_text=RETENTION_88, with_report=True):
        root = Path(tempfile.mkdtemp())
        (root / "materials").mkdir(parents=True, exist_ok=True)
        (root / "exercises").mkdir(parents=True, exist_ok=True)
        (root / "exercises" / "99-结课综合测验-2026-11-20.md").write_text(final_text, encoding="utf-8")
        (root / "exercises" / "88-延迟测量-2026-12-20.md").write_text(retention_text, encoding="utf-8")
        if with_report:
            (root / "materials" / "效果报告-测试课程.md").write_text(report_text, encoding="utf-8")
        return root

    def codes(root):
        rep, _hits = find_report(root)
        if rep is None:
            return None
        return [f["code"] for f in check_report(root, rep)]

    def messages(root):
        rep, _hits = find_report(root)
        if rep is None:
            return []
        return [f["message"] for f in check_report(root, rep)]

    # 0 正例：四段齐、判定合法、指针闭合 → 零告警
    c0 = codes(build(CLEAN))
    chk("正例：合规报告零告警", c0 == [], str(c0))

    # 0b 标题带日期括注 / 全角冒号：本仓其它判据都容忍，这里也必须容忍（假阳性收口）
    c0b = codes(build(CLEAN.replace("## 结课绝对水平\n", "## 结课绝对水平（2026-11-20）\n")))
    chk("标题带括注不判缺段", c0b == [], str(c0b))
    c0c = codes(build(CLEAN.replace("## 结课绝对水平\n", "## 结课绝对水平：\n")))
    chk("标题带全角冒号不判缺段", c0c == [], str(c0c))
    chk("normalize_heading 去括注+冒号",
        normalize_heading("结课绝对水平（2026-11-20）：") == "结课绝对水平")

    # 1 缺段
    c1 = codes(build(CLEAN.replace("## 元认知校准\n- 判定：已测\n- 见下方指针记录的 信心=4 行。\n\n", "")))
    chk("缺段 → W-EFFECT-MARKER", c1 is not None and "W-EFFECT-MARKER" in c1, str(c1))

    # 2 判定行理由为空
    c2 = codes(build(CLEAN.replace("（理由：第 30 天尚未到）", "（理由：）")))
    chk("未测理由为空 → W-EFFECT-MARKER", c2 is not None and "W-EFFECT-MARKER" in c2, str(c2))

    # 3 99- 卷缺「目标线：」
    c3 = codes(build(CLEAN, final_text="## 作答与判分\n- 题 1：作答「…」｜正确性=对\n"))
    chk("99- 卷缺目标线 → W-EFFECT-LEVEL", c3 is not None and "W-EFFECT-LEVEL" in c3, str(c3))

    # 4 88- 文件写了 lesson_id=
    # 必须同时给出真的 88- 指针，否则本用例命中的是「缺指针」分支而不是 lesson_id 分支——
    # 那正是本仓反复吃亏的假绿：断言绿了，被测的那条判据一次都没跑（变异测试 M2 抓出）。
    CLEAN_RET = (CLEAN
                 .replace("- 判定：未测（理由：第 30 天尚未到）", "- 判定：已测\n- 见下方 88- 指针。")
                 .replace("- exercises/99-结课综合测验-2026-11-20.md\n",
                          "- exercises/99-结课综合测验-2026-11-20.md\n"
                          "- exercises/88-延迟测量-2026-12-20.md\n"))
    r4 = build(CLEAN_RET,
               retention_text="## 延迟测量\n- 题 1：作答「…」｜正确性=对｜lesson_id=L-03\n")
    c4 = codes(r4)
    m4 = messages(r4)
    chk("88- 写 lesson_id= → W-EFFECT-RETENTION",
        c4 is not None and "W-EFFECT-RETENTION" in c4, str(c4))
    chk("88- 用例命中的是 lesson_id 分支（不是缺指针分支）",
        any("lesson_id=" in m for m in m4)
        and not any("未给出 exercises/88-" in m for m in m4), str(m4))

    # 4b 元认知段裸写 progress.md（不带路径）也必须算指到
    r4b = build(CLEAN.replace("- 见下方指针记录的 信心=4 行。", "- 见 progress.md 的记录。"))
    c4b = codes(r4b)
    chk("裸写 progress.md 也算指到（不报 W-EFFECT-CALIBRATION）",
        c4b == [], str(c4b))

    # 5 报告不存在 → 找不到报告（调用方打印「跳过」且 rc=0）
    rep5, _h = find_report(build(CLEAN, with_report=False))
    chk("报告不存在 → 找不到报告（调用方打印跳过）", rep5 is None)

    # 6 指针悬空 → W-EFFECT-POINTER
    c6 = codes(build(CLEAN.replace("exercises/99-结课综合测验-2026-11-20.md",
                                   "exercises/99-结课综合测验-2026-01-01.md")))
    chk("指针悬空 → W-EFFECT-POINTER", c6 is not None and "W-EFFECT-POINTER" in c6, str(c6))

    # 7 报告写「键=值」字段行 → W-EFFECT-MARKER
    c7 = codes(build(CLEAN.replace("- 得分 8/10。", "- 信心=4")))
    chk("写「键=值」字段行 → W-EFFECT-MARKER", c7 is not None and "W-EFFECT-MARKER" in c7, str(c7))

    print("SELFTEST OK" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="效果报告机检（W-EFFECT-*，只告警不拦停）")
    ap.add_argument("task_dir", nargs="?", help="任务目录（<数据根>/<slug>）")
    ap.add_argument("--selftest", action="store_true",
                    help="运行内嵌样例自检（临时目录，不写盘被校验目录）")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    if not args.task_dir:
        ap.print_usage()
        return 2
    task_dir = Path(args.task_dir)
    if not task_dir.is_dir():
        print("[learn-task-workflow] 任务目录不存在或不可访问：" + str(task_dir),
              file=sys.stderr)
        return 2

    report, hits = find_report(task_dir)
    if report is None:
        # 「跳过」与「通过」必须分开打印：没查 ≠ 查过没问题（票 66 语义）。
        print("已跳过：未找到效果报告（%s/%s），未校验" % (MATERIALS, REPORT_GLOB),
              file=sys.stderr)
        print(json.dumps({"ok": True, "checked": False, "skipped": True,
                          "warnings": []}, ensure_ascii=False))
        return 0

    if len(hits) > 1:
        print("[learn-task-workflow] 命中 %d 份效果报告，只校验 %s"
              % (len(hits), report.name), file=sys.stderr)

    findings = check_report(task_dir, report)
    for f in findings:
        print("[W] %s %s %s" % (f["code"], f["where"], f["message"]))
    if findings:
        print("共 %d 项：E 0 项，W %d 项（只告警不拦停）" % (len(findings), len(findings)))
    else:
        print("通过：无违规项（只校验完整性与指针闭合；得分率与内容一致性不校验）")
    print(json.dumps({"ok": True, "checked": True, "skipped": False,
                      "report": report.name,
                      "warnings": [{"code": f["code"], "where": f["where"],
                                    "message": f["message"]} for f in findings]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
