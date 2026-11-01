#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ltw_typography - 讲义读者版/排版检查模块 + 文件结构可读性闸口（独立 CLI）。

两种用法：
1. 被 verify_explanation.py --reader 调用（run_checks，讲义读者版 W-READER-*，不阻断）；
2. 独立闸口：`python -B scripts/ltw_typography.py <学员可读.md>... [--selftest]`
   —— 按 ops/layout.md 对任意学员可读文件跑 E/W 级结构检查（E-LAYOUT-*/W-LAYOUT-*），
   任一 E 级违规退出码 1。规则数值来自 contracts/rules.json 的 constants.layout。

纯函数：不写盘、不联网、不读环境变量。语义上的"是否更易读"仍归人工读者验证。
"""
import json
import re
from pathlib import Path

H2_RE = re.compile(r"^##\s")
MD_IMAGE_ALT_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
GENERIC_ALT = {"图", "图片", "示意图", "图像", "figure", "image", "diagram"}
THIRD_EXEMPT_RE = re.compile(
    r"^\s*(?:[-*+]\s+|\d+[.、)]\s*)?(?:\*\*)?\s*③\s*不适用|纯概念[·・]?\s*无\s*③", re.M)
NUMERIC_CELL_RE = re.compile(
    r"^[−\-+]?\d[\d,.]*(?:\s*(?:%|‰|°|元|万元|亿元|个|人|次|分|秒|分钟|小时|天|年|月|日|"
    r"kg|g|mg|m|cm|mm|km|L|mL|mol))?$")
DEFAULT_HEADING_BODY_EXEMPT = (
    "本节速览", "概念地图", "回看索引", "本节自测", "自测", "自测题",
    "检验", "检验题", "检验问题", "本节检验", "答案", "参考答案",
    "扩展（选读）", "扩展(选读)", "待解决问题", "本章速览", "本章回看",
    "术语表", "词汇表", "速查表", "清单", "来源", "参考资料",
)
DEFAULT_GENERIC_LINK_TEXTS = (
    "点击这里", "这里", "链接", "点我", "阅读更多",
    "click here", "here", "link", "read more",
)
def _is_caption(text, prefixes):
    if not text:
        return False
    stripped = re.sub(r"^(?:>\s*)?(?:[-*+]\s+)?(?:\*\*)?", "", text.strip())
    return (any(stripped.startswith(p) for p in prefixes)
            or bool(re.match(r"图\s*\d+\s*[：:]", stripped)))
LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")


def table_cells(row):
    """拆 Markdown 表格行；返回去首尾空格的单元格。"""
    return [c.strip() for c in row.strip().strip("|").split("|")]


def is_table_sep(row):
    """表格分隔行：每个单元格形如 --- / :--- / ---: / :---:。"""
    cells = table_cells(row)
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c or "") for c in cells)


def table_blocks(lines, fence):
    """收集连续表格行（围栏代码块内不算），返回每块的行号列表。"""
    blocks, cur = [], []
    for i, ln in enumerate(lines):
        if not fence[i] and ln.strip().startswith("|"):
            cur.append(i)
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    return blocks


def _svg_problems(path, cfg):
    """读者版 SVG 技术项：根元素 viewBox/role、title/desc、字号/线宽、无脚本/外链。"""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ["SVG 读取失败"]
    problems = []
    root = re.search(r"<svg\b[^>]*>", text, re.I)
    if not root or "viewBox=" not in root.group(0):
        problems.append("根元素缺 viewBox")
    if not root or not re.search(r"role\s*=\s*[\"']img[\"']", root.group(0)):
        problems.append("根元素缺 role=\"img\"")
    for tag, label in (("<title", "title"), ("<desc", "desc")):
        if tag not in text:
            problems.append("缺 <{}>".format(label))
    if "<script" in text.lower():
        problems.append("含 script")
    if re.search(r"(?:href|xlink:href)\s*=\s*[\"']https?://", text, re.I):
        problems.append("含外部引用")
    for raw in re.findall(r"font-size\s*=\s*[\"']([0-9.]+)", text):
        if float(raw) < cfg["svg_font_min"]:
            problems.append("字号 {} < {}".format(raw, cfg["svg_font_min"]))
    for raw in re.findall(r"stroke-width\s*=\s*[\"']([0-9.]+)", text):
        if float(raw) < cfg["svg_line_min"]:
            problems.append("线宽 {} < {}".format(raw, cfg["svg_line_min"]))
    return problems


def _first_body_line(lines, i, fence):
    j = i + 1
    while j < len(lines) and (fence[j] or not lines[j].strip()):
        j += 1
    return j


def check_heading_body(lines, fence, add, cfg):
    """H2 标题后先有正文或带标签的首行；结构区/清单类标题可直接跟表/列表。"""
    exempt = cfg.get("heading_body_exempt") or DEFAULT_HEADING_BODY_EXEMPT
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if not m:
            continue
        # 只查 H2：H1 是文档标题（元信息列表合法）；H3+ 子标题下直接跟列表是常见版式
        if len(m.group(1)) != 2:
            continue
        text = m.group(2).strip()
        if any(text.startswith(e) or text.endswith(e) or e in text for e in exempt):
            continue
        j = _first_body_line(lines, i, fence)
        if j >= len(lines):
            continue
        nxt = lines[j].lstrip()
        if not nxt:
            continue
        if re.match(r"^(?:[-*+]\s+|\d+[.、)]\s*)", nxt):
            # 概念单元的合法开篇：一句话结论/定义/① 题目/概念引入 等「标签：内容」
            opening = r"^(?:[-*+]\s+|\d+[.、)]\s*)?(?:\*\*)?一句话结论\s*[：:]"
            if re.match(r"^##\s*概念\s*\d+", ln):
                opening = (r"^(?:[-*+]\s+|\d+[.、)]\s*)(?:\*\*)?"
                           r"[^：:\n]{1,10}\s*[：:]")
            if re.match(opening, nxt):
                continue
            add("W", "W-READER-HEADING-BODY", i,
                "标题后直接跟列表——标题下先写一段正文（或把一句话结论/定义放首行），再列条目")
        elif nxt.startswith("|"):
            add("W", "W-READER-HEADING-BODY", i,
                "标题后直接跟表格——标题下先写一段正文，再放表")
        elif nxt.startswith("!["):
            add("W", "W-READER-HEADING-BODY", i,
                "标题后直接跟图片——标题下先写一段正文，再放图")
        elif re.match(r"^#{1,6}\s+", nxt):
            add("W", "W-READER-HEADING-BODY", i,
                "标题后直接跟子标题——标题下先写一段正文，再分子标题")


def check_caption(lines, fence, add, cfg):
    """图片后应有图注（图注：… 或 图 N：…），表格内图片豁免。"""
    prefixes = tuple(cfg.get("figure_caption_prefixes")
                     or ("图注：", "图注:", "图 "))
    for i, ln in enumerate(lines):
        if fence[i] or ln.lstrip().startswith("|"):
            continue
        matches = list(MD_IMAGE_ALT_RE.finditer(ln))
        if not matches:
            continue
        for m in matches:
            tail = ln[m.end():]
            if re.search(r"图注\s*[：:]", tail):
                continue
            j = _first_body_line(lines, i, fence)
            nxt = lines[j].strip() if j < len(lines) else ""
            if not _is_caption(nxt, prefixes):
                add("W", "W-READER-CAPTION", i,
                    "图片后缺图注——图注在图下写结论（图注：… 或 图 N：…）")


def check_linktext(lines, fence, add, cfg):
    """链接文字应写清目的，不用空文字/泛称。"""
    generic = {t.lower() for t in (cfg.get("generic_link_texts") or DEFAULT_GENERIC_LINK_TEXTS)}
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        for m in LINK_RE.finditer(ln):
            text = m.group(1).strip()
            if not text or text.lower() in generic:
                add("W", "W-READER-LINKTEXT", i,
                    "链接文字为空或泛称——写清目的（如「二分法步骤表」），不写「点击这里/这里/链接」")


def check_table_align(lines, fence, add, cfg):
    """数值列（≥N 个纯数值单元格）应右对齐；混合列不报。"""
    min_n = int(cfg.get("table_align_min_numeric", 2))
    for block in table_blocks(lines, fence):
        if len(block) < min_n + 1:
            continue
        sep_idx = None
        for idx in block[1:3]:
            if is_table_sep(lines[idx]):
                sep_idx = idx
                break
        if sep_idx is None:
            continue
        header = table_cells(lines[block[0]])
        sep = table_cells(lines[sep_idx])
        data_rows = [r for r in block if r > sep_idx]
        if not data_rows:
            continue
        for col in range(min(len(header), len(sep))):
            cells = []
            for r in data_rows:
                cs = table_cells(lines[r])
                if col < len(cs) and cs[col]:
                    cells.append(cs[col])
            if len(cells) < min_n:
                continue
            raw_sep = sep[col].strip()
            right_aligned = raw_sep.startswith("-") and raw_sep.endswith(":")
            if all(NUMERIC_CELL_RE.match(c) for c in cells) and not right_aligned:
                add("W", "W-READER-TABLE-ALIGN", block[0],
                    "数值列未右对齐——表头写单位，分隔行用 ---: 让数字右对齐")


def run_checks(lines, doc, vis, fence, base_dir, box_rows, add, cfg):
    """读者版/排版检查（W 级，只在 --reader 显式启用时执行，不拦截）。"""
    # 1. 标题层级不跳级
    prev = 0
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        m = re.match(r"^(#{1,6})\s+", ln)
        if not m:
            continue
        level = len(m.group(1))
        if prev and level > prev + 1:
            add("W", "W-READER-HEADING", i,
                "标题层级跳级 H{}→H{}——用 H2 分单元、H3 分小节,不跳级".format(prev, level))
        prev = level

    # 2. 表格:表头 + 2–4 列(手机可读)
    for block in table_blocks(lines, fence):
        if len(block) < 2 or not is_table_sep(lines[block[1]]):
            add("W", "W-READER-TABLE", block[0],
                "表格缺表头分隔行——补齐「| 列名 | … |」与「|---|---|」")
            continue
        header = table_cells(lines[block[0]])
        if len(header) < cfg["table_cols_min"] or len(header) > cfg["table_cols_max"]:
            add("W", "W-READER-TABLE", block[0],
                "表格列数 {}——手机端保持 {}–{} 列,宽表拆成列表或两张表".format(
                    len(header), cfg["table_cols_min"], cfg["table_cols_max"]))
        if any(not c for c in header):
            add("W", "W-READER-TABLE", block[0],
                "表头存在空列名——每列写清名称,单位放表头")

    # 3. 图片 alt 与 SVG 技术项
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        for m in MD_IMAGE_ALT_RE.finditer(vis[i]):
            alt, target = m.group(1).strip(), m.group(2).strip()
            if not alt or alt.lower() in GENERIC_ALT:
                add("W", "W-READER-ALT", i,
                    "图片 alt 为空或过于笼统——写「图型:一句话结论」,不写「示意图/图片」")
            if base_dir is None or re.match(r"(?:https?:|data:|mailto:)", target, re.I):
                continue
            path = Path(target) if Path(target).is_absolute() else Path(base_dir) / target
            if path.suffix.lower() == ".svg" and path.exists():
                probs = _svg_problems(path, cfg)
                if "SVG 读取失败" in probs:
                    add("E", "E-IMG-READ", i, "SVG 读取失败或编码不是 UTF-8")
                elif probs:
                    add("W", "W-READER-SVG", i,
                        "SVG 读者版技术项不合格:" + "、".join(probs) +
                        "——补 viewBox/role/title/desc,字号 ≥14、线宽 ≥1.5,去脚本/外链")

    # 4. 本节速览:位置 + 3 列、1–3 行数据
    if "## 本节速览" in lines:
        start = lines.index("## 本节速览")
        first_unit = doc["units"][0]["start"] if doc["units"] else len(lines)
        if start > first_unit:
            add("W", "W-READER-OVERVIEW", start,
                "本节速览应在第一个 ## 概念 之前——读者先看路线,再看单元")
        block = []
        for j in range(start + 1, len(lines)):
            if H2_RE.match(lines[j]):
                break
            if fence[j]:
                continue
            if lines[j].strip().startswith("|"):
                block.append(j)
            elif block:
                break
        if len(block) < 2:
            add("W", "W-READER-OVERVIEW", start,
                "本节速览表缺失或不完整——用 {} 列「要解决的问题 | 一句话结论 | 用在哪」".format(
                    cfg["overview_cols"]))
        else:
            cols = len(table_cells(lines[block[0]]))
            if cols != cfg["overview_cols"]:
                add("W", "W-READER-OVERVIEW", block[0],
                    "本节速览应为 {} 列,实际 {}".format(cfg["overview_cols"], cols))
            data_rows = len(block) - 2
            if not cfg["overview_rows_min"] <= data_rows <= cfg["overview_rows_max"]:
                add("W", "W-READER-OVERVIEW", block[0],
                    "本节速览数据行 {}——只留 {}–{} 行,对应关键能力项".format(
                        data_rows, cfg["overview_rows_min"], cfg["overview_rows_max"]))
    else:
        add("W", "W-READER-OVERVIEW", 0,
            "读者版缺 ## 本节速览——用 {} 列「要解决的问题 | 一句话结论 | 用在哪」".format(
                cfg["overview_cols"]))

    # 5. 回看索引三行 + 位置(答案区之后,停车位/扩展区之前)
    if "## 回看索引" in lines:
        start = lines.index("## 回看索引")
        end = next((j for j in range(start + 1, len(lines)) if H2_RE.match(lines[j])),
                   len(lines))
        tail = "\n".join(lines[start:end])
        for key in ("核心一句话", "最容易错", "下一步"):
            if key not in tail:
                add("W", "W-READER-INDEX", start,
                    "回看索引缺「{}」——用「核心一句话/最容易错/下一步」三行".format(key))
        last_ans = max((s for s, _ in doc["selftest"]), default=-1)
        if start <= last_ans:
            add("W", "W-READER-INDEX", start,
                "回看索引应在自测答案区之后——先做题对答案,再回看索引")
        for later in ("## 待解决问题", "## 扩展（选读）"):
            if later in lines and lines.index(later) < start:
                add("W", "W-READER-INDEX", start,
                    "回看索引应在{}之前——保持文末收束顺序".format(later))

    # 6. 概念单元首行一句话结论(只在启用 P1 速览时查;豁免单元跳过)
    if "## 本节速览" in lines:
        for u in doc["units"]:
            unit_text = "\n".join(lines[u["start"]:u["end"]])
            if THIRD_EXEMPT_RE.search(unit_text) or re.search(r"【[^】]*参照[^】]*】", unit_text):
                continue
            body = [ln.strip() for ln in lines[u["start"] + 1:u["end"]] if ln.strip()]
            if body and not re.match(r"^(?:[-*+]\s+|\d+[.、)]\s*)?一句话结论\s*[：:]", body[0]):
                add("W", "W-READER-CONCLUSION", u["start"],
                    "概念 " + str(u["num"]) + " 首行缺「一句话结论:……」——"
                    "长节/读者版先给结论再展开;纯概念/参照级/L3 可标豁免")

    # 7. 段落加粗密度:连续两段都在抢重点时提示(术语密集段可例外)
    prev_emphasis = False
    for i, ln in enumerate(lines):
        if fence[i] or i in box_rows:
            prev_emphasis = False
            continue
        s = ln.lstrip()
        if not s or s.startswith(("#", "|", ">", "```")):
            prev_emphasis = False
            continue
        count = len(re.findall(r"\*\*[^*]+\*\*", vis[i]))
        if count >= 2 and prev_emphasis:
            add("W", "W-READER-EMPHASIS", i,
                "连续两段都用了加粗——只给术语首现/关键判断/易错点;术语密集段可例外,其余改普通文字")
        prev_emphasis = count >= 2

    # 8. 超长正文行:一行塞多个逻辑层(vis 已剥公式与代码,长度即可读长度)
    limit = cfg["prose_line_max_chars"]
    answer_ranges = doc["selftest"]
    for i, ln in enumerate(lines):
        if fence[i] or i in box_rows:
            continue
        if any(s <= i < e for s, e in answer_ranges):
            continue
        s = vis[i].strip()
        if not s or s.startswith(("#", "|", ">")):
            continue
        if len(s) > limit:
            add("W", "W-READER-LONGLINE", i,
                "单行可见正文 {} 字——一行塞了多个逻辑层;按「一段一义」拆句拆段,"
                "推导每步一行,台账/重复内容移出正文".format(len(s)))

    # 9. 列表嵌套深度:>3 层扫读困难
    depth_max = cfg["list_depth_max"]
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        m = re.match(r"^(\s*)(?:[-*+]|\d+[.、)])\s", ln)
        if not m:
            continue
        depth = len(m.group(1).expandtabs(4)) // 2 + 1
        if depth > depth_max:
            add("W", "W-READER-DEEPNEST", i,
                "列表嵌套 {} 层——超过 {} 层扫读困难;提升层级或拆成小节".format(
                    depth, depth_max))

    # 10–13. 新版式检查
    check_heading_body(lines, fence, add, cfg)
    check_caption(lines, fence, add, cfg)
    check_linktext(lines, fence, add, cfg)
    check_table_align(lines, fence, add, cfg)


# ═══════════════════════════════════════════════════════════════════
# 文件结构可读性闸口（ops/layout.md；独立 CLI 用，constants.layout 驱动）
# ═══════════════════════════════════════════════════════════════════

# 列表标记后无空格：`1.（题 1）`、`-要点`、`1、题面`——CommonMark 不认定为列表。
LIST_SPACE_RE = re.compile(r"^(\s*(?:>\s*)*)(\d+[.)、]|[-*+])(?=[^\s\d.）)\-*+])")
HR_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
LATEX_ARROW_RE = re.compile(
    r"\$\\(?:right|left|Right|Left|long|Long|leftright|Leftright)arrow\b[^$]*\$|\$\\to\b[^$]*\$")
_DEFAULT_LAYOUT = {
    "hard_line_max": 400,
    "anchor_gap_max": 400,
    "para_chars_max": 150,
    "para_sentences_max": 4,
    "hr_max": 3,
    "section_bold_floor_chars": 300,
    "table_cols_max_hard": 4,
    "emphasis_floor_exempt": [
        "题组", "作答与判分", "复述检查清单", "操作作品验收",
        "参考答案", "答案", "备注", "来源", "参考资料",
        "自测", "概念地图", "总表", "清单", "检验", "检验题", "检验问题",
    ],
}


def _load_layout_cfg():
    """读 contracts/rules.json 的 constants.layout；缺失时用内置默认。"""
    path = Path(__file__).resolve().parent.parent / "contracts" / "rules.json"
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))["constants"].get("layout", {})
    except (OSError, UnicodeError, ValueError, KeyError):
        cfg = {}
    out = dict(_DEFAULT_LAYOUT)
    out.update({k: v for k, v in cfg.items()})
    return out


def _vis_lines(lines):
    """可见正文（剥围栏/代码/公式）。复用 verify_explanation 的实现（惰性导入避免环）。"""
    global _COMPUTE_VISIBLE
    if _COMPUTE_VISIBLE is None:
        from verify_explanation import compute_visible as fn
        _COMPUTE_VISIBLE = fn
    return _COMPUTE_VISIBLE(lines)


_COMPUTE_VISIBLE = None


def check_layout(text, cfg=None):
    """学员可读文件的结构可读性检查（ops/layout.md）。

    返回 (sev, code, lineno_1based, msg) 列表；sev ∈ {"E", "W"}。
    只做可静态判定项；「是否更易读」的语义判断仍归人工读者。
    """
    cfg = dict(_DEFAULT_LAYOUT, **(cfg or {}))
    lines = text.splitlines()
    vis, fence = _vis_lines(lines)
    findings = []

    def add(sev, code, idx, msg):
        findings.append((sev, code, idx + 1, msg))

    hard_line = int(cfg["hard_line_max"])
    gap_max = int(cfg["anchor_gap_max"])
    floor_chars = int(cfg["section_bold_floor_chars"])
    hr_max = int(cfg["hr_max"])
    cols_max = int(cfg["table_cols_max_hard"])

    # E1. 行内 $ 当行成对（跳过围栏与 $$ 跨行块内行）
    in_fence = in_math = False
    for i, ln in enumerate(lines):
        if in_fence:
            if ln.lstrip().startswith("```"):
                in_fence = False
            continue
        if ln.lstrip().startswith("```"):
            in_fence = True
            continue
        if in_math:
            if "$$" in ln:
                in_math = False
            continue
        if "$$" in ln:
            if ln.count("$$") % 2 == 1:
                in_math = True
            continue
        if ln.count("$") % 2 == 1:
            add("E", "E-LAYOUT-MATH-UNPAIRED", i,
                "行内 $ 不成对（本行 %d 个）——补齐定界符；编辑残片（如「ightarrow$」）必须删除；"
                "美元金额请转义 \\$ 或写「美元」" % ln.count("$"))

    # E2. 列表标记后必须空格
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        m = LIST_SPACE_RE.match(ln)
        if m:
            add("E", "E-LAYOUT-LIST-SPACE", i,
                "列表标记「%s」后无空格——CommonMark 不认定为列表，渲染成文字墙；"
                "标记后先空格再写内容，顿号条目（1、）一律改「1. 」" % m.group(2))

    # E3. 单行可见正文超硬上限（标题/表格/引用行豁免，与 W-READER-LONGLINE 同口径）
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        s = vis[i].strip()
        if not s or s.startswith(("#", "|", ">")) or ln.lstrip().startswith(("|", ">")):
            continue
        if len(s) > hard_line:
            add("E", "E-LAYOUT-LONGLINE", i,
                "单行可见正文 %d 字（硬上限 %d）——一行塞了多个逻辑层；"
                "按每题卡片拆短行，台账内容移出正文" % (len(s), hard_line))

    # E4. 标题不跳级
    prev = 0
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        m = re.match(r"^(#{1,6})\s+", ln)
        if not m:
            continue
        level = len(m.group(1))
        if prev and level > prev + 1:
            add("E", "E-LAYOUT-HEADING-SKIP", i,
                "标题层级跳级 H%d→H%d——用 H2 分单元、H3 分小节，不跳级" % (prev, level))
        prev = level

    # E5. 表格列数硬上限 + 表头分隔行
    for block in table_blocks(lines, fence):
        if len(block) < 2 or not is_table_sep(lines[block[1]]):
            add("E", "E-LAYOUT-TABLE-WIDE", block[0],
                "表格缺表头分隔行——补「| 列名 | … |」与「|---|---|」，或改列表/卡片")
            continue
        cols = len(table_cells(lines[block[0]]))
        if cols > cols_max:
            add("E", "E-LAYOUT-TABLE-WIDE", block[0],
                "表格 %d 列（硬上限 %d）——拆成卡片、两张表或列表" % (cols, cols_max))

    # W1. 视觉锚点间距：连续正文超过 gap_max 字无任何锚点
    anchor_re = re.compile(r"^(#{1,6}\s|\s*(?:[-*+]|\d+[.)])\s|\||>|\s*!\[)")
    pending = 0
    pend_start = 0
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        if HR_RE.match(ln) or anchor_re.match(ln) or ("$" in ln):
            if pending > gap_max:
                add("W", "W-LAYOUT-ANCHOR-GAP", pend_start,
                    "连续正文约 %d 字无视觉锚点——每约一屏（%d 字）给一个标题/列表/表格/图/公式/引用块"
                    % (pending, gap_max))
            pending = 0
            pend_start = i + 1
            continue
        pending += len(vis[i].strip())
    if pending > gap_max:
        add("W", "W-LAYOUT-ANCHOR-GAP", pend_start,
            "文末连续正文约 %d 字无视觉锚点——每约一屏（%d 字）给一个锚点" % (pending, gap_max))

    # W1b. 段落长度：每段 ≤ para_sentences_max 句或 ≤ para_chars_max 字
    #      （与强调下限同一豁免表；列表/表格/引用/标题/围栏行不进段落）
    floor_exempt = cfg.get("emphasis_floor_exempt", [])
    para_sents = int(cfg.get("para_sentences_max", 4))
    para_chars = int(cfg.get("para_chars_max", 150))
    state = {"para_start": None, "parts": [], "sec_ln": ""}

    def _flush_para():
        if state["para_start"] is None:
            return
        if any(e in state["sec_ln"] for e in floor_exempt):
            return
        body = "".join(state["parts"])
        sents = len(re.findall(r"[。！？!?]", body))
        chars = len(re.sub(r"\s", "", body))
        if sents > para_sents or chars > para_chars:
            add("W", "W-LAYOUT-PARA-LONG", state["para_start"],
                "段落约 %d 句 / %d 字（基线 ≤%d 句或 ≤%d 字）——拆段，一段一义"
                % (sents, chars, para_sents, para_chars))

    for i, ln in enumerate(lines):
        if fence[i]:
            _flush_para()
            state["para_start"], state["parts"] = None, []
            continue
        stripped = ln.strip()
        if not stripped or HR_RE.match(ln) or anchor_re.match(ln):
            _flush_para()
            state["para_start"], state["parts"] = None, []
            if re.match(r"^##\s", ln):
                state["sec_ln"] = ln
            continue
        if state["para_start"] is None:
            state["para_start"] = i
            state["parts"] = []
        state["parts"].append(vis[i])
    _flush_para()

    # W2. 强调下限：H2 节正文 ≥floor_chars 而零加粗 = 强调清零
    #     （题组/判分/答案等记录型区块豁免——台账不考究强调，见 constants.layout）
    sec_start = sec_chars = sec_bold = None
    sec_exempt = False
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        if re.match(r"^##\s", ln):
            if (sec_start is not None and sec_chars >= floor_chars
                    and sec_bold == 0 and not sec_exempt):
                add("W", "W-LAYOUT-EMPHASIS-FLOOR", sec_start,
                    "本节正文约 %d 字零加粗（强调清零）——关键判断/易错点至少标一处" % sec_chars)
            sec_start, sec_chars, sec_bold = i, 0, 0
            sec_exempt = any(e in ln for e in floor_exempt)
        elif sec_start is not None:
            sec_chars += len(vis[i].strip())
            sec_bold += len(re.findall(r"\*\*[^*]+\*\*", ln))
    if (sec_start is not None and sec_chars >= floor_chars
            and sec_bold == 0 and not sec_exempt):
        add("W", "W-LAYOUT-EMPHASIS-FLOOR", sec_start,
            "末节正文约 %d 字零加粗（强调清零）——关键判断/易错点至少标一处" % sec_chars)

    # W3. 分隔线全文 ≤ hr_max 条
    hr_seen = 0
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        if HR_RE.match(ln):
            hr_seen += 1
            if hr_seen == hr_max + 1:
                add("W", "W-LAYOUT-SEPARATOR", i,
                    "分隔线超过 %d 条——只用于一级大区块之间，其余删除" % hr_max)

    # W4. 行尾全文统一
    if "\r\n" in text and re.search(r"(?<!\r)\n", text):
        add("W", "W-LAYOUT-LINE-ENDING", 0,
            "行尾混用 CRLF 与 LF——全文统一为一种（建议 LF）")

    # W5. 非公式语境的 LaTeX 箭头（全文无 $$ 块且无结构命令时才判）
    if "$$" not in text and not re.search(r"\\(?:frac|sqrt|sum|int)\b", text):
        for i, ln in enumerate(lines):
            if fence[i]:
                continue
            if LATEX_ARROW_RE.search(ln):
                add("W", "W-LAYOUT-LATEX-ARROW", i,
                    "非公式语境用 LaTeX 箭头——关系记号改 Unicode（→/⇒）；真公式按 ops/formulas.md")

    return findings


_SELFTEST_CASES = [
    ("E-LAYOUT-LIST-SPACE", "# 题\n\n1.（题 1）判定下列词性\n", "E"),
    ("E-LAYOUT-LONGLINE", "# 题\n\n" + "这" * 401 + "\n", "E"),
    ("E-LAYOUT-MATH-UNPAIRED", "# 题\n\n残行 ightarrow$ v2.0\n", "E"),
    ("E-LAYOUT-HEADING-SKIP", "# A\n\n## B\n\n#### D\n", "E"),
    ("E-LAYOUT-TABLE-WIDE", "# 题\n\n| a | b | c | d | e |\n|---|---|---|---|---|\n| 1 | 2 | 3 | 4 | 5 |\n", "E"),
    ("W-LAYOUT-SEPARATOR", "# 题\n\n---\n\n---\n\n---\n\n---\n\n正文。\n", "W"),
    ("W-LAYOUT-LATEX-ARROW", "# 题\n\n主语 $\\rightarrow$ 直接宾语\n", "W"),
    ("W-LAYOUT-LINE-ENDING", "# 题\r\n\r\n正文一句。\n", "W"),
    ("W-LAYOUT-PARA-LONG", "# 题\n\n第一句。第二句。第三句。第四句。第五句。第六句。\n", "W"),
    ("clean", "# 题\n\n一句**关键**判断。\n\n- 列表项\n1. 有序项\n\n| a | b |\n|---|---|\n| 1 | 2 |\n", None),
]


def _selftest():
    ok = fail = 0
    for name, sample, want_sev in _SELFTEST_CASES:
        fs = check_layout(sample)
        codes = {(s, c) for s, c, _, _ in fs}
        if want_sev is None:
            passed = not any(s == "E" for s, _, _, _ in fs)
            print("[{}] selftest {}：期望零 E，实际 {}".format(
                "OK" if passed else "FAIL", name, [c for s, c, _, _ in fs if s == "E"]))
        else:
            passed = any(s == want_sev and c == name for s, c, _, _ in fs)
            print("[{}] selftest {}：期望 {} 命中".format(
                "OK" if passed else "FAIL", name, name))
        ok += passed
        fail += not passed
    print("ltw_typography --selftest: {} checks, {} OK, {} FAIL".format(ok + fail, ok, fail))
    return 1 if fail else 0


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(
        description="文件结构可读性闸口（ops/layout.md；E 级违规退出码 1；只读）")
    ap.add_argument("paths", nargs="*", help="学员可读 .md 文件（可多个）")
    ap.add_argument("--selftest", action="store_true", help="运行内置突变体自测")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.paths:
        ap.error("需要至少一个 .md 路径，或 --selftest")
    cfg = _load_layout_cfg()
    bad = 0
    for p in args.paths:
        path = Path(p)
        try:
            # newline="" 保留原始行尾——行尾混用检查（W-LAYOUT-LINE-ENDING）依赖原始字节
            with path.open("r", encoding="utf-8", newline="") as fh:
                text = fh.read()
        except (OSError, UnicodeError) as exc:
            print("[E] E-READ-FILE 0 {} 读取失败：{}".format(path, exc))
            bad += 1
            continue
        fs = check_layout(text, cfg)
        for sev, code, ln, msg in fs:
            print("[{}] {} {}:{} {}".format(sev, code, path, ln, msg))
        if any(f[0] == "E" for f in fs):
            bad += 1
    print("ltw_typography: {} 个文件，{} 个存在 E 级违规".format(len(args.paths), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
