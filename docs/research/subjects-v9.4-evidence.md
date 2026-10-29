# subjects/ v9.4.0 分科教学细则——证据档案

> 本文档是 `references/subjects/` 六个文件（v9.4.0 重写）的**维护者侧证据档案**，不进运行时加载。
> 每条注明来源与证据强度：**A** = 元分析/系统综述/预注册 RCT；**B** = 权威教材/专家共识/一手产品文档；**C** = 产品实践/专家经验。
> 调研日期：2026-10-29。规则正文只保留「作者+年份」式内联标注，完整链接在此。

## 1. 跨族通则（common.md 的依据）

| 规则 | 证据 | 强度 | 来源 |
|---|---|---|---|
| 检索练习与间隔练习为高效用技术；重读/划线/摘要为低效用 | Dunlosky et al. 2013 对 10 种学习技术分级（practice testing、distributed practice = high；elaborative interrogation、self-explanation、interleaving = moderate；summarization、highlighting、keyword mnemonic、imagery、rereading = low） | A | [Improving Students' Learning With Effective Learning Techniques](https://doi.org/10.1177/1529100612453266) |
| 交错练习（混排不同类题，迫使先选方法）大幅优于分块练习 | Rohrer, Dedrick & Stershic 2015（d=0.42 即时 / 0.79 延迟，74% vs 42%）；Rohrer et al. 2020 预注册课堂整群 RCT（54 班 700+ 人，61% vs 38%，d=0.83，15 名教师全员正向） | A | [2015 JEdPsych PDF](http://uweb.cas.usf.edu/~drohrer/pdfs/Rohrer_et_al_2015JEdPsych.pdf)、[2020 JEdPsych PDF](http://uweb.cas.usf.edu/~drohrer/pdfs/Rohrer_et_al_2020JEdPsych.pdf) |
| 检索练习优于精细加工（含画概念图） | Karpicke & Blunt 2011, Science：检索组在推理题、甚至以「画概念图」为 criterial test 时仍胜出 | A | [Science 331:772](https://doi.org/10.1126/science.1199327) |
| 独立完成率 70–80% 的难度校准（难度伺服参数） | Wilson et al. 2019「八五规则」（最优错误率 ≈15.87%）；Rosenshine 2012 课堂成功率高参考线 ~80% | B | 既有 scoring.md 引用，v9.4 不变 |
| 掌握学习 + 精细前置链的有效组合（「知识边界」定位） | Math Academy《The Math Academy Way》：自适应诊断（约 30–45 分钟）定位 knowledge frontier；掌握推进；间隔重复与交错复习结合；「层叠」（新知回固旧知） | B | [how-our-ai-works](https://mathacademy.com/how-our-ai-works)、[pedagogy](https://www.mathacademy.com/pedagogy)、[The Math Academy Way PDF](https://www.justinmath.com/files/the-math-academy-way.pdf) |
| 知识空间理论式诊断：用最少题数把学员定位到知识状态 | ALEKS/KST：每题选似然 ≈0.5 的条目二分状态空间；300–600 条目课程；周期性 progress assessment 兼作检索练习并强制交错 | B | [Cosyn et al. 2021 preprint](https://jmatayoshi.github.io/publications/JMP2021_KST_ALEKS_preprint.pdf)、[Doignon & Falmagne 2020](https://escholarship.org/uc/item/94b9x5sw) |
| 苏格拉底式不直给答案的设计与边界 | Khanmigo：以提问与提示阶梯代替直给（「friction by design」）；对照实验显示学习增益但与对照组差异不显著（Shetye et al. 2024，转引）；对赶时间学员有挫败感——本技能以姿态 A/B/C 切换与「二次答错兜底」「缺事实直接给」缓解此缺陷 | C | [khanmigo.ai](https://www.khanmigo.ai)、[aicompetence 综述](https://aicompetence.org/ai-socratic-tutors) |
| 纳米级知识点拆分 + 前置追溯归因 | 松鼠AI：超纳米级知识点拆分（宣称比同行细 10 倍）、MCM（思维方式/能力/方法）模型、Source Tracing Model（沿前置链找错因根） | C | [1EdTech 项目书](https://www.1edtech.org/sites/default/files/media/docs/2024/SquirrelAI.pdf)、[AAAI-33 报道](https://www.prnewswire.com/news-releases/squirrel-ai-learning-present-at-the-33rd-aaai-conference-interpreting-the-new-development-trend-of-ai-education-300825910.html) |
| 记忆模型的工程化：半衰期回归 | Duolingo HLR（Settles & Meeder, ACL 2016）：h = 2^(Θ·x)，预测遗忘，+12% 日活跃；对话家教不训练模型，但其「按遗忘曲线排复习」与 scheduler.py 同源 | B | [ACL 2016 PDF](https://research.duolingo.com/papers/settles.acl16.pdf) |
| 诊断题设计：每个干扰项 = 一种具名误区 | Eedi/Craig Barton：诊断题三原则（一个正确项 + 三个各对应特定误区的干扰项）；400 万作答数据显示同一误区跨知识点复发（如「用大数减小数」） | B | [Barton 幻灯](https://www.lboro.ac.uk/media/media/services/lumen/Formative%20assessment%20slides.pdf)、[Eedi Substack 2025](https://eedi.substack.com/p/what-do-4-million-students-responses) |
| 预测试效应（未采纳说明） | prequestions 对后续学习有正效应（Kornell 等），但本技能「永不先测未讲内容」是防挫败与判分污染的硬闸口：前测只发生在 S1 摸底（其结果转为讲授证据而非判分分母），故不采纳 S3 前测 | B | 未逐条核验原始文献，暂列 C |
| 游戏化/连击激励（未采纳说明） | Math Academy XP≈1 分钟专注（B）；Duolingo streak 提升留存（C）。本技能无界面层，连击类机制归「失败日零施压」替代 | B/C | 同上 |

## 2. 数学类（math.md）

| 规则 | 证据 | 强度 | 来源 |
|---|---|---|---|
| CRA 序（具体→表征→抽象）大效应 | Ebner et al. 2025 元分析（30 项单被试研究，Tau-BC=0.997；有无障碍学员均有效） | A | [Sage 元分析](https://journals.sagepub.com/doi/10.1177/09388982241292299) |
| 变式教学（概念性/过程性变式） | 顾泠沅青浦实验传统；Marton variation theory；与 R43「一次一维」、预测轮同构 | B | 教研共识，未逐条核验原始文献 |
| 数学误区库 | Barton/Eedi 诊断题误区集：等号=光标、分数分子分母各加、负数比大小看绝对值、(−8)²=−64、系数指数混淆（y·y·y=3y）、合并不同类项（9x+y−6x+y=5xy）、去括号只乘第一项、解方程重复同一运算、运算顺序从左到右、乘法使数变大 | B | [AQA GCSE 误区集](https://gcse-maths-foundation.co.uk/misconceptions)、[Mathematics Assessment Probes (Sage)](https://in.sagepub.com/sites/default/files/upm-assets/37758_book_item_37758.pdf)、Eedi Substack |
| Polya 四步（弄清问题→拟定计划→执行→回顾） | 《How to Solve It》经典；对应本技能审题圈画、解后验算与依据句模板 | B | 教科书共识 |
| SSDD 同表面不同深层（同一题面配不同深层问法） | Barton 官方站与 Tips for Teachers（2022）：四收益=顺带间隔复习、防自动导航（attention attenuation）、判别对比（discriminative contrast）、防新方法过度泛化 | B | [ssddproblems.com](https://ssddproblems.com/)、[Tips for Teachers](https://tipsforteachers.co.uk/ssdd-problems/) |
| 导数误区（=切线斜率的几何化短路；平均 vs 瞬时变化率） | MAA 2018：学生几乎人人公式化求导、几乎无人会算平均变化率——把导数等同于切线斜率短路了「两联动变量的乘性变化关系」理解；Tyne 2016（UMaine）：斜率是导数根基但本身难学 | B | [MAA Math Values](https://maa.org/math-values/2018-11-26-the-derivative-is-not-the-slope-of-the-tangent-line/)、[Tyne 2016](https://digitalcommons.library.umaine.edu/etd/2510)、[Ayeh 2025 函数概念挑战（竖直线检验过度依赖）](https://doi.org/10.30935/scimath/16596) |

## 3. 编程类（programming.md）

| 规则 | 证据 | 强度 | 来源 |
|---|---|---|---|
| PRIMM（Predict-Run-Investigate-Modify-Make）：读先于写 | Sentance & Waite 提出；2023 意大利中学对照实验：学习效果略优于传统法、胜任感显著提升 | B | [ICERI 2023 实证](http://disi.unitn.it/~montreso/pubs/papers/2023-ICERI.pdf) |
| Parsons 问题（打乱代码行排序/缩进补全） | 降低外在负荷、支持支架、有效教阈值概念；与 faded worked example 同源 | A− | [Koli Calling 2025 综述](https://dl.acm.org/doi/10.1145/3769994.3770032) |
| 子目标标注（subgoal labels） | Margulieux et al. 2020 学期级对照（N=265）：随堂测验更优、退课/挂科更少、方差更低——对挣扎学员尤其有效 | A− | [IJ STEM Ed](https://link.springer.com/article/10.1186/s40594-020-00222-7) |
| 新手误区（心智模型） | Qian & Lehman 2017 综述：句法/概念/策略三层困难；notional machine 误解（赋值=数学等式、执行顺序误解、print≠return、类型误判、可变引用共享）；Vihavainen et al. 2014 系统综述：教学干预平均提升通过率近 1/3 | A− | [ACM 综述](https://dl.acm.org/doi/pdf/10.1145/3077618)、[ICER 2014](https://dl.acm.org/doi/10.1145/2632320.2632349) |
| AI 生成代码必须实跑 | LLM 幻觉与算术滑步为已知问题（Khanmigo 评测亦指出数学可靠性不保证）；与既有「首次示范必实跑」规则互证 | C | [EduGenius 评测](https://www.edugenius.app/blog/khanmigo-vs-other-ai-tutors-an-honest-comparison) |

## 4. 语言类（language.md）

| 规则 | 证据 | 强度 | 来源 |
|---|---|---|---|
| 显式语法教学优于隐式 | Norris & Ortega 2000（49 研究，显式>隐式，大效应，效果持久）；Spada & Tomita 2010（41 研究，简单与复杂特征均显式占优，且溢出到自发使用） | A | [Language Learning 2000](https://doi.org/10.1111/0023-8333.00136)、[Language Learning 2010](https://doi.org/10.1111/j.1467-9922.2010.00562.x) |
| 词汇量目标锚点 | Nation 2006：98% 覆盖需 8,000–9,000 词族（书面）/6,000–7,000（口语）；95% 覆盖 ≈4,000 词族；van Zeeland & Schmitt 2012：听力 95% 覆盖 2,000–3,000 词族可达；前 2,000–3,000 高频词族为第一优先 | A | [Nation 2006 PDF](https://www.lextutor.ca/cover/papers/nation%5F2006.pdf)、[Schmitt et al. 2015 复制倡议](https://www.cambridge.org/core/journals/language-teaching/article/how-much-vocabulary-is-needed-to-use-english-replication-of-van-zeeland-schmitt-2012-nation-2006-and-cobb-2007/1D217A56A2E0056E67802A6A8360FDDE) |
| 四股平衡（意义输入/意义输出/语言聚焦/流利度） | Nation 2001 四 strand；Schmitt 2008 综述：刻意学习与伴随学习都要有，参与度（engagement）是最大化原则 | A− | [Language Teaching Research 2008](https://doi.org/10.1177/1362168808089921) |
| 词汇间隔重复 | Kim & Webb 2022 元分析（48 实验）：间隔中到大效应；长间隔在延迟后测更优；等距与扩展间隔等效 | A | [Language Learning 2022](https://onlinelibrary.wiley.com/doi/10.1111/lang.12479) |
| 产出导向法 POA（中国语境） | 文秋芳：输出驱动、输入促成、选择性学习三假说；驱动-促成-评价三阶段教师中介；促成=在 ZPD 内从已有知识逐步搭建——与「先教后练+三阶梯+产出闸」同构 | B | [Language Teaching 2016](https://doi.org/10.1017/s026144481600001x) |
| 归纳式教学的边界 | 零基础学员缺「发现规律」的原材料（既有规则先行条款）；与显式教学元分析一致，保留演绎默认 | A（反向支持） | 同 Norris & Ortega |

## 5. 理论概念类（theory.md）

| 规则 | 证据 | 强度 | 来源 |
|---|---|---|---|
| 反驳式呈现（先明说误区→戳破→给正解） | Schroeder & Kucera 2022 元分析（44 比较，g=0.41 稳健）；Danielson et al. 2024 预注册元分析（294 效应量，一致显著优势）；Guzzetti 1993 早期元分析同向 | A | [Ed Psych Review 2022](https://doi.org/10.1007/s10648-021-09656-z)、[Educational Psychologist 2024](https://doi.org/10.1080/00461520.2024.2365628) |
| 概念转变需「不满+可理解可替代」 | Posner et al. 1982 经典条件（dissatisfaction + intelligible + plausible + fruitful）→ 讲授先让学员看见旧概念的失灵，再给新概念 | B | 经典理论，转引自上 |
| 概念清单/误区清单的建设方式 | 物理概念测试 FCI 等概念清单传统：误区条目=可判定行为，配干扰项 | B | 领域共识 |
| 法学 IRAC（争点-规则-适用-结论） | 法学院写作通识；映射既有「结论—依据—适用」与请求权基础条款 | C | 领域共识 |

## 6. 记忆密集类（memory.md）

| 规则 | 证据 | 强度 | 来源 |
|---|---|---|---|
| 复习一律检索式、重读不算复习 | Dunlosky 2013 分级（见 §1）；Karpicke & Blunt 2011 | A | 同 §1 |
| cloze 卡片原子化（一卡一事实） | SuperMemo 20 条规则之 minimum information principle；与 scheduler.py 条目粒度一致 | B | 工程共识 |
| 关键词记忆法只用于具象词、短期 | Dunlosky 2013：低效用评级——适用材料有限、保持期短；抽象内容改机制挂钩 | A | 同 §1 |
| 双编码（文字+图/时间线/流程图） | Paivio 双重编码理论、Mayer 多媒体原则（教学共识级） | B | 教科书共识 |
| 易混对同表对比 | 诊断教学传统（Malcolm Swan）：对比表把适用条件摆出来；与既有「对比辨析卡」同源 | C | 教研共识 |

## 7. 中国教材与考试语境（判档表与备考侧重）

> 本节由独立调研任务产出（2026-10-29，十个子题），关键事实均取证于官方原文（A）或主流教研转述（B）。

| 事实 | 内容 | 强度 | 来源 |
|---|---|---|---|
| 2022 义务教育课标 | 《义务教育课程方案和课程标准（2022 年版）》（教材〔2022〕2 号）：各科凝练核心素养；跨学科主题学习 ≥10% 课时；新增学业质量标准；倡导大单元与教—学—评一致性 | A | 教育部 moe.gov.cn 课标 PDF |
| 中考依标命题 | 教育部办公厅 2022 年中考命题通知：严格依据课程标准命题、**取消初中学业水平考试大纲**、推进省级统一命题 | A | moe.gov.cn/srcsite/A06/s3321/202204 |
| 高中课标结构 | 2017 年版 2020 年修订：必修（全修全考）/选择性必修（升学考试范围）/选修（学而不考或学而备考）；毕业 144 学分 | A | moe.gov.cn/srcsite/A26/s8001/202006 |
| 核心素养表述 | 语文四要素（文化自信、语言运用、思维能力、审美创造）；数学「三会」（会用数学的眼光观察/思维思考/语言表达现实世界）；英语四大（语言能力、文化意识、思维品质、学习能力）＋「学习理解→应用实践→迁移创新」活动观 | A/B | 课标原文及解读 |
| 统编语文体系 | 「双线组元」（人文主题+语文要素）＋「三位一体」（教读—自读—课外阅读）＋整本书阅读任务群；2024 修订版名著导读改整本书阅读、书目精简为 1+1 | A/B | 教育部教材发布会实录、人教社修订说明 |
| 数学内容四领域 | 数与代数、图形与几何、统计与概率、综合与实践；2022 版结构化整合（负数/方程/反比例移初中） | A/B | 课标原文 |
| 新高考数学 19 题制 | 2024 起：单选 8×5＋多选 3×6＋填空 3×5＋解答 5 题 77 分（13/15/15/17/17）；多选**部分选对得部分分、选错得 0 分**；六大板块不再固定顺序 | A | 2024 新课标卷真题及评分细则 |
| 新高考英语结构 | 听力 30＋阅读 37.5＋七选五 12.5＋完形 15＋语法填空 15＋应用文 15＋读后续写 25（150 分/120 分钟） | B | 多来源一致，以当年真题为准 |
| 陕西专升本英语 | 满分 150、150 分钟、**无听力**；词汇语法单选＋阅读＋完形＋英译汉＋作文；翻译 20 分、作文 20 分（单选/阅读分值说法不一，**以陕西省教育考试院大纲为准**） | B/C | 库课/杰程等，官方大纲为图片 |
| 考研数学 | 150 分：单选 10×5＋填空 6×5＋解答 6 题 70；数一/数三高数约 56%、线代约 22%、概率约 22%；数二不考概率 | B | 大纲通行口径，研招网可核 |
| 考研英语一/二差异 | 新题型英一 10/英二 15；翻译英一 5 句 10 分/英二整段 15 分；大作文英一 20（图画）/英二 15（图表） | B | 中国教育在线 2024 |
| 408 统考 | 数据结构 45＋组成原理 45＋操作系统 35＋网络 25；单选 80＋综合 70 | B | 2009 以来稳定 |
| 考证合格线 | 教资折算 120 分 70 合格（写作 50/150）；法考客观 180/300、主观 108/180；CPA 每科 60/100 五年有效；软考每科 45/75 | B | 官方公告口径 |
| 社区最大痛点 | 中英文社区一致抱怨「AI 直接给答案让孩子跳过思考」——本技能「先教后练 + 永不先测未讲 + 判分四态」结构正面回应；次痛点为无温度/不会引导（对应过程性反馈与姿态三档） | C | 知乎/微信/Reddit 讨论 |
| AI 教育政策 | 《关于加强中小学人工智能教育的通知》（教基厅函〔2024〕32 号）；《中小学生成式人工智能使用指南（2025 年版）》：生成式 AI 分学段规范使用、不得以 AI 直接生成作业答案替代学习（K12 场景合规边界） | A/B | moe.gov.cn |

- 本仓备考规则的既有落点（考纲权重分层 R38、对照源优先级、真题分值证据分级）不变；v9.4 增量：①common.md 应试技巧包补「多选部分分作答策略」与「对照源按用户类型分轨」一行；②各族「备考侧重」按上述考种结构差异化。
- 「学科族判档表」的裁决规则（语文归语言类走母语差异、理化生计算目归数学类、计算机理论归理论概念类、法条背诵归记忆密集类）为本仓原创组合，无外部文献依赖。
- 遗留待核实项（写入技能前必须核对，不得凭记忆补数）：陕西专升本英语单选/阅读精确分值、陕西高数考纲结构（原文图片）、高中学业质量水平分级数、数二精确占比、CPA 各年题量。

## 8. 明确不采纳的机制（蓝军记录）

1. **S3 先测后教 / prequestions**：预测试效应存在，但与「永不先测未讲内容」硬闸口冲突，且对话场景挫败成本高——不采纳，前测仅限 S1。
2. **概念图/思维导图作为主复习手段**：Karpicke & Blunt 2011 显示检索练习胜出——概念图仅作「跨目串联」的可选形态（既有规则），不作复习主形态。
3. **XP/积分/连击游戏化**：无界面层，且外部激励对成人自学效果不稳定——以「失败日零施压 + 过程性表扬」替代。
4. **强制苏格拉底问答**：Khanmigo 式「永远不直给」对赶考学员产生摩擦——本技能保留提示阶梯但保留姿态 B（直讲）与「缺事实直接给」出口。
5. **无限重试同一题**：连错触发熔断与换角度重教（既有规则），不采纳题库式无限刷。
