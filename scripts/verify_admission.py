#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每批四条准入机检（只读、零网络、幂等、stdlib-only）。

规格 90 的用户故事 36 写着「每一批都有四条固定的准入条件（脚本自测、规则清单回归、
指针校验、续学验证），这样我不用每批重新发明验收方式」。在 9.21.26 之前，这四条只存在于
规格正文与 14 张已关闭实施票的票面里——`grep` 仓内文档零命中，施工者要验收得先考古。

本脚本把「文档写了四条」变成「文档写的那四条真的能跑」：

    E-ADMIT-MISSING    references/gates.md 里找不到「每批四条准入」节
    E-ADMIT-COUNT      准入条目数不等于 4（少一条 = 少一道关；多一条 = 有人偷偷加了口径）
    E-ADMIT-FIELD      某条缺「跑什么 / 判定 / 失败处置」三栏之一
    E-ADMIT-NOCMD      某条没有可执行命令（`python -B …`）
    E-ADMIT-RED        某条命令执行后 rc != 0

为什么命令要**真的跑**：文档里的验收清单最典型的腐烂方式不是被删，是命令里的脚本改了名
或参数变了，而正文一个字没动。只比对文本会全绿——那种绿是本仓反复吃过的假绿。所以每一条
都必须现场执行一次，rc=0 才算这条准入成立。

为什么条数必须**恰好 4**：这四条是「每批固定、不逐批重新发明」的承诺。允许 3 条或 5 条，
等于允许施工者按当批方便自行裁剪——那正是这条用户故事要消灭的东西。

用法：
    python -B scripts/verify_admission.py
    python -B scripts/verify_admission.py --selftest
    python -B scripts/verify_admission.py --root <技能根>
退出码：0 四条齐备且全部可执行；1 有缺口；2 用法错误。
"""
from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rule_contract import skill_root  # noqa: E402

GATES = "references/gates.md"
HEADING = "## 每批四条准入"
NEXT_HEADING_RE = re.compile(r"(?m)^## ")
EXPECTED = 4
# 条目既可以是「1. **标题**」的列表项，也可以是「### 1. 标题」的小节标题——
# 参考册用后者更可读，而列表项在票面与规格里更常见。两种都认，解析结果一致。
ITEM_RE = re.compile(r"(?m)^(?:#{2,4}\s*)?(\d+)\.\s*(?:\*\*(.+?)\*\*|([^\n*].*?))\s*$")
CMD_RE = re.compile(r"`(python\s+-B\s+[^`]+)`")
FIELDS = ("跑什么", "判定", "失败处置")


def read_section(root: Path):
    """返回 (section_text, why)。取不到返回 (None, 原因)。"""
    path = root / GATES
    if not path.is_file():
        return None, "%s 不存在" % GATES
    text = path.read_text(encoding="utf-8", errors="replace")
    start = text.find(HEADING)
    if start < 0:
        return None, "%s 里没有「%s」节" % (GATES, HEADING)
    nxt = NEXT_HEADING_RE.search(text, start + len(HEADING))
    end = nxt.start() if nxt else len(text)
    return text[start:end], None


def parse_items(section: str):
    """把一节切成条目：[(序号, 标题, 正文)]。"""
    marks = list(ITEM_RE.finditer(section))
    items = []
    for i, m in enumerate(marks):
        body_start = m.end()
        body_end = marks[i + 1].start() if i + 1 < len(marks) else len(section)
        title = (m.group(2) or m.group(3) or "").strip()
        items.append((int(m.group(1)), title, section[body_start:body_end]))
    return items


def run_cmd(root: Path, line: str):
    argv = [sys.executable, "-B"] + shlex.split(line)[2:]
    proc = subprocess.run(argv, cwd=str(root), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return proc.returncode


def check(root: Path, runner=None):
    """返回 (ok, problems, stats)。runner 可注入，供自测替换成假执行。"""
    problems = []
    stats = {"items": 0, "executed": 0}
    section, why = read_section(root)
    if section is None:
        problems.append(("E-ADMIT-MISSING", why))
        return False, problems, stats

    items = parse_items(section)
    stats["items"] = len(items)
    if len(items) != EXPECTED:
        problems.append(("E-ADMIT-COUNT",
                         "准入条目数 %d，应为 %d——这四条是「每批固定、不逐批重新发明」的承诺"
                         % (len(items), EXPECTED)))

    runner = runner or (lambda line: run_cmd(root, line))
    for num, title, body in items:
        missing = [f for f in FIELDS if f not in body]
        if missing:
            problems.append(("E-ADMIT-FIELD",
                             "第 %d 条「%s」缺栏：%s" % (num, title, "、".join(missing))))
        m = CMD_RE.search(body)
        if not m:
            problems.append(("E-ADMIT-NOCMD",
                             "第 %d 条「%s」没有可执行命令（要求形如 python -B …）"
                             % (num, title)))
            continue
        line = m.group(1).strip()
        rc = runner(line)
        stats["executed"] += 1
        if rc != 0:
            problems.append(("E-ADMIT-RED",
                             "第 %d 条「%s」的命令 rc=%d：%s" % (num, title, rc, line)))
    return not problems, problems, stats


def _selftest() -> int:
    """夹具用例：正例 + 缺节 + 条数不符 + 缺栏 + 无命令 + 命令失败。"""
    failures = []
    total = [0]

    def item(n, title, cmd="python -B scripts/a.py --selftest", fields=("跑什么", "判定", "失败处置")):
        body = "\n"
        body += "- **跑什么**：\n" if "跑什么" in fields else ""
        body += "- 命令：`%s`\n" % cmd
        body += "- **判定**：rc=0\n" if "判定" in fields else ""
        body += "- **失败处置**：停下修\n" if "失败处置" in fields else ""
        return "%d. **%s**%s" % (n, title, body)

    def build(items):
        return "\n" + HEADING + "\n\n" + "\n".join(items) + "\n\n## 下一节\n"

    def case(name, files, expect_ok, runner=None):
        total[0] += 1
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel, body in files.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body, encoding="utf-8")
            ok, problems, _st = check(root, runner=runner)
            if ok != expect_ok:
                failures.append("%s：期望 ok=%s，实得 ok=%s（%s）"
                                % (name, expect_ok, ok, problems[:2]))

    good_items = [item(i + 1, "第%d关" % (i + 1)) for i in range(EXPECTED)]
    case("四条齐备且可执行", {GATES: build(good_items)}, True, runner=lambda line: 0)

    case("缺整节", {GATES: "# 闸口册\n\n## 别的节\n"}, False, runner=lambda line: 0)

    case("只有三条", {GATES: build(good_items[:3])}, False, runner=lambda line: 0)

    case("多出一条", {GATES: build(good_items + [item(5, "第五条")])}, False,
         runner=lambda line: 0)

    bad_field = good_items[:]
    bad_field[1] = item(2, "第2关", fields=("跑什么", "判定"))
    case("缺「失败处置」栏", {GATES: build(bad_field)}, False, runner=lambda line: 0)

    no_cmd = good_items[:]
    no_cmd[2] = "3. **第3关**\n- **跑什么**：无\n- **判定**：rc=0\n- **失败处置**：停\n"
    case("某条没有命令", {GATES: build(no_cmd)}, False, runner=lambda line: 0)

    case("某条命令失败", {GATES: build(good_items)}, False, runner=lambda line: 1)

    # 小节标题形态（### 1. 标题）与列表形态必须等价解析
    heading_form = "\n" + HEADING + "\n\n" + "\n".join(
        "### %d. 第%d关\n- **跑什么**：命令\n- 命令：`python -B scripts/a.py --selftest`\n"
        "- **判定**：rc=0\n- **失败处置**：停\n" % (i + 1, i + 1) for i in range(EXPECTED)
    ) + "\n## 下一节\n"
    case("小节标题形态也可解析", {GATES: heading_form}, True, runner=lambda line: 0)

    for f in failures:
        print("FAIL " + f)
    print("%s 每批四条准入：%d 个用例" % ("PASS" if not failures else "FAIL", total[0]))
    return 0 if not failures else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="每批四条准入机检")
    ap.add_argument("--selftest", action="store_true", help="跑内置用例再检查真实树")
    ap.add_argument("--root", default=None, help="技能根（默认脚本所在仓库）")
    args = ap.parse_args(argv)

    if args.selftest:
        rc = _selftest()
        if rc:
            return rc

    root = Path(args.root) if args.root else skill_root()
    ok, problems, stats = check(root)
    if not ok:
        for code, detail in problems:
            print("FAIL [%s] %s" % (code, detail))
        return 1
    print("PASS 每批四条准入：%d 条齐备，%d 条命令全部 rc=0" % (stats["items"], stats["executed"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
