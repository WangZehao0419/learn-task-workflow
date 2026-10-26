#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kp_sort.py - 知识清单 KP 依赖拓扑排序与检环（确定性，stdlib-only）。

用途：知识型/技能型任务在 S2「排序」子步调用（见 references/workflow.md），
对知识清单文件（行式六字段 + 可选类型/视觉任务，格式见 references/data.md
「知识清单文件」）按各行「前置」声明的依赖边计算合法拓扑序。判断归模型（依赖边真实性、
该不该有边），排序与检环归本脚本；只读零写盘。可选分型字段由 progress_check 校验，
本脚本只读前六段并忽略附加段。

用法：
    python kp_sort.py <清单文件路径>
    python kp_sort.py --selftest

输出（stdout，JSON）：
    成功  {"order": ["KP-01-01", ...], "version": <N|null>, "count": <M>, "sort_rule": <...|null>}
    失败  {"error": "..."}（含环时另含 "cycle" 环路径数组）
退出码：0 成功 / 1 失败（清单缺失、畸形、前置引用不存在、依赖环、版本不足）/ 2 用法错误

确定性纪律：
  - 同层 tie-break 在脚本内显式实现：最小堆 Kahn 变体，按 KP 编号（节序, KP 序）
    数值升序出堆——同输入双跑输出逐字节一致（幂等）；禁止依赖 graphlib 迭代序
    （graphlib 仅用于 prepare() 检环，其排序输出不读取不透传）。
  - 路径以显式实参为基准，不依赖 cwd；无任何写盘调用。
  - 解释器版本不足（无 graphlib）时显式报错，不静默降级。
"""

import argparse
import heapq
import json
import re
import sys
from pathlib import Path

from ltw_parse import KP_ID_RE, normalize_kp_id, parse_kp_row

VALID = """# 知识清单：格式演示（示例仅为格式演示，KP 取舍与依赖声明规则领域无关）
- 版本：2
- 排序规则：拓扑序（依赖边见各行前置列）
- 覆盖范围：全量
- 覆盖摘要：总 5 ｜ 未讲 5 ｜ 已讲 0 ｜ 暂缓 0 ｜ 排除 0

- KP-01-01 ｜ 概念甲 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 1.1 ｜ 状态：未讲
- KP-01-02 ｜ 概念乙 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 1.1 ｜ 状态：未讲
- KP-02-01 ｜ 方法丙 ｜ 小节 2 ｜ 前置：KP-01-02 ｜ 来源：总纲 1.2 ｜ 状态：未讲
- KP-02-02 ｜ 综合题 ｜ 小节 2 ｜ 前置：KP-02-01，KP-01-01 ｜ 来源：总纲 1.2 ｜ 状态：未讲
- KP-03-01 ｜ 应用 ｜ 小节 3 ｜ 前置：  ｜ 来源：总纲 1.3 ｜ 状态：未讲
"""
CYCLE = """# 知识清单：含环夹具
- 版本：1

- KP-01-01 ｜ 甲 ｜ 小节 1 ｜ 前置：KP-01-03 ｜ 来源：总纲 1.1 ｜ 状态：未讲
- KP-01-02 ｜ 乙 ｜ 小节 1 ｜ 前置：KP-01-01 ｜ 来源：总纲 1.1 ｜ 状态：未讲
- KP-01-03 ｜ 丙 ｜ 小节 1 ｜ 前置：KP-01-02 ｜ 来源：总纲 1.1 ｜ 状态：未讲
"""
MALFORMED = """# 知识清单：畸形夹具
- 版本：1

- KP-01-01 ｜ 缺状态段 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 1.1
"""
BAD_PREREQ = """# 知识清单：前置悬空夹具
- 版本：1

- KP-01-01 ｜ 甲 ｜ 小节 1 ｜ 前置：KP-09-09 ｜ 来源：总纲 1.1 ｜ 状态：未讲
"""
WIDE = """# 知识清单：单位数宽容夹具
- 版本：1

- KP-1-2 ｜ 乙 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 1.1 ｜ 状态：未讲
- KP-1-10 ｜ 丙 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 1.1 ｜ 状态：未讲
- KP-1-1 ｜ 甲 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 1.1 ｜ 状态：未讲
"""
MIXED = """# 知识清单：状态混合夹具（order 含全部行，excluded/held 单独计数）
- 版本：1

- KP-01-01 ｜ 甲 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 1.1 ｜ 状态：已讲
- KP-01-02 ｜ 乙 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 1.1 ｜ 状态：排除
- KP-02-01 ｜ 丙 ｜ 小节 2 ｜ 前置：KP-01-01 ｜ 来源：总纲 1.2 ｜ 状态：暂缓
- KP-02-02 ｜ 丁 ｜ 小节 2 ｜ 前置：  ｜ 来源：总纲 1.2 ｜ 状态：未讲(已会：摸底全对，2026-10-11)
"""
HALF_WIDTH_HEADER = """# 知识清单：半角头行夹具（头行冒号半角/全角双兼容，与 progress_check 口径对齐）
- 版本: 7
- 覆盖范围: 全量

- KP-01-01 ｜ 甲 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 1.1 ｜ 状态：未讲
"""
TYPED = """# 知识清单：分型字段夹具（排序只读前六段）
- 版本：1
- 覆盖范围：全量

- KP-01-01 ｜ 甲 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 1.1 ｜ 状态：未讲 ｜ 类型：概念
- KP-01-02 ｜ 乙 ｜ 小节 1 ｜ 前置：KP-01-01 ｜ 来源：总纲 1.1 ｜ 状态：未讲 ｜ 类型：记忆 ｜ 视觉任务：识别, 关系
"""


def kp_key(kid):
    """tie-break 键：(节序, KP 序) 数值升序——纯数字字典序 = 教学序；单位数宽容。"""
    m = KP_ID_RE.match(kid)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return (10 ** 9, 10 ** 9)


def parse_kp_list(text):
    """解析清单文本（只读）。返回 dict：version / sort_rule / rows / malformed。
    头行键名（版本 / 排序规则 / 文件头行名集）全角/半角冒号双兼容（与 progress_check 口径对齐）；
    version 半角头行不再静默丢失（返回 None）。"""
    version = None
    sort_rule = None
    rows, malformed = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if re.match(r"^-\s*版本[：:]", line):
            m = re.search(r"\d+", re.split(r"[：:]", line, maxsplit=1)[1])
            version = int(m.group()) if m else None
            continue
        if re.match(r"^-\s*排序规则[：:]", line):
            sort_rule = re.split(r"[：:]", line, maxsplit=1)[1].strip()
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
        elif line.startswith("- ") and KP_ID_RE.match(line[2:].strip().split(" ", 1)[0]):
            # KP 行缺竖线分段（如「- KP-01-01 变量命名 小节 1」）→ 计畸形，
            # 不得静默吞成「空合法清单」成功（P1）
            malformed.append(line[2:].strip())
    return {"version": version, "sort_rule": sort_rule, "rows": rows, "malformed": malformed}


def find_cycle(ids, deps):
    """沿「前置边」做确定性 DFS，返回真实闭环路径（首尾为同一节点，不含无环叶）。

    只用自生成路径输出：不读取、不拼接第三方异常文本（graphlib 的 str(CycleError)
    内含集合迭代序，跨 hash seed 不稳定）。遍历顺序全部经 kp_key 显式排序，保证
    跨 `PYTHONHASHSEED` 逐字节一致；未找到环时返回剩余节点（仅作兜底，不应触发）。
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {i: WHITE for i in ids}
    for start in sorted(ids, key=kp_key):
        if color[start] != WHITE:
            continue
        path = [start]                 # 当前 DFS 栈上的 GRAY 节点（自生成路径）
        on_path = {start: 0}
        color[start] = GRAY
        stack = [(start, iter(sorted((d for d in deps.get(start, ()) if d in color), key=kp_key)))]
        while stack:
            node, it = stack[-1]
            pushed = False
            for nxt in it:
                if color[nxt] == GRAY:
                    # 命中栈上灰色节点 → 从该节点到当前的路径即真实闭环（首尾同节点）
                    return path[on_path[nxt]:] + [nxt]
                if color[nxt] == WHITE:
                    color[nxt] = GRAY
                    on_path[nxt] = len(path)
                    path.append(nxt)
                    stack.append((nxt, iter(sorted((d for d in deps.get(nxt, ()) if d in color), key=kp_key))))
                    pushed = True
                    break
            if not pushed:
                color[node] = BLACK
                path.pop()
                del on_path[node]
                stack.pop()
    return sorted(ids, key=kp_key)


def _counts(rows):
    """excluded/held 计数：状态为排除/暂缓的条目数（order 含清单全部行，
    讲授序与出题序仅取纳入项 = 状态 ∈ {未讲, 已讲}，口径见 data.md）。"""
    excluded = sum(1 for r in rows if r["status"] == "排除")
    held = sum(1 for r in rows if r["status"] == "暂缓")
    return excluded, held


def sort_from_text(text):
    """清单文本 → (结果 dict, 退出码)。纯函数，零副作用。"""
    parsed = parse_kp_list(text)
    if parsed["malformed"]:
        return ({"error": "清单存在畸形行（六字段：KP编号｜知识点｜所属小节｜前置｜来源｜状态）："
                          + parsed["malformed"][0],
                 "malformed_count": len(parsed["malformed"])}, 1)
    rows = parsed["rows"]
    ids = [r["id"] for r in rows]
    # 别名归一：仅用于查重与前置匹配；输出 order 保留原书写形态（向后兼容）
    norm = [normalize_kp_id(i) for i in ids]
    norm_to_raw = {}
    for r, n in zip(rows, norm):
        norm_to_raw.setdefault(n, r["id"])
    seen, dups = set(), []
    for n in norm:
        if n in seen and n not in dups:
            dups.append(n)
        seen.add(n)
    if dups:
        return ({"error": "清单存在重复 KP 编号（含单位数/补零别名归一）：" + "、".join(dups)}, 1)
    if not ids:
        # 显式空清单（如「无」）→ 成功返回空 order；但**含 KP 编号痕迹却零解析行**
        # → 疑似解析失败，不得静默吞成「空成功」（P1）
        if re.search(r"KP-\d+-\d+", text):
            return ({"error": "疑似解析失败：文本含 KP 编号但未解析出任何合法 KP 行"
                              "（检查六字段：KP编号｜知识点｜所属小节｜前置｜来源｜状态）",
                     "kp_token_found": True}, 1)
        exc_n, held_n = _counts(rows)
        return ({"order": [], "version": parsed["version"], "count": 0,
                 "excluded": exc_n, "held": held_n,
                 "sort_rule": parsed["sort_rule"]}, 0)
    # K02 显式所属节与编号冲突：编号第一节数字即所属节序号，显式声明的节号必须一致
    sec_conflicts = [r for r in rows if r["sec_decl"] is not None and r["sec_decl"] != r["sec"]]
    if sec_conflicts:
        return ({"error": "KP 显式所属节与编号冲突：" + "、".join(
                    "{0}（编号节 {1}，声明小节 {2}）".format(r["id"], r["sec"], r["sec_decl"])
                    for r in sec_conflicts),
                 "section_conflicts": [{"id": r["id"], "id_section": r["sec"],
                                        "declared_section": r["sec_decl"]} for r in sec_conflicts]}, 1)
    for r in rows:
        missing = [p for p in r["prereqs"] if normalize_kp_id(p) not in norm_to_raw]
        if missing:
            return ({"error": "KP " + r["id"] + " 前置引用不存在的 KP：" + "、".join(missing)}, 1)

    # K01 硬先修教学阻塞：纳入项（未讲/已讲）的硬前置若被文档过滤为暂缓/排除，
    # 实际讲授序会缺失必需先修——必须显式报 blocker，不能让调用侧从成功序里自行过滤。
    # 软边保持现状：「软辅助：X」不是硬边（解析阶段已拒绝），前置列一律视为硬边。
    status_by_norm = {normalize_kp_id(r["id"]): r["status"] for r in rows}
    blockers = []
    for r in rows:
        if r["status"] not in ("未讲", "已讲"):
            continue
        for p in r["prereqs"]:
            disposition = status_by_norm.get(normalize_kp_id(p))
            if disposition in ("暂缓", "排除"):
                blockers.append({"kp": r["id"], "prerequisite": p, "prerequisite_status": disposition})
    if blockers:
        detail = "；".join("{0} 的硬前置 {1} 状态为{2}".format(b["kp"], b["prerequisite"], b["prerequisite_status"])
                           for b in blockers)
        return ({"error": "纳入项存在被暂缓/排除的硬先修，讲授序不完整：" + detail, "blockers": blockers}, 1)

    # 依赖边以「原 id」为键（输出向后兼容），前置目标经别名归一回映射到原 id
    deps = {r["id"]: {norm_to_raw[normalize_kp_id(p)] for p in r["prereqs"]} for r in rows}
    # 检环（契约口径：捕获环形依赖异常 → exit ≠ 0 + 环路径，不静默）；
    # 标准库实名 graphlib.CycleError；
    # graphlib 仅用 prepare() 检环，其迭代序/排序输出不读取不透传（禁止依赖 static_order）。
    try:
        from graphlib import TopologicalSorter
    except ImportError:
        return ({"error": "Python 版本不足：kp_sort 依赖标准库 graphlib（Python ≥ 3.9），"
                          "本技能要求 Python ≥ 3.10；当前 " + sys.version.split()[0] + "，不静默降级"}, 1)
    try:
        from graphlib import CycleError as _CycleError
    except ImportError:  # 防御：极旧/改名运行时回退
        try:
            from graphlib import CircularDependencyError as _CycleError
        except ImportError:
            _CycleError = ValueError
    try:
        TopologicalSorter(deps).prepare()
    except _CycleError:
        # K03：环路径由自生成 DFS（find_cycle）给出，只输出确定性路径；
        # 不拼接 str(exc)（graphlib 的异常文本内含集合迭代序，跨 hash seed 不稳定）。
        cycle = find_cycle(ids, deps)
        return ({"error": "检测到依赖环：" + " → ".join(cycle), "cycle": cycle}, 1)

    # 最小堆 Kahn 变体：同层按 kp_key 数值升序出堆，保证幂等（同输入逐字节一致）。
    indeg = {i: len(deps[i]) for i in ids}
    dependents = {i: [] for i in ids}
    for i in ids:
        for d in deps[i]:
            dependents[d].append(i)
    heap = [kp_key(i) + (i,) for i in ids if indeg[i] == 0]
    heapq.heapify(heap)
    order = []
    while heap:
        _s, _n, i = heapq.heappop(heap)
        order.append(i)
        for nxt in dependents[i]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                heapq.heappush(heap, kp_key(nxt) + (nxt,))
    exc_n, held_n = _counts(rows)
    return ({"order": order, "version": parsed["version"], "count": len(order),
             "excluded": exc_n, "held": held_n,
             "sort_rule": parsed["sort_rule"]}, 0)


def run(kp_list_path):
    p = Path(kp_list_path)
    if not p.is_file():
        return ({"error": "清单文件不存在：" + str(p)}, 1)
    try:
        text = p.read_text(encoding="utf-8-sig", errors="replace")  # utf-8-sig：BOM 吞首行缝隙闭合，无 BOM 无副作用
    except OSError as exc:
        return ({"error": "清单文件不可读：" + str(exc)}, 1)
    return sort_from_text(text)


def selftest():
    ok = True

    # ① 合法清单：输出为合法拓扑序（逐边断言前置先于后继）
    res, code = sort_from_text(VALID)
    ok = ok and code == 0 and "order" in res
    order, pos = res["order"], {k: i for i, k in enumerate(res["order"])}
    deps = {r["id"]: r["prereqs"] for r in parse_kp_list(VALID)["rows"]}
    for k, ds in deps.items():
        for d in ds:
            ok = ok and pos[d] < pos[k]
    # ② 同层 tie-break 显式：无依赖者按 (节序, KP 序) 升序出堆（不依赖 graphlib 迭代序）
    ok = ok and order[0] == "KP-01-01" and order[1] == "KP-01-02" and order[4] == "KP-03-01"
    ok = ok and res["count"] == 5 and res["version"] == 2
    ok = ok and res["excluded"] == 0 and res["held"] == 0

    # ②b 状态混合：order 含全部行；excluded/held 计数正确；半角括号「未讲(已会：…)」宽容解析
    res2b, code2b = sort_from_text(MIXED)
    ok = ok and code2b == 0
    ok = ok and res2b["count"] == 4 and res2b["excluded"] == 1 and res2b["held"] == 1
    ok = ok and set(res2b["order"]) == {"KP-01-01", "KP-01-02", "KP-02-01", "KP-02-02"}

    # ③ 单位数宽容：数值序而非字符串字典序（KP-1-2 先于 KP-1-10）
    res3, code3 = sort_from_text(WIDE)
    ok = ok and code3 == 0 and res3["order"] == ["KP-1-1", "KP-1-2", "KP-1-10"]

    # ④ 含环夹具：exit ≠ 0 + error 含环路径，不静默
    resc, codec = sort_from_text(CYCLE)
    ok = ok and codec != 0 and "环" in resc.get("error", "")
    ok = ok and set(resc.get("cycle", [])) == {"KP-01-01", "KP-01-02", "KP-01-03"}

    # ⑤ 畸形清单显式报错；前置引用不存在显式报错
    resm, codem = sort_from_text(MALFORMED)
    ok = ok and codem != 0 and "畸形" in resm.get("error", "")
    resp, codep = sort_from_text(BAD_PREREQ)
    ok = ok and codep != 0 and "KP-09-09" in resp.get("error", "")

    # ⑥ 幂等：同输入双跑输出逐字节一致
    s1 = json.dumps(sort_from_text(VALID)[0], ensure_ascii=False, sort_keys=True)
    s2 = json.dumps(sort_from_text(VALID)[0], ensure_ascii=False, sort_keys=True)
    ok = ok and s1 == s2 and s1 == json.dumps(res, ensure_ascii=False, sort_keys=True)

    # ⑦ 头行冒号宽容：半角/全角双兼容（与 progress_check 口径对齐）——半角头行 version 正确解析
    resh, codeh = sort_from_text(HALF_WIDTH_HEADER)
    ok = ok and codeh == 0 and resh["version"] == 7
    ok = ok and resh["order"] == ["KP-01-01"] and resh["count"] == 1

    # ⑧ P1 空/疑似解析失败分离：显式「无」清单 → 成功空 order
    empty_ok = "# 知识清单：空\n- 版本：1\n- 覆盖范围：全量\n\n- 无\n"
    rese, codee = sort_from_text(empty_ok)
    ok = ok and codee == 0 and rese.get("order") == [] and rese.get("count") == 0

    # ⑨ P1 缺竖线分段的 KP 行 → 计畸形（不静默吞为空成功）
    no_sep = "# 知识清单：缺分隔\n- 版本：1\n\n- KP-01-01 变量命名 小节 1 前置 来源 状态 未讲\n"
    resn, coden = sort_from_text(no_sep)
    ok = ok and coden != 0 and "畸形" in resn.get("error", "")

    # ⑩ P1 含 KP 编号痕迹却零解析行（且无畸形行）→ 疑似解析失败，不吞为空成功
    ghost = "# 知识清单：幽灵\n- 版本：1\n- 覆盖摘要：总 1 ｜ 未讲 1 ｜ 已讲 0 ｜ 暂缓 0 ｜ 排除 0\n\n参考 KP-01-01\n"
    resg, codeg = sort_from_text(ghost)
    ok = ok and codeg != 0 and resg.get("kp_token_found") is True

    # ⑪ P1 别名归一：KP-1-1 与 KP-01-01 视为同一 KP → 重复报错（不产生两个对象）
    alias_dup = ("# 知识清单：别名重复\n- 版本：1\n\n"
                 "- KP-01-01 ｜ 甲 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 ｜ 状态：未讲\n"
                 "- KP-1-1 ｜ 甲别名 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 ｜ 状态：未讲\n")
    resd, coded = sort_from_text(alias_dup)
    ok = ok and coded != 0 and "重复" in resd.get("error", "")

    # ⑫ v6.1 可选类型/视觉任务字段：排序只读前六段，不因附加字段报畸形
    rest, codet = sort_from_text(TYPED)
    ok = ok and codet == 0 and rest.get("order") == ["KP-01-01", "KP-01-02"]

    # ⑫ P1 别名前置：前置用单位数 KP-1-1，目标写补零 KP-01-01 → 能命中，不误报不存在
    alias_pre = ("# 知识清单：别名前置\n- 版本：1\n\n"
                 "- KP-01-01 ｜ 甲 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 ｜ 状态：未讲\n"
                 "- KP-01-02 ｜ 乙 ｜ 小节 1 ｜ 前置：KP-1-1 ｜ 来源：总纲 ｜ 状态：未讲\n")
    resa, codea = sort_from_text(alias_pre)
    ok = ok and codea == 0 and resa["order"].index("KP-01-01") < resa["order"].index("KP-01-02")

    # ⑬ K01 硬先修教学阻塞：纳入项的硬前置被暂缓/排除 → 显式 blocker（不是成功序让调用侧自行过滤）
    held_pre = ("# 知识清单：暂缓硬先修\n- 版本：1\n\n"
                "- KP-01-01 ｜ 甲 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 ｜ 状态：暂缓\n"
                "- KP-02-01 ｜ 乙 ｜ 小节 2 ｜ 前置：KP-01-01 ｜ 来源：总纲 ｜ 状态：未讲\n")
    resh2, codeh2 = sort_from_text(held_pre)
    ok = ok and codeh2 != 0 and resh2.get("blockers")
    ok = ok and resh2["blockers"][0]["prerequisite"] == "KP-01-01"
    ok = ok and resh2["blockers"][0]["prerequisite_status"] == "暂缓"
    excluded_pre = ("# 知识清单：排除硬先修\n- 版本：1\n\n"
                    "- KP-01-01 ｜ 甲 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 ｜ 状态：排除\n"
                    "- KP-02-01 ｜ 乙 ｜ 小节 2 ｜ 前置：KP-01-01 ｜ 来源：总纲 ｜ 状态：已讲\n")
    resex, codeex = sort_from_text(excluded_pre)
    ok = ok and codeex != 0 and resex["blockers"][0]["prerequisite_status"] == "排除"

    # ⑭ K02 显式所属节与编号冲突：编号节 1 却声明「小节 99」→ 拒绝并结构化说明
    sec_conf = ("# 知识清单：所属节冲突\n- 版本：1\n\n"
                "- KP-01-01 ｜ 甲 ｜ 小节 99 ｜ 前置：  ｜ 来源：总纲 ｜ 状态：未讲\n")
    ress, codes = sort_from_text(sec_conf)
    ok = ok and codes != 0 and "冲突" in ress.get("error", "")
    ok = ok and ress.get("section_conflicts", [{}])[0].get("declared_section") == 99
    # 一致时不禁用：编号节与显式所属节相符 → 正常排序
    sec_ok = ("# 知识清单：所属节一致\n- 版本：1\n\n"
              "- KP-01-01 ｜ 甲 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 ｜ 状态：未讲\n")
    ok = ok and sort_from_text(sec_ok)[1] == 0

    # ⑮ K03 环路径：真实闭环（首尾同节点）、不含无环叶、且 error 不拼接第三方异常文本
    leaf_cycle = ("# 知识清单：环含无环叶\n- 版本：1\n\n"
                  "- KP-01-01 ｜ 甲 ｜ 小节 1 ｜ 前置：  ｜ 来源：总纲 ｜ 状态：未讲\n"
                  "- KP-01-02 ｜ 乙 ｜ 小节 1 ｜ 前置：KP-01-01，KP-01-03 ｜ 来源：总纲 ｜ 状态：未讲\n"
                  "- KP-01-03 ｜ 丙 ｜ 小节 1 ｜ 前置：KP-01-01，KP-01-02 ｜ 来源：总纲 ｜ 状态：未讲\n")
    resl, codel = sort_from_text(leaf_cycle)
    cyc = resl.get("cycle", [])
    ok = ok and codel != 0 and cyc and cyc[0] == cyc[-1] and "KP-01-01" not in cyc
    ok = ok and set(cyc) == {"KP-01-02", "KP-01-03"}
    ok = ok and "nodes are in a cycle" not in resl.get("error", "")  # 不含 graphlib 异常文本
    # 确定性（同进程双跑逐字节一致，等价于跨 hash seed 一致的口径）
    ok = ok and (json.dumps(resl, ensure_ascii=False, sort_keys=True)
                 == json.dumps(sort_from_text(leaf_cycle)[0], ensure_ascii=False, sort_keys=True))

    print(("OK " if ok else "FAIL ") + "kp_sort --selftest")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kp_sort.py")
    ap.add_argument("kp_list", nargs="?", default=None, help="知识清单文件路径（显式实参，不依赖 cwd）")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if sys.version_info < (3, 9):
        print(json.dumps({"error": "Python 版本不足：kp_sort 依赖标准库 graphlib（Python ≥ 3.9），"
                                   "本技能要求 Python ≥ 3.10；当前 " + sys.version.split()[0] + "，不静默降级"},
                         ensure_ascii=False, sort_keys=True))
        return 1
    if not args.kp_list:
        ap.print_usage()
        return 2
    result, code = run(args.kp_list)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
