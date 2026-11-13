# ADR-0003：调度增长律整体换成 FSRS-6

- 状态：已采纳
- 日期：2026-11-13
- 决策者：维护者
- 相关：决策 #61（八题全按推荐）；任务 #77（本 ADR 的落地票）；#76（删 `--init-shift`，本票阻塞它）；#59（旧律 R 地板缺陷，已作废）

## 背景

`scripts/scheduler.py` 原本是自研简化双参数算法：

```
成功档  factor = grade_base[档] * (1 + 0.35*(R-1)) * (1.3 - 0.1*D)
        R = clamp(elapsed/S, 0.25, 2.0)
        S' = max(S*factor, S+0.5)
失败档  S' = max(1.0, S*0.3)
新卡    S = init_s[档]；D = default_d + --init-shift
间隔    interval_days = round_half_up(S')
```

它有两个结构性缺陷，都不是调参能修的：

1. **R 的下限 0.25 是常数地板**。隔天复习（`elapsed=1`）时 R 恒被抬到 0.25 以上，good 档每次恒定 +62%，连续 12 天把 S 顶到 365 天上限；同序列 FSRS-6 只到 51 天（票 59 实测）。
2. **间隔承诺的保持率不可知**。本仓无法回答「这个 due 对应多大概率还记得」，因为没有 `desired_retention` 这个旋钮。

`docs/research/fsrs-default-params.md` 已把 FSRS-6 的 21 个默认参数、六个公式、两套参考实现的边界差异逐项核到一手来源（awesome-fsrs wiki / `py-fsrs` / `fsrs-rs`，三处交叉核对无差异）。决策票 #61 据此拍板八题，全部按推荐。

## 决策

**增长律整体换成 FSRS-6，记账法保持本仓原样。**

### 换的是什么

| 项 | 旧律 | 新律（FSRS-6） |
|---|---|---|
| 常数 | 10 项 | 21 个 `w` + `desired_retention` + `s_max` + `s_min` + `maximum_interval` + `enable_fuzzing`（`s_min=0.0001` 是票面「加」清单之外的第六键——票面只列了五个，但 fsrs-rs 的 S 下界必须进契约，否则边界变硬编码） |
| R 的语义 | `elapsed/S` 的相对时间比（夹 [0.25,2]） | 回忆概率 `(1+factor·t/S)^(-w20)`，值域 (0,1] |
| 成功档 S | 档位常数 × 线性修正 | `S·(1+e^w8·(11-D)·S^(-w9)·(e^(w10(1-R))-1)·w15^[Hard]·w16^[Easy])` |
| 失败档 S | `max(1.0, 0.3S)`，与 elapsed 无关 | `min(w11·D^(-w12)·((S+1)^w13-1)·e^(w14(1-R)), S/e^(w17·w18))` |
| 难度 D | [1,5]，0.5 粒度，档位常数漂移 | [1,10] 连续，线性阻尼 + 向 D0(4) 均值回归 |
| 间隔 | `round_half_up(S')` | `min(max(1, round_half_up(I(desired_retention, S'))), maximum_interval)` |
| 上限 | `s_max = 365` | `s_max = 36500`（S 上限）+ `maximum_interval = 365`（间隔护栏），两个常数分开 |

### 保留的是什么（不抄的部分）

- **四档判分**（again / hard / good / easy）与判分四态映射，不动。
- **`elapsed=0` 同会话特判**（决策 #61 Q6=I1）：仍只刷新召回、S/D 不变、原 due 原样返回。FSRS-6 的**同日复习公式**（`S·e^(w17(G−3+w18))·S^(−w19)`，w17–w19）**不实现**，副产品是 w19 下界分歧（py-fsrs 0 / fsrs-rs 0.01）整个消失。
- **遗忘后 S 的短期上界保留**：票面六公式块里遗忘后 S 是 `min(长期项, S/e^(w17·w18))`，这条 min 用的是 w17/w18 但**不是**同日复习公式，按票面原文保留。实测它会在 7 个组合里真的生效（如 S=1/D=1/R=0.1：长期项 1.307187 被短期项 0.951728 压住），selftest 有断言钉住。
- **不实现 Learning/Relearning 状态机与 `state`/`step` 字段**：抄完整 FSRS 收益为零（该笔记 §4.3）。
- **不做 optimizer / 参数拟合**：单学员几十条记录不构成拟合条件（该笔记 §3.4）。默认参数是 ~10k 用户的群体先验，不是这个学员的画像——文档不得声称后者。
- **纯文本 progress.md、零第三方依赖、只读不写盘、确定性**：全部不动。

### 两处主动偏离官方默认（必须在文档写明）

| 常数 | 本仓 | FSRS 默认 | 为什么偏离 |
|---|---|---|---|
| `maximum_interval` | 365 天 | 36500 天 | 产品护栏：一个学习任务排到 100 年后没有教学意义，也无法在结课后验证。S 仍可长到 36500，只是间隔封顶 365 |
| `enable_fuzzing` | `false`（且启动自检强制） | `true` | 本仓契约要求「同输入同输出」；fuzzing 一开幂等即失效。脚本在 fuzzing=true 时**拒绝启动**，不静默忽略 |

另有两条**本仓口径优先**：

- 舍入用 `int(x+0.5)`（0.5 进位），不用 FSRS 的银行家舍入。
- 间隔下限 1 天由本仓显式写进公式（FSRS 的 `max(next_interval, 1)` 同义，但本仓把它写进契约注释与断言）。

### 边界取 fsrs-rs，不取 py-fsrs

同一个 21 元数组在两套实现下会算出不同结果，必须选定一套：

| 项 | 取值 | 理由 |
|---|---|---|
| `S_MIN` | 0.0001 | fsrs-rs `simulation.rs` |
| `S_MAX` | 36500 | fsrs-rs；py-fsrs 的 `INITIAL_STABILITY_MAX=100` 只约束新卡 |
| D 值域 | [1,10] 连续 | 两套一致 |
| 参数个数 | 本仓只接受 21 | 不接受 fsrs-rs 的 17/19/34 自动补齐——补齐是 optimizer 的兼容层，本仓不跑 optimizer |

## 后果

### 换律后必须一起改的东西

- `contracts/rules.json` 的 `scheduler` 块整体替换（旧 10 项常量名全部退役）。
- `scripts/scheduler.py`：常数加载、公式、D 解析（去 `_half_step`）、`check_difficulty`、六组断言全部重写。
- `references/assessment.md` / `references/data.md` / `contracts/scripts-contract.json` / `CREDITS.md` 同步口径。
- **新卡 D 改由 D0(G) 决定**，`--init-shift` 失效；形参暂留兼容旧调用，由 #76 删除。因此 #77 必须先合、#76 后合。

### 行为跳变（对既有数据）

- **D 需要换算**：旧 [1,5] → 新 [1,10]，`D = 1 + (d-1)·9/4`。本机 `.learning/` 不存在、`git ls-files` 零命中，**本仓不写迁移脚本**；规则只服务将来的外部数据根。
- **改 `desired_retention` 会让所有既有条目下一次间隔跳变**：r=0.85 时 S=100 → 约 130 天；r=0.95 → 约 74 天。默认 0.9 不动，改前须知会这件事。
- **首间隔变了**：新卡四档从 1/2/3/6 天变成 **1/1/2/8 天**（again 档仍是 1 天而不是 0）。

### 验收锚点

决策票 #61 的十条验收全部落在 `scripts/scheduler.py --selftest` 与 `evals/verify-gate-registry.py`：elapsed=1 时 S=100 增幅 <5%、连续 12 天 daily good 后 S<100、首间隔 1/1/2/8、`elapsed=0` 仍 same_session、D=1.4969 与 1.5 都合法、间隔恒 ≥1、同输入同输出、`maximum_interval` 封顶但 S 可继续长。断言重写后做过**变异测试**：把 R 改成恒 1、把间隔改回直接取整 S、把 D 改回 0.5 粒度，三种变异均让 `--selftest` 变红。
