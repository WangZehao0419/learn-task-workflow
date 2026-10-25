#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-v682-docs.py - v6.8.2 对话轮呈现与语气契约（stdlib-only、只读）。

检查「对话轮呈现标记」「讲授与反馈语气契约」是否写入规则文件、
版本字段是否同步、指针是否齐全，并用 mutation 证明检查器不是空转。
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


def parse_version(value):
    try:
        return tuple(int(part) for part in str(value).split("."))
    except ValueError:
        return ()


def version_in(text, pattern):
    m = re.search(pattern, text or "")
    return m.group(1) if m else ""


RULE_FILES = (
    "SKILL.md",
    "references/lecture-styles.md",
    "references/teaching-loop.md",
    "references/phases-and-gates.md",
    "references/data-and-recovery.md",
    "references/redlines.md",
)

POINTERS = {
    "SKILL.md": ("对话轮呈现标记",),
    "references/teaching-loop.md": ("对话轮呈现标记",),
    "references/phases-and-gates.md": ("对话轮呈现标记",),
    "references/data-and-recovery.md": ("S3 讲授呈现", "重点加粗、结论先行"),
}

LABELS = ("**结论：**", "**易错：**", "**检验：**")
TITLES = ("对话轮呈现标记", "讲授与反馈语气契约")
STYLE_TERMS = (
    "一段一义", "五段落位", "明确通用偏好", "任务级偏好",
    "顺序固定", "正文在结论与易错之间", "定位放结论后的第一句正文",
    "不按下列顺序输出", "不使用 Markdown 标题",
    "公式独立成行", "下划线", "彩色", "emoji", "分隔线",
)
DELETE_TERMS = ("必要推导", "完整示例", "1 句确认", "复述证据")
VOICE_TERMS = ("专业严谨", "高效务实", "直言不讳", "不嘲讽", "不确定")


def dependency_versions(deps_text):
    if isinstance(deps_text, dict):
        data = deps_text
    else:
        try:
            data = json.loads(deps_text or "{}")
        except (ValueError, TypeError):
            return []
    versions = []
    if isinstance(data, dict):
        if "applies_to_version" in data:
            versions.append(data.get("applies_to_version"))
        for dep in data.get("dependencies", []):
            setup = dep.get("setup") if isinstance(dep, dict) else None
            if isinstance(setup, dict) and "applies_to_version" in setup:
                versions.append(setup.get("applies_to_version"))
    return versions


def problems(texts, evals, deps):
    found = []
    if not isinstance(evals, dict):
        evals = {}
    cases = evals.get("cases")
    if not isinstance(cases, list):
        cases = []
    styles = text_of(texts, "references/lecture-styles.md")

    for label in LABELS:
        if label not in styles:
            found.append("lecture-styles 缺少标签「{}」".format(label))
    for title in TITLES:
        if title not in styles:
            found.append("lecture-styles 缺少标题「{}」".format(title))
    for term in STYLE_TERMS:
        if term not in styles:
            found.append("lecture-styles 缺少呈现规则「{}」".format(term))
    for term in DELETE_TERMS:
        if term not in styles:
            found.append("lecture-styles 删除测试缺少「{}」".format(term))
    if "锚点行" not in styles or "`结论：` / `检验：`" not in styles:
        found.append("压缩出口未保留锚点与结论/检验")
    for term in VOICE_TERMS:
        if term not in styles:
            found.append("语气契约缺少「{}」".format(term))
    if "发出前 3 问" not in styles:
        found.append("缺少「发出前 3 问」")

    for rel, needles in POINTERS.items():
        for needle in needles:
            if needle not in text_of(texts, rel):
                found.append("{} 缺少指针「{}」".format(rel, needle))

    for rel in RULE_FILES:
        if rel != "references/lecture-styles.md" and "**结论：**" in text_of(texts, rel):
            found.append("{} 复制了呈现标签，不是单一事实源".format(rel))

    exact = (6, 8, 2)
    skill_version = version_in(
        text_of(texts, "SKILL.md"), r"version:\s*(\d+\.\d+\.\d+)")
    if parse_version(skill_version) != exact:
        found.append("SKILL.md version 不是 6.8.2")
    setup_version = version_in(
        text_of(texts, "references/setup-guide.md"),
        r"适用版本：(\d+\.\d+\.\d+)")
    if parse_version(setup_version) != exact:
        found.append("setup-guide 适用版本不是 6.8.2")
    dep_versions = dependency_versions(deps)
    if not dep_versions or any(parse_version(v) != exact for v in dep_versions):
        found.append("skill-dependencies applies_to_version 不是 6.8.2")
    credits_version = version_in(
        text_of(texts, "CREDITS.md"), r"当前版本说明\*\*：(\d+\.\d+\.\d+)")
    if parse_version(credits_version) != exact:
        found.append("CREDITS 当前版本说明不是 6.8.2")
    if parse_version(evals.get("applies_to_version")) != exact:
        found.append("evals.json applies_to_version 不是 6.8.2")
    formula = text_of(texts, "evals/verify-formula-typesetting.py")
    if "6.8.2" not in formula or "6.8.1" in formula:
        found.append("verify-formula-typesetting.py 未同步 6.8.2")

    case = next(
        (c for c in cases if isinstance(c, dict) and c.get("id") == "E137"),
        None)
    if not isinstance(case, dict):
        found.append("evals.json 缺少 E137")
    else:
        condition = str(case.get("pass_condition", ""))
        if case.get("kind") != "human":
            found.append("E137 kind 不是 human")
        if case.get("verdict") != "未验证":
            found.append("E137 verdict 不是未验证")
        for needle in ("**结论：**", "**易错：**", "**检验：**", "下划线"):
            if needle not in condition:
                found.append("E137 pass_condition 缺少「{}」".format(needle))

    if "**结论：**" in text_of(texts, "scripts/verify_explanation.py"):
        found.append("verify_explanation.py 意外包含呈现标签（范围应只查讲义）")
    return found


def mutate(texts, rel, old, new):
    changed = dict(texts)
    changed[rel] = changed.get(rel, "").replace(old, new)
    return changed


def flagged(texts, evals, deps):
    try:
        return bool(problems(texts, evals, deps))
    except Exception:
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="v6.8.2 对话轮呈现与语气契约（只读）")
    parser.add_argument("--skill-root", default=None)
    args = parser.parse_args(argv)

    root = (
        Path(args.skill_root).resolve()
        if args.skill_root
        else Path(__file__).resolve().parents[1]
    )
    rels = list(RULE_FILES) + [
        "references/setup-guide.md",
        "CREDITS.md",
        "evals/verify-formula-typesetting.py",
        "scripts/verify_explanation.py",
    ]
    texts = {rel: read(root, rel) for rel in rels}
    deps = read(root, "skill-dependencies.json")
    try:
        evals = json.loads(read(root, "evals/evals.json") or "{}")
    except ValueError as exc:
        evals = {}
        print("[FAIL] evals.json 不是合法 JSON：{}".format(exc))

    c = Checker()
    found = problems(texts, evals, deps)
    c.check("1.1 规则、指针与版本字段全部符合 v6.8.2", not found, found)

    mutations = (
        ("删易错标签", mutate(
            texts, "references/lecture-styles.md", "**易错：**", "")),
        ("下划线改波浪线", mutate(
            texts, "references/lecture-styles.md", "下划线", "波浪线")),
        ("SKILL 复制结论标签", mutate(
            texts, "SKILL.md", "对话轮呈现标记",
            "对话轮呈现标记（**结论：** 先结论后展开）")),
        ("版本回到 6.8.1", mutate(
            texts, "SKILL.md", "6.8.2", "6.8.1")),
        ("删发出前 3 问", mutate(
            texts, "references/lecture-styles.md", "发出前 3 问", "")),
        ("删五段落位", mutate(
            texts, "references/lecture-styles.md", "五段落位", "")),
    )
    for name, mutated in mutations:
        got = problems(mutated, evals, deps)
        c.check("2.x mutation 能抓到：" + name, bool(got), got)

    deps_missing = '{"dependencies": []}'
    c.check("2.x mutation 能抓到：依赖清单缺版本",
            bool(problems(texts, evals, deps_missing)),
            problems(texts, evals, deps_missing))

    malformed = (
        (texts, [], deps),
        (texts, {"cases": None, "applies_to_version": "6.8.2"}, deps),
        (texts, evals, {"dependencies": []}),
        (None, evals, deps),
        ({"references/lecture-styles.md": None}, evals, deps),
    )
    c.check("2.x malformed 输入被捕获且不崩溃",
            all(flagged(tx, ev, dp) for tx, ev, dp in malformed))

    print("verify-v682-docs: {} checks, {} OK, {} FAIL".format(
        c.ok + c.fail, c.ok, c.fail))
    return 0 if c.fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
