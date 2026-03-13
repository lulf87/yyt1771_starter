# Task-018：Workspace 阶段状态展示与右侧摘要重构

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- `docs/ui_information_architecture_v1.md`
- `docs/workspace_page_breakdown_v1.md`
- `docs/workspace_stage_mapping_v1.md`
- 当前项目中的：
  - `src/webapp/templates/workspace.html`
  - `src/webapp/static/app.js`
  - `src/webapp/static/app.css`
  - `src/webapp/routes/session.py`

## 任务目标

把当前 workspace 的左侧 stepper 从“静态展示”推进为“会话阶段状态展示”，并把右侧摘要区整理成更清晰的层级。

这轮不做真实步骤切换，不做参数调整，不改后端核心契约。

---

## 背景约束

1. 当前已经有：
   - `/workspace/{session_id}`
   - summary API
   - detail API
   - replay 曲线与关键帧展示
2. 当前工作台已经能显示：
   - session summary
   - replay detail
   - curve
   - key frames
3. 需要在不加重后端复杂度的前提下，让页面更有“阶段感”和“流程感”。
4. 风格仍参考 `af-analyzer`，但结构必须遵守工作台 IA。
5. 不允许引入前端工程化。

---

## 本轮要做的事

### 1. 在前端增加阶段映射逻辑

根据现有 summary/detail，在前端推导出 6 步的状态。

最小步骤：
1. 准备
2. 采集
3. 处理
4. 计算
5. 调整
6. 存储

建议状态集合：
- `done`
- `active`
- `todo`
- `error`（可选）

建议映射请按 `docs/workspace_stage_mapping_v1.md` 执行。

要求：
- 不新增复杂后端状态机字段
- 不修改 `core` 契约
- 允许在 JS 里做最小状态推导

### 2. Stepper 视觉状态化

要求：
- 每一步都能显示当前状态
- `active` 明显高亮
- `done` 与 `todo` 有清晰区分
- `error`（若实现）有最小可辨识样式
- 当前步建议仍默认是“计算”

建议 hook：
- `workspace-stepper`
- `workspace-step`
- `workspace-step-status`

### 3. 右侧摘要区重构

将右侧 side panel 整理成 4 个清晰卡片：

#### A. Workflow Stage
至少显示：
- current_stage
- session_state
- source/mode
- 简短说明

#### B. Session Summary
至少显示：
- session_id
- point_count
- af95

#### C. Detail Snapshot
至少显示：
- detail 是否存在
- points 数量
- key_frames 数量

#### D. Quick Actions
至少显示：
- Return Home
- Refresh Workspace

要求：
- 不新增复杂操作
- 只是层次重构

### 4. 页面空态/异常态补齐

要求：
- session failed 时，stepper 可体现异常
- detail 缺失时，stage mapping 仍能工作
- 不要因为 detail 缺失导致整个 side panel 崩掉

### 5. 样式微调

继续保持当前深色工作台风格，但只做最小必要样式：
- step 状态
- side panel 分层
- 信息可读性增强

不要大改整体视觉。

### 6. 补测试

至少新增或修改：
- `tests/webapp/test_workspace_ui.py`

覆盖：
- 页面 HTML 中包含新的阶段/摘要 hook
- JS 中存在阶段映射相关逻辑痕迹，或通过页面行为测试覆盖
- detail 缺失时页面结构仍成立
- 若你实现 error 状态，也请补对应最小测试

---

## 允许修改

- `docs/workspace_stage_mapping_v1.md`
- `src/webapp/templates/workspace.html`
- `src/webapp/static/app.js`
- `src/webapp/static/app.css`
- `tests/webapp/test_workspace_ui.py`

## 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要新增 `frontend/`
- 不要引入 React/Vue/Vite
- 不要做真正步骤切换
- 不要做参数调整逻辑
- 不要做 live 实时采集映射
- 不要新增复杂后端状态机

---

## 设计要求

1. 这是“阶段感增强”，不是最终流程引擎。
2. 页面仍然必须通过现有 API 获取数据。
3. 小步推进，避免一次做太重。
4. 保持当前工作台整体结构不变。

---

## 验收命令

至少运行：

```bash
pytest -q
```

建议补充：

```bash
python -m src.webapp.serve --profile dev_mock
```

---

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
