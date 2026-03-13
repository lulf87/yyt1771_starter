# Task-019：Workspace 计算视图强化与点帧联动

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- `docs/ui_information_architecture_v1.md`
- `docs/workspace_page_breakdown_v1.md`
- `docs/workspace_stage_mapping_v1.md`
- `docs/workspace_computation_view_v1.md`
- 当前项目中的：
  - `src/webapp/templates/workspace.html`
  - `src/webapp/static/app.js`
  - `src/webapp/static/app.css`

## 任务目标

把当前 `/workspace/{session_id}` 的“计算视图”做得更清楚：

- 曲线主图阅读性增强
- 点 / 关键帧双向轻联动
- 右侧增加 Active Selection 信息卡片
- Af95 表达更清晰
- 保持现有工作台结构不变

这轮仍然不做手动调整，不做 ROI 编辑，不做 live 实时接入。

---

## 背景约束

1. 当前工作台已经有：
   - summary 加载
   - detail 加载
   - 曲线展示
   - 关键帧展示
   - stepper
   - 右侧摘要卡片
2. 需要继续保持：
   - Mac 上开发调试
   - Windows 上最终运行
   - 浏览器作为统一入口
3. 不能引入前端工程化。
4. 不允许引入复杂图表库。

---

## 本轮要做的事

### 1. 曲线图阅读性增强

要求：
- 曲线标题更明确
- 增加最小坐标标签：
  - X：Temperature (°C)
  - Y：metric_raw
- Af95 标记更清晰
- 当前选中点更清晰
- 点数不足或 detail 缺失时有友好空态

建议 hook：
- `workspace-curve`
- `workspace-curve-title`
- `workspace-curve-empty`
- `workspace-active-point`

### 2. 点 / 关键帧双向轻联动

要求：
- 点击关键帧卡片 -> 高亮曲线点
- 点击曲线点 -> 高亮关键帧卡片（若可匹配）
- 当前选中对象写入 Active Selection 卡片

匹配策略可以从简：
- 优先按 timestamp_ms 匹配
- 若没有完美匹配，可按 index 对齐，但请说明

### 3. 新增 Active Selection 卡片

在右侧 side panel 中新增一块：
- `Active Selection`

至少显示：
- label
- timestamp_ms
- celsius
- metric_raw
- metric_norm（若存在）
- feature_point_px
- quality（若存在）

若无选中对象，显示最小空态。

建议 hook：
- `workspace-active-selection`
- `workspace-active-label`
- `workspace-active-timestamp`
- `workspace-active-celsius`
- `workspace-active-metric-raw`
- `workspace-active-feature-point`

### 4. Af95 结果强化

要求：
- 在右侧摘要中提升 Af95 的视觉层级
- 明确单位显示
- 若无值则显示 `N/A`

### 5. 样式微调

要求：
- 保持当前深色工业风
- 选中关键帧卡片有明显高亮
- 选中曲线点有明显高亮
- Active Selection 卡片可读性明显

不要大改整体布局。

### 6. 补测试

至少新增或修改：
- `tests/webapp/test_workspace_ui.py`

覆盖：
- 页面 HTML 中存在新增 hook
- detail 存在时，页面结构支持 active selection
- detail 缺失时，active selection / curve / keyframes 空态可成立
- 若静态 JS 中加入了明确的函数名或钩子，可补最小断言

---

## 允许修改

- `docs/workspace_computation_view_v1.md`
- `src/webapp/templates/workspace.html`
- `src/webapp/static/app.js`
- `src/webapp/static/app.css`
- `tests/webapp/test_workspace_ui.py`

## 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要新增 `frontend/`
- 不要引入 React/Vue/Vite
- 不要引入复杂图表库
- 不要做参数调整
- 不要做 live 实时接入
- 不要新增复杂后端逻辑

---

## 设计要求

1. 这是“计算视图强化”，不是参数调整界面。
2. 页面必须继续通过现有 API 获取数据。
3. 小步推进，不要大改整体工作台结构。
4. 视觉风格继续参考当前工业深色风格。

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
