# subjects/ v9.5.0 —— 证据档案

> 维护者侧档案，不进运行时加载。每条注明来源与证据强度：**A** = 元分析 / 大型 RCT / 官方标准原文；**B** = 权威教材 / 领域共识 / 一手产品文档；**C** = 产品实践 / 教学经验 / 二手转述。
> 调研日期：2026-10-30。规则正文只保留「作者 年份」式内联标注，完整链接在此。

## 0. 本轮结构决策的依据（为什么拆三轴）

| 决策 | 证据 | 强度 | 来源 |
|---|---|---|---|
| 教学处方应**按学习结果类型**开，不按学科开 | Gagné《学习的条件》五类结果（言语信息 / 智慧技能 / 认知策略 / 动作技能 / 态度），原文主张「different internal and external conditions are necessary for each type of learning」 | B | [Conditions of Learning（Wikipedia 综述）](https://en.wikipedia.org/wiki/Conditions_of_Learning)、[EBSCO Research Starters](https://www.ebsco.com/research-starters/religion-and-philosophy/gagnes-conditions-learning) |
| 内容维 = 事实 / 概念 / 程序 / 原理；表现维 = 记忆 / 运用 / 发现 | Merrill 成分显示理论（CDT）；本仓 `kp.types` 的「记忆/概念/程序/设计」与之几乎重合，故直接复用、枚举零改动 | B | [成分显示理论（中国大百科全书）](https://www.zgbk.com/ecph/words?ID=34599&SiteID=1&Type=bkzyb)、[Concept learning（CDT 节）](https://en.wikipedia.org/wiki/Concept_learning) |
| 学科差异不能只靠通用族表达：学科专属难点在**表征系统、误区库、验收规范** | 「按目取族」把物理计算题路由到数学族会丢掉受力图 / 量纲 / 极限检验；Nurrenbern–Pickering 效应证明算法流畅可与概念缺失并存 | A− | 见 §2 物理、§3 化学 |
| 官方 skill 规范允许扁平 references + 按需加载，不支持深嵌套 | 顶层仅 `SKILL.md` / `scripts/` / `references/` / `assets/`，未规定嵌套层数；社区指南把 deeply nested references 列为反模式 | A / C | [anthropics/skills skill-creator](https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/SKILL.md) |

## 1. 跨轴：掌握深度与题目难度

| 规则 | 证据 | 强度 | 来源 |
|---|---|---|---|
| SOLO 五级（前结构 / 单点 / 多点 / 关联 / 拓展抽象）直接对「回答结构」建模，可对任何口头回答即时判级 | Biggs & Collis 1982 | B | [SOLO 五级定义](http://baike.baidu.com/item/solo/5908556) |
| DOK 四级（回忆再现 / 技能概念 / 策略思维 / 拓展思维）量的是**认知加工复杂度**，同一动词可落不同级 | Webb 1997 | B | [DOK 四级判据（转译 Webb 2002）](https://www.360doc.cn/article/0_1104734381.html) |
| Bloom 修订版的价值在**知识维度**（事实/概念/程序/反省认知）而非认知过程六级 | Anderson & Krathwohl 2001 | B | [CMU Eberly Center](http://www.cmu.edu/teaching/designteach/design/bloomsTaxonomy.html) |
| **只给级名不给行为定义等于没分级** | Mr. Ranedeer 的 depth 1-10 在源码里只是变量名，无一级行为定义；仓库已 `DISCONTINUED` | A（源码直读） | [Mr.-Ranedeer-AI-Tutor](https://github.com/JushBJJ/Mr.-Ranedeer-AI-Tutor) |
| 掌握判定只认行为证据，模型自评不可靠 | LLMKT：评价教学原则的人际一致性显著高于预测学生答题正确性 | A | [arXiv:2503.06424](https://arxiv.org/html/2503.06424v1) |
| 参与度而非可及性是 AI 家教的第一约束 | Khanmigo 两年整群 RCT（田纳西 18 校）："The binding constraint appears to be engagement" | A | [HN 讨论串（含论文 DOI）](https://news.ycombinator.com/item?id=49972419) |

## 2. 实验科学群与物理包

| 规则 | 证据 | 强度 | 来源 |
|---|---|---|---|
| 交互式参与显著优于传统讲授 | Hake 1998：62 门课 / 约 6000 学生，传统课归一化增益 ⟨g⟩=0.23，互动参与课 ⟨g⟩≈0.48 | A | [PER-Central](https://www.per-central.org/items/detail.cfm?ID=2662) |
| Peer Instruction 的**活性成分是同伴讨论**，不是设备 | 机制研究：讨论组 +21%、独自反思 +10%、分心组 +3%；Hunsu 2016 meta（53 研究）：clickers 相对同等教学法无认知收益 | A− | [PI 机制综述](https://pmc.ncbi.nlm.nih.gov/articles/PMC7145884/)、[Hake](https://www.per-central.org/items/detail.cfm?ID=2662) |
| FCI 误区条目可直接作干扰项：冲力说、匀速需恒力、作用于反作用不对称、v=0 即无力、摩擦力方向、graph-as-picture | Halloun & Hestenes 1985；Beichner TUG-K2；McDermott 组 | A− | [FCI 条目](https://www.per-central.org/items/detail.cfm?ID=2585)、[常见困难文献清单](https://www.dbserc.pitt.edu/resources/common-student-difficulties-physics) |
| 电学误区：电流消耗模型、单极模型、先到先亮、电流均分、电势当单端量 | McDermott 1992（35% 学过微积分的大学生排序错）、Shipstone 1984 | B | [电学概念形成研究综述](https://wk.baidu.com/view/09bcc015a48da0116c175f0e7cd184254a351b33) |
| 季节成因的距离说是跨年龄顽固误区 | Schneps & Sadler《Private Universe》：哈佛毕业生仍持「夏天因为离太阳近」 | A− | [Science in School](https://scienceinchool.org/article/2010/privateuniverse/)（原文域名 scienceinschool.org） |
| 多重表征互译是 PER 核心策略 | Van Heuvelen 1991（文字-运动图-受力图-能量图-数学）；Rosengrant et al. 2006 | B | [PRSTPER 物理 DBER 综述](https://link.aps.org/doi/10.1103/PhysRevSTPER.10.020119) |
| 显式解题流程：先做问题描述（定系统、画图、标已知）再找方程 | Heller & Reif 1984；Huffman 1997（显式解题教学同时提高解题与概念理解） | B | [PMC8715817](https://pmc.ncbi.nlm.nih.gov/articles/PMC8715817/) |
| 概念清单的误区条目多为**流行率诊断数据**，不等于「有干预 RCT 证明可纠正」 | 全部分析中已按此降级标注 | — | 方法论提醒 |

## 3. 化学与生物包

| 规则 | 证据 | 强度 | 来源 |
|---|---|---|---|
| 三重表征（宏观-微观-符号）是化学难学的结构性原因；数学强的学生可纯算法得分而不理解机理 | Johnstone 1982/1991 | B | [DBER 书目](https://www.nationalacademies.org/read/13362/chapter/15)、[三重表征策略](https://www.dxhx.pku.edu.cn/article/2016/1000-8438-20161009.shtml) |
| 概念题与算法题分离：能算化学计量题的学生答不对同概念粒子图题 | Nurrenbern & Pickering 1987（JCE 64:508），Sawrey 1990、Nakhleh 1993 复现 | A− | [MDPI 引文列表](https://www.mdpi.com/2227-7102/14/6/570) |
| 化学概念掌握的整体水平偏低 | CCI（Mulford & Robinson 2002）：1400+ 名修过高中化学的大一学生，22 题平均 45%，一学期后 50% | A | [ChemEd X 官方页](https://www.chemedx.org/JCEDLib/QBank/collection/CQandChP/CQs/ConceptsInventory/CCIIntro.html) |
| 高频化学误区：含 H 即酸（57.65%）、pH 与温度（70.59%）、摩尔=摩尔质量（68.5%）、平衡=反应停止、平衡=浓度相等、redox 必含氧、化学键非黑即白 | 德国 4300–7500 人四层诊断 + Schmidt 说理研究 | B | [四层诊断汇总](https://www.ebiotrade.com/newsf/2026-8/20260818000438963.htm) |
| 呈现顺序：先宏观演示、再粒子动画，学生产出的粒子层解释更多 | Williamson et al. 2012（JCE 89(8)） | B | [条目](http://m.zhangqiaokeyan.com/journal-foreign-detail/0704013883872.html) |
| 进化误区极顽固：生物专业大二学生一年大学普通生物后，主动学习组 70%、传统组 86% 仍在解释中使用至少一个误区 | Nehm & Ha 2008 | A− | [条目](https://m.zhangqiaokeyan.com/academic-journal-foreign_bioscience_thesis/020413368668.html) |
| 生物误区：个体主动进化 / 目的论、进化=进步、植物「吃」土壤、光合呼吸互逆且分时、能量循环、显性=更多、DNA/基因/染色体层级混淆 | CINS、ACORNS、Haslam & Treagust 1987 两层诊断 | A−/B | [Haslam & Treagust](https://www.academia.edu/29063971/) |
| 概念图由学生**自己画**才有效 | Nesbit & Adesope 2006（画图 g≈0.82 / 看图 g≈0.37）；EPR 2024 科学域 g=0.776（生物 0.671、化学 0.590、物理地学 1.040），异质性高 | A | [EPR 2024](https://link.springer.com/article/10.1007/s10648-024-09877-y) |
| 生物大概念骨架 | Vision & Change（AAAS 2011）五概念 + BioCore Guide 德尔菲共识；AP Bio 4 Big Ideas | B | [BER 综述](https://link.springer.com/article/10.1186/s43031-019-0017-6) |

## 4. 数学与统计群、calculus 包

| 规则 | 证据 | 强度 | 来源 |
|---|---|---|---|
| 八条数学实践（MP1–MP8）可作思维习惯检查表 | CCSS-M | A | [加州教育部转载官方原文](https://www.cde.ca.gov/be/st/ss/mathpractices.asp) |
| CPA（具体→图形→抽象）+ 条形模型作应用题中间表征 | Singapore Math；bar model 由 Kho Tek Hong 1983 引入 | B | [新加坡 NLB 官方 Model Method 条目](https://www.nlb.gov.sg/main/article-detail?cmsuuid=8751b049-8105-4437-b193-a8a306710247) |
| 数学能力是五股缠绕，验收不能只测程序 | Kilpatrick 五股（Adding It Up, NRC 2001） | B | [NAP 全文](https://nap.nationalacademies.org/catalog/10076/adding-it-up-helping-children-learn-mathematics) |
| 几何思维有水平层级，跨级教学无效 | van Hiele 五水平（视觉→分析→非形式演绎→形式演绎→严格性） | B | 领域共识 |
| 概念要经过 Action→Process→Object→Schema | APOS（Dubinsky）；Sfard operational vs structural；Tall & Gray procept | B | [Sfard 1991](https://doi.org/10.1007/BF00311053) |
| 高交互材料必须分步教，不可一句话直出题 | 元素交互性（Sweller, van Merriënboer & Paas） | A | [CLT 20 年回顾](https://link.springer.com/article/10.1007/s10648-019-09465-5) |
| 专升本/成人重学数学卡在初等代数而非高数 | 中文社区四方一致（知乎 19.8 万浏览问答、B 站、机构文、家长帖） | A（社区共识） | [知乎](https://www.zhihu.com/question/401549751) |
| 导数被几何化成「切线斜率公式」而丢掉平均/瞬时变化率理解 | MAA 2018；Tyne 2016 | B | [MAA Math Values](https://maa.org/math-values/2018-11-26-the-derivative-is-not-the-slope-of-the-tangent-line/) |

## 5. 语言群、chinese / english 包

| 规则 | 证据 | 强度 | 来源 |
|---|---|---|---|
| 显式语法教学优于隐式，效果持久且溢出到自发使用 | Norris & Ortega 2000（49 研究）；Spada & Tomita 2010（41 研究） | A | [Language Learning 2010](https://doi.org/10.1111/j.1467-9922.2010.00562.x) |
| 词汇覆盖阈值：读 95% ≈ 4000–5000 词族、98% ≈ 8000–9000；听 95% ≈ 2000–3000 | Nation 2006；Laufer & Ravenhorst-Kalovski 2010；van Zeeland & Schmitt 2013（复现：95% 组 7.65/10，98% 组 8.22/10） | A | [van Zeeland & Schmitt 2013](https://academic.oup.com/applij/article/34/4/457/199564) |
| 词汇间隔重复中到大效应，长间隔在延迟后测更优 | Kim & Webb 2022 元分析（48 实验） | A | [Language Learning 2022](https://onlinelibrary.wiley.com/doi/10.1111/lang.12479) |
| 纠错反馈：recast 最常用但修复率最低；prompt 式（诱导、元语言提示、澄清请求、重复）修复率更高 | Lyster & Ranta 1997（SSLA 19:37–66） | B | [综述](https://www.researchgate.net/publication/228657586_Corrective_Feedback_in_SLA_Classroom_Practice_and_Future_Directions) |
| 广泛阅读对语言能力有稳定正效应（前后测虚高，组间更小） | Kim 2012 组间 d=0.62；Nakanishi 2015 前后测 0.61–1.48 | A | [Cambridge Elements](https://www.cambridge.org/core/elements/extensive-reading/D9A225311DA459DECA98CCA98DC66A57) |
| 产出导向法（输出驱动、输入促成、选择性学习） | 文秋芳（Language Teaching 2016） | B | [doi](https://doi.org/10.1017/s026144481600001x) |
| 阅读理解 = 解码 × 语言理解（乘积模型），诊断先分流解码弱与理解弱 | Simple View of Reading（Gough & Tunmer 1986）；Scarborough Reading Rope | B | [Science of Reading vs Balanced Literacy](https://www.lexialearning.com/blog/the-science-of-reading-vs-balanced-literacy) |
| 结构化读写优先于三线索法：系统 phonics 有实证，三线索猜词训练的是弱读者行为 | National Reading Panel 2000 五支柱；多州立法限制 three-cueing | A | [NRP 报告](https://www.nichd.nih.gov/publications/pubs/nrp)、[Fordham 调查报告（中文转述）](https://stem.zjnu.edu.cn/2026/0603/c9134a555834/page.htm) |
| 写作策略教学（体裁策略 + 自我调节）效应量大 | SRSD（Graham & Harris）；机构汇总 meta > 0.85（需打折，来自利益相关方页面） | A−/B | [srsdonline.org/research](https://srsdonline.org/research/) |
| 阅读认知过程三层：定位信息 / 理解 / 评估与反思，另有任务管理 | PISA 2018 阅读框架 | A | [Nature HSSC 引 OECD 2019 框架](https://www.nature.com/articles/s41599-023-01886-6) |
| **中文分级阅读无国家标准**，现有多轨并行 | 中国社科院 2023；首师大「阅」标准 1–16 级；北师大边芳团队 2025 六大成果 | B | [中国社科院](https://www.cssn.cn/jyx/202303/t20230313_5602671.shtml) |
| CEFR 指导学时（累计从零）：A2≈180–200h、B1≈350–400h、B2≈500–600h、C1≈700–800h | Cambridge English 官方 | A | [Cambridge 指导学时](https://support.cambridgeenglish.org/hc/zh-cn/articles/202838506) |

## 6. 计算与技术群、computing-theory 包

| 规则 | 证据 | 强度 | 来源 |
|---|---|---|---|
| PRIMM（预测-运行-调查-修改-创造）：读先于写 | Sentance & Waite；2023 意大利中学对照：学习效果略优、胜任感显著提升 | B | [ICERI 2023](http://disi.unitn.it/~montreso/pubs/papers/2023-ICERI.pdf) |
| Parsons 问题降低外在负荷、支持支架 | Koli Calling 2025 综述（SLR，非 meta） | A− | [ACM](https://dl.acm.org/doi/10.1145/3769994.3770032) |
| 子目标标注降低退课与挂科，对挣扎学员尤其有效 | Margulieux et al. 2020 学期级对照（N=265） | A− | [IJ STEM Ed](https://link.springer.com/article/10.1186/s40594-020-00222-7) |
| 读码能力是写码能力的基础 | BRACElet：code reading ↔ code writing 相关 r≈0.56；约一半学生长期停留在低 Bloom 层级 | B/A− | [GOV.UK 计算教育研究综述](https://www.gov.uk/government/publications/research-review-series-computing) |
| 新手误区：赋值=数学等式、执行顺序=书写顺序、print=return、类型想当然、可变对象共享引用 | Qian & Lehman 2017 综述（notional machine 类误解） | A− | [ACM 综述](https://dl.acm.org/doi/pdf/10.1145/3077618) |
| 计算思维四分解：分解 / 模式识别 / 抽象 / 算法 | CSTA K-12 五概念×七实践；CS2023 的 CKC 三维 | A | [CS2023 发布稿](https://www.computer.org/press-room/new-cs2023-curriculum-guide) |
| 代码示例必须实跑 | LLM 幻觉与算术滑步为已知问题；与本仓既有「首次示范必实跑」互证 | C | — |

## 7. 人文社科群、history / law / economics-psychology 包

| 规则 | 证据 | 强度 | 来源 |
|---|---|---|---|
| 历史思维三启发式：sourcing / corroboration / contextualization | Wineburg 1991 出声思维研究：**历史学家 98% 的场合先做 sourcing，高中生只有 31%**；历史成绩与历史思维几乎无关 | A− | [历史思维综述（中译）](https://www.ebiotrade.com/NEWSF/2025-6/20250629073606057.htm) |
| 史料教学（Reading Like a Historian / DBQ）有随机对照且优于对照 | Reisman 2012（Cognition and Instruction 30:86–112）：事实知识、历史思维、阅读理解均优；效应量未取到 | A−（RCT 存在确认） | [UCL Press 系统综述](https://journals.uclpress.co.uk/herj/article/pubid/Hist_Educ_Res_J-20-9/) |
| 历史误区：presentism、史料=事实、单因果、必然论、时间线压缩、单源信任 | Wineburg；英格兰二阶概念模型 | B | 同上 |
| 学科阅读策略是学科专属的，不能只教通用阅读 | Shanahan & Shanahan 2008（disciplinary literacy） | B | [引文](https://link.springer.com/article/10.1007/s11256-021-00610-5) |
| 法学请求权基础检索顺序：契约→缔约过失→无因管理→物权→不当得利→侵权 | 王泽鉴《民法思维》 | B | 权威教材 |
| IRAC / CREAC 与 SRSD 同构（体裁策略显式教学） | 法律写作通识 + SRSD 证据外推 | C/B | 领域共识 |
| 经济：机会成本只取次优选项；财政/货币政策按决策主体归类；变化率下降≠水平下降 | 高中经济教学观察（800 份试卷分析） | C | [教学观察](https://m.renrendoc.com/paper/491635455.html) |
| 金融素养的感知与实测分离 | Allgood & Walstad 2016（Economic Inquiry 54:675） | A− | [引文](https://www.researchgate.net/publication/322240062) |
| 心理学谬误是现成的反驳式素材：学习风格、左右脑、宣泄有效 | Pashler 2008；Dekker 2012（教师对 15 条神经迷思平均认同 49%）；Kjærvik & Bushman 2024 元分析（154 研究 / 10189 人）：提高唤醒的发泄无效甚至加重 | A | [Pashler 2008](https://www.psychologicalscience.org/news/releases/learning-styles-debunked-there-is-no-evidence-supporting-auditory-and-visual-learning-psychologists-say.html) |
| 原理课的记忆衰退：修完原理课数月后，多数学生回答简单经济问题不优于未修课者 | Frank（Journal of Economic Education, Economic Naturalist） | B | [原文摘要](https://m.doc88.com/p-08147127734739.html) |

## 8. 地理、医学、艺术与技能

| 规则 | 证据 | 强度 | 来源 |
|---|---|---|---|
| 季节成因的距离说在哈佛毕业生与天文专业学生中同样流行（21/23 仍错） | Private Universe；gettingsmart 汇总 | A− | [gettingsmart](https://www.gettingsmart.com/2019/11/16/the-persistence-of-misconceptions/) |
| 深时压缩：能排对事件顺序但时间尺度严重失真 | Libarkin, Kurdziel & Anderson 2007；Cheek 2010 汇总 79 项地学误区研究 | A− | [NAP《How People Learn II》第 4 章](https://nap.nationalacademies.org/read/18687/chapter/4) |
| 地学阈值概念：深时、空间思维、储库-流量-反馈语言 | Kastens et al. 2009（Eos） | B | [中译](https://zhuanlan.zhihu.com/p/403494027) |
| GIS 训练提升空间定位与比较思维，对空间综合分析无效 | Lee & Bednarz 2009；中国高中 15 周实验 | B/C | [引文](https://dergipark.org.tr/en/pub/rigeo/issue/40887/493149) |
| illness scripts（启用条件-故障-后果三元组）是临床专家的知识形态，基于其组织教学有 RCT 支持 | Feltovich & Barrows 1984；BMC Med Educ 2021 随机分组 | A− | [BMC](https://bmcmededuc.biomedcentral.com/articles/10.1186/s12909-021-02522-0) |
| **提醒偏误不足以去偏**：去偏 checklist 不优于对照 | Sibbald et al.（JGIM）ECG 判读 RCT | A− | [条目](https://xueshu.baidu.com/usercenter/paper/show?paperid=bacbc01263b77f7680c719e8c4bcd978) |
| 间隔重复在医学教育有效 | Donovan & Radosevich 1999 元分析 d=0.46；数字间隔教育系统综述 SMD=0.32（2 年后 0.34） | A | [PMC11502984](https://pmc.ncbi.nlm.nih.gov/articles/PMC11502984/) |
| 动作技能三阶段：认知→联结→自动化 | Fitts & Posner | B | 领域共识 |
| 刻意练习解释力有限：游戏 26%、音乐 21%、体育 18%、教育 4%、职业 <1% | Macnamara, Hambrick & Oswald 2014（88 研究 / 11000+ 被试） | A | [PubMed](https://ngdc.cncb.ac.cn/openlb/publication/OLB-PM-24986855) |
| 外部注意焦点（关注动作效果）优于内部焦点（关注身体动作） | Wulf 研究群；Chua et al. 2021 系统综述；中文元分析 ES=0.617 | A | [PeerJ](https://peerj.com/articles/20012/)、[中文元分析](https://wap.cnki.net/touch/web/Journal/Article/BJTD201204019.html) |
| 心理练习有效，认知任务获益大于动作任务 | Feltz & Landers 1983 元分析 d=0.48；Driskell et al. 1994 | A | [转引](https://thesportjournal.org/article/effect-of-mental-training-on-the-performance-of-college-runner-distance-runners/) |
| 情境干扰：习得期组块好、迁移期随机好 | Sci Rep 2024 元分析（54 研究） | A | [Sci Rep](https://www.nature.com/articles/s41598-024-65753-3) |

## 9. 通用教学机制（进 content-types 与群切片）

| 规则 | 证据 | 强度 | 来源 |
|---|---|---|---|
| 无指导发现劣于直接教学；有指导的发现仍略逊于直接教学，但显著优于无指导发现 | Alfieri et al. 2011（164 研究）：unassisted vs explicit d=−0.38；guided vs unassisted d=+0.30 | A | [Semantic Scholar](https://www.semanticscholar.org/paper/66de567d0a1fc1a1da77d494757f81377e4b26cf) |
| Productive Failure 有正效应，**但必须紧跟对比式讲解** | Sinha & Kapur 2021（53 研究 / 166 比较）Hedges g=0.36，优势主要在迁移测验；无对比讲解时优势消失甚至反转 | A | [综述](https://www.mindomax.com/productive-failure) |
| 撤样例的判据是独立成功率，不是课时 | expertise reversal（Kalyuga）：独立正确率 ≥70–80% 即撤指导；跨新 KP 时重置 | A | [CLT 复制危机与新发展](https://link.springer.com/article/10.1007/s10648-023-09817-2) |
| 分段原则有效的前提是**学习者自控分段** | 中文元分析（16 篇 / 22 效应量）：保持 d=0.46、迁移 d=0.40；系统自动分段无效 | A | [元分析摘要](https://m.zhangqiaokeyan.com/academic-conference-cn_meeting-80257_thesis/020223556828.html) |
| 反馈按层级：task / process / self-regulation 有效，**self 层（夸人）几乎无效且有害** | Hattie & Timperley 2007（d=0.79）；Kluger & DeNisi 1996（607 研究，平均 d=0.41，但 38% 的反馈降低表现；负面反馈平均 d=−0.14） | A | [Frontiers 综述](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2021.720195/full) |
| 延迟 JOL 比即时 JOL 准确 | Dunlosky & Nelson 1992/1994 | B | 领域共识 |
| 预判误区清单必须先于讲授存在，三处消费（讲义④ / 干扰项 / 讲授点破） | 本仓既有 R42；Eedi 诊断题设计（一个正确项 + 三个各对应具名误区的干扰项） | B | [Eedi](https://eedi.substack.com/p/what-do-4-million-students-responses) |
| 交错练习优于分块（数学） | Rohrer 2015 / 2020（61% vs 38%，d=0.83） | A | [JEdPsych PDF](http://uweb.cas.usf.edu/~drohrer/pdfs/Rohrer_et_al_2020JEdPsych.pdf) |
| 检索练习优于精细加工 | Karpicke & Blunt 2011（Science） | A | [doi](https://doi.org/10.1126/science.1199327) |

## 10. 明确不采纳（蓝军清单）

| 不采纳项 | 理由 | 来源 |
|---|---|---|
| 学习风格匹配教学（视觉型 / 听觉型 / 动觉型） | 无合格实验支持 meshing hypothesis；且本仓改用「双编码对所有人生效」 | Pashler et al. 2008 |
| 左右脑 / Brain Gym | 神经迷思；教师认同率 >80% 但无实证 | Dekker et al. 2012 |
| 一万小时定律 | Macnamara 2014：教育域仅解释 4% 方差；Gladwell 曲解了 Ericsson 的定义 | Macnamara 2014 |
| Bloom 2-sigma 当可达目标 | 96 项辅导研究综述无一复现；现代估计 0.33–0.37 SD | [Nintil 综述中译](https://zhuanlan.zhihu.com/p/720099642) |
| 三线索法猜词作为主要解码策略 | 与 NRP 系统 phonics 证据相反；训练的是弱读者行为 | NRP 2000 |
| 学习金字塔（听讲 5% / 教别人 90%） | 无原始研究 | 领域证伪 |
| Growth mindset 作为独立干预 | Sisk 2018 d≈0.08；仅低成就 + 支持性环境有小效应 | Sisk 2018 / Yeager 2019 |
| 固定「1/2/4/7/15 天艾宾浩斯复习表」 | 遗忘曲线是描述不是处方；有效的是间隔 + 检索的组合 | Dunlosky 2013 |
| 抄写式错题本 | 抄题 ≠ 提取；必须写「我当时哪一步想岔了」并可重做 | Roediger & Karpicke 2006 |
| 把 clickers / 技术本身当活性成分 | Hunsu 2016：无认知收益；活性成分是同伴讨论 | Hunsu 2016 |
| rubber duck debugging 有实证 | 零量化证据；有证据的是「口头化」本身 | — |
| 考试结构与考纲数据写进细则 | 结构年年变；改为每次开课核验官方大纲并落盘到该任务 | 本仓 S0–S2 既有口径 |

## 11. 明确无法核实（不得写入规则）

1. **「Lasry 2014 PI 元分析」**：不存在；可核实的是 Lasry 2008 / Lasry 2016 与 Hunsu 2016、Chien 2016 两个 clicker meta。
2. **「Renkl 的 worked example 元分析」**：不存在；Renkl 未做过该主题 meta。
3. **「TCCI（Thermodynamic & Chemical Kinetics Concept Inventory）」**：三轮检索未命中。
4. **「MeDiSA」**：未命中；相近工具为 GCA、CDCI、Genetic Drift Inventory。
5. **「Deng 2019 / Tariq 2023 医学间隔重复元分析」**：未命中；改用 Donovan & Radosevich 1999 与数字间隔教育 SMD=0.32。
6. **「Doja 2014 PBL meta」**：未找到；可用 Dochy 2003、Gijbels 2005。
7. **Follow Through（Stebbins 1977）的具体效应量数值**：仅能确认「DI 为 9 模型中全维度最优」。
8. **Modeling Instruction 的归一化增益数值**：方法与文献链可核实，数字未取到。
9. **Reisman RLH 的具体效应量**：RCT 存在与正结论可核实，数值未取到。
10. **Chua et al. 2021 的确切 g/d**：结论确认，数值未取到（可替代中文元分析 ES=0.617）。
11. **JushBJJ/AI-Tutor**：仓库不存在（README 404）。
12. **CEFR 各级官方词汇量 / CSE↔CEFR 官方对表 / JLPT 各级词汇量**：均无官方发布，市面数字皆为第三方估值。
13. **Lexile / F&P / AR 之间的官方换算表**：不存在，一切换算表为近似。
14. **Betty Edwards《用右脑绘画》方法本身的对照实证**：未找到；其「右脑模式」机制主张与神经迷思文献冲突。
15. **「91.3% 家长辅导作业情绪失控」等流传数字**：多站互引但无原始调查，不采信。
