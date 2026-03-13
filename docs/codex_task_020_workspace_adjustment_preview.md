# Task-020：Workspace Adjustment Preview 只读面板

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- `docs/ui_information_architecture_v1.md`
- `docs/workspace_page_breakdown_v1.md`
- `docs/workspace_stage_mapping_v1.md`
- `docs/workspace_computation_view_v1.md`
- `docs/workspace_adjustment_preview_v1.md`
- 当前项目中的：
  - `src/webapp/templates/workspace.html`
  - `src/webapp/static/app.js`
  - `src/webapp/static/app.css`

## 任务目标

在当前 workspace 已具备“曲线 + 关键帧 + Active Selection”的基础上，新增一个**只读的 Adjustment Preview 面板**，用于展示：

- 自动分析依据
- 当前选中对象的提取/分析上下文
- 未来可调整项的界面占位

这轮仍然不做真正参数修改，不做手动结果覆写。

---

## 背景约束

1. 当前工作台已经有：
   - Workflow Stage
   - Session Summary
   - Detail Snapshot
   - Active Selection
   - Curve + Key Frames
2. 当前 detail 数据主要来自 replay artifact。
3. 需要继续保持：
   - Mac 上开发调试
   - Windows 上最终运行
   - 浏览器作为统一入口
4. 不能引入前端工程化。
5. 不要让用户误以为当前版本已经支持真实手动调整。

---

## 本轮要做的事

### 1. 在 workspace 中增加 Adjustment Preview 区

建议位置：
- 中央主区中，位于 Key Frame Panel 下方

要求：
- 使用清晰标题，例如 `Adjustment Preview`
- 页面整体结构仍保持当前工作台不变
- 不大改首页与其他区域

建议 hook：
- `workspace-adjustment-preview`

### 2. 新增 Automatic Basis 卡片

至少展示：
- source
- point_count
- key_frame_count
- af95
- current_stage
- detail 是否存在
- 当前 active selection 的最小摘要

建议 hook：
- `workspace-adjustment-basis`
- `workspace-adjustment-source`
- `workspace-adjustment-point-count`
- `workspace-adjustment-keyframe-count`
- `workspace-adjustment-af95`

### 3. 新增 Extraction & Analysis Context 卡片

至少展示：
- ROI
- feature_point_px
- baseline_px
- quality
- threshold_value
- component_area
- metric_norm
- stage

要求：
- 没有值时显示 `N/A`
- 优先使用当前 active selection / 当前 detail 中已有数据
- 不新增后端接口

建议 hook：
- `workspace-adjustment-context`
- `workspace-adjustment-roi`
- `workspace-adjustment-feature-point`
- `workspace-adjustment-baseline`
- `workspace-adjustment-quality`
- `workspace-adjustment-threshold`
- `workspace-adjustment-component-area`

### 4. 新增 Future Adjustment Controls 卡片（只读/禁用）

建议展示三组：
- 图像处理参数
- 曲线分析参数
- 结果覆写

要求：
- 所有输入控件或按钮必须是 disabled / read-only
- 必须有明确提示：
  - `Coming soon`
  - `Read-only in current phase`
  - 或同类文案
- 不允许触发任何保存或修改行为

建议 hook：
- `workspace-adjustment-controls`
- `workspace-adjustment-coming-soon`

### 5. 与 Active Selection 联动

要求：
- 当当前选中点/帧变化时，Adjustment Preview 中的 basis/context 随之更新
- 若没有 active selection，则显示空态/`N/A`
- 不新增复杂交互，只复用当前已有的 active selection 逻辑

### 6. 左侧 stepper 微调

要求：
- 当前仍高亮“计算”
- “调整”步骤在视觉上显示为 ready/upcoming，而不是 active
- 不做真正步骤切换逻辑

### 7. 样式微调

要求：
- 保持当前深色工业风
- Adjustment Preview 使用卡片式分区
- 禁用控件视觉上清楚但不抢主图
- 不要大改整体布局

### 8. 补测试

至少新增或修改：
- `tests/webapp/test_workspace_ui.py`

覆盖：
- 页面 HTML 中包含 Adjustment Preview 相关 hook
- detail 缺失时 Adjustment Preview 仍可显示结构与空态
- 静态 JS 中存在 Adjustment Preview 更新逻辑痕迹，或通过页面结构测试覆盖
- “Future Adjustment Controls” 明确处于只读/coming soon 状态

---

## 允许修改

- `docs/workspace_adjustment_preview_v1.md`
- `src/webapp/templates/workspace.html`
- `src/webapp/static/app.js`
- `src/webapp/static/app.css`
- `tests/webapp/test_workspace_ui.py`

## 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要新增 `frontend/`
- 不要引入 React/Vue/Vite
- 不要新增复杂后端逻辑
- 不要做真正参数调整
- 不要做 live 实时接入
- 不要新增可写 API

---

## 设计要求

1. 这是“Adjustment Preview”，不是“Adjustment Editor”。
2. 页面必须继续通过现有 API 获取数据。
3. 不允许出现可实际修改结果的交互。
4. 小步推进，保持当前工作台结构稳定。

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
