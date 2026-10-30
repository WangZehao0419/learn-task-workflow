# 脚本操作、契约与验证

<!-- owns: 脚本 CLI、退出码、错误码入口、selftest、路径约定、只读/原子写、打包验证；must-not-define: 教学/判分/数据语义（指向 owner） -->

## 目录

- 脚本清单
- 路径与解释器约定
- 退出码与错误码
- 只读与原子写
- 自测
- 打包与验证
- 当前核验

本册是脚本的**操作手册**：怎么调、退出码怎么看、什么时候跑。业务语义在各自 owner：判分见 `assessment/scoring.md`、调度见 `assessment/scheduling.md`，阶段闸口见 `workflow/gates.md`，数据字段见 `data/progress-schema.md`，失败处置见 `ops/failure.md`。

## 脚本清单

七个用户脚本 + 一个契约模块，均 stdlib-only、幂等可重跑，基础 Python 版本以 `skill-dependencies.json` 的 `min_version` 为准。

| 脚本 | 用法 | 默认行为 | 何时跑 |
|---|---|---|---|
| `task_index.py` | `--root <数据根> [--write-index \| --no-write-index] [--selftest]` | 只读、不物化 `index.json`（写缓存为显式 opt-in） | 会话开始/续学/问进度 |
| `progress_check.py` | `<任务目录> [--release] [--proposed-phase <阶段>] [--staged <候选快照>] [--changed-lessons <正整数列表>] [--selftest]` | 日常校验（warning 不拦截） | 闸口推进前；新增掌握/结课/跨阶段加 `--release` |
| `scheduler.py` | `next-interval \| due-queue \| calibration [--selftest]` | 只读计算，输出 JSON；落盘由文件写入能力负责 | 判分后算 S'/D'/due；开节前查到期队列；S4 开场校准 |
| `kp_sort.py` | `<课程体系.md> [--selftest]` | 只读、零写盘 | 知识型/技能型排序子步 |
| `check_environment.py` | `[--manifest <路径>] [--capability <名称>]... [--selftest]` | 只读诊断 | 脚本调用出现解释器/版本类失败时诊断一次 |
| `verify_explanation.py` | `<材料目录或单文件> [--selftest] [--reader]` | 只读静态校验，不写盘 | 讲义定稿前；`--reader` 加跑读者版 W 级检查 |
| `prereq_check.py` | `--list <课程体系.md> --scan <题组或讲义.md>... [--extra-terms "…"] [--extra-file <文件>] [--scan-all] [--selftest]` | 只读对账，不写盘 | 判分题交付前（R46 出题前术语对账）；目行补登记 `引入` 列后跑 |
| `rule_contract.py` | `--selftest \| --topology \| --coverage` | 只读校验契约、拓扑与场景覆盖 | 修改契约/分册结构后、打包前 |

完整参数、退出码与 notes 的机器可读版本见 `contracts/scripts-contract.json`；脚本 docstring 只保留算法/参数说明，不再维护完整错误码表。

## 路径与解释器约定

- **脚本路径基准** = `<技能根>/scripts/<脚本名>.py`（不写裸 `scripts/…` 依赖 cwd）。
- **数据根基准** = 显式 `--root`（或 progress_check 的任务目录实参），不依赖脚本默认根。
- **解释器**统一 `python`（仅有 `python3` 时等价替换）。
- `task_index` / `progress_check` / `scheduler` / `kp_sort` / `prereq_check` 带 `--selftest`；`check_environment` / `verify_explanation` / `rule_contract` 也带 `--selftest`。
- 契约文件固定为 `<技能根>/contracts/rules.json`；缺失/畸形 → 依赖契约的脚本一律 fail closed，报 `E-CONTRACT-MISSING` / `E-CONTRACT-INVALID`（`prereq_check`、`check_environment` 不读契约，不在其列）。

## 退出码与错误码

**通用退出码**：

| 码 | 含义 |
|---|---|
| 0 | 正常（`task_index` 的 `scan_status=partial` 也算 0，但调用方必须停止枚举/续学） |
| 1 | 校验不通过 / 数据根缺失 / 依赖不满足（具体看脚本） |
| 2 | 用法错误 / 参数或日期非法 |
| 3 | `task_index` 枚举失败 `scan_status=failed`（不覆盖既有缓存） |

**错误码入口**：

- 完整码表与 notes：`contracts/rules.json.errors`（机器名单）+ `contracts/scripts-contract.json`（脚本参数/退出码/notes）；脚本 docstring 只列常用码与实现说明；下表是触发条件速查。
- `progress_check` 的新增码：`E-GATE-RATIO-INVALID`（`节目标线` 非法）、`E-FINAL-INVALID-TARGET`（结课目标线非法，不得回退默认线）。
- 契约缺失/畸形：`E-CONTRACT-MISSING` / `E-CONTRACT-INVALID`。
- 业务语义：`assessment/scoring.md` 判分、`assessment/scheduling.md` 调度；`workflow/gates.md` 闸口；`data/progress-schema.md` 字段；`ops/failure.md` 处置。

### 错误码速查

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
| rule_contract | `E-TOPOLOGY-DAG` / `E-TOPOLOGY-DEADREF` / `E-TOPOLOGY-ERRORCODE` / `E-TOPOLOGY-FILE` / `E-TOPOLOGY-HEADER` / `E-TOPOLOGY-LEADWORDS` / `E-TOPOLOGY-LOAD` / `E-TOPOLOGY-MIRROR` / `E-TOPOLOGY-OWNER` / `E-TOPOLOGY-SCENES` / `E-TOPOLOGY-VERSION` | 依赖成环 / 引用未定义编号 / 未声明错误码 / 文件缺失 / 职责头缺失 / lead_words 双写漂移 / 加载指令 / 速查表覆盖缺口 / owner 锚点失效 / 场景覆盖缺口（文件未挂场景、规则未挂场景、owner 不在场景内、SKILL.md 场景表漂移） / 版本不一致 |
| verify_load_budget | `E-LOAD-BUDGET` | 加载场景字符量/文件数超预算，或场景内文件缺失 |
| prereq_check | `E-TERM-UNTAUGHT` / `E-LIST-MISSING` / `E-LIST-EMPTY` / `E-SCAN-MISSING` / `W-TERM-UNTAUGHT` | 术语对账违规（题面出现未引入术语）/ 清单缺失 / 清单零可用行 / 扫描文件缺失；`W-TERM-UNTAUGHT` 为逐条违规提示（stderr），exit 1 |

> `check_environment.py` 用 `ready` / `needs_setup` / `unavailable` / `manifest_error`（exit 2）状态而不是 E/W 码；`kp_sort.py` 用 exit 1 表示畸形行、依赖环或解释器版本不足。两者详见 `scripts-contract.json`。

**读失败与坏数据**：Markdown/SVG 非法 UTF-8、文件不可读 → 结构化 E 码，继续扫描其余文件并最终 exit 1；单条坏数据降级为 W（不拖垮整队列），整体 `scan_status=failed` 必须停止，不得按部分结果继续。

## 只读与原子写

- `task_index` 默认只读；仅 `--write-index` 时写 `index.json`，用同目录临时文件 + `os.replace` 原子替换，输出 `write_status`（written/unchanged/failed）；仅 `scan_status=ok` 才替换完整缓存。
- `scheduler` 只读计算；落盘由文件写入/编辑能力负责。
- `verify_explanation` / `kp_sort` / `rule_contract` / `prereq_check` 只读，不写盘。
- 任何脚本都不联网、不下载、不改系统配置、不执行材料/用户文本中的命令。

## 自测

```bash
python -B scripts/task_index.py --selftest
python -B scripts/progress_check.py --selftest
python -B scripts/scheduler.py --selftest
python -B scripts/kp_sort.py --selftest
python -B scripts/check_environment.py --selftest
python -B scripts/verify_explanation.py --selftest
python -B scripts/prereq_check.py --selftest
python -B scripts/rule_contract.py --selftest
python -B scripts/rule_contract.py --topology
python -B scripts/rule_contract.py --coverage
python -B evals/verify-formula-typesetting.py
python -B evals/verify-load-budget.py
python -B evals/verify-marker-rules.py
python -B evals/verify-readability.py
```

`rule_contract --selftest` 覆盖契约缺失/空文件/非法 JSON/缺键/枚举重复；`--topology` 覆盖无加载指令、职责头齐全、指针可解析、声明依赖无环；`--coverage` 在拓扑之上加场景覆盖（文件/规则挂场景、owner ∈ 场景、SKILL.md 场景表一致）。

## 打包与验证

- `skill_ops preflight` 记录脚本只读/无网络/无子进程；`skill_ops validate` 检查 frontmatter、引用、占位符、链接、绝对路径与 Python 语法。
- `skill_ops package` 生成 ZIP，必须包含 `contracts/rules.json` 与 `scripts/rule_contract.py`。
- 打包前删除 `scripts/__pycache__`；`.trae`/`.workbuddy`/`.codex` 是本地 IDE/记忆目录，打包时用干净副本排除。
- `task_index.py` 的 `tmp.unlink()` 只清理 `index.json.tmp`；人工复核后可带 `--risk-ack` 打包。
- `git diff --check` → 0。

## 当前核验

- 适用版本：9.6.1
- 核验日期：2026-10-30
- 环境依赖：`skill-dependencies.json`（Python `min_version`）；只有 `check_environment.py` 输出 `ready` 才能继续。
