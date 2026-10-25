#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规则契约加载与拓扑检查（stdlib-only）。

契约固定为 <技能根>/contracts/rules.json。缺失/畸形时所有调用方必须 fail closed。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

SCHEMA = "ltw-rules/1"
REQUIRED_TOP = ("schema", "version", "files", "rules", "path_aliases", "constants")
REQUIRED_CONST = (
    "phases", "types", "subject_families", "teaching_strategies",
    "review_origin_phases", "grading", "kp", "gates", "restatement",
    "budget", "schemas", "headings", "scheduler", "errors",
)
LOAD_DIRECTIVE_RE = re.compile(r"(?:@references/|加载\s*`?references/)")
OLD_NAMES = (
    "entry-routing.md", "phases-and-gates.md", "teaching-loop.md",
    "lecture-styles.md", "handout-design.md", "data-and-recovery.md",
    "redlines.md", "setup-guide.md", "subject-playbooks.md",
    "formula-typesetting.md", "methodology.md",
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
        _require(k in data, "E-CONTRACT-INVALID", "缺少顶层键：%s" % k)
    _require(data.get("schema") == SCHEMA, "E-CONTRACT-INVALID", "schema 必须为 %s" % SCHEMA)

    files = data["files"]
    _require(isinstance(files, list) and files, "E-CONTRACT-INVALID", "files 必须是非空数组")
    ids, paths = [], []
    for f in files:
        _require(isinstance(f, dict), "E-CONTRACT-INVALID", "files 条目必须是对象")
        for k in ("id", "path", "layer", "owns", "depends_on"):
            _require(k in f, "E-CONTRACT-INVALID", "files 条目缺少 %s" % k)
        ids.append(f["id"])
        paths.append(f["path"])
        _require(isinstance(f["depends_on"], list), "E-CONTRACT-INVALID", "depends_on 必须是数组")
    _require(not _dup(ids), "E-CONTRACT-INVALID", "files.id 重复：%s" % _dup(ids))
    _require(not _dup(paths), "E-CONTRACT-INVALID", "files.path 重复：%s" % _dup(paths))
    for f in files:
        for dep in f["depends_on"]:
            _require(dep in ids, "E-CONTRACT-INVALID", "未知依赖 id：%s" % dep)

    rules = data["rules"]
    _require(isinstance(rules, list) and rules, "E-CONTRACT-INVALID", "rules 必须是非空数组")
    rids, owners = [], []
    for r in rules:
        _require(isinstance(r, dict), "E-CONTRACT-INVALID", "rules 条目必须是对象")
        for k in ("id", "owner", "type"):
            _require(k in r, "E-CONTRACT-INVALID", "rules 条目缺少 %s" % k)
        _require(re.match(r"^R\d+$", str(r["id"])) is not None,
                 "E-CONTRACT-INVALID", "rule id 非法：%s" % r["id"])
        rids.append(r["id"])
        owners.append(r["owner"])
    _require(not _dup(rids), "E-CONTRACT-INVALID", "rule id 重复：%s" % _dup(rids))

    aliases = data["path_aliases"]
    _require(isinstance(aliases, dict), "E-CONTRACT-INVALID", "path_aliases 必须是对象")
    for old, new in aliases.items():
        _require(isinstance(new, str) and new in paths,
                 "E-CONTRACT-INVALID", "path_aliases 指向未知文件：%s → %s" % (old, new))

    c = data["constants"]
    _require(isinstance(c, dict), "E-CONTRACT-INVALID", "constants 必须是对象")
    for k in REQUIRED_CONST:
        _require(k in c, "E-CONTRACT-INVALID", "constants 缺少 %s" % k)
    for key in ("phases", "types", "subject_families", "teaching_strategies", "review_origin_phases"):
        _require(isinstance(c[key], list) and c[key], "E-CONTRACT-INVALID", "%s 必须是非空数组" % key)
        _require(not _dup(c[key]), "E-CONTRACT-INVALID", "%s 有重复值：%s" % (key, _dup(c[key])))

    g = c["grading"]
    _require(isinstance(g.get("values"), list) and len(g["values"]) == 4,
             "E-CONTRACT-INVALID", "grading.values 必须是四态")
    _require(not _dup(g["values"]), "E-CONTRACT-INVALID", "grading.values 有重复")

    kp = c["kp"]
    for key in ("states", "types", "visual_tasks"):
        _require(isinstance(kp.get(key), list) and kp[key], "E-CONTRACT-INVALID", "kp.%s 必须是非空数组" % key)
        _require(not _dup(kp[key]), "E-CONTRACT-INVALID", "kp.%s 有重复" % key)

    for key in ("min_ratio", "final_ratio"):
        val = c["gates"].get(key)
        _require(isinstance(val, list) and len(val) == 2 and all(isinstance(x, int) for x in val),
                 "E-CONTRACT-INVALID", "gates.%s 必须是 [a,b] 整数" % key)
        a, b = val
        _require(0 <= a <= b and b > 0, "E-CONTRACT-INVALID", "gates.%s 非法：%s" % (key, val))

    budget = c["budget"]
    for key in ("self_test", "exercise_group_min", "exercise_group_max",
                "unit_check_max", "core_total_max", "l3_review_min", "l3_review_max"):
        _require(isinstance(budget.get(key), int), "E-CONTRACT-INVALID", "budget.%s 必须是整数" % key)
    _require(budget["exercise_group_min"] <= budget["exercise_group_max"],
             "E-CONTRACT-INVALID", "题组下限大于上限")

    for key in ("self_test", "answer_suffixes", "lead_words", "unicode_denylist"):
        _require(isinstance(c["headings"].get(key), list) and c["headings"][key],
                 "E-CONTRACT-INVALID", "headings.%s 必须是非空数组" % key)
        _require(not _dup(c["headings"][key]), "E-CONTRACT-INVALID", "headings.%s 有重复" % key)

    errs = c["errors"]
    for level in ("E", "W"):
        _require(isinstance(errs.get(level), list), "E-CONTRACT-INVALID", "errors.%s 必须是数组" % level)
    _require(not _dup(errs["E"] + errs["W"]), "E-CONTRACT-INVALID", "errors 有重复码")
    return data


def load(path: Path | None = None) -> dict:
    p = Path(path) if path else default_path()
    if not p.exists():
        _fail("E-CONTRACT-MISSING", "契约不存在：%s" % p)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        _fail("E-CONTRACT-INVALID", "契约不可读：%s" % e)
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
        print(json.dumps({"ok": False, "code": e.code, "message": e.message}, ensure_ascii=False))
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


def _heading_exists(root: Path, rel: str, anchor: str) -> bool:
    p = root / rel
    if not p.exists():
        return False
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.startswith("#") and anchor in ln:
            return True
    return False


def _dag(files: list) -> tuple[bool, str]:
    graph = {f["id"]: list(f["depends_on"]) for f in files}
    state = {}

    def visit(n):
        if state.get(n) == 1:
            return False
        if state.get(n) == 2:
            return True
        state[n] = 1
        for d in graph.get(n, []):
            if not visit(d):
                return False
        state[n] = 2
        return True

    for n in graph:
        if not visit(n):
            return False, "依赖成环：%s" % n
    return True, ""


def topology(path: Path | None = None) -> dict:
    root = skill_root()
    data = load(path)
    issues = []
    files = data["files"]

    # 1. references 不写加载指令
    for f in files:
        p = root / f["path"]
        if not p.exists():
            issues.append("E-TOPOLOGY-FILE: 文件不存在 %s" % f["path"])
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if LOAD_DIRECTIVE_RE.search(text):
            issues.append("E-TOPOLOGY-LOAD: %s 含加载指令" % f["path"])
        # 2. 职责头
        if "<!-- owns:" not in text or "must-not-define:" not in text:
            issues.append("E-TOPOLOGY-HEADER: %s 缺 owns/must-not-define" % f["path"])
        # 3. 旧文件名只允许出现在 alias 表
        for old in OLD_NAMES:
            if old in text:
                issues.append("E-TOPOLOGY-OLDNAME: %s 含旧文件名 %s" % (f["path"], old))

    # 4. 规则 owner 可解析
    for r in data["rules"]:
        owner = r["owner"]
        if "#" not in owner:
            issues.append("E-TOPOLOGY-OWNER: %s owner 缺 #anchor" % r["id"])
            continue
        rel, anchor = owner.split("#", 1)
        if not (root / rel).exists():
            issues.append("E-TOPOLOGY-OWNER: %s owner 文件不存在 %s" % (r["id"], rel))
        elif not _heading_exists(root, rel, anchor):
            issues.append("E-TOPOLOGY-OWNER: %s owner 小节不存在 %s#%s" % (r["id"], rel, anchor))

    # 5. 依赖无环
    ok, msg = _dag(files)
    if not ok:
        issues.append("E-TOPOLOGY-DAG: " + msg)

    return {
        "ok": not issues,
        "files": len(files),
        "rules": len(data["rules"]),
        "issues": issues,
    }


def _selftest() -> int:
    failures = []

    def chk(name, fn):
        try:
            fn()
            print("PASS", name)
        except Exception as e:
            failures.append(name)
            print("FAIL", name, "::", e)

    def real():
        d = load()
        assert d["schema"] == SCHEMA
        assert get("gates.min_ratio") == [2, 3]

    chk("real contract loads", real)

    def missing():
        try:
            load(skill_root() / "contracts" / "__missing__.json")
        except ContractError as e:
            assert e.code == "E-CONTRACT-MISSING"
            return
        raise AssertionError("missing contract did not fail")

    chk("missing contract", missing)

    def empty():
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write("")
            p = Path(f.name)
        try:
            load(p)
        except ContractError as e:
            assert e.code == "E-CONTRACT-INVALID"
            return
        finally:
            p.unlink(missing_ok=True)
        raise AssertionError("empty contract did not fail")

    chk("empty contract", empty)

    def bad_json():
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write("{not json")
            p = Path(f.name)
        try:
            load(p)
        except ContractError as e:
            assert e.code == "E-CONTRACT-INVALID"
            return
        finally:
            p.unlink(missing_ok=True)
        raise AssertionError("bad json did not fail")

    chk("invalid json", bad_json)

    def missing_key():
        d = json.loads(default_path().read_text(encoding="utf-8"))
        d.pop("constants")
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
            p = Path(f.name)
        try:
            load(p)
        except ContractError as e:
            assert e.code == "E-CONTRACT-INVALID"
            return
        finally:
            p.unlink(missing_ok=True)
        raise AssertionError("missing key did not fail")

    chk("missing key", missing_key)

    def dup_enum():
        d = json.loads(default_path().read_text(encoding="utf-8"))
        d["constants"]["phases"].append(d["constants"]["phases"][0])
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
            p = Path(f.name)
        try:
            load(p)
        except ContractError as e:
            assert e.code == "E-CONTRACT-INVALID"
            return
        finally:
            p.unlink(missing_ok=True)
        raise AssertionError("dup enum did not fail")

    chk("duplicate enum", dup_enum)

    def bad_ratio():
        d = json.loads(default_path().read_text(encoding="utf-8"))
        d["constants"]["gates"]["min_ratio"] = [4, 3]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
            p = Path(f.name)
        try:
            load(p)
        except ContractError as e:
            assert e.code == "E-CONTRACT-INVALID"
            return
        finally:
            p.unlink(missing_ok=True)
        raise AssertionError("bad ratio did not fail")

    chk("invalid ratio", bad_ratio)

    def topo_ok():
        r = topology()
        assert r["ok"], r["issues"]

    chk("topology clean", topo_ok)

    if failures:
        print("SELFTEST FAILED:", ", ".join(failures))
        return 1
    print("SELFTEST OK")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="规则契约加载与拓扑检查")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--selftest", action="store_true")
    g.add_argument("--topology", action="store_true")
    g.add_argument("--get", metavar="DOTTED")
    args = ap.parse_args(argv)
    try:
        if args.selftest:
            return _selftest()
        if args.topology:
            r = topology()
            print(json.dumps(r, ensure_ascii=False, indent=1))
            return 0 if r["ok"] else 1
        print(json.dumps(get(args.get), ensure_ascii=False, indent=1))
        return 0
    except ContractError as e:
        print(json.dumps({"ok": False, "code": e.code, "message": e.message}, ensure_ascii=False))
        return 1
    except Exception as e:  # 不让 traceback 成为外部协议
        print(json.dumps({"ok": False, "code": "E-CONTRACT-INVALID", "message": str(e)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
