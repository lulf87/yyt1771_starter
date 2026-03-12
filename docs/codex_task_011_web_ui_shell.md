# Task-011：最小 Web 页面壳与浏览器交互

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目中的 `src/webapp/`
- 当前已经存在的：
  - `/health`
  - `/api/system/profile`
  - `/api/session/run-mock`
  - `/api/session/{session_id}`

## 任务目标

在不引入前端工程化的前提下，给项目增加一个**最小浏览器页面壳**，让用户可以在浏览器里直接看到：

- 系统健康状态
- 当前 profile
- 触发一次 mock session
- 查看最近一次 session 结果

这轮仍然不接真实设备，不做实时视频流，不做复杂前端框架。

---

## 背景约束

1. 最终交互形式已经确定为 Web。
2. 当前后端已经有最小 API 闭环。
3. 我们希望保持：
   - Mac 上源码开发调试
   - Windows 上最终运行
   - 浏览器作为统一交互入口
4. 不允许引入 `frontend/` 顶层目录，也不做 npm / vite / react 之类的工程化前端。

---

## 本轮要做的事

### 1. 在 `src/webapp/` 内增加最小模板与静态资源

建议目录：

```text
src/webapp/
  templates/
    index.html
  static/
    app.js
    app.css
```

要求：
- 不要新增顶层 `frontend/`
- 继续把页面资源收敛在 `src/webapp/` 内
- 页面结构保持简单、可读、可维护

### 2. 在 FastAPI app 中挂载静态文件并增加页面路由

建议：
- 挂载 `/static`
- 新增 `GET /` 或 `GET /ui` 页面路由
- 使用模板渲染最小页面

页面至少要包含这些区域：
- app 标题
- 当前 profile 展示区
- 健康状态展示区
- “运行 mock session”按钮
- 最近一次 session 结果展示区

### 3. 用最小原生 JS 调现有 API

要求：
- 不引入前端框架
- 只用最小原生 JavaScript
- 页面加载后请求：
  - `/health`
  - `/api/system/profile`
- 点击按钮后调用：
  - `POST /api/session/run-mock`
- 成功后把返回的 summary 展示到页面上

可选：
- 根据返回的 session_id 再调用一次 `GET /api/session/{session_id}` 做二次读取验证

### 4. 增加最小页面测试

至少新增：

```text
tests/webapp/test_ui_shell.py
```

覆盖：
- 页面路由返回 200
- HTML 中包含关键占位内容（例如标题、按钮文本、某个 data-testid 或元素 id）
- 静态文件可被挂载访问（至少测一个）

---

## 允许修改

- `src/webapp/app.py`
- `src/webapp/routes/` 下新增或修改页面路由
- `src/webapp/templates/**`
- `src/webapp/static/**`
- `tests/webapp/**`

## 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要让页面路由直接依赖 `camera/temp/plc/vision/curve/sync`
- 不要新增 `frontend/` 顶层目录
- 不要引入 React/Vue/Vite/npm 工程
- 不要做实时流媒体页面

---

## 设计要求

1. 浏览器页面只是 `webapp` 的一层外壳，不能把业务逻辑塞进模板。
2. 页面通过既有 API 获取数据，不要绕开 API 直接碰 workflow/storage。
3. 继续保持 `src.*` 绝对导入。
4. 让页面在没有真实设备时也可运行。
5. 页面样式保持极简，避免过度设计。

---

## 建议实现方向

- FastAPI 官方支持：
  - `StaticFiles`
  - `Jinja2Templates`
- 页面模板里用明确的 `id`，方便 JS 和测试定位：
  - `health-status`
  - `profile-name`
  - `run-mock-btn`
  - `session-result`

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

如果有办法，也请说明启动后页面访问路径，例如：
- `http://127.0.0.1:8000/`

---

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
