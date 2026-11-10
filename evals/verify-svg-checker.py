#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SVG 校验器回归（只读、零网络、幂等）。

背景：`_svg_problems` 原本只扫 `font-size="N"` / `stroke-width="N"` 两种
presentational attribute 与 `href="https?://"`，导致以下违规全部漏检：
  1. `style="font-size: 8px"` 内联字号
  2. `<style>` 内 CSS 类声明字号
  3. `@import url(http…)` / `url(//…)` 外部资源
  4. **自包含判据下的相对路径引用**——`<use href="a.svg#a">`、`<image href="data:…">`、
     `url(other.svg#g)`、`@import url("evil.css")`。判据源头是 `references/handout-layout.md`
     「SVG 为纯静态图形——不含 script 与外部引用」，即文档必须自包含；旧实现只枚举
     `https?://` 与 `//`，相对路径正好从枚举缝里漏出去。
本脚本用内联临时 SVG 复现以上各类，要求违规必须报错、文档内锚点（`#id`）必须放行。

用法：python -B evals/verify-svg-checker.py [--selftest]
退出码：0 全过；1 有失败；2 参数/环境错误。
"""
import argparse
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import ltw_typography  # noqa: E402

CFG = {"svg_font_min": 14, "svg_line_min": 1.5}

CASES = [
    (
        "内联 style 字号低于下限必须报错",
        '<svg viewBox="0 0 100 100" role="img"><title>t</title><desc>d</desc>'
        '<text style="font-size: 8px">x</text></svg>',
        "字号",
    ),
    (
        "<style> 内 CSS 类字号低于下限必须报错",
        '<svg viewBox="0 0 100 100" role="img"><title>t</title><desc>d</desc>'
        '<style>.tiny{font-size:8px}</style><text class="tiny">x</text></svg>',
        "字号",
    ),
    (
        "@import 外部样式表必须报错",
        '<svg viewBox="0 0 100 100" role="img"><title>t</title><desc>d</desc>'
        '<style>@import url("http://evil.example/x.css");</style></svg>',
        "@import",
    ),
    (
        "url(//…) 协议相对外链必须报错",
        '<svg viewBox="0 0 100 100" role="img"><title>t</title><desc>d</desc>'
        '<rect fill="url(//cdn.example/p.svg#g)"/></svg>',
        "外部资源",
    ),
    (
        "<image href> 外链图片必须报错",
        '<svg viewBox="0 0 100 100" role="img"><title>t</title><desc>d</desc>'
        '<image href="https://example.com/a.png"/></svg>',
        "外部",
    ),
    (
        "style 内线宽低于下限必须报错",
        '<svg viewBox="0 0 100 100" role="img"><title>t</title><desc>d</desc>'
        '<rect style="stroke-width: 0.5"/></svg>',
        "线宽",
    ),

    # 自包含判据：相对路径同样指向仓外文件，旧实现只查 https?:// 与 //，故全漏。
    (
        "<use href> 相对路径必须报错（自包含）",
        '<svg viewBox="0 0 100 100" role="img"><title>t</title><desc>d</desc>'
        '<use href="../secrets/x.svg#a"/></svg>',
        "外部",
    ),
    (
        "<use xlink:href> 相对路径必须报错（自包含）",
        '<svg viewBox="0 0 100 100" role="img"><title>t</title><desc>d</desc>'
        '<use xlink:href="a.svg#a"/></svg>',
        "外部",
    ),
    (
        "<image href=data:base64> 必须报错（自包含）",
        '<svg viewBox="0 0 100 100" role="img"><title>t</title><desc>d</desc>'
        '<image href="data:image/png;base64,AAA"/></svg>',
        "外部",
    ),
    (
        "url(相对路径) 必须报错（自包含）",
        '<svg viewBox="0 0 100 100" role="img"><title>t</title><desc>d</desc>'
        '<rect fill="url(other.svg#g)"/></svg>',
        "外部资源",
    ),
    (
        "@import 相对路径必须报错（自包含）",
        '<svg viewBox="0 0 100 100" role="img"><title>t</title><desc>d</desc>'
        '<style>@import url("evil.css");</style></svg>',
        "@import",
    ),
]

GOOD = [
    (
        "合规 SVG 零告警",
        '<svg viewBox="0 0 100 100" role="img"><title>t</title><desc>d</desc>'
        '<defs><marker id="a"/></defs>'
        '<rect fill="url(#a)" style="font-size:16px"/></svg>',
    ),
    # 自包含判据只封「文档外」引用，文档内锚点必须放行，否则会误杀合法 marker/渐变/符号复用。
    (
        "文档内锚点 url(#a) 必须放行",
        '<svg viewBox="0 0 100 100" role="img"><title>t</title><desc>d</desc>'
        '<defs><marker id="a"/></defs><rect fill="url(#a)"/></svg>',
    ),
    (
        "<use href=\"#sym\"> 文档内符号复用必须放行",
        '<svg viewBox="0 0 100 100" role="img"><title>t</title><desc>d</desc>'
        '<defs><g id="sym"/></defs><use href="#sym"/></svg>',
    ),
]


def run():
    fails = []
    for name, svg, must_contain in CASES:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "case.svg"
            p.write_text(svg, encoding="utf-8")
            probs = ltw_typography._svg_problems(p, CFG)
        if not probs:
            fails.append("{}：违规未被发现（返回空）".format(name))
        elif not any(must_contain in x for x in probs):
            fails.append("{}：报了 {}，但未含关键字「{}」".format(name, probs, must_contain))
    for name, svg in GOOD:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "case.svg"
            p.write_text(svg, encoding="utf-8")
            probs = ltw_typography._svg_problems(p, CFG)
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
