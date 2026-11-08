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

**版本说明（7.0.x 结构收敛批）**：7.0.1。在 6.11.0 基础上完成结构性收敛（v6.11.1–v6.14.0 四个批次，最终合并发版 7.0.0）：`--topology` 护栏扩展（加载指令措辞、版本四方一致、全仓错误码 ⊆ 契约、operations 速查表双向覆盖、lead_words 双写、T/F/R 编号引用必有定义）；T01–T11 / F05–F14 共 18 个设计编号重建定义表并入契约 rules（33→51 条），脚本侧 62 处历史编号记号清除（消除与 R1–R33 的双命名空间撞号）；grading.aliases / reader / schemas 死契约接线为唯一数值源（KP 视觉别名 chart/table_graph 漂移随之修复）；新建 `scripts/ltw_parse.py` 统一 task_index / progress_check / kp_sort / scheduler 的行级解析（−233 行重复）；双 owner 重复规则归唯一 owner（视觉任务纪律、due-queue 预算、复述证据三连、题量上限、懂了吗、300 字软提示）；composition 五件套对齐现行定义；formulas 评测口径迁出至 `evals/formula-checks-rubric.md`；9 个大分册补目录；SKILL.md frontmatter 收敛为单一 description。7.0.1 排版收尾（语义零改动）：handout-layout.md 文内剩余重复组逐组归唯一事实源、副本改指路（答案三件套、交付起笔形态清单、单元≠KP、闭卷自检、两态用词、三遍路径/速览/回看索引/标题导航）；五个约 800–1900 字符的超长段落拆为子条目（最长行 1900→411 字符）；全套门控零回归。归因与许可不变，教学效果仍待真人冷读与延迟迁移验证。

**v9.4.0 分科教学细则的证据来源（2026-10-29）**：`references/subjects/` 六文件重写依据公开教育研究与产品一手资料（全部为思想层参考，未复制任何正文/模板）：Math Academy《The Math Academy Way》与官方文档（诊断定位知识边界、前置依赖链、间隔重复+交错复习结合）；ALEKS/Knowledge Space Theory（Cosyn et al. 2021）；Duolingo 半衰期回归（Settles & Meeder, ACL 2016）；Khanmigo 苏格拉底护栏（官方文档与评测）；松鼠AI 纳米级知识点拆分与 MCM（1EdTech 项目书、AAAI-33 报道）；Eedi/Craig Barton 诊断题设计（每个干扰项=一种具名误区）；交错练习 RCT（Rohrer et al. 2015/2020）；CRA 元分析（Ebner et al. 2025）；检索练习 vs 概念图（Karpicke & Blunt 2011, Science）；学习技术效用分级（Dunlosky et al. 2013）；反驳文本元分析（Schroeder & Kucera 2022；Danielson et al. 2024）；显式语法教学元分析（Norris & Ortega 2000；Spada & Tomita 2010）；词汇量覆盖（Nation 2006；Schmitt et al. 2015）；词汇间隔重复元分析（Kim & Webb 2022）；PRIMM 对照课堂类实证（ICERI 2023；PRIMM 本身无受控 RCT、实证以教师体验为主，v9.8.0 复核降级）；Parsons 问题与子目标标注（Koli Calling 2025；Margulieux et al. 2020）；新手程序员误区综述（Qian & Lehman 2017）；产出导向法（文秋芳, Language Teaching 2016）；2022 义务教育课标、2017(2020 修订)高中课标、新高考 2024 数学 19 题制、专升本/考研/考证考纲结构（教育部官方文件与真题口径）。完整逐条来源与证据分级（A/B/C）自 v9.16.3 起并入本文件下方「v9.4.0 分科逐条证据」节（维护者侧档案，机检不可见）。均为公开文献与产品公开文档的思想层借鉴，无版权材料复制。

**v9.5.0 分科细则的结构与证据（2026-10-30）**：把学科层拆成三条独立的轴——内容类型定策略、学科群定表征、学科包定内容（全部为思想层参考，未复制任何正文/模板）：Gagné《学习的条件》五类学习结果与「不同结果类型需要不同教学条件」；Merrill 成分显示理论的内容维（事实/概念/程序/原理）× 表现维（记忆/运用/发现），本仓既有 `kp.types` 与之重合故直接复用；Shulman 的 PCK 与 Ball 等的 MKT 作为「学科细则该写什么」的框架。掌握深度标尺取 SOLO 五级（Biggs & Collis 1982）作验收、DOK 四级（Webb 1997）作题难、Bloom 知识维度（Anderson & Krathwohl 2001）作 KP 分型。学科侧证据：Hake 1998 交互式参与归一化增益；FCI 与 TUG-K 类力学/图像误区；McDermott 组电学误区；Johnstone 三重表征与 Nurrenbern–Pickering 概念题/算法题分离；CCI 大样本基线；Vision & Change 五概念与 CINS 自然选择误区；CCSS-M 八条数学实践；Singapore CPA 与 bar model；van Hiele 五水平；APOS/procept；van Zeeland & Schmitt 词汇覆盖阈值；Norris & Ortega 与 Spada & Tomita 显式语法教学；Lyster & Ranta 纠错反馈类型；NRP 五支柱与 Simple View of Reading；SRSD 写作策略教学；PISA 2018 阅读过程框架；BRACElet 与 PRIMM/Parsons/子目标标注；Wineburg 史料三启发式；请求权基础检索；illness scripts 与去偏清单的负面 RCT；Fitts & Posner 动作技能三阶段、Macnamara 2014 刻意练习分域解释力、Wulf 外部注意焦点。蓝军侧：学习风格、左右脑、一万小时、Bloom 2-sigma、三线索法、学习金字塔等均经核查后**不写入正文**。完整逐条来源、证据分级（A/B/C）、「明确无法核实」与「不采纳清单」自 v9.16.3 起并入本文件「v9.5.0 分科逐条证据」节与「不采纳与排除总账」「引用黑名单」两节；计划-交付比对与无损失台账为当版过程记录，随维护侧档案库于 v9.16.3 移除。**考试结构（分值、题型、时长、合格线）自本版起不写入细则**——每次开课按官方大纲与近 3–5 年真题现查，结果落盘到该任务的课程体系与备料台账。

**v9.7.0 呈现与排版系统的证据来源（2026-10-30）**：排版/可读性部分为思想层参考，未复制任何正文/模板：Butterick《Practical Typography》key rules（行长、行距、少强调）；WCAG 2.2 1.4.8（CJK 40 字符/行、非两端对齐、1.5 行距、200% 缩放）；W3C《Requirements for Chinese Text Layout》（clreq：中文 17–40 字、最长 48）；GB/T 15834-2011《标点符号用法》、GB/T 15835-2011《出版物上数字用法》、GB 3100-3102《量和单位》；Hartley & Trueman 1983 与 Waller 1982 的「标题作为 access structure」及 Lorch & Lorch 1996 的反向边界。教学设计侧：Rosenshine 2012 十条（小步、示范、检查理解、独立练习）、Sweller & Cooper 1985 工作样例、Kestin et al. 2025 AI 家教 RCT；流利度边界取 Bjork & Bjork 2011，难读字体取 Meyer et al. 2015、Rummer et al. 2016 复制失败与 Xie et al. 2018 元分析争议（Kühl 2020）。产品与社区侧仅作设计参考、不作实验证据：OpenStax 教材结构（章首目标、Be Prepared、worked example + Try It、Key Terms/Equations、Section Summary、Review Exercises、Answer Key）、Khanmigo（不直接给答案/逐步提示）、Math Academy（小步/掌握/间隔复习）、OpenAI Study Mode（分节 + quick check）、Duolingo（bite-size）、Wikipedia《Signs of AI writing》与 HN/Reddit 对 AI 腔的批评、ClawHub/OpenClaw 的 skill 打包方式、Mr. Ranedeer AI Tutor 的可配置教学参数（仅参考「显式输出契约」；学习风格/emoji 开关不采纳）。完整逐条来源、证据分级（A=实验/元分析/标准；B=方向支持；C=产品/社区/设计决策）、不采纳清单与未核实项自 v9.16.3 起并入本文件「v9.7.0 排版逐条证据」节与总账、黑名单两节。

**v9.4.0 分科逐条证据（自 docs/research/subjects-v9.4-evidence.md 于 v9.16.3 并入，2026-10-29 调研；维护侧档案，机检不可见）**：分级 A=元分析/系统综述/预注册 RCT、B=权威教材/领域共识/一手产品文档、C=产品实践/专家经验；仅录上方摘要段未覆盖的增量条目，不采纳与待核实项见下方总账与黑名单。

| 条目 | 证据与来源 | 强度 |
|---|---|---|
| Dunlosky 2013 十种学习技术三档分级 | practice testing、distributed practice=high；elaborative interrogation、self-explanation、interleaving=moderate；summarization、highlighting、keyword mnemonic、imagery、rereading=low（[PSPI](https://doi.org/10.1177/1529100612453266)） | A |
| 交错练习数值（Rohrer 组） | Rohrer, Dedrick & Stershic 2015：d=0.42 即时 / 0.79 延迟（74% vs 42%）；Rohrer et al. 2020 预注册课堂整群 RCT：54 班 700+ 人，61% vs 38%，d=0.83，15 名教师全员正向 | A |
| Math Academy 诊断与「层叠」 | 自适应诊断约 30–45 分钟定位 knowledge frontier；「层叠」=新知回固旧知（[官方 pedagogy](https://www.mathacademy.com/pedagogy)） | B |
| ALEKS/KST 机制细节 | 每题选似然 ≈0.5 的条目二分状态空间；300–600 条目课程；周期性 progress assessment 兼作检索练习并强制交错；KST 奠基 Doignon & Falmagne 2020（[全文](https://escholarship.org/uc/item/94b9x5sw)） | B |
| Khanmigo 边界补充 | 「friction by design」；对照实验学习增益与对照组差异不显著（Shetye et al. 2024，转引）；对赶时间学员有挫败感——以姿态 A/B/C 切换、「二次答错兜底」「缺事实直接给」缓解 | C |
| 松鼠AI Source Tracing Model | 沿前置链找错因根（纳米拆分与 MCM 之外的第三件，[1EdTech 项目书](https://www.1edtech.org/sites/default/files/media/docs/2024/SquirrelAI.pdf)） | C |
| Duolingo HLR 数值 | h = 2^(Θ·x) 半衰期回归；上线 +12% 日活跃（Settles & Meeder, [ACL 2016](https://research.duolingo.com/papers/settles.acl16.pdf)） | B |
| Eedi 诊断题细节 | 三原则=一个正确项+三个各对应具名误区的干扰项；400 万作答数据显示同一误区跨知识点复发（如「用大数减小数」）（[Eedi Substack](https://eedi.substack.com/p/what-do-4-million-students-responses)） | B |
| prequestions 不采纳说明 | 预测试效应对后续学习有正效应（Kornell 等），但「永不先测未讲内容」是防挫败与判分污染的硬闸口：前测只发生在 S1 摸底（结果转讲授证据而非判分分母）；未逐条核验原始文献 | B→C |
| 游戏化/连击不采纳说明 | Math Academy XP≈1 分钟专注；Duolingo streak 提升留存——本技能无界面层，连击类归「失败日零施压」替代 | B/C |
| CRA 数值细节 | Ebner et al. 2025：30 项单被试研究、Tau-BC=0.997；有无障碍学员均有效 | A |
| 变式教学（数学） | 顾泠沅青浦实验传统；Marton variation theory；与 R43「一次一维」、预测轮同构；教研共识、未逐条核验原始文献 | B |
| 数学误区库明细 | Barton/Eedi 十项：等号=光标、分数分子分母各加、负数比大小看绝对值、(−8)²=−64、y·y·y=3y、9x+y−6x+y=5xy、去括号只乘第一项、解方程重复同一运算、运算顺序从左到右、乘法使数变大（[AQA GCSE 误区集](https://gcse-maths-foundation.co.uk/misconceptions)、[Sage Mathematics Assessment Probes](https://in.sagepub.com/sites/default/files/upm-assets/37758_book_item_37758.pdf)） | B |
| Polya 四步 | 《How to Solve It》：弄清问题→拟定计划→执行→回顾；对应审题圈画、解后验算与依据句模板 | B |
| SSDD 同表面不同深层 | 同一题面配不同深层问法；四收益=顺带间隔复习、防自动导航（attention attenuation）、判别对比（discriminative contrast）、防新方法过度泛化（[ssddproblems.com](https://ssddproblems.com/)、Tips for Teachers 2022） | B |
| 导数误区三源 | MAA 2018：学生几乎人人公式化求导、几乎无人会算平均变化率；Tyne 2016（UMaine）：斜率是导数根基但本身难学；Ayeh 2025：函数概念挑战、竖直线检验过度依赖（[MAA](https://maa.org/math-values/2018-11-26-the-derivative-is-not-the-slope-of-the-tangent-line/)、[Ayeh](https://doi.org/10.30935/scimath/16596)） | B |
| Vihavainen 2014 CS1 干预 | 系统综述：教学干预平均提升通过率近 1/3（[ICER 2014](https://dl.acm.org/doi/10.1145/2632320.2632349)） | A− |
| 词汇量目标数值 | Nation 2006：98% 覆盖需 8,000–9,000 词族（书面）/6,000–7,000（口语）；95%≈4,000；van Zeeland & Schmitt 2012：听力 95% 覆盖 2,000–3,000 词族可达 | A |
| 四股平衡与参与度 | Nation 2001 四 strand（意义输入/意义输出/语言聚焦/流利度）；Schmitt 2008：刻意学习与伴随学习都要有，参与度（engagement）是最大化原则（[LTR 2008](https://doi.org/10.1177/1362168808089921)） | A− |
| 归纳式教学边界 | 零基础学员缺「发现规律」的原材料——保留演绎默认（与显式教学元分析一致，反向支持） | A |
| 反驳式呈现早期元分析 | Guzzetti 1993 早期元分析同向（Schroeder & Kucera 2022、Danielson 2024 之外的前期证据） | A |
| 概念转变四条件 | Posner et al. 1982：dissatisfaction + intelligible + plausible + fruitful——讲授先让学员看见旧概念失灵，再给新概念 | B |
| cloze 原子化 | SuperMemo 20 条规则之 minimum information principle（一卡一事实），与 scheduler.py 条目粒度一致 | B |
| 双重编码 | Paivio 双重编码理论（Mayer 多媒体原则的理论前身） | B |
| 易混对对比表 | Malcolm Swan 诊断教学传统：对比表把适用条件摆出来 | C |
| 中考依标命题 | 教育部办公厅 2022 通知：严格依据课程标准命题、**取消初中学业水平考试大纲**、推进省级统一命题 | A |
| 高中课标与统编语文 | 2017 版 2020 修订：必修（全修全考）/选择性必修（升学考试范围）/选修（学而不考或学而备考）、毕业 144 学分；语文四要素/数学「三会」/英语活动观；统编语文「双线组元」+「三位一体」+整本书阅读任务群（2024 修订版名著导读改整本书阅读、书目精简 1+1） | A/B |
| 新高考细则 | 数学 19 题制：单选 8×5+多选 3×6+填空 3×5+解答 5 题 77 分（13/15/15/17/17），多选部分选对得部分分、选错 0 分，六大板块不固定顺序；英语：听力 30+阅读 37.5+七选五 12.5+完形 15+语法填空 15+应用文 15+读后续写 25（150 分/120 分钟） | A/B |
| 考试结构档案数据组（不进细则，仅作开课现查的示例记录） | 考研数学 150 分：单选 10×5+填空 6×5+解答 70，数一/数三高数约 56%、线代约 22%、概率约 22%，数二不考概率；考研英语一/二：新题型 10/15、翻译 10/15、大作文 20/15；408 统考：数据结构 45+组成原理 45+操作系统 35+网络 25；考证合格线：教资折算 120 分 70 合格、法考客观 180/300+主观 108/180、CPA 每科 60/100 五年有效、软考 45/75；陕西专升本英语 150 分无听力（精确分值待核，见黑名单） | B |
| AI 教育政策合规边界 | 《关于加强中小学人工智能教育的通知》（教基厅函〔2024〕32 号）；《中小学生成式人工智能使用指南（2025 年版）》：生成式 AI 分学段规范使用、不得以 AI 直接生成作业答案替代学习（K12 场景合规边界） | A/B |

**v9.5.0 分科逐条证据（自 docs/research/subjects-v9.5-evidence.md 于 v9.16.3 并入，2026-10-30 调研）**：分级 A=元分析/大型 RCT/官方标准原文、B=权威教材/领域共识/一手产品文档、C=产品实践/教学经验/二手转述；方法论提醒——概念清单的误区条目多为流行率诊断数据，不等于「有干预 RCT 证明可纠正」，引用时按此降级。

| 条目 | 证据与来源 | 强度 |
|---|---|---|
| Mr. Ranedeer 深度参数可核事实 | depth 1-10 在源码里只是变量名，无一级行为定义——「只给级名不给行为定义等于没分级」；仓库已 DISCONTINUED | A（源码直读） |
| LLMKT 模型自评 | 评价教学原则的人际一致性显著高于预测学生答题正确性——掌握判定只认行为证据（[arXiv:2503.06424](https://arxiv.org/html/2503.06424v1)） | A |
| Hake 1998 数值 | 62 门课/约 6000 学生：传统课归一化增益 ⟨g⟩=0.23，互动参与课 ⟨g⟩≈0.48 | A |
| Peer Instruction 活性成分 | 同伴讨论：讨论组 +21%、独自反思 +10%、分心组 +3%；Hunsu 2016 meta（53 研究）：clickers 相对同等教学法无认知收益——设备不是活性成分 | A− |
| FCI 误区条目来源 | Halloun & Hestenes 1985；Beichner TUG-K2；McDermott 组；条目示例：冲力说、匀速需恒力、v=0 即无力、摩擦力方向、graph-as-picture | A− |
| 电学误区 | 电流消耗模型、单极模型、先到先亮、电流均分、电势当单端量；McDermott 1992：35% 学过微积分的大学生电流排序错；Shipstone 1984 | B |
| 《Private Universe》 | Schneps & Sadler 纪录片研究：哈佛毕业生仍持「夏天因为离太阳近」；天文专业 21/23 仍错——季节误区跨年龄顽固 | A− |
| 多重表征互译 | Van Heuvelen 1991（文字-运动图-受力图-能量图-数学）；Rosengrant et al. 2006 | B |
| 显式解题流程 | Heller & Reif 1984：先问题描述（定系统、画图、标已知）再找方程；Huffman 1997：显式解题教学同时提高解题与概念理解 | B |
| 概念题/算法题分离复现链 | Nurrenbern & Pickering 1987（JCE 64:508）；Sawrey 1990、Nakhleh 1993 复现 | A− |
| CCI 作者与数值 | Mulford & Robinson 2002：1400+ 名修过高中化学的大一学生，22 题平均 45%，一学期后 50% | A |
| 德国化学四层诊断 | 4300–7500 人：含 H 即酸 57.65%、pH 与温度 70.59%、摩尔=摩尔质量 68.5%；另有平衡=反应停止、平衡=浓度相等、redox 必含氧、化学键非黑即白等高频误区 | B |
| 呈现顺序（化学） | Williamson et al. 2012（JCE 89(8)）：先宏观演示、再粒子动画，学生产出的粒子层解释更多 | B |
| 进化误区留存 | Nehm & Ha 2008：生物专业大二一年普通生物后，主动学习组 70%、传统组 86% 仍用至少一个误区；ACORNS 工具；Haslam & Treagust 1987 两层诊断 | A−/B |
| 生物大概念骨架 | BioCore Guide 德尔菲共识；AP Bio 4 Big Ideas（Vision & Change 五概念之外） | B |
| 概念图自画 vs 看图 | Nesbit & Adesope 2006：自己画 g≈0.82 / 看图 g≈0.37；EPR 2024 科学域 g=0.776（生物 0.671、化学 0.590、物理地学 1.040），异质性高 | A |
| bar model 出处 | Singapore Math；bar model 由 Kho Tek Hong 1983 引入（[NLB 官方条目](https://www.nlb.gov.sg/main/article-detail?cmsuuid=8751b049-8105-4437-b193-a8a306710247)） | B |
| 数学能力五股 | Kilpatrick 五股《Adding It Up》（NRC 2001）：概念理解/程序流畅/策略能力/适应性推理/生产倾向——验收不能只测程序 | B |
| APOS/procept 作者 | APOS=Dubinsky；Sfard 1991 operational vs structural；Tall & Gray procept | B |
| 词汇阈值补充 | Laufer & Ravenhorst-Kalovski 2010；van Zeeland & Schmitt 2013 复现：95% 覆盖组 7.65/10、98% 组 8.22/10 | A |
| 纠错反馈细节 | Lyster & Ranta 1997（SSLA 19:37–66）：recast 最常用但修复率最低；prompt 式（诱导、元语言提示、澄清请求、重复）修复率更高 | B |
| 广泛阅读效应 | Kim 2012 组间 d=0.62；Nakanishi 2015 前后测 0.61–1.48（虚高警示，组间更小） | A |
| 阅读模型作者 | Simple View of Reading=Gough & Tunmer 1986（解码×语言理解乘积模型）；Scarborough Reading Rope | B |
| SRSD 归属与折扣 | SRSD=Graham & Harris；机构汇总 meta>0.85 需打折（来自利益相关方页面） | A−/B |
| 中文分级阅读现状 | 无国家标准，多轨并行：中国社科院 2023；首师大「阅」标准 1–16 级；北师大边芳团队 2025 六大成果 | B |
| CEFR 官方指导学时 | 累计从零：A2≈180–200h、B1≈350–400h、B2≈500–600h、C1≈700–800h（[Cambridge 官方](https://support.cambridgeenglish.org/hc/zh-cn/articles/202838506)） | A |
| 计算思维框架 | CSTA K-12 五概念×七实践；CS2023 CKC 三维（分解/模式识别/抽象/算法的框架出处） | A |
| BRACElet 数值 | code reading ↔ code writing 相关 r≈0.56；约一半学生长期停留在低 Bloom 层级 | B/A− |
| 历史思维数值 | Wineburg 1991 出声思维：历史学家 98% 的场合先做 sourcing，高中生只有 31%；历史成绩与历史思维几乎无关 | A− |
| RLH RCT 出处 | Reisman 2012（Cognition and Instruction 30:86–112）：Reading Like a Historian 随机对照，事实知识/历史思维/阅读理解均优（效应量未取到，见黑名单） | A− |
| 学科读写 | Shanahan & Shanahan 2008 disciplinary literacy：阅读策略是学科专属的，不能只教通用阅读 | B |
| 请求权基础检索顺序 | 王泽鉴《民法思维》：契约→缔约过失→无因管理→物权→不当得利→侵权 | B |
| 金融素养感知分离 | Allgood & Walstad 2016（Economic Inquiry 54:675）：感知与实测分离 | A− |
| 原理课记忆衰退 | Frank「Economic Naturalist」：修完原理课数月后，多数学生回答简单经济问题不优于未修课者 | B |
| 心理学谬误素材 | Pashler 2008（学习风格无证据）；Dekker 2012：教师对 15 条神经迷思平均认同 49%；Kjærvik & Bushman 2024 元分析（154 研究/10189 人）：提高唤醒的「宣泄」无效甚至加重 | A |
| 地学误区组 | 深时压缩：能排对事件顺序但时间尺度严重失真（Libarkin, Kurdziel & Anderson 2007；Cheek 2010 汇总 79 项地学误区研究）；地学阈值概念：深时、空间思维、储库-流量-反馈语言（Kastens et al. 2009）；GIS 训练提升空间定位与比较思维、对空间综合分析无效（Lee & Bednarz 2009；中国高中 15 周实验） | A−/B |
| 医学教育组 | illness scripts 三元组（启用条件-故障-后果）教学有 RCT 支持（Feltovich & Barrows 1984；BMC Med Educ 2021 随机分组）；提醒偏误不足以去偏：checklist 不优于对照（Sibbald et al., JGIM，ECG 判读 RCT）；间隔重复有效（Donovan & Radosevich 1999 d=0.46；数字间隔教育 SMD=0.32、2 年后 0.34） | A−/A |
| 刻意练习分域数值 | 游戏 26%、音乐 21%、体育 18%、教育 4%、职业 <1%（Macnamara, Hambrick & Oswald 2014：88 研究/11000+ 被试） | A |
| 心理练习 | Feltz & Landers 1983 元分析 d=0.48；Driskell et al. 1994：认知任务获益大于动作任务 | A |
| 情境干扰元分析 | Sci Rep 2024（54 研究）：习得期组块好、迁移期随机好 | A |
| 外部注意焦点补充 | Chua et al. 2021 系统综述；中文元分析 ES=0.617（Wulf 研究群之外的量化补充） | A |
| 无指导发现劣于直接教学 | Alfieri et al. 2011（164 研究）：unassisted vs explicit d=−0.38；guided vs unassisted d=+0.30——有指导的发现仍略逊直接教学但显著优于无指导发现 | A |
| Productive Failure 条件 | Sinha & Kapur 2021（53 研究/166 比较）Hedges g=0.36，优势主要在迁移测验；**必须紧跟对比式讲解**，无对比讲解时优势消失甚至反转 | A |
| 撤样例判据 | expertise reversal（Kalyuga）：独立正确率 ≥70–80% 即撤指导；跨新 KP 时重置——判据是独立成功率，不是课时 | A |
| 分段前提=自控 | 中文元分析（16 篇/22 效应量）：保持 d=0.46、迁移 d=0.40；系统自动分段无效——分段原则有效的前提是学习者自控分段 | A |
| 反馈层级数值 | Hattie & Timperley 2007 d=0.79；Kluger & DeNisi 1996（607 研究）：平均 d=0.41 但 38% 的反馈降低表现，负面反馈平均 d=−0.14——self 层（夸人）几乎无效且有害 | A |

**v9.7.0 排版逐条证据（自 docs/research/v9.7.0-typography-evidence.md 于 v9.16.3 并入，2026-10-30 调研）**：

| 条目 | 证据与来源 | 强度 |
|---|---|---|
| Butterick 数值细则 | 行宽 45–90 字符；印刷 10–12pt、网页 15–25px；行距 120–145%；段距 4–10pt 或首行缩进二选一；少用加粗/斜体、不并用；除链接外不用下划线；慎用居中 | B |
| WCAG 2.2 1.4.8 细则补充 | 段距 ≥1.5×行距；200% 缩放无横向滚动；用户可自选前景/背景色（80 字符/CJK 40、非两端对齐、行距 ≥1.5 已在映射表） | A |
| Math Academy 量化参数 | 每主题小步任务：首次学习约 10 题、复习 3–5 题；默认「先示范/讲解，再做」 | C |
| OpenAI Study Mode 补充 | 支持「换个讲法/考考我」；「无限对话」不吸收（产品增长手段非教学证据） | C |
| Tufte 图形三原则 | data-ink ratio、small multiples、去装饰；图内直接标注优于图例 | B |
| 4C/ID | 整体任务与认知负荷框架（Merrill 成分显示之外的本仓参照） | B |
| CommonMark 可移植性纪律 | 不用 `> [!NOTE]` 等宿主专属 callout、复杂 HTML、脚注依赖；嵌套列表在部分宿主渲染不稳——只用引用块+加粗标签 | C |
| 渲染器差异清单 | 表格列宽、代码换行、引用块样式、`<details>` 支持不一；`<br>`/双空格换行在部分宿主被吞——规则写成「内容级、渲染器无关」 | C |

**v9.8.0 缺口导向外证调研证据（自 docs/research/v9.8.0-gap-scan-evidence.md 与 docs/review/v9.8.0-gap-candidates.md 于 v9.16.3 并入，2026-10-31 调研）**：分级沿用「已验证/方向支持/设计决策/社区经验」四档，白皮书与评论上限「社区经验」。

| 条目 | 证据与来源 | 证据级 |
|---|---|---|
| IRT 不适用于单学员场景 | 样本量门槛：1PL≈100、2PL≈250–500、3PL≥500（Jiang 2016；Cheong 2012；Sahin & Anil 2017）；贝叶斯 IRT 也需 50–100（Fox 2024）；等值/题目曝光同理不适用——本技能无跨学员题库 | 已验证 |
| CTT 阈值与引用归属修正（V1） | 区分度 D：≥0.40 很好、0.30–0.39 尚可、0.20–0.29 需修订（Ebel & Frisbie 1991 第 5 版第 11 章，原文已核）；难度 p 0.3–0.8 宜用出自 **Chae 2019**（非 E&F——原书难度表为 4 档描述、无「宜用带」主张）；单学员无经验 p/D，降维为出题前预估自检（R48） | 设计决策（惯例降维） |
| 命题指南 | Haladyna, Downing & Rodriguez 2002：31 条命题指南（双证据链）；Rodriguez 2005：选择题 3 选项效率最优（本技能多为情境题组，选项数规则不迁移） | 方向支持 |
| 教育干预效应基准（V2 实锤） | Kraft 2020（Educational Researcher 49(4)）：教育 RCT 基准 <0.05 小 / 0.05–0.20 中 / ≥0.20 大；中位数约 0.10 SD、36% 低于 0.05、作者自述「主观但不武断」——评判效应量大小的口径锚 | 方向支持 |
| Hattie 铰点批评 | Simpson 2017、Bergeron 2017：Hattie 铰点 0.40 为设计混杂产物（相关/实验设计混算、r→d 误换、样本非独立）——汇总量排序不作机制取舍依据，单项元分析为准 | 方向支持 |
| rubric/给分点清单证据 | Panadero, Jonsson, Pinedo & Fernández-Castilla 2023（Educational Psychology Review 36，校正发表偏倚）：学业成绩 g=0.45（k=21）；SMC=0.38；SRL g=0.23、自我效能 g=0.18（CI 均跨 0，**不得外推进话术**）；Jonsson & Svingby 2007（75 项）+ Panadero & Jonsson 2013（21 项）：可靠性提升条件=分析式+任务特定措辞+伴样例——R47 给分点清单依据，判分仍归 scoring.md 不造第二事实源 | 已验证（成绩）/方向支持（其余） |
| R49 断学恢复 if-then 依据 | Gollwitzer & Sheeran 2006 元分析（94 项独立检验）d=0.65、8000+ 被试，对自我调节失败（拖延）人群最有效；Bieleke & Keller 2021 同向；与 growth mindset（信念干预 d≈0.08）划界=行为计划工具非信念干预 | 方向支持 |
| 自我效能不新增话术 | Bandura 1997 四来源（mastery experience 最强）；Schlichtenhorst et al. 2026 系统综述——掌握闸口/小步/先教后练/达标反馈即 mastery experience 的结构化，硬上话术会滑向 mindset 式干预；Richardson, Abraham & Bond 2012（r≈0.59 二手待核，见黑名单）、Honicke & Broadbent 2016 为相关证据非干预效应 | 方向支持 |
| 归因再训练（V3 待核维持） | Hall & Perry 2007；Haynes, Perry, Stupnisky & Daniels 2009（系统综述**非**元分析，精确 d 付费墙未取）；Wilson, Damiani & Shelton 2002——可控行为归因（努力/策略）替代能力归因，低成就学员最强；仅备查行、不写效应量、不进闸口 | 方向支持（效应量待核） |
| 考试焦虑证据与裁决 | Ramirez & Beilock 2011、Allen 2017、Bosshard et al. 2024（Scientific Reports）：表达性书写降焦虑=小效应、成绩结果混杂；重评（reappraisal）正向 g≈0.3–0.4（二手待核）——但干预须在考场前 10 分钟执行，AI 家教触达不了、迁移断裂（不采纳裁决见总账） | 方向支持（迁移断裂） |
| andragogy 不采纳依据 | Hartree 1984、Merriam 2001 等：构念难操作化、难证伪；现有 S2 计划确认+学员选择权已是 self-direction 的结构化 | 明确不采纳 |
| 特殊需求不新增规则 | Harris et al. 2005（ERIC EJ722290）：自监控一致改善 on-task 与成绩；college ADHD 2020；Martin 2021 综述——判分四态落盘+校准画像+复习债清单即自监控的结构化；「chunking」无独立证据 | 方向支持 |
| 概念↔程序双向迭代 | Rittle-Johnson, Siegler & Alibali 2001（~2,084 引；2015「Not a One-Way Street」、2019 续）：概念知识与程序知识双向迭代发展，非严格单向先行——kp_sort 报环后「先教可独立检验的一侧、另一侧紧接着教不悬空」定向判据（R50）依据 | 方向支持 |
| KST placement 补充 | Matayoshi 2024：placement 效度评估（Cosyn et al. 2021 之外） | 方向支持 |
| concreteness fading | Fyfe, McNeil, Son & Goldstone 2014 系统综述（~611 引）：具体起步→渐隐至抽象迁移收益最好，**抽象→具体是最差顺序**；Ching & Wu 2019；Carbonneau 2013（55 研究）：具体性收益依赖教学条件——「概念先行 or 程序先行」无普适优劣（直接对比研究两侧都有效），「先教可检验侧」为设计决策+方向支持 | 方向支持/设计决策 |
| PS-I 顺序（不翻案） | He 2025（Educational Psychology Review，PS-I 顺序元分析）：问题先行概念理解更优、程序知识持平，但按先验知识调节、**新手更宜显式教学先行**（摘要级转述待核，见黑名单）——不构成对「永不先测未讲内容」的翻案压力 | 方向支持（待核） |
| 变式教学无专项元分析 | England 2020 综述、Miao et al. 2018——R43「一次一维」无独立文献锚，属设计决策 | 综述级支持 |
| 显式语法测量偏差边界 | 测试偏向显式知识——显式优势不得说成普适；复杂规则上优势最清晰（Spada & Tomita 2010）；2023 更新元分析与 Norris & Ortega 2000 同向 | 边界注记 |
| 探究式教学 | 2024 大规模元分析（431 研究，g≈0.51）与 2023 高阶思维元分析（g=0.893）正向；引导式持续优于自放式（Lazonder & Harmsen 2016 结论延续）——与「教师主导分步」路线一致 | 方向支持 |
| 史料实证证据状态 | 无权威元分析；单篇+实践文献（López-Fernández 2023，课堂干预）支持史料批判教学——history 册现有写法与证据水平相称、不拔高 | 状态标注 |
| 医学检索练习领域适用 | Deng et al. 2021 医学教育专项元分析 + Adesope, Trevisan & Sundararajan 2017（Review of Educational Research）+ 健康专业系统综述一致支持 | 方向支持 |
| 渐进增加 CI | Porter 2008：渐进增加的情境干扰有益——动作技能域「分块→交错」切换判据的补充 | 方向支持 |
| PRIMM 降级修正（E20） | PRIMM 实证以教师体验为主（Sentance & Waite），**无受控效果研究**；理论底座=样例效应+代码理解——不宜宣称 PRIMM 本身有效果证据；活性成分「读先于写」已被工作样例行覆盖 | 设计决策（借力） |
| 专家辅导员反馈时机 | D'Mello et al. 2010：学员答得含糊或没答时**不给反馈、先追问**——避免打断有效的努力（与提示阶梯/八动作精神一致）；Sottilare 等《Design Recommendations for ITS》系列为设计参考非实验 | 方向支持 |
| 学情画像外部口径 | BKT/DKT 需大规模交互数据训练（单学员不适用，与 IRT 同构）；FoLiBi（[arXiv:2309.14796](https://arxiv.org/abs/2309.14796)）；Open Learner Models（Angra 2022）：把学习者模型摊开给学员看——四态判分+信心时序（反馈前收集）+cw 优先+复习债队列=同一套指标的手工确定性版；校准差距预测后续学习（Dinsmore & Alexander 2013 口径） | 方向支持（互证） |
| 技能生态与评测参照 | ClawHub 供应链审计：31,000+ 技能中 2,371 含恶意模式；HF 官方 skills 仓 27 个按 A/B/C 安全分级；26,502 个 ClawHub 技能实证分析——「ClawHub/GitHub/HF 一律未审计、只取结构」纪律的量化佐证；外部评测基准 GuideEval（苏格拉底引导三阶段行为基准）/TutorEval 存在，仅作参照不进闸口 | 社区经验 |
| 支架 fading 补充 | Doo et al. 2020 元分析（在线学习支架大效应，356 引）+ Martin 2018/Hao 2016（fading 必要）——支架有效但必须撤（与 Kalyuga 专长反转同向，无新规则） | 方向支持 |
| 能力表扬反效应补充 | Kamins & Dweck 1999；Haimovitz & Corpus 2011（Mueller & Dweck 1998、Glerum et al. 2020 之外的证据链补充） | 方向支持 |
| rubric 细化无有害证据 | 未找到「细化有害」的直接证据；Panadero 2023 中「评估标准条数」等多数调节变量不显著——给分点按「任务特定」口径，不追求条数 | 未找到 |

（v9.8.0 的 R6 失败模式七类对照与 R7 版本核对（NBER 升格一手/WCAG 统一 2.2/GB 现行/中文行长无新裁决证据）已由下方映射表对应行收编；G4 同类技能四轴结构对照为当版工程结论，随过程档案移除。）

**v9.12.0 保持复习与可选加练证据（自 docs/research/v9.12.0-retention-evidence.md 于 v9.16.3 并入，2026-11-01 调研）**：本版本段为 CREDITS 原先整版缺位者，整节新增；仓内断点盘点与架构约束为当版工程记录，随档案移除。

| 条目 | 证据与来源 | 对应规则 |
|---|---|---|
| 检索练习元分析组 | Adesope et al. 2017（217 项研究）：检索练习优于重读，且学习与终测间隔超过 1 天时优势更大；Rowland 2014 元分析同向；Corral et al. 2025（Learning & Instruction）：保持与**迁移应用**同时优于重学、一周延迟仍成立；Chan et al. 2024（QJEP）：**外显（动笔/说出）检索优于内隐回忆**——作答式复习而非默看 | R51 热身记账 / teach-back 不省 |
| successive relearning | Rawson, Dunlosky & Sciartelli 2013（Educational Psychology Review）：跨天分布的检索会话每次做到成功提取、重复多轮——一个月延迟保持约为集中检索/重读的 2–3 倍；Rawson et al. 2018：3 个间隔会话各 1 次成功提取 > 单会话 3 次提取（约 2 倍） | R52 清除跨日化 / R54 目级化 |
| 交错与变式促迁移 | Taylor & Rohrer 2010：交错练习使测试成绩**翻倍**（与块状练习对照）；Firth 2021 系统综述（Review of Education）：交错促进辨别与归纳；Schorn et al. 2021：交错练习初始习得较差但长期保持更好——「拒绝零评判」与零施压话术依据。⚠️ 与映射表 Schorn et al. 2020（CogSci，情境干扰机制）系**两篇**，勿混引 | R55 举一反三 |
| 类比对比促远迁移 | Gentner, Loewenstein & Thompson（analogical encoding）：对**两例做结构对比**的学员在远迁移上显著优于分开学习两例；Loewenstein et al. 2003 同向；Gray & Holyoak：自我解释利近迁移、类比利远迁移——「两题并排对比+一句话总结结构」设计依据 | R55 举一反三 |
| 自主选择与动机支持 | Cullen et al. 2024（Science Advances「Choosing to learn」）：给予选择权（可退出的高挑战通道）提升投入与掌握；Zepeda et al. 2020：合意困难需配动机支持，学员常因即时表现差而回避——「可选加练+不追问+按挑战口径反馈」三件套依据 | R55 可选加练 |
| 终身式回访 | Bahrick 1979：超长期保持需分布式回访（R53 归档低频回访同向） | R53 归档回访 |

**v9.13.0 排版可读性证据（自 docs/research/v9.13.0-readability-evidence.md 于 v9.16.3 并入，2026-11-01 调研）**：考古裁决（强度全线软默认/题组场景无版面 owner）与预算守恒记录为当版工程过程，随档案移除；仅外部来源与阈值归因入账。

| 条目 | 证据与来源 | 用途 |
|---|---|---|
| CommonMark Spec §6.3（0.31.2） | 列表标记后必须跟空格/制表符——`1.（题）` 不构成列表，渲染成文字墙 | E-LAYOUT-LIST-SPACE 依据 |
| GitHub 数学表达式文档 | 行内公式定界符兼容性分歧（`$...$`/`` $`...`$ ``/```math```） | LaTeX 定界符规则 |
| Google 开发者文档风格指南 | ≥3 个相关信息才用表，保持窄而简单 | 表格规则 |
| W3C WAI 标题教程 | 标题层级连续（不跳级）为最佳实践 | E-LAYOUT-HEADING-SKIP 依据 |
| Anthropic prompt engineering | 范例（multishot）比描述更能锁定模型的格式/语气/结构 | 判分卡片 v2 模板即范例的依据 |
| Miller 1956 / Cowan 2001 | 工作记忆 7±2 / 4±1 chunks——映射表「节点 ≤7±2 设计经验值」与「列表 ≤7 项」的阈值根源 | 映射表归因补充 |
| IFEval / AutoIF / FollowBench | LLM 对**可验证约束**（数字阈值、格式标记）遵守率高且可自动回归；模糊原则（「简洁、美观」）遵守不稳定；约束叠加时遵守率显著下降——「激活硬规则 ≤15 条、其余外置 lint 后置检查」依据（[IFEval](https://arxiv.org/abs/2311.07911)、[AutoIF](https://arxiv.org/abs/2406.13542)） | 硬规则预算 |
| Abela 图表选择器 / FT Visual Vocabulary | 比较→柱状、趋势→折线、构成→饼、关系→散点 | 图表选型规则 |
| Stephen Few / Baymard | 查值用表、看模式用图；行长 50–75 CPL（中文折算 25–45 字/行）——中文行长证据组补充 | 版式基线参考 |
| 中文文案排版指北 | 盘古之白等中西文混排惯例（[sparanoid/chinese-copywriting-guidelines](https://github.com/sparanoid/chinese-copywriting-guidelines)） | 排版规则 |
| Anti-Slop / Field Guide to AI Slop | AI 排版反模式（过度加粗、滥用分隔线、八股结构）——问题在「过度且均匀使用」，不在元素本身 | 反 AI 腔 6 条 |
| NN/g 数值补充 | 扫读 20%–28%、简洁文案可用性 +58%（映射表 79% 扫描/16% 逐字读之外） | 可读性规则 |

**机制→文献→边界映射（v9.16.2 自 references/ops.md 并入；维护侧档案，不进上下文、不进任何闸口）**：本表记录本技能各机制的文献依据与边界标注，供维护者核验、溯源与后续审查锚定。使用方式（维护侧）：修改量化口径（85%、通过线、间隔参数等）前先查边界标注——标「启发式 / 推断级」的参数可按任务实际调整，标「已验证」的机制推翻需新证据；与 owner 分册冲突时，以机制定义方为准。表内 references/ 路径为维护侧导航、非机检对象；分册改名批次须同步检查本表。

| 机制（定义处） | 文献依据 | 边界标注 |
|---|---|---|
| 检索练习（测试远优于重读）（workflow S3/S4） | Roediger & Karpicke 2006：测试回忆一周后保持 56% vs 重读 42%（d=0.83），无反馈亦成立；重读抬高自信但不改善记忆；Yang et al. 2021（Psychological Bulletin）真实课堂元分析：222 项研究、48,478 名学生，g=0.499，跨学段/学科/题型稳定 | 已验证（原文数值核对）。**不自动推出「复习永不原题」**——变式优先、原题保持按目标保留（T11） |
| 间隔重复 / S-D 双参数调度（`assessment.md` + scheduler.py） | Cepeda et al. 2006/2008：分散练习普遍优于集中；最优复习间隔约为测验延迟的 5%–20% | 自研简化算法为工程取舍（零依赖），非 FSRS/SM-2 标准实现 |
| Hard 档答对仍拉长间隔（scheduler.py `max(S*factor, S+0.5)`） | Anki(SM-2 改)：Hard = 间隔 ×1.2 且必然增长；原版 SM-2 q=3 仍按 I(n)=I(n−1)×EF 放大（EF 下限 1.3）；FSRS：Hard 评分稳定度「增加或持平」 | 与主流一致；Hard base=1.4 略高于 Anki 1.2，属参数选择 |
| 难度伺服 85% 目标（`assessment.md`） | Wilson et al. 2019（Nature Communications）：训练错误率 ~15.87% 最优（仿真）；Rosenshine 课堂研究 ~82% 成功率呼应 | **启发式参数**：Wilson 为仿真研究且作者自述「85% 不是魔法数字」，不宜当普适硬参数 |
| 示范先行 / 工作样例与例题—习题交替（`teaching.md`） | Sweller 认知负荷理论：新手先学完整样例优于直接解题（Sweller & Cooper 1985 起）；例题—习题对优于纯解题（Van Gog, Kester & Paas 2011；Cheng 2014 元分析：学习效率显著更优；Chen 2023 佐证），新手期交替、随熟练度渐撤 | 已验证 |
| 样例撤除 / 高起点跳样例（`teaching.md`） | 专长反转效应：Kalyuga, Ayres, Chandler & Sweller 2003——熟练度升高后支架优势缩小乃至反转 | 已验证 |
| 分块 → 交错切换判据（`assessment.md` 题组；`workflow.md`） | Rohrer & Taylor 2007：练习期分块 89% vs 混练 60%，一周后反转 63% vs 20%（d=1.34，错因多为「算对但选错公式」）；Brunmair & Richter 2019 元分析 g=0.42 | **切换时序为推断级**：两态各有据，「先分块后切交错」的先后顺序无直接实验；动作技能域同构证据（情境干扰效应）：随机/交错练习保持与迁移更好、习得期表现更差，按任务复杂度×技能水平调节（Schorn et al. 2020；Horbacewicz 2018 系统综述；Schorn et al. 2021 系另一篇：初始习得较差但长期保持更好） |
| 目级讲授 / 按最细知识点分段（workflow「逐目推进」） | Mayer 多媒体学习分段原则（Mayer & Moreno 2003；Mayer 2009）：分段呈现优于连续整段，学习者可在段间加工；Sweller 认知负荷理论：新手工作记忆容量有限 | **分段优于整段，但目尺寸由最细知识点决定**：按「1 道题能独立检验」切目，不设固定分钟阈值；段长受材料复杂度、先验知识与交互方式调节 |
| 判定题 / 条件化出题（`assessment.md`） | 惰性知识（Whitehead 1929 inert ideas）；Gick & Holyoak 1980 类比迁移失败（仅 ~10% 自发解出）；Quilici & Mayer 1996：分类练习显著改善「选对统计检验」的能力 | 已验证（判定题训练有直接证据） |
| 延迟自评 / postdiction（`assessment.md` 判分） | Nelson & Dunlosky 1991 延迟 JOL 效应：延迟数分钟的自评远好于即时；Pierce & Smith 2001：考后自评优于事前预测；校准差距（信心−实际）预测后续学习（Dinsmore & Alexander 2013 口径） | 「隔一刻钟」为经验值（文献为「延迟数分钟」级）；**反馈后补报属回顾性（postdiction）测量、与原信心不是同一种测量**——本技能仅将**反馈前**收集的信心用于 cw/校准 |
| cw 优先修复（自信但错先复习）（`assessment.md` 调度） | Butterfield & Metcalfe 2001 起 hypercorrection：高信心错答经反馈更易被纠正 | 已验证（cw 机制的直接背书） |
| 反馈三问（任务层/过程层/自我调节层，禁自我层空泛表扬）（`teaching.md` 反馈） | Hattie & Timperley 反馈模型；能力表扬反效应：夸「聪明」→回避难题/受挫放弃/谎报成绩（Mueller & Dweck 1998 六实验；Glerum et al. 2020 复制）——「禁自我层空泛表扬」的直接依据；详述反馈 g=0.49 ＞ 给正解 0.32 ＞ 仅报对错 0.05（Van der Kleij, Feskens & Eggen 2015, RER，58 项实验）；先让学员自纠优于即时报错拦截（Mathan & Koedinger 2005） | 已验证 |
| 变式自创关（`workflow.md` 顽固清除链第③步） | 生成效应：自己生成的内容记得更牢 | 方向支持；「自创变式」具体形式为设计推断 |
| 睡眠巩固 / 考前睡眠优先（workflow S5） | Rasch & Born 2013（睡眠主动巩固）；睡眠剥夺表现降 ~1.37 SD（Pilcher & Huffcutt 1996）；MIT/Okano 2019：与成绩相关的是**学习期间**睡眠，考前一晚不相关 | 「熬夜有害」强证据；「考前一晚补觉有效」无证据 |
| S5 综合测验达标线：按目标量表（workflow S5） | Kulik, Kulik & Bangert-Drowns 1990 掌握学习元分析（108 项，+0.52 SD，纳入线 ≥70%）；现代实践综述：掌握线「不低于 80%、不高于 90%，仅安全攸关任务更高」 | 5 题卷一律 100% 无文献依据（把猜测噪声当失败）；备考型达标线取用户目标分数、按真题分值结构计分（**不再一律要求满分**），为对齐真实考试的设计决策 |
| 掌握闸口 / 判分证据强制（workflow 闸口） | Bastani et al. PNAS 2025：无限制答疑使学生练习量升、裸考成绩反降；Tennessee RCT：中位学生 2/3 练习日不主动发起对话 | 本技能「硬闸口 + 结构化判分」路线的实证背书 |
| 纯文本 markdown 学习史（progress.md 形态）（`data.md`） | Khan Academy 工程实测：结构化纯文本学习史输入使下一题独立正确率 +6.1%；**该实测中某种表示不便解析**（不同任务/系统上的表示效果未普遍化） | 形态选择的**方向支持**；**不能推出「JSON 一律无效」**——只说明「在特定系统里某种表示不便解析」 |
| 深度契约（M 机制 / C 对比）（`handout-layout.md`） | 自我解释（self-explanation）与对比案例方向；本技能以「层清单 + 三层追问 + 六问审计」落地 | **设计决策**：无单篇直接实验；不宣称「研究证明」；M 段无来源/推导时标「课程约定/未核实」 |
| 概念探测（elicit→冲突→反驳式讲授，R56）（`teaching.md`） | 反驳式文本元分析 Schroeder & Kucera 2022（Educational Psychology Review，44 项比较，g=0.41）；概念转变策略元分析 Pacaci, Ustun & Ozdemir 2024（JRST，k=218 / 18,051 人，g=1.10，干预研究常见偏高）；Peer Instruction 归一化增益 0.25→0.5–0.7（≈2 倍余，Crouch & Mazur 2001，非 RCT）；生成预测在大意外（大预测误差）时增强学习（Brod, Hasselhorn & Bunge 2018）；迷思抑制模型：迷思与科学概念共存、靠抑制压制、需反复压制（Foisy, Potvin, Riopel & Masson 2015 EEG；Potvin prevalence 模型） | **方向支持**：「学员先承诺再冲突」的独立增益缺单独分离的 RCT，故 R56 为软默认；概念转变一次不根除（接保持复习压制，R54）；选择题前测在无反馈时保持不及后测（Latimier et al. 2019, npj Science of Learning），默认开放短答 |
| S1 迷思诊断题（`workflow.md`） | 概念清单效度：Hestenes, Wells & Swackhamer 1992（FCI，The Physics Teacher）；Treagust 1988 起双层诊断题（two-tier diagnostic，IJSE） | **方向支持**：诊断工具效度证据充分，「诊断→教学增益」因果链证据间接——定位为教学素材播种（喂 R42 清单），不作闸口、不计起点判定 |
| 教学姿态三档 / 学员选择权（`teaching.md`） | ICER 2026 交叉研究（N=1,059）：仅改系统提示对四项确认指标无显著差异，建议给学员 scaffolded/direct 选择权；Oreopoulos & Low 2026（NBER w35620）：两年整群 RCT（田纳西 18 所中学），Khanmigo 配置为 coach 不给答案；分配效应每学期 1.3 个全国百分位（≈每学年 0.06–0.08 SD），与不用 AI 的练习相当；中位学员仅 1/3 练习日发消息、出错练习中仅 17% 对话，消息多为直接要答案——约束是参与度 | **方向支持**：ICER 摘要已读；NBER w35620 摘要已核；不推出「直讲优于引导」的普适结论 |
| 提示泄漏三判据 / 降梯（`teaching.md` 提示） | ICER'25 answer-aware hints：语义相似度 + 约束提示防答案泄漏；GitHub Academy A2：L1–L3 阶梯 + 可运行代码过滤 | **方向支持**：两来源均为二手/技能包自述，未逐篇核原文；本技能用三判据 + 发前自检落地 |
| 过度泛化错因（`teaching.md` 错因） | Linux.do balanced-5 的错因枚举含「过度泛化/边界」；Socratopia「无反例则无概念」 | **设计决策**：来源为社区实践帖，非实验；与现有「误解/方法选择」并列，不替代 |
| 续学回忆题（workflow 入场自检） | 检索练习（Roediger & Karpicke 2006，现版已有）；Master Teacher Phase 5 resume recall | **方向支持**：检索练习已验证；「≥3 天先 1 题」为工程阈值，非文献常数 |
| 读者版可读性：三遍路径 / 先结论 / 一段一义 / 列表-表格分工 / 标题导航（`handout-layout.md`） | NN/g 眼动研究：79% 用户扫描、16% 逐字读；F 型与层饼型扫描；ISO 24495-1:2023 简明语言四原则（相关 / 可找 / 可理解 / 可用）；WMO 教学设计指南（标题、列表、留白、短段落） | **方向支持/设计决策**：网页阅读研究不等同长时学习材料；不推出「越短越好」；必要推导优先于版面；加粗阈值以 `handout-layout.md`「字体语义」为准 |
| 多媒体学习原则：coherence / signaling / redundancy / spatial contiguity / segmenting / pre-training（`handout-layout.md` 图解语法） | Mayer 2017 综述：multimedia d=1.67、coherence d=0.70、signaling d=0.46、redundancy d=0.87、spatial contiguity d=0.79、segmenting d=0.70、pre-training d=0.46；Mayer 2005：coherence 中位 1.32、spatial contiguity 1.11、redundancy 0.69；Noetel et al. 2021 meta-meta（29 综述 / 1,189 研究 / 78,177 参与者）；Alpizar et al. 2020 signaling 元分析；Schroeder & Cenkci 2018 spatial contiguity 元分析；Sundararajan & Adesope 2020 seductive details 元分析（58 研究 / 7,500+ 学员）；Cromley & Chen 2025 元分析（92 篇 / 181 研究 / 591 效应，总体 g=0.37，受媒介、年龄、领域、时长调节） | **方向支持**：效应量异质，受先验知识与材料复杂度调节；不把某一 d 值当固定承诺；文字+图对事实/推断/迁移有较大一致效应，动画/游戏/VR 证据较弱；seductive details 平均有害，但个别情境（如缓解数学焦虑）仍有争议 |
| 概念图 / 文本结构 / 图表组织（`handout-layout.md`） | Nesbit & Adesope 2006 概念图元分析；Schroeder et al. 2018 概念图元分析 g=0.58；Krieglstein et al. 2022 概念图结构显著性降低迷失；Hebert et al. 2016 / Pyle et al. 2017 / Bogaerds-Hazenberg et al. 2020 文本结构教学元分析；Schneider et al. 2021 概念图 signaling / spatial contiguity / segmenting | **方向支持**：概念图并非一律有效；结构显著性、分组与分段比节点数量更关键；不推出「每节必画图」；一次呈现节点 ≤7±2 为设计经验值，完整概念图可更多但须分层/分组；不是实验常数 |
| 中文排版 / 屏幕阅读 / 打印（`handout-layout.md`） | W3C clreq：中文正文行长 17–40 字、横排最长 48 字；WCAG 2.2（2023-10 现行，含 2.1 相关条款）1.4.1（颜色非唯一手段）、1.4.3（4.5:1；大字 3:1）、1.4.11（图形 3:1）、1.4.8 AAA（CJK 40 字/行、行距 1.5、非两端对齐）；Zhu et al. 2021 手机中文字号/行距；Gao 2019 技术文本 76 字/行偏好；Chan et al. 2013 校对 36 字/行 + 1.5 行距；Lonsdale 2014 排版综述；Pan et al. 2020 14-point / 正极性 | **方向支持/设计决策**：行长证据冲突（17–48 vs 76），本技能取 25–40 字、上限 48，不把 76 当默认（2023 年后行长冲突无新裁决证据，Huang 2023 最接近、无裁决数值）；字号/行距受设备与年龄调节；Markdown 无法控制渲染主题，规则以「内容结构不依赖主题」为准 |
| 屏幕 vs 纸面（`handout-layout.md` 打印自检） | Delgado et al. 2018 元分析（54 研究、约 17 万参与者）：纸面理解优于屏幕，说明文/限时/长文更明显 | **方向支持**：效应不大且非所有阅读；讲义应纸面友好，不假设只在屏幕读；不推出「必须打印」 |
| 自我解释 / 闭卷自检（`handout-layout.md` 闭卷自检；You-do 首次独立成功的一句「为什么」） | Bisra et al. 2018 元分析：自我解释 g=0.55（69 效应）；Rittle-Johnson et al. 2017 数学自我解释 g=0.27；解释正误答案均促进学习（Siegler 2002） | **方向支持**：提示形式与任务类型调节；不把 g=0.55 当固定收益；低先验学员需提示支架，故 You-do 只问一句、不每题追问 |
| 讲授轮分轮呈现 / 路线先行 / 一步一停（`handout-layout.md`「对话轮呈现标记」） | Kestin et al. 2025（Scientific Reports，AI 家教 RCT：系统提示约束「简短、一次只给一步」，学习增益 0.73–1.3 SD 且用时更短）；OpenAI Study Mode（信息组织成易跟随的小节 + 小节间 quick check）；NN/g GenAI 写作研究（用户只读约 20% 文字，TLDR 先行）；AutoTutor EMT 五步帧（先抽学员答案再补讲） | **方向支持/设计决策**：单轮 250 字锚点无一手实证，属工程约定；Stanford SCALE A/B：按学员状态切换教学策略省约 3 轮且不损质量——切换，不站队 |
| 排版可读性：行长/行距/对齐/强调/标题（`handout-layout.md` 版式基线；`handout-layout.md` 字体语义；`handout-layout.md` 结构预算） | Butterick《Practical Typography》key rules（45–90 字符/行、行距 120–145%、少强调、不下划线）；WCAG 2.2 1.4.8（80 字符/CJK 40、非两端对齐、行距 ≥1.5、200% 缩放）；W3C clreq（中文 17–40 字、最长 48）；Hartley & Trueman 1983 / Waller 1982（标题作为 access structure，帮助搜索/定位）；Lorch & Lorch 1996（标题不总提升自由回忆） | **方向支持/设计决策**：网页/印刷可读性研究不能直接推出学习成绩；中文行长证据冲突，取 25–40、上限 48；版式基线是参考值，不是闸口 |
| 中文标点/数字/单位（`handout-layout.md`） | GB/T 15834-2011 标点符号用法；GB/T 15835-2011 出版物上数字用法；GB 3100-3102 量和单位；W3C clreq | **标准依据**：用于正文一致性；不把出版规范当教学效果证据；Markdown 渲染器差异处按内容级规则执行 |
| 小步/示范/检查/步骤块（`handout-layout.md` 轮型与结构预算） | Rosenshine 2012 十条（small steps, models, check understanding, independent practice）；Sweller & Cooper 1985（worked example）；Kestin et al. 2025（AI 家教 RCT） | **方向支持**：小步与检查有课堂研究支持；聊天步骤块与单轮预算是工程约定，不是固定字数 |
| 流利度/难读字体边界（`handout-layout.md` 版式基线；`handout-layout.md` 语气） | Bjork & Bjork 2011（desirable difficulties；流利度≠存储强度）；Meyer et al. 2015（disfluent fonts don't help math）；Rummer et al. 2016 复制失败；Xie et al. 2018 元分析争议（Kühl 2020 指出编码错误） | **明确不采用**：不用难读字体/低对比/Sans Forgetica 制造「努力感」；排版目标是降低无关负荷，不是制造难度 |
| 反 AI 腔（`handout-layout.md` 语气契约） | Wikipedia《Signs of AI writing》；HN/Reddit 对 AI 腔的批评；Butterick 少强调原则 | **社区/设计决策**：列 6 条可判定模式；不声称「检测 AI」；不牺牲必要推导与完整示例 |
| 产品参考：轮型/提示/反馈（`handout-layout.md` 对话呈现系统） | Khanmigo（不直接给答案/逐步提示）；Math Academy（小步/掌握/间隔复习）；OpenAI Study Mode（分节+quick check）；Duolingo（bite-size） | **产品设计参考**：不当作实验证据；不引入游戏化/学习风格 |
| 排除：bionic reading（首字母加粗提速） | Snell 2024（Acta Psychologica）：无收益；Zhao et al. 2025 RCT：不优于无修改文本 | **明确不采用**；中文场景更无依据 |
| 排除：「注意力只有 8 秒」类流行数字 | 出处为营销文章，学界不认可 | **明确不采用**：不作为任何时长/密度规则的依据 |
| 排除：渐进式总结分层加粗体系（Forte） | 个人知识管理经验（Forte Labs 博客），无教学实验 | **明确不采用**：与信号稀缺原则冲突（连续加粗降低扫读效率）；只取「结论先行」（信号规则已覆盖） |
| KP 前置链与拓扑排序（`data.md` + kp_sort.py） | 学习进阶方法论（Corcoran, Mosher & Rogat 2009：序列是假设、须按学员验证）；知识空间理论/ALEKS 大规模验证前置结构（Cosyn et al. 2021） | 方向支持：按任务自建+摸底校准=按学员验证的微缩版；不进口外部进阶路径 |
| Parsons 题（`subjects/computing-practice.md`） | Ericson 等：与手写代码学习等效、解题效率更高 | 方向支持：干扰项可降低新手效率，成人敏感度未测——干扰项克制使用 |
| CRA/CPA 序（`teaching.md`、数学族） | Peltier et al. 2020 元分析、Bouck et al. 2018 综述 | 方向支持（人群受限）：强证据集中在学习障碍人群；一般学员属设计决策，不写「研究表明」 |
| 化学三重表征（`disciplines/chemistry.md`、science-teach） | Johnstone 三层；Taber 2013 批评性综述 | 方向支持/标准参照：失败模式=跳层不搭桥；「层级阶梯」隐喻勿当刚性 |
| AI 家教弃用失败模式对照（社区经验级） | Khanmigo 低参与与停用（NBER w35620）；access≠engagement（Stanford 研究） | 社区经验：自选择偏差已知，不作教学效果证据；注记：提示阶梯须伴随正确性兜底（脚本算题），否则弃用加倍 |

**不采纳与排除总账（跨版本汇拢，v9.16.3 自维护侧档案并入）**：映射表内「排除」行与各摘要段蓝军句（学习风格/左右脑/一万小时/Bloom 2-sigma/三线索法/学习金字塔、bionic reading、注意力 8 秒、渐进式总结、难读字体）不重复列，见对应行；此处收档案侧的裁决正本。

| 不采纳项 | 理由与依据 | 重新考虑条件 | 源版本 |
|---|---|---|---|
| S3 先测后教 / prequestions | 预测试效应存在（Kornell 等）但与「永不先测未讲内容」硬闸口冲突、对话场景挫败成本高；前测仅限 S1 摸底（结果转讲授证据而非判分分母）；He 2025 PS-I 收益按先验知识调节、新手偏显式先行，不构成翻案 | 无 | v9.4/v9.8 |
| 概念图/思维导图作主复习手段 | Karpicke & Blunt 2011：检索练习胜出（连 criterial test 为画概念图时仍然）——概念图仅作「跨目串联」的可选形态 | 无 | v9.4 |
| XP/积分/连击游戏化 | **终局不采纳（用户 2026-10-31 裁决：砍掉，不留口子）**：①无 UI 载体 ②外部激励与掌握导向、失败日零施压冲突 ③备考核心激励已在目标本身；Sailer & Homner 2020 元分析（认知 g≈0.49、动机 g≈0.36、行为 g≈0.25；短干预与弱对照设计夸大效应）数据仅作事实记录——拒绝依据不是有效性问题 | 无（终局） | v9.4→v9.8 N1 |
| 强制苏格拉底问答 | 「永远不直给」对赶考学员产生摩擦；NBER w35620 一手：coach 模式低参与、拒绝辅助者大量停用——姿态三档+「缺事实直接给」出口已按证据落地 | 无（一手 RCT 与现有设计一致） | v9.4/v9.8 |
| 无限重试同一题 | 连错触发熔断与换角度重教，不采纳题库式无限刷 | 无 | v9.4 |
| Growth mindset 独立干预 | Sisk 2018 d≈0.08；Yeager 2019：仅低成就+支持性环境有小效应；与 R49 断学恢复划界=信念干预（d≈0.08）≠行为计划工具（d=0.65），构念不同 | 出现大样本预注册翻案 RCT | v9.5 |
| 固定「1/2/4/7/15 天艾宾浩斯复习表」 | 遗忘曲线是描述不是处方；有效的是间隔+检索的组合（Dunlosky 2013） | 无 | v9.5 |
| 抄写式错题本 | 抄题≠提取；必须写「我当时哪一步想岔了」并可重做（Roediger & Karpicke 2006 依据） | 无 | v9.5 |
| clickers/技术本体当活性成分 | Hunsu 2016：无认知收益；活性成分是同伴讨论 | 无 | v9.5 |
| rubber duck debugging「有实证」 | 零量化证据；有证据的是「口头化」本身 | 出现量化研究 | v9.5 |
| 考试结构与考纲数据写进细则 | 结构年年变；每次开课核验官方大纲并落盘到该任务（上方 v9.4 档案数据组仅为示例记录，不进任何 owner） | 无 | v9.5 |
| 双栏中文正文 / 宿主 callout（`> [!NOTE]`）/ 聊天嵌套列表 / 「留白越多越好」 / 「一行一个观点」拆碎推导 / 「所有内容都用表格」 | 行长过短断行频繁；可移植性差；渲染不稳、扫读差；留白是结构信号非装饰；必要推导必须连续；表格只用于并列属性对比（Butterick/WCAG/CommonMark/Mayer coherence） | 无 | v9.7 |
| 全大写/下划线/彩色字强调、装饰 emoji/图标/3D/阴影/背景纹理 | 跨渲染器不稳、coherence 原则——增加无关负荷（映射表「难读字体」明确不采用行的邻近增量） | 无 | v9.7 |
| 考试焦虑话术（表达性书写/情绪重评） | 干预须在考场前 10 分钟执行，AI 家教触达不了、迁移断裂；失败日零施压已占生态位 | 未来做「模考日/考前一晚」独立功能时 | v9.8 |
| andragogy（成人学习理论） | 二分法经验基础弱、不可证伪（Hartree 1984 起，Merriam 2001）；S2 计划确认+学员选择权已是 self-direction 的结构化 | 出现成人与儿童学习机制质性差异的可证伪实验 | v9.8 |
| BKT/DKT 知识追踪建模 | 需大规模交互数据训练；单学员场景不适用（与 IRT 同构结论） | 多学员聚合产品形态出现时 | v9.8 |
| 非母语教学法专项 | 当前用户群无此场景（判定不适用，未检索） | 出现留学预科/CLIL 类任务 | v9.8 |
| rubric 过度细化管控 | 未找到「细化有害」直接证据且条数非关键调节变量——给分点按「任务特定」口径即可 | 出现条数×认知负荷实验证据 | v9.8 |
| 归因再训练话术规则 | 效应量待核（2009 综述非元分析、精确值付费墙）；T10 错因分类已覆盖功能面——仅备查行 | 出现可靠元分析合并值时升级备查行措辞（仍不进闸口） | v9.8 |
| 学习风格匹配 / 难读字体 / 注意力 8 秒 / 长讲义高密度 / 纯提问式辅导 | 既有拒绝（Pashler 2008；Sans Forgetica 复制失败；营销数字；v9.7 排版证据；NBER 一手）在 2026-10-31 全部反面检索中无翻案信号——详见映射表「排除」行 | 大样本预注册翻案 RCT | v9.8 复核维持 |
| 结构性拒绝（流程与工程） | 考纲数据进细则、不采纳清单进运行时正文、CSS/JS/pandoc 渲染脚本、新增教学阶段/闸口/progress 字段、setup-guide 空壳——均随各版机检与架构裁决维持 | 无 | v9.4–v9.8 |

**引用黑名单（明确无法核实，禁止再引；2026-10-30/31 两轮核查，v9.16.3 自维护侧档案并入）**：

1. **「Lasry 2014 PI 元分析」**：不存在；可核实的是 Lasry 2008/2016 与 Hunsu 2016、Chien 2016 两个 clicker meta。
2. **「Renkl 的 worked example 元分析」**：不存在（Renkl 未做过该主题 meta）。
3. **「TCCI（Thermodynamic & Chemical Kinetics Concept Inventory）」**：三轮检索未命中。
4. **「MeDiSA」**：未命中；相近工具为 GCA、CDCI、Genetic Drift Inventory。
5. **「Deng 2019 / Tariq 2023 医学间隔重复元分析」**：未命中；改用 Donovan & Radosevich 1999 与数字间隔教育 SMD=0.32（注：Deng et al. **2021** 存在，勿与 2019 混引）。
6. **「Doja 2014 PBL meta」**：未找到；可用 Dochy 2003、Gijbels 2005。
7. **Follow Through（Stebbins 1977）具体效应量**：仅能确认「DI 为 9 模型中全维度最优」。
8. **Modeling Instruction 归一化增益数值**：方法与文献链可核实，数字未取到。
9. **Reisman RLH 效应量**：RCT 存在与正结论可核实，数值未取到。
10. **Chua et al. 2021 确切 g/d**：结论确认，数值未取到（替代：中文元分析 ES=0.617）。
11. **JushBJJ/AI-Tutor**：仓库不存在（README 404）。
12. **CEFR 各级官方词汇量 / CSE↔CEFR 官方对表 / JLPT 各级词汇量**：均无官方发布，市面数字皆为第三方估值（CEFR 官方**指导学时**存在，见 v9.5.0 证据节）。
13. **Lexile / F&P / AR 官方换算表**：不存在，一切换算表为近似。
14. **Betty Edwards《用右脑绘画》对照实证**：未找到；其「右脑模式」机制主张与神经迷思文献冲突。
15. **「91.3% 家长辅导作业情绪失控」等流传数字**：多站互引但无原始调查，不采信。
16. **v9.4.0 遗留待核实 5 项（写入技能前必须核对，不得凭记忆补数）**：陕西专升本英语单选/阅读精确分值、陕西高数考纲结构（官方原文为图片）、高中学业质量水平分级数、数二精确占比、CPA 各年题量。
17. **v9.8.0 待核标注**：Richardson et al. 2012 r≈0.59（二手转述）、归因再训练精确 d（Haynes 2009 系统综述非元分析、付费墙）、He 2025（摘要级转述）、Gollwitzer & Sheeran d=0.65 与 Richardson r 同批来自检索摘要（方向支持级引用）。
18. **v9.7.0 未核实/未执行**：未逐篇核对全部论文精确效应量与页码；打印/PDF 未在 pandoc/xelatex/浏览器/Prince 实测；未跑真人冷读与延迟迁移；未验证所有渲染器对 `<details>`/表格对齐/引用块的支持。

**口径注记（E32）**：easedup/educator-skills、liulifeng8918/socratic-dialogue-skill、GarethManning/education-agent-skills 三个同类技能仓于 2026-10-31 缺口扫描时仅作**未审计结构参照**（未安装、未执行），按既定「未审计不入借鉴归因表」口径不入上方归因表。

**版本注记（v9.17.0）**：本文件历史归因行中出现的 `handout-layout.md` 等版式册路径，是当时维护侧的归因位置；该册已于 v9.17.0 退役，不再运行时加载。历史行按「不改写历史」惯例保留。

**许可**：本技能以 **MIT 许可证**发布（完整文本见包内 `LICENSE` 文件），版权归「王责豪」所有（Copyright © 2026），允许任何人免费使用、复制、修改与再分发，须随分发保留本声明、`LICENSE` 文件与上表来源归因。上表 16 个外部仓库来源均为思想层语义借鉴、未复制任何代码/正文/模板；其中 4 个上游未声明许可证或无法核验（uuta/dotfiles、spaced-repetition-teaching、Clawic study、skill-tutor），本技能未使用其任何受版权保护的表达，仅参考其公开描述的机制思想；roebi/agent-skills（CC BY-NC-SA 4.0）同样仅思想层参考、零复制，与本技能的 MIT 许可不构成冲突。上表许可证核验日期：2026-10-22（DeepTutor 为 Apache-2.0；其余沿用 2026-10-12 的 GitHub API 与上游页面逐项核实）。
docs