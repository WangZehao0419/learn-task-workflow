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

**当前版本说明**：7.0.1。在 6.11.0 基础上完成结构性收敛（v6.11.1–v6.14.0 四个批次，最终合并发版 7.0.0）：`--topology` 护栏扩展（加载指令措辞、版本四方一致、全仓错误码 ⊆ 契约、operations 速查表双向覆盖、lead_words 双写、T/F/R 编号引用必有定义）；T01–T11 / F05–F14 共 18 个设计编号重建定义表并入契约 rules（33→51 条），脚本侧 62 处历史编号记号清除（消除与 R1–R33 的双命名空间撞号）；grading.aliases / reader / schemas 死契约接线为唯一数值源（KP 视觉别名 chart/table_graph 漂移随之修复）；新建 `scripts/ltw_parse.py` 统一 task_index / progress_check / kp_sort / scheduler 的行级解析（−233 行重复）；双 owner 重复规则归唯一 owner（视觉任务纪律、due-queue 预算、复述证据三连、题量上限、懂了吗、300 字软提示）；composition 五件套对齐现行定义；formulas 评测口径迁出至 `evals/formula-checks-rubric.md`；9 个大分册补目录；SKILL.md frontmatter 收敛为单一 description。7.0.1 排版收尾（语义零改动）：handout.md 文内剩余重复组逐组归唯一事实源、副本改指路（答案三件套、交付起笔形态清单、单元≠KP、闭卷自检、两态用词、三遍路径/速览/回看索引/标题导航）；五个约 800–1900 字符的超长段落拆为子条目（最长行 1900→411 字符）；全套门控零回归。归因与许可不变，教学效果仍待真人冷读与延迟迁移验证。

**v9.4.0 分科教学细则的证据来源（2026-10-29）**：`references/subjects/` 六文件重写依据公开教育研究与产品一手资料（全部为思想层参考，未复制任何正文/模板）：Math Academy《The Math Academy Way》与官方文档（诊断定位知识边界、前置依赖链、间隔重复+交错复习结合）；ALEKS/Knowledge Space Theory（Cosyn et al. 2021）；Duolingo 半衰期回归（Settles & Meeder, ACL 2016）；Khanmigo 苏格拉底护栏（官方文档与评测）；松鼠AI 纳米级知识点拆分与 MCM（1EdTech 项目书、AAAI-33 报道）；Eedi/Craig Barton 诊断题设计（每个干扰项=一种具名误区）；交错练习 RCT（Rohrer et al. 2015/2020）；CRA 元分析（Ebner et al. 2025）；检索练习 vs 概念图（Karpicke & Blunt 2011, Science）；学习技术效用分级（Dunlosky et al. 2013）；反驳文本元分析（Schroeder & Kucera 2022；Danielson et al. 2024）；显式语法教学元分析（Norris & Ortega 2000；Spada & Tomita 2010）；词汇量覆盖（Nation 2006；Schmitt et al. 2015）；词汇间隔重复元分析（Kim & Webb 2022）；PRIMM 实证（ICERI 2023）；Parsons 问题与子目标标注（Koli Calling 2025；Margulieux et al. 2020）；新手程序员误区综述（Qian & Lehman 2017）；产出导向法（文秋芳, Language Teaching 2016）；2022 义务教育课标、2017(2020 修订)高中课标、新高考 2024 数学 19 题制、专升本/考研/考证考纲结构（教育部官方文件与真题口径）。完整逐条来源与证据分级（A/B/C）见仓库 `docs/research/subjects-v9.4-evidence.md`（维护者侧档案，不进安装包）。均为公开文献与产品公开文档的思想层借鉴，无版权材料复制。

**v9.5.0 分科细则的结构与证据（2026-10-30）**：把学科层拆成三条独立的轴——内容类型定策略、学科群定表征、学科包定内容（全部为思想层参考，未复制任何正文/模板）：Gagné《学习的条件》五类学习结果与「不同结果类型需要不同教学条件」；Merrill 成分显示理论的内容维（事实/概念/程序/原理）× 表现维（记忆/运用/发现），本仓既有 `kp.types` 与之重合故直接复用；Shulman 的 PCK 与 Ball 等的 MKT 作为「学科细则该写什么」的框架。掌握深度标尺取 SOLO 五级（Biggs & Collis 1982）作验收、DOK 四级（Webb 1997）作题难、Bloom 知识维度（Anderson & Krathwohl 2001）作 KP 分型。学科侧证据：Hake 1998 交互式参与归一化增益；FCI 与 TUG-K 类力学/图像误区；McDermott 组电学误区；Johnstone 三重表征与 Nurrenbern–Pickering 概念题/算法题分离；CCI 大样本基线；Vision & Change 五概念与 CINS 自然选择误区；CCSS-M 八条数学实践；Singapore CPA 与 bar model；van Hiele 五水平；APOS/procept；van Zeeland & Schmitt 词汇覆盖阈值；Norris & Ortega 与 Spada & Tomita 显式语法教学；Lyster & Ranta 纠错反馈类型；NRP 五支柱与 Simple View of Reading；SRSD 写作策略教学；PISA 2018 阅读过程框架；BRACElet 与 PRIMM/Parsons/子目标标注；Wineburg 史料三启发式；请求权基础检索；illness scripts 与去偏清单的负面 RCT；Fitts & Posner 动作技能三阶段、Macnamara 2014 刻意练习分域解释力、Wulf 外部注意焦点。蓝军侧：学习风格、左右脑、一万小时、Bloom 2-sigma、三线索法、学习金字塔等均经核查后**不写入正文**。完整逐条来源、证据分级（A/B/C）、「明确无法核实」与「不采纳清单」见仓库 `docs/research/subjects-v9.5-evidence.md`（维护者侧档案，不进安装包）；计划-交付比对与无损失台账见 `docs/review/v9.5.0-coverage-audit.md` 与 `docs/review/v9.5.0-no-loss-ledger.md`。**考试结构（分值、题型、时长、合格线）自本版起不写入细则**——每次开课按官方大纲与近 3–5 年真题现查，结果落盘到该任务的课程体系与备料台账。

**许可**：本技能以 **MIT 许可证**发布（完整文本见包内 `LICENSE` 文件），版权归「王责豪」所有（Copyright © 2026），允许任何人免费使用、复制、修改与再分发，须随分发保留本声明、`LICENSE` 文件与上表来源归因。上表 16 个外部仓库来源均为思想层语义借鉴、未复制任何代码/正文/模板；其中 4 个上游未声明许可证或无法核验（uuta/dotfiles、spaced-repetition-teaching、Clawic study、skill-tutor），本技能未使用其任何受版权保护的表达，仅参考其公开描述的机制思想；roebi/agent-skills（CC BY-NC-SA 4.0）同样仅思想层参考、零复制，与本技能的 MIT 许可不构成冲突。上表许可证核验日期：2026-10-22（DeepTutor 为 Apache-2.0；其余沿用 2026-10-12 的 GitHub API 与上游页面逐项核实）。
