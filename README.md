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

- `SKILL.md`（145 行）—— 激活即读的指令正文：调度协议、**十一条教学红线的完整判据**、阶段速查、数据三簿、按动作与按能力的分册指针。
- `references/`（**27 册**）—— 15 本按能力域合并的**正本册** + 12 个学科 **variant 包**。
- `contracts/rules.json`（7 KB）—— **只存业务常量与结构版本**：枚举 / 阈值 / 标题白名单 / 错误码。不含场景注册表、意图登记或文件清单。
- `scripts/`（10 个，stdlib-only、幂等只读）—— 进度校验、判分证据验证、间隔调度、纯常量加载。
- `evals/` —— 行为级验收脚本、红线回归与触发率用例、夹具。
- `GLOSSARY.md` —— 五个 canonical 词（索引机检 / 行为机检 / 正本册 / variant 包 / 教学红线）。
- `docs/adr/` —— 长期决策记录（ADR-0001 验收轴改判；ADR-0002 编译层退役）。

十一条教学红线的判据写在 `SKILL.md` 里、**自足可判**，不依赖任何分册；正本册只承载背景、例外与学科差异。
目录级导航见 `SKILL.md`「参考文件（按需加载）」。

### 三个已退役的概念

本仓库曾有一套自研编译层：一份机器契约（`files` / `rules` / `scenes` / `intents`）反向生成
`SKILL.md` 的三张加载表，再由脚本校验 127 个分册的文件头、指针与版本。

**它已按职责拆分退役**（见 ADR-0002）。现在：

- 没有**场景注册表**，没有**意图登记**，没有**文件清单**，没有**派生表**
- 没有「索引机检」——结构自洽不再是闸口
- 保留的是**业务常量加载**（七个确定性脚本仍从 `rule_contract.py` 读判分四态、调度参数等）
- 兜底改用**逐文件内容保真比对** + 七个脚本的 `--selftest` import 不变量 + 行为机检

## 自检

```bash
# 常量加载器
python -B scripts/rule_contract.py --selftest

# 七个确定性脚本
for s in scripts/*.py; do python -B "$s" --selftest; done

# 行为机检
python -B evals/verify-formula-typesetting.py
python -B evals/verify-marker-rules.py
python -B evals/verify-readability.py
python -B evals/report-load-footprint.py --check

# 验收资产结构（只校资产可用性，不跑红线、不打分）
python -B evals/verify-redline-assets.py
python -B evals/verify-trigger-assets.py
python -B evals/compare-baseline.py --selftest
```

全部脚本命令、退出码与 selftest 清单见 `references/ops.md`。

## 验收权重

| 层级 | 内容 |
|---|---|
| **P0 主证据** | 教学红线盲回放 11/11 零违规；真人冷读通过 |
| **前置门槛** | 行为机检全绿；触发率 eval 达阈值；旧版快照 baseline 对照跑通 |
| **报告项** | 官方 Agent Skills 规范符合度（**只报告，不设闸**） |
| **明确不作闸口** | 索引机检（已退役）、分册数量、契约是否存在 |

> 红线回归与冷读的**资产已就绪，执行与评分尚未进行**（见 `evals/evals.json` 的
> `redline_regression` / `human_cold_read`，`verdict` 一律为 `未验证`）。
> 按 `evidence_policy`：未跑的条目不得标「通过」。

## 维护

- **版本**：`SKILL.md` frontmatter 的 `metadata.version` 与 `contracts/rules.json` 各登记一处；
  两者不一致由 `rule_contract.py` 加载时暴露。本次发布升版到 **9.20.3**（SKILL.md 与契约一致）。
- **加一门学科**：只在 `references/disciplines/` 加一个 variant 包，不牵动其他文档。
- **改一条规则**：改它在**正本册**里的那一处；要引用就写指针，不复制条文。
- **文献与借鉴出处**：见 `CREDITS.md`（维护侧档案，不进运行时上下文）。
- **版本历史**：见 `git log` 与 tag；重做前的可回滚锚点是 `baseline/v9.19.2-pre-redo`。
