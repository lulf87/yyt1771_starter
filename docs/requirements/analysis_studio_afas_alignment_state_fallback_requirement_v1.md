# Analysis Studio AFAS Alignment State / Fallback Requirement v1

Updated on 2026-03-29
Status: CANONICAL_REQUIREMENT_ADDENDUM
Clarifies implementation scope of:
- `analysis_studio_afas_alignment_requirement_v1.md`
- `home_workspace_shell_requirement_v1.md`
- `afas_full_postprocessing_migration_requirement_v1.md`

## Purpose

这份 requirement 用于把 workspace 向 AFAS 风格分析界面收敛后，最容易在实现阶段分叉的 4 个边界锁死：

1. `分析参数` 或 `通道选择` 改变后，分析到底何时触发
2. `afas_available=0`、single-channel、summary-only 等状态下，默认界面如何降级
3. replay context 在默认首屏到底放在哪里
4. 向 AFAS 内容模型收敛时，如何继续保留现有 DOM / JS / test-anchor guardrails

它解决的不是新的视觉方向问题，而是：

> 避免 Analysis Studio 在“更像 AFAS”之后，反而因为触发语义、降级路径和兼容边界不清而出现多个实现分支。

如果本文件与：

- `analysis_studio_afas_alignment_requirement_v1.md`

冲突，则：

- `analysis_studio_afas_alignment_requirement_v1.md` 继续定义 workspace 默认首屏的 AFAS-style content model
- 本文件进一步冻结参数触发语义、fallback states、replay placement 和 first-pass refactor guardrails

如果本文件与：

- `home_workspace_shell_requirement_v1.md`

冲突，则：

- `home_workspace_shell_requirement_v1.md` 继续定义 Home / Workspace 的 surface 分工、session-scoped shell 语义，以及 DOM / API / test-anchor 护栏
- 本文件定义 AFAS-style workspace 在这些护栏下应该如何实现

如果本文件与：

- `afas_full_postprocessing_migration_requirement_v1.md`

冲突，则：

- `afas_full_postprocessing_migration_requirement_v1.md` 继续定义算法、参数、图表、结果与导出 capability parity
- 本文件只定义这些能力在默认分析界面上的 operator-facing 触发方式与降级方式

---

## Scope Boundary

这份 requirement 只约束下面这类工作：

- [workspace.html](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/templates/workspace.html)
- [app.css](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/static/app.css)
- [app.js](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/static/app.js)
- 必要时的 [ui.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/routes/ui.py)

它不直接要求：

- 新增 backend API
- 修改 AFAS analysis contract
- 修改 artifact schema
- 修改 replay / session backend contract
- 修改 AFAS 核心算法

它冻结的是：

> AFAS-style Analysis Studio first-screen behavior under the current session-scoped workspace contract

---

## Frozen Decisions

### R1. The default AFAS-style analysis surface must auto-load analysis rather than rely on a primary manual rerun step

从本 requirement 起，workspace 默认 operator path 在 `afas_available=1` 时冻结为：

```text
进入 workspace
-> 自动加载当前 session 的 active channel 分析
-> 查看结果
-> 必要时改通道 / 改参数
-> 自动刷新分析结果
-> 导出
```

因此：

1. workspace 首次加载且 `afas_available=1` 时，默认应自动加载当前 active channel 的 AFAS 分析结果
2. `通道选择` 改变时，应自动切换并刷新分析
3. `分析参数` 改变时，也应自动刷新分析，但触发粒度必须是 commit-driven，而不是每个键击都立即请求

当前冻结的 commit 语义如下：

- slider / select / stepper 类控件：
  - 在值提交后自动刷新
- numeric input 类控件：
  - 在 `blur`、`Enter`、或等价提交事件后自动刷新
- 不要求对每个正在输入中的字符都重新分析

这条 requirement 的重点不是禁止实现 debounce，而是冻结：

> 默认 operator-facing AFAS workflow 不再把“点击运行分析按钮”当成必要主步骤。

如果为了兼容现有 JS 或测试需要，现有 `Run AFAS` 钩子可以继续保留，但它应降级为：

- hidden compatibility hook
- secondary internal fallback

而不是继续占据默认主操作位。

### R2. Fallback states must be explicit for `afas_available=0`, single-channel, and summary-only sessions

AFAS-style first screen 不是“只在理想多通道 session 上好看”，它还必须冻结下面 3 种现实状态的表现。

#### 1. `afas_available=0`

当 session 没有 AFAS dataset 时：

- 仍保留轻量 session strip
- 主分析区显示明确 empty state
- empty state 必须直接说明：
  - 当前 session 没有 AFAS dataset
  - 因此无法显示 AFAS 总览图、单通道切线分析和结果面板
- `通道选择`、`分析参数`、`导出` 不得继续表现为可正常工作的主控件
  - 可以 hidden
  - 也可以 disabled

允许同时保留 replay context，但：

- replay context 只是补充上下文
- 不得因为 AFAS dataset 缺失，就把默认首屏重新退回旧的 rail / sticky summary / engineering cards

#### 2. single-channel dataset

当 dataset 只有一个有效通道时：

- 分析主屏仍然保留
- `通道选择` 不应继续占据与多通道等重的视觉层级

允许的实现方式包括：

- 单通道标签
- disabled selector
- 极简单选 chip

不建议继续渲染一个视觉重量很高、但实际上只有一个选项的 chooser 区块。

#### 3. summary-only or no replay detail

当 session 只有 summary，或没有 replay detail 时：

- AFAS 分析主屏的存在与否，仍以 `afas_available` 为准
- replay context 可以明确提示 detail 缺失
- 但 detail 缺失本身，不得把页面重新退回“研发过程面板”

也就是说：

> replay detail 是可选上下文，不是 AFAS-style first screen 的前置条件。

### R3. Replay placement is fixed to a compact context strip / foldout above the main AFAS analysis area

当前第一轮实现中，replay 在默认首屏中的落位冻结为：

1. 顶部轻量 session strip
2. 紧接其后的 compact replay context strip
3. 再往下才是：
   - `通道选择`
   - `分析参数`
   - `总览图`
   - `单通道切线分析`
   - `分析结果`

这个 replay context strip 必须满足：

- 默认比 AFAS 主分析区轻
- 默认 collapsed 或 compact
- 只有在用户明确展开时，才露出更多 replay 内容

在当前 scope 内，不再允许把 replay placement 留给实现者自由选择成：

- 单独 context tab
- 页面 hero 曲线
- 与 AFAS 图表并列争夺默认首屏主焦点

这条 requirement 的目的是：

> 既保留 session-scoped product 的 replay 语义，又避免 replay 重新抢回 workspace 首屏。

### R4. AFAS-style refactor must preserve current DOM / JS / test anchors in the first pass

虽然默认界面要向 AFAS 收敛，但第一轮 refactor 仍必须继续遵守现有 shell guardrails。

因此当前冻结为：

1. 允许：
   - 重排 wrapper
   - 改变默认可见层级
   - 把旧 rail / sidepanel / engineering cards 移到 secondary screen、foldout 或 hidden state

2. 不允许在第一轮中直接破坏：
   - 现有 route contract
   - 现有 API contract
   - 现有 `id`
   - 现有 `data-testid`
   - 现有 `data-afas-available` 等 dataset hooks

3. 如果 AFAS-style 默认交互已经不再需要某个旧主按钮，例如 `Run AFAS`：
   - 也必须先保留它的兼容锚点
   - 或在同一轮里同步完成 JS 和测试适配
   - 不允许只为了“更像 AFAS”而先删掉现有 hook，再把兼容留给后续修补

这条 requirement 的重点不是反对 AFAS-style 收敛，而是冻结：

> 第一轮向 AFAS 收敛时，必须是兼容式重排，而不是破坏式重写。

### R5. This addendum locks behavior and degradation, not a new product role

本文件不要求：

- 把 workspace 改成独立 AFAS 上传器
- 放弃 session-scoped product
- 放弃 replay artifact
- 放弃 adjustment / version 等 secondary capability
- 改写 AFAS math / export contract

它只要求：

> 把 Analysis Studio 默认分析界面的触发语义、降级路径、replay 落位与兼容护栏先锁死，再进入实现。
