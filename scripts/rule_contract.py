#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规则常量加载器（stdlib-only，纯常量）。

契约固定为 <技能根>/contracts/rules.json，只承载两件事：**结构版本** 与 **业务常量**。
七个确定性脚本与行为脚本从这里读判分、调度、续学、排印所需的枚举与阈值；
读取失败时 fail closed——调用方不得退回内置默认值继续跑。

契约里不再有场景注册表、意图登记、文件清单、规则编号登记或退役编号表；
那些只服务索引的编译关系已随编译层一起退役。

--selftest 覆盖：真实契约可加载、缺文件、空文件、非法 JSON、缺键、枚举重复、比例非法、
kp.judge（目行判定三字段的枚举与日期上限）缺失或越界。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA = "ltw-rules/3"
# 必填键收窄为结构版本与常量两组
REQUIRED_TOP = ("schema", "version", "constants")
# 七个确定性脚本与行为脚本实际消费的业务常量键
REQUIRED_CONST = (
    "phases", "types", "subject_families", "group_slugs", "discipline_slugs",
    "review_origin_phases", "grading", "kp", "gates", "restatement",
    "budget", "schemas", "headings", "scheduler", "errors",
)


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
    return data


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
        ran[0] += 1
        try:
            fn()
            got_ok = True
        except ContractError:
            got_ok = False
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
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()
    if args.keys:
        data = load_or_exit()
        print(json.dumps({"schema": data["schema"], "version": data["version"],
                          "constants": sorted(data["constants"])}, ensure_ascii=False))
        return 0
    print(json.dumps(get(args.get), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
