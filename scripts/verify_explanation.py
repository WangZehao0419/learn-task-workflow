#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_explanation.py - 讲义(materials/*.md)静态结构校验(stdlib-only、幂等只读、--selftest)。

用途:对私人家教工作流的讲义材料做静态校验。静态脚本只能证明结构与格式约束,
不能证明数学、事实、代码或教学体验正确(语义正确性须人工/领域复核,见 spec
「验收证据边界」)。

【Markdown 解析契约(冻结——修改须同步 spec 与 selftest)】
1. 概念单元边界:行首 `## 概念 <数字> · …` 开启一个单元,至下一个 `## ` 二级标题
   (下一个概念单元、「本节自测答案」或其他节)或文件尾;三级标题(###)不切断单元;
   「## 概念地图」无数字编号,不是概念单元。
2. 定稿/草稿标识:头部(第一个 `## ` 之前)的 `- 状态:<基值>(<括注>)` 行;
   基值 = 冒号后、第一个全/半角左括号前的文本(去 `*` 与空白);基值含「定稿」→
   定稿文件,其余(含「草稿」与无状态行)一律按草稿处理。
3. 标准答案框起止:概念单元内 `⑤ 标准答案(…):` 标记行之后,跳过空行,
   自首个 `>` 引用行起连续收集(中间空行后仍为 `>` 行则延续;出现非 `>` 非空行即止)。
   本版契约只认 Markdown 引用块为框体(代码任务框体形态未纳入);⑤标记行存在但
   框体缺失报 E-BOX-INCOMPLETE。
4. 排除范围(不参与正文 Unicode 检查):
   - ``` 代码围栏内全部行;
   - 行内 code span(`…`)与 $…$ / $$…$$ 公式内字符(剥除后按可见正文检查);
   - 标准答案框与非标准答案框的 `>` 引用块(前者按框体例单独查 E,后者整体豁免);
   - 「## 本节自测答案」区(至下一个 `## ` 或文件尾)——节末练习短答案与五要素之⑤
     合法并存,不属五要素之⑤;
   - 判分记账状态行(「状态(日期…):…」模式)——定稿下它已被 E-LEDGER-RESIDUE
     单独捕获、草稿下它是合法记录位,均不再重复报 Unicode。
5. 分层标签允许形式:含核心词「最小必需」「选学」「后期必用」之一(允许「本节」
   前缀省略与「——/(…)」括注变体);位置为概念单元正文,或规划区(第一个概念单元
   之前)中对应概念行——表格行 `| 概念 N |…|` 或列表行 `N. …`。
6. 五要素标记:①目标 / ②分步 / ③答案 / ④易错 / ⑤标准答案;⑤标记行匹配
   「⑤ 标准答案」,后缀括注(如「(可整体誊抄)」)可选。
   纯概念/记忆类可显式标注「⑤ 不适用(纯概念)」申请豁免:同时豁免②③⑤(三者同属
   「完整示例」),①④仍须具备;单元内引用块无「解:/答:」起笔即通过。若同时存在⑤标记
   报 E-FIFTH-CONFLICT;若仍有「解:/答:」起笔报 E-FIFTH-EXEMPT-MISUSE(豁免
   不得用于含可复现解答的单元)。

【规则表(6 类检查 / 9 个规则码)】
| 规则码           | 级 | 触发条件                                                            |
|------------------|----|---------------------------------------------------------------------|
| E-LEDGER-RESIDUE | E  | 定稿文件正文含判分记账状态行(「状态(…):已通过/关闭/讲授中」等);草稿不查 |
| E-REQ-MISSING    | E  | 概念单元五要素缺失(单元级;纯概念标「⑤ 不适用」时②③⑤ 豁免,①④仍查) |
| W-UNICODE-CHAR   | W  | 讲义可见正文出现 denylist 字符(→ ✔ ✓ ✅ √ ≤ ≥ ∪ ⇔ ⇒)               |
| E-BOX-FORMAT     | E  | 标准答案框内出现 ①–⑩ 分点编号 / → ⇒ 箭头 / ✓ ✔ ✅ √ 验算标记 / 讲解批注行 |
| E-BOX-INCOMPLETE | E  | 标准答案框缺「题目」、缺「解:/答:」解答主体,或 ⑤标记行后无框体       |
| W-NO-TIER        | W  | 概念单元(含规划区对应行)既无「最小必需」也无「选学/后期必用」分层标注 |
| W-STYLE-POINTER  | W  | 头部出现「标准答案体例(/数学排版约定(」整段规则块(疑似重复,应为指针行);头部含「体例约定(」指针行即合规 |
| E-FIFTH-CONFLICT | E  | 概念单元同时标注「⑤ 不适用(纯概念)」与「⑤ 标准答案」(自相矛盾)     |
| E-FIFTH-EXEMPT-MISUSE | E | 标注了「⑤ 不适用」但单元引用块内仍有「解:/答:」解答起笔(豁免被滥用) |

denylist 口径:任务点名字符(→ ✓ √ ≤ ≥ ∪ ⇔)及其同族验算/箭头标记(✔ ✅ ⇒);
乘号「×」、全角「＝」等修辞/排版字符未纳入,避免误伤中文修辞用法。
框内只查体例四类(分点/箭头/验算/批注);≤ ≥ ∪ 等数学符号在框内不查(框体豁免
正文 W,LaTeX 合规性由 formula-typesetting 机制负责,不在本脚本范围)。

用法:
    python verify_explanation.py <材料目录|单文件.md>   # 目录递归取 *.md(忽略 assets/ 与非 .md)
    python verify_explanation.py --selftest            # 内嵌样例自检(临时目录,不写盘被校验目录)

输出:按 文件路径→行号→规则码 稳定排序,逐条「[级] 码 路径:行号 提示」;末尾摘要行。
退出码:0 = 无 E(可有 W);1 = 有 E;2 = 用法/路径错误。
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

# ── denylist:已被 LaTeX 约定取代的 Unicode 写法(顺序即输出消息中的展示顺序)──
DENY_CHARS = "→✔✓✅√≤≥∪⇔⇒"
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
SOLVED_RE = re.compile(r"解\s*[:：]|答\s*[:：]")

CONCEPT_RE = re.compile(r"^##\s*概念\s*(\d+)")
H2_RE = re.compile(r"^##\s")
SELFTEST_HEAD_RE = re.compile(r"^##\s*本节自测答案")
STATUS_LINE_RE = re.compile(r"^-\s*状态\s*[:：]\s*(.*)$")
# 记账状态行:「状态(日期…):」+ 判分词确认;头部「- 状态:定稿(…)」是「状态:」在前,
# 不满足「状态(」紧邻结构,不会误命中
LEDGER_RE = re.compile(r"状态\s*[(（][^)）]*[)）]\s*[:：]")
LEDGER_WORD_RE = re.compile(r"通过|关闭|讲授中|已讲|封档")
FIFTH_RE = re.compile(r"⑤\s*标准答案")
FIFTH_EXEMPT_RE = re.compile(r"⑤\s*不适用|纯概念[·・]?\s*无\s*⑤")
# 豁免误用检测:只认引用块内的「解:/答:」起笔(标准答案框体例),
# 不匹配普通行首的问答式表述(如「答:这个术语指……」),避免误伤纯概念正文
SOLVED_LEAD_RE = re.compile(r"(?m)^\s*>\s*(?:解|答)\s*[:：]")
REQ_RES = (
    (re.compile(r"①\s*目标"), "① 目标"),
    (re.compile(r"②\s*分步"), "② 分步"),
    (re.compile(r"③\s*答案"), "③ 答案"),
    (re.compile(r"④\s*易错"), "④ 易错"),
)
# 与⑤同属「完整示例」,纯概念豁免时一并跳过;①目标、④易错仍须具备
EXAMPLE_ITEMS = ("② 分步", "③ 答案")
TIER_WORDS = ("最小必需", "选学", "后期必用")
# 概念单元正文必须用【…】标签承载分层;规划区行保留纯文本兼容(表格列/列表行)
TIER_TAG_RE = re.compile(r"【[^】]*(?:最小必需|选学|后期必用)[^】]*】")
PLAN_ROW_RE = re.compile(r"^\s*(\d+)\s*\.\s")
PLAN_TABLE_RE = re.compile(r"^\|\s*概念\s*(\d+)\s*\|")
POINTER_BLOCK_WORDS = ("标准答案体例（", "标准答案体例(",
                       "数学排版约定（", "数学排版约定(")
POINTER_OK_RE = re.compile(r"体例约定\s*[（(]")
BOX_ANNOT_RE = re.compile(r"^\s*>\s*[（(]?\s*(?:注意?|验证|说明|批注)\s*[:：]")


def compute_visible(lines):
    """逐行产出「可见正文」:剥代码围栏、行内 code span、$…$ 与 $$…$$ 公式。

    返回 (vis_lines, fence_flags)。围栏内 vis 为空串;跨行 $$ 块起点整行退出正文,
    直到含闭合 $$ 的行。公式/代码内的 denylist 字符(如 `\rightarrow` 的字面引用、
    code span 中引述的旧写法示例)因此天然豁免。
    """
    vis, fence = [], []
    in_fence = False
    in_math_block = False
    for ln in lines:
        if in_fence:
            vis.append("")
            fence.append(True)
            if ln.lstrip().startswith("```"):
                in_fence = False
            continue
        if ln.lstrip().startswith("```"):
            vis.append("")
            fence.append(True)
            in_fence = True
            continue
        fence.append(False)
        if in_math_block:
            vis.append("")
            if "$$" in ln:
                in_math_block = False
            continue
        out = []
        i, n = 0, len(ln)
        mode = None  # None=正文 / "code"=code span / "inline"=行内公式
        while i < n:
            ch = ln[i]
            if mode is None:
                if ch == "`":
                    mode = "code"
                    out.append(" ")
                elif ch == "$":
                    if i + 1 < n and ln[i + 1] == "$":
                        j = ln.find("$$", i + 2)
                        if j != -1:            # 单行内闭合的 $$…$$
                            out.append(" " * (j + 2 - i))
                            i = j + 2
                            continue
                        in_math_block = True   # 跨行块起点:整行退出正文
                        out = [" "] * n
                        break
                    mode = "inline"
                    out.append(" ")
                else:
                    out.append(ch)
            elif mode == "code":
                if ch == "`":
                    mode = None
                out.append(" ")
            else:  # 行内公式;未闭合则该行剩余均视为公式内
                if ch == "$":
                    mode = None
                out.append(" ")
            i += 1
        vis.append("".join(out))
    return vis, fence


def parse_doc(lines):
    """划分文档结构:头部/规划区边界、概念单元列表、自测区范围、定稿标识。"""
    n = len(lines)
    h2 = [i for i, ln in enumerate(lines) if H2_RE.match(ln)]
    header_end = h2[0] if h2 else n
    units = []
    for pos, i in enumerate(h2):
        m = CONCEPT_RE.match(lines[i])
        if m:
            end = h2[pos + 1] if pos + 1 < len(h2) else n
            units.append({"num": int(m.group(1)), "start": i, "end": end})
    plan_end = units[0]["start"] if units else n
    st = next((i for i, ln in enumerate(lines) if SELFTEST_HEAD_RE.match(ln)), None)
    if st is None:
        selftest_rng = None
    else:
        after = [i for i in h2 if i > st]
        selftest_rng = (st, after[0] if after else n)
    # 定稿判定只认头部第一条状态行的基值(冒号后、左括号前),括注里的
    # 「闸口通过后转定稿」等字样不得影响判定
    is_final = False
    for ln in lines[:header_end]:
        m = STATUS_LINE_RE.match(ln)
        if m:
            base = re.split(r"[（(]", m.group(1))[0].replace("*", "").strip()
            is_final = "定稿" in base
            break
    return {"header_end": header_end, "plan_end": plan_end, "units": units,
            "selftest": selftest_rng, "is_final": is_final}


def collect_boxes(lines, units):
    """定位每个⑤标记行对应的标准答案框。返回 [{fifth_line, rows, exists}]。"""
    boxes = []
    for u in units:
        for i in range(u["start"], u["end"]):
            if not FIFTH_RE.search(lines[i]):
                continue
            rows = set()
            j = i + 1
            while j < u["end"] and not lines[j].strip():   # 跳过标记行与框之间的空行
                j += 1
            started = False
            while j < u["end"]:
                s = lines[j].strip()
                if s.startswith(">"):
                    rows.add(j)
                    started = True
                    j += 1
                elif not s and started:
                    # 松散引用:空行后仍是 > 行则延续,否则框结束
                    k = j + 1
                    while k < u["end"] and not lines[k].strip():
                        k += 1
                    if k < u["end"] and lines[k].strip().startswith(">"):
                        j = k
                        continue
                    break
                else:
                    break
            boxes.append({"fifth_line": i, "rows": rows, "exists": started})
    return boxes


def check_text(text, rel):
    """校验单份讲义文本,返回 findings 列表(已按 文件→行号→规则码 排序)。"""
    lines = text.splitlines()
    doc = parse_doc(lines)
    vis, fence = compute_visible(lines)
    boxes = collect_boxes(lines, doc["units"])
    box_rows = set()
    for b in boxes:
        box_rows |= b["rows"]
    hs, he = doc["selftest"] if doc["selftest"] else (-1, -1)
    findings = []

    def add(level, code, line0, msg):
        findings.append((level, code, rel, line0 + 1, msg))

    # ── 规则 1:定稿判分记账残留(草稿不查)──
    ledger_rows = set()
    for i, ln in enumerate(lines):
        if LEDGER_RE.search(ln) and LEDGER_WORD_RE.search(ln):
            ledger_rows.add(i)
            if doc["is_final"]:
                add("E", "E-LEDGER-RESIDUE", i,
                    "定稿内判分记账残留(「状态(日期):已通过/关闭/讲授中」等状态行)——"
                    "历史证据移 exercises/ 与 progress.md,定稿须记账零残留")

    # ── 规则 2:概念单元五要素(单元级,不得全文件计数代替)──
    for u in doc["units"]:
        body = "\n".join(lines[u["start"]:u["end"]])
        has_fifth = bool(FIFTH_RE.search(body))
        exempt = bool(FIFTH_EXEMPT_RE.search(body))
        if has_fifth and exempt:
            add("E", "E-FIFTH-CONFLICT", u["start"],
                "概念 " + str(u["num"]) + " 同时标注「⑤ 不适用(纯概念)」与「⑤ 标准答案」——"
                "二者只能取一:确有可复现解答就给⑤框,纯概念就删⑤标记")
        elif exempt:
            if SOLVED_LEAD_RE.search(body):
                add("E", "E-FIFTH-EXEMPT-MISUSE", u["start"],
                    "概念 " + str(u["num"]) + " 标注「⑤ 不适用」但单元内仍有「解:/答:」解答起笔——"
                    "有可复现解答的概念须给完整⑤框,不得用豁免跳过")
            else:
                # 豁免②③⑤(同属完整示例),①目标与④易错仍须具备
                missing = [label for rx, label in REQ_RES
                           if label not in EXAMPLE_ITEMS and not rx.search(body)]
                if missing:
                    add("E", "E-REQ-MISSING", u["start"],
                        "概念 " + str(u["num"]) + " 纯概念豁免下仍缺:" + "、".join(missing) +
                        "——纯概念可省②③⑤,但①目标与④易错不得省")
        else:
            missing = [label for rx, label in REQ_RES if not rx.search(body)]
            if not has_fifth:
                missing.append("⑤ 标准答案")
            if missing:
                add("E", "E-REQ-MISSING", u["start"],
                    "概念 " + str(u["num"]) + " 五要素缺失:" + "、".join(missing) +
                    "——含解题过程的概念逐个补齐;纯概念无可复现产物可标「⑤ 不适用(纯概念)」"
                    "豁免②③⑤(①④仍须),不得以全文件计数代替")

    # ── 规则 3:正文 Unicode denylist(按排除范围过滤后逐行检查)──
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        if hs <= i < he:
            continue                      # 「本节自测答案」区:短答案合法并存
        if i in box_rows:
            continue                      # 标准答案框:按 E-BOX-FORMAT 单独查
        if ln.lstrip().startswith(">"):
            continue                      # 非标准答案框的引用块豁免
        if i in ledger_rows:
            continue                      # 记账行已单独捕获/属合法记录位,不重复报
        hit = [ch for ch in DENY_CHARS if ch in vis[i]]
        if hit:
            add("W", "W-UNICODE-CHAR", i,
                "正文违规字符:" + "、".join(hit) +
                "——已被 LaTeX 约定取代($\\rightarrow$、$\\checkmark$、$\\leq$ 等),"
                "正文须改用 LaTeX 或文字表述")

    # ── 规则 4:标准答案框体例 ──
    for b in boxes:
        if not b["exists"]:
            add("E", "E-BOX-INCOMPLETE", b["fifth_line"],
                "⑤标记行后无标准答案框(> 引用块)——框须紧邻标记行(只允许空行),"
                "教材原题等其他引用前移;须补「题目 + 从「解:」到结论」的完整可复现解答")
            continue
        box_vis = [vis[r] for r in sorted(b["rows"])]
        joined = "\n".join(box_vis)
        # 框内四类体例违规各自定位到首个违规框行,便于直接修
        circ = [r for r in sorted(b["rows"]) if any(c in vis[r] for c in CIRCLED)]
        if circ:
            add("E", "E-BOX-FORMAT", circ[0],
                "标准答案框内出现①②分点编号——须改为 ∵/∴/又 串联的连续解答(给分点分行保留)")
        arrow = [r for r in sorted(b["rows"]) if ("→" in vis[r] or "⇒" in vis[r])]
        if arrow:
            add("E", "E-BOX-FORMAT", arrow[0],
                "标准答案框内出现箭头(→/⇒)——须改用文字或 LaTeX($\\Rightarrow$)")
        check = [r for r in sorted(b["rows"]) if any(c in vis[r] for c in "✓✔✅√")]
        if check:
            add("E", "E-BOX-FORMAT", check[0],
                "标准答案框内出现验算标记(✓/√)——验算归「②分步」,框内只留成品解答")
        for r in sorted(b["rows"]):
            if BOX_ANNOT_RE.match(lines[r]):
                add("E", "E-BOX-FORMAT", r,
                    "标准答案框内出现讲解性批注行——批注归「②分步」,框内只留成品解答")
        if "题目" not in joined:
            add("E", "E-BOX-INCOMPLETE", b["fifth_line"],
                "标准答案框缺「题目」行——框须含题目与解答主体")
        if not SOLVED_RE.search(joined):
            add("E", "E-BOX-INCOMPLETE", b["fifth_line"],
                "标准答案框缺「解:/答:」解答主体起笔")

    # ── 规则 5:分层标注缺失(概念单元正文 + 规划区对应行)──
    plan_hits = {}
    for i in range(doc["plan_end"]):
        m = PLAN_TABLE_RE.match(lines[i])
        if m:
            plan_hits.setdefault(int(m.group(1)), []).append(i)
            continue
        m = PLAN_ROW_RE.match(lines[i])
        if m:
            plan_hits.setdefault(int(m.group(1)), []).append(i)
    for u in doc["units"]:
        body = "\n".join(lines[u["start"]:u["end"]])
        body_tagged = bool(TIER_TAG_RE.search(body))
        plan_tagged = any(any(w in lines[i] for w in TIER_WORDS)
                          for i in plan_hits.get(u["num"], []))
        if not (body_tagged or plan_tagged):
            add("W", "W-NO-TIER", u["start"],
                "概念 " + str(u["num"]) + " 缺分层标注——正文用【本节最小必需】或"
                "【选学·后期必用(何时用/依赖哪节)】;规划区对应行可写纯文本")

    # ── 规则 6:头部指针行缺失 / 疑似重复规则块 ──
    has_pointer = any(POINTER_OK_RE.search(lines[i]) for i in range(doc["header_end"]))
    for i in range(doc["header_end"]):
        for w in POINTER_BLOCK_WORDS:
            if w in lines[i]:
                add("W", "W-STYLE-POINTER", i,
                    "头部出现整段「" + (w.rstrip("(（")) + "」规则块——疑似重复规则"
                    "(指针行" + ("已同时存在,仍应删除规则块正文" if has_pointer else "缺失") +
                    ");应压为一行「体例约定(LaTeX 排版/标准答案框):统一见 progress.md『质量保障机制』」")
                break   # 同一行命中多个词只报一条,避免噪音

    findings.sort(key=lambda f: (f[2], f[3], f[1], f[4]))
    return findings


def report(findings):
    """打印逐条结果与摘要行,返回退出码(0=无 E,1=有 E)。"""
    for level, code, rel, lineno, msg in findings:
        print("[{}] {} {}:{} {}".format(level, code, rel, lineno, msg))
    if findings:
        e_count = sum(1 for f in findings if f[0] == "E")
        w_count = len(findings) - e_count
        print("共 {} 项:E {} 项,W {} 项".format(len(findings), e_count, w_count))
        return 1 if e_count else 0
    print("通过:无违规项(结构通过;内容准确性、来源可信度与教学体验未校验,须人工/领域复核)")
    return 0


def main(argv=None):
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        prog="verify_explanation.py",
        description="讲义静态结构校验(只读、幂等;规则明细见脚本 docstring 契约)")
    ap.add_argument("path", nargs="?", default=None,
                    help="材料目录(递归取 *.md,忽略 assets/ 与非 .md)或单个 .md 文件")
    ap.add_argument("--selftest", action="store_true",
                    help="运行内嵌样例自检(临时目录,不写盘被校验目录)")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.path:
        ap.print_usage()
        return 2
    p = Path(args.path)
    if p.is_dir():
        files = sorted(f for f in p.rglob("*.md")
                       if f.is_file() and "assets" not in f.parts)
        if not files:
            print("[learn-task-workflow] 目录下未找到 .md 材料:" + str(p),
                  file=sys.stderr)
            return 2
    elif p.is_file():
        files = [p]
    else:
        print("[learn-task-workflow] 路径不存在或不可访问:" + str(p), file=sys.stderr)
        return 2
    findings = []
    for f in files:
        rel = f.relative_to(p).as_posix() if p.is_dir() else f.name
        try:
            text = f.read_text(encoding="utf-8-sig")
        except OSError as exc:
            # 单个文件不可读不阻断其余文件,降级为 stderr 提示
            print("[learn-task-workflow] 跳过不可读文件 " + str(f) + ":" + str(exc),
                  file=sys.stderr)
            continue
        findings.extend(check_text(text, rel))
    return report(findings)


# ═══════════════════ selftest 内嵌样例(运行于临时目录,不写盘被校验目录) ═══════════════════

# 合规定稿:指针行、规划分层、五要素齐(目标态⑤)、干净框、围栏/code/公式/引用块/自测区豁免
FIX_OK = """# 第 1 节 · 示例
- 状态:定稿(节闸口通过)
- 体例约定(LaTeX 排版/标准答案框):统一见 progress.md『质量保障机制』
- 节内概念单元规划(1):
  1. 示例概念 【本节最小必需】

## 概念 1 · 示例概念
正文含公式 $x \\rightarrow 2$ 与代码 `→ √ ≤`,均为合法载体;公式 $$a^2+b^2=c^2$$ 亦合规。
> 这是普通引用块:→ ✓ √ 均豁免。

- ① 目标:解方程。
- ② 分步:先算判别式。
- ③ 答案:$x=2$。
- ④ 易错:负号。
- ⑤ 标准答案(可整体誊抄):

> 题目:解方程 $x^2-4=0$。
> 解:$x^2=4$,∴ $x=\\pm 2$。

## 本节自测答案
1. $x=2$,答案行含 → 与 √ 属合法区
"""

# 定稿 + 概念末记账状态行 → E-LEDGER-RESIDUE
FIX_LEDGER = """# 第 1 节 · 示例
- 状态:定稿(闸口通过)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
- ① 目标:分解。
- ② 分步:套公式。
- ③ 答案:$x=1$。
- ④ 易错:符号。
- ⑤ 标准答案:

> 题目:分解 $x^2-1$。
> 解:$x^2-1=(x+1)(x-1)$。

- **状态(2026-10-10):已通过**——全对,概念 1 关闭。
"""

# 同文改草稿 → 不查记账(概念末状态行是草稿合法记录位)
FIX_LEDGER_DRAFT = FIX_LEDGER.replace("- 状态:定稿(闸口通过)", "- 状态:草稿(讲授中)")

# 两个概念单元,概念 1 缺④、概念 2 齐 → 单元级计数,只报概念 1
FIX_UNITS = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(2):
  1. 甲 【本节最小必需】
  2. 乙 【本节最小必需】

## 概念 1 · 甲
- ① 目标:一。
- ② 分步:二。
- ③ 答案:三。
- ⑤ 标准答案:

> 题目:一题。
> 解:一步。

## 概念 2 · 乙
- ① 目标:一。
- ② 分步:二。
- ③ 答案:三。
- ④ 易错:四。
- ⑤ 标准答案(可整体誊抄):

> 题目:一题。
> 解:一步。
"""

# 概念缺⑤标记(五要素其余齐) → E-REQ-MISSING 且消息指向「⑤ 标准答案」
FIX_NO_FIFTH = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
- ① 目标:一。
- ② 分步:二。
- ③ 答案:三。
- ④ 易错:四。
"""

# 正文裸违规字符 → W-UNICODE-CHAR(一行一条,消息列出命中字符)
FIX_UNICODE = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
正文裸箭头 → 与对勾 ✓ 属违规。
- ① 目标:一。
- ② 分步:二。
- ③ 答案:三。
- ④ 易错:四。
- ⑤ 标准答案:

> 题目:一题。
> 解:一步。
"""

# 排除范围不误报:围栏 / code span / 公式 / 引用块 / 自测区
FIX_UNICODE_EXEMPT = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
围栏内合法:
```
→ ✓ √ ≤ ≥ ∪ ⇔
```
行内 code `→ ✓ √` 与公式 $a \\leq b$、`√` 字面均豁免。
> 普通引用块豁免:→ ✓ √。

- ① 目标:一。
- ② 分步:二。
- ③ 答案:三。
- ④ 易错:四。
- ⑤ 标准答案:

> 题目:一题。
> 解:一步。

## 本节自测答案
1. → √ ≤ 答案行合法
"""

# 框内四类体例违规:分点 / 箭头 / 验算标记 / 批注行(各计一条 E-BOX-FORMAT)
FIX_BOX_BAD = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
- ① 目标:一。
- ② 分步:二。
- ③ 答案:三。
- ④ 易错:四。
- ⑤ 标准答案:

> 题目:解方程。
> 解:第一步 → 第二步;
> ① 设 $x$;
> 验算:$x=2$ ✓;
> (注:这里容易错。)
"""

# 框缺「题目」→ E-BOX-INCOMPLETE
FIX_BOX_NOQ = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
- ① 目标:一。
- ② 分步:二。
- ③ 答案:三。
- ④ 易错:四。
- ⑤ 标准答案:

> 解:$x=2$。
"""

# ⑤标记行后无框体 → E-BOX-INCOMPLETE
FIX_BOX_MISSING = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
- ① 目标:一。
- ② 分步:二。
- ③ 答案:三。
- ④ 易错:四。
- ⑤ 标准答案:

这一行不是引用块,框体缺失。
"""

# 规划行与概念内均无分层标注 → W-NO-TIER(纯 W,退出码 0)
FIX_TIER = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(1):
  1. 甲

## 概念 1 · 甲
- ① 目标:一。
- ② 分步:二。
- ③ 答案:三。
- ④ 易错:四。
- ⑤ 标准答案:

> 题目:一题。
> 解:一步。
"""

# 正文出现「选学」二字但无【】标签 → W-NO-TIER(关键词不算分层标注)
FIX_TIER_LOOSE = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(1):
  1. 甲

## 概念 1 · 甲
本节选学内容后面再讲。
- ① 目标:一。
- ② 分步:二。
- ③ 答案:三。
- ④ 易错:四。
- ⑤ 标准答案:

> 题目:一题。
> 解:一步。
"""

# 头部两个旧规则块 → 2 条 W-STYLE-POINTER
FIX_POINTER = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 数学排版约定(2026-10-17 学员要求):公式一律用 LaTeX
- 标准答案体例(2026-10-17 学员反馈后确立):只放连续解答
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
- ① 目标:一。
- ② 分步:二。
- ③ 答案:三。
- ④ 易错:四。
- ⑤ 标准答案:

> 题目:一题。
> 解:一步。
"""

# 「## 概念地图」不是概念单元;表格行承载分层标注 → 单元级零误报
FIX_MAP = """# 第 1 节 · 示例
- 状态:草稿(进行中)

## 概念地图
| 单元 | 内容 | 分层 |
|---|---|---|
| 概念 1 | 甲 | 本节最小必需 |

## 概念 1 · 甲
- ① 目标:一。
- ② 分步:二。
- ③ 答案:三。
- ④ 易错:四。
- ⑤ 标准答案:

> 题目:一题。
> 解:一步。
"""

# 记账行内的违规字符不重复报(只报 E-LEDGER-RESIDUE)
FIX_LEDGER_MIX = """# 第 1 节 · 示例
- 状态:定稿(通过)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
- ① 目标:一。
- ② 分步:二。
- ③ 答案:三。
- ④ 易错:四。
- ⑤ 标准答案:

> 题目:一题。
> 解:一步。
- **状态(2026-10-10):已通过**——全对 → 关闭。
"""

# 纯概念显式豁免:标「⑤ 不适用(纯概念)」,②③⑤ 一并豁免,①④ 齐 → 零 E
FIX_FIFTH_EXEMPT = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
- ① 目标:认识 $\\pm$ 记号的读法。
- ④ 易错:把 $\\pm$ 读成「两个符号」而非「两次取值」。
- ⑤ 不适用（纯概念）:本节只讲记号语义,无可复现产物。
"""

# 豁免被滥用:标了「⑤ 不适用」却仍有「> 解:」起笔 → E-FIFTH-EXEMPT-MISUSE
FIX_FIFTH_EXEMPT_BAD = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
- ① 目标:解方程。
- ④ 易错:符号。
- ⑤ 不适用（纯概念）:概念讲解。

> 解:$x=2$。
"""

# ⑤标记与豁免并存 → E-FIFTH-CONFLICT
FIX_FIFTH_CONFLICT = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
- ① 目标:一。
- ④ 易错:四。
- ⑤ 标准答案:
- ⑤ 不适用（纯概念）:补充说明。

> 题目:一题。
> 解:一步。
"""

# 纯概念豁免 + 正文行首「答:」属普通问答表述,不得误判为解答起笔 → 零 E
FIX_FIFTH_EXEMPT_ANS = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
- ① 目标:认识术语。
- ④ 易错:混淆近义词。
- ⑤ 不适用（纯概念）:只讲术语语义。
答:这个术语指一组可复现的操作。
"""

# 头部指针行改用半角括号 → 同样合规(FIX_OK 的全角版已覆盖正向)
FIX_OK_HALF = FIX_OK.replace("体例约定（LaTeX 排版/标准答案框）",
                             "体例约定(LaTeX 排版/标准答案框)")

# ⑤ 与引用块之间插入普通文字 → 框不成立,报 E-BOX-INCOMPLETE
FIX_BOX_GAP = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
- ① 目标:一。
- ② 分步:二。
- ③ 答案:三。
- ④ 易错:四。
- ⑤ 标准答案:

教材原题如下(非答案框):

> 题目:一题。
> 解:一步。
"""


def selftest():
    ok = True

    def chk(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print("[{}] {}".format("OK" if cond else "FAIL", name))

    def codes(findings, code):
        return [f for f in findings if f[1] == code]

    # ① 合规定稿:全规则通过(指针行/规划分层/五要素/干净框/各豁免区)
    r = check_text(FIX_OK, "ok.md")
    chk("合规定稿零违规", r == [])

    # ② 定稿记账残留:恰 1 条 E-LEDGER-RESIDUE,行号指向记账行
    r = check_text(FIX_LEDGER, "ledger.md")
    ledger_line = FIX_LEDGER.splitlines().index(
        "- **状态(2026-10-10):已通过**——全对,概念 1 关闭。") + 1
    chk("定稿记账残留恰 1 条且行号正确",
        len(codes(r, "E-LEDGER-RESIDUE")) == 1 and codes(r, "E-LEDGER-RESIDUE")[0][3] == ledger_line)

    # ③ 草稿不查记账
    r = check_text(FIX_LEDGER_DRAFT, "draft.md")
    chk("草稿不报记账残留", len(codes(r, "E-LEDGER-RESIDUE")) == 0)

    # ④ 概念单元级计数:两概念其一缺④只报该单元
    r = check_text(FIX_UNITS, "units.md")
    req = codes(r, "E-REQ-MISSING")
    chk("单元级五要素:恰 1 条且只指向概念 1",
        len(req) == 1 and "概念 1" in req[0][4] and "概念 2" not in req[0][4])

    # ⑤ ⑤两种目标态形式都识别(标准答案 / 标准答案(可整体誊抄))
    chk("⑤「标准答案」两种目标态均识别(无 E-REQ)",
        len(codes(check_text(FIX_UNITS, "units.md"), "E-REQ-MISSING")) == 1
        and len(codes(check_text(FIX_OK, "ok.md"), "E-REQ-MISSING")) == 0)

    # ⑥ 概念缺⑤标记 → E-REQ-MISSING 且消息指向「⑤ 标准答案」
    r = check_text(FIX_NO_FIFTH, "nofifth.md")
    req = codes(r, "E-REQ-MISSING")
    chk("缺⑤报 E-REQ-MISSING 且消息含「⑤ 标准答案」",
        len(req) == 1 and "⑤ 标准答案" in req[0][4])

    # ⑦ 正文裸违规字符 → W-UNICODE-CHAR,消息含命中字符
    r = check_text(FIX_UNICODE, "uni.md")
    uni = codes(r, "W-UNICODE-CHAR")
    chk("正文违规字符报 W 且行号正确",
        len(uni) == 1 and "→" in uni[0][4] and "✓" in uni[0][4]
        and uni[0][3] == FIX_UNICODE.splitlines().index("正文裸箭头 → 与对勾 ✓ 属违规。") + 1)

    # ⑧ 排除范围不误报:围栏 / code span / 公式 / 引用块 / 自测区
    chk("围栏/code/公式/引用块/自测区零误报",
        len(codes(check_text(FIX_UNICODE_EXEMPT, "exempt.md"), "W-UNICODE-CHAR")) == 0)

    # ⑨ 框内四类体例违规各计一条 E-BOX-FORMAT
    r = check_text(FIX_BOX_BAD, "boxbad.md")
    chk("框内分点/箭头/验算/批注各 1 条 E-BOX-FORMAT",
        len(codes(r, "E-BOX-FORMAT")) == 4)

    # ⑩ 框缺「题目」→ E-BOX-INCOMPLETE
    chk("框缺题目报 E-BOX-INCOMPLETE",
        len(codes(check_text(FIX_BOX_NOQ, "noq.md"), "E-BOX-INCOMPLETE")) == 1)

    # ⑪ ⑤标记行后无框体 → E-BOX-INCOMPLETE
    chk("⑤行后无框体报 E-BOX-INCOMPLETE",
        len(codes(check_text(FIX_BOX_MISSING, "nob.md"), "E-BOX-INCOMPLETE")) == 1)

    # ⑫ 分层标注缺失:恰 1 条 W-NO-TIER 且无 E(纯 W 退出码 0)
    r = check_text(FIX_TIER, "tier.md")
    e_count = sum(1 for f in r if f[0] == "E")
    chk("分层缺失报 W-NO-TIER 且无 E", len(codes(r, "W-NO-TIER")) == 1 and e_count == 0)

    # 分层收紧:正文出现「选学」二字但无【】标签 → 仍报 W-NO-TIER
    r = check_text(FIX_TIER_LOOSE, "tierloose.md")
    chk("正文关键词不算分层标注", len(codes(r, "W-NO-TIER")) == 1)

    # ⑬ 头部两个旧规则块 → 2 条 W-STYLE-POINTER;指针行形态不报(FIX_OK 已覆盖)
    chk("头部规则块报 2 条 W-STYLE-POINTER",
        len(codes(check_text(FIX_POINTER, "ptr.md"), "W-STYLE-POINTER")) == 2)

    # ⑭ 「## 概念地图」不生成单元;表格行分层标注生效
    r = check_text(FIX_MAP, "map.md")
    chk("概念地图不误判 + 表格行分层生效",
        len(codes(r, "E-REQ-MISSING")) == 0 and len(codes(r, "W-NO-TIER")) == 0)

    # ⑮ 记账行内违规字符不重复报:只 E-LEDGER、零 W-UNICODE
    r = check_text(FIX_LEDGER_MIX, "mix.md")
    chk("记账行不重复报 Unicode",
        len(codes(r, "E-LEDGER-RESIDUE")) == 1
        and len(codes(r, "W-UNICODE-CHAR")) == 0)

    # ⑯ 输出按 文件→行号→规则码 稳定排序
    mixed = check_text(FIX_UNICODE, "a.md") + check_text(FIX_BOX_BAD, "a.md")
    keys = [(f[2], f[3]) for f in mixed]
    chk("输出按 文件→行号 稳定排序", keys == sorted(keys))

    # ⑰–⑲ 纯概念⑤豁免:合法豁免零 E / 滥用报错 / 与⑤并存报冲突
    r = check_text(FIX_FIFTH_EXEMPT, "exempt5.md")
    chk("纯概念豁免⑤零 E", sum(1 for f in r if f[0] == "E") == 0)
    r = check_text(FIX_FIFTH_EXEMPT_BAD, "exemptbad.md")
    chk("豁免滥用报 E-FIFTH-EXEMPT-MISUSE",
        len(codes(r, "E-FIFTH-EXEMPT-MISUSE")) == 1)
    r = check_text(FIX_FIFTH_CONFLICT, "conflict.md")
    chk("⑤与豁免并存报 E-FIFTH-CONFLICT",
        len(codes(r, "E-FIFTH-CONFLICT")) == 1)
    r = check_text(FIX_FIFTH_EXEMPT_ANS, "exemptans.md")
    chk("正文行首「答:」不误判为解答起笔",
        sum(1 for f in r if f[0] == "E") == 0)
    # 头部指针行:半角括号同样合规
    chk("半角括号指针行不报 W-STYLE-POINTER",
        len(codes(check_text(FIX_OK_HALF, "okhalf.md"), "W-STYLE-POINTER")) == 0)
    # ⑤ 与框之间插普通文字 → 框不成立
    chk("⑤与引用块之间插内容报 E-BOX-INCOMPLETE",
        len(codes(check_text(FIX_BOX_GAP, "boxgap.md"), "E-BOX-INCOMPLETE")) == 1)

    # ㉑–㉔ 退出码:0=无 E / 1=有 E / 2=用法或路径错误
    with tempfile.TemporaryDirectory() as td:
        d0 = Path(td) / "ok"
        d0.mkdir()
        (d0 / "a.md").write_text(FIX_OK, encoding="utf-8")
        d1 = Path(td) / "bad"
        d1.mkdir()
        (d1 / "a.md").write_text(FIX_LEDGER, encoding="utf-8")
        chk("退出码 0(无 E)", main([str(d0)]) == 0)
        chk("退出码 1(有 E)", main([str(d1)]) == 1)
        chk("退出码 2(路径不存在)", main([str(Path(td) / "不存在")]) == 2)
        chk("退出码 2(缺参数)", main([]) == 2)

    print(("OK " if ok else "FAIL ") + "verify_explanation --selftest")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
