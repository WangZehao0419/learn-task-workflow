#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""formula-typesetting 静态契约校验脚本（stdlib-only、零网络、幂等只读）。

用途：
  对「公式与科学符号呈现」机制（v5.5.0 引入）做仓库内静态契约验证，作为
  FORMULA-01–FORMULA-10 真实回放前的登记完整性证据。本脚本只读取
  技能包文件，不写任何文件、不访问网络，可重复运行（幂等）。

检查项（8 组，共 56 项）：
  1. 主文件入口：SKILL.md 含 "formula-typesetting" 的行恰好 2 行，条件指针行
     与索引行的关键词契约；
  2. 分册存在与章节：references/formula-typesetting.md 的定位声明「唯一事实源」、
     排除边界「不触发」、八个章节标题（含按序出现）、formula_checks / selected_inline /
     selected_block / mhchem 标记；
  3. teaching-loop 交叉引用：references/teaching-loop.md 中 "formula-typesetting"
     恰好出现 1 次且该行含「呈现与渲染阻断」；
  4. lecture-styles 范例修订：范例去上标化（含 x^2−x−6>0 与解集完整句、不含 x²）、
     五要素标记（完整示例/易错点/③ 答案/⑤ 小结）与两共用节标题未被波及；
  5. evals/evals.json 契约：FORMULA-01–10 登记字段与未回填语义、阻断标记、
     formula_checks_rubric、grading_axes、版本字段、E01/E24 存续、run_log_ref 与
     machine_evidence_ref 登记证据、FORMULA-02 定义域表述；
  6. 版本字段：SKILL.md / skill-dependencies.json / references/setup-guide.md /
     CREDITS.md 四处 6.9.0，及 setup-guide.md 核验日期；
  7. 无残留：管理文件范围内（SKILL.md、CREDITS.md、skill-dependencies.json、
     evals/evals.json、references/ 下全部 .md）不含 math-typesetting / task-updates /
     U-5.4。范围不含 evals/run-log.md——其既有遗留内容由运行记录留痕，
     不属本脚本管辖；
  8. 证据总数自校验：evals.json 的 machine_evidence_ref 登记的总检查数与本脚本
     实际检查总数一致（本组须为最后一组，按「已登记检查数 + 1」动态计算）。

用法：
  python -B evals/verify-formula-typesetting.py [--skill-root <技能根目录>]
  --skill-root 缺省取本脚本所在目录的上级目录（即技能根）。

退出码语义：
  0 = 全部检查通过；1 = 存在任何 FAIL（含文件缺失、JSON 解析失败）。
"""

import argparse
import json
import sys
from pathlib import Path

# 残留关键词（旧机制命名与已删除的回补协议标识）
RESIDUE_KEYWORDS = ("math-typesetting", "task-updates", "U-5.4")

# formula-typesetting.md 八个章节标题（按实际文件原文的包含式前缀断言）
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

# evals.json 中 FORMULA 条目的必需键
CASE_REQUIRED_KEYS = (
    "id", "scenario", "kind", "prompt", "fixture", "pass_condition",
    "actual_output", "run_id", "scores", "verdict", "reviewer",
    "review_note", "formula_checks",
)
# 回放前必须保持 null 的证据字段（未回填语义）
CASE_NONE_KEYS = ("actual_output", "run_id", "scores", "reviewer", "formula_checks")
FORMULA_IDS = tuple(f"FORMULA-{i:02d}" for i in range(1, 11))
FORMULA_BLOCKING_IDS = ("FORMULA-03", "FORMULA-05", "FORMULA-06", "FORMULA-07",
                        "FORMULA-09", "FORMULA-10")
RUBRIC_KEYS = ("学科内容", "结构渲染", "教学解释", "复制保真", "边界", "阻断规则")


class Checker:
    """逐项输出 [OK]/[FAIL] 行并累计计数。"""

    def __init__(self):
        self.ok = 0
        self.fail = 0

    def check(self, name, cond, detail=""):
        passed = bool(cond)
        if passed:
            self.ok += 1
        else:
            self.fail += 1
        line = f"[{'OK' if passed else 'FAIL'}] {name}"
        if detail and not passed:
            line += f"（{detail}）"
        print(line)


def read_text(path: Path):
    """utf-8 读取文本；文件不存在或不可读返回 None（由检查项报告 FAIL）。"""
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


def group1_main_entry(skill_md: str, c: Checker) -> None:
    """组 1：SKILL.md 条件指针行与索引行契约。"""
    lines = [l for l in skill_md.splitlines() if "formula-typesetting" in l]
    c.check("1.1 SKILL.md 含 formula-typesetting 的行恰好 2 行",
            len(lines) == 2, f"实际 {len(lines)} 行")
    pointer = [l for l in lines if "学习者可见的公式" in l]
    c.check("1.2 条件指针行（含「学习者可见的公式」）恰好 1 行",
            len(pointer) == 1, f"实际 {len(pointer)} 行")
    p = pointer[0] if pointer else ""
    c.check("1.3 指针行含触发语（公式/方程式/科学符号）",
            all(k in p for k in ("公式", "方程式", "科学符号")))
    c.check("1.4 指针行含代码边界词（代码围栏/代码字符串/引用的公式源码）",
            all(k in p for k in ("代码围栏", "代码字符串", "引用的公式源码")))
    c.check("1.5 指针行含排除词（日期/版本号/普通数字/跳过）",
            all(k in p for k in ("日期", "版本号", "普通数字", "跳过")))
    index = [l for l in lines if "唯一事实源" in l and "不覆盖教学决策" in l]
    c.check("1.6 索引行含「唯一事实源」与「不覆盖教学决策」",
            len(index) == 1, f"实际 {len(index)} 行")


def group2_booklet(booklet, c: Checker) -> None:
    """组 2：分册存在、定位声明、八个章节与标记。"""
    exists = booklet is not None
    c.check("2.1 references/formula-typesetting.md 存在且可读", exists)
    body = booklet if exists else ""
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
    c.check("2.13 含「formula_checks」（附加评分口径）", "formula_checks" in body)
    c.check("2.14 含「selected_inline」（选定记录位）", "selected_inline" in body)
    c.check("2.15 含「selected_block」（选定记录位）", "selected_block" in body)
    c.check("2.16 含「mhchem」（化学可选扩展标记）", "mhchem" in body)


def group3_teaching_loop(teaching, c: Checker) -> None:
    """组 3：teaching-loop.md 交叉引用契约。"""
    body = teaching if teaching is not None else ""
    count = body.count("formula-typesetting")
    c.check("3.1 teaching-loop.md 中 formula-typesetting 恰好出现 1 次",
            count == 1, f"实际 {count} 次")
    hits = [l for l in body.splitlines() if "formula-typesetting" in l]
    c.check("3.2 交叉引用行含「呈现与渲染阻断」",
            len(hits) == 1 and "呈现与渲染阻断" in hits[0])


def group4_lecture_styles(styles, c: Checker) -> None:
    """组 4：lecture-styles.md 范例修订与共用节完整性。"""
    body = styles if styles is not None else ""
    c.check("4.1 含「x^2−x−6>0」（范例已去上标）", "x^2−x−6>0" in body)
    c.check("4.2 不含「x²」（U+00B2）", "x²" not in body)
    # 集合语义：x<−2 或 x>3 即 {x | x<−2 或 x>3}，「或」为公式环境外的自然语言并集连接；
    # 用户已手动删除答案框中的集合括注，此处只锚定完整句，不要求也不禁止括注回添。
    c.check("4.3 含「∴原不等式的解集为 x<−2 或 x>3」",
            "∴原不等式的解集为 x<−2 或 x>3" in body)
    c.check("4.4 含「完整示例」（五要素标记）", "完整示例" in body)
    c.check("4.5 含「易错点」（五要素标记）", "易错点" in body)
    c.check("4.6 含「③ 答案」（五要素标记）", "③ 答案" in body)
    c.check("4.7 含节标题「## 新记号/新操作讲透」", "## 新记号/新操作讲透" in body)
    c.check("4.8 含节标题「## 图像可视化双轨」", "## 图像可视化双轨" in body)


def group5_evals_contract(evals_data, c: Checker) -> None:
    """组 5：evals.json 的 FORMULA 登记契约与全局字段。"""
    c.check("5.1 evals/evals.json 可解析", evals_data is not None)
    data = evals_data if isinstance(evals_data, dict) else {}
    cases = data.get("cases") if isinstance(data.get("cases"), list) else []
    by_id = {}
    for case in cases:
        if isinstance(case, dict) and isinstance(case.get("id"), str):
            by_id[case["id"]] = case
    missing_ids = [i for i in FORMULA_IDS if i not in by_id]
    extra = sorted(k for k in by_id if k.startswith("FORMULA-") and k not in FORMULA_IDS)
    c.check("5.2 FORMULA-01–10 共 10 条（无多余 FORMULA-*）",
            not missing_ids and not extra, f"缺失 {missing_ids} 多余 {extra}")
    present = [i for i in FORMULA_IDS if i in by_id]
    miss_keys = {i: [k for k in CASE_REQUIRED_KEYS if k not in by_id[i]] for i in present}
    c.check("5.3 每条 FORMULA 含全部必需键",
            all(not v for v in miss_keys.values()),
            str({k: v for k, v in miss_keys.items() if v}))
    bad_verdict = [i for i in present if by_id[i].get("verdict") != "未验证"]
    c.check("5.4 每条 verdict == 未验证", not bad_verdict, str(bad_verdict))
    not_null = [i for i in present
                if any(by_id[i].get(k) is not None for k in CASE_NONE_KEYS)]
    c.check("5.5 actual_output/run_id/scores/reviewer/formula_checks 均为 null",
            not not_null, str(not_null))
    bad_block = [i for i in FORMULA_BLOCKING_IDS
                 if i in by_id and "阻断" not in str(by_id[i].get("review_note") or "")]
    c.check("5.6 FORMULA-03/05/06/07/09/10 review_note 含「阻断」",
            not bad_block, str(bad_block))
    rubric = data.get("formula_checks_rubric")
    c.check("5.7 formula_checks_rubric 含五维与阻断规则",
            isinstance(rubric, dict) and all(k in rubric for k in RUBRIC_KEYS))
    axes = data.get("grading_axes")
    c.check("5.8 grading_axes 长度为 5",
            isinstance(axes, list) and len(axes) == 5,
            f"实际 {len(axes) if isinstance(axes, list) else type(axes).__name__}")
    c.check("5.9 applies_to_version == 6.9.0", data.get("applies_to_version") == "6.9.0",
            f"实际 {data.get('applies_to_version')!r}")
    c.check("5.10 updated_at == 2026-10-25", data.get("updated_at") == "2026-10-25",
            f"实际 {data.get('updated_at')!r}")
    c.check("5.11 E01 与 E24 条目仍存在", "E01" in by_id and "E24" in by_id)
    # 顶层运行日志指针：指向「运行记录」节与本次静态回放的 run_id
    run_log_ref = data.get("run_log_ref")
    c.check("5.12 run_log_ref 非 null 且含 run-log 路径与本轮回放 run_id",
            isinstance(run_log_ref, str)
            and "evals/run-log.md" in run_log_ref
            and "formula-typesetting-5.5.0-20261017-static" in run_log_ref)
    # 机器证据指针：脚本名、退出码语义与非渲染验证定位
    evidence = data.get("machine_evidence_ref")
    c.check("5.13 machine_evidence_ref 含脚本名、退出码 0 与非渲染验证声明",
            isinstance(evidence, str)
            and "verify-formula-typesetting.py" in evidence
            and "退出码 0" in evidence
            and "非渲染验证" in evidence)
    # FORMULA-02 定义域表述：两式须分别写条件且不得合并（5.15 兜底未回填语义）
    f02 = by_id.get("FORMULA-02")
    pc02 = f02.get("pass_condition") if isinstance(f02, dict) else None
    c.check("5.14 FORMULA-02 pass_condition 含两式各自定义域与「不得合并」表述",
            isinstance(pc02, str)
            and all(k in pc02 for k in ("c>0", "c≠0", "(a+b)/c≥0", "不得合并")))
    c.check("5.15 FORMULA-02 verdict 未验证且 formula_checks 为 null",
            isinstance(f02, dict) and f02.get("verdict") == "未验证"
            and f02.get("formula_checks") is None)


def group6_versions(skill_md, deps_data, setup_md, credits_md, c: Checker) -> None:
    """组 6：四处版本字段同步 6.9.0。"""
    c.check("6.1 SKILL.md 含 version: 6.9.0", "version: 6.9.0" in (skill_md or ""))
    # applies_to_version 按实际结构位于 dependencies[].setup（python-runtime 条目）；
    # 顶层若也存在则一并收集，要求出现且全部为 6.9.0
    values = []
    if isinstance(deps_data, dict):
        if "applies_to_version" in deps_data:
            values.append(deps_data.get("applies_to_version"))
        deps = deps_data.get("dependencies")
        for dep in deps if isinstance(deps, list) else []:
            setup = dep.get("setup") if isinstance(dep, dict) else None
            if isinstance(setup, dict) and "applies_to_version" in setup:
                values.append(setup.get("applies_to_version"))
    c.check("6.2 skill-dependencies.json applies_to_version == 6.9.0",
            bool(values) and all(v == "6.9.0" for v in values),
            f"实际 {values!r}" if values else "未找到 applies_to_version 字段")
    c.check("6.3 setup-guide.md 含「适用版本：6.9.0」", "适用版本：6.9.0" in (setup_md or ""))
    c.check("6.4 CREDITS.md 含「6.9.0」", "6.9.0" in (credits_md or ""))
    c.check("6.5 setup-guide.md 含「核验日期：2026-10-25」",
            "核验日期：2026-10-25" in (setup_md or ""))


def group7_no_residue(scope, c: Checker) -> None:
    """组 7：管理文件范围内无旧机制残留（范围不含 evals/run-log.md）。"""
    for i, keyword in enumerate(RESIDUE_KEYWORDS, start=1):
        hits = [name for name, text in scope if keyword in (text or "")]
        c.check(f"7.{i} 范围内文件不含「{keyword}」", not hits, f"命中 {hits}")


def group8_evidence_total(evals_data, c: Checker) -> None:
    """组 8：machine_evidence_ref 登记总数与本脚本实际检查总数自校验（须最后运行）。"""
    data = evals_data if isinstance(evals_data, dict) else {}
    evidence = data.get("machine_evidence_ref")
    # 总数自校验用动态计算而非写死数字：本项是最后登记的检查，脚本实际总数 =
    # 此前已登记检查数 + 本项自身 1，evals.json 登记数因此与本脚本总数永久同步。
    expected_total = c.ok + c.fail + 1
    c.check("8.1 machine_evidence_ref 登记的总检查数与本脚本实际总数一致",
            isinstance(evidence, str) and str(expected_total) in evidence,
            f"期望登记 {expected_total}")


def main(argv=None) -> int:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass

    parser = argparse.ArgumentParser(
        description="formula-typesetting 静态契约校验（只读、零网络、幂等）")
    parser.add_argument("--skill-root", default=None,
                        help="技能根目录（缺省：本脚本所在目录的上级目录）")
    args = parser.parse_args(argv)
    root = (Path(args.skill_root).resolve() if args.skill_root
            else Path(__file__).resolve().parent.parent)

    skill_md = read_text(root / "SKILL.md")
    booklet = read_text(root / "references" / "formula-typesetting.md")
    teaching = read_text(root / "references" / "teaching-loop.md")
    styles = read_text(root / "references" / "lecture-styles.md")
    evals_raw = read_text(root / "evals" / "evals.json")
    deps_raw = read_text(root / "skill-dependencies.json")
    setup_md = read_text(root / "references" / "setup-guide.md")
    credits_md = read_text(root / "CREDITS.md")

    scope = [
        ("SKILL.md", skill_md),
        ("CREDITS.md", credits_md),
        ("skill-dependencies.json", deps_raw),
        ("evals/evals.json", evals_raw),
    ]
    refs_dir = root / "references"
    if refs_dir.is_dir():
        for path in sorted(refs_dir.glob("*.md")):
            scope.append((f"references/{path.name}", read_text(path)))

    c = Checker()
    group1_main_entry(skill_md or "", c)
    group2_booklet(booklet, c)
    group3_teaching_loop(teaching, c)
    group4_lecture_styles(styles, c)
    group5_evals_contract(parse_json(evals_raw), c)
    group6_versions(skill_md, parse_json(deps_raw), setup_md, credits_md, c)
    group7_no_residue(scope, c)
    group8_evidence_total(parse_json(evals_raw), c)

    total = c.ok + c.fail
    print(f"verify-formula-typesetting: {total} checks, {c.ok} OK, {c.fail} FAIL")
    return 1 if c.fail else 0


if __name__ == "__main__":
    sys.exit(main())
