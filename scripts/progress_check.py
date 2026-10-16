#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""progress_check.py - 进度文件校验与落盘证据验证（确定性，stdlib-only）。

用途：技能在跨阶段推进前调用，做四件事：
  1) 校验 progress.md 的必填字段与枚举合法性；
  2) 验证「已掌握（[x]/[X]）」小节是否都有对应的 exercises/ 判分记录（落盘证据）；
  3) 覆盖完整性只读告警（v2.3，warning 非 error，不阻断旧任务）：
     W-NO-COVERAGE-AUDIT（结课/已完成缺「暂缓与范围外」区块或缺审计记录）、
     W-UNPARSED-HOLD（暂缓条目畸形计 0）、
     W-EMPTY-EVIDENCE（判分记录文件存在但内容无「判分/作答」结构——空文件或模板），
     并在 coverage 字段回显 hold_count / excluded_count / hold_unparsed / route_undone / audit_record_found。
  4) KP 清单只读告警（v2.4，全部 warning 非 error，不阻断旧任务；仅 progress.md
     记有「知识清单」指针的任务才触发，旧任务零触发）：
     W-KP-STATE-MISMATCH（小节已掌握 × 清单该节存在无摸底括注的「未讲」KP；
     带「已会」括注行豁免）、
     W-UNPARSED-KP（清单行畸形/状态非法/前置引用不存在/重复编号/覆盖范围行畸形或写法偏差，
     不计入摘要计数）、
     W-KP-SUMMARY-MISMATCH（覆盖摘要行计数与逐行实际不符；rows 空但摘要行有值照常核对）、
     W-KP-LIST-MISSING（指针存在但文件不存在或不可读）、
     W-KP-HOLD-CROSS（清单摘要暂缓数 ≠ 暂缓区块可比条目数（处置为暂缓的条目）/ 清单排除数 ≠ 处置为排除的条目数；
     「滚雪球候选」等设计性范围外条目与排除条目均不计入暂缓比对基数）。

用法：
    python progress_check.py <任务目录>              # 历史/日常校验（warning 不阻断旧任务）
    python progress_check.py <任务目录> --release    # 放行校验：本次新增掌握/结课/跨阶段前的严格检查
    python progress_check.py <任务目录> --release --proposed-phase 已完成
    python progress_check.py <任务目录> --release --staged <候选progress快照> [--changed-lessons 2,3]
    python progress_check.py --selftest

--release 模式（本次放行校验，与历史检查分离）：
    · **结构化作答闸口（R01/R15）**：判分记录须**同题三要素配对**——真实学员作答（非占位）
      + 可判定结果（正确性/调度档，**精确枚举**） + 独立性枚举（独立 / 提示后·提示②–④ / 未测）；
      缺失或 `未测` 一律**不推为独立**；零条「有作答且有判定」→ E-NO-GRADED-ATTEMPT；
      全错 → E-ALL-FAILED；仅提示后对 → E-HINT-ONLY；缺独立性 → E-NO-INDEPENDENCE；
      低于 2/3 → E-GATE-THRESHOLD；同 attempt_id 冲突 → E-ATTEMPT-CONFLICT。
    · **逐关键能力独立通过（R16）**：声明「关键能力」区块时每项须至少一次独立正确 →
      否则 E-KEY-ABILITY-UNMET（关键项错不被简单题抵消）。
    · **复述 / 目标型证据（R17）**：复述清单按**勾选项**计数（≥2，兼容同行多勾选）；
      「操作作品验收」类区块含 ≥2 个已勾选核验项可**等价替代**；二者皆无 → E-NO-RESTATEMENT。
    · 空文件/仅含模板字样的判分记录 → E-EMPTY-EVIDENCE。
    · **阶段证据按内容而非文件名（R14）**：S2 须有**可用**的 00 摸底（E-NO-DIAGNOSTIC）；
      结课/已完成须有**可用**的 99 综合测验（缺文件 E-NO-FINAL-EXAM、空文件 E-FINAL-NO-EVIDENCE、
      未达目标线 E-FINAL-BELOW-TARGET、纳入 KP 未覆盖 E-FINAL-BLUEPRINT-GAP）；
      空或不可解析（含混合不可解析）路线 → E-NO-ROUTE-STRICT；未勾选小节 → E-ROUTE-UNDONE；
      清单纳入口径下仍有「未讲」关键能力 KP → E-CORE-UNLEARNED。
    · **候选差分覆盖（R13）**：给 `--staged` 时由**磁盘原状态与候选状态的真实差集**推导新增掌握；
      `--changed-lessons` 必须覆盖该差集（否则 E-UNDECLARED-CHANGES）、编号须属候选已掌握
      （否则 E-CHANGED-SET-INVALID）；未声明时默认只校验差集。
    · **确定性证据选取（R18）**：候选可写 `- 本次证据：<文件名>` 显式指定；否则按
      「文件名日期最新 → 字典序最大」确定性选定（多份 real 时给 W-MULTI-EVIDENCE），
      结果不随目录枚举顺序变化；输出回显 `evidence_used`。
    · **稳定 ID 与游标（R22）**：路线 lesson_id 须唯一（E-LESSON-ID-DUP）；暂缓/排除对账按
      **归一化后的对象 ID 集合**比较（`KP-90-1` ≡ `KP-90-01`）；游标「待回应」须同时命中
      **存在的文件与题号**、「最后提交」须指向**真实作答事件**（否则 E-CURSOR-DANGLING）。
    · 「起点」合法枚举 {零基础, 入门, 进阶}，非法 → E-ENUM-START；
    · 「复习来源阶段」必须为合法枚举（逐节学习/结课/已完成/无），任意字符串被拒（E-REVIEW-ORIGIN）。

拟提交状态（R02，先校验后提交）：
    · 严格闸口校验的是**拟提交目标状态**：`--proposed-phase` 覆盖目标阶段、`--staged` 传
      候选 progress 快照；两者皆缺时只校验当前落盘状态，输出 proposed_state_supplied:false
      + W-NO-PROPOSED-STATE，明示「目标变更未被校验」。
    · `--changed-lessons` 为显式增量机制：只校验本次新增掌握的小节，旧资料不阻断无关新节；
      输出 checked_lessons 回显本次严格校验覆盖的小节号。

历史模式保留 warning 级、不阻断旧任务（旧数据只有真实性告警时仍可继续教学）。

退出码：0 通过 / 1 校验不通过 / 2 用法错误
"""

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

# 同步维护提示：本三组枚举与 task_index.py 顶部同名枚举必须同步修改；
# ENUM_KP_STATUS / parse_kp_row 与 kp_sort.py 的同名枚举与解析函数必须同步修改；
# hold_entry_malformed / hold_disposition_excluded 与 task_index.py 的同名函数（本文件另有 hold_is_designed）必须同步修改。
ENUM_PHASE = ["接料建档", "诊断摸底", "计划确认中", "逐节学习", "复习巩固", "结课", "已完成"]
ENUM_TYPE = ["知识型", "技能型", "备考型", "材料型"]
ENUM_FAMILY = ["数学类", "编程类", "语言类", "理论概念类", "记忆密集类"]
# 「复习来源阶段」返回点枚举（F04：已完成任务可复习并返回「已完成」；任意字符串被拒）
ENUM_REVIEW_FROM = ["逐节学习", "结课", "已完成"]

# 全程必填；「起点」由 S1 产出，仅在 S1 诊断结束（离开 S0/S1）后必填（见 check()）。
BASE_REQUIRED = ["当前阶段", "类型", "学科族", "目标"]
FIELD_RE = re.compile(r"^-\s*([^：:]+)[：:]\s*(.*)$")
# 已完成勾选：x / X 均识别
ROUTE_RE = re.compile(r"^-\s*\[([xX ])\]\s*(\d+)\.\s*(.*)$")
CHECKBOX_RE = re.compile(r"^-\s*\[[^\]]*\]")  # 形如 - [..] 的勾选语法（用于发现未解析行）
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
# 「暂缓与范围外」区块（v2.3）条目应含的三段（自由文本 + 竖线分段，不做枚举硬校验）
HOLD_KEYS = ("来源", "处置", "触发条件")

# ── 判分证据结构判定（F03：区分真实作答证据与空文件/模板）──
EVIDENCE_HEAD_RE = re.compile(r"(判分|作答)")
# 结果标记：档位词 / 对错 / 正确率 / 得分 / 勾叉 / 分数比值
GRADE_ROW_RE = re.compile(
    r"(Good|Easy|Hard|Again|对|错|正确|错误|得分|满分|正确率|✓|✗|√|×|\d+\s*/\s*\d+)")
# 占位符：模板里的 <…>、待填、占位、示例标记——落在占位行上的结果不计为真实证据
PLACEHOLDER_RE = re.compile(r"<[^>]*>|待填|占位|模板|示例")


def evidence_strength(text):
    """判分记录文本的证据强度：real（真实作答判分）/ template（仅模板占位）/ empty（无结构）。

    real     —— 含「判分/作答」段，且存在**不含占位符**的结果行；
    template —— 含「判分/作答」段，但结果只出现在占位行（或只有标题、无结果）；
    empty    —— 无「判分/作答」段（空文件或无关内容）。
    历史模式对 template/empty 出 W-EMPTY-EVIDENCE（warning）；放行模式升级为 E-EMPTY-EVIDENCE。
    """
    if not EVIDENCE_HEAD_RE.search(text):
        return "empty"
    for line in text.splitlines():
        if GRADE_ROW_RE.search(line) and not PLACEHOLDER_RE.search(line):
            return "real"
    return "template"


# ── 放行模式结构化作答与闸口判定（R01：关键词出现 ≠ 真实且达标的作答）──
# 旧实现只查「全文含作答/判分 + 任一非占位评分词」，导致无学员答案、全部答错、
# 只有标题、无复述清单等均被放行。以下把判分记录解析为**结构化作答行**再判闸口。
ENUM_START = ["零基础", "入门", "进阶"]
DIAG_PREFIXES = ("00-", "0-")   # S1 摸底证据专号（exercises/00-摸底-<日期>.md）
FINAL_PREFIXES = ("99-",)       # S5 结课综合测验专号（exercises/99-结课综合测验-<日期>.md）
GATE_RATIO = 2.0 / 3.0          # S3 小节验收默认通过线：≥2/3
ANSWER_RE = re.compile(r"作答[「\"'（(]([^」\"'）)]*)[」\"'）)]")
ALT_ANSWER_RE = re.compile(r"答案[：:]\s*([^｜|，,]+)")
RESTATE_RE = re.compile(r"复述")
ARTIFACT_HEAD_RE = re.compile(r"作品|操作|产出|交付|实现")
RESTATE_FAIL_TOKENS = ("未通过", "不通过", "未达标")
RESTATE_PASS_TOKENS = ("通过", "达标", "全对")
CHECKED_RE = re.compile(r"\[[xX]\]")            # 勾选**项**（不是行数）：同行多勾选各计一项
INDEP_RE = re.compile(r"独立性\s*[=＝]\s*([^｜|，,]+)")
CORRECT_RE = re.compile(r"正确性\s*[=＝]\s*([^｜|，,]+)")
GRADE_RE = re.compile(r"(?:调度档|档位|结果|档)\s*[=＝]\s*([^｜|，,]+)")
# ↑ 取值一律截到下一个 ｜/|/,/， 分隔符为止：`\S+` 会把 `错｜独立性=独立｜Again` 整段吞掉（V03）
ATTEMPT_ID_ROW_RE = re.compile(r"attempt_id\s*[=＝]\s*([A-Za-z0-9_\-]+)")
ATTEMPT_ID_ANY_RE = re.compile(r"(?:attempt_id|evt)\s*[=＝]\s*([A-Za-z0-9_\-]+)")
ABILITY_TAG_RE = re.compile(r"能力\s*[=＝]\s*([Cc]\d+)")
KEY_ABILITY_HEAD_RE = re.compile(r"关键能力")
KEY_ABILITY_ROW_RE = re.compile(r"^\s*-\s*([Cc]\d+)\s*[：:]\s*(.+?)\s*$")
KEY_ITEM_FLAG = "关键项"
QNUM_RE = re.compile(r"题\s*(\d+)")
DATE_IN_NAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
EVIDENCE_REF_RE = re.compile(r"本次证据[：:]\s*(\S+)")
KP_ID_ANY_RE = re.compile(r"KP-(\d+)-(\d+)")
# 正确性/独立性均按**精确枚举**解析（V03）：`正确性=不对` 不得被子串 `对` 误判为正确；
# 独立性缺失或 `未测` 均**不得推为独立**。
CORRECT_TRUE_EXACT = ("对", "正确", "✓", "√")
CORRECT_FALSE_EXACT = ("错", "错误", "✗", "×", "不对", "不正确", "否")
GRADE_TRUE_EXACT = ("Good", "Easy", "Hard")
GRADE_FALSE_EXACT = ("Again",)


def evidence_section(text):
    """取「作答与判分」段文本（到下一个二级标题为止）；无该段则回退全文。

    注意：**文档标题本身**若含「判分/作答」字样（如「S1 摸底判分」）不得被当作证据段起点，
    否则会截在错误位置。只认标题正文**以「作答」或「判分」开头**的标题；无此类标题时才
    退化为「任一含该词的标题」（兼容旧式 `# 判分记录`）。
    """
    lines = text.splitlines()
    start, fallback = None, None
    for i, ln in enumerate(lines):
        if not ln.lstrip().startswith("#"):
            continue
        h = ln.lstrip("#").strip()
        if not EVIDENCE_HEAD_RE.search(h):
            continue
        if h.startswith("作答") or h.startswith("判分"):
            start = i + 1
            break
        if fallback is None:
            fallback = i + 1
    if start is None:
        start = fallback
    if start is None:
        return text
    out = []
    for ln in lines[start:]:
        if ln.lstrip().startswith("## "):
            break
        out.append(ln)
    return "\n".join(out)


def _section_bodies(text, head_re):
    """取出标题匹配 head_re 的二级区块正文（列表）；用于按区块计数勾选项。"""
    out, cur = [], None
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("## "):
            if head_re.search(s):
                cur = []
                out.append(cur)
            else:
                cur = None
            continue
        if cur is not None:
            cur.append(ln)
    return ["\n".join(b) for b in out]


def _checked_count(bodies):
    """区块内勾选**项**总数（同行多个 [x] 各计一项——兼容官方模板「一行多勾选」）。"""
    return sum(len(CHECKED_RE.findall(b)) for b in bodies)


def _restate_state(text):
    """复述证据状态：passed / failed / absent（缺复述记录同样不得支撑掌握）。

    v2.5（V05）：按**勾选项**计数（≥2），不再数勾选行数——官方模板把多个关键点写在
    同一行，旧口径只算 1 项会误拒合法模板。
    """
    for ln in text.splitlines():
        if RESTATE_RE.search(ln) and any(t in ln for t in RESTATE_FAIL_TOKENS):
            return "failed"
    bodies = _section_bodies(text, RESTATE_RE)
    if bodies:
        return "passed" if _checked_count(bodies) >= 2 else "failed"
    for ln in text.splitlines():
        if RESTATE_RE.search(ln) and any(t in ln for t in RESTATE_PASS_TOKENS):
            return "passed"
    return "absent"


def _artifact_state(text):
    """目标型证据状态（V05）：作品/操作/产出类区块含 ≥2 个已勾选核验项 → passed。

    与复述**等价可替代**：用来核验独立过程与结果（独立运行 / 边界输入 / 目标测试），
    而非凭「做了作品」无条件通过——须有 ≥2 个已勾选核验项。
    """
    bodies = _section_bodies(text, ARTIFACT_HEAD_RE)
    if bodies and _checked_count(bodies) >= 2:
        return "passed"
    return "absent"


def _parse_correct(tok):
    """正确性按**精确枚举**解析：`不对`/`不正确` 是错，不得被子串 `对` 误判为正确（V03）。"""
    t = (tok or "").strip()
    if t in CORRECT_TRUE_EXACT:
        return True
    if t in CORRECT_FALSE_EXACT:
        return False
    return None


def _parse_indep(tok):
    """独立性按枚举解析：独立 / 提示后 / 未测；未知值与缺失**均不得**推为独立（V03）。"""
    if tok is None:
        return None
    t = tok.strip()
    if t.startswith("独立"):
        return "独立"
    if "提示" in t:
        return "提示后"
    if t in ("未测", "未记录", "无", "缺"):
        return "未测"
    return "未测"


def parse_attempts(text):
    """把判分记录解析为结构化作答行（R01/R15）。

    **同题三要素配对**：真实学员作答（非占位）+ 可判定结果（正确性或调度档）+
    独立性枚举；三者齐备才算一条有效已判分记录（`graded`）。缺一不计入，
    不同记录的字段**不得**被拼成总体合格（V03）。
    """
    attempts, incomplete = [], 0
    for ln in evidence_section(text).splitlines():
        s = ln.strip()
        if not s.startswith("- "):
            continue
        body = s[2:]
        m = ANSWER_RE.search(body)
        raw_answer = m.group(1).strip() if m else ""
        if not raw_answer:
            m2 = ALT_ANSWER_RE.search(body)
            raw_answer = m2.group(1).strip() if m2 else ""
        has_answer = bool(raw_answer) and not PLACEHOLDER_RE.search(raw_answer)
        correct = None
        m = CORRECT_RE.search(body)
        if m:
            correct = _parse_correct(m.group(1))
        if correct is None:
            m = GRADE_RE.search(body)
            if m:
                tok = m.group(1).strip()
                if tok in GRADE_TRUE_EXACT:
                    correct = True
                elif tok in GRADE_FALSE_EXACT:
                    correct = False
        m = INDEP_RE.search(body)
        indep = _parse_indep(m.group(1)) if m else None
        aid = ATTEMPT_ID_ROW_RE.search(body)
        ab = ABILITY_TAG_RE.search(body)
        qm = QNUM_RE.search(body)
        if not (has_answer or correct is not None or indep is not None or aid or ab):
            continue     # 既无作答/判定/独立性/attempt/能力标记 → 非作答行（标题、说明等）
        graded = bool(has_answer and correct is not None and indep is not None)
        if not graded:
            incomplete += 1
        attempts.append({
            "qid": qm.group(1) if qm else "",
            "attempt_id": aid.group(1) if aid else "",
            "ability": ab.group(1).upper() if ab else "",
            "has_answer": has_answer, "correct": correct,
            "indep": indep, "graded": graded,
        })
    return {"attempts": attempts, "incomplete": incomplete}


def parse_key_abilities(text):
    """解析「关键能力」清单区块：{C1: 描述, ...}（供逐能力独立通过判定，V04）。"""
    out = {}
    for b in _section_bodies(text, KEY_ABILITY_HEAD_RE):
        for ln in b.splitlines():
            m = KEY_ABILITY_ROW_RE.match(ln)
            if m:
                out[m.group(1).upper()] = m.group(2).strip()
    return out


def has_graded_pool(text):
    """是否存在至少一条「有作答 + 有判定」的记录（诊断/结课证据用，不要求独立性/复述）。"""
    return any(a["has_answer"] and a["correct"] is not None
               for a in parse_attempts(text)["attempts"])


def gate_evidence(ev_text, require_restatement=True, require_independence=True):
    """严格模式闸口判定：返回 [(error_code, message)]（空列表=达标）。

    口径（对齐 phases-and-gates「小节验收」）：真实作答 + 同题完整判定 + 独立性枚举
    + 正确率 ≥2/3 + **每项关键能力独立通过** + **复述或目标型作品证据**通过。
    诊断/结课证据合同不同（`require_restatement=False`、`require_independence=False`）。
    """
    parsed = parse_attempts(ev_text)
    errs = []
    pool = [a for a in parsed["attempts"] if a["has_answer"] and a["correct"] is not None]
    if not pool:
        errs.append(("E-NO-GRADED-ATTEMPT",
                     "无「有真实作答且有判定」的记录（仅结果行 / 仅作答行 / 待批改均不计）"
                     "——不得据此声称掌握"))
        return errs
    # attempt 幂等去重：同一 attempt_id 只计一次；结果冲突则整条诊断（V04）
    seen, dedup, conflict = {}, [], []
    for a in pool:
        aid = a["attempt_id"]
        if not aid:
            dedup.append(a)
            continue
        if aid not in seen:
            seen[aid] = a
            dedup.append(a)
        elif seen[aid]["correct"] != a["correct"] and aid not in conflict:
            conflict.append(aid)
    if conflict:
        errs.append(("E-ATTEMPT-CONFLICT",
                     "同一 attempt_id 出现互相冲突的判定：" + "、".join(conflict) +
                     "——须核对本次真实作答，不得按多行重复抬分"))
    if require_independence and any(a["indep"] in (None, "未测") for a in dedup):
        errs.append(("E-NO-INDEPENDENCE",
                     "存在「有作答有判定但独立性缺失或未测」的记录——缺失不推为独立，"
                     "须按 独立性=独立/提示后 明确落盘"))
    correct = [a for a in dedup if a["correct"]]
    independent_correct = [a for a in correct if a["indep"] == "独立"]
    if not correct:
        errs.append(("E-ALL-FAILED", "本次新增掌握的记录全部失败/Again——不得据此声称掌握"))
    if correct and not independent_correct:
        errs.append(("E-HINT-ONLY",
                     "正确项全部依赖提示（无独立正确）——不得据此声称独立掌握"))
    if (len(correct) / len(dedup)) < GATE_RATIO:
        errs.append(("E-GATE-THRESHOLD",
                     "正确率 " + str(len(correct)) + "/" + str(len(dedup))
                     + " 低于小节验收默认线 2/3"))
    # 逐关键能力独立通过（V04）：声明了关键能力清单时，每项都要有**独立**正确记录
    abilities = parse_key_abilities(ev_text)
    if abilities:
        unmet = [k for k in abilities
                 if not any(a["ability"] == k for a in independent_correct)]
        if unmet:
            errs.append(("E-KEY-ABILITY-UNMET",
                         "关键能力未达成独立通过（须每项至少一次独立正确）："
                         + "、".join(sorted(unmet)) + "（已声明："
                         + "、".join(sorted(abilities)) + "）"))
    if require_restatement:
        rst, art = _restate_state(ev_text), _artifact_state(ev_text)
        if rst != "passed" and art != "passed":
            errs.append(("E-NO-RESTATEMENT",
                         "缺复述通过证据（" + ("复述未通过" if rst == "failed" else "未见复述记录")
                         + "），亦无目标型作品/操作证据（须含 ≥2 个已勾选核验项）"))
    return errs


def has_prefix(names, prefixes):
    """是否存在以给定专号前缀开头的判分证据文件（如 00 摸底 / 99 综合测验）。"""
    return any(n.startswith(p) for n in names for p in prefixes)


def _file_date(name):
    m = DATE_IN_NAME_RE.search(name or "")
    return m.group(1) if m else ""


def pick_special(ex_names, prefixes):
    """按专号前缀挑一份判分记录：日期最新 → 字典序最大（确定性，避免枚举顺序依赖）。"""
    cand = [n for n in ex_names if any(n.startswith(p) for p in prefixes)]
    if not cand:
        return None
    return max(cand, key=lambda n: (_file_date(n), n))


def normalize_kp_id(kid):
    """KP 编号归一化：`KP-90-1` ≡ `KP-90-01`（补零兼容；暂缓对账先归一化再比集合，V10）。"""
    m = KP_ID_ANY_RE.fullmatch(kid or "")
    if not m:
        return kid
    return "KP-{}-{}".format(int(m.group(1)), int(m.group(2)))


def _read_evidence(ex_dir, name):
    try:
        return (ex_dir / name).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def pick_evidence(cands, ex_dir, ref=None):
    """确定性选取本节的判分证据（V06/多项 real）。

    · 候选状态显式引用（`本次证据：<文件名>`）→ 只认该文件；引用不到 → 返回 ("MISSING", False)。
    · 否则在**结构真实**（real）的候选中按「文件名日期最新 → 字典序最大」确定性选定，
      并回报是否存在多份 real 候选（供 W-MULTI-EVIDENCE 提示显式引用）。
    绝不按目录枚举顺序先到先得、也不挑「任意历史最好成绩」。
    """
    if ref:
        base = re.split(r"[\\/]", ref)[-1]
        hit = [n for n in cands if n == base or n.startswith(ref)]
        if not hit:
            return "MISSING", False
        return max(sorted(hit), key=lambda n: (_file_date(n), n)), False
    reals = [n for n in cands if evidence_strength(_read_evidence(ex_dir, n)) == "real"]
    if not reals:
        return None, False
    return max(reals, key=lambda n: (_file_date(n), n)), len(reals) > 1


def parse_cursor(text):
    """解析「下次续学」区块的动作游标（F08/F22）：待回应（文件 + 题号）、最后提交 ID。"""
    out = {"待回应": None, "待回应题号": None, "最后提交": None}
    for raw in text.splitlines():
        s = raw.strip()
        m = re.search(r"待回应[：:]\s*(.*)$", s)
        if m:
            ref = m.group(1).strip()
            qm = QNUM_RE.search(ref)
            if qm:
                out["待回应题号"] = qm.group(1)
                ref = ref[:qm.start()].strip()
            out["待回应"] = ref.rstrip("｜| ").strip()
        m = re.search(r"最后提交[：:]\s*([^\s｜|]+)", s)
        if m:
            out["最后提交"] = m.group(1).strip()
    return out


def collect_submission_ids(text, ex_dir, ex_names):
    """收集可作为「最后提交」引用的**真实作答事件** ID（F22）：

    ① 判分记录文件内的 `attempt_id=` / `evt=`（作答事件依据）；
    ② progress.md「薄弱点」「错题本」条目元数据内的 `evt=`（同一作答的第二投影）。
    仅写在其他位置的字段**不算**事件——不得据此把悬空游标当有效定位。
    """
    ids = set()
    for n in ex_names:
        try:
            t = (ex_dir / n).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in ATTEMPT_ID_ANY_RE.finditer(t):
            ids.add(m.group(1))
    section = None
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("## "):
            section = s[3:].strip()
            continue
        if section in ("薄弱点", "错题本") and s.startswith("- "):
            for m in re.finditer(r"evt\s*=\s*([A-Za-z0-9_\-]+)", s):
                ids.add(m.group(1))
    return ids


# ── 知识清单文件（v2.4）解析 ──
ENUM_KP_STATUS = ("未讲", "已讲", "暂缓", "排除")
KP_ID_RE = re.compile(r"^KP-(\d+)-(\d+)$")
KP_ID_IN_TEXT_RE = re.compile(r"KP-\d+-\d+")
# 稳定引用（F09）：路线行与判分记录可声明 lesson_id=…；消费方优先按 ID 匹配，旧资料回退序号
LESSON_ID_RE = re.compile(r"lesson_id\s*=\s*([A-Za-z0-9_\-]+)")
# 覆盖范围行合法值：全量 或 已细化至第 N 节（宽容匹配，行缺失视同全量）
KP_COVER_RE = re.compile(r"^已细化至第\s*\d+\s*节")
KP_SUMMARY_KEY_RE = re.compile(r"(总|未讲|已讲|暂缓|排除)\s*(\d+)")


def kp_status_base(raw):
    """状态列取枚举基值：容忍尾部（…）括注（如「未讲（已会：摸底证据，日期）」，
    全角/半角括号双兼容）；「已会（…）」按保守口径归「未讲」基值（信息性标注，留在分母内）。
    非法返回 None。"""
    s = raw.strip()
    if not s:
        return None
    if s.startswith("已会"):
        return "未讲"
    for st in ENUM_KP_STATUS:
        if s == st or s.startswith(st + "（") or s.startswith(st + "("):
            return st
    return None


def parse_kp_row(segs):
    """清单行六段（KP编号｜知识点｜所属小节｜前置｜来源｜状态）→ dict；畸形返回 None。"""
    if len(segs) != 6:
        return None
    kid, title, section, pre, source, status = segs
    m = KP_ID_RE.match(kid)
    if not m or not title or not section:
        return None
    if (not pre.startswith("前置：") or not source.startswith("来源：")
            or not source[len("来源："):].strip() or not status.startswith("状态：")):
        return None
    pre_body = pre[len("前置："):].strip()
    prereqs = []
    if pre_body:
        for p in re.split(r"[,，、\s]+", pre_body):
            if not p or not KP_ID_RE.match(p):
                return None
            prereqs.append(p)
    raw_status = status[len("状态："):].strip()
    base = kp_status_base(raw_status)
    if base is None:
        return None
    # 摸底「已会」括注探测（全角/半角括号双兼容）：带括注行豁免 W-KP-STATE-MISMATCH
    bottom_note = raw_status.startswith("已会") or re.match(r"^未讲[(（]\s*已会", raw_status) is not None
    return {"id": kid, "sec": int(m.group(1)), "no": int(m.group(2)),
            "prereqs": prereqs, "status": base, "bottom_note": bottom_note}


def parse_kp_list(path):
    """解析知识清单文件（只读）。返回 dict：version / coverage_range（None=行缺失，视同全量）/
    coverage_malformed（含「覆盖范围」字样但未解析为合法值）/ summary_present / summary /
    rows / malformed / unreadable。
    - 头行键名全角/半角冒号双兼容（与 progress.md 字段行 FIELD_RE 半角宽容口径对齐）；
    - 读取失败（指针指向目录/不可读文件）标 unreadable，交告警层降级，不裸崩；
    - utf-8-sig 读取：BOM 吞首行缝隙闭合，对无 BOM 文件无副作用；
    - 畸形行不解析、不计数（不静默，交告警）。"""
    try:
        text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return {"version": None, "coverage_range": None, "coverage_malformed": False,
                "summary_present": False, "summary": {}, "rows": [], "malformed": [],
                "unreadable": True}
    version = None
    coverage_range = None
    coverage_malformed = False
    summary_present = False
    summary = {}
    rows, malformed = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if re.match(r"^-\s*版本[：:]", line):
            m = re.search(r"\d+", re.split(r"[：:]", line, maxsplit=1)[1])
            version = int(m.group()) if m else None
            continue
        if re.match(r"^-\s*覆盖范围[：:]", line):
            coverage_range = re.split(r"[：:]", line, maxsplit=1)[1].strip()
            continue
        if re.match(r"^-\s*覆盖摘要[：:]", line):
            summary_present = True
            for m in KP_SUMMARY_KEY_RE.finditer(re.split(r"[：:]", line, maxsplit=1)[1]):
                summary[m.group(1)] = int(m.group(2))
            continue
        if "覆盖范围" in line and not line.startswith("#"):
            # 含「覆盖范围」字样却非合法头行（写法偏差/BOM 残缺）→ 分批标注失效不得静默
            coverage_malformed = True
            continue
        if line.startswith("- ") and ("｜" in line or "|" in line):
            body = line[2:].strip()
            first = re.split(r"[｜|]", body, maxsplit=1)[0].strip()
            if KP_ID_RE.match(first):
                row = parse_kp_row([s.strip() for s in re.split(r"[｜|]", body)])
                if row is None:
                    malformed.append(body)
                else:
                    rows.append(row)
            elif re.match(r"^(版本|对照源|排序规则|覆盖范围|覆盖摘要|最近更新)[：:]", first):
                continue  # 文件头行（含 ｜ 分段的覆盖摘要行），非 KP 行
            else:
                malformed.append(body)
    return {"version": version, "coverage_range": coverage_range,
            "coverage_malformed": coverage_malformed,
            "summary_present": summary_present, "summary": summary,
            "rows": rows, "malformed": malformed, "unreadable": False}


def hold_entry_malformed(body):
    """有竖线分段但缺 来源/处置/触发条件 任一段 → 畸形（纯自由文本行不判畸形）。"""
    if "｜" not in body and "|" not in body:
        return False
    for key in HOLD_KEYS:
        if not re.search(key + r"[：:]", body):
            return True
    return False


def hold_disposition_excluded(body):
    """处置段含「排除」→ 该条按排除处置计（排除侧交叉核对用；无竖线分段判 False）。"""
    if "｜" not in body and "|" not in body:
        return False
    for seg in re.split(r"[｜|]", body):
        seg = seg.strip()
        if seg.startswith("处置"):
            return "排除" in seg
    return False


def hold_is_designed(body):
    """滚雪球候选 / 来源：范围护栏 → 设计性范围外条目（按设计留在 progress.md、不入清单，不计入暂缓基数）。"""
    return "滚雪球候选" in body or re.search(r"来源[：:]\s*范围护栏", body) is not None


def parse(text):
    fields = {}
    section = None
    sections = set()
    lessons = []        # (num, done, label)
    unparsed_routes = []  # 学习路线区出现勾选语法却未匹配的行
    hold_entries = []   # 「暂缓与范围外」条目（非「无」行）
    log_lines = []      # 学习日志条目行
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            section = line[3:].strip()
            sections.add(section)
            continue
        if section == "学习路线":
            s = line.strip()
            m = ROUTE_RE.match(s)
            if m:
                lessons.append((int(m.group(2)), m.group(1).lower() == "x", m.group(3).strip()))
            elif CHECKBOX_RE.match(s):
                unparsed_routes.append(s)
            continue
        if section == "暂缓与范围外":
            s = line.strip()
            if s.startswith("- "):
                body = s[2:].strip()
                if body not in ("无", "无。"):
                    hold_entries.append(body)
            continue
        if section == "学习日志":
            s = line.strip()
            if s.startswith("- "):
                log_lines.append(s[2:].strip())
            continue
        m = FIELD_RE.match(line.strip())
        if m and section is None:
            key = m.group(1).strip()
            if key not in fields:
                fields[key] = m.group(2).strip()
    return fields, lessons, unparsed_routes, sections, hold_entries, log_lines


def check(task_dir, release=False, proposed=None):
    """校验任务；release=True 走严格放行闸口。

    proposed（R02 拟提交状态）：可选 dict，键：
      text            —— 拟提交的 progress.md 候选快照文本（校验该对象而非磁盘现状）
      phase           —— 拟提交的目标阶段（覆盖候选文本中的「当前阶段」）
      changed_lessons —— 本次新增掌握的小节编号列表；给定时严格证据校验只覆盖这些小节
                         （显式增量机制，旧资料不阻断无关新节）
    未提供 proposed 时只校验当前落盘状态：目标变更（拟转阶段/拟新增掌握）未被校验，
    输出 `proposed_state_supplied:false` + W-NO-PROPOSED-STATE 明示（不得据此声称已校验）。
    """
    task_dir = Path(task_dir)
    proposed = proposed or {}
    proposed_state_supplied = bool(proposed.get("text") is not None or proposed.get("phase"))
    declared_changes = proposed.get("changed_lessons")
    errors, warnings = [], []
    checked_lessons = []      # 本次严格证据校验覆盖的小节号（增量机制透明化）
    mandatory_unlearned_ids = []   # 结课时仍「未讲」的关键能力 KP（清单纳入口径）
    included_kp_ids = []      # 纳入出题分母的 KP（状态 ∈ {未讲, 已讲}）——结课蓝图覆盖核对用
    delta = None              # 候选快照相对磁盘原状态的**真实新增掌握**集合（R13）
    evidence_used = []        # 各小节实际选用的判分证据文件（确定性选取透明化，V06）
    prog = task_dir / "progress.md"
    if proposed.get("text") is not None:
        text = proposed["text"]
    else:
        if not prog.exists():
            return {"ok": False, "task_dir": str(task_dir),
                    "errors": [{"code": "E-NO-PROGRESS", "message": "缺少 progress.md"}],
                    "warnings": [], "coverage": None,
                    "proposed_state_supplied": proposed_state_supplied}
        try:
            text = prog.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return {"ok": False, "task_dir": str(task_dir),
                    "errors": [{"code": "E-UNREADABLE-PROGRESS",
                                "message": "progress.md 存在但不可读（可能是目录或无权限）"}],
                    "warnings": [], "coverage": None,
                    "proposed_state_supplied": proposed_state_supplied}
    fields, lessons, unparsed_routes, sections, hold_entries, log_lines = parse(text)
    if proposed.get("phase"):
        fields["当前阶段"] = proposed["phase"]   # 校验拟提交目标阶段，而非磁盘旧状态

    # ── R13 候选差分：真实新增掌握集合必须被声明覆盖（漏查即拦停）──
    if proposed.get("text") is not None and prog.exists():
        try:
            disk_text = prog.read_text(encoding="utf-8", errors="replace")
        except OSError:
            disk_text = None
        if disk_text is not None:
            _df, disk_lessons, _du, _ds, _dh, _dl = parse(disk_text)
            disk_done = {n for n, d, _lbl in disk_lessons if d}
            cand_done = {n for n, d, _lbl in lessons if d}
            delta = sorted(cand_done - disk_done)
            if declared_changes is not None:
                unknown = sorted(n for n in declared_changes if n not in cand_done)
                if unknown:
                    errors.append({"code": "E-CHANGED-SET-INVALID",
                                   "message": "--changed-lessons 含候选态并未掌握的小节编号："
                                              + "、".join(str(n) for n in unknown)})
                if not set(delta).issubset(set(declared_changes)):
                    errors.append({"code": "E-UNDECLARED-CHANGES",
                                   "message": "候选快照新增掌握的小节未被 --changed-lessons 覆盖（漏查）：新增 "
                                              + "、".join(str(n) for n in delta)
                                              + "；声明 " + "、".join(str(n) for n in declared_changes)
                                              + "——须逐一校验证据或修正声明"})
    # 实际严格校验范围：显式声明 > 候选差分 > 全部已掌握小节
    if declared_changes is not None:
        changed_lessons = list(declared_changes)
    elif delta is not None:
        changed_lessons = list(delta)
    else:
        changed_lessons = None

    for key in BASE_REQUIRED:
        if not fields.get(key):
            errors.append({"code": "E-MISSING-FIELD", "message": "缺少必填字段 '" + key + "'"})

    phase = fields.get("当前阶段", "")
    # 「起点」由 S1 产出：S0（接料建档）与 S1（诊断摸底，进行中）不要求；
    # 诊断结束进入 S2 起（计划确认中/逐节学习/复习巩固/结课/已完成）必填。
    # 修复 F01：旧规则「离开 S0 即必填」会把 S1 进行中误判为缺字段。
    if phase and phase not in ("接料建档", "诊断摸底") and not fields.get("起点"):
        errors.append({"code": "E-MISSING-FIELD", "message": "缺少必填字段 '起点'（诊断结束进入 S2 起必填）"})

    if phase and phase not in ENUM_PHASE:
        errors.append({"code": "E-ENUM-PHASE", "message": "当前阶段取值非法: " + phase})
    if fields.get("类型", "") and fields["类型"] not in ENUM_TYPE:
        errors.append({"code": "E-ENUM-TYPE", "message": "类型取值非法: " + fields["类型"]})
    if fields.get("学科族", "") and fields["学科族"] not in ENUM_FAMILY:
        errors.append({"code": "E-ENUM-FAMILY", "message": "学科族取值非法: " + fields["学科族"]})

    review_from = fields.get("复习来源阶段", "")
    if phase == "复习巩固":
        if review_from in ("", "无"):
            errors.append({"code": "E-REVIEW-ORIGIN",
                           "message": "复习巩固阶段缺少「复习来源阶段」（无法确定返回点）"})
        elif review_from not in ENUM_REVIEW_FROM:
            # 任意返回阶段字符串被拒（F04：合法返回点 = 逐节学习 / 结课 / 已完成）
            errors.append({"code": "E-REVIEW-ORIGIN",
                           "message": "「复习来源阶段」取值非法: " + review_from +
                                      "（合法枚举：" + " / ".join(ENUM_REVIEW_FROM) + "）"})

    # 落盘证据：已掌握小节必须有 exercises/ 判分记录
    ex_dir = task_dir / "exercises"
    ex_names = []
    if ex_dir.is_dir():
        ex_names = [p.name for p in ex_dir.iterdir() if p.is_file()]
    # F09：路线内 lesson_id 必须唯一（同一证据不得被两节共用、无法判定归属）
    route_id_list = [LESSON_ID_RE.search(lbl).group(1) for _n, _d, lbl in lessons
                     if LESSON_ID_RE.search(lbl)]
    dup_ids = sorted({i for i in route_id_list if route_id_list.count(i) > 1})
    if dup_ids:
        errors.append({"code": "E-LESSON-ID-DUP",
                       "message": "学习路线存在重复 lesson_id（同一证据会被两节共用、无法判定归属）："
                                  + "、".join(dup_ids)})
    # 候选状态可为本次提交**显式引用**判分证据（`- 本次证据：<文件名>`）
    ev_ref_m = EVIDENCE_REF_RE.search(text)
    ev_ref = ev_ref_m.group(1) if ev_ref_m else None
    for num, done, label in lessons:
        if not done:
            continue
        if changed_lessons is not None and num not in changed_lessons:
            continue   # 增量：只校验本次新增掌握的小节，旧资料不阻断无关新节
        checked_lessons.append(num)
        # 编号宽容匹配：同时接受两位补零 "01-" 与单位数 "1-"
        prefixes = ("{:02d}-".format(num), "{}-".format(num))
        # F09 稳定引用：路线行声明 lesson_id 时**优先按 ID 匹配**（重排/改名后仍正确）；
        # 未声明或旧资料无 ID 时才回退序号前缀匹配（零迁移）。
        route_id_m = LESSON_ID_RE.search(label)
        route_id = route_id_m.group(1) if route_id_m else None
        hit = []
        if route_id:
            for n in ex_names:
                m = LESSON_ID_RE.search(_read_evidence(ex_dir, n))
                if m and m.group(1) == route_id:
                    hit.append(n)
        if not hit:
            hit = [n for n in ex_names if n.startswith(prefixes[0]) or n.startswith(prefixes[1])]
        if route_id and hit:
            # 回退命中的文件声明了另一个 lesson_id → 证据错配（重排后串用他节证据）
            mism = []
            for n in hit:
                m = LESSON_ID_RE.search(_read_evidence(ex_dir, n))
                if m and m.group(1) != route_id:
                    mism.append(n + "（lesson_id=" + m.group(1) + "）")
            if mism:
                errors.append({"code": "E-EVIDENCE-ID-MISMATCH",
                               "message": "小节 " + str(num) + "（lesson_id=" + route_id +
                                          "）的判分证据声明了另一稳定 ID：" + "、".join(mism) +
                                          "——按序号回退串到了他节证据，拒绝放行"})
        if not hit:
            errors.append({"code": "E-NO-EVIDENCE",
                           "message": "小节 " + str(num) + " 标已掌握，但 exercises/ 无判分记录（" +
                                      prefixes[0] + "* 或 " + prefixes[1] + "*）"})
            continue
        # V06：确定性选证据（显式引用优先；否则「日期最新 → 字典序最大」），不看枚举顺序
        chosen, multi = pick_evidence(hit, ex_dir, ev_ref)
        if chosen == "MISSING":
            errors.append({"code": "E-EVIDENCE-REF-MISSING",
                           "message": "候选状态引用的本次证据不存在：" + str(ev_ref)})
            continue
        if multi:
            warnings.append({"code": "W-MULTI-EVIDENCE",
                             "message": "小节 " + str(num) + " 存在多份结构真实（real）的判分证据，已按"
                                        "「日期最新 → 字典序最大」确定性选定 " + str(chosen) +
                                        "；如需以特定提交为准，请在候选状态写 `- 本次证据：<文件名>`"})
        if chosen:
            evidence_used.append(chosen)
            best, best_text = "real", _read_evidence(ex_dir, chosen)
        else:
            # 无 real 证据：仍按确定性顺序找 template/empty，给出可核查的拦截原因
            best, best_text = "empty", ""
            for n in sorted(hit):
                t = _read_evidence(ex_dir, n)
                if evidence_strength(t) == "template":
                    best, best_text = "template", t
                    break
            if best == "empty":
                best_text = _read_evidence(ex_dir, sorted(hit)[0])
        if best != "real":
            kind = ("空文件或无作答/判分结构" if best == "empty"
                    else "仅含「作答/判分」模板、无真实结果")
            empty_msg = ("小节 " + str(num) + " 的判分记录未提供可用证据（" + kind +
                         "）：" + "、".join(sorted(hit)))
            if release:
                errors.append({"code": "E-EMPTY-EVIDENCE", "message": empty_msg})
            else:
                warnings.append({"code": "W-EMPTY-EVIDENCE", "message": empty_msg})
        elif release:
            # R01/R15：结构化作答 + 闸口判定（不再仅凭「含评分词」放行）
            for code, msg in gate_evidence(best_text):
                errors.append({"code": code, "message": "小节 " + str(num) + "：" + msg})

    # 未解析勾选行：出现勾选语法却未被识别（不得静默）
    for line in unparsed_routes:
        warnings.append({"code": "W-UNPARSED-ROUTE",
                         "message": "学习路线存在未解析的勾选行（应为 \"- [x] N. 小节名\"）：" + line})

    # ── 覆盖完整性（v2.3，只读告警：warning 非 error，不阻断旧任务） ──
    hold_section_present = "暂缓与范围外" in sections
    malformed_holds = [b for b in hold_entries if hold_entry_malformed(b)]
    base_holds = [b for b in hold_entries if not hold_entry_malformed(b)]  # 合规条目（畸形条目计 0，不静默）
    hold_count = len(base_holds)
    excluded_count = sum(1 for b in base_holds if hold_disposition_excluded(b))
    route_undone = sum(1 for _n, done, _l in lessons if not done)
    # 审计记录存在性：学习日志行同时含「审计」关键词与 YYYY-MM-DD 日期
    audit_record_found = any(("审计" in ln and DATE_RE.search(ln)) for ln in log_lines)

    for body in malformed_holds:
        warnings.append({"code": "W-UNPARSED-HOLD",
                         "message": "「暂缓与范围外」存在未解析条目（应含 来源/处置/触发条件 竖线分段）：" + body})

    # 粒度核对：暂缓/排除条目须与清单 KP 行**一一对应**（一行一条目）；
    # 设计性范围外（滚雪球候选）不受此限（本就不入清单）。
    for body in base_holds:
        if hold_is_designed(body):
            continue
        if len(re.findall(r"KP-\d+-\d+", body)) >= 2:
            warnings.append({"code": "W-UNPARSED-HOLD",
                             "message": "「暂缓与范围外」条目含多个 KP 编号（粒度不符：暂缓/排除条目应与清单 KP 行一一对应、一行一条目）：" + body})

    if phase in ("结课", "已完成"):
        if release and route_undone > 0:
            # 放行模式：不得凭仍有未勾选小节的路线声称结课/已完成（F03/T05）
            errors.append({"code": "E-ROUTE-UNDONE",
                           "message": "阶段为「" + phase + "」但学习路线仍有 " + str(route_undone) +
                                      " 个未勾选小节——不得凭未完成路线声称结课/已完成"})
        if not hold_section_present:
            warnings.append({"code": "W-NO-COVERAGE-AUDIT",
                             "message": "结课/已完成任务缺「暂缓与范围外」区块（旧任务属合法「未审计」形态，"
                                        "不阻断；建议下次正常文件写入/编辑时顺带补区块并补跑覆盖审计）"})
        if not audit_record_found:
            warnings.append({"code": "W-NO-COVERAGE-AUDIT",
                             "message": "学习日志未发现覆盖审计记录（需同时含「审计」关键词与 YYYY-MM-DD 日期），"
                                        "转结课前应完成覆盖率审计（warning，不阻断）"})

    coverage = {
        "hold_section_present": hold_section_present,
        "hold_count": hold_count,  # 区块合规条目总数（含处置为排除的条目）
        "excluded_count": excluded_count,  # 其中处置为「排除」的条目数；暂缓口径 = hold_count − excluded_count
        "hold_unparsed": len(malformed_holds),
        "route_undone": route_undone,
        "audit_record_found": audit_record_found,
    }

    # ── KP 清单只读告警（v2.4；无指针旧任务零触发，warning 非 error，不阻断） ──
    kp_pointer = fields.get("知识清单", "")
    if kp_pointer:
        list_name = re.split(r"[｜|]", kp_pointer)[0].strip()
        list_path = task_dir / list_name
        if not list_path.exists():
            warnings.append({"code": "W-KP-LIST-MISSING",
                             "message": "progress.md 记有知识清单指针但文件不存在：" + list_name})
        else:
            kp = parse_kp_list(list_path)
            if kp["unreadable"]:
                # 指针指向目录/不可读文件：降级为 W 级告警 + 正常 JSON 输出，杜绝 traceback 裸崩
                warnings.append({"code": "W-KP-LIST-MISSING",
                                 "message": "progress.md 记有知识清单指针但文件不可读（可能是同名目录或无权限）：" + list_name})
            else:
                for body in kp["malformed"]:
                    warnings.append({"code": "W-UNPARSED-KP",
                                     "message": "知识清单存在未解析行（六字段：KP编号｜知识点｜所属小节｜前置｜来源｜状态；"
                                                "畸形行不计入摘要计数）：" + body})
                cr = kp["coverage_range"]
                if kp["coverage_malformed"] or (cr is not None and cr != "全量" and not KP_COVER_RE.match(cr)):
                    warnings.append({"code": "W-UNPARSED-KP",
                                     "message": "知识清单「覆盖范围」行畸形（应为「全量」或「已细化至第 N 节，其余待细化」）；"
                                                "分批标注写法偏差不得静默失效：" +
                                                (cr if cr is not None else "<未能解析出值>")})
                # KP 编号查重（沿用不计入摘要计数口径）：封堵不跑 kp_sort 类型（备考/材料型）的静默重复
                seen_ids, dup_ids = set(), []
                rows_unique = []
                for r in kp["rows"]:
                    if r["id"] in seen_ids:
                        if r["id"] not in dup_ids:
                            dup_ids.append(r["id"])
                    else:
                        seen_ids.add(r["id"])
                        rows_unique.append(r)
                for i in dup_ids:
                    warnings.append({"code": "W-UNPARSED-KP",
                                     "message": "知识清单存在重复 KP 编号（重复行不计入摘要计数）：" + i})
                for r in rows_unique:
                    for p in r["prereqs"]:
                        if p not in seen_ids:
                            warnings.append({"code": "W-UNPARSED-KP",
                                             "message": "知识清单 " + r["id"] + " 前置引用不存在的 KP：" + p})
                # 摘要核对与双写交叉核对：rows 为空但摘要行有值（如「清单仅写『无』却称总 4」）照常核对，不静默
                actual = {"总": len(rows_unique), "未讲": 0, "已讲": 0, "暂缓": 0, "排除": 0}
                for r in rows_unique:
                    actual[r["status"]] += 1
                summary_has_value = kp["summary_present"] and any(
                    kp["summary"].get(k) for k in ("总", "未讲", "已讲", "暂缓", "排除"))
                if rows_unique or summary_has_value:
                    if not kp["summary_present"] or any(kp["summary"].get(k) != v for k, v in actual.items()):
                        warnings.append({"code": "W-KP-SUMMARY-MISMATCH",
                                         "message": ("知识清单覆盖摘要行{state}（脚本核对权威）：实际 总 {总} ｜ 未讲 {未讲} ｜ "
                                                     "已讲 {已讲} ｜ 暂缓 {暂缓} ｜ 排除 {排除}")
                                                    .format(state="缺失" if not kp["summary_present"] else "计数与逐行实际不符",
                                                            **actual)})
                    # 暂缓/排除双写对账：按**对象 ID 集合**比较（数量相同但对象不同也能检出），
                    # 设计性范围外（滚雪球候选）与不含 KP 编号的条目不计入集合、显式豁免。
                    # 先按 KP 编号**归一化**（`KP-90-1` ≡ `KP-90-01`）再比集合，避免补零写法误报（V10）
                    kp_hold_ids = {normalize_kp_id(r["id"]) for r in rows_unique if r["status"] == "暂缓"}
                    kp_excl_ids = {normalize_kp_id(r["id"]) for r in rows_unique if r["status"] == "排除"}
                    prg_hold_ids, prg_excl_ids = set(), set()
                    for b in base_holds:
                        if hold_is_designed(b):
                            continue   # 设计性范围外按设计留在 progress.md、不入清单
                        ids = [normalize_kp_id(i) for i in KP_ID_IN_TEXT_RE.findall(b)]
                        if hold_disposition_excluded(b):
                            prg_excl_ids.update(ids)
                        else:
                            prg_hold_ids.update(ids)
                    if kp["summary_present"] and "暂缓" in kp["summary"]:
                        if kp_hold_ids != prg_hold_ids:
                            warnings.append({"code": "W-KP-HOLD-CROSS",
                                             "message": "暂缓侧双写账本按对象 ID 对账不一致——仅清单暂缓："
                                                        + ("、".join(sorted(kp_hold_ids - prg_hold_ids)) or "无")
                                                        + "；仅在 progress.md 暂缓："
                                                        + ("、".join(sorted(prg_hold_ids - kp_hold_ids)) or "无")
                                                        + "（清单摘要暂缓数 " + str(kp["summary"]["暂缓"]) +
                                                        "，区块可比暂缓条目数 " + str(len(prg_hold_ids)) +
                                                        "）——先核对差异项是否为『滚雪球候选』等设计性范围外条目"
                                                        "（属设计性差异可忽略）；非设计性差异才提醒补齐另一侧（warning，不阻断）"})
                    if kp["summary_present"] and "排除" in kp["summary"]:
                        if kp_excl_ids != prg_excl_ids:
                            warnings.append({"code": "W-KP-HOLD-CROSS",
                                             "message": "排除侧双写账本按对象 ID 对账不一致——仅清单排除："
                                                        + ("、".join(sorted(kp_excl_ids - prg_excl_ids)) or "无")
                                                        + "；仅在 progress.md 处置排除："
                                                        + ("、".join(sorted(prg_excl_ids - kp_excl_ids)) or "无")
                                                        + "（清单摘要排除数 " + str(kp["summary"]["排除"]) +
                                                        "，区块处置排除条目数 " + str(len(prg_excl_ids)) +
                                                        "）——核对清单『排除』状态与区块『处置：经用户确认排除』是否对齐，"
                                                        "提醒补齐另一侧（warning，不阻断）"})
                if rows_unique:
                    done_secs = {num for num, done, _lbl in lessons if done}
                    by_sec = {}
                    for r in rows_unique:
                        by_sec.setdefault(r["sec"], []).append(r)
                    # 纳入节点（状态 ∈ {未讲, 已讲}）中仍「未讲」的 KP = 关键能力缺证据，
                    # 结课时不得放行（带「已会」摸底括注行属合法信息性标注，不计）
                    mandatory_unlearned_ids.extend(
                        r["id"] for r in rows_unique
                        if r["status"] == "未讲" and not r["bottom_note"])
                    # 纳入出题分母的 KP（未讲/已讲）——结课综合测验须逐项覆盖（V02 蓝图覆盖）
                    included_kp_ids.extend(
                        r["id"] for r in rows_unique if r["status"] in ("未讲", "已讲"))
                    for sec in sorted(by_sec):
                        rows_in = by_sec[sec]
                        # 判定：存在「无摸底括注且基值为未讲」的行即告警；带「已会」括注行豁免
                        flagged = [r for r in rows_in if r["status"] == "未讲" and not r["bottom_note"]]
                        if sec in done_secs and flagged:
                            warnings.append({"code": "W-KP-STATE-MISMATCH",
                                             "message": "小节 " + str(sec) + " 勾选「已掌握」，但清单内该节存在「未讲」KP：" +
                                                        "、".join(r["id"] for r in flagged) +
                                                        "（可能是清单滞后，提醒在节末落盘更新时补齐；"
                                                        "带『已会（摸底证据）』括注的 KP 属预期形态——信息性标注留在分母，"
                                                        "不触发本告警；其是否移出分母（标排除）在结课前覆盖率审计时经用户确认，"
                                                        "勿在节末自行翻转）"})

    if not lessons and not unparsed_routes:
        warnings.append({"code": "W-NO-ROUTE", "message": "尚无学习路线（S2 前正常）"})
    if review_from and review_from != "无" and phase != "复习巩固":
        warnings.append({"code": "W-STALE-REVIEW-ORIGIN",
                         "message": "非复习巩固阶段仍留有「复习来源阶段」，确认是否应清空"})

    # ── F08 动作游标悬空引用（放行模式为 error；历史模式为 warning）──
    cursor = parse_cursor(text)
    if cursor["待回应"] or cursor["最后提交"]:
        def _cursor_fail(msg):
            if release:
                errors.append({"code": "E-CURSOR-DANGLING", "message": msg})
            else:
                warnings.append({"code": "W-CURSOR-DANGLING", "message": msg})

        if cursor["待回应"]:
            ref = cursor["待回应"]
            base = re.split(r"[\\/]", ref)[-1]
            hitf = [n for n in ex_names if n == base or n.startswith(ref)]
            if not hitf:
                _cursor_fail("动作游标「待回应」指向的判分记录不存在：" + ref +
                             "（恢复时无处可定位，须先修正游标）")
            elif cursor["待回应题号"]:
                # 文件存在但**题号不存在**于该文件 → 续学动作仍会悬空（V10）
                body = _read_evidence(ex_dir, hitf[0])
                if not re.search(r"题\s*" + re.escape(cursor["待回应题号"]) + r"(?!\d)", body):
                    _cursor_fail("动作游标「待回应」引用 " + ref + " 题" +
                                 str(cursor["待回应题号"]) + "，但该判分记录内无此题号"
                                 "——续学无法定位，须先修正游标")
        if cursor["最后提交"]:
            known = collect_submission_ids(text, ex_dir, ex_names)
            if cursor["最后提交"] not in known:
                _cursor_fail("动作游标「最后提交」引用的 ID 不存在于任何**真实作答事件**"
                             "（判分记录或薄弱点/错题元数据的 attempt_id=/evt=）：" +
                             cursor["最后提交"] + "（无法核对重复事件，须先修正游标）")

    # ── R01/R02 放行模式严格闸口（只在 release 生效；历史模式不阻断旧任务）──
    if release:
        if not proposed_state_supplied:
            warnings.append({"code": "W-NO-PROPOSED-STATE",
                             "message": "未提供拟提交状态（--proposed-phase/--staged）：只校验当前落盘状态，"
                                        "拟转阶段/拟新增掌握的目标变更未被校验——不得据此声称已校验"})
        start = fields.get("起点", "")
        if phase and phase not in ("接料建档", "诊断摸底") and start and start not in ENUM_START:
            errors.append({"code": "E-ENUM-START",
                           "message": "起点取值非法: " + start +
                                      "（合法枚举：" + " / ".join(ENUM_START) + "）"})
        # S1→S2 闸口：进入 S2 必须有一份**可用**的 00 专号摸底判分证据（V02：空文件/仅文件名不算）
        if phase == "计划确认中":
            diag = pick_special(ex_names, DIAG_PREFIXES)
            if diag is None or not has_graded_pool(_read_evidence(ex_dir, diag)):
                errors.append({"code": "E-NO-DIAGNOSTIC",
                               "message": "进入 S2（计划确认中）但缺**可用**的 S1 摸底判分证据"
                                          "（exercises/00-摸底-<日期>.md，须含真实作答与判定；"
                                          "空文件或仅凭文件名不得证明已诊断）"})
        if phase in ("结课", "已完成"):
            # 空路线 / 不可解析路线不得凭「零个未完成行」放行（结课范围不可证明）
            if not lessons:
                errors.append({"code": "E-NO-ROUTE-STRICT",
                               "message": "阶段为「" + phase + "」但学习路线缺失或不可解析"
                                          "（" + ("存在未解析勾选行" if unparsed_routes else "无勾选行") +
                                          "）——不得据此声称结课"})
            elif unparsed_routes:
                # 混合「可解析 + 不可解析」路线同样是范围不可证明（V02）
                errors.append({"code": "E-NO-ROUTE-STRICT",
                               "message": "阶段为「" + phase + "」但学习路线含未解析勾选行："
                                          + "；".join(unparsed_routes) +
                                          "——结课范围不可证明，须先修正路线"})
            fin = pick_special(ex_names, FINAL_PREFIXES)
            if fin is None:
                errors.append({"code": "E-NO-FINAL-EXAM",
                               "message": "阶段为「" + phase + "」但缺结课综合测验证据"
                                          "（exercises/99-结课综合测验-<日期>.md）"})
            elif not has_graded_pool(_read_evidence(ex_dir, fin)):
                errors.append({"code": "E-FINAL-NO-EVIDENCE",
                               "message": "结课综合测验 " + fin + " 无可用判分证据（须含真实作答与判定）"
                                          "——空文件或仅凭文件名不得证明结课"})
            else:
                ftext = _read_evidence(ex_dir, fin)
                # 结课证据合同不同于小节：另按真实分值与目标线，不套「复述 / 逐关键能力独立」
                for fcode, fmsg in gate_evidence(ftext, require_restatement=False,
                                                require_independence=False):
                    mapped = {"E-NO-GRADED-ATTEMPT": "E-FINAL-NO-EVIDENCE",
                              "E-ATTEMPT-CONFLICT": "E-FINAL-ATTEMPT-CONFLICT",
                              "E-ALL-FAILED": "E-FINAL-BELOW-TARGET",
                              "E-HINT-ONLY": "E-FINAL-BELOW-TARGET",
                              "E-GATE-THRESHOLD": "E-FINAL-BELOW-TARGET"}.get(fcode, fcode)
                    errors.append({"code": mapped, "message": "结课综合测验 " + fin + "：" + fmsg})
                gap = [k for k in included_kp_ids if k not in ftext]
                if gap:
                    errors.append({"code": "E-FINAL-BLUEPRINT-GAP",
                                   "message": "结课综合测验 " + fin +
                                              " 未覆盖全部纳入 KP（蓝图覆盖缺口）：" + "、".join(gap) +
                                              "——须按能力—任务—评分点蓝图逐项对应"})
            if mandatory_unlearned_ids:
                errors.append({"code": "E-CORE-UNLEARNED",
                               "message": "阶段为「" + phase + "」但清单内仍有关键能力 KP 状态「未讲」：" +
                                          "、".join(mandatory_unlearned_ids) +
                                          "——关键能力缺可判分证据，不得结课"})

    return {"ok": not errors, "task_dir": str(task_dir), "phase": phase,
            "release": release, "errors": errors, "warnings": warnings,
            "coverage": coverage,
            "proposed_state_supplied": proposed_state_supplied,
            "checked_lessons": checked_lessons,
            "delta_new_mastery": delta,
            "evidence_used": evidence_used}


GOOD = """# 学习任务：示例
- 数据根：<root>
- 当前阶段：逐节学习
- 类型：技能型
- 学科族：编程类
- 目标：入门
- 起点：零基础
- 复习来源阶段：无

## 学习路线
- [x] 1. 变量
- [ ] 2. 循环
"""
BAD = """# 学习任务：示例
- 当前阶段：复习巩固
- 类型：知识型
- 学科族：数学类
- 目标：x
- 起点：入门

## 学习路线
- [x] 1. 变量
"""
S0 = """# 学习任务：示例
- 数据根：<root>
- 当前阶段：接料建档
- 类型：技能型
- 学科族：编程类
- 目标：入门
"""
UPPER = """# 学习任务：示例
- 数据根：<root>
- 当前阶段：逐节学习
- 类型：技能型
- 学科族：编程类
- 目标：入门
- 起点：零基础

## 学习路线
- [X] 1. 极限
"""
# v2.3 覆盖完整性夹具：结课 + 暂缓区块齐整 + 审计记录
DONE_OK = """# 学习任务：示例
- 数据根：<root>
- 当前阶段：结课
- 类型：备考型
- 学科族：语言类
- 目标：通过考试
- 起点：入门

## 学习路线
- [x] 1. 词法
- [x] 2. 句法

## 暂缓与范围外
- 插入语 ｜ 来源：S2 对照 ｜ 处置：暂缓 ｜ 触发条件：用户要求
- 倒装句 ｜ 来源：范围护栏 ｜ 处置：暂缓 ｜ 触发条件：阶段末审计

## 学习日志
- 2026-10-11：覆盖率审计——对照源考纲共 12 项，差异 1 项已补讲
"""
# 畸形暂缓条目（有竖线分段但缺「触发条件」）→ W-UNPARSED-HOLD，非 error
HOLD_BAD = """# 学习任务：示例
- 数据根：<root>
- 当前阶段：逐节学习
- 类型：材料型
- 学科族：数学类
- 目标：啃完教材
- 起点：入门

## 学习路线
- [ ] 1. 第一章

## 暂缓与范围外
- 插入语 ｜ 来源：S2 对照 ｜ 处置：暂缓
"""

# ── v2.4 KP 清单夹具 ──
KPLIST_OK = """# 知识清单：示例
- 版本：1
- 对照源：自拟总纲
- 排序规则：拓扑序（依赖边见各行前置列）
- 覆盖范围：全量
- 最近更新：2026-10-11
- 覆盖摘要：总 4 ｜ 未讲 2 ｜ 已讲 1 ｜ 暂缓 1 ｜ 排除 0

- KP-01-01 ｜ 变量命名 ｜ 小节 1 ｜ 前置：  ｜ 来源：目录 1.1 ｜ 状态：已讲
- KP-02-01 ｜ 循环与迭代 ｜ 小节 2 ｜ 前置：KP-01-01 ｜ 来源：目录 1.2 ｜ 状态：未讲
- KP-02-02 ｜ 递归初步 ｜ 小节 2 ｜ 前置：KP-02-01 ｜ 来源：目录 1.2 ｜ 状态：未讲（已会：摸底题 2 全对，2026-10-11）
- KP-03-01 ｜ 高级主题 ｜ 小节 3 ｜ 前置：KP-02-01 ｜ 来源：目录 1.3 ｜ 状态：暂缓
"""
KP_PROG_OK = """# 学习任务：示例
- 数据根：<root>
- 当前阶段：逐节学习
- 类型：知识型
- 学科族：编程类
- 目标：入门
- 起点：零基础
- 知识清单：知识清单.md ｜ 版本 1 ｜ 总 4

## 学习路线
- [x] 1. 变量
- [ ] 2. 循环

## 暂缓与范围外
- 高级主题 KP-03-01 ｜ 来源：S2 对照 ｜ 处置：暂缓 ｜ 触发条件：用户要求
"""
KP_PROG_NOHOLD = """# 学习任务：示例
- 数据根：<root>
- 当前阶段：逐节学习
- 类型：知识型
- 学科族：编程类
- 目标：入门
- 起点：零基础
- 知识清单：知识清单.md ｜ 版本 1 ｜ 总 4

## 学习路线
- [x] 1. 变量
- [ ] 2. 循环
"""
KP_PROG_NA = """# 学习任务：示例
- 数据根：<root>
- 当前阶段：逐节学习
- 类型：知识型
- 学科族：编程类
- 目标：入门
- 起点：零基础
- 知识清单：知识清单.md ｜ 版本 1 ｜ 总 2

## 学习路线
- [ ] 1. 变量
- [ ] 2. 循环
"""
# 畸形清单：状态非法 / 前置引用不存在 / 行缺段 / 覆盖范围行畸形（各计 1 条 W-UNPARSED-KP）
KPLIST_BAD = """# 知识清单：示例
- 版本：1
- 对照源：自拟总纲
- 覆盖范围：大概全量
- 最近更新：2026-10-11
- 覆盖摘要：总 2 ｜ 未讲 2 ｜ 已讲 0 ｜ 暂缓 0 ｜ 排除 0

- KP-01-01 ｜ 变量命名 ｜ 小节 1 ｜ 前置：  ｜ 来源：目录 1.1 ｜ 状态：学会
- KP-02-01 ｜ 循环 ｜ 小节 2 ｜ 前置：KP-09-09 ｜ 来源：目录 1.2 ｜ 状态：未讲
- KP-02-02 ｜ 递归 ｜ 小节 2 ｜ 前置：KP-02-01 ｜ 来源：目录 1.2 ｜ 状态：未讲
- KP-03-01 ｜ 尾行缺段 ｜ 小节 3 ｜ 前置：KP-02-02 ｜ 来源：目录 1.3
"""
# 半角括号已会变体：不得报畸形或硬失败
KPLIST_HALFPAREN = KPLIST_OK.replace("状态：未讲（已会：摸底题 2 全对，2026-10-11）",
                                     "状态：未讲(已会：摸底题 2 全对，2026-10-11)")
# rows 空 + 摘要行有值（矛盾态）：必须出 W-KP-SUMMARY-MISMATCH
KPLIST_EMPTY_NOSUM = """# 知识清单：无行有摘要矛盾态
- 版本：1
- 覆盖范围：全量
- 覆盖摘要：总 4 ｜ 未讲 4 ｜ 已讲 0 ｜ 暂缓 0 ｜ 排除 0

- 无
"""
# 重复编号：重复行不计入摘要计数（unique 2 与摘要总 2 一致）
KPLIST_DUP = """# 知识清单：重复编号夹具
- 版本：1
- 覆盖范围：全量
- 覆盖摘要：总 2 ｜ 未讲 2 ｜ 已讲 0 ｜ 暂缓 0 ｜ 排除 0

- KP-01-01 ｜ 甲 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 1.1 ｜ 状态：未讲
- KP-01-01 ｜ 甲重复 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 1.1 ｜ 状态：未讲
- KP-01-02 ｜ 乙 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 1.1 ｜ 状态：未讲
"""
# 半角冒号覆盖范围行：宽容解析不告警
KPLIST_HALFCOLON = KPLIST_OK.replace("- 覆盖范围：全量", "- 覆盖范围:全量")
# 含「覆盖范围」字样但非合法头行（写法偏差）：必须出 W-UNPARSED-KP，不静默失效
KPLIST_COVERBROKEN = KPLIST_OK.replace("- 覆盖范围：全量", "- 覆盖范围行（残缺）：全量")
# 整节摸底已会（带括注）+ 该节勾选已掌握：豁免 W-KP-STATE-MISMATCH
KPLIST_ALLBOTTOM = (KPLIST_OK
                    .replace("状态：已讲", "状态：未讲（已会：摸底题 1 全对，2026-10-11）")
                    .replace("总 4 ｜ 未讲 2 ｜ 已讲 1", "总 4 ｜ 未讲 3 ｜ 已讲 0"))
# progress.md 暂缓区块含滚雪球候选（设计性范围外）：HOLD-CROSS 不得误报
KP_PROG_SNOWBALL = KP_PROG_OK + "- 后续章节候选项 ｜ 来源：范围护栏 ｜ 处置：暂缓 ｜ 触发条件：用户要求 ｜ 滚雪球候选\n"
# 排除侧夹具：清单排除 1、暂缓侧一致 → 仅排除侧 HOLD-CROSS
KPLIST_EXCL = (KPLIST_OK
               .replace("- KP-02-02 ｜ 递归初步 ｜ 小节 2 ｜ 前置：KP-02-01 ｜ 来源：目录 1.2 ｜ 状态：未讲（已会：摸底题 2 全对，2026-10-11）",
                        "- KP-02-02 ｜ 递归初步 ｜ 小节 2 ｜ 前置：KP-02-01 ｜ 来源：目录 1.2 ｜ 状态：排除")
               .replace("总 4 ｜ 未讲 2 ｜ 已讲 1 ｜ 暂缓 1 ｜ 排除 0",
                        "总 4 ｜ 未讲 1 ｜ 已讲 1 ｜ 暂缓 1 ｜ 排除 1"))
# 场景 A 夹具：区块仅一条「处置：经用户确认排除」+ 清单暂缓 0/排除 1（两侧口径对齐 → 零 HOLD-CROSS）
KP_PROG_ONLYEXCL = KP_PROG_OK.replace("处置：暂缓", "处置：经用户确认排除")
KPLIST_ONLYEXCL_OK = (KPLIST_OK
                      .replace("状态：暂缓", "状态：排除")
                      .replace("总 4 ｜ 未讲 2 ｜ 已讲 1 ｜ 暂缓 1 ｜ 排除 0",
                               "总 4 ｜ 未讲 2 ｜ 已讲 1 ｜ 暂缓 0 ｜ 排除 1"))
# 场景 C 夹具：区块仅一条排除条目 + 清单排除 0（暂缓 0）→ 恰 1 条排除侧 HOLD-CROSS
KPLIST_NOEXCL = (KPLIST_OK
                 .replace("- KP-03-01 ｜ 高级主题 ｜ 小节 3 ｜ 前置：KP-02-01 ｜ 来源：目录 1.3 ｜ 状态：暂缓",
                          "- KP-03-01 ｜ 高级主题 ｜ 小节 3 ｜ 前置：KP-02-01 ｜ 来源：目录 1.3 ｜ 状态：未讲")
                 .replace("总 4 ｜ 未讲 2 ｜ 已讲 1 ｜ 暂缓 1 ｜ 排除 0",
                          "总 4 ｜ 未讲 3 ｜ 已讲 1 ｜ 暂缓 0 ｜ 排除 0"))
# 重叠夹具：同一条目既「滚雪球候选」又「处置：排除」（暂缓基数须互斥判定、不得为负）
KP_PROG_OVERLAP = KP_PROG_OK.replace(
    "- 高级主题 KP-03-01 ｜ 来源：S2 对照 ｜ 处置：暂缓 ｜ 触发条件：用户要求",
    "- 争议项 ｜ 来源：范围护栏 ｜ 处置：经用户确认排除 ｜ 触发条件：无 ｜ 滚雪球候选")
KPLIST_OVERLAP_OK = (KPLIST_OK
                     .replace("状态：暂缓", "状态：排除")
                     .replace("暂缓 1 ｜ 排除 0", "暂缓 0 ｜ 排除 1"))
# 粒度夹具：暂缓条目一行并两个 KP 编号（应对应清单 KP 行、一行一条目）
KP_PROG_MULTIKP = KP_PROG_OK.replace(
    "- 高级主题 KP-03-01 ｜ 来源：S2 对照 ｜ 处置：暂缓 ｜ 触发条件：用户要求",
    "- 高级主题 KP-03-01、KP-03-02 ｜ 来源：S2 对照 ｜ 处置：暂缓 ｜ 触发条件：用户要求")


def selftest():
    ok = True
    with tempfile.TemporaryDirectory() as td:
        # ① 规范态：小写 [x] + 判分记录 → 通过
        d = Path(td) / "good"
        (d / "exercises").mkdir(parents=True)
        (d / "progress.md").write_text(GOOD, encoding="utf-8")
        (d / "exercises" / "01-变量-2026-01-01.md").write_text("## 作答与判分\n- 题1：Good", encoding="utf-8")
        r = check(d)
        ok = ok and r["ok"]

        # ② 无证据 + 复习返回点缺失 → 拦截
        d2 = Path(td) / "bad"
        d2.mkdir()
        (d2 / "progress.md").write_text(BAD, encoding="utf-8")
        r2 = check(d2)
        codes = [e["code"] for e in r2["errors"]]
        ok = ok and (not r2["ok"]) and ("E-NO-EVIDENCE" in codes) and ("E-REVIEW-ORIGIN" in codes)

        # ③ S0 态（无「起点」）→ 通过（不误报）
        d3 = Path(td) / "s0"
        d3.mkdir()
        (d3 / "progress.md").write_text(S0, encoding="utf-8")
        r3 = check(d3)
        ok = ok and r3["ok"]

        # ④ 大写 [X] + 判分记录 → 通过且无 W-NO-ROUTE
        d4 = Path(td) / "upper"
        (d4 / "exercises").mkdir(parents=True)
        (d4 / "progress.md").write_text(UPPER, encoding="utf-8")
        (d4 / "exercises" / "01-极限-2026-01-01.md").write_text("## 作答与判分\n- 题1：Good", encoding="utf-8")
        r4 = check(d4)
        ok = ok and r4["ok"] and not any(w["code"] == "W-NO-ROUTE" for w in r4["warnings"])

        # ⑤ 大写 [X] 但无判分记录 → 被拦截
        d5 = Path(td) / "upper-noex"
        d5.mkdir()
        (d5 / "progress.md").write_text(UPPER, encoding="utf-8")
        r5 = check(d5)
        ok = ok and (not r5["ok"]) and any(e["code"] == "E-NO-EVIDENCE" for e in r5["errors"])

        # ⑥ 单位数编号判分记录 → 通过（宽容匹配，不假阳性）
        d6 = Path(td) / "single"
        (d6 / "exercises").mkdir(parents=True)
        (d6 / "progress.md").write_text(UPPER, encoding="utf-8")
        (d6 / "exercises" / "1-极限-2026-01-01.md").write_text("## 作答与判分\n- 题1：Good", encoding="utf-8")
        r6 = check(d6)
        ok = ok and r6["ok"]

        # ⑦ v2.3 覆盖完整性：结课 + 区块齐整 + 审计记录 → 通过且无覆盖告警
        d7 = Path(td) / "done-ok"
        (d7 / "exercises").mkdir(parents=True)
        (d7 / "progress.md").write_text(DONE_OK, encoding="utf-8")
        (d7 / "exercises" / "01-词法-2026-01-01.md").write_text("## 作答与判分\n- 题1：Good", encoding="utf-8")
        (d7 / "exercises" / "02-句法-2026-01-02.md").write_text("## 作答与判分\n- 题1：Good", encoding="utf-8")
        r7 = check(d7)
        c7 = r7["coverage"]
        ok = ok and r7["ok"]
        ok = ok and not any(w["code"] == "W-NO-COVERAGE-AUDIT" for w in r7["warnings"])
        ok = ok and c7["hold_section_present"] and c7["hold_count"] == 2
        ok = ok and c7["hold_unparsed"] == 0 and c7["route_undone"] == 0
        ok = ok and c7["audit_record_found"] is True

        # ⑧ 结课缺区块 + 缺审计记录 → 仅 W-NO-COVERAGE-AUDIT（warning 非 error，不阻断旧任务）
        d8 = Path(td) / "done-noaudit"
        d8.mkdir()
        (d8 / "progress.md").write_text(
            DONE_OK.split("## 暂缓与范围外")[0] + "## 学习日志\n- 2026-10-10：讲了词法\n", encoding="utf-8")
        (d8 / "exercises").mkdir()
        (d8 / "exercises" / "01-词法-2026-01-01.md").write_text("## 作答与判分\n- 题1：Good", encoding="utf-8")
        (d8 / "exercises" / "02-句法-2026-01-02.md").write_text("## 作答与判分\n- 题1：Good", encoding="utf-8")
        r8 = check(d8)
        ok = ok and r8["ok"]  # warning 不影响 ok
        ok = ok and sum(1 for w in r8["warnings"] if w["code"] == "W-NO-COVERAGE-AUDIT") == 2

        # ⑨ 畸形暂缓条目（有竖线缺字段）→ W-UNPARSED-HOLD 且非 error、计 0
        d9 = Path(td) / "hold-bad"
        d9.mkdir()
        (d9 / "progress.md").write_text(HOLD_BAD, encoding="utf-8")
        r9 = check(d9)
        c9 = r9["coverage"]
        ok = ok and r9["ok"]  # 畸形条目是告警不是错误
        ok = ok and any(w["code"] == "W-UNPARSED-HOLD" for w in r9["warnings"])
        ok = ok and c9["hold_unparsed"] == 1 and c9["hold_count"] == 0

        # ⑩ 旧任务（S3 进行中、无暂缓区块）→ 不产生覆盖告警（零迁移）
        r4c = r4["coverage"]
        ok = ok and not r4c["hold_section_present"]
        ok = ok and not any(w["code"].startswith("W-NO-COVERAGE") or w["code"] == "W-UNPARSED-HOLD"
                            for w in r4["warnings"])

        # ⑪ v2.4 KP 清单规范态：无任何 KP 告警；hold_count 与清单摘要暂缓数交叉一致
        d11 = Path(td) / "kp-ok"
        d11.mkdir()
        (d11 / "progress.md").write_text(KP_PROG_OK, encoding="utf-8")
        (d11 / "exercises").mkdir()
        (d11 / "exercises" / "01-变量-2026-01-01.md").write_text("## 作答与判分\n- 题1：Good", encoding="utf-8")
        (d11 / "知识清单.md").write_text(KPLIST_OK, encoding="utf-8")
        r11 = check(d11)
        ok = ok and r11["ok"]
        ok = ok and not any(w["code"].startswith("W-KP") or w["code"] == "W-UNPARSED-KP"
                            for w in r11["warnings"])
        ok = ok and r11["coverage"]["hold_count"] == 1

        # ⑫ 小节勾选「已掌握」× 清单该节 KP 全「未讲」→ W-KP-STATE-MISMATCH（warning 非 error）
        d12 = Path(td) / "kp-state"
        d12.mkdir()
        (d12 / "progress.md").write_text(KP_PROG_OK, encoding="utf-8")
        (d12 / "exercises").mkdir()
        (d12 / "exercises" / "01-变量-2026-01-01.md").write_text("## 作答与判分\n- 题1：Good", encoding="utf-8")
        (d12 / "知识清单.md").write_text(
            KPLIST_OK.replace("状态：已讲", "状态：未讲").replace("未讲 2 ｜ 已讲 1", "未讲 3 ｜ 已讲 0"),
            encoding="utf-8")
        r12 = check(d12)
        ok = ok and r12["ok"]
        ok = ok and sum(1 for w in r12["warnings"] if w["code"] == "W-KP-STATE-MISMATCH") == 1
        ok = ok and sum(1 for w in r12["warnings"]
                        if w["code"].startswith("W-KP") or w["code"] == "W-UNPARSED-KP") == 1

        # ⑬ 指针存在但文件不存在 → W-KP-LIST-MISSING（warning 非 error）
        d13 = Path(td) / "kp-missing"
        d13.mkdir()
        (d13 / "progress.md").write_text(KP_PROG_OK, encoding="utf-8")
        (d13 / "exercises").mkdir()
        (d13 / "exercises" / "01-变量-2026-01-01.md").write_text("## 作答与判分\n- 题1：Good", encoding="utf-8")
        r13 = check(d13)
        ok = ok and r13["ok"]
        ok = ok and sum(1 for w in r13["warnings"] if w["code"] == "W-KP-LIST-MISSING") == 1
        ok = ok and sum(1 for w in r13["warnings"]
                        if w["code"].startswith("W-KP") or w["code"] == "W-UNPARSED-KP") == 1

        # ⑭ 清单畸形（状态非法/前置引用不存在/行缺段/覆盖范围行畸形）→ 4 条 W-UNPARSED-KP，
        #    畸形行不计入摘要计数（有效行 2 条与摘要总 2 一致，不触发 W-KP-SUMMARY-MISMATCH）
        d14 = Path(td) / "kp-bad"
        d14.mkdir()
        (d14 / "progress.md").write_text(KP_PROG_NA, encoding="utf-8")
        (d14 / "知识清单.md").write_text(KPLIST_BAD, encoding="utf-8")
        r14 = check(d14)
        ok = ok and r14["ok"]
        ok = ok and sum(1 for w in r14["warnings"] if w["code"] == "W-UNPARSED-KP") == 4
        ok = ok and not any(w["code"].startswith("W-KP-") for w in r14["warnings"])

        # ⑮ 覆盖摘要行计数与逐行实际不符 → W-KP-SUMMARY-MISMATCH（warning 非 error）
        d15 = Path(td) / "kp-sum"
        d15.mkdir()
        (d15 / "progress.md").write_text(KP_PROG_OK, encoding="utf-8")
        (d15 / "exercises").mkdir()
        (d15 / "exercises" / "01-变量-2026-01-01.md").write_text("## 作答与判分\n- 题1：Good", encoding="utf-8")
        (d15 / "知识清单.md").write_text(
            KPLIST_OK.replace("总 4 ｜ 未讲 2 ｜ 已讲 1", "总 4 ｜ 未讲 1 ｜ 已讲 2"), encoding="utf-8")
        r15 = check(d15)
        ok = ok and r15["ok"]
        ok = ok and sum(1 for w in r15["warnings"] if w["code"] == "W-KP-SUMMARY-MISMATCH") == 1
        ok = ok and sum(1 for w in r15["warnings"]
                        if w["code"].startswith("W-KP") or w["code"] == "W-UNPARSED-KP") == 1

        # ⑯ 清单摘要暂缓数 ≠ progress.md 暂缓条目数 → W-KP-HOLD-CROSS（必改④交叉告警）
        d16 = Path(td) / "kp-cross"
        d16.mkdir()
        (d16 / "progress.md").write_text(KP_PROG_NOHOLD, encoding="utf-8")
        (d16 / "exercises").mkdir()
        (d16 / "exercises" / "01-变量-2026-01-01.md").write_text("## 作答与判分\n- 题1：Good", encoding="utf-8")
        (d16 / "知识清单.md").write_text(KPLIST_OK, encoding="utf-8")
        r16 = check(d16)
        ok = ok and r16["ok"]
        ok = ok and sum(1 for w in r16["warnings"] if w["code"] == "W-KP-HOLD-CROSS") == 1
        ok = ok and sum(1 for w in r16["warnings"]
                        if w["code"].startswith("W-KP") or w["code"] == "W-UNPARSED-KP") == 1

        # ⑰ v2.4 零迁移：无指针旧任务不触发任何 KP 告警（B7 零新增误报锚点）
        for rr in (r4, r6, r9):
            ok = ok and not any(w["code"].startswith("W-KP") or w["code"] == "W-UNPARSED-KP"
                                for w in rr["warnings"])

        # ── 边界与宽容性断言（⑱–㉔） ──

        def _kp_warnings(r):
            return [w for w in r["warnings"] if w["code"].startswith("W-KP") or w["code"] == "W-UNPARSED-KP"]

        def _mk(task_text, list_text, make_list=True, with_ex=True, list_name="知识清单.md"):
            d = Path(td) / ("r2-" + str(len(list(Path(td).iterdir()))))
            d.mkdir()
            (d / "progress.md").write_text(task_text, encoding="utf-8")
            if with_ex:
                (d / "exercises").mkdir()
                (d / "exercises" / "01-变量-2026-01-01.md").write_text("## 作答与判分\n- 题1：Good", encoding="utf-8")
            if make_list:
                (d / list_name).write_text(list_text, encoding="utf-8")
            return d

        # ⑱ 半角括号「未讲(已会：…)」→ 不报畸形、按未讲基值计数、零 KP 告警
        r18 = check(_mk(KP_PROG_OK, KPLIST_HALFPAREN))
        ok = ok and r18["ok"] and not _kp_warnings(r18)

        # ⑲ rows 空 + 摘要行有值 → W-KP-SUMMARY-MISMATCH（矛盾态不静默）
        r19 = check(_mk(KP_PROG_NA, KPLIST_EMPTY_NOSUM))
        ok = ok and r19["ok"]
        ok = ok and sum(1 for w in _kp_warnings(r19) if w["code"] == "W-KP-SUMMARY-MISMATCH") == 1

        # ⑳ 重复编号 → W-UNPARSED-KP 且重复行不计入摘要计数（无 SUMMARY-MISMATCH）
        r20 = check(_mk(KP_PROG_NA, KPLIST_DUP))
        ok = ok and r20["ok"]
        ok = ok and sum(1 for w in _kp_warnings(r20) if w["code"] == "W-UNPARSED-KP") == 1
        ok = ok and not any(w["code"] == "W-KP-SUMMARY-MISMATCH" for w in _kp_warnings(r20))

        # ㉑ 滚雪球候选（设计性范围外）不计入 HOLD-CROSS 比对基数：护栏场景零误报
        r21 = check(_mk(KP_PROG_SNOWBALL, KPLIST_OK))
        ok = ok and r21["ok"]
        ok = ok and not any(w["code"] == "W-KP-HOLD-CROSS" for w in _kp_warnings(r21))
        ok = ok and r21["coverage"]["hold_count"] == 2

        # ㉒ 指针指向同名目录 → W-KP-LIST-MISSING 级 W 告警，不裸崩、正常 JSON、exit 0
        r22 = check(_mk(KP_PROG_OK, KPLIST_OK, make_list=False))
        d22 = Path(r22["task_dir"])
        (d22 / "知识清单.md").mkdir()  # 同名目录
        r22 = check(d22)
        ok = ok and r22["ok"]
        ok = ok and sum(1 for w in _kp_warnings(r22) if w["code"] == "W-KP-LIST-MISSING") == 1

        # ㉓ 覆盖范围行：半角冒号宽容解析零告警；含「覆盖范围」字样但残缺 → W-UNPARSED-KP
        r23a = check(_mk(KP_PROG_OK, KPLIST_HALFCOLON))
        ok = ok and r23a["ok"] and not _kp_warnings(r23a)
        r23b = check(_mk(KP_PROG_OK, KPLIST_COVERBROKEN))
        ok = ok and r23b["ok"]
        ok = ok and any(w["code"] == "W-UNPARSED-KP" and "覆盖范围" in w["message"]
                        for w in _kp_warnings(r23b))

        # ㉔ STATE-MISMATCH 豁免：整节摸底「已会」括注（全角）+ 该节勾选已掌握 → 不告警
        r24 = check(_mk(KP_PROG_OK, KPLIST_ALLBOTTOM))
        ok = ok and r24["ok"]
        ok = ok and not any(w["code"] == "W-KP-STATE-MISMATCH" for w in _kp_warnings(r24))

        # ㉕ 排除侧交叉核对：清单排除 1 vs 区块处置排除 0（暂缓侧一致）→ 仅排除侧 HOLD-CROSS
        r25 = check(_mk(KP_PROG_OK, KPLIST_EXCL))
        ok = ok and r25["ok"]
        ok = ok and sum(1 for w in _kp_warnings(r25) if w["code"] == "W-KP-HOLD-CROSS") == 1
        ok = ok and sum(1 for w in _kp_warnings(r25)
                        if w["code"].startswith("W-KP") or w["code"] == "W-UNPARSED-KP") == 1

        # ㉖ 判分文件存在但内容无「判分/作答」→ W-EMPTY-EVIDENCE（warning 级不阻断）
        d26 = Path(td) / "empty-ev"
        (d26 / "exercises").mkdir(parents=True)
        (d26 / "progress.md").write_text(GOOD, encoding="utf-8")
        (d26 / "exercises" / "01-变量-2026-01-01.md").write_text("# 空文件", encoding="utf-8")
        r26 = check(d26)
        ok = ok and r26["ok"]  # warning 不影响 ok
        ok = ok and any(w["code"] == "W-EMPTY-EVIDENCE" for w in r26["warnings"])

        # ㉗ 场景 A：区块仅排除条目 + 清单暂缓 0/排除 1（两侧口径对齐）→ 零 HOLD-CROSS、零 KP 告警
        r27 = check(_mk(KP_PROG_ONLYEXCL, KPLIST_ONLYEXCL_OK))
        ok = ok and r27["ok"] and not _kp_warnings(r27)

        # ㉘ 场景 C：区块仅排除条目 + 清单排除 0 → 恰 1 条且为排除侧（暂缓侧不误报）
        r28 = check(_mk(KP_PROG_ONLYEXCL, KPLIST_NOEXCL))
        ok = ok and r28["ok"]
        cross28 = [w for w in _kp_warnings(r28) if w["code"] == "W-KP-HOLD-CROSS"]
        ok = ok and len(cross28) == 1 and "排除侧" in cross28[0]["message"]
        ok = ok and len(_kp_warnings(r28)) == 1

        # ㉙ 重叠条目（既滚雪球候选又处置排除）→ 设计性条目显式豁免、不计入集合；
        #     ID 集合口径下清单「排除 KP-03-01」在区块无对应对象 → 恰 1 条排除侧 HOLD-CROSS
        #     （旧 count 口径只比数量、看不出「对象不同」；此处改为按对象 ID 对账）
        r29 = check(_mk(KP_PROG_OVERLAP, KPLIST_OVERLAP_OK))
        ok = ok and r29["ok"]
        cross29 = [w for w in _kp_warnings(r29) if w["code"] == "W-KP-HOLD-CROSS"]
        ok = ok and len(cross29) == 1 and "排除侧" in cross29[0]["message"]

        # ㉚ 粒度核对：暂缓条目一行并两个 KP 编号 → W-UNPARSED-HOLD（粒度不符，提示须与清单 KP 行一一对应）
        r30 = check(_mk(KP_PROG_MULTIKP, KPLIST_OK))
        ok = ok and r30["ok"]
        ok = ok and any(w["code"] == "W-UNPARSED-HOLD" and "粒度" in w["message"] for w in r30["warnings"])
        # ㉛ F01：S1（诊断摸底，进行中）缺「起点」→ 合法（不误报 E-MISSING-FIELD）；
        #      进入 S2（计划确认中）仍缺「起点」→ 拦停（诊断结论未落盘）
        d31 = Path(td) / "s1-noqidian"
        d31.mkdir()
        (d31 / "progress.md").write_text(
            "# 学习任务：诊断中\n- 数据根：<root>\n- 当前阶段：诊断摸底\n"
            "- 类型：知识型\n- 学科族：数学类\n- 目标：自测\n", encoding="utf-8")
        r31 = check(d31)
        ok = ok and r31["ok"] and not any(e["code"] == "E-MISSING-FIELD" for e in r31["errors"])
        d31b = Path(td) / "s2-noqidian"
        d31b.mkdir()
        (d31b / "progress.md").write_text(
            "# 学习任务：计划中\n- 数据根：<root>\n- 当前阶段：计划确认中\n"
            "- 类型：知识型\n- 学科族：数学类\n- 目标：自测\n", encoding="utf-8")
        r31b = check(d31b)
        ok = ok and (not r31b["ok"]) and any(e["code"] == "E-MISSING-FIELD" for e in r31b["errors"])

        # ㉜ F04：复习来源阶段 =「已完成」合法（已完成任务可复习并返回）；任意字符串被拒
        d32 = Path(td) / "rev-done"
        d32.mkdir()
        (d32 / "progress.md").write_text(
            "# 学习任务：复习\n- 数据根：<root>\n- 当前阶段：复习巩固\n- 复习来源阶段：已完成\n"
            "- 类型：知识型\n- 学科族：数学类\n- 目标：自测\n- 起点：入门\n", encoding="utf-8")
        r32 = check(d32)
        ok = ok and r32["ok"]
        d32b = Path(td) / "rev-bad"
        d32b.mkdir()
        (d32b / "progress.md").write_text(
            "# 学习任务：复习\n- 数据根：<root>\n- 当前阶段：复习巩固\n- 复习来源阶段：随便写\n"
            "- 类型：知识型\n- 学科族：数学类\n- 目标：自测\n- 起点：入门\n", encoding="utf-8")
        r32b = check(d32b)
        ok = ok and (not r32b["ok"]) and any(e["code"] == "E-REVIEW-ORIGIN" for e in r32b["errors"])

        # ㉝ F03：只含「作答/判分」模板（占位行）——历史模式 warning，放行模式 E-EMPTY-EVIDENCE。
        # 用 data-and-recovery.md 的判分记录模板（含 <学员答案> / Again 占位）直接作夹具。
        d33 = Path(td) / "rel-template"
        (d33 / "exercises").mkdir(parents=True)
        (d33 / "progress.md").write_text(UPPER, encoding="utf-8")
        (d33 / "exercises" / "01-极限-2026-01-01.md").write_text(
            "## 作答与判分（模板）\n- 题 1：作答「<学员答案>」｜信心=<1-5>｜<Good|Hard|Again>\n",
            encoding="utf-8")
        r33_hist = check(d33)
        r33_rel = check(d33, release=True)
        ok = ok and r33_hist["ok"] and any(w["code"] == "W-EMPTY-EVIDENCE" for w in r33_hist["warnings"])
        ok = ok and (not r33_rel["ok"]) and any(e["code"] == "E-EMPTY-EVIDENCE" for e in r33_rel["errors"])
        # 真实作答证据（Good 行）在历史与放行模式下均放行。
        # R01 起放行模式还要求「复述通过」证据——故补齐复述清单；旧断言「仅一条 Good
        # 即放行」正是被验收判为误放行的行为，此处精确更新（非删断言）。
        d33c = Path(td) / "rel-real"
        (d33c / "exercises").mkdir(parents=True)
        (d33c / "progress.md").write_text(UPPER, encoding="utf-8")
        (d33c / "exercises" / "01-极限-2026-01-01.md").write_text(
            "## 作答与判分\n- 题 1：作答「-3」｜正确性=对｜独立性=独立｜调度档=Good\n"
            "## 复述检查清单\n- [x] 关键点1：极限定义\n- [x] 无事实性错误\n",
            encoding="utf-8")
        ok = ok and check(d33c, release=True)["ok"]

        # ㉞ F03：放行模式——阶段结课但学习路线仍有未勾选小节 → E-ROUTE-UNDONE
        d34 = Path(td) / "rel-undone"
        (d34 / "exercises").mkdir(parents=True)
        (d34 / "progress.md").write_text(
            "# 学习任务：结课未完成\n- 数据根：<root>\n- 当前阶段：结课\n"
            "- 类型：知识型\n- 学科族：数学类\n- 目标：自测\n- 起点：入门\n\n"
            "## 学习路线\n- [x] 1. 甲\n- [ ] 2. 乙\n", encoding="utf-8")
        (d34 / "exercises" / "01-甲-2026-01-01.md").write_text("## 作答与判分\n- 题1：Good", encoding="utf-8")
        r34 = check(d34, release=True)
        ok = ok and (not r34["ok"]) and any(e["code"] == "E-ROUTE-UNDONE" for e in r34["errors"])

        # ㉟ F08/F09 零迁移：progress.md 含可选新键（evt=）与「动作游标」行 →
        # 合法通过、无告警（脚本对未知可选字段零感知，旧任务加键不需迁移）
        d35 = Path(td) / "cursor"
        (d35 / "exercises").mkdir(parents=True)
        (d35 / "progress.md").write_text(
            "# 学习任务：可选新字段\n- 数据根：<root>\n- 当前阶段：逐节学习\n"
            "- 类型：技能型\n- 学科族：编程类\n- 目标：入门\n- 起点：零基础\n\n"
            "## 学习路线\n- [x] 1. 极限\n\n"
            "## 薄弱点\n- 某点：表现（S=3.0，D=3，last=2026-10-09，due=2026-10-10，信心=4，cw，evt=E1）\n\n"
            "## 下次续学\n- 动作游标：批改 ｜ 待回应：01-极限 题1 ｜ 最后提交：E1\n",
            encoding="utf-8")
        (d35 / "exercises" / "01-极限-2026-01-01.md").write_text(
            "## 作答与判分\n- 题 1：作答「x」｜信心=5｜Good\n", encoding="utf-8")
        r35 = check(d35)
        ok = ok and r35["ok"] and not r35["warnings"]

        # ═══ R01/R02 回归：结构化作答闸口 + 拟提交状态 + 增量机制 ═══
        def _mk2(name, progress_text, files=None):
            d = Path(td) / name
            d.mkdir()
            (d / "progress.md").write_text(progress_text, encoding="utf-8")
            for rel, txt in (files or {}).items():
                fp = d / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(txt, encoding="utf-8")
            return d

        PROG_S3 = ("# 学习任务：严格闸口\n- 数据根：<root>\n- 当前阶段：逐节学习\n"
                   "- 类型：技能型\n- 学科族：编程类\n- 目标：独立编程\n- 起点：零基础\n\n"
                   "## 学习路线\n- [x] 1. 变量\n")
        EV_OK = ("## 作答与判分\n- 题1：作答「3」｜正确性=对｜独立性=独立｜调度档=Good\n"
                 "## 复述检查清单\n- [x] 关键点1：变量\n- [x] 无事实性错误\n")

        def _codes(name, prog, ev, **kw):
            d = _mk2(name, prog, {"exercises/01-变量-2026-01-01.md": ev} if ev is not None else None)
            r = check(d, **kw)
            return r, [e["code"] for e in r["errors"]]

        # ㊱ 无学员答案（只有档位词）/ 只有标题 → E-NO-GRADED-ATTEMPT（旧：误放行）
        r36a, c36a = _codes("r01-no-answer", PROG_S3, "## 作答与判分\n- 题1：Good", release=True)
        ok = ok and (not r36a["ok"]) and "E-NO-GRADED-ATTEMPT" in c36a
        r36b, c36b = _codes("r01-header", PROG_S3, "## 作答与判分\n# 错题记录", release=True)
        ok = ok and (not r36b["ok"]) and "E-NO-GRADED-ATTEMPT" in c36b
        # ㊲ 全部答错/Again → E-ALL-FAILED；仅提示后全对 → E-HINT-ONLY
        r37a, c37a = _codes("r01-all-wrong", PROG_S3,
                            "## 作答与判分\n- 题1：作答「错误答案」｜正确性=错｜独立性=独立｜Again\n"
                            "- 复述：未通过", release=True)
        ok = ok and (not r37a["ok"]) and "E-ALL-FAILED" in c37a
        r37b, c37b = _codes("r01-hinted", PROG_S3,
                            "## 作答与判分\n- 题1：作答「3」｜正确性=对｜独立性=提示后｜调度档=Hard\n"
                            "- 复述：未通过", release=True)
        ok = ok and (not r37b["ok"]) and "E-HINT-ONLY" in c37b
        # ㊳ 独立正确但缺复述清单 → E-NO-RESTATEMENT；补齐复述清单 → 放行
        r38a, c38a = _codes("r01-no-restate", PROG_S3,
                            "## 作答与判分\n- 题1：作答「3」｜正确性=对｜独立性=独立｜调度档=Good",
                            release=True)
        ok = ok and (not r38a["ok"]) and "E-NO-RESTATEMENT" in c38a and "E-NO-GRADED-ATTEMPT" not in c38a
        r38b, _c38b = _codes("r01-valid", PROG_S3, EV_OK, release=True)
        ok = ok and r38b["ok"] and r38b["checked_lessons"] == [1]
        # ㊴ 结课/已完成：空路线 → E-NO-ROUTE-STRICT；不可解析路线 → E-NO-ROUTE-STRICT
        DONE_HEAD = ("# 学习任务：结课\n- 数据根：<root>\n- 当前阶段：已完成\n"
                     "- 类型：技能型\n- 学科族：编程类\n- 目标：x\n- 起点：零基础\n\n")
        r39a, c39a = _codes("r01-done-noroute", DONE_HEAD + "## 学习路线\n", None, release=True)
        ok = ok and "E-NO-ROUTE-STRICT" in c39a and "E-NO-FINAL-EXAM" in c39a
        r39b, c39b = _codes("r01-done-unparsed", DONE_HEAD + "## 学习路线\n- [x] 变量\n",
                            EV_OK, release=True)
        ok = ok and "E-NO-ROUTE-STRICT" in c39b
        # ㊵ 已完成且有路线与小节证据，但缺 99 综合测验 → E-NO-FINAL-EXAM；补齐后放行
        r40a, c40a = _codes("r01-done-nofinal", DONE_HEAD + "## 学习路线\n- [x] 1. 变量\n",
                            EV_OK, release=True)
        ok = ok and "E-NO-FINAL-EXAM" in c40a
        d40b = _mk2("r01-done-final", DONE_HEAD + "## 学习路线\n- [x] 1. 变量\n",
                    {"exercises/01-变量-2026-01-01.md": EV_OK,
                     "exercises/99-结课综合测验-2026-01-01.md": EV_OK})
        ok = ok and check(d40b, release=True)["ok"]
        # ㊶ 已完成但清单纳入口径下仍有「未讲」关键能力 KP → E-CORE-UNLEARNED
        KPLIST_CORE = ("# 知识清单：示例\n- 版本：1\n- 对照源：自拟总纲\n"
                       "- 排序规则：拓扑序\n- 覆盖范围：全量\n- 最近更新：2026-01-01\n"
                       "- 覆盖摘要：总 1 ｜ 未讲 1 ｜ 已讲 0 ｜ 暂缓 0 ｜ 排除 0\n\n"
                       "- KP-01-01 ｜ 变量 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 ｜ 状态：未讲\n")
        r41, c41 = _codes("r01-core", DONE_HEAD + "## 学习路线\n- [x] 1. 变量\n",
                          EV_OK, release=True)
        # 「知识清单」指针须写在元信息区（首个二级标题之前）才被解析——单独补齐并重校验
        d41 = Path(r41["task_dir"])
        prog41 = (d41 / "progress.md").read_text(encoding="utf-8")
        (d41 / "progress.md").write_text(
            prog41.replace("- 起点：零基础\n", "- 起点：零基础\n- 知识清单：知识清单.md\n"),
            encoding="utf-8")
        (d41 / "知识清单.md").write_text(KPLIST_CORE, encoding="utf-8")
        (d41 / "exercises" / "99-结课综合测验-2026-01-01.md").write_text(EV_OK, encoding="utf-8")
        r41 = check(d41, release=True)
        ok = ok and (not r41["ok"]) and any(e["code"] == "E-CORE-UNLEARNED" for e in r41["errors"])
        # ㊷ 拟提交状态：同一磁盘状态（逐节学习、路线未完成）拟转「已完成」必须被拒
        PROG_UNDONE = PROG_S3.replace("- [x] 1. 变量", "- [ ] 1. 变量")
        d42 = _mk2("r02-proposed", PROG_UNDONE, {"exercises/01-变量-2026-01-01.md": EV_OK})
        r42_disk = check(d42, release=True)
        ok = ok and r42_disk["ok"] and r42_disk["proposed_state_supplied"] is False
        ok = ok and any(w["code"] == "W-NO-PROPOSED-STATE" for w in r42_disk["warnings"])
        r42_prop = check(d42, release=True, proposed={"phase": "已完成"})
        ok = ok and (not r42_prop["ok"]) and r42_prop["phase"] == "已完成"
        ok = ok and any(e["code"] == "E-ROUTE-UNDONE" for e in r42_prop["errors"])
        # ㊸ S2 闸口：缺 00 摸底证据 → E-NO-DIAGNOSTIC；起点非法 → E-ENUM-START
        S2_HEAD = ("# 学习任务：计划\n- 数据根：<root>\n- 当前阶段：计划确认中\n"
                   "- 类型：知识型\n- 学科族：数学类\n- 目标：自测\n")
        r43a, c43a = _codes("r01-s2-nodiag", S2_HEAD + "- 起点：入门\n\n## 学习路线\n- [ ] 1. 甲\n",
                            None, release=True)
        ok = ok and "E-NO-DIAGNOSTIC" in c43a
        r43b, c43b = _codes("r01-s2-badstart", S2_HEAD + "- 起点：随意伪造\n\n## 学习路线\n- [ ] 1. 甲\n",
                            None, release=True)
        d43b = Path(r43b["task_dir"])
        (d43b / "exercises").mkdir(exist_ok=True)
        (d43b / "exercises" / "00-摸底-2026-01-01.md").write_text(EV_OK, encoding="utf-8")
        r43b = check(d43b, release=True)
        c43b = [e["code"] for e in r43b["errors"]]
        ok = ok and "E-ENUM-START" in c43b and "E-NO-DIAGNOSTIC" not in c43b
        # ㊹ 增量机制：旧小节证据为坏模板、本次新增小节证据合格 → --changed-lessons 只校新增
        PROG_TWO = PROG_S3.replace("- [x] 1. 变量\n", "- [x] 1. 变量\n- [x] 2. 循环\n")
        d44 = _mk2("r02-changed", PROG_TWO,
                   {"exercises/01-变量-2026-01-01.md": "## 作答与判分\n- 题1：<答案>｜<Good|Again>",
                    "exercises/02-循环-2026-01-01.md": EV_OK})
        ok = ok and not check(d44, release=True)["ok"]          # 整档校验收旧模板阻断
        r44 = check(d44, release=True, proposed={"changed_lessons": [2]})
        ok = ok and r44["ok"] and r44["checked_lessons"] == [2]
        # ㊺ CLI：--proposed-phase / --changed-lessons 端到端可用且语义一致
        ok = ok and main([str(d42), "--release", "--proposed-phase", "已完成"]) == 1
        ok = ok and main([str(d44), "--release", "--changed-lessons", "2"]) == 0
        ok = ok and main([str(d44), "--release", "--changed-lessons", "x"]) == 2

        # ═══ R09 回归：稳定 ID 匹配 + 按对象 ID 对账 + 游标悬空 ═══
        # ㊻ 路线 lesson_id 与判分证据声明的 lesson_id 不一致（重排后串用他节）→ E-EVIDENCE-ID-MISMATCH
        d46 = _mk2("r09-idmismatch",
                   PROG_S3.replace("- [x] 1. 变量\n",
                                   "- [x] 1. 循环（lesson_id=L-B）\n- [ ] 2. 变量（lesson_id=L-A）\n"),
                   {"exercises/01-变量-2026-01-01.md":
                    "# 变量，lesson_id=L-A\n## 作答与判分\n- attempt_id=A-1，题1：作答「3」｜Good"})
        r46 = check(d46, release=True)
        ok = ok and any(e["code"] == "E-EVIDENCE-ID-MISMATCH" for e in r46["errors"])
        # ㊼ 按 ID 正匹配容忍重排：序号与文件名不符但 lesson_id 一致 → 正常匹配、不误报
        d47 = _mk2("r09-idmatch",
                   PROG_S3.replace("- [x] 1. 变量\n", "- [x] 1. 循环（lesson_id=L-A）\n"),
                   {"exercises/01-变量-2026-01-01.md":
                    "# 变量，lesson_id=L-A\n## 作答与判分\n- attempt_id=A-1，题1：作答「3」｜正确性=对"
                    "｜独立性=独立｜调度档=Good\n## 复述检查清单\n- [x] 关键点1\n- [x] 无事实性错误\n"})
        r47 = check(d47, release=True)
        ok = ok and r47["ok"] and not any(e["code"] == "E-EVIDENCE-ID-MISMATCH"
                                          for e in r47["errors"])
        # ㊽ 数量相同但对象不同 → W-KP-HOLD-CROSS（旧口径只比数量、直接放行）
        d48 = _mk2("r09-kpids", KP_PROG_OK, {"知识清单.md":
                   "# 知识清单：示例\n- 版本：1\n- 对照源：自拟总纲\n- 排序规则：拓扑序\n"
                   "- 覆盖范围：全量\n- 最近更新：2026-01-01\n"
                   "- 覆盖摘要：总 1 ｜ 未讲 0 ｜ 已讲 0 ｜ 暂缓 1 ｜ 排除 0\n\n"
                   "- KP-90-01 ｜ 甲 ｜ 小节 90 ｜ 前置：  ｜ 来源：总纲 ｜ 状态：暂缓\n"})
        r48 = check(d48, release=True)
        ok = ok and any(w["code"] == "W-KP-HOLD-CROSS" and "仅清单暂缓" in w["message"]
                        for w in r48["warnings"])
        # ㊾ 游标指向不存在的判分记录/提交 ID → E-CURSOR-DANGLING（放行模式，两条各计）
        d49 = _mk2("r09-cursor",
                   PROG_S3 + "\n## 下次续学\n- 动作游标：批改 ｜ 待回应：不存在.md 题99"
                             " ｜ 最后提交：NO-SUCH-ATTEMPT\n",
                   {"exercises/01-变量-2026-01-01.md": EV_OK})
        r49 = check(d49, release=True)
        ok = ok and sum(1 for e in r49["errors"] if e["code"] == "E-CURSOR-DANGLING") == 2
        # 合法游标（引用存在的文件与已出现的 evt）→ 不报悬空
        d49b = _mk2("r09-cursor-ok",
                    PROG_S3 + "\n## 下次续学\n- 动作游标：批改 ｜ 待回应：01-变量 题1 ｜ 最后提交：E1\n"
                    "\n## 薄弱点\n- 某点（S=3.0，D=3，last=2026-01-01，due=2026-01-02，信心=4，cw，evt=E1）\n",
                    {"exercises/01-变量-2026-01-01.md": EV_OK})
        r49b = check(d49b, release=True)
        ok = ok and not any(e["code"] == "E-CURSOR-DANGLING" for e in r49b["errors"])

    print(("OK " if ok else "FAIL ") + "progress_check --selftest")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="progress_check.py")
    ap.add_argument("task_dir", nargs="?", default=None)
    ap.add_argument("--release", action="store_true",
                    help="放行校验：本次新增掌握/结课/跨阶段前的严格检查"
                         "（结构化作答与闸口、空证据、未完成/不可解析路线、缺综合测验、关键能力未讲拦停）")
    ap.add_argument("--proposed-phase", default=None,
                    help="拟提交的目标阶段（校验该候选状态，如 --release --proposed-phase 已完成）")
    ap.add_argument("--staged", default=None,
                    help="拟提交的 progress.md 候选快照文件（校验拟提交对象而非磁盘现状）")
    ap.add_argument("--changed-lessons", default=None,
                    help="本次新增掌握的小节编号（逗号/顿号分隔），限定严格证据校验范围"
                         "（旧资料不阻断无关新节；不给则校验全部已掌握小节）")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.task_dir:
        ap.print_usage()
        return 2
    proposed = {}
    if args.proposed_phase:
        proposed["phase"] = args.proposed_phase
    if args.staged:
        staged = Path(args.staged)
        if not staged.is_file():
            print("[learn-task-workflow] --staged 指向的拟提交快照不存在或不是文件：" + str(staged),
                  file=sys.stderr)
            return 2
        proposed["text"] = staged.read_text(encoding="utf-8", errors="replace")
    if args.changed_lessons:
        nums = []
        for tok in re.split(r"[,，、\s]+", args.changed_lessons):
            if not tok:
                continue
            if not tok.isdigit():
                print("[learn-task-workflow] --changed-lessons 只接受小节编号（数字）：" + tok,
                      file=sys.stderr)
                return 2
            nums.append(int(tok))
        proposed["changed_lessons"] = nums
    result = check(args.task_dir, release=args.release, proposed=proposed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
