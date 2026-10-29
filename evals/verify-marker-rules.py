#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""五要素新编号规则的行为契约校验脚本（stdlib-only、零网络、幂等只读）。

用途：
  对 5.10.0 五要素重编号（①题目 ②解析 ③答案框 ④易错 ⑤小结）引入的
  五项新规则做**行为级**机器验证：在临时目录构造讲义夹具，真实运行
  scripts/verify_explanation.py（子进程），断言其退出码与违规码输出。
  与 verify_explanation.py --selftest 的区别：selftest 走进程内函数调用，
  本脚本走完整 CLI 路径（含目录扫描与退出码语义），作为 E56–E60 的
  machine_ref 证据。不写任何仓库文件、不访问网络，可重复运行（幂等）。

检查项（5 组，共 19 项）：
  1. 旧编号写法不特判：
     完整旧格式、部分旧写法、「⑤ 卷面」均按普通缺项/框体例错误照报（E-REQ-MISSING 在列），
     混合讲义中新旧单元同一套判；
  2. W-MARKER-CONTENT（③ 标记行留空）：
     标记行带内容恰报 1 条 W 且不阻断（退出码 0）、加粗空标记不报、
     「③ 不适用（纯概念）：」后带说明不报；
  3. ⑤ 小结必检：
     缺 ⑤ 报 E-REQ-MISSING 且消息点名「⑤ 小结」、纯概念豁免不连带豁免 ⑤、
     纯概念补上 ⑤ 后零违规；
  4. 标记行行首锚定：
     正文提及「见 ③ 答案」不误判为标记行、有序列表（1. ①）识别、
     加粗列表标记识别；
  5. 多题单元答案框：
     一框按题号分段（（1）解：…）零违规、题号 + 占位答案报 E-BOX-EMPTY、
     每题一个「③ 答案（第 N 题）」框零违规、卡片布局（检验列表行 +
     单元内多 ③ 框）零违规。

退出码语义：
  0 = 全部检查通过；1 = 存在任何 FAIL。

用法：
  python -B evals/verify-marker-rules.py [--skill-root <技能根目录>]
  --skill-root 缺省取本脚本所在目录的上级目录（即技能根）。
"""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ── 夹具：完整有效讲义的公共骨架（草稿态，不触发定稿导读检查）──
HEAD = "# 第 1 节 · 示例\n- 状态：草稿（进行中）\n\n## 概念 1 · {title} 【本节最小必需】\n"

# 组 1 夹具：旧编号三种样态 + 混合讲义
FIX_LEGACY_FULL = HEAD.format(title="甲") + """- ① 目标：解方程。
- ② 分步：先算判别式。
- ③ 答案：$x=2$。
- ④ 易错：负号。
- ⑤ 标准答案(可整体誊抄):

> 题目：解方程 $x^2-4=0$。
>
> 解：$x^2=4$，$x=\\\\pm 2$。
"""

FIX_LEGACY_PARTIAL = HEAD.format(title="甲") + """- ① 题目：解方程。
- ② 分步：先算判别式。
- ③ 答案：$x=2$。
- ④ 易错：负号。
- ⑤ 标准答案:

> 解：$x^2=4$，$x=\\\\pm 2$。
"""

FIX_LEGACY_JUANMIAN = HEAD.format(title="甲") + """- ① 目标：解方程。
- ② 分步：先算判别式。
- ③ 答案：$x=2$。
- ④ 易错：负号。
- ⑤ 卷面:

> 解：$x^2=4$，$x=\\\\pm 2$。
"""

FIX_MIXED = (HEAD.format(title="旧") + """- ① 目标：解方程。
- ② 分步：先算判别式。
- ③ 答案：$x=2$。
- ④ 易错：负号。
- ⑤ 标准答案:

> 解：$x^2=4$，$x=\\\\pm 2$。

## 概念 2 · 新 【本节最小必需】
- ① 题目：二。
- ② 解析：三，得四。
- ③ 答案：

> 解:一步。

- ④ 易错：五。
""")

# 组 2 夹具：③ 标记行带内容 / 加粗空标记 / 豁免带说明
FIX_MARKER_CONTENT = HEAD.format(title="甲") + """- ① 题目：一。
- ② 解析：二，得三。
- ③ 答案：x=3。

> 解:一步。

- ④ 易错：四。
- ⑤ 小结：三步法。
"""

FIX_MARKER_BOLD = HEAD.format(title="甲") + """- ① 题目：一。
- ② 解析：二，得三。
- **③ 答案：**

> 解:一步。

- **④ 易错：**四。
- **⑤ 小结：**三步法。
"""

FIX_EXEMPT_NOTE = HEAD.format(title="甲") + """- ① 题目：认识记号的读法。
- ③ 不适用（纯概念）：只讲记号语义，无可复现产物。
- ④ 易错：读成两个符号。
- ⑤ 小结：一个符号，两次取值。
"""

# 组 3 夹具：缺 ⑤ / 纯概念无 ⑤ / 纯概念有 ⑤
FIX_NO_SUMMARY = HEAD.format(title="甲") + """- ① 题目：一。
- ② 解析：二，得三。
- ③ 答案：

> 解:一步。

- ④ 易错：四。
"""

FIX_EXEMPT_NO_SUMMARY = HEAD.format(title="甲") + """- ① 题目：认识记号的读法。
- ③ 不适用（纯概念）：只讲记号语义，无可复现产物。
- ④ 易错：读成两个符号。
"""

# FIX_EXEMPT_NOTE 即「纯概念有 ⑤」，复用。

# 组 4 夹具：正文提及 / 有序列表 / 加粗列表标记
FIX_MENTION = HEAD.format(title="甲") + """- ① 题目：一。
- ② 解析：关键步骤见 ③ 答案。
- ③ 答案：

> 解:一步。

- ④ 易错：四。
- ⑤ 小结：三步法。
"""

FIX_NUMBERED = HEAD.format(title="甲") + """1. ① 题目：一。
2. ② 解析：二，得三。
3. ③ 答案：

> 解:一步。

4. ④ 易错：四。
5. ⑤ 小结：三步法。
"""

# FIX_MARKER_BOLD 即「加粗列表标记」，复用。

# 组 5 夹具：一框按题号分段 / 题号占位 / 每题一框 / 卡片布局
FIX_QNUM_OK = HEAD.format(title="甲") + """- ① 题目：两道小题。
- ② 解析：第 (1) 题代入；第 (2) 题套通项。
- ③ 答案：

> (1) 答:B。

> (2) 解:由 $a_n=a_1+(n-1)d$ 代入得 $a_n=2n-9$。

- ④ 易错：代错首项。
- ⑤ 小结：代入、化简、写全。
"""

FIX_QNUM_PLACEHOLDER = HEAD.format(title="甲") + """- ① 题目：一。
- ② 解析：二，得三。
- ③ 答案：

> (1) 解:略。

- ④ 易错：四。
- ⑤ 小结：三步法。
"""

FIX_PERQ_BOXES = HEAD.format(title="甲") + """- ① 题目：两道小题。
- ② 解析：第 1 题代入；第 2 题套通项。
- ③ 答案（第 1 题）：

> 解:由 $a_n=a_1+(n-1)d$ 代入得 $a_n=2n-9$。

- ③ 答案（第 2 题）：

> 解:由 $a_n=a_1q^{n-1}$ 代入得 $a_5=162$。

- ④ 易错：代错首项。
- ⑤ 小结：代入、化简、写全。
"""

FIX_CARD = HEAD.format(title="甲") + """- ① 题目：本卡题型与分值。
- ② 解析：第一步判类型；第二步套公式。
- ④ 易错：把公差当公比。
- ⑤ 小结：判类型、套公式、代数据。
- 检验：①已知 $a_1=-7$、$d=2$，求 $a_n$。②已知 $a_1=2$、$q=3$，求 $a_5$。
- ③ 答案（第 1 题）：

> 解:由 $a_n=a_1+(n-1)d$ 代入，得 $a_n=2n-9$。

- ③ 答案（第 2 题）：

> 解:由 $a_n=a_1q^{n-1}$ 代入，得 $a_5=162$。
"""

# 违规行格式：[E] CODE file:line message
FINDING_RE = re.compile(r"^\[(E|W)\] ([A-Z][A-Z-]*) (.+?):(\d+) ", re.M)


class Checker:
    """逐项输出 [OK]/[FAIL] 行并累计计数。"""

    def __init__(self):
        self.ok = 0
        self.fail = 0

    def check(self, name, cond, detail=""):
        if cond:
            self.ok += 1
            print(f"[OK] {name}")
        else:
            self.fail += 1
            suffix = f"（{detail}）" if detail else ""
            print(f"[FAIL] {name}{suffix}")


class Runner:
    """在临时目录运行 verify_explanation.py 并缓存结果（幂等只读仓库）。"""

    def __init__(self, skill_root: Path):
        self.script = skill_root / "scripts" / "verify_explanation.py"
        self._cache = {}

    def run(self, name, content):
        if name in self._cache:
            return self._cache[name]
        with tempfile.TemporaryDirectory() as td:
            Path(td, name).write_text(content, encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-B", str(self.script), td],
                capture_output=True, text=True, encoding="utf-8")
        findings = FINDING_RE.findall(proc.stdout or "")
        result = {
            "exit": proc.returncode,
            "findings": findings,           # [(level, code, file, line)]
            "codes": [f[1] for f in findings],
            "stdout": proc.stdout or "",
        }
        self._cache[name] = result
        return result


def group1_legacy(rv: Runner, c: Checker) -> None:
    """组 1：旧编号写法不特判，按普通体例错误照报。"""
    r = rv.run("legacy_full.md", FIX_LEGACY_FULL)
    c.check("1.1 旧编号单元按普通缺项错误照报、退出码 1",
            r["exit"] == 1 and any(code == "E-REQ-MISSING" for code in r["codes"]),
            f"codes={r['codes']} exit={r['exit']}")
    r = rv.run("legacy_partial.md", FIX_LEGACY_PARTIAL)
    c.check("1.3 部分旧写法（⑤ 仍标准答案）同样按普通错误照报",
            any(code == "E-REQ-MISSING" for code in r["codes"]),
            f"codes={r['codes']}")
    r = rv.run("legacy_juanmian.md", FIX_LEGACY_JUANMIAN)
    c.check("1.4 旧标签「⑤ 卷面」同样不特判",
            any(code == "E-REQ-MISSING" for code in r["codes"]),
            f"codes={r['codes']}")
    r = rv.run("mixed.md", FIX_MIXED)
    c.check("1.5 混合讲义：新旧单元都按同一套体例错误判",
            any(code == "E-REQ-MISSING" for code in r["codes"]),
            f"codes={r['codes']}")


def group2_marker_content(rv: Runner, c: Checker) -> None:
    """组 2：③ 标记行留空。"""
    r = rv.run("marker_content.md", FIX_MARKER_CONTENT)
    c.check("2.1 ③ 标记行带内容恰报 1 条 W-MARKER-CONTENT",
            r["codes"].count("W-MARKER-CONTENT") == 1, f"codes={r['codes']}")
    c.check("2.2 仅 W 不阻断（退出码 0）", r["exit"] == 0, f"exit={r['exit']}")
    r = rv.run("marker_bold.md", FIX_MARKER_BOLD)
    c.check("2.3 加粗空标记（**③ 答案：**）不报 W",
            "W-MARKER-CONTENT" not in r["codes"], f"codes={r['codes']}")
    r = rv.run("exempt_note.md", FIX_EXEMPT_NOTE)
    c.check("2.4 「③ 不适用（纯概念）：」后带说明不报 W",
            "W-MARKER-CONTENT" not in r["codes"], f"codes={r['codes']}")


def group3_summary_required(rv: Runner, c: Checker) -> None:
    """组 3：⑤ 小结必检。"""
    r = rv.run("no_summary.md", FIX_NO_SUMMARY)
    c.check("3.1 缺 ⑤ 报 E-REQ-MISSING 且消息点名「⑤ 小结」",
            "E-REQ-MISSING" in r["codes"] and "⑤ 小结" in r["stdout"],
            f"codes={r['codes']}")
    r = rv.run("exempt_no_summary.md", FIX_EXEMPT_NO_SUMMARY)
    c.check("3.2 纯概念豁免不连带豁免 ⑤（仍报 E-REQ-MISSING）",
            "E-REQ-MISSING" in r["codes"] and "⑤ 小结" in r["stdout"],
            f"codes={r['codes']}")
    r = rv.run("exempt_note.md", FIX_EXEMPT_NOTE)
    c.check("3.3 纯概念补上 ⑤ 后零违规", r["codes"] == [] and r["exit"] == 0,
            f"codes={r['codes']} exit={r['exit']}")


def group4_line_anchor(rv: Runner, c: Checker) -> None:
    """组 4：标记行行首锚定。"""
    r = rv.run("mention.md", FIX_MENTION)
    c.check("4.1 正文提及「见 ③ 答案」不误判（零违规）",
            r["codes"] == [] and r["exit"] == 0,
            f"codes={r['codes']} exit={r['exit']}")
    r = rv.run("numbered.md", FIX_NUMBERED)
    c.check("4.2 有序列表标记（1. ① 题目）识别（零违规）",
            r["codes"] == [], f"codes={r['codes']}")
    r = rv.run("marker_bold.md", FIX_MARKER_BOLD)
    c.check("4.3 加粗列表标记识别（不报缺项）",
            "E-REQ-MISSING" not in r["codes"], f"codes={r['codes']}")


def group5_multiq(rv: Runner, c: Checker) -> None:
    """组 5：多题单元答案框。"""
    r = rv.run("qnum_ok.md", FIX_QNUM_OK)
    c.check("5.1 一框按题号分段（(1) 答:… / (2) 解:…）零违规",
            r["codes"] == [] and r["exit"] == 0,
            f"codes={r['codes']} exit={r['exit']}")
    r = rv.run("qnum_placeholder.md", FIX_QNUM_PLACEHOLDER)
    c.check("5.2 题号 + 占位答案仍报 E-BOX-EMPTY",
            "E-BOX-EMPTY" in r["codes"], f"codes={r['codes']}")
    r = rv.run("perq_boxes.md", FIX_PERQ_BOXES)
    c.check("5.3 每题一个「③ 答案（第 N 题）」框零违规",
            r["codes"] == [], f"codes={r['codes']}")
    r = rv.run("card.md", FIX_CARD)
    c.check("5.4 卡片布局（检验列表行 + 单元内多 ③ 框）零违规",
            r["codes"] == [] and r["exit"] == 0,
            f"codes={r['codes']} exit={r['exit']}")


def main(argv=None) -> int:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="五要素新编号规则行为契约校验")
    parser.add_argument("--skill-root", default=None,
                        help="技能根目录（缺省取本脚本上级目录）")
    args = parser.parse_args(argv)
    root = (Path(args.skill_root) if args.skill_root
            else Path(__file__).resolve().parent.parent)
    script = root / "scripts" / "verify_explanation.py"
    if not script.is_file():
        print(f"[FAIL] 未找到 {script}")
        return 1
    rv = Runner(root)
    c = Checker()
    group1_legacy(rv, c)
    group2_marker_content(rv, c)
    group3_summary_required(rv, c)
    group4_line_anchor(rv, c)
    group5_multiq(rv, c)
    print(f"\n共 {c.ok + c.fail} 项:OK {c.ok} 项,FAIL {c.fail} 项")
    return 0 if c.fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
