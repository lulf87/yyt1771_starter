# Task-017：Workspace 第一版接入 replay detail

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- `docs/ui_information_architecture_v1.md`
- `docs/workspace_page_breakdown_v1.md`
- 当前项目中的：
  - `src/webapp/routes/ui.py`
  - `src/webapp/templates/workspace.html`
  - `src/webapp/static/app.js`
  - `src/webapp/static/app.css`
  - `src/webapp/routes/session.py`

## 任务目标

把当前 `/workspace/{session_id}` 从“结构空壳”推进成“replay 分析工作台第一版”：

- 页面加载后读取 session summary
- 页面加载后读取 replay detail
- 中央主区显示最小曲线图
- 中央主区显示关键帧预览
- 右侧面板显示 summary/detail 摘要
- 保持现有首页与 API 不被破坏

---

## 背景约束

1. 当前已经有：
   - `GET /api/session/{session_id}`
   - `GET /api/session/{session_id}/detail`
   - 首页控制台
   - `/workspace/{session_id}` 页面壳
2. 当前 replay detail 已包含：
   - `af95`
   - `points`
   - `key_frames`
3. 最终交互形式仍然是：
   - Mac 上开发调试
   - Windows 上最终运行
   - 浏览器作为统一入口
4. 视觉风格可参考 `af-analyzer`，但版面结构必须按工作台 IA 和页面拆解说明执行。
5. 不允许引入前端工程化。

---

## 本轮要做的事

### 1. 工作台页面读取 summary + detail

在工作台页面 JS 中：
- 解析当前 `session_id`
- 请求：
  - `GET /api/session/{session_id}`
  - `GET /api/session/{session_id}/detail`

要求：
- 使用现有 API
- 不新增重复 API
- 不绕开 API 直接访问存储层

### 2. 顶部状态栏与右侧摘要实化

至少在页面中展示：
- session_id
- state
- point_count
- af95
- source（若 detail 中存在）
- key frame 数量
- point 数量

建议使用明确的 hook id，例如：
- `workspace-session-id`
- `workspace-session-state`
- `workspace-af95`
- `workspace-point-count`
- `workspace-source`
- `workspace-keyframe-count`

### 3. 中央主区增加最小曲线图

要求：
- 使用原生 SVG 绘制折线
- X 轴使用 `celsius`
- Y 轴使用 `metric_raw`
- 若存在 `af95`，画一个最小标记
- 若点数不足，显示友好提示而不是报错

建议 hook：
- `workspace-curve`
- `workspace-curve-empty`

### 4. 关键帧预览区

要求：
- 渲染 replay detail 的 key_frames
- 优先展示 first / middle / last
- 每张卡片显示：
  - label
  - timestamp_ms
  - metric_raw
  - feature_point_px
  - 灰度预览

灰度预览要求：
- 不引入图像库
- 用 Canvas 或简单 DOM 网格均可
- 因当前 replay 图像很小，直接渲染二维数组即可

建议 hook：
- `workspace-keyframes`
- `workspace-keyframe-card`

### 5. 轻联动

至少做一个简单联动：
- 点击关键帧卡片
- 高亮曲线中对应点

要求：
- 不做复杂 tooltip 系统
- 不做拖拽交互
- 不做参数调整

### 6. 错误态与空态

要求：
- summary 不存在时：返回 404 页面或最小错误页，任选一种，但请说明
- detail 不存在时：
  - 工作台页面仍可展示 summary
  - 中央区域显示 “No replay detail available”

### 7. 首页入口保持可用

要求：
- 最近会话中的“Open Workspace”入口继续可用
- mock/replay 成功后的“进入工作台”入口继续可用

### 8. 补测试

至少新增或修改：
- `tests/webapp/test_workspace_ui.py`
- 如你改动了首页挂钩，也可补 `tests/webapp/test_ui_shell.py`

覆盖：
- 工作台页面对存在 session 返回 200
- 页面 HTML 中包含关键 hook：
  - `workspace-shell`
  - `workspace-stepper`
  - `workspace-main`
  - `workspace-sidepanel`
  - `workspace-curve`
  - `workspace-keyframes`
- detail 缺失时页面空态合理
- 静态 JS 中存在 detail 拉取和关键 hook 使用痕迹，或通过页面行为测试进行验证

---

## 允许修改

- `docs/workspace_page_breakdown_v1.md`
- `src/webapp/routes/ui.py`
- `src/webapp/templates/workspace.html`
- `src/webapp/static/app.js`
- `src/webapp/static/app.css`
- 相关测试文件

## 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要新增 `frontend/`
- 不要引入 React/Vue/Vite
- 不要做 live 实时流接入
- 不要做参数调整/手动覆写逻辑
- 不要新增复杂图表库，优先原生 SVG/Canvas

---

## 设计要求

1. 这是“工作台第一版内容接线”，不是最终完整版分析界面。
2. 页面必须通过现有 API 获取 summary/detail。
3. 继续保持 `src.*` 绝对导入。
4. 视觉风格可轻度向 `af-analyzer` 靠拢，但不要破坏现有页面结构。
5. 小步推进，避免一次做太重。

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

如有条件，也请说明：
- 页面访问地址
- 打开 `/workspace/{session_id}` 后的预期表现

---

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
