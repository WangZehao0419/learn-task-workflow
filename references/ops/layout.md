# 文件结构可读性：硬禁令与基线

<!-- intent:I-FILE-LAYOUT@global -->

<!-- owns: 学员可读落盘文件（讲义、题组/判分、复习、结课产物等 .md）的版面结构下限：E 级硬禁令、W 级强制基线、结构模式选择树、机器闸口（ltw_typography 直跑）; must-not-define: 字级排印（ops/typography）、讲义版面基线（handout/typography）、聊天轮版式（teaching/presentation）、判分语义（assessment/scoring）、文件槽位 schema（assessment/exercise-files、handout/unit-schema） -->

落盘文件按本册守版面下限；对话轮不适用。阈值在 `contracts/rules.json` `constants.layout`；`python -B scripts/ltw_typography.py <文件.md>` 机器可查（见 `ops/scripts.md`）。**强度**：E = 落盘闸口（写盘前清零）；W = 同轮修复或显式后置；字级与聊天轮仍按 `ops/typography.md` 不设闸口。

## 硬禁令

- **E-LAYOUT-LIST-SPACE**：列表标记后必须空格；`1.（题）`、`-要点`、`1、`不是列表，渲染成文字墙。
- **E-LAYOUT-LONGLINE**：单行可见正文 ≤400 字（剥公式/代码）——台账巨行拆每题卡片（体例见 `assessment/exercise-files.md`）。
- **E-LAYOUT-MATH-UNPAIRED**：行内 `$` 当行成对；残片禁落盘；美元转义或写「美元」。
- **E-LAYOUT-HEADING-SKIP**：标题不跳级。
- **E-LAYOUT-TABLE-WIDE**：表格 ≤4 列且有表头分隔行，装不下拆卡片/两表/列表。

## W 级强制基线

段落 ≤4 句或 ≤150 字；连续正文每 ≤400 字一个锚点（标题/列表/表格/图/公式/引用块）；H2 节正文 ≥300 字至少一处加粗，题组/判分/答案等记录型区块豁免（上限按 `ops/typography.md` 配额）；分隔线 ≤3 条；行尾全文统一；无 `$$` 的文件用 Unicode 记号（`→`）不写 LaTeX 箭头（真公式按 `ops/formulas.md`）。

## 结构模式选择树

查值/对照 → 表格；有先后 → 有序列表；并列 → 无序列表；因果论证 → 正文；**题目/判分/复习记录 → 每题一张小卡片**（体例见 `assessment/exercise-files.md`）。
