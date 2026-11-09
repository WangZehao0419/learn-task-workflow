#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文档指针校验（只读、零网络、幂等）。

校验 SKILL.md 与 references/ 下所有 doc 指针的可解析性，四项：

1. 路径存在：指针目标文件必须存在。
2. 锚点命中唯一：「小节名」必须能在目标文件唯一命中。
   锚点有两种书写形态，都必须被识别：
   - 全路径形态：`references/x.md`「小节名」，解析到 x.md；
   - 本册形态：「本册「小节名」」/「本节「小节名」」，解析到**当前文件**。
   只认前一种会让后一种整片隐形——那正是 #31 登记的盲区，清掉的自指会
   换个写法继续存在，而闸口显示为零。
   命中方式两层——标题优先，正文加粗词兜底（列表项内的加粗强调词是文档真实
   组织单元，如「压缩与加速」是逐目推进下的一条独立规则）。两层都必须唯一命中；
   命中多个即歧义，命中零个即断链。
3. 编号唯一：§N 编号在目标文件内只对应一个标题。本仓已弃用 §N（#31 方案 B），
   此项用于防止回潮。
4. 自指为零：分册内不得出现指向自己的指针。两种形态都算自指。

为什么不把「加粗词命中」判为失败：本仓的锚点契约见 references/ops.md——
「其他分册要引用就写一句指向正本的指针（`references/xxx.md`「小节名」）」。
「小节名」在实践中包含两类：标题，以及列表项内被加粗的规则条名。两者都要求
唯一命中，但报告时分开计数，便于判断某条规则是否该升格为标题。

退出码：0 全部通过（无 E 级问题）；1 有 E 级问题；2 用法错误。
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

FENCE = "```"
DATA_FILES = {"progress.md", "课程体系.md", "记忆.md", "profile.md"}
PLACEHOLDER = re.compile(r"(?:xxx|yyy|zzz|NN|<[^>]+>)", re.I)

PTR_RE = re.compile(r"`([A-Za-z0-9_\-/]+\.md)`")
ANCHOR_RE = re.compile(r"`([A-Za-z0-9_\-/]+\.md)`\s*[「“]([^」”]{2,60})[」”]")
# 「本册「小节名」」与「本节「小节名」」——不带路径，指向当前文件。
# 这是 #31 登记的机检盲区：旧版只认 ANCHOR_RE，这类指针完全不可见。
# 两者都要校验锚点存在性，但只有「本册」算自指：
#   本册 = 指向整册自己，零跳转价值，违反「分册零互指」→ E
#   本节 = 同节内的导航，是正常行文 → 只校验锚点，不计自指
LOCAL_ANCHOR_RE = re.compile(r"(本册|本节)\s*[「“]([^」”]{2,60})[」”]")
SECNO_RE = re.compile(r"§(\d+(?:\.\d+)*)")

# 讲「指针如何解析」的规则说明行：其中的反引号路径是字面示例，不是可解析指针。
# 按文件 + 行首特征豁免，避免把示例清单当成自指。
SELF_EXEMPT = {
    "SKILL.md": ["例外按字面解析："],
}


def strip_fences(text):
    """逐行去掉围栏代码块内的内容（保留行号）。"""
    out, in_fence = [], False
    for line in text.split("\n"):
        if line.strip().startswith(FENCE):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else line)
    return out


def headings(lines):
    """返回 [(行号, 标题文字)]，忽略代码块内。"""
    hs = []
    for i, line in enumerate(lines, 1):
        m = re.match(r"^(#{1,6})\s+(.*?)\s*$", line)
        if m:
            hs.append((i, m.group(2)))
    return hs


def bold_terms(lines):
    """返回 [(行号, 加粗词)]，忽略代码块内。"""
    out = []
    for i, line in enumerate(lines, 1):
        for m in re.finditer(r"\*\*(.+?)\*\*", line):
            t = m.group(1).strip().rstrip("：:")
            if t:
                out.append((i, t))
    return out


def normalize(name):
    """去掉前导编号与标点，便于标题名比较。"""
    return re.sub(r"^[\d.\s、]+", "", name).strip()


def resolve(src, ptr):
    """把指针解析为相对仓库根的路径。"""
    if ptr.startswith("references/"):
        return ptr
    if ptr == "SKILL.md":
        return "SKILL.md"
    return "references/" + ptr


MIN_PREFIX = 4


def matches(anchor, candidates):
    """锚点与候选名匹配，返回命中列表。

    匹配强度依次递减，命中即返回该层结果（不再往下找）：
    1. 原文精确相等
    2. 去编号后精确相等
    3. 去编号后互为前缀，且较短一方不少于 MIN_PREFIX 字

    不做任意子串包含：那会让「图」命中「概念地图」，产生大量假歧义。
    """
    a_raw, a = anchor, normalize(anchor)
    exact = [c for c in candidates if c == a_raw]
    if exact:
        return exact
    exact = [c for c in candidates if normalize(c) == a]
    if exact:
        return exact
    out = []
    for c in candidates:
        nc = normalize(c)
        if len(a) >= MIN_PREFIX and nc.startswith(a):
            out.append(c)
        elif len(nc) >= MIN_PREFIX and a.startswith(nc):
            out.append(c)
    return out


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.counts = {}

    def err(self, kind, where, detail):
        self.errors.append({"kind": kind, "where": where, "detail": detail})

    def warn(self, kind, where, detail):
        self.warnings.append({"kind": kind, "where": where, "detail": detail})

    def bump(self, key, n=1):
        self.counts[key] = self.counts.get(key, 0) + n


def collect_files(root):
    files = ["SKILL.md"]
    refs = root / "references"
    if refs.is_dir():
        for dirpath, _dirnames, filenames in os.walk(refs):
            for fn in sorted(filenames):
                if fn.endswith(".md"):
                    p = Path(dirpath) / fn
                    files.append(str(p.relative_to(root)).replace(os.sep, "/"))
    return sorted(files)


def _check_anchor(rep, where, target, anchor, get_headings, get_bold):
    """锚点在 target 内必须唯一命中：标题优先，加粗词兜底。"""
    by_head = matches(anchor, get_headings(target))
    if len(by_head) == 1:
        rep.bump("anchor_by_heading")
        return
    if len(by_head) > 1:
        rep.err("E-PTR-AMBIG", where,
                "「%s」在 %s 命中 %d 个标题：%s"
                % (anchor, target, len(by_head), by_head[:4]))
        return
    by_bold = matches(anchor, get_bold(target))
    if len(by_bold) == 1:
        rep.bump("anchor_by_bold")
        rep.warn("W-PTR-BOLD", where,
                 "「%s」只在 %s 的正文加粗词命中（非标题）"
                 % (anchor, target))
    elif len(by_bold) > 1:
        rep.err("E-PTR-AMBIG", where,
                "「%s」在 %s 命中 %d 个加粗词：%s"
                % (anchor, target, len(by_bold), by_bold[:4]))
    else:
        rep.err("E-PTR-ANCHOR", where,
                "「%s」在 %s 既无标题也无加粗词命中"
                % (anchor, target))


def check(root, rep):
    files = collect_files(root)
    head_cache, bold_cache = {}, {}

    def get_headings(rel):
        if rel not in head_cache:
            lines = strip_fences((root / rel).read_text(encoding="utf-8"))
            head_cache[rel] = [t for _i, t in headings(lines)]
        return head_cache[rel]

    def get_bold(rel):
        if rel not in bold_cache:
            lines = strip_fences((root / rel).read_text(encoding="utf-8"))
            bold_cache[rel] = [t for _i, t in bold_terms(lines)]
        return bold_cache[rel]

    for rel in files:
        path = root / rel
        if not path.is_file():
            rep.err("E-PTR-PATH", rel, "文件本身不存在")
            continue
        lines = strip_fences(path.read_text(encoding="utf-8"))
        rep.bump("files")

        for lineno, line in enumerate(lines, 1):
            where = "%s:%d" % (rel, lineno)

            # 检查 1/2：路径存在 + 锚点命中唯一
            # 收集两种形态：全路径（目标在别处）与本册/本节（目标是自己）
            anchors = [(m.group(1), m.group(2).strip())
                       for m in ANCHOR_RE.finditer(line)]
            local = [(m.group(1), m.group(2).strip())
                     for m in LOCAL_ANCHOR_RE.finditer(line)]
            # 全路径形态的指针本身若已自指，其「小节名」不再重复计一次本册锚点
            consumed = set()
            for ptr, anchor in anchors:
                if os.path.normpath(resolve(rel, ptr)) == os.path.normpath(rel):
                    consumed.add(anchor)

            for ptr, anchor in anchors:
                rep.bump("anchors")
                if PLACEHOLDER.search(ptr) or PLACEHOLDER.search(anchor):
                    rep.bump("placeholders")
                    continue
                target = resolve(rel, ptr)
                tpath = root / target
                if not tpath.is_file():
                    rep.err("E-PTR-PATH", where,
                            "目标文件不存在：%s" % target)
                    continue
                _check_anchor(rep, where, target, anchor,
                              get_headings, get_bold)

            for marker, anchor in local:
                if anchor in consumed:
                    continue
                rep.bump("anchors")
                rep.bump("anchor_by_local")
                if PLACEHOLDER.search(anchor):
                    rep.bump("placeholders")
                    continue
                _check_anchor(rep, where, rel, anchor,
                              get_headings, get_bold)

            # 检查 3：§N 编号唯一
            for m in SECNO_RE.finditer(line):
                num = m.group(1)
                rep.bump("secnos")
                owner = rel
                for pm in PTR_RE.finditer(line[:m.start()]):
                    owner = resolve(rel, pm.group(1))
                if not (root / owner).is_file():
                    continue
                owner_lines = strip_fences(
                    (root / owner).read_text(encoding="utf-8"))
                hits = []
                for _i, t in headings(owner_lines):
                    nt = normalize(t)
                    m2 = re.match(r"^(\d+(?:\.\d+)*)[.、]?\s", t)
                    if m2 and m2.group(1) == num:
                        hits.append(t)
                if len(hits) > 1:
                    rep.err("E-PTR-SECNO", where,
                            "§%s 在 %s 命中 %d 个标题"
                            % (num, owner, len(hits)))
                elif not hits:
                    rep.warn("W-PTR-SECNO", where,
                             "§%s 在 %s 无对应标题（本仓已弃用 §N）"
                             % (num, owner))

            # 检查 4：自指为零（E 级——清零后不可回潮）
            exempt_prefixes = SELF_EXEMPT.get(rel, ())
            is_exempt = any(line.lstrip().startswith(p) for p in exempt_prefixes)
            if not is_exempt:
                for m in PTR_RE.finditer(line):
                    ptr = m.group(1)
                    if PLACEHOLDER.search(ptr):
                        continue
                    if os.path.basename(ptr) in DATA_FILES:
                        continue
                    target = resolve(rel, ptr)
                    if os.path.normpath(target) == os.path.normpath(rel):
                        rep.err("E-PTR-SELF", where,
                                "自指指针：%s 指向自己（同册引用去掉路径）"
                                % ptr)
                # 「本册「…」」指向整册自己 → E；「本节「…」」是同节导航，合法
                for m in LOCAL_ANCHOR_RE.finditer(line):
                    if m.group(1) == "本册":
                        rep.err("E-PTR-SELF", where,
                                "自指锚点：本册「%s」指向自己（同册引用去掉路径）"
                                % m.group(2).strip())
    return rep


def _selftest():
    """内置用例：每项检查都有正例与反例。"""
    import tempfile
    failures = []

    def chk(name, fn):
        try:
            fn()
            print("PASS", name)
        except AssertionError as e:
            failures.append(name)
            print("FAIL", name, "::", e)

    def build(files):
        td = tempfile.mkdtemp()
        root = Path(td)
        for rel, content in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        return root

    def ok_clean():
        root = build({
            "SKILL.md": "见 `references/a.md`「甲节」。\n",
            "references/a.md": "# A\n\n## 甲节\n\n内容。\n",
        })
        rep = check(root, Report())
        assert not rep.errors, rep.errors

    def detect_missing_file():
        root = build({
            "SKILL.md": "见 `references/nope.md`「某节」。\n",
        })
        rep = check(root, Report())
        assert any(e["kind"] == "E-PTR-PATH" for e in rep.errors), rep.errors

    def detect_missing_anchor():
        root = build({
            "SKILL.md": "见 `references/a.md`「不存在的节」。\n",
            "references/a.md": "# A\n\n## 甲节\n",
        })
        rep = check(root, Report())
        assert any(e["kind"] == "E-PTR-ANCHOR" for e in rep.errors), rep.errors

    def detect_ambiguous():
        root = build({
            "SKILL.md": "见 `references/a.md`「重复节名」。\n",
            "references/a.md": "# A\n\n## 重复节名\n\n## 重复节名\n",
        })
        rep = check(root, Report())
        assert any(e["kind"] == "E-PTR-AMBIG" for e in rep.errors), rep.errors

    def bold_fallback_is_warn():
        root = build({
            "SKILL.md": "见 `references/a.md`「粗体条」。\n",
            "references/a.md": "# A\n\n## 甲节\n\n- **粗体条**：规则。\n",
        })
        rep = check(root, Report())
        assert not rep.errors, rep.errors
        assert any(w["kind"] == "W-PTR-BOLD" for w in rep.warnings), rep.warnings

    def self_pointer_is_error():
        root = build({
            "SKILL.md": "# 入口\n",
            "references/a.md": "# A\n\n见 `references/a.md`「甲节」。\n\n## 甲节\n",
        })
        rep = check(root, Report())
        assert any(e["kind"] == "E-PTR-SELF" for e in rep.errors), rep.errors

    def benku_anchor_resolves():
        # 「本册「…」」指向本文件里的标题，必须算命中，不是盲区
        root = build({
            "SKILL.md": "# 入口\n",
            "references/a.md": "# A\n\n## 存在的节\n\n见本册「存在的节」。\n",
        })
        rep = check(root, Report())
        assert not any(e["kind"] == "E-PTR-ANCHOR" for e in rep.errors), rep.errors
        assert rep.counts.get("anchor_by_local", 0) >= 1, rep.counts
        # 但它同时是自指，必须报 E
        assert any(e["kind"] == "E-PTR-SELF" for e in rep.errors), rep.errors

    def benku_anchor_missing_is_error():
        # 盲区回归守卫：指向不存在的小节，必须报 E-PTR-ANCHOR 而不是静默
        root = build({
            "SKILL.md": "# 入口\n",
            "references/a.md": "# A\n\n## 甲节\n\n见本册「根本不存在的节」。\n",
        })
        rep = check(root, Report())
        assert any(e["kind"] == "E-PTR-ANCHOR" for e in rep.errors), rep.errors

    def jieben_anchor_detected():
        # 本节是同节导航，合法：要校验锚点存在性，但不算自指
        root = build({
            "SKILL.md": "# 入口\n",
            "references/a.md": "# A\n\n## 甲节\n\n见本节「甲节」。\n",
        })
        rep = check(root, Report())
        assert not rep.errors, rep.errors
        assert rep.counts.get("anchor_by_local", 0) >= 1, rep.counts

    def jieben_anchor_missing_is_error():
        # 本节也要校验锚点：指向不存在的小节必须报 E
        root = build({
            "SKILL.md": "# 入口\n",
            "references/a.md": "# A\n\n## 甲节\n\n见本节「不存在的节」。\n",
        })
        rep = check(root, Report())
        assert any(e["kind"] == "E-PTR-ANCHOR" for e in rep.errors), rep.errors

    def data_files_exempt():
        root = build({
            "SKILL.md": "# 入口\n",
            "references/a.md": "# A\n\n见 `progress.md`「某区」。\n",
        })
        rep = check(root, Report())
        assert not any(e["kind"] == "E-PTR-SELF" for e in rep.errors), rep.errors

    def placeholder_skipped():
        root = build({
            "SKILL.md": "例：`references/xxx.md`「小节名」。\n",
        })
        rep = check(root, Report())
        assert not rep.errors, rep.errors

    def detect_secno_ambiguous():
        root = build({
            "SKILL.md": "见 `references/a.md` §1。\n",
            "references/a.md": "# A\n\n## 1. 甲\n\n## 1. 乙\n",
        })
        rep = check(root, Report())
        assert any(e["kind"] == "E-PTR-SECNO" for e in rep.errors), rep.errors

    def fences_ignored():
        root = build({
            "SKILL.md": "# 入口\n\n```\n见 `references/nope.md`「某节」。\n```\n",
        })
        rep = check(root, Report())
        assert not rep.errors, rep.errors

    cases = [
        ("干净文档零问题", ok_clean),
        ("抓到路径不存在", detect_missing_file),
        ("抓到锚点不存在", detect_missing_anchor),
        ("抓到锚点歧义", detect_ambiguous),
        ("加粗词兜底只报 W", bold_fallback_is_warn),
        ("自指报 E", self_pointer_is_error),
        ("本册锚点能解析且报自指", benku_anchor_resolves),
        ("本册锚点断链报 E", benku_anchor_missing_is_error),
        ("本节锚点合法不报自指", jieben_anchor_detected),
        ("本节锚点断链报 E", jieben_anchor_missing_is_error),
        ("数据文件豁免自指", data_files_exempt),
        ("占位示例被跳过", placeholder_skipped),
        ("抓到 §N 歧义", detect_secno_ambiguous),
        ("代码块内不校验", fences_ignored),
    ]
    for name, fn in cases:
        chk(name, fn)

    if failures:
        print("FAIL 文档指针校验 %d/%d" % (len(failures), len(cases)))
        return 1
    print("PASS 文档指针校验 %d/%d" % (len(cases), len(cases)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="文档指针校验（只读）")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--root", help="仓库根（默认取本脚本上两级）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出报告")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    root = (Path(args.root).resolve() if args.root
            else Path(__file__).resolve().parent.parent)
    rep = check(root, Report())

    if args.json:
        print(json.dumps({
            "ok": not rep.errors,
            "counts": rep.counts,
            "errors": rep.errors,
            "warnings": rep.warnings,
        }, ensure_ascii=False, indent=1))
    else:
        print("=== 文档指针校验 ===")
        for k in ("files", "anchors", "anchor_by_heading", "anchor_by_bold",
                  "anchor_by_local", "secnos", "placeholders"):
            if k in rep.counts:
                print("  %-20s %d" % (k, rep.counts[k]))
        print()
        if rep.errors:
            print("E 级问题 %d 处：" % len(rep.errors))
            for e in rep.errors:
                print("  [%s] %s :: %s" % (e["kind"], e["where"], e["detail"]))
        if rep.warnings:
            print("W 级提示 %d 处：" % len(rep.warnings))
            for w in rep.warnings:
                print("  [%s] %s :: %s" % (w["kind"], w["where"], w["detail"]))
        if not rep.errors:
            print("PASS 文档指针校验：无 E 级问题")
    return 0 if not rep.errors else 1


if __name__ == "__main__":
    sys.exit(main())