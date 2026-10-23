#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-v66-stage3.py - v6.6 阶段 3 契约（stdlib-only、只读）。

检查“来源四向对齐、覆盖行、深度分配、教学例/评估例真实性、来源保真”是否
写进 handout-design 并接线；语义执行仍由模型/评审负责。
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
    except OSError:
        return ""


def version_tuple(text):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", str(text or ""))
    return tuple(int(x) for x in m.groups()) if m else None


def at_least_v66(text):
    v = version_tuple(text)
    return v is not None and v >= (6, 6, 0)


def stage3_problems(handout):
    problems = []
    for phrase, label in (
        ("## 9. 来源、范围与评估真实性（阶段 3）", "阶段 3 正文"),
        ("### 9.1 四向对齐", "四向对齐"),
        ("来源→KP→讲义→题组", "四向链路"),
        ("### 9.2 覆盖行与暂缓/范围外", "覆盖行"),
        ("覆盖：来源 3.1–3.2（KP-01/02）", "覆盖行格式"),
        ("SR-7", "SR-7 出口"),
        ("### 9.3 深度分配", "深度分配"),
        ("高频高分→深讲/工作", "深度规则"),
        ("### 9.4 教学例 vs 评估例：来源真实性", "教学/评估例"),
        ("来源原题/真题/学员真实任务", "评估例真实性"),
        ("不是第二个完整教学例", "评估例边界"),
        ("### 9.5 来源保真", "来源保真"),
        ("页码/章节/图号/表号/数据位置", "来源锚点"),
        ("引用原文不超过本单元两成", "引用上限"),
        ("来源冲突", "来源冲突"),
        ("未核实", "未核实"),
        ("### 9.6 模块目标与考试对齐", "模块/考试对齐"),
        ("考频/题型/分值", "考试对齐"),
        ("独立写讲义无 S2", "独立讲义模块目标出口"),
        ("P1 质量与运营", "P1"),
        ("P2 教材级章节层", "P2"),
        ("证据与边界", "证据边界"),
        ("11 条", "一页合同条数"),
    ):
        if phrase not in handout:
            problems.append(label)
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="v6.6 阶段 3 契约（只读）")
    parser.add_argument("--skill-root", default=None)
    args = parser.parse_args(argv)
    root = (Path(args.skill_root).resolve() if args.skill_root
            else Path(__file__).resolve().parent.parent)

    skill = read(root, "SKILL.md")
    handout = read(root, "references/handout-design.md")
    phases = read(root, "references/phases-and-gates.md")
    entry = read(root, "references/entry-routing.md")
    teaching = read(root, "references/teaching-loop.md")
    credits = read(root, "CREDITS.md")
    setup = read(root, "references/setup-guide.md")
    deps_raw = read(root, "skill-dependencies.json")
    evals_raw = read(root, "evals/evals.json")
    try:
        deps = json.loads(deps_raw)
    except (TypeError, ValueError):
        deps = {}
    try:
        evals = json.loads(evals_raw)
    except (TypeError, ValueError):
        evals = {}

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
    c.check("1.1 SKILL.md 版本 ≥ 6.6.0",
            at_least_v66(version_in(skill, r"version:\s*(\d+\.\d+\.\d+)")))
    c.check("1.2 setup-guide 适用版本 ≥ 6.6.0",
            at_least_v66(version_in(setup, r"适用版本：(\d+\.\d+\.\d+)")))
    c.check("1.3 skill-dependencies 版本 ≥ 6.6.0",
            bool(deps_versions) and all(at_least_v66(v) for v in deps_versions),
            deps_versions)
    c.check("1.4 CREDITS 当前版本说明 ≥ 6.6.0",
            at_least_v66(version_in(credits, r"当前版本说明\*\*：(\d+\.\d+\.\d+)")))
    c.check("1.5 evals 版本 ≥ 6.6.0",
            at_least_v66(evals.get("applies_to_version", "")))

    c.check("2.1 阶段 3 正文齐全", not stage3_problems(handout),
            stage3_problems(handout))
    c.check("2.2 四向对齐矩阵含来源/KP/单元/题组",
            all(k in handout for k in ("来源小节", "KP", "讲义单元", "自测/题组")))
    c.check("2.3 覆盖行含暂缓/范围外",
            all(k in handout for k in ("覆盖：", "暂缓", "范围外", "SR-7")))
    c.check("2.4 深度分配覆盖四类任务",
            all(k in handout for k in ("备考", "知识型", "技能型", "材料型",
                                       "深讲", "工作", "参照")))
    c.check("2.5 评估例真实性",
            all(k in handout for k in ("来源原题/真题/学员真实任务",
                                       "不是第二个完整教学例", "答案三件套")))
    c.check("2.6 来源保真",
            all(k in handout for k in ("来源锚点", "改编", "引用原文不超过本单元两成",
                                       "来源冲突", "版本/年份", "未核实")))
    c.check("2.7 模块/考试对齐",
            all(k in handout for k in ("模块目标", "考频/题型/分值", "不编造官方分值")))

    c.check("3.1 SKILL 索引登记阶段 3",
            "阶段 3 来源/范围/深度/评估真实性" in skill)
    c.check("3.2 phases 接线",
            "来源/覆盖/深度按 `handout-design.md` §9" in phases)
    c.check("3.3 entry-routing 接线",
            "来源映射/覆盖行/深度分配按 §9" in entry)
    c.check("3.4 teaching-loop 接线",
            "讲义来源映射" in teaching)

    c.check("4.1 E116 已登记且指向本契约",
            any(isinstance(case, dict) and case.get("id") == "E116"
                and "verify-v66-stage3.py" in str(case.get("machine_ref", ""))
                for case in evals.get("cases", [])))

    # ── mutation：改坏阶段 3 规则后，检查器必须报错 ──
    mutations = (
        ("四向对齐被删", handout.replace("### 9.1 四向对齐", "")),
        ("覆盖行格式被删", handout.replace("覆盖：来源 3.1–3.2（KP-01/02）", "")),
        ("深度分配被删", handout.replace("### 9.3 深度分配", "")),
        ("引用上限被删", handout.replace("引用原文不超过本单元两成", "")),
        ("评估例真实性被删", handout.replace("### 9.4 教学例 vs 评估例：来源真实性", "")),
    )
    for name, mutated in mutations:
        c.check("5.x mutation 能抓到：" + name, bool(stage3_problems(mutated)),
                stage3_problems(mutated))

    print("verify-v66-stage3: {} checks, {} OK, {} FAIL".format(
        c.ok + c.fail, c.ok, c.fail))
    return 0 if c.fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
