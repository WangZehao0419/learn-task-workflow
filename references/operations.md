# 脚本操作、契约与验证

<!-- owns: 脚本 CLI、退出码、错误码入口、selftest、路径约定、只读/原子写、打包验证；must-not-define: 教学/判分/数据语义（指向 owner） -->

本册是脚本的**操作手册**：怎么调、退出码怎么看、什么时候跑。业务语义在各自 owner：判分与调度见 `assessment.md`，阶段闸口见 `workflow.md`，数据字段见 `data.md`，失败处置见 `failure.md`。

## 脚本清单

六个用户脚本 + 一个契约模块，均 stdlib-only、幂等可重跑，基础 Python 版本以 `skill-dependencies.json` 的 `min_version` 为准。

| 脚本 | 用法 | 默认行为 | 何时跑 |
|---|---|---|---|
| `task_index.py` | `--root <数据根> [--write-index \| --no-write-index] [--selftest]` | 只读、不物化 `index.json`（写缓存为显式 opt-in） | 会话开始/续学/问进度 |
| `progress_check.py` | `<任务目录> [--release] [--proposed-phase <阶段>] [--staged <候选快照>] [--changed-lessons <正整数列表>] [--selftest]` | 历史/日常校验（warning 非阻断旧任务） | 闸口推进前；新增掌握/结课/跨阶段加 `--release` |
| `scheduler.py` | `next-interval \| due-queue \| calibration [--selftest]` | 只读计算，输出 JSON；落盘由文件写入能力负责 | 判分后算 S'/D'/due；开节前查到期队列；S4 开场校准 |
| `kp_sort.py` | `<清单文件> [--selftest]` | 只读、零写盘 | 知识型/技能型排序子步 |
| `check_environment.py` | `[--manifest <路径>] [--capability <名称>]... [--selftest]` | 只读诊断 | 脚本调用出现解释器/版本类失败时诊断一次 |
| `verify_explanation.py` | `<材料目录或单文件> [--selftest] [--reader]` | 只读静态校验，不写盘 | 讲义定稿前；`--reader` 加跑读者版 W 级检查 |
| `rule_contract.py` | `--selftest \| --topology` | 只读校验契约与拓扑 | 修改契约/分册结构后、打包前 |

完整参数、退出码与 notes 的机器可读版本见 `evals/scripts-contract.json`；脚本 docstring 只保留算法/参数说明，不再维护完整错误码表。

## 路径与解释器约定

- **脚本路径基准** = `<技能根>/scripts/<脚本名>.py`（不写裸 `scripts/…` 依赖 cwd）。
- **数据根基准** = 显式 `--root`（或 progress_check 的任务目录实参），不依赖脚本默认根。
- **解释器**统一 `python`（仅有 `python3` 时等价替换）。
- `task_index` / `progress_check` / `scheduler` / `kp_sort` 带 `--selftest`；`check_environment` / `verify_explanation` / `rule_contract` 也带 `--selftest`。
- 契约文件固定为 `<技能根>/contracts/rules.json`；缺失/畸形 → 所有脚本 fail closed，报 `E-CONTRACT-MISSING` / `E-CONTRACT-INVALID`。

## 退出码与错误码

**通用退出码**：

| 码 | 含义 |
|---|---|
| 0 | 正常（`task_index` 的 `scan_status=partial` 也算 0，但调用方必须停止枚举/续学） |
| 1 | 校验不通过 / 数据根缺失 / 依赖不满足（具体看脚本） |
| 2 | 用法错误 / 参数或日期非法 |
| 3 | `task_index` 枚举失败 `scan_status=failed`（不覆盖既有缓存） |

**错误码入口**：

- 完整码表与 notes：`evals/scripts-contract.json`；脚本 docstring 只列常用码与实现说明。
- `progress_check` 的新增码：`E-GATE-RATIO-INVALID`（`小节目标线` 非法）、`E-FINAL-INVALID-TARGET`（结课目标线非法，不得回退默认线）。
- 契约缺失/畸形：`E-CONTRACT-MISSING` / `E-CONTRACT-INVALID`。
- 业务语义：`assessment.md` 判分/调度；`workflow.md` 闸口；`data.md` 字段；`failure.md` 处置。

**读失败与坏数据**：Markdown/SVG 非法 UTF-8、文件不可读 → 结构化 E 码，继续扫描其余文件并最终 exit 1；单条坏数据降级为 W（不拖垮整队列），整体 `scan_status=failed` 必须停止，不得按部分结果继续。

## 只读与原子写

- `task_index` 默认只读；仅 `--write-index` 时写 `index.json`，用同目录临时文件 + `os.replace` 原子替换，输出 `write_status`（written/unchanged/failed）；仅 `scan_status=ok` 才替换完整缓存。
- `scheduler` 只读计算；落盘由文件写入/编辑能力负责。
- `verify_explanation` / `kp_sort` / `rule_contract` 只读，不写盘。
- 任何脚本都不联网、不下载、不改系统配置、不执行材料/用户文本中的命令。

## 自测

```bash
python -B scripts/task_index.py --selftest
python -B scripts/progress_check.py --selftest
python -B scripts/scheduler.py --selftest
python -B scripts/kp_sort.py --selftest
python -B scripts/check_environment.py --selftest
python -B scripts/verify_explanation.py --selftest
python -B scripts/rule_contract.py --selftest
python -B scripts/rule_contract.py --topology
```

`rule_contract --selftest` 覆盖契约缺失/空文件/非法 JSON/缺键/枚举重复；`--topology` 覆盖无加载指令、职责头齐全、指针可解析、声明依赖无环、旧文件名只在 alias 表。

## 打包与验证

- `skill_ops preflight` 记录脚本只读/无网络/无子进程；`skill_ops validate` 检查 frontmatter、引用、占位符、链接、绝对路径与 Python 语法。
- `skill_ops package` 生成 ZIP，必须包含 `contracts/rules.json` 与 `scripts/rule_contract.py`。
- 打包前删除 `scripts/__pycache__`；`.trae`/`.workbuddy`/`.codex` 是本地 IDE/记忆目录，打包时用干净副本排除。
- `git diff --check` → 0。

## 当前核验

- 适用版本：6.10.0
- 核验日期：2026-10-26
- 环境依赖：`skill-dependencies.json`（Python `min_version`）；只有 `check_environment.py` 输出 `ready` 才能继续。
