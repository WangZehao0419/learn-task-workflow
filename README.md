# learn-task-workflow

面向真人学员的私人家教工作流 skill：把「系统学习」需求跑成带硬闸口、进度落盘、跨会话可续学的任务流——先教后练、判分四态、间隔复习、分型验收、条件化出题与讲义生成。

## 定位

- **适合**：多轮系统学习 / 备考 / 啃材料，要进度可跟踪、练习有反馈、跨会话能接着学；也支持独立生成学习用讲义 / 题组 / 试卷。
- **不适合**：单点知识问答、单题解题、代写、单纯总结材料或主题调研。完整触发边界见 `SKILL.md` frontmatter 与 `references/routing.md`。

## 安装

把整个目录复制到宿主的 skills 目录。运行环境只需本地 Python（标准库，无第三方依赖）：

```bash
python scripts/check_environment.py
```

## 架构

- `SKILL.md`（158 行）—— 激活即读的指令正文：调度协议、**十一条教学红线的完整判据**、阶段速查、数据三簿、按动作与按能力的分册指针。
- `references/`（**27 个 .md**）—— **20 本按学员动作切分的正本册**（含 `routing`/`subjects-index`/`registry`/`knowledge-artifacts` 等，单册 ≤35,000 B）+ 7 本学科群切片 + `subjects-index.md` 学科层入口 + 12 个学科 **variant 包**（在 `references/disciplines/`，不计入正本册）。
- `contracts/rules.json`（33 KB）—— **只存业务常量与结构版本**：枚举 / 阈值 / 标题白名单 / 错误码 / 红线凭据台账。不含场景注册表、意图登记或文件清单。
- `scripts/`（**22 个文件** = 19 个命令行脚本 + 3 个内部模块，stdlib-only、幂等只读）—— 进度校验、判分证据验证、间隔调度、效果报告机检、纯常量加载、结构机检。
- `evals/` —— 行为级验收脚本、红线回归与触发率用例、夹具。
- `GLOSSARY.md` —— 五个 canonical 词（索引机检 / 行为机检 / 正本册 / variant 包 / 教学红线）。
- `docs/adr/` —— 长期决策记录（ADR-0001 验收轴改判；ADR-0002 编译层退役；ADR-0003 调度增长律换 FSRS-6）。

十一条教学红线的判据写在 `SKILL.md` 里、**自足可判**，不依赖任何分册；正本册只承载背景、例外与学科差异。
目录级导航见 `SKILL.md`「参考文件（按需加载）」。

### 三个已退役的概念

本仓库曾有一套自研编译层：一份机器契约（`files` / `rules` / `scenes` / `intents`）反向生成
`SKILL.md` 的三张加载表，再由脚本校验 127 个分册的文件头、指针与版本。

**它已按职责拆分退役**（见 ADR-0002）。现在：

- 没有**场景注册表**，没有**意图登记**，没有**文件清单**，没有**派生表**
- 没有「索引机检」——结构自洽不再是闸口
- 保留的是**业务常量加载**（5 个模块仍从 `rule_contract.py` 读判分四态、调度参数等：`ltw_parse` / `progress_check` / `scheduler` / `task_index` / `verify_explanation`）
- 兜底改用**逐文件内容保真比对** + 19 个命令行脚本的 `--selftest` import 不变量 + 行为机检
- 两个**内部模块**（`ltw_parse.py` / `ltw_typography.py`）无 CLI，不在 `--selftest` 名单里；覆盖由四个消费者脚本与 `evals/verify-svg-checker.py` 承担，登记关系见 `contracts/scripts-contract.json` 的 `internal_modules`，由 `evals/verify-gate-registry.py` 机检

## 自检

**本地与 CI 跑同一条命令**（票 107）。命令清单只有一处正本：
`contracts/scripts-contract.json` 的 `verification.selftest`（21 条脚本自测）与
`verification.evals`（9 条登记表与行为机检）。本文件不再抄第二份——抄一份就多一处会漂移的副本。

```bash
python -B evals/run-gates.py
```

退出码即结论，三档不合并：`0` 全部通过 / `1` 有闸口查出违规 / `2` 有闸口未测（环境不可用，**不等于通过**）。

CI（`.github/workflows/gates.yml`）跑的就是这条命令，没有第二套口径：违规标红，未测标黄（neutral check run），
通过标绿。想单独看某条，`python -B evals/run-gates.py --list` 打印完整清单。

逐脚本命令、退出码与 selftest 清单见 `references/ops.md`。

## 验收权重

| 层级 | 内容 |
|---|---|
| **P0 主证据** | 教学红线盲回放零违规；真人冷读通过（**两项目前都没有可复核的执行记录**，见下） |
| **前置门槛** | 行为机检全绿；触发率 eval 达阈值；旧版快照 baseline 对照跑通 |
| **报告项** | 官方 Agent Skills 规范符合度（**只报告，不设闸**） |
| **明确不作闸口** | 索引机检（已退役）、分册数量、契约是否存在 |

> **红线回归与冷读的执行记录目前都不可复核。** `evals/evals.json` 的
> `human_cold_read` 为 `未验证`；`redline_regression` 的 11 条 `verdict` 是历史评分留下的底层记录，
> 其对应的执行记录（第七轮 v7）已按 [票 43](https://github.com/WangZehao0419/learn-task-workflow/issues/43) 退役——
> 原件与 git 证据冲突，矛盾消除前不计入 P0。按 `evidence_policy`：没有可复核证据的条目不得算「通过」。
>
> 自 9.21.23 起这三块证据（`cases` / `redline_regression` / `trigger_eval`）**全部**带
> `decided_against_version`，由 `scripts/verify_eval_versions.py` 机检：红线块与触发块的取值都是
> `unknown`（v7 回放声称的判据与 git 对不上、触发块从未运行），按降级口径视作「未验证」——
> 它们**不会**再挂在「通过」栏里。

## 维护

- **版本**：`SKILL.md` frontmatter 的 `metadata.version` 与 `contracts/rules.json` 各登记一处；
  两者是否一致由发版清单人工逐条核对（见 `references/ops.md`「打包与验证」），改一处必改另一处。本次发布升版到 **9.22.4**（SKILL.md 与契约一致）。
- **加一门学科**：只在 `references/disciplines/` 加一个 variant 包，不牵动其他文档。
- **改一条规则**：改它在**正本册**里的那一处；要引用就写指针，不复制条文。
- **文献与借鉴出处**：见 `CREDITS.md`（维护侧档案，不进运行时上下文）。
- **版本历史**：见 `git log` 与 tag；重做前的可回滚锚点是 `baseline/v9.19.2-pre-redo`（→ `725e852`，其 `references/` 树与 `v9.19.2` 相同）。
- **重做删了什么、去了哪**：见 `docs/migrations/content-ledger.md`——v9.19.2 → 当前每一次删除/改名/拆分逐条登记，由 `scripts/verify_content_ledger.py` 机检。
