# learn-task-workflow

面向 LLM agent 的私人家教工作流 skill：把「系统学习」需求跑成带硬闸口、进度落盘、跨会话可续学的任务流——先教后练、判分四态、间隔复习、分型验收、条件化出题与讲义生成。

## 定位

- **适合**：多轮系统学习 / 备考 / 啃材料，要进度可跟踪、练习有反馈、跨会话能接着学；也支持独立生成学习用讲义 / 题组 / 试卷。
- **不适合**：单点知识问答、单题解题、代写、单纯总结材料或主题调研。完整触发边界见 `SKILL.md` frontmatter 与 `references/routing/triggers.md`。

## 安装

把整个目录复制到宿主的 skills 目录。运行环境只需本地 Python（标准库，无第三方依赖）：

```bash
python scripts/check_environment.py
```

## 架构

- `SKILL.md` —— 路由与加载调度：21 个场景按轮次取用，叠加与补读另计；场景核心集见其中的加载场景表。
- `references/`（95 册）—— 规则正本，每册头部有 `owns / must-not-define` 职责声明。
- `contracts/rules.json` —— 机器契约：枚举 / 阈值 / 预算 / 错误码 / 44 条跨文件意图。
- `scripts/`（10 个，stdlib-only、幂等只读）—— 进度校验、判分证据验证、间隔调度、契约校验。
- `evals/` —— 行为级验收脚本与夹具。

分册职责的唯一事实源是文件头声明与 `contracts/rules.json` 的 `files[]`；目录级导航见 `SKILL.md`「参考文件（按需加载）」。

## 自检

```bash
python -B scripts/rule_contract.py --selftest
python -B evals/verify-load-budget.py
```

全部脚本命令、退出码与 selftest 清单见 `references/ops/scripts.md`。

## 维护

版本号五方同步（`SKILL.md` frontmatter / `contracts/rules.json` / `skill-dependencies.json` / `evals/evals.json` / `references/ops/scripts.md` 的「适用版本」行），由 `rule_contract.py --topology` 机检。文献与借鉴出处见 `CREDITS.md`（维护侧档案，不进运行时上下文）。版本历史见 `git log` 与 tag。
