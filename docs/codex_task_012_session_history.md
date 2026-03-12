# Task-012：会话历史列表 API 与页面展示

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目中的 `src/webapp/`
- 当前已经存在的：
  - `/`
  - `/health`
  - `/api/system/profile`
  - `/api/session/run-mock`
  - `/api/session/{session_id}`

## 任务目标

在现有最小 Web 页面壳基础上，再补一条“**查看历史会话**”能力：

- 后端新增一个最小历史列表 API
- 页面上展示最近若干条 session summary
- 点击按钮运行 mock session 后，历史列表自动刷新

这轮仍然不接真实设备，不做实时视频，不做前端工程化。

---

## 背景约束

1. 最终交互仍然是浏览器 + Python 后端。
2. 当前已经有：
   - profile 配置加载
   - health/profile API
   - 单次 mock session 执行
   - 按 session_id 查询单条 summary
   - 最小 HTML/JS 页面壳
3. 需要继续保持：
   - Mac 上开发调试
   - Windows 上最终运行
   - 页面只通过 API 获取数据
4. 不允许让 UI 直接读设备适配器。

---

## 本轮要做的事

### 1. 为存储层补最小“列表”能力

请在不破坏现有行为的前提下，为 SQLite summary 仓库补一个只读列表接口，例如：

- `list_summaries(limit: int = 10) -> list[SessionSummary]`

要求：
- 按创建时间倒序，最新在前
- limit 做基本正数校验
- 不要改已有 `get_summary(session_id)` 行为

如果你认为更适合放到新的只读方法，也可以，但不要扩大设计范围。

### 2. 新增历史列表 API

建议新增：

- `GET /api/session`

返回最小列表响应，例如：

```json
{
  "items": [
    {
      "session_id": "...",
      "state": "completed",
      "point_count": 5,
      "af95": 42.3
    }
  ]
}
```

要求：
- 支持可选 query 参数 `limit`
- 默认返回最近 10 条
- 对非法 limit 返回 422 或框架默认校验错误都可以

### 3. 页面增加“最近会话”区域

在当前 `index.html` 页面里增加一个简单区域：
- 标题：最近会话
- 一个列表容器
- 页面加载时拉取 `GET /api/session`
- 点击“Run Mock Session”成功后自动刷新列表

要求：
- 保持极简，不做复杂表格框架
- 可以用 `<ul>`、`<ol>`、`<div>` 列表
- 每条至少展示：
  - session_id
  - state
  - point_count
  - af95

### 4. 最小 JS 增量

继续使用原生 JS：
- 新增 `loadRecentSessions()`
- `bootstrap()` 时并行加载 health/profile/recent sessions
- run mock 后刷新 recent sessions

### 5. 测试补齐

至少新增或修改：
- `tests/storage/test_sqlite_repo.py`
- `tests/webapp/test_session_api.py`
- `tests/webapp/test_ui_shell.py`

覆盖：
- repo list 行为正确
- `/api/session` 返回列表
- 页面 HTML 中包含最近会话区域的关键 hook
- 静态 JS 中包含列表接口调用痕迹，或页面测试验证 hook 存在

---

## 允许修改

- `src/storage/sqlite_repo.py`
- `src/webapp/schemas.py`
- `src/webapp/routes/session.py`
- `src/webapp/templates/index.html`
- `src/webapp/static/app.js`
- 相关测试文件

## 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要引入前端工程化
- 不要新增 `frontend/` 顶层目录
- 不要接真实设备
- 不要改现有 API 的核心语义

---

## 设计要求

1. 页面只能通过 API 看历史列表，不要绕开 API 直接访问 repo。
2. 历史列表是“最小可用”，不是最终报表页。
3. 继续保持 `src.*` 绝对导入。
4. 让无真实设备环境下测试仍可运行。
5. 优先小改动。

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
