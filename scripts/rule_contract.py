#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规则契约加载与拓扑检查（stdlib-only）。

契约固定为 <技能根>/contracts/rules.json。缺失/畸形时所有调用方必须 fail closed。

--topology 检查：references 无加载指令、owns/must-not-define 职责头、
R/T/F 规则 owner 锚点可解析、依赖无环、
版本四方一致（SKILL.md / rules.json / skill-dependencies.json / evals.json）、
全仓 E-/W- 错误码 ⊆ 契约 errors、operations.md 速查表与 errors 双向覆盖、
handout.md canonical 集合与 headings.lead_words 双写一致。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

SCHEMA = "ltw-rules/1"
REQUIRED_TOP = ("schema", "version", "files", "rules", "constants", "scenes")
REQUIRED_CONST = (
    "phases", "types", "subject_families", "group_slugs", "discipline_slugs",
    "review_origin_phases", "grading", "kp", "gates", "restatement",
    "budget", "schemas", "headings", "scheduler", "errors",
)
LOAD_DIRECTIVE_RE = re.compile(r"(?:@references/|加载\s*`?references/|加载时机)")
ERROR_CODE_RE = re.compile(r"\b[EW]-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b")
# references/SKILL.md 中引用的 T/F/R 设计编号（如（T11）（F05）（R05））必须有契约 rules 定义
NUM_REF_RE = re.compile(r"\b([TF]\d{2}|R\d{1,2})\b")
# 错误码扫描范围：任何提到 E-/W- 码的文件都必须只提契约声明过的码
SCAN_GLOBS = (
    "scripts/*.py",
    "evals/verify-*.py",
    "references/**/*.md",
    "contracts/scripts-contract.json",
    "SKILL.md",
)
# 场景文件表里的展开令牌 → 契约常量键。每个令牌展开为「同名文件的一组实例」。
TOKEN_KEYS = {"{group}": "group_slugs", "{discipline}": "discipline_slugs"}


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
        _require(re.match(r"^[RTF]\d+$", str(r["id"])) is not None,
                 "E-CONTRACT-INVALID", "rule id 非法：%s" % r["id"])
        rids.append(r["id"])
        owners.append(r["owner"])
    _require(not _dup(rids), "E-CONTRACT-INVALID", "rule id 重复：%s" % _dup(rids))

    scenes = data["scenes"]
    _require(isinstance(scenes, dict) and scenes, "E-CONTRACT-INVALID", "scenes 必须是非空对象")
    for sid, sc in scenes.items():
        _require(isinstance(sc, dict), "E-CONTRACT-INVALID", "scenes.%s 必须是对象" % sid)
        for k in ("label", "files"):
            _require(k in sc, "E-CONTRACT-INVALID", "scenes.%s 缺 %s" % (sid, k))
        _require(isinstance(sc["files"], list) and sc["files"],
                 "E-CONTRACT-INVALID", "scenes.%s.files 必须是非空数组" % sid)
    for r in rules:
        if "scenes" in r:
            _require(isinstance(r["scenes"], list) and r["scenes"],
                     "E-CONTRACT-INVALID", "rule %s.scenes 必须是非空数组" % r["id"])
            for sid in r["scenes"]:
                _require(sid in scenes, "E-CONTRACT-INVALID",
                         "rule %s 引用未定义场景 %s" % (r["id"], sid))

    intents = data.get("intents", [])
    _require(isinstance(intents, list), "E-CONTRACT-INVALID", "intents 必须是数组")
    seen_intents = set()
    for it in intents:
        _require(isinstance(it, dict), "E-CONTRACT-INVALID", "intents 条目必须是对象")
        for k in ("id", "scope", "owner", "marker", "consumers", "scenes"):
            _require(k in it, "E-CONTRACT-INVALID", "intent 缺少 %s" % k)
        _require(isinstance(it["consumers"], list), "E-CONTRACT-INVALID",
                 "intent %s.consumers 必须是数组" % it["id"])
        _require(isinstance(it["scenes"], list) and it["scenes"], "E-CONTRACT-INVALID",
                 "intent %s.scenes 必须是非空数组" % it["id"])
        key = (it["id"], it["scope"])
        _require(key not in seen_intents, "E-CONTRACT-INVALID",
                 "intent 重复：%s@%s" % key)
        seen_intents.add(key)
        for sid in it["scenes"]:
            _require(sid in scenes, "E-CONTRACT-INVALID",
                     "intent %s 引用未定义场景 %s" % (it["id"], sid))

    for sid, sc in scenes.items():
        for key in ("stack", "supplements"):
            if key in sc:
                _require(isinstance(sc[key], list), "E-CONTRACT-INVALID",
                         "scenes.%s.%s 必须是数组" % (sid, key))
        for item in sc.get("stack", []):
            _require(isinstance(item, dict) and "scene" in item and "when" in item,
                     "E-CONTRACT-INVALID", "scenes.%s.stack 条目缺 scene/when" % sid)
        for item in sc.get("supplements", []):
            _require(isinstance(item, dict), "E-CONTRACT-INVALID",
                     "scenes.%s.supplements 条目必须是对象" % sid)
            for k in ("file", "section", "when", "intent"):
                _require(k in item, "E-CONTRACT-INVALID",
                         "scenes.%s.supplements 条目缺少 %s" % (sid, k))

    c = data["constants"]
    _require(isinstance(c, dict), "E-CONTRACT-INVALID", "constants 必须是对象")
    for k in REQUIRED_CONST:
        _require(k in c, "E-CONTRACT-INVALID", "constants 缺少 %s" % k)
    for key in ("phases", "types", "subject_families", "review_origin_phases"):
        _require(isinstance(c[key], list) and c[key], "E-CONTRACT-INVALID", "%s 必须是非空数组" % key)
        _require(not _dup(c[key]), "E-CONTRACT-INVALID", "%s 有重复值：%s" % (key, _dup(c[key])))

    gs = c["group_slugs"]
    _require(isinstance(gs, dict) and gs, "E-CONTRACT-INVALID", "group_slugs 必须是非空对象")
    for gk, gv in gs.items():
        _require(isinstance(gv, str) and gv, "E-CONTRACT-INVALID",
                 "group_slugs.%s 必须是非空字符串" % gk)
    _require(not _dup(list(gs.values())), "E-CONTRACT-INVALID", "group_slugs 值有重复")
    _require(set(gs) == set(c["subject_families"]), "E-CONTRACT-INVALID",
             "group_slugs 键集必须与 subject_families 一致")

    ds = c["discipline_slugs"]
    _require(isinstance(ds, list) and ds, "E-CONTRACT-INVALID", "discipline_slugs 必须是非空数组")
    for dv in ds:
        _require(isinstance(dv, str) and dv, "E-CONTRACT-INVALID",
                 "discipline_slugs 条目必须是非空字符串")
    _require(not _dup(ds), "E-CONTRACT-INVALID", "discipline_slugs 有重复值：%s" % _dup(ds))

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


def _skill_md_version(root: Path) -> str:
    text = (root / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"(?m)^version:\s*(\S+)\s*$", text)
    return m.group(1) if m else ""


def check_versions(skill_version: str, contract_version: str,
                   deps_path: Path, evals_path: Path) -> list:
    """版本四方一致：SKILL.md == rules.json == skill-dependencies == evals.json。"""
    issues = []
    if not skill_version:
        issues.append("E-TOPOLOGY-VERSION: SKILL.md frontmatter 缺 version")
    if skill_version and contract_version != skill_version:
        issues.append("E-TOPOLOGY-VERSION: rules.json version %s ≠ SKILL.md %s"
                      % (contract_version, skill_version))
    try:
        deps = json.loads(deps_path.read_text(encoding="utf-8"))
        dep_ver = deps["dependencies"][0]["setup"]["applies_to_version"]
        if dep_ver != skill_version:
            issues.append("E-TOPOLOGY-VERSION: skill-dependencies.json applies_to_version %s ≠ SKILL.md %s"
                          % (dep_ver, skill_version))
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        issues.append("E-TOPOLOGY-VERSION: skill-dependencies.json 缺 dependencies[0].setup.applies_to_version")
    try:
        ev_ver = json.loads(evals_path.read_text(encoding="utf-8"))["applies_to_version"]
        if ev_ver != skill_version:
            issues.append("E-TOPOLOGY-VERSION: evals.json applies_to_version %s ≠ SKILL.md %s"
                          % (ev_ver, skill_version))
    except (OSError, ValueError, KeyError):
        issues.append("E-TOPOLOGY-VERSION: evals.json 缺 applies_to_version")
    return issues


def check_error_codes(declared: set, root: Path) -> tuple[set, list]:
    """全仓出现的 E-/W- 码必须都在契约 errors 中声明。"""
    used, where = set(), {}
    for pattern in SCAN_GLOBS:
        for p in sorted(root.glob(pattern)):
            rel = p.relative_to(root).as_posix()
            for code in ERROR_CODE_RE.findall(p.read_text(encoding="utf-8", errors="replace")):
                used.add(code)
                where.setdefault(code, rel)
    unknown = sorted(used - declared)
    issues = ["E-TOPOLOGY-ERRORCODE: 未声明码 %s（见于 %s）" % (c, where[c]) for c in unknown]
    return used, issues


def check_mirror(declared: set, ops_text: str) -> list:
    """operations.md 错误码速查表与契约 errors 双向覆盖。

    逐字覆盖为常规要求；家族根码（如 E-BOX，仅作前缀匹配用、脚本从不逐字
    发出）可由operations.md 中其任一子码覆盖。
    """
    ops_codes = set(ERROR_CODE_RE.findall(ops_text))
    issues = ["E-TOPOLOGY-MIRROR: operations.md 含未声明码 %s" % c
              for c in sorted(ops_codes - declared)]
    for c in sorted(declared - ops_codes):
        if not any(o.startswith(c + "-") for o in ops_codes):
            issues.append("E-TOPOLOGY-MIRROR: operations.md 缺码 %s 条目" % c)
    return issues


def check_lead_words(contract_words: list, text: str) -> list:
    """ops/typography.md canonical 集合与契约 headings.lead_words 双写一致。"""
    m = re.search(r"\*\*canonical 集合\*\*[^：]*：(.+)", text)
    if not m:
        return ["E-TOPOLOGY-LEADWORDS: ops/typography.md 缺 canonical 集合行"]
    doc_words = set(re.findall(r"`([^`]+)`", m.group(1)))
    cw = set(contract_words)
    issues = ["E-TOPOLOGY-LEADWORDS: 契约缺 lead_word %s" % w for w in sorted(doc_words - cw)]
    issues += ["E-TOPOLOGY-LEADWORDS: ops/typography.md 缺 lead_word %s" % w for w in sorted(cw - doc_words)]
    return issues


def check_number_refs(rule_ids: set, texts: list) -> list:
    """references/SKILL.md 引用的 T/F/R 设计编号必须都在契约 rules 中有定义。

    R 记号做零值归一（（R05）≡ R5）；T/F 记号固定两位数字形。
    """
    issues = []
    for name, text in texts:
        for m in NUM_REF_RE.finditer(text):
            tok = m.group(1)
            norm = "R%d" % int(tok[1:]) if tok[0] == "R" else tok
            if norm not in rule_ids:
                issues.append("E-TOPOLOGY-DEADREF: %s 引用未定义编号 %s" % (name, tok))
    return issues


def _token_names(data: dict) -> dict:
    """令牌 → 名字列表。{group} 取 group_slugs 的值，{discipline} 取 discipline_slugs。"""
    c = data["constants"]
    slugs = c["group_slugs"]
    return {
        "{group}": list(slugs.values()) if isinstance(slugs, dict) else list(slugs),
        "{discipline}": list(c["discipline_slugs"]),
    }


def _expand_files(files_list: list, token_names: dict) -> list:
    """把场景文件表里的令牌展开成具体路径；同一路径出现两个令牌属设计错误，此处跳过。"""
    out = []
    for f in files_list:
        toks = [t for t in TOKEN_KEYS if t in f]
        if not toks:
            out.append(f)
            continue
        if len(toks) > 1:
            continue
        out.extend(f.replace(toks[0], n) for n in token_names[toks[0]])
    return out


def check_scenes(data: dict, root: Path) -> tuple[list, dict]:
    """E-TOPOLOGY-SCENES：场景注册表、规则覆盖与文件覆盖的一致性。"""
    issues = []
    token_names = _token_names(data)
    for tok, names in token_names.items():
        if not names:
            issues.append("E-TOPOLOGY-SCENES: 令牌 %s 展开为空" % tok)
    expanded = {}
    for sid, sc in data["scenes"].items():
        toks = {t for f in sc["files"] for t in TOKEN_KEYS if t in f}
        if len(toks) > 1:
            issues.append("E-TOPOLOGY-SCENES: 场景 %s 同时使用多个令牌 %s"
                          % (sid, sorted(toks)))
            continue
        files = _expand_files(sc["files"], token_names)
        for f in files:
            if not (root / f).exists():
                issues.append("E-TOPOLOGY-SCENES: 场景 %s 文件不存在 %s" % (sid, f))
        expanded[sid] = set(files)
    covered = set()
    for files in expanded.values():
        covered |= files
    for f in data["files"]:
        if f["path"] not in covered:
            issues.append("E-TOPOLOGY-SCENES: 文件未属于任何场景 %s" % f["path"])
    for r in data["rules"]:
        scs = r.get("scenes") or []
        if not scs:
            issues.append("E-TOPOLOGY-SCENES: 规则未挂场景 %s" % r["id"])
            continue
        owner_file = r["owner"].split("#", 1)[0]
        if not any(owner_file in expanded.get(sid, set()) for sid in scs):
            issues.append("E-TOPOLOGY-SCENES: 规则 %s owner %s 不在其场景内"
                          % (r["id"], owner_file))

    intent_keys = {"%s@%s" % (it["id"], it["scope"]) for it in data.get("intents", [])}
    for sid, sc in data["scenes"].items():
        for item in sc.get("stack", []):
            target = item.get("scene")
            if target not in data["scenes"]:
                issues.append("E-TOPOLOGY-SCENES: 场景 %s stack 指向未定义场景 %s" % (sid, target))
            elif target == sid:
                issues.append("E-TOPOLOGY-SCENES: 场景 %s stack 不能指向自身" % sid)
        for item in sc.get("supplements", []):
            target = item.get("file")
            if not target or not (root / target).exists():
                issues.append("E-TOPOLOGY-SCENES: 场景 %s supplement 文件不存在 %s" % (sid, target))
            if item.get("intent") not in intent_keys:
                issues.append("E-TOPOLOGY-SCENES: 场景 %s supplement intent 未定义 %s"
                              % (sid, item.get("intent")))

    def _stack_cycle(start):
        pending = [(start, [start])]
        while pending:
            node, path = pending.pop()
            for item in data["scenes"].get(node, {}).get("stack", []):
                nxt = item["scene"]
                if nxt in path:
                    return True
                pending.append((nxt, path + [nxt]))
        return False

    for sid in data["scenes"]:
        if _stack_cycle(sid):
            issues.append("E-TOPOLOGY-SCENES: 场景 %s stack 成环" % sid)
    return issues, expanded


def _allowed_files(data: dict, expanded: dict, sid: str) -> set:
    """场景可加载集：core + stack 闭包 + supplements + 全局文件。"""
    allowed = set(expanded.get(sid, set()))
    pending = [sid]
    seen = set()
    while pending:
        cur = pending.pop()
        if cur in seen:
            continue
        seen.add(cur)
        sc = data["scenes"].get(cur, {})
        for item in sc.get("stack", []):
            target = item["scene"]
            allowed |= expanded.get(target, set())
            pending.append(target)
        for item in sc.get("supplements", []):
            allowed.add(item["file"])
    allowed |= {"SKILL.md", "contracts/rules.json"}
    return allowed


def check_intents(data: dict, root: Path, expanded: dict) -> list:
    """intent 正本唯一、marker 唯一、consumer 有指针、owner 可加载。"""
    issues = []
    files_paths = {f["path"] for f in data["files"]}
    for it in data.get("intents", []):
        owner = it.get("owner", "")
        if "#" not in owner:
            issues.append("E-TOPOLOGY-OWNER: intent %s owner 缺 #anchor" % it.get("id"))
            continue
        rel, anchor = owner.split("#", 1)
        if rel != "SKILL.md" and rel not in files_paths:
            issues.append("E-TOPOLOGY-OWNER: intent %s owner 不在 files：%s" % (it.get("id"), rel))
        if not (root / rel).exists():
            issues.append("E-TOPOLOGY-OWNER: intent %s owner 文件不存在：%s" % (it.get("id"), rel))
            continue
        if not _heading_exists(root, rel, anchor):
            issues.append("E-TOPOLOGY-OWNER: intent %s owner 小节不存在：%s" % (it.get("id"), owner))
            continue
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        marker = "<!-- %s -->" % it.get("marker", "")
        if text.count(marker) != 1:
            issues.append("E-TOPOLOGY-OWNER: intent %s marker 必须恰好一次（当前 %d）"
                          % (it.get("id"), text.count(marker)))
        short = rel.split("references/", 1)[-1]
        for consumer in it.get("consumers", []):
            cp = root / consumer
            if not cp.exists():
                issues.append("E-TOPOLOGY-DEADREF: intent %s consumer 不存在：%s"
                              % (it.get("id"), consumer))
                continue
            ct = cp.read_text(encoding="utf-8", errors="replace")
            if rel not in ct and short not in ct:
                issues.append("E-TOPOLOGY-DEADREF: intent %s consumer %s 缺指向 owner 的指针"
                              % (it.get("id"), consumer))
        if not any(rel in _allowed_files(data, expanded, sid) for sid in it.get("scenes", [])):
            issues.append("E-TOPOLOGY-OWNER: intent %s owner %s 不在任何声明场景的 core/stack/supplements"
                          % (it.get("id"), rel))
    return issues


def check_intent_pointers(data: dict, root: Path, expanded: dict) -> list:
    """已登记 consumer 在场景内引用 owner 时，owner 必须在该场景可加载。"""
    issues = []
    for it in data.get("intents", []):
        rel = it.get("owner", "").split("#", 1)[0]
        for consumer in it.get("consumers", []):
            for sid in it.get("scenes", []):
                if consumer not in expanded.get(sid, set()):
                    continue
                if rel not in _allowed_files(data, expanded, sid):
                    issues.append(
                        "E-TOPOLOGY-DEADREF: intent %s 在场景 %s：%s 引用 %s 不在 core/stack/supplements"
                        % (it.get("id"), sid, consumer, rel))
    return issues


def check_load_table(root: Path, data: dict, expanded: dict) -> list:
    """SKILL.md 加载场景表与契约 scenes 一致（E-TOPOLOGY-SCENES）。"""
    issues = []
    token_names = _token_names(data)
    text = (root / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    start = text.find("## 加载场景表")
    end = text.find("## 场景叠加与补读")
    if start != -1 and end > start:
        text = text[start:end]
    rows = {}
    for ln in text.splitlines():
        m = re.match(r"^\|\s*`([a-z0-9-]+)`\s*\|", ln)
        if not m:
            continue
        rows[m.group(1)] = set(_expand_files(
            re.findall(r"`(references/[^`]+)`", ln), token_names))
    for sid in data["scenes"]:
        if sid not in rows:
            issues.append("E-TOPOLOGY-SCENES: SKILL.md 场景表缺行 %s" % sid)
            continue
        want = expanded.get(sid, set())
        got = rows[sid]
        if got != want:
            issues.append("E-TOPOLOGY-SCENES: SKILL.md 场景 %s 文件不符（缺 %s 多 %s）"
                          % (sid, sorted(want - got), sorted(got - want)))
    return issues


def check_skill_supplement_table(skill_text: str, root: Path) -> list:
    """SKILL.md 补读表中的 file + 「section」必须能在目标文件中找到标题。"""
    issues = []
    start = skill_text.find("**补读表**")
    end = skill_text.find("**补读失败**", start if start != -1 else 0)
    if start == -1:
        return issues
    block = skill_text[start:end if end != -1 else len(skill_text)]
    for ln in block.splitlines():
        if not ln.lstrip().startswith("|"):
            continue
        files = re.findall(r"`([^`]+\.md)`", ln)
        sections = re.findall(r"「([^」]+)」", ln)
        for rel in files:
            if not rel.startswith("references/"):
                rel = "references/" + rel
            for section in sections:
                if not _heading_exists(root, rel, section):
                    issues.append("E-TOPOLOGY-DEADREF: SKILL.md 补读表小节不存在 %s#%s"
                                  % (rel, section))
    return issues


def check_section_refs(data: dict, root: Path) -> list:
    """窄版小节引用检查：supplements[].section + SKILL 补读表；不扫散文 §。"""
    issues = []
    for sid, sc in data.get("scenes", {}).items():
        for item in sc.get("supplements", []):
            rel, section = item.get("file"), item.get("section")
            if rel and section and not _heading_exists(root, rel, section):
                issues.append("E-TOPOLOGY-DEADREF: 场景 %s supplement 小节不存在 %s#%s"
                              % (sid, rel, section))
    skill_path = root / "SKILL.md"
    if skill_path.exists():
        issues += check_skill_supplement_table(
            skill_path.read_text(encoding="utf-8", errors="replace"), root)
    return issues


def coverage(path: Path | None = None, strict: bool = True) -> dict:
    """拓扑检查 + 场景覆盖 + 加载表 + intent 登记/指针闭合。"""
    root = skill_root()
    data = load(path)
    base = topology(path)
    issues = list(base["issues"])
    scene_issues, expanded = check_scenes(data, root)
    issues += scene_issues
    issues += check_load_table(root, data, expanded)
    issues += check_intents(data, root, expanded)
    if strict:
        issues += check_intent_pointers(data, root, expanded)
    return {
        "ok": not issues,
        "files": base["files"],
        "rules": base["rules"],
        "scenes": len(data["scenes"]),
        "intents": len(data.get("intents", [])),
        "strict_pointers": strict,
        "error_codes": base["error_codes"],
        "version": base["version"],
        "issues": issues,
    }


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

    # 3. 规则 owner 可解析
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

    # 6. 版本四方一致
    skill_version = _skill_md_version(root)
    issues += check_versions(skill_version, data.get("version", ""),
                             root / "skill-dependencies.json",
                             root / "evals" / "evals.json")

    # 7. 全仓错误码 ⊆ 契约声明
    errs = data["constants"]["errors"]
    declared = set(errs["E"]) | set(errs["W"])
    used, code_issues = check_error_codes(declared, root)
    issues += code_issues

    # 8. operations.md 速查表双向覆盖
    ops_path = root / "references" / "ops" / "scripts.md"
    if ops_path.exists():
        issues += check_mirror(declared, ops_path.read_text(encoding="utf-8", errors="replace"))
    else:
        issues.append("E-TOPOLOGY-MIRROR: ops/scripts.md 不存在")

    # 9. lead_words 双写一致
    handout_path = root / "references" / "ops" / "typography.md"
    if handout_path.exists():
        issues += check_lead_words(data["constants"]["headings"]["lead_words"],
                                   handout_path.read_text(encoding="utf-8", errors="replace"))
    else:
        issues.append("E-TOPOLOGY-LEADWORDS: ops/typography.md 不存在")

    # 9.5 补读/supplement 小节必须存在（窄版；不扫散文 §）
    issues += check_section_refs(data, root)

    # 10. T/F/R 编号引用必有定义
    rule_ids = {r["id"] for r in data["rules"]}
    ref_texts = []
    skill_path = root / "SKILL.md"
    if skill_path.exists():
        ref_texts.append(("SKILL.md", skill_path.read_text(encoding="utf-8", errors="replace")))
    for f in files:
        p = root / f["path"]
        if p.exists():
            ref_texts.append((f["path"], p.read_text(encoding="utf-8", errors="replace")))
    issues += check_number_refs(rule_ids, ref_texts)

    return {
        "ok": not issues,
        "files": len(files),
        "rules": len(data["rules"]),
        "error_codes": {"used": len(used), "declared": len(declared)},
        "version": skill_version,
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

    def ver_ok():
        root = skill_root()
        v = _skill_md_version(root)
        assert not check_versions(v, v, root / "skill-dependencies.json", root / "evals" / "evals.json")

    chk("versions aligned", ver_ok)

    def ver_drift():
        root = skill_root()
        v = _skill_md_version(root)
        issues = check_versions("9.9.9", v, root / "skill-dependencies.json", root / "evals" / "evals.json")
        assert issues and all(i.startswith("E-TOPOLOGY-VERSION") for i in issues), issues

    chk("version drift detected", ver_drift)

    def codes_unknown():
        used, issues = check_error_codes({"E-CONTRACT-INVALID"}, skill_root())
        assert used, "真实仓库应扫到错误码"
        assert issues and all(i.startswith("E-TOPOLOGY-ERRORCODE") for i in issues), issues[:3]

    chk("undeclared code detected", codes_unknown)

    def mirror_both_ways():
        a, b, c = ("E-" + "ZQX" + "-A", "E-" + "ZQX" + "-B", "E-" + "ZRX" + "-C")
        assert check_mirror({a}, "x `%s` y" % a) == []
        issues = check_mirror({a, b}, "`%s` 额外 `%s`" % (a, c))
        assert any(c in i for i in issues) and any(b in i for i in issues), issues
        root, child = "E-" + "ZSY", "E-" + "ZSY" + "-CHILD"
        assert check_mirror({root, child}, "`%s` 触发条件" % child) == []

    chk("mirror bidirectional", mirror_both_ways)

    def leadwords_both_ways():
        t = "**canonical 集合**（脚本必须全部接受）：`解`、`答`"
        assert check_lead_words(["解", "答"], t) == []
        issues = check_lead_words(["解", "证明"], t)
        assert any("证明" in i for i in issues) and any("答" in i for i in issues), issues
        assert check_lead_words(["解"], "无标记文本") == \
            ["E-TOPOLOGY-LEADWORDS: ops/typography.md 缺 canonical 集合行"]

    chk("leadwords bidirectional", leadwords_both_ways)

    def deadref_ok():
        root = skill_root()
        d = load()
        ids = {r["id"] for r in d["rules"]}
        texts = [(f["path"], (root / f["path"]).read_text(encoding="utf-8", errors="replace"))
                 for f in d["files"]]
        texts.append(("SKILL.md", (root / "SKILL.md").read_text(encoding="utf-8", errors="replace")))
        assert not check_number_refs(ids, texts), "真实仓库存在未定义编号引用"

    chk("number refs defined", deadref_ok)

    def deadref_catch():
        issues = check_number_refs({"R5", "T01"}, [("t.md", "见（R05）与（T01），但（F99）未定义")])
        assert len(issues) == 1 and "F99" in issues[0], issues
        assert issues[0].startswith("E-TOPOLOGY-DEADREF")

    chk("dead number ref detected", deadref_catch)

    def cov_ok():
        r = coverage()
        assert r["ok"], r["issues"]

    chk("coverage clean", cov_ok)

    def cov_missing_scene():
        root = skill_root()
        d = load()
        d["rules"] = [dict(r, scenes=[]) if r["id"] == "R1" else r for r in d["rules"]]
        issues, _ = check_scenes(d, root)
        assert any("R1" in i for i in issues), issues

    chk("coverage missing scene detected", cov_missing_scene)

    def group_slugs_mismatch():
        d = json.loads(default_path().read_text(encoding="utf-8"))
        d["constants"]["group_slugs"].pop(next(iter(d["constants"]["group_slugs"])))
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
            p = Path(f.name)
        try:
            load(p)
        except ContractError as e:
            assert e.code == "E-CONTRACT-INVALID" and "group_slugs" in e.message, e.message
            return
        finally:
            p.unlink(missing_ok=True)
        raise AssertionError("group_slugs key drift not caught")

    chk("group_slugs key drift detected", group_slugs_mismatch)

    def discipline_slugs_dup():
        d = json.loads(default_path().read_text(encoding="utf-8"))
        d["constants"]["discipline_slugs"].append(d["constants"]["discipline_slugs"][0])
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
            p = Path(f.name)
        try:
            load(p)
        except ContractError as e:
            assert e.code == "E-CONTRACT-INVALID" and "discipline_slugs" in e.message, e.message
            return
        finally:
            p.unlink(missing_ok=True)
        raise AssertionError("discipline_slugs duplicate not caught")

    chk("discipline_slugs duplicate detected", discipline_slugs_dup)

    def token_expand():
        d = load()
        names = _token_names(d)
        got = _expand_files(["a/{group}-teach.md"], names)
        assert len(got) == len(d["constants"]["subject_families"]), got
        assert "a/math-teach.md" in got, got
        got2 = _expand_files(["b/{discipline}.md"], names)
        assert len(got2) == len(d["constants"]["discipline_slugs"]), got2
        assert "b/calculus.md" in got2, got2
        assert _expand_files(["c/common.md"], names) == ["c/common.md"]

    chk("token expansion", token_expand)

    def loadtable_drift():
        root = skill_root()
        d = load()
        _, expanded = check_scenes(d, root)
        text = (root / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        bad = text.replace("references/ops/formulas.md", "references/ops/formulasX.md", 1)
        before = (root / "SKILL.md").read_bytes()
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "SKILL.md").write_text(bad, encoding="utf-8")
            issues = check_load_table(Path(td), d, expanded)
        after = (root / "SKILL.md").read_bytes()
        assert before == after, "selftest must not modify real SKILL.md"
        assert issues and all(i.startswith("E-TOPOLOGY-SCENES") for i in issues), issues

    chk("load table drift detected", loadtable_drift)

    def intent_dup():
        d = json.loads(default_path().read_text(encoding="utf-8"))
        d["intents"] = list(d.get("intents", []))
        d["intents"].append(dict(d["intents"][0]))
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
            p = Path(f.name)
        try:
            load(p)
        except ContractError as e:
            assert e.code == "E-CONTRACT-INVALID" and "intent" in e.message, e.message
            return
        finally:
            p.unlink(missing_ok=True)
        raise AssertionError("duplicate intent scope not caught")

    chk("duplicate intent scope detected", intent_dup)

    def intent_clean():
        d = load()
        root = skill_root()
        _, expanded = check_scenes(d, root)
        owner_issues = check_intents(d, root, expanded)
        pointer_issues = check_intent_pointers(d, root, expanded)
        assert not owner_issues, owner_issues[:3]
        assert not pointer_issues, pointer_issues[:3]

    chk("intents and pointers clean", intent_clean)

    def pointer_unloadable():
        d = load()
        root = skill_root()
        _, expanded = check_scenes(d, root)
        d2 = json.loads(json.dumps(d))
        d2["intents"].append({
            "id": "I-TEST", "scope": "x",
            "owner": "references/handout/figures.md#图像可视化双轨",
            "marker": "intent:I-TEST@x",
            "consumers": ["references/handout/quality.md"],
            "scenes": ["s5-close"],
        })
        issues = check_intent_pointers(d2, root, expanded)
        assert any("I-TEST" in i for i in issues), issues

    chk("unloadable intent pointer detected", pointer_unloadable)

    def section_refs_clean():
        issues = check_section_refs(load(), skill_root())
        assert not issues, issues[:3]

    chk("section refs clean", section_refs_clean)

    def missing_scene_file():
        d = json.loads(default_path().read_text(encoding="utf-8"))
        d["scenes"]["entry"]["files"].append("references/__missing__.md")
        issues, _ = check_scenes(d, skill_root())
        assert any("文件不存在" in i for i in issues), issues

    chk("missing rule file detected", missing_scene_file)

    def empty_section_file():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "references").mkdir()
            (root / "references" / "empty.md").write_text("", encoding="utf-8")
            d = {"scenes": {"s": {"supplements": [{
                "file": "references/empty.md",
                "section": "不存在",
                "when": "selftest",
                "intent": "I-TEST@x",
            }]}}}
            issues = check_section_refs(d, root)
            assert any("supplement 小节不存在" in i for i in issues), issues

    chk("empty rule file section detected", empty_section_file)

    def supplement_section_missing():
        d = json.loads(default_path().read_text(encoding="utf-8"))
        d["scenes"]["s3-teach"]["supplements"].append({
            "file": "references/assessment/generation.md",
            "section": "不存在的小节",
            "when": "selftest",
            "intent": "I-SELF-TEST-VS-GROUP@handout",
        })
        issues = check_section_refs(d, skill_root())
        assert any("supplement 小节不存在" in i for i in issues), issues

    chk("supplement section missing detected", supplement_section_missing)

    def skill_supplement_drift():
        root = skill_root()
        text = (root / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        bad = text.replace("「题量预算与自测≠题组」", "「不存在的小节」", 1)
        issues = check_skill_supplement_table(bad, root)
        assert any("SKILL.md 补读表小节不存在" in i for i in issues), issues

    chk("SKILL supplement section drift detected", skill_supplement_drift)

    def owner_anchor_missing():
        d = load()
        root = skill_root()
        _, expanded = check_scenes(d, root)
        d2 = json.loads(json.dumps(d))
        d2["intents"][0]["owner"] = "references/routing/triggers.md#不存在的小节"
        issues = check_intents(d2, root, expanded)
        assert any("owner 小节不存在" in i for i in issues), issues

    chk("owner anchor missing detected", owner_anchor_missing)

    def consumer_pointer_missing():
        d = load()
        root = skill_root()
        _, expanded = check_scenes(d, root)
        d2 = json.loads(json.dumps(d))
        d2["intents"][0]["consumers"] = ["references/ops/composition.md"]
        issues = check_intents(d2, root, expanded)
        assert any("缺指向 owner 的指针" in i for i in issues), issues

    chk("consumer pointer missing detected", consumer_pointer_missing)

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
    g.add_argument("--coverage", action="store_true")
    g.add_argument("--get", metavar="DOTTED")
    ap.add_argument("--strict-pointers", action="store_true",
                    help="显式开启指针闭合检查（当前默认开启）")
    ap.add_argument("--no-strict-pointers", action="store_true",
                    help="关闭指针闭合检查，仅报告 intent 正本/consumer 问题")
    args = ap.parse_args(argv)
    try:
        if args.selftest:
            return _selftest()
        if args.topology:
            r = topology()
            print(json.dumps(r, ensure_ascii=False, indent=1))
            return 0 if r["ok"] else 1
        if args.coverage:
            r = coverage(strict=not args.no_strict_pointers)
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
