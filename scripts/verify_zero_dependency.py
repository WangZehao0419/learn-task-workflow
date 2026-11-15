#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""零外部依赖机检（AST 静态判定；只读、零网络、幂等、stdlib-only）。

规格 90 的用户故事 49 写着「这次施工不引入任何网络调用或外部依赖，因为零外部依赖是
已经通过机检证明的结构性质」。**这句话在 9.21.24 之前是假的**：全仓 `import ast` 零命中，
没有任何脚本证明过这条性质——它只是一句承诺。本脚本把那句承诺变成会红的断言。

四条判据，各自独立、各自能单独证红：

    E-ZERODEP-THIRDPARTY   import 了既不在标准库、也不是本仓模块的第三方包
    E-ZERODEP-NETWORK      import 了具备联网能力的模块（即使它属于标准库）
    E-ZERODEP-DYNAMIC      用了 __import__ / importlib，绕过静态判定
    E-ZERODEP-STDLIB-NA    （fail closed）解释器没有 sys.stdlib_module_names，
                           无法区分标准库与第三方——判不了就不许判绿

为什么「网络模块即使是标准库也要拦」：标准库里的 socket / urllib / http / ssl /
ftplib / smtplib / imaplib / poplib / telnetlib / xmlrpc 都能直接发起或接收网络连接。
零依赖承诺里说的「零网络调用」不是「没装第三方包」，是**这条代码路径上不存在联网能力**。
把它们放进白名单等于允许偷偷联网。

为什么动态 import 要单独判：`__import__("socket")` 与 `importlib.import_module(name)`
在 AST 上只是一个普通调用，静态分析看不见目标。留这个口子，前三条判据都可以被绕开。

为什么 STDLIB-NA 要 fail closed：Python < 3.10 没有 `sys.stdlib_module_names`。此时
「不在标准库名单里」与「名单不存在」无法区分，写成「名单缺失就跳过」等于让闸口在旧解释器
上自动全绿——那正是本仓反复吃过的假绿。判不了就红，并说清为什么。

扫描范围：`scripts/` 与 `evals/` 下全部 .py（递归）。这两个目录是本技能的运行时与验收面，
第三方依赖出现在这里就会在用户机器上要求 pip install。

用法：
    python -B scripts/verify_zero_dependency.py
    python -B scripts/verify_zero_dependency.py --selftest
    python -B scripts/verify_zero_dependency.py --root <技能根>
退出码：0 全合规；1 有违规或环境不可判定；2 用法错误。
"""
from __future__ import annotations

import argparse
import ast
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rule_contract import skill_root  # noqa: E402
import ltw_exit  # noqa: E402  三态退出码唯一定义处（票 106）

SCAN_DIRS = ("scripts", "evals")

# 具备联网能力的模块：即使是标准库也不许出现（含传输层、协议层与浏览器壳）。
NETWORK_MODULES = frozenset({
    "socket", "ssl", "selectors", "http", "urllib", "urllib2", "urlparse",
    "httplib", "ftplib", "smtplib", "imaplib", "poplib", "nntplib",
    "telnetlib", "xmlrpc", "webbrowser", "asyncio", "socketserver",
    "http.client", "http.server", "urllib.request", "urllib.error",
    "requests", "httpx", "aiohttp", "urllib3", "websocket", "websockets",
})

# 动态 import 的两个入口名。
DYNAMIC_CALLS = frozenset({"__import__", "import_module"})
DYNAMIC_MODULES = frozenset({"importlib"})


def local_module_stems(root: Path):
    """本仓自己的模块名集合：scripts/ 与 evals/ 下 .py 的文件名（不含扩展名）。"""
    stems = set()
    for base in SCAN_DIRS:
        d = root / base
        if d.is_dir():
            stems |= {p.stem for p in d.glob("*.py") if p.is_file()}
    return stems


def target_files(root: Path):
    out = []
    for base in SCAN_DIRS:
        d = root / base
        if d.is_dir():
            out.extend(sorted(p for p in d.rglob("*.py") if p.is_file()))
    return out


def scan_file(path: Path, root: Path, stdlib, local):
    """返回 (problems, stats)。problems 是 [(code, 说明)]。"""
    problems = []
    rel = path.relative_to(root).as_posix()
    try:
        src = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        problems.append(("E-ZERODEP-UNREADABLE", "%s :: 不可读或非 UTF-8（%s）" % (rel, exc)))
        return problems, {"imports": 0}
    try:
        tree = ast.parse(src, filename=rel)
    except SyntaxError as exc:
        problems.append(("E-ZERODEP-UNREADABLE",
                         "%s :: 语法错误，静态判定无从进行（第 %s 行：%s）"
                         % (rel, exc.lineno, exc.msg)))
        return problems, {"imports": 0}

    imports = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports += 1
                problems.extend(_judge(alias.name, rel, node.lineno, stdlib, local))
        elif isinstance(node, ast.ImportFrom):
            if node.level:            # 相对 import 只在本包内，必是本地模块
                imports += 1
                continue
            if node.module:
                imports += 1
                problems.extend(_judge(node.module, rel, node.lineno, stdlib, local))
        elif isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name in DYNAMIC_CALLS:
                problems.append(("E-ZERODEP-DYNAMIC",
                                 "%s:%d :: 用了 %s(...)——动态 import 绕过静态判定"
                                 % (rel, node.lineno, name)))
    return problems, {"imports": imports}


def _call_name(func):
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _judge(module, rel, lineno, stdlib, local):
    """判一个 import 目标；返回 problems 列表。"""
    top = module.split(".")[0]
    out = []
    # 网络能力：按全名与顶层名两种写法判（http.client 与 http 都拦）
    if module in NETWORK_MODULES or top in NETWORK_MODULES:
        out.append(("E-ZERODEP-NETWORK",
                    "%s:%d :: import 了具备联网能力的模块 %s" % (rel, lineno, module)))
        return out
    if module in DYNAMIC_MODULES or top in DYNAMIC_MODULES:
        out.append(("E-ZERODEP-DYNAMIC",
                    "%s:%d :: import 了 %s——动态 import 的入口，静态判定看不见目标"
                    % (rel, lineno, module)))
        return out
    if top in local:
        return out
    if top in stdlib:
        return out
    out.append(("E-ZERODEP-THIRDPARTY",
                "%s:%d :: import 了第三方包 %s（既不在标准库，也不是本仓模块）"
                % (rel, lineno, module)))
    return out


def check(root: Path):
    """返回 (ok, problems, stats)。stdlib 名单缺失时 fail closed。"""
    problems = []
    stats = {"files": 0, "imports": 0}
    stdlib = getattr(sys, "stdlib_module_names", None)
    if stdlib is None:
        problems.append(("E-ZERODEP-STDLIB-NA",
                         "本解释器是 Python %d.%d，没有 sys.stdlib_module_names（3.10+ 才有）——"
                         "无法区分标准库与第三方包，判不了就不许判绿"
                         % sys.version_info[:2]))
        return False, problems, stats
    stdlib = set(stdlib)
    local = local_module_stems(root)
    files = target_files(root)
    if not files:
        problems.append(("E-ZERODEP-NO-SOURCE",
                         "%s 下没有任何 .py——扫描面为空时「零违规」不构成证据"
                         % "/".join(SCAN_DIRS)))
        return False, problems, stats
    stats["files"] = len(files)
    for path in files:
        file_problems, file_stats = scan_file(path, root, stdlib, local)
        problems.extend(file_problems)
        stats["imports"] += file_stats["imports"]
    return not problems, problems, stats


def _selftest() -> int:
    """夹具用例：正例 + 第三方 + 网络模块 + 动态 import + 空扫描面 + 语法错误。"""
    failures = []
    total = [0]

    def case(name, files, expect_ok):
        total[0] += 1
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel, body in files.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body, encoding="utf-8")
            ok, problems, _stats = check(root)
            if ok != expect_ok:
                failures.append("%s：期望 ok=%s，实得 ok=%s（%s）"
                                % (name, expect_ok, ok, problems[:2]))

    def good():
        return {
            "scripts/rule_contract.py": "CONST = 1\n",
            "scripts/a.py": "import json\nimport sys\nfrom pathlib import Path\n"
                            "import rule_contract\nfrom rule_contract import skill_root\n",
            "evals/b.py": "from __future__ import annotations\nimport re\nimport a\n",
        }

    case("纯标准库 + 本仓模块", good(), True)

    bad = good()
    bad["scripts/a.py"] += "import requests\n"
    case("第三方包 requests", bad, False)

    bad = good()
    bad["scripts/a.py"] += "import socket\n"
    case("标准库但能联网 socket", bad, False)

    bad = good()
    bad["scripts/a.py"] += "from urllib.request import urlopen\n"
    case("urllib.request 子模块", bad, False)

    bad = good()
    bad["scripts/a.py"] += "import http.client\n"
    case("http.client 点号写法", bad, False)

    bad = good()
    bad["scripts/a.py"] += "mod = __import__('socket')\n"
    case("__import__ 动态逃逸", bad, False)

    bad = good()
    bad["scripts/a.py"] += "import importlib\n"
    case("importlib 入口", bad, False)

    case("扫描面为空", {"scripts/.keep": ""}, False)

    bad = good()
    bad["scripts/a.py"] += "def broken(:\n"
    case("语法错误 fail closed", bad, False)

    for f in failures:
        print("FAIL " + f)
    print("%s 零外部依赖：%d 个用例" % ("PASS" if not failures else "FAIL", total[0]))
    return 0 if not failures else 1


def main(argv=None) -> int:
    ap = ltw_exit.UsageParser(description="零外部依赖机检（AST 静态判定）")
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
        # 解释器缺 stdlib 名单 = 判不了（未测）；其余违规是判据真的生效了。
        if any(code == "E-ZERODEP-STDLIB-NA" for code, _ in problems):
            return ltw_exit.env_error("解释器缺 sys.stdlib_module_names，判不了就不许判绿",
                                      code="E-ZERODEP-STDLIB-NA")
        return ltw_exit.EXIT_VIOLATION
    print("PASS 零外部依赖：%d 个 .py / %d 条 import，全部落在标准库或本仓模块，"
          "无网络模块、无动态 import" % (stats["files"], stats["imports"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
