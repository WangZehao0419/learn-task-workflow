#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-v64-consistency.py - v6.4 阶段 0 + 理解核心契约（stdlib-only、只读）。

只检查“规则有没有写进对应分册、彼此是否还对得上”：状态行两分、③ 豁免
canonical、交付标识单一表、L3 复习产物例外、单元≠KP、头部/指针、深讲拆节、
类型单元数、命名/附件、概念地图阈值、理解核心六件套、版本与 eval 登记。语义执行仍由模型/评审负责。
"""

import argparse
import json
import re
from pathlib import Path


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


def read(root, rel):
    try:
        return (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def version_tuple(text):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", str(text or ""))
    return tuple(int(x) for x in m.groups()) if m else None


def at_least_v64(text):
    v = version_tuple(text)
    return v is not None and v >= (6, 4, 0)


def style_problems(styles):
    """v6.4 阶段 0 对 lecture-styles 的最小一致性要求。"""
    problems = []
    for phrase, label in (
        ("讲义状态行", "讲义状态行"),
        ("台账状态行", "台账状态行"),
        ("③ 不适用（纯记忆）", "纯记忆豁免"),
        ("③ 不适用（已会·检索版）", "L3 豁免"),
        ("方案：", "设计类交付标识"),
        ("5 个以上概念", "概念地图阈值"),
        ("修复表、决策日志、对照表算附件", "④/⑤ 附件例外"),
        ("单元≠KP", "单元-KP"),
        ("完整深讲", "完整深讲"),
        ("拆节", "深讲拆节"),
        ("检索版要点卡", "L3 产物命名"),
    ):
        if phrase not in styles:
            problems.append(label)
    return problems


CANON_MARKERS = {
    "解", "答", "解答", "证明", "参考答案", "答案", "参考概括", "参考译文",
    "译文", "范文", "例文", "代码", "脚本", "输出", "步骤", "操作", "方案",
    "设计说明", "Model answer", "Sample answer", "Answer", "Solution", "Proof",
    "Translation", "Output", "Code", "Script", "Steps", "Key",
}


def lead_markers(text):
    """从 verify_explanation.py 的 LEAD_WORDS 块提取标识集合。"""
    m = re.search(r"LEAD_WORDS\s*=\s*\((.*?)\)", text or "", re.S)
    if not m:
        return set()
    block = m.group(1).replace('"', "")
    block = re.sub(r"\n\s*", "", block)
    return {token.strip() for token in block.split("|") if token.strip()}


def main(argv=None):
    parser = argparse.ArgumentParser(description="v6.4 阶段 0 + 理解核心契约（只读）")
    parser.add_argument("--skill-root", default=None)
    args = parser.parse_args(argv)
    root = (Path(args.skill_root).resolve() if args.skill_root
            else Path(__file__).resolve().parent.parent)

    skill = read(root, "SKILL.md")
    styles = read(root, "references/lecture-styles.md")
    handout = read(root, "references/handout-design.md")
    phases = read(root, "references/phases-and-gates.md")
    teaching = read(root, "references/teaching-loop.md")
    subjects = read(root, "references/subject-playbooks.md")
    credits = read(root, "CREDITS.md")
    setup = read(root, "references/setup-guide.md")
    deps_raw = read(root, "skill-dependencies.json")
    evals_raw = read(root, "evals/evals.json")
    verify_explanation = read(root, "scripts/verify_explanation.py")
    try:
        deps = json.loads(deps_raw)
    except (TypeError, ValueError):
        deps = {}
    try:
        evals = json.loads(evals_raw)
    except (TypeError, ValueError):
        evals = {}
    if not isinstance(evals, dict):
        evals = {}
    if not isinstance(evals.get("cases"), list):
        evals = dict(evals, cases=[])

    deps_versions = []
    if isinstance(deps, dict):
        if "applies_to_version" in deps:
            deps_versions.append(deps.get("applies_to_version"))
        for dep in deps.get("dependencies", []):
            setup_obj = dep.get("setup") if isinstance(dep, dict) else None
            if isinstance(setup_obj, dict) and "applies_to_version" in setup_obj:
                deps_versions.append(setup_obj.get("applies_to_version"))

    def version_in(text, pattern):
        m = re.search(pattern, text or "")
        return m.group(1) if m else ""

    c = Checker()
    c.check("1.1 SKILL.md 版本 ≥ 6.4.0",
            at_least_v64(version_in(skill, r"version:\s*(\d+\.\d+\.\d+)")))
    c.check("1.2 setup-guide 适用版本 ≥ 6.4.0",
            at_least_v64(version_in(setup, r"适用版本：(\d+\.\d+\.\d+)")))
    c.check("1.3 skill-dependencies 版本 ≥ 6.4.0",
            bool(deps_versions) and all(at_least_v64(v) for v in deps_versions),
            deps_versions)
    c.check("1.4 CREDITS 当前版本说明 ≥ 6.4.0",
            at_least_v64(version_in(credits, r"当前版本说明\*\*：(\d+\.\d+\.\d+)")))
    c.check("1.5 evals 版本 ≥ 6.4.0",
            at_least_v64(evals.get("applies_to_version", "")))

    c.check("2.1 一页合同分册存在且含一页合同",
            "一页合同" in handout)
    c.check("2.2 状态行两分（讲义/台账）",
            all(k in handout for k in ("讲义状态行", "台账状态行", "不是一回事")))
    c.check("2.3 ③ 豁免 canonical 四类",
            all(k in handout for k in ("③ 不适用（纯概念）", "③ 不适用（纯记忆）",
                                       "③ 不适用（已会·检索版）", "③ 不适用（参照级）")))
    c.check("2.4 交付标识单一表含设计/记忆",
            all(k in handout for k in ("方案：", "设计说明：", "答案：", "单一来源")))
    c.check("2.5 L3 复习产物例外",
            all(k in handout for k in ("L3 复习产物例外", "3–5 题", "只约束 **S3 新学**")))
    c.check("2.6 单元≠KP / 多对多",
            all(k in handout for k in ("单元 ≠ KP", "一个单元可映射多个 KP", "不强制 1:1")))
    c.check("2.7 头部合并/指针存在",
            all(k in handout for k in ("3 行", "只在目标区存在时写", "死指针")))
    c.check("2.8 深讲拆节",
            all(k in handout for k in ("完整深讲", "拆节", "机制段 ≠ 深讲")))
    c.check("2.9 类型单元数",
            all(k in handout for k in ("记忆 5–7", "程序 3–5", "设计 1–3")))
    c.check("2.10 命名/附件",
            all(k in handout for k in ("检索版要点卡", "不再另造", "算附件")))
    c.check("2.11 概念地图阈值",
            all(k in handout for k in ("≥5 个概念", "旧「8 个以上」阈值废止")))
    c.check("2.12 理解核心六件套",
            all(k in handout for k in ("理解四证", "设计六问", "四段支架",
                                       "闭卷自检", "二次定稿", "关键能力对齐",
                                       "冷读四证", "先猜", "自解释")))

    c.check("3.1 lecture-styles 与合同一致",
            not style_problems(styles), style_problems(styles))
    c.check("3.2 phases 同步状态行/最细知识点/拆节",
            all(k in phases for k in ("台账状态行", "讲义状态行", "最细知识点",
                                      "节内块数不设上限", "拆节", "L3 复习产物")))
    c.check("3.3 teaching-loop 同步深讲与设计标识",
            all(k in teaching for k in ("完整深讲", "方案：", "设计说明：")))
    c.check("3.4 subject-playbooks 同步设计/记忆标识",
            all(k in subjects for k in ("方案：", "设计说明：", "纯记忆")))
    style_order = [styles.find(x) for x in ("教学例", "配对练习", "易错点〔④",
                                             "闭卷自检", "评估例/迁移")]
    c.check("3.5 lecture-styles 同步四段/闭卷/评估例 + 顺序",
            all(k in styles for k in ("配对练习", "闭卷自检", "评估例", "迁移/判定"))
            and all(i >= 0 for i in style_order) and style_order == sorted(style_order))
    c.check("3.6 phases 同步四段/二次定稿",
            all(k in phases for k in ("四段", "④/⑤", "二次定稿")))

    c.check("4.1 脚本接受设计类交付标识",
            all(k in verify_explanation for k in ("方案", "设计说明")))
    c.check("4.2 脚本提示含纯记忆/检索版",
            all(k in verify_explanation for k in ("纯记忆", "已会·检索版")))
    c.check("4.3 SKILL 登记 handout-design",
            "handout-design.md" in skill)
    script_markers = lead_markers(verify_explanation)
    marker_table = re.search(r"### 2\.3.*?(?=### 2\.4)", handout, re.S)
    marker_table = marker_table.group(0) if marker_table else ""
    table_only = marker_table.split("**canonical 集合**")[0]
    c.check("4.4 交付标识集合一致（脚本/合同表/lecture-styles）",
            script_markers == CANON_MARKERS
            and all(m in table_only for m in CANON_MARKERS)
            and all(m in styles for m in CANON_MARKERS),
            "脚本独有=" + repr(sorted(script_markers - CANON_MARKERS))
            + " 缺失=" + repr(sorted(CANON_MARKERS - script_markers)))

    c.check("5.1 E108 已登记且指向本契约",
            any(isinstance(case, dict) and case.get("id") == "E108"
                and "verify-v64-consistency.py" in str(case.get("machine_ref", ""))
                for case in evals.get("cases", [])))

    # ── mutation：改坏关键规则后，检查器必须报错 ──
    mutations = (
        ("概念地图阈值改回 8+", styles.replace("5 个以上概念", "8 个以上概念")),
        ("台账状态行被合并回状态行", styles.replace("台账状态行", "状态行")),
        ("设计类标识被删", styles.replace("方案：", "")),
        ("深讲拆节被删", styles.replace("拆节", "")),
        ("纯记忆被误写成纯概念", styles.replace("纯记忆", "纯概念")),
    )
    for name, mutated in mutations:
        c.check("6.x mutation 能抓到：" + name, bool(style_problems(mutated)),
                style_problems(mutated))
    mut_script = verify_explanation.replace("|Steps|Key", "|Steps|Key|Extra")
    c.check("6.x mutation 能抓到：脚本交付标识多出一项",
            lead_markers(mut_script) != CANON_MARKERS)

    print("verify-v64-consistency: {} checks, {} OK, {} FAIL".format(
        c.ok + c.fail, c.ok, c.fail))
    return 0 if c.fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
