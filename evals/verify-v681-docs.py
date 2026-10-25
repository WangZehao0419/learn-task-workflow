#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-v681-docs.py - v6.8.1 最细知识点块契约（stdlib-only、只读）。

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
    except (OSError, UnicodeDecodeError):
        return ""


def text_of(texts, rel):
    if not isinstance(texts, dict):
        return ""
    value = texts.get(rel, "")
    return value if isinstance(value, str) else ""


def version_in(text, pattern):
    m = re.search(pattern, text or "")
    return m.group(1) if m else ""


def parse_version(value):
    try:
        return tuple(int(part) for part in str(value).split("."))
    except ValueError:
        return ()


def ver_at_least(value, minimum):
    parts = parse_version(value)
    return bool(parts) and parts >= minimum


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
    "SKILL.md": ("最细知识点", "独立答对才进下一块"),
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
    if not isinstance(evals, dict):
        evals = {}
    cases = evals.get("cases")
    if not isinstance(cases, list):
        cases = []
    for rel in RULE_FILES:
        body = text_of(texts, rel)
        for needle in REQUIRED.get(rel, ()):
            if needle not in body:
                found.append("{} 缺少「{}」".format(rel, needle))
        for needle in LEGACY:
            if needle in body:
                found.append("{} 仍含旧口径「{}」".format(rel, needle))

    minimum = (6, 8, 1)
    if not ver_at_least(
            version_in(text_of(texts, "SKILL.md"), r"version:\s*(\d+\.\d+\.\d+)"),
            minimum):
        found.append("SKILL.md version 低于 6.8.1")
    if not ver_at_least(
            version_in(text_of(texts, "references/setup-guide.md"),
                       r"适用版本：(\d+\.\d+\.\d+)"),
            minimum):
        found.append("setup-guide 适用版本低于 6.8.1")
    if isinstance(deps, dict):
        deps_data = deps
    else:
        try:
            deps_data = json.loads(deps or "{}")
        except (ValueError, TypeError):
            deps_data = {}
    dep_versions = []
    if isinstance(deps_data, dict):
        if "applies_to_version" in deps_data:
            dep_versions.append(deps_data.get("applies_to_version"))
        for dep in deps_data.get("dependencies", []):
            setup = dep.get("setup") if isinstance(dep, dict) else None
            if isinstance(setup, dict) and "applies_to_version" in setup:
                dep_versions.append(setup.get("applies_to_version"))
    if not dep_versions or any(not ver_at_least(v, minimum) for v in dep_versions):
        found.append("skill-dependencies 未声明 ≥6.8.1")
    credits_version = version_in(
        text_of(texts, "CREDITS.md"), r"当前版本说明\*\*：(\d+\.\d+\.\d+)")
    if not ver_at_least(credits_version, minimum):
        found.append("CREDITS 当前版本说明低于 6.8.1")
    if not ver_at_least(evals.get("applies_to_version"), minimum):
        found.append("evals.json applies_to_version 低于 6.8.1")
    if not any(
        isinstance(case, dict) and case.get("id") == "E136"
        for case in cases
    ):
        found.append("evals.json 缺少 E136")
    formula = text_of(texts, "evals/verify-formula-typesetting.py")
    if not re.search(r"6\.8\.\d+", formula):
        found.append("verify-formula-typesetting.py 未同步 6.8.x")
    if "6.8.0" in formula:
        found.append("verify-formula-typesetting.py 仍含 6.8.0")
    return found


def mutate(texts, rel, old, new):
    changed = dict(texts)
    changed[rel] = changed.get(rel, "").replace(old, new)
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description="v6.8.1 最细知识点块契约（只读）")
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
    if not isinstance(evals, dict):
        evals = {}
    if not isinstance(evals.get("cases"), list):
        evals = dict(evals, cases=[])

    c = Checker()
    found = problems(texts, evals, deps)
    c.check("1.1 规则文件与版本字段全部符合 ≥v6.8.1", not found, found)

    malformed_ok = True
    malformed_cases = (
        (texts, []),
        (texts, {"cases": None, "applies_to_version": "6.8.2"}),
        (texts, {}),
        (None, evals),
        ({"SKILL.md": None}, evals),
    )
    for malformed_texts, malformed_evals in malformed_cases:
        try:
            malformed_ok = malformed_ok and bool(
                problems(malformed_texts, malformed_evals, deps))
        except Exception:
            malformed_ok = False
    c.check("1.1b 畸形 texts/evals 输入被捕获且不崩溃", malformed_ok)

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
        ("版本回到 6.8.0", mutate(texts, "SKILL.md", "6.8.2", "6.8.0")),
    )
    for name, mutated in mutations:
        got = problems(mutated, evals, deps)
        c.check("2.x mutation 能抓到：" + name, bool(got), got)

    print("verify-v681-docs: {} checks, {} OK, {} FAIL".format(
        c.ok + c.fail, c.ok, c.fail))
    return 0 if c.fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
