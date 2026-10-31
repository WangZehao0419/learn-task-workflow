# 文献依据

<!-- owns: 机制→文献→边界映射（只读，不进闸口）; must-not-define: 来源分级、运行时判定、闸口 -->

## 文献依据

本册是「机制 → 文献依据 → 边界标注」映射表：供核验、溯源与后续审查锚定使用。**按需加载，不参与任何闸口判定**。

### 使用方式

- 学员或审查方质疑某机制「凭什么」时，读本册对应行给依据；
- 修改量化口径（85%、通过线、间隔参数等）前，先查本册边界标注——标「启发式 / 推断级」的参数可按任务实际调整，标「已验证」的机制推翻需新证据；
- 本册不被任何脚本读取、不进任何闸口；与 owner 分册冲突时，以机制定义方为准。

### 映射表

| 机制（定义处） | 文献依据 | 边界标注 |
|---|---|---|
| 检索练习（测试远优于重读）（workflow S3/S4） | Roediger & Karpicke 2006：测试回忆一周后保持 56% vs 重读 42%（d=0.83），无反馈亦成立；重读抬高自信但不改善记忆；Yang et al. 2021（Psychological Bulletin）真实课堂元分析：222 项研究、48,478 名学生，g=0.499，跨学段/学科/题型稳定 | 已验证（原文数值核对）。**不自动推出「复习永不原题」**——变式优先、原题保持按目标保留（T11） |
| 间隔重复 / S-D 双参数调度（`assessment/scheduling.md` + scheduler.py） | Cepeda et al. 2006/2008：分散练习普遍优于集中；最优复习间隔约为测验延迟的 5%–20% | 自研简化算法为工程取舍（零依赖），非 FSRS/SM-2 标准实现 |
| Hard 档答对仍拉长间隔（scheduler.py `max(S*factor, S+0.5)`） | Anki(SM-2 改)：Hard = 间隔 ×1.2 且必然增长；原版 SM-2 q=3 仍按 I(n)=I(n−1)×EF 放大（EF 下限 1.3）；FSRS：Hard 评分稳定度「增加或持平」 | 与主流一致；Hard base=1.4 略高于 Anki 1.2，属参数选择 |
| 难度伺服 85% 目标（`assessment/scoring.md`） | Wilson et al. 2019（Nature Communications）：训练错误率 ~15.87% 最优（仿真）；Rosenshine 课堂研究 ~82% 成功率呼应 | **启发式参数**：Wilson 为仿真研究且作者自述「85% 不是魔法数字」，不宜当普适硬参数 |
| 示范先行 / 工作样例与例题—习题交替（`teaching/lesson-flow.md`） | Sweller 认知负荷理论：新手先学完整样例优于直接解题（Sweller & Cooper 1985 起）；例题—习题对优于纯解题（Van Gog, Kester & Paas 2011；Cheng 2014 元分析：学习效率显著更优；Chen 2023 佐证），新手期交替、随熟练度渐撤 | 已验证 |
| 样例撤除 / 高起点跳样例（`teaching/lesson-flow.md`） | 专长反转效应：Kalyuga, Ayres, Chandler & Sweller 2003——熟练度升高后支架优势缩小乃至反转 | 已验证 |
| 分块 → 交错切换判据（`assessment/generation.md` 题组；`workflow/s3-block.md`） | Rohrer & Taylor 2007：练习期分块 89% vs 混练 60%，一周后反转 63% vs 20%（d=1.34，错因多为「算对但选错公式」）；Brunmair & Richter 2019 元分析 g=0.42 | **切换时序为推断级**：两态各有据，「先分块后切交错」的先后顺序无直接实验；动作技能域同构证据（情境干扰效应）：随机/交错练习保持与迁移更好、习得期表现更差，按任务复杂度×技能水平调节（Schorn et al. 2020；Horbacewicz 2018 系统综述） |
| 目级讲授 / 按最细知识点分段（workflow「逐目推进」） | Mayer 多媒体学习分段原则（Mayer & Moreno 2003；Mayer 2009）：分段呈现优于连续整段，学习者可在段间加工；Sweller 认知负荷理论：新手工作记忆容量有限 | **分段优于整段，但目尺寸由最细知识点决定**：按「1 道题能独立检验」切目，不设固定分钟阈值；段长受材料复杂度、先验知识与交互方式调节 |
| 判定题 / 条件化出题（`assessment/generation.md`） | 惰性知识（Whitehead 1929 inert ideas）；Gick & Holyoak 1980 类比迁移失败（仅 ~10% 自发解出）；Quilici & Mayer 1996：分类练习显著改善「选对统计检验」的能力 | 已验证（判定题训练有直接证据） |
| 延迟自评 / postdiction（`assessment/scoring.md` 判分） | Nelson & Dunlosky 1991 延迟 JOL 效应：延迟数分钟的自评远好于即时；Pierce & Smith 2001：考后自评优于事前预测；校准差距（信心−实际）预测后续学习（Dinsmore & Alexander 2013 口径） | 「隔一刻钟」为经验值（文献为「延迟数分钟」级）；**反馈后补报属回顾性（postdiction）测量、与原信心不是同一种测量**——本技能仅将**反馈前**收集的信心用于 cw/校准 |
| cw 优先修复（自信但错先复习）（`assessment/scheduling.md` 调度） | Butterfield & Metcalfe 2001 起 hypercorrection：高信心错答经反馈更易被纠正 | 已验证（cw 机制的直接背书） |
| 反馈三问（任务层/过程层/自我调节层，禁自我层空泛表扬）（`teaching/interaction.md` 反馈） | Hattie & Timperley 反馈模型；能力表扬反效应：夸「聪明」→回避难题/受挫放弃/谎报成绩（Mueller & Dweck 1998 六实验；Glerum et al. 2020 复制）——「禁自我层空泛表扬」的直接依据 | 已验证 |
| 变式自创关（`workflow/s4-review.md` 顽固清除链第③步） | 生成效应：自己生成的内容记得更牢 | 方向支持；「自创变式」具体形式为设计推断 |
| 睡眠巩固 / 考前睡眠优先（workflow S5） | Rasch & Born 2013（睡眠主动巩固）；睡眠剥夺表现降 ~1.37 SD（Pilcher & Huffcutt 1996）；MIT/Okano 2019：与成绩相关的是**学习期间**睡眠，考前一晚不相关 | 「熬夜有害」强证据；「考前一晚补觉有效」无证据 |
| S5 综合测验达标线：按目标量表（workflow S5） | Kulik, Kulik & Bangert-Drowns 1990 掌握学习元分析（108 项，+0.52 SD，纳入线 ≥70%）；现代实践综述：掌握线「不低于 80%、不高于 90%，仅安全攸关任务更高」 | 5 题卷一律 100% 无文献依据（把猜测噪声当失败）；备考型达标线取用户目标分数、按真题分值结构计分（**不再一律要求满分**），为对齐真实考试的设计决策 |
| 掌握闸口 / 判分证据强制（workflow 闸口） | Bastani et al. PNAS 2025：无限制答疑使学生练习量升、裸考成绩反降；Tennessee RCT：中位学生 2/3 练习日不主动发起对话 | 本技能「硬闸口 + 结构化判分」路线的实证背书 |
| 纯文本 markdown 学习史（progress.md 形态）（`data/progress-schema.md`） | Khan Academy 工程实测：结构化纯文本学习史输入使下一题独立正确率 +6.1%；**该实测中某种表示不便解析**（不同任务/系统上的表示效果未普遍化） | 形态选择的**方向支持**；**不能推出「JSON 一律无效」**——只说明「在特定系统里某种表示不便解析」 |
| 深度契约（M 机制 / C 对比）（`teaching/presentation.md`） | 自我解释（self-explanation）与对比案例方向；本技能以「层清单 + 三层追问 + 六问审计」落地 | **设计决策**：无单篇直接实验；不宣称「研究证明」；M 段无来源/推导时标「课程约定/未核实」 |
| 教学姿态三档 / 学员选择权（`teaching/lesson-flow.md`） | ICER 2026 交叉研究（N=1,059）：仅改系统提示对四项确认指标无显著差异，建议给学员 scaffolded/direct 选择权；Oreopoulos & Low 2026（NBER w35620）：两年整群 RCT（田纳西 18 所中学），Khanmigo 配置为 coach 不给答案；分配效应每学期 1.3 个全国百分位（≈每学年 0.06–0.08 SD），与不用 AI 的练习相当；中位学员仅 1/3 练习日发消息、出错练习中仅 17% 对话，消息多为直接要答案——约束是参与度 | **方向支持**：ICER 摘要已读；NBER w35620 摘要已核；不推出「直讲优于引导」的普适结论 |
| 提示泄漏三判据 / 降梯（`teaching/interaction.md` 提示） | ICER'25 answer-aware hints：语义相似度 + 约束提示防答案泄漏；GitHub Academy A2：L1–L3 阶梯 + 可运行代码过滤 | **方向支持**：两来源均为二手/技能包自述，未逐篇核原文；本技能用三判据 + 发前自检落地 |
| 过度泛化错因（`teaching/interaction.md` 错因） | Linux.do balanced-5 的错因枚举含「过度泛化/边界」；Socratopia「无反例则无概念」 | **设计决策**：来源为社区实践帖，非实验；与现有「误解/方法选择」并列，不替代 |
| 续学回忆题（workflow 入场自检） | 检索练习（Roediger & Karpicke 2006，现版已有）；Master Teacher Phase 5 resume recall | **方向支持**：检索练习已验证；「≥3 天先 1 题」为工程阈值，非文献常数 |
| 读者版可读性：三遍路径 / 先结论 / 一段一义 / 列表-表格分工 / 标题导航（`handout/quality.md`） | NN/g 眼动研究：79% 用户扫描、16% 逐字读；F 型与层饼型扫描；ISO 24495-1:2023 简明语言四原则（相关 / 可找 / 可理解 / 可用）；WMO 教学设计指南（标题、列表、留白、短段落） | **方向支持/设计决策**：网页阅读研究不等同长时学习材料；不推出「越短越好」；必要推导优先于版面；加粗阈值以 `ops/typography.md`「字体语义」为准 |
| 多媒体学习原则：coherence / signaling / redundancy / spatial contiguity / segmenting / pre-training（`handout/quality.md` 图解语法） | Mayer 2017 综述：multimedia d=1.67、coherence d=0.70、signaling d=0.46、redundancy d=0.87、spatial contiguity d=0.79、segmenting d=0.70、pre-training d=0.46；Mayer 2005：coherence 中位 1.32、spatial contiguity 1.11、redundancy 0.69；Noetel et al. 2021 meta-meta（29 综述 / 1,189 研究 / 78,177 参与者）；Alpizar et al. 2020 signaling 元分析；Schroeder & Cenkci 2018 spatial contiguity 元分析；Sundararajan & Adesope 2020 seductive details 元分析（58 研究 / 7,500+ 学员）；Cromley & Chen 2025 元分析（92 篇 / 181 研究 / 591 效应，总体 g=0.37，受媒介、年龄、领域、时长调节） | **方向支持**：效应量异质，受先验知识与材料复杂度调节；不把某一 d 值当固定承诺；文字+图对事实/推断/迁移有较大一致效应，动画/游戏/VR 证据较弱；seductive details 平均有害，但个别情境（如缓解数学焦虑）仍有争议 |
| 概念图 / 文本结构 / 图表组织（`handout/quality.md`） | Nesbit & Adesope 2006 概念图元分析；Schroeder et al. 2018 概念图元分析 g=0.58；Krieglstein et al. 2022 概念图结构显著性降低迷失；Hebert et al. 2016 / Pyle et al. 2017 / Bogaerds-Hazenberg et al. 2020 文本结构教学元分析；Schneider et al. 2021 概念图 signaling / spatial contiguity / segmenting | **方向支持**：概念图并非一律有效；结构显著性、分组与分段比节点数量更关键；不推出「每节必画图」；一次呈现节点 ≤7±2 为设计经验值，完整概念图可更多但须分层/分组；不是实验常数 |
| 中文排版 / 屏幕阅读 / 打印（`handout/quality.md`） | W3C clreq：中文正文行长 17–40 字、横排最长 48 字；WCAG 2.2（2023-10 现行，含 2.1 相关条款）1.4.1（颜色非唯一手段）、1.4.3（4.5:1；大字 3:1）、1.4.11（图形 3:1）、1.4.8 AAA（CJK 40 字/行、行距 1.5、非两端对齐）；Zhu et al. 2021 手机中文字号/行距；Gao 2019 技术文本 76 字/行偏好；Chan et al. 2013 校对 36 字/行 + 1.5 行距；Lonsdale 2014 排版综述；Pan et al. 2020 14-point / 正极性 | **方向支持/设计决策**：行长证据冲突（17–48 vs 76），本技能取 25–40 字、上限 48，不把 76 当默认（2023 年后行长冲突无新裁决证据，Huang 2023 最接近、无裁决数值）；字号/行距受设备与年龄调节；Markdown 无法控制渲染主题，规则以「内容结构不依赖主题」为准 |
| 屏幕 vs 纸面（`handout/quality.md` 打印自检） | Delgado et al. 2018 元分析（54 研究、约 17 万参与者）：纸面理解优于屏幕，说明文/限时/长文更明显 | **方向支持**：效应不大且非所有阅读；讲义应纸面友好，不假设只在屏幕读；不推出「必须打印」 |
| 自我解释 / 闭卷自检（`handout/pipeline.md` 闭卷自检） | Bisra et al. 2018 元分析：自我解释 g=0.55（69 效应）；Rittle-Johnson et al. 2017 数学自我解释 g=0.27 | **方向支持**：提示形式与任务类型调节；不把 g=0.55 当固定收益 |
| 讲授轮分轮呈现 / 路线先行 / 一步一停（`teaching/presentation.md`「对话轮呈现标记」） | Kestin et al. 2025（Scientific Reports，AI 家教 RCT：系统提示约束「简短、一次只给一步」，学习增益 0.73–1.3 SD 且用时更短）；OpenAI Study Mode（信息组织成易跟随的小节 + 小节间 quick check）；NN/g GenAI 写作研究（用户只读约 20% 文字，TLDR 先行）；AutoTutor EMT 五步帧（先抽学员答案再补讲） | **方向支持/设计决策**：单轮 250 字锚点无一手实证，属工程约定；Stanford SCALE A/B：按学员状态切换教学策略省约 3 轮且不损质量——切换，不站队 |
| 排版可读性：行长/行距/对齐/强调/标题（`handout/typography.md` 版式基线；`ops/typography.md` 字体语义；`teaching/presentation.md` 结构预算） | Butterick《Practical Typography》key rules（45–90 字符/行、行距 120–145%、少强调、不下划线）；WCAG 2.2 1.4.8（80 字符/CJK 40、非两端对齐、行距 ≥1.5、200% 缩放）；W3C clreq（中文 17–40 字、最长 48）；Hartley & Trueman 1983 / Waller 1982（标题作为 access structure，帮助搜索/定位）；Lorch & Lorch 1996（标题不总提升自由回忆） | **方向支持/设计决策**：网页/印刷可读性研究不能直接推出学习成绩；中文行长证据冲突，取 25–40、上限 48；版式基线是参考值，不是闸口 |
| 中文标点/数字/单位（`ops/typography.md`） | GB/T 15834-2011 标点符号用法；GB/T 15835-2011 出版物上数字用法；GB 3100-3102 量和单位；W3C clreq | **标准依据**：用于正文一致性；不把出版规范当教学效果证据；Markdown 渲染器差异处按内容级规则执行 |
| 小步/示范/检查/步骤块（`teaching/presentation.md` 轮型与结构预算） | Rosenshine 2012 十条（small steps, models, check understanding, independent practice）；Sweller & Cooper 1985（worked example）；Kestin et al. 2025（AI 家教 RCT） | **方向支持**：小步与检查有课堂研究支持；聊天步骤块与单轮预算是工程约定，不是固定字数 |
| 流利度/难读字体边界（`handout/typography.md` 版式基线；`teaching/presentation.md` 语气） | Bjork & Bjork 2011（desirable difficulties；流利度≠存储强度）；Meyer et al. 2015（disfluent fonts don't help math）；Rummer et al. 2016 复制失败；Xie et al. 2018 元分析争议（Kühl 2020 指出编码错误） | **明确不采用**：不用难读字体/低对比/Sans Forgetica 制造「努力感」；排版目标是降低无关负荷，不是制造难度 |
| 反 AI 腔（`teaching/presentation.md` 语气契约） | Wikipedia《Signs of AI writing》；HN/Reddit 对 AI 腔的批评；Butterick 少强调原则 | **社区/设计决策**：列 6 条可判定模式；不声称「检测 AI」；不牺牲必要推导与完整示例 |
| 产品参考：轮型/提示/反馈（`teaching/presentation.md` 对话呈现系统） | Khanmigo（不直接给答案/逐步提示）；Math Academy（小步/掌握/间隔复习）；OpenAI Study Mode（分节+quick check）；Duolingo（bite-size） | **产品设计参考**：不当作实验证据；不引入游戏化/学习风格 |
| 排除：bionic reading（首字母加粗提速） | Snell 2024（Acta Psychologica）：无收益；Zhao et al. 2025 RCT：不优于无修改文本 | **明确不采用**；中文场景更无依据 |
| 排除：「注意力只有 8 秒」类流行数字 | 出处为营销文章，学界不认可 | **明确不采用**：不作为任何时长/密度规则的依据 |
| 排除：渐进式总结分层加粗体系（Forte） | 个人知识管理经验（Forte Labs 博客），无教学实验 | **明确不采用**：与信号稀缺原则冲突（连续加粗降低扫读效率）；只取「结论先行」，已并入既有规则 |
| KP 前置链与拓扑排序（`data/curriculum.md` + kp_sort.py） | 学习进阶方法论（Corcoran, Mosher & Rogat 2009：序列是假设、须按学员验证）；知识空间理论/ALEKS 大规模验证前置结构（Cosyn et al. 2021） | 方向支持：按任务自建+摸底校准=按学员验证的微缩版；不进口外部进阶路径 |
| Parsons 题（`subjects/computing-practice.md`） | Ericson 等：与手写代码学习等效、解题效率更高 | 方向支持：干扰项可降低新手效率，成人敏感度未测——干扰项克制使用 |
| CRA/CPA 序（`teaching/explanation-craft.md`、数学族） | Peltier et al. 2020 元分析、Bouck et al. 2018 综述 | 方向支持（人群受限）：强证据集中在学习障碍人群；一般学员属设计决策，不写「研究表明」 |
| 化学三重表征（`disciplines/chemistry.md`、science-teach） | Johnstone 三层；Taber 2013 批评性综述 | 方向支持/标准参照：失败模式=跳层不搭桥；「层级阶梯」隐喻勿当刚性 |
| AI 家教弃用失败模式对照（社区经验级） | Khanmigo 低参与与停用（NBER w35620）；access≠engagement（Stanford 研究） | 社区经验：自选择偏差已知，不作教学效果证据；注记：提示阶梯须伴随正确性兜底（脚本算题），否则弃用加倍 |

