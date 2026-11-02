# -*- coding: utf-8 -*-
"""v9.13.4 结构评审: 跨文件近重复表述扫描（只读）。

方法：抽句子 -> 归一化 -> 8 字符 shingle -> Jaccard >= 0.55 视为近重复对。
输出按重复对数排的文件热点 + 具体重复句对样例。
"""
import re
import glob
from itertools import combinations
from collections import defaultdict

FILES = sorted(glob.glob("references/*/*.md")) + ["SKILL.md"]

def norm(s: str) -> str:
    s = re.sub(r"[|`*_>#\[\]()]", "", s)
    s = re.sub(r"\s+", "", s)
    return s

def shingles(s: str, k=8):
    return {s[i:i + k] for i in range(max(0, len(s) - k + 1))}

sentences = []  # (file, lineno, norm_text, shingle_set)
for fp in FILES:
    with open(fp, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("<!--") or line.startswith("---"):
                continue
            # 按中文句读切句
            for seg in re.split(r"[。；;]", line):
                n = norm(seg)
                if len(n) >= 15:  # 太短的句子没有指纹价值
                    sentences.append((fp, ln, n, shingles(n)))

print(f"files={len(FILES)} sentences(>=15字)={len(sentences)}")

pairs = []
for (f1, l1, n1, s1), (f2, l2, n2, s2) in combinations(sentences, 2):
    if f1 == f2 and abs(l1 - l2) <= 2:
        continue  # 同文件相邻行跳过
    inter = len(s1 & s2)
    if inter == 0:
        continue
    jac = inter / len(s1 | s2)
    if jac >= 0.55:
        pairs.append((jac, f1, l1, n1[:70], f2, l2, n2[:70]))

pairs.sort(reverse=True)
print(f"near-dup pairs (J>=0.55): {len(pairs)}")

# 文件对热点
hot = defaultdict(int)
for p in pairs:
    key = tuple(sorted([p[1], p[4]]))
    hot[key] += 1

print("\n== 跨文件重复热点 TOP15 ==")
for (f1, f2), c in sorted(hot.items(), key=lambda x: -x[1])[:15]:
    if f1 != f2:
        print(f"  {c:3d}  {f1}  <->  {f2}")

print("\n== 同文件内重复（间隔>2行） TOP10 ==")
same = defaultdict(int)
for p in pairs:
    if p[1] == p[4]:
        same[p[1]] += 1
for f, c in sorted(same.items(), key=lambda x: -x[1])[:10]:
    print(f"  {c:3d}  {f}")

print("\n== 重复句对样例（J 最高 25 条，仅跨文件） ==")
shown = 0
for jac, f1, l1, n1, f2, l2, n2 in pairs:
    if f1 != f2:
        print(f"\n[J={jac:.2f}] {f1}:{l1}\n    {n1}\n  {f2}:{l2}\n    {n2}")
        shown += 1
        if shown >= 25:
            break
