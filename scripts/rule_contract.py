#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规则常量加载器（stdlib-only，纯常量）。

契约固定为 <技能根>/contracts/rules.json，只承载两件事：**结构版本** 与 **业务常量**。
七个确定性脚本与行为脚本从这里读判分、调度、续学、排印所需的枚举与阈值；
读取失败时 fail closed——调用方不得退回内置默认值继续跑。

契约里不再有场景注册表、意图登记、文件清单、规则编号登记或退役编号表；
那些只服务索引的编译关系已随编译层一起退役。

--selftest 覆盖：真实契约可加载、缺文件、空文件、非法 JSON、缺键、枚举重复、比例非法、
kp.judge（目行判定三字段的枚举与日期上限）缺失或越界；以及**两处 schema 声明必须相等**
——登记表 contracts/scripts-contract.json 里本脚本那条的 schema 与本文件的常量 SCHEMA——
含「只改其中一处就红、还原就绿」的变异用例，与「索引侧 learn-task-index/7 不参与相等」的反例。

红线凭据结构（票 96）是 constants 下的两个**平行块**，不进 REQUIRED_CONST——加字段不会让旧
契约报错，缺这个块也不是错（阶段性对象）：

    redlines: { "<线号>": { "title": …, "criteria": [ {key, order, evidence,
                                                     coverage, decision_layer,
                                                     cannot_infer} … ] } }
    sources:  { "<出处 id>": { "table": "CREDITS.md", "section": … } }

子判据用**双层键**：语义标识 `R<线号>.<slug>`（定下不得再改）+ 顺序号 `order`（可重排）。
语义标识**不得派生自位置**——纯数字 slug 一律判非法，否则重排一次就能让一条规则被另一条
顶替，而数量不变、硬闸静默放行。

出处外键**双向**校验：正向是硬错——凭据引用了 sources 里没有的 id 即 E-EVIDENCE-REF-MISSING；
反向是检出——sources 里没有任何子判据引用的条目由 orphan_sources() 报出来（`--redlines`
与 `--redline-keys` 都会显示）。反向**不判硬错**：容器先于内容落地，票 98 才填凭据正文，
此刻 23 条出处必然全部未被引用；把它设成硬错会让契约在整个重写期不可加载，等于用闸口
堵死自己的施工顺序。

票 98 往容器里填了内容，并把两条体例约束变成会红的断言：

    E-REDLINE-SEGMENT-MISSING  四段（凭据/覆盖/判定层/不能推出）缺任一段即红
    E-REDLINE-SEGMENT-OVER     四段合计字符数 > REDLINE_SEGMENT_LIMIT（400）即红
    E-SKILL-REDLINE-BUDGET     SKILL.md 红线节字符数 > SKILL_REDLINE_SECTION_LIMIT（5000）即红

字符数的算法写死在这里，不留解释空间：**四段合计** = coverage + decision_layer +
cannot_infer + 出处外键（按 `、` 连接）的字符数，判据原文不计。**红线节** = 从
`## 十一条教学红线` 那一行起、到下一个二级标题之前为止（含标题行，行间换行计 1 字符）。

为什么「上界写死在契约里」而不是写死在 SKILL.md 里：判据自足 ≠ 判定自足。入口只放判据，
体例预算与凭据正文在契约里，两者由同一处常量收口，才不会出现「文档写 400、代码没拦」的漂移。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA = "ltw-rules/3"
# schema 声明在仓里有两处必然相等的副本（票 91）：本文件的 SCHEMA，与登记表
# contracts/scripts-contract.json 里 rule_contract.py 那条的 schema。这对副本漂移过很久
# 且没人发现——validate() 只查被加载的契约，查不到登记表里的那一处。
SCHEMA_REGISTRY_SCRIPT = "rule_contract.py"
# 只有 rule_contract.py 可以声明 ltw-rules/ 家族。同一份登记表里的 learn-task-index/7
# 是索引产物版本，语义不同，**不要求相等**，也不得被这条判据一并抹平。
SCHEMA_FAMILY = "ltw-rules/"
# 必填键收窄为结构版本与常量两组
REQUIRED_TOP = ("schema", "version", "constants")
# 七个确定性脚本与行为脚本实际消费的业务常量键
REQUIRED_CONST = (
    "phases", "types", "subject_families", "group_slugs", "discipline_slugs",
    "review_origin_phases", "grading", "kp", "gates", "restatement",
    "budget", "schemas", "headings", "scheduler", "errors",
)
# 红线凭据结构的字段与键形态（票 96）。
# slug 必须以小写字母开头——纯数字（R1.1）会被这里挡住，这是「语义标识不得派生自位置」
# 的机器判据，不是命名风格建议。
REDLINE_FIELDS = ("key", "order", "evidence", "coverage", "decision_layer",
                  "cannot_infer")
REDLINE_KEY_RE = re.compile(r"^R(?P<line>[1-9][0-9]*)\.(?P<slug>[a-z][a-z0-9]*(?:-[a-z0-9]+)*)$")
SOURCE_FIELDS = ("table", "section")
# 票 42 Q7：每条子判据的「凭据 + 覆盖 + 判定层 + 不能推出」四段合计 ≤400 字符。
# 票 42/49/52 的算术：11 条判据正文约 3.2k 字符已占掉入口预算，四段 11×400 塞进去必然
# 撑破 5,000 字符上限，所以四段只能住契约——这里把它变成会红的断言，而不是文档里的一句话。
REDLINE_SEGMENT_LIMIT = 400
# 票 42 Q7：红线节（`## 十一条教学红线` 到下一个二级标题）合计 ≤5,000 字符。
# SKILL.md 是**被重写对象**，它的预算由契约侧的只读检查来断言，不让被测方给自己打分。
SKILL_MD = "SKILL.md"
REDLINE_SECTION_HEAD = "## 十一条教学红线"
SKILL_REDLINE_SECTION_LIMIT = 5000
REDLINE_SEGMENT_TEXT_FIELDS = ("coverage", "decision_layer", "cannot_infer")
# 凭据段（票 42 A 段）是**两样东西**：凭据类型 E1–E6（这一条有多硬）与出处外键
# R<批>-<n>（硬到哪一步有原始文献）。两者都进 evidence，因为它俩是同一段的两个坐标：
# 只写类型会退化成「我觉得算工程约定」，只写出处又答不出「有没有实验」。
# E6 不是「弱」：它是「不可用实验裁决」，价值立场一旦定下，约束力与 E1 同级——这句必须
# 落在代码旁边，否则下游会把 E6 当可豁免项。未在下面的白名单里的类型串一律按孤儿引用判红，
# 这样「凭据分级」不允许随手编一个新等级出来。
REDLINE_EVIDENCE_TIERS = ("E1", "E2", "E3", "E4", "E5", "E6")


class ContractError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__("%s: %s" % (code, message))


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_path() -> Path:
    return skill_root() / "contracts" / "rules.json"


def _fail(code: str, msg: str) -> None:
    raise ContractError(code, msg)


def _require(cond: bool, code: str, msg: str) -> None:
    if not cond:
        _fail(code, msg)


def _dup(values) -> list:
    seen, dup = set(), []
    for v in values:
        if v in seen:
            dup.append(v)
        seen.add(v)
    return dup


def schema_declarations_mismatch(data: dict) -> "str | None":
    """两处必须相等的 schema 声明：登记表里 rule_contract.py 的 schema 与代码常量 SCHEMA。

    判据（票 91）：
      ① 登记表里必须有一条 rule_contract.py，且它的 schema == SCHEMA；
      ② ltw-rules/ 家族只允许 rule_contract.py 声明——别的脚本也声明 ltw-rules/*
         说明有人在把第三处一并抹平，必须红；
      ③ 其余 schema（如索引侧的 learn-task-index/7）是另一套产物版本，**不参与**比较：
         它们可以自由变化，不得被本判据收编。

    返回 None 表示通过，否则返回人读差异。本函数只读、不写盘、不联网。
    """
    entries = data.get("scripts_contract")
    if not isinstance(entries, list):
        return "登记表缺 scripts_contract 数组"
    declared = None
    outsiders = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        schema = entry.get("schema")
        if not (isinstance(schema, str) and schema.strip()):
            continue
        if entry.get("script") == SCHEMA_REGISTRY_SCRIPT:
            declared = schema
        elif schema.startswith(SCHEMA_FAMILY):
            outsiders.append("%s=%r" % (entry.get("script"), schema))
    if declared is None:
        return "登记表缺 %s 的 schema 声明" % SCHEMA_REGISTRY_SCRIPT
    if declared != SCHEMA:
        return "登记表 %r ≠ 代码常量 %r" % (declared, SCHEMA)
    if outsiders:
        return "ltw-rules 家族被第三处声明：%s" % "、".join(outsiders)
    return None


def validate(data: dict) -> dict:
    _require(isinstance(data, dict), "E-CONTRACT-INVALID", "契约顶层必须是对象")
    for k in REQUIRED_TOP:
        _require(k in data, "E-CONTRACT-INVALID", "契约缺少顶层键 %s" % k)
    _require(data["schema"] == SCHEMA, "E-CONTRACT-INVALID",
             "契约 schema 必须是 %s（实际 %r）" % (SCHEMA, data["schema"]))
    _require(isinstance(data["version"], str) and data["version"].strip(),
             "E-CONTRACT-INVALID", "version 必须是非空字符串")

    c = data["constants"]
    _require(isinstance(c, dict), "E-CONTRACT-INVALID", "constants 必须是对象")
    for k in REQUIRED_CONST:
        _require(k in c, "E-CONTRACT-INVALID", "constants 缺少 %s" % k)

    for key in ("phases", "types", "subject_families", "review_origin_phases",
                "discipline_slugs"):
        _require(isinstance(c[key], list) and c[key],
                 "E-CONTRACT-INVALID", "%s 必须是非空数组" % key)
        _require(not _dup(c[key]), "E-CONTRACT-INVALID",
                 "%s 有重复值：%s" % (key, _dup(c[key])))

    gs = c["group_slugs"]
    _require(isinstance(gs, dict) and gs, "E-CONTRACT-INVALID", "group_slugs 必须是非空对象")
    for gk, gv in gs.items():
        _require(isinstance(gv, str) and gv, "E-CONTRACT-INVALID",
                 "group_slugs.%s 必须是非空字符串" % gk)
    _require(not _dup(list(gs.values())), "E-CONTRACT-INVALID", "group_slugs 值有重复")
    _require(set(gs) == set(c["subject_families"]), "E-CONTRACT-INVALID",
             "group_slugs 键集必须与 subject_families 一致")

    g = c["grading"]
    _require(isinstance(g.get("values"), list) and len(g["values"]) == 4,
             "E-CONTRACT-INVALID", "grading.values 必须是四态")
    _require(not _dup(g["values"]), "E-CONTRACT-INVALID", "grading.values 有重复")

    kp = c["kp"]
    for key in ("states", "types", "visual_tasks"):
        _require(isinstance(kp.get(key), list) and kp[key],
                 "E-CONTRACT-INVALID", "kp.%s 必须是非空数组" % key)
        _require(not _dup(kp[key]), "E-CONTRACT-INVALID", "kp.%s 有重复" % key)

    # 目行判定三字段（票 81 决议）：枚举与上限从契约取，解析器不得内置默认值。
    judge = kp.get("judge")
    _require(isinstance(judge, dict), "E-CONTRACT-INVALID", "kp.judge 必须是对象")
    for key in ("values",):
        _require(isinstance(judge.get(key), list) and judge[key],
                 "E-CONTRACT-INVALID", "kp.judge.%s 必须是非空数组" % key)
        _require(not _dup(judge[key]), "E-CONTRACT-INVALID", "kp.judge.%s 有重复" % key)
    _require(isinstance(judge.get("max_dates"), int) and judge["max_dates"] >= 1,
             "E-CONTRACT-INVALID", "kp.judge.max_dates 必须是 ≥1 的整数")
    _require(isinstance(judge.get("pointer_prefix"), str) and judge["pointer_prefix"].strip(),
             "E-CONTRACT-INVALID", "kp.judge.pointer_prefix 必须是非空字符串")
    _require(isinstance(judge.get("pointer_sep"), str) and judge["pointer_sep"].strip(),
             "E-CONTRACT-INVALID", "kp.judge.pointer_sep 必须是非空字符串")

    for key in ("min_ratio", "final_ratio"):
        val = c["gates"].get(key)
        _require(isinstance(val, list) and len(val) == 2
                 and all(isinstance(x, int) for x in val),
                 "E-CONTRACT-INVALID", "gates.%s 必须是 [a,b] 整数" % key)
        _require(0 < val[0] <= val[1], "E-CONTRACT-INVALID",
                 "gates.%s 必须满足 0 < a <= b" % key)

    for key in ("budget", "schemas", "headings", "scheduler", "restatement"):
        _require(isinstance(c[key], dict) and c[key],
                 "E-CONTRACT-INVALID", "%s 必须是非空对象" % key)

    errs = c["errors"]
    _require(isinstance(errs, dict) and errs, "E-CONTRACT-INVALID", "errors 必须是非空对象")
    for level in ("E", "W"):
        _require(isinstance(errs.get(level), list), "E-CONTRACT-INVALID",
                 "errors.%s 必须是数组" % level)
        _require(not _dup(errs[level]), "E-CONTRACT-INVALID", "errors.%s 有重复" % level)

    _validate_redlines(c)
    return data


def _validate_redlines(c: dict) -> None:
    """校验 redlines / sources 两块的形态与双向外键。

    两块要么都在、要么都不在——只出现一块说明有人在半途改契约，此时任何一侧的判定
    都不可信，直接 fail closed。
    """
    has_red, has_src = "redlines" in c, "sources" in c
    if not has_red and not has_src:
        return
    _require(has_red and has_src, "E-CONTRACT-INVALID",
             "redlines 与 sources 必须成对出现（redlines=%s / sources=%s）"
             % (has_red, has_src))

    reds, srcs = c["redlines"], c["sources"]
    _require(isinstance(reds, dict) and reds, "E-CONTRACT-INVALID", "redlines 必须是非空对象")
    _require(isinstance(srcs, dict), "E-CONTRACT-INVALID", "sources 必须是对象")

    for sid, sv in srcs.items():
        _require(isinstance(sv, dict), "E-CONTRACT-INVALID", "sources.%s 必须是对象" % sid)
        for f in SOURCE_FIELDS:
            _require(isinstance(sv.get(f), str) and sv[f].strip(), "E-CONTRACT-INVALID",
                     "sources.%s.%s 必须是非空字符串" % (sid, f))

    # 线号：十进制字符串，从 1 起连续、不缺不重
    for k in reds:
        _require(isinstance(k, str) and k.isdigit() and int(k) >= 1, "E-CONTRACT-INVALID",
                 "redlines 的线号必须是 ≥1 的十进制字符串（实际 %r）" % (k,))
    nums = sorted(int(k) for k in reds)
    _require(nums == list(range(1, len(nums) + 1)), "E-CONTRACT-INVALID",
             "redlines 线号必须从 1 起连续（实际 %s）" % nums)

    seen_keys = {}
    for num in nums:
        line = reds[str(num)]
        _require(isinstance(line, dict), "E-CONTRACT-INVALID", "redlines.%d 必须是对象" % num)
        _require(isinstance(line.get("title"), str) and line["title"].strip(),
                 "E-CONTRACT-INVALID", "redlines.%d.title 必须是非空字符串" % num)
        crits = line.get("criteria")
        _require(isinstance(crits, list) and crits, "E-CONTRACT-INVALID",
                 "redlines.%d.criteria 必须是非空数组" % num)

        orders = []
        for ct in crits:
            _require(isinstance(ct, dict), "E-CONTRACT-INVALID",
                     "redlines.%d 的子判据必须是对象" % num)
            for f in REDLINE_FIELDS:
                _require(f in ct, "E-CONTRACT-INVALID",
                         "redlines.%d 有子判据缺字段 %s" % (num, f))
            key = ct["key"]
            _require(isinstance(key, str), "E-CONTRACT-INVALID",
                     "redlines.%d 的 key 必须是字符串" % num)
            m = REDLINE_KEY_RE.match(key)
            _require(m is not None, "E-CONTRACT-INVALID",
                     "子判据 key %r 不是 R<线号>.<slug> 形态；slug 必须以小写字母起头——"
                     "纯序号（如 R1.1）把位置当身份，重排即静默顶替" % (key,))
            _require(int(m.group("line")) == num, "E-CONTRACT-INVALID",
                     "子判据 %s 的线号与所在的 redlines.%d 不符" % (key, num))
            _require(key not in seen_keys, "E-CONTRACT-INVALID",
                     "子判据 key 重复：%s（%s 与 %s）" % (key, seen_keys.get(key), num))
            seen_keys[key] = "%d" % num

            order = ct["order"]
            _require(isinstance(order, int) and not isinstance(order, bool) and order >= 1,
                     "E-CONTRACT-INVALID", "%s.order 必须是 ≥1 的整数" % key)
            orders.append(order)

            ev = ct["evidence"]
            _require(isinstance(ev, list), "E-CONTRACT-INVALID", "%s.evidence 必须是数组" % key)
            tiers = [ref for ref in ev if isinstance(ref, str)
                     and ref in REDLINE_EVIDENCE_TIERS]
            _require(tiers, "E-EVIDENCE-REF-MISSING",
                     "%s 的凭据段没有凭据类型（E1–E6 一个都没有，无法判断这一条有多硬）" % key)
            for ref in ev:
                if isinstance(ref, str) and ref in REDLINE_EVIDENCE_TIERS:
                    continue
                _require(isinstance(ref, str) and ref in srcs, "E-EVIDENCE-REF-MISSING",
                         "%s 引用了 sources 里不存在的出处 %r（孤儿引用）" % (key, ref))
            for f in REDLINE_SEGMENT_TEXT_FIELDS:
                _require(isinstance(ct[f], str), "E-CONTRACT-INVALID",
                         "%s.%s 必须是字符串" % (key, f))

            # 四段体例（票 98）：缺一段即红，超 400 字符即红。既不做成「警告」也不做成
            # 「可选」——可选等于永远没人填，这是本仓在「契约首版留空」上已经交过的学费。
            # 凭据段的「空」由上面的类型检查先兜住（没有 E1–E6 就是 E-EVIDENCE-REF-MISSING），
            # 这里只管另外三段——留一个永远够不着的分支，等于留一处没人验证过的判据。
            empty = [f for f in REDLINE_SEGMENT_TEXT_FIELDS if not ct[f].strip()]
            _require(not empty, "E-REDLINE-SEGMENT-MISSING",
                     "%s 的四段没写全，缺：%s（凭据/覆盖/判定层/不能推出缺一不可）"
                     % (key, "、".join(empty)))
            seg_len = redline_segment_length(ct)
            _require(seg_len <= REDLINE_SEGMENT_LIMIT, "E-REDLINE-SEGMENT-OVER",
                     "%s 的四段合计 %d 字符 > 上限 %d（判据原文不计；超出即把研究笔记搬进契约）"
                     % (key, seg_len, REDLINE_SEGMENT_LIMIT))

        _require(sorted(orders) == list(range(1, len(orders) + 1)), "E-CONTRACT-INVALID",
                 "redlines.%d 的 order 必须是 1..%d 的一个排列（实际 %s）"
                 % (num, len(orders), orders))


def redlines_of(data: dict) -> dict:
    return data["constants"].get("redlines") or {}


def redline_keys(data: dict) -> list:
    """语义标识全集（冻结基准：键集合相等即通过）。"""
    return sorted(ct["key"] for line in redlines_of(data).values()
                  for ct in line["criteria"])


def redline_fingerprint(data: dict) -> str:
    """内容指纹：只用于「变了就告警」，不当硬闸——重写期每批都会改内容。"""
    canon = json.dumps(redlines_of(data), ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def orphan_sources(data: dict) -> list:
    """反向校验：sources 里没有任何子判据引用的条目（检出，不判硬错）。"""
    srcs = data["constants"].get("sources") or {}
    used = {ref for line in redlines_of(data).values()
            for ct in line["criteria"] for ref in ct["evidence"]}
    return sorted(set(srcs) - used)


def redline_segment_text(ct: dict) -> str:
    """四段的人读正文：覆盖 + 判定层 + 不能推出 + 出处外键（判据原文不计）。"""
    parts = [ct.get(f, "") if isinstance(ct.get(f), str) else ""
             for f in REDLINE_SEGMENT_TEXT_FIELDS]
    ev = ct.get("evidence")
    parts.append("、".join(ev) if isinstance(ev, list) else "")
    return "".join(parts)


def redline_segment_length(ct: dict) -> int:
    return len(redline_segment_text(ct))


def skill_redline_section(skill_md, head=REDLINE_SECTION_HEAD) -> "str | None":
    """截出 SKILL.md 的红线节：从 head 那一行起，到下一个二级标题之前。

    找不到 head 返回 None（调用方必须把它当红——找不到锚点的预算检查是假绿）。
    """
    lines = Path(skill_md).read_text(encoding="utf-8").split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.startswith(head):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end])


def skill_redline_section_chars(skill_md, head=REDLINE_SECTION_HEAD) -> "int | None":
    sec = skill_redline_section(skill_md, head)
    return None if sec is None else len(sec)


def skill_redline_section_violation(root: Path | None = None) -> "str | None":
    """红线节字符数超预算、或锚点缺失时返回人读说明；通过返回 None。只读。"""
    base = Path(root) if root is not None else skill_root()
    p = base / SKILL_MD
    try:
        chars = skill_redline_section_chars(p)
    except OSError as e:
        return "红线节预算检查读不到 %s：%s" % (SKILL_MD, e)
    if chars is None:
        return "%s 里找不到红线节锚点 %r（找不到就无从检查，按红处理）" % (SKILL_MD, REDLINE_SECTION_HEAD)
    if chars > SKILL_REDLINE_SECTION_LIMIT:
        return "红线节 %d 字符 > 上限 %d" % (chars, SKILL_REDLINE_SECTION_LIMIT)
    return None


def render_redlines(data: dict) -> str:
    """把凭据台账渲成人类可读文本。只读：调用方打印即可，不落盘。"""
    reds = redlines_of(data)
    if not reds:
        return "（契约里没有 redlines 块）"
    out = ["红线凭据台账（%d 条线 / %d 条子判据 / 出处 %d 条 / 未被引用 %d 条）"
           % (len(reds), len(redline_keys(data)),
              len(data["constants"].get("sources") or {}), len(orphan_sources(data)))]
    for num in sorted(reds, key=int):
        line = reds[num]
        out.append("")
        out.append("红线 %s｜%s（%d 条子判据）" % (num, line["title"], len(line["criteria"])))
        for ct in sorted(line["criteria"], key=lambda x: x["order"]):
            out.append("  %d. %s" % (ct["order"], ct["key"]))
            out.append("     凭据：%s" % ("、".join(ct["evidence"]) or "（待填）"))
            out.append("     覆盖：%s" % (ct["coverage"].strip() or "（待填）"))
            out.append("     判定层：%s" % (ct["decision_layer"].strip() or "（待填）"))
            out.append("     不能推出：%s" % (ct["cannot_infer"].strip() or "（待填）"))
    orph = orphan_sources(data)
    if orph:
        out.append("")
        out.append("未被任何子判据引用的出处（%d 条，反向校验检出）：%s"
                   % (len(orph), "、".join(orph)))
    return "\n".join(out)


def load(path: Path | None = None) -> dict:
    p = Path(path) if path is not None else default_path()
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        _fail("E-CONTRACT-MISSING", "契约不可读：%s" % e)
    if not text.strip():
        _fail("E-CONTRACT-INVALID", "契约为空：%s" % p)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        _fail("E-CONTRACT-INVALID", "契约 JSON 非法：%s" % e)
    return validate(data)


def load_or_exit() -> dict:
    """供 CLI 脚本在启动时调用；契约缺失/畸形即结构化失败并 exit 1。"""
    try:
        return load()
    except ContractError as e:
        print(json.dumps({"ok": False, "code": e.code, "message": e.message},
                         ensure_ascii=False))
        raise SystemExit(1)


def get(dotted: str, path: Path | None = None):
    cur = load(path)
    parts = dotted.split(".")
    if isinstance(cur, dict) and parts[0] not in cur and "constants" in cur:
        cur = cur["constants"]
    for part in parts:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            _fail("E-CONTRACT-INVALID", "契约键不存在：%s" % dotted)
    return cur


def _selftest() -> int:
    import tempfile

    fails = []
    ran = [0]

    def case(name, fn, expect_ok):
        # ContractError = 契约按预期被拒；其他异常是**用例自己写坏了**，必须显式报 FAIL，
        # 不能冒泡成 traceback 让人误以为是环境问题。
        ran[0] += 1
        try:
            fn()
            got_ok = True
        except ContractError:
            got_ok = False
        except Exception as exc:
            fails.append("%s: 用例自身抛错 %s: %s" % (name, type(exc).__name__, exc))
            return
        if got_ok != expect_ok:
            fails.append("%s: 期望 %s，实际 %s" % (name, "通过" if expect_ok else "失败",
                                                "通过" if got_ok else "失败"))

    real = default_path()
    case("真实契约可加载", lambda: load(real), True)
    case("缺文件", lambda: load(Path(str(real) + ".nope")), False)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        def write(name, obj):
            p = td / name
            if isinstance(obj, str):
                p.write_text(obj, encoding="utf-8")
            else:
                p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            return p

        base = json.loads(real.read_text(encoding="utf-8"))

        case("空文件", lambda: load(write("empty.json", "")), False)
        case("非法 JSON", lambda: load(write("bad.json", "{oops")), False)

        for k in REQUIRED_TOP:
            def missing(k=k):
                d = json.loads(json.dumps(base))
                d.pop(k)
                return load(write("miss_%s.json" % k, d))
            case("缺顶层键 %s" % k, missing, False)

        def bad_schema():
            d = json.loads(json.dumps(base))
            d["schema"] = "ltw-rules/2"
            return load(write("schema.json", d))
        case("schema 版本不符", bad_schema, False)

        # ── 两处 schema 声明必须相等（票 91）──────────────────────────────
        # 真实登记表当夹具：断言的对象就是线上那两个值，不是另造一份常量。
        def must(cond, msg):
            if not cond:
                _fail("E-CONTRACT-INVALID", msg)

        real_contract = json.loads(
            (skill_root() / "contracts" / "scripts-contract.json").read_text(encoding="utf-8"))

        def mutate(script, new_schema, drop_entry=False):
            d = json.loads(json.dumps(real_contract))
            kept = []
            for entry in d["scripts_contract"]:
                if isinstance(entry, dict) and entry.get("script") == script:
                    if drop_entry:
                        continue
                    if new_schema is None:
                        entry.pop("schema", None)
                    else:
                        entry["schema"] = new_schema
                kept.append(entry)
            d["scripts_contract"] = kept
            return d

        def pair_ok():
            diff = schema_declarations_mismatch(real_contract)
            must(diff is None, "真实登记表两处 schema 不一致：%s" % diff)

        def pair_drift_detected():
            must(schema_declarations_mismatch(mutate(SCHEMA_REGISTRY_SCRIPT, SCHEMA + "-drift"))
                 is not None, "文档侧单独漂移没有被发现")

        def pair_reverted_clean():
            must(schema_declarations_mismatch(mutate(SCHEMA_REGISTRY_SCRIPT, SCHEMA)) is None,
                 "还原后仍报漂移")

        def pair_missing_field_detected():
            must(schema_declarations_mismatch(mutate(SCHEMA_REGISTRY_SCRIPT, None))
                 is not None, "文档侧删掉 schema 字段没有被发现")

        def pair_missing_entry_detected():
            must(schema_declarations_mismatch(
                mutate(SCHEMA_REGISTRY_SCRIPT, SCHEMA, drop_entry=True)) is not None,
                 "登记表里没有 rule_contract.py 这一条也没有被发现")

        def pinned(script, new_schema):
            # 先把文档侧钉到代码常量，再动 targets：这样反例只证明「这一处不参与相等」。
            # 不钉的话，文档侧漂移会污染反例，让它为错误的理由变红（变异测试 M1 实测踩到）。
            base = mutate(SCHEMA_REGISTRY_SCRIPT, SCHEMA)
            for entry in base["scripts_contract"]:
                if isinstance(entry, dict) and entry.get("script") == script:
                    entry["schema"] = new_schema
            return base

        def index_side_exempt():
            # 反例：索引侧是另一套产物版本，改它不得变红——锁住「不得把第三个一并抹平」
            must(schema_declarations_mismatch(pinned("task_index.py", "learn-task-index/99")) is None,
                 "索引侧 schema 被收编进了两处相等判据")

        def third_declaration_rejected():
            # 另一个脚本也来声明 ltw-rules/*，必须红：这条判据只认一处登记
            must(schema_declarations_mismatch(pinned("task_index.py", SCHEMA)) is not None,
                 "ltw-rules 家族被第三处声明也没有被发现")

        case("真实登记表两处 schema 相等", pair_ok, True)
        case("变异：只改文档侧一处 → 红", pair_drift_detected, True)
        case("变异：文档侧还原 → 绿", pair_reverted_clean, True)
        case("变异：文档侧删掉 schema 字段 → 红", pair_missing_field_detected, True)
        case("变异：登记表缺该条目 → 红", pair_missing_entry_detected, True)
        case("反例：索引侧 schema 不参与相等 → 绿", index_side_exempt, True)
        case("反例：第三处声明 ltw-rules/* → 红", third_declaration_rejected, True)

        def dup_phase():
            d = json.loads(json.dumps(base))
            d["constants"]["phases"].append(d["constants"]["phases"][0])
            return load(write("dup.json", d))
        case("枚举重复", dup_phase, False)

        def bad_ratio():
            d = json.loads(json.dumps(base))
            d["constants"]["gates"]["min_ratio"] = [4, 3]
            return load(write("ratio.json", d))
        case("比例非法", bad_ratio, False)

        def bad_group():
            d = json.loads(json.dumps(base))
            d["constants"]["group_slugs"].pop(next(iter(d["constants"]["group_slugs"])))
            return load(write("group.json", d))
        case("group_slugs 与学科族不一致", bad_group, False)

        def dup_discipline():
            d = json.loads(json.dumps(base))
            d["constants"]["discipline_slugs"].append(d["constants"]["discipline_slugs"][0])
            return load(write("disc.json", d))
        case("discipline_slugs 重复", dup_discipline, False)

        def bad_judge():
            d = json.loads(json.dumps(base))
            d["constants"]["kp"]["judge"]["max_dates"] = 0
            return load(write("judge.json", d))
        case("kp.judge.max_dates 非正", bad_judge, False)

        def missing_judge():
            d = json.loads(json.dumps(base))
            d["constants"]["kp"].pop("judge")
            return load(write("nojudge.json", d))
        case("kp.judge 缺失", missing_judge, False)

        def retired_key():
            d = json.loads(json.dumps(base))
            d["constants"].pop("scheduler")
            return load(write("nokey.json", d))
        case("缺业务常量键", retired_key, False)

        # ── 红线凭据结构（票 96）：删键红 / 语义标识退化成序号红 / 还原绿 ──
        def without_redlines():
            d = json.loads(json.dumps(base))
            d["constants"].pop("redlines")
            d["constants"].pop("sources")
            return load(write("noreds.json", d))
        case("两块都没有时旧契约仍可加载（平行块不破旧校验）", without_redlines, True)

        def only_one_block():
            d = json.loads(json.dumps(base))
            d["constants"].pop("sources")
            return load(write("halfred.json", d))
        case("redlines 与 sources 只出现一块", only_one_block, False)

        def drop_criterion_key():
            d = json.loads(json.dumps(base))
            first = d["constants"]["redlines"]["1"]["criteria"][0]
            first.pop("order")
            return load(write("nokeycrit.json", d))
        case("子判据缺键", drop_criterion_key, False)

        def numeric_slug():
            d = json.loads(json.dumps(base))
            first = d["constants"]["redlines"]["1"]["criteria"][0]
            first["key"] = "R1.1"
            return load(write("numslug.json", d))
        case("语义标识退化成序号", numeric_slug, False)

        def dangling_source():
            d = json.loads(json.dumps(base))
            d["constants"]["redlines"]["1"]["criteria"][0]["evidence"] = ["R0-0"]
            return load(write("dangling.json", d))
        case("凭据引用不存在的出处（孤儿引用）", dangling_source, False)

        def order_gap():
            d = json.loads(json.dumps(base))
            d["constants"]["redlines"]["1"]["criteria"][0]["order"] = 9
            return load(write("ordergap.json", d))
        case("order 不是 1..n 的排列", order_gap, False)

        def line_gap():
            d = json.loads(json.dumps(base))
            d["constants"]["redlines"].pop("5")
            return load(write("linegap.json", d))
        case("线号不连续", line_gap, False)

        # 还原：在同一个用例里先改坏再改回，必须重新变绿——证明上面的红是那一处改动造成的，
        # 不是夹带进来的别的错
        def mutate_then_restore():
            d = json.loads(json.dumps(base))
            first = d["constants"]["redlines"]["1"]["criteria"][0]
            original = first["key"]
            first["key"] = "R1.1"
            try:
                load(write("restore_bad.json", d))
            except ContractError:
                pass
            else:
                raise AssertionError("改坏的那份本应加载失败")
            first["key"] = original
            return load(write("restore_ok.json", d))
        case("改坏后还原", mutate_then_restore, True)

        def real_contract_has_redlines():
            data = load(real)
            keys = redline_keys(data)
            assert len(keys) == len(set(keys)), "语义标识不唯一"
            assert all(REDLINE_KEY_RE.match(k) for k in keys), "存在非 R<线>.<slug> 形态"
            assert len(redlines_of(data)) == 11, "红线条数不是 11"
            return data
        case("真实契约的红线凭据结构可用", real_contract_has_redlines, True)

        def key_set_is_identity():
            # 键集合相等即通过：只改内容不改键 → 指纹变、键集合不变
            d = json.loads(json.dumps(base))
            d["constants"]["redlines"]["1"]["criteria"][0]["coverage"] = "改内容不改键"
            data = load(write("content.json", d))
            assert redline_keys(data) == redline_keys(load(real)), "键集合不该变"
            assert redline_fingerprint(data) != redline_fingerprint(load(real)), "指纹该变"
            return data
        case("内容指纹只告警：改内容不改键，键集合不变", key_set_is_identity, True)

        def orphan_reported():
            data = load(real)
            srcs = set(data["constants"]["sources"])
            used = srcs - set(orphan_sources(data))
            assert used <= srcs, "孤儿不应凭空多出来"
            assert set(orphan_sources(data)) | used == srcs, "孤儿与被引用必须覆盖 sources"
            return data
        case("反向校验：sources 被孤儿/被引用完整覆盖", orphan_reported, True)

        # ── 四段体例与红线节预算（票 98）────────────────────────────────
        # 这一组盯的是「体例本身会不会烂掉」：四段少一段没人发现、超 400 字符没人发现、
        # 入口红线节被写胖到压缩砍点之后没人发现——三种都是静默失效，必须各自会红。
        def drop_segment(field):
            def _make():
                d = json.loads(json.dumps(base))
                d["constants"]["redlines"]["1"]["criteria"][0][field] = ""
                return load(write("noseg_%s.json" % field, d))
            return _make

        for field in REDLINE_SEGMENT_TEXT_FIELDS:
            case("四段缺 %s → 红" % field, drop_segment(field), False)

        def drop_evidence():
            d = json.loads(json.dumps(base))
            d["constants"]["redlines"]["1"]["criteria"][0]["evidence"] = []
            return load(write("noev.json", d))
        # 凭据为空时先被类型检查拦下（没有 E1–E6 就判断不了这一条有多硬），
        # 所以这里断言的是「红」，不是某个具体错误码——写死错误码会把实现细节当判据。
        case("四段缺凭据 → 红", drop_evidence, False)

        def evidence_source_only():
            # 只有出处的凭据段等价于「没分级」：必须红，否则「这条有多硬」永远没人写
            d = json.loads(json.dumps(base))
            d["constants"]["redlines"]["1"]["criteria"][0]["evidence"] = ["R1-1"]
            return load(write("evonly.json", d))
        case("凭据只有出处、没有 E1–E6 类型 → 红", evidence_source_only, False)

        def evidence_bad_tier():
            d = json.loads(json.dumps(base))
            d["constants"]["redlines"]["1"]["criteria"][0]["evidence"] = ["E9"]
            return load(write("evtier.json", d))
        case("凭据类型不在 E1–E6 白名单 → 红", evidence_bad_tier, False)

        def segment_over():
            d = json.loads(json.dumps(base))
            ct = d["constants"]["redlines"]["1"]["criteria"][0]
            ct["cannot_infer"] = "推" * REDLINE_SEGMENT_LIMIT
            return load(write("segover.json", d))
        case("四段合计超 400 字符 → 红", segment_over, False)

        def segment_boundary_ok():
            # 正好等于上限必须绿：把边界写成 < 会把上限悄悄改成 399，谁也不会发现
            d = json.loads(json.dumps(base))
            ct = d["constants"]["redlines"]["1"]["criteria"][0]
            room = REDLINE_SEGMENT_LIMIT - (redline_segment_length(ct) - len(ct["cannot_infer"]))
            assert room > 0, "夹具预算不足，边界用例失效"
            ct["cannot_infer"] = "推" * room
            assert redline_segment_length(ct) == REDLINE_SEGMENT_LIMIT
            return load(write("segedge.json", d))
        case("四段合计正好 400 字符 → 绿", segment_boundary_ok, True)

        def real_segments_filled():
            data = load(real)
            names = redline_keys(data)
            assert names, "真实契约没有子判据"
            for line in redlines_of(data).values():
                for ct in line["criteria"]:
                    assert ct["evidence"], "%s 凭据段为空" % ct["key"]
                    for f in REDLINE_SEGMENT_TEXT_FIELDS:
                        assert ct[f].strip(), "%s.%s 为空" % (ct["key"], f)
                    assert redline_segment_length(ct) <= REDLINE_SEGMENT_LIMIT, \
                        "%s 四段 %d 字符超预算" % (ct["key"], redline_segment_length(ct))
            return data
        case("真实契约：四段全部写全且都在 400 字符内", real_segments_filled, True)

        def forbidden_source_not_cited():
            # R1-5 在 CREDITS 里明写「未核实、不得引用」。它必须一直是孤儿——
            # 有人把它填进 evidence，就是拿未核实的条目当凭据，比留空更坏。
            data = load(real)
            orph = set(orphan_sources(data))
            assert "R1-5" in orph, "R1-5 标了不得引用，不得出现在任何凭据里"
            return data
        case("负向记录 R1-5 未被任何子判据引用", forbidden_source_not_cited, True)

        def skill_budget_ok():
            assert skill_redline_section_violation() is None, \
                "真实 SKILL.md 红线节超预算：%s" % skill_redline_section_violation()
        case("真实 SKILL.md 红线节 ≤%d 字符" % SKILL_REDLINE_SECTION_LIMIT,
             skill_budget_ok, True)

        # 红线节预算的变异：在临时目录里造一份 SKILL.md，把红线节撑胖 → 必红；还原 → 必绿。
        # 不拿真实 SKILL.md 开刀：变异测试改被测文件再改回来，中间态一旦被别的进程读到就是事故。
        def skill_budget_mutation():
            fake = td / "fake_skill"
            fake.mkdir(exist_ok=True)
            p = fake / SKILL_MD
            p.write_text("%s\n小\n\n## 下一节\n" % REDLINE_SECTION_HEAD, encoding="utf-8")
            assert skill_redline_section_violation(fake) is None, "小红线节应通过"
            p.write_text("%s\n%s\n\n## 下一节\n"
                         % (REDLINE_SECTION_HEAD, "胖" * (SKILL_REDLINE_SECTION_LIMIT + 1)),
                         encoding="utf-8")
            assert skill_redline_section_violation(fake) is not None, "撑胖后没有变红"
            p.write_text("%s\n小\n\n## 下一节\n" % REDLINE_SECTION_HEAD, encoding="utf-8")
            assert skill_redline_section_violation(fake) is None, "还原后仍报超预算"
            return True
        case("变异：红线节撑到 >%d 字符 → 红，还原 → 绿"
             % SKILL_REDLINE_SECTION_LIMIT, skill_budget_mutation, True)

        def skill_budget_anchor_missing():
            fake = td / "fake_nohead"
            fake.mkdir(exist_ok=True)
            (fake / SKILL_MD).write_text("## 别的节\n内容\n", encoding="utf-8")
            assert skill_redline_section_violation(fake) is not None, \
                "锚点找不到时必须按红处理，否则是假绿"
            return True
        case("红线节锚点缺失 → 红（找不到即无从检查）", skill_budget_anchor_missing, True)

    if fails:
        for f in fails:
            print("FAIL", f)
        return 1
    print("PASS 纯常量加载器：%d 个用例" % ran[0])
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="规则常量加载器（只读）")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--selftest", action="store_true")
    g.add_argument("--get", metavar="DOTTED")
    g.add_argument("--keys", action="store_true", help="列出业务常量键")
    g.add_argument("--redline-keys", action="store_true",
                   help="只读：输出红线子判据的语义标识集合与内容指纹（键集合是身份，"
                        "指纹变了只告警）")
    g.add_argument("--redlines", action="store_true",
                   help="只读：把红线凭据台账渲到 stdout（不落盘）")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()
    if args.keys:
        data = load_or_exit()
        print(json.dumps({"schema": data["schema"], "version": data["version"],
                          "constants": sorted(data["constants"])}, ensure_ascii=False))
        return 0
    if args.redline_keys:
        data = load_or_exit()
        print(json.dumps({
            "schema": data["schema"],
            "version": data["version"],
            "redline_count": len(redlines_of(data)),
            "keys": redline_keys(data),
            "fingerprint": redline_fingerprint(data),
            "orphan_sources": orphan_sources(data),
            "segment_limit": REDLINE_SEGMENT_LIMIT,
            "segment_max_chars": max((redline_segment_length(ct)
                                     for line in redlines_of(data).values()
                                     for ct in line["criteria"]), default=0),
            "skill_redline_section_chars": skill_redline_section_chars
            (skill_root() / SKILL_MD),
            "skill_redline_section_limit": SKILL_REDLINE_SECTION_LIMIT,
            "skill_redline_section_violation": skill_redline_section_violation(),
        }, ensure_ascii=False, indent=1))
        return 0
    if args.redlines:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(render_redlines(load_or_exit()))
        return 0
    print(json.dumps(get(args.get), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
