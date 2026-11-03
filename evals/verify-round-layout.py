#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付轮版式行为测试（stdlib-only、只读、幂等）。

对 `evals/fixtures/round-layout/*.md` 逐份检查学员可见文本是否命中
`references/teaching/round-layout.md`「交付轮版式」与 SKILL.md 硬规则 11
的地板：轮型名/状态锚点、轮首句段句上限与禁词、题卡与提交格式、重发形态、
自造记号、编号裸用。夹具头部用

    <!-- round-layout: kind=task|summary|resend -->
    <!-- expect: E-ROUND-JARGON,W-ROUND-PREAMBLE-LONG -->

声明类型与期望码集；脚本做**精确集合比对**（多报、漏报都算失败）。
不写仓库文件、不访问网络，可重复运行。
"""
import argparse
import json
import re
import sys
from pathlib import Path

FIXTURE_DIR = "evals/fixtures/round-layout"
KIND_RE = re.compile(r"<!--\s*round-layout:\s*kind=([a-z]+)\s*-->")
EXPECT_RE = re.compile(r"<!--\s*expect:\s*([^>]*?)-->")
TASK_LINE_RE = re.compile(r"^\s*\*\*题\s*[0-9]+\*\*")
TASK_ANY_RE = re.compile(r"^\s*(?:\*\*)?题\s*[0-9]+")
SUMMARY_RE = re.compile(r"^\s*\*\*本节小结\*\*")
TYPE_WORDS = ("续学", "清债", "讲授轮", "反馈轮", "提示轮", "路线轮", "状态轮",
              "交付轮", "出题轮", "开场轮", "收尾轮", "重发轮")
FIELD_WORDS = ("信心", "正确性", "作答", "日期")


def _strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", " ", text)


def _strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def _blocks(text: str) -> int:
    return len([b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()])


def _sentences(text: str) -> int:
    n = len(re.findall(r"[。！？!?]", text))
    return n if n else (1 if text.strip() else 0)


def _opening(text: str) -> tuple:
    """返回 (轮首区, 主体)。主体从首个题行/小结行起。"""
    lines = text.split("\n")
    start = 0
    for i, line in enumerate(lines):
        if TASK_ANY_RE.match(line) or SUMMARY_RE.match(line):
            start = i
            break
    else:
        start = len(lines)
    return "\n".join(lines[:start]), "\n".join(lines[start:])


def _first_task_chars(body: str) -> int:
    for line in body.split("\n"):
        if TASK_LINE_RE.match(line):
            return len(re.sub(r"\s", "", line))
    return 0


def check_fixture(path: Path, cfg: dict) -> tuple:
    raw = path.read_text(encoding="utf-8", errors="replace")
    kind_m = KIND_RE.search(raw)
    kind = kind_m.group(1) if kind_m else "task"
    expect_m = EXPECT_RE.search(raw)
    expect = set()
    if expect_m:
        expect = {x.strip() for x in expect_m.group(1).split(",") if x.strip()}

    text = _strip_comments(raw)
    plain = _strip_code(text)
    opening, body = _opening(plain)
    codes = set()

    if not all(k in cfg for k in ("opening_blocks_max", "opening_sentences_max",
                                  "ban_words_opening", "ban_words_body")):
        return {"E-ROUND-CONST"}, expect

    # 1 轮型名 / 状态锚点（轮首区）
    if any(w in opening for w in TYPE_WORDS):
        codes.add("E-ROUND-TYPE-NAME")

    # 2 轮首句段句上限；含「清」必须含「条」
    if _blocks(opening) > cfg["opening_blocks_max"] or _sentences(opening) > cfg["opening_sentences_max"]:
        codes.add("E-ROUND-OPENING")
    if "清" in opening and "条" not in opening:
        codes.add("E-ROUND-OPENING")

    # 3 禁词：轮首区全表、正文窄表
    if any(w.lower() in opening.lower() for w in cfg["ban_words_opening"]):
        codes.add("E-ROUND-JARGON")
    if any(w.lower() in body.lower() for w in cfg["ban_words_body"]):
        codes.add("E-ROUND-JARGON")

    # 4 题卡与提交格式
    if kind == "task":
        if not TASK_LINE_RE.search(body):
            codes.add("E-ROUND-CARD")
        if re.search(r"题\s*[0-9]+\s*　", plain):
            codes.add("E-ROUND-CARD")
        if not re.search(r"信心分", body) or not re.search(r"1[–-]5", body):
            codes.add("E-ROUND-CARD")
    elif kind == "summary":
        if not SUMMARY_RE.search(body):
            codes.add("E-ROUND-CARD")

    # 5 重发不得重念开场
    if kind == "resend":
        if opening.strip() or any(w in plain for w in ("今天清", "记录才", "先练它")):
            codes.add("E-ROUND-RESEND")

    # 6 记号位：竖线全文禁；等号只在台账上下文报
    if "｜" in plain:
        codes.add("E-ROUND-MARK")
    for line in plain.split("\n"):
        if "=" in line and ("｜" in line or any(w in line for w in FIELD_WORDS)):
            codes.add("E-ROUND-MARK")
            break

    # 7 编号裸用（成对名称合法）
    if re.search(r"第\s*[0-9]+(?:\s*/\s*[0-9]+)?\s*目(?!「)", plain) or re.search(r"目\s*=\s*[0-9]+(?!「)", plain):
        codes.add("E-ROUND-JARGON")

    # 8 轮首铺垫相对长度（W，不拦截）
    first = _first_task_chars(body)
    if first and len(re.sub(r"\s", "", opening)) > first:
        codes.add("W-ROUND-PREAMBLE-LONG")

    return codes, expect


def _selftest(root: Path, cfg: dict) -> int:
    """对正例做定点变异，断言检查项真的会命中（防脚本退化为空跑）。"""
    import tempfile

    base = (root / FIXTURE_DIR / "positive-task.md").read_text(encoding="utf-8")
    resend = (root / FIXTURE_DIR / "positive-resend.md").read_text(encoding="utf-8")
    cases = [
        ("type-name", base.replace("今天清", "**续学**｜今天清"), "E-ROUND-TYPE-NAME"),
        ("jargon", base.replace("先练它。", "先练它，台账对一下。"), "E-ROUND-JARGON"),
        ("card", base.replace("**题 1**", "题 1　"), "E-ROUND-CARD"),
        ("mark", base.replace("先练它。", "先练它｜按顺序。"), "E-ROUND-MARK"),
        ("resend", resend.replace("**题 1**", "今天清 1 条。\n\n**题 1**"), "E-ROUND-RESEND"),
        ("opening", base.replace("今天清 2 条；", "今天清 2 条。补充一句。第二句。"), "E-ROUND-OPENING"),
    ]
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        for name, text, code in cases:
            p = Path(td) / (name + ".md")
            p.write_text(text, encoding="utf-8")
            got, _ = check_fixture(p, cfg)
            if code in got:
                print("[OK] selftest %s -> %s" % (name, code))
            else:
                bad += 1
                print("[FAIL] selftest %s 未命中 %s（actual=%s）"
                      % (name, code, ",".join(sorted(got)) or "(none)"))
    return 0 if bad == 0 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="交付轮版式夹具校验（只读）")
    ap.add_argument("--skill-root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--selftest", action="store_true", help="仅验证自身可解析")
    args = ap.parse_args(argv)
    root = Path(args.skill_root).resolve()
    contract = root / "contracts" / "rules.json"
    if not contract.exists():
        print("E-ROUND-CONST: contracts/rules.json 不存在")
        return 2
    try:
        cfg = json.loads(contract.read_text(encoding="utf-8")).get("constants", {}).get("round_layout", {})
    except (OSError, ValueError) as exc:
        print("E-ROUND-CONST: contracts/rules.json 读取失败（%s）" % exc)
        return 2
    fdir = root / FIXTURE_DIR
    if not fdir.is_dir():
        print("E-ROUND-CONST: 夹具目录不存在 %s" % FIXTURE_DIR)
        return 2
    files = sorted(fdir.glob("*.md"))
    if not files:
        print("E-ROUND-CONST: 夹具为空")
        return 2
    if args.selftest:
        return _selftest(root, cfg)
    bad = 0
    for path in files:
        got, want = check_fixture(path, cfg)
        if got == want:
            print("[OK] %s" % path.name)
        else:
            bad += 1
            print("[FAIL] %s" % path.name)
            print("  expect: %s" % (",".join(sorted(want)) or "(none)"))
            print("  actual: %s" % (",".join(sorted(got)) or "(none)"))
            print("  extra : %s" % (",".join(sorted(got - want)) or "-"))
            print("  missed: %s" % (",".join(sorted(want - got)) or "-"))
    print("%d fixtures, %d OK, %d FAIL" % (len(files), len(files) - bad, bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
