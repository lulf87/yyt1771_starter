# Task-021：手动调整数据契约与版本追踪骨架

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- `docs/adjustment_contract_v1.md`
- 当前项目中的：
  - `src/storage/session_artifacts.py`
  - `src/storage/sqlite_repo.py`
  - `src/workflow/session.py`
  - `src/webapp/schemas.py`
  - `src/webapp/deps.py`
  - `src/webapp/routes/session.py`

## 任务目标

在不开放真实手动调整 UI 的前提下，先建立“手动调整”的后端契约与版本追踪骨架：

- 自动结果与人工结果分离
- 支持 adjustment draft
- 支持 apply 形成版本历史
- 通过最小 API 读写 adjustment state
- 不破坏现有 mock/replay/session 逻辑

---

## 背景约束

1. 当前已经有：
   - session summary
   - replay detail artifact
   - workspace adjustment preview（只读）
2. 当前还没有：
   - adjustment version history
   - adjustment draft persistence
   - manual result contract
3. 本轮要优先做后端骨架，不先做 UI 改值界面。
4. 不允许修改 `core` 契约。

---

## 本轮要做的事

### 1. 新增 adjustment contract 文档
请将 `docs/adjustment_contract_v1.md` 视为本轮契约基线。

如你在实现中做了小调整，请同步更新文档，但不要扩大范围。

### 2. 增加 adjustment 持久化存储
建议新增：

```text
src/storage/session_adjustments.py
```

职责：
- 在 `artifact_dir/adjustments/<session_id>.json` 中保存 adjustment state
- 支持：
  - 读取原始 adjustment artifact
  - 保存 draft
  - 应用 draft 形成 version history

要求：
- 不影响现有 `session_artifacts.py`
- 不改现有 SQLite summary 存储
- 路径使用相对 artifact_dir 拼接

### 3. 增加最小 workflow/service 层封装
建议新增：

```text
src/workflow/adjustments.py
```

职责：
- 基于 session summary + adjustment artifact 组装 adjustment state
- 推导：
  - auto_result
  - latest_result
- 执行：
  - save_draft(...)
  - apply_draft(...)

要求：
- 不要把所有逻辑塞进 route
- 不新增复杂状态机
- 当前优先支持 `af95`，但结构对 `as_value / af_value / af_tan` 兼容

### 4. 新增 web API

建议新增：

- `GET /api/session/{session_id}/adjustment`
- `PUT /api/session/{session_id}/adjustment/draft`
- `POST /api/session/{session_id}/adjustment/apply`

#### GET adjustment
返回 adjustment state：
- session_id
- auto_result
- latest_result
- draft
- applied_versions

#### PUT draft
请求体建议：
```json
{
  "overrides": {
    "af95": 43.1
  },
  "reason": "visual confirmation"
}
```

行为：
- 保存或覆盖当前 draft
- 不修改 summary
- 不增加 applied_versions

#### POST apply
行为：
- 使用当前 draft 生成一个 applied version
- 清空 draft
- 返回更新后的 adjustment state

要求：
- 若 session 不存在 -> 404
- 若 draft 不存在而 apply -> 400
- 若 overrides key 非法 -> 422 或框架默认校验错误均可

### 5. 新增 schema
请在 `src/webapp/schemas.py` 中增加最小 schema，例如：
- `AdjustmentResultResponse`
- `AdjustmentDraftRequest`
- `AdjustmentDraftResponse`
- `AppliedAdjustmentVersionResponse`
- `AdjustmentStateResponse`

命名可微调，但要清晰表达结构。

### 6. 最小配置复用
本轮优先复用已有：
- `storage.artifact_dir`

不要新增复杂配置；也不要新开一套 adjustment 专用根目录。

### 7. 测试补齐

至少新增：
- `tests/storage/test_session_adjustments.py`
- `tests/webapp/test_adjustment_api.py`

可选新增：
- `tests/workflow/test_adjustments.py`

覆盖：
- session 不存在时 GET/PUT/POST 返回合理错误
- 首次 GET adjustment 时，若没有 artifact，也能基于 summary 组装默认 state
- PUT draft 后，draft 可读回
- POST apply 后：
  - draft 被清空
  - applied_versions 增加
  - latest_result 更新
- 多次 apply 版本号递增
- 非法 override key 有最小校验测试

---

## 允许修改

- `docs/adjustment_contract_v1.md`
- `src/storage/session_adjustments.py`
- `src/workflow/adjustments.py`
- `src/webapp/app.py`
- `src/webapp/schemas.py`
- `src/webapp/deps.py`
- `src/webapp/routes/` 下新增或修改 adjustment 路由
- 相关测试文件

## 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要做真正前端可编辑 UI
- 不要让 apply 直接改写现有 SQLite summary
- 不要新增 `frontend/`
- 不要引入复杂状态机

---

## 设计要求

1. 自动结果与人工结果必须分离。
2. 历史版本必须可追溯。
3. 本轮重点是契约和骨架，不是最终完整调整系统。
4. 优先小步推进，保持现有 session / replay / workspace 能继续工作。

---

## 验收命令

至少运行：

```bash
pytest -q
```

如果你新增了 API，也建议补充：
```bash
python -m src.webapp.serve --profile dev_mock
```

---

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
