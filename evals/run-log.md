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
