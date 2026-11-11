#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ltw_typography - 讲义读者版检查模块。

被 verify_explanation.py --reader 调用（run_checks 文案/结构类 + check_image_rules 图类，
讲义读者版 W-READER-*，不阻断）。两个入口分开：图检查不该被「像不像讲义」的门挡住，
合在一起还会让同一张图被两处各查一遍。
不写盘、不联网、不读环境变量；只读被校验材料所在目录内的 SVG。
语义上的"是否更易读"仍归人工读者验证。
"""
import re
from pathlib import Path

H2_RE = re.compile(r"^##\s")
MD_IMAGE_ALT_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
# 正文「图:路径」写法(与 verify_explanation.IMG_LABEL_RE 同义),仅用于判断"要不要跑图检查"
IMG_LABEL_PROBE_RE = re.compile(r"图\s*[：:]\s*([^\s（()）]+)")
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


# 相对字号换算基准：1em/1rem 缺省 = 16px（CSS 初始值）。写成模块常量而不是裸数字，
# 是为了让 contracts/rules.json 的 reader.svg_relative_font_base 成为唯一事实源——
# 两条口径一旦分叉，就是「文档说 16、代码按 12 判」这类静默漂移。
SVG_RELATIVE_FONT_BASE_DEFAULT = 16.0
# CSS 绝对长度单位换算（仅这些单位能确定 px 值）；其余相对单位一律跳过不判。
SVG_ABS_UNITS = {
    "px": 1.0, "pt": 96.0 / 72.0, "pc": 16.0, "in": 96.0,
    "cm": 96.0 / 2.54, "mm": 96.0 / 25.4, "q": 96.0 / 101.6,
}
# 无法换算为 px 的单位（相对容器/视口）：判不了就不判，跳过。
SVG_REL_UNITS = {"em", "rem", "ex", "ch", "vw", "vh", "vmin", "vmax", "%"}
# CSS 关键字字号：绝对值可判，相对关键字跳过（与 em 同理，取决于父级）。
SVG_ABS_KEYWORDS = {
    "xx-small": 9.0, "x-small": 10.0, "small": 13.0,
    "medium": 16.0, "large": 18.0, "x-large": 24.0, "xx-large": 32.0,
}
SVG_REL_KEYWORDS = {"smaller", "larger", "inherit", "initial", "unset", "revert"}
# SVG 呈现属性缺省值（未声明时的实际渲染基线）。font-size 缺省 medium=16，
# stroke-width 缺省 1——两者都低于本仓下限，故「未声明」本身就是缺陷。
SVG_DEFAULT_FONT_SIZE = 16.0
SVG_DEFAULT_STROKE_WIDTH = 1.0
# 中文字宽估算系数（v2 §5.1 实测校准，msyh.ttc unitsPerEm=2048，6 万条实测最坏低估 0.000%）
SVG_CHAR_WIDTH = {
    "space": 0.30, "digit": 0.60, "upper": 1.05, "lower": 0.95,
    "ascii_other": 0.90, "wide": 1.00,
}


def _svg_width_em(s):
    """按字符分类累加字宽（em）。CJK/全角 >= U+2E80 记 1.00。"""
    total = 0.0
    for ch in s:
        o = ord(ch)
        if ch in " \t\n":
            total += SVG_CHAR_WIDTH["space"]
        elif o >= 0x2E80:
            total += SVG_CHAR_WIDTH["wide"]
        elif "0" <= ch <= "9":
            total += SVG_CHAR_WIDTH["digit"]
        elif "A" <= ch <= "Z":
            total += SVG_CHAR_WIDTH["upper"]
        elif "a" <= ch <= "z":
            total += SVG_CHAR_WIDTH["lower"]
        else:
            total += SVG_CHAR_WIDTH["ascii_other"]
    return total


def _svg_style_decls(text):
    """扫 style="" 与 <style> 内的 CSS 声明，产出 {属性: [原始值]}。

    合并两个来源是刻意的：票 53 之前只扫 presentational attribute，
    style 内联与 <style> 类声明都是绕过点，二者必须走同一条判定路径。
    """
    decls = {}
    chunks = re.findall(r"""style\s*=\s*"([^"]*)\"""", text, re.I)
    chunks += re.findall(r"style\s*=\s*'([^']*)'", text, re.I)
    for body in re.findall(r"<style\b[^>]*>(.*?)</style>", text, re.I | re.S):
        chunks.append(body)
    for chunk in chunks:
        for prop, val in re.findall(r"([a-z-]+)\s*:\s*([^;}]*)", chunk, re.I):
            decls.setdefault(prop.lower().strip(), []).append(val.strip())
    return decls


def _svg_font_px(raw, base, in_font_shorthand=False):
    """把一个 font-size 值换算成 px；判不了返回 None。

    「判不了返回 None」是这条判据的核心：相对单位 em/rem/% 若按字面数字判，
    1.2em 会被当成 1.2px（误报），8em 会被当成 8px 而漏掉真溢出。两者都错，
    所以必须先换算、换算不了就不判。
    """
    if raw is None:
        return None
    v = raw.strip()
    if v.lower().endswith("!important"):
        v = v[: -len("!important")].strip()
    if not v:
        return None
    low = v.lower()
    if low in SVG_REL_KEYWORDS:
        return None
    if low in SVG_ABS_KEYWORDS:
        return SVG_ABS_KEYWORDS[low]
    m = re.match(r"^(-?[0-9]*\.?[0-9]+)\s*([a-z%]*)$", low)
    if not m:
        return None
    try:
        num = float(m.group(1))
    except ValueError:
        return None
    unit = m.group(2)
    if unit == "":
        # 无单位在 font-size 里非法、在 font 简写里是 px
        return num if in_font_shorthand else None
    if unit in SVG_ABS_UNITS:
        return num * SVG_ABS_UNITS[unit]
    if unit == "em" or unit == "rem":
        # em/rem 以父级字号为基准；SVG 根继承 medium=16。基准写进
        # rules.json 的 svg_relative_font_base，故这是有依据的近似而非猜。
        return num * base
    if unit == "%":
        return num / 100.0 * base
    if unit in SVG_REL_UNITS:
        return None
    return None


def _svg_length_px(raw, base):
    """把长度值换算成 px；无单位在 SVG 里就是用户单位（=px），故与字号规则不同。

    与 _svg_font_px 分开是必要的：font-size 的无单位值非法，stroke-width 的无单位值
    合法（0.5 就是 0.5 用户单位）。共用一个函数会把合法线宽判成「判不了」而漏检。
    """
    if raw is None:
        return None
    v = raw.strip()
    if v.lower().endswith("!important"):
        v = v[: -len("!important")].strip()
    if not v:
        return None
    m = re.match(r"^(-?[0-9]*\.?[0-9]+)\s*([a-z%]*)$", v.lower())
    if not m:
        return None
    try:
        num = float(m.group(1))
    except ValueError:
        return None
    unit = m.group(2)
    if unit == "":
        return num
    if unit in SVG_ABS_UNITS:
        return num * SVG_ABS_UNITS[unit]
    if unit == "em" or unit == "rem":
        return num * base
    if unit == "%":
        return num / 100.0 * base
    return None


def _svg_font_decls(text):
    """收集 font-size 的全部声明来源：呈现属性、font 简写、style/CSS。

    返回 [(原始值, 是否来自 font 简写)]，交给 _svg_font_px 统一换算。
    """
    out = []
    for raw in re.findall(r"font-size\s*=\s*[\"']([^\"']*)", text, re.I):
        out.append((raw, False))
    for raw in re.findall(r"font\s*=\s*[\"']([^\"']*)", text, re.I):
        out.append((_svg_font_from_shorthand(raw), True))
    decls = _svg_style_decls(text)
    for raw in decls.get("font-size", []):
        out.append((raw, False))
    for raw in decls.get("font", []):
        out.append((_svg_font_from_shorthand(raw), True))
    return out


def _svg_font_from_shorthand(raw):
    """从 font 简写里取字号分量；无字号返回 None。

    简写形如 8px/1.5 sans-serif、italic bold 8px serif。跳过 style/weight 前缀词，
    取第一个带单位或纯数字的尺寸分量。
    """
    if not raw:
        return None
    tokens = re.split(r"[\s,]+", raw.strip())
    for tok in tokens:
        if not tok:
            continue
        head = tok.split("/")[0]
        if re.match(r"^-?[0-9]*\.?[0-9]+(?:px|pt|pc|in|cm|mm|q|em|rem|ex|ch|vw|vh|vmin|vmax|%)?$",
                    head, re.I):
            return head
        if head.lower() in SVG_ABS_KEYWORDS or head.lower() in SVG_REL_KEYWORDS:
            return head
    return None


def _svg_problems(path, cfg):
    """读者版 SVG 技术项：根元素 viewBox/role/xmlns、title/desc、字号/线宽、无脚本/外链。"""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ["SVG 读取失败"]
    problems = []
    base = float(cfg.get("svg_relative_font_base") or SVG_RELATIVE_FONT_BASE_DEFAULT)
    font_min = cfg["svg_font_min"]
    line_min = cfg["svg_line_min"]
    forbidden = tuple(cfg.get("svg_forbidden_tags") or ("foreignObject",))
    require_light_bg = cfg.get("svg_canvas_light_bg_required", True)
    root = re.search(r"<svg\b[^>]*>", text, re.I)
    root_tag = root.group(0) if root else ""
    if not root or "viewBox=" not in root_tag:
        problems.append("根元素缺 viewBox")
    if not root or not re.search(r"role\s*=\s*[\"']img[\"']", root_tag):
        problems.append("根元素缺 role=\"img\"")
    if not root or not re.search(r"\bxmlns\s*=", root_tag):
        problems.append("根元素缺 xmlns")
    for tag, label in (("title", "title"), ("desc", "desc")):
        m = re.search(r"<{0}\b[^>]*>(.*?)</{0}>".format(tag), text, re.I | re.S)
        if not m:
            problems.append("缺 <{}>".format(label))
        elif not re.sub(r"<[^>]+>", "", m.group(1)).strip():
            # 只查存在性会放过 <title></title>：读屏软件读不到任何内容，
            # 与完全没写等价。故判据是「内容非空」，不是「标签出现」。
            problems.append("<{}> 内容为空".format(label))
    low_text = text.lower()
    if "<script" in low_text:
        problems.append("含 script")
    for tag in forbidden:
        if re.search(r"<{}\b".format(re.escape(tag)), text, re.I):
            problems.append("含禁用的 <{}>（可嵌 HTML 绕过字体/无障碍检查）".format(tag))
    if re.search(r"\son[a-z]+\s*=", text, re.I):
        # 事件属性可执行脚本，等价于 <script>；用 \son 避免误伤 <only> 这类标签名
        problems.append("含事件属性 on*=")
    if re.search(r"(?:href|xlink:href)\s*=\s*[\"']https?://", text, re.I):
        problems.append("含外部引用")
    # 外链判据（第一性）：handout-layout.md「SVG 为纯静态图形——不含 script 与外部引用」
    # = 文档必须**自包含**。故判据不是「枚举外网协议」，而是「除文档内锚点 #id 外，一切引用皆外链」：
    # 相对路径同样指向仓外文件，正是绕过点（旧实现只看 https?:// 与 //）。
    if re.search(r"@import\b", text, re.I):
        problems.append("含 @import 外部样式表")
    for raw_ref in re.findall(r"url\(\s*([\"']?)([^)\"']+)\1\s*\)", text, re.I):
        target = raw_ref[1].strip()
        if not target.startswith("#"):
            problems.append("含外部资源引用 url({})".format(target[:40]))
            break
    for m in re.finditer(r"<(?:image|use)\b[^>]*?\b(?:xlink:)?href\s*=\s*([\"'])(.*?)\1", text, re.I | re.S):
        target = m.group(2).strip()
        if not target.startswith("#"):
            problems.append("含外部图片/引用 href({})".format(target[:40]))
            break

    # SVG-16：url(#id) 必须指向文档内真实存在的 id。悬空引用会渲染成空白，
    # 是「图看起来画了、实际什么都没显示」的静默失败，只能靠 id 集合比对抓。
    ids = set(re.findall(r"\bid\s*=\s*[\"']([^\"']+)[\"']", text))
    dangling = []
    for m in re.finditer(r"url\(\s*[\"']?#([^)\"'\s]+)", text, re.I):
        ref_id = m.group(1)
        if ref_id not in ids and ref_id not in dangling:
            dangling.append(ref_id)
    if dangling:
        problems.append("url(#id) 指向文档内不存在的 id：{}".format(
            "、".join(dangling[:3])))

    # SVG-17：自带浅色底（handout-layout.md:1116「SVG 自带浅色底（不依赖透明背景）」）。
    # 判据是「根级有一个铺满 viewBox 的浅色 rect」，不是「文本里出现 #fff」——
    # 后者会被任意元素的描边颜色蒙混过关。
    if require_light_bg and not _svg_has_light_canvas(text, root_tag):
        problems.append("缺自带浅色底 <rect>（不依赖透明背景）")

    # SVG-10 / SVG-11 / SVG-20：字号与线宽。呈现属性、style 内联、<style> CSS 三处
    # 走同一条换算路径；相对单位先换算再判，换算不了就跳过（见 _svg_font_px）。
    for raw, is_shorthand in _svg_font_decls(text):
        px = _svg_font_px(raw, base, in_font_shorthand=is_shorthand)
        if px is None:
            continue
        if px < font_min:
            label = "font 简写字号" if is_shorthand else "字号"
            problems.append("{} {} < {}".format(label, raw.strip()[:20], font_min))
            break
    line_decls = list(re.findall(r"stroke-width\s*=\s*[\"']([^\"']*)", text, re.I))
    line_decls += _svg_style_decls(text).get("stroke-width", [])
    for raw in line_decls:
        px = _svg_length_px(raw, base)
        if px is None:
            continue
        if px < line_min:
            problems.append("线宽 {} < {}".format(raw.strip()[:20], line_min))
            break

    # 无默认基线：完全未声明 font-size 的 <text> / stroke-width 的 <line>。
    # SVG 缺省 font-size=medium=16px、stroke-width=1，故「没写」不是「无约束」，
    # 而是落到一个低于下限的值——这正是旧实现的结构性盲区。
    font_declared = bool(re.search(r"font-size\s*[:=]", text, re.I)
                         or re.search(r"\bfont\s*[:=]", text, re.I))
    if not font_declared and re.search(r"<text\b", text, re.I):
        problems.append("<text> 未声明 font-size（缺省 {} < {}）".format(
            int(SVG_DEFAULT_FONT_SIZE), font_min))
    line_declared = bool(re.search(r"stroke-width\s*[:=]", text, re.I))
    if not line_declared and re.search(r"<(?:line|polyline|path)\b", text, re.I):
        problems.append("<line> 未声明 stroke-width（缺省 {} < {}）".format(
            SVG_DEFAULT_STROKE_WIDTH, line_min))

    # SVG-18（近似机检）：viewBox 缩放后实际字号。宿主显示宽未知，只能按
    # 「viewBox 宽 == 目标显示宽」这一设计约束反推：viewBox 明显宽于常见显示宽时，
    # 图必然被缩小，声明的 14px 实际渲染更小。判不了的场合不假装精确。
    if root:
        vb = re.search(r"viewBox\s*=\s*[\"']([^\"']+)[\"']", root_tag, re.I)
        if vb:
            nums = [float(x) for x in re.findall(r"-?[0-9]*\.?[0-9]+", vb.group(1))]
            if len(nums) == 4 and nums[2] > SVG_VIEWBOX_WARN_WIDTH:
                problems.append(
                    "viewBox 宽 {} 超过设计宽 {}（缩放到常见显示宽后字号会小于 {}，"
                    "按 1:1 设计）".format(int(nums[2]), int(SVG_VIEWBOX_WARN_WIDTH), font_min))

    # SVG-19（近似机检）：文本估算宽度超出 viewBox。公式见 v2 §5.1；
    # 只报近似值、不阻断——实际宽度取决于读者机器命中的字体。
    if root:
        vb = re.search(r"viewBox\s*=\s*[\"']([^\"']+)[\"']", root_tag, re.I)
        if vb:
            nums = [float(x) for x in re.findall(r"-?[0-9]*\.?[0-9]+", vb.group(1))]
            if len(nums) == 4:
                overflow = _svg_text_overflow(text, nums[2], base, font_min)
                if overflow:
                    problems.append(overflow)
    return problems


# viewBox 宽超过此值即视为「大图缩小」：handout-layout.md 要求按目标显示宽 1:1 设计，
# 640–720 是正文栏的常见宽度；再宽就必然被缩放，14px 声明值随之缩水。
SVG_VIEWBOX_WARN_WIDTH = 720.0
# 文本宽度判定的左右内边距（按 24px 估，与仓内样板 SVG 的 x=24 起点一致）
SVG_TEXT_PADDING = 24.0


def _svg_has_light_canvas(text, root_tag):
    """根级是否存在铺满 viewBox 的浅色底 rect。

    判据是「位置+尺寸覆盖画布」且「填充色亮度足够高」，不是「文本里出现 #fff」——
    后者会被任意描边色蒙混过关。填充色支持 #rgb/#rrggbb/rgb()/white 与常见命名色。
    """
    vb = re.search(r"viewBox\s*=\s*[\"']([^\"']+)[\"']", root_tag or "", re.I)
    if not vb:
        return False
    nums = [float(x) for x in re.findall(r"-?[0-9]*\.?[0-9]+", vb.group(1))]
    if len(nums) != 4:
        return False
    vx, vy, vw, vh = nums
    for m in re.finditer(r"<rect\b([^>]*)>", text, re.I):
        attrs = m.group(1)

        def attr(name):
            mm = re.search(r"\b{}\s*=\s*[\"']([^\"']*)[\"']".format(name), attrs, re.I)
            return mm.group(1).strip() if mm else None

        try:
            x = float(attr("x") or 0)
            y = float(attr("y") or 0)
            w = float(attr("width") or 0)
            h = float(attr("height") or 0)
        except ValueError:
            continue
        # 必须覆盖整块画布（允许 2px 误差），局部色块不算底
        if not (x <= vx + 2 and y <= vy + 2 and w >= vw - 2 and h >= vh - 2):
            continue
        fill = attr("fill") or _svg_css_fill(text, attr("class"))
        if fill and _svg_is_light_color(fill):
            return True
    return False


def _svg_css_fill(text, class_name):
    """从 <style> 里按 class 查 fill（浅色底写成 CSS 类的场合）。"""
    if not class_name:
        return None
    for cls in class_name.split():
        m = re.search(r"\.{}\b[^{{}}]*\{{([^}}]*)\}}".format(re.escape(cls)), text, re.I)
        if m:
            fm = re.search(r"fill\s*:\s*([^;}}]+)", m.group(1), re.I)
            if fm:
                return fm.group(1).strip()
    return None


def _svg_is_light_color(color):
    """颜色亮度是否达到「浅色底」标准（相对亮度 > 0.6）。"""
    c = (color or "").strip().lower()
    named = {"white": (255, 255, 255), "ivory": (255, 255, 240),
             "snow": (255, 250, 250), "whitesmoke": (245, 245, 245),
             "ghostwhite": (248, 248, 255)}
    rgb = named.get(c)
    if rgb is None:
        m = re.fullmatch(r"#([0-9a-f]{3})", c)
        if m:
            rgb = tuple(int(ch * 2, 16) for ch in m.group(1))
        else:
            m = re.fullmatch(r"#([0-9a-f]{6})", c)
            if m:
                rgb = tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
            else:
                m = re.fullmatch(r"rgba?\(\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+).*", c)
                if m:
                    rgb = tuple(int(m.group(i)) for i in (1, 2, 3))
    if rgb is None:
        return False
    r, g, b = rgb
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0 > 0.6


def _svg_text_overflow(text, vb_width, base, font_min):
    """SVG-19 近似机检：估算文本宽度是否超出 viewBox 宽。超了返回描述，否则 None。

    公式见 v2 §5.1（分类系数，6 万条实测最坏低估 0.000%）。只报近似——实际宽度
    取决于读者机器命中的字体，SVG 不嵌字体，所以这条只能报 W 不能阻断。
    """
    avail = vb_width - 2 * SVG_TEXT_PADDING
    if avail <= 0:
        return None
    for m in re.finditer(r"<text\b([^>]*)>(.*?)</text>", text, re.I | re.S):
        attrs, content = m.group(1), m.group(2)
        label = re.sub(r"<[^>]+>", "", content).strip()
        if not label:
            continue
        fm = re.search(r"font-size\s*=\s*[\"']([^\"']*)", attrs, re.I)
        size = _svg_font_px(fm.group(1), base) if fm else None
        if size is None:
            sm = re.search(r"font-size\s*:\s*([^;\"']+)", attrs, re.I)
            size = _svg_font_px(sm.group(1), base) if sm else None
        if size is None:
            size = SVG_DEFAULT_FONT_SIZE
        width = _svg_width_em(label) * size
        if width > avail:
            return ("文本估算宽 {}px 超出 viewBox 可用宽 {}px（近似值，见 v2 §5.1）："
                    "{}".format(int(width), int(avail), label[:16]))
    return None


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


# 受「像不像讲义」gate 约束的文案/结构类规则;图检查不在其中(见 check_image_rules)。
# 这份清单只用于「跳过要可判定」的登记,规则码本身以 contracts/rules.json 的
# errors 段为准——不在此重复登记图检查那四个码。
TEXT_RULE_CODES = (
    "W-READER-HEADING", "W-READER-TABLE", "W-READER-OVERVIEW", "W-READER-INDEX",
    "W-READER-CONCLUSION", "W-READER-EMPHASIS", "W-READER-LONGLINE",
    "W-READER-DEEPNEST", "W-READER-HEADING-BODY", "W-READER-LINKTEXT",
    "W-READER-TABLE-ALIGN",
)


def _prose_image_targets(vis_line):
    """取正文「图:路径」写法里的路径(排除落在图片语法区间内的 alt)。

    与 verify_explanation.image_refs 同义但更窄:只认正文写法,Markdown 图片语法
    那条由 MD_IMAGE_ALT_RE 单独处理,避免同一目标被查两遍。
    """
    spans = [m.span() for m in MD_IMAGE_ALT_RE.finditer(vis_line)]
    out = []
    for m in IMG_LABEL_PROBE_RE.finditer(vis_line):
        if any(s <= m.start() < e for s, e in spans):
            continue
        out.append(m.group(1))
    return out


def _check_svg_target(i, target, base_dir, add, cfg):
    """单个 SVG 目标的读者版技术项检查(两种图引用写法共用)。"""
    if base_dir is None or re.match(r"(?:https?:|data:|mailto:)", target, re.I):
        return
    path = Path(target) if Path(target).is_absolute() else Path(base_dir) / target
    if path.suffix.lower() != ".svg" or not path.exists():
        return
    probs = _svg_problems(path, cfg)
    if "SVG 读取失败" in probs:
        add("E", "E-IMG-READ", i, "SVG 读取失败或编码不是 UTF-8")
    elif probs:
        add("W", "W-READER-SVG", i,
            "SVG 读者版技术项不合格:" + "、".join(probs) +
            "——补 viewBox/role/xmlns、非空 title/desc、自带浅色底;"
            "字号 ≥14、线宽 ≥1.5(相对单位按基准换算);"
            "去 script/事件属性/foreignObject/外部引用;"
            "url(#id) 须指向文档内真实 id")


def has_image_ref(lines, vis, fence):
    """文本里是否有图片引用(Markdown 图片语法或「图:路径」正文写法)。

    只回答「要不要跑图检查」,不回答「像不像讲义」——两件事被本票拆开。
    读 vis 而不是原始行:与 check_image_rules 同一坐标系,否则 code span 里
    引述的写法示例会让它判「有图」,白跑一遍全套图检查。
    """
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        if MD_IMAGE_ALT_RE.search(vis[i]) or IMG_LABEL_PROBE_RE.search(vis[i]):
            return True
    return False


def check_image_rules(lines, vis, fence, base_dir, add, cfg):
    """图相关检查(alt / 图注 / SVG 技术项 / SVG 读取失败)。

    只读校验材料所在目录内的 SVG;不写盘、不联网、不读环境变量。
    与 run_checks 分开,因为图检查对任何含图文本都成立,不该被
    「像不像讲义」的 gate 挡住——结构不全的讲义恰恰最需要查图。
    """
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        # alt 与「图:路径」两种写法都要查:W-READER-ALT 的建议写法就是
        # 「图型:一句话结论」,照规范写只出现在 alt 里,正文写法另有一套。
        # 一律以 vis(剥掉 code span/公式后的可见正文)为准——反引号里引述的
        # 示例不是真图片,不查(与 E-IMG-DEADLINK 同一坐标系)。
        for m in MD_IMAGE_ALT_RE.finditer(vis[i]):
            alt, target = m.group(1).strip(), m.group(2).strip()
            if not alt or alt.lower() in GENERIC_ALT:
                add("W", "W-READER-ALT", i,
                    "图片 alt 为空或过于笼统——写「图型:一句话结论」,不写「示意图/图片」")
            _check_svg_target(i, target, base_dir, add, cfg)
        for target in _prose_image_targets(vis[i]):
            _check_svg_target(i, target, base_dir, add, cfg)
    check_caption(lines, vis, fence, add, cfg)


def check_caption(lines, vis, fence, add, cfg):
    """图片后应有图注（图注：… 或 图 N：…），表格内图片豁免。

    与 alt/SVG 检查同一坐标系:只认 vis(剥掉 code span/公式后的可见正文),
    反引号里引述的「写法示例」不是真图片,不要求配图注。
    """
    prefixes = tuple(cfg.get("figure_caption_prefixes")
                     or ("图注：", "图注:", "图 "))
    for i, ln in enumerate(lines):
        if fence[i] or ln.lstrip().startswith("|"):
            continue
        matches = list(MD_IMAGE_ALT_RE.finditer(vis[i]))
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
    """读者版/排版检查（W 级，只在 --reader 显式启用时执行，不拦截）。

    只做文案/结构类规则。图检查由 check_image_rules 单独承担——两者曾经共用一个
    布尔开关,结果同一张图会被两处各查一遍(重复报码)。拆成两个入口,调用方组合。
    """
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

    # 3. 图片 alt / SVG / 图注不在本函数内——由 check_image_rules 独立承担。

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

    # 10–13. 新版式检查(图注归图检查组,由 check_image_rules 负责,不在此重复)
    check_heading_body(lines, fence, add, cfg)
    check_linktext(lines, fence, add, cfg)
    check_table_align(lines, fence, add, cfg)
