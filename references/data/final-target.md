# 结课综合测验目标线（99-）

<!-- owns: 结课综合测验目标线（99-）与覆盖口径；must-not-define: progress 字段（progress-schema）、稳定引用与对账（reconciliation）、教学与讲义 -->

> 何时读：写结课综合测验目标线。

<!-- intent:I-FINAL-TARGET@global -->

- **结课综合测验（`99-`）额外一行**：文件头写 `目标线：a/b`（如 `目标线：4/5`，可写 `目标线：7/10` 这类非 5 题卷）。这是 `progress_check.py` 判达标线的机器可读入口：**不写按契约 `gates.final_ratio` 判**，写了按该值判（`1 ≤ a ≤ b`；`a=0` 视为非法）；**非法值 → `E-FINAL-INVALID-TARGET` 拦停，不得回退默认线**。普通节题组不需要这一行；收紧/放宽达标线却没写这行，脚本仍按契约默认拦停。
- 判分记录的字段与体例（attempt 行、正式/轻量确认、分型字段）正本见 `references/assessment/exercise-files.md`「正式/轻量确认（推进确认）」；判分四态、独立性、作废改判、幂等去重与闸口计分口径正本见 `references/assessment/grading-states.md`「判分口径」；目行 KP 编号与「1 目 = 1 KP」正本见 `references/data/curriculum.md`「课程体系文件」层级口径。
