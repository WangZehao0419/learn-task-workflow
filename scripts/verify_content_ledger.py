#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""内容台账机检（只读、零网络、幂等、stdlib-only；需要完整 git 历史）。

票 104 把用户故事 34「清除冗余内容时有台账可查」从一句承诺变成会红的断言。
台账是人写的，半年后必然与仓库脱节——所以台账的每一行都必须能被本脚本验证，
而不是又一份散文。六条判据：

    C0 基线可指认  基线 tag 必须存在且可解析；它的 references/ 树必须与 v9.19.2 逐字相同
                   （两个 tag 指同一批分册，台账才不因「换了基线」而失去意义）
    C1 覆盖面      git diff --diff-filter=DR 的每个路径都必须在台账里出现，少一条即红
    C2 无幽灵行    台账里出现的每个原路径都必须真的被删除或改名过，多一条即红
    C3 去向可达    去向列的每个路径必须真实存在；每个「小节」必须在目标文件内恰好命中 1 次
    C4 改名一致    处置为「改名」的行，去向必须等于 git 实测的改名目标
    C5 判据非空    每行判据必须给出承接证据或明确的废弃理由，不得留空或只写占位

为什么每条都要「双向」：只查 C1 会放过幽灵行（台账写着一堆没发生过的路径，
读者按台账去 git show 全扑空）；只查 C2 会放过漏登记（删了 112 个文件、台账只
记 20 条，照样全绿——而漏登记正是本票要消灭的东西）。C3 同理：去向指向不存在的
路径时，台账比没有台账更糟，它把读者送去空指针。

为什么基线 tag 缺失要 fail closed 而不是跳过：跳过等于「没有基线 → 没有 diff →
没有缺行 → 绿」。tag 一丢，闸口就自动全绿，这正是本仓反复出现的「文档声称有、
脚本不校验」。宁可红，不可假绿。

用法：
    python -B scripts/verify_content_ledger.py              # 检查真实树
    python -B scripts/verify_content_ledger.py --selftest   # 自测 + 真实树

退出码：0 六条判据全过；1 有判据不通过（含 git/tag 不可用——一律 fail closed）；2 用法错误。
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rule_contract import skill_root  # noqa: E402

BQ = chr(96)
C1 = chr(0x300C)
C2 = chr(0x300D)

BASELINE_TAG = "baseline/v9.19.2-pre-redo"
PEER_TAG = "v9.19.2"
LEDGER = "docs/migrations/v10-content-ledger.md"
LEDGER_SECTION = "## 台账"

DISP_DELETE = "删除"
DISP_RENAME = "改名"
DISP_SPLIT = "拆分"
DISP_MERGE = "合并"
DISPATCHES = (DISP_DELETE, DISP_RENAME, DISP_SPLIT, DISP_MERGE)

ROW_RE = re.compile("^\\|\\s*" + BQ + "([^" + BQ + "]+)" + BQ
                    + "\\s*\\|\\s*([^|]+?)\\s*\\|\\s*(.+?)\\s*\\|\\s*(.+?)\\s*\\|\\s*$")
SEG_RE = re.compile("^" + BQ + "([^" + BQ + "]+)" + BQ + "\\s*(?:" + C1 + "(.+)" + C2 + ")?\\s*$")
SEP = " + "
PLACEHOLDER = re.compile("^(?:无|—|-|待补|TODO|TBD)$", re.I)
ANGLE = re.compile("<[^>]{1,30}>")
HEAD_RE = re.compile("^(#{1,6})\\s+(.*?)\\s*$")
NUM_PREFIX = re.compile("^[0-9]+(?:\\.[0-9]+)*[.、]?\\s*")


class GitError(RuntimeError):
    pass


def git(root: Path, *args: str) -> str:
    """只读调用 git；失败一律抛出，由调用方转成红（不静默降级）。"""
    exe = shutil.which("git")
    if not exe:
        raise GitError("PATH 上找不到 git——台账判据依赖 git 历史，无法校验即判红")
    proc = subprocess.run([exe, "-C", str(root), *args], capture_output=True)
    if proc.returncode != 0:
        raise GitError("git %s 失败：%s" % (" ".join(args),
                                           proc.stderr.decode("utf-8", "replace").strip()))
    return proc.stdout.decode("utf-8", "replace")


def headings(body: str):
    """返回正文里所有标题的文字。

    **不按围栏过滤**：本仓 references/planning.md 与 references/intake-optional.md
    的围栏是奇数（第 72 行开了 ```markdown 到文件尾都没闭合）。按围栏过滤会把这两个
    文件第 72 行之后的真实标题整片吞掉，于是「去向小节」永远判 0 次命中——闸口变成
    对真实落点喊红、对假落点喊绿的反向工具。宁可多收代码块里的模板标题（那只会让
    唯一性命中更严），不可少收真实标题。
    """
    lines = body.splitlines()
    out = []
    for idx, line in enumerate(lines):
        m = HEAD_RE.match(line)
        if not m:
            continue
        title = m.group(2).strip()
        # 排除模板样例标题：本仓把 profile.md / 课程体系.md 的样例整段写在正文里，
        # 样例里也有 `## 学习者画像` 这类标题。它不是可跳转的真实小节，
        # 若算进去，「学习者画像」就成了 2 次命中，真实落点反被判歧义。
        nxt = ""
        for j in range(idx + 1, min(idx + 3, len(lines))):
            if lines[j].strip():
                nxt = lines[j].strip()
                break
        if ANGLE.search(title) or (ANGLE.search(nxt) and not nxt.startswith("#")):
            continue
        out.append(title)
    return out


def heading_key(text: str) -> str:
    """标题比对键：去前导编号与首尾空白，全角/半角竖线不参与归一（台账写的是原文）。"""
    return NUM_PREFIX.sub("", text.strip()).strip()


def anchor_hits(body: str, anchor: str) -> int:
    """锚点必须在目标文件里恰好命中一个**标题**。

    为什么按标题而不是子串计数：小节名会作为普通词组在正文里反复出现
    （「判分口径」在一册里能出现三次），子串计数会把真实存在的落点判成歧义，
    于是闸口逼着人去写更长的句子来绕开——那不是可机检，那是可机检的假象。
    """
    want = heading_key(anchor)
    return sum(1 for h in headings(body) if heading_key(h) == want)


def parse_dests(dest_text: str):
    """解析去向列 -> [(路径, 小节或空)]。

    按「 + 」切成多段（拆分行的多个去向），每段单独匹配；小节名用**贪婪**配对，
    因为真实小节名里可能嵌套引号：references/ops.md「核验状态与「不能推出什么」」。
    非贪婪会在第一个右引号处截断，把一条真实落点判成「小节不存在」。
    """
    out = []
    for seg in dest_text.split(SEP):
        seg = seg.strip()
        if not seg:
            continue
        m = SEG_RE.match(seg)
        if m:
            out.append((m.group(1).strip(), (m.group(2) or "").strip()))
        else:
            found = re.findall(BQ + "([^" + BQ + "]+)" + BQ, seg)
            out.extend((p.strip(), "") for p in found)
    return out


def parse_ledger(text: str):
    """解析台账表 -> (rows, errors)。rows: [{line, old, disp, dest_text, why, dests}]。"""
    rows, errors = [], []
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith(LEDGER_SECTION):
            start = i
            break
    if start is None:
        return [], ["E-LEDGER-PARSE 台账缺少「%s」小节——没有表就没有可校验的东西" % LEDGER_SECTION]
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line.startswith("## ") and i > start + 1:
            break
        m = ROW_RE.match(line)
        if not m:
            continue
        old, disp, dest_text, why = (m.group(1).strip(), m.group(2).strip(),
                                     m.group(3).strip(), m.group(4).strip())
        if old == "原路径" or set(old) <= set("-: "):
            continue
        dests = parse_dests(dest_text)
        rows.append({"line": i + 1, "old": old, "disp": disp, "dest_text": dest_text,
                     "why": why, "dests": dests})
    if not rows:
        errors.append("E-LEDGER-PARSE 台账表 0 行——空表不能算通过")
    return rows, errors


def check(root: Path, ledger_rel: str = LEDGER):
    """返回问题列表（空 = 全过）。"""
    probs = []
    ledger_path = Path(ledger_rel)
    if not ledger_path.is_absolute():
        ledger_path = root / ledger_rel
    if not ledger_path.is_file():
        return ["E-LEDGER-MISSING 台账不存在：%s" % ledger_rel]
    try:
        text = ledger_path.read_text(encoding="utf-8")
    except OSError as exc:
        return ["E-LEDGER-MISSING 台账不可读：%s（%s）" % (ledger_rel, exc)]

    rows, parse_errors = parse_ledger(text)
    probs.extend(parse_errors)

    # ── C0 基线可指认 ──────────────────────────────────────────────
    try:
        git(root, "rev-parse", "--verify", BASELINE_TAG + "^{commit}")
    except GitError as exc:
        probs.append("E-LEDGER-BASELINE 基线 tag %s%s%s 不可解析：%s" % (BQ, BASELINE_TAG, BQ, exc))
        return probs
    try:
        peer = git(root, "rev-parse", "--verify", PEER_TAG + "^{commit}").strip()
    except GitError:
        peer = ""
    if not peer:
        probs.append("E-LEDGER-BASELINE 对照 tag %s%s%s 不存在——台账声称两 tag 的 references/ 树相同，无法断言"
                     % (BQ, PEER_TAG, BQ))
    else:
        base_tree = git(root, "rev-parse", BASELINE_TAG + "^{tree}:references").strip()
        peer_tree = git(root, "rev-parse", PEER_TAG + "^{tree}:references").strip()
        if base_tree != peer_tree:
            probs.append("E-LEDGER-BASELINE %s%s%s 与 %s%s%s 的 references/ 树不同（%s vs %s）——台账前言声称逐字相同"
                         % (BQ, BASELINE_TAG, BQ, BQ, PEER_TAG, BQ, base_tree, peer_tree))

    # ── 实测清单：DR 路径与改名目标 ────────────────────────────────
    try:
        status = git(root, "diff", "--diff-filter=DR", "--name-status", "-M", BASELINE_TAG, "HEAD")
    except GitError as exc:
        probs.append("E-LEDGER-BASELINE 取不到 %s..HEAD 的差异：%s" % (BASELINE_TAG, exc))
        return probs
    actual, rename_target = set(), {}
    for line in status.strip().splitlines():
        parts = line.split(chr(9))
        if len(parts) < 2:
            continue
        if parts[0].startswith("R") and len(parts) >= 3:
            actual.add(parts[1])
            rename_target[parts[1]] = parts[2]
        else:
            actual.add(parts[1])

    seen = {}
    for row in rows:
        seen.setdefault(row["old"], []).append(row["line"])
    listed = set(seen)

    # ── C1 覆盖面：实测有、台账没有 ────────────────────────────────
    for old in sorted(actual - listed):
        probs.append("E-LEDGER-COVERAGE 未登记：%s%s%s 已被删除/改名，台账里没有这一行" % (BQ, old, BQ))
    # ── C2 无幽灵行：台账有、实测没有 ──────────────────────────────
    for old in sorted(listed - actual):
        probs.append("E-LEDGER-GHOST 幽灵行：%s%s%s 在 %s..HEAD 里既没被删除也没被改名（第 %s 行）"
                     % (BQ, old, BQ, BASELINE_TAG, ",".join(str(n) for n in seen[old])))
    for old, lines_no in sorted(seen.items()):
        if len(lines_no) > 1:
            probs.append("E-LEDGER-GHOST 重复登记：%s%s%s 出现 %d 次（第 %s 行）"
                         % (BQ, old, BQ, len(lines_no), ",".join(str(n) for n in lines_no)))

    for row in rows:
        old, disp, why, dests = row["old"], row["disp"], row["why"], row["dests"]
        where = "第 %d 行 %s%s%s" % (row["line"], BQ, old, BQ)
        # ── C5 判据非空 ────────────────────────────────────────────
        if not why or PLACEHOLDER.match(why) or len(why) < 12:
            probs.append("E-LEDGER-JUDGE 判据为空或过短：%s —— 要么给承接证据，要么写明废弃理由" % where)
        elif not ("承接" in why or "废弃" in why):
            probs.append("E-LEDGER-JUDGE 判据既没说承接也没说废弃：%s（%s）" % (where, why[:40]))
        # ── 处置词合法 ─────────────────────────────────────────────
        if disp not in DISPATCHES:
            probs.append("E-LEDGER-DISP 处置取值非法：%s = 「%s」（只允许 %s）"
                         % (where, disp, " / ".join(DISPATCHES)))
        # ── C3 去向可达 ────────────────────────────────────────────
        if not dests:
            probs.append("E-LEDGER-DEST 去向列为空：%s —— 删除也要写承接册，真的废弃要写理由" % where)
        for dest, anchor in dests:
            if dest == old:
                probs.append("E-LEDGER-DEST 去向指向自己：%s —— 被删除的文件不可能承接自己" % where)
                continue
            target = root / dest
            if not target.is_file():
                probs.append("E-LEDGER-DEST 去向路径不存在：%s -> %s%s%s" % (where, BQ, dest, BQ))
                continue
            if not anchor:
                continue
            try:
                body = target.read_text(encoding="utf-8")
            except OSError as exc:
                probs.append("E-LEDGER-DEST 去向不可读：%s -> %s%s%s（%s）" % (where, BQ, dest, BQ, exc))
                continue
            hits = anchor_hits(body, anchor)
            if hits != 1:
                probs.append("E-LEDGER-ANCHOR 去向小节命中 %d 次（要求恰好 1 次）：%s -> %s%s%s%s%s%s"
                             % (hits, where, BQ, dest, BQ, C1, anchor, C2))
        # ── C4 改名一致 ────────────────────────────────────────────
        if disp == DISP_RENAME:
            want = rename_target.get(old)
            if not want:
                probs.append("E-LEDGER-RENAME 处置写「改名」，但 git 实测这不是改名：%s" % where)
            elif dests and dests[0][0] != want:
                probs.append("E-LEDGER-RENAME 改名去向与实测不符：%s 写 %s%s%s，实测 %s%s%s"
                             % (where, BQ, dests[0][0], BQ, BQ, want, BQ))
        elif old in rename_target:
            probs.append("E-LEDGER-RENAME git 实测这是改名，台账却写「%s」：%s -> %s%s%s"
                         % (disp, where, BQ, rename_target[old], BQ))
    return probs


def _git(args, cwd):
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True)
    if proc.returncode != 0:
        raise GitError(proc.stderr.decode("utf-8", "replace"))
    return proc.stdout.decode("utf-8", "replace")


def _row(old, disp, dest, anchor, why):
    """构造一行台账表格文本，避免自测里手写拼接出错。"""
    dest_text = BQ + dest + BQ + ((C1 + anchor + C2) if anchor else "")
    return "| " + BQ + old + BQ + " | " + disp + " | " + dest_text + " | " + why + " |"


def _selftest() -> int:
    """夹具用例：正例 + 每条判据各一条反例 + 真实制品变异。"""
    if not shutil.which("git"):
        # 不得「跳过即通过」：G3 只认 rc=0，跳过会让这条闸口在无 git 环境里静默全绿，
        # 而本脚本的全部判据都建立在 git 历史上——没有 git 就没有可验证的东西，只能红。
        print("FAIL 自测需要 git，PATH 上没有——本闸口的判据全建立在 git 历史上，无 git 即无法校验")
        return 1
    failures = []
    ran = [0]

    def case(name, fn):
        ran[0] += 1
        try:
            fn()
        except AssertionError as exc:
            failures.append("%s：%s" % (name, exc))
        except Exception as exc:  # noqa: BLE001 - 自测要把任何异常都记成失败
            failures.append("%s：%s: %s" % (name, type(exc).__name__, exc))

    GOOD = _row("references/old/a.md", DISP_DELETE, "references/new.md", "甲节",
                "逐字承接：原文 3/3 行仍在 references/new.md「甲节」")
    RENAMED = _row("references/old/b.md", DISP_RENAME, "references/renamed.md", "",
                   "改名承接：同一册换路径（git diff -M 实测 R 记录）")
    NEW_TEXT = "# 新册\n\n## 甲节\n\n内容。\n"

    def build(root: Path, rows, *, tag=True, new_text=NEW_TEXT, peer_same=True):
        (root / "references" / "old").mkdir(parents=True, exist_ok=True)
        (root / "references" / "old" / "a.md").write_text("# 旧甲\n\n内容一。\n", encoding="utf-8")
        (root / "references" / "old" / "b.md").write_text("# 旧乙\n\n内容二。\n", encoding="utf-8")
        (root / "references" / "keep.md").write_text("# 保留\n", encoding="utf-8")
        _git(["init", "-q", "-b", "main"], root)
        _git(["config", "user.email", "t@example.com"], root)
        _git(["config", "user.name", "t"], root)
        _git(["add", "-A"], root)
        _git(["commit", "-q", "-m", "base"], root)
        if tag:
            _git(["tag", PEER_TAG], root)
        (root / "references" / "old" / "a.md").unlink()
        _git(["mv", "references/old/b.md", "references/renamed.md"], root)
        (root / "references" / "new.md").write_text(new_text, encoding="utf-8")
        (root / "docs" / "migrations").mkdir(parents=True, exist_ok=True)
        body = ("# 台账\n\n" + LEDGER_SECTION + "\n\n| 原路径 | 处置 | 去向 | 判据 |\n"
                "|---|---|---|---|\n" + "\n".join(rows) + "\n")
        (root / LEDGER).write_text(body, encoding="utf-8")
        _git(["add", "-A"], root)
        _git(["commit", "-q", "-m", "redo"], root)
        if tag:
            _git(["tag", BASELINE_TAG, "HEAD~1"], root)
        if not peer_same:
            _git(["tag", "-d", PEER_TAG], root)
            _git(["tag", PEER_TAG, "HEAD"], root)
        return root

    def with_repo(rows, **kw):
        root = Path(tempfile.mkdtemp())
        build(root, rows, **kw)
        return root, check(root)

    def good_baseline():
        _root, probs = with_repo([GOOD, RENAMED])
        assert not probs, probs
    case("正例：删除 + 改名两行台账全绿", good_baseline)

    def missing_row_red():
        _root, probs = with_repo([GOOD])
        assert any("COVERAGE" in p for p in probs), probs
    case("变异：删掉一行 → C1 红（漏登记）", missing_row_red)

    def ghost_row_red():
        ghost = _row("references/old/ghost.md", DISP_DELETE, "references/new.md", "甲节",
                     "改写承接：原文 1/1 行仍在 references/new.md「甲节」")
        _root, probs = with_repo([GOOD, RENAMED, ghost])
        assert any("GHOST" in p for p in probs), probs
    case("变异：加一行不存在的原路径 → C2 红（幽灵行）", ghost_row_red)

    def bad_dest_red():
        bad = _row("references/old/a.md", DISP_DELETE, "references/nope.md", "",
                   "逐字承接：原文 3/3 行仍在 references/nope.md")
        _root, probs = with_repo([bad, RENAMED])
        assert any("E-LEDGER-DEST" in p for p in probs), probs
    case("变异：去向改成不存在的路径 → C3 红", bad_dest_red)

    def bad_anchor_red():
        bad = _row("references/old/a.md", DISP_DELETE, "references/new.md", "不存在的节",
                   "逐字承接：原文 3/3 行仍在 references/new.md「不存在的节」")
        _root, probs = with_repo([bad, RENAMED])
        assert any("ANCHOR" in p for p in probs), probs
    case("变异：去向小节不存在 → C3 红（把读者送去空指针）", bad_anchor_red)

    def dup_anchor_red():
        dup = "# 新册\n\n## 甲节\n\n内容。\n\n## 甲节\n\n重复节名。\n"
        _root, probs = with_repo([GOOD, RENAMED], new_text=dup)
        assert any("ANCHOR" in p for p in probs), probs
    case("变异：去向小节重名（命中 2 次）→ C3 红", dup_anchor_red)

    def rename_mismatch_red():
        bad = _row("references/old/b.md", DISP_RENAME, "references/new.md", "",
                   "改名承接：同一册换路径")
        _root, probs = with_repo([GOOD, bad])
        assert any("RENAME" in p for p in probs), probs
    case("变异：改名去向与 git 实测不符 → C4 红", rename_mismatch_red)

    def empty_judge_red():
        bad = _row("references/old/a.md", DISP_DELETE, "references/new.md", "甲节", "—")
        _root, probs = with_repo([bad, RENAMED])
        assert any("JUDGE" in p for p in probs), probs
    case("变异：判据列写「—」→ C5 红（不得留空）", empty_judge_red)

    def no_tag_red():
        _root, probs = with_repo([GOOD, RENAMED], tag=False)
        assert any("BASELINE" in p for p in probs), probs
    case("fail closed：基线 tag 不存在 → C0 红（不静默跳过）", no_tag_red)

    def peer_diverged_red():
        _root, probs = with_repo([GOOD, RENAMED], peer_same=False)
        assert any("BASELINE" in p for p in probs), probs
    case("fail closed：两 tag 的 references/ 树不同 → C0 红", peer_diverged_red)

    # ── 真实制品变异：拷真台账到临时文件再改，不动被测文件本身 ──────────
    def real_ledger_mutations():
        real = skill_root()
        src = real / LEDGER
        if not src.is_file():
            raise AssertionError("真实台账不存在：%s" % LEDGER)
        base = src.read_text(encoding="utf-8")
        assert not check(real), check(real)[:5]
        lines = base.splitlines()
        data_idx = [i for i, ln in enumerate(lines) if ROW_RE.match(ln)]
        assert len(data_idx) >= 3, "真实台账数据行不足"

        def run_with(text):
            td = Path(tempfile.mkdtemp())
            p = td / "ledger.md"
            p.write_text(text, encoding="utf-8")
            return check(real, ledger_rel=str(p))

        drop = lines[:data_idx[0]] + lines[data_idx[0] + 1:]
        probs = run_with("\n".join(drop) + "\n")
        assert any("COVERAGE" in p for p in probs), ("删一行必须红", probs[:3])

        ghost = _row("references/ghost-never-existed.md", DISP_DELETE, "references/ops.md",
                     "脚本操作与验证", "改写承接：原文 1/1 行仍在 references/ops.md「脚本操作与验证」")
        probs = run_with("\n".join(lines[:data_idx[0]] + [ghost] + lines[data_idx[0]:]) + "\n")
        assert any("GHOST" in p for p in probs), ("加幽灵行必须红", probs[:3])

        # 只改「去向」列（第 3 个单元格）。改原路径列测的是 C1/C2，不是 C3——
        # 变异必须打在它要证明的那条判据上，否则用例绿了也证明不了 C3 会咬人。
        victim = lines[data_idx[0]]
        cells = victim.split("|")
        assert len(cells) >= 5, "真实台账首行不是四列表格"
        dest_cell = cells[3]
        assert BQ + "references/" in dest_cell, "真实台账首行的去向列不含 references/ 路径"
        cells[3] = dest_cell.replace(BQ + "references/", BQ + "references/zzz-", 1)
        broken = "|".join(cells)
        assert broken != victim
        mutated = lines[:data_idx[0]] + [broken] + lines[data_idx[0] + 1:]
        probs = run_with("\n".join(mutated) + "\n")
        assert any("E-LEDGER-DEST" in p for p in probs), ("改坏去向必须红", probs[:3])

        assert not check(real), "还原后应绿"
    case("真实制品变异：删一行 / 加幽灵行 / 改坏去向 → 红，还原 → 绿", real_ledger_mutations)

    def real_tree():
        probs = check(skill_root())
        assert not probs, probs[:5]
    case("真实树：台账覆盖面与 git 实测双向相等、去向全部可达", real_tree)

    for f in failures:
        print("FAIL " + f)
    print("%s 内容台账机检：%d 个用例" % ("PASS" if not failures else "FAIL", ran[0]))
    return 0 if not failures else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="内容台账机检（只读，需要 git 历史）")
    ap.add_argument("--selftest", action="store_true", help="跑内置用例再检查真实树")
    ap.add_argument("--root", default=None, help="技能根（默认脚本所在仓库）")
    ap.add_argument("--ledger", default=None, help="台账路径（自测用）")
    args = ap.parse_args(argv)

    if args.selftest:
        rc = _selftest()
        if rc:
            return rc

    root = Path(args.root) if args.root else skill_root()
    ledger_rel = args.ledger or LEDGER
    probs = check(root, ledger_rel)
    for p in probs:
        print("FAIL " + p)
    if probs:
        return 1
    path = Path(ledger_rel)
    if not path.is_absolute():
        path = root / ledger_rel
    rows, _ = parse_ledger(path.read_text(encoding="utf-8"))
    print("PASS 内容台账：%d 行全部可机检（覆盖面双向相等、去向可达、改名一致、判据非空）" % len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
