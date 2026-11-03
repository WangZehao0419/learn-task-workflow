# learn-task-workflow 结构体检与修改单

- 审计对象：`d:\me\learn-task-workflow`（版本 9.15.1）
- 审计日期：2026-11-03
- 审计性质：只读审计 + 方案设计；本次未修改任何既有文件。最终核验（2026-11-03 22:48）时 `git status --porcelain` 只有本单一个未跟踪文件 `?? docs/refactor-proposal-2026-11-03.md`
- 体量口径：字符数按 Python 文本读取（UTF-8 解码、CRLF 归一为 LF），与 `verify-load-budget.py` 的预算口径一致；行数按 `splitlines()` 计
- 审计依据：SKILL.md、README、CHANGELOG、contracts/、scripts/、evals/、references/、docs/、.trae/，以及实际运行的 9 个脚本 selftest、5 个 eval 校验器、`rule_contract --topology/--coverage/--audit-strict`
- 审计期间工作区出现过一次并发会话的瞬时改动并已回退，见 1.6；本单所有基线数字均按回退后的 9.15.1 计算

---

## 0. 一句话结论

**规则层已经过关，真正塌的是控制面**：加载预算贴顶（6 个场景余量不足 1,000 字符）、校验器存在三处“假绿”（版本第五源未纳入机检、`E-TERM-UNTAUGHT` 是只写不发的死码、`--audit-strict` 对 211 条不可达指针放行）、评测只覆盖 S3/S4 且 3 例未验证。继续加规则时，维护者只能在“拆场景”和“改校验器”之间反复付费，而不是在教学内容上迭代。

三个最致命的结构性问题：

1. **容量悬崖**：`s4-review` 场景预算 32,957/33,000（余 43 字符），最坏轮 `s3-handout` 135,695/137,800（余 2,105 字符）；SKILL.md:191 又明令“加规则先拆场景，不抬上限”。新增一条规则的平均成本已经高于拆一个场景。
2. **假绿**：版本校验只覆盖 4 个文件（`scripts/rule_contract.py:300-323`），`references/ops/scripts.md:97` 仍写“适用版本：9.13.4”却全绿；`E-TERM-UNTAUGHT` 在 `contracts/rules.json:2174` 和 `references/ops/error-codes.md:51` 被声明为由 `prereq_check` 发出，但 `scripts/prereq_check.py:248` 只发 `W-TERM-UNTAUGHT`；`--audit-strict` 在 211 条 `E-POINTER-LOAD` 下仍返回 0。
3. **评测窄**：`evals/evals.json` 共 23 例，仅 1 例 machine，20 例“通过”依赖人工回放，3 例（E33/E34/E35）明确“未验证”；用例没有 scene/rule 字段，无法机器证明 22 个场景、78 条规则被覆盖。

---

## 1. 现状诊断

### 1.1 体量与结构地图

| 层 | 真实体量 | 事实与风险 |
|---|---|---|
| `SKILL.md` | 207 行 / 18,575 字符 | 常驻入口。80–193 行是 22 场景加载表，占 11,488 字符（约 62%）；其余是红线、速查与目录导航 |
| `references/` | 99 册 / 276,836 字符 | 61 册不足 60 行，15 册不足 30 行；文本入链 Top5（册内相对路径正则计数）：`assessment/scoring.md` 72、`assessment/generation.md` 54、`teaching/interaction.md` 36、`handout/unit-schema.md` 32、`workflow/s3-block.md` 30 |
| `contracts/rules.json` | 4,372 行 / 89,754 字符 | 99 files / 78 rules / 46 intents / 22 scenes / 162 个错误码；只被脚本读取，不占模型上下文 |
| `contracts/scripts-contract.json` | 128 行 / 6,580 字符 | 9 个 CLI + 1 个内部模块的参数、退出码、notes 契约 |
| `scripts/` | 10 个 .py / 429,927 字符 | `progress_check.py` 2,883 行；`check()` 849–1788（940 行）；`selftest()` 1846–2830（985 行） |
| `evals/` | `evals.json` 514 行 / 18,513 字符；5 个 `verify-*.py` 共 47,723 字符 | 23 例：20 通过、3 未验证；machine 仅 E31 一例 |
| `docs/` | 44 文件 / 364,760 字符 | `docs/review/` 37 册 268,873 字符；`docs/research/` 6 册 72,448 字符；无总索引 |
| `CHANGELOG.md` | 42 行 / 21,560 字符 | 一个版本压成一条超长行，diff 不可读 |

另有本地未跟踪产物（均被 `.gitignore` 排除，不属于 skill 内容，2026-11-03 实测）：`.workbuddy/` 40 文件 7,699 KB、`review_inputs/` 51 文件 551 KB、`.zcode/` 24 文件 155 KB、`.trae/` 27 文件 236 KB、`outputs/` 7 文件 835 KB，合计约 9.3 MB。

### 1.2 结构判断：不是“规则屎山”，是“控制面屎山”

本次没有发现新的规则级双定义。抽查三组高风险概念，均为单正本 + 指针：

- “判分四态”正本在 `references/assessment/scoring.md:3`（`owns` 声明），`references/assessment/generation.md:36/87`、`references/data/layout.md:64` 只回指。
- “先教后练”正本在 `references/teaching/lesson-flow.md:3/9`（`owns` 声明），`references/assessment/generation.md:63/64`、`references/assessment/scheduling.md:25`、`references/teaching/explain-quality.md:16` 只回指。
- 版式与错误码由 `references/ops/typography.md`、`contracts/rules.json` 持有，SKILL.md 只留摘要。

因此，**早期“概念重复/规则冲突”问题基本已收敛**（`CHANGELOG.md` 多处记录的“去重”批可佐证，第 9/17/19/23 行）。真正的问题是：

- 加载单位已经切到最小，再切只会增加路由成本；
- 机器契约虽大，但不进上下文，拆它只会改 CLI 契约；
- 预算、校验、评测这三条控制链没有跟着规则一起演进。

### 1.3 重复与冲突点

| 编号 | 位置 | 事实 | 性质 |
|---|---|---|---|
| C1 | `SKILL.md:74` vs 全书 | SKILL.md 默认称呼“同学”；`references/` 与 SKILL.md 其余位置共 374 处用“学员” | 术语不统一；是否改需拍板 |
| C2 | `SKILL.md:191` vs `docs/review/v9.12.2-fix-baseline.md:11` | 现行硬规则写“加规则先拆场景，不抬上限”；v9.12.2 记录曾把 `supplements_per_scene_max` 4→5、`supplement_chars_max` 20000→24000 来容纳新机制 | 规则没有例外条款，历史上已破例一次 |
| C3 | `references/ops/error-codes.md:51` vs `scripts/prereq_check.py:248` | 文档把 `E-TERM-UNTAUGHT` 归给 `prereq_check`；脚本只发 `W-TERM-UNTAUGHT` | 文档-代码冲突，详见 1.4 |
| C4 | `README.md:41` vs `scripts/rule_contract.py:300-323` | README 说“版本号四方同步，`scripts.md` 的适用版本随版更新”；机检只查四方，第五源靠手工 | 流程承诺与校验能力冲突 |
| C5 | `README.md:27` vs `references/ops/scripts.md:55` | README 称脚本“幂等只读”；`task_index` 在 `--write-index` 时会写 `index.json` | 默认只读成立，“只读”绝对化不成立 |
| C6 | `README.md:27` vs `references/ops/scripts.md:9` | README 写“10 个”；scripts.md 写“八个用户脚本 + 一个契约模块”（另有内部模块 `ltw_parse.py`） | 计数口径不同，易误读 |

未发现需要立即删除的重复规则；不建议用“合并小册”解决重复，理由见第 4 节。

### 1.4 文档-脚本漂移点（全部可复现）

| 编号 | 文档位置 | 文档说法 | 真实情况 | 为什么没被拦住 |
|---|---|---|---|---|
| D1 | `references/ops/scripts.md:97` | `适用版本：9.13.4` | 当前版本 9.15.1（`SKILL.md` frontmatter、`contracts/rules.json`、`skill-dependencies.json`、`evals/evals.json` 均为 9.15.1） | `check_versions` 只比对四处（`scripts/rule_contract.py:300-323`），scripts.md 不在名单 |
| D2 | `references/ops/error-codes.md:51` | `prereq_check` 发 `E-TERM-UNTAUGHT` / `E-LIST-MISSING` / `E-LIST-EMPTY` / `E-SCAN-MISSING` / `W-TERM-UNTAUGHT` | `scripts/prereq_check.py:248` 只 append `W-TERM-UNTAUGHT`；`contracts/scripts-contract.json:104` 的 notes 也只登记 W。`E-TERM-UNTAUGHT` 在 `contracts/rules.json:2174` 声明，但全仓脚本与 evals 无任何产出 | `--topology` 只查“提到即声明”和“文档双向覆盖”，不查“声称的发出者真的发出” |
| D3 | `docs/review/v9.15.0-round-layout-baseline.md:26/52` | `E-POINTER-LOAD` 警告“约 40 条” | `python -B scripts/rule_contract.py --audit-strict` 实测 `loadability=211`；`CHANGELOG.md:5` 也写“loadability 211 与基线同集” | 审计文档与 CHANGELOG 各自维护数字，没有单一事实源 |
| D4 | `references/ops/error-codes.md:7`、`references/ops/scripts.md:46` | 机器名单在 `contracts/rules.json.errors` | 顶层键不存在；实际在 `contracts/rules.json.constants.errors`（`rule_contract --get errors` 做了别名，JSON 读取器没有） | 文档路径未在机检中解析 |
| D5 | `evals/evals.json:446` | E31 证据写 `verify-readability 31 checks, 31 OK` | 实测 `verify-readability: 34 checks, 34 OK, 0 FAIL` | machine 证据是冻结字符串，没有随校验器增长重跑 |
| D6 | `README.md:27` | 脚本“幂等只读” | `task_index` 的 `--write-index` 会原子写 `index.json`（`references/ops/scripts.md:55`） | README 未随脚本能力更新 |

### 1.5 校验与评测现状（本次实测）

| 检查 | 真实输出摘要 | 结论 |
|---|---|---|
| `scripts/rule_contract.py --topology` | `ok: true`，`version: 9.15.1`，`issues: []` | 全绿，但 D1 仍存在 |
| `scripts/rule_contract.py --coverage` | `files=99, rules=78, scenes=22, intents=46, error_codes={used:157, declared:162}` | 覆盖完整；未校验“码是否真的发出” |
| `scripts/rule_contract.py --audit-strict` | `counts={pointer:0, contract:0, loadability:211}`，rc 0 | 211 条不可达指针不参与闸口 |
| `evals/verify-load-budget.py` | `ok: true`，`worst=s3-handout 135,695/137,800`；`s4-review 32,957/33,000`；`s3-teach 39,449/39,700`；`s3-exercise 31,306/31,600`；`s3-grade 24,669/25,400`；`s3-deep 18,757/19,600`；`s3-handout 67,109/68,100`；`s3-handout-revise 59,424/60,800` | 6 个场景余量 <1,000 字符，最紧 43 字符 |
| `evals/verify-readability.py` | `34 checks, 34 OK, 0 FAIL` | 与 E31 冻结的 31 不一致 |
| `evals/verify-marker-rules.py` | 18/18 | 通过 |
| `evals/verify-round-layout.py` | 7 fixtures, 7 OK | 通过 |
| `evals/verify-formula-typesetting.py` | `35 checks, 35 OK, 0 FAIL` | 通过 |
| 9 个脚本 `--selftest` | 全部 exit 0 | 通过 |
| `scripts/check_environment.py` | `status: "ready"`，`next_action: "进入正常流程"` | 通过 |

`E-POINTER-LOAD` 的 211 条分布（脚本原始输出解析）：

- 来源 Top5：`references/ops/literature.md` 19、`references/assessment/generation.md` 13、`references/ops/failure.md` 12、`references/workflow/s3-block.md` 10、`references/teaching/explain-quality.md` 8。
- 目标 Top5：`references/assessment/scoring.md` 18、`references/handout/pipeline.md` 8、`references/teaching/lesson-flow.md` 8、`references/data/profile.md` 8、`references/handout/typography.md` 8。
- 实例：`E-POINTER-LOAD: references/assessment/generation.md -> references/assessment/exercise-files.md（场景 s4-review,s5-close）`。

这组数字说明：**不是文件少，而是“读过 A 册就能顺着指针去读 B 册”的假设，在 211 处不成立**。SKILL.md:189 又要求“补读失败 → 停止当前运行”，所以模型要么停轮，要么凭记忆执行。

### 1.6 审计期间的一次并发改动（已回退，不计入基线）

审计窗口内（22:45–22:48）另一并发会话曾应用一批 v10.0.0「format 域」改动，随后整体回退。快照如下：

| 时间 | 观察 |
|---|---|
| 22:45:02 | 新增 `docs/review/v10.0.0-format-domain-baseline.md`（4,955 字符） |
| 22:46:33 | `scripts/ltw_typography.py` 被改（+156/−7）：新增 `--kind doc\|ledger\|card\|brief`、`profiles` 与 `E-LEDGERFMT-*` |
| 22:47:19 | `contracts/rules.json` 被改（+28/−1）：`constants.layout.profiles` + 6 个 `E-LEDGERFMT-*` + `W-FIG-DECISION` |
| 22:47:2x | `python -B scripts/rule_contract.py --topology` → `ok: false`，`used=163, declared=169`，8 条 `E-TOPOLOGY-MIRROR`：`error-codes.md` 缺 6 个 `E-LEDGERFMT-*` 与 `W-FIG-DECISION` 条目；`ltw_typography._DEFAULT_LAYOUT` 键集与 `constants.layout` 不一致（契约多 `[]` / 脚本多 `['profiles']`） |
| 22:48:29 | 改动已全部回退：`git status` 只剩本单文件，`--topology` 恢复 `ok: true`、`used=157, declared=162` |

两点结论：

1. `--topology` 确实能抓到“新增码未进 error-codes.md”和“脚本键集与契约不一致”，机检骨架有效；但它抓不到“声明的发出者并未发出”（见 P0-2），也只在有人主动跑时才抓。
2. 审计期间工作区是移动目标：22:47:51 的 `git status` 快照未列出 `contracts/rules.json`，而紧接着的 `git diff` 显示它已被改（同一秒内的并发写入与索引 stat 竞态）。所以“工作区干净”这类断言必须带时间戳，不能当作长期事实。

---

## 2. 与业界做法的差距

| 编号 | 业界做法 | 本仓库现状 | 差距判断 |
|---|---|---|---|
| G1 | Agent Skills 规范建议 `SKILL.md` 正文控制在 500 行以内，并给出 “instructions < 5000 tokens recommended” 的量级；核心原则是“context window is a public good” | 207 行，行数达标；但 18,575 字符（按中文约 1 字符 1 token 的保守口径，约 18k token） | 行数合规、token 量级不合规。注意：**不建议把 80–193 的加载表搬走**，搬走不会减少每轮加载量（见第 4 节） |
| G2 | 规范要求 “Keep file references one level deep from SKILL.md. Avoid deeply nested reference chains.” | 211 条 `E-POINTER-LOAD`，即 A 册在场景 X 内指向场景 X 不可加载的 B 册；如 `generation.md -> exercise-files.md` 在 `s4-review,s5-close` | 存在大量二级引用链，且没有“这是导航指针，不是运行时依赖”的机器标记 |
| G3 | 渐进披露三层：metadata（约 100 tokens）→ SKILL.md → 资源“按需”加载 | 第三层按“场景整包”加载：`s3-handout` 一次 16 个文件 67,109 字符，不区分子任务 | 粒度偏粗；但这是项目刻意的“单场景一次备齐”取舍，不能简单判错 |
| G4 | 确定性脚本负责可判定部分，模型负责判断；eval 用确定性 grader + 稳定环境 + 真实任务 | 脚本分工做得好（9 个 CLI、stdlib-only、selftest 全覆盖）；但 23 例中仅 1 例 machine，其余是人工回放记录 | 确定性能力没有接到评测链上，结构改动无法被自动回归捕获 |
| G5 | 评测应从真实失败中取 20–50 个任务，先小后大，持续跑，记录方差/通过率 | 23 例，3 例未验证，无 scene/rule 覆盖字段，无 runner、无重复跑、无 pass@k | 评测是“验收档案”，不是“可重复 harness” |
| G6 | 文档与代码的单一事实源：版本、错误码、路径应由机检保证 | 版本第五源靠手工；错误码只查“声明/文档覆盖”，不查“发出”；文档路径 `rules.json.errors` 不可解析 | 控制面缺少“说的 = 做的”的等式 |

来源：

- [Skill authoring best practices — Claude Platform Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Agent Skills Specification](https://agentskills.io/specification.md)
- [Equipping agents for the real world with Agent Skills — Anthropic](https://www.anthropic.com/research/equipping-agents-for-the-real-world-with-agent-skills)
- [Demystifying evals for AI agents — Anthropic Engineering](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [Configuration and multi-file skills — Claude Academy](https://academy.claude.com/courses/introduction-to-agent-skills/configuration-and-multi-file-skills)

---

## 3. 修改清单

排序原则：P0 = 会让“全绿”说谎或让下一次改动直接撞墙；P1 = 让控制面可度量、可回归；P2 = 可维护性与文档精度。

### P0-1 把 `scripts.md` 的“适用版本”纳入机检（D1）

| 项 | 内容 |
|---|---|
| 问题 | `references/ops/scripts.md:97` 写 `适用版本：9.13.4`，当前版本 9.15.1；`--topology` 仍 `ok: true`。这是“流程承诺五源同步、机检只查四源”的直接后果 |
| 具体改法 | 1. 在 `scripts/rule_contract.py:300-323` 的 `check_versions` 增加第五源：读取 `<root>/references/ops/scripts.md`，用 `适用版本[：:]\s*(\S+)` 提取，缺失或不等则追加 `E-TOPOLOGY-VERSION`。2. 把 `references/ops/scripts.md:97` 改为 `9.15.1`。3. 在 `scripts/rule_contract.py:952-958` 的版本 selftest 里增加一个“scripts.md 写成 9.9.9 必须报错”的断言。4. `README.md:41` 的“四方同步 + scripts.md 随版”改为“五源同步（含 scripts.md 适用版本）” |
| 涉及文件 | `scripts/rule_contract.py`、`references/ops/scripts.md`、`README.md` |
| 回归风险 | 改 `check_versions` → `--topology`（`rule_contract.py:770`）与 `--selftest`（`:947`）都会受影响；`check_environment.py` 通过 `contracts/scripts-contract.json` 调 `--topology`，若 scripts.md 缺失或格式变化，环境会从 `ready` 变成失败。因此解析必须容错：文件缺失也应报 `E-TOPOLOGY-VERSION`（这是真实缺陷），但正则要允许全角/半角冒号与前后空格 |
| 验证方式 | `python -B scripts/rule_contract.py --topology`（应 `ok: true` 且版本 9.15.1）；`python -B scripts/rule_contract.py --selftest`；`python -B scripts/check_environment.py` 仍 `ready`。在临时 worktree 把 scripts.md 改成 `9.9.9`，确认 `--topology` exit 1 |
| 回滚方式 | 回退这 4 处 hunk；版本号改回 9.13.4 不是回滚，是保留缺陷 |

### P0-2 删除 `E-TERM-UNTAUGHT` 死码，并补“发出者”校验（D2）

| 项 | 内容 |
|---|---|
| 问题 | `contracts/rules.json:2174` 声明 `E-TERM-UNTAUGHT`；`references/ops/error-codes.md:51` 把它归给 `prereq_check`；但 `scripts/prereq_check.py:248` 只发 `W-TERM-UNTAUGHT`，`contracts/scripts-contract.json:104` 的 notes 也只登记 W。结果是文档承诺一个永远不会出现的 E 码，而 `--topology` 全绿 |
| 具体改法 | 1. 最小修复：从 `contracts/rules.json:2174` 删除 `E-TERM-UNTAUGHT`，从 `references/ops/error-codes.md:51` 的码表删除该码；保留 `W-TERM-UNTAUGHT`（它已有真实产出，且 exit 1 已表达“失败”）。2. 系统性修复：给 `contracts/scripts-contract.json` 的每个脚本增加 `emits: ["W-..."]` 字段，或在 `rule_contract.py` 的 `check_error_codes`（`:327-338`）增加一条“每个声明的码必须在其声明的 emitter 源码中出现”的检查；`E-CONTRACT-INVALID` 之类跨脚本码允许 `emitter: "any"`。3. 在 `--selftest` 增加“文档声称发出但源码没有 → 必须报错”的断言 |
| 涉及文件 | `contracts/rules.json`、`references/ops/error-codes.md`、`contracts/scripts-contract.json`、`scripts/rule_contract.py` |
| 回归风险 | 改 `constants.errors` → `check_mirror`（`:341-353`）双向覆盖、`--topology`、`--coverage` 都会重算；只删一侧必然触发 `E-TOPOLOGY-MIRROR`，所以两侧必须同一提交。`emits` 字段若加得太严，`E-CONTRACT-MISSING` 这类由多脚本发出的码会误报，需要 `emitter: "any"` 白名单 |
| 验证方式 | `python -B scripts/rule_contract.py --topology` 应 `ok: true`；`--coverage` 的 `declared` 应从 162 变 161；`grep -R "E-TERM-UNTAUGHT"` 应无结果；`python -B scripts/prereq_check.py --selftest` 通过 |
| 回滚方式 | 恢复两行（rules.json 一个数组元素、error-codes.md 一行）；`emits` 字段可独立回退，不影响运行 |

### P0-3 给“不可达指针”加只降不升的债务闸口（D3 + 1.5）

| 项 | 内容 |
|---|---|
| 问题 | `--audit-strict` 的 `loadability` 是信息项（`references/ops/scripts.md:21` 明写“loadability 信息项不参与”），211 条不参与退出码；`CHANGELOG.md:5` 说“211 与基线同集”，`docs/review/v9.15.0...:26/52` 却说“约 40 条”，没有单一事实源。结果是债务可见、不可控 |
| 具体改法 | 1. 在 `contracts/rules.json.constants.scenes_budget` 增加 `pointer_load_baseline: 211`（新增字段，当前不存在）。2. 在 `scripts/rule_contract.py` 的 `--audit-strict` 分支（`:1631-1638`，判定在 1635–1637）读取该值：`loadability > baseline` 时打印 `E-POINTER-LOAD-DEBT`（新增建议码）并 exit 1；`loadability < baseline` 时打印“可下调基线”，仍 exit 0。`--audit` 保持纯报告。3. 在 `--selftest` 增加纯函数断言：`211 <= 211` 通过、`212 > 211` 失败。4. 在最新基准文档追加一节“2026-11-03 复核：实测 211”，不要改写历史数字 |
| 涉及文件 | `contracts/rules.json`、`scripts/rule_contract.py`、`docs/review/v9.15.0-round-layout-baseline.md`（只追加复核节） |
| 回归风险 | 改 `--audit-strict` 的退出码 → 任何把它当“发布前必过”的流程会受影响；当前 211 仍 rc 0，不会立刻红灯，但未来新增一条跨场景指针就会红灯。这是有意的闸口，必须同时在 `scripts.md:21` 写明“loadability 现在是只降不升预算，不再是纯信息项” |
| 验证方式 | `python -B scripts/rule_contract.py --audit-strict` 现在 rc 0；把基线临时改为 210，确认 rc 1；`--selftest` 通过；`--audit` 仍 rc 0 |
| 回滚方式 | 删除 `pointer_load_baseline` 与对应分支；恢复 `scripts.md:21` 的“信息项”表述 |

### P1-1 给评测加“场景/规则覆盖矩阵”，并显式登记缺口

| 项 | 内容 |
|---|---|
| 问题 | `evals/evals.json` 23 例没有 scene/rule 字段；按 `scenario` 文本人工归类，覆盖集中在 S3/S4/公式，S0/S1/S2/S5/结课/persist/failure/literature/entry 等场景没有对应条目。3 例未验证也没有阻断“行为全绿”的话术 |
| 具体改法 | 1. 在 `evals/evals.json` 顶层增加 `coverage`：22 个场景键，每键为 `{"cases": ["E30"], "exempt_reason": "..."}`；未覆盖场景必须写 `exempt_reason`（例如“需真实学习任务回放，2026-11-xx 前补”），不允许静默留空。2. 新增 `evals/verify-eval-coverage.py`（第 6 个校验器）：校验 22 个场景键齐全、case id 唯一、`verdict` 取值合法、machine 例必须有 `evidence_command`；输出 `未验证: [E33,E34,E35]` 但不阻断静态校验。3. 把 `evals/evals.json:85` 的 `machine_evidence_ref` 从“五个 verify-*.py”改为“六个”。4. 在 `evals/evals.json` 顶层增加 `retired_case_ids`（与 `contracts/rules.json.retired_rule_ids` 对齐），解释 E02–E23 的 22 个编号空档 |
| 涉及文件 | `evals/evals.json`、新增 `evals/verify-eval-coverage.py`、`evals/evals.json:85` |
| 回归风险 | 新校验器只读 evals.json，不碰 references，加载预算不变；但 `machine_evidence_ref` 的“五个”是现有事实字符串，改成“六个”必须与新脚本同一提交。`coverage` 若设为强制字段，23 个 case 不需要逐个补字段（放顶层即可），避免大改 |
| 验证方式 | `python -B evals/verify-eval-coverage.py` 首次应通过且打印未覆盖场景清单与 3 条未验证；删掉 `coverage["s0-s2"]` 应失败；现有 5 个 verify 脚本仍全过 |
| 回滚方式 | 删除新脚本、`coverage`/`retired_case_ids` 顶层块，恢复 `machine_evidence_ref` 字符串 |

### P1-2 重跑并刷新 machine 证据（D5）

| 项 | 内容 |
|---|---|
| 问题 | `evals/evals.json:446` 写 `verify-readability 31 checks, 31 OK`，实测 34/34；`evals/evals.json:437` 的 review_note 仍写“最坏 96,693≤137,800”，而当前最坏是 135,695。machine 例的证据是冻结字符串，校验器增长后没有重跑 |
| 具体改法 | 1. 把 E31 的 `actual_output` 改为 34/34，并新增 `evidence_command` 与 `evidence_observed_at` 字段。2. E30 的“最坏 96,693”标注为“v9.12.2 历史轮次”，或改为当前 135,695（需同时更新 `pass_condition` 的判定口径）。3. 在 `verify-eval-coverage.py` 里校验：machine 例必须有 `evidence_command`；`actual_output` 中的 `N checks` 必须与命令输出的 `N` 一致（可正则抽取） |
| 涉及文件 | `evals/evals.json`、`evals/verify-eval-coverage.py` |
| 回归风险 | 只改 JSON 字符串，不影响运行；但会改变“历史证据”的可追溯性。建议保留 `run_id` 与 `evidence_observed_at`，不要覆盖旧 run_id |
| 验证方式 | 重跑 `python -B evals/verify-readability.py`，输出 34；对照 `evals.json:446`；`verify-eval-coverage` 不应因计数不一致报错 |
| 回滚方式 | 恢复原字符串与 run_id |

### P1-3 给场景预算加“余量预警”（不是抬上限）

| 项 | 内容 |
|---|---|
| 问题 | `s4-review` 余 43 字符、`s3-teach` 余 251、`s3-exercise` 余 294、`s3-grade` 余 731、`s3-deep` 余 843、`s3-handout` 余 991；最坏轮余 2,105。当前只在“超限”时失败，贴顶不可见 |
| 具体改法 | 1. 在 `evals/verify-load-budget.py`（`:10` 说明 `E-LOAD-BUDGET`、`:28` 读预算）增加：`usage = chars / max`，`usage >= 0.98` 时打印 `[warn] <scene> 余 <N> 字符`，并汇总 `headroom_warnings`。2. 该告警不改变 exit code（仍只在超限时 exit 1）。3. 若要给告警一个正式码，新增 `W-LOAD-HEADROOM` 到 `contracts/rules.json.constants.errors.W` 与 `references/ops/error-codes.md`；否则只用文本 warn，避免契约 churn |
| 涉及文件 | `evals/verify-load-budget.py`；若用正式码，另加 `contracts/rules.json`、`references/ops/error-codes.md` |
| 回归风险 | 加正式 W 码会触发 `check_error_codes`/`check_mirror`（`scripts/rule_contract.py:327-353`），必须三处同提交；只用文本 warn 则零契约风险。预警输出可能被现有日志断言误判为失败，需要确认没有脚本 grep `[warn]` |
| 验证方式 | `python -B evals/verify-load-budget.py` 应仍 `ok: true` 且列出 ≥98% 的 4 个场景（s4-review、s3-teach、s3-exercise、s3-handout）；exit 0 |
| 回滚方式 | 删除预警块；若加了 W 码，同时回退三处 |

### P1-4 把 3 个未验证用例变成“发布门”的显式输入

| 项 | 内容 |
|---|---|
| 问题 | E33/E34/E35 在 `evals/evals.json:486/498/509` 标“未验证”，reviewer 为 null；`README.md:28` 仍称 evals 为“行为级验收脚本”。这本身是诚实的，但没有机制阻止下一次发布继续带着 3 个空位 |
| 具体改法 | 1. 在 `verify-eval-coverage.py` 输出 `blocking_unverified` 列表，并在 `README.md:28` 加一句“未验证用例不阻断静态校验，但阻断‘行为全绿’表述”。2. 在 `CHANGELOG` 下一版的发布记录里固定写“未验证 N 条：…”，不写“全部通过”。3. 给 E33/E34/E35 各加 `owner` 与 `due_version` 字段（人工责任，不是代码） |
| 涉及文件 | `evals/evals.json`、`evals/verify-eval-coverage.py`、`README.md`、`CHANGELOG.md` |
| 回归风险 | 纯文档/元数据，无运行时风险；但 `owner`/`due_version` 若设为必填，23 个 case 都要补，建议只对未验证例要求 |
| 验证方式 | `verify-eval-coverage` 打印 3 条；人为把 E33 改成“通过”但 reviewer 仍 null，应报错 |
| 回滚方式 | 删除新增字段与输出 |

### P2-1 拆 `progress_check.py` 的 940 行 `check()`（只在下次必须改它时做）

| 项 | 内容 |
|---|---|
| 问题 | `scripts/progress_check.py` 2,883 行；`check()` 849–1788 共 940 行，`selftest()` 1846–2830 共 985 行。一个函数同时做解析、闸口、证据、报告，任何一处改动都要通读全函数 |
| 具体改法 | 1. 先做行为等价切分：按职责抽出 `_collect_evidence()`、`_check_gate_ratio()`、`_check_exercise_evidence()`、`_render_report()` 四个内部函数，保留 `check()` 作为编排。2. 新增 `scripts/_progress_evidence.py` 之类的内部模块时，参照 `ltw_parse.py` 的 precedent，并在 `contracts/scripts-contract.json` 登记为 internal module。3. 不改变 CLI 参数、退出码、JSON 字段 |
| 涉及文件 | `scripts/progress_check.py`、`contracts/scripts-contract.json`、`references/ops/scripts.md`（若新增内部模块） |
| 回归风险 | 无其他脚本 `import progress_check`（已 grep 确认），但它是数据写回前的主闸口，切分错误会让坏数据通过。必须用现有 `--selftest` 作为行为基线，前后输出逐字比对；不要在同一次改动里改任何阈值或文案 |
| 验证方式 | 改前保存 `python -B scripts/progress_check.py --selftest` 输出；改后逐字 diff；再用 `evals/verify-load-budget.py` 确认 references 未被触碰 |
| 回滚方式 | 单文件 revert；因为不改契约，回滚成本低 |

### P2-2 给 `docs/` 加索引并区分“现行/存档”

| 项 | 内容 |
|---|---|
| 问题 | `docs/review/` 37 册 268,873 字符，`docs/research/` 6 册 72,448 字符；没有索引，最新基准与历史基准混放；D3 的“约 40”正因于此 |
| 具体改法 | 1. 新增 `docs/review/README.md`：表格列出每册日期、版本、结论、是否现行；明确“只有最新一册是 normative，其余是 archive”。2. 在 `README.md:37` 的“逐版本审计基准”后加指向该索引的链接。3. 不改写任何历史文档的正文（历史数字保留，但标注日期） |
| 涉及文件 | 新增 `docs/review/README.md`、`README.md` |
| 回归风险 | 运行时零影响；但新增文档会被 skill 打包带走，增加包体。若打包流程排除 `docs/`，则无影响 |
| 验证方式 | 索引内相对链接逐个 `Test-Path`；`grep` 确认每个 `docs/review/*.md` 都在索引里 |
| 回滚方式 | 删除索引与 README 链接 |

### P2-3 统一“学员/同学”称谓

| 项 | 内容 |
|---|---|
| 问题 | `SKILL.md:74` 默认称呼“同学”；`references/teaching/lesson-flow.md:34` 也出现“同学”；其余 374 处用“学员”。项目记忆里的统一称谓是“学员” |
| 具体改法 | 二选一，不要混用：A. 把对话默认称呼改为“学员”（改 `SKILL.md:74` 与 `lesson-flow.md:34`）；B. 保留“同学”作为对话称呼，但在 `SKILL.md:74` 明确“文档称学员、对话称同学”，并把这条写进术语表。推荐 A，除非用户明确喜欢“同学” |
| 涉及文件 | `SKILL.md`、`references/teaching/lesson-flow.md`；若选 B，另加 `references/ops/glossary.md`（若不存在则不改，避免新建） |
| 回归风险 | 只影响话术，不影响脚本；但 eval 的 fixture/actual_output 可能含“同学”，需要 grep 后同步 |
| 验证方式 | `grep -R "同学"` 只剩允许的展示样例；`verify-round-layout` 等文案校验仍过 |
| 回滚方式 | 改回原文 |

### P2-4 修正契约路径与脚本计数口径

| 项 | 内容 |
|---|---|
| 问题 | `references/ops/error-codes.md:7`、`references/ops/scripts.md:46` 写 `contracts/rules.json.errors`，实际是 `constants.errors`；`README.md:27` 写“10 个”，`scripts.md:9` 写“八个用户脚本 + 一个契约模块” |
| 具体改法 | 1. 两处路径改为 `contracts/rules.json.constants.errors`，并注明 `rule_contract --get errors` 是别名。2. README 改为“10 个 .py（9 个 CLI + 1 个内部模块 `ltw_parse.py`）”；scripts.md:9 保持“8 个用户脚本 + 1 个契约模块 + 1 个内部模块” |
| 涉及文件 | `references/ops/error-codes.md`、`references/ops/scripts.md`、`README.md` |
| 回归风险 | 文档-only；但若把路径写死进新校验器，需同时支持别名 |
| 验证方式 | `python -B scripts/rule_contract.py --get constants.errors` 可读；`--get errors` 仍可读；`--topology` 仍 ok |
| 回滚方式 | 改回原文 |

---

## 4. 不做清单（看着乱但不该动）

1. **不拆 `references/` 的单册，不合并 61 个 <60 行的小册**。v9.13.5 已裁决：拆/合不改变加载字符量，只增加路由与锚点维护（CHANGELOG.md:15）。文件是加载单位，不是代码模块；当前 15 册 <30 行是刻意的“一个规则一个落点”。
2. **不拆 `contracts/rules.json`**。它 89,754 字符，但只在 `rule_contract.py` 读取，不进上下文；拆成多文件会改变 CLI 契约与全仓 82 处文本引用（本次计数），收益为零。
3. **不合并 `subjects/` 与 `disciplines/` 的 4×7 矩阵**。27 册“文本零入链”里有 18 册 `subjects/*`、5 册 `disciplines/*`，其余为 `routing/ecosystem.md`、`data/reconciliation.md`；`subjects/{group}-*.md` 是模板通配加载，不是孤儿；把它们并成一本会让每次学科切换都加载无关学科。
4. **不删 `docs/review/` 历史**。它是版本三态审计的基准，删了会失去“当时为什么这么改”的可追溯性；只加索引（P2-2），不改写历史数字。
5. **不动 `.workbuddy/`、`.zcode/`、`.trae/`、`review_inputs/`、`outputs/`**。这些是本地未跟踪产物（实测合计 9,476 KB，约 9.3 MB），不影响 skill 运行，也不在 git 里。
6. **不为过预算抬 `chars_max`**。`SKILL.md:191` 明令“不抬上限”；s4-review 余 43 字符是制度性约束，正确解法是“拆场景/腾文字/减指针”，不是把 33,000 改成 34,000。
7. **不把 SKILL.md 的场景表搬出去凑 5k token**。80–193 的 11,488 字符是每轮都要用的路由索引；搬到 reference 后仍要每轮加载，净收益为零，反而多一次加载与一次指针失败。
8. **不改判分/闸口语义**（R35、R46、R52、四态、作废申诉等）。本次是结构审计；语义改动需要独立的教学评审与真实学员回放，不能混在结构重构里。

---

## 5. 分批落地路径

| 批次 | 内容 | 验收标准 | 依赖 |
|---|---|---|---|
| 批次 1（P0，1 个 PR，不动教学内容） | P0-1 版本第五源；P0-2 死码 + emits 校验；P0-3 指针债务基线；D3 复核节；D4 路径修正（可并入） | `--topology` ok；`--selftest` ok；`--coverage` declared 161；`--audit-strict` 211 rc 0，基线改 210 则 rc 1；9 个 selftest 与 5 个 verify 全过；`verify-load-budget` 数字与改前完全一致 | 无 |
| 批次 2（P1，评测与控制面） | P1-1 覆盖矩阵 + 第 6 个校验器；P1-2 machine 证据重跑；P1-3 余量预警；P1-4 未验证门 | 新校验器通过并列出未覆盖场景/3 条未验证；machine 计数与脚本一致；`verify-load-budget` 仍 ok 且列出 ≥98% 的 4 个场景；references 未被触碰 | 依赖批次 1 的版本检查与指针基线 |
| 批次 3（P2，可维护性） | P2-1 `progress_check` 行为等价切分；P2-2 docs 索引；P2-3 称谓；P2-4 路径/计数 | `progress_check --selftest` 输出逐字一致；索引链接全通；`--topology` 仍 ok；`grep` 无禁忌称谓 | 依赖批次 2 的评测覆盖，才能接住重构回归 |

批次之间的硬约束：

- 批次 1 不碰 references 正文，所以 `verify-load-budget` 的 22 个场景数字应保持原值；任何字符变化都说明改错了文件。
- 批次 2 的覆盖矩阵会先暴露缺口，不要为了让检查变绿而删场景键；用 `exempt_reason` 记录，再按批次 3/后续补。
- 批次 3 的 `progress_check` 切分必须单独 PR，且不与任何阈值/文案改动混在一起。

---

## 6. 待确认问题

1. **目标宿主的上下文窗口与预算口径**：`round_chars_max=137800`（`contracts/rules.json:2276`）是按哪个模型、多少 token 的窗口定的？是按字符还是 token？如果是 128k token 窗口，135,695 字符已接近上限；如果是 200k，仍有空间。
2. **`scripts.md` 的“适用版本”是保留并纳入机检，还是直接删掉这个字段？** 保留更可追溯，但要求每次发版改两处；删掉则少一个漂移源。
3. **`E-TERM-UNTAUGHT` 是删掉，还是让 `prereq_check` 真的输出 E 级码？** 当前 exit 1 已表达失败，删掉更简单；若保留，需要定义 E 与 W 的分工。
4. **“学员/同学”统一为哪个？** `SKILL.md:74` 与 `lesson-flow.md:34` 是改“学员”，还是明确“文档称学员、对话称同学”？
5. **`docs/review/` 是否随 skill 一起分发？** 若随包分发，37 册 268,873 字符会让安装包膨胀；若不随包，索引只需服务维护者。
6. **E33/E34/E35 由谁在哪个版本前回放？** 是否接受“未验证不阻断静态校验、但阻断‘行为全绿’表述”？
7. **是否接受“指针债务只降不升”闸口？** 接受后，新增一条跨场景指针必须先清一条旧债，或者在同一 PR 里把 `pointer_load_baseline` 下调；这会改变写规则的手感。
8. **审计期间那批 v10.0.0「format 域」改动是否由你方单独推进？** 若继续推进，需先补齐 `references/ops/error-codes.md` 的 6 个 `E-LEDGERFMT-*` 与 `W-FIG-DECISION` 条目、统一 `constants.layout` 与 `ltw_typography._DEFAULT_LAYOUT` 的键集（含 `profiles`）、并创建改动 docstring 里引用的 `references/format/doc-structure.md` 与 `format/floor.md`（回退前这两个路径在仓库中不存在）。

---

## 附录 A：本次实测命令与输出摘要

```text
python -B scripts/rule_contract.py --topology
=> ok: true, version: 9.15.1, issues: []

python -B scripts/rule_contract.py --coverage
=> files=99, rules=78, scenes=22, intents=46, error_codes={used:157, declared:162}, issues: []

python -B scripts/rule_contract.py --audit-strict
=> counts={pointer:0, contract:0, loadability:211}, rc=0

python -B evals/verify-load-budget.py
=> ok: true, worst=s3-handout 135,695/137,800
   s4-review 32,957/33,000; s3-teach 39,449/39,700; s3-exercise 31,306/31,600
   s3-grade 24,669/25,400; s3-deep 18,757/19,600; s3-handout 67,109/68,100
   s3-handout-revise 59,424/60,800

python -B evals/verify-readability.py
=> 34 checks, 34 OK, 0 FAIL

python -B evals/verify-marker-rules.py
=> 18/18

python -B evals/verify-round-layout.py
=> 7 fixtures, 7 OK

python -B evals/verify-formula-typesetting.py
=> 35 checks, 35 OK, 0 FAIL

python -B scripts/check_environment.py
=> status: ready, next_action: 进入正常流程

9 个 scripts/*.py --selftest
=> 全部 exit 0

python -B scripts/rule_contract.py --topology（22:48:29 复核，并发改动回退后）
=> ok: true, used: 157, declared: 162, issues: []

git status --porcelain（22:48:29）
=> ?? docs/refactor-proposal-2026-11-03.md

（22:47 的瞬时并发状态曾为 ok: false / used: 163 / declared: 169 / 8 条 E-TOPOLOGY-MIRROR，见 1.6，不计入基线）
```

## 附录 B：来源

- [Skill authoring best practices — Claude Platform Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Agent Skills Specification](https://agentskills.io/specification.md)
- [Equipping agents for the real world with Agent Skills — Anthropic](https://www.anthropic.com/research/equipping-agents-for-the-real-world-with-agent-skills)
- [Demystifying evals for AI agents — Anthropic Engineering](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [Configuration and multi-file skills — Claude Academy](https://academy.claude.com/courses/introduction-to-agent-skills/configuration-and-multi-file-skills)
