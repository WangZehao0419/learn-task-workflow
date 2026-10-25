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

**当前版本说明**：6.9.0。本版删除全部运行降级路径：环境、输入、脚本、实跑、渲染、落盘或真人验证失败时立即停止，处理完重跑原检查，不再提供人工代验、低等级来源、未实跑版本或替代格式继续；环境清单升 schema 2，移除 `functional_degradations`/依赖级 `degradation`/`partial`。修复伪答案放行、同会话 due、重复调度键、KP 别名、attempt 冲突、非法目标线、reader 缺失与坏编码等确定性问题；统一深讲不强制拆节、P1 可选、代码实跑与真人冷读阻断规则；精简 SKILL 常驻入口。6.8.2 新增对话轮呈现标记与讲授/反馈语气契约：结论先行、三标签、加粗配额、一段一义、禁用装饰、发出前 3 问；语气定为专业严谨、高效务实、直言不讳；同步 `evals/verify-v682-docs.py` 与 E137，不新增闸口、脚本或 progress.md 字段，旧任务零迁移。6.8.1 把讲授单位收敛为「块 = 当前节目标内最细知识点」：一块一知识点、每块 1 道独立检验、独立答对才推进；删除 5–10 分钟、≤5–7 块、≤2 套新记号、30/45 分钟休息、每节 ≤3–4 道正式确认与合并组；层级固定为模块→节→块，排期按节+课时，教材节不按块数拆；节 1 重切 12 个知识点块 + 1 节末综合并做 22 节粒度审计；新增 E136 与 `evals/verify-v681-docs.py`；脚本契约元数据移到 `evals/scripts-contract.json`，`skill-dependencies.json` 保持环境清单 schema 兼容。不新增运行时脚本、告警码、progress.md 字段或闸口阈值，旧任务零迁移。6.8.0 新增小节负载门与逐块推进（默认 1 块 = 1 个 KP；块尺寸 5–10 分钟；逐块确认，关键块正式 ≤3–4 道、简单块轻量确认；通用前置探针；多块小节节末跨块串联）；同步 S3 小步③、对话讲授契约、题量预算、课首块清单、中断续学与版本字段；不新增运行时脚本、告警码、progress.md 字段或闸口阈值，旧任务零迁移。6.7.3 新增读者版可读性契约（三遍路径/一句一判断/标题强调/图解语法/无障碍语义）、P1 读者路径与图表一致性、`verify_explanation.py --reader` W 级检查、E129–E134 与概念/程序/设计三份读者版样板；不新增运行时硬闸口、不新增 progress.md 字段、旧讲义不回溯。保留 v6.7.2 的清理结果：本版按用户要求移除原 SR-8 安全边界及其评测 E43；原 SR-9「未判/作废语义误用」重编号为 SR-8，红线编号恢复连续；术语「学生」统一为「学员」；其余规则不变。保留 v6.7.1 的清理结果：P2 教师备课包/教师版、预习模式、家长版周报/给家长看的学习报告别名与「帮我备课」入口均已移除；学习简报保留为学员自用周复盘，教材级章节层保留。P1 与阶段 3 不变：来源→KP→讲义→题组四向对齐、覆盖行、深度分配、教学例/评估例真实性、来源保真，以及文本结构、主张—证据表、设计量表、主图、效用价值、质量回路、要点卡、移动端/MVP、问题停车位等。包含 `evals/verify-v66-stage3.py`、`evals/verify-v67-p1p2.py`（清理后 19 项）与 E116–E134。不新增 progress.md 字段、不改闸口、旧讲义零迁移；P1 与教材章节层按需启用，不改变 11 条硬合同。v6.0–v6.5 的保持复习/四态判分、分型验收/大纲契约、交接/记忆纪律/来源证据、出题流水线与视觉任务原图来源、讲义理解核心、类型/支持级，以及阶段 3 的来源/范围要求继续有效。机制细则以 `SKILL.md` 与 `references/` 下各分册为准。读者版可读性/图解语法的证据边界见 `methodology.md`；E129–E134 为机器契约，学习效果仍待真人冷读与延迟迁移验证。

**许可**：本技能以 **MIT 许可证**发布（完整文本见包内 `LICENSE` 文件），版权归「王责豪」所有（Copyright © 2026），允许任何人免费使用、复制、修改与再分发，须随分发保留本声明、`LICENSE` 文件与上表来源归因。上表 16 个外部仓库来源均为思想层语义借鉴、未复制任何代码/正文/模板；其中 4 个上游未声明许可证或无法核验（uuta/dotfiles、spaced-repetition-teaching、Clawic study、skill-tutor），本技能未使用其任何受版权保护的表达，仅参考其公开描述的机制思想；roebi/agent-skills（CC BY-NC-SA 4.0）同样仅思想层参考、零复制，与本技能的 MIT 许可不构成冲突。上表许可证核验日期：2026-10-22（DeepTutor 为 Apache-2.0；其余沿用 2026-10-12 的 GitHub API 与上游页面逐项核实）。
