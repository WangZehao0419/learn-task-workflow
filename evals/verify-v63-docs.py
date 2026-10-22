#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-v63-docs.py - v6.3 文档型增强静态契约（stdlib-only、只读）。

检查“规则有没有真正写进对应分册”：出题流水线四步、旧题去重、规划字段、
一次修复、视觉任务原始来源、版本字段与 eval 登记。语义是否执行仍由模型/评审负责。
"""

import argparse
import json
import re
from pathlib import Path

import sys


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


def line_with(text, needle):
    return next((line for line in text.splitlines() if needle in line), "")


def version_tuple(text):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", str(text or ""))
    return tuple(int(x) for x in m.groups()) if m else None


def at_least_v63(text):
    v = version_tuple(text)
    return v is not None and v >= (6, 3, 0)


def main(argv=None):
    parser = argparse.ArgumentParser(description="v6.3 文档型增强静态契约（只读）")
    parser.add_argument("--skill-root", default=None)
    args = parser.parse_args(argv)
    root = (Path(args.skill_root).resolve() if args.skill_root
            else Path(__file__).resolve().parent.parent)

    skill = read(root, "SKILL.md")
    data = read(root, "references/data-and-recovery.md")
    teaching = read(root, "references/teaching-loop.md")
    styles = read(root, "references/lecture-styles.md")
    phases = read(root, "references/phases-and-gates.md")
    subjects = read(root, "references/subject-playbooks.md")
    redlines = read(root, "references/redlines.md")
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
    c.check("1.1 SKILL.md 版本 ≥ 6.3.0",
            at_least_v63(version_in(skill, r"version:\s*(\d+\.\d+\.\d+)")))
    c.check("1.2 setup-guide 适用版本 ≥ 6.3.0",
            at_least_v63(version_in(setup, r"适用版本：(\d+\.\d+\.\d+)")))
    c.check("1.3 skill-dependencies 版本 ≥ 6.3.0",
            bool(deps_versions) and all(at_least_v63(v) for v in deps_versions),
            deps_versions)
    c.check("1.4 CREDITS 当前版本说明 ≥ 6.3.0",
            at_least_v63(version_in(credits, r"当前版本说明\*\*：(\d+\.\d+\.\d+)")))
    c.check("1.5 evals 版本 ≥ 6.3.0",
            at_least_v63(evals.get("applies_to_version", "")))

    c.check("2.1 讲义规则含「出题流水线（四步，v6.3）」",
            "## 出题流水线（四步，v6.3）" in styles)
    c.check("2.2 四步齐全（探索/规划/生成/修复）",
            all(k in styles for k in ("1. **探索**", "2. **规划**",
                                      "3. **生成**", "4. **修复**")))
    explore_line = line_with(styles, "1. **探索**")
    plan_line = line_with(styles, "2. **规划**")
    gen_line = line_with(styles, "3. **生成**")
    repair_line = line_with(styles, "4. **修复**")
    c.check("2.3 探索步读最近题组并避免重复旧题",
            all(k in explore_line for k in ("最近题组与判分记录", "避免重复旧题",
                                            "S5 按蓝图读全部纳入 KP",
                                            "无任务时跳过", "跨日续学可重跑")))
    c.check("2.4 规划步定 topic/题型/难度/KP 且含判定题",
            all(k in plan_line for k in ("逐题定 topic、题型", "难度",
                                         "至少 1 道判定题", "组内 topic 不重复",
                                         "S5 综合测验按蓝图")))
    c.check("2.5 生成步含选项打乱/字母中立/答案键私有",
            all(k in gen_line for k in ("选项等长并打乱", "不引用字母",
                                        "答案键批改前私有", "KP 映射")))
    c.check("2.6 修复步一次性自检且答案键不确定标未判",
            all(k in repair_line for k in ("整套题一次性自检", "修一次并重检",
                                           "答案键不确定标 `未判`",
                                           "本节自测同题（仅 S3 新学题组适用，此项无例外）")))
    c.check("2.7 零提示规则在流水线第 3–4 步核对",
            "以下规则在流水线第 3 步生成与第 4 步修复时逐条核对" in styles)
    c.check("2.8 S3 练习接入出题流水线",
            "出题流水线（四步，v6.3）" in line_with(phases, "| ④ | **练习** |"))
    c.check("2.9 S4 抽取与出题接入出题流水线",
            "出题流水线（四步，v6.3）" in line_with(phases, "动作（抽取与出题）"))
    c.check("2.10 「考考我」接入出题流水线",
            "出题流水线（四步，v6.3）" in line_with(data, "**考考我**"))
    c.check("2.11 S5 综合测验先按蓝图定覆盖/题量/分值，再走流水线",
            all(k in styles for k in ("S5 综合测验", "能力—任务—评分点蓝图",
                                      "再用本流水线")))
    c.check("2.12 T11 原题保持例外覆盖探索/规划/修复",
            all("T11 明确选择「原题保持」时除外" in line
                for line in (explore_line, plan_line, repair_line)))

    c.check("3.1 数据模型含「视觉任务来源纪律（v6.3，零迁移）」",
            "视觉任务来源纪律（v6.3，零迁移）" in data)
    c.check("3.2 视觉任务必须基于原始图/表并记来源锚点",
            all(k in data for k in ("原始图/表/截图/数据", "原始像素",
                                    "原始数据表", "页码/图号/数据位置",
                                    "图中编号、关系与数据按原图")))
    c.check("3.3 禁止生成图/重绘图/讲义示意图替代原图",
            "不得用生成图、重绘图或讲义示意图替代原图" in data)
    c.check("3.4 原图不可用/旧证据无锚点时不删字段，按未判或补齐",
            all(k in data for k in ("新任务不要声明该视觉任务",
                                    "不得删除或改写字段或证据标签",
                                    "无法补齐时按 `未判` 处理")))
    c.check("3.5 提示后不算独立且不新增字段/告警码/闸口",
            all(k in data for k in ("提示后作答不算独立",
                                    "不新增字段、告警码或闸口")))
    c.check("3.6 来源备课接入视觉任务原始来源",
            all(k in teaching for k in ("视觉任务取原始来源", "页码/图号")))
    c.check("3.7 学科分册接入视觉任务来源",
            all(k in subjects for k in ("视觉任务来源",
                                        "不用生成图或讲义示意图替代",
                                        "其他学科有原始图/表时同样适用")))
    c.check("3.8 讲义绘图规则声明讲解图不能替代原始来源",
            "视觉任务与讲解图分开" in styles)
    c.check("3.9 知识清单规则只在有原始图/表的 KP 上声明视觉任务",
            "只在确有原始图/表的 KP 上声明" in phases)
    c.check("3.10 红线 CR-8 覆盖视觉字段的删除或改写",
            all(k in redlines for k in ("删除或改写 KP 类型/视觉任务字段或证据标签",
                                        "不得删除或改写"))
            and "删除或改写 KP 类型/视觉任务字段或证据标签" in skill)

    c.check("4.1 CREDITS 的 DeepTutor 行含出题流水线与视觉任务原图来源",
            all(k in credits for k in ("DeepTutor", "出题流水线",
                                       "视觉任务原图来源")))
    c.check("4.2 SKILL 描述含出题四步流水线与视觉任务原图来源",
            all(k in skill for k in ("出题四步流水线", "视觉任务原图来源")))
    cases = [case for case in evals.get("cases", []) if isinstance(case, dict)]
    ids = {case.get("id") for case in cases}
    c.check("4.3 evals 登记 E71–E73", {"E71", "E72", "E73"}.issubset(ids))
    e71 = next((case for case in cases if case.get("id") == "E71"), {})
    c.check("4.4 E71 指向 verify-v63-docs.py",
            "verify-v63-docs.py" in str(e71.get("machine_ref", "")))
    c.check("4.5 evals 用例总数至少 78", len(cases) >= 78, len(cases))

    print("verify-v63-docs: " + str(c.ok) + " checks, " + str(c.ok) + " OK, "
          + str(c.fail) + " FAIL")
    return 0 if c.fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
