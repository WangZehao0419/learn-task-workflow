#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""出题前术语对账（R46 机器护栏，stdlib-only、幂等只读）。

用途：
  判分题交付前，扫描题组/讲义文本中出现的「未引入术语」——即：某知识点的
  「引入」列登记的术语（或该 KP 名称本身），在课程体系中该 KP 仍为「未讲/暂缓/排除」
  状态，却出现在了待交付的题目文本里。这正是「未教术语进判分题」教学事故
  （R46 / SR-10）的机器可检形态。

对账集合（已引入 = 三者并集）：
  1. 课程体系中状态为「已讲」的 KP 的「引入」列术语；
  2. 状态为「已讲」的 KP 名称本身（清单行第 2 段）；
  3. --extra-terms 追加（地基目/术语地图/摸底证据里已给过定义的术语，
     逗号或分号分隔；也可用 --extra-file 传一个每行一个术语的文件）。

扫描范围（默认）：文件中「## 题组」「## 自测」「## 检验」等题面区标题行之后、
下一个 ## 标题之前的行；--scan-all 扫全文。术语命中按**整词包含**判定
（术语原样出现在文本中），长度 <2 的单字不参与匹配。

输入：
  python -B scripts/prereq_check.py --list <课程体系.md> --scan <题组或讲义.md>... 
      [--extra-terms "术语1,术语2"] [--extra-file <术语清单.txt>] [--scan-all]
  python -B scripts/prereq_check.py --selftest

退出码：
  0 = 干净（无未引入术语命中）
  1 = 存在命中（输出违规清单：文件、行号、术语、来源 KP）
  2 = 用法/文件错误（缺参数、文件不可读、清单零可用行）

输出：JSON 单行（stdout）：{"ok":bool,"violations":[...],"taught_term_count":N,"scanned_files":[...]}
  人读摘要走 stderr，方便交互式使用时直接看。

清单行解析口径与 kp_sort.py 一致：`｜` 分段，状态取第 6 段基值
（剥离尾部「（…）」括注）；「引入：」为可选第 7+ 段，冒号后半按
「；」「,」「、」拆分。缺「引入」段的 KP 不贡献术语（旧任务零迁移）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

STATUS_SPLIT_RE = re.compile(r"（[^）]*）\s*$")
QUESTION_SECTION_RE = re.compile(r"^#{1,2}\s*(题组|本节自测|自测|自测题|检验|检验题|检验问题|本节检验|练习|题)")
ANY_H2_RE = re.compile(r"^#{1,2}\s")
SPLIT_RE = re.compile(r"[；;、,，]")


def parse_list(path: Path) -> tuple[dict[str, list[str]], dict[str, list[str]], int]:
    """返回 (taught_terms, untaught_terms_by_kp, usable_rows)。"""
    taught: dict[str, list[str]] = {}
    untaught: dict[str, list[str]] = {}
    usable = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("- ") or "｜" not in line:
            continue
        segs = [s.strip() for s in line[2:].split("｜")]
        if len(segs) < 6:
            continue
        usable += 1
        name = segs[1]
        status_raw = segs[5] if len(segs) > 5 else ""
        status = STATUS_SPLIT_RE.sub("", status_raw).strip()
        for prefix in ("状态：", "状态:"):
            if status.startswith(prefix):
                status = status[len(prefix):].strip()
        terms: list[str] = []
        for seg in segs[6:]:
            if seg.startswith("引入") and ("：" in seg or ":" in seg):
                body = seg.split("：", 1)[1] if "：" in seg else seg.split(":", 1)[1]
                terms = [t.strip() for t in SPLIT_RE.split(body) if len(t.strip()) >= 2]
        if status == "已讲":
            taught[name] = terms
        else:
            untaught[f"{segs[0]} {name}"] = terms
    return taught, untaught, usable


def question_lines(text: str, scan_all: bool) -> list[tuple[int, str]]:
    """返回 (行号, 行文本)。默认只扫题面区；--scan-all 扫全文。"""
    out: list[tuple[int, str]] = []
    in_q = scan_all
    for i, line in enumerate(text.splitlines(), 1):
        if not scan_all:
            if QUESTION_SECTION_RE.match(line.strip()):
                in_q = True
                continue
            if in_q and ANY_H2_RE.match(line.strip()):
                in_q = False
        if in_q and line.strip():
            out.append((i, line))
    return out


def build_taught_set(taught: dict[str, list[str]]) -> set[str]:
    """已引入术语集合 = 已讲 KP 名称 ∪ 其引入列 ∪ 追加项（extras 以 __extra__* 键混入）。"""
    out: set[str] = set()
    for name, terms in taught.items():
        if not name.startswith("__extra__") and len(name) >= 2:
            out.add(name)
        out.update(t for t in terms if len(t) >= 2)
    return out


def check_files(taught_set: set[str], untaught: dict[str, list[str]],
                files: list[tuple[str, list[tuple[int, str]]]]) -> list[dict]:
    violations: list[dict] = []
    for fname, lines in files:
        for lineno, text in lines:
            for kp, terms in untaught.items():
                # 候选术语 = 该未讲 KP 的引入列 + 其名称本身（≥2 字才匹配）
                kp_name = kp.split(" ", 1)[1] if " " in kp else kp
                for term in [t for t in [kp_name, *terms] if len(t) >= 2]:
                    if term in text and term not in taught_set:
                        violations.append({
                            "file": fname, "line": lineno, "term": term, "untaught_kp": kp,
                            "excerpt": text.strip()[:60],
                        })
    # 同行同术语去重（KP 名称与引入列重复登记时只报一次）
    seen: set[tuple] = set()
    uniq = []
    for v in violations:
        key = (v["file"], v["line"], v["term"])
        if key not in seen:
            seen.add(key)
            uniq.append(v)
    return uniq


def _selftest() -> int:
    ok = True

    def chk(name: str, cond: bool):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok = ok and cond

    list_md = """# 课程体系：测试
- KP-01-01 ｜ 主语与谓语 ｜ 节 1 ｜ 前置：  ｜ 来源：p.3 ｜ 状态：已讲 ｜ 引入：谓语；主语
- KP-02-01 ｜ 定语从句 ｜ 节 2 ｜ 前置：KP-01-01 ｜ 来源：p.132 ｜ 状态：未讲 ｜ 引入：定语；先行词
- KP-02-02 ｜ 状语 ｜ 节 2 ｜ 前置： ｜ 来源：p.152 ｜ 状态：未讲（已会：摸底，2026-10-11）｜ 引入：状语
"""
    q_clean = "# 题\n\n## 题组\n1. 找出下句的主语与谓语：The dog runs.\n\n## 参考答案\n- 略\n"
    q_bad = "# 题\n\n## 题组\n1. 找出下句的主语、谓语，并指出定语是哪个词：The red dog runs.\n2. 主语与谓语各是什么？\n\n## 参考答案\n- 略\n"

    with tempfile.TemporaryDirectory() as td:
        lp = Path(td) / "课程体系.md"
        lp.write_text(list_md, encoding="utf-8")
        taught, untaught, usable = parse_list(lp)
        chk("usable rows = 3", usable == 3)
        chk("taught has 主语与谓语", "主语与谓语" in taught)
        chk("untaught has 2 KP", len(untaught) == 2)
        # 状态括注剥离：KP-02-02 带摸底括注仍按「未讲」计
        chk("括注剥离进 untaught", any("状语" in k for k in untaught))

        qp = Path(td) / "q_clean.md"
        qp.write_text(q_clean, encoding="utf-8")
        lines = question_lines(qp.read_text(encoding="utf-8"), scan_all=False)
        v = check_files(build_taught_set(taught), untaught, [("q_clean.md", lines)])
        chk("clean question → 0 violations", len(v) == 0)

        qp2 = Path(td) / "q_bad.md"
        qp2.write_text(q_bad, encoding="utf-8")
        lines2 = question_lines(qp2.read_text(encoding="utf-8"), scan_all=False)
        v2 = check_files(build_taught_set(taught), untaught, [("q_bad.md", lines2)])
        terms_hit = {x["term"] for x in v2}
        chk("bad question hits 定语", "定语" in terms_hit)
        chk("答案区不误扫（参考答案行不计）", all(x["line"] <= 5 for x in v2))
        chk("主语谓语（已讲）不报", "主语" not in terms_hit and "谓语" not in terms_hit)

        # --extra-terms：把「定语」补进已引入集合后变干净
        taught2 = dict(taught)
        taught2["__extra__定语"] = ["定语"]
        v3 = check_files(build_taught_set(taught2), untaught, [("q_bad.md", lines2)])
        chk("extra-terms 豁免定语", len(v3) == 0)

    print("SELFTEST OK" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="出题前术语对账（R46）")
    ap.add_argument("--list", required=False, help="课程体系.md 路径")
    ap.add_argument("--scan", action="append", default=[], help="待扫描的题组/讲义文件（可多次）")
    ap.add_argument("--extra-terms", default="", help="追加已引入术语（逗号/分号分隔）")
    ap.add_argument("--extra-file", default="", help="追加已引入术语文件（每行一个）")
    ap.add_argument("--scan-all", action="store_true", help="扫描全文而非仅题面区")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    if not args.list or not args.scan:
        print(json.dumps({"ok": False, "code": "E-USAGE", "message": "需要 --list 与 --scan"}), file=sys.stderr)
        return 2
    lpath = Path(args.list)
    if not lpath.is_file():
        print(json.dumps({"ok": False, "code": "E-LIST-MISSING", "message": str(lpath)}), file=sys.stderr)
        return 2
    taught, untaught, usable = parse_list(lpath)
    if usable == 0:
        print(json.dumps({"ok": False, "code": "E-LIST-EMPTY", "message": "清单零可用行"}), file=sys.stderr)
        return 2
    for t in SPLIT_RE.split(args.extra_terms):
        if len(t.strip()) >= 2:
            taught[f"__extra__{t.strip()}"] = [t.strip()]
    if args.extra_file:
        ef = Path(args.extra_file)
        if ef.is_file():
            for t in ef.read_text(encoding="utf-8").splitlines():
                t = t.strip()
                if len(t) >= 2:
                    taught[f"__extra__{t}"] = [t]

    files = []
    for sp in args.scan:
        p = Path(sp)
        if not p.is_file():
            print(json.dumps({"ok": False, "code": "E-SCAN-MISSING", "message": str(p)}), file=sys.stderr)
            return 2
        files.append((sp, question_lines(p.read_text(encoding="utf-8"), scan_all=args.scan_all)))

    violations = check_files(build_taught_set(taught), untaught, files)
    result = {
        "ok": not violations,
        "violations": violations,
        "taught_term_count": sum(len(v) for v in taught.values()) + len(taught),
        "scanned_files": [f[0] for f in files],
    }
    print(json.dumps(result, ensure_ascii=False))
    for v in violations[:20]:
        print(f"W-TERM-UNTAUGHT {v['file']}:{v['line']} 「{v['term']}」来自未讲 {v['untaught_kp']}", file=sys.stderr)
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
