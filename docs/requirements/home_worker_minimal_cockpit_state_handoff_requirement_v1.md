# Home Worker Minimal Cockpit State / Handoff Requirement v1

Updated on 2026-04-01
Status: CANONICAL_REQUIREMENT_ADDENDUM
Clarifies implementation scope of:
- `home_worker_minimal_cockpit_requirement_v1.md`
- `home_workspace_shell_requirement_v1.md`
- `live_setup_freeze_roi_tracking_requirement_v1.md`

## Purpose

这份 requirement 用于把首页一线工人极简操作面在工程实现上最容易分叉的 4 个边界锁死：

1. 默认首屏把工程状态卡收掉以后，最小 `ready` 信号到底还留不留
2. 完成态只剩 `保存数据 / 进入分析` 后，`进入分析` 的目标 session 到底如何继续保持确定性
3. `保存数据` 到底是新的持久化动作，还是面向操作员的导出 / 确认动作
4. 温控设置确认之后如果又改 ROI / sensitivity / 温度 / 功率，页面状态机应如何回退

它解决的不是新的视觉方向问题，而是：

> 避免首页在变得更干净以后，反而因为状态语义不清而让实现出现分叉。

如果本文件与：

- `home_worker_minimal_cockpit_requirement_v1.md`

冲突，则：

- `home_worker_minimal_cockpit_requirement_v1.md` 继续定义首页默认到底显示什么、不显示什么
- 本文件进一步冻结 worker-minimal cockpit 的 readiness signal、completion handoff、save semantics 和 post-confirm state transitions

如果本文件与：

- `home_workspace_shell_requirement_v1.md`

冲突，则：

- `home_workspace_shell_requirement_v1.md` 继续定义 `Compact Result -> Workspace` 的 deterministic target rule 和 DOM / API guardrails
- 本文件定义 worker-minimal completion dock 仍应如何继承这些规则

如果本文件与：

- `live_setup_freeze_roi_tracking_requirement_v1.md`

冲突，则在 ROI / sensitivity 触发 recapture + recompute、以及温控设置确认的上位语义上，仍以 `live_setup_freeze_roi_tracking_requirement_v1.md` 为准。

---

## Scope Boundary

这份 requirement 只约束下面这类工作：

- [index.html](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/templates/index.html)
- [app.css](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/static/app.css)
- [app.js](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/static/app.js)
- 与首页 handoff 直接相关的 [workspace.html](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/templates/workspace.html)

它不直接要求：

- 新增 backend API
- 修改 API response contract
- 修改 session schema
- 修改 ROI / A-B detection algorithm
- 修改 AFAS analysis contract

但如果现有 route / schema / client state 还无法表示当前 run 的：

- 温控设置包
- 温控设置 confirmed 状态
- 因 ROI / sensitivity / fresh-frame recompute 导致的 ready-to-run 回退

则必须做最小 supporting contract extension。

它冻结的是：

> worker-minimal cockpit state semantics and completion handoff rules

---

## Frozen Decisions

### R1. Home must retain a tiny readiness signal even after the large status cards are removed

首页默认首屏虽然不再显示 `系统 / 配置 / 模式` 大卡，但仍必须保留一个极简 `ready` 信号。

允许的实现形式包括：

- `Ready / Not Ready` pill
- 单行 `设备就绪 / 未就绪` 状态
- 小型健康灯 + 状态文案

这枚 readiness signal 必须满足：

1. 默认可见
2. 弱于实时预览与主操作链
3. 不重新引回 `Profile / Mode / backend` 等工程上下文大卡

也就是说：

> 可以去掉工程状态大卡，但不能把“现在到底能不能开始做 setup”也一起删掉。

### R2. Worker-minimal completion dock must still expose the exact workspace target

首页完成态虽然不再显示大块 `Compact Result` 摘要卡，但 `进入分析` 仍必须继续服务一个 deterministic workspace target。

因此完成态动作区必须保留一个极轻的 target context，例如：

- `session id`
- `session state`

并且：

1. `进入分析` 必须永远打开这一个被显示出来的 target session
2. 这个 target session 的选择顺序仍以 [home_workspace_shell_requirement_v1.md](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/docs/requirements/home_workspace_shell_requirement_v1.md) 中已冻结的 deterministic rule 为准
3. 不允许把 session target 完全藏掉，只剩一个无法判断去向的 `进入分析` 按钮

这条 requirement 的重点不是恢复旧摘要卡，而是保留：

> 一个轻量但明确的 handoff target。

### R3. `保存数据` is an operator-facing export / confirm action over already-persisted results

首页完成态中的 `保存数据` 语义进一步冻结为：

- 已持久化测试产物的保存确认入口
- 或已持久化测试产物的导出 / 下载入口

它明确不是：

- 新的 pre-run setup save
- 替代 `Save Definition` 的新名字
- 一个要求新增 persistence API 的后端动作

因此本轮实现应默认采用：

> 复用系统现有持久化结果，把 `保存数据` 做成 operator-facing 的确认 / 导出语义。

如果后续要把 `保存数据` 扩展成新的持久化协议，那必须是另一轮 requirement，而不是在当前 minimal cockpit refactor 中顺手扩大 scope。

### R3a. Completed home state persists until the operator explicitly starts a new test

实时测试结束后，无论是自动到目标温度停止、手动停止，还是失败但已有可分析数据，首页都必须把这个 run 作为当前 completion target 保持住。

状态保持规则如下：

1. 从首页进入数据分析页，再返回首页时，仍显示同一个完成 run 的过程曲线、completion dock 和 `进入分析` target
2. 首页刷新或重新 bootstrap 时，如果 session storage 中的当前 live run 已经是 terminal 状态，不得自动创建新的 live setup run
3. 只有用户二次确认 `新测试` 后，首页才允许清空当前完成结果、创建新的 live setup run，并重新启动预览 setup 流程
4. `新测试` 是显式重置动作，不替代 `保存数据`，也不改变 `进入分析` 的 deterministic session target 规则

这条要求的目的，是避免完成结果在 home / workspace 往返时丢失，让 operator 在决定保存、分析或开始下一次测试之前始终面对同一个当前结果。

### R4. Post-confirm temperature-setting state must be explicit and event-driven

温控设置确认之后，首页不能只靠“当前看起来字段都填了”来判断是否还能开始测试，而必须遵守显式状态机。

当前冻结的事件规则如下：

1. 如果用户修改下面任一温控字段：
   - 目标温度
   - 温度功率
   - 控制方式
   那么当前 `temperature settings confirmed` 必须被清空
   - `开始测试` 必须重新 disabled
   - 直到用户再次执行温控设置确认

2. 如果用户修改 ROI 几何、`Sensitivity`，或主动触发一次新的 `A/B` 重算：
   - 系统仍必须遵守上位 requirement 的“先抓新帧，再重算 `A/B`”
   - `开始测试` 必须临时 disabled
   - 等到新的 `A/B` 已生成且结果有效后，页面才可恢复到可开始测试
   - 只要温控设置字段没有变化，`temperature settings confirmed` 不必自动清空

3. 如果 `A/B` 进入下列任一状态：
   - low confidence
   - recomputing
   - no valid result on latest frame
   那么 `开始测试` 都不得继续保持 enabled

4. 只有同时满足下面 3 个条件时，页面才允许进入 ready-to-run：
   - ROI 有效
   - 最新一轮自动 `A/B` 已在新抓帧上得到有效结果
   - 当前温控设置包已被显式确认：
     - target temperature
     - manual mode
     - power

这条 requirement 的目的，是避免出现：

- 温度或功率已经变了但页面仍显示可开始测试
- `A/B` 已因 ROI / sensitivity 变化而重算，但按钮仍保持旧的 ready 状态

### R5. This addendum is about semantics, not visual rollback

本文件不要求：

- 恢复 hero
- 恢复 journey ribbon
- 恢复 `系统 / 配置 / 模式` 大卡
- 恢复三列 `Compact Result` 摘要卡

它只要求：

> 在保持首页极简操作面的前提下，把实现边界锁到不会让前端各写各的。
