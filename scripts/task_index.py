#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""task_index.py - 学习任务索引与进度解析（确定性，stdlib-only）。

用途：技能在「继续学习 / 问进度 / 会话开始」时调用，枚举数据根下的所有
任务目录，解析每个 progress.md 的关键字段，输出机器可读的 JSON 索引，并把索引
物化为数据根下的 index.json（派生缓存，可重复重建）；物化仅限规范数据根，非规范根跳过并告警。

用法：
         python task_index.py [--root <数据根>] [--write-index] [--selftest]

约定：
    --root 省略时，默认取 <cwd>/.learning（仅在 cwd = 工作区根时正确；
           推荐始终显式传 --root，见 SKILL.md「脚本调用约定」）。
    **默认只读不写索引**；仅显式传 `--write-index` 才物化 index.json（写时原子替换、
           区分「未变化/写入失败」，失败保留原缓存）。`--no-write-index` 为默认行为的显式写法。
    --root 应指向「数据根」（<工作区根>/.learning）；若指向其它位置会打印告警且不物化索引（保持只读）。
    输出：每任务含 hold_count（「暂缓与范围外」区块合规条目总数，含处置为「排除」的条目）、
          excluded_count（区块内处置为「排除」的合规条目数）与 hold_unparsed（畸形条目数，
          计 0 并向 stderr 出 W-UNPARSED-HOLD 告警）；暂缓口径 = hold_count − excluded_count；
          schema 为 learn-task-index/5，消费方按存在性读取新键（scan_status / scan_error /
          current_block / block_total）。
    scan_status：ok（完整枚举、无不可读条目）/ partial（完整枚举但有不可读条目）/
                 failed（无法枚举——root 非目录或列目录失败；tasks 不可信，task_count 置 null，
                 不得当「无任务」处理）。
    幂等：index.json 内容不含易变时间戳，同一输入重复执行结果一致。

退出码：0 正常（含 partial）/ 1 数据根缺失或非法 / 2 用法错误 / 3 枚举失败（failed，未覆盖缓存）
"""

import argparse
import contextlib
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import rule_contract

# 枚举唯一来源：contracts/rules.json（缺失/畸形即结构化失败）。
_C = rule_contract.load_or_exit()["constants"]
ENUM_PHASE = _C["phases"]
ENUM_TYPE = _C["types"]
ENUM_FAMILY = _C["subject_families"]

FIELD_RE = re.compile(r"^-\s*([^：:]+)[：:]\s*(.*)$")
# 已完成勾选：x / X 均识别
ROUTE_RE = re.compile(r"^-\s*\[([xX ])\]\s*(\d+)\.\s*(.*)$")
# 「下次续学」小节行里的块位置：「已讲到第 k/总块」→ current_block / block_total
BLOCK_RE = re.compile(r"(?:已讲到第\s*)?(\d+)\s*/\s*(\d+)\s*块")
# 「暂缓与范围外」区块条目应含的三段（自由文本 + 竖线分段，不做枚举硬校验）
HOLD_KEYS = ("来源", "处置", "触发条件")

# 数据根第一层的**合法全局文件**：不得判为「旧版单任务文件」（画像由文档声明为可选全局文件、脚本零感知）
LEGACY_EXCLUDE = {"profile.md"}


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


def default_root():
    """默认数据根 = <cwd>/.learning（仅当 cwd = 工作区根时正确）。"""
    return Path.cwd() / ".learning"


def is_canonical_data_root(path):
    """判断 path 是否形如 <工作区根>/.learning（软校验，仅用于告警）。"""
    p = Path(path)
    return p.name == ".learning"


def parse_progress(text):
    """从 progress.md 提取关键字段与列表计数（纯文本解析，无第三方依赖）。"""
    fields = {}
    section = None
    route_done = 0
    route_total = 0
    weak_points = []
    wrong_items = 0
    hold_entries = []   # 「暂缓与范围外」条目（非「无」行）
    block_done = None   # 「下次续学」小节行的块位置（可选，缺失为 None）
    block_total = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if section == "学习路线":
            m = ROUTE_RE.match(line.strip())
            if m:
                route_total += 1
                if m.group(1).lower() == "x":
                    route_done += 1
            continue
        if section == "薄弱点":
            s = line.strip()
            if s.startswith("- ") and s not in ("- 无", "- 无。"):
                weak_points.append(s[2:].strip())
            continue
        if section == "错题本":
            if line.strip().startswith("- ["):
                wrong_items += 1
            continue
        if section == "暂缓与范围外":
            s = line.strip()
            if s.startswith("- "):
                body = s[2:].strip()
                if body not in ("无", "无。"):
                    hold_entries.append(body)
            continue
        if section and section.startswith("下次续学"):
            m = BLOCK_RE.search(line)
            if m:
                block_done = int(m.group(1))
                block_total = int(m.group(2))
            continue
        m = FIELD_RE.match(line.strip())
        if m and section is None:
            key = m.group(1).strip()
            val = m.group(2).strip()
            if key not in fields:
                fields[key] = val
    malformed = [b for b in hold_entries if hold_entry_malformed(b)]
    valid_holds = [b for b in hold_entries if not hold_entry_malformed(b)]
    return {
        "fields": fields,
        "route_done": route_done,
        "route_total": route_total,
        "weak_points": weak_points,
        "wrong_items": wrong_items,
        "hold_count": len(valid_holds),  # 区块合规条目总数（含处置为排除的条目）；畸形条目计 0
        "hold_unparsed": len(malformed),
        "excluded_count": sum(1 for b in valid_holds if hold_disposition_excluded(b)),
        "block_done": block_done,
        "block_total": block_total,
    }


def classify(parsed):
    phase = parsed["fields"].get("当前阶段", "")
    return {
        "phase": phase,
        "phase_valid": phase in ENUM_PHASE,
        "type": parsed["fields"].get("类型", ""),
        "type_valid": parsed["fields"].get("类型", "") in ENUM_TYPE,
        "family": parsed["fields"].get("学科族", ""),
        "family_valid": parsed["fields"].get("学科族", "") in ENUM_FAMILY,
        "current_lesson": parsed["fields"].get("当前小节", ""),
        "current_block": parsed.get("block_done"),
        "block_total": parsed.get("block_total"),
        "review_from": parsed["fields"].get("复习来源阶段", ""),
        "last_update": parsed["fields"].get("最近更新", ""),
        "data_root": parsed["fields"].get("数据根", ""),
        "route_done": parsed["route_done"],
        "route_total": parsed["route_total"],
        "weak_point_count": len(parsed["weak_points"]),
        "wrong_item_count": parsed["wrong_items"],
        "hold_count": parsed["hold_count"],
        "hold_unparsed": parsed["hold_unparsed"],
        "excluded_count": parsed["excluded_count"],
    }


def _list_dir(path):
    """列目录（独立函数，便于 selftest 注入枚举失败以验证 failed 路径）。"""
    return sorted(Path(path).iterdir())


def scan(root):
    """枚举 root 下的任务目录与旧版单文件。

    返回 (tasks, legacy, root_exists, unreadable, scan_status, scan_error)：
      tasks      —— 解析成功的任务列表
      legacy     —— 数据根第一层的旧版单文件（扩展名大小写不敏感）
      root_exists—— root 是否存在
      unreadable —— 存在但读取失败的任务（{"slug":..,"error":"unreadable"}），
                    单条坏文件不阻断整次枚举（降级并继续）。
      scan_status—— ok（完整枚举、无不可读条目）/ partial（完整枚举但有不可读条目）/
                    failed（无法枚举：root 非目录，或列目录抛 OSError）。
                    failed 时 tasks/legacy 不可信，调用方不得当「无任务」处理。
      scan_error —— failed 时的结构化原因字符串；否则 None。
    """
    root = Path(root)
    tasks = []
    legacy = []
    unreadable = []
    if not root.exists():
        return tasks, legacy, False, unreadable, "ok", None
    if not root.is_dir():
        # root 存在但非目录：无法枚举 → failed；由 main() 决定退出码与提示，不在此崩溃。
        return tasks, legacy, True, unreadable, "failed", "root_not_a_directory"
    try:
        entries = _list_dir(root)
    except OSError as exc:
        print("[learn-task-workflow] 无法读取数据根：" + str(root) + "（" + str(exc) + "）",
              file=sys.stderr)
        return tasks, legacy, True, unreadable, "failed", "root_unreadable: " + str(exc)
    for p in entries:
        try:
            if p.is_dir():
                prog = p / "progress.md"
                if prog.exists():
                    try:
                        text = prog.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        unreadable.append({"slug": p.name, "error": "unreadable"})
                        continue
                    info = classify(parse_progress(text))
                    info["slug"] = p.name
                    info["progress"] = str(prog.relative_to(root).as_posix())
                    info["has_materials"] = (p / "materials").is_dir()
                    info["has_exercises"] = (p / "exercises").is_dir()
                    tasks.append(info)
            elif p.is_file() and p.suffix.lower() == ".md":
                # 扩展名大小写不敏感；排除数据根第一层的合法全局文件（如画像 profile.md），不得判为旧版单任务文件
                if p.name.lower() not in LEGACY_EXCLUDE:
                    legacy.append(p.name)
        except OSError:
            # 单条条目异常：降级跳过，不阻断整次枚举。
            unreadable.append({"slug": p.name, "error": "unreadable"})
            continue
    scan_status = "partial" if unreadable else "ok"
    return tasks, legacy, True, unreadable, scan_status, None


def build_index(root, tasks, legacy, root_exists, unreadable=None,
                scan_status="ok", scan_error=None):
    # 派生缓存：字段排序稳定、不含易变时间戳，保证幂等。
    return {
        "schema": "learn-task-index/5",  # 加键（scan_status/scan_error；current_block/block_total；failed 时 task_count=null）逐次升 schema，消费方按存在性读取
        "data_root": str(Path(root)),
        "root_exists": root_exists,
        "scan_status": scan_status,
        "scan_error": scan_error,
        # failed 时 tasks 不可信 → task_count 置 null（未知），绝不谎报 0（=「无任务」）
        "task_count": None if scan_status == "failed" else len(tasks),
        "tasks": sorted(tasks, key=lambda t: t["slug"]),
        "legacy_single_files": sorted(legacy),
        "unreadable": sorted(unreadable or [], key=lambda x: x["slug"]),
    }


def _write_atomic(path, payload):
    """同目录临时文件 + os.replace 原子替换（Windows 亦原子；可注入故障以测 failed 分支）。"""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)


def write_index_if_changed(root, index):
    """写 index.json：内容未变→"unchanged"；成功→"written"；失败→"failed"（不静默、不半截）。

    · 原子替换：先写同目录 `<name>.tmp`，再 `os.replace` 覆盖——中断不产生半截 JSON。
    · 区分「未变化」与「写入失败」，失败保留原缓存并向 stderr 告警。
    · 既有缓存**编码非法/内容损坏**时视为可重建派生数据：告警后直接重建，
      不因 UnicodeDecodeError 裸崩（R10）。
    """
    path = Path(root) / "index.json"
    payload = json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        if path.exists():
            try:
                existing = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, ValueError):
                print("[learn-task-workflow] 告警：既有 index.json 编码非法/内容损坏，"
                      "已按可重建派生数据处理并重建。", file=sys.stderr)
                existing = None
            if existing == payload:
                return "unchanged"
        _write_atomic(path, payload)
        return "written"
    except OSError as exc:
        tmp = path.with_name(path.name + ".tmp")
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        print("[learn-task-workflow] 告警：index.json 写入失败（" + str(exc) +
              "），保留原缓存、不产生半截文件。", file=sys.stderr)
        return "failed"


def warn_about_root(root, exists):
    """数据根缺失/非法时向 stderr 打印显式指引（不得静默）。"""
    root = Path(root)
    if not exists:
        print("[learn-task-workflow] 数据根不存在：" + str(root) + "\n"
              "  提示：默认根 = <cwd>/.learning，仅在 cwd = 工作区根时正确。\n"
              "  若你刚在技能包目录内运行，请显式传 --root \"<工作区根>/.learning\".",
              file=sys.stderr)
    elif not root.is_dir():
        print("[learn-task-workflow] --root 指向的不是目录：" + str(root) +
              "（应指向数据根 <工作区根>/.learning）", file=sys.stderr)
    elif not is_canonical_data_root(root):
        print("[learn-task-workflow] 告警：--root 不在规范数据根（<工作区根>/.learning）内："
              + str(root), file=sys.stderr)


SAMPLE = """# 学习任务：示例
- 数据根：<root>
- 当前阶段：逐节学习
- 类型：技能型
- 学科族：编程类
- 当前小节：2
- 复习来源阶段：无

## 学习路线
- [X] 1. 变量
- [ ] 2. 循环

## 薄弱点
- 循环边界：off-by-one

## 错题本
- [2026-01-01] 题A ｜ 错因：越界

## 暂缓与范围外
- 无
"""

# 暂缓区块夹具：2 条合规暂缓条目 + 1 条畸形（有竖线缺「触发条件」）
HOLD_SAMPLE = """# 学习任务：示例
- 数据根：<root>
- 当前阶段：逐节学习
- 类型：材料型
- 学科族：数学类
- 当前小节：2

## 学习路线
- [x] 1. 第一章
- [ ] 2. 第二章

## 暂缓与范围外
- 插入语 ｜ 来源：S2 对照 ｜ 处置：暂缓 ｜ 触发条件：用户要求
- 倒装句 ｜ 来源：范围护栏 ｜ 处置：暂缓 ｜ 触发条件：阶段末审计
- 虚拟语气 ｜ 来源：S2 对照 ｜ 处置：暂缓
- 超纲从句 ｜ 来源：S2 对照 ｜ 处置：经用户确认排除 ｜ 触发条件：无
"""

# 块游标夹具：从「下次续学」小节行解析「已讲到第 2/5 块」
BLOCK_SAMPLE = SAMPLE + "\n## 下次续学\n- 阶段：逐节学习；小节：第 2 节（已讲到第 2/5 块）；先收作业：无；先复习：无\n"
# 兼容：标题带后缀 + 无「已讲到第」前缀
BLOCK_SAMPLE_ALT = SAMPLE + "\n## 下次续学（v6.8）\n- 小节：第 2 节（第 2/5 块）\n"


def selftest():
    parsed = parse_progress(SAMPLE)
    info = classify(parsed)
    ok = (
        info["phase"] == "逐节学习"
        and info["phase_valid"]
        and info["type_valid"]
        and info["family_valid"]
        and info["route_done"] == 1          # 大写 [X] 也被计入
        and info["route_total"] == 2
        and info["weak_point_count"] == 1
        and info["wrong_item_count"] == 1
        # 无暂缓项（「无」行）→ hold_count 0，无畸形
        and info["hold_count"] == 0
        and info["excluded_count"] == 0
        and info["hold_unparsed"] == 0
    )
    # 合规条目计数 + 畸形条目计 0 并标注；排除条目计入 hold_count、单列 excluded_count
    hold_info = classify(parse_progress(HOLD_SAMPLE))
    ok = ok and hold_info["hold_count"] == 3 and hold_info["hold_unparsed"] == 1
    ok = ok and hold_info["excluded_count"] == 1
    # 旧档案（无暂缓区块）→ hold_count 0 不炸
    legacy_info = classify(parse_progress(SAMPLE.split("## 暂缓与范围外")[0]))
    ok = ok and legacy_info["hold_count"] == 0 and legacy_info["hold_unparsed"] == 0
    ok = ok and legacy_info["excluded_count"] == 0
    # 块游标：有「已讲到第 k/总块」→ 解析；无 → None（旧档案零迁移）
    block_info = classify(parse_progress(BLOCK_SAMPLE))
    ok = ok and block_info["current_block"] == 2 and block_info["block_total"] == 5
    block_alt = classify(parse_progress(BLOCK_SAMPLE_ALT))
    ok = ok and block_alt["current_block"] == 2 and block_alt["block_total"] == 5
    ok = ok and info["current_block"] is None and info["block_total"] is None
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / ".learning"
        d = root / "python"
        (d / "exercises").mkdir(parents=True)
        (d / "progress.md").write_text(SAMPLE, encoding="utf-8")
        # 旧版单文件：大写扩展名应被识别；合法全局画像 profile.md 不得被判为旧版文件
        (root / "旧版笔记.MD").write_text("旧内容", encoding="utf-8")
        (root / "profile.md").write_text("# 学习者画像\n- 类比领域：做饭\n", encoding="utf-8")
        tasks, legacy, exists, unreadable, scan_status, scan_error = scan(root)
        idx = build_index(root, tasks, legacy, exists, unreadable,
                          scan_status, scan_error)
        w1 = write_index_if_changed(root, idx)
        w2 = write_index_if_changed(root, idx)
        ok = ok and exists and len(tasks) == 1 and tasks[0]["slug"] == "python"
        ok = ok and legacy == ["旧版笔记.MD"]
        ok = ok and "profile.md" not in legacy  # 全局画像不得被判为旧版单任务文件
        ok = ok and unreadable == []
        ok = ok and scan_status == "ok" and scan_error is None
        ok = ok and idx["schema"] == "learn-task-index/5"
        ok = ok and w1 == "written" and w2 == "unchanged"  # 幂等：第二次不重写
        ok = ok and not (root / "index.json.tmp").exists()  # 原子替换不留半截
        # 非规范数据根（临时目录）不物化 index.json（保持只读）
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            rc = main(["--root", td])
        ok = ok and rc == 0 and not (Path(td) / "index.json").exists()

        # 默认只读：规范根下**不带** --write-index 也不物化（缓存写入改为显式 opt-in）
        canonical0 = Path(td) / "ws0" / ".learning"
        (canonical0 / "python").mkdir(parents=True)
        (canonical0 / "python" / "progress.md").write_text(SAMPLE, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc_nw = main(["--root", str(canonical0)])
        ok = ok and rc_nw == 0 and not (canonical0 / "index.json").exists()

        # 枚举失败注入：_list_dir 抛 OSError → scan_status=failed、exit 3、task_count=null，
        # 且**不得覆盖**上一次完整缓存（隔离故障注入，不依赖真实 ACL/断电）。
        canonical = Path(td) / "ws" / ".learning"
        (canonical / "python").mkdir(parents=True)
        (canonical / "python" / "progress.md").write_text(SAMPLE, encoding="utf-8")
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            rc_ok = main(["--root", str(canonical), "--write-index"])
        cache = canonical / "index.json"
        cache_before = cache.read_text(encoding="utf-8") if cache.exists() else None
        ok = ok and rc_ok == 0 and cache_before is not None and '"task_count": 1' in cache_before

        original_list = _list_dir

        def _boom(_path):
            raise OSError("injected read failure")

        try:
            globals()["_list_dir"] = _boom
            buf_out, buf_err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
                rc_fail = main(["--root", str(canonical)])
            payload = json.loads(buf_out.getvalue())
        finally:
            globals()["_list_dir"] = original_list
        cache_after = cache.read_text(encoding="utf-8") if cache.exists() else None
        ok = ok and rc_fail == 3
        ok = ok and payload["scan_status"] == "failed"
        ok = ok and payload["task_count"] is None  # 未知，不得谎报 0
        ok = ok and cache_after == cache_before  # 枚举失败不覆盖上次完整缓存

        # 写入失败注入：_write_atomic 抛 OSError → 返回 "failed"，保留原缓存、无 .tmp 半截残留
        before_write_fail = cache.read_text(encoding="utf-8")
        original_atomic = _write_atomic

        def _boom_write(_path, _payload):
            raise OSError("injected write failure")

        try:
            globals()["_write_atomic"] = _boom_write
            st = write_index_if_changed(canonical, {"schema": "injected", "changed": True})
        finally:
            globals()["_write_atomic"] = original_atomic
        ok = ok and st == "failed"
        ok = ok and cache.read_text(encoding="utf-8") == before_write_fail
        ok = ok and not (canonical / "index.json.tmp").exists()

        # R10：stdout 契约含 write_status（机器可读，不靠解析 stderr 自然语言）
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            main(["--root", str(canonical)])
        ok = ok and json.loads(buf_out.getvalue())["write_status"] is None  # 未写索引 → None

        # R10：partial 扫描不得覆盖上次完整缓存（一个 progress 不可读 → 2 任务缓存保留）
        canonical2 = Path(td) / "ws2" / ".learning"
        for slug in ("alpha", "beta"):
            (canonical2 / slug).mkdir(parents=True)
            (canonical2 / slug / "progress.md").write_text(SAMPLE, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            main(["--root", str(canonical2), "--write-index"])
        cache2 = canonical2 / "index.json"
        complete_cache = cache2.read_text(encoding="utf-8")
        ok = ok and '"task_count": 2' in complete_cache
        original_read_text = Path.read_text
        bad_progress = canonical2 / "beta" / "progress.md"

        def _partial_read(self, *a, **k):
            if self == bad_progress:
                raise OSError("injected partial unreadable")
            return original_read_text(self, *a, **k)

        try:
            Path.read_text = _partial_read
            buf_out, buf_err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
                rc_partial = main(["--root", str(canonical2), "--write-index"])
            payload_partial = json.loads(buf_out.getvalue())
        finally:
            Path.read_text = original_read_text
        ok = ok and rc_partial == 0 and payload_partial["scan_status"] == "partial"
        ok = ok and payload_partial["task_count"] == 1
        ok = ok and payload_partial["write_status"] == "skipped_incomplete_scan"  # 机器可读跳过原因
        ok = ok and cache2.read_text(encoding="utf-8") == complete_cache  # 完整缓存未被覆盖

        # R10：坏编码缓存 → 告警重建，不 UnicodeDecodeError 裸崩
        cache2.write_bytes(b"\xff\xfe\x80invalid-utf8")
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            rc_badenc = main(["--root", str(canonical2), "--write-index"])
        payload_badenc = json.loads(buf_out.getvalue())
        ok = ok and rc_badenc == 0
        ok = ok and payload_badenc["write_status"] == "written"
        ok = ok and '"task_count": 2' in cache2.read_text(encoding="utf-8")  # 已重建
        ok = ok and "编码非法" in buf_err.getvalue()
    print(("OK " if ok else "FAIL ") + "task_index --selftest")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="task_index.py")
    ap.add_argument("--root", default=None)
    ap.add_argument("--write-index", dest="write_index", action="store_true", default=False,
                    help="物化 index.json（默认不写；需显式开启）")
    ap.add_argument("--no-write-index", dest="write_index", action="store_false",
                    help="保持只读、不写 index.json（默认行为）")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    root = Path(args.root) if args.root else default_root()
    tasks, legacy, exists, unreadable, scan_status, scan_error = scan(root)
    index = build_index(root, tasks, legacy, exists, unreadable,
                        scan_status, scan_error)

    warn_about_root(root, exists)
    if scan_status == "failed":
        # 枚举失败：tasks 不可信——绝不当「无任务」，绝不覆盖上一次完整缓存。
        print("[learn-task-workflow] 枚举失败 scan_status=failed（原因：" + str(scan_error) +
              "）：数据根 " + str(root) + " 无法完整枚举；tasks 视为未知（task_count=null，非 0），"
              "已跳过 index.json 物化以保留上次完整缓存。", file=sys.stderr)
    if unreadable:
        print("[learn-task-workflow] 告警 " + str(len(unreadable)) +
              " 个任务目录的 progress.md 不可读，已在索引 unreadable 中标注。", file=sys.stderr)
    # 「暂缓与范围外」畸形条目：计 0 并显式告警，不静默（W-UNPARSED-HOLD）
    for t in tasks:
        if t.get("hold_unparsed", 0) > 0:
            print("[learn-task-workflow] 告警 W-UNPARSED-HOLD：任务 " + t["slug"] +
                  " 的「暂缓与范围外」区块有 " + str(t["hold_unparsed"]) +
                  " 条未解析条目（应含 来源/处置/触发条件 竖线分段），已计 0。", file=sys.stderr)

    # 仅当数据根为规范数据根（<工作区根>/.learning）、是合法目录、且**枚举完整（ok）**时才物化索引；
    # 枚举失败（failed）与部分扫描（partial）绝不覆盖上次完整缓存——partial 仍返回可读任务与
    # unreadable 原因，但缓存保持上一次完整版本（R10）。非规范根保持只读并向 stderr 明示。
    write_status = None
    if args.write_index and exists and root.is_dir():
        if not is_canonical_data_root(root):
            print("[learn-task-workflow] 告警：--root 不在规范数据根（<工作区根>/.learning）内，"
                  "已跳过 index.json 物化（保持只读）。", file=sys.stderr)
            write_status = "skipped_noncanonical_root"
        elif scan_status != "ok":
            print("[learn-task-workflow] 告警：scan_status=" + scan_status +
                  "（非完整扫描），已跳过 index.json 物化以保留上次完整缓存。", file=sys.stderr)
            write_status = "skipped_incomplete_scan"
        else:
            write_status = write_index_if_changed(root, index)
            if write_status == "written":
                print("[learn-task-workflow] 已物化 index.json（原子替换）。", file=sys.stderr)
            # "unchanged" 静默；"failed" 已在 write_index_if_changed 内告警
    # write_status 只进 stdout 契约、不进缓存内容（保持缓存逐字节稳定与幂等）
    out = dict(index)
    out["write_status"] = write_status
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    # 退出码：0 正常（含 partial）；1 数据根缺失或非目录（仍输出空索引，不崩溃）；3 枚举失败
    if scan_status == "failed":
        return 3
    return 0 if (exists and root.is_dir()) else 1


if __name__ == "__main__":
    sys.exit(main())
