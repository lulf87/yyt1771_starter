# WP-A：Adjustment MVP（大工单）

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- `docs/adjustment_contract_v1.md`
- `docs/workspace_adjustment_preview_v1.md`
- `docs/adjustment_mvp_breakdown_v1.md`
- 当前项目中的：
  - `src/storage/session_adjustments.py`
  - `src/workflow/adjustments.py`
  - `src/webapp/routes/session.py`
  - `src/webapp/schemas.py`
  - `src/webapp/templates/workspace.html`
  - `src/webapp/static/app.js`
  - `src/webapp/static/app.css`

## 任务目标

一次性完成 **Adjustment MVP**：

1. 让 workspace 支持最小可编辑 adjustment draft
2. 支持 draft 保存
3. 支持 apply adjustment
4. 展示 auto result 与 latest result
5. 展示 applied version history
6. 保持当前 replay/mock/workspace 既有能力不回退

---

## 范围定义

### 本轮必须完成
- 基于现有 adjustment API 完成前端接线
- 工作台增加最小可编辑 adjustment 区
- 当前优先支持 `af95`
- reason 输入可用
- Save Draft / Apply Adjustment 可用
- version history 可展示
- latest result 可展示

### 本轮不要扩散
- 不做 ROI 编辑
- 不做 threshold/baseline/smoothing 调整
- 不做 As / Af / Af-tan 编辑逻辑
- 不做 live 模式接入
- 不引入前端工程化
- 不新增 `frontend/` 顶层目录
- 不修改 `core` 契约

---

## 你可以自行拆分的子任务（建议，不强制）
你可以自主决定合理顺序，但建议至少覆盖以下子任务：

### 子任务 A：后端契约与 API 收尾
检查并必要时完善：
- adjustment schema 是否足够前端使用
- GET/PUT/POST adjustment API 的错误路径与返回结构
- applied version 序列的稳定性
- latest_result 推导是否正确

### 子任务 B：workspace UI 升级
把 Adjustment Preview 升级成 Adjustment MVP：
- Automatic Result
- Latest Result
- Draft Editor
- Adjustment Status
- Version History

### 子任务 C：交互与刷新
完成：
- 页面初始加载 adjustment state
- Save Draft
- Apply Adjustment
- apply 成功后的局部刷新
- 错误提示与空态

### 子任务 D：测试补齐
补全：
- storage/workflow/API/UI 层关键路径测试

你可以合并实现，但最终结果必须同时满足这些能力。

---

## 详细要求

### 1. Adjustment API
应至少可用并经过测试：
- `GET /api/session/{session_id}/adjustment`
- `PUT /api/session/{session_id}/adjustment/draft`
- `POST /api/session/{session_id}/adjustment/apply`

要求：
- session 不存在 -> 404
- apply 时 draft 不存在 -> 400
- override key 非法 -> 合理校验错误
- latest_result 与 auto_result 正确区分

### 2. Workspace UI
在 workspace 中至少展示：

#### Automatic Result
- Auto Af95
- Auto result source

#### Latest Result
- Latest Af95
- Latest result source
- Latest version（如有）

#### Draft Editor
- `af95` 可编辑
- `reason` 可编辑
- Save Draft 按钮
- Apply Adjustment 按钮

#### Adjustment Status
- has draft
- applied count
- manual override state

#### Version History
- version
- reason
- created_at
- result_before.af95
- result_after.af95

### 3. 交互
要求：
- 页面加载后自动拉 adjustment state
- Save Draft 成功后，draft 状态更新
- Apply Adjustment 成功后：
  - draft 清空
  - latest_result 更新
  - version history 增加
  - workspace 局部刷新
- 失败时有最小错误提示

### 4. UI 约束
- 继续只用原生 JS
- 保持当前工业深色风格
- 不大改整个 workspace 总布局
- 允许对右侧摘要与中央 adjustment 区做重组，但不要破坏 curve/keyframe 主结构

### 5. 测试要求
至少补齐或修改：
- `tests/storage/test_session_adjustments.py`
- `tests/workflow/test_adjustments.py`
- `tests/webapp/test_adjustment_api.py`
- `tests/webapp/test_workspace_ui.py`

测试至少覆盖：
- 无 artifact 时 adjustment state 组装正常
- PUT draft 后可读回
- POST apply 后 draft 清空、版本增加、latest_result 更新
- 页面存在 Adjustment MVP 关键 hook
- 页面可显示 auto/latest/draft/version history
- API 错误路径可测

---

## 允许修改

- `docs/adjustment_mvp_breakdown_v1.md`
- `src/storage/session_adjustments.py`
- `src/workflow/adjustments.py`
- `src/webapp/app.py`
- `src/webapp/deps.py`
- `src/webapp/routes/session.py`
- `src/webapp/schemas.py`
- `src/webapp/templates/workspace.html`
- `src/webapp/static/app.js`
- `src/webapp/static/app.css`
- 相关测试文件

## 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要新增 `frontend/`
- 不要引入 React/Vue/Vite
- 不要引入复杂状态机
- 不要让 apply 直接改写 SQLite summary
- 不要同时扩展到 live 模式

---

## 设计要求

1. 这是 Adjustment MVP，不是最终完整调整系统。
2. 当前优先把 `af95` 这条链路打通。
3. 自动结果、最新结果、草稿、已应用版本必须明确区分。
4. 所有历史修改必须可追溯。
5. 优先小步收口，但这次作为一个大工单一次完成。

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
