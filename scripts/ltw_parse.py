#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""progress.md 与课程体系.md 的共享行级解析原语（单一实现）。

task_index / progress_check / kp_sort / scheduler 复用同一实现，防止字段行、
路线行、暂缓条目、KP 行的解析口径在各脚本间分叉。只收行级与字符级原语；
清单**文件级**读取（头行键、覆盖摘要、IO 语义）因各脚本返回契约不同而留在
各自模块，行级解析一律走本模块。

契约唯一来源 contracts/rules.json（缺失/畸形即结构化失败，fail closed）。
"""
from __future__ import annotations

import math
import re
from datetime import date

import rule_contract

_C = rule_contract.load_or_exit()["constants"]

# ── 行内注释剥离（唯一实现，全仓共用）──
# 模板与人工书写常在字段行尾用「两个以上空格 + #」挂解说（见 references/data.md 各模板）。
# 该解说属于文档层，**不是字段值的一部分**；不剥离会让「节目标线」等字段拿到脏值，
# 且在未被枚举/格式校验覆盖的字段（当前节、目标）上**静默通过闸口**。
# 只认「2 个以上空格 + #」这一个形态：
#   - 单空格 + #（如「学完 # 标记」）不剥离，保留为值的一部分；
#   - 值内嵌的 #（C#、第#3章）前面没有空格，天然不受影响。
INLINE_COMMENT_RE = re.compile(r"\s{2,}#.*$")


def strip_inline_comment(text):
    """去掉字段行尾「2 个以上空格 + #…」的解说注释；不影响值内嵌的 #。"""
    return INLINE_COMMENT_RE.sub("", text or "")


# progress.md 字段行 / 课程体系节路线勾选行 / 「下次续学」目位置行
FIELD_RE = re.compile(r"^-\s*([^：:]+)[：:]\s*(.*)$")


def parse_field_line(line):
    """FIELD_RE 匹配 + 行尾注释剥离，返回 (键, 值) 或 None。

    三个消费者（progress_check / task_index / scheduler）统一走这里，
    避免「谁来剥离注释」在各脚本间分叉。
    """
    m = FIELD_RE.match(line)
    if not m:
        return None
    return m.group(1).strip(), strip_inline_comment(m.group(2)).strip()


ROUTE_RE = re.compile(r"^-\s*\[([xX ])\]\s*(\d+)\.\s*(.*)$")
BLOCK_RE = re.compile(r"(?:已讲到第\s*)?(\d+)\s*/\s*(\d+)\s*目(?!\s*[标录])")
# 「暂缓与范围外」条目应含的三段（自由文本 + 竖线分段，不做枚举硬校验）
HOLD_KEYS = ("来源", "处置", "触发条件")
# KP 编号：行首锚定版（KP_ID_RE）供整字段校验；未锚定版（KP_ID_ANY_RE）供归一化与文本抽取
KP_ID_RE = re.compile(r"^KP-(\d+)-(\d+)$")
KP_ID_ANY_RE = re.compile(r"KP-(\d+)-(\d+)")

ENUM_KP_STATUS = tuple(_C["kp"]["states"])
ENUM_KP_TYPE = tuple(_C["kp"]["types"])
ENUM_KP_VISUAL = tuple(_C["kp"]["visual_tasks"])


def normalize_kp_id(kid):
    """KP 编号归一化：单位数与补零别名归一到两位规范形（KP-1-1 ≡ KP-01-01）。

    仅用于**重复检测与集合/前置匹配**（等价类比较，两侧同走本函数）；
    排序输出与落盘仍保留原书写形态。
    """
    m = KP_ID_ANY_RE.fullmatch(kid or "")
    if not m:
        return kid
    return "KP-{0:02d}-{1:02d}".format(int(m.group(1)), int(m.group(2)))


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


def hold_entry_malformed(body):
    """有竖线分段但缺 来源/处置/触发条件 任一段 → 畸形（纯自由文本行不判畸形）。"""
    if "｜" not in body and "|" not in body:
        return False
    for key in HOLD_KEYS:
        if not re.search(key + r"[：:]", body):
            return True
    return False


def hold_disposition_excluded(body):
    """处置段含「排除」→ 该条按排除处置计（hold_count 仍含该条目；暂缓口径 = hold_count − excluded_count）。"""
    if "｜" not in body and "|" not in body:
        return False
    for seg in re.split(r"[｜|]", body):
        seg = seg.strip()
        if seg.startswith("处置"):
            return "排除" in seg
    return False


def parse_kp_optional(segs):
    """解析目行可选字段（类型/视觉任务/引入）；无字段返回 (None, [], "")，畸形返回 None。

    `引入：` 登记该目首次引入的术语（R46 出题前术语对账账本，分号/顿号分隔），
    解析为原文整段（切分交由 prereq_check），不参与枚举校验。"""
    kp_type = None
    visual_tasks = []
    intro = ""
    for seg in segs:
        if seg.startswith("引入：") or seg.startswith("引入:"):
            if intro:
                return None
            intro = re.split(r"[：:]", seg, maxsplit=1)[1].strip()
            if not intro:
                return None
        elif seg.startswith("类型：") or seg.startswith("类型:"):
            if kp_type is not None:
                return None
            raw = re.split(r"[：:]", seg, maxsplit=1)[1].strip()
            if raw not in ENUM_KP_TYPE:
                return None
            kp_type = raw
        elif seg.startswith("视觉任务：") or seg.startswith("视觉任务:"):
            if visual_tasks:
                return None
            raw = re.split(r"[：:]", seg, maxsplit=1)[1].strip()
            if not raw:
                return None
            for tok in re.split(r"[,，、/\s]+", raw):
                if not tok:
                    continue
                if tok not in ENUM_KP_VISUAL or tok in visual_tasks:
                    return None
                visual_tasks.append(tok)
            if not visual_tasks:
                return None
        else:
            return None
    return kp_type, visual_tasks, intro


def parse_kp_row(segs):
    """课程体系目行六段（KP编号｜目名｜所属节｜前置｜来源｜状态）+ 可选类型/视觉任务 → dict。

    可选字段缺失返回 type=None、visual_tasks=[]（目行未声明时统一闸口）；畸形返回 None。
    附带 sec_decl（显式「节 N」序号，供与编号契约「编号节序 = 所属节」比对）
    与 bottom_note（摸底「已会」括注探测，带括注行豁免 W-KP-STATE-MISMATCH）。
    """
    if len(segs) < 6:
        return None
    kid, title, section, pre, source, status = segs[:6]
    optional = parse_kp_optional(segs[6:])
    if optional is None:
        return None
    kp_type, visual_tasks, intro = optional
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
    # K02：解析显式所属节的序号（仅当形如「节 N」时）
    sec_decl = None
    sec_m = re.fullmatch(r"节\s*(\d+)", section)
    if sec_m:
        sec_decl = int(sec_m.group(1))
    # 摸底「已会」括注探测（全角/半角括号双兼容）
    bottom_note = raw_status.startswith("已会") or re.match(r"^未讲[(（]\s*已会", raw_status) is not None
    # v9.12.0（R54）：「需巩固」标注探测（`已讲（需巩固：依据，日期）`）——基值仍为已讲，仅作只读计数
    needs_consolidation = "需巩固" in raw_status
    return {"id": kid, "sec": int(m.group(1)), "no": int(m.group(2)),
            "sec_decl": sec_decl, "prereqs": prereqs, "status": base,
            "bottom_note": bottom_note, "needs_consolidation": needs_consolidation,
            "type": kp_type, "visual_tasks": visual_tasks,
            "intro": intro}

# ---------------------------------------------------------------------------
# 条目元数据解析（T04）：META_KEYS / META_TOKEN_RES / parse_meta 与括注拆分
# ---------------------------------------------------------------------------
# 下沉理由：due-queue（scheduler）与闸口（progress_check）都要读同一条「顺延=」
# 判据。放在 scheduler 会让校验脚本反向依赖调度脚本；各写一份正则则是同一判据
# 写两遍。本模块已是 4 脚本共用的行级解析层，判据只在这里实现一次。
#
# 调度域常数（S/D 值域）在此按契约取用：元数据解析的 fullmatch 纪律要求「越域即坏
# token」，而这个值域的唯一来源就是 contracts/rules.json 的 scheduler 块。
_S = _C["scheduler"]
S_MAX = float(_S["s_max"])
S_MIN = float(_S["s_min"])
D_MIN, D_MAX = 1.0, 10.0             # FSRS-6 的 D 值域（连续，无粒度要求）

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _finite_pos(tok, hi=S_MAX):
    """解析有限正浮点（S 等）；非数值 / NaN / Inf / <=0 / >hi 一律返回 None。

    坏元数据（如 S=1..2）不得让整队列裸崩——解析失败按「缺省」处理，
    由调用方走默认链并标 migrated，不静默崩溃。有效域 (0, hi]，默认 hi=S_MAX。
    """
    try:
        v = float(tok)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v) or v <= 0 or v > hi:
        return None
    return v


def _in_range(tok, lo, hi):
    """解析 [lo,hi] 内浮点（D 等）；失败或越界返回 None。NaN/Inf 一律 None。"""
    try:
        v = float(tok)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v) or v < lo or v > hi:
        return None
    return v


def _valid_iso(tok):
    """是否为合法真实日历日期（YYYY-MM-DD）；非法（如 2026-02-30）返回 None。"""
    if not DATE_RE.match(tok or ""):
        return None
    try:
        date.fromisoformat(tok)
    except ValueError:
        return None
    return tok


# 输入行已由 parse_progress_sections 剥去「- 」前缀
WRONG_LINE_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2})\]\s*(.*)$")
META_KEYS = ("S=", "D=", "last=", "due=", "信心=", "evt=", "attempt_id=", "子类=", "错因=", "级=",
             "顺延=")
# ↑ v2.6：与 META_TOKEN_RES 的「键=」形态一一对应（v2.5 的 attempt_id= 现已补解析器）；
#   cw/顽固 为无值标记，拆分判定改由 _looks_like_meta 按整段括注逐 token 可解析判定，
#   避免普通中文括注（如「抄自 cw 笔记」）因子串命中被误拆。
#   此前不被拆出，导致同一次作答的投影无法归组合并。
# v2.8：追加「顺延=」——票 58 定的干预留痕计数，此前未进白名单，写了就逐条报
#   W-META-INVALID，等于「已定的语义没有落点」。
# 元数据逐键严格格式（分隔后整 token fullmatch）：只认合法前缀会把 S=3oops 截成 3、
# 信心=50 截成 5，把坏内容当有效观测——v2.4 起一律 fullmatch，坏 token 显式记入
# invalid_tokens 并降级（走缺省链），不再「截前缀修正」。
META_TOKEN_RES = (
    ("S", re.compile(r"S=(\S+)"), lambda g: _finite_pos(g, S_MAX)),
    ("D", re.compile(r"D=(\S+)"), lambda g: _in_range(g, D_MIN, D_MAX)),
    ("last", re.compile(r"last=(\S+)"), _valid_iso),
    ("due", re.compile(r"due=(\S+)"), _valid_iso),
    ("错因", re.compile(r"错因=(\S+)"),
     lambda g: g if g in ("知识性", "理解性", "技巧性") else None),
    ("子类", re.compile(r"子类=(\S+)"), lambda g: g),
    ("级", re.compile(r"级=(\S+)"), lambda g: g if g in ("A", "B", "C") else None),
    ("evt", re.compile(r"evt=([A-Za-z0-9_\-]+)"), lambda g: g),
    ("attempt_id", re.compile(r"attempt_id=([A-Za-z0-9_\-]+)"), lambda g: g),
    # 顺延：非负整数，fullmatch 纪律同其他键。坏值（顺延=abc / 顺延=-1）走
    # invalid_tokens → 按缺省链继续、不硬拒，与既有坏值口径一致。
    ("顺延", re.compile(r"顺延=(\d+)"), lambda g: int(g)),
)
# 空区占位标记：薄弱点/错题本/归档区无内容时按文档写「无」，解析器须跳过，不得当作坏数据
# 整行「无+括注」形态（如「无（暂无错题）」）同为占位；「无法/无向」等真实知识点开头不受影响
NONE_MARKS = ("无", "无。", "（暂无）", "(暂无)")
NONE_RE = re.compile(r"无[（(][^（）()]*[）)]")


def parse_progress_sections(text):
    """提取「最近更新」字段与薄弱点/错题本/保持复习三区的条目行（纯文本解析）。"""
    section = None
    recent_update = None
    weak_lines = []
    wrong_lines = []
    retention_lines = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if section is None:
            fv = parse_field_line(line.strip())
            if fv and fv[0] == "最近更新":
                recent_update = fv[1]
            continue
        if section == "薄弱点" and line.strip().startswith("- "):
            weak_lines.append(line.strip()[2:].strip())
        elif section == "错题本" and line.strip().startswith("- "):
            wrong_lines.append(line.strip()[2:].strip())
        elif section == "保持复习" and line.strip().startswith("- "):
            retention_lines.append(line.strip()[2:].strip())
    return recent_update, weak_lines, wrong_lines, retention_lines


def parse_meta(meta_text):
    """解析全角括号 / 「元数据：」段内的 键=值 与无值标记（cw/顽固）。

    v2.4：分隔后**逐 token fullmatch**，坏 token（重复键、畸形值、越域）不截前缀，
    一律记入 invalid_tokens 并保持该键为 None（走缺省链），由调用方告警披露。
    """
    meta = {"S": None, "D": None, "last": None, "due": None, "信心": None,
            "cw": False, "顽固": False, "错因": None, "子类": None, "级": None, "evt": None,
            "attempt_id": None, "顺延": None,
            "invalid_tokens": [], "dup_keys": [], "信心_retro": False}
    tokens = [t for t in re.split(r"[，,;；\s]+", meta_text or "") if t]
    seen = set()
    for tok in tokens:
        if tok == "cw":
            meta["cw"] = True
            continue
        if tok == "顽固":
            meta["顽固"] = True
            continue
        # 信心单独处理：区分「数值原信心」「回顾性时序标志」「重复键」「坏值」
        m = re.fullmatch(r"信心=(\S+)", tok)
        if m:
            g = m.group(1)
            if "信心" in seen:
                meta["dup_keys"].append("信心")      # 同一条目重复信心 → 身份歧义
                meta["invalid_tokens"].append(tok)
            else:
                seen.add("信心")
                if re.fullmatch(r"[1-5]", g):
                    meta["信心"] = int(g)
                elif g in ("回顾性", "回顾"):
                    meta["信心_retro"] = True        # 文档定义的合法时序标志，非坏 token
                else:
                    meta["invalid_tokens"].append(tok)
            continue
        matched = False
        for key, pat, conv in META_TOKEN_RES:
            m = pat.fullmatch(tok)
            if not m:
                continue
            matched = True
            if key in seen:
                meta["dup_keys"].append(key)         # 重复键 → 标坏 + 记入歧义键
                meta["invalid_tokens"].append(tok)
                break
            seen.add(key)
            value = conv(m.group(1))
            if value is None:
                meta["invalid_tokens"].append(tok)   # 畸形/越域值 → 标坏，保持缺省
            else:
                meta[key] = value
            break
        if not matched and "=" in tok:
            meta["invalid_tokens"].append(tok)       # 未知键=值 → 标坏
    return meta


def _looks_like_meta(candidate):
    """括注是否为元数据段：逐 token（分词口径同 parse_meta）判定——

    「键=」形态的键必须 ∈ META_KEYS，cw/顽固 须为独立 token；出现任何
    非元数据词（如「抄自 cw 笔记」的「抄自」）即判普通括注，不拆。
    """
    toks = [t for t in re.split(r"[，,;；\s]+", candidate) if t]
    if not toks:
        return False
    for tok in toks:
        if tok in ("cw", "顽固"):
            continue
        key = tok.split("=", 1)[0] if "=" in tok else None
        if key is not None and (key + "=") in META_KEYS:
            continue
        return False
    return True


def split_weak_item(line):
    """薄弱点行：尾部全角/半角括注为元数据段时拆出（推荐全角，半角兜底），否则整行是条目文本。

    拆分判定用 _looks_like_meta（v2.6）：整段括注逐 token 均为元数据形态才拆，
    纯子串命中不再触发；混合散文与元数据的括注不拆（元数据留在条目名，不静默拆碎）。
    """
    for close_ch, open_ch in (("）", "（"), (")", "(")):
        if line.endswith(close_ch) and open_ch in line:
            idx = line.rfind(open_ch)
            candidate = line[idx + 1:-1]
            if _looks_like_meta(candidate):
                return line[:idx].strip(), candidate
    return line, None


def split_wrong_item(rest):
    """错题本行：取首个「｜/|」前的题目段作条目名；行尾「元数据：…」段拆出（全角/半角双兼容）。"""
    m = re.search(r"元数据[：:](.*)$", rest)
    if m:
        rest = rest[:m.start()].rstrip("｜| ").strip()
    return re.split(r"[｜|]", rest)[0].strip(), (m.group(1).strip() if m else None)
