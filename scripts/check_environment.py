#!/usr/bin/env python3
"""check_environment.py - 环境诊断（只读，stdlib-only）。

读取包内 skill-dependencies.json 依赖清单，逐项执行检查并输出
ready / needs_setup / unavailable。只有 ready 可以继续；其他状态必须停止，
处理缺失项后重新检查。文件写入与来源检索在实际动作边界验证，不属于本机器清单。
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
DEPENDENCY_TYPES = {"runtime"}
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
    top_allowed = {"schema_version", "capabilities", "dependencies"}
    dependency_allowed = {"id", "type", "required", "auth_type", "capabilities", "checks", "setup"}
    check_allowed = {"id", "type", "required", "min_version", "capabilities"}
    setup_allowed = {"official_home_url", "official_docs_url", "download_url", "login_url", "credential_url", "console_path", "scopes", "credential_storage", "steps", "verify", "rotate_or_revoke", "security", "verified_at", "applies_to_version"}
    if set(manifest) - top_allowed:
        raise ValueError(f"清单包含未知顶层字段：{sorted(set(manifest) - top_allowed)}")
    if manifest.get("schema_version") != "2":
        raise ValueError("schema_version 必须为字符串 2")
    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities or not all(isinstance(item, str) and item for item in capabilities):
        raise ValueError("capabilities 必须是非空字符串数组")
    declared_capabilities = set(capabilities)
    dependencies = manifest.get("dependencies")
    if not isinstance(dependencies, list):
        raise ValueError("dependencies 必须是数组")
    seen = set()
    covered_capabilities = set()
    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            raise ValueError(f"dependencies[{index}] 必须是对象")
        if set(dependency) - dependency_allowed:
            raise ValueError(f"dependencies[{index}] 含未知字段：{sorted(set(dependency) - dependency_allowed)}")
        dependency_id = dependency.get("id")
        if not isinstance(dependency_id, str) or not dependency_id or dependency_id in seen:
            raise ValueError(f"dependencies[{index}].id 缺失或重复")
        seen.add(dependency_id)
        if dependency.get("type") not in DEPENDENCY_TYPES:
            raise ValueError(f"dependencies[{index}].type 无效")
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
        covered_capabilities.update(dependency_capabilities)
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
            # 多检查必须逐个声明受影响能力，避免漏声明导致无关能力被一并阻断。
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
                                 "——不声明会默认影响全部能力，导致无关能力被一并阻断")
        if dependency.get("required") is True and required_checks == 0:
            raise ValueError(f"必需依赖 {dependency_id} 至少需要一个必需检查")
        setup = dependency.get("setup")
        required_setup = {"official_home_url", "official_docs_url", "steps", "verify", "security", "verified_at", "applies_to_version"}
        if not isinstance(setup, dict) or not required_setup <= set(setup) or set(setup) - setup_allowed:
            raise ValueError(f"依赖 {dependency_id} 配置说明缺失或含未知字段")
        for field in ("official_home_url", "official_docs_url", "download_url", "login_url", "credential_url"):
            if field in setup and (not isinstance(setup[field], str) or not setup[field].startswith("https://")):
                raise ValueError(f"依赖 {dependency_id} 的 {field} 必须为 HTTPS URL")
        steps = setup.get("steps")
        if (not isinstance(steps, list) or not steps
                or not all(isinstance(step, str) and step.strip() for step in steps)):
            raise ValueError(f"依赖 {dependency_id} 的 setup.steps 必须是非空字符串数组")
        for field in ("verify", "security", "verified_at", "applies_to_version"):
            if not isinstance(setup.get(field), str) or not setup[field].strip():
                raise ValueError(f"依赖 {dependency_id} 的 setup.{field} 必须是非空字符串")
        auth_type = dependency.get("auth_type")
        if auth_type not in {"none", "browser-login", "token", "api-key", "oauth", "service-account"}:
            raise ValueError(f"依赖 {dependency_id} 的 auth_type 无效")
    uncovered = declared_capabilities - covered_capabilities
    if uncovered:
        raise ValueError(f"以下能力没有可执行检查覆盖：{sorted(uncovered)}")


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
        return "unavailable"
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
            "schema_version": "2",
            "capabilities": ["功能甲"],
            "dependencies": [{
                "id": "d1", "type": "runtime", "required": True, "auth_type": "none",
                "capabilities": ["功能甲"],
                "checks": [{"id": "c1", "type": "python", "required": True, "min_version": "3.8",
                            "capabilities": ["功能甲"]}],
                "setup": {"official_home_url": "https://x", "official_docs_url": "https://y",
                          "steps": ["s"], "verify": "v", "security": "sec",
                          "verified_at": "2026-10-15", "applies_to_version": "5.2.1"},
            }],
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
    m = base(); m["functional_degradations"] = []; cases.append(m)                         # 已删除的降级字段
    m = base(); m["dependencies"][0]["degradation"] = []; cases.append(m)                  # 已删除的依赖降级字段
    m = base(); m["dependencies"] = []; cases.append(m)                                    # 声明能力无检查覆盖不得 ready
    m = base(); m["unknown_key"] = 1; cases.append(m)                                      # 未知顶层字段
    # E01 新增：依赖 required 严格布尔；capabilities 元素必须为字符串；min_version 严格格式/类型；check.id 必填唯一
    m = base(); m["dependencies"][0]["required"] = "false"; cases.append(m)                # 字符串 required 不得误当 true
    m = base(); m["dependencies"][0].pop("required"); cases.append(m)                      # required 键缺失
    m = base(); m["dependencies"][0]["capabilities"] = [{}]; cases.append(m)               # 非字符串能力元素（原裸崩 TypeError）
    m = base(); m["dependencies"][0]["type"] = "bogus"; cases.append(m)                    # 未知依赖类型
    m = base(); m["dependencies"][0].pop("type"); cases.append(m)                          # 依赖类型缺失
    m = base(); m["dependencies"][0]["setup"]["steps"] = "s"; cases.append(m)              # steps 必须为数组
    m = base(); m["dependencies"][0]["setup"]["steps"] = [1]; cases.append(m)              # steps 元素必须为字符串
    m = base(); m["dependencies"][0]["setup"]["verify"] = ["v"]; cases.append(m)           # verify 必须为字符串
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

    # 版本判定：任何被请求能力的检查失败都阻断，不给 partial 或降级出口
    from types import SimpleNamespace
    import io
    import contextlib
    saved_sys = sys
    try:
        globals()["sys"] = SimpleNamespace(version_info=(3, 9, 18))
        ok = ok and check_item({"id": "v", "type": "python", "required": True,
                                "min_version": "3.10", "capabilities": ["基础"]})["status"] == "unavailable"
        ok = ok and dependency_status(
            [{"id": "g", "required": False, "status": "unavailable", "capabilities": ["KP"]}],
            {"基础"}) == "ready"
        ok = ok and dependency_status(
            [{"id": "g", "required": False, "status": "unavailable", "capabilities": ["KP"]}],
            {"KP"}) == "unavailable"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_old = main(["--manifest", str(manifest_path), "--capability", "进度校验与证据验证"])
        out_old = json.loads(buf.getvalue())
        ok = ok and rc_old == 1 and out_old["status"] == "unavailable"
        ok = ok and "functional_degradations" not in out_old and "unmapped_capabilities" not in out_old
        ok = ok and "停止" in out_old["next_action"]
    finally:
        globals()["sys"] = saved_sys

    # 当前解释器（≥3.10）：全部机器可检查能力 ready，且无降级字段
    for args in (["--manifest", str(manifest_path), "--capability", "进度校验与证据验证"],
                 ["--manifest", str(manifest_path)]):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(args)
        output = json.loads(buf.getvalue())
        ok = ok and rc == 0 and output["status"] == "ready"
        ok = ok and "functional_degradations" not in output and "unmapped_capabilities" not in output
        ok = ok and "partial" not in buf.getvalue()

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

    # 状态只覆盖本次请求能力；任何受影响能力未就绪都阻断，不附带替代方案。
    scope = set(args.capability) or set(manifest["capabilities"])
    results = []
    has_missing = False
    has_unavailable = False
    for dependency in dependencies:
        check_results = [check_item(item) for item in dependency["checks"]]
        dependency_state = dependency_status(check_results, scope)
        dep_capabilities = [cap for cap in dependency["capabilities"] if cap in scope]
        if dependency_state == "missing":
            has_missing = True
        elif dependency_state != "ready":
            has_unavailable = True
        scoped_checks = [item for item in check_results if check_in_scope(item, scope)]
        failures = [item for item in scoped_checks if item["status"] != "ready"]
        item = {
            "id": dependency["id"],
            "type": dependency["type"],
            "required": bool(dependency["required"]),
            "capabilities": dep_capabilities,
            "status": dependency_state,
            "checks": failures if failures else [{"id": check["id"], "status": "ready", "reason_code": "ok"} for check in scoped_checks],
        }
        if dependency_state != "ready":
            item["setup"] = filtered_setup(dependency["setup"])
        results.append(item)

    if has_missing:
        status = "needs_setup"
    elif has_unavailable:
        status = "unavailable"
    else:
        status = "ready"
    output = {
        "status": status,
        "requested_capabilities": args.capability,
        "dependencies": results if status == "ready" else [item for item in results if item["status"] != "ready"],
        "next_action": {
            "ready": "进入正常流程",
            "needs_setup": "停止当前运行；完成缺失项配置后重新检查，ready 后从原阶段继续",
            "unavailable": "停止当前运行；处理故障后重新检查，ready 后从原阶段继续",
        }[status],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if status == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
