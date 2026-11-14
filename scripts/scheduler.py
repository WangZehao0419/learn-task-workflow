#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scheduler.py - 间隔重复调度计算（FSRS-6 增长律 + 本仓记账法；确定性，stdlib-only，只读）。

用途：learn-task-workflow v2.1 的确定性调度环节。判分（grade/信心/复述）与
落盘决策归模型；S'/D'/due 计算与到期排序归本脚本。脚本**只读计算**——
不改写任何用户数据，输出 JSON 到 stdout，落盘由宿主提供的文件写入/编辑能力负责（见
SKILL.md「判断归模型、数据归脚本」）。

子命令：
    next-interval  判分后算下一间隔：
        python scheduler.py next-interval --grade {again|hard|good|easy} \
            (--stability <S> | --new-card) --difficulty <D> \
            (--elapsed <N> | --last YYYY-MM-DD --today YYYY-MM-DD) \
            [--current-due YYYY-MM-DD] [--confidence <1-5>]
        --elapsed 与 --last/--today 同传时数值必须一致（elapsed = today-last），
        不一致 exit 2；仅传 --elapsed（无 --last/--today）时 due 为 null，
        只回 interval_days，由模型以当日推算绝对日期——保证输出不依赖
        机器时钟、完全确定。同会话重复答对（elapsed=0）必须传 --current-due，
        返回原日期，不以重算值覆盖。
        **FSRS-6 起 elapsed 对四档全必填**（失败档的遗忘后 S 也依赖 R(t,S)，
        缺 elapsed 无法算 R，脚本拒绝猜）。新卡初始难度只由评分档 D0(G)
        决定，不接收方向偏移；--init-shift 已删除（旧调用侧传它 exit 2）。
        **due 锚点**：新 due = 本次复习日期 today + interval_days；last 仅用于
        计算 elapsed（经过天数）与旧记录回显，**不**参与 due 起算——否则逾期卡
        复习后会把 due 算到过去日期。仅当 today 缺省（直连函数调用）时才回退用 last。

    due-queue      开节前查到期队列：
        python scheduler.py due-queue --root <数据根> [--slug <slug>] \
            --today YYYY-MM-DD [--all]
        读 <root>/<slug>/progress.md 的「薄弱点」「错题本」「保持复习」三区，
        按 cw 优先 → 最逾期优先 → due 早优先 → slug/条目名稳定序 排序。
        每条输出 reason（到期/逾期/优先级的人类可读说明）；schema=ltw-due-queue/5。
        条目回显「顺延」计数（干预留痕，不进排序、不改 S/D、不写 last）。
        默认只出 due <= today；--all 出全部（供收尾五件套报具体日期用）。
        v2.2：条目输出新增 错因/级/meta_default 三键（加键升 schema
        ltw-due-queue/5）；排序契约 cw→最逾期→due 早→稳定序 逐字不动。
        v2.7：D 回显形态随 FSRS-6 换律而变（连续值、[1,10]、保留 4 位小数），
        按 data.md 的 minor 规则把 schema 从 /3 升到 /4；键集合与排序契约不动。
        v2.8：条目回显新增「顺延」键（键集合变化，按 data.md minor 规则升 /5）；
        reason 追加顺延披露。排序契约仍逐字不动。
        薄弱点/错题行元数据挂载点全角/半角双兼容（推荐全角，
        半角兜底），防模型写半角括号/竖线时元数据静默丢失。

    calibration    校准画像统计（只读快照口径，v2.4 收紧）：
        python scheduler.py calibration --root <数据根> [--slug <slug>]
        读 <root>/<slug>/progress.md 两区条目元数据（信心、cw、evt）。口径：
        先按 evt 归组并合并互补字段、冲突作废 → 再形成「合法观察」（可推算日期
        且无冲突）→ 才统计。分母只数合法观察中**显式**写有「信心=」的条目；
        分子 cw 只数「反馈前信心 ≥4 且 cw」的合法观察（cw 必须是同口径高信心
        错误观察的子集）。孤立 cw / 低信心 cw / 同 evt 冲突 → 单独告警并令
        rate_valid=false、不输出比率（不谎报）。无 evt 条目各成单条观察并报
        W-NO-EVT（提示补 evt，同次作答的投影才能去重）。
        快照口径不做时间窗，不需 --today。脚本只算不判，教学化呈现归模型。

公式契约（FSRS-6 增长律；不得在调用侧自行更改；w / desired_retention / s_max /
    s_min / maximum_interval / enable_fuzzing 六项唯一来源 = 契约 scheduler 块，
    此处不重复数值）:
    常量：decay = -w20；factor = 0.9^(1/decay) - 1
    遗忘曲线      R(t,S) = (1 + factor*t/S)^(-w20)          （R 是回忆概率，0-1）
    下次间隔      I(r,S) = S/factor * (r^(1/(-w20)) - 1)
    初始稳定度    S0(G) = w[G-1]        （again/hard/good/easy = 1/2/3/4）
    初始难度      D0(G) = clamp(w4 - e^(w5*(G-1)) + 1, 1, 10)
    难度更新      ΔD = -w6*(G-3); D' = D + ΔD*(10-D)/9;
                  D'' = w7*D0(4) + (1-w7)*D'
    成功回忆后 S  S' = S*(1 + e^w8*(11-D)*S^(-w9)*(e^(w10*(1-R))-1)
                          * w15^[G=2] * w16^[G=4])，夹 [s_min, s_max]
    遗忘后 S      S' = min(w11*D^(-w12)*((S+1)^w13 - 1)*e^(w14*(1-R)),
                           S/e^(w17*w18))，夹 [s_min, s_max]
    间隔取整：interval_days = min(max(1, round_half_up(I(desired_retention, S'))),
                                  maximum_interval)
    同日复习（Q6=I1）：elapsed=0 且答对仍走 same_session 特判——不套上面任何公式，
        只刷新召回，S/D 不变、原 due 原样返回；w17-w19 的同日复习公式不实现。
    round 一律四舍五入 0.5 进位（int(x+0.5)），规避银行家舍入歧义。
    fuzzing 恒关（契约 enable_fuzzing=false）：同输入同输出。
    信心度仅回显，不进公式（cw 惩罚已由 grade=again 承载，避免双重惩罚）。
    有效域（所有计算入口先验，NaN/Inf 一律拒绝、exit 2）：S ∈ [s_min, s_max]，
    D ∈ [1, 10] 连续（不再要求 0.5 粒度），elapsed 有限且 ≥0（长中断只让 R 趋 0，
    不放大间隔）；日期加法越界（如 9999-12-31 + 间隔）同样结构化拒绝，不裸崩、
    不输出非有限数（json.dumps allow_nan=False）。
    上限拆两个常数：s_max=36500 是 FSRS/fsrs-rs 的 S 上限；maximum_interval=365
    是本仓的产品护栏（偏离 FSRS 官方默认，见 docs/adr/0003-fsrs6-full-switch.md）。

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
from datetime import date, timedelta
from pathlib import Path

import rule_contract
# 条目元数据解析（META_KEYS / parse_meta / 括注拆分）与 S/D 值域常数住在
# ltw_parse：due-queue 与 progress_check 必须读同一条判据，各写一份就是判据分叉。
from ltw_parse import (DATE_RE, D_MAX, D_MIN, FIELD_RE, META_KEYS, META_TOKEN_RES,
                       NONE_MARKS, NONE_RE, S_MAX, S_MIN, WRONG_LINE_RE,
                       _finite_pos, _in_range, _looks_like_meta, _valid_iso,
                       parse_day_rows, parse_field_line, parse_meta,
                       parse_progress_sections, split_weak_item, split_wrong_item)


class ScheduleError(ValueError):
    """调度参数/范围错误：统一结构化拒绝（exit 2），不让异常栈成为外部协议。"""


# 调度常数唯一来源：contracts/rules.json（缺失/畸形即结构化失败）。
_CONSTANTS = rule_contract.load_or_exit()["constants"]
_C = _CONSTANTS["scheduler"]
_SCHEMAS = _CONSTANTS["schemas"]


def _contract_fail(msg):
    """契约自检失败：fail closed，不退回内置默认值继续跑。

    与 rule_contract.load_or_exit() 同口径——契约畸形属「校验不通过」，走 exit 1 +
    结构化 JSON（E-CONTRACT-INVALID），不走 exit 2（那是用法/参数错误）。同一类失败
    在同一个脚本里必须只有一个退出码，否则调用方没法统一处理。
    """
    print(json.dumps({"ok": False, "code": "E-CONTRACT-INVALID", "message": msg},
                     ensure_ascii=False))
    raise SystemExit(1)


W = [float(x) for x in _C["w"]]
DESIRED_RETENTION = float(_C["desired_retention"])
MAXIMUM_INTERVAL = int(_C["maximum_interval"])
ENABLE_FUZZING = bool(_C["enable_fuzzing"])
if len(W) != 21:
    _contract_fail("scheduler.w 必须是 21 项（FSRS-6），实际 " + str(len(W)) + " 项")
if ENABLE_FUZZING:
    # 本仓确定性契约：fuzzing 一开，同输入不再同输出，直接拒绝启动。
    _contract_fail("scheduler.enable_fuzzing 必须为 false（确定性契约）")
if not (0.0 < DESIRED_RETENTION < 1.0):
    _contract_fail("scheduler.desired_retention 须在 (0,1)，实际 " + str(DESIRED_RETENTION))
if not (0.0 < S_MIN < S_MAX):
    _contract_fail("scheduler 须满足 0 < s_min < s_max")
if MAXIMUM_INTERVAL < 1:
    _contract_fail("scheduler.maximum_interval 须 ≥ 1，实际 " + str(MAXIMUM_INTERVAL))

DECAY = -W[20]                       # FSRS-6 遗忘曲线衰减指数（decay = -w20）
# 曲线形状常数：按 FSRS 定义**只由 w20 与参考保持率 0.9 决定**，与 desired_retention 无关
# （desired_retention 只进 interval_for 的 I(r,S)）。改 desired_retention 不会改变它。
FACTOR = 0.9 ** (1.0 / DECAY) - 1.0
_GRADE_INDEX = {"again": 1, "hard": 2, "good": 3, "easy": 4}
ELAPSED_INF = float("inf")   # 经过天数只要求「有限且 ≥0」：R(t,S) 随 t 单调趋 0，
# 长中断自然压低增幅，无需人为上界（长中断兼容）。
DATE_MIN_ORD = date.min.toordinal()
DATE_MAX_ORD = date.max.toordinal()
DEFAULT_CAUSE = "知识性"  # v2.2：错因缺省枚举（仅脚本输出侧占位回显，模型不得盲补）
DEFAULT_LEVEL = "B"       # v2.2：级缺省枚举（同上）

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


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def retrievability(elapsed, stability):
    """FSRS-6 遗忘曲线 R(t,S) = (1 + factor*t/S)^(-w20)，值域 (0,1]。

    与旧律同名不同义：旧 R 是 elapsed/S 的**相对时间比**（可 >1，夹 [0.25,2]），
    新 R 是**回忆概率**（0-1）。S=100 / elapsed=1 时前者 0.01、后者约 0.9985。
    """
    return (1.0 + FACTOR * elapsed / stability) ** (-W[20])


def initial_stability(grade):
    """S0(G) = w[G-1]（again/hard/good/easy = 1/2/3/4）。"""
    return W[_GRADE_INDEX[grade] - 1]


def initial_difficulty(grade, clamp=True):
    """D0(G) = w4 - e^(w5*(G-1)) + 1；clamp 时夹 [1,10]。

    easy 档原始值约 -4.77，靠夹持兜底到 1——这是 FSRS-6 默认参数的既有形态。
    """
    v = W[4] - math.e ** (W[5] * (_GRADE_INDEX[grade] - 1)) + 1.0
    return _clamp(v, D_MIN, D_MAX) if clamp else v


def next_difficulty(difficulty, grade):
    """ΔD=-w6*(G-3)；D'=D+ΔD*(10-D)/9；D''=w7*D0(4)+(1-w7)*D'，夹 [1,10]。"""
    delta = -(W[6] * (_GRADE_INDEX[grade] - 3))
    damped = difficulty + delta * (10.0 - difficulty) / 9.0
    v = W[7] * initial_difficulty("easy", clamp=False) + (1.0 - W[7]) * damped
    return _clamp(v, D_MIN, D_MAX)


def stability_after_success(stability, difficulty, r, grade):
    """成功回忆后 S'（hard 乘 w15、easy 乘 w16），夹 [s_min, s_max]。"""
    hard_penalty = W[15] if grade == "hard" else 1.0
    easy_bonus = W[16] if grade == "easy" else 1.0
    v = stability * (1.0 + math.e ** W[8] * (11.0 - difficulty)
                     * (stability ** -W[9])
                     * (math.e ** (W[10] * (1.0 - r)) - 1.0)
                     * hard_penalty * easy_bonus)
    return _clamp(v, S_MIN, S_MAX)


def stability_after_failure(stability, difficulty, r):
    """遗忘后 S = min(长期项, S/e^(w17*w18))，夹 [s_min, s_max]。

    短期项只在同日复习公式启用时才有意义（Q6=I1 未启用 w17-w19），但 fsrs-rs
    在长期公式里同样取这条 min 上界；此处照参考实现保留，行为可对照。
    """
    long_term = (W[11] * (difficulty ** -W[12])
                 * (((stability + 1.0) ** W[13]) - 1.0)
                 * math.e ** (W[14] * (1.0 - r)))
    short_term = stability / math.e ** (W[17] * W[18])
    return _clamp(min(long_term, short_term), S_MIN, S_MAX)


def interval_for(stability):
    """I(r,S) → 四舍五入 → 下限 1 天 → 产品护栏 maximum_interval。"""
    days = (stability / FACTOR) * (DESIRED_RETENTION ** (1.0 / (-W[20])) - 1.0)
    return min(max(1, round_half_up(days)), MAXIMUM_INTERVAL)


# 缺省链（progress.md 元数据缺失时的兜底）：S 取 S0(good)、D 取 D0(good)，
# 与旧律的 default_s / default_d 同位置、同用途，值随增长律换新。
# 必须按输出侧同口径 round 到 4 位：D 是连续值，未 round 的 2.118103970459016 会被
# due-queue 原样写进 progress.md，与 data.md「落盘保留 4 位小数」及 next-interval 的
# 回显形态打架（两条路径对同一个 D 给出两种写法）。
DEFAULT_S = round(initial_stability("good"), 4)
DEFAULT_D = round(initial_difficulty("good"), 4)


def next_interval(grade, stability=None, difficulty=None, elapsed=None,
                  last=None, today=None, confidence=None,
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
        s_new = initial_stability(grade)
        d_new = initial_difficulty(grade)
    else:
        # 纵深防御：纯函数入口亦校验有限值与范围（CLI 已校验，直连调用不绕过）。
        require_finite(stability, "stability", S_MIN, S_MAX)
        require_finite(difficulty, "difficulty", D_MIN, D_MAX)
        # FSRS-6：失败档的遗忘后 S 也依赖 R(t,S)，故四档都要求 elapsed。
        require_finite(elapsed, "elapsed", 0.0, ELAPSED_INF)
        s_old = stability
        d_old = difficulty
        if elapsed == 0 and grade != "again":
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
            r = retrievability(elapsed, stability)
            if grade == "again":
                s_new = stability_after_failure(stability, difficulty, r)
            else:
                s_new = stability_after_success(stability, difficulty, r, grade)
            d_new = next_difficulty(difficulty, grade)

    # 输出侧确定性舍入（4 位小数）：消除浮点噪音（如 13.767699999999999），
    # 同输入同输出的 JSON 才逐字节稳定；D 是连续值（[1,10]，无粒度要求），
    # 落盘回读必须能逐位还原，故同口径保留 4 位。
    s_new = round(s_new, 4)
    d_new = round(d_new, 4)

    # 间隔由 S 与 desired_retention 反解（FSRS-6），不再直接取整 S。
    interval_days = interval_for(s_new)
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

# 条目元数据解析（META_KEYS / parse_meta / 括注拆分）已下沉 scripts/ltw_parse.py：
# due-queue 与 progress_check 必须读同一条判据（如「顺延=」），各写一份即判据分叉。
# 本模块只从 ltw_parse 导入，不再保留本地副本。



# parse_progress_sections / parse_meta / _looks_like_meta / split_weak_item /
# split_wrong_item 全部由 ltw_parse 提供（见文件头 import）。


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
        due = safe_add_days(last, interval_for(s_val))
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
        # 顺延=n：干预留痕计数（票 58 定语义、票 72 定消费口径）。缺省 None 与 0 都表示
        # 「无顺延」，回显时统一成整数；它不改 S/D、不写 last、不产生 evt，只作披露。
        "顺延": meta["顺延"] if meta["顺延"] is not None else 0,
    }, migrated


def observations_from_text(text, slug):
    """把 progress.md 两区条目解析为「原始观察」列表（未去重、未统计）。

    返回 (raws, warnings)；queue 与 calibration 共用，防解析器漂移。
    raw = {item, kind, wrong_date, recent, meta, meta_text}
    """
    recent_update, weak_lines, wrong_lines, retention_lines, _day_lines = parse_progress_sections(text)
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
    # 顺延披露（票 72 Q1：形态判据「顺延>0 → 下一轮开场必须明示」）。只报形态，
    # 不给「累计欠账」总数、不把顺延数当进度指标——Q3 的三条禁止项。
    if entry.get("顺延"):
        parts.append("已顺延 " + str(entry["顺延"]) + " 次（保留原到期日）")
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
    # 加键回显；排序契约不动（cw→最逾期→due 早→稳定序 逐字保留）
    fields = fields + ("错因", "级", "meta_default", "顺延", "reason")
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
            "confidence_dist": {str(i): 0 for i in range(1, 6)},
            "cw_items": [],
            "migrated_count": 0,
            "unparsed_count": 0,
            "default_filled": 0,
        }
        for o in obs:
            if o["evt"] is None:
                warnings.append("W-NO-EVT: " + slug + " / " + o["item"]
                                + "（条目无 evt= 作答事件 ID，按单条观察计入校准；"
                                  "同次作答的薄弱点/错题投影补同一 evt 可去重）")
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
# day-streak：日达标连续未达计数（只读、纯计算、不写盘；票 75 判据④）
# ---------------------------------------------------------------------------

def _prev_day(d):
    """前一天；越过 date.min 返回 None（结构化降级，不让 OverflowError 冒到外部协议）。"""
    try:
        return d - timedelta(days=1)
    except (OverflowError, ValueError):
        return None


def day_streak_output(root, slug_filter, today):
    """按「日达标」区派生连续未达天数（只存按天事实、不存派生计数）。

    口径（票 75 决议，逐条落在这里）：
      · 达的判据是**可机检等价物**：当天 ≥1 条到期复习或 ≥1 次作答——由模型在
        写入行时判定并落「达/未达」，本函数只消费行，不重算教学事实；
      · 连续天数由行序派生，**不单独落盘**；
      · 缺区合法：等同「无历史」，entries=[] / miss_streak=0，不推断不回溯；
      · **缺天终止计数**（宁可漏，不可错）：today 当天没有记录、或记录为「达」，
        连续段就此终止，绝不把「没记录」折算成「未达」；
      · 同一天多行按**最后一行**为准（后写覆盖先写），不静默累加；
      · 计数只从 today 往前数，不因未来日期行而提前终止。
    """
    entries_text, warnings = read_progress_entries(root, slug_filter)
    per_slug = []
    for slug, text in entries_text:
        _recent, _weak, _wrong, _ret, day_lines = parse_progress_sections(text)
        rows, bad = parse_day_rows(day_lines)
        for body in bad:
            warnings.append("W-DAY-ROW-INVALID: " + slug
                            + "（应为「<YYYY-MM-DD> ｜ 达|未达 ｜ 证据：<…>」，实际：" + body + "）")
        by_date = {}
        for row in rows:
            prev = by_date.get(row["date"])
            # 同日多行：**「达」优先**，其余按最后一行。
            # 方向不能反——反了就把「达标日」改判成「未达」，凭空造出一次未达并触发
            # 红线 8 判据④ 的干预，正是「宁可漏，不可错」要防的那种错。
            if prev is None or row["met"] or not prev["met"]:
                by_date[row["date"]] = row
        ordered = [by_date[d] for d in sorted(by_date)]
        miss_streak = 0
        cursor = today
        while True:
            row = by_date.get(cursor.isoformat())
            if row is None or row["met"]:
                break                           # 缺天 / 达 → 连续段终止
            miss_streak += 1
            nxt = _prev_day(cursor)
            if nxt is None:                     # 日期下溢（0001-01-01 再往前）→ 停，不裸崩
                warnings.append("W-DAY-STREAK-UNDERFLOW: " + slug
                                + "（连续未达已数到日期下界，计数在此停止）")
                break
            cursor = nxt
        last_met = None
        for row in ordered:
            if row["met"]:
                last_met = row["date"]
        per_slug.append({
            "slug": slug,
            "entries": ordered,
            "miss_streak": miss_streak,
            "last_met_date": last_met,
            "day_rows_invalid": len(bad),
        })
    return {
        "schema": _SCHEMAS["day_streak"],
        "today": today.isoformat(),
        "root": str(Path(root)),
        "per_slug": per_slug,
        "warnings": warnings,
    }


def cmd_day_streak(args):
    today = parse_date_str(args.today, "--today")
    root = Path(args.root)
    if not root.exists() or not root.is_dir():
        print("[learn-task-workflow] 数据根不存在或不是目录：" + str(root)
              + "（应指向 <工作区根>/.learning）", file=sys.stderr)
        return 1
    print(json.dumps(day_streak_output(root, args.slug, today),
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
    # FSRS-6：D 是 [1,10] 的连续值，不再要求 0.5 粒度（Q4=G1）。
    if not (D_MIN <= value <= D_MAX):
        fail("--difficulty 须在 [1,10]，收到：" + str(value))
    return float(value)


def cmd_next_interval(args):
    if args.new_card and args.stability is not None:
        fail("--new-card 与 --stability 不可同时使用")
    if not args.new_card and args.stability is None:
        fail("既有条目必须传 --stability（新卡请传 --new-card）")
    if args.new_card and args.difficulty is not None:
        fail("--new-card 时初始 D 由评分档的 D0(G) 决定，不传 --difficulty")
    stability = None
    difficulty = None
    if not args.new_card:
        stability = require_finite(args.stability, "--stability", S_MIN, S_MAX)
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
        elapsed = (today_d - last_d).days   # 有限且 ≥0（日期已校验，today ≥ last）；R(t,S) 随 t 单调趋 0
    elif args.elapsed is None:
        fail("必须提供 --elapsed 或 --last/--today 之一组（FSRS-6 四档都依赖 R(t,S)）")
    confidence = args.confidence
    if confidence is not None and not (1 <= confidence <= 5):
        fail("--confidence 须在 [1,5]，收到：" + str(confidence))
    if args.current_due is not None:
        parse_date_str(args.current_due, "--current-due")
    result = next_interval(args.grade, stability=stability, difficulty=difficulty,
                           elapsed=elapsed, last=last, today=args.today,
                           confidence=confidence,
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
        description="间隔重复调度计算（FSRS-6 增长律，只读，不写任何文件）")
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
    p4 = sub.add_parser("day-streak", help="日达标连续未达计数（只读，票 75 判据④）")
    p4.add_argument("--root", required=True)
    p4.add_argument("--slug", default=None)
    p4.add_argument("--today", required=True)
    p4.set_defaults(func=cmd_day_streak)
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
- 学科族：人文社科
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
- 学科族：人文社科
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
- 学科族：数学与统计
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
- 学科族：人文社科
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
- 学科族：人文社科
- 目标：自测
- 起点：入门

## 保持复习
- 第 3 节 函数 ｜ 元数据：S=4.0，D=3，last=2026-10-18，due=2026-10-22
- 第 4 节 类 ｜ 元数据：S=3.0，D=3，last=2026-10-18
"""

FIX_R3 = """# 学习任务：己
- 当前阶段：复习巩固
- 类型：知识型
- 学科族：人文社科
- 目标：自测
- 起点：入门

## 保持复习
- 第 5 节 无日期
"""


def approx(a, b, eps=1e-9):
    return abs(a - b) <= eps


def selftest():
    ok = True

    # 断言 1：good, S=3, D=3, elapsed=3（FSRS-6 重算：R=0.9687、S'=13.7677、D'=2.9922）
    # due 锚点 = 本次复习日 today（2026-10-13）+ 14 天 = 2026-10-27；不再用 last 起算
    r = next_interval("good", stability=3.0, difficulty=3, elapsed=3,
                      last="2026-10-10", today="2026-10-13")
    ok = ok and approx(r["stability_new"], 13.7677, 1e-4)
    ok = ok and approx(r["difficulty_new"], 2.9922, 1e-4)
    ok = ok and r["interval_days"] == 14
    ok = ok and r["due"] == "2026-10-27"

    # 断言 2：遗忘曲线单调——elapsed 越大 R 越小、S' 增幅越大；不再有 [0.25,2] 相对时间比地板
    r_low = next_interval("good", stability=3.0, difficulty=3, elapsed=0.5)
    ok = ok and approx(r_low["stability_new"], 5.4082, 1e-4)      # R≈0.977
    r_high = next_interval("good", stability=3.0, difficulty=3, elapsed=10)
    ok = ok and approx(r_high["stability_new"], 25.4873, 1e-4)    # R≈0.800
    ok = ok and r_low["stability_new"] < r["stability_new"] < r_high["stability_new"]

    # 断言 2b：同会话重复答对（elapsed=0）只刷新召回，不增长 S/D、不推迟 due（Q6=I1）
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
    ok = ok and approx(r_not_same["stability_new"], 7.4893, 1e-4)  # R≈0.957 -> 正常增长

    # 断言 3：失败档 again 走遗忘后 S（依赖 R、D），不再是与 elapsed 无关的 S*0.3
    r = next_interval("again", stability=5.0, difficulty=3, elapsed=5,
                      last="2026-10-05", today="2026-10-10")
    ok = ok and approx(r["stability_new"], 0.9839, 1e-4)
    ok = ok and approx(r["difficulty_new"], 7.6844, 1e-4)
    ok = ok and r["interval_days"] == 1
    ok = ok and r["due"] == "2026-10-11"
    r = next_interval("again", stability=2.0, difficulty=3, elapsed=2)
    ok = ok and approx(r["stability_new"], 0.5476, 1e-4)
    ok = ok and r["interval_days"] == 1  # 遗忘后 S 再小，间隔下限仍是 1 天

    # 断言 4：难度更新（线性阻尼 + 向 D0(4) 回归）与 [1,10] 连续夹持——不再有 0.5 粒度
    r = next_interval("hard", stability=3.0, difficulty=3, elapsed=3)
    ok = ok and approx(r["difficulty_new"], 5.3383, 1e-4)
    r = next_interval("easy", stability=3.0, difficulty=1, elapsed=3)
    ok = ok and r["difficulty_new"] == 1  # 下界夹持
    r = next_interval("again", stability=3.0, difficulty=5, elapsed=3)
    ok = ok and approx(r["difficulty_new"], 8.3418, 1e-4)
    r = next_interval("again", stability=3.0, difficulty=10, elapsed=3)
    ok = ok and approx(r["difficulty_new"], 9.9852, 1e-4)  # 上界附近仍连续
    ok = ok and r["difficulty_new"] <= 10.0
    # D 连续：1.4969 与 1.5 都合法，且都能原值落盘回读（不再被 0.5 粒度拦掉）
    ok = ok and approx(parse_meta("S=3，D=1.4969")["D"], 1.4969)
    ok = ok and approx(parse_meta("S=3，D=1.5")["D"], 1.5)
    ok = ok and check_difficulty(1.4969) == 1.4969
    ok = ok and check_difficulty(1.5) == 1.5

    # 断言 5：新卡 S0 = w[G-1]、D0 = clamp(w4-e^(w5*(G-1))+1, 1, 10)
    # easy 档 D0 原始值约 -4.77，靠夹持兜底到 1——这是 FSRS-6 默认参数的既有形态
    expect = {
        "again": (0.212, 6.4133, 1),
        "hard": (1.2931, 5.1122, 1),
        "good": (2.3065, 2.1181, 2),
        "easy": (8.2956, 1.0, 8),
    }
    for grade, (s0, d0, iv0) in expect.items():
        r = next_interval(grade, new_card=True)
        ok = ok and approx(r["stability_new"], s0, 1e-4)
        ok = ok and approx(r["difficulty_new"], d0, 1e-4)
        ok = ok and r["interval_days"] == iv0
        ok = ok and r["stability_old"] is None and r["difficulty_old"] is None
        ok = ok and r["same_session"] is False
    # 断言 5c：--init-shift 已删除——旧调用侧传它必须拿到 exit 2（argparse 未知参数），
    # 不得静默接受后按 D0(G) 返回，否则「已删除」只是文档承诺。
    try:
        main(["next-interval", "--grade", "good", "--new-card",
              "--last", "2026-11-13", "--today", "2026-11-13", "--init-shift", "1"])
        ok = False
    except SystemExit as exc:
        ok = ok and exc.code == 2

    # 断言 5b：遗忘后 S 的短期上界 min(长期项, S/e^(w17*w18)) 真的会生效
    # （票面六公式块原文；不是 w17-w19 的同日复习公式）。S=1/D=1/R≈0.1 时长期项反超。
    import math as _m
    _stf = _m.e ** (W[17] * W[18])
    _r5b = 0.1                               # S=1/D=1 且 R 极低时长期项反超（全域扫描实测）
    _long = (W[11] * (1.0 ** -W[12]) * (((1.0 + 1) ** W[13]) - 1.0)
             * _m.e ** (W[14] * (1.0 - _r5b)))
    _short = 1.0 / _stf
    ok = ok and _short < _long                       # 前提：短期项确实更小
    ok = ok and approx(stability_after_failure(1.0, 1.0, _r5b), _short, 1e-9)
    ok = ok and approx(stability_after_failure(1.0, 1.0, _r5b), min(_long, _short), 1e-9)

    # 断言 6：S 上限 s_max=36500 与产品护栏 maximum_interval=365 分开
    # S=300, easy, D=1, elapsed=300 -> S'=1470.4321（远未触 s_max），间隔封 365
    r = next_interval("easy", stability=300.0, difficulty=1, elapsed=300)
    ok = ok and approx(r["stability_new"], 1470.4321, 1e-3)
    ok = ok and r["stability_new"] < S_MAX
    ok = ok and r["interval_days"] == 365

    # 断言 6a：契约畸形必须 exit 1（与 rule_contract.load_or_exit 同口径），不是 exit 2。
    # 不启子进程（ops.md「脚本无子进程」），直接调 _contract_fail 看它抛什么。
    import contextlib as _cl
    import io as _io
    _buf = _io.StringIO()
    try:
        with _cl.redirect_stdout(_buf):
            _contract_fail("selftest 探针")
        ok = False                                   # 没抛即失败
    except SystemExit as _exc:
        ok = ok and _exc.code == 1
    _probe = json.loads(_buf.getvalue())
    ok = ok and _probe["ok"] is False
    ok = ok and _probe["code"] == "E-CONTRACT-INVALID"

    # 断言 6b（票 61 验收 1）：elapsed=1, S=100, good -> S' 增幅 < 5%
    # 旧律在 R 地板 0.25 下恒定 +62%，12 天顶到 365 天上限（票 59 的原始缺陷）
    r = next_interval("good", stability=100.0, difficulty=3, elapsed=1)
    ok = ok and (r["stability_new"] - 100.0) / 100.0 < 0.05
    ok = ok and approx(r["stability_new"], 102.8918, 1e-3)

    # 断言 6c（票 61 验收 2）：连续 12 天 daily good -> S < 100（旧律会顶到 365）
    s_walk, d_walk = initial_stability("good"), initial_difficulty("good")
    for _ in range(12):
        r_walk = next_interval("good", stability=s_walk, difficulty=d_walk, elapsed=1)
        s_walk, d_walk = r_walk["stability_new"], r_walk["difficulty_new"]
    ok = ok and s_walk < 100.0
    ok = ok and approx(s_walk, 51.3848, 1e-3)

    # 断言 6d（票 61 验收 6/7/8）：间隔恒 ≥1；同输入同输出；S 可长到 36500 而间隔封 365
    ok = ok and interval_for(S_MIN) >= 1
    ok = ok and interval_for(S_MAX) == MAXIMUM_INTERVAL
    r_idem_a = next_interval("good", stability=3.0, difficulty=3, elapsed=3)
    r_idem_b = next_interval("good", stability=3.0, difficulty=3, elapsed=3)
    ok = ok and json.dumps(r_idem_a, sort_keys=True) == json.dumps(r_idem_b, sort_keys=True)
    s_grow, d_grow = 365.0, 1.0
    for _ in range(6):
        r_grow = next_interval("easy", stability=s_grow, difficulty=d_grow,
                               elapsed=max(1, int(s_grow)))
        s_grow, d_grow = r_grow["stability_new"], r_grow["difficulty_new"]
    ok = ok and r_grow["interval_days"] == 365
    ok = ok and s_grow > 365.0  # S 继续长，只是间隔被封


    # 断言 7：due-queue（cw 排前 / 缺省链兜底 migrated / 无日期告警且 exit 0）
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
    ok = ok and by_item["默认链点"]["migrated"] is True  # 缺 S/D/due，靠「最近更新」兜底推日期
    # 缺省链已随增长律换新：S 取 S0(good)=2.3065、D 取 D0(good)=2.1181。
    # 断言必须与字面值比，不能与 DEFAULT_S/DEFAULT_D 自比——自比恒真，抓不到精度回归。
    ok = ok and approx(by_item["默认链点"]["S"], 2.3065, 1e-9)
    ok = ok and approx(by_item["默认链点"]["D"], 2.1181, 1e-9)
    # D 落盘形态必须与 next-interval 一致（4 位小数），不得泄出 2.118103970459016
    ok = ok and by_item["默认链点"]["D"] == next_interval("good", new_card=True)["difficulty_new"]
    ok = ok and str(by_item["默认链点"]["D"]).count(".") <= 1 and len(str(by_item["默认链点"]["D"]).split(".")[-1]) <= 4
    ok = ok and by_item["默认链点"]["due"] == "2026-10-07"  # 最近更新 10-05 + round(2.3065)=2
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
        ok = ok and out_r["schema"] == "ltw-due-queue/5"
        ok = ok and len(out_r["queue"]) == 1
        ok = ok and out_r["queue"][0]["kind"] == "保持"
        ok = ok and out_r["queue"][0]["reason"].startswith("保持复习")
        # 断言 7c：calibration 输出 schema 与契约一致（ltw-calibration/4），
        # 防止 schema 字符串在 rules.json 与 scripts-contract.json 之间再度漂移
        (root_r / "slug-mix").mkdir()
        (root_r / "slug-mix" / "progress.md").write_text(
            FIX_R + "\n## 薄弱点\n- 某点（S=3.0，D=3，last=2026-10-19，"
            "due=2026-10-20，信心=4，cw）\n", encoding="utf-8")
        cal_out = calibration_output(root_r, "slug-mix")
        ok = ok and cal_out["schema"] == _SCHEMAS["calibration"]
        ok = ok and cal_out["schema"] == "ltw-calibration/4"
        ok = ok and cal_out["per_slug"][0]["rate_valid"] is True
        ok = ok and cal_out["per_slug"][0]["overconfidence_rate"] == 1.0

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
         "--difficulty", "10.5", "--elapsed", "3"],  # D 越界（FSRS-6 上界 10）
        ["next-interval", "--grade", "good", "--stability", "3",
         "--difficulty", "0.5", "--elapsed", "3"],  # D 越界（FSRS-6 下界 1）
        ["next-interval", "--grade", "good", "--stability", "3",
         "--difficulty", "3"],  # 缺 elapsed 组（四档都依赖 R(t,S)）
        ["next-interval", "--grade", "again", "--stability", "3",
         "--difficulty", "3"],  # 失败档同样必须给 elapsed（FSRS-6 遗忘后 S 依赖 R）
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
    ok = ok and any(w.startswith("W-NO-EVT") and "slug-a" in w for w in cal_warn)  # 无 evt → 提示补标
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
    # v6.0 schema 升 ltw-due-queue/3（加 reason/保持复习）；v2.7 因 D 回显形态变化升 /4；
    # v2.8 加「顺延」回显键升 /5；
    # 排序契约（cw 排前）断言 7 逐字保留未动
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
    ok = ok and out["schema"] == "ltw-due-queue/5"

    # 断言 12b（v2.8）：顺延计数——解析、坏值、回显、reason 披露，且不进排序契约。
    # 顺延=n 是票 58 定的干预留痕（只碰 due、不碰 S/D），票 72 定其消费口径为形态判据。
    ok = ok and "顺延=" in META_KEYS
    ok = ok and parse_meta("S=3，D=3，顺延=1")["顺延"] == 1
    ok = ok and parse_meta("顺延=0")["顺延"] == 0
    # 坏值：非数字 / 负数 → invalid_tokens，按缺省链继续、不硬拒（与既有坏值口径一致）
    ok = ok and parse_meta("顺延=abc")["invalid_tokens"] == ["顺延=abc"]
    ok = ok and parse_meta("顺延=abc")["顺延"] is None
    ok = ok and parse_meta("顺延=-1")["invalid_tokens"] == ["顺延=-1"]
    # 重复键 → 标坏，保留首值（与 S/D 重复键同口径）
    _dup_sy = parse_meta("顺延=1，顺延=2")
    ok = ok and _dup_sy["invalid_tokens"] == ["顺延=2"] and _dup_sy["顺延"] == 1
    # 含顺延的括注必须能被拆成元数据段（否则「点（顺延=1）」会把元数据留在条目名里）
    _sy_name, _sy_meta = split_weak_item("点（S=3，D=3，顺延=2）")
    ok = ok and _sy_name == "点" and _sy_meta is not None
    # 回显与 reason 披露：顺延>0 → 条目带「顺延」键且 reason 明示次数
    _sy_q, _sy_w = queue_from_progress_texts(
        [("slug-sy", "- 最近更新：2026-10-01\n## 薄弱点\n"
                     "- 顺延点：没清完（S=3，D=3，last=2026-10-01，due=2026-10-02，顺延=2）\n"
                     "- 无顺延点：正常（S=3，D=3，last=2026-10-01，due=2026-10-02）\n")],
        date.fromisoformat("2026-10-10"))
    _sy_by = {e["item"]: e for e in _sy_q}
    ok = ok and _sy_by["顺延点：没清完"]["顺延"] == 2
    ok = ok and _sy_by["无顺延点：正常"]["顺延"] == 0
    ok = ok and "已顺延 2 次" in review_reason(_sy_by["顺延点：没清完"])
    ok = ok and "顺延" not in review_reason(_sy_by["无顺延点：正常"])
    # 顺延不得进排序契约：走**真实的** due_queue_output 排序，而不是在本断言里再排一遍
    # （自己按自己的键排一遍，等于没验被测代码——变异测试会照出这种假断言）。
    # 甲 due 更早（逾期 8 天）、乙 due 更晚（逾期 7 天）却带顺延=9：
    # 若顺延进了排序键，乙会被提前；正确行为是甲仍在前。
    with tempfile.TemporaryDirectory() as _td_sy:
        _root_sy = Path(_td_sy) / ".learning"
        (_root_sy / "slug-o").mkdir(parents=True)
        (_root_sy / "slug-o" / "progress.md").write_text(
            "- 最近更新：2026-10-01\n## 薄弱点\n"
            "- 甲：普通逾期（S=3，D=3，last=2026-10-01，due=2026-10-02）\n"
            "- 乙：大量顺延（S=3，D=3，last=2026-10-01，due=2026-10-03，顺延=9）\n",
            encoding="utf-8")
        _sy_out = due_queue_output(_root_sy, None, date.fromisoformat("2026-10-10"), False)
        _sy_items = [e["item"] for e in _sy_out["queue"]]
        ok = ok and _sy_items == ["甲：普通逾期", "乙：大量顺延"]
        ok = ok and _sy_out["queue"][1]["顺延"] == 9

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
    ok = ok and r15["interval_days"] == 29
    ok = ok and r15["due"] == "2026-11-13"

    # 断言 16：坏元数据隔离——单条坏数据（坏 S / 坏日历日期）不得让整队列裸崩，
    # 其余好条目仍可用；坏值按缺省链解析并标 migrated。
    fix_d = ("# 学习任务：坏元数据\n- 数据根：<root>\n- 当前阶段：复习巩固\n"
             "- 类型：知识型\n- 学科族：人文社科\n- 目标：自测\n- 起点：入门\n"
             "- 最近更新：2026-10-08\n\n## 学习路线\n- [ ] 1. 基础\n\n## 薄弱点\n"
             "- 坏S点：缺省（S=1..2，D=3，last=2026-10-09，due=2026-10-11）\n"
             "- 坏日期点：缺省（S=2.0，D=3，last=2026-02-30，due=2026-02-30）\n"
             "- 好点：正常（S=3.0，D=3，last=2026-10-09，due=2026-10-10）\n")
    q16, w16 = queue_from_progress_texts([("slug-d", fix_d)],
                                         date.fromisoformat("2026-10-12"))
    by16 = {e["item"].split("：")[0]: e for e in q16}
    ok = ok and len(q16) == 3  # 三条均入队，无崩溃、无丢失
    # 坏 S → 缺省链取 S0(good)=2.3065；坏日期 → 回退最近更新 2026-10-08 + round(2.3065)=2
    ok = ok and approx(by16["坏S点"]["S"], 2.3065, 1e-9) and by16["坏S点"]["migrated"] is True
    ok = ok and by16["坏日期点"]["due"] == "2026-10-10"
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
               "- 类型：知识型\n- 学科族：数学与统计\n- 目标：自测\n- 起点：入门\n\n## 薄弱点\n"
               "- A点：投影甲（S=3.0，D=3，last=2026-10-09，due=2026-10-10，信心=4，cw，evt=E1）\n"
               "- B点：投影乙（S=3.0，D=3，last=2026-10-09，due=2026-10-10，cw，evt=E1）\n"
               "- C点：无信心（S=3.0，D=3，last=2026-10-09，due=2026-10-10，cw）\n"
               "- D点：无信心（S=3.0，D=3，last=2026-10-09，due=2026-10-10，cw）\n")
    t04_per, t04_warn = calibration_from_progress_texts([("slug-t04", fix_t04)])
    t04 = t04_per[0]
    ok = ok and t04["total_items"] == 3        # B 与 A 同 evt → 只计一次（无 evt 的 C/D 各成单条）
    ok = ok and sum(1 for w in t04_warn if w.startswith("W-NO-EVT")) == 2  # C/D 无 evt → 提示补标
    ok = ok and t04["with_confidence"] == 1
    ok = ok and t04["cw_count"] == 1           # cw 必须是高信心(≥4)观察的子集
    ok = ok and t04["orphan_cw_count"] == 2    # C/D 有 cw 无信心 → 孤立，不入分子
    ok = ok and t04["overconfidence_rate"] is None and t04["rate_valid"] is False

    # 断言 19：单条过大 S 不得拖垮整队列（S=9999999 曾抛 year 29405 out of range；
    # 308 位 S 曾 OverflowError）——好条必须保留，坏条降级告警不崩。
    for bad_s in ("9999999", "9" * 308, "1e309"):
        fix_big = ("# 学习任务：大S\n- 当前阶段：复习巩固\n- 类型：知识型\n"
                   "- 学科族：人文社科\n- 目标：自测\n- 起点：入门\n"
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
    # FSRS-6 起 D=3.3 是合法连续值，坏 D 改用越界的 11（值域 [1,10]）
    m21 = parse_meta("S=3oops，D=11，last=2026-10-09oops，信心=50，cw")
    ok = ok and m21["S"] is None and m21["D"] is None and m21["last"] is None
    ok = ok and m21["信心"] is None and m21["cw"] is True
    ok = ok and len(m21["invalid_tokens"]) == 4
    m21b = parse_meta("S=3，D=3.5，last=2026-10-09，信心=5，cw")   # 合法：D 连续值、信心 1-5
    ok = ok and m21b["S"] == 3.0 and m21b["D"] == 3.5 and m21b["信心"] == 5
    ok = ok and m21b["invalid_tokens"] == []
    m21c = parse_meta("S=3，S=4，D=3")                             # 重复键 → 标坏
    ok = ok and m21c["invalid_tokens"] and m21c["S"] == 3.0
    # 断言 21d（v2.6）：META_KEYS 与 META_TOKEN_RES 对齐——attempt_id= 有解析器不再告警；
    # 错因=/级= 括注拆出；纯子串括注不误拆；坏值括注仍拆出走 W-META-INVALID 路径。
    m21d = parse_meta("S=3，attempt_id=A-9，evt=E1")
    ok = ok and m21d["attempt_id"] == "A-9" and m21d["evt"] == "E1"
    ok = ok and m21d["invalid_tokens"] == []
    w21e_name, w21e_meta = split_weak_item("极限定义（错因=理解性，级=A）")
    ok = ok and w21e_name == "极限定义" and w21e_meta == "错因=理解性，级=A"
    w21f_name, w21f_meta = split_weak_item("点（抄自 cw 笔记）")
    ok = ok and w21f_name == "点（抄自 cw 笔记）" and w21f_meta is None
    w21g_name, w21g_meta = split_weak_item("坏S点（S=3oops）")
    ok = ok and w21g_name == "坏S点" and w21g_meta == "S=3oops"

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
    ok = ok and evt24["total_items"] == 1 and evt24["cw_count"] == 1
    # 断言 25：长中断（10 年）不再因人为上界被拒（R(t,S) 单调趋 0，长中断自然压低增幅）
    try:
        main(["next-interval", "--grade", "good", "--stability", "3", "--difficulty", "3",
              "--last", "2016-10-14", "--today", "2026-10-15"])
    except SystemExit:
        ok = False

    # 断言 26（v2.9，票 75 判据④）：day-streak 只消费按天事实、缺天终止计数
    with tempfile.TemporaryDirectory() as td_ds:
        root_ds = Path(td_ds) / ".learning"

        def _mk(slug, day_block):
            d = root_ds / slug
            d.mkdir(parents=True)
            (d / "progress.md").write_text(
                "# 学习任务：丁\n- 最近更新：2026-10-15\n\n## 保持复习\n- 无\n\n"
                + day_block, encoding="utf-8")
            return d

        # 26a：连续三行未达 → miss_streak=3（今天 10-15，10-15/14/13 全未达）
        _mk("ds3", "## 日达标\n"
                   "- 2026-10-13 ｜ 未达 ｜ 证据：无\n"
                   "- 2026-10-14 ｜ 未达 ｜ 证据：无\n"
                   "- 2026-10-15 ｜ 未达 ｜ 证据：无\n")
        # 26b：缺区 → entries=[] 且 miss_streak=0（缺区合法，不推断、不回溯）
        _mk("dsnone", "")
        # 26c：缺天终止计数——10-15/10-14 未达，10-13 缺 → 只数 2，不把没记录当未达
        _mk("dsgap", "## 日达标\n"
                     "- 2026-10-14 ｜ 未达 ｜ 证据：无\n"
                     "- 2026-10-15 ｜ 未达 ｜ 证据：无\n")
        # 26d：坏行 → W-DAY-ROW-INVALID，且坏行不参与计数
        _mk("dsbad", "## 日达标\n"
                     "- 2026-10-15 未达（缺竖线）\n"
                     "- 2026-13-40 ｜ 未达 ｜ 证据：无\n"
                     "- 2026-10-15 ｜ 未知 ｜ 证据：无\n")
        # 26e：同日多行 → 最后一行生效；达 → 计数终止
        _mk("dslast", "## 日达标\n"
                      "- 2026-10-15 ｜ 未达 ｜ 证据：无\n"
                      "- 2026-10-15 ｜ 达 ｜ 证据：exercises/01-x.md\n")
        # 26f：今天是「达」→ miss_streak=0，但 last_met_date 记下来
        _mk("dsmet", "## 日达标\n"
                     "- 2026-10-14 ｜ 未达 ｜ 证据：无\n"
                     "- 2026-10-15 ｜ 达 ｜ 证据：evt=E1\n")

        ds = day_streak_output(root_ds, None, date.fromisoformat("2026-10-15"))
        by_slug = {p["slug"]: p for p in ds["per_slug"]}
        ok = ok and ds["schema"] == "ltw-day-streak/1"
        ok = ok and by_slug["ds3"]["miss_streak"] == 3
        ok = ok and len(by_slug["ds3"]["entries"]) == 3
        ok = ok and by_slug["ds3"]["entries"][0]["evidence"] == "无"
        ok = ok and by_slug["dsnone"]["entries"] == [] and by_slug["dsnone"]["miss_streak"] == 0
        ok = ok and by_slug["dsgap"]["miss_streak"] == 2          # 缺天终止，不折算成未达
        ok = ok and by_slug["dsbad"]["miss_streak"] == 0          # 坏行不参与计数
        ok = ok and by_slug["dsbad"]["day_rows_invalid"] == 3
        ok = ok and any(w.startswith("W-DAY-ROW-INVALID") for w in ds["warnings"])
        ok = ok and by_slug["dslast"]["miss_streak"] == 0         # 同日最后一行「达」生效
        ok = ok and by_slug["dslast"]["last_met_date"] == "2026-10-15"
        ok = ok and by_slug["dsmet"]["miss_streak"] == 0
        ok = ok and by_slug["dsmet"]["last_met_date"] == "2026-10-15"
        # 26g：今天没有记录（缺天）→ 不数（宁可漏，不可错）
        ds_tomorrow = day_streak_output(root_ds, "ds3", date.fromisoformat("2026-10-16"))
        ok = ok and ds_tomorrow["per_slug"][0]["miss_streak"] == 0
        # 26h：CLI 端到端——数据根不存在 exit 1，不谎报成功
        try:
            rc_ds = cmd_day_streak(argparse.Namespace(
                root=str(Path(td_ds) / "__no_such_dir__"), slug=None, today="2026-10-15"))
            ok = ok and rc_ds == 1
        except SystemExit:
            ok = False

    # 断言 27（复核 9aaf728 补）：同日「达→未达」不得反向改判（否则凭空造出一次未达）
    with tempfile.TemporaryDirectory() as td_rv:
        root_rv = Path(td_rv) / ".learning"
        d_rv = root_rv / "rv"
        d_rv.mkdir(parents=True)
        (d_rv / "progress.md").write_text(
            "# 学习任务：复核\n- 最近更新：2026-10-15\n\n## 日达标\n"
            "- 2026-10-15 ｜ 达 ｜ 证据：exercises/01-x.md\n"
            "- 2026-10-15 ｜ 未达 ｜ 证据：无\n"
            "- 2026-10-14 ｜ 未达 ｜ 证据：无\n", encoding="utf-8")
        rv = day_streak_output(root_rv, "rv", date.fromisoformat("2026-10-15"))
        ok = ok and rv["per_slug"][0]["miss_streak"] == 0     # 达优先，不改判
        # entries 按日期排序（不是插入序）：按日期取，别拿下标当顺序
        _by_date = {e["date"]: e for e in rv["per_slug"][0]["entries"]}
        ok = ok and _by_date["2026-10-15"]["met"] is True
        ok = ok and _by_date["2026-10-15"]["evidence"] == "exercises/01-x.md"
        # 反向顺序（未达→达）同结论：方向无关，达恒胜
        (d_rv / "progress.md").write_text(
            "# 学习任务：复核\n- 最近更新：2026-10-15\n\n## 日达标\n"
            "- 2026-10-15 ｜ 未达 ｜ 证据：无\n"
            "- 2026-10-15 ｜ 达 ｜ 证据：exercises/01-x.md\n", encoding="utf-8")
        rv2 = day_streak_output(root_rv, "rv", date.fromisoformat("2026-10-15"))
        ok = ok and rv2["per_slug"][0]["miss_streak"] == 0

        # 日期下溢：0001-01-01 再往前 → 结构化停（W-DAY-STREAK-UNDERFLOW），不裸崩
        d_uf = root_rv / "uf"
        d_uf.mkdir(parents=True)
        (d_uf / "progress.md").write_text(
            "# 学习任务：下溢\n- 最近更新：0001-01-02\n\n## 日达标\n"
            "- 0001-01-01 ｜ 未达 ｜ 证据：无\n"
            "- 0001-01-02 ｜ 未达 ｜ 证据：无\n", encoding="utf-8")
        uf = day_streak_output(root_rv, "uf", date(1, 1, 2))
        ok = ok and uf["per_slug"][0]["miss_streak"] == 2
        ok = ok and any(w.startswith("W-DAY-STREAK-UNDERFLOW") for w in uf["warnings"])

        # 模板占位行不是坏数据：照 data.md 原样抄不应自报坏行
        _tpl_rows, _tpl_bad = parse_day_rows([
            "<YYYY-MM-DD> ｜ <达|未达> ｜ 证据：<exercises 文件名 / evt=ID / 无>",
            "（无记录时本区写「无」）",
        ])
        ok = ok and _tpl_rows == [] and _tpl_bad == []
        # 但真坏行照报：日期非法 / 状态非法
        _bad_rows, _bad_bad = parse_day_rows(["2026-02-30 ｜ 未达 ｜ 证据：无", "2026-10-15 ｜ 未知 ｜ 证据：无"])
        ok = ok and _bad_rows == [] and len(_bad_bad) == 2
        # 证据位留空合法（未达本就没证据），不再当坏行
        _empty_rows, _empty_bad = parse_day_rows(["2026-10-15 ｜ 未达 ｜ 证据："])
        ok = ok and len(_empty_rows) == 1 and _empty_bad == []
        ok = ok and _empty_rows[0]["evidence"] == ""

    print(("OK " if ok else "FAIL ") + "scheduler --selftest")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
