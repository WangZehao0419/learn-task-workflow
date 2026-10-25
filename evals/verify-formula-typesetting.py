#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""formula-typesetting 结构契约校验（只读、零网络、幂等）。

只检查结构、章节、交叉引用与评测登记，不检查具体教学效果；版本/日期/run_id
等易漂移字段不在本脚本断言范围内。
"""
import argparse
import json
import sys
from pathlib import Path

CHAPTERS = (
    "## 1. 行内与块级",
    "## 2. 结构与嵌套",
    "## 3. 多步推导",
    "## 4. 物理专节",
    "## 5. 化学专节",
    "## 6. 统计/概率专节",
    "## 7. 代码边界",
    "## 8. 目标宿主验证记录模板",
)
FORMULA_IDS = tuple(f"FORMULA-{i:02d}" for i in range(1, 11))
CASE_REQUIRED_KEYS = (
    "id", "scenario", "kind", "prompt", "fixture", "pass_condition",
    "actual_output", "run_id", "scores", "verdict", "reviewer",
    "review_note", "formula_checks",
)
CASE_NONE_KEYS = ("actual_output", "run_id", "scores", "reviewer", "formula_checks")
RUBRIC_KEYS = ("学科内容", "结构渲染", "教学解释", "复制保真", "边界", "阻断规则")
RESIDUE_KEYWORDS = ("math-typesetting", "task-updates", "U-5.4")


class Checker:
    def __init__(self):
        self.ok = 0
        self.fail = 0

    def check(self, name, cond, detail=""):
        passed = bool(cond)
        self.ok += passed
        self.fail += not passed
        line = f"[{'OK' if passed else 'FAIL'}] {name}"
        if detail and not passed:
            line += f"（{detail}）"
        print(line)


def read_text(path: Path):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def parse_json(raw):
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def group_skill(skill_md, c):
    body = skill_md or ""
    c.check("1.1 SKILL.md 引用 references/formulas.md", "references/formulas.md" in body)
    c.check("1.2 SKILL.md 不再引用旧文件名", ("formula-" + "typesetting.md") not in body)


def group_formulas(formulas, c):
    body = formulas or ""
    c.check("2.1 references/formulas.md 存在且可读", formulas is not None)
    c.check("2.2 含「唯一事实源」（定位声明）", "唯一事实源" in body)
    c.check("2.3 含「不触发」（排除边界）", "不触发" in body)
    pos = -1
    ordered = True
    for i, chapter in enumerate(CHAPTERS):
        idx = body.find(chapter)
        c.check(f"2.{4 + i} 含章节「{chapter}」", idx != -1)
        if idx == -1 or idx < pos:
            ordered = False
        else:
            pos = idx
    c.check("2.12 八个章节标题按序出现", ordered)
    c.check("2.13 含「formula_checks」", "formula_checks" in body)
    c.check("2.14 含「selected_inline」", "selected_inline" in body)
    c.check("2.15 含「selected_block」", "selected_block" in body)
    c.check("2.16 含「mhchem」", "mhchem" in body)


def group_crossrefs(teaching, handout, c):
    t = teaching or ""
    h = handout or ""
    c.check("3.1 teaching.md 引用 formulas.md", "formulas.md" in t)
    c.check("3.2 teaching.md 含「新记号/新操作讲透」", "## 新记号/新操作讲透" in t)
    c.check("4.1 handout.md 含「## 图像可视化双轨」", "## 图像可视化双轨" in h)
    c.check("4.2 handout.md 含「③ 答案」", "③ 答案" in h)
    c.check("4.3 handout.md 含「完整示例」", "完整示例" in h)


def group_evals(evals_data, c):
    data = evals_data if isinstance(evals_data, dict) else {}
    cases = data.get("cases") if isinstance(data.get("cases"), list) else []
    by_id = {case["id"]: case for case in cases
             if isinstance(case, dict) and isinstance(case.get("id"), str)}
    missing = [i for i in FORMULA_IDS if i not in by_id]
    extra = sorted(k for k in by_id if k.startswith("FORMULA-") and k not in FORMULA_IDS)
    c.check("5.1 FORMULA-01–10 共 10 条（无多余）", not missing and not extra,
            f"缺失 {missing} 多余 {extra}")
    present = [i for i in FORMULA_IDS if i in by_id]
    miss_keys = {i: [k for k in CASE_REQUIRED_KEYS if k not in by_id[i]] for i in present}
    c.check("5.2 每条 FORMULA 含全部必需键", all(not v for v in miss_keys.values()),
            str({k: v for k, v in miss_keys.items() if v}))
    bad_verdict = [i for i in present if by_id[i].get("verdict") != "未验证"]
    c.check("5.3 每条 verdict == 未验证", not bad_verdict, str(bad_verdict))
    not_null = [i for i in present if any(by_id[i].get(k) is not None for k in CASE_NONE_KEYS)]
    c.check("5.4 证据字段均为 null", not not_null, str(not_null))
    rubric = data.get("formula_checks_rubric")
    c.check("5.5 formula_checks_rubric 含五维与阻断规则",
            isinstance(rubric, dict) and all(k in rubric for k in RUBRIC_KEYS))
    axes = data.get("grading_axes")
    c.check("5.6 grading_axes 长度为 5", isinstance(axes, list) and len(axes) == 5)
    c.check("5.7 E01 与 E24 条目仍存在", "E01" in by_id and "E24" in by_id)
    f02 = by_id.get("FORMULA-02")
    pc02 = f02.get("pass_condition") if isinstance(f02, dict) else None
    c.check("5.8 FORMULA-02 定义域表述完整",
            isinstance(pc02, str) and all(k in pc02 for k in ("c>0", "c≠0", "(a+b)/c≥0", "不得合并")))


def group_residue(scope, c):
    for i, keyword in enumerate(RESIDUE_KEYWORDS, start=1):
        hits = [name for name, text in scope if keyword in (text or "")]
        c.check(f"6.{i} 范围内文件不含「{keyword}」", not hits, f"命中 {hits}")


def main(argv=None) -> int:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="formulas.md 结构契约校验（只读）")
    parser.add_argument("--skill-root", default=None)
    args = parser.parse_args(argv)
    root = (Path(args.skill_root).resolve() if args.skill_root
            else Path(__file__).resolve().parent.parent)

    skill_md = read_text(root / "SKILL.md")
    formulas = read_text(root / "references" / "formulas.md")
    teaching = read_text(root / "references" / "teaching.md")
    handout = read_text(root / "references" / "handout.md")
    evals_raw = read_text(root / "evals" / "evals.json")

    scope = [("SKILL.md", skill_md), ("evals/evals.json", evals_raw)]
    refs_dir = root / "references"
    if refs_dir.is_dir():
        for path in sorted(refs_dir.glob("*.md")):
            scope.append((f"references/{path.name}", read_text(path)))

    c = Checker()
    group_skill(skill_md, c)
    group_formulas(formulas, c)
    group_crossrefs(teaching, handout, c)
    group_evals(parse_json(evals_raw), c)
    group_residue(scope, c)
    total = c.ok + c.fail
    print(f"verify-formula-typesetting: {total} checks, {c.ok} OK, {c.fail} FAIL")
    return 1 if c.fail else 0


if __name__ == "__main__":
    sys.exit(main())
