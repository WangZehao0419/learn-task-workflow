# 归因与许可声明（CREDITS）

本技能在**思想层**借鉴了下列公开方案，**未整段复制任何候选技能的代码、正文或模板**。借鉴点与来源许可证如下：

| 来源 | 许可证 | 借鉴方式 |
|------|--------|----------|
| claude-tutor（github.com/kirilxd/claude-tutor） | MIT | 语义借鉴：轻量间隔重复排程思想、可验证性（触发用例 + 闸口证据落盘） |
| tutor-skills（bevibing / RoundTable02） | MIT | 语义借鉴：概念级薄弱点追踪、出题「零提示」约束 |
| duthaho/skillhub | MIT | 语义借鉴：持久 markdown 日志 + 按日期排复习 |
| uuta/dotfiles | 未声明（默认版权保留） | 语义借鉴：范围护栏（单课程小节数上限） |
| roebi/agent-skills | **CC BY-NC-SA 4.0** | **仅思想层参考，不复制正文/模板**（规避 NonCommercial / ShareAlike 许可不兼容风险） |
| Bloom（github.com/Li-Evan/Bloom，learn-crossover / learn-occam） | MIT | 语义借鉴：跨界三猜想讲授前置、「只用确证的已会知识」铁律、澄清轮次上限、轻量出口「值不值得学」框架 |
| universal-diagnostic-tutor（github.com/SenmuuuuW/universal-diagnostic-tutor-skill） | MIT | 语义借鉴：判分后教学动作决策（八动作）、「只追问会改变答案的缺失信息」、失败分类学驱动的 QA 核对方法论 |
| kaogong-skill（github.com/KeWang0622/kaogong-skill） | MIT | 语义借鉴：来源三级分级与出处四要素、主观题批改纪律（语义等价/训练量表声明）、统计样本数披露 |
| agent-tutor-skill（github.com/Bhala-Srinivash/agent-tutor-skill） | MIT | 语义借鉴：学习者画像（类比领域）、掌握度徽章（按稳定度分档可视化） |
| feynman-tutor（github.com/koukekoukej-glitch/feynman-tutor） | MIT | 语义借鉴：学习者笔记三层结构与「一次观察不升级成画像」纪律、「缺事实直接给」的苏格拉底边界 |
| learning-tutor（github.com/MyLiya46/learning-tutor） | MIT | 语义借鉴：课首知识图谱定位、费曼输出任务六选一 |
| spaced-repetition-teaching（clawhub.ai/tylerbittner/skills/spaced-repetition-teaching） | 未标注（其引用的 FSRS 算法参考实现为 MIT） | 语义借鉴：条件化知识卡片字段（Interrogate 追问 / When to reach for it 触发信号）→ 判定题机制、「遗忘是数据不是失败」 |
| learn-faster-kit（github.com/hluaguo/learn-faster-kit） | MIT | 思想层参考（FASTER 框架与既有方法论同源，未直接采纳机制） |
| Clawic study（clawhub.ai/ivangdavila/study） | 未公开源码仓库 | 语义借鉴：学习方法有效性档案（What Works 裁决）、出题形态分界（可推导/任意性内容）、分块→交错切换判据、考前睡眠巩固 |
| skill-tutor（github.com/Nitzan94/claude-code-skills） | 未声明（默认版权保留） | 语义借鉴：真实项目练习优先 |
| DeepTutor（github.com/HKUDS/DeepTutor） | Apache-2.0 | 语义借鉴：掌握后保持复习、同会话重复抑制、KP 分型掌握门、判分四态/作废申诉、模块目标/材料覆盖、记忆写法纪律、ask hint、来源备课/讲授证据、出题流水线、视觉任务原图来源、选项/答案键规则；未复制代码/正文/模板 |
| 公开行为科学研究（游戏化激励与间隔重复文献） | 公开文献 | 语义借鉴：学习连击呈现（断档不惩罚、轻提醒） |
| 独立教学工作区能力 | 由宿主按需提供 | 互补**分工声明**（非复制）：本技能走中文应试/材料场景的 markdown 进度流 |

**原创贡献**：强制阶段闸口纪律（禁止跨阶段、单轮只推一小步）、薄弱点/错题本双轨、学科族教学法分流、中文应试与材料场景适配、确证已会铁律与摸底/画像/跨界三机制的联动闭环、教学八动作与难度伺服的正交设计、学习者画像「可选全局文件 + 三铁律 + 脚本零感知」的零迁移落地方式——上述组合在 prior-art 检索到的同类方案中未见同时具备。其中保持复习、分型门、四态判分、交接/记忆纪律、ask hint、来源证据、出题流水线、视觉任务原图来源与选项规则等单项机制受 DeepTutor 启发；中文应试场景、脚本化闸口与零迁移落地为本技能原创组合。

**当前版本说明**：6.10.2。在 6.10.1 基础上，补齐 v6.9.0 → v6.10.1 迁移审计发现的 5 项缺口：S4 加载 teaching、S3 讲义/题组拆行、未作答题组优先、讲义草稿留存、深度审计不替代小节闸口；同步版本字段与 eval 元数据。6.10.1 的 15 项规则补回、6.10.0 的职责重构、契约自检与拓扑检查保持不变；归因与许可不变，教学效果仍待真人冷读与延迟迁移验证。

**许可**：本技能以 **MIT 许可证**发布（完整文本见包内 `LICENSE` 文件），版权归「王责豪」所有（Copyright © 2026），允许任何人免费使用、复制、修改与再分发，须随分发保留本声明、`LICENSE` 文件与上表来源归因。上表 16 个外部仓库来源均为思想层语义借鉴、未复制任何代码/正文/模板；其中 4 个上游未声明许可证或无法核验（uuta/dotfiles、spaced-repetition-teaching、Clawic study、skill-tutor），本技能未使用其任何受版权保护的表达，仅参考其公开描述的机制思想；roebi/agent-skills（CC BY-NC-SA 4.0）同样仅思想层参考、零复制，与本技能的 MIT 许可不构成冲突。上表许可证核验日期：2026-10-22（DeepTutor 为 Apache-2.0；其余沿用 2026-10-12 的 GitHub API 与上游页面逐项核实）。
