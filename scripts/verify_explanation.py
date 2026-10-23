#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_explanation.py - 讲义(materials/*.md)静态结构校验(stdlib-only、幂等只读、--selftest)。

用途:对私人家教工作流的讲义材料做静态校验。静态脚本只能证明结构与格式约束,
不能证明数学、事实、代码或教学体验正确(语义正确性须人工/领域复核,见 spec
「验收证据边界」)。

【Markdown 解析契约(冻结——修改须同步 spec 与 selftest)】
1. 概念单元边界:行首 `## 概念 <数字> · …` 开启一个单元,至下一个 `## ` 二级标题
   (下一个概念单元、自测/检验答案区或其他节)或文件尾;三级标题(###)不切断单元;
   「## 概念地图」无数字编号,不是概念单元。
2. 定稿/草稿标识:头部(第一个 `## ` 之前)的 `- 状态:<基值>(<括注>)` 行;
   基值 = 冒号后、第一个全/半角左括号前的文本(去 `*` 与空白);基值含「定稿」→
   定稿文件,其余(含「草稿」与无状态行)一律按草稿处理。
3. 答案框起止:概念单元内 `③ 答案(…):` 标记行之后,跳过空行,
   自首个 `>` 引用行起连续收集(中间空行后仍为 `>` 行则延续;出现非 `>` 非空行即止)。
   框体 = Markdown 引用块;③标记行存在但框体缺失报 E-BOX-INCOMPLETE。
   标记行须留空:行内带实质内容会与框内答案并存、易不一致,报 W-MARKER-CONTENT。
   框内不写题面段(题目归 ①题目),直接从交付起笔写解题过程;标记行须行首起(正文提及不算)。
   框内分段:一段一个可独立核对的最小单元(计算类即一次变形/一次代入/一次判定),
   段间用只含 `>` 的空行隔开;段数不设下限(单步答案一段即可)。
   段内多行只在拆断了行内 `$…$` 公式或 code span(该行定界符未闭合)时报 E-BOX-WRAP
   ——渲染会直接损坏;普通文字多行不报,由「讲解出厂自检」人工核对。
   例外:框内 fenced 代码块(``` 起止)整块算一段,块内多行不计段内断行,
   块内也不查体例四类(编号/箭头/验算/批注)。
   框内体例与学科无关,只认一件:任一段以交付标识起笔
   (解/答/解答/证明/答案/参考答案/参考概括/参考译文/译文/范文/例文/代码/脚本/输出/步骤/操作/
   Answer/Solution/Proof/Model answer/Sample answer/Translation/Output/Code),
   或框内直接给出代码块(代码本身即可交付)。数学的「解:」只是交付标识之一,不是唯一形态。
   交付标识段须有实质内容:去掉标识与标点后为空,或只剩占位词(略/从略/见教材/见课本/
   同上/自行体会/此处省略/答案见…,限 20 字内)→ 报 E-BOX-EMPTY。
4. 排除范围(不参与正文 Unicode 检查):
   - ``` 代码围栏内全部行;
   - 行内 code span(`…`)与 $…$ / $$…$$ 公式内字符(剥除后按可见正文检查);
   - 答案框与非答案框的 `>` 引用块(前者按框体例单独查 E,后者整体豁免);
   - 自测/检验答案区(标题见规则 10;至下一个 `## ` 或文件尾)——节末练习短答案与五要素之③
     合法并存,不属五要素之③;该区答案可短,但只有占位词(略/见教材/同上)报
     W-SELFTEST-EMPTY(不阻断,学员无法据此对答案);整区只有标题、无任何答案行同样报此码
     (框内非空围栏代码块算作答,不判空)。
   - 判分记账状态行(「状态(日期…):…」模式)——定稿下它已被 E-LEDGER-RESIDUE
     单独捕获、草稿下它是合法记录位,均不再重复报 Unicode。
5. 分层标签允许形式:含核心词「最小必需」「选学」「后期必用」「参照」之一(允许「本节」
   前缀省略与「——/(…)」括注变体);位置为概念单元正文,或规划区(第一个概念单元
   之前)中对应概念行——表格行 `| 概念 N |…|` 或列表行 `N. …`。
   「参照」对应深度契约的参照级:只需 ①题目(定义与边界写在正文),可标
   「③ 不适用(参照级)」豁免②③④⑤;工作级/最小必需级不可用参照豁免。
6. 五要素标记:①题目 / ②解析 / ③答案 / ④易错 / ⑤小结。
   ③ 是答案框(见规则 3),标记行须在行首(可带列表项 `-`/`1.` 或加粗),匹配「③ 答案」,后缀括注可选;正文提及「见 ③ 答案」不作标记;
   ⑤ 是小结(≤3 句、只压缩不引入新信息),标记行匹配「⑤ 小结」——脚本只查标记存在,
   摘要内容质量归人工出厂自检。
   纯概念/记忆类可显式标注「③ 不适用(纯概念)」申请豁免:同时豁免②③(二者同属
   「完整示例」),①题目、④易错、⑤小结仍须具备;单元内引用块无交付标识起笔即通过。
   若同时存在「③ 答案」标记报 E-THIRD-CONFLICT;若仍有交付标识起笔
   (解:/答:/代码:/Answer: 等)报 E-THIRD-EXEMPT-MISUSE(豁免不得用于含可复现解答的单元)。
   单元内出现旧编号(①目标 / ⑤标准答案 / ⑤卷面)时只报一条 E-MARKER-LEGACY
   (附迁移对照),该单元不再叠加缺项与框体例错误。

7. 扩展(选读)区:行首 `## 扩展` 起至文末(扩展区须为文件最后一个区);区内概念单元与
   答案框豁免五要素(E-REQ-MISSING)、分层标注(W-NO-TIER)与框体例(E-BOX-*),正文 Unicode 照查。

8. 给分点量表(框外,备考/阅卷型适用):含「给分点量表」的行,按 `（N分）` 取各点分值、
   按「合计 N 分」取声明总分;两者齐全时校验相加(E-RUBRIC-SUM)。该行须标性质——
   「训练量表」或「官方」字样,缺失报 W-RUBRIC-SOURCE。非备考任务不写量表,不受此查。

9. 节首导读(定稿必备三行,草稿不查):头部(第一个 `## ` 之前)须含「本节目标」「前置」
   「预计」三项;定稿缺任一 → E-HEADER-BRIEF。

10. 自测/检验答案区(标题约定——题面与答案共用词干,长词干在前):
   题面区认 `## 本节自测` / `## 自测` / `## 自测题` / `## 检验` / `## 检验题` /
   `## 检验问题` / `## 本节检验`(词干后可跟空白、全/半角括号或冒号);
   答案区认同词干 + `答案`/`答案区`/`答案要点`/`答案与解析`,也认通用的 `## 答案` / `## 参考答案`
   (`## 本节自测答案` 最常用)。标题统一用中文,不认英文标题(`## Self-test` 等)。
   一个文件可有多个答案区(如自测、检验各一区),逐区检查。
   题面区之后没有同族(自测/检验)答案区、也没有通用答案区 → W-SELFTEST-MISSING
   (答案无处可查;文末一个 `## 参考答案` 可统管前面多个题面区,同族答案区只覆盖同类题面区);
   有答案区时按规则 3b 逐区查占位词与空区(W-SELFTEST-EMPTY)。
   **开放/动手检验豁免**:题面区内出现 `- 检验说明:开放题,无标准答案`
   (含 开放/口头/无标准答案/不设/跳过/练手/动手/压缩 任一字样)即不报 MISSING——
   口头复述、动手练手类本无书面答案,但豁免须显式写出,不能靠不写答案默认获得。

11. 图引用死链(仅当校验入口能确定讲义所在目录时执行):框内 `图：<相对路径>` 与
   Markdown 图片语法 `![](<相对路径>)` 须指向真实文件,缺失报 E-IMG-DEADLINK;
   http(s)/data: 等外部地址与锚点不查。

【规则表(13 类检查 / 27 个规则码;末组 W-READER-* 仅 --reader 启用)】
| 规则码           | 级 | 触发条件                                                            |
|------------------|----|---------------------------------------------------------------------|
| E-LEDGER-RESIDUE | E  | 定稿文件正文含判分记账状态行(「状态(…):已通过/关闭/讲授中」等);草稿不查 |
| E-REQ-MISSING    | E  | 概念单元五要素缺失(单元级;纯概念标「③ 不适用」时②③ 豁免,①④⑤仍查;参照级标「③ 不适用(参照级)」时②③④⑤ 豁免,仅查①) |
| W-UNICODE-CHAR   | W  | 讲义可见正文出现 denylist 字符(→ ✔ ✓ ✅ √ ≤ ≥ ∪ ⇔ ⇒)               |
| E-BOX-FORMAT     | E  | 答案框内出现句中 ①–⑩ 分点编号 / → ⇒ 箭头 / ✓ ✔ ✅ 验算标记 / 讲解批注行(围栏代码块内不查;√ 视为根号,不算验算标记) |
| E-BOX-INCOMPLETE | E  | 答案框缺交付起笔标识,或 ③标记行后无框体                           |
| E-BOX-EMPTY      | E  | 交付标识段去标识与标点后为空,或只剩「略/见教材/同上/自行体会」等占位词(20 字内) |
| E-RUBRIC-SUM     | E  | 给分点量表各点分值之和 ≠ 声明合计(两项齐全才判,缺项不报)          |
| W-RUBRIC-SOURCE  | W  | 给分点量表未标性质(缺「训练量表」或「官方」字样)                     |
| W-SELFTEST-EMPTY | W  | 自测/检验答案区只有占位词(略/见教材/同上)或整区为空,学员无法对答案 |
| W-SELFTEST-MISSING | W | 有自测/检验题面区(标题见规则 10),但其后无同族/通用答案区(答案无处可查;开放/动手检验须写「- 检验说明:」显式豁免) |
| E-BOX-WRAP       | E  | 答案框段内断行拆断了行内 `$…$` / code span(渲染直接损坏)            |
| W-MARKER-CONTENT | W  | `③ 答案` 标记行带了答案内容(应与框内答案并存时易不一致;标记行应留空) |
| W-NO-TIER        | W  | 概念单元(含规划区对应行)无「最小必需/选学/后期必用/参照」任一分层标注 |
| W-STYLE-POINTER  | W  | 头部出现「…体例(/…排版(/…约定(/…格式(」整段规则块(疑似重复,应为指针行);头部含「体例约定(」指针行即合规 |
| E-MARKER-LEGACY  | E  | 单元内出现旧编号(①目标 / ⑤标准答案 / ⑤卷面);每单元只报一条,不再叠加缺项与框体例 |
| E-THIRD-CONFLICT | E  | 概念单元同时标注「③ 不适用(纯概念)」与「③ 答案」(自相矛盾)       |
| E-THIRD-EXEMPT-MISUSE | E | 标注了「③ 不适用」但单元引用块内仍有「解:/答:」解答起笔(豁免被滥用) |
| E-HEADER-BRIEF   | E  | 定稿文件头部缺「本节目标」「前置」「预计」任一(草稿不查)             |
| E-IMG-DEADLINK   | E  | `图：<相对路径>` 或 `![](<相对路径>)` 指向的文件不存在(死链)        |
| W-READER-HEADING | W  | 读者版标题层级跳级(H1→H3 等);仅 `--reader`                       |
| W-READER-TABLE   | W  | 读者版表格缺表头分隔行、列数不在 2–4、表头有空列名;仅 `--reader`     |
| W-READER-ALT     | W  | 读者版图片 alt 为空或只写「示意图/图片」;仅 `--reader`               |
| W-READER-SVG     | W  | 读者版 SVG 根元素缺 viewBox/role、缺 title/desc、字号 <14/线宽 <1.5、含脚本/外链;仅 `--reader` |
| W-READER-OVERVIEW | W | 读者版 `## 本节速览` 缺失、非 3 列或数据行不在 1–3;仅 `--reader`      |
| W-READER-INDEX   | W  | 读者版 `## 回看索引` 缺「核心一句话/最容易错/下一步」;仅 `--reader`    |
| W-READER-CONCLUSION | W | 启用 `## 本节速览` 时概念单元首行缺「一句话结论:」;纯概念/参照/L3 豁免;仅 `--reader` |
| W-READER-EMPHASIS | W | 读者版连续两段普通段落都出现 ≥2 处加粗;仅 `--reader`              |

denylist 口径:任务点名字符(→ ✓ √ ≤ ≥ ∪ ⇔)及其同族验算/箭头标记(✔ ✅ ⇒);
乘号「×」、全角「＝」等修辞/排版字符未纳入,避免误伤中文修辞用法。
框内只查体例四类(分点/箭头/验算/批注);≤ ≥ ∪ 等数学符号在框内不查(框体豁免
正文 W,LaTeX 合规性由 formula-typesetting 机制负责,不在本脚本范围)。框内验算
标记只认 ✓ ✔ ✅——「√」在答案里绝大多数是根号(`x=√2`),不再按对勾处理。

用法:
    python verify_explanation.py <材料目录|单文件.md>   # 目录递归取 *.md(忽略 assets/ 与非 .md)
    python verify_explanation.py <材料目录|单文件.md> --reader  # 加跑读者版 W 级可读性检查(不阻断)
    python verify_explanation.py --selftest            # 内嵌样例自检(临时目录,不写盘被校验目录)

输出:按 文件路径→行号→规则码 稳定排序,逐条「[级] 码 路径:行号 提示」;末尾摘要行。
退出码:0 = 无 E(可有 W);1 = 有 E;2 = 用法/路径错误。
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

# ── denylist:已被 LaTeX 约定取代的 Unicode 写法(顺序即输出消息中的展示顺序)──
DENY_CHARS = "→✔✓✅√≤≥∪⇔⇒"
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
# 交付标识:可复现答案的起笔,覆盖数学/编程/语言/文科/记忆/设计/精读各族
LEAD_WORDS = ("参考答案|参考概括|参考译文|解答|答案|证明|译文|范文|例文|代码|脚本|输出|步骤|操作|方案|设计说明|解|答"
              "|Model answer|Sample answer|Answer|Solution|Proof|Translation"
              "|Output|Code|Script|Steps|Key")
LEAD_RE = re.compile(r"^\s*(?:" + LEAD_WORDS + r")\s*[：:]", re.I)

CONCEPT_RE = re.compile(r"^##\s*概念\s*(\d+)")
H2_RE = re.compile(r"^##\s")
# 自测/检验标题约定(见 lecture-styles「自测与题组的分工」):题面区=词干,
# 答案区=词干+答案(可带「区/与解析」);长词干在前,避免「## 检验问题答案」被 `检验` 先吃掉。
# 词干后须是行尾/空白/左括号/冒号:防「## 检验方法」「## 检验步骤」「## 检验清单」被当成
# 题面区,也防交替回溯让「## 检验问题答案」经 `检验` 分支漏成题面区。
SELFTEST_TAIL = r"(?![^\s（(：:])"
SELFTEST_STEM = r"(?:本节)?(?:检验问题|自测题?|检验题?)"
SELFTEST_ANS_TAIL = r"(?:区|要点|[与及和]?解析)?"
SELFTEST_HEAD_RE = re.compile(
    r"^##\s*(?:" + SELFTEST_STEM + r"\s*答案" + SELFTEST_ANS_TAIL +
    r"|(?:本节)?(?:参考)?答案" + SELFTEST_ANS_TAIL + r")" + SELFTEST_TAIL)
# 开放/动手检验豁免:题面区内显式声明不按书面答案核对(开放、口头、练手、本节不设),不报 MISSING
SELFTEST_OPEN_RE = re.compile(
    r"^\s*[-*]\s*(?:检验|自测)说明\s*[：:].*"
    r"(?:开放|口头|无标准答案|不设|跳过|练手|动手|压缩)")
STATUS_LINE_RE = re.compile(r"^-\s*状态\s*[:：]\s*(.*)$")
# 记账状态行:「状态(日期…):」+ 判分词确认;头部「- 状态:定稿(…)」是「状态:」在前,
# 不满足「状态(」紧邻结构,不会误命中
LEDGER_RE = re.compile(r"状态\s*[(（][^)）]*[)）]\s*[:：]")
LEDGER_WORD_RE = re.compile(r"通过|关闭|讲授中|已讲|封档")
# 列表项前缀:项目符号(- * +)或「1. / 1、/ 1)」;标记行须在行首,正文提及不算
_ITEM = r"(?:[-*+]\s+|\d+[.、)]\s*)"


def marker_re(num, word):
    """五要素标记行:行首(可带列表项与加粗),正文提及「见 ③ 答案」不算标记。"""
    return re.compile(r"^\s*" + _ITEM + r"?(?:\*\*)?\s*" + num + r"\s*" + word, re.M)


THIRD_RE = marker_re("③", "答案")              # 答案框标记行
FIFTH_RE = marker_re("⑤", "小结")              # 小结标记行(必检;只查存在,内容归人工自检)
# 标记行带内容:与框内答案并存、易不一致 → W(标记行应留空)
MARKER_CONTENT_RE = re.compile(
    r"^\s*" + _ITEM + r"?(?:\*\*)?\s*③\s*答案\s*"
    r"(?:[（(][^)）]*[)）])?\s*[：:]\s*(.*)$")
# 旧编号残留:①目标 / ⑤标准答案 / ⑤卷面 —— 整单元只报一条,不叠加缺项与框体例
LEGACY_MARK_RE = re.compile(
    r"^\s*" + _ITEM + r"?(?:\*\*)?\s*(?:①\s*目标|⑤\s*(?:标准答案|卷面))", re.M)
EXT_HEAD_RE = re.compile(r"^##\s*扩展")
THIRD_EXEMPT_RE = re.compile(
    r"^\s*" + _ITEM + r"?(?:\*\*)?\s*③\s*不适用|纯概念[·・]?\s*无\s*③", re.M)
# 豁免误用检测:只认引用块内的交付标识起笔(答案框体例),
# 不匹配普通行首的问答式表述(如「答:这个术语指……」),避免误伤纯概念正文
SOLVED_LEAD_RE = re.compile(r"(?m)^\s*>\s*(?:" + LEAD_WORDS + r")\s*[：:]", re.I)
REQ_RES = (
    (marker_re("①", "题目"), "① 题目"),
    (marker_re("②", "解析"), "② 解析"),
    (marker_re("③", "答案"), "③ 答案"),
    (marker_re("④", "易错"), "④ 易错"),
    (marker_re("⑤", "小结"), "⑤ 小结"),
)
# ②③同属「完整示例」,纯概念豁免时一并跳过;①题目、④易错、⑤小结仍须具备
EXAMPLE_ITEMS = ("② 解析", "③ 答案")
TIER_WORDS = ("最小必需", "选学", "后期必用", "参照")
# 概念单元正文必须用【…】标签承载分层;规划区行保留纯文本兼容(表格列/列表行)
TIER_TAG_RE = re.compile(r"【[^】]*(?:最小必需|选学|后期必用|参照)[^】]*】")
PLAN_ROW_RE = re.compile(r"^\s*(\d+)\s*\.\s")
PLAN_TABLE_RE = re.compile(r"^\|\s*概念\s*(\d+)\s*\|")
# 头部整段规则块:体例/排版/约定/格式 + 括号(全半角);指针行(体例约定()另行放行
POINTER_BLOCK_RE = re.compile(r"(?:体例|排版|约定|格式)\s*[（(]")
POINTER_OK_RE = re.compile(r"体例约定\s*[（(]")
# 节首导读三行(定稿必备);草稿不查
BRIEF_WORDS = ("本节目标", "前置", "预计")
# 自测题面区(有题无答案区 → W);「…答案」由 SELFTEST_HEAD_RE 单独识别
SELFTEST_STEM_RE = re.compile(r"^##\s*" + SELFTEST_STEM + SELFTEST_TAIL)
# 标题正文归类(自测/检验),用于判断答案区是否与题面区同族——「本节自测答案」
# 要能覆盖「## 自测题」,所以按族比而不是按字面前缀比
SELFTEST_KEY_RES = (("自测", re.compile(r"^(?:本节)?自测题?")),
                    ("检验", re.compile(r"^(?:本节)?检验(?:问题|题)?")))


def is_selftest_q(line):
    """题面区标题 = 是自测/检验标题,且不是对应的答案区。"""
    return bool(SELFTEST_STEM_RE.match(line)) and not SELFTEST_HEAD_RE.match(line)


def selftest_key(body):
    """标题正文归类:自测 / 检验 / None(通用答案区或非自测标题)。"""
    for key, rx in SELFTEST_KEY_RES:
        if rx.match(body):
            return key
    return None


def answer_covers(q_line, a_line):
    """该答案区是否覆盖这个题面区:同族答案区,或通用答案区(## 答案 / ## 参考答案)。

    同族只覆盖同类题面区(「检验问题答案」不给「自测」兜底);通用答案区出现在
    题面区之后即视为覆盖——文末一个「## 参考答案」统管前面多个题面区是合法布局。
    """
    q_key = selftest_key(q_line.strip().lstrip("#").strip())
    a_key = selftest_key(a_line.strip().lstrip("#").strip())
    return a_key is None or a_key == q_key
# 图引用:框内「图:assets/x.svg(示意)」与 Markdown 图片语法;外部地址不查
IMG_LABEL_RE = re.compile(r"图\s*[：:]\s*([^\s（()）]+)")
IMG_MD_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
MD_IMAGE_ALT_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
GENERIC_ALT = {"图", "图片", "示意图", "图像", "figure", "image", "diagram"}
BOX_ANNOT_RE = re.compile(r"^\s*>\s*[（(]?\s*(?:注意?|验证|说明|批注)\s*[:：]")
# 占位答案:结构上像答案、实际不可复现;限 20 字内,避免误伤含「略」的正常表述
PLACEHOLDER_RE = re.compile(
    r"^(?:[（(]\s*略\s*[)）]|略[。.]?$|从略|见(?:教材|课本|原书|讲义|本节答案|上文答案)"
    r"|同上[。.]?$|自行(?:体会|补充|推导|查看|思考)|此处省略|答案见)")
ANSWER_PUNCT_RE = re.compile(r"[\s。．.，,；;：:、…—\-（）()【】\[\]\"'“”!！?？]+")


def has_code_block(lines, start, end):
    """答案区内是否有非空的围栏代码块(编程类自测以代码作答,不得判空)。"""
    in_fence = False
    for i in range(start, end):
        s = lines[i].strip()
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence and s:
            return True
    return False
# 给分点量表:框外单独一行,「①…（2分）；②…（3分）；合计 5 分（训练量表,非官方细则）」
RUBRIC_RE = re.compile(r"给分点量表")
SCORE_RE = re.compile(r"[（(]\s*(\d+(?:\.\d+)?)\s*分\s*[)）]")
TOTAL_RE = re.compile(r"合计\s*(\d+(?:\.\d+)?)\s*分")
RUBRIC_SOURCE_RE = re.compile(r"训练量表|官方")


def compute_visible(lines):
    """逐行产出「可见正文」:剥代码围栏、行内 code span、$…$ 与 $$…$$ 公式。

    返回 (vis_lines, fence_flags)。围栏内 vis 为空串;跨行 $$ 块起点整行退出正文,
    直到含闭合 $$ 的行。公式/代码内的 denylist 字符(如 `\rightarrow` 的字面引用、
    code span 中引述的旧写法示例)因此天然豁免。
    """
    vis, fence = [], []
    in_fence = False
    in_math_block = False
    for ln in lines:
        if in_fence:
            vis.append("")
            fence.append(True)
            if ln.lstrip().startswith("```"):
                in_fence = False
            continue
        if ln.lstrip().startswith("```"):
            vis.append("")
            fence.append(True)
            in_fence = True
            continue
        fence.append(False)
        if in_math_block:
            vis.append("")
            if "$$" in ln:
                in_math_block = False
            continue
        out = []
        i, n = 0, len(ln)
        mode = None  # None=正文 / "code"=code span / "inline"=行内公式
        while i < n:
            ch = ln[i]
            if mode is None:
                if ch == "`":
                    mode = "code"
                    out.append(" ")
                elif ch == "$":
                    if i + 1 < n and ln[i + 1] == "$":
                        j = ln.find("$$", i + 2)
                        if j != -1:            # 单行内闭合的 $$…$$
                            out.append(" " * (j + 2 - i))
                            i = j + 2
                            continue
                        in_math_block = True   # 跨行块起点:整行退出正文
                        out = [" "] * n
                        break
                    mode = "inline"
                    out.append(" ")
                else:
                    out.append(ch)
            elif mode == "code":
                if ch == "`":
                    mode = None
                out.append(" ")
            else:  # 行内公式;未闭合则该行剩余均视为公式内
                if ch == "$":
                    mode = None
                out.append(" ")
            i += 1
        vis.append("".join(out))
    return vis, fence


def parse_doc(lines):
    """划分文档结构:头部/规划区边界、概念单元列表、自测/检验答案区范围(可多区)、定稿标识。"""
    n = len(lines)
    h2 = [i for i, ln in enumerate(lines) if H2_RE.match(ln)]
    header_end = h2[0] if h2 else n
    units = []
    for pos, i in enumerate(h2):
        m = CONCEPT_RE.match(lines[i])
        if m:
            end = h2[pos + 1] if pos + 1 < len(h2) else n
            units.append({"num": int(m.group(1)), "start": i, "end": end})
    plan_end = units[0]["start"] if units else n
    # 答案区可有多个(如自测、检验各一区):逐区收集,逐区查占位/空区
    selftest_rngs = []
    for st in [i for i, ln in enumerate(lines) if SELFTEST_HEAD_RE.match(ln)]:
        after = [i for i in h2 if i > st]
        selftest_rngs.append((st, after[0] if after else n))
    # 定稿判定只认头部第一条状态行的基值(冒号后、左括号前),括注里的
    # 「闸口通过后转定稿」等字样不得影响判定
    is_final = False
    for ln in lines[:header_end]:
        m = STATUS_LINE_RE.match(ln)
        if m:
            base = re.split(r"[（(]", m.group(1))[0].replace("*", "").strip()
            is_final = "定稿" in base
            break
    return {"header_end": header_end, "plan_end": plan_end, "units": units,
            "selftest": selftest_rngs, "is_final": is_final}


def box_body(line):
    """取引用行去 `>` 后的正文(保留行内可见文本)。"""
    s = line.strip()
    return s[1:].strip() if s.startswith(">") else s


# 题号前缀:多题单元在框内以「（1）/1.」起笔属正常卷面,不算「缺交付起笔」
QNUM_RE = re.compile(r"^\s*(?:[（(]\s*\d+\s*[)）]|\d+\s*[.、)])\s*")


def lead_text(vis_line):
    """取段落首行的起笔文本:剥引用标记、题号与强调符,便于匹配交付标识。"""
    t = re.sub(r"^\s*>+\s?", "", vis_line).strip()
    return QNUM_RE.sub("", re.sub(r"[*_]", "", t)).strip()


def answer_body(line):
    """交付标识段的答案正文(保留公式与代码字面,去引用符、题号与强调符)。"""
    return LEAD_RE.sub("", QNUM_RE.sub("", re.sub(r"[*_`]", "", box_body(line))), count=1).strip()


def split_paragraphs(lines, rows):
    """按「只含 > 的空行」切分答案框段落,围栏代码块整块算一段。

    返回 [{"rows": [行号,...], "code": bool}, ...](保持行序)。code=True 的段是
    框内 ``` 围栏块,块内多行不按「段内断行」判,块内也不查体例四类。
    """
    paras, cur = [], []

    def flush(code=False):
        if cur:
            paras.append({"rows": list(cur), "code": code})
            del cur[:]

    in_code = False
    for r in sorted(rows):
        body = box_body(lines[r])
        is_fence = body.startswith("```")
        if in_code:
            cur.append(r)
            if is_fence:            # 闭合围栏:整块收尾
                in_code = False
                flush(code=True)
            continue
        if is_fence:
            flush()                 # 围栏另起一段
            cur.append(r)
            in_code = True
            continue
        if body:
            cur.append(r)
        else:
            flush()
    flush(code=in_code)             # 未闭合围栏按代码段收尾,渲染仍是一块
    return paras


def breaks_inline(lines, rows):
    """段内多行是否拆断了行内 `$…$` 公式或 code span(定界符跨行未闭合)。

    整行成对的 `$$…$$` 与成对 code span 先剥离,再看剩余定界符奇偶;
    奇数说明该行的公式/代码被换行截断,渲染会直接损坏(判 E 的唯一情形)。
    """
    for r in rows:
        body = box_body(lines[r])
        body = re.sub(r"\$\$.*?\$\$", "", body)
        body = re.sub(r"`[^`]*`", "", body)
        if body.count("$") % 2 or body.count("`") % 2:
            return True
    return False


def collect_boxes(lines, units):
    """定位每个③标记行对应的答案框。返回 [{marker_line, rows, exists, paras}]。"""
    boxes = []
    for u in units:
        for i in range(u["start"], u["end"]):
            if not THIRD_RE.search(lines[i]):
                continue
            rows = set()
            j = i + 1
            while j < u["end"] and not lines[j].strip():   # 跳过标记行与框之间的空行
                j += 1
            started = False
            while j < u["end"]:
                s = lines[j].strip()
                if s.startswith(">"):
                    rows.add(j)
                    started = True
                    j += 1
                elif not s and started:
                    # 松散引用:空行后仍是 > 行则延续,否则框结束
                    k = j + 1
                    while k < u["end"] and not lines[k].strip():
                        k += 1
                    if k < u["end"] and lines[k].strip().startswith(">"):
                        j = k
                        continue
                    break
                else:
                    break
            boxes.append({"marker_line": i, "rows": rows, "exists": started,
                          "paras": split_paragraphs(lines, rows) if started else []})
    return boxes


def _table_cells(row):
    """拆 Markdown 表格行;返回去首尾空格的单元格。"""
    return [c.strip() for c in row.strip().strip("|").split("|")]


def _is_table_sep(row):
    """表格分隔行:每个单元格形如 --- / :--- / ---: / :---:。"""
    cells = _table_cells(row)
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c or "") for c in cells)


def _table_blocks(lines, fence):
    """收集连续表格行(围栏代码块内不算),返回每块的行号列表。"""
    blocks, cur = [], []
    for i, ln in enumerate(lines):
        if not fence[i] and ln.strip().startswith("|"):
            cur.append(i)
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    return blocks


def _svg_reader_problems(path):
    """读者版 SVG 技术项:根元素 viewBox/role、title/desc、字号/线宽、无脚本/外链。"""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return ["SVG 读取失败"]
    problems = []
    root = re.search(r"<svg\b[^>]*>", text, re.I)
    if not root or "viewBox=" not in root.group(0):
        problems.append("根元素缺 viewBox")
    if not root or not re.search(r"role\s*=\s*[\"']img[\"']", root.group(0)):
        problems.append("根元素缺 role=\"img\"")
    for tag, label in (("<title", "title"), ("<desc", "desc")):
        if tag not in text:
            problems.append("缺 <{}>".format(label))
    if "<script" in text.lower():
        problems.append("含 script")
    if re.search(r"(?:href|xlink:href)\s*=\s*[\"']https?://", text, re.I):
        problems.append("含外部引用")
    for raw in re.findall(r"font-size\s*=\s*[\"']([0-9.]+)", text):
        if float(raw) < 14:
            problems.append("字号 {} < 14".format(raw))
    for raw in re.findall(r"stroke-width\s*=\s*[\"']([0-9.]+)", text):
        if float(raw) < 1.5:
            problems.append("线宽 {} < 1.5".format(raw))
    return problems


def reader_checks(lines, doc, vis, fence, base_dir, box_rows, add):
    """读者版 P1 可读性检查(W 级,只在 --reader 时执行,不阻断旧讲义)。

    这里只查可静态判定的结构项:标题层级、表格、图片 alt/SVG、速览/回看索引、
    概念首行一句话结论、段落强调。语义上的“是否更易读”仍归人工读者验证。
    """
    # 1. 标题层级不跳级
    prev = 0
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        m = re.match(r"^(#{1,6})\s+", ln)
        if not m:
            continue
        level = len(m.group(1))
        if prev and level > prev + 1:
            add("W", "W-READER-HEADING", i,
                "标题层级跳级 H{}→H{}——用 H2 分单元、H3 分小节,不跳级".format(prev, level))
        prev = level

    # 2. 表格:表头 + 2–4 列(手机可读)
    for block in _table_blocks(lines, fence):
        if len(block) < 2 or not _is_table_sep(lines[block[1]]):
            add("W", "W-READER-TABLE", block[0],
                "表格缺表头分隔行——补齐「| 列名 | … |」与「|---|---|」")
            continue
        header = _table_cells(lines[block[0]])
        if len(header) < 2 or len(header) > 4:
            add("W", "W-READER-TABLE", block[0],
                "表格列数 {}——手机端保持 2–4 列,宽表拆成列表或两张表".format(len(header)))
        if any(not c for c in header):
            add("W", "W-READER-TABLE", block[0],
                "表头存在空列名——每列写清名称,单位放表头")

    # 3. 图片 alt 与 SVG 技术项
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        for m in MD_IMAGE_ALT_RE.finditer(vis[i]):
            alt, target = m.group(1).strip(), m.group(2).strip()
            if not alt or alt.lower() in GENERIC_ALT:
                add("W", "W-READER-ALT", i,
                    "图片 alt 为空或过于笼统——写「图型:一句话结论」,不写「示意图/图片」")
            if base_dir is None or re.match(r"(?:https?:|data:|mailto:)", target, re.I):
                continue
            path = Path(target) if Path(target).is_absolute() else Path(base_dir) / target
            if path.suffix.lower() == ".svg" and path.exists():
                probs = _svg_reader_problems(path)
                if probs:
                    add("W", "W-READER-SVG", i,
                        "SVG 读者版技术项不合格:" + "、".join(probs) +
                        "——补 viewBox/role/title/desc,字号 ≥14、线宽 ≥1.5,去脚本/外链")

    # 4. 本节速览:位置 + 3 列、1–3 行数据
    if "## 本节速览" in lines:
        start = lines.index("## 本节速览")
        first_unit = doc["units"][0]["start"] if doc["units"] else len(lines)
        if start > first_unit:
            add("W", "W-READER-OVERVIEW", start,
                "本节速览应在第一个 ## 概念 之前——读者先看路线,再看单元")
        block = []
        for j in range(start + 1, len(lines)):
            if H2_RE.match(lines[j]):
                break
            if fence[j]:
                continue
            if lines[j].strip().startswith("|"):
                block.append(j)
            elif block:
                break
        if len(block) < 2:
            add("W", "W-READER-OVERVIEW", start,
                "本节速览表缺失或不完整——用 3 列「要解决的问题 | 一句话结论 | 用在哪」")
        else:
            cols = len(_table_cells(lines[block[0]]))
            if cols != 3:
                add("W", "W-READER-OVERVIEW", block[0],
                    "本节速览应为 3 列,实际 {}".format(cols))
            data_rows = len(block) - 2
            if not 1 <= data_rows <= 3:
                add("W", "W-READER-OVERVIEW", block[0],
                    "本节速览数据行 {}——只留 1–3 行,对应 1–3 项关键能力".format(data_rows))

    # 5. 回看索引三行 + 位置(答案区之后,停车位/扩展区之前)
    if "## 回看索引" in lines:
        start = lines.index("## 回看索引")
        end = next((j for j in range(start + 1, len(lines)) if H2_RE.match(lines[j])),
                   len(lines))
        tail = "\n".join(lines[start:end])
        for key in ("核心一句话", "最容易错", "下一步"):
            if key not in tail:
                add("W", "W-READER-INDEX", start,
                    "回看索引缺「{}」——用「核心一句话/最容易错/下一步」三行".format(key))
        last_ans = max((i for i, ln in enumerate(lines) if SELFTEST_HEAD_RE.match(ln)),
                       default=-1)
        if start <= last_ans:
            add("W", "W-READER-INDEX", start,
                "回看索引应在自测答案区之后——先做题对答案,再回看索引")
        for later in ("## 待解决问题", "## 扩展（选读）"):
            if later in lines and lines.index(later) < start:
                add("W", "W-READER-INDEX", start,
                    "回看索引应在{}之前——保持文末收束顺序".format(later))

    # 6. 概念单元首行一句话结论(只在启用 P1 速览时查;豁免单元跳过)
    if "## 本节速览" in lines:
        for u in doc["units"]:
            unit_text = "\n".join(lines[u["start"]:u["end"]])
            if THIRD_EXEMPT_RE.search(unit_text) or re.search(r"【[^】]*参照[^】]*】", unit_text):
                continue
            body = [ln.strip() for ln in lines[u["start"] + 1:u["end"]] if ln.strip()]
            if body and not re.match(r"^(?:[-*+]\s+|\d+[.、)]\s*)?一句话结论\s*[：:]", body[0]):
                add("W", "W-READER-CONCLUSION", u["start"],
                    "概念 " + str(u["num"]) + " 首行缺「一句话结论:……」——"
                    "长节/读者版先给结论再展开;纯概念/参照级/L3 可标豁免")

    # 7. 段落加粗密度:连续两段都在抢重点时提示(术语密集段可例外)
    prev_emphasis = False
    for i, ln in enumerate(lines):
        if fence[i] or i in box_rows:
            prev_emphasis = False
            continue
        s = ln.lstrip()
        if not s or s.startswith(("#", "|", ">", "```")):
            prev_emphasis = False
            continue
        count = len(re.findall(r"\*\*[^*]+\*\*", vis[i]))
        if count >= 2 and prev_emphasis:
            add("W", "W-READER-EMPHASIS", i,
                "连续两段都用了加粗——只给术语首现/关键判断/易错点;术语密集段可例外,其余改普通文字")
        prev_emphasis = count >= 2


def check_text(text, rel, base_dir=None, reader=False):
    """校验单份讲义文本,返回 findings 列表(已按 文件→行号→规则码 排序)。

    base_dir 给定时才做图引用死链检查(相对路径按讲义所在目录解析);
    selftest 等内存校验不传,避免把宿主目录当成讲义目录。
    """
    lines = text.splitlines()
    doc = parse_doc(lines)
    vis, fence = compute_visible(lines)
    boxes = collect_boxes(lines, doc["units"])
    box_rows = set()
    for b in boxes:
        box_rows |= b["rows"]
    ans_ranges = doc["selftest"]
    findings = []

    def in_answer(i):
        """是否落在任一自测/检验答案区内(短答案合法,不查五要素与 Unicode)。"""
        return any(s <= i < e for s, e in ans_ranges)

    def add(level, code, line0, msg):
        findings.append((level, code, rel, line0 + 1, msg))

    # 扩展(选读)区:本文件最后一个区,范围到文末;区内豁免五要素/分层/框体例,Unicode 照查
    ext_ranges = []
    for i, ln in enumerate(lines):
        if EXT_HEAD_RE.match(ln):
            ext_ranges.append((i, len(lines)))
            break

    def in_ext(idx):
        return any(s <= idx < e for s, e in ext_ranges)

    # ── 规则 1:定稿判分记账残留(草稿不查)──
    ledger_rows = set()
    for i, ln in enumerate(lines):
        if LEDGER_RE.search(ln) and LEDGER_WORD_RE.search(ln):
            ledger_rows.add(i)
            if doc["is_final"]:
                add("E", "E-LEDGER-RESIDUE", i,
                    "定稿内判分记账残留(「状态(日期):已通过/关闭/讲授中」等状态行)——"
                    "历史证据移 exercises/ 与 progress.md,定稿须记账零残留")

    # ── 规则 2:概念单元五要素(单元级,不得全文件计数代替)──
    legacy_units = []
    for u in doc["units"]:
        if in_ext(u["start"]):
            continue
        body = "\n".join(lines[u["start"]:u["end"]])
        if LEGACY_MARK_RE.search(body):
            legacy_units.append(u)
            add("E", "E-MARKER-LEGACY", u["start"],
                "概念 " + str(u["num"]) + " 仍是旧编号(①目标/②分步/③答案/④易错/⑤标准答案)——"
                "新体例:①题目 → ②解析 → ③答案(框) → ④易错 → ⑤小结;迁移:②分步与旧③答案"
                "并入②解析、旧③答案行删掉、⑤标准答案改③答案并删题面段、小结补⑤编号。"
                "本单元只报这一条,缺项与框体例暂不叠加")
            continue
        has_third = bool(THIRD_RE.search(body))
        exempt = bool(THIRD_EXEMPT_RE.search(body))
        if has_third and exempt:
            add("E", "E-THIRD-CONFLICT", u["start"],
                "概念 " + str(u["num"]) + " 同时标注「③ 不适用」与「③ 答案」——"
                "二者只能取一:确有可复现解答就给③框,纯概念/纯记忆/已会·检索版就删③标记")
        elif exempt:
            if SOLVED_LEAD_RE.search(body):
                add("E", "E-THIRD-EXEMPT-MISUSE", u["start"],
                    "概念 " + str(u["num"]) + " 标注「③ 不适用」但单元内仍有「解:/答:」解答起笔——"
                    "有可复现解答的概念须给完整③框,不得用豁免跳过")
            else:
                # 参照级只需①题目(定义与边界写在正文),②③④⑤一并豁免;
                # 其余情况豁免②③(同属完整示例),①题目、④易错、⑤小结仍须具备
                is_ref = bool(re.search(r"【[^】]*参照[^】]*】", body))
                drop = set(EXAMPLE_ITEMS) | ({"④ 易错", "⑤ 小结"} if is_ref else set())
                missing = [label for rx, label in REQ_RES
                           if label not in drop and not rx.search(body)]
                if missing:
                    scope = ("参照级可省②③④⑤,但①题目不得省" if is_ref
                             else "纯概念/纯记忆/已会·检索版可省②③,但①题目、④易错、⑤小结不得省")
                    add("E", "E-REQ-MISSING", u["start"],
                        "概念 " + str(u["num"]) + " 豁免下仍缺:" + "、".join(missing) +
                        "——" + scope)
        else:
            missing = [label for rx, label in REQ_RES if not rx.search(body)]
            if missing:
                add("E", "E-REQ-MISSING", u["start"],
                    "概念 " + str(u["num"]) + " 五要素缺失:" + "、".join(missing) +
                    "——①题目 ②解析 ③答案(框) ④易错 ⑤小结 逐个补齐(③ 须写在本单元内,任何 `## ` 标题都会终结单元);纯概念/纯记忆/已会·检索版无可复现产物"
                    "可标「③ 不适用(纯概念/纯记忆/已会·检索版)」豁免②③(①④⑤仍须);参照级可标"
                    "「③ 不适用(参照级)」豁免②③④⑤(①仍须);不得以全文件计数代替")

    # ── 规则 3:正文 Unicode denylist(按排除范围过滤后逐行检查)──
    for i, ln in enumerate(lines):
        if fence[i]:
            continue
        if in_answer(i):
            continue                      # 自测/检验答案区:短答案合法并存
        if i in box_rows:
            continue                      # 答案框:按 E-BOX-FORMAT 单独查
        if ln.lstrip().startswith(">"):
            continue                      # 非答案框的引用块豁免
        if i in ledger_rows:
            continue                      # 记账行已单独捕获/属合法记录位,不重复报
        hit = [ch for ch in DENY_CHARS if ch in vis[i]]
        if hit:
            add("W", "W-UNICODE-CHAR", i,
                "正文违规字符:" + "、".join(hit) +
                "——已被 LaTeX 约定取代($\\rightarrow$、$\\checkmark$、$\\leq$ 等),"
                "正文须改用 LaTeX 或文字表述")

    # ── 规则 3b:自测/检验答案区的占位/空答案(W,不阻断;每区各查一次)──
    for hs, he in ans_ranges:
        answered = False
        for i in range(hs + 1, he):
            if fence[i]:
                continue
            body = re.sub(r"^\s*(?:\d+[.、)]|[-*])\s*", "", lines[i].strip())
            compact = ANSWER_PUNCT_RE.sub("", body)
            if not compact:
                continue
            answered = True
            if len(compact) <= 20 and PLACEHOLDER_RE.match(compact):
                add("W", "W-SELFTEST-EMPTY", i,
                    "答案区只有占位词——短答案可以,但「略/见教材/同上」学员对不了答案;"
                    "须给可核对的短答案或指向讲义 ③")
        if not answered and not has_code_block(lines, hs + 1, he):
            add("W", "W-SELFTEST-EMPTY", hs,
                "答案区为空——学员做完无处核对;至少给一行可核对的短答案或指向讲义 ③")

    # ── 规则 4:答案框体例(学科中立)──
    def in_legacy(idx):
        """落在旧编号单元内(该单元只报 E-MARKER-LEGACY,不再叠加框体例错误)。"""
        return any(u["start"] <= idx < u["end"] for u in legacy_units)

    for b in boxes:
        if in_ext(b["marker_line"]) or in_legacy(b["marker_line"]):
            continue
        if not b["exists"]:
            add("E", "E-BOX-INCOMPLETE", b["marker_line"],
                "③标记行后无答案框(> 引用块)——框须紧邻标记行(只允许空行),"
                "教材原题等其他引用前移;框内直接从交付起笔写解题过程")
            continue
        mm = MARKER_CONTENT_RE.match(lines[b["marker_line"]].strip())
        if mm and ANSWER_PUNCT_RE.sub("", mm.group(1).strip("*_ ")):
            add("W", "W-MARKER-CONTENT", b["marker_line"],
                "③答案标记行带了答案内容——标记行只写「③ 答案:」,答案写进紧随的 > 框;"
                "两处并存容易与框内内容不一致")
        paras = b["paras"]
        code_rows = set()
        for p in paras:
            if p["code"]:
                code_rows |= set(p["rows"])
        text_rows = [r for r in sorted(b["rows"]) if r not in code_rows]
        # 框内四类体例违规各自定位到首个违规框行,便于直接修;围栏代码块内不查
        for r in text_rows:
            body = LEAD_RE.sub("", lead_text(vis[r]), count=1).lstrip(CIRCLED + " \t")
            if any(c in body for c in CIRCLED):
                add("E", "E-BOX-FORMAT", r,
                    "答案框内出现句中分点编号——给分点须各占一段、以 ① 起头"
                    "(段首编号合法),推导类改为连续解答")
                break
        arrow = [r for r in text_rows if ("→" in vis[r] or "⇒" in vis[r])]
        if arrow:
            add("E", "E-BOX-FORMAT", arrow[0],
                "答案框内出现箭头(→/⇒)——须改用文字或 LaTeX($\\rightarrow$/$\\Rightarrow$)")
        check = [r for r in text_rows if any(c in vis[r] for c in "✓✔✅")]
        if check:
            add("E", "E-BOX-FORMAT", check[0],
                "答案框内出现验算/核对标记(✓/√)——验算归「②解析」,框内只留成品答案")
        for r in text_rows:
            if BOX_ANNOT_RE.match(lines[r]):
                add("E", "E-BOX-FORMAT", r,
                    "答案框内出现讲解性批注行——批注归「②解析」,框内只留成品答案")
        starts = [p["rows"][0] for p in paras if not p["code"]]
        if not (any(LEAD_RE.match(lead_text(vis[r])) for r in starts)
                or any(p["code"] for p in paras)):
            add("E", "E-BOX-INCOMPLETE", b["marker_line"],
                "答案框缺交付起笔——须有一段以交付标识起笔(解:/答:/证明:/参考答案:/"
                "参考概括:/参考译文:/范文:/代码:/输出:/Answer:/Solution: 等),或直接给出代码块;"
                "题目归 ①题目,框内不重复题面")
        # 空答案 / 占位答案:结构合规但不可复现(「代码:」后接代码块属合法留空)
        has_code = any(p["code"] for p in paras)
        for r in starts:
            lm = LEAD_RE.match(lead_text(vis[r]))
            if not lm:
                continue
            compact = ANSWER_PUNCT_RE.sub("", answer_body(lines[r]))
            if not compact:
                if has_code and re.match(r"(?:代码|脚本|Code|Script)\s*[：:]", lm.group(0), re.I):
                    continue
                add("E", "E-BOX-EMPTY", r,
                    "答案框内的答案为空——须给可复现的完整内容")
                break
            if len(compact) <= 20 and PLACEHOLDER_RE.match(compact):
                add("E", "E-BOX-EMPTY", r,
                    "答案框内只有占位答案——「略/见教材/同上/自行体会」不算答案,"
                    "须给可复现的完整内容")
                break
        # 分段:一段一个可独立核对的最小单元,段数不设下限(单步答案一段即可);段内多行按其后果分级
        for p in paras:
            if p["code"]:
                continue
            if len(p["rows"]) > 1:
                if breaks_inline(lines, p["rows"]):
                    add("E", "E-BOX-WRAP", p["rows"][1],
                        "答案框段内断行拆断了行内公式或代码——同一段里的多行会被渲染成"
                        "一行,`$…$` / `…` 被换行截断会直接破坏渲染;把该句合并成一行")
                # 普通文字多行不再提示(降噪);是否按最小单元分段归「讲解出厂自检」人工核对

    # ── 规则 5:给分点量表(框外;只校验声明与合计,两项齐全才判)──
    for i, ln in enumerate(lines):
        if fence[i] or not RUBRIC_RE.search(ln) or in_ext(i):
            continue
        head = ln.split("合计")[0]
        scores = [float(x) for x in SCORE_RE.findall(head)]
        total_m = TOTAL_RE.search(ln)
        if not total_m and len(scores) < 2:
            continue          # 只是提到「给分点量表」的指针行,不是量表体
        if total_m and len(scores) >= 2:
            total = float(total_m.group(1))
            if abs(sum(scores) - total) > 0.01:
                add("E", "E-RUBRIC-SUM", i,
                    "给分点量表分值不相加:各点合计 " + "{:g}".format(sum(scores)) +
                    " 分,声明合计 " + "{:g}".format(total) +
                    " 分——改各点分值或改合计,二者须一致")
        if not RUBRIC_SOURCE_RE.search(ln):
            add("W", "W-RUBRIC-SOURCE", i,
                "给分点量表未标性质——无官方细则写「训练量表,非官方细则」,"
                "有官方来源写「官方细则」并附名称/年份")

    # ── 规则 6:分层标注缺失(概念单元正文 + 规划区对应行)──
    plan_hits = {}
    for i in range(doc["plan_end"]):
        m = PLAN_TABLE_RE.match(lines[i])
        if m:
            plan_hits.setdefault(int(m.group(1)), []).append(i)
            continue
        m = PLAN_ROW_RE.match(lines[i])
        if m:
            plan_hits.setdefault(int(m.group(1)), []).append(i)
    for u in doc["units"]:
        if in_ext(u["start"]):
            continue
        body = "\n".join(lines[u["start"]:u["end"]])
        body_tagged = bool(TIER_TAG_RE.search(body))
        plan_tagged = any(any(w in lines[i] for w in TIER_WORDS)
                          for i in plan_hits.get(u["num"], []))
        if not (body_tagged or plan_tagged):
            add("W", "W-NO-TIER", u["start"],
                "概念 " + str(u["num"]) + " 缺分层标注——正文用【本节最小必需】/"
                "【选学·后期必用(何时用/依赖哪节)】/【参照】(只须知其存在);"
                "规划区对应行可写纯文本")

    # ── 规则 7:头部疑似重复规则块(体例/排版/约定/格式 泛化)──
    has_pointer = any(POINTER_OK_RE.search(lines[i]) for i in range(doc["header_end"]))
    for i in range(doc["header_end"]):
        m = POINTER_BLOCK_RE.search(lines[i])
        if not m or POINTER_OK_RE.search(lines[i]):
            continue                        # 指针行本身合规,不报
        add("W", "W-STYLE-POINTER", i,
            "头部出现整段「" + m.group(0).rstrip("（(") + "…」规则块——疑似重复规则"
            "(指针行" + ("已同时存在,仍应删除规则块正文" if has_pointer else "缺失") +
            ");应压为一行「体例约定(LaTeX 排版/答案框):统一见 progress.md『质量保障机制』」")

    # ── 规则 8:定稿缺节首导读三行(草稿不查)──
    if doc["is_final"] and doc["units"]:
        head_text = "\n".join(lines[:doc["header_end"]])
        lack = [w for w in BRIEF_WORDS if w not in head_text]
        if lack:
            add("E", "E-HEADER-BRIEF", 0,
                "定稿缺节首导读:" + "、".join(lack) +
                "——第一个概念单元之前补三行「- 本节目标:……」「- 前置:……(无则写「无」)」"
                "「- 预计:约 N 分钟」,学员隔周回看据此判断学什么、要不要补前置、多久")

    # ── 规则 9:题面区后面没有答案区 → 答案无处可查(W;逐区判断)──
    q = [i for i, ln in enumerate(lines) if is_selftest_q(ln)]
    for qi in q:
        q_end = next((j for j, ln in enumerate(lines) if j > qi and H2_RE.match(ln)),
                     len(lines))
        # 该区算「有答案」:其后出现同词干答案区,或任一通用答案区
        if any(st > qi and answer_covers(lines[qi], lines[st]) for st, _ in ans_ranges):
            continue
        if any(SELFTEST_OPEN_RE.match(lines[i]) for i in range(qi, q_end)):
            continue
        add("W", "W-SELFTEST-MISSING", qi,
            "有自测/检验题面区但后面没有答案区——学员做完无处对答案;"
            "在该区之后补「## 本节自测答案」(或「## 检验问题答案」「## 参考答案」,"
            "短答案合法,占位词会被 W-SELFTEST-EMPTY 拦);确属开放/口头/练手检验"
            "则在该区首行写「- 检验说明:开放题,无标准答案」申请豁免")

    # ── 规则 10:图引用死链(需要讲义所在目录;外部地址不查)──
    if base_dir is not None:
        for i, ln in enumerate(lines):
            if fence[i]:
                continue
            # 用可见正文匹配:行内 code span / $…$ 中引述的写法示例不算图引用
            for m in list(IMG_LABEL_RE.finditer(vis[i])) + list(IMG_MD_RE.finditer(vis[i])):
                ref = m.group(1).strip().strip("<>").split("#")[0]
                if not ref or re.match(r"(?:https?:|data:|mailto:)", ref, re.I):
                    continue
                target = (Path(base_dir) / ref) if not Path(ref).is_absolute() else Path(ref)
                if not target.exists():
                    add("E", "E-IMG-DEADLINK", i,
                        "图引用死链:" + ref + " 不存在——图须先落盘后引用(相对讲义所在目录解析),"
                        "先写 SVG 再引用,或删掉该行改文字描述")

    # ── 规则 11:读者版 P1 可读性(W;仅 --reader 显式启用,不回溯旧讲义)──
    # 只对像讲义的文本生效(有概念单元或读者版导航块),避免把冷读记录/台账当讲义报噪声
    if reader and (doc["units"] or "## 本节速览" in lines or "## 回看索引" in lines):
        reader_checks(lines, doc, vis, fence, base_dir, box_rows, add)

    findings.sort(key=lambda f: (f[2], f[3], f[1], f[4]))
    return findings


def report(findings):
    """打印逐条结果与摘要行,返回退出码(0=无 E,1=有 E)。"""
    for level, code, rel, lineno, msg in findings:
        print("[{}] {} {}:{} {}".format(level, code, rel, lineno, msg))
    if findings:
        e_count = sum(1 for f in findings if f[0] == "E")
        w_count = len(findings) - e_count
        print("共 {} 项:E {} 项,W {} 项".format(len(findings), e_count, w_count))
        return 1 if e_count else 0
    print("通过:无违规项(结构通过;内容准确性、来源可信度与教学体验未校验,须人工/领域复核)")
    return 0


def main(argv=None):
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        prog="verify_explanation.py",
        description="讲义静态结构校验(只读、幂等;规则明细见脚本 docstring 契约)")
    ap.add_argument("path", nargs="?", default=None,
                    help="材料目录(递归取 *.md,忽略 assets/ 与非 .md)或单个 .md 文件")
    ap.add_argument("--selftest", action="store_true",
                    help="运行内嵌样例自检(临时目录,不写盘被校验目录)")
    ap.add_argument("--reader", action="store_true",
                    help="读者版 P1 可读性检查(W 级、不阻断;仅显式启用,旧讲义不回溯)")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.path:
        ap.print_usage()
        return 2
    p = Path(args.path)
    if p.is_dir():
        files = sorted(f for f in p.rglob("*.md")
                       if f.is_file() and "assets" not in f.parts)
        if not files:
            print("[learn-task-workflow] 目录下未找到 .md 材料:" + str(p),
                  file=sys.stderr)
            return 2
    elif p.is_file():
        files = [p]
    else:
        print("[learn-task-workflow] 路径不存在或不可访问:" + str(p), file=sys.stderr)
        return 2
    findings = []
    for f in files:
        rel = f.relative_to(p).as_posix() if p.is_dir() else f.name
        try:
            text = f.read_text(encoding="utf-8-sig")
        except OSError as exc:
            # 单个文件不可读不阻断其余文件,降级为 stderr 提示
            print("[learn-task-workflow] 跳过不可读文件 " + str(f) + ":" + str(exc),
                  file=sys.stderr)
            continue
        findings.extend(check_text(text, rel, base_dir=f.parent, reader=args.reader))
    return report(findings)


# ═══════════════════ selftest 内嵌样例(运行于临时目录,不写盘被校验目录) ═══════════════════

_HEAD = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
"""


def _unit(box, goal="一。", parse="二，得三。", err="四。", summary="三步法。"):
    """拼一个五要素齐的单元:①题目 → ②解析 → ③答案(框) → ④易错 → ⑤小结。"""
    return ("- ① 题目:" + goal + "\n"
            "- ② 解析:" + parse + "\n"
            "- ③ 答案:\n\n"
            + box +
            "\n- ④ 易错:" + err + "\n"
            "- ⑤ 小结:" + summary + "\n")


# 合规定稿:指针行 + 导读三行 + 规划分层 + 五要素齐 + 两段干净框 + 各豁免区
FIX_OK = """# 第 1 节 · 示例
- 状态:定稿(节闸口通过)
- 体例约定（LaTeX 排版/答案框）:统一见 progress.md『质量保障机制』
- 本节目标:能独立解一元一次方程并代回验算。
- 前置:会移项与合并同类项(无则写「无」)。
- 预计:约 20 分钟。
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
正文含公式 $x \\rightarrow 2$ 与代码 `→ √ ≤`,均为合法载体;公式 $$a^2+b^2=c^2$$ 亦合规。
> 这是普通引用块:→ ✓ √ 均豁免。

""" + _unit("> 解:由 $x^2-4=0$ 得 $x=\\pm 2$。\n>\n> ∴ 原方程有两个实根。\n") + """
## 本节自测答案
1. $x=2$,答案行含 → 与 √ 属合法区
"""

# 定稿 + 概念末记账状态行 → E-LEDGER-RESIDUE(定稿另缺导读,此处只查记账)
FIX_LEDGER = _HEAD.replace("- 状态:草稿(进行中)", "- 状态:定稿(闸口通过)") + _unit(
    "> 解:$x^2-1=(x+1)(x-1)$。\n") + """
- **状态(2026-10-10):已通过**——全对,概念 1 关闭。
"""

# 同文改草稿 → 不查记账
FIX_LEDGER_DRAFT = FIX_LEDGER.replace("- 状态:定稿(闸口通过)", "- 状态:草稿(讲授中)")

# 两个概念单元,概念 1 缺④、概念 2 齐 → 单元级计数,只报概念 1
FIX_UNITS = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(2):
  1. 甲 【本节最小必需】
  2. 乙 【本节最小必需】

## 概念 1 · 甲
- ① 题目:一。
- ② 解析:二，得三。
- ③ 答案:

> 解:一步。

- ⑤ 小结:三步法。

## 概念 2 · 乙
""" + _unit("> 解:一步。\n")

# 概念缺③标记 → E-REQ-MISSING 且消息指向「③ 答案」
FIX_NO_THIRD = _HEAD + """- ① 题目:一。
- ② 解析:二，得三。
- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 正文裸违规字符 → W-UNICODE-CHAR
FIX_UNICODE = _HEAD + "正文裸箭头 → 与对勾 ✓ 属违规。\n" + _unit("> 解:一步。\n")

# 排除范围不误报:围栏 / code span / 公式 / 引用块 / 自测区
FIX_UNICODE_EXEMPT = _HEAD + """围栏内合法:
```
→ ✓ √ ≤ ≥ ∪ ⇔
```
行内 code `→ ✓ √` 与公式 $a \\leq b$、`√` 字面均豁免。
> 普通引用块豁免:→ ✓ √。

""" + _unit("> 解:一步。\n") + """
## 本节自测答案
1. → √ ≤ 答案行合法
"""

# 框内四类体例违规:句中分点 / 箭头 / 验算标记 / 批注行(各计一条 E-BOX-FORMAT)
FIX_BOX_BAD = _HEAD + _unit(
    "> 解:先移项 → 再配方;① 设 $x$,② 求根;\n>\n> 验算:$x=2$ ✓;\n>\n> (注:这里容易错。)\n")

# ③标记行后无框体 → E-BOX-INCOMPLETE
FIX_BOX_MISSING = _HEAD + """- ① 题目:一。
- ② 解析:二，得三。
- ③ 答案:

这一行不是引用块,框体缺失。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# ③ 与引用块之间插普通文字 → 框不成立
FIX_BOX_GAP = _HEAD + """- ① 题目:一。
- ② 解析:二，得三。
- ③ 答案:

教材原题如下(非答案框):

> 教材原题：解方程 $x^2-4=0$。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 规划行与概念内均无分层标注 → W-NO-TIER(纯 W,退出码 0)
FIX_TIER = (_HEAD.replace(" 【本节最小必需】", "")) + _unit("> 解:一步。\n")

# 正文出现「选学」二字但无【】标签 → W-NO-TIER(关键词不算分层标注)
FIX_TIER_LOOSE = (_HEAD.replace(" 【本节最小必需】", "")
                  ).replace("## 概念 1 · 甲\n", "## 概念 1 · 甲\n本节选学内容后面再讲。\n"
                            ) + _unit("> 解:一步。\n")

# 头部两个旧规则块 → 2 条 W-STYLE-POINTER
FIX_POINTER = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 数学排版约定(2026-10-17 学员要求):公式一律用 LaTeX
- 答案体例(2026-10-17 学员反馈后确立):只放连续解答
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
""" + _unit("> 解:一步。\n")

# 化学/代码规则块同样属「整段规则块」
FIX_POINTER_MORE = FIX_POINTER.replace(
    "- 数学排版约定(2026-10-17 学员要求):公式一律用 LaTeX",
    "- 化学方程式排版约定(2026-10-17):系数、条件与状态写全").replace(
    "- 答案体例(2026-10-17 学员反馈后确立):只放连续解答",
    "- 代码体例(2026-10-17):围栏块 + 输出")

# 「## 概念地图」不是概念单元;表格行承载分层标注 → 单元级零误报
FIX_MAP = """# 第 1 节 · 示例
- 状态:草稿(进行中)

## 概念地图
| 单元 | 内容 | 分层 |
|---|---|---|
| 概念 1 | 甲 | 本节最小必需 |

## 概念 1 · 甲
""" + _unit("> 解:一步。\n")

# 记账行内的违规字符不重复报(只报 E-LEDGER-RESIDUE)
FIX_LEDGER_MIX = """# 第 1 节 · 示例
- 状态:定稿(通过)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
""" + _unit("> 解:一步。\n") + """
- **状态(2026-10-10):已通过**——全对 → 关闭。
"""

# 纯概念显式豁免:标「③ 不适用(纯概念)」,②③ 一并豁免,①④⑤ 齐 → 零 E
FIX_THIRD_EXEMPT = _HEAD + """- ① 题目:认识 $\\pm$ 记号的读法。
- ④ 易错:把 $\\pm$ 读成「两个符号」而非「两次取值」。
- ⑤ 小结:$\\pm$ 是一口气算两次。
- ③ 不适用（纯概念）:本节只讲记号语义,无可复现产物。
"""

# 豁免被滥用:标了「③ 不适用」却仍有「> 解:」起笔
FIX_THIRD_EXEMPT_BAD = FIX_THIRD_EXEMPT + """
> 解:$x=2$。
"""

# ③答案 与 ③不适用 并存 → E-THIRD-CONFLICT
FIX_THIRD_CONFLICT = _HEAD + """- ① 题目:一。
- ④ 易错:四。
- ⑤ 小结:三步法。
- ③ 答案:

> 解:一步。

- ③ 不适用（纯概念）:补充说明。
"""

# 纯概念豁免 + 正文行首「答:」属普通问答表述,不得误判为解答起笔 → 零 E
FIX_THIRD_EXEMPT_ANS = _HEAD + """- ① 题目:认识术语。
- ④ 易错:混淆近义词。
- ⑤ 小结:一句话记术语。
- ③ 不适用（纯概念）:只讲术语语义。
答:这个术语指一组可复现的操作。
"""

# 纯记忆/已会·检索版:同一豁免结构,文档标签必须被接受
FIX_THIRD_MEMORY = _HEAD + """- ① 题目:记住三个条约年份。
- ④ 易错:年份张冠李戴。
- ⑤ 小结:时间线 + 关键词。
- ③ 不适用（纯记忆）:只做线索卡,无可复现产物。
"""

FIX_THIRD_L3 = _HEAD + """- ① 题目:独立完成检索题。
- ④ 易错:把旧条件套到新情境。
- ⑤ 小结:先判别再执行。
- ③ 不适用（已会·检索版）:已会单元只检索,不再给完整示例。
"""

# 头部指针行改用半角括号 → 同样合规
FIX_OK_HALF = FIX_OK.replace("体例约定（LaTeX 排版/答案框）", "体例约定(LaTeX 排版/答案框)")

# 正文提及「见 ③ 答案」不得被当成标记行(行首限定)
FIX_MARKER_MENTION = _HEAD + """- ① 题目:一。
- ② 解析:关键步骤见 ③ 答案。
- ③ 答案:

> 解:一步。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 框内以题号起笔(多题单元卷面)同样算交付起笔
FIX_QNUM_BOX = _HEAD + """- ① 题目:一。
- ② 解析:二，得三。
- ③ 答案:

> (1) 答:B。
>
> (2) 解:由 $a_n=a_1+(n-1)d$ 代入得 $a_n=2n-9$。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 卡片式布局:检验写成列表行、③ 详解在单元内(不设 ## 检验 标题)
FIX_CARD = """# 第 1 节 · 示例
- 状态:草稿(进行中)

## 概念 1 · 甲 【本节最小必需】
- ① 题目:本卡题型与分值。
- ② 解析:第一步、第二步。
- ④ 易错:四。
- ⑤ 小结:三步法。
- 检验:①已知 $a_1=-7$、$d=2$,求 $a_n$。②已知 $a_1=2$、$q=3$,求 $a_5$。
- ③ 答案(第 1 题):

> 解:由 $a_n=a_1+(n-1)d$ 代入,得 $a_n=2n-9$。

- ③ 答案(第 2 题):

> 解:由 $a_n=a_1q^{n-1}$ 代入,得 $a_5=162$。
"""

# 有序列表写标记(1. ① 题目)同样识别
FIX_NUMBERED = """# 第 1 节 · 示例
- 状态:草稿(进行中)

## 概念 1 · 甲 【本节最小必需】
1. ① 题目:一。
2. ② 解析:二，得三。
3. ③ 答案:

> 解:一步。

4. ④ 易错:四。
5. ⑤ 小结:三步法。
"""

# ③ 标记行带答案内容 → W-MARKER-CONTENT(与框内答案并存)
FIX_MARKER_CONTENT = _HEAD + """- ① 题目:一。
- ② 解析:二，得三。
- ③ 答案:三。

> 解:一步。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""


# ── 答案框分段:一段一个可独立核对的最小单元,段数不设下限 ──
_BOX_SEG = _HEAD + """- ① 题目:一。
- ② 解析:二，得三。
- ③ 答案:

"""

# 单段多行:不再由脚本提示(降噪),由出厂自检人工核对 → 零 findings
FIX_BOX_ONELINE = _BOX_SEG + """> 解:第一步。
> 第二步。
> 第三步。
> ∴ 结论。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 段内断行:2 段、第 1 段 3 行 → 同样不再提示(仅拆断公式才报 E)
FIX_BOX_LONGSEG = _BOX_SEG + """> 解:第一步。
> 第二步。
> 第三步。
>
> ∴ 结论。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 分段合规:2 段各 1 行 → 0 条
FIX_BOX_OKSEG = _BOX_SEG + """> 解:第一步。
>
> ∴ 结论。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 单步答案只占一段 → 合规(段数不设下限)
FIX_BOX_ONE = _BOX_SEG + """> 答:B。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 段内断行拆断了行内公式(该行 $ 未闭合)→ E-BOX-WRAP(渲染直接损坏)
FIX_BOX_BROKENMATH = _BOX_SEG + """> 解:先算 $x=
> 2$ 再代入。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 旧编号残留:①目标 / ⑤标准答案 → 只报 1 条 E-MARKER-LEGACY,不叠加缺项与框体例
FIX_LEGACY = _HEAD + """- ① 目标:一。
- ② 分步:二。
- ③ 答案:三。
- ④ 易错:四。
- ⑤ 标准答案:

> 题目:一题。
>
> 解:一步。
"""

# 扩展(选读)区:区内单元缺五要素/无分层/框未分段,全部豁免
FIX_EXT_IN = _BOX_SEG + """> 解:一步。

- ④ 易错:四。
- ⑤ 小结:三步法。

## 扩展（选读）
## 概念 2 · 乙
补充内容,无五要素、无分层标注。
- ① 题目:只有一个题目行。
- ③ 答案:

> 解:一步。
> 解:两步。
"""

# 同内容但不在扩展区 → 五要素/分层/分段三项照常报
FIX_EXT_OUT = _BOX_SEG + """> 解:一步。

- ④ 易错:四。
- ⑤ 小结:三步法。

## 概念 2 · 乙
补充内容,无五要素、无分层标注。
- ① 题目:只有一个题目行。
- ③ 答案:

> 解:一步。
> 解:两步。
"""


# ── 跨学科答案框体例:交付标识与学科无关,段首分点合法,代码块整块一段 ──

# 文科按点给分:每点一段、段首 ①–⑩ 是给分点,合法
FIX_BOX_HUMAN = _BOX_SEG + """> 答:①资本:殖民扩张与海外贸易积累了大量资本。
>
> ②劳动力:圈地运动为工厂提供自由劳动力。
>
> ③市场:海外殖民地扩大了商品需求。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 编程:代码块整块算一段,块内多行不判段内断行
FIX_BOX_CODE = _BOX_SEG + """> 代码:

> ```python
> import os
> for name in os.listdir('.'):
>     if name.endswith('.txt'):
>         os.rename(name, 'out_' + name)
> ```
>
> 输出:目录内 .txt 文件均带 out_ 前缀,无报错即成功。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 英语:交付标识用英文,同样合规
FIX_BOX_EN = _BOX_SEG + """> Model answer: He runs very fast.

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 精读笔记式:参考概括起交付、原文定位收尾
FIX_BOX_READING = _BOX_SEG + """> 参考概括：作者主张中国乡土社会是「熟悉社会」，以人情与礼俗维持秩序，而非契约。
>
> 原文定位：第一章第 2 段，第 3–7 句。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 设计类:方案/设计说明起交付,多解+评价标准
FIX_BOX_DESIGN = _BOX_SEG + """> 方案：先满足约束 A；再在 B/C 之间取舍。
>
> 评价标准：约束覆盖、取舍理由、可行性。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

FIX_BOX_DESIGN2 = _BOX_SEG + """> 设计说明：目标、约束、备选、取舍。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 给分点挤在一句里(句中编号)→ E-BOX-FORMAT
FIX_BOX_MIDPOINT = _BOX_SEG + """> 答:①先设未知数②再列方程。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 无交付起笔(整段是叙述)→ E-BOX-INCOMPLETE
FIX_BOX_NOLEAD = _BOX_SEG + """> 我们把两式相减得 $x=2$。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 答案为空(只有起笔)→ E-BOX-EMPTY
FIX_BOX_EMPTY = _BOX_SEG + """> 解:

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 占位答案(略)→ E-BOX-EMPTY
FIX_BOX_PLACEHOLDER = _BOX_SEG + """> 解:略。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 「代码:」后接代码块属合法留空,不得误报 E-BOX-EMPTY
FIX_BOX_CODELABEL = _BOX_SEG + """> 代码:
>
> ```python
> import os
> print(os.listdir('.'))
> ```

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 给分点量表(框外)合计正确且标了性质 → 零违规
FIX_RUBRIC_OK = _BOX_SEG + """> 解:$x^2-4=0$,∴ $x=\\pm 2$;代回均成立。

- ④ 易错:四。
- ⑤ 小结:三步法。
- 给分点量表：①移项（2分）；②求根（3分）；合计 5 分（训练量表，非官方细则）
"""

# 量表各点之和 5 分 ≠ 声明合计 6 分 → E-RUBRIC-SUM
FIX_RUBRIC_BAD = FIX_RUBRIC_OK.replace("合计 5 分", "合计 6 分")

# 量表未标性质 → W-RUBRIC-SOURCE
FIX_RUBRIC_NOSRC = FIX_RUBRIC_OK.replace("（训练量表，非官方细则）", "")

# 自测答案只有占位词 → W-SELFTEST-EMPTY(不阻断)
FIX_SELFTEST_PLACEHOLDER = FIX_RUBRIC_OK + """
## 本节自测答案
1. 略
"""

# 自测答案区只有标题、没有任何答案行 → W-SELFTEST-EMPTY
FIX_SELFTEST_BLANK = FIX_RUBRIC_OK + """
## 本节自测答案

"""

# √ 在答案里多是根号(x=√2),不得按验算标记判 E-BOX-FORMAT
FIX_BOX_SQRT = _BOX_SEG + """> 解:x=√2。

- ④ 易错:四。
- ⑤ 小结:三步法。
"""

# 参照级单元:标【参照】+「③ 不适用(参照级)」,只需①题目 → 零 E、零 W-NO-TIER
FIX_TIER_REF = """# 第 1 节 · 示例
- 状态:草稿(进行中)
- 节内概念单元规划(1):
  1. 乙 【参照】

## 概念 1 · 乙 【参照】
- ① 题目:这个术语指什么、什么时候用不上。
- ③ 不适用（参照级）:只作参照,不要求作答,定义与边界见正文。
"""

# 定稿缺节首导读三行 → E-HEADER-BRIEF
FIX_NO_BRIEF = """# 第 1 节 · 示例
- 状态:定稿(闸口通过)
- 节内概念单元规划(1):
  1. 甲 【本节最小必需】

## 概念 1 · 甲
""" + _unit("> 解:一步。\n")

# 有「## 本节自测」题面区、无「## 本节自测答案」→ W-SELFTEST-MISSING
FIX_SELFTEST_NOANS = FIX_BOX_OKSEG + """
## 本节自测
1. 一题?
2. 二题?
"""

# 标题别名:自测写在「## 检验问题」下且无答案区 → 同样报 W-SELFTEST-MISSING
FIX_SELFTEST_ALT = FIX_BOX_OKSEG + """
## 检验问题
1. 这块的主张是什么?
"""

# 标题别名配对:「## 检验问题」+「## 检验问题答案」→ 不报 MISSING/EMPTY
FIX_SELFTEST_ALT_OK = FIX_SELFTEST_ALT + """
## 检验问题答案
1. 主张是「乡土社会是熟悉社会」。
"""

# 开放检验显式豁免:该区首行写「- 检验说明:」→ 不报 MISSING
FIX_SELFTEST_OPEN = FIX_BOX_OKSEG + """
## 检验
- 检验说明:开放题,无标准答案(说出即算)
1. 用自己的话复述这块。
"""

# 反例:「## 检验方法」是化学正文节,不是自测题面区 → 零违规
FIX_SELFTEST_METHOD = FIX_BOX_OKSEG + """
## 检验方法
向溶液中滴加 BaCl2 溶液,生成白色沉淀。
"""

# 别名:「## 自测题」+ 通用答案区「## 参考答案」→ 不报 MISSING
FIX_SELFTEST_ALIAS_OK = FIX_BOX_OKSEG + """
## 自测题
1. 一题?

## 参考答案
1. 答案一。
"""

# 别名:「## 检验题」+「## 答案与解析」→ 不报 MISSING
FIX_SELFTEST_ALIAS2_OK = FIX_BOX_OKSEG + """
## 检验题
1. 一题?

## 答案与解析
1. 答案一。
"""

# 两个答案区各自检查:第二个为空 → 恰 1 条 W-SELFTEST-EMPTY,且不误报 MISSING
FIX_SELFTEST_TWO = FIX_BOX_OKSEG + """
## 检验问题
1. 一题?

## 检验问题答案
1. 答案一。

## 自测题
1. 二题?

## 本节自测答案
"""

# 动手练手类检验:写「- 检验说明:练手任务…」→ 不报 MISSING
FIX_SELFTEST_HANDSON = FIX_BOX_OKSEG + """
## 检验
- 检验说明:练手任务,按成功标志自评
1. 把脚本跑通。
"""

# 两个题面区共用文末一个通用答案区 → 都算有答案,不报 MISSING
FIX_SELFTEST_SHARED = FIX_BOX_OKSEG + """
## 自测
1. 一题?

## 检验问题
1. 二题?

## 参考答案
1. 答案一。
2. 答案二。
"""

# 同词干答案区只覆盖同名题面区 → 恰 1 条 MISSING
FIX_SELFTEST_SPECIFIC = FIX_BOX_OKSEG + """
## 自测
1. 一题?

## 检验问题
1. 二题?

## 检验问题答案
1. 答案二。
"""

# 编程类自测:答案区只有代码块,也算已作答(不得判空)
FIX_SELFTEST_CODE = FIX_BOX_OKSEG + """
## 本节自测
1. 打印当前目录。

## 本节自测答案
1.

```python
print(os.listdir('.'))
```
"""


def selftest():
    ok = True

    def chk(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print("[{}] {}".format("OK" if cond else "FAIL", name))

    def codes(findings, code):
        return [f for f in findings if f[1] == code]

    # ① 合规定稿:全规则通过
    chk("合规定稿零违规", check_text(FIX_OK, "ok.md") == [])

    # ② 定稿记账残留
    r = check_text(FIX_LEDGER, "ledger.md")
    ledger_line = FIX_LEDGER.splitlines().index(
        "- **状态(2026-10-10):已通过**——全对,概念 1 关闭。") + 1
    chk("定稿记账残留恰 1 条且行号正确",
        len(codes(r, "E-LEDGER-RESIDUE")) == 1
        and codes(r, "E-LEDGER-RESIDUE")[0][3] == ledger_line)

    # ③ 草稿不查记账
    chk("草稿不报记账残留",
        len(codes(check_text(FIX_LEDGER_DRAFT, "draft.md"), "E-LEDGER-RESIDUE")) == 0)

    # ④ 概念单元级计数:两概念其一缺④只报该单元
    r = check_text(FIX_UNITS, "units.md")
    req = codes(r, "E-REQ-MISSING")
    chk("单元级五要素:恰 1 条且只指向概念 1",
        len(req) == 1 and "概念 1" in req[0][4] and "④ 易错" in req[0][4])

    # ⑤ 概念缺③ → E-REQ-MISSING 且消息指向「③ 答案」
    r = check_text(FIX_NO_THIRD, "nothird.md")
    req = codes(r, "E-REQ-MISSING")
    chk("缺③报 E-REQ-MISSING 且消息含「③ 答案」",
        len(req) == 1 and "③ 答案" in req[0][4])

    # ⑥ 正文裸违规字符
    r = check_text(FIX_UNICODE, "uni.md")
    uni = codes(r, "W-UNICODE-CHAR")
    chk("正文违规字符报 W 且行号正确",
        len(uni) == 1 and "→" in uni[0][4] and "✓" in uni[0][4]
        and uni[0][3] == FIX_UNICODE.splitlines().index("正文裸箭头 → 与对勾 ✓ 属违规。") + 1)

    # ⑦ 排除范围不误报
    chk("围栏/code/公式/引用块/自测区零误报",
        len(codes(check_text(FIX_UNICODE_EXEMPT, "exempt.md"), "W-UNICODE-CHAR")) == 0)

    # ⑧ 框内四类体例违规各计一条
    r = check_text(FIX_BOX_BAD, "boxbad.md")
    chk("框内分点/箭头/验算/批注各 1 条 E-BOX-FORMAT",
        len(codes(r, "E-BOX-FORMAT")) == 4)

    # ⑨ ③标记行后无框体
    chk("③行后无框体报 E-BOX-INCOMPLETE",
        len(codes(check_text(FIX_BOX_MISSING, "nob.md"), "E-BOX-INCOMPLETE")) == 1)

    # ⑩ ③与框之间插内容 → 框不成立
    chk("③与引用块之间插内容报 E-BOX-INCOMPLETE",
        len(codes(check_text(FIX_BOX_GAP, "boxgap.md"), "E-BOX-INCOMPLETE")) == 1)

    # ⑪ 分层标注缺失:纯 W、退出码 0
    r = check_text(FIX_TIER, "tier.md")
    chk("分层缺失报 W-NO-TIER 且无 E",
        len(codes(r, "W-NO-TIER")) == 1 and not [f for f in r if f[0] == "E"])
    chk("正文关键词不算分层标注",
        len(codes(check_text(FIX_TIER_LOOSE, "tierloose.md"), "W-NO-TIER")) == 1)

    # ⑫ 头部规则块
    chk("头部规则块报 2 条 W-STYLE-POINTER",
        len(codes(check_text(FIX_POINTER, "ptr.md"), "W-STYLE-POINTER")) == 2)
    chk("化学/代码规则块同样报 2 条 W-STYLE-POINTER",
        len(codes(check_text(FIX_POINTER_MORE, "ptrmore.md"), "W-STYLE-POINTER")) == 2)
    chk("半角括号指针行不报 W-STYLE-POINTER",
        len(codes(check_text(FIX_OK_HALF, "okhalf.md"), "W-STYLE-POINTER")) == 0)

    # ⑬ 概念地图不生成单元;表格行分层生效
    r = check_text(FIX_MAP, "map.md")
    chk("概念地图不误判 + 表格行分层生效",
        len(codes(r, "E-REQ-MISSING")) == 0 and len(codes(r, "W-NO-TIER")) == 0)

    # ⑭ 记账行内违规字符不重复报
    r = check_text(FIX_LEDGER_MIX, "mix.md")
    chk("记账行不重复报 Unicode",
        len(codes(r, "E-LEDGER-RESIDUE")) == 1
        and len(codes(r, "W-UNICODE-CHAR")) == 0)

    # ⑮ 输出稳定排序
    mixed = check_text(FIX_UNICODE, "a.md") + check_text(FIX_BOX_BAD, "a.md")
    keys = [(f[2], f[3]) for f in mixed]
    chk("输出按 文件→行号 稳定排序", keys == sorted(keys))

    # ⑯ 纯概念③豁免:合法零 E / 滥用报错 / 并存报冲突 / 正文「答:」不误判
    r = check_text(FIX_THIRD_EXEMPT, "exempt3.md")
    chk("纯概念豁免③零 E", not [f for f in r if f[0] == "E"])
    r = check_text(FIX_THIRD_EXEMPT_BAD, "exemptbad.md")
    chk("豁免滥用报 E-THIRD-EXEMPT-MISUSE",
        len(codes(r, "E-THIRD-EXEMPT-MISUSE")) == 1)
    r = check_text(FIX_THIRD_CONFLICT, "conflict.md")
    chk("③答案与③不适用并存报 E-THIRD-CONFLICT",
        len(codes(r, "E-THIRD-CONFLICT")) == 1)
    r = check_text(FIX_THIRD_EXEMPT_ANS, "exemptans.md")
    chk("正文行首「答:」不误判为解答起笔", not [f for f in r if f[0] == "E"])
    r = check_text(FIX_THIRD_MEMORY, "memory.md")
    chk("纯记忆③豁免零 E", not [f for f in r if f[0] == "E"])
    r = check_text(FIX_THIRD_L3, "l3.md")
    chk("已会·检索版③豁免零 E", not [f for f in r if f[0] == "E"])

    # ⑰ 正文提及标记词不误判;标记行带内容报 W
    chk("正文提及「见 ③ 答案」不误判为标记行",
        check_text(FIX_MARKER_MENTION, "mention.md") == [])
    chk("有序列表写标记同样识别",
        check_text(FIX_NUMBERED, "numbered.md") == [])
    chk("框内题号起笔不误判缺交付起笔",
        check_text(FIX_QNUM_BOX, "qnum.md") == [])
    chk("卡片式布局(检验列表行+多③框)零违规",
        check_text(FIX_CARD, "card.md") == [])
    r = check_text(FIX_MARKER_CONTENT, "marker.md")
    chk("③标记行带答案内容报 W-MARKER-CONTENT 且无 E",
        len(codes(r, "W-MARKER-CONTENT")) == 1 and not [f for f in r if f[0] == "E"])

    # ⑱ 跨学科答案框
    chk("文科按点给分的答案框零违规", check_text(FIX_BOX_HUMAN, "human.md") == [])
    chk("编程代码块答案框零违规", check_text(FIX_BOX_CODE, "code.md") == [])
    chk("英语 Model answer 框零违规", check_text(FIX_BOX_EN, "en.md") == [])
    chk("精读框（参考概括/原文定位）零违规",
        check_text(FIX_BOX_READING, "reading.md") == [])
    chk("设计类「方案：」答案框零违规",
        check_text(FIX_BOX_DESIGN, "design.md") == [])
    chk("设计类「设计说明：」答案框零违规",
        check_text(FIX_BOX_DESIGN2, "design2.md") == [])
    chk("句中分点编号仍报 E-BOX-FORMAT",
        len(codes(check_text(FIX_BOX_MIDPOINT, "mid.md"), "E-BOX-FORMAT")) == 1)
    chk("缺交付起笔报 E-BOX-INCOMPLETE",
        len(codes(check_text(FIX_BOX_NOLEAD, "nolead.md"), "E-BOX-INCOMPLETE")) == 1)
    chk("空答案报 E-BOX-EMPTY",
        len(codes(check_text(FIX_BOX_EMPTY, "empty.md"), "E-BOX-EMPTY")) == 1)
    chk("占位答案报 E-BOX-EMPTY",
        len(codes(check_text(FIX_BOX_PLACEHOLDER, "placeholder.md"), "E-BOX-EMPTY")) == 1)
    chk("「代码:」后接代码块不误报 E-BOX-EMPTY",
        check_text(FIX_BOX_CODELABEL, "codelabel.md") == [])
    chk("√ 作根号不误报 E-BOX-FORMAT", check_text(FIX_BOX_SQRT, "sqrt.md") == [])

    # ⑲ 分段:按最小单元,段数不设下限
    r = check_text(FIX_BOX_ONELINE, "oneline.md")
    chk("单段多行不再提示(降噪,零 findings)", r == [])
    r = check_text(FIX_BOX_LONGSEG, "longseg.md")
    chk("多段中段内多行同样不再提示", r == [])
    chk("分段合规的框零 E-BOX-WRAP",
        len(codes(check_text(FIX_BOX_OKSEG, "okseg.md"), "E-BOX-WRAP")) == 0)
    chk("单步答案一段不被判未分段",
        check_text(FIX_BOX_ONE, "one.md") == [])
    chk("段内拆断公式报 E-BOX-WRAP",
        len(codes(check_text(FIX_BOX_BROKENMATH, "brokenmath.md"), "E-BOX-WRAP")) == 1)

    # ⑳ 旧编号:只报 1 条,不叠加
    r = check_text(FIX_LEGACY, "legacy.md")
    chk("旧编号只报 1 条 E-MARKER-LEGACY、不叠加缺项",
        len(codes(r, "E-MARKER-LEGACY")) == 1
        and len(codes(r, "E-REQ-MISSING")) == 0
        and len(codes(r, "E-BOX-INCOMPLETE")) == 0
        and len(r) == 1)

    # ㉑ 量表
    chk("给分点量表合计正确零违规", check_text(FIX_RUBRIC_OK, "rubric.md") == [])
    chk("量表合计不符报 E-RUBRIC-SUM",
        len(codes(check_text(FIX_RUBRIC_BAD, "rubricbad.md"), "E-RUBRIC-SUM")) == 1)
    r = check_text(FIX_RUBRIC_NOSRC, "rubricsrc.md")
    chk("量表未标性质报 W-RUBRIC-SOURCE 且无 E",
        len(codes(r, "W-RUBRIC-SOURCE")) == 1 and not [f for f in r if f[0] == "E"])

    # ㉒ 自测答案区
    r = check_text(FIX_SELFTEST_PLACEHOLDER, "stempty.md")
    chk("自测答案写「略」报 W-SELFTEST-EMPTY 且无 E",
        len(codes(r, "W-SELFTEST-EMPTY")) == 1 and not [f for f in r if f[0] == "E"])
    r = check_text(FIX_SELFTEST_BLANK, "stblank.md")
    chk("自测答案区为空报 W-SELFTEST-EMPTY 且无 E",
        len(codes(r, "W-SELFTEST-EMPTY")) == 1 and not [f for f in r if f[0] == "E"])
    r = check_text(FIX_SELFTEST_NOANS, "stnoans.md")
    chk("有自测无答案区报 W-SELFTEST-MISSING 且无 E",
        len(codes(r, "W-SELFTEST-MISSING")) == 1 and not [f for f in r if f[0] == "E"])
    r = check_text(FIX_SELFTEST_ALT, "stalt.md")
    chk("「## 检验问题」无答案区同样报 W-SELFTEST-MISSING",
        len(codes(r, "W-SELFTEST-MISSING")) == 1 and not [f for f in r if f[0] == "E"])
    r = check_text(FIX_SELFTEST_ALT_OK, "staltok.md")
    chk("「## 检验问题答案」配对后不报 MISSING/EMPTY",
        not codes(r, "W-SELFTEST-MISSING") and not codes(r, "W-SELFTEST-EMPTY")
        and not [f for f in r if f[0] == "E"])
    r = check_text(FIX_SELFTEST_OPEN, "stopen.md")
    chk("开放检验写「- 检验说明:」后不报 W-SELFTEST-MISSING",
        not codes(r, "W-SELFTEST-MISSING") and not [f for f in r if f[0] == "E"])
    chk("「## 检验方法」正文节不误判为自测题面区",
        check_text(FIX_SELFTEST_METHOD, "stmethod.md") == [])
    r = check_text(FIX_SELFTEST_ALIAS_OK, "stalias.md")
    chk("「## 自测题」+「## 参考答案」配对后不报 MISSING",
        not codes(r, "W-SELFTEST-MISSING") and not [f for f in r if f[0] == "E"])
    r = check_text(FIX_SELFTEST_ALIAS2_OK, "stalias2.md")
    chk("「## 检验题」+「## 答案与解析」配对后不报 MISSING",
        not codes(r, "W-SELFTEST-MISSING") and not [f for f in r if f[0] == "E"])
    r = check_text(FIX_SELFTEST_ALIAS2_OK.replace("答案与解析", "答案要点"), "stalias3.md")
    chk("「## 答案要点」也认作答案区",
        not codes(r, "W-SELFTEST-MISSING") and not [f for f in r if f[0] == "E"])
    r = check_text(FIX_SELFTEST_TWO, "sttwo.md")
    chk("多个答案区逐区检查:仅空区报 1 条 W-SELFTEST-EMPTY",
        len(codes(r, "W-SELFTEST-EMPTY")) == 1
        and not codes(r, "W-SELFTEST-MISSING")
        and not [f for f in r if f[0] == "E"])
    r = check_text(FIX_SELFTEST_HANDSON, "sthandson.md")
    chk("练手类检验写「- 检验说明:」后不报 W-SELFTEST-MISSING",
        not codes(r, "W-SELFTEST-MISSING") and not [f for f in r if f[0] == "E"])
    r = check_text(FIX_SELFTEST_SHARED, "stshared.md")
    chk("文末通用答案区统管多个题面区,不报 MISSING",
        not codes(r, "W-SELFTEST-MISSING") and not [f for f in r if f[0] == "E"])
    r = check_text(FIX_SELFTEST_SPECIFIC, "stspecific.md")
    chk("同词干答案区不兜底其他题面区:恰 1 条 W-SELFTEST-MISSING",
        len(codes(r, "W-SELFTEST-MISSING")) == 1 and not [f for f in r if f[0] == "E"])
    r = check_text(FIX_SELFTEST_CODE, "stcode.md")
    chk("答案区只有代码块时不误报 W-SELFTEST-EMPTY",
        not codes(r, "W-SELFTEST-EMPTY") and not [f for f in r if f[0] == "E"])

    # ㉓ 参照级 / 导读 / 扩展区
    r = check_text(FIX_TIER_REF, "tierref.md")
    chk("参照级【参照】+③不适用(参照级)零 E、零 W-NO-TIER",
        not [f for f in r if f[0] == "E"] and len(codes(r, "W-NO-TIER")) == 0)
    chk("定稿缺节首导读报 E-HEADER-BRIEF",
        len(codes(check_text(FIX_NO_BRIEF, "nobrief.md"), "E-HEADER-BRIEF")) == 1)
    r = check_text(FIX_EXT_IN, "extin.md")
    chk("扩展区内豁免五要素/分层/框体例",
        not [f for f in r
             if f[1] in ("E-REQ-MISSING", "W-NO-TIER", "E-BOX-WRAP")])
    r = check_text(FIX_EXT_OUT, "extout.md")
    chk("扩展区外同内容照常报错",
        len(codes(r, "E-REQ-MISSING")) == 1
        and len(codes(r, "W-NO-TIER")) == 1)

    # ㉔ 退出码:0=无 E / 1=有 E / 2=用法或路径错误
    with tempfile.TemporaryDirectory() as td:
        d0 = Path(td) / "ok"
        d0.mkdir()
        (d0 / "a.md").write_text(FIX_OK, encoding="utf-8")
        d1 = Path(td) / "bad"
        d1.mkdir()
        (d1 / "a.md").write_text(FIX_LEDGER, encoding="utf-8")
        chk("退出码 0(无 E)", main([str(d0)]) == 0)
        chk("退出码 1(有 E)", main([str(d1)]) == 1)
        chk("退出码 2(路径不存在)", main([str(Path(td) / "不存在")]) == 2)
        chk("退出码 2(缺参数)", main([]) == 2)
        d2 = Path(td) / "img"
        (d2 / "assets").mkdir(parents=True)
        (d2 / "assets" / "ok.svg").write_text("<svg/>", encoding="utf-8")
        md_ok = FIX_BOX_OKSEG + "图：assets/ok.svg（示意）\n"
        md_dead = FIX_BOX_OKSEG + "![](assets/missing.svg)\n"
        chk("图存在时不报死链",
            len(codes(check_text(md_ok, "ok.md", base_dir=d2), "E-IMG-DEADLINK")) == 0)
        chk("图缺失报 E-IMG-DEADLINK",
            len(codes(check_text(md_dead, "dead.md", base_dir=d2), "E-IMG-DEADLINK")) == 1)
        md_code = FIX_BOX_OKSEG + "示例：`图：assets/missing.svg` 这样写\n"
        chk("行内 code span 里的图示例不误报死链",
            len(codes(check_text(md_code, "code.md", base_dir=d2), "E-IMG-DEADLINK")) == 0)
        (d2 / "dead.md").write_text(md_dead, encoding="utf-8")
        chk("入口目录校验能命中图死链(退出码 1)", main([str(d2)]) == 1)

    print(("OK " if ok else "FAIL ") + "verify_explanation --selftest")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
