#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SVG 校验器回归（只读、零网络、幂等）。

覆盖三段历史：
  1. 票 53：style 内联字号 / <style> 类字号 / @import / 相对路径外链（自包含判据）
  2. 票 57：14 项漏检（xmlns、foreignObject、事件属性、悬空 url(#id)、空 title/desc、
     浅色底、font 简写、CSS 关键字、无默认基线的 text/line、viewBox 缩放、文本溢出）
     与 2 项相对字号误报（1.2em / 1.2rem 必须零告警）
  3. 放行项：文档内锚点 url(#a) / <use href="#sym"> 不得误杀

判据源头：references/handout-layout.md「4.2 图 / SVG 技术要求」与
「图像可视化双轨」；参数取自 contracts/rules.json 的 reader 块（单一事实源，
避免「文档写 16、代码按 12 判」的静默漂移）。

用法：python -B evals/verify-svg-checker.py [--selftest]
退出码：0 全过；1 有失败；2 参数/环境错误。
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import ltw_typography  # noqa: E402

FALLBACK_CFG = {
    "svg_font_min": 14,
    "svg_line_min": 1.5,
    "svg_relative_font_base": 16,
    "svg_canvas_light_bg_required": True,
    "svg_forbidden_tags": ["foreignObject"],
}


def load_cfg():
    """从 contracts/rules.json 取 reader 块；读不到就用内置缺省。"""
    path = SKILL_ROOT / "contracts" / "rules.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cfg = dict(FALLBACK_CFG)
        cfg.update(data["constants"]["reader"])
        return cfg
    except (OSError, KeyError, ValueError):
        return dict(FALLBACK_CFG)


CFG = load_cfg()
NS = 'xmlns="http://www.w3.org/2000/svg"'
LIGHT_BG = '<rect x="0" y="0" width="100" height="100" fill="#ffffff"/>'


def svg(inner, vb="0 0 100 100", ns=True, bg=True, title="t", desc="d"):
    """拼一个结构合规的 SVG，只让被测项成为唯一变量。"""
    return ('<svg viewBox="{vb}" role="img"{ns}><title>{t}</title><desc>{d}</desc>'
            '{bg}{inner}</svg>').format(
                vb=vb, ns=(" " + NS) if ns else "", bg=LIGHT_BG if bg else "",
                t=title, d=desc, inner=inner)


# (用例名, SVG 文本, 期望命中的关键字)
CASES = [
    # --- 票 53：绕过点 ---
    ("内联 style 字号低于下限必须报错",
     svg('<text style="font-size: 8px">x</text>'), "字号"),
    ("<style> 内 CSS 类字号低于下限必须报错",
     svg('<style>.tiny{font-size:8px}</style><text class="tiny">x</text>'), "字号"),
    ("@import 外部样式表必须报错",
     svg('<style>@import url("http://evil.example/x.css");</style>'), "@import"),
    ("url(//…) 协议相对外链必须报错",
     svg('<rect fill="url(//cdn.example/p.svg#g)"/>'), "外部资源"),
    ("<image href> 外链图片必须报错",
     svg('<image href="https://example.com/a.png"/>'), "外部"),
    ("style 内线宽低于下限必须报错",
     svg('<rect style="stroke-width: 0.5"/>'), "线宽"),
    ("<use href> 相对路径必须报错（自包含）",
     svg('<use href="../secrets/x.svg#a"/>'), "外部"),
    ("<use xlink:href> 相对路径必须报错（自包含）",
     svg('<use xlink:href="a.svg#a"/>'), "外部"),
    ("<image href=data:base64> 必须报错（自包含）",
     svg('<image href="data:image/png;base64,AAA"/>'), "外部"),
    ("url(相对路径) 必须报错（自包含）",
     svg('<rect fill="url(other.svg#g)"/>'), "外部资源"),
    ("@import 相对路径必须报错（自包含）",
     svg('<style>@import url("evil.css");</style>'), "@import"),

    # --- 票 57 漏检：结构项 ---
    ("根元素缺 xmlns 必须报错",
     svg('<text font-size="16">x</text>', ns=False), "xmlns"),
    ("<foreignObject> 必须报错（可嵌 HTML 绕过字体/无障碍检查）",
     svg('<foreignObject><div>x</div></foreignObject>'), "foreignObject"),
    ("事件属性 onload= 必须报错",
     svg('<rect onload="alert(1)" width="10" height="10"/>'), "事件属性"),
    ("<title> 内容为空必须报错",
     svg('<text font-size="16">x</text>', title=""), "title"),
    ("<desc> 内容为空必须报错",
     svg('<text font-size="16">x</text>', desc=""), "desc"),
    ("url(#id) 指向不存在的 id 必须报错",
     svg('<line x1="0" y1="0" x2="9" y2="9" stroke-width="2" '
         'marker-end="url(#nope)"/>'), "不存在的 id"),
    ("缺自带浅色底 rect 必须报错",
     svg('<text font-size="16">x</text>', bg=False), "浅色底"),

    # --- 票 57 漏检：字号/线宽盲区 ---
    ("font-size:small（CSS 关键字）必须报错",
     svg('<text style="font-size:small">x</text>'), "字号"),
    ("font:8px sans-serif（简写）必须报错",
     svg('<text style="font:8px sans-serif">x</text>'), "简写"),
    ("完全未声明 font-size 的 <text> 必须报错（缺省 16 不达标）",
     svg('<text x="5" y="20">x</text>'), "未声明 font-size"),
    ("完全未声明 stroke-width 的 <line> 必须报错（缺省 1 不达标）",
     svg('<line x1="0" y1="0" x2="9" y2="9" stroke="#000"/>'), "未声明 stroke-width"),

    # --- 票 57 漏检：近似机检项 ---
    ("viewBox 远宽于设计宽必须报错（缩放后实际字号 <14）",
     svg('<text font-size="14">x</text>', vb="0 0 4000 100"), "viewBox 宽"),
    ("中文文本估算宽度超出 viewBox 必须报错",
     svg('<text font-size="16" x="5" y="20">'
         '这是一个很长很长的中文标题文字用于测试是否超出边界</text>'), "超出 viewBox"),
]

# (用例名, SVG 文本) —— 必须零告警
GOOD = [
    ("合规 SVG 零告警",
     svg('<defs><marker id="a"/></defs>'
         '<rect fill="url(#a)" style="font-size:16px"/>')),
    # 自包含判据只封「文档外」引用，文档内锚点必须放行，否则会误杀合法 marker/渐变/符号复用。
    ("文档内锚点 url(#a) 必须放行",
     svg('<defs><marker id="a"/></defs><rect fill="url(#a)"/>')),
    ('<use href="#sym"> 文档内符号复用必须放行',
     svg('<defs><g id="sym"/></defs><use href="#sym"/>')),

    # --- 票 57 误报回归：相对字号必须零告警 ---
    # 旧实现 _min_num 只抓第一个数字、不区分单位，把 1.2em 当 1.2px 判死。
    ('font-size="1.2em" 不得误报（相对单位先换算基准）',
     svg('<text font-size="1.2em">x</text>')),
    ('font-size="1.2rem" 不得误报（相对单位先换算基准）',
     svg('<text font-size="1.2rem">x</text>')),
    ('style="font-size:1.2em" 不得误报',
     svg('<text style="font-size:1.2em">x</text>')),
    ('style="font-size:120%" 不得误报（120% × 16 = 19.2 ≥ 14）',
     svg('<text style="font-size:120%">x</text>')),
    ("字号 14px 正好在下限上不得误报",
     svg('<text font-size="14px">x</text>')),
    ("stroke-width 1.5 正好在下限上不得误报",
     svg('<line x1="0" y1="0" x2="9" y2="9" stroke-width="1.5"/>')),
]


def _run_one(svg_text):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "case.svg"
        p.write_text(svg_text, encoding="utf-8")
        return ltw_typography._svg_problems(p, CFG)


def run():
    fails = []
    for name, svg_text, must_contain in CASES:
        probs = _run_one(svg_text)
        if not probs:
            fails.append("{}：违规未被发现（返回空）".format(name))
        elif not any(must_contain in x for x in probs):
            fails.append("{}：报了 {}，但未含关键字「{}」".format(
                name, probs, must_contain))
    for name, svg_text in GOOD:
        probs = _run_one(svg_text)
        if probs:
            fails.append("{}：合规样例被误报 {}".format(name, probs))
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="只跑内置用例")
    ap.parse_args()
    fails = run()
    total = len(CASES) + len(GOOD)
    for f in fails:
        print("[FAIL] " + f)
    print("verify-svg-checker: {} checks, {} OK, {} FAIL".format(
        total, total - len(fails), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
