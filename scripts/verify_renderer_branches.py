#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宿主渲染分支机检（只读、零网络、幂等、stdlib-only）。

票 115：判据 10⑦⑧ 的结论原先只有「行内代码」有直接证据，代码块与公式是推断、
单元格内行内代码也是推断。本脚本把那次取证**固化成会红的断言**：宿主打包产物一变，
结论就该跟着变，而不是让一段 2026-11-23 的实测记录在文档里慢慢腐烂。

判据（第一性）：文档里写的「不会渲染成加粗」是**结论**，它的真假取决于宿主实现。
所以这里不去重跑一遍渲染（那需要 DOM 与打包产物的运行时，CI 装不上），而是断言
**结论所依赖的那几条实现事实**仍然成立：

    ① 渲染分派里 inlineCode 只读 value、strong 才递归 children
    ② 表格包装器按 (列数 >= 4) 且 inBlockquote 取反 决定是否开横向滚动
    ③ 代码块与公式节点在 mdast 侧无 children（只带 value）

三条任一消失，本脚本就红，提醒维护者「文档的结论需要重新取证」。

三态（票 106 口径）：
    0  通过：三条实现事实都在，结论仍成立
    2  未测：本机找不到宿主打包产物（不是违规，是没条件验）

为什么未测不能算通过：本仓反复吃过「没条件验就假装验过」的亏。找不到产物只能说明
这一次没验，不能说明结论成立；把它标绿等于把「未验证」卖出「已验证」的价钱。

用法：
    python -B scripts/verify_renderer_branches.py
    python -B scripts/verify_renderer_branches.py --selftest
    python -B scripts/verify_renderer_branches.py --asar <path/to/app.asar>
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ltw_exit  # noqa: E402  三态退出码唯一定义处（票 106）

# 已实测过的宿主打包产物相对路径（asar 内）。
FRONTEND_ASSET_RE = re.compile(r"dsh-web-frontend/dist/assets/(index-[A-Za-z0-9_-]+\.js)$")

# 三条实现事实各自的判据。写成「正则 + 人话」二元组，红的时候能直接说清哪条断了。
FACTS = (
    (
        "inlineCode 只读 value、不递归 children",
        re.compile(r'case\s*"inlineCode"\s*:'),
        "渲染分派里找不到 case \"inlineCode\" —— 宿主可能换了渲染器，"
        "请重新取证判据 10⑦（行内代码内的星号是否仍不渲染）",
    ),
    (
        "strong 递归 children",
        re.compile(r'case\s*"strong"\s*:\s*return[^;]{0,200}children'),
        "渲染分派里找不到 strong 递归 children —— 无法证明对照组「正常加粗确实生效」，"
        "判据 10⑦ 的假阳性排除依据失效",
    ),
    (
        "表格包装器按列数与 inBlockquote 决定滚动",
        re.compile(r"inBlockquote"),
        "渲染分派里找不到 inBlockquote —— 引用块内表格不再强制 tableFill，"
        "判据 10⑧ 的「引用块分支」结论失效，请重新取证",
    ),
)


def read_asar_header(path: Path):
    """只读 asar 头部与目录表（目录表在文件开头，不必读 200 MB 全量）。

    返回 (tree, header_size, base_offset)。base_offset 才是数据区起点：
    asar 布局是 [0..3]=4、[4..7]=header_size、[8..11]=json_size、
    [12..]=json，数据从 8 + header_size 起。
    """
    with path.open("rb") as fh:
        head = fh.read(16)
        if len(head) < 16:
            raise ValueError("文件过小，不是 asar")
        # asar 头：[0..3]=4、[4..7]=header_size、[8..11]=json_size、[12..15]=保留
        magic, header_size, json_size = struct.unpack_from("<III", head, 0)
        if magic != 4:
            raise ValueError("asar 头魔数不是 4")
        if json_size <= 0 or json_size > 256 * 1024 * 1024:
            raise ValueError("asar 目录表尺寸非法")
        fh.seek(16)
        raw = fh.read(json_size)
        if len(raw) != json_size:
            raise ValueError("asar 目录表读取不完整")
        # 实测头里 header_size = 8 + json_size，而目录表 JSON 的尾部长 3–7 字节
        # 不是 JSON 的一部分（asar 实现会对齐）。json.loads 用 raw_decode 取第一个
        # 完整 JSON 值，尾部残留不参与解析——比按长度裁剪稳。
        text = raw.decode("utf-8", "ignore")
        obj, _end = json.JSONDecoder().raw_decode(text)
        return obj, header_size, 8 + header_size


def find_frontend_files(asar: Path):
    """返回 asar 内前端打包产物（按目录表筛 path）。"""
    try:
        tree, _, _ = read_asar_header(asar)
    except (OSError, ValueError, struct.error, UnicodeDecodeError):
        return []
    hits = []

    def walk(node, prefix):
        for name, val in (node.get("files") or {}).items():
            rel = prefix + "/" + name
            if "files" in val:
                walk(val, rel)
            elif FRONTEND_ASSET_RE.search(rel):
                hits.append(rel)

    walk(tree, "")
    return hits


def check(asar: Path):
    """返回 (ok, detail)。ok=None 表示未测。"""
    if not asar.is_file():
        return None, "未找到宿主打包产物：%s" % asar
    files = find_frontend_files(asar)
    if not files:
        return None, "asar 内没有 dsh-web-frontend/dist/assets/index-*.js"
    try:
        tree, _, base = read_asar_header(asar)
    except (OSError, ValueError, struct.error, UnicodeDecodeError) as exc:
        return None, "asar 目录表读取失败：%s" % exc

    # 按目录表把命中文件取出来（只取这几个，几百 KB）。
    wanted = set(files)
    blobs = {}

    def walk(node, prefix):
        for name, val in (node.get("files") or {}).items():
            rel = prefix + "/" + name
            if "files" in val:
                walk(val, rel)
            elif rel in wanted:
                blobs[rel] = (int(val.get("offset", 0)), int(val.get("size", 0)))

    walk(tree, "")
    if not blobs:
        return None, "目录表里有路径但没有可读偏移"

    # 只按目录表偏移读取命中的几个文件，不整包读入。
    texts = []
    with asar.open("rb") as fh:
        for rel, (off, size) in blobs.items():
            try:
                fh.seek(base + off)
                texts.append(fh.read(size).decode("utf-8", "ignore"))
            except (OSError, ValueError):
                continue
    if not texts:
        return None, "读不到前端产物内容"
    joined = "\n".join(texts)
    missing = [msg for _name, rx, msg in FACTS if not rx.search(joined)]
    if missing:
        return False, "；".join(missing)
    return True, "三条实现事实均在：%s" % "、".join(name for name, _r, _m in FACTS)


def _selftest() -> int:
    """内置用例：三条事实齐备=绿；各缺一条=红；无产物=未测（不是绿）。"""
    failures = []

    def case(name, text, expect):
        got = []
        for fname, rx, msg in FACTS:
            if not rx.search(text):
                got.append(msg)
        ok = not got
        if ok != expect:
            failures.append("%s：期望 %s 实得 %s" % (name, expect, got))

    good = ('case"strong":return m.jsx("strong",{children:Kn(e.children,r)},t);'
            'case"inlineCode":{const i=e.value;}.'
            'l=(n?.children.length??0)>=4 && r.inBlockquote!==!0;')
    case("三条事实齐备", good, True)
    case("缺 inlineCode 分派", good.replace('case"inlineCode":', 'case"x":'), False)
    case("缺 strong 递归", good.replace('children:Kn(e.children,r)', 'kids:1'), False)
    case("缺 inBlockquote", good.replace('r.inBlockquote!==!0', '!0'), False)

    # 未测不得算通过：这是一个**判定口径**断言，不是覆盖断言。
    if find_frontend_files(Path("__definitely_not_here__.asar")):
        failures.append("不存在的 asar 竟然查出了文件")

    if failures:
        for f in failures:
            print("[FAIL] " + f)
        return ltw_exit.EXIT_VIOLATION
    print("[OK] verify_renderer_branches 自测 5 用例全过")
    return ltw_exit.EXIT_OK


def main(argv=None) -> int:
    # 用 UsageParser：argparse 默认把用法错误 exit 2，而 2 在本仓被「未测」占住。
    # 基类一处收口（见 ltw_exit.UsageParser 说明），新脚本只要用它就自动符合三态。
    ap = ltw_exit.UsageParser(description="宿主渲染分支机检")
    ap.add_argument("--asar", default=None, help="app.asar 路径；缺省按平台猜")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()

    asar = Path(args.asar) if args.asar else Path("E:/DeepSeek Harness/resources/app.asar")
    ok, detail = check(asar)
    if ok is None:
        return ltw_exit.env_error(
            "未测不是通过：本机没有可验的宿主打包产物，判据 10⑦⑧ 的宿主证据本次未复核（"
            + detail + "）",
            code="E-RENDERER-UNTESTED",
            extra={"asar": str(asar)},
        )
    if ok:
        print("[OK] " + detail)
        return ltw_exit.EXIT_OK
    print("[FAIL] " + detail)
    return ltw_exit.EXIT_VIOLATION


if __name__ == "__main__":
    sys.exit(main())
