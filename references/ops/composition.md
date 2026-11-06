# 跨机制组合规则

<!-- owns: 跨机制组合、优先级、互不替代；must-not-define: 各机制自身定义（指向 owner） -->

| 机制 A | 机制 B | 关系与组合规则 |
|---|---|---|
| 教学八动作 | 难度伺服三档 | **正交**：八动作是教学动作维度，伺服三档是难度维度。可组合（如「降档 + 换角度重讲」），每次判分后选定动作并随判分记录落盘（动作 + 一句依据）。定义见 `references/teaching/eight-moves.md`「教学八动作（R23）」与 `references/assessment/grading-states.md`「难度伺服」 |
| 单轮一小步 | 节末五件套 | **等待轮**：五件套②（学员输出任务）占一轮等待用户写完；③落盘、④复习日期、⑤进度对账同轮连做，不新增等待轮（紧凑节奏下按 `references/workflow/s3-cycle.md`「S3 逐节学习（循环体）」合并，等待轮相应减少）。五件定义见 `references/workflow/s3-close.md`「节末收尾五件套」 |
| cw 条目 | 校准画像 | **两层语义**：cw 是逐条重测信号（该条先练，进 due-queue 排序优先）；校准画像 = **当前问题记录中的高信心错误占比**（聚合元认知素材）。cw 是画像的输入行，画像是 cw 的列总和；**画像只描述问题记录投影，不评价整体人格/整体校准水平**。定义见 `references/assessment/scheduling.md`「校准画像」 |
| 课程体系目行状态 | progress.md「暂缓与范围外」 | **双写账本**：课程体系目行记状态（分母账本），progress.md 暂缓区块记处置明细（处置账本）；交叉核对走 `W-KP-HOLD-CROSS`。字段格式见 `references/data/curriculum.md` 与 `references/data/progress-schema.md` |
| 错因 / 级 | S / D 调度字段 | **互不替代**：错因与级是内容属性（错什么，定补救动作与整理深度），S/D 是调度属性（何时再练）；级不参与 due-queue 排序。定义见 `references/teaching/interaction.md` 与 `references/data/progress-schema.md` |
| 检索变式口径 | S3 热身 / S4 复习 / 测验重试 | **变式优先、原题按目标保留**：变式形态、目标组合与例外（T11）唯一事实源见 `references/assessment/generation.md`「零提示与条件化判定题」；本行只声明该口径适用于这三类场景 |
| 节末第 5 件对账 | 覆盖率审计 | **分工**：逐节对账走五件套第 5 件（限 2–3 行）；全量核对走覆盖率审计（不每节都做）。定义见 `references/workflow/s5-close.md` |
| 提示阶梯第 5 梯 | 「不代劳」条款 | **不冲突**：梯底给「答案+缘由」是引导失败后的教学干预，不是响应用户代写请求。定义见 `references/teaching/interaction.md`「提问与提示起点（T06）」 |
| 范围护栏（默认 ~12 节，可按目标调整） | 暂缓与范围外 | **裁剪留痕**：护栏触发时被推迟节全部进暂缓并标「滚雪球候选」，裁剪必须留痕、可见、经用户过目。触发规则见 `references/ops/failure.md` SR-7，字段见 `references/data/progress-schema.md` |
| 苏格拉底边界 | 提示阶梯 / 直接讲解 | **分工**：阶梯管答案级释放节奏；边界情形（缺事实 / 要求直讲 / 精力耗尽）的处置唯一事实源见 `references/teaching/interaction.md`「提问与提示起点（T06）」，本表只引用不另立 |
| 反馈分流（按对错） | 提示阶梯 / 零提示 | **分工**：分流管「判分与错位反馈的时机」与「何时即时确认」（答错即时判分指错位；单题/低信心/首次新方法答对亦即时确认），阶梯管「答案级内容的释放节奏」（渐进 5 梯）；答错即时判分 ≠ 即时给答案。**唯一事实源见 `references/teaching/feedback.md`「反馈策略（T09）」**，本表与阶段表只引用不另立相反规则 |
| 熔断条 | 教学姿态自动切B | **熔断优先**：同节连续 2 题 Again 同时命中两者时，按熔断条处置（本轮不继续出题，走教学八动作或收尾，见 `references/teaching/eight-moves.md`「教学八动作（R23）」与 `references/teaching/interaction.md`「提问与提示起点（T06）」熔断条）；自动切B（`references/teaching/teaching-posture.md`「教学姿态三档（S2 选定，默认混合）」）只在熔断未触发、或熔断恢复后学员仍要求继续讲授时生效，不把熔断轮变成直讲轮 |
| 热身后台记账（R51） | 熔断条 | **互斥豁免**：热身 Again 只刷调度与「需巩固」标注，**不计入熔断条「同节连续 2 题判 Again」的计数**——熔断条保护的是新授练习轮，防「开头复习连错」误熔断。定义见 `references/workflow/s3-cycle.md`「每轮小步（五步）」与 `references/teaching/interaction.md`「提问与提示起点（T06）」 |
| 熔断条 | 可选加练（R55） | **熔断优先、加练即止**：加练轮内触发熔断条（连续 2 题 Again 或学员负向语句）→ 本轮加练立即停止、不转必修、不补题，按熔断条处置收尾；学员拒绝或中途放弃加练**零评判**。定义见 `references/teaching/interaction.md`（熔断条）与 `references/assessment/reinforce.md`「可选加练（巩固与举一反三，R55）」 |
| 对话讲授 | 讲义生成 | **同轮串行**：teach 管轮型/停轮与不整篇投喂（R41），handout 管单元 schema 与定稿；teach 输出不复制讲义全文；同轮只允许一个主场景。定义见 `references/workflow/s3-block.md` 与 `references/handout/pipeline.md` |

## 组合冲突裁决

1. 先定位两个机制的 owner 小节，按 owner 定义执行；本册只决定顺序、优先级与互不替代关系。
2. owner 之间若出现实质冲突，按 `SKILL.md` 的裁决顺序（同一规则冲突归其 owner）处理；不得在本册另立第三条规则。
3. 涉及数字时写契约键（`contracts/rules.json`），不重复打印数值。

## 跨文件意图唯一 owner

唯一事实源 = `contracts/rules.json.intents`（机器可读：id / scope / owner / marker / consumers / scenes）。本册不维护第二份意图表。

新增跨文件意图的顺序：先登记 intent（owner + marker + consumers + scenes），再在 owner 小节写 `<!-- intent:... -->`，最后在 consumer 写指向 owner 的指针。`rule_contract.py --coverage` 检查 owner 唯一、marker 唯一、consumer 指针与指针闭合；`--no-strict-pointers` 只用于临时排查。
