#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""progress.md 与知识清单的共享行级解析原语（单一实现）。

task_index / progress_check / kp_sort / scheduler 复用同一实现，防止字段行、
路线行、暂缓条目、KP 行的解析口径在各脚本间分叉。只收行级与字符级原语；
清单**文件级**读取（头行键、覆盖摘要、IO 语义）因各脚本返回契约不同而留在
各自模块，行级解析一律走本模块。

契约唯一来源 contracts/rules.json（缺失/畸形即结构化失败，fail closed）。
"""
from __future__ import annotations

import re

import rule_contract

_C = rule_contract.load_or_exit()["constants"]

# progress.md 字段行 / 学习路线勾选行 / 「下次续学」块位置行
FIELD_RE = re.compile(r"^-\s*([^：:]+)[：:]\s*(.*)$")
ROUTE_RE = re.compile(r"^-\s*\[([xX ])\]\s*(\d+)\.\s*(.*)$")
BLOCK_RE = re.compile(r"(?:已讲到第\s*)?(\d+)\s*/\s*(\d+)\s*块")
# 「暂缓与范围外」条目应含的三段（自由文本 + 竖线分段，不做枚举硬校验）
HOLD_KEYS = ("来源", "处置", "触发条件")
# KP 编号：行首锚定版（KP_ID_RE）供整字段校验；未锚定版（KP_ID_ANY_RE）供归一化与文本抽取
KP_ID_RE = re.compile(r"^KP-(\d+)-(\d+)$")
KP_ID_ANY_RE = re.compile(r"KP-(\d+)-(\d+)")

ENUM_KP_STATUS = tuple(_C["kp"]["states"])
ENUM_KP_TYPE = tuple(_C["kp"]["types"])
ENUM_KP_VISUAL = tuple(_C["kp"]["visual_tasks"])
KP_TYPE_ALIASES = dict(_C["kp"]["type_aliases"])
KP_VISUAL_ALIASES = dict(_C["kp"]["visual_aliases"])


def normalize_kp_id(kid):
    """KP 编号归一化：单位数与补零别名归一到两位规范形（KP-1-1 ≡ KP-01-01）。

    仅用于**重复检测与集合/前置匹配**（等价类比较，两侧同走本函数）；
    排序输出与落盘仍保留原书写形态（向后兼容）。
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
    """解析 KP 行可选字段（类型/视觉任务）；无字段返回 (None, [])，畸形返回 None。"""
    kp_type = None
    visual_tasks = []
    for seg in segs:
        if seg.startswith("类型：") or seg.startswith("类型:"):
            if kp_type is not None:
                return None
            raw = re.split(r"[：:]", seg, maxsplit=1)[1].strip()
            value = raw if raw in ENUM_KP_TYPE else KP_TYPE_ALIASES.get(raw.lower())
            if value is None:
                return None
            kp_type = value
        elif seg.startswith("视觉任务：") or seg.startswith("视觉任务:"):
            if visual_tasks:
                return None
            raw = re.split(r"[：:]", seg, maxsplit=1)[1].strip()
            if not raw:
                return None
            for tok in re.split(r"[,，、/\s]+", raw):
                if not tok:
                    continue
                value = tok if tok in ENUM_KP_VISUAL else KP_VISUAL_ALIASES.get(tok.lower())
                if value is None or value in visual_tasks:
                    return None
                visual_tasks.append(value)
            if not visual_tasks:
                return None
        else:
            return None
    return kp_type, visual_tasks


def parse_kp_row(segs):
    """清单行六段（KP编号｜知识点｜所属小节｜前置｜来源｜状态）+ 可选类型/视觉任务 → dict。

    可选字段缺失返回 type=None、visual_tasks=[]（旧任务统一闸口）；畸形返回 None。
    附带 sec_decl（显式「小节 N」序号，供与编号契约「编号第一节 = 所属节」比对）
    与 bottom_note（摸底「已会」括注探测，带括注行豁免 W-KP-STATE-MISMATCH）。
    """
    if len(segs) < 6:
        return None
    kid, title, section, pre, source, status = segs[:6]
    optional = parse_kp_optional(segs[6:])
    if optional is None:
        return None
    kp_type, visual_tasks = optional
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
    # K02：解析显式所属节的序号（仅当形如「小节 N」时）
    sec_decl = None
    sec_m = re.fullmatch(r"小节\s*(\d+)", section)
    if sec_m:
        sec_decl = int(sec_m.group(1))
    # 摸底「已会」括注探测（全角/半角括号双兼容）
    bottom_note = raw_status.startswith("已会") or re.match(r"^未讲[(（]\s*已会", raw_status) is not None
    return {"id": kid, "sec": int(m.group(1)), "no": int(m.group(2)),
            "sec_decl": sec_decl, "prereqs": prereqs, "status": base,
            "bottom_note": bottom_note, "type": kp_type, "visual_tasks": visual_tasks}
