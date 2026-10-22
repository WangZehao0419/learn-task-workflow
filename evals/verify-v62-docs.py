#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-v62-docs.py - v6.2 文档型增强静态契约（stdlib-only、只读）。

检查的不是教学效果，而是“规则有没有真正写进对应分册”：
交接/学习记录/讲授证据、记忆写法纪律、ask hint、来源备课、选项与答案键规则、
版本字段与 eval 登记是否齐全。语义是否执行仍由模型/评审负责。
"""

import argparse
import json
from pathlib import Path

import sys


class Checker:
    def __init__(self):
        self.ok = 0
        self.fail = 0

    def check(self, name, cond, detail=""):
        if cond:
            self.ok += 1
            print("[OK] " + name)
        else:
            self.fail += 1
            print("[FAIL] " + name + (("：" + str(detail)) if detail else ""))


def read(root, rel):
    try:
        return (root / rel).read_text(encoding="utf-8")
    except OSError:
        return ""


def main(argv=None):
    parser = argparse.ArgumentParser(description="v6.2 文档型增强静态契约（只读）")
    parser.add_argument("--skill-root", default=None)
    args = parser.parse_args(argv)
    root = (Path(args.skill_root).resolve() if args.skill_root
            else Path(__file__).resolve().parent.parent)

    skill = read(root, "SKILL.md")
    data = read(root, "references/data-and-recovery.md")
    teaching = read(root, "references/teaching-loop.md")
    styles = read(root, "references/lecture-styles.md")
    phases = read(root, "references/phases-and-gates.md")
    credits = read(root, "CREDITS.md")
    setup = read(root, "references/setup-guide.md")
    deps = read(root, "skill-dependencies.json")
    evals_raw = read(root, "evals/evals.json")
    try:
        evals = json.loads(evals_raw)
    except (TypeError, ValueError):
        evals = {}

    c = Checker()
    c.check("1.1 SKILL.md 版本为 6.2.0", "version: 6.2.0" in skill)
    c.check("1.2 setup-guide 适用版本为 6.2.0", "适用版本：6.2.0" in setup)
    c.check("1.3 skill-dependencies 版本为 6.2.0", '"applies_to_version": "6.2.0"' in deps)
    c.check("1.4 CREDITS 当前版本说明为 6.2.0", "**当前版本说明**：6.2.0" in credits)
    c.check("1.5 evals 版本为 6.2.0", evals.get("applies_to_version") == "6.2.0")
    c.check("1.6 CREDITS 登记 DeepTutor 的 Apache-2.0 归因",
            "DeepTutor" in credits and "Apache-2.0" in credits
            and "未复制代码/正文/模板" in credits)

    c.check("2.1 学习进度含「本次交接」", "## 本次交接" in data)
    c.check("2.2 学习进度含「学习记录」", "## 学习记录" in data)
    c.check("2.3 学习进度含「讲授证据」", "## 讲授证据" in data)
    c.check("2.4 交接/记录/证据有分工与零迁移说明",
            all(k in data for k in ("本次交接", "学习记录", "讲授证据", "空更新合法", "v6.2", "零迁移")))
    c.check("2.5 记忆写法纪律已写入",
            all(k in data for k in ("记忆写法纪律", "≤120 字", "禁用绝对化词",
                                    "当前证据与当前表态优先", "无证据不写")))
    c.check("2.6 讲授证据只认已公开内容",
            all(k in data for k in ("已经公开讲给学习者", "讲授证据只证明", "不证明“学会”")))

    c.check("3.1 ask hint 已写入教学决策",
            all(k in teaching for k in ("ask hint", "不知道问什么时", "≤25 个汉字",
                                        "不是答案", "重复上一条已答")))
    c.check("3.2 来源备课与讲授证据已写入教学决策",
            all(k in teaching for k in ("来源备课与讲授证据", "最小来源包",
                                        "讲授 ≠ 掌握", "逐字引用")))
    c.check("3.3 选项打乱/字母中立/答案键规则已写入讲义规则",
            all(k in styles for k in ("选项打乱与字母中立", "答案键与解析纪律",
                                      "正确项不得更长", "不按正确性排序")))
    c.check("3.4 S3/S5 收尾已接上交接与学习记录",
            all(k in phases for k in ("节末交接", "本次交接", "学习记录", "讲授证据")))

    ids = {case.get("id") for case in evals.get("cases", []) if isinstance(case, dict)}
    c.check("4.1 evals 登记 E66–E69", {"E66", "E67", "E68", "E69"}.issubset(ids))

    print("verify-v62-docs: " + str(c.ok) + " checks, " + str(c.ok) + " OK, "
          + str(c.fail) + " FAIL")
    return 0 if c.fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
