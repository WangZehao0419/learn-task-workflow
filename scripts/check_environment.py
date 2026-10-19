#!/usr/bin/env python3
"""check_environment.py - 环境诊断（只读，stdlib-only）。

读取包内 skill-dependencies.json 依赖清单，逐项执行检查并输出四状态
（ready / partial / needs_setup / unavailable）路由结论。当前清单仅含
python 运行时检查项；声明了但无可检查依赖的能力（学习数据落盘、备料来源
检索）输出 unmapped_capabilities（not_checkable），不报清单错误。
检查器全程只读：不写盘、不安装、不发起网络请求。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# 版本声明只接受「纯数字点分」格式（如 3 / 3.8 / 3.8.10）。
# 用 fullmatch 整体匹配，拒绝前后缀垃圾（"3.8.9999999garbage"、"garbage3.8"）与
# 非字符串强转（数字 3、布尔 False）——不得再用 re.search + str() 宽松放行。
VERSION_RE = re.compile(r"\d+(?:\.\d+)*\Z")
VALID_TYPES = {"python"}
EVIDENCE_LABELS = {"已验证", "部分验证", "推断", "未验证"}
SETUP_OUTPUT_FIELDS = {
    "official_home_url", "official_docs_url", "download_url", "login_url",
    "credential_url", "console_path", "scopes", "credential_storage", "steps",
    "verify", "rotate_or_revoke", "verified_at", "applies_to_version",
}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON 根节点必须是对象：{path}")
    return data


def parse_version(value: str) -> tuple[int, int, int] | None:
    """严格解析版本声明：仅接受纯数字点分字符串并整体匹配（fullmatch）。

    返回补零到三段的元组（与 sys.version_info[:3] 可比）；任何非字符串或
    含前后缀垃圾的输入返回 None（调用方据此判定「未声明/声明无效」）。
    """
    if not isinstance(value, str) or not VERSION_RE.fullmatch(value):
        return None
    parts = [int(item) for item in value.split(".")]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def filtered_setup(setup: Any) -> dict[str, Any]:
    if not isinstance(setup, dict):
        return {}
    return {key: setup[key] for key in SETUP_OUTPUT_FIELDS if key in setup}


def validate_manifest(manifest: dict[str, Any]) -> None:
    top_allowed = {"schema_version", "capabilities", "dependencies", "functional_degradations",
                   "scripts_contract", "verification"}
    dependency_allowed = {"id", "type", "required", "auth_type", "capabilities", "checks", "setup", "degradation"}
    check_allowed = {"id", "type", "required", "min_version", "capabilities"}
    setup_allowed = {"official_home_url", "official_docs_url", "download_url", "login_url", "credential_url", "console_path", "scopes", "credential_storage", "steps", "verify", "rotate_or_revoke", "security", "verified_at", "applies_to_version"}
    degradation_allowed = {"capability", "trigger", "fallback", "user_input", "limitations", "evidence_label", "recovery", "stop_condition"}
    if set(manifest) - top_allowed:
        raise ValueError(f"清单包含未知顶层字段：{sorted(set(manifest) - top_allowed)}")
    if manifest.get("schema_version") != "1":
        raise ValueError("schema_version 必须为字符串 1")
    # 可选扩展块（v2.3 起）：CLI 行为契约与验证口径。缺省合法（向后兼容）。
    contract = manifest.get("scripts_contract")
    if contract is not None:
        if not isinstance(contract, list) or not all(isinstance(item, dict) for item in contract):
            raise ValueError("scripts_contract 必须是对象数组")
    verification = manifest.get("verification")
    if verification is not None:
        if not isinstance(verification, dict) or not isinstance(verification.get("selftest", []), list):
            raise ValueError("verification 必须是含 selftest 数组的对象")
    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities or not all(isinstance(item, str) and item for item in capabilities):
        raise ValueError("capabilities 必须是非空字符串数组")
    declared_capabilities = set(capabilities)
    dependencies = manifest.get("dependencies")
    if not isinstance(dependencies, list):
        raise ValueError("dependencies 必须是数组")
    functional = manifest.get("functional_degradations")
    if not isinstance(functional, list) or not functional:
        raise ValueError("functional_degradations 必须是非空数组")
    covered = set()
    required_degradation_fields = {"capability", "trigger", "fallback", "user_input", "limitations", "evidence_label", "recovery", "stop_condition"}
    for index, item in enumerate(functional):
        if not isinstance(item, dict) or not required_degradation_fields <= set(item) or set(item) - degradation_allowed:
            raise ValueError(f"functional_degradations[{index}] 字段不完整或含未知字段")
        for field in required_degradation_fields:
            if not isinstance(item[field], str) or (field != "user_input" and not item[field].strip()):
                raise ValueError(f"functional_degradations[{index}].{field} 无效")
        if item["evidence_label"] not in EVIDENCE_LABELS:
            raise ValueError(f"functional_degradations[{index}].evidence_label 无效")
        covered.add(item["capability"])
    if declared_capabilities - covered:
        raise ValueError(f"以下功能缺少普通功能降级：{sorted(declared_capabilities - covered)}")
    if covered - declared_capabilities:
        raise ValueError(f"普通功能降级引用未声明功能：{sorted(covered - declared_capabilities)}")
    seen = set()
    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            raise ValueError(f"dependencies[{index}] 必须是对象")
        if set(dependency) - dependency_allowed:
            raise ValueError(f"dependencies[{index}] 含未知字段：{sorted(set(dependency) - dependency_allowed)}")
        dependency_id = dependency.get("id")
        if not isinstance(dependency_id, str) or not dependency_id or dependency_id in seen:
            raise ValueError(f"dependencies[{index}].id 缺失或重复")
        seen.add(dependency_id)
        # E01：required 必须是布尔——字符串 "false" 不得被 bool() 误当 true，键缺失也必须拒绝
        if not isinstance(dependency.get("required"), bool):
            raise ValueError(f"dependencies[{index}].required 必须是布尔值")
        dependency_capabilities = dependency.get("capabilities")
        # E01：逐元素校验类型，避免 [{}] 这类非字符串元素进入 set 运算裸崩 TypeError
        if (not isinstance(dependency_capabilities, list) or not dependency_capabilities
                or not all(isinstance(cap, str) and cap for cap in dependency_capabilities)):
            raise ValueError(f"dependencies[{index}].capabilities 必须是非空字符串数组")
        unknown = set(dependency_capabilities) - declared_capabilities
        if unknown:
            raise ValueError(f"依赖 {dependency_id} 引用了未声明功能：{sorted(unknown)}")
        checks = dependency.get("checks")
        if not isinstance(checks, list) or not checks or not all(isinstance(item, dict) for item in checks):
            raise ValueError(f"依赖 {dependency_id} 的 checks 必须是非空对象数组")
        required_checks = 0
        seen_check_ids = set()
        for check in checks:
            if set(check) - check_allowed:
                raise ValueError(f"依赖 {dependency_id} 的检查含未知字段：{sorted(set(check) - check_allowed)}")
            # E01：check.id 必填，且在依赖内唯一
            check_id = check.get("id")
            if not isinstance(check_id, str) or not check_id or check_id in seen_check_ids:
                raise ValueError(f"依赖 {dependency_id} 的检查 id 缺失或重复：{check_id!r}")
            seen_check_ids.add(check_id)
            if check.get("type") not in VALID_TYPES or not isinstance(check.get("required"), bool):
                raise ValueError(f"依赖 {dependency_id} 存在无效检查")
            if check["required"]:
                required_checks += 1
            # E02：check 可声明其影响的能力；省略时继承依赖声明的全部能力。
            # 但「多检查」必须逐个声明——否则漏声明会默认影响全部，导致过度降级。
            check_capabilities = check.get("capabilities")
            if check_capabilities is not None:
                if (not isinstance(check_capabilities, list) or not check_capabilities
                        or not all(isinstance(cap, str) and cap for cap in check_capabilities)):
                    raise ValueError(f"依赖 {dependency_id} 的检查 {check_id} 的 capabilities 必须是非空字符串数组")
                if set(check_capabilities) - declared_capabilities:
                    raise ValueError(f"依赖 {dependency_id} 的检查 {check_id} 引用了未声明功能："
                                     f"{sorted(set(check_capabilities) - declared_capabilities)}")
            # E01：min_version 必须为字符串且整体匹配声明格式（fullmatch，不做 str 强转/search）
            if "min_version" in check:
                min_version = check["min_version"]
                if not isinstance(min_version, str) or parse_version(min_version) is None:
                    raise ValueError(f"依赖 {dependency_id} 的检查 {check_id} 的 min_version 无效：{min_version!r}")
            if any(field in check for field in ("auth_env", "auth_header", "auth_scheme")):
                raise ValueError(f"依赖 {dependency_id} 的检查项不得携带凭据字段")
        if len(checks) > 1:
            missing_scope = [c.get("id") for c in checks if not c.get("capabilities")]
            if missing_scope:
                raise ValueError(f"依赖 {dependency_id} 含多个检查，以下检查未声明 capabilities：{missing_scope}"
                                 "——不声明会默认影响全部能力，导致过度降级")
        if dependency.get("required") is True and required_checks == 0:
            raise ValueError(f"必需依赖 {dependency_id} 至少需要一个必需检查")
        setup = dependency.get("setup")
        required_setup = {"official_home_url", "official_docs_url", "steps", "verify", "security", "verified_at", "applies_to_version"}
        if not isinstance(setup, dict) or not required_setup <= set(setup) or set(setup) - setup_allowed:
            raise ValueError(f"依赖 {dependency_id} 配置说明缺失或含未知字段")
        for field in ("official_home_url", "official_docs_url", "download_url", "login_url", "credential_url"):
            if field in setup and (not isinstance(setup[field], str) or not setup[field].startswith("https://")):
                raise ValueError(f"依赖 {dependency_id} 的 {field} 必须为 HTTPS URL")
        auth_type = dependency.get("auth_type")
        if auth_type not in {"none", "browser-login", "token", "api-key", "oauth", "service-account"}:
            raise ValueError(f"依赖 {dependency_id} 的 auth_type 无效")
        degradations = dependency.get("degradation")
        if not isinstance(degradations, list) or not degradations:
            raise ValueError(f"依赖 {dependency_id} 缺少依赖故障降级")
        degradation_capabilities = set()
        for degradation in degradations:
            if not isinstance(degradation, dict) or not required_degradation_fields <= set(degradation) or set(degradation) - degradation_allowed:
                raise ValueError(f"依赖 {dependency_id} 的 degradation 字段不完整或含未知字段")
            for field in required_degradation_fields:
                if not isinstance(degradation[field], str) or (field != "user_input" and not degradation[field].strip()):
                    raise ValueError(f"依赖 {dependency_id} 的 degradation.{field} 无效")
            if degradation["evidence_label"] not in EVIDENCE_LABELS:
                raise ValueError(f"依赖 {dependency_id} 的 evidence_label 无效")
            degradation_capabilities.add(degradation["capability"])
        unknown_degradation = degradation_capabilities - set(dependency_capabilities)
        missing_degradation = set(dependency_capabilities) - degradation_capabilities
        if unknown_degradation:
            raise ValueError(f"依赖 {dependency_id} 的降级引用未关联功能：{sorted(unknown_degradation)}")
        if missing_degradation:
            raise ValueError(f"依赖 {dependency_id} 的以下功能缺少降级：{sorted(missing_degradation)}")


def check_item(item: dict[str, Any]) -> dict[str, Any]:
    check_type = item.get("type")
    result = {
        "id": item.get("id", check_type),
        "type": check_type,
        "required": bool(item.get("required", True)),
        "capabilities": list(item.get("capabilities", [])),
        "status": "unavailable",
        "reason_code": "configuration_invalid",
        "detail": "检查定义无效",
    }

    if check_type == "python":
        minimum = parse_version(item.get("min_version"))
        current = sys.version_info[:3]
        ready = minimum is None or current >= minimum
        result.update(status="ready" if ready else "unavailable", reason_code="ok" if ready else "version_incompatible", detail=f"Python {current[0]}.{current[1]}.{current[2]}；最低要求 {item.get('min_version', '未指定')}")
        return result

    return result


def check_in_scope(check_result: dict[str, Any], scope: set[str]) -> bool:
    """E02：检查项是否落在本次请求作用域——以检查声明的受影响能力与 scope 求交。

    未声明能力的检查（防御）视为对全部请求有效。
    """
    capabilities = check_result.get("capabilities") or []
    return not capabilities or bool(set(capabilities) & scope)


def select_dependencies(manifest: dict[str, Any], capabilities: set[str]) -> list[dict[str, Any]]:
    dependencies = manifest["dependencies"]
    if not capabilities:
        return dependencies
    declared = set(manifest["capabilities"])
    unknown = capabilities - declared
    if unknown:
        raise ValueError(f"请求了清单未声明的功能：{sorted(unknown)}")
    selected = [dependency for dependency in dependencies if capabilities & set(dependency["capabilities"])]
    # 允许为空：能力已声明但无可检查依赖（如「学习数据落盘」「备料来源检索」由宿主/模型侧提供）。
    # 这类能力由 main 标 not_checkable 并按 functional_degradations 执行，不得报清单错误。
    return selected


def dependency_status(check_results: list[dict[str, Any]], scope: set[str]) -> str:
    # E02：只统计与本次请求能力（scope）相关的检查；无关检查的失败不波及本次请求
    scoped = [item for item in check_results if check_in_scope(item, scope)]
    required = [item for item in scoped if item["required"]]
    optional = [item for item in scoped if not item["required"]]
    if any(item["status"] == "missing" for item in required):
        return "missing"
    if any(item["status"] == "unavailable" for item in required):
        return "unavailable"
    if any(item["status"] != "ready" for item in optional):
        return "partial"
    return "ready"


def selftest() -> int:
    """清单类型/版本格式严格校验的自测：基线通过 + 六类畸形必须被拒。"""
    ok = True
    manifest_path = Path(__file__).resolve().parents[1] / "skill-dependencies.json"
    try:
        validate_manifest(load_json(manifest_path))
    except Exception:  # noqa: BLE001 - 自测下任何失败都记为不通过
        ok = False

    def base() -> dict[str, Any]:
        return {
            "schema_version": "1",
            "capabilities": ["功能甲"],
            "dependencies": [{
                "id": "d1", "type": "python", "required": True, "auth_type": "none",
                "capabilities": ["功能甲"],
                "checks": [{"id": "c1", "type": "python", "required": True, "min_version": "3.8",
                            "capabilities": ["功能甲"]}],
                "setup": {"official_home_url": "https://x", "official_docs_url": "https://y",
                          "steps": "s", "verify": "v", "security": "sec",
                          "verified_at": "2026-10-15", "applies_to_version": "5.2.1"},
                "degradation": [{"capability": "功能甲", "trigger": "t", "fallback": "f",
                                 "user_input": "", "limitations": "l", "evidence_label": "未验证",
                                 "recovery": "r", "stop_condition": "s"}],
            }],
            "functional_degradations": [{"capability": "功能甲", "trigger": "t", "fallback": "f",
                                         "user_input": "", "limitations": "l", "evidence_label": "未验证",
                                         "recovery": "r", "stop_condition": "s"}],
        }

    try:
        validate_manifest(base())  # 基线必须通过
    except ValueError:
        ok = False

    cases = []
    m = base(); m["dependencies"][0]["checks"][0]["required"] = "true"; cases.append(m)   # 布尔误收字符串
    m = base(); m["schema_version"] = 1; cases.append(m)                                   # 版本号非字符串
    m = base(); m["capabilities"] = "功能甲"; cases.append(m)                              # capabilities 畸形
    m = base(); m["dependencies"][0]["checks"][0]["min_version"] = "abc"; cases.append(m)  # 非法版本
    m = base(); m["functional_degradations"][0]["evidence_label"] = "已核验"; cases.append(m)  # 证据标签非法
    m = base(); m["unknown_key"] = 1; cases.append(m)                                      # 未知顶层字段
    # E01 新增：依赖 required 严格布尔；capabilities 元素必须为字符串；min_version 严格格式/类型；check.id 必填唯一
    m = base(); m["dependencies"][0]["required"] = "false"; cases.append(m)                # 字符串 required 不得误当 true
    m = base(); m["dependencies"][0].pop("required"); cases.append(m)                      # required 键缺失
    m = base(); m["dependencies"][0]["capabilities"] = [{}]; cases.append(m)               # 非字符串能力元素（原裸崩 TypeError）
    for bad in ("3.8.9999999garbage", "garbage3.8", 3, False):                             # 版本前缀/后缀垃圾与非字符串
        m = base(); m["dependencies"][0]["checks"][0]["min_version"] = bad; cases.append(m)
    m = base(); m["dependencies"][0]["checks"][0].pop("id"); cases.append(m)               # check.id 缺失
    m = base(); m["dependencies"][0]["checks"].append(                                    # check.id 重复
        {"id": "c1", "type": "python", "required": False, "capabilities": ["功能甲"]}); cases.append(m)
    m = base(); m["dependencies"][0]["checks"].append(                                    # 多检查漏声明能力
        {"id": "c2", "type": "python", "required": False, "min_version": "3.9"}); cases.append(m)
    for case in cases:
        try:
            validate_manifest(case)
            ok = False  # 未拒绝即失败
        except ValueError:
            pass

    # 单检查可省略 capabilities（继承依赖范围）；多检查必须逐个声明，见上一条拒绝用例
    m = base(); m["dependencies"][0]["checks"][0].pop("capabilities")
    try:
        validate_manifest(m)
    except ValueError:
        ok = False

    # check_item：python 版本满足 → ready；parse_version 严格（不被前后缀垃圾/强转蒙混）
    ok = ok and check_item({"id": "p", "type": "python", "required": True,
                            "min_version": "3.8"})["status"] == "ready"
    ok = ok and parse_version("3.8") == (3, 8, 0)
    ok = ok and parse_version("3.8.10") == (3, 8, 10)
    ok = ok and parse_version("3.8.9999999garbage") is None
    ok = ok and parse_version("garbage3.8") is None
    ok = ok and parse_version(3) is None and parse_version(False) is None
    # select_dependencies：未声明功能 → 拒绝
    try:
        select_dependencies(base(), {"不存在"})
        ok = False
    except ValueError:
        pass

    # 版本判定与按能力降级：3.9 < 最低版本 3.10 → 必需检查失败，整体 unavailable
    from types import SimpleNamespace
    import io
    import contextlib
    saved_sys = sys
    try:
        globals()["sys"] = SimpleNamespace(version_info=(3, 9, 18))
        ok = ok and check_item({"id": "v", "type": "python", "required": True,
                                "min_version": "3.10", "capabilities": ["基础"]})["status"] == "unavailable"
        # 可选检查失败只影响它声明的能力（E02 契约，用合成数据保留覆盖）
        ok = ok and dependency_status(
            [{"id": "g", "required": False, "status": "unavailable", "capabilities": ["KP"]}],
            {"基础"}) == "ready"
        ok = ok and dependency_status(
            [{"id": "g", "required": False, "status": "unavailable", "capabilities": ["KP"]}],
            {"KP"}) == "partial"
        # 端到端：低于最低版本时必需检查失败，整体 unavailable，不得放行
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_old = main(["--manifest", str(manifest_path), "--capability", "进度校验与证据验证"])
        out_old = json.loads(buf.getvalue())
        ok = ok and rc_old == 1 and out_old["status"] == "unavailable"
        ok = ok and not out_old["unmapped_capabilities"]
        # 检查未声明能力时，降级条目继承依赖范围（本例只剩被请求的进度校验）
        ok = ok and {d["capability"] for d in out_old["functional_degradations"]} == {"进度校验与证据验证"}
    finally:
        globals()["sys"] = saved_sys

    # 当前解释器（≥3.10）：可检查能力 ready；默认请求因两项不可检查而 partial
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc_base = main(["--manifest", str(manifest_path), "--capability", "进度校验与证据验证"])
    out_base = json.loads(buf.getvalue())
    ok = ok and rc_base == 0 and out_base["status"] == "ready"
    ok = ok and not out_base["functional_degradations"]
    ok = ok and not out_base["unmapped_capabilities"]

    # 默认请求全部能力：仅两项「无可检查依赖」能力，降级集合应恰为两者
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc_all = main(["--manifest", str(manifest_path)])
    out_all = json.loads(buf.getvalue())
    ok = ok and rc_all == 0 and out_all["status"] == "partial"
    ok = ok and {d["capability"] for d in out_all["functional_degradations"]} == {
        "学习数据落盘", "备料来源检索"}
    ok = ok and {u["capability"] for u in out_all["unmapped_capabilities"]} == {
        "学习数据落盘", "备料来源检索"}

    # 单请求不可检查能力：不报清单错误，返回 not_checkable + 对应降级，状态 partial
    ok = ok and select_dependencies(load_json(manifest_path), {"学习数据落盘"}) == []
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc_unmapped = main(["--manifest", str(manifest_path), "--capability", "学习数据落盘"])
    out_unmapped = json.loads(buf.getvalue())
    ok = ok and rc_unmapped == 0 and out_unmapped["status"] == "partial"
    ok = ok and out_unmapped["dependencies"] == []
    ok = ok and [u["capability"] for u in out_unmapped["unmapped_capabilities"]] == ["学习数据落盘"]
    ok = ok and [d["capability"] for d in out_unmapped["functional_degradations"]] == ["学习数据落盘"]

    print(("OK " if ok else "FAIL ") + "check_environment --selftest")
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="检查当前 Skill 的依赖和运行环境")
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parents[1] / "skill-dependencies.json")
    parser.add_argument("--capability", action="append", default=[], help="本次请求涉及的功能，可重复传入")
    parser.add_argument("--selftest", action="store_true", help="运行内置自测（清单校验契约）")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    try:
        manifest = load_json(args.manifest)
        validate_manifest(manifest)
        dependencies = select_dependencies(manifest, set(args.capability))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "unavailable", "reason_code": "manifest_error", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    except Exception as exc:  # 防御：任何未预期的清单结构异常也必须结构化诊断，绝不裸崩成外部协议 traceback
        print(json.dumps({"status": "unavailable", "reason_code": "manifest_error",
                          "error": f"清单处理异常：{type(exc).__name__}: {exc}"}, ensure_ascii=False, indent=2))
        return 2

    # E02：本次诊断作用域 = 请求能力（为空则视为全部已声明能力）；
    # 状态与输出只按「请求能力 ∩ 失败检查」计算，不波及相关能力。
    scope = set(args.capability) or set(manifest["capabilities"])
    # 声明了但无可检查依赖的能力（如学习数据落盘、备料来源检索）：不参与 check 判定，
    # 单独输出 not_checkable，避免「没检查过」被读成「检查通过」。
    checkable_capabilities: set[str] = set()
    for dependency in manifest["dependencies"]:
        checkable_capabilities.update(dependency["capabilities"])
    unmapped_capabilities = sorted(scope - checkable_capabilities)

    results = []
    has_required_missing = False
    has_required_unavailable = False
    has_optional_problem = False
    # 受影响能力来自失败检查声明的 capabilities；单检查未声明时继承依赖范围。
    # 多检查必须逐个声明（validate_manifest 强制），避免漏声明导致过度降级。
    failed_check_capabilities: set[str] = set()

    for dependency in dependencies:
        check_results = [check_item(item) for item in dependency["checks"]]
        status = dependency_status(check_results, scope)
        dependency_required = bool(dependency["required"])
        # 仅保留落在本次作用域内的能力，避免展开与请求能力无关的功能
        dep_capabilities = [cap for cap in dependency["capabilities"] if cap in scope]
        if dependency_required and status == "missing":
            has_required_missing = True
        elif dependency_required and status == "unavailable":
            has_required_unavailable = True
        elif status in {"missing", "unavailable", "partial"}:
            has_optional_problem = True
        # 仅展示作用域内的检查项（无关检查的失败不进输出）
        scoped_checks = [item for item in check_results if check_in_scope(item, scope)]
        failures = [item for item in scoped_checks if item["status"] != "ready"]
        # 修复：累积「失败检查自身声明的能力」∩「请求范围」，供后续精确生成降级列表
        for failure in failures:
            # 检查未声明能力时继承依赖范围（单检查场景）；多检查则校验器已强制逐个声明
            caps = failure["capabilities"] or dependency["capabilities"]
            failed_check_capabilities.update(cap for cap in caps if cap in scope)
        item = {
            "id": dependency["id"],
            "type": dependency["type"],
            "required": dependency_required,
            "capabilities": dep_capabilities,
            "status": status,
            "checks": failures if failures else [{"id": check["id"], "status": "ready", "reason_code": "ok"} for check in scoped_checks],
        }
        if status == "missing" and dependency_required:
            item["setup"] = filtered_setup(dependency["setup"])
        elif status in {"unavailable", "partial", "missing"}:
            item["degradation"] = [d for d in dependency["degradation"] if d["capability"] in dep_capabilities]
        results.append(item)

    if has_required_missing:
        status = "needs_setup"
    elif has_required_unavailable:
        status = "unavailable"
    elif has_optional_problem or unmapped_capabilities:
        status = "partial"
    else:
        status = "ready"

    visible_results = results if status == "ready" else [item for item in results if item["status"] != "ready"]
    # 修复：功能降级只列「失败检查声明的能力 ∩ 请求范围」，不再按可见依赖的整项能力展开，
    # 保证仅真正受失败检查牵连的能力被降级，其余请求到的能力保持可用。
    affected_capabilities = set(failed_check_capabilities) | set(unmapped_capabilities)
    visible_functional_degradations = [item for item in manifest["functional_degradations"] if item["capability"] in affected_capabilities] if status != "ready" else []
    output = {
        "status": status,
        "requested_capabilities": args.capability,
        "dependencies": visible_results,
        "unmapped_capabilities": [
            {"capability": capability, "status": "not_checkable", "reason_code": "no_dependency",
             "note": "清单未声明可检查依赖；按 functional_degradations 执行，不得声称已验证"}
            for capability in unmapped_capabilities
        ],
        "functional_degradations": visible_functional_degradations,
        "next_action": {
            "ready": "跳过配置引导，进入正常流程",
            "partial": "进入可用流程，只说明受影响或不可机器检查的功能、限制和降级",
            "needs_setup": "只展示缺失必需项的配置步骤，完成后重新检查",
            "unavailable": "展示结构化故障原因、恢复步骤和安全降级",
        }[status],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if status in {"ready", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
