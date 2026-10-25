#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-v65-stage2.py - v6.5 阶段 2 契约（stdlib-only、只读）。

检查“类型模板、四步流水线、L1/L2/L3、学习者状态、决策日志/修复表”是否真正
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
    except (OSError, UnicodeDecodeError):
        return ""


def version_tuple(text):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", str(text or ""))
    return tuple(int(x) for x in m.groups()) if m else None


def at_least_v65(text):
    v = version_tuple(text)
    return v is not None and v >= (6, 5, 0)


def stage2_problems(handout):
    problems = []
    for phrase, label in (
        ("## 4. 类型模板（阶段 2）", "类型模板"),
        ("### 4.1 类型判定", "类型判定"),
        ("### 4.2 四类矩阵", "四类矩阵"),
        ("类型决定证据形态，风格决定呈现，学科提供素材", "类型/风格/学科分工"),
        ("记忆 5–7 chunk", "类型单元数"),
        ("## 5. 讲义生成四步流水线（阶段 2）", "四步流水线"),
        ("### 5.1 分析：任务拆解与专家盲点", "分析步"),
        ("3–7 个子技能/决策点", "子技能拆解"),
        ("最小典型", "示例选择"),
        ("## 6. L1/L2/L3 支持级（阶段 2）", "支持级"),
        ("按技能判，不按课程判", "按技能判"),
        ("L3 用**检索版要点卡**", "L3 产物"),
        ("### 6.1 动态升降", "动态升降"),
        ("## 7. 学习者状态层（阶段 2）", "学习者状态"),
        ("确证铁律延伸到讲义", "学习者证据"),
        ("已会·可跳过", "个性化标签"),
        ("## 8. 决策日志与修复表（阶段 2）", "决策日志/修复表"),
        ("症状 → 最可能原因 → 现在做什么 → 怎么验证修好了", "修复表格式"),
        ("来源四向对齐", "来源对齐"),
    ):
        if phrase not in handout:
            problems.append(label)
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="v6.5 阶段 2 契约（只读）")
    parser.add_argument("--skill-root", default=None)
    args = parser.parse_args(argv)
    root = (Path(args.skill_root).resolve() if args.skill_root
            else Path(__file__).resolve().parent.parent)

    skill = read(root, "SKILL.md")
    handout = read(root, "references/handout-design.md")
    styles = read(root, "references/lecture-styles.md")
    phases = read(root, "references/phases-and-gates.md")
    entry = read(root, "references/entry-routing.md")
    teaching = read(root, "references/teaching-loop.md")
    subjects = read(root, "references/subject-playbooks.md")
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
    c.check("1.1 SKILL.md 版本 ≥ 6.5.0",
            at_least_v65(version_in(skill, r"version:\s*(\d+\.\d+\.\d+)")))
    c.check("1.2 setup-guide 适用版本 ≥ 6.5.0",
            at_least_v65(version_in(setup, r"适用版本：(\d+\.\d+\.\d+)")))
    c.check("1.3 skill-dependencies 版本 ≥ 6.5.0",
            bool(deps_versions) and all(at_least_v65(v) for v in deps_versions),
            deps_versions)
    c.check("1.4 CREDITS 当前版本说明 ≥ 6.5.0",
            at_least_v65(version_in(credits, r"当前版本说明\*\*：(\d+\.\d+\.\d+)")))
    c.check("1.5 evals 版本 ≥ 6.5.0",
            at_least_v65(evals.get("applies_to_version", "")))

    c.check("2.1 阶段 2 正文齐全", not stage2_problems(handout)
            and all(k in handout for k in ("概念 5–7", "程序 3–5", "设计 1–3")),
            stage2_problems(handout))
    c.check("2.2 四类模板齐全",
            all(k in handout for k in ("记忆", "概念", "程序", "设计",
                                       "① 题目/任务", "② 解析/过程",
                                       "③ 答案", "④ 易错", "⑤ 小结")))
    c.check("2.3 类型化答案形态",
            all(k in handout for k in ("`方案：`/`设计说明：`", "`答案：`/`答：`",
                                       "`答：`/`参考答案：`", "`解：`/`步骤：`/`代码：`",
                                       "纯记忆豁免", "不写框内批注")))
    c.check("2.4 流水线四步齐全",
            all(k in handout for k in ("| 分析 |", "| 设计 |", "| 生成 |", "| 修复 |")))
    c.check("2.5 支持级与动态",
            all(k in handout for k in ("L1", "L2", "L3", "70–90%",
                                       ">90%", "跨会话", "可同会话",
                                       "L1 | 关键能力独立通过")))
    c.check("2.6 学习者状态三源",
            all(k in handout for k in ("KP 状态", "薄弱点/错题本/保持复习",
                                       "本次交接/学习记录/画像", "本次 S1/S3 证据",
                                       "已会不是 KP 状态")))
    c.check("2.7 决策日志/修复表条件触发",
            all(k in handout for k in ("复杂程序与设计", "决策日志", "修复表",
                                       "附件")))

    c.check("3.1 lecture-styles 指向类型/支持级",
            all(k in styles for k in ("类型矩阵见 `handout-design.md` §4",
                                      "L2/L3 可不出完整教学例")))
    c.check("3.2 phases 接线",
            all(k in phases for k in ("四步流水线", "§4–§8", "决策日志")))
    c.check("3.3 entry-routing 独立写讲义接线",
            all(k in entry for k in ("四步流水线", "决策日志",
                                      "L3 可产出检索版要点卡")))
    c.check("3.4 teaching-loop 备课接线",
            all(k in teaching for k in ("§4–§8", "类型矩阵")))
    c.check("3.5 subject-playbooks 类型指针",
            "类型模板" in subjects)
    c.check("3.6 SKILL 索引登记阶段 2",
            "阶段 2 类型/流水线/支持级/学习者/决策日志" in skill)

    c.check("4.1 E109 已登记且指向本契约",
            any(isinstance(case, dict) and case.get("id") == "E109"
                and "verify-v65-stage2.py" in str(case.get("machine_ref", ""))
                for case in evals.get("cases", [])))

    # ── mutation：改坏阶段 2 规则后，检查器必须报错 ──
    mutations = (
        ("四类矩阵被删", handout.replace("### 4.2 四类矩阵", "")),
        ("L3 检索版产物被删", handout.replace("L3 用**检索版要点卡**", "")),
        ("专家盲点被删", handout.replace("专家盲点", "")),
        ("决策日志被删", handout.replace("决策日志", "")),
        ("来源对齐被删", handout.replace("来源四向对齐", "")),
    )
    for name, mutated in mutations:
        c.check("5.x mutation 能抓到：" + name, bool(stage2_problems(mutated)),
                stage2_problems(mutated))

    print("verify-v65-stage2: {} checks, {} OK, {} FAIL".format(
        c.ok + c.fail, c.ok, c.fail))
    return 0 if c.fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
