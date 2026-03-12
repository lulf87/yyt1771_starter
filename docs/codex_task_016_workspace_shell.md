# Task-016：工作台信息架构冻结与 `/workspace/{session_id}` 空壳

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- `docs/ui_information_architecture_v1.md`
- 当前项目中的 `src/webapp/`

## 任务目标

在不大改现有首页的前提下，正式引入“**试验工作台**”概念，并先做最小空壳页面：

- 新增 `/workspace/{session_id}`
- 落地顶部状态栏 + 左侧步骤导航 + 中央主工作区 + 右侧信息面板 的骨架
- 先不做复杂交互
- 先让 replay/mock 的会话结果能跳转到工作台页面

这轮是 **UI 信息架构冻结 + 页面骨架**，不是最终完整 UI 改版。

---

## 约束

1. 视觉风格参考 `af-analyzer`，但版面结构按 `docs/ui_information_architecture_v1.md` 执行。
2. 不引入前端工程化。
3. 不新增 `frontend/` 顶层目录。
4. 不让页面直接碰 `camera/temp/plc/vision/curve/sync`。
5. 不修改 `core` 契约。
6. 不做真实设备联调。

---

## 本轮要做的事

### 1. 新增工作台页面路由
建议：
- `GET /workspace/{session_id}`

要求：
- 页面可以读取 session_id
- 页面可展示最小会话上下文
- 不存在的 session_id 可返回 404 或最小错误页，任选一种，但请说明

### 2. 新增工作台模板
建议新增：
```text
src/webapp/templates/workspace.html
```

页面最小区域：
- 顶部状态栏
- 左侧步骤导航（6 步）
- 中央主工作区占位
- 右侧结果/参数面板占位

建议步骤标题：
1. 准备
2. 采集
3. 处理
4. 计算
5. 调整
6. 存储

### 3. 增加最小静态交互
在现有 `app.js` 中增加：
- 从首页 session 列表或运行结果跳转到 `/workspace/{session_id}`
- 工作台页面读取当前 session_id
- 若能方便实现，可在工作台加载当前 summary 的最小信息

### 4. 首页增加进入工作台入口
要求：
- 最近会话列表中每条增加“Open Workspace”入口
- run-mock / run-replay 成功后，也提供进入工作台的入口或自动跳转（二选一，建议先加按钮，不自动跳转）

### 5. 增加最小测试
至少新增：
- `tests/webapp/test_workspace_ui.py`

覆盖：
- `/workspace/{session_id}` 返回 200（针对存在的 session）
- HTML 中包含关键 hook：
  - `workspace-shell`
  - `workspace-stepper`
  - `workspace-main`
  - `workspace-sidepanel`
- 首页 HTML 或静态 JS 中存在进入工作台的挂钩

---

## 允许修改

- `docs/ui_information_architecture_v1.md`
- `src/webapp/app.py`
- `src/webapp/routes/` 下新增或修改 UI 路由
- `src/webapp/templates/**`
- `src/webapp/static/app.js`
- `src/webapp/static/app.css`
- 相关测试文件

## 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要新增 `frontend/`
- 不要引入 React/Vue/Vite
- 不要把工作台做成复杂实时控制台
- 不要做最终参数调整逻辑

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
