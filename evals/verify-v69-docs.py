#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-v69-docs.py - v6.9.0 最细知识点块契约（stdlib-only、只读）。

检查「块 = 当前节目标内最细知识点」是否写入规则文件、旧口径是否清零、
版本字段是否同步，并用 mutation 证明检查器不是空转。
只读静态证据，不替代真人回放。
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


def version_in(text, pattern):
    m = re.search(pattern, text or "")
    return m.group(1) if m else ""


RULE_FILES = (
    "SKILL.md",
    "references/phases-and-gates.md",
    "references/teaching-loop.md",
    "references/lecture-styles.md",
    "references/handout-design.md",
    "references/data-and-recovery.md",
    "references/redlines.md",
)

REQUIRED = {
    "SKILL.md": ("最细知识点", "独立答对才进下一块", "6.9.0"),
    "references/phases-and-gates.md": (
        "1 块 = 1 个最细知识点",
        "禁止多概念块",
        "不设时间上限",
        "独立答对才进下一块",
    ),
    "references/teaching-loop.md": (
        "1 块 = 1 个最细知识点",
        "独立答对才进下一块",
        "不按块数/时长拆",
    ),
    "references/lecture-styles.md": ("一个块 = 1 个最细知识点",),
    "references/handout-design.md": ("对话讲授仍按 1 块 = 1 个最细知识点",),
    "references/data-and-recovery.md": (
        "1 个讲授块 = 1 个 KP",
        "需 2 道题分别检验两个判断 → 拆 KP",
    ),
    "references/redlines.md": ("多概念块",),
}

LEGACY = (
    "一个块可映射多个 KP",
    "块 ≠ KP",
    "合并组",
    "每节默认 ≤3–4 道",
    "每节 ≤3–4 道",
    "≤5–7 个 KP",
    "每块 5–10 分钟",
    "块尺寸 5–10 分钟",
)


def problems(texts, evals, deps):
    found = []
    for rel in RULE_FILES:
        body = texts.get(rel, "")
        for needle in REQUIRED.get(rel, ()):
            if needle not in body:
                found.append("{} 缺少「{}」".format(rel, needle))
        for needle in LEGACY:
            if needle in body:
                found.append("{} 仍含旧口径「{}」".format(rel, needle))

    if version_in(texts.get("SKILL.md", ""), r"version:\s*(\d+\.\d+\.\d+)") != "6.9.0":
        found.append("SKILL.md version 不是 6.9.0")
    if "适用版本：6.9.0" not in texts.get("references/setup-guide.md", ""):
        found.append("setup-guide 适用版本不是 6.9.0")
    if '"applies_to_version": "6.9.0"' not in deps:
        found.append("skill-dependencies 未声明 6.9.0")
    if not re.search(r"当前版本说明\*\*：6\.9\.0", texts.get("CREDITS.md", "")):
        found.append("CREDITS 当前版本说明不是 6.9.0")
    if evals.get("applies_to_version") != "6.9.0":
        found.append("evals.json applies_to_version 不是 6.9.0")
    if not any(
        isinstance(case, dict) and case.get("id") == "E136"
        for case in evals.get("cases", [])
    ):
        found.append("evals.json 缺少 E136")
    formula = texts.get("evals/verify-formula-typesetting.py", "")
    if "6.9.0" not in formula:
        found.append("verify-formula-typesetting.py 未同步 6.9.0")
    if "6.8.0" in formula:
        found.append("verify-formula-typesetting.py 仍含 6.8.0")
    return found


def mutate(texts, rel, old, new):
    changed = dict(texts)
    changed[rel] = changed.get(rel, "").replace(old, new)
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description="v6.9.0 最细知识点块契约（只读）")
    parser.add_argument("--skill-root", default=None)
    args = parser.parse_args(argv)

    root = (
        Path(args.skill_root).resolve()
        if args.skill_root
        else Path(__file__).resolve().parents[1]
    )
    rels = list(RULE_FILES) + ["references/setup-guide.md", "CREDITS.md",
                               "evals/verify-formula-typesetting.py"]
    texts = {rel: read(root, rel) for rel in rels}
    deps = read(root, "skill-dependencies.json")
    try:
        evals = json.loads(read(root, "evals/evals.json") or "{}")
    except ValueError as exc:
        evals = {}
        print("[FAIL] evals.json 不是合法 JSON：{}".format(exc))

    c = Checker()
    found = problems(texts, evals, deps)
    c.check("1.1 规则文件与版本字段全部符合 v6.9.0", not found, found)

    c.check("1.2 节内块数不设上限、教材节不按块数拆",
            "节内块数不设上限" in texts["references/phases-and-gates.md"]
            and "教材节不按块数拆" in texts["references/phases-and-gates.md"])
    c.check("1.3 加速不合并知识点",
            "只压缩单块讲法" in texts["references/phases-and-gates.md"]
            or "只压缩单块讲法" in texts["references/lecture-styles.md"])
    c.check("1.4 SR-9 覆盖多概念块", "多概念块" in texts["references/redlines.md"])
    c.check("1.5 E136 是可执行的人评用例",
            any(
                isinstance(case, dict) and case.get("id") == "E136"
                and "拆成 3 块" in str(case.get("pass_condition", ""))
                for case in evals.get("cases", [])
            ))

    mutations = (
        ("SKILL 去掉最细知识点", mutate(texts, "SKILL.md", "最细知识点", "知识点")),
        ("phases 放回多 KP 块", mutate(
            texts, "references/phases-and-gates.md",
            "1 块 = 1 个最细知识点", "块 ≠ KP；一个块可映射多个 KP")),
        ("teaching 放回合并组", mutate(
            texts, "references/teaching-loop.md",
            "独立答对才进下一块", "合并组")),
        ("lecture 放回每节 ≤3–4 道", mutate(
            texts, "references/lecture-styles.md",
            "不设每节道数上限", "每节 ≤3–4 道")),
        ("redlines 去掉多概念块", mutate(
            texts, "references/redlines.md", "多概念块", "整节投喂")),
        ("版本回到 6.8.0", mutate(texts, "SKILL.md", "6.9.0", "6.8.0")),
    )
    for name, mutated in mutations:
        got = problems(mutated, evals, deps)
        c.check("2.x mutation 能抓到：" + name, bool(got), got)

    print("verify-v69-docs: {} checks, {} OK, {} FAIL".format(
        c.ok + c.fail, c.ok, c.fail))
    return 0 if c.fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
