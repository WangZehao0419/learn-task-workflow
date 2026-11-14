# 规则与错误码总表 正本册

> 要查错误码含义与触发条件时读本册；规则编号总表同册续建。

## 本册目录

1. 错误码速查表

## 错误码速查表
### 错误码速查

> 按脚本分组；同一行的码共享触发条件。机器名单以 `contracts/rules.json.errors` 为准（覆盖完整性由 `rule_contract.py --topology` 校验）；本表只补人类可读的触发条件，不重复业务语义。

| 来源 | 码 | 触发条件（速查） |
|---|---|---|
| progress_check | `E-NO-PROGRESS` / `E-UNREADABLE-PROGRESS` / `E-MISSING-FIELD` | 缺 progress.md / 不可读 / 缺必填字段（起点自 S2 起必填） |
| progress_check | `E-ENUM-PHASE` / `E-ENUM-TYPE` / `E-ENUM-FAMILY` / `E-ENUM-START` / `E-ENUM-GRADE` | 阶段 / 类型 / 学科族 / 起点 / 判分结果非法枚举 |
| progress_check | `E-LESSON-ID-MISSING` / `E-LESSON-ID-DUP` | 节路线行缺 `lesson_id=` / 路线间 `lesson_id` 重复 |
| progress_check | `E-NO-EVIDENCE` / `E-EMPTY-EVIDENCE` / `E-NO-GRADED-ATTEMPT` / `E-ALL-FAILED` / `E-HINT-ONLY` / `E-NO-INDEPENDENCE` / `E-KEY-ABILITY-UNMET` / `E-GATE-THRESHOLD` / `E-NO-RESTATEMENT` | 已掌握/放行证据缺失或质量不足：无声明该 `lesson_id=` 的判分记录、空模板、无有效判定、全错、仅提示后对、独立性缺失、关键能力未独立通过、低于比例线、缺复述 |
| progress_check | `E-KP-TYPED-GATE` | 声明了 KP 类型/视觉任务但缺对应分型证据 |
| progress_check | `E-PREREQ-UNMET` | 出题前前置闸（票 37 Q3 / 票 83）：被出题或判分的目（节证据 attempt 行点名的 KP + 复述勾选点名的 KP + 结课综合测验点名的 KP）其硬前置 `判定≠已判` 且无摸底「已会」括注；前置被暂缓/排除同样拦（它不会被判，等它等于等不到）。**只在 `--release` 生效**，且只对已采用判定字段的任务生效（清单任意一行写了 `判定`）——全零的旧任务按未采用处理，否则升级当天存量任务全红。与 `W-KP-JUDGE` 的分工：W- 拦已写下的记账，E- 拦还没发生的那道题（票 81 Q4） |
| progress_check | `E-REVIEW-ORIGIN` | S4「复习来源阶段」缺失或不在合法返回枚举 |
| progress_check | `E-ROUTE-UNDONE` / `E-NO-ROUTE-STRICT` / `E-ROUTE-NUMBER` | 结课/已完成但路线未完成 / 路线不可解析 / 路线编号非法 |
| progress_check | `E-NO-FINAL-EXAM` / `E-FINAL-NO-EVIDENCE` / `E-FINAL-BELOW-TARGET` / `E-FINAL-BLUEPRINT-GAP` / `E-FINAL-INVALID-TARGET` / `E-FINAL-ATTEMPT-CONFLICT` | 结课综合测验缺失 / 空文件 / 未达目标线 / 纳入 KP 缺**评分点映射**（同行 `KP=<id>｜评分点=<…>`；仅题面提编号不算）/ 目标线非法 / 同 attempt 结果冲突 |
| progress_check | `E-CORE-UNLEARNED` / `E-NO-DIAGNOSTIC` | 关键能力未讲 / 缺 S1 摸底证据 |
| progress_check | `E-ATTEMPT-CONFLICT` | 同 attempt 结果冲突 |
| progress_check | `E-CURSOR-DANGLING` / `E-EVIDENCE-REF-MISSING` | 动作游标悬空 / 候选证据不存在 |
| progress_check | `E-UNDECLARED-CHANGES` / `E-CHANGED-SET-INVALID` | 候选差分漏查 / 变更集非法 |
| progress_check | `E-GATE-RATIO-INVALID` | `节目标线` 非法 |
| progress_check | `W-EMPTY-EVIDENCE` / `W-UNGRADED-ATTEMPT` / `W-VOIDED-ATTEMPT` | 日常模式空证据 / 未判 / 作废提示（不拦截） |
| progress_check | `W-NO-ROUTE` / `W-UNPARSED-ROUTE` / `W-NO-COVERAGE` / `W-NO-COVERAGE-AUDIT` | 无路线 / 路线畸形 / 无覆盖 / 缺审计 |
| progress_check / task_index | `W-UNPARSED-HOLD` / `W-MULTI-EVIDENCE` / `W-CURSOR-DANGLING` / `W-NO-PROPOSED-STATE` | 暂缓条目畸形 / 多份证据 / 游标悬空 / 未提供拟提交状态 |
| progress_check | `W-KP` / `W-KP-LIST-MISSING` / `W-KP-SUMMARY-MISMATCH` / `W-KP-HOLD-CROSS` / `W-KP-STATE-MISMATCH` | 课程体系缺失 / 覆盖摘要不符 / 双写不交 / 状态不符 |
| progress_check | `W-KP-ROW-UNKNOWN-SEG` | 目行含**段名不在白名单**的未知段：该段被忽略、整行照常解析（票 92 前向兼容兜底），每个段名一条告警、同一段名跨行合并；warning 不拦截、不影响 `ok`。**只放宽这一个分支**——状态非法、前置引用不存在、缺段、重复编号仍走 `W-UNPARSED-KP`，无冒号残段与必需段错位同样判畸形 |
| progress_check | `W-KP-JUDGE` | 目行判定三字段**格式合法但语义不闭合**：`判定=已判` 却缺 `判定依据` / 依据指向的判分记录或题号不存在 / 日期非空时指针个数 ≠ 日期个数（日期为空时只允许 1 个指针）/ 同日重复不足「不同日数」/ `判定` 缺席或为「未判」却写了另两字段。**只验指针闭合，验不了「这个题号是不是真的判对了」**（闸口看不到对话与判分过程）；warning 不拦截、不影响 `ok` |
| progress_check | `W-CURRENT-SECTION` | `当前节` 与学习路线勾选/阶段不一致（节末未递增、跳节或未写末节序号） |
| progress_check | `W-GRADED-LOSS-UNLOGGED` | 节判分记录中「判错」行或标「→ 入薄弱点」行未入薄弱点/错题本（含 `j-` 加练；`z-`/`00-`/`99-`/`S4-` 前缀与作废行豁免；warning 不拦截） |
| progress_check | `W-UNPARSED-KP` / `W-UNPARSED-MODULE` / `W-UNPARSED-MATERIAL` / `W-MODULE` / `W-MODULE-CONTRACT-INCOMPLETE` / `W-MATERIAL-COVERAGE-GAP` | 课程体系目行 / 章规划行 / 材料条目畸形，或章规划与材料覆盖契约不完整 |
| progress_check | `W-STALE-REVIEW-ORIGIN` | 复习来源阶段指向已失效的阶段值 |
| progress_check | `W-REVIEW-DEBT` | 存在 `顺延>0` 的复习条目（形态判据，E5）：下一轮开场须明示队列长度与顺延方案。**只验数据形态，验不了「模型有没有明示」**；不参与「连续 3 天」计数；warning 不拦截 |
| progress_check | `W-SECTION-LEVEL` | 状态簿的区标题不是二级标题（如 `### 检索锚` / `### 日达标`）。三级不切换区，条目会被并进上一条区间当条目消费，**且全程不报错**——解析层已对任何层级的同名区硬性静音（不并区、不计入），本告警让该静音看得见。只告警不拦停：存量文件不回溯，修法是把它改成 `## ` 开头 |
| scheduler | `W-PROGRESS` / `W-PROGRESS-MISSING` / `W-PROGRESS-UNREADABLE` / `W-CONFIDENCE-AMBIGUOUS` / `W-CW-LOWCONF` / `W-CW-ORPHAN` / `W-META-INVALID` / `W-NO-EVT` | 任务进度缺失/不可读；信心/时序歧义、低信心 cw、孤立 cw、元数据非法；校准不计或跳过；条目缺 `evt=` 按单条观察计入 |
| scheduler | `W-UNPARSED-ITEM` | 调度条目无法解析或缺合法日期，不入队、不猜值 |
| scheduler / progress_check | `W-DAY-ROW-INVALID` | 「日达标」条目形态不符（应为「<YYYY-MM-DD> ｜ 达|未达 ｜ 证据：<…>」）/ 日期非 ISO / 状态非「达|未达」。只告警不拦停——阈值是 E5 工程约定，不能拿它拦学员 |
| verify_explanation | `E-BOX` / `E-BOX-EMPTY` / `E-BOX-FORMAT` / `E-BOX-INCOMPLETE` / `E-BOX-WRAP` / `E-HEADER-BRIEF` / `E-REQ-MISSING` | 五要素 / 答案框 / 标记行 / 节首导读缺失或体例错误 |
| verify_explanation | `E-IMG-DEADLINK` / `E-IMG-READ` / `E-READ-FILE` | 图引用死链 / 图读取失败 / 文件读取失败 |
| verify_explanation | `E-RUBRIC-SUM` | 给分点量表各点分值之和不等于合计 |
| verify_explanation | `E-THIRD-CONFLICT` / `E-THIRD-EXEMPT-MISUSE` / `E-LEDGER-RESIDUE` / `W-LEDGER-DRAFT` / `W-RUBRIC-SOURCE` | ③ 不适用与 ③ 答案并存 / 豁免被滥用 / 定稿判分记账残留 / 草稿内台账状态行（学员会读草稿） / 给分点量表缺「官方/训练量表」声明 |
| verify_explanation | `W-MARKER-CONTENT` / `W-STYLE-POINTER` / `W-UNICODE-CHAR` | 标记行带内容 / 头部复制规则正文 / Unicode denylist 字符；`W-UNICODE-CHAR` 定稿前必须清零 |
| verify_explanation | `W-SELFTEST-MISSING` / `W-SELFTEST-EMPTY` | 自测/检验题面区缺同族答案区 / 答案区为空或占位 |
| verify_explanation | `W-READER` / `W-READER-ALT` / `W-READER-CAPTION` / `W-READER-CONCLUSION` / `W-READER-DEEPNEST` / `W-READER-EMPHASIS` / `W-READER-HEADING` / `W-READER-HEADING-BODY` / `W-READER-INDEX` / `W-READER-LINKTEXT` / `W-READER-LONGLINE` / `W-READER-OVERVIEW` / `W-READER-SVG` / `W-READER-TABLE` / `W-READER-TABLE-ALIGN` | `--reader` 版式项：标题/表格/图注/alt/SVG/速览/索引/结论/强调/链接/长行/嵌套。图检查（`E-IMG-READ`/`W-READER-SVG`/`W-READER-ALT`/`W-READER-CAPTION`）对任何含图文本生效，不受「像不像讲义」的 gate 约束；gate 关闭时摘要打印「已跳过 N 项读者版检查（未校验）」，不再输出「通过：无违规项」 |
| verify_explanation | `W-NO-TIER` | 讲义单元缺 tier 标签 |
| rule_contract | `E-CONTRACT-MISSING` / `E-CONTRACT-INVALID` | 契约缺失 / 畸形 |
| report_load_footprint | `E-LOAD-STRUCT` | 加载结构不成立：场景文件缺失、同一场景混用多个令牌、补读小节不存在 |
| prereq_check | `E-LIST-MISSING` / `E-LIST-EMPTY` / `E-SCAN-MISSING` / `W-TERM-UNTAUGHT` | 清单缺失 / 清单零可用行 / 扫描文件缺失；`W-TERM-UNTAUGHT` 为术语对账逐条违规提示（stderr），exit 1 |
| verify_effect_report | `W-EFFECT-MARKER` / `W-EFFECT-LEVEL` / `W-EFFECT-RETENTION` / `W-EFFECT-CALIBRATION` / `W-EFFECT-POINTER` | 效果报告缺段（标题容忍尾随括注与全角冒号）/ 判定行缺失或不合体例 / 未测理由占位 / 报告写了「键=值」字段行（只认行首列表项形态，体例纪律）；99- 卷缺「目标线：」；88- 延迟测量写了 `lesson_id=`；元认知未指到「信心=」行或 progress.md；证据指针悬空。**只告警不拦停**，恒 rc=0；报告不存在打印「跳过」不打印「通过」 |

> `check_environment.py` 用 `ready` / `needs_setup` / `unavailable` / `manifest_error`（exit 2）状态而不是 E/W 码；`kp_sort.py` 用 exit 1 表示畸形行、依赖环或解释器版本不足（`fringe` 子命令同口径，但它把「硬前置被暂缓/排除」作为 `blockers` 数据报出、照常 exit 0）。两者详见 `scripts-contract.json`。
>
> `degraded` 不是错误码、也不是第五种状态：它是 `ready` 输出里的一个可选数组，读的是「有没有走降级路径」这件事。检查项里只有 `command_not_found` 一个 reason_code 属它。
