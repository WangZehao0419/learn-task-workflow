#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scheduler.py - 间隔重复调度计算（自研简化双参数算法，非 FSRS/SM-2 标准实现；确定性，stdlib-only，只读）。

用途：learn-task-workflow v2.1 的确定性调度环节。判分（grade/信心/复述）与
落盘决策归模型；S'/D'/due 计算与到期排序归本脚本。脚本**只读计算**——
不改写任何用户数据，输出 JSON 到 stdout，落盘由宿主提供的文件写入/编辑能力负责（见
SKILL.md「判断归模型、数据归脚本」）。

子命令：
    next-interval  判分后算下一间隔：
        python scheduler.py next-interval --grade {again|hard|good|easy} \
            (--stability <S> | --new-card) --difficulty <D> \
            (--elapsed <N> | --last YYYY-MM-DD --today YYYY-MM-DD) \
            [--current-due YYYY-MM-DD] [--confidence <1-5>] [--init-shift {-1|0|1}]
        --elapsed 与 --last/--today 同传时数值必须一致（elapsed = today-last），
        不一致 exit 2；仅传 --elapsed（无 --last/--today）时 due 为 null，
        只回 interval_days，由模型以当日推算绝对日期——保证输出不依赖
        机器时钟、完全确定。同会话重复答对（elapsed=0）必须传 --current-due，
        返回原日期，不以重算值覆盖。
        **due 锚点**：新 due = 本次复习日期 today + interval_days；last 仅用于
        计算 elapsed（经过天数）与旧记录回显，**不**参与 due 起算——否则逾期卡
        复习后会把 due 算到过去日期。仅当 today 缺省（直连函数调用）时才回退用 last。

    due-queue      开节前查到期队列：
        python scheduler.py due-queue --root <数据根> [--slug <slug>] \
            --today YYYY-MM-DD [--all]
        读 <root>/<slug>/progress.md 的「薄弱点」「错题本」「保持复习」三区，
        按 cw 优先 → 最逾期优先 → due 早优先 → slug/条目名稳定序 排序。
        每条输出 reason（到期/逾期/优先级的人类可读说明）；schema=ltw-due-queue/3。
        默认只出 due <= today；--all 出全部（供收尾五件套报具体日期用）。
        v2.2：条目输出新增 错因/级/meta_default 三键（加键升 schema
        ltw-due-queue/3）；排序契约 cw→最逾期→due 早→稳定序 逐字不动。
        薄弱点/错题行元数据挂载点全角/半角双兼容（推荐全角，
        半角兜底），防模型写半角括号/竖线时元数据静默丢失。

    calibration    校准画像统计（只读快照口径，v2.4 收紧）：
        python scheduler.py calibration --root <数据根> [--slug <slug>]
        读 <root>/<slug>/progress.md 两区条目元数据（信心、cw、evt）。口径：
        先按 evt 归组并合并互补字段、冲突作废 → 再形成「合法观察」（可推算日期
        且无冲突）→ 才统计。分母只数合法观察中**显式**写有「信心=」的条目；
        分子 cw 只数「反馈前信心 ≥4 且 cw」的合法观察（cw 必须是同口径高信心
        错误观察的子集）。孤立 cw / 低信心 cw / 同 evt 冲突 → 单独告警并令
        rate_valid=false、不输出比率（不谎报）。dedup_mode 区分 by_evt /
        legacy_double_count / mixed（混排披露 evt_tagged_count、legacy_count）。
        快照口径不做时间窗，不需 --today。脚本只算不判，教学化呈现归模型。

公式契约（不得在调用侧自行更改；grade_base / init_s / d_drift / s_max / r_min /
    r_max / d_min / d_max / default_s / default_d 十项常数唯一来源 = 契约
    scheduler 块，此处不重复数值）:
    成功档（hard/good/easy）：
        factor = grade_base[档] * (1 + 0.35*(R-1)) * (1.3 - 0.1*D)
        R = clamp(elapsed/S, r_min, r_max)
        S' = max(S*factor, S+0.5)，上限 s_max
    失败档（again）：S' = max(1.0, S*0.3)
    难度漂移：again / hard / easy / good 各取 d_drift[档]，夹 [d_min, d_max]（0.5 粒度）
    新卡：初始 S 取 init_s[档]；初始 D 取 default_d + --init-shift
          （顺向检索 -1，默认 0，反向问/迁移 +1）
    round 一律四舍五入 0.5 进位（int(x+0.5)），规避银行家舍入歧义。
    信心度仅回显，不进公式（cw 惩罚已由 grade=again 承载，避免双重惩罚）。
    有效域（所有计算入口先验，NaN/Inf 一律拒绝、exit 2）：S ∈ (0, s_max]，
    D ∈ [d_min, d_max] 且 0.5 粒度，elapsed 有限且 ≥0（R 已夹紧，长中断不放大间隔）；
    日期加法越界（如 9999-12-31 + 间隔）同样结构化拒绝，不裸崩、不输出非有限数
    （json.dumps allow_nan=False）。

约定：
    --root 显式传数据根，不依赖 cwd（沿用脚本调用约定）。
    幂等：同输入同输出；脚本不写任何文件（可用文本检索能力验证无写盘调用）。

退出码：0 正常 / 1 数据根缺失或非法 / 2 用法或参数错误（失败显式报错，不谎报成功）
"""

import argparse
import json
import math
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

import rule_contract
from ltw_parse import FIELD_RE


class ScheduleError(ValueError):
    """调度参数/范围错误：统一结构化拒绝（exit 2），不让异常栈成为外部协议。"""


# 调度常数唯一来源：contracts/rules.json（缺失/畸形即结构化失败）。
_CONSTANTS = rule_contract.load_or_exit()["constants"]
_C = _CONSTANTS["scheduler"]
_SCHEMAS = _CONSTANTS["schemas"]
GRADE_BASE = dict(_C["grade_base"])
INIT_S = dict(_C["init_s"])
D_DRIFT = dict(_C["d_drift"])
S_MAX = float(_C["s_max"])
R_MIN, R_MAX = float(_C["r_min"]), float(_C["r_max"])
D_MIN, D_MAX = float(_C["d_min"]), float(_C["d_max"])
ELAPSED_INF = float("inf")   # 经过天数只要求「有限且 ≥0」：R=elapsed/S 已夹在 [0.25,2.0]，
# 故长中断（如 10 年）不会放大间隔，无需人为上界（长中断兼容）。
DATE_MIN_ORD = date.min.toordinal()
DATE_MAX_ORD = date.max.toordinal()
DEFAULT_S = float(_C["default_s"])
DEFAULT_D = int(_C["default_d"])
DEFAULT_CAUSE = "知识性"  # v2.2：错因缺省枚举（仅脚本输出侧占位回显，模型不得盲补）
DEFAULT_LEVEL = "B"       # v2.2：级缺省枚举（同上）

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def fail(msg):
    """用法/参数错误：stderr 显式说明 + exit 2，不静默退化。"""
    print("[learn-task-workflow] 参数错误：" + msg, file=sys.stderr)
    sys.exit(2)


def round_half_up(x):
    """四舍五入 0.5 进位（int(x+0.5)），规避 Python 银行家舍入歧义。"""
    return int(x + 0.5)


def norm_num(x):
    """整数化的浮点输出为 int（3.0 -> 3），其余保持 float。"""
    if isinstance(x, float) and x.is_integer():
        return int(x)
    return x


def _finite_pos(tok, hi=S_MAX):
    """解析有限正浮点（S 等）；非数值 / NaN / Inf / <=0 / >hi 一律返回 None。

    坏元数据（如 `S=1..2`）不得让整队列裸崩——解析失败按「缺省」处理，
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


def _half_step(v):
    """D 须为 0.5 粒度；None（解析失败）视为不合规。"""
    if v is None:
        return False
    return abs(v * 2 - round(v * 2)) < 1e-9


def require_finite(value, name, lo, hi):
    """CLI 计算入口统一有限值+范围校验（纵深防御：NaN/Inf/越界一律拒绝）。

    `nan <= 0` 为 False 会绕过旧的正数判断，故必须先 `math.isfinite` 再比范围。
    """
    if not math.isfinite(value):
        raise ScheduleError(name + " 必须是有限数值（NaN/Inf 拒绝），收到：" + str(value))
    if value < lo or value > hi:
        raise ScheduleError(
            name + " 须在 [" + str(lo) + "," + str(hi) + "]，收到：" + str(value))
    return value


def safe_add_days(anchor_iso, days):
    """日期加法带上界检查；越界返回 None（不含法结果），不抛异常。

    `days` 可能来自坏元数据（如 S=1e308），`date + timedelta` 会 OverflowError
    或 ValueError：统一在此转成「不可推算」，由调用方走告警降级。
    """
    try:
        anchor = date.fromisoformat(anchor_iso)
        ord_new = anchor.toordinal() + int(days)
    except (TypeError, ValueError, OverflowError):
        return None
    if ord_new < DATE_MIN_ORD or ord_new > DATE_MAX_ORD:
        return None
    return date.fromordinal(ord_new).isoformat()


def _valid_iso(tok):
    """是否为合法真实日历日期（YYYY-MM-DD）；非法（如 2026-02-30）返回 None。"""
    if not DATE_RE.match(tok or ""):
        return None
    try:
        date.fromisoformat(tok)
    except ValueError:
        return None
    return tok


def clamp_r(elapsed, stability):
    """R = elapsed/S 夹在 [0.25, 2.0]。"""
    return max(R_MIN, min(R_MAX, elapsed / stability))


def next_interval(grade, stability=None, difficulty=None, elapsed=None,
                  last=None, today=None, confidence=None, init_shift=0,
                  new_card=False, current_due=None):
    """纯计算函数：同输入同输出，不碰文件、不取当前时间。

    返回输出 JSON（dict）。

    同会话重复抑制：elapsed=0 且答对时只刷新召回（same_session=true），
    不增长 S、不改 D、不推迟 due。否则一天内反复刷题会把 massed practice
    误记成长期保持，违背「流利度 ≠ 存储强度」。既有卡此分支必须提供
    current_due，避免用重算值猜测并覆盖已有复习日。
    """
    same_session = False
    if new_card:
        s_old = None
        d_old = None
        s_new = INIT_S[grade]
        d_new = max(1, min(5, 3 + init_shift))
    else:
        # 纵深防御：纯函数入口亦校验有限值与范围（CLI 已校验，直连调用不绕过）。
        require_finite(stability, "stability", 1e-9, S_MAX)
        require_finite(difficulty, "difficulty", D_MIN, D_MAX)
        if grade != "again":
            require_finite(elapsed, "elapsed", 0.0, ELAPSED_INF)
        s_old = stability
        d_old = difficulty
        if grade == "again":
            s_new = max(1.0, stability * 0.3)
            d_new = max(1.0, min(5.0, difficulty + D_DRIFT[grade]))
        elif elapsed == 0:
            same_session = True
            if current_due is None:
                raise ScheduleError("同会话重复答对必须提供 --current-due，以保留原复习日")
            if not DATE_RE.match(current_due):
                raise ScheduleError("--current-due 必须是 YYYY-MM-DD 绝对日期，收到：" + str(current_due))
            try:
                date.fromisoformat(current_due)
            except ValueError as exc:
                raise ScheduleError("--current-due 不是合法日期：" + str(current_due)) from exc
            s_new = stability
            d_new = difficulty
        else:
            r = clamp_r(elapsed, stability)
            factor = GRADE_BASE[grade] * (1 + 0.35 * (r - 1)) * (1.3 - 0.1 * difficulty)
            s_new = max(stability * factor, stability + 0.5)
            d_new = max(1.0, min(5.0, difficulty + D_DRIFT[grade]))
        s_new = min(s_new, S_MAX)

    # 输出侧确定性舍入（4 位小数）：消除浮点噪音（如 6.6000000000000005），
    # 同输入同输出的 JSON 才逐字节稳定；不影响 interval_days 的 0.5 进位取整。
    s_new = round(s_new, 4)

    interval_days = round_half_up(s_new)
    # due 锚点 = 本次复习日期 today（逾期卡复习后必须从「今天」起算下一间隔），
    # 仅当 today 缺省时才回退用 last（兼容直连函数调用；CLI 侧要求成对传入）。
    anchor = today if today is not None else last
    if same_session:
        due = current_due
    elif anchor is not None:
        due = safe_add_days(anchor, interval_days)
        if due is None:
            raise ScheduleError(
                "下一复习日超出可表示日期范围（锚点 " + str(anchor)
                + " + " + str(interval_days) + " 天）")
    else:
        due = None

    return {
        "grade": grade,
        "stability_old": norm_num(s_old) if s_old is not None else None,
        "stability_new": norm_num(s_new),
        "difficulty_old": norm_num(d_old) if d_old is not None else None,
        "difficulty_new": norm_num(d_new),
        "interval_days": interval_days,
        "due": due,
        "confidence": confidence,
        "same_session": same_session,
        "migrated": False,
    }


# ---------------------------------------------------------------------------
# due-queue：读 progress.md 的薄弱点 / 错题本两区，只读排序输出
# ---------------------------------------------------------------------------

# 输入行已由 parse_progress_sections 剥去「- 」前缀
WRONG_LINE_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2})\]\s*(.*)$")
META_KEYS = ("S=", "D=", "last=", "due=", "信心=", "cw", "顽固", "evt=", "attempt_id=", "子类=")
# ↑ v2.5：`evt=`/`attempt_id=` 也列为元数据挂载标记——仅含 `evt=` 的弱项投影（无 S/D/cw）
#   此前不被拆出，导致同一次作答的投影无法归组合并。
# 元数据逐键严格格式（分隔后整 token fullmatch）：只认合法前缀会把 S=3oops 截成 3、
# 信心=50 截成 5，把坏内容当有效观测——v2.4 起一律 fullmatch，坏 token 显式记入
# invalid_tokens 并降级（走缺省链），不再「截前缀修正」。
META_TOKEN_RES = (
    ("S", re.compile(r"S=(\S+)"), lambda g: _finite_pos(g, S_MAX)),
    ("D", re.compile(r"D=(\S+)"),
     lambda g: _in_range(g, D_MIN, D_MAX) if _half_step(_in_range(g, D_MIN, D_MAX)) else None),
    ("last", re.compile(r"last=(\S+)"), _valid_iso),
    ("due", re.compile(r"due=(\S+)"), _valid_iso),
    ("错因", re.compile(r"错因=(\S+)"),
     lambda g: g if g in ("知识性", "理解性", "技巧性") else None),
    ("子类", re.compile(r"子类=(\S+)"), lambda g: g),
    ("级", re.compile(r"级=(\S+)"), lambda g: g if g in ("A", "B", "C") else None),
    ("evt", re.compile(r"evt=([A-Za-z0-9_\-]+)"), lambda g: g),
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
            m = FIELD_RE.match(line.strip())
            if m and m.group(1).strip() == "最近更新":
                recent_update = m.group(2).strip()
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
    一律记入 `invalid_tokens` 并保持该键为 None（走缺省链），由调用方告警披露。
    """
    meta = {"S": None, "D": None, "last": None, "due": None, "信心": None,
            "cw": False, "顽固": False, "错因": None, "子类": None, "级": None, "evt": None,
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


def split_weak_item(line):
    """薄弱点行：尾部全角/半角括号内含调度元数据时拆出（推荐全角，半角兜底），否则整行是条目文本。"""
    for close_ch, open_ch in (("）", "（"), (")", "(")):
        if line.endswith(close_ch) and open_ch in line:
            idx = line.rfind(open_ch)
            candidate = line[idx + 1:-1]
            if any(k in candidate for k in META_KEYS):
                return line[:idx].strip(), candidate
    return line, None


def split_wrong_item(rest):
    """错题本行：取首个「｜/|」前的题目段作条目名；行尾「元数据：…」段拆出（全角/半角双兼容）。"""
    m = re.search(r"元数据[：:](.*)$", rest)
    if m:
        rest = rest[:m.start()].rstrip("｜| ").strip()
    return re.split(r"[｜|]", rest)[0].strip(), (m.group(1).strip() if m else None)


def resolve_item(item_text, meta_text, kind, wrong_date, recent_update):
    """按默认链解析一条目：元数据 -> 条目日期/最近更新 -> 排除。

    返回 (queue_item 或 None, migrated)。None 表示无任何日期可推（W-UNPARSED-ITEM）。
    """
    meta = parse_meta(meta_text) if meta_text else parse_meta("")
    s_val = meta["S"] if meta["S"] is not None else DEFAULT_S
    d_val = meta["D"] if meta["D"] is not None else DEFAULT_D
    last = meta["last"]
    if last is None and kind in ("错题", "保持"):
        # 错题用出错日、保持复习用掌握日作缺省 last；坏 [日期] 前缀不参与推算。
        last = _valid_iso(wrong_date)
    if last is None:
        last = _valid_iso(recent_update) if recent_update else None
    due = meta["due"]
    if due is None and last is not None:
        # last 已经过 _valid_iso 校验；safe_add_days 处理越界/坏 S 的加法（返回 None）
        due = safe_add_days(last, round_half_up(s_val))
    migrated = not (meta["S"] is not None and meta["D"] is not None
                    and (meta["due"] is not None or meta["last"] is not None))
    if due is None:
        return None, migrated
    # 错因/级只对薄弱点/错题有意义；保持复习不参与这套问题元数据，避免假 meta_default。
    is_retention = kind == "保持"
    return {
        "item": item_text,
        "kind": kind,
        "due": due,
        "cw": meta["cw"],
        "顽固": meta["顽固"],
        "S": norm_num(s_val),
        "D": norm_num(d_val),
        "migrated": migrated,
        "错因": meta["错因"] if meta["错因"] is not None else ("" if is_retention else DEFAULT_CAUSE),
        "级": meta["级"] if meta["级"] is not None else ("" if is_retention else DEFAULT_LEVEL),
        "meta_default": (not is_retention) and (meta["错因"] is None or meta["级"] is None),
        "teach": meta["顽固"],
    }, migrated


def observations_from_text(text, slug):
    """把 progress.md 两区条目解析为「原始观察」列表（未去重、未统计）。

    返回 (raws, warnings)；queue 与 calibration 共用，防解析器漂移。
    raw = {item, kind, wrong_date, recent, meta, meta_text}
    """
    recent_update, weak_lines, wrong_lines, retention_lines = parse_progress_sections(text)
    raws = []
    warnings = []
    for line in weak_lines:
        if line in NONE_MARKS or NONE_RE.fullmatch(line):
            continue
        item_text, meta_text = split_weak_item(line)
        raws.append({"item": item_text, "kind": "薄弱点", "wrong_date": None,
                     "recent": recent_update, "meta": parse_meta(meta_text),
                     "meta_text": meta_text})
    for line in wrong_lines:
        if line in NONE_MARKS or NONE_RE.fullmatch(line):
            continue
        m = WRONG_LINE_RE.match(line)
        if not m:
            warnings.append("W-UNPARSED-ITEM: " + slug + " / " + line
                            + "（错题行缺 [YYYY-MM-DD] 前缀，不入队）")
            continue
        wrong_date, rest = m.group(1), m.group(2)
        item_text, meta_text = split_wrong_item(rest)
        raws.append({"item": item_text, "kind": "错题", "wrong_date": wrong_date,
                     "recent": recent_update, "meta": parse_meta(meta_text),
                     "meta_text": meta_text})
    for line in retention_lines:
        if line in NONE_MARKS or NONE_RE.fullmatch(line):
            continue
        m = WRONG_LINE_RE.match(line)
        # 掌握日期前缀推荐但不强制：省略时由元数据 last/due 或「最近更新」兜底；
        # 只有全部日期来源都缺失时，才由 resolve_item 统一告警不入队。
        mastery_date, rest = (m.group(1), m.group(2)) if m else ("", line)
        item_text, meta_text = split_wrong_item(rest)
        raws.append({"item": item_text, "kind": "保持", "wrong_date": mastery_date,
                     "recent": recent_update, "meta": parse_meta(meta_text),
                     "meta_text": meta_text})
    return raws, warnings


def queue_from_progress_texts(entries, today):
    """纯函数核心：从 (slug, progress.md 全文) 列表收集到期条目与告警。

    任何单条坏数据不崩溃；无可推算日期的条目输出 W-UNPARSED-ITEM 且不入队；
    坏元数据 token 输出 W-META-INVALID 并按缺省链继续（不静默「截前缀修正」）。
    """
    warnings = []
    queue = []
    for slug, text in entries:
        raws, w = observations_from_text(text, slug)
        warnings.extend(w)
        for r in raws:
            try:
                entry, _migrated = resolve_item(r["item"], r["meta_text"], r["kind"],
                                                r["wrong_date"], r["recent"])
            except (ValueError, OverflowError):
                entry = None   # 纵深防御：单条推算异常 → 降级告警，不拖垮整队列
            if entry is None:
                warnings.append("W-UNPARSED-ITEM: " + slug + " / " + r["item"]
                                + "（无可推算日期，不入队）")
                continue
            if r["meta"]["invalid_tokens"]:
                warnings.append("W-META-INVALID: " + slug + " / " + r["item"]
                                + "（坏 token 已按缺省链处理："
                                + "，".join(r["meta"]["invalid_tokens"]) + "）")
            entry["slug"] = slug
            queue.append(entry)
    resolved = []
    for entry in queue:
        try:
            due_d = date.fromisoformat(entry["due"])
        except (TypeError, ValueError):
            # due 非法（不应到达此处——resolve_item 已校验；作纵深防御）
            warnings.append("W-UNPARSED-ITEM: " + entry["slug"] + " / " + entry["item"]
                            + "（due 非合法日期，不入队）")
            continue
        entry["overdue_days"] = (today - due_d).days
        resolved.append(entry)
    return resolved, warnings


def read_progress_entries(root, slug_filter):
    """遍历任务目录读 progress.md 文本（只读），due-queue 与 calibration 共用。

    返回 (entries, warnings)；任何单文件读取失败降级为告警，不崩溃。
    解析逻辑（parse_progress_sections / parse_meta / split_* / resolve_item）
    两命令完全同源，防解析器漂移。
    """
    warnings = []
    root = Path(root)
    if slug_filter:
        task_dir = root / slug_filter
        prog = task_dir / "progress.md"
        if not prog.exists():
            warnings.append("W-PROGRESS-MISSING: " + slug_filter
                            + "（<root>/<slug>/progress.md 不存在，已跳过）")
            return [], warnings
        try:
            entries = [(slug_filter, prog.read_text(encoding="utf-8", errors="replace"))]
        except OSError:
            warnings.append("W-PROGRESS-UNREADABLE: " + slug_filter
                            + "（progress.md 不可读，已跳过）")
            return [], warnings
    else:
        entries = []
        for task_dir in sorted(p for p in root.iterdir()
                               if p.is_dir() and (p / "progress.md").exists()):
            try:
                entries.append((task_dir.name,
                                (task_dir / "progress.md").read_text(
                                    encoding="utf-8", errors="replace")))
            except OSError:
                warnings.append("W-PROGRESS-UNREADABLE: " + task_dir.name
                                + "（progress.md 不可读，已跳过）")
    return entries, warnings


def collect_queue(root, slug_filter, today):
    """遍历任务目录读 progress.md（只读），转交纯函数核心。任何坏数据不崩溃。"""
    entries, warnings = read_progress_entries(root, slug_filter)
    queue, parse_warnings = queue_from_progress_texts(entries, today)
    # 读取层告警（W-PROGRESS-*）并入输出，不因多任务枚举分支被丢弃。
    return queue, warnings + parse_warnings


def review_reason(entry):
    """生成人类可读的复习理由（确定性；不引入向量/遗忘曲线估算）。"""
    kind_label = {"薄弱点": "薄弱点", "错题": "错题", "保持": "保持复习"}.get(
        entry["kind"], entry["kind"])
    parts = [kind_label]
    if entry["cw"]:
        parts.append("自信但错，优先修复")
    if entry["顽固"]:
        parts.append("两次提示到梯底，优先重教")
    overdue = entry["overdue_days"]
    if overdue > 0:
        parts.append("已逾期 " + str(overdue) + " 天")
    elif overdue == 0:
        parts.append("今天到期")
    else:
        parts.append("还有 " + str(-overdue) + " 天到期")
    parts.append("S=" + str(entry["S"]) + "，D=" + str(entry["D"]))
    return "；".join(parts)


def due_queue_output(root, slug_filter, today, show_all):
    """默认只出 due <= today；--all 出全部。排序：cw 优先 -> 最逾期 -> due 早 -> 稳定序。"""
    queue, warnings = collect_queue(root, slug_filter, today)
    if not show_all:
        queue = [e for e in queue if e["overdue_days"] >= 0]
    ordered = sorted(queue, key=lambda e: (
        0 if e["cw"] else 1,
        -e["overdue_days"],
        e["due"],
        e["slug"],
        e["item"],
    ))
    fields = ("slug", "item", "kind", "due", "overdue_days", "cw", "顽固",
              "S", "D", "migrated", "teach")
    fields = fields + ("错因", "级", "meta_default", "reason")  # 加键回显；排序契约不动
    return {
        "schema": _SCHEMAS["due_queue"],
        "today": today.isoformat(),
        "root": str(Path(root)),
        "queue": [{**{k: e[k] for k in fields if k != "reason"},
                   "reason": review_reason(e)} for e in ordered],
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# calibration：校准画像统计（只读快照口径，v2.2 新增；与 due-queue 同源解析器）
# ---------------------------------------------------------------------------

def _merge_evt_group(group, slug, warnings):
    """把同一 evt 的多个投影合并为一个观察；互补字段合并，冲突则整个观察作废。

    返回 obs：{item, evt, 信心, cw, resolvable, entry, migrated, meta_default,
    invalid_tokens, conflict, raws_count}
    """
    raws = group["raws"]
    evt = group["evt"]
    confidences = sorted({r["meta"]["信心"] for r in raws
                          if r["meta"]["信心"] is not None})
    dup = any("信心" in r["meta"]["dup_keys"] for r in raws)  # 只有重复信心键才构成身份歧义
    retro = any(r["meta"]["信心_retro"] for r in raws)      # 回顾性时序标志（合法）
    # 冲突：数值信心不一致 / 重复信心键 / 「回顾性 × 数值原信心」并存（同一次作答不可能两副身份）
    conflict = len(confidences) > 1 or dup or (retro and bool(confidences))
    retro_only = retro and not confidences and not dup        # 纯回顾性观察：不入校准统计
    invalid_tokens = []
    for r in raws:
        invalid_tokens.extend(r["meta"]["invalid_tokens"])
    entry = None
    migrated = False
    for r in raws:   # 互补：任一投影可推算日期即可（优先第一个可推算的）
        e, mig = resolve_item(r["item"], r["meta_text"], r["kind"],
                              r["wrong_date"], r["recent"])
        if e is not None:
            entry, migrated = e, mig
            break
    if conflict:
        warnings.append("W-CONFIDENCE-AMBIGUOUS: " + slug + " / " + (evt or raws[0]["item"])
                        + "（信心/时序身份歧义：数值信心 "
                        + ("/".join(str(c) for c in confidences) if confidences else "无")
                        + ("；重复信心键" if dup else "")
                        + ("；回顾性与数值原信心并存" if (retro and confidences) else "")
                        + " → 该观察不可采信，不计入有效统计）")
    return {
        "item": raws[0]["item"],
        "evt": evt,
        "信心": confidences[0] if len(confidences) == 1 else None,
        "cw": any(r["meta"]["cw"] for r in raws),
        "resolvable": entry is not None,
        "migrated": migrated,
        "meta_default": (entry["meta_default"] if entry else False),
        "invalid_tokens": invalid_tokens,
        "conflict": conflict,
        "retro_only": retro_only,
        "raws_count": len(raws),
    }


def _group_by_evt(raws):
    """按 evt 归组：同 evt 的多投影合入一组；无 evt 的各成一组。保持稳定序。"""
    groups, index = [], {}
    for r in raws:
        evt = r["meta"]["evt"]
        if evt is None:
            groups.append({"evt": None, "raws": [r]})
        elif evt in index:
            index[evt]["raws"].append(r)
        else:
            g = {"evt": evt, "raws": [r]}
            index[evt] = g
            groups.append(g)
    return groups


def calibration_from_progress_texts(entries):
    """纯函数核心：从 (slug, progress.md 全文) 列表统计校准画像（快照口径）。

    口径（v2.4）：
      1. 先按 evt 归组、合并互补字段、冲突作废（`_merge_evt_group`）；
      2. 再形成「合法观察」——可推算日期 + 无冲突；
      3. 分母 `with_confidence` 只数合法观察中**显式**写有「信心=」的条目；
      4. 分子 `cw_count` 只数合法观察中「反馈前信心≥4 且 cw」的条目——
         cw 必须是同口径高信心错误观察的子集；孤立（无信心）/低信心 cw 单独告警，
         且只要存在孤立/低信心 cw 或冲突观察，`rate_valid=False` 且不输出比率（不谎报）。
    单条坏数据告警不崩溃，exit 0。
    """
    warnings = []
    per_slug = []
    for slug, text in entries:
        raws, w = observations_from_text(text, slug)
        # 保持复习是已掌握内容的调度账本，不是问题记录；校准画像只统计薄弱点/错题。
        raws = [r for r in raws if r["kind"] != "保持"]
        warnings.extend(w)
        groups = _group_by_evt(raws)
        obs = [_merge_evt_group(g, slug, warnings) for g in groups]

        stat = {
            "slug": slug,
            "total_items": len(obs),      # 归组后条目数（同 evt 多投影只计一次）
            "with_confidence": 0,
            "cw_count": 0,
            "orphan_cw_count": 0,         # cw 但缺显式信心（子集外孤立观察）
            "low_confidence_cw_count": 0,  # cw 但反馈前信心 <4
            "conflict_count": 0,
            "retro_excluded_count": 0,    # 纯回顾性（反馈后补报）观察：合法但不得计入原信心口径
            "overconfidence_rate": None,
            "rate_valid": False,
            "invalid_reason": None,
            "dedup_mode": "legacy_double_count",
            "evt_tagged_count": 0,
            "legacy_count": 0,
            "confidence_dist": {str(i): 0 for i in range(1, 6)},
            "cw_items": [],
            "migrated_count": 0,
            "unparsed_count": 0,
            "default_filled": 0,
        }
        tagged = sum(1 for r in raws if r["meta"]["evt"] is not None)
        legacy = len(raws) - tagged
        stat["evt_tagged_count"] = tagged
        stat["legacy_count"] = legacy
        if tagged and legacy:
            stat["dedup_mode"] = "mixed"
        elif tagged:
            stat["dedup_mode"] = "by_evt"
        else:
            stat["dedup_mode"] = "legacy_double_count"

        for o in obs:
            if o["invalid_tokens"]:
                warnings.append("W-META-INVALID: " + slug + " / " + o["item"]
                                + "（坏 token 已按缺省链处理："
                                + "，".join(o["invalid_tokens"]) + "）")
            if o["conflict"]:
                stat["conflict_count"] += 1
                continue
            if o["retro_only"]:
                # 文档定义：反馈后补报标「信心=回顾性」，**不用于 cw、不用于校准**。
                # 合法时序标志 → 不算坏数据、不进分母，也不产告警。
                stat["retro_excluded_count"] += 1
                continue
            if not o["resolvable"]:
                stat["unparsed_count"] += 1
                warnings.append("W-UNPARSED-ITEM: " + slug + " / " + o["item"]
                                + "（无可推算日期，不入统计）")
                continue
            if o["migrated"]:
                stat["migrated_count"] += 1
            if o["meta_default"]:
                stat["default_filled"] += 1
            conf = o["信心"]
            if o["cw"]:
                if conf is None:
                    stat["orphan_cw_count"] += 1
                    warnings.append("W-CW-ORPHAN: " + slug + " / " + o["item"]
                                    + "（cw 缺显式信心，不计入分子——不能与外层分母混算）")
                elif conf < 4:
                    stat["low_confidence_cw_count"] += 1
                    warnings.append("W-CW-LOWCONF: " + slug + " / " + o["item"]
                                    + "（cw 但反馈前信心 " + str(conf)
                                    + " < 4，不计入分子）")
                else:
                    stat["cw_count"] += 1
                    stat["cw_items"].append(o["item"])
            if conf is not None:
                stat["with_confidence"] += 1
                stat["confidence_dist"][str(conf)] += 1

        reasons = []
        if stat["conflict_count"]:
            reasons.append(str(stat["conflict_count"]) + " 条信心/时序身份歧义（已作废，见 W-CONFIDENCE-AMBIGUOUS）")
        if stat["orphan_cw_count"]:
            reasons.append(str(stat["orphan_cw_count"]) + " 条 cw 无显式信心（孤立观察）")
        if stat["low_confidence_cw_count"]:
            reasons.append(str(stat["low_confidence_cw_count"]) + " 条 cw 反馈前信心 <4")
        if stat["with_confidence"] == 0:
            reasons.append("合法观察中无显式信心条目（分母为 0）")
        if reasons:
            stat["overconfidence_rate"] = None
            stat["rate_valid"] = False
            stat["invalid_reason"] = "；".join(reasons)
        else:
            stat["overconfidence_rate"] = round(
                stat["cw_count"] / stat["with_confidence"], 4)
            stat["rate_valid"] = True
        per_slug.append(stat)
    return per_slug, warnings


def calibration_output(root, slug_filter):
    """组装 calibration 输出 JSON（只读；落盘由文件写入/编辑能力负责）。"""
    entries, warnings = read_progress_entries(root, slug_filter)
    per_slug, parse_warnings = calibration_from_progress_texts(entries)
    return {
        "schema": _SCHEMAS["calibration"],  # 含 orphan/low/conflict/dedup 计数与口径披露键
        "root": str(Path(root)),
        "per_slug": per_slug,
        "warnings": warnings + parse_warnings,
    }


def cmd_calibration(args):
    root = Path(args.root)
    if not root.exists() or not root.is_dir():
        print("[learn-task-workflow] 数据根不存在或不是目录：" + str(root)
              + "（应指向 <工作区根>/.learning）", file=sys.stderr)
        return 1
    print(json.dumps(calibration_output(root, args.slug),
                     ensure_ascii=False, indent=2, allow_nan=False))
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_date_str(value, label):
    if not DATE_RE.match(value or ""):
        fail(label + " 必须是 YYYY-MM-DD 绝对日期（禁相对日期），收到：" + str(value))
    try:
        return date.fromisoformat(value)
    except ValueError:
        fail(label + " 不是合法日期：" + str(value))


def check_difficulty(value):
    if not (1 <= value <= 5):
        fail("--difficulty 须在 [1,5]，收到：" + str(value))
    if abs(value * 2 - round(value * 2)) > 1e-9:
        fail("--difficulty 须为 0.5 粒度，收到：" + str(value))
    return float(value)


def cmd_next_interval(args):
    if args.new_card and args.stability is not None:
        fail("--new-card 与 --stability 不可同时使用")
    if not args.new_card and args.stability is None:
        fail("既有条目必须传 --stability（新卡请传 --new-card）")
    if args.new_card and args.difficulty is not None:
        fail("--new-card 时初始 D 由 --init-shift 决定，不传 --difficulty")
    stability = None
    difficulty = None
    if not args.new_card:
        stability = require_finite(args.stability, "--stability", 1e-9, S_MAX)
        if args.difficulty is None:
            fail("既有条目必须传 --difficulty")
        difficulty = check_difficulty(args.difficulty)
    elapsed = None
    last = None
    today = None
    has_pair = args.last is not None or args.today is not None
    if args.last is not None and args.today is None:
        fail("传 --last 时必须同时传 --today（YYYY-MM-DD）")
    if args.today is not None and args.last is None:
        fail("传 --today 时必须同时传 --last（YYYY-MM-DD）")
    if args.elapsed is not None and has_pair:
        # 允许同传（验收口径 P5-②），但数值必须一致；不一致才算混用冲突。
        elapsed_arg = require_finite(args.elapsed, "--elapsed", 0.0, ELAPSED_INF)
        last_d = parse_date_str(args.last, "--last")
        today_d = parse_date_str(args.today, "--today")
        if elapsed_arg != (today_d - last_d).days:
            fail("--elapsed（" + str(args.elapsed) + "）与 --last/--today 推算的"
                 "间隔（" + str((today_d - last_d).days) + " 天）不一致，属混用冲突")
    if args.elapsed is not None and not has_pair:
        elapsed = require_finite(args.elapsed, "--elapsed", 0.0, ELAPSED_INF)
    if has_pair:
        last_d = parse_date_str(args.last, "--last")
        today_d = parse_date_str(args.today, "--today")
        if today_d < last_d:
            fail("--today 早于 --last：" + args.today + " < " + args.last)
        last = last_d.isoformat()
        elapsed = (today_d - last_d).days   # 有限且 ≥0（日期已校验，today ≥ last）；R 会夹到 [0.25,2]
    elif args.elapsed is None and args.grade != "again":
        fail("成功档（hard/good/easy）必须提供 --elapsed 或 --last/--today 之一组")
    confidence = args.confidence
    if confidence is not None and not (1 <= confidence <= 5):
        fail("--confidence 须在 [1,5]，收到：" + str(confidence))
    if args.current_due is not None:
        parse_date_str(args.current_due, "--current-due")
    result = next_interval(args.grade, stability=stability, difficulty=difficulty,
                           elapsed=elapsed, last=last, today=args.today,
                           confidence=confidence, init_shift=args.init_shift,
                           new_card=args.new_card, current_due=args.current_due)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


def cmd_due_queue(args):
    today = parse_date_str(args.today, "--today")
    root = Path(args.root)
    if not root.exists() or not root.is_dir():
        print("[learn-task-workflow] 数据根不存在或不是目录：" + str(root)
              + "（应指向 <工作区根>/.learning）", file=sys.stderr)
        return 1
    result = due_queue_output(root, args.slug, today, args.all)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


def build_parser():
    ap = argparse.ArgumentParser(
        prog="scheduler.py",
        description="间隔重复调度计算（自研简化双参数算法，只读，不写任何文件）")
    ap.add_argument("--selftest", action="store_true",
                    help="运行内置自测（公式与队列契约断言）")
    sub = ap.add_subparsers(dest="cmd")
    p1 = sub.add_parser("next-interval", help="判分后算 S'/D'/due")
    p1.add_argument("--grade", required=True,
                    choices=["again", "hard", "good", "easy"])
    p1.add_argument("--stability", type=float, default=None)
    p1.add_argument("--new-card", action="store_true")
    p1.add_argument("--difficulty", type=float, default=None)
    p1.add_argument("--elapsed", type=float, default=None)
    p1.add_argument("--last", default=None)
    p1.add_argument("--today", default=None)
    p1.add_argument("--current-due", default=None)
    p1.add_argument("--confidence", type=int, default=None)
    p1.add_argument("--init-shift", type=int, default=0, choices=[-1, 0, 1])
    p1.set_defaults(func=cmd_next_interval)
    p2 = sub.add_parser("due-queue", help="查到期复习队列（只读）")
    p2.add_argument("--root", required=True)
    p2.add_argument("--slug", default=None)
    p2.add_argument("--today", required=True)
    p2.add_argument("--all", action="store_true")
    p2.set_defaults(func=cmd_due_queue)
    p3 = sub.add_parser("calibration", help="校准画像统计（只读快照口径，v2.2）")
    p3.add_argument("--root", required=True)
    p3.add_argument("--slug", default=None)
    p3.set_defaults(func=cmd_calibration)
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not getattr(args, "func", None):
        ap.print_help(file=sys.stderr)
        return 2
    try:
        return args.func(args)
    except ScheduleError as exc:
        # 统一结构化拒绝：参数/范围/日期越界一律 exit 2，异常栈不进外部协议
        fail(str(exc))
    except (ValueError, OverflowError) as exc:
        print("[learn-task-workflow] 计算失败：" + type(exc).__name__ + ": " + str(exc),
              file=sys.stderr)
        return 2


# ---------------------------------------------------------------------------
# selftest：公式与队列契约断言，先于实现钉死口径
# ---------------------------------------------------------------------------

FIX_A = """# 学习任务：甲
- 数据根：<root>
- 当前阶段：复习巩固
- 类型：知识型
- 学科族：理论概念类
- 目标：自测
- 起点：入门
- 最近更新：2026-10-05

## 学习路线
- [x] 1. 基础

## 薄弱点
- 自信但错点：负数溢出（S=2.0，D=3，last=2026-10-09，due=2026-10-09，信心=5，cw）
- 更逾期点：单位换算（S=3.0，D=3，last=2026-10-01，due=2026-10-04，信心=2）
- 顽固点：符号混淆（S=1.5，D=3.5，last=2026-10-09，due=2026-10-10，顽固）
- 默认链点：无元数据（v2 条目，靠「最近更新」补日期）
- 无日期点：无元数据

## 错题本
- [2026-10-08] 老错题 ｜ 错因：粗心 ｜ 元数据：S=1.0，D=4，last=2026-10-08，due=2026-10-09
"""

FIX_B = """# 学习任务：乙
- 数据根：<root>
- 当前阶段：逐节学习
- 类型：知识型
- 学科族：理论概念类
- 目标：自测
- 起点：入门

## 学习路线
- [ ] 1. 基础

## 薄弱点
- 完全无日期点：连「最近更新」都没有
"""

FIX_C = """# 学习任务：丙
- 数据根：<root>
- 当前阶段：复习巩固
- 类型：备考型
- 学科族：数学类
- 目标：自测
- 起点：入门
- 最近更新：2026-10-05

## 学习路线
- [ ] 1. 极限

## 薄弱点
- 完整点：极限定义（S=2.0，D=3，last=2026-10-09，due=2026-10-09，信心=4，cw，错因=理解性，级=A）

## 错题本
- [2026-10-09] 变式题 ｜ 错因：审题漏条件 ｜ 元数据：S=1.0，D=4，last=2026-10-09，due=2026-10-10，信心=2，错因=技巧性，级=B
"""

FIX_R = """# 学习任务：丁
- 数据根：<root>
- 当前阶段：复习巩固
- 类型：知识型
- 学科族：理论概念类
- 目标：自测
- 起点：入门
- 最近更新：2026-10-20

## 学习路线
- [x] 1. 变量
- [x] 2. 循环

## 保持复习
- [2026-10-12] 第 1 节 变量 ｜ 元数据：S=3.0，D=3，last=2026-10-12，due=2026-10-15
- [2026-10-13] 第 2 节 循环 ｜ 元数据：S=7.0，D=4，last=2026-10-18，due=2026-10-25
"""

FIX_R2 = """# 学习任务：戊
- 当前阶段：复习巩固
- 类型：知识型
- 学科族：理论概念类
- 目标：自测
- 起点：入门

## 保持复习
- 第 3 节 函数 ｜ 元数据：S=4.0，D=3，last=2026-10-18，due=2026-10-22
- 第 4 节 类 ｜ 元数据：S=3.0，D=3，last=2026-10-18
"""

FIX_R3 = """# 学习任务：己
- 当前阶段：复习巩固
- 类型：知识型
- 学科族：理论概念类
- 目标：自测
- 起点：入门

## 保持复习
- 第 5 节 无日期
"""


def approx(a, b, eps=1e-9):
    return abs(a - b) <= eps


def selftest():
    ok = True

    # 断言 1：good, S=3, D=3, elapsed=3 -> factor=2.2, S'=6.6, D'=3
    # due 锚点 = 本次复习日 today（2026-10-13）+ 7 天 = 2026-10-20；不再用 last 起算
    r = next_interval("good", stability=3.0, difficulty=3, elapsed=3,
                      last="2026-10-10", today="2026-10-13")
    ok = ok and approx(r["stability_new"], 6.6)
    ok = ok and r["difficulty_new"] == 3
    ok = ok and r["interval_days"] == 7
    ok = ok and r["due"] == "2026-10-20"

    # 断言 2：R 夹持（elapsed/S 夹在 [0.25, 2.0]）
    r_low = next_interval("good", stability=3.0, difficulty=3, elapsed=0.5)
    # R=0.25 -> factor=2.2*(1+0.35*(-0.75))=1.6225 -> S'=max(4.8675, 3.5)=4.8675
    ok = ok and approx(r_low["stability_new"], 4.8675)
    r_high = next_interval("good", stability=3.0, difficulty=3, elapsed=10)
    # R=2.0 -> factor=2.2*1.35=2.97 -> S'=max(8.91, 3.5)=8.91
    ok = ok and approx(r_high["stability_new"], 8.91)

    # 断言 2b：同会话重复答对（elapsed=0）只刷新召回，不增长 S/D、不推迟 due
    r_same = next_interval("easy", stability=6.0, difficulty=3, elapsed=0,
                           last="2026-10-20", today="2026-10-20",
                           current_due="2026-10-20")
    ok = ok and r_same["same_session"] is True
    ok = ok and approx(r_same["stability_new"], 6.0)
    ok = ok and r_same["difficulty_new"] == 3
    ok = ok and r_same["interval_days"] == 6
    ok = ok and r_same["due"] == "2026-10-20"
    r_same_h = next_interval("hard", stability=3.0, difficulty=3, elapsed=0,
                             current_due="2026-10-18")
    ok = ok and r_same_h["same_session"] is True
    ok = ok and approx(r_same_h["stability_new"], 3.0)
    ok = ok and r_same_h["difficulty_new"] == 3
    ok = ok and r_same_h["due"] == "2026-10-18"
    try:
        next_interval("hard", stability=3.0, difficulty=3, elapsed=0,
                      current_due="昨天")
        ok = False
    except ScheduleError:
        pass
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc_cli = main(["next-interval", "--grade", "good", "--stability", "3",
                       "--difficulty", "3", "--elapsed", "0",
                       "--current-due", "2026-10-20"])
    cli_out = json.loads(buf.getvalue())
    ok = ok and rc_cli == 0 and cli_out["due"] == "2026-10-20"
    r_not_same = next_interval("good", stability=3.0, difficulty=3, elapsed=1)
    ok = ok and r_not_same["same_session"] is False
    ok = ok and approx(r_not_same["stability_new"], 5.06)  # R=1/3 -> 仍正常增长

    # 断言 3：失败档 again
    r = next_interval("again", stability=5.0, difficulty=3, elapsed=5,
                      last="2026-10-05", today="2026-10-10")
    ok = ok and approx(r["stability_new"], 1.5)
    ok = ok and r["difficulty_new"] == 4
    r = next_interval("again", stability=2.0, difficulty=3, elapsed=2)
    ok = ok and approx(r["stability_new"], 1.0)

    # 断言 4：难度漂移与 [1,5] 夹持（D 0.5 粒度）
    r = next_interval("hard", stability=3.0, difficulty=3, elapsed=3)
    ok = ok and r["difficulty_new"] == 3.5
    r = next_interval("easy", stability=3.0, difficulty=1, elapsed=3)
    ok = ok and r["difficulty_new"] == 1
    r = next_interval("again", stability=3.0, difficulty=5, elapsed=3)
    ok = ok and r["difficulty_new"] == 5

    # 断言 5：新卡初始表 4 档 + --init-shift 1 -> D=4
    expect_s = {"again": 1.0, "hard": 1.5, "good": 3.0, "easy": 6.0}
    for grade, s0 in expect_s.items():
        r = next_interval(grade, new_card=True, init_shift=0)
        ok = ok and approx(r["stability_new"], s0)
        ok = ok and r["difficulty_new"] == 3
        ok = ok and r["stability_old"] is None and r["difficulty_old"] is None
        ok = ok and r["same_session"] is False
    r = next_interval("good", new_card=True, init_shift=1)
    ok = ok and r["difficulty_new"] == 4
    r = next_interval("good", new_card=True, init_shift=-1)
    ok = ok and r["difficulty_new"] == 2

    # 断言 6：S' 上限 365 护栏（S=300, easy, D=1 -> 1080 -> 365）
    r = next_interval("easy", stability=300.0, difficulty=1, elapsed=300)
    ok = ok and r["stability_new"] == 365

    # 断言 7：due-queue（cw 排前 / 旧格式 migrated / 无日期告警且 exit 0）
    # 纯函数核心直接喂夹具文本——selftest 全程零写盘。
    entries = [("slug-a", FIX_A), ("slug-b", FIX_B)]
    today = date.fromisoformat("2026-10-10")
    queue, warnings = queue_from_progress_texts(entries, today)
    ordered = sorted(queue, key=lambda e: (
        0 if e["cw"] else 1,
        -e["overdue_days"],
        e["due"],
        e["slug"],
        e["item"],
    ))
    ok = ok and len(ordered) >= 1 and ordered[0]["cw"] is True  # cw 排前
    by_item = {e["item"].split("：")[0]: e for e in ordered}
    ok = ok and by_item["更逾期点"]["overdue_days"] == 6  # 最逾期次优先
    ok = ok and by_item["默认链点"]["migrated"] is True  # v2 旧格式默认链
    ok = ok and by_item["默认链点"]["S"] == 3 and by_item["默认链点"]["D"] == 3
    ok = ok and by_item["默认链点"]["due"] == "2026-10-08"  # 最近更新+round(3)
    ok = ok and by_item["顽固点"]["teach"] is True  # 顽固 -> teach
    ok = ok and by_item["自信但错点"]["cw"] is True
    ok = ok and by_item["老错题"]["kind"] == "错题"
    ok = ok and any(w.startswith("W-UNPARSED-ITEM") and "完全无日期点" in w
                    for w in warnings)
    ok = ok and all("完全无日期点" != e["item"].split("：")[0] for e in ordered)
    # 排序稳定性：同输入重跑顺序一致（幂等）
    queue2, warnings2 = queue_from_progress_texts(entries, today)
    ordered2 = sorted(queue2, key=lambda e: (
        0 if e["cw"] else 1, -e["overdue_days"], e["due"], e["slug"], e["item"]))
    ok = ok and json.dumps(ordered2, ensure_ascii=False, sort_keys=True) == \
        json.dumps(ordered, ensure_ascii=False, sort_keys=True)
    # --all 口径：未来条目也保留（收尾五件套报日期用）
    future, _w = queue_from_progress_texts(
        [("slug-c", "# 学习任务：丙\n- 当前阶段：复习巩固\n\n## 薄弱点\n- 未来点：未到期（S=2.0，D=3，last=2026-10-10，due=2026-10-13）\n")],
        today)
    ok = ok and len(future) == 1 and future[0]["overdue_days"] == -3

    # 断言 7b：保持复习区被 due-queue 识别；reason 说明到期原因；schema 升 /3
    today_r = date.fromisoformat("2026-10-20")
    rq, rw = queue_from_progress_texts([("slug-r", FIX_R)], today_r)
    by_r = {e["item"]: e for e in rq}
    ok = ok and by_r["第 1 节 变量"]["kind"] == "保持"
    ok = ok and by_r["第 1 节 变量"]["overdue_days"] == 5
    ok = ok and by_r["第 2 节 循环"]["overdue_days"] == -5
    ok = ok and by_r["第 1 节 变量"]["meta_default"] is False
    ok = ok and by_r["第 1 节 变量"]["错因"] == "" and by_r["第 1 节 变量"]["级"] == ""
    ok = ok and "保持复习" in review_reason(by_r["第 1 节 变量"])
    ok = ok and "已逾期 5 天" in review_reason(by_r["第 1 节 变量"])
    ok = ok and "还有 5 天到期" in review_reason(by_r["第 2 节 循环"])
    ok = ok and not any(w.startswith("W-UNPARSED-ITEM") for w in rw)
    cal_r, _cw_r = calibration_from_progress_texts([("slug-r", FIX_R)])
    ok = ok and cal_r[0]["total_items"] == 0  # 保持复习不进校准画像
    # 日期前缀可省略：元数据 last/due 能推出 due 时仍入队；全部日期来源缺失才告警
    rq2, rw2 = queue_from_progress_texts([("slug-r2", FIX_R2)], today_r)
    by_r2 = {e["item"]: e for e in rq2}
    ok = ok and by_r2["第 3 节 函数"]["due"] == "2026-10-22"
    ok = ok and by_r2["第 4 节 类"]["due"] == "2026-10-21"
    ok = ok and not any(w.startswith("W-UNPARSED-ITEM") for w in rw2)
    rq3, rw3 = queue_from_progress_texts([("slug-r3", FIX_R3)], today_r)
    ok = ok and not rq3
    ok = ok and any(w.startswith("W-UNPARSED-ITEM") and "第 5 节 无日期" in w
                    for w in rw3)
    # 混合任务：保持复习不进校准，薄弱点仍正常计入
    mix_cal, _ = calibration_from_progress_texts([(
        "slug-mix", FIX_R + "\n## 薄弱点\n- 某点（S=3.0，D=3，last=2026-10-19，"
        "due=2026-10-20，信心=4，cw）\n")])
    ok = ok and mix_cal[0]["total_items"] == 1
    ok = ok and mix_cal[0]["cw_count"] == 1
    with tempfile.TemporaryDirectory() as td_r:
        root_r = Path(td_r) / ".learning"
        (root_r / "slug-r").mkdir(parents=True)
        (root_r / "slug-r" / "progress.md").write_text(FIX_R, encoding="utf-8")
        out_r = due_queue_output(root_r, None, today_r, False)
        ok = ok and out_r["schema"] == "ltw-due-queue/3"
        ok = ok and len(out_r["queue"]) == 1
        ok = ok and out_r["queue"][0]["kind"] == "保持"
        ok = ok and out_r["queue"][0]["reason"].startswith("保持复习")

    # 断言 8：畸形输入 -> exit 2（不谎报成功）
    bad_calls = [
        ["next-interval", "--grade", "bogus", "--stability", "3",
         "--difficulty", "3", "--elapsed", "3"],
        ["next-interval", "--grade", "good", "--stability", "3",
         "--difficulty", "3", "--elapsed", "5", "--last", "2026-10-10",
         "--today", "2026-10-13"],  # elapsed 与 last/today 数值冲突（5 != 3）
        ["next-interval", "--grade", "good", "--stability", "0",
         "--difficulty", "3", "--elapsed", "3"],  # S<=0
        ["next-interval", "--grade", "good", "--stability", "3",
         "--difficulty", "7", "--elapsed", "3"],  # D 越界
        ["next-interval", "--grade", "good", "--stability", "3",
         "--difficulty", "3.3", "--elapsed", "3"],  # D 非 0.5 粒度
        ["next-interval", "--grade", "good", "--stability", "3",
         "--difficulty", "3"],  # 成功档缺 elapsed 组
        ["next-interval", "--grade", "good", "--new-card",
         "--difficulty", "3"],  # new-card 与 --difficulty 冲突
        ["next-interval", "--grade", "good", "--stability", "3",
         "--difficulty", "3", "--elapsed", "-1"],  # elapsed 负数
        ["next-interval", "--grade", "good", "--stability", "3",
         "--difficulty", "3", "--last", "2026-10-10"],  # last 缺 today
        ["next-interval", "--grade", "good", "--stability", "3",
         "--difficulty", "3", "--elapsed", "0"],  # 同会话缺现有 due
        ["next-interval", "--grade", "good", "--stability", "3",
         "--difficulty", "3", "--elapsed", "0", "--current-due", "昨天"],
        ["next-interval", "--grade", "good", "--stability", "3",
         "--difficulty", "3", "--elapsed", "3", "--confidence", "9"],  # 信心越界
        ["due-queue", "--root", "x", "--today", "明天"],  # 非法日期
        # 非有限数：NaN/Inf 一律结构化拒绝 rc=2（不得裸崩或输出 Infinity）
        ["next-interval", "--grade", "good", "--stability", "nan",
         "--difficulty", "3", "--elapsed", "3"],
        ["next-interval", "--grade", "good", "--stability", "inf",
         "--difficulty", "3", "--elapsed", "3"],
        ["next-interval", "--grade", "good", "--stability", "3",
         "--difficulty", "3", "--elapsed", "nan"],
        ["next-interval", "--grade", "good", "--stability", "3",
         "--difficulty", "3", "--elapsed", "inf"],
        ["next-interval", "--grade", "good", "--stability", "9999999",
         "--difficulty", "3", "--elapsed", "3"],         # S 超上界
        ["next-interval", "--grade", "good", "--new-card",
         "--last", "9999-12-31", "--today", "9999-12-31"],  # due 日期越界
    ]
    for call in bad_calls:
        try:
            main(call)
            ok = False  # 未抛 SystemExit(2) 即失败
        except SystemExit as exc:
            ok = ok and exc.code == 2

    # 断言 9：calibration 手工验算锚点（FIX_A：显式信心恰 2 条、其中 cw 1 条
    # → rate=0.5；顽固点/默认链点/老错题/无日期点均无显式信心，不计入分母）
    cal_per, cal_warn = calibration_from_progress_texts(
        [("slug-a", FIX_A), ("slug-b", FIX_B)])
    pa = {p["slug"]: p for p in cal_per}["slug-a"]
    ok = ok and pa["with_confidence"] == 2
    ok = ok and pa["cw_count"] == 1
    ok = ok and pa["overconfidence_rate"] == 0.5  # 1/2 手工验算锚点
    ok = ok and pa["confidence_dist"] == {"1": 0, "2": 1, "3": 0, "4": 0, "5": 1}
    ok = ok and pa["total_items"] == 6
    ok = ok and pa["migrated_count"] == 2  # 默认链点 + 无日期点（均靠「最近更新」补日期）
    ok = ok and pa["default_filled"] == 6  # 全部 6 条均缺 错因/级
    ok = ok and len(pa["cw_items"]) == 1 and pa["cw_items"][0].startswith("自信但错点")
    ok = ok and pa["dedup_mode"] == "legacy_double_count"  # 无 evt → 沿用声明式双计
    ok = ok and pa["rate_valid"] is True

    # 断言 10：FIX_B（完全无日期）→ rate=null（不谎报 0）+ W-UNPARSED-ITEM 告警
    pb = {p["slug"]: p for p in cal_per}["slug-b"]
    ok = ok and pb["overconfidence_rate"] is None and pb["rate_valid"] is False
    ok = ok and pb["with_confidence"] == 0 and pb["unparsed_count"] == 1
    ok = ok and any(w.startswith("W-UNPARSED-ITEM") and "完全无日期点" in w
                    for w in cal_warn)

    # 断言 11：v2.1 形态条目（有信心无错因/级）→ 计入分母（承断言 9），且
    # due-queue 输出错因/级填缺省并标 meta_default:true
    ok = ok and by_item["自信但错点"]["错因"] == "知识性"
    ok = ok and by_item["自信但错点"]["级"] == "B"
    ok = ok and by_item["自信但错点"]["meta_default"] is True

    # 断言 12：due-queue 新键——v2.2 完整条目错因/级原值回显 meta_default:false；
    # v6.0 schema 升 ltw-due-queue/3（加 reason/保持复习）；排序契约（cw 排前）断言 7 逐字保留未动
    queue_c, _wc = queue_from_progress_texts(
        [("slug-c", FIX_C)], date.fromisoformat("2026-10-10"))
    ok = ok and len(queue_c) == 2
    by_item_c = {e["item"].split("：")[0]: e for e in queue_c}
    ok = ok and by_item_c["完整点"]["错因"] == "理解性"
    ok = ok and by_item_c["完整点"]["级"] == "A"
    ok = ok and by_item_c["完整点"]["meta_default"] is False
    ok = ok and by_item_c["变式题"]["错因"] == "技巧性"
    ok = ok and by_item_c["变式题"]["级"] == "B"
    ok = ok and by_item_c["变式题"]["meta_default"] is False
    out = due_queue_output(Path(__file__).resolve().parent, None,
                           date.fromisoformat("2026-10-10"), True)
    ok = ok and out["schema"] == "ltw-due-queue/3"

    # 断言 13：calibration 畸形输入 → exit 2；--root 非目录 → exit 1
    for call in [["calibration"]]:  # 缺必填 --root → argparse exit 2
        try:
            main(call)
            ok = False
        except SystemExit as exc:
            ok = ok and exc.code == 2
    ok = ok and main(["calibration", "--root",
                      str(Path(__file__).resolve().parent / "__no_such_dir__")]) == 1

    # 断言 14：半角容忍——半角括号元数据可拆出、半角竖线错题行可分段，解析与全角等价
    it14, mt14 = split_weak_item("半角点：正负号 (S=2.0, D=3, last=2026-10-09, due=2026-10-09, 信心=4, cw)")
    ok = ok and it14 == "半角点：正负号" and mt14 is not None
    m14 = parse_meta(mt14)
    ok = ok and m14["S"] == 2.0 and m14["D"] == 3 and m14["信心"] == 4 and m14["cw"] is True
    it14b, mt14b = split_wrong_item("半角题 | 我的答案：错 | 元数据：S=1.0, D=4, last=2026-10-09, due=2026-10-10, cw")
    ok = ok and it14b == "半角题" and mt14b is not None
    m14b = parse_meta(mt14b)
    ok = ok and m14b["S"] == 1.0 and m14b["D"] == 4 and m14b["cw"] is True
    # 全角优先不受影响：全角行仍按全角括号拆出
    it14c, mt14c = split_weak_item("全角点：正负号（S=2.0，D=3，last=2026-10-09，信心=4，cw）")
    ok = ok and it14c == "全角点：正负号" and mt14c is not None
    # 断言 14b：子类 token 被识别，不进入 invalid_tokens
    m14d = parse_meta("S=3.0，D=3，last=2026-10-09，due=2026-10-10，错因=理解性，级=B，子类=过度泛化")
    ok = ok and m14d["子类"] == "过度泛化"
    ok = ok and "子类=过度泛化" not in m14d["invalid_tokens"]

    # 断言 15：due 锚定「本次复习日」——逾期卡复习后 due 必落在未来，
    # 不得回落到过去日期（旧缺陷：last=2026-10-01 起算 → due=2026-10-10 已是过去）
    r15 = next_interval("good", stability=3.0, difficulty=3, elapsed=14,
                        last="2026-10-01", today="2026-10-15")
    ok = ok and r15["interval_days"] == 9
    ok = ok and r15["due"] == "2026-10-24"

    # 断言 16：坏元数据隔离——单条坏数据（坏 S / 坏日历日期）不得让整队列裸崩，
    # 其余好条目仍可用；坏值按缺省链解析并标 migrated。
    fix_d = ("# 学习任务：坏元数据\n- 数据根：<root>\n- 当前阶段：复习巩固\n"
             "- 类型：知识型\n- 学科族：理论概念类\n- 目标：自测\n- 起点：入门\n"
             "- 最近更新：2026-10-08\n\n## 学习路线\n- [ ] 1. 基础\n\n## 薄弱点\n"
             "- 坏S点：缺省（S=1..2，D=3，last=2026-10-09，due=2026-10-11）\n"
             "- 坏日期点：缺省（S=2.0，D=3，last=2026-02-30，due=2026-02-30）\n"
             "- 好点：正常（S=3.0，D=3，last=2026-10-09，due=2026-10-10）\n")
    q16, w16 = queue_from_progress_texts([("slug-d", fix_d)],
                                         date.fromisoformat("2026-10-12"))
    by16 = {e["item"].split("：")[0]: e for e in q16}
    ok = ok and len(q16) == 3  # 三条均入队，无崩溃、无丢失
    ok = ok and by16["坏S点"]["S"] == 3 and by16["坏S点"]["migrated"] is True  # 坏 S → 默认 3
    ok = ok and by16["坏日期点"]["due"] == "2026-10-10"  # 坏日期 → 回退最近更新 2026-10-08 + 2
    ok = ok and by16["坏日期点"]["migrated"] is True
    ok = ok and by16["好点"]["due"] == "2026-10-10" and by16["好点"]["migrated"] is False
    # 坏值走默认链（标 W-META-INVALID 披露），但**不得**判为不可推算的 UNPARSED
    ok = ok and not any(w.startswith("W-UNPARSED-ITEM")
                        and ("坏S点" in w or "坏日期点" in w) for w in w16)
    ok = ok and any(w.startswith("W-META-INVALID") and "坏S点" in w for w in w16)

    # 断言 17：坏元数据端到端（due-queue CLI）——写入含坏数据的 progress.md，
    # 命令仍 exit 0 且正常输出（不裸崩）。
    with tempfile.TemporaryDirectory() as td17:
        root17 = Path(td17) / ".learning"
        (root17 / "slug-d").mkdir(parents=True)
        (root17 / "slug-d" / "progress.md").write_text(fix_d, encoding="utf-8")
        rc17 = main(["due-queue", "--root", str(root17), "--today", "2026-10-12"])
        ok = ok and rc17 == 0

    # 断言 18：校准去重与畸形率——同一作答事件（evt=E1）的较多投影只计一次；
    # cw 多于有信心的条目 → rate 不展示（null + rate_valid False + 原因）。
    fix_t04 = ("# 学习任务：校准T04\n- 当前阶段：复习巩固\n- 复习来源阶段：逐节学习\n"
               "- 类型：知识型\n- 学科族：数学类\n- 目标：自测\n- 起点：入门\n\n## 薄弱点\n"
               "- A点：投影甲（S=3.0，D=3，last=2026-10-09，due=2026-10-10，信心=4，cw，evt=E1）\n"
               "- B点：投影乙（S=3.0，D=3，last=2026-10-09，due=2026-10-10，cw，evt=E1）\n"
               "- C点：无信心（S=3.0，D=3，last=2026-10-09，due=2026-10-10，cw）\n"
               "- D点：无信心（S=3.0，D=3，last=2026-10-09，due=2026-10-10，cw）\n")
    t04_per, _tw = calibration_from_progress_texts([("slug-t04", fix_t04)])
    t04 = t04_per[0]
    ok = ok and t04["dedup_mode"] == "mixed"   # 含 evt 与无 evt 混排 → 单独标口径
    ok = ok and t04["evt_tagged_count"] == 2 and t04["legacy_count"] == 2
    ok = ok and t04["total_items"] == 3        # B 与 A 同 evt → 只计一次（不同次投影才各计）
    ok = ok and t04["with_confidence"] == 1
    ok = ok and t04["cw_count"] == 1           # cw 必须是高信心(≥4)观察的子集
    ok = ok and t04["orphan_cw_count"] == 2    # C/D 有 cw 无信心 → 孤立，不入分子
    ok = ok and t04["overconfidence_rate"] is None and t04["rate_valid"] is False

    # 断言 19：单条过大 S 不得拖垮整队列（S=9999999 曾抛 year 29405 out of range；
    # 308 位 S 曾 OverflowError）——好条必须保留，坏条降级告警不崩。
    for bad_s in ("9999999", "9" * 308, "1e309"):
        fix_big = ("# 学习任务：大S\n- 当前阶段：复习巩固\n- 类型：知识型\n"
                   "- 学科族：理论概念类\n- 目标：自测\n- 起点：入门\n"
                   "- 最近更新：2026-10-08\n\n## 薄弱点\n"
                   "- 坏S：超大（S=" + bad_s + "，D=3，last=2026-10-09）\n"
                   "- 好点：正常（S=3.0，D=3，last=2026-10-09，due=2026-10-10）\n")
        q19, _w19 = queue_from_progress_texts(
            [("slug-big", fix_big)], date.fromisoformat("2026-10-15"))
        items19 = {e["item"].split("：")[0]: e for e in q19}
        ok = ok and "好点" in items19                       # 好条保留
        ok = ok and items19["好点"]["due"] == "2026-10-10"

    # 断言 20：safe_add_days 越界返回 None（不抛异常）
    ok = ok and safe_add_days("9999-12-31", 3) is None
    ok = ok and safe_add_days("2026-10-15", 3) == "2026-10-18"
    ok = ok and safe_add_days("not-a-date", 3) is None

    # 断言 21：parse_meta 逐 token fullmatch——坏 token 不截前缀，全部落 invalid_tokens，
    # 各键保持缺省（旧缺陷：S=3oops→3、信心=50→5、last=2026-10-09oops→2026-10-09）。
    m21 = parse_meta("S=3oops，D=3.3，last=2026-10-09oops，信心=50，cw")
    ok = ok and m21["S"] is None and m21["D"] is None and m21["last"] is None
    ok = ok and m21["信心"] is None and m21["cw"] is True
    ok = ok and len(m21["invalid_tokens"]) == 4
    m21b = parse_meta("S=3，D=3.5，last=2026-10-09，信心=5，cw")   # 合法：D 半步、信心 1-5
    ok = ok and m21b["S"] == 3.0 and m21b["D"] == 3.5 and m21b["信心"] == 5
    ok = ok and m21b["invalid_tokens"] == []
    m21c = parse_meta("S=3，S=4，D=3")                             # 重复键 → 标坏
    ok = ok and m21c["invalid_tokens"] and m21c["S"] == 3.0

    # 断言 22：校准「先形成合法观察再统计」——无日期条目不再误计且与告警一致；
    # 孤立/低信心 cw 不再越过闸口；互补投影合并、冲突投影作废。
    cal_fix = {
        "no_date": ("- 最近更新：\n## 薄弱点\n- 无日期（信心=5，cw）\n"),
        "orphan": ("- 最近更新：2026-10-08\n## 薄弱点\n- 有信心（信心=3）\n"
                   "- 无信心（cw）\n"),
        "low": ("- 最近更新：2026-10-08\n## 薄弱点\n- 低信心（信心=1，cw）\n"),
        "complete": ("- 最近更新：2026-10-08\n## 薄弱点\n- A（信心=5，cw，evt=E1）\n"
                     "## 错题本\n- [2026-10-08] B ｜ 元数据：信心=5，cw，evt=E1\n"),
        "partial": ("- 最近更新：2026-10-08\n## 薄弱点\n- A（S=3，evt=E1）\n"
                    "## 错题本\n- [2026-10-08] B ｜ 元数据：信心=5，cw，evt=E1\n"),
        "conflict": ("- 最近更新：2026-10-08\n## 薄弱点\n- A（信心=2，evt=E1）\n"
                     "## 错题本\n- [2026-10-08] B ｜ 元数据：信心=5，cw，evt=E1\n"),
    }
    c22, w22 = calibration_from_progress_texts(
        [(k, v) for k, v in cal_fix.items()])
    p22 = {p["slug"]: p for p in c22}
    # 无日期：不入统计，与告警「不入统计」一致
    ok = ok and p22["no_date"]["rate_valid"] is False
    ok = ok and p22["no_date"]["with_confidence"] == 0 and p22["no_date"]["cw_count"] == 0
    # 孤立 cw（另一条才有信心）：不得标有效
    ok = ok and p22["orphan"]["rate_valid"] is False and p22["orphan"]["orphan_cw_count"] == 1
    ok = ok and p22["orphan"]["with_confidence"] == 1 and p22["orphan"]["cw_count"] == 0
    # 低信心 cw（信心=1）：不计入分子
    ok = ok and p22["low"]["rate_valid"] is False
    ok = ok and p22["low"]["low_confidence_cw_count"] == 1 and p22["low"]["cw_count"] == 0
    # 完全一致投影：去重后 1/1 有效
    ok = ok and p22["complete"]["total_items"] == 1 and p22["complete"]["rate_valid"] is True
    ok = ok and p22["complete"]["overconfidence_rate"] == 1.0
    # 互补投影：缺失的信心/cw 被合并，不再丢失
    ok = ok and p22["partial"]["with_confidence"] == 1 and p22["partial"]["cw_count"] == 1
    ok = ok and p22["partial"]["rate_valid"] is True
    # 冲突投影：整条作废 + 告警
    ok = ok and p22["conflict"]["rate_valid"] is False and p22["conflict"]["conflict_count"] == 1
    ok = ok and any(w.startswith("W-CONFIDENCE-AMBIGUOUS") for w in w22)

    # 断言 23：坏 cw 与坏 token 均给结构化告警（不静默）
    ok = ok and any(w.startswith("W-CW-ORPHAN") for w in w22)
    ok = ok and any(w.startswith("W-CW-LOWCONF") for w in w22)
    _q23, w23 = queue_from_progress_texts(
        [("s", "- 最近更新：2026-10-08\n## 薄弱点\n- 点（S=3oops，D=3，last=2026-10-09）\n")],
        date.fromisoformat("2026-10-15"))
    ok = ok and any(w.startswith("W-META-INVALID") for w in w23)

    # 断言 24：信心/时序身份歧义不得产出有效比率
    ok = ok and parse_meta("信心=回顾性")["invalid_tokens"] == []      # 回顾性是合法时序标志
    ok = ok and parse_meta("信心=回顾性")["信心_retro"] is True
    ok = ok and parse_meta("信心=5，信心=2")["dup_keys"] == ["信心"]     # 重复信心 → 记入歧义键
    dup24 = calibration_from_progress_texts(
        [('s', '- 最近更新：2026-10-15\n## 薄弱点\n- A（信心=5，信心=2，cw，evt=E1）\n')])[0][0]
    ok = ok and dup24["rate_valid"] is False and dup24["cw_count"] == 0
    ok = ok and dup24["conflict_count"] == 1
    dup_schedule = calibration_from_progress_texts(
        [('s', '- 最近更新：2026-10-15\n## 薄弱点\n- A（S=3，S=4，信心=5，cw，evt=E2）\n')])[0][0]
    ok = ok and dup_schedule["rate_valid"] is True
    ok = ok and dup_schedule["conflict_count"] == 0
    ok = ok and dup_schedule["overconfidence_rate"] == 1.0
    retro24 = calibration_from_progress_texts(
        [('s', '- 最近更新：2026-10-15\n## 薄弱点\n- A（信心=回顾性，evt=E1）\n')])[0][0]
    ok = ok and retro24["with_confidence"] == 0 and retro24["rate_valid"] is False
    ok = ok and retro24["retro_excluded_count"] == 1 and retro24["conflict_count"] == 0
    mix24 = calibration_from_progress_texts(
        [('s', '- 最近更新：2026-10-15\n## 薄弱点\n- A（信心=回顾性，evt=E1）\n'
              '## 错题本\n- [2026-10-15] B ｜ 元数据：信心=5，cw，evt=E1\n')])[0][0]
    ok = ok and mix24["rate_valid"] is False and mix24["cw_count"] == 0 and mix24["conflict_count"] == 1
    evt24 = calibration_from_progress_texts(
        [('s', '- 最近更新：2026-10-15\n## 薄弱点\n- A（evt=E1）\n'
              '## 错题本\n- [2026-10-15] B ｜ 元数据：信心=5，cw，evt=E1\n')])[0][0]
    ok = ok and evt24["total_items"] == 1 and evt24["dedup_mode"] == "by_evt" and evt24["cw_count"] == 1
    # 断言 25：长中断（10 年）不再因人为上界被拒（R 已夹 [0.25,2]）
    try:
        main(["next-interval", "--grade", "good", "--stability", "3", "--difficulty", "3",
              "--last", "2016-10-14", "--today", "2026-10-15"])
    except SystemExit:
        ok = False

    print(("OK " if ok else "FAIL ") + "scheduler --selftest")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
