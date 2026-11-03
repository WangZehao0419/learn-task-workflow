# learn-task-workflow

面向 LLM agent 的私人家教工作流 skill：把「系统学习」需求跑成带硬闸口、进度落盘、跨会话可续学的任务流——先教后练、判分四态、间隔复习、分型验收、条件化出题与讲义生成。

## 定位

- **适合**：多轮系统学习 / 备考 / 啃材料，要进度可跟踪、练习有反馈、跨会话能接着学；也支持独立生成学习用讲义 / 题组 / 试卷。
- **不适合**：单点知识问答、单题解题、代写、单纯总结材料或主题调研（触发与不触发的完整边界见 `SKILL.md` frontmatter 与 `references/routing/triggers.md`）。

## 安装

把整个目录复制到宿主的 skills 目录（或用宿主的 skill 安装流程）。运行环境只需本地 Python（标准库，无第三方依赖），环境自检：

```bash
python scripts/check_environment.py
```

## 使用

对话中以「我要学 X / 教我 X / 带我学 X / 备考 X / 继续学习 / 考考我 / 给 X 写讲义」等说法触发；完整触发短语、近邻陷阱与不触发边界见 `SKILL.md` frontmatter。

## 架构一览

- `SKILL.md` —— 路由与加载调度（21 个场景按轮次取用：讲课 / 批改 / 节末收尾 / 题组 / 复习 / 讲义各一套核心文件，叠加与补读另计）。
- `references/`（98 册）—— 规则正本；每册头部有 `owns / must-not-define` 职责声明，跨文件只留指针。
- `contracts/rules.json` —— 机器契约：枚举 / 阈值 / 预算 / 错误码 / 46 条跨文件意图。
- `scripts/`（10 个，stdlib-only、幂等只读）—— 进度校验与判分证据验证、间隔调度、术语对账、契约校验等确定性环节。
- `evals/` —— 行为级验收脚本与夹具。

## 自检

```bash
python -B scripts/rule_contract.py --selftest
python -B evals/verify-load-budget.py
```

全部脚本命令、退出码与 selftest 清单见 `references/ops/scripts.md`；逐版本审计要点（自 v9.16.3 起）写入 `CHANGELOG.md` 对应版本条目。

## 发布流程要点

版本号五方同步（`SKILL.md` / `contracts/rules.json` / `skill-dependencies.json` / `evals.json` / `ops/scripts.md`「适用版本」，由 `rule_contract.py --topology` 机检），自 v9.16.1 起 scripts.md 适用版本纳入机检；自 v9.16.3 起审计基准文档不再入库（维护侧档案库 docs/ 已退役、永不重建），每版本审计要点写入 CHANGELOG 对应版本条目。版本历史见 `CHANGELOG.md`。
