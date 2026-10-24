# 评测运行日志（run-log）

本文件是 `evals.json` 的运行记录载体：machine 侧记录脚本端到端夹具与 selftest 的真实输出；human 回放待真实教学会话产生后回填，并交**独立评分者**（非执行模型）按五轴打分。

## 运行记录

### run_id: v53-migration-budget-fixture（2026-10-16）

> **历史存档**：本节的技能版本为 5.3.0，**不再是 E25/E26 的当前有效证据**——v5.4.1 修改了终测预算解析与数据根比对；E25/E26 的现行证据见下方 `v542-entry-id-fixture`。本节仅作演进留痕。

- 技能版本：5.3.0；执行环境：Windows / Python 3.13.3
- 覆盖场景：E25（迁移后恢复）、E26（终测预算）
- 执行方式：临时数据根 + 真实脚本调用（非 selftest 内嵌夹具）

#### E25 迁移后恢复（跨工作区/跨设备）

| 步骤 | 动作 | 结果 |
|---|---|---|
| 1 | `task_index.py --root <新根>`（progress.md「数据根」字段=旧机器路径） | schema=learn-task-index/5；`root_mismatch=true`；stderr 含 `W-ROOT-MISMATCH` |
| 2 | `progress_check.py <任务> --release`（字段未修复） | exit=1；errors=`[E-ROOT-MISMATCH]`（拦停，不得凭失同步状态提交） |
| 3 | 按 v5.3 迁移规则更新「数据根」字段为新根 → 重跑 task_index | `root_mismatch=false`，stderr 无告警 |
| 4 | 重跑 progress_check release | exit=0；ok=true；零 ROOT-MISMATCH 告警 |

全程未新建任何重复任务（规则：失同步只告警与拦停，不得据此建档）。

#### E26 长课程终测预算

| 夹具 | 结果 |
|---|---|
| 预算行「题量 ≤2 ｜ 实际题量 3」（超限） | exit=1；errors=`[E-EXAM-BUDGET-EXCEEDED]` |
| 预算行「题量 ≤5 ｜ 实际题量 2」（限额内） | exit=0；ok=true |
| 缺预算行 | exit=0；ok=true；warnings 含 `W-NO-EXAM-BUDGET`（不阻断旧任务） |
| 预算行注明「全真」（≤2 实际 5 + 备考型全真模式） | exit=0；ok=true；零预算告警（豁免） |

### run_id: v541-migration-budget-fixture（2026-10-16）

- 技能版本：**5.4.1**；执行环境：Windows / Python 3.13.3
- **包内可重跑**：`python -B evals/verify-e25-e26.py`（stdlib-only；**每次运行使用唯一临时目录**、只清理本进程自建目录；建真实数据根并调用**技能包真实脚本**；stdout 与 stderr **分开断言**；12/12）。下方输出即该脚本的原始产物
- 证据角色：E25、E26 的 **v5.4.1 证据**（取代 `v53-migration-budget-fixture`——该节版本为 5.3.0，而 v5.4.1 已修改终测预算解析与数据根比对）；**已被下方 `v542-entry-id-fixture` 取代为当前有效证据**（v5.4.2 未改动 E25/E26 相关脚本，重跑结果 12/12 一致；本节作 v5.4.1 留痕）

#### E25 迁移后恢复（跨工作区/跨设备）

```
[PASS] E25-1 task_index：stdout JSON root_mismatch=True 且 stderr 含 W-ROOT-MISMATCH
[PASS] E25-2 progress_check --release：stdout JSON 以 E-ROOT-MISMATCH 拦停（不在 stderr）
[PASS] E25-3 修正字段后 task_index：rc3=0、root_mismatch=False、两通道零 ROOT 告警
[PASS] E25-4 重跑 release：不再告警（rc=0）
[PASS] E25-5 全程未新建重复任务：任务目录集合与任务数均不变
```

#### E26 终测预算矩阵

```
[PASS] E26-a 超限（知识型 ≤2 实际 3）→ E-EXAM-BUDGET-EXCEEDED 拦停
[PASS] E26-b 限额内（≤5 实际 2）→ 放行、零预算告警
[PASS] E26-c 缺预算行 → W-NO-EXAM-BUDGET（不阻断）
[PASS] E26-d 备考型 + 全真 → 豁免，零预算告警
[PASS] E26-e 仅「实际题量 = 9」→ 按畸形计（v5.4.1 修复）
[PASS] E26-f 备考型 + 非全真 + 声明超限 → 不得豁免（v5.4.1 修复）
[PASS] E26-g 预算行写在正文（二级标题后）→ 按缺行计（头部口径）
verify-e25-e26: 12/12 cases passed
```

### run_id: v54-script-suite-20261016（2026-10-16）

> **历史存档（部分被取代）**：本节技能版本为 5.4.1。其中「设计参照自检」与「判别力检验」两小节的 E27 输出（**19/19、7/7**）已先后被 v5.4.2 的 `v542-entry-id-fixture`（20/20、8/8）、`v542-entry-id-highwater-repair`（21/21、9/9）与 `v542-ledger-sync-repair`（**23/23、11/11，当前**）取代——v5.4.2 依次新增 C16/M8、C17/M9、C18/C19/M10/M11。五脚本 selftest 与终测预算修复回归结论仍成立。本节仅作演进留痕。

- 技能版本：5.4.1；执行环境：Windows / Python 3.13.3
- 执行方式：包内脚本真实调用（五脚本 `--selftest` + `evals/verify-e27.py` + 正则级直接验证）
- 覆盖场景：五脚本 selftest 全量回归；终测预算校验缺陷修复回归；U-* 规则逻辑的设计参照自检（**非验收证据**）

#### 五脚本 selftest（v5.3/v5.4 改动后全量回归）

```
python -B scripts/task_index.py --selftest        → OK（含 root_mismatch 五组用例、占位符整值判定）
python -B scripts/progress_check.py --selftest    → OK（含 E/W-ROOT-MISMATCH、预算行七组用例）
python -B scripts/scheduler.py --selftest         → OK
python -B scripts/kp_sort.py --selftest           → OK
python -B scripts/check_environment.py --selftest → OK
```

注意：selftest **只输出 OK/FAIL、不逐码留痕**——这正是早前批次用例无法据以恢复 `machine_verified` 的原因之一（见文末「归档缺口声明」）。

#### 终测预算校验修复回归（v5.4.1）

```
BUDGET_LIMIT_RE 取值：
  「题量 ≤12 ｜ 实际题量 8」   -> 12     （正常路径）
  「实际题量 = 9」             -> None   （修复：旧版把 9 误读为上限，畸形行被静默放行）
  「题量<=12」                 -> 12     （兼容 < 与 = 组合写法）
BUDGET_FULLREAL_RE：
  「备考型全真模式」           -> True   （豁免成立）
  「非全真模式」               -> False  （修复：旧版子串匹配「全真」误判为豁免）
progress_check --selftest 新增用例：
  ㊿c 仅「实际题量 = 9」                    → W-UNPARSED-EXAM-BUDGET（不再静默放行）
  ㊿d 备考型 + 非全真 + 声明超限            → E-EXAM-BUDGET-EXCEEDED（不再被豁免放过）
```

#### 设计参照自检：U-* 更新回补规则逻辑（`python -B evals/verify-e27.py`）

**⚠️ 这不是验收证据**：U-* 回补属**模型侧行为**，包内 `scripts/` 无任何实现；本脚本以内存数据重新实现规则逻辑，只检查「规则表述自洽、分支划分清楚」，**不读写 progress.md、不调用技能脚本、不验证模型真实路由**。对应 E27 因此判定为 `unrun`（见 evals.json）。

```
[PASS] C0 检查时机：白名单 + 已选定（未知意图不检查）
[PASS] C1 适用 AND 匹配：任一维度不符即不匹配
[PASS] C2 清单为空 → 零动作
[PASS] C3 已完成任务：非复习路径不动作；复习路径放行 A 级与复习必需 B 级
[PASS] C4 C 级条目 → 只说明差异与选项，不写盘
[PASS] C5 条目级幂等：补一条后不得记任务级 U-ID（防其余条目永久跳过）
[PASS] C6 条目级幂等：全部补齐后二次检查 no-op（无重复追加）
[PASS] C7 任务级幂等：U-ID 已记录 → 整任务跳过，二次结果不变
[PASS] C8 多候选：未选定不检查；选定后只检查该任务
[PASS] C9 条目级适用前提：非 S4 复习判分场景 → 降 D、不补
[PASS] C10 只补缺失字段：已有错因仅缺级时不重复追加
[PASS] C11 条目级适用前提：S4 阶段但本轮无真实复习判分 → 降 D、不补
[PASS] C12 写入未生效不记 U-ID：锚点未命中 → 不记 U-ID
[PASS] C13a 旧条目无 evt + 本轮新 evt → 唯一命中补写并惰性分配 entry_id
[PASS] C13b 旧 evt=E7（错题行）与本轮新 evt=E2 不同 → 命中并只改错题行
[PASS] C13c 同一 evt 双投影：只更新 target_entry 指定的那一条
[PASS] C13d 旧行多重命中 / 零命中 → 挂起不写入（不猜）
[PASS] C14 快照只落所属区块：别区块同款锚点不得误插
[PASS] C15 已完成→S4→已完成组合：来源阶段=已完成的 S4 现场条目级补写照常
verify-e27 (design reference): 19/19 cases passed        （exit=0）
```

v5.4.1 修订说明：条目级判定已从「比对本轮 evt 与旧条目 evt」改为 **`target_entry` 绑定 + 稳定 `entry_id`**（`evt` 只表示一次作答事件，禁止用于条目定位）；C13a/C13b 锁定「旧条目无 evt」与「旧新 evt 不同（旧 evt=E7 在**错题行**，target 指向该行且只改该行）」两种跨作答场景，C13c 锁定「同一 evt 的双投影只动 target 指定那条」，C13d 锁定「未给序号的多重命中 / 零命中挂起不猜」，C15 锁定「已完成→S4→已完成」组合（**边界诚实声明**：`simulate` 仅按 `当前阶段` 路由、不验证「复习来源阶段」特有的路由行为）；C11/C12/C14 分别锁定「S4 阶段但本轮未判分仍降 D」「写入未生效不记 U-ID」「快照只在所属区块内插入」；C0 为白名单 + 未知意图反例；C3 补齐已完成任务的 **A 级**复习路径。

#### 判别力检验：`python -B evals/verify-e27.py --mutation`

向本脚本**副本**注入 7 种「旧缺陷行为」，断言对应用例**必须 FAIL**——用于排除「恒真断言」（测了却抓不住缺陷）。注入副本若自身崩溃会被记为 ERR 而非误报为"无失败"。

```
[PASS] M1 evt 相等匹配定位条目（旧行为） → 失败用例 ['C13a', 'C13b', 'C13c', 'C13d', 'C15', 'C5']
[PASS] M2 只判阶段、不判本轮真实判分（旧行为） → ['C11']
[PASS] M3 锚点用全文替换（可落错区块） → ['C14']
[PASS] M4 整字段追加（重复追加） → ['C10']
[PASS] M5 未给出现序号时取第一条（宽松） → ['C13d']
[PASS] M6 锚点未命中仍记 U-ID → ['C12', 'C14']
[PASS] M7 条目级补一条即记任务级 U-ID → ['C15', 'C5']
mutation-check: 7/7 mutations detected
```

### run_id: v542-entry-id-fixture（2026-10-16）

> **E27 设计参照计数已被取代**：本节的 E27 `20/20`、mutation `8/8` 是修复前基线，已被后续设计参照修复记录取代（当前见最下方 `v542-ledger-sync-repair`：`23/23`、`11/11`）；本节 E25/E26 `12/12` 仍为当前有效证据（E25/E26 相关脚本未改）。

- 技能版本：**5.4.2**；执行环境：Windows / Python 3.13.3
- **包内可重跑**：`evals/verify-e25-e26.py`（E25/E26 端到端夹具，唯一临时目录、自清）与 `evals/verify-e27.py`（设计参照自检）；下方输出为**本轮原始产物**
- 改动范围（v5.4.2）：①`entry_id` 持久生命周期（身份账本：登记行 append-only、归档保 ID、删除留 tombstone、新 ID 取「登记+活动+归档」全集最大序号 +1、旧任务无法证明历史高水位则挂起）文档口径收口（`data-and-recovery.md`、`phases-and-gates.md`、`task-updates.md`）；②`scripts/scheduler.py` **识别并回显** `entry_id`（只解析/不回填、不自动分配；due-queue 加可选键 → schema `ltw-due-queue/2` 升 `/3`）；③`evals/verify-e27.py` 收口「多重命中」文案 + 新增 C16 生命周期用例 + M8 变异。E25/E26 相关脚本未改
- 证据角色：**E25、E26 的当前有效证据**（12/12，取代 `v541-migration-budget-fixture`）；五脚本 selftest、due-queue `entry_id` 契约、E27 设计回归（20/20）与 mutation（8/8）为本轮机器侧原始输出

#### E25/E26 端到端夹具（脚本未改，重跑复核）

```
$ python -B evals/verify-e25-e26.py --json
"passed": 12, "failed": 0
E25-1…E25-5 全 PASS（root_mismatch 两通道分离 / release 拦停 / 修正后零告警 / 不新建重复任务）；
E26-a…E26-g 全 PASS（超限拦停 / 限额内放行 / 缺行 W-NO-EXAM-BUDGET / 全真豁免 / 畸形计 / 非全真不豁免 / 头外缺行）
```

#### 五脚本 selftest（v5.4.2）

```
python -B scripts/task_index.py --selftest        → OK task_index --selftest
python -B scripts/progress_check.py --selftest    → OK progress_check --selftest
python -B scripts/scheduler.py --selftest         → OK scheduler --selftest
python -B scripts/kp_sort.py --selftest           → OK kp_sort --selftest
python -B scripts/check_environment.py --selftest → OK check_environment --selftest
```

#### due-queue 识别并回显 entry_id（T2 直接契约断言，本轮原始输出）

```
$ python -B -c "import sys; sys.path.insert(0,'scripts'); import scheduler; text='## 薄弱点\n- 概念（S=2,D=3,last=2026-10-10,due=2026-10-12,错因=理解性,级=B,entry_id=ENT-01）\n'; q,w=scheduler.queue_from_progress_texts([('sample',text)],scheduler.date.fromisoformat('2026-10-16')); assert not w, w; assert q[0].get('entry_id') == 'ENT-01', q; print('entry_id parser contract: OK')"
entry_id parser contract: OK
```

- 合法 `entry_id=ENT-01`：无 `W-META-INVALID`，队列项回显 `entry_id="ENT-01"`；
- 缺 ID 的旧条目：照常入队、输出 `entry_id: null`（消费方按存在性读取）；
- 非法 `entry_id=foo`：仍给 `W-META-INVALID` 且 `entry_id` 为 `null`；
- `scheduler.py --selftest` 断言 26 覆盖上述四项 + 薄弱点/错题本两种投影 + 端到端 due_queue_output；
- due-queue schema：`ltw-due-queue/2` → `ltw-due-queue/3`（加可选键，排序契约 cw→最逾期→due 早→稳定序逐字不动）。

#### E27 设计参照自检（**非验收证据**）

> U-* 回补属模型侧行为，包内 `scripts/` 无实现；本脚本以内存数据重实现规则逻辑，仅验证「规则表述自洽、分支划分清楚」，不读写 progress.md、不调用技能脚本。E27 仍为 `unrun`。

```
[PASS] C0 … C16   （共 20 例，v5.4.2 新增 C16「entry_id 生命周期不复用」）
verify-e27 (design reference): 20/20 cases passed        （exit=0）
```

#### 判别力检验（mutation，v5.4.2 增至 8 种）

```
$ python -B evals/verify-e27.py --mutation
[PASS] M1 evt 相等匹配定位条目（旧行为） → 失败用例 ['C13a', 'C13b', 'C13c', 'C13d', 'C15', 'C5']
[PASS] M2 只判阶段、不判本轮真实判分（旧行为） → ['C11']
[PASS] M3 锚点用全文替换（可落错区块） → ['C14']
[PASS] M4 整字段追加（重复追加） → ['C10']
[PASS] M5 未给出现序号时取第一条（宽松） → ['C13d']
[PASS] M6 锚点未命中仍记 U-ID → ['C12', 'C14']
[PASS] M7 条目级补一条即记任务级 U-ID → ['C15', 'C5']
[PASS] M8 分配只扫当前文本最大值（旧行为：删除最高号即复用旧 ID） → ['C16']
mutation-check: 8/8 mutations detected
```

#### 其它校验（本轮）

```
python -m json.tool evals/evals.json    → rc=0（可解析）
git diff --check                         → rc=0（无空白错误；仅 CRLF 换行提示，非错误）
全包缓存扫描                              → __pycache__ 目录 0、.pyc/.pyo 文件 0
```

### run_id: v542-entry-id-highwater-repair（2026-10-17）

> **E27 设计参照计数已被取代**：本节的 `21/21`、`9/9` 已被下方 `v542-ledger-sync-repair`（`23/23`、`11/11`）取代；本节仅作演进留痕。

- 技能版本：**5.4.2**；执行环境：Windows / Python 3.13.3
- 性质：**设计参照自检修复记录**——U-* 回补属模型侧行为、`scripts/` 无实现，本记录**不是** E27 的运行时验收证据；E27 仍为 `unrun`
- 修复：`evals/verify-e27.py` 引入 `entry_id` **高水位三态**（可见 ID → 已知高水位取 max+1；**新建任务**显式前提才可从 `ENT-01` 起；**旧任务无登记且无可见 `entry_id` → 未知高水位 → 挂起不猜**）。C13a/C13b 旧条目夹具补登记行 `已用条目ID：ENT-01`（有可证明高水位 → 目标分配 `ENT-02`）；新增 **C17**（未知高水位挂起：不猜 ID、不补字段、不记 U-ID）与 **M9**（空集合回落 `ENT-01`，令 C17 具判别力）；C13d 夹具补登记行，使「多重命中」分支不被挂起提前短路
- 取代关系：**取代 `v542-entry-id-fixture` 的 E27 设计参照计数**（`20/20`→`21/21`、`8/8`→`9/9`）；**不取代**该记录的 E25/E26 `12/12` 证据
- E27 的 `unrun` 判定不变

#### E27 设计参照自检（**非验收证据**）

```
"passed": 21, "failed": 0
C0 … C15（原 19 例）+ C16 entry_id 生命周期不复用 + C17 未知历史高水位挂起不猜
```

#### 判别力检验（`--mutation`，增至 9 种）

```
[PASS] M1 evt 相等匹配定位条目（旧行为） → 失败用例 ['C13a', 'C13b', 'C13c', 'C13d', 'C15', 'C5']
[PASS] M2 只判阶段、不判本轮真实判分（旧行为） → ['C11']
[PASS] M3 锚点用全文替换（可落错区块） → ['C14']
[PASS] M4 整字段追加（重复追加） → ['C10']
[PASS] M5 未给出现序号时取第一条（宽松） → ['C13d']
[PASS] M6 锚点未命中仍记 U-ID → ['C12', 'C14']
[PASS] M7 条目级补一条即记任务级 U-ID → ['C15', 'C5']
[PASS] M8 分配只扫当前文本最大值（旧行为：删除最高号即复用旧 ID） → ['C13a', 'C13b', 'C16', 'C17']
[PASS] M9 空集合回落 ENT-01（旧行为：历史高水位未知也猜号） → ['C17']
mutation-check: 9/9 mutations detected
```

### run_id: v542-ledger-sync-repair（2026-10-17）

> **E27 设计参照计数已被取代**：本节的 `23/23`、`11/11` 已被下方 `v542-followup-p1-p2-repair-20261017`（`26/26`、`14/14`）取代；本节仅作演进留痕。

- 技能版本：**5.4.2**；执行环境：Windows / Python 3.13.3
- 性质：**设计参照自检修复记录**——U-* 回补属模型侧行为、`scripts/` 无实现，本记录**不是** E27 的运行时验收证据；E27 仍为 `unrun`
- 修复（P2-A）：惰性分配改为**条目行 + 身份账本同趟写入**（`assign_entry_id` 调 `ensure_registry_entry_id`；新增 `registry_state()` / `ensure_registry_entry_id()`），并把登记行收口为**唯一格式**（只允许一条、位于第一个 `## ` 之前、ID 形如 `ENT-<数字>`、ASCII 逗号 + 空格、按数字升序）；**多条登记行 / 非法 ID / 登记行位于标题之后 → 失败关闭**（不改文本、不猜、不合并）。新增 **C18**（账本同步）、**C19**（格式边界）与 **M10**（只改条目行、不写账本）、**M11**（忽略畸形登记行继续分配）
- 取代关系：**取代此前的 E27 设计参照计数**（`21/21`→`23/23`、`9/9`→`11/11`）；**不取代** E25/E26 的 `v542-entry-id-fixture` `12/12` 证据
- E27 的 `unrun` 判定不变

#### E27 设计参照自检（**非验收证据**）

```
"passed": 23, "failed": 0
C0 … C15（原 19 例）+ C16 生命周期不复用 + C17 未知高水位挂起 + C18 惰性分配同步身份账本 + C19 登记行格式边界
```

#### 判别力检验（`--mutation`，增至 11 种）

```
[PASS] M1 evt 相等匹配定位条目（旧行为） → 失败用例 ['C13a', 'C13b', 'C13c', 'C13d', 'C15', 'C18', 'C5']
[PASS] M2 只判阶段、不判本轮真实判分（旧行为） → ['C11']
[PASS] M3 锚点用全文替换（可落错区块） → ['C14']
[PASS] M4 整字段追加（重复追加） → ['C10']
[PASS] M5 未给出现序号时取第一条（宽松） → ['C13d']
[PASS] M6 锚点未命中仍记 U-ID → ['C12', 'C14']
[PASS] M7 条目级补一条即记任务级 U-ID → ['C15', 'C5']
[PASS] M8 分配只扫当前文本最大值（旧行为：删除最高号即复用旧 ID） → ['C13a', 'C13b', 'C16', 'C17', 'C18']
[PASS] M9 空集合回落 ENT-01（旧行为：历史高水位未知也猜号） → ['C17']
[PASS] M10 只改条目行、不写身份账本（旧行为） → ['C18']
[PASS] M11 忽略畸形登记行并继续分配（旧行为） → ['C19']
mutation-check: 11/11 mutations detected
```

### run_id: v542-five-round-stability-20261017（2026-10-17）

- 技能版本：**5.4.2**；执行环境：Windows / Python 3.13.3
- 性质：**五轮可重跑稳定性证据**；其中 E27 部分仍是设计参照（`scripts/` 无实现），**不是**运行时验收
- 脚本（包内可重跑、stdlib-only、只读代码树、不创建固定临时目录）：`evals/verify-v542-stability.py`
- 命令：`python -B evals/verify-v542-stability.py --output evals/stability/v542-five-round-stability-20261017.json`
- 结果：`rounds=5`；`distinct_signatures=1`；`all_rounds_passed=True`；`static_ok=True`；退出码 **0**
- 每轮**功能命令集**（固定，顺序即签名顺序，共 9 条）：五脚本 `--selftest`、`evals/verify-e25-e26.py --json`、entry_id parser contract、`evals/verify-e27.py --json`、`evals/verify-e27.py --mutation`
- 一次性静态检查（**不属每轮**）：账本契约、两个 JSON 解析、`git diff --check`、缓存扫描
- 原始 JSON（含 R1–R5 完整 stdout/stderr/return code/签名/关键计数，约 180 KB）：`evals/stability/v542-five-round-stability-20261017.json`
- **非覆盖行为验证**：以同一 `--output` 复跑一次 → 提示「目标已存在，未覆盖」并派生 `…-attempt-02.json`（退出码 0、`rounds=5/5`、`distinct_signatures=1`）；验证后移除该冗余副本，只保留规范路径一份。`evals/stability/` **未被 `.gitignore` 排除**（仅有 `__pycache__`/`*.pyc`/`*.pyo` 规则），归档可入库
- 签名算法：每条命令规范化 `{label, returncode, status, counts, failed_ids}` → 按命令清单顺序组成数组 → `json.dumps(ensure_ascii=False, sort_keys=True, separators=(',',':'))` → SHA-256；stdout/stderr、时间戳、绝对临时路径、耗时与 Python 版本**不进签名**，原始流仍完整保留供人工复核
- 本轮各轮一致关键计数（基线）：五脚本 selftest 全 OK、E25/E26 `12/12`、E27 设计参照 `23/23`、mutation `11/11`
- 证据角色：**历史基线**；其 E27 计数已被 `v542-followup-p1-p2-repair-20261017`（`26/26`、`14/14`）取代；E25/E26 的 `machine_verified` 仍锚定 `v542-entry-id-fixture`（本记录不改写其 run_id）

### run_id: v542-followup-p1-p2-repair-20261017（2026-10-17）

- 技能版本：**5.4.2**；执行环境：Windows / Python 3.13.3
- 性质：**设计参照自检修复记录**——U-* 回补属模型侧行为、`scripts/` 无实现，本记录**不是** E27 的运行时验收证据；E27 仍为 `unrun`
- 修复（本 followup，1 个 P1 + 4 个 P2）：
  - **P1 多目标行号漂移**：`simulate()` 改为**先完整验证、后一次性提交**——全部目标先定位、重复目标失败关闭、无 ID 目标按**原始行号升序**预分配 ID；字段 / `entry_id` 均为原地改（不改行数），唯一改变行数的动作（插入/替换登记行）放到**全部条目写完之后**；任一目标零命中 / 多重命中 / 重复指向 → **整趟失败关闭**（不部分写入）
  - **P2-a 登记行严格校验**：`registry_state()` 要求等于 `_registry_line()` 规范输出（`- ` 前缀、全角冒号、无首尾空格、`, ` 分隔、规范数字 `zfill(2)`、至少一个、严格升序、无重复/尾逗号/空 token）；任一不符 → `malformed` 失败关闭；**空值行不得当 absent**；**缺失仍为合法 absent**
  - **P2-b ID 扫描限定三类结构化来源**（登记行 / `## 薄弱点`·`## 错题本` 条目行 / `## 错题归档`），说明文字与学习日志里的伪 ID **不计**
  - **P2-c 稳定性计数精确比较**：`EXPECTED_COUNTS`（E25/E26 `12/12`、E27 `26/26`、mutation `14/14`）+ guard `--selftest`
  - **P2-d 归档并发安全**：`O_CREAT|O_EXCL` 排他创建，已存在/被占用则派生 `-attempt-NN`
- 新增用例与变异：**C20**（多目标一次性提交）、**C21**（多目标任一无效整趟失败关闭）、**C22**（ID 扫描限定来源）；**M12→C20、M13→C21、M14→C22**
- **P1 修复前后复现（同一夹具：活动区锚点 `ENT-01` + 两个无 ID 目标 A、B）**：

  ```text
  旧（倒序逐条 patch+assign，写入时插入登记行 → 行号漂移）
    registry : ['- 已用条目ID：ENT-01, ENT-02']
    A 行     : '- A点：甲（S=2.0，D=4，last=2026-09-18，due=2026-09-22）'   ← 未获补写（漏写）
    B 行     : '- B点：乙（…，错因=理解性，级=B，entry_id=ENT-02）'          ← 唯一被写，A 被漏
  新（预分配后一次性提交）
    registry : ['- 已用条目ID：ENT-01, ENT-02, ENT-03']
    A 行     : '…错因=理解性，级=B，entry_id=ENT-02'
    B 行     : '…错因=理解性，级=B，entry_id=ENT-03'
    锚点行   : 字节不变（非 target 行不被改动）
  ```

- 计数：`verify-e27.py --json` → `passed=26, failed=0`；`--mutation` → `mutation-check: 14/14 mutations detected`
- 稳定性（P2-c / P2-d 本轮原始输出）：

  ```text
  $ python -B evals/verify-v542-stability.py --selftest
  OK stability guard --selftest                                            （rc=0；含「空套件/计数缩减/缺键/rc≠0 必须失败」负例）

  $ python -B evals/verify-v542-stability.py --output evals/stability/v542-followup-five-round-stability-20261017.json
  stability: rounds=5/5, distinct_signatures=1, all_rounds_passed=True, static_ok=True
  archive: evals\stability\v542-followup-five-round-stability-20261017.json （rc=0）

  并发 smoke（两进程同一 --output、各 --rounds 1）
    p1 archive: …v542-concurrency-smoke-20261017.json
    p2 archive: …v542-concurrency-smoke-20261017-attempt-02.json
    p2 stderr : [stability] 目标已存在，未覆盖：改用 -attempt-NN 排他创建
    两文件均完整可解析（rounds=1、9 条命令含原始 stdout/stderr/returncode）；无覆盖
    （smoke 为 1 轮临时产物，核验后已清理，仅保留规范归档一份）
  ```

- 取代关系：**取代此前的 E27 设计参照计数**（`23/23`→`26/26`、`11/11`→`14/14`）；**不取代** E25/E26 的 `v542-entry-id-fixture` `12/12`（E25/E26 逻辑与 run_id 不变）
- E27 台账：`verdict=unrun`、`run_id=null`、`actual_output=null`（不变）

### 归档缺口声明（2026-10-16 核查）

`rework-20261015-scheduler-audit` 与 `rework-20261015-state-acceptance` 两批 run_id 的**原始输出未随包归档**，其引用的夹具名（`cal_duplicate_complete`、`completed_missing_core`、`release_s2_no_diagnostic`、`stable_id_reorder_false_evidence_match`、`cursor_missing_reference`、`environment_python38_*` 等）**在当前脚本中已不存在** → 无法按原样独立复现。据此，`evals.json` 中依赖这两批 run_id 的 9 个用例（E07、E13、E15、E18、E19、E20、E21、E22、E23）已**降级为 `unrun`**，原声明保留在各自 `review_note` 并标注「不计为证据」。恢复 `machine_verified` 须补可重跑夹具并归档逐码输出。

当前仍为 `machine_verified` 的用例仅 **2 个：E25、E26**，其当前有效证据均为 **`v542-entry-id-fixture`（技能版本 5.4.2，真实脚本端到端输出，见上）**。**E27 已撤回 `machine_verified`**——其机制属模型侧行为、包内无机器实现，`verify-e27.py` 只是设计参照自检，不构成运行时验收证据；E27 需由真实教学会话回放 + 独立评分判定。


### run_id: formula-typesetting-5.5.0-20261017-static（2026-10-17）

- 类型：machine（静态契约验证；非渲染回放）
- 技能版本：5.5.0；执行环境：Windows / Python 3.13.3
- 覆盖场景：FORMULA-01–FORMULA-10 登记完整性 + 公式呈现机制静态契约（SKILL.md 条件指针 / formula-typesetting.md 章节 / teaching-loop 交叉引用 / lecture-styles 范例修订 / 版本字段 / 无残留）
- 脚本输出：`python -B evals/verify-formula-typesetting.py` → 退出码 0（50 OK / 0 FAIL）；五脚本 --selftest 全部 OK（task_index / progress_check / scheduler / kp_sort / check_environment）；`python -m json.tool evals/evals.json` 解析通过
- 边界声明：**渲染/宿主实测未执行**——目标聊天宿主与 Markdown 预览器的定界符验证未做，selected_inline/selected_block 未选定（候选清单与验证程序见 formula-typesetting.md 第 8 章）；FORMULA-01–10 全部保持「未验证」，待真实回放 + 独立评分后回填 actual_output/run_id/scores/verdict/formula_checks
- 既有问题留痕：evals/verify-e25-e26.py 在本基线下为 4/12（本轮真实重跑：passed=4, failed=8；evals.json 现含 E01–E24，该脚本仍按 v5.4.x 夹具断言 E25/E26），属 remove-update-backfill 手术遗留，本记录如实留痕、不处理、不掩盖
### 外部宿主验证阻塞声明（2026-10-17）

- 触发：本执行环境无聊天宿主渲染能力，且目标聊天宿主名称/版本、主要 Markdown 预览器名称/版本待用户提供，无法执行真实宿主验证（固定样例渲染、复制与窄屏检查）。
- 影响：`references/formula-typesetting.md` 第 8 节 (e) 的 selected_inline 与 selected_block 保持「未选定」；FORMULA-01–10 全部保持「未验证」，不得改为「通过」。
- 下一步所需输入：①目标聊天宿主名称与版本；②主要 Markdown 预览器名称与版本；③（可选）可访问的预览环境授权。输入齐备后按 `formula-typesetting.md` 第 8 章 (c) 固定样例与 (d) 五步流程实测，回填本日志与 (e) 记录位。
- 边界：本声明为纯追加留痕；公式静态契约证据见上方 run_id: formula-typesetting-5.5.0-20261017-static。

### 宿主验证处置决定（2026-10-17）

- 决定：用户裁定不提供聊天宿主与 Markdown 预览器信息，真实宿主验证不单独执行，改为「在不同工具中实际发现渲染问题时再修」的发现式策略。
- 存续状态：selected_inline 与 selected_block 保持「未选定」；FORMULA-01–10 保持「未验证」；公式呈现期间恒用 formula-typesetting.md 第 7 节纯文本明确分组降级（机制默认，无需实测）。
- 重启条件：任一宿主中出现公式渲染异常时，携带宿主名称/版本与异常公式样例，按第 8 章 (c)/(d) 实测并回填本日志与 (e) 记录位。

### run_id: formula-typesetting-5.5.0-20261017-acceptance-recheck（2026-10-17）

- 类型：machine（静态契约复核；非渲染回放）
- 背景：验收反馈指出上一条静态记录中「50 OK / 0 FAIL」与脚本当前 56 项不符——该数字是脚本扩容（50→56 项）前的历史输出，按追加式日志纪律原样保留、不覆盖不删除，本条为当前版本复核。
- 脚本输出：`python -B evals/verify-formula-typesetting.py --skill-root .` → 退出码 0（56 checks, 56 OK, 0 FAIL）
- JSON：`python -m json.tool evals/evals.json` 通过（退出码 0）
- 五脚本 --selftest：task_index / progress_check / scheduler / kp_sort / check_environment 全部退出码 0
- 边界声明：真实宿主渲染、复制、窄屏与独立学科评分未执行（所有者裁定延后，发现式修复）；selected_inline/selected_block 未选定；FORMULA-01–10 保持「未验证」

## human 回放（待真实教学会话回填）

每条回放记录格式：

```
### run_id: <回放标识>（日期）
- 场景：<evals.json 对应 case id 或新场景>
- 输入上下文：<学员原话 / 任务现场>
- 实际输出：<对话关键轮次摘录或文件副作用>
- 文件副作用：<新建/修改的文件>
- 阶段变化 / 证据变化：<S 前后值 / exercises 变化>
- 脚本输出：<相关校验码>
- 独立评分：<五轴分数 + 评分理由>（评分者须非执行模型）
- verdict：<verified / human_unscored / failed>
```

回放检查项（六维）：入口路由 / 教学动作 / 闸口真实性 / 落盘正确性 / 恢复可用性 / 用户负担。

优先回放清单（对应 evals.json unrun 条目）：E01–E05（教学正确性）、E08（常规授权）、E10（正常下课）、E14（模考高分非满分）、E16（图错核验）、E17（教法裁决作用域）、E24（无陪学意图不建档）、E27（更新回补检查——模型侧行为，机器侧无实现，须由真实教学会话回放 + 独立评分判定）。

### run_id: v580-design-note（2026-10-18）

- 技能版本：5.8.0（计划）
- 状态：**未运行**；本节只是用例设计说明，不构成任何通过证据。
- 新增用例：E36–E46（深度契约/提示泄漏/冲刺姿态/卡壳/过度泛化/备料/续学回忆/安全边界/学习简报/现象→符号/计划一句话+D-B）。
- 说明：E36–E46 的 `actual_output` / `run_id` / `scores` 均为 null，`verdict` 保持「未验证」；待真实会话回填后由独立评分者按五轴打分。
- 相关规则源：`lecture-styles.md`「深度契约」、`teaching-loop.md` 第 2.1/4/7/9 节、`redlines.md` SR-8、`phases-and-gates.md` S0/S2/S3/S4、`data-and-recovery.md` 快捷指令/异常分支。

### run_id: v580-selftest-20261018

- 类型：machine（脚本自检；非真实教学回放）
- 技能版本：5.8.0
- 命令：`python scripts/<name>.py --selftest`（check_environment / kp_sort / progress_check / scheduler / task_index / verify_explanation）
- 实际输出：六个脚本全部退出码 0
- 结构校验：`skill_ops.py validate` 退出码 1，11 条**既有告警**（`.trae` 开发稿 4 条、`methodology.md` 证据等级词误判 3 条、`skill-dependencies.json` 自定义 schema 4 条）；本次改动未新增 error
- 边界：未跑真实教学会话；E36–E46 仍为「未验证」，不得据本节声明教学效果通过

### run_id: v590-box-generic-20261021

- 类型：machine（脚本自检 + 跨学科样例静态回归；非真实教学回放）
- 技能版本：5.9.0（工作区未提交，版本随提交时统一升）
- 命令：`python scripts/<name>.py --selftest`（check_environment / kp_sort / progress_check / scheduler / task_index / verify_explanation）
- 实际输出：六个脚本全部退出码 0；`verify_explanation --selftest` 新增 5 条跨学科答案框用例（文科按点给分 / 编程代码块 / 英语 Prompt / 句中分点 / 缺交付起笔）全部 OK
- 样例回归：历史（按点给分）、编程（代码块 + 输出）、数学（含粗体题面）三份讲义 `verify_explanation.py` 均退出码 0；改前同两份非数学样例报 4 条 E（`E-BOX-FORMAT` 分点、`E-BOX-INCOMPLETE`×2、`E-BOX-WRAP` 代码块）
- 契约校验：`evals/verify-formula-typesetting.py` 56 checks / 56 OK / 0 FAIL（版本字段保持 5.9.0）
- 结构校验：`skill_ops.py validate` 退出码 1，6 条告警——`.trae` 开发稿 4 条、`skill-dependencies.json` 自定义 schema 1 条（既有）；另 1 条为工作区 `.workbuddy/memory` 文件里的具体路径，不属包内容
- 边界：无真实教学会话回放；E47 与既有 human 条目保持「未验证」，不得据本节声明教学效果通过

### run_id: v590-answer-integrity-20261021

- 类型：machine（脚本自检 + 反例回归；非真实教学回放）
- 技能版本：5.9.0（工作区未提交）
- 改动：`verify_explanation.py` 新增 `E-BOX-EMPTY`（交付段为空，或只剩「略／从略／见教材／同上／自行体会／此处省略／答案见…」且去标点后 ≤20 字）；「代码：／脚本：」后接代码块属合法留空；`data-and-recovery.md` 题组新增可选「参考答案」区块（判分后回填、位于文件末尾、不拆 `-答案.md` 分册）
- 实际输出：六个脚本 selftest 全 0；`verify_explanation --selftest` 新增 3 条用例通过（空答案 / 占位 / 代码标签不误报）；改前「解：略」「解：」两份反例均返回退出码 0，改后各报 `E-BOX-EMPTY`
- 契约校验：`evals/verify-formula-typesetting.py` 56 checks / 56 OK / 0 FAIL
- 结构校验：`skill_ops.py validate` 6 条已知告警（同 v590-box-generic 记录）
- 边界：无真实对话回放；E48 保持「未验证」

### run_id: v590-answer-rubric-20261021

- 类型：machine（脚本自检 + 指针行回归；非真实教学回放）
- 技能版本：5.9.0（工作区未提交）
- 改动：给分点量表定体例（框外单独一行、各点之和须等于合计）；新增 `E-RUBRIC-SUM`（合计不符）与 `W-RUBRIC-SOURCE`（缺「训练量表／官方」声明），只对含合计或 ≥2 个分值的量表体生效、指针行不误报；`lecture-styles.md` 补客观题逐项排除、带图答案引用、②与⑤不重复、自测「先做后看」提示；`subject-playbooks.md` 数学族补「理科计算与化学」子形态
- 实际输出：六个脚本 selftest 全 0；`verify_explanation --selftest` 新增 3 条量表用例通过；「给分点量表见 progress.md」指针行零告警
- 契约校验：`evals/verify-formula-typesetting.py` 56 checks / 56 OK / 0 FAIL
- 结构校验：`skill_ops.py validate` 6 条已知告警
- 边界：无真实对话回放；E49 保持「未验证」

### run_id: v590-lecture-flow-20261021

- 类型：machine（脚本回归 + 流程核验；非真实教学回放）
- 技能版本：5.9.0（工作区未提交）
- 改动：① `progress.md` 新增可选「质量保障机制」区，承接讲义头部指针与自检 W 后置记录（此前指针指向不存在的区块）；② 定稿后纠错补回退路径（先改回「草稿（修订中）」→ 修 → 重跑校验与自检 → 再定稿），`teaching-loop.md` 第 1.3 节加指针；③ 写明讲义自测与 `exercises/` 题组的分工（自测不进闸口、不作证据、与题组不同题），同步自检第 9 项与小步④
- 实际输出：含新区块的 progress.md 经 `progress_check.py` 零告警（exit 0）、`task_index.py` 正常解析；六个脚本 selftest 全 0；契约 56/56
- 结构校验：`skill_ops.py validate` 6 条已知告警
- 边界：无真实对话回放；E50 保持「未验证」

### run_id: v590-lecture-readability-20261021

- 类型：machine（脚本自检；非真实教学回放）
- 技能版本：5.9.0（工作区未提交）
- 改动：① 讲义定稿新增节首导读三行（本节目标 / 前置 / 预计时长），入 schema、`phases-and-gates.md` 定稿要求与自检第 8 项；② 自检第 14 项（配图逐面板核对）从「可后置」移入「发出讲授轮必查（仅含图时）」；③ `lecture-styles.md` 开头新增「卡壳信号 → 换哪套」映射表，`teaching-loop.md` 八动作加指针；④ 标准讲义补「术语首次出现给白话或定义」，入自检第 5 项；⑤ 自测答案区禁占位，新增 `W-SELFTEST-EMPTY`（W 级不阻断，规则码 15 个）
- 实际输出：`verify_explanation --selftest` 44 项全 OK（新增自测答案占位用例）；六个脚本 selftest 全 0；契约 56/56
- 结构校验：`skill_ops.py validate` 6 条已知告警
- 边界：无真实对话回放；E51 保持「未验证」

### run_id: v590-reading-style-20261021

- 类型：machine（脚本自检；非真实教学回放）
- 技能版本：5.9.0（工作区未提交）
- 改动：① 新增第 6 套「精读笔记式」（材料型默认；单元=一个论证块；五要素映射；⑤=`原文：`+`参考概括：`+`原文定位：`），`phases-and-gates.md` 加材料型选风格指引；② 脚本题面标识加「原文」、交付标识加「参考概括」，新增精读框用例；③ 合并重复——「先示范后练习」（phases 两处、teaching-loop 专长反转改为指针）、反馈时序与判分证据（phases 三处压成执行要点 + 指针）、SKILL「不代劳」压缩；④ 豁免改名：机制豁免（M）与 ⑤ 空位豁免
- 实际输出：`verify_explanation --selftest` 新增精读框用例通过；六个脚本 selftest 全 0；契约 56/56
- 结构校验：`skill_ops.py validate` 6 条已知告警
- 边界：无真实对话回放；E52 保持「未验证」

### run_id: v590-lecture-deep-audit-20261021

- 类型：machine（脚本自检 + 7 份最小样例实测；非真实教学回放）
- 技能版本：5.9.0（工作区未提交）
- 改动（审计 17 项，按「脚本 → 文档对齐 → 结构 → 精简」顺序）：
  - 脚本：① 框内 `√` 不再按验算标记判（答案里的根号不误报），验算只认 ✓ ✔ ✅；② 段内多行按后果分级——普通文字 `W-BOX-WRAP`，拆断 `$…$`/code span 才 `E-BOX-WRAP`；③ 深讲参照级与分层标注打通（`【参照】` + `⑤ 不适用（参照级）` 豁免②③④⑤、仅查①）；④ 新增 `E-IMG-DEADLINK`（按讲义目录解析 `图：` 与 `![]()`）；⑤ 新增 `E-HEADER-BRIEF`（定稿缺导读三行，草稿不查）；⑥ 新增 `W-SELFTEST-MISSING`（有自测题面区无答案区）；⑦ 头部规则块识别泛化到「体例/排版/约定/格式（」
  - 文档：⑧ 统一讲义默认顺序（完整示例 → 易错点 → 小结 → 检验）并调范例；⑨ 体例清单补 `原文：`/`参考概括：`/`原文定位：`；⑩ 图像双轨扩到流程/架构/时序/装置/受力/结构式，图文核对改「以领域事实为准」；⑪ schema 新增「风格 × 五要素落点」表（6 套风格各定义 ③⑤）；⑫ 材料型按「有无主张—证据结构」分流（论证文→精读，条文/数据→标准讲义，代码→操作手册）；⑬ 每节题量预算 ≤6（自测 2 + 题组 2–3 + 检验 0–2，验收复用题组题）；⑭ 可选「概念地图」区块与「压缩已熟」要点卡落盘位置；⑮ `teaching-loop.md` 体例复述压成指针；⑯ 精读「结构骨架」与「论证拆解」合并为「结构骨架与证据强度」；⑰ 自测提示语改「再看本节自测答案」
- 实际输出：`verify_explanation --selftest` 57 项全 OK（新增 √ 根号 / 段内断公式 / 参照级 / 缺导读 / 自测无答案区 / 化学代码规则块 / 图死链 / 行内代码示例不误报死链 / 自测答案区为空 9 条）；6 份脚本 selftest 全 0；契约 56/56；`git diff --check` 为 0
- 样例实测（改前 → 改后）：`> 解:x=√2。` E-BOX-FORMAT → 0；长论述段内两行 E-BOX-WRAP → W-BOX-WRAP；`【参照】` 五项全缺 + W-NO-TIER → 标参照级豁免后 0；图死链 0 → E-IMG-DEADLINK；有自测无答案区 0 → W-SELFTEST-MISSING
- 结构校验：`skill_ops.py validate` 6 条已知告警
- 复核轮（同日）：精读式「材料型默认」改为「论证文材料默认」并写明分流；题量预算统一为「自测 2 + 题组 2–3 + 单元检验 0–1 ≤6」，对话轮与 phases ③ 的 0–2 同步收敛；脚本 docstring 断行与规则注释重号修正；依赖清单能力描述补新检查；卡壳映射补精读；精读骨架补 ①③④ 落点；图核对补架构/时序；新增「自测答案区为空」与「行内代码图示例不误报」两条自检；E53 扩为五份夹具。
- 边界：无真实对话回放；E53 保持「未验证」，不得据本节声明教学效果通过

### run_id: v590-slot-and-title-20261021

- 类型：machine（脚本自检 + 4 份最小样例实测；非真实教学回放）
- 技能版本：5.9.0（工作区未提交）
- 改动：
  - 骨架槽位（`lecture-styles.md`）：六套风格骨架逐槽位加〔〕落点标注——标准讲义、费曼卡、考试冲刺卡、对比辨析卡、操作手册式各补 ④ 与小结点，精读笔记式补 ⑤ 与小结；schema 新增「七槽位落点必须可指认」（④/小结不得靠反例、对照表、报错清单、检查清单顺带承担），「风格 × 五要素落点」表改注「只列 ③⑤ 与豁免，①②④小结检验见骨架」，出厂自检第 8 项加人工核对项
  - 标题约定（`verify_explanation.py`）：`W-SELFTEST-MISSING` / `W-SELFTEST-EMPTY` 从只认 `## 本节自测` 扩为词干 `(本节)?(检验问题|自测|检验)` + `答案` 后缀（复核轮再扩，见下条）；词干后限行尾/空白/左括号，避免 `## 检验方法`、`## 检验步骤` 误判；新增开放检验豁免行 `- 检验说明：开放题，无标准答案`
  - 同步：SKILL.md 脚本能力描述、`skill-dependencies.json` 两处降级描述与 scripts_contract 备注、evals 新增 E54/E55
- 实际输出：`verify_explanation --selftest` 60 项全 OK（新增「检验问题无答案区」「检验问题答案配对」「开放检验豁免」「检验方法不误判」4 项）；样例实测 `## 检验问题` 无答案区 0 → W-SELFTEST-MISSING；`## 检验问题答案` 配对 → 0；`## 检验` + 检验说明 → 0；`## 检验方法` → 0；`## 小测` → 0（既不检查也不豁免）
- 边界：无真实对话回放；E54、E55 保持「未验证」，不得据本节声明教学效果通过
- 复核轮（同日，检查遗漏）：发现 4 处——① 只认五种题面标题，`## 自测题`/`## 检验题` 这类自然变体漏检；② 答案区只认「…答案」，`## 参考答案`/`## 答案`/`## 答案要点`/`## 答案与解析` 漏认；③ 单文件只查第一个答案区，第二个空区不告警；④ 豁免只认「开放/口头/无标准答案」，操作手册式的练手任务与「本节不设检验」无法豁免。修法：题面词干扩为 `(本节)?(检验问题|自测题?|检验题?)`；答案区加通用 `(本节)?(参考)?答案` + `区/要点/(与)解析`；`parse_doc` 收多答案区，逐区查 EMPTY、逐题面区查 MISSING；豁免原因扩到 不设/跳过/练手/动手/压缩；英文标题明确不识别（标题统一用中文）。
- 复核另补 1 处：答案区只有围栏代码块（编程类自测以代码作答）曾被判空 → 改为围栏内非空行即算作答，新增 selftest 用例。
- 复核实测（10 组样例）：`## 自测题` 无答案 → MISSING；+`## 参考答案` → 0；`## 检验题`+`## 答案与解析` → 0；`## 自测`+`## 答案` → 0；两区一空 → 恰 1 条 EMPTY；练手说明 → 0；无说明无答案 → MISSING；`## 检验步骤` → 0；`## Self-test` → 0（不识别）；`## 答案要点` → 0。`verify_explanation --selftest` 66 项全 OK。
- 边界：仍无真实对话回放；E54、E55 保持「未验证」。
- 复核第二轮（同日）：① 覆盖判定改为按族——同族答案区只覆盖同类题面区（「检验问题答案」不给「自测」兜底），通用答案区（`## 答案`/`## 参考答案`）可统管其前的多个题面区；原「答案区须落在下一个题面区之前」会把「自测 + 检验问题 + 文末参考答案」误报为缺答案。② 修「小结最多三句」与记忆族「本节地图 ≤7 条」的规则冲突：密度原则加地图变体上限（只列概念名与依赖、不写解释），schema 段落同步。③ 文档与脚本 docstring 的覆盖语义同步。`verify_explanation --selftest` 68 项全 OK。
- 复核第三轮（同轮补漏）：逐套骨架点数〔〕槽位，发现费曼卡缺 ③ 落点（表里有、骨架没标）→ 12 岁版收尾补 ③ 一句话结论，并写明 ③ 与小结分工（③ 收「是什么」，小结收「怎么记/何时用」）；费曼卡与冲刺卡的「槽位下限」补 ③。

### run_id: v590-cross-subject-example-20261022

- 类型：machine（文档改动 + 8 份最小讲义实测；非真实教学回放）
- 技能版本：5.9.0（工作区未提交）
- 改动（`references/lecture-styles.md`）：
  - 成品范例去 Unicode 箭头（②分步「→」改「，得」）；补【本节最小必需】；④ 与「常见误区」改为同源（④ 列全、误区展开其中两条）；只保留数学一个完整范例，文科完整例降为片段
  - 体例段加硬规则：**不得默认 `解：`**，按内容所属学科族取形态
  - 新增「其余族的最小形态」：语言 / 编程 / 理科计算与化学 / 文科与记忆（按点给分）/ 理论（案例）/ 精读 六类各 3–13 行 ⑤ 片段（篇幅从简），只演示段结构
- 实测：数学完整范例与六类片段（语言 Prompt/Model answer、编程 任务/代码/输出、物理公式代入、化学 `->` 配平、文科 `答：①②③` 每点一段、理论 `结论/依据/适用` 三段、精读 原文/参考概括/原文定位；理科计算与化学各一份样例）逐份落成讲义跑 `verify_explanation`，全部 0 违规；六脚本 --selftest 全 0；契约 56/56；`git diff --check` 0；`validate` 6 条既有告警
- 边界：无真实对话回放；片段是格式参照，不构成教学效果证据

### run_id: v59-five-element-rekey（2026-10-22）

- 技能版本：5.10.0（工作区，未提交）
- 覆盖场景：五要素重编号后的机器侧结构验证（EXP-01/05、E47–E49、E53 的判分标准已同步改写）
- 执行方式：临时目录 + 真实脚本调用（非对话回放）

#### 结果

- `verify_explanation.py --selftest`：全 OK（终检后 73 项）（含旧编号单条报错、③ 标记行带内容、单步答案一段、③④⑤ 豁免口径）
- 八族最小讲义（数学 / 语言 / 编程 / 物理 / 化学 / 文科 / 理论 / 精读）各 1 份，目录校验退出码 0、零违规
- 旧编号讲义：恰 1 条 `E-MARKER-LEGACY`，不叠加 `E-REQ-MISSING` / `E-BOX-INCOMPLETE`；关掉拦截的对照跑为 2 条
- 其余 5 个脚本 `--selftest` 全 0；`evals/verify-formula-typesetting.py` 56/56；`git diff --check` 0；`skill_ops.py validate` 6 条既有告警

#### 边界

- 无真实对话回放：EXP-01/05、E47–E55 仍为「未验证」；本次只改判分标准措辞，不构成教学效果证据
- 新增规则（`E-MARKER-LEGACY` / `W-MARKER-CONTENT` / ⑤ 小结必检 / ③ 框不写题面段）尚无对应 eval 用例
#### 追记：W-BOX-WRAP 降噪（同日）

- 用户决定「降噪」：取消普通段内多行的提示，规则码 20 → 19；`E-BOX-WRAP` 保留（仅拆断 `$…$` / code span 时报）。
- 改判据落点：`lecture-styles.md`「框内分段」注明脚本不提示、归出厂自检 2.1 人工核对；脚本 docstring 规则表、`SKILL.md`、`skill-dependencies.json`、E53 判分标准同步。
- selftest 断言改为「多步挤一段 → 零 findings」，仍全 OK（终检后 73 项）；实测三例：多步挤一段 0、拆断公式 1 条 E、正常分段 0。
- 三风格实写复测（费曼卡 / 考试冲刺卡 / 对比辨析卡，含检验列表行、多 ③ 框、纯概念豁免样态）：修正卡片布局说明后全部零违规；此前冲刺卡 / 辨析卡各报 1 条假「缺 ③」，根因是 `## 本节自测答案` 等标题把 ③ 切出概念单元。

### run_id: marker-rules-5.10.0-20261022-machine（2026-10-22）

- 技能版本：5.10.0（工作区，未提交）
- 覆盖场景：五要素新编号五项规则的机器侧行为验证——E56（旧编号单因单报）、E57（③ 标记行留空）、E58（⑤ 小结必检、豁免不连带）、E59（标记行行首锚定）、E60（多题单元答案框）
- 执行方式：`evals/verify-marker-rules.py`（新增，stdlib-only）——临时目录构造 14 份讲义夹具，子进程真实运行 `scripts/verify_explanation.py` 全 CLI 路径，断言退出码与违规码

#### 结果

- 行为契约 19 项全 OK（组 1 五项 / 组 2 四项 / 组 3 三项 / 组 4 三项 / 组 5 四项）
- 关键断言：旧格式恰 1 条 E-MARKER-LEGACY 且不叠加缺项/框体例、退出码 1；仅 W 时退出码 0；纯概念豁免不连带豁免 ⑤；正文提及「见 ③ 答案」不误判；题号 + 占位答案仍报 E-BOX-EMPTY
- evals.json：cases 60 → 65（E56–E60，kind: machine，verdict 未验证待独立评分）；machine_evidence_ref 登记新脚本；updated_at 2026-10-22
- 连带修正：`verify-formula-typesetting.py` 5.10 的 updated_at 钉死值 2026-10-21 → 2026-10-22（evals.json 当日合法更新），契约恢复 56/56
- 其余：六脚本 selftest 全 0；`git diff --check` 0；`skill_ops validate` 6 条既有告警

#### 边界

- 本运行只证明「脚本对五项新规则的判定行为符合判分标准」，不构成教学效果证据；E56–E60 verdict 保持「未验证」，待独立评分者复核

### run_id: v600-selftest-20261022（2026-10-22）

- 技能版本：6.0.0（工作区，未提交）
- 覆盖场景：E61（同会话重复答对不增长稳定度）、E62（保持复习进入到期队列并说明理由）、E63（判分四态/作废/未判）
- 执行方式：脚本 selftest 内嵌纯函数与临时目录夹具（非对话回放；无真实教学会话）

#### 结果

- `scheduler.py --selftest`：OK（新增断言 2b 同会话抑制、断言 7b 保持复习/reason/schema、保持复习日期前缀容错与校准隔离；原有排序与回归断言保留）
- `progress_check.py --selftest`：OK（新增 v6.0 四态组：partial-mix / partial-pass / ungraded / void-only / void-excluded / result-conflict，加测带括号注的调度档、英文四态别名、作废旧行+同 attempt_id 改判）
- 端到端临时任务：`due-queue` 输出 `kind=保持`/`reason`/schema `/3`；`progress_check --release` 通过并报 `W-VOIDED-ATTEMPT`/`W-UNGRADED-ATTEMPT`；`next-interval` 新卡与同会话 CLI 结果符合契约
- 对抗性矩阵：四态 token 矩阵、闸口 2/3 边界、全 partial/全未判/全作废、partial 缺独立性、同 attempt 冲突、作废后改判、保持复习无日期前缀的元数据兜底与无可推算日期告警，全部通过
- 变异测试：关闭同会话抑制、恢复校准污染、把 partial 计为正确、忽略作废、恢复保持复习 meta_default=true 五个定向变异，均被 selftest 抓住（5/5），证明新断言不是空转
- 其余四脚本 `--selftest` 全 0；`evals/verify-formula-typesetting.py` 56/56；`evals/verify-marker-rules.py` 19/19
- evals.json：cases 65 → 68（E61–E63，kind: machine，verdict 未验证待独立评分）；applies_to_version 6.0.0；machine_evidence_ref 已登记 v6.0 selftest
- 文档：SKILL.md / data-and-recovery.md / phases-and-gates.md / teaching-loop.md / redlines.md / skill-dependencies.json / CREDITS.md 已同步「保持复习、四态、作废/申诉、零迁移」
- `git diff --check`：0

#### 边界

- 脚本 selftest 只证明确定性解析/调度/闸口行为符合新契约，不构成教学效果证据；E61–E63 verdict 保持「未验证」，待独立评分者复核
- 未做真实对话回放；保持复习的初始条目写入与 S4 清除转区仍由模型按文档执行，需在后续真实任务中抽检

### run_id: v610-selftest-20261022（2026-10-22）

- 技能版本：6.1.0
- 覆盖场景：E64（KP 分型验收）、E65（大纲契约与 intake）
- 执行方式：脚本 selftest 内嵌纯函数与临时目录夹具（非对话回放；无真实教学会话）

#### 结果

- `progress_check.py --selftest`：OK（新增 v6.1 分型组：typed-ok / typed-mem / typed-con / typed-vis / typed-bad / typed-old / typed-half-colon / typed-alias / typed-title-only / typed-missing-status；大纲契约与 intake 组：contract-ok / incomplete / no-material / module-bad / material-bad / gap / duplicate-cover / same-prefix / placeholder / strategy-ok / strategy-bad）
- `kp_sort.py --selftest`：OK（新增分型字段夹具：排序只读前六段，不因类型/视觉任务附加段报畸形）
- 其余四脚本 `--selftest` 全 0；`evals/verify-formula-typesetting.py` 56/56；`evals/verify-marker-rules.py` 19/19
- evals.json：cases 68 → 70（E64–E65，kind: machine，verdict 未验证待独立评分）；applies_to_version 6.1.0；machine_evidence_ref 已登记 v6.1 selftest
- 文档：SKILL.md / data-and-recovery.md / phases-and-gates.md / teaching-loop.md / skill-dependencies.json / CREDITS.md / setup-guide.md 已同步「KP 分型、分型验收标签、模块目标/材料覆盖、目标程度/教学策略、零迁移」
- 变异测试 7/7：关闭分型门、清空模块目标检查、关闭教学策略枚举、让 kp_sort 拒绝附加字段、关闭 KP 别名归一、忽略契约占位、放行畸形分型字段，七种定向变异均被 selftest 抓住
- `git diff --check`：0

#### 边界

- 分型验收只对 `知识清单.md` 中声明了类型/视觉任务的 KP 生效；旧清单缺字段仍走统一闸口，不能据此声称旧任务已做分型
- 模块目标/材料覆盖是结构提示（W 级），不替代教学判断；材料是否真正匹配模块仍需模型/用户核对
- 未做真人对话回放；E64–E65 verdict 保持「未验证」

### run_id: v620-selftest-20261022（2026-10-22）

- 技能版本：6.2.0
- 覆盖场景：E66（v6.2 文档契约）、E67（续学先读交接与学习记录）、E68（ask hint）、E69（来源备课与讲授证据）、E70（选项/答案键规则）
- 执行方式：E66 为静态文档契约脚本；E67–E70 为待真实回放的人类场景（当前未验证）

#### 结果

- `evals/verify-v62-docs.py`：17/17 OK，退出码 0（版本、DeepTutor 归因、交接/记录/证据、记忆纪律、ask hint、来源备课、选项规则、E66–E69 登记）
- 文档契约变异 5/5：移除 ask hint、移除记忆写法纪律、移除选项规则、改错版本、移除 DeepTutor 归因，均被脚本抓住
- 其余六脚本 `--selftest` 全 0；`evals/verify-formula-typesetting.py` 56/56；`evals/verify-marker-rules.py` 19/19
- 集成自检：含「本次交接/学习记录/讲授证据」三区的临时 task，`progress_check` exit 0 且无 E，`task_index` scan_status=ok、tasks=1（新分区不被旧脚本误判）
- evals.json：cases 70 → 75（E66 machine + E67–E70 human，verdict 未验证）；applies_to_version 6.2.0；machine_evidence_ref 已登记文档契约
- 文档：SKILL.md / data-and-recovery.md / phases-and-gates.md / teaching-loop.md / lecture-styles.md / skill-dependencies.json / CREDITS.md / setup-guide.md 已同步「交接/学习记录/讲授证据、记忆纪律、ask hint、来源备课、选项规则」
- `git diff --check`：0

#### 边界

- 文档契约只证明“规则已写入对应分册”，不证明模型在真实对话中会执行；E66 不能替代教学效果证据
- E67–E70 仍是人类场景，未做真实回放；verdict 保持「未验证」
- v6.2 不新增脚本闸口，旧任务仍零迁移

### run_id: v630-selftest-20261023（2026-10-23）

- 技能版本：6.3.0
- 覆盖场景：E71（v6.3 文档契约）、E72（出题流水线四步）、E73（视觉任务原始来源）
- 执行方式：E71 为静态文档契约脚本；E72–E73 为待真实回放的人类场景（当前未验证）

#### 结果

- `evals/verify-v63-docs.py`：32/32 OK，退出码 0（版本五处、四步流水线、旧题去重、规划字段、一次修复、视觉任务原始来源、S5 蓝图优先、T11 例外、CR-8 改写覆盖、E71–E73 登记）
- `evals/verify-v62-docs.py`：17/17 OK，退出码 0（版本断言改为 ≥6.2.0，历史契约在 6.3.0 下继续成立）
- 文档契约变异 11/11：删掉规划步、删掉规划步难度、删掉生成图禁令、删掉视觉任务来源纪律、改错版本、删掉 S3 流水线引用、删掉 T11 例外、删掉无任务跳过、删掉 S5 规划按蓝图、删掉自测同题无例外、删掉 CR-8 改写，均被脚本抓住
- 其余六脚本 `--selftest` 全 0；`evals/verify-formula-typesetting.py` 56/56；`evals/verify-marker-rules.py` 19/19
- 集成自检：含「本次交接/学习记录/讲授证据」三区的临时 task，`progress_check` exit 0 且无 E，`task_index` scan_status=ok、tasks=1（v6.3 未改脚本，旧任务仍可读）
- evals.json：cases 75 → 78（E71 machine + E72–E73 human，verdict 未验证）；applies_to_version 6.3.0；machine_evidence_ref 已登记 v6.3 文档契约
- 文档：SKILL.md / data-and-recovery.md / phases-and-gates.md / teaching-loop.md / lecture-styles.md / subject-playbooks.md / references/redlines.md / skill-dependencies.json / CREDITS.md / setup-guide.md 已按落点同步出题流水线与视觉任务来源规则
- `git diff --check`：0

#### 边界

- 文档契约只证明“规则已写入对应分册”，不证明模型在真实对话中会执行；E71 不能替代教学效果证据
- E72–E73 仍是人类场景，未做真实回放；verdict 保持「未验证」
- 视觉任务的来源锚点是文档纪律（写在题面/题组文件），不是新增脚本字段或硬闸口；旧证据不追溯作废
- v6.3 不新增脚本闸口、不加数据字段，旧任务仍零迁移

### run_id: v640-consistency-20261023（2026-10-23）

- 技能版本：6.4.0（阶段 0 一致性 + 阶段 1 理解核心；类型/支持/来源细节仍为后续阶段目标）
- 覆盖场景：E108（v6.4 一致性 + 理解核心契约）
- 执行方式：E108 为静态文档契约脚本 + 内置 mutation；无真实对话回放

#### 结果

- `evals/verify-v64-consistency.py`：34/34 OK，退出码 0（版本五处、状态行两分、③ 豁免四类、交付标识单一表与集合比对、L3 复习产物例外、单元≠KP、头部/指针、深讲拆节、类型单元数、命名/附件、概念地图阈值、理解核心六件套、E108 登记）
- 理解核心：`handout-design.md` §3 已写四证/六问/四段/闭卷/二次定稿/关键能力/冷读；`lecture-styles.md` 标准骨架改为教学例→配对→④/⑤→闭卷解释→评估例/迁移；`phases-and-gates.md`、`teaching-loop.md` 接入
- 文档契约变异 6/6：概念地图阈值改回 8+、台账状态行合并回状态行、删除设计类标识、删除深讲拆节、纯记忆误写为纯概念、脚本交付标识多出一项，均被脚本抓住
- 六个脚本 `--selftest` 全 0；`evals/verify-formula-typesetting.py` 56/56；`evals/verify-marker-rules.py` 19/19；`evals/verify-v62-docs.py` 17/17；`evals/verify-v63-docs.py` 32/32
- `scripts/verify_explanation.py --selftest`：设计类 `方案：`/`设计说明：` 框零违规，纯记忆/已会·检索版 ③ 豁免零 E，旧夹具仍全过
- evals.json：cases 78 → 79（E108 machine，verdict 未验证）；applies_to_version 6.4.0；machine_evidence_ref 已登记 v6.4 一致性/理解核心契约
- 文档：新增 `references/handout-design.md`；lecture-styles / phases-and-gates / teaching-loop / subject-playbooks / SKILL / setup-guide / skill-dependencies / CREDITS / evals 已同步
- `git diff --check`：0

#### 边界

- 一致性/理解核心契约只证明“规则已写入且互相对得上”，不证明模型在真实对话中会执行；E108 不能替代教学效果证据
- 类型模板、L1/L2/L3 动态、来源四向对齐、教学例/评估例的来源保真在 `handout-design.md` 中仍为**后续阶段目标**；阶段 0/1 未新增自动闸口、数据字段或迁移
- 四证/闭卷/二次定稿是文档规则与阅读动作，未新增脚本硬闸口；S3 仍由判分+关键能力+复述把关
- 旧讲义不回溯；`③ 不适用（纯记忆/已会·检索版）` 与设计类标识为增量合法出口，不改变旧文件判定
- 纯记忆/纯概念/参照级豁免的语义边界仍由人工/评审确认，脚本只做结构匹配

### run_id: v650-stage2-20261023（2026-10-23）

- 技能版本：6.5.0（阶段 2；来源四向对齐与 P1/P2 仍为后续）
- 覆盖场景：E109（阶段 2 契约）、E110–E115（记忆/设计模板、支持级、学习者状态、流水线/决策日志、类型×支持；人评未验证）
- 执行方式：E109 为静态文档契约 + mutation；E110–E115 为待真实回放的人评场景

#### 结果

- `evals/verify-v65-stage2.py`：24/24 OK，退出码 0（类型模板、四步流水线、L1/L2/L3 动态、学习者状态、决策日志/修复表、接线、E109 登记）
- 文档契约变异 5/5：删除四类矩阵、L3 检索版产物、专家盲点、决策日志、来源待办，均被脚本抓住
- 六个脚本 `--selftest` 全 0；`evals/verify-formula-typesetting.py` 56/56；`evals/verify-marker-rules.py` 19/19；`evals/verify-v62-docs.py` 17/17；`evals/verify-v63-docs.py` 32/32；`evals/verify-v64-consistency.py` 34/34
- 类型结构样板：记忆、设计、程序 L2 三份最小结构样板跑 `verify_explanation.py`；程序样板最初把「验证：」写进 ③ 框，被 `E-BOX-FORMAT` 抓住——改为 `输出：` 交付段后 0 E，并把类型矩阵的 ③ 形态改为「模型解答+输出（决策点/验证写 ②/④，不写框内批注）」
- `scripts/verify_explanation.py --selftest`：设计/记忆标识、纯记忆/L3 豁免、旧夹具仍全过
- evals.json：cases 79 → 86（E109 machine + E110–E115 human，verdict 未验证）；applies_to_version 6.5.0；machine_evidence_ref 已登记 v6.5 阶段 2 契约
- 支持级证据：L1→L2 可用同会话独立成功（支架渐退）；L2→L3、L3 保持要求「跨会话独立成功」；同一会话重复答对不单独作为 L3 证据，S/D 也不因同会话重复增长（v6.0 同会话抑制）
- 文档口径修正：`已会` 不是 KP 状态（KP 状态只有未讲/已讲/暂缓/排除）；已会证据来自 S1/伺服/跨会话连续正确/学员确认，`handout-design.md` §7 已把「KP 状态」与「已会证据」拆开
- 文档：`handout-design.md` §4–§8（类型模板/四步流水线/支持级/学习者状态/决策日志）；lecture-styles / phases-and-gates / entry-routing / teaching-loop / subject-playbooks / SKILL 已接线；版本五处同步 6.5.0
- `git diff --check`：0

#### 边界

- 阶段 2 是文档 + 接线规则，不新增运行时闸口、progress.md 字段或迁移；S3 仍由判分+关键能力+复述把关
- E109 只证明规则写入并接线，不证明模型在真实对话中会执行；E110–E115 未跑
- 来源四向对齐、覆盖行、深度分配、教学例/评估例真实性仍在阶段 3；P1/P2 质量件未做
- L1/L3 模拟冷读（机会成本）两版 4/4，但为 LLM 读者且 fixtures 未提交；不能替代真人冷读与 2 天延迟迁移
- 旧讲义不回溯；类型/支持级只影响新生成/新定稿讲义

### run_id: v660-stage3-20261023（2026-10-23）

- 技能版本：6.6.0（阶段 3；P1/P2 仍为后续）
- 覆盖场景：E116（阶段 3 契约）、E117–E121（四向对齐/覆盖行、深度分配、评估例真实性、来源保真、模块/考试对齐；人评未验证）
- 执行方式：E116 为静态文档契约 + mutation；E117–E121 为待真实回放的人评场景

#### 结果

- `evals/verify-v66-stage3.py`：22/22 OK，退出码 0（四向对齐、覆盖行、深度分配、教学例/评估例真实性、来源保真、模块/考试对齐、接线、E116 登记）
- 文档契约变异 5/5：删除四向对齐、覆盖行格式、深度分配、引用上限、评估例真实性，均被脚本抓住
- 六个脚本 `--selftest` 全 0；`evals/verify-formula-typesetting.py` 56/56；`evals/verify-marker-rules.py` 19/19；`evals/verify-v62-docs.py` 17/17；`evals/verify-v63-docs.py` 32/32；`evals/verify-v64-consistency.py` 34/34；`evals/verify-v65-stage2.py` 24/24
- evals.json：cases 86 → 92（E116 machine + E117–E121 human，verdict 未验证）；applies_to_version 6.6.0；machine_evidence_ref 已登记 v6.6 阶段 3 契约
- 文档：`handout-design.md` §9–§11（来源/覆盖/深度/评估真实性/来源保真）；一页合同 11 条；SKILL / phases / entry-routing / teaching-loop 已接线；版本五处同步 6.6.0
- `git diff --check`：0

#### 边界

- 阶段 3 是文档 + 接线规则，不新增运行时闸口、progress.md 字段或迁移；覆盖行/来源锚点仍是文档纪律，未做脚本完整性校验
- E116 只证明规则写入并接线，不证明模型在真实对话中会执行；E117–E121 未跑
- P1/P2 质量件（文本结构、主张—证据表、教材章节、教师包等）未做
- 旧讲义不回溯；来源/覆盖/深度只影响新生成/新定稿讲义

### run_id: v670-p1p2-20261023（2026-10-23）

- 技能版本：6.7.0（合并 6.6.0 阶段 3 内部里程碑与 P1/P2 可选增强）
- 覆盖场景：E122（P1/P2 契约）、E123–E128（文本结构/主张—证据、设计量表/主图、质量回路/要点卡/移动端/MVP、教材章节、教师包、预习；人评未验证）
- 执行方式：E122 为静态文档契约 + mutation；E123–E128 为待真实回放的人评场景

#### 结果

- `evals/verify-v67-p1p2.py`：20/20 OK，退出码 0（P1/P2 规则、接线、E122 登记）
- 文档契约变异 6/6：删除文本结构、设计量表、要点卡/间隔、要点卡/调度/扩展区冲突、教材章节、教师包，均被脚本抓住
- 六个脚本 `--selftest` 全 0；`evals/verify-formula-typesetting.py` 56/56；`evals/verify-marker-rules.py` 19/19；`evals/verify-v62-docs.py` 17/17；`evals/verify-v63-docs.py` 32/32；`evals/verify-v64-consistency.py` 34/34；`evals/verify-v65-stage2.py` 24/24；`evals/verify-v66-stage3.py` 22/22
- evals.json：cases 92 → 99（E122 machine + E123–E128 human，verdict 未验证）；applies_to_version 6.7.0；machine_evidence_ref 已登记 v6.7 P1/P2 契约
- 文档：`handout-design.md` §10–§12（P1/P2/证据）；一页合同仍 11 条（P1/P2 为可选增强）；SKILL / entry-routing / phases 已接线；版本五处同步 6.7.0
- 自检修正：清理旧阶段指针（§2.4/§10）；§9.6/§10.6 补独立讲义出口；§10.1/§10.5/§11.1 明确结构图/提示/章首路线位置；§10.2/§10.3/§10.7/§10.8 补表格/量表/要点卡/MVP 落点与类型例外；§10.6 升 L3 仍按 §6.1；§10.9 停车位放在扩展区之前；§11.1 章节混合检索、§11.3 预问题不计单节题量；§11.2 教师版不套学生讲义结构校验；契约补相应 mutation（20/20）
- `git diff --check`：0

#### 边界

- P1/P2 是可选增强，不新增运行时闸口、progress.md 字段或迁移；11 条硬合同不变
- E122 只证明规则写入并接线，不证明模型在真实对话中会执行；E123–E128 未跑
- 不做完整教材平台；正式 Word/排版仍让位文档技能；预习模式不把预读当已讲/已掌握
- 旧讲义不回溯；P1/P2 只影响新生成/新定稿讲义

### run_id: v671-cleanup-20261023（2026-10-23）

- 技能版本：6.7.1（清理教师/家长侧入口）
- 覆盖场景：删除 P2 教师备课包/教师版、预习模式；删除「家长版周报/给家长看的学习报告」别名；学习简报改为学员自用；保留教材级章节层
- 执行方式：静态文档契约 + 全量回归；人评 E123–E126 未跑

#### 结果

- `evals/verify-v67-p1p2.py`：19/19 OK，退出码 0（P1 + 教材章节层、接线、E122 登记）
- 文档契约变异 5/5：删除文本结构、设计量表、要点卡/间隔、要点卡/调度/扩展区冲突、教材章节，均被脚本抓住
- 六个脚本 `--selftest` 全 0；`evals/verify-formula-typesetting.py` 56/56；`evals/verify-marker-rules.py` 19/19；`evals/verify-v62-docs.py` 17/17；`evals/verify-v63-docs.py` 32/32；`evals/verify-v64-consistency.py` 34/34；`evals/verify-v65-stage2.py` 24/24；`evals/verify-v66-stage3.py` 22/22
- evals.json：cases 99 → 97（删除 E127/E128；E44 改为自用学习简报；E122 收窄为 P1 + 教材章节层）；applies_to_version 6.7.1；machine_evidence_ref 已登记 v6.7.1 清理
- 文档：`handout-design.md` §9.1/§9.2 教师侧改家教侧；§11 只保留教材章节层；SKILL / CREDITS / entry-routing / data-and-recovery 去掉教师/家长入口；版本五处同步 6.7.1
- `git diff --check`：0

#### 边界

- P1 与阶段 3 不变；P2 只保留教材章节层；不新增字段/闸口；旧讲义零迁移
- 学习简报保留为学员自用；SR-8 家长/监护人安全提示保留；课堂研究引用仅作证据
- E123–E126 等人评未跑；历史 v6.7 记录中教师包/预习条目保留为 release 历史，不再出现在当前规则

### run_id: v672-cleanup-20261023（2026-10-23）

- 技能版本：6.7.2（按用户要求移除 SR-8 安全边界）
- 覆盖场景：删除 SR-8 规则、SKILL/redlines/teaching-loop 相关引用、E43 评测；其余规则不变
- 执行方式：静态文档契约 + 全量回归；人评 E44/E45–E126 未跑

#### 结果

- 六个脚本 `--selftest` 全 0；`evals/verify-formula-typesetting.py` 56/56；`evals/verify-marker-rules.py` 19/19；`evals/verify-v62-docs.py` 17/17；`evals/verify-v63-docs.py` 32/32；`evals/verify-v64-consistency.py` 34/34；`evals/verify-v65-stage2.py` 24/24；`evals/verify-v66-stage3.py` 22/22；`evals/verify-v67-p1p2.py` 19/19
- evals.json：cases 97 → 96（删除 E43）；applies_to_version 6.7.2；machine_evidence_ref 已登记 v6.7.2 清理
- 文档：SKILL 红线改三类；redlines 删除 SR-8；teaching-loop 删除危机转介句；handout-design E 范围改 E44–E126；版本五处同步 6.7.2
- `git diff --check`：0

#### 边界

- 只移除 SR-8 与 E43；P1、阶段 3、教材章节层、学习简报不变；不新增字段/闸口；旧讲义零迁移
- 历史 v6.7/v6.7.1 记录保留原有 SR-8 描述，作为 release 历史

### run_id: v672-cleanup2-20261023（2026-10-23）

- 技能版本：6.7.2（续清理：红线编号重排 + 术语统一）
- 覆盖场景：SR-9「未判/作废语义误用」重编号为 SR-8，红线编号恢复连续；references 内「学生」统一为「学员」；其余规则不变
- 执行方式：静态文档契约 + 全量回归；人评未跑

#### 结果

- 六个脚本 `--selftest` 全 0；`evals/verify-formula-typesetting.py` 56/56；`verify-marker-rules.py` 19/19；`verify-v62-docs.py` 17/17；`verify-v63-docs.py` 32/32；`verify-v64-consistency.py` 34/34；`verify-v65-stage2.py` 24/24；`verify-v66-stage3.py` 22/22；`verify-v67-p1p2.py` 19/19
- 文档：redlines SR-9→SR-8；handout-design/lecture-styles/phases-and-gates 术语统一；handout-design 类型判定问句改为直接问学员（修正第三人称错位）；CREDITS/evals.json 同步说明；`evals/verify-v67-p1p2.py` 断言同步「学员版」
- 码表校正：SKILL 删除不存在的 `E-NO-ATTEMPT`；data 将 `W-EVT-CONFLICT` 更正为 `W-CONFIDENCE-AMBIGUOUS`；补登 `E-EVIDENCE-REF-MISSING` / `W-MULTI-EVIDENCE` / `E-FINAL-ATTEMPT-CONFLICT` / `W-CONFIDENCE-AMBIGUOUS`；码表标题改「常用」（完整码表以脚本输出与 docstring 为准）；E19 的 review_note 标注旧码名迁移
- 引用校正：methodology 去掉失效的「§8」自引用（改指「核验状态与不能推出什么」节名）；phases 二次定稿的「§3.6」补 `handout-design.md` 前缀；复检两文件 `missing_local_sections` 归零
- `git diff --check`：0

#### 边界

- 只改编号与称谓，不改触发条件、处置动作、闸口与字段；历史 v672 记录中的「移除 SR-8」指原安全边界，保留为 release 历史
- 「学生」保留 3 处：目标用户枚举（entry-routing）与文献转述（methodology）

### run_id: v673-readability-20261023（2026-10-23）

- 技能版本：6.7.3（发布）
- 类型：machine（文档契约 + 样板版面 + mutation；非真人回放）
- 覆盖场景：E129–E134（读者路径 / 段落与标题版式 / 图解语法 / 黑白打印与证据边界 / 程序型样板 / 设计型样板）；人评未跑

#### 改动

- `lecture-styles.md`：新增「读者版可读性契约」（三遍路径、一段一义、标题/强调/留白、图解语法、5 问自检、渲染建议）；**拆分默认不变量（标题导航/段落/图解语法/颜色+线型/黑白可读/alt）与 P1 可选增强（速览/回看索引/一句话结论/章级块）**；新增 L1/L2/L3 与记忆/概念/程序/设计/精读/参照级变体表；补读者验证四问；图像双轨加图解语法指针；schema 默认顺序补 P1 可选增量。
- `handout-design.md`：新增 10.10 读者路径与三层速览、10.11 图表系统与视觉一致性；10.4/10.8/10.9/11.1/12 同步；P1 可选，不新增字段/闸口；收口「强调标记」歧义、字号 `max(14px, 0.8×正文)`、颜色按领域语义、短节豁免逻辑。
- 自检修正：强调配额统一为「连续两段不都用加粗抢重点」（`handout-design`、`lecture-styles`、`--reader`、`verify-readability` 四处一致）；5 问/读者四问对短节条件化（无速览时只看标题/导读）；`methodology` 节点预算改为「一次呈现 ≤7±2，完整概念图可更多但须分层」。
- 自检修正（第二轮）：程序型 SVG「端点异号才有根」改为「保证有根」（充分条件，不是必要条件）；设计型样板改选「每日增量云备份」以同时满足 RTO 4 小时与 RPO 24 小时，配对答案同步改指该方案；概念/设计型主图改为按第 10.4 节可省；表格表题规则区分「速览表由标题承担」与「数据表加表题」；速览与概念地图顺序明确为「先速览、后地图」；`--reader` 与 `verify-readability` 均增加速览/回看索引位置检查。
- `methodology.md`：登记可读性与可视化文献依据与边界（Mayer 2017/2005、Noetel 2021、Cromley & Chen 2025、Alpizar 2020、Schroeder 2018、Sundararajan & Adesope 2020、Nesbit & Adesope 2006、Krieglstein 2022、Hebert/Pyle/Bogaerds-Hazenberg、W3C clreq、WCAG 2.1、Zhu 2021、Gao 2019、Chan 2013、Lonsdale 2014、Pan 2020、Delgado 2018、Bisra 2018）。
- `SKILL.md` / `phases-and-gates.md` / `skill-dependencies.json`：描述、参考索引与 S3 定稿口径接线；`verify_explanation.py` 新增 opt-in `--reader`（W 级可读性检查，不阻断、旧讲义不回溯）。
- 新增 `evals/fixtures/reader-layout/` 读者版样板（概念）+ `procedure/` 程序型样板 + `design/` 设计型样板与 SVG 图；新增 `evals/verify-readability.py`（文档契约 + 样板版面 + L1/L3 烟测 + 程序/设计烟测 + 7 个样板 mutation + 3 个文档 mutation + 2 个 `--reader` 运行时 mutation，22 项）。
- `evals/evals.json`：cases 96→102（E129–E134，machine，verdict 未验证）；`machine_evidence_ref` / `run_log_ref` 更新；applies_to_version 6.7.3。

#### 结果

- 六个脚本 `--selftest` 全 0；`verify-formula-typesetting.py` 56/56；`verify-marker-rules.py` 19/19；`verify-v62-docs.py` 17/17；`verify-v63-docs.py` 32/32；`verify-v64-consistency.py` 34/34；`verify-v65-stage2.py` 24/24；`verify-v66-stage3.py` 22/22；`verify-v67-p1p2.py` 19/19；`verify-readability.py` 22/22。
- 样板经 `verify_explanation.py` 与 `--reader` 校验：0 违规；`evals.json` JSON 有效；`git diff --check` 0。

#### 边界

- 只证明规则在场 + 样板结构合格，不证明真人更易读或学习效果更好；E129–E132 保持「未验证」。
- 中文行长证据冲突（17–48 字/行 vs 76 字/行），本技能取 25–40 字、上限 48；多媒体原则效应量受先验知识、材料复杂度、媒介与时长调节，不把 d/g 当固定收益。
- 不新增运行时闸口、不新增 progress 字段、旧讲义不回溯；版本按约定未升。

### run_id: v680-block-pacing-20261024（2026-10-24）

- 技能版本：6.8.0（工作区 + 安装区同步；未提交、未推送）
- 类型：machine（文档契约 + 静态脚本回归；非真人回放）
- 覆盖场景：新增 E135（块级推进：逐块停轮 vs 整节投喂，human，未验证；真人回放延期）；其余 102 项保持「未验证」；本次仅做静态契约回归

#### 改动

- `SKILL.md` / `phases-and-gates.md` / `teaching-loop.md` / `lecture-styles.md` / `handout-design.md` / `data-and-recovery.md`：新增小节负载门与逐块推进（块尺寸 5–10 分钟、通用前置探针、关键块正式 ≤3–4、简单块轻量确认、跨块串联）。
- 版本字段同步：`skill-dependencies.json` / `setup-guide.md` / `CREDITS.md` / `evals.json` / `verify-formula-typesetting.py`。
- `scripts/task_index.py`：新增 `current_block` / `block_total` 可选解析（来自「下次续学」的「已讲到第 k/总块」，兼容标题后缀与无前缀写法），schema 4→5；`data-and-recovery.md` / `skill-dependencies.json` 同步；selftest 含 block 夹具。
- `references/redlines.md` / `SKILL.md`：新增 SR-9「整节投喂 / 一轮多块」；`references/methodology.md`：新增 5–10 分钟块尺寸文献行；`evals/evals.json`：新增 E135（human，未验证）。

#### 结果

- 六个脚本 `--selftest` 全 0；`verify-formula-typesetting.py` 56/56；`verify-v64-consistency.py` 34/34；`git diff --check` 0。

#### 边界

- 只证明规则在场与静态契约通过，不证明真人学习效率提升；真实学习效果仍待回放。
- E135 真人学习回放按用户 2026-10-24 决定延期，保持「未验证」；本次不做真人回放。

### run_id: v690-finest-kp-block-20261025（2026-10-25）

- 技能版本：6.9.0（工作区；未提交、未推送）
- 类型：machine（文档契约 + 静态脚本回归；非真人回放）
- 覆盖场景：新增 E136（一个块塞多个知识点 → 拆 3 块，human，未验证）；更新 E135（加速不合并）；其余保持「未验证」；本次仅做静态契约回归

#### 改动

- `SKILL.md` / `phases-and-gates.md` / `teaching-loop.md` / `lecture-styles.md` / `handout-design.md` / `data-and-recovery.md` / `redlines.md`：讲授单位收敛为「块 = 当前节目标内最细知识点」；1 块 1 检、独立答对才推进；删除 5–10 分钟、15–30 分钟、≤5–7 块、≤2 套新记号、30/45 分钟休息、每节 ≤3–4 道正式确认、合并组、多 KP 块。
- `SKILL.md` / `references/methodology.md`：块尺寸改为按最细知识点，不设时间阈值。
- 版本字段同步：`skill-dependencies.json` / `setup-guide.md` / `CREDITS.md` / `evals.json` / `verify-formula-typesetting.py`；`evals.json` updated_at 2026-10-25。
- `evals/evals.json`：更新 E118/E135，新增 E136；新增 `evals/verify-v69-docs.py`；`evals/verify-v64-consistency.py` 3.2 改为检查最细知识点/节内块数不设上限。
- 学习档案 `shaanxi-zhuanshengben-english`：节 1 场 1 重切 13 块；`01A` 增讲授块清单与 9 类词性子块；课程体系追加附录 C（22 节粒度审计，约 236–244 块）；progress.md 学习日志记录重切与审计。

#### 结果

- 六个脚本 `--selftest` 全 0；`verify-formula-typesetting.py` 56/56；`verify-v69-docs.py` 11/11（含 6 个 mutation）；`verify-marker-rules.py` 19/19；`verify-readability.py` 22/22；`verify-v62-docs.py` 17/17；`verify-v63-docs.py` 32/32；`verify-v64-consistency.py` 34/34；`verify-v65-stage2.py` 24/24；`verify-v66-stage3.py` 22/22；`verify-v67-p1p2.py` 19/19。
- `verify_explanation.py --reader` 对 `01A-词性与词性判断.md`：0 E 0 W；`evals.json` / `skill-dependencies.json` JSON 有效；`git diff --check` 0。
- 数据核对：01A 讲授块清单 13 行；课程体系附录 C 覆盖 22 节；旧 2026-10-24 判分与探针记录保留。

#### 边界

- 只证明规则在场与静态契约通过，不证明真人学习效率提升；E135/E136 保持「未验证」，本轮不做真人回放。
- 22 节块数是规划估算（无教材正文的节标暂定）；实际块数开节前按「知识梳理」正文复核。
- 教材节不按块数拆；节 1 实际课堂节奏与 22 节课时影响仍待真人回放。

#### 修复轮（skill-studio 复审，2026-10-25）

- 删除 `scripts/__pycache__`（字节码缓存导致 preflight `scan_complete=False`）。
- 将 `scripts_contract` / `verification` 从 `skill-dependencies.json` 移到 `evals/scripts-contract.json`，manifest 恢复 skill-studio schema 兼容；`references/setup-guide.md` 同步指向新文件，并补打包清理与 `--risk-ack` 说明；manifest 的 verify 补 `--reader`。
- 课程表修旧数据：22 节总量 38.5 场→38.5 课次；节 1 块预算改为场 1 13 块 + 场 2 17 块；附录 C 总量 237–244 块；progress 补场 2 的 17 块暂定清单。
- 01A 块 13 改为「1 道跨块综合 + 3 道节末题组」。

**复测结果：**

- 干净副本 `skill_ops validate`：0 issues。
- 干净副本 `skill_ops preflight`：`scan_complete=True`，`summary high=1 / medium=169`，仍为 `blocked`；唯一 high 是 `scripts/task_index.py:295` 的 `tmp.unlink`，只清理 `index.json.tmp`，selftest 也要求失败后无 `.tmp` 残留；人工复核接受，打包需 `--risk-ack`。
- 六个脚本 `--selftest` 全 0；`verify-formula-typesetting.py` 56/56；`verify-v69-docs.py` 11/11；`verify-v62-docs.py` 17/17；`verify-v63-docs.py` 32/32；`verify-v64-consistency.py` 34/34；`verify-v65-stage2.py` 24/24；`verify-v66-stage3.py` 22/22；`verify-v67-p1p2.py` 19/19；`verify-marker-rules.py` 19/19；`verify-readability.py` 22/22。
- `01A` `verify_explanation.py --reader`：0 E 0 W；`progress_check.py`：ok；`evals.json` / `skill-dependencies.json` / `evals/scripts-contract.json` JSON 有效。

#### 闭包轮（12+1 修正，2026-10-25）

- 发现「综合」不是知识点：已从 01A、备课报告、课程表、附录 C 的块清单移出；节 1 场 1 = 12 个知识点块 + 1 节末综合；场 2 暂定 17 块；审计总量约 236 块（暂定，节末综合不计）。
- `scripts/check_environment.py` 移除已迁移的 `scripts_contract` / `verification` 允许项，环境清单 schema 与 skill-studio 一致；selftest 退出码 0。
- 复测：六脚本 selftest 0；全部文档契约 0；`01A --reader` 0E/0W；`progress_check` ok；干净副本 `skill_ops validate` 0；preflight 仍只有 1 个 high `task_index.py:295 tmp.unlink`（临时文件清理，人工复核接受）。
