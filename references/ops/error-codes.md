# 错误码速查表

<!-- owns: 错误码速查（E/W 码人读触发条件速查）; must-not-define: 机器码表正本（rules.json.errors）、脚本 CLI/退出码/selftest/路径约定（ops/scripts.md）、失败处置流程（ops/failure.md） -->

## 错误码速查

> 按脚本分组；同一行的码共享触发条件。机器名单以 `contracts/rules.json.errors` 为准（覆盖完整性由 `rule_contract.py --topology` 校验）；本表只补人类可读的触发条件，不重复业务语义。

| 来源 | 码 | 触发条件（速查） |
|---|---|---|
| progress_check | `E-NO-PROGRESS` / `E-UNREADABLE-PROGRESS` / `E-MISSING-FIELD` | 缺 progress.md / 不可读 / 缺必填字段（起点自 S2 起必填） |
| progress_check | `E-ENUM-PHASE` / `E-ENUM-TYPE` / `E-ENUM-FAMILY` / `E-ENUM-START` / `E-ENUM-GRADE` | 阶段 / 类型 / 学科族 / 起点 / 判分结果非法枚举 |
| progress_check | `E-LESSON-ID-MISSING` / `E-LESSON-ID-DUP` | 节路线行缺 `lesson_id=` / 路线间 `lesson_id` 重复 |
| progress_check | `E-NO-EVIDENCE` / `E-EMPTY-EVIDENCE` / `E-NO-GRADED-ATTEMPT` / `E-ALL-FAILED` / `E-HINT-ONLY` / `E-NO-INDEPENDENCE` / `E-KEY-ABILITY-UNMET` / `E-GATE-THRESHOLD` / `E-NO-RESTATEMENT` | 已掌握/放行证据缺失或质量不足：无声明该 `lesson_id=` 的判分记录、空模板、无有效判定、全错、仅提示后对、独立性缺失、关键能力未独立通过、低于比例线、缺复述 |
| progress_check | `E-KP-TYPED-GATE` | 声明了 KP 类型/视觉任务但缺对应分型证据 |
| progress_check | `E-REVIEW-ORIGIN` | S4「复习来源阶段」缺失或不在合法返回枚举 |
| progress_check | `E-ROUTE-UNDONE` / `E-NO-ROUTE-STRICT` / `E-ROUTE-NUMBER` | 结课/已完成但路线未完成 / 路线不可解析 / 路线编号非法 |
| progress_check | `E-NO-FINAL-EXAM` / `E-FINAL-NO-EVIDENCE` / `E-FINAL-BELOW-TARGET` / `E-FINAL-BLUEPRINT-GAP` / `E-FINAL-INVALID-TARGET` / `E-FINAL-ATTEMPT-CONFLICT` | 结课综合测验缺失 / 空文件 / 未达目标线 / 蓝图未覆盖 / 目标线非法 / 同 attempt 结果冲突 |
| progress_check | `E-CORE-UNLEARNED` / `E-NO-DIAGNOSTIC` | 关键能力未讲 / 缺 S1 摸底证据 |
| progress_check | `E-ATTEMPT-CONFLICT` | 同 attempt 结果冲突 |
| progress_check | `E-CURSOR-DANGLING` / `E-EVIDENCE-REF-MISSING` | 动作游标悬空 / 候选证据不存在 |
| progress_check | `E-UNDECLARED-CHANGES` / `E-CHANGED-SET-INVALID` | 候选差分漏查 / 变更集非法 |
| progress_check | `E-GATE-RATIO-INVALID` | `节目标线` 非法 |
| progress_check | `W-EMPTY-EVIDENCE` / `W-UNGRADED-ATTEMPT` / `W-VOIDED-ATTEMPT` | 日常模式空证据 / 未判 / 作废提示（不拦截） |
| progress_check | `W-NO-ROUTE` / `W-UNPARSED-ROUTE` / `W-NO-COVERAGE` / `W-NO-COVERAGE-AUDIT` | 无路线 / 路线畸形 / 无覆盖 / 缺审计 |
| progress_check / task_index | `W-UNPARSED-HOLD` / `W-MULTI-EVIDENCE` / `W-CURSOR-DANGLING` / `W-NO-PROPOSED-STATE` | 暂缓条目畸形 / 多份证据 / 游标悬空 / 未提供拟提交状态 |
| progress_check | `W-KP` / `W-KP-LIST-MISSING` / `W-KP-SUMMARY-MISMATCH` / `W-KP-HOLD-CROSS` / `W-KP-STATE-MISMATCH` | 课程体系缺失 / 覆盖摘要不符 / 双写不交 / 状态不符 |
| progress_check | `W-CURRENT-SECTION` | `当前节` 与学习路线勾选/阶段不一致（节末未递增、跳节或未写末节序号） |
| progress_check | `W-GRADED-LOSS-UNLOGGED` | 节判分记录中「判错」行或标「→ 入薄弱点」行未入薄弱点/错题本（含 `j-` 加练；`z-`/`00-`/`99-`/`S4-` 前缀与作废行豁免；warning 不拦截） |
| progress_check | `W-UNPARSED-KP` / `W-UNPARSED-MODULE` / `W-UNPARSED-MATERIAL` / `W-MODULE` / `W-MODULE-CONTRACT-INCOMPLETE` / `W-MATERIAL-COVERAGE-GAP` | 课程体系目行 / 章规划行 / 材料条目畸形，或章规划与材料覆盖契约不完整 |
| progress_check | `W-STALE-REVIEW-ORIGIN` | 复习来源阶段指向已失效的阶段值 |
| scheduler | `W-PROGRESS` / `W-PROGRESS-MISSING` / `W-PROGRESS-UNREADABLE` / `W-CONFIDENCE-AMBIGUOUS` / `W-CW-LOWCONF` / `W-CW-ORPHAN` / `W-META-INVALID` / `W-NO-EVT` | 任务进度缺失/不可读；信心/时序歧义、低信心 cw、孤立 cw、元数据非法；校准不计或跳过；条目缺 `evt=` 按单条观察计入 |
| scheduler | `W-UNPARSED-ITEM` | 调度条目无法解析或缺合法日期，不入队、不猜值 |
| verify_explanation | `E-BOX` / `E-BOX-EMPTY` / `E-BOX-FORMAT` / `E-BOX-INCOMPLETE` / `E-BOX-WRAP` / `E-HEADER-BRIEF` / `E-REQ-MISSING` | 五要素 / 答案框 / 标记行 / 节首导读缺失或体例错误 |
| verify_explanation | `E-IMG-DEADLINK` / `E-IMG-READ` / `E-READ-FILE` | 图引用死链 / 图读取失败 / 文件读取失败 |
| verify_explanation | `E-RUBRIC-SUM` | 给分点量表各点分值之和不等于合计 |
| verify_explanation | `E-THIRD-CONFLICT` / `E-THIRD-EXEMPT-MISUSE` / `E-LEDGER-RESIDUE` / `W-LEDGER-DRAFT` / `W-RUBRIC-SOURCE` | ③ 不适用与 ③ 答案并存 / 豁免被滥用 / 定稿判分记账残留 / 草稿内台账状态行（学员会读草稿） / 给分点量表缺「官方/训练量表」声明 |
| verify_explanation | `W-MARKER-CONTENT` / `W-STYLE-POINTER` / `W-UNICODE-CHAR` | 标记行带内容 / 头部复制规则正文 / Unicode denylist 字符；`W-UNICODE-CHAR` 定稿前必须清零 |
| verify_explanation | `W-SELFTEST-MISSING` / `W-SELFTEST-EMPTY` | 自测/检验题面区缺同族答案区 / 答案区为空或占位 |
| verify_explanation | `W-READER` / `W-READER-ALT` / `W-READER-CAPTION` / `W-READER-CONCLUSION` / `W-READER-DEEPNEST` / `W-READER-EMPHASIS` / `W-READER-HEADING` / `W-READER-HEADING-BODY` / `W-READER-INDEX` / `W-READER-LINKTEXT` / `W-READER-LONGLINE` / `W-READER-OVERVIEW` / `W-READER-SVG` / `W-READER-TABLE` / `W-READER-TABLE-ALIGN` | `--reader` 版式项：标题/表格/图注/alt/SVG/速览/索引/结论/强调/链接/长行/嵌套 |
| verify_explanation | `W-NO-TIER` | 讲义单元缺 tier 标签 |
| rule_contract | `E-CONTRACT-MISSING` / `E-CONTRACT-INVALID` | 契约缺失 / 畸形 |
| rule_contract | `E-TOPOLOGY-DAG` / `E-TOPOLOGY-DEADREF` / `E-TOPOLOGY-ERRORCODE` / `E-TOPOLOGY-FILE` / `E-TOPOLOGY-HEADER` / `E-TOPOLOGY-LEADWORDS` / `E-TOPOLOGY-LOAD` / `E-TOPOLOGY-MIRROR` / `E-TOPOLOGY-OWNER` / `E-TOPOLOGY-SCENES` / `E-TOPOLOGY-VERSION` | 依赖成环 / 引用未定义编号或补读小节 / 未声明错误码 / 文件缺失 / 职责头缺失 / lead_words 双写漂移 / 加载指令 / 速查表覆盖缺口 / owner 锚点失效或 intent 正本/marker 失效 / 场景覆盖缺口（含 stack/supplements/intent scene） / 版本不一致 |
| rule_contract | `E-POINTER-ANCHOR` / `E-POINTER-FILE` / `E-POINTER-LOAD` | 指针目标文件/标题不存在，或 rule 文件在 core 场景引用了不可加载 owner |
| rule_contract | `E-TOPOLOGY-DEBT` / `E-TOPOLOGY-INTENT` / `E-TOPOLOGY-ORPHAN` / `E-TOPOLOGY-OWNER-DUP` / `E-TOPOLOGY-SCHEMA` / `E-TOPOLOGY-SECTIONNUM` / `E-TOPOLOGY-SUPPLEMENT` / `E-TOPOLOGY-ROUTE` | 指针债务超基线（E-POINTER-LOAD 对数 > constants.pointer_load_baseline，只降不升）/ 规则-intent 映射不闭合 / 磁盘孤儿 / owner 重复 / schema 镜像不一致 / §N 无对应标题 / 补读表漂移 / 场景判别表行内引用的文件在该行主场景不可达 |
| rule_contract | `W-TOPOLOGY-HEADING-DUP` / `W-TOPOLOGY-MARKER-SCOPE` | 同级标题重复 / marker 不在 owner 小节内 |
| verify_load_budget | `E-LOAD-BUDGET` | 加载场景字符量/文件数超预算，或场景内文件缺失 |
| prereq_check | `E-LIST-MISSING` / `E-LIST-EMPTY` / `E-SCAN-MISSING` / `W-TERM-UNTAUGHT` | 清单缺失 / 清单零可用行 / 扫描文件缺失；`W-TERM-UNTAUGHT` 为术语对账逐条违规提示（stderr），exit 1 |

> `check_environment.py` 用 `ready` / `needs_setup` / `unavailable` / `manifest_error`（exit 2）状态而不是 E/W 码；`kp_sort.py` 用 exit 1 表示畸形行、依赖环或解释器版本不足。两者详见 `scripts-contract.json`。
