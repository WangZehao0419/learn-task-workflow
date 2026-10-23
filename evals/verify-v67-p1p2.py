#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-v67-p1p2.py - v6.7.2 P1/P2 契约（stdlib-only、只读）。

检查 P1（文本结构、主张—证据、设计量表、主图、质量回路、要点卡、移动端/MVP、
问题停车位/贯穿案例/难度预算）与 P2（教材章节层）是否写入
handout-design 并接线；语义执行仍由模型/评审负责。
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


def at_least_v671(text):
    v = version_tuple(text)
    return v is not None and v >= (6, 7, 1)


def p1p2_problems(handout):
    problems = []
    for phrase, label in (
        ("## 10. P1 质量与运营（可选增强）", "P1"),
        ("### 10.1 文本结构", "文本结构"),
        ("序列", "序列结构"),
        ("### 10.2 主张—证据表", "主张—证据"),
        ("主张 | 证据/来源 | 强度/边界", "主张—证据表格式"),
        ("学员版放正文，需要补充时放 `## 扩展（选读）` 区，不另起附录", "主张—证据表位置"),
        ("### 10.3 设计类评价量表", "设计量表"),
        ("训练量表", "量表性质"),
        ("### 10.4 按类型选主图", "主图选择"),
        ("权衡矩阵", "设计主图"),
        ("### 10.5 效用价值提示", "效用价值"),
        ("作为独立一行，不并入 ⑤ 三句", "效用价值提示位置"),
        ("### 10.6 质量回路", "质量回路"),
        ("记在 progress.md 记录侧，不写进定稿讲义", "质量回路落点"),
        ("独立讲义无 progress.md 时省略，不新建", "质量回路独立讲义出口"),
        ("### 10.7 要点卡与间隔复习", "要点卡/间隔"),
        ("1/7/30", "间隔节奏"),
        ("按类型：概念判别句/记忆线索卡/程序决策流程/设计权衡句", "要点卡类型化"),
        ("记忆线索卡按 §2.9 可到 7 条", "要点卡记忆例外"),
        ("L3 检索版按 §6 的 3–5 题", "L3 检索版题量"),
        ("陪学任务内按现有 `## 保持复习` 条目交给 scheduler/due-queue，以条目级 due 为主", "调度不双轨"),
        ("### 10.8 移动端与 MVP", "移动端/MVP"),
        ("≤4 列", "移动端表格"),
        ("### 10.9 问题停车位/贯穿案例/难度预算", "P1 收尾"),
        ("问题停车位：讲义末尾 `## 待解决问题`（有 `## 扩展（选读）` 时放在其前", "停车位与扩展区顺序"),
        ("贯穿案例：多概念小节可用一个案例逐步演化", "贯穿案例"),
        ("难度预算：每节 1 道", "难度预算"),
        ("## 11. P2 教材级章节层（可选）", "P2"),
        ("### 11.1 教材级章节层", "教材章节"),
        ("术语表自测", "术语自测"),
        ("P1/P2 是可选增强", "可选增强边界"),
        ("## 12. 证据与边界", "证据边界"),
    ):
        if phrase not in handout:
            problems.append(label)
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="v6.7.2 P1/P2 契约（只读）")
    parser.add_argument("--skill-root", default=None)
    args = parser.parse_args(argv)
    root = (Path(args.skill_root).resolve() if args.skill_root
            else Path(__file__).resolve().parent.parent)

    skill = read(root, "SKILL.md")
    handout = read(root, "references/handout-design.md")
    phases = read(root, "references/phases-and-gates.md")
    entry = read(root, "references/entry-routing.md")
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
    c.check("1.1 SKILL.md 版本 ≥ 6.7.2",
            at_least_v671(version_in(skill, r"version:\s*(\d+\.\d+\.\d+)")))
    c.check("1.2 setup-guide 适用版本 ≥ 6.7.2",
            at_least_v671(version_in(setup, r"适用版本：(\d+\.\d+\.\d+)")))
    c.check("1.3 skill-dependencies 版本 ≥ 6.7.2",
            bool(deps_versions) and all(at_least_v671(v) for v in deps_versions),
            deps_versions)
    c.check("1.4 CREDITS 当前版本说明 ≥ 6.7.2",
            at_least_v671(version_in(credits, r"当前版本说明\*\*：(\d+\.\d+\.\d+)")))
    c.check("1.5 evals 版本 ≥ 6.7.2",
            at_least_v671(evals.get("applies_to_version", "")))

    c.check("2.1 P1/P2 正文齐全", not p1p2_problems(handout),
            p1p2_problems(handout))
    c.check("2.2 文本结构五型",
            all(k in handout for k in ("序列", "比较", "因果", "问题—解决", "主张—证据")))
    c.check("2.3 设计量表与主图",
            all(k in handout for k in ("标准", "水平", "训练量表", "权衡矩阵")))
    c.check("2.4 质量回路/要点卡/移动端",
            all(k in handout for k in ("实际用时", "心理努力", "1/7/30", "≤4 列", "MVP", "核心解释段")))
    c.check("2.5 教材章节层",
            all(k in handout for k in ("章首", "章末", "术语表自测")))

    c.check("3.1 SKILL 索引登记 P1/P2",
            "P1/P2 可选增强见 §10–§11" in skill)
    c.check("3.2 entry-routing 教材/整章接线",
            all(k in entry for k in ("教材/整章", "章首路线图", "章末混合检索")))
    c.check("3.3 phases 接线",
            "P1/P2 可选增强见 `handout-design.md` §10–§11" in phases)

    c.check("4.1 E122 已登记且指向本契约",
            any(isinstance(case, dict) and case.get("id") == "E122"
                and "verify-v67-p1p2.py" in str(case.get("machine_ref", ""))
                for case in evals.get("cases", [])))

    # ── mutation：改坏 P1/P2 规则后，检查器必须报错 ──
    mutations = (
        ("文本结构被删", handout.replace("### 10.1 文本结构", "")),
        ("设计量表被删", handout.replace("### 10.3 设计类评价量表", "")),
        ("要点卡/间隔被删", handout.replace("### 10.7 要点卡与间隔复习", "")),
        ("要点卡/调度/扩展区冲突被删", handout
         .replace("L3 检索版按 §6 的 3–5 题", "")
         .replace("陪学任务内按现有 `## 保持复习` 条目交给 scheduler/due-queue，以条目级 due 为主", "")
         .replace("问题停车位：讲义末尾 `## 待解决问题`（有 `## 扩展（选读）` 时放在其前", "")),
        ("教材章节被删", handout.replace("### 11.1 教材级章节层", "")),
    )
    for name, mutated in mutations:
        c.check("5.x mutation 能抓到：" + name, bool(p1p2_problems(mutated)),
                p1p2_problems(mutated))

    print("verify-v67-p1p2: {} checks, {} OK, {} FAIL".format(
        c.ok + c.fail, c.ok, c.fail))
    return 0 if c.fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
