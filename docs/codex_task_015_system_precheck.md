# Task-015：系统预检查 API 与设备就绪面板

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目中的：
  - `src/webapp/config.py`
  - `src/webapp/deps.py`
  - `src/webapp/routes/health.py`
  - `src/webapp/routes/session.py`
  - `src/webapp/templates/index.html`
  - `src/webapp/static/app.js`
  - `src/workflow/precheck.py`
  - `configs/dev_mock.yaml`
  - `configs/dev_lab.yaml`
  - `configs/prod_win.yaml`

## 任务目标

在当前“mock + replay + detail 可视化”基础上，增加一条**系统预检查（precheck）**能力，让浏览器页面可以看到当前 profile 下的运行就绪情况。

这轮的目标不是连真机做完整诊断，而是做一个**跨平台、可扩展、对未来真机联调友好的就绪面板**。

---

## 背景约束

1. 当前已经有：
   - `/health`
   - `/api/system/profile`
   - `/api/session`
   - `/api/session/run-mock`
   - `/api/session/run-replay`
   - `/api/session/{session_id}`
   - `/api/session/{session_id}/detail`
   - 最小浏览器页面壳 + replay detail 可视化
2. 项目最终形态仍然是：
   - Mac 上开发调试
   - Windows 上最终运行
   - 浏览器作为统一交互入口
3. 当前相机 / PLC / 温度设备细节尚未完全定型，因此这轮不应依赖真实设备在线。
4. 仍然不允许让页面层直接碰设备适配器。

---

## 本轮要做的事

### 1. 设计最小 precheck 结果结构

建议在 `src/webapp/schemas.py` 中增加类似：

- `PrecheckItemResponse`
- `PrecheckResponse`

建议字段：

```json
{
  "status": "ok",
  "items": [
    {
      "name": "sqlite_path",
      "status": "ok",
      "detail": "data/dev_mock.sqlite3 parent directory is writable"
    },
    {
      "name": "artifact_dir",
      "status": "ok",
      "detail": "var/artifacts is available"
    },
    {
      "name": "replay_dataset",
      "status": "ok",
      "detail": "examples/replay found"
    },
    {
      "name": "camera_adapter",
      "status": "pending",
      "detail": "hik_rtsp_opencv configured but live connectivity is not checked in precheck"
    }
  ]
}
```

要求：
- 顶层 `status` 至少支持：
  - `ok`
  - `warn`
  - `fail`
- 每个 item 至少包含：
  - `name`
  - `status`
  - `detail`

### 2. 增加一个最小 precheck 服务/函数

建议在 `src/webapp/deps.py` 或 `src/workflow/precheck.py` 附近增加最小实现，但不要扩大设计范围。

precheck 至少检查：

#### 必做
- `storage.sqlite_path`
  - 父目录是否可创建 / 可写
- `storage.artifact_dir`
  - 目录是否存在或可创建
- `replay.dataset_path`
  - 路径是否存在
- `profile/adapters`
  - 当前 profile 中是否存在 `camera/temp/plc` 配置值

#### 建议做成“warn/pending”，不要做真机连接
- `camera_adapter`
- `temp_adapter`
- `plc_adapter`

要求：
- 这轮**不真正打开 RTSP、Modbus、PLC 连接**
- 只做“配置存在性 + 本地路径有效性 + 未来可扩展”的预检查
- 相对路径要按项目根目录解析，兼容 Mac 和 Windows 源码运行

### 3. 新增 precheck API

建议新增：

- `GET /api/system/precheck`

返回最小 precheck 响应。

要求：
- 基于当前运行 profile
- 不做重型计算
- 不读取真实设备
- 路由层通过 deps / helper 间接获取结果，不要把所有逻辑塞进 route

### 4. 页面增加“System Precheck”区域

在 `index.html` 里增加一个最小区域，显示：
- 总体状态
- 每个检查项名称、状态、说明
- 一个“Refresh Precheck”按钮

`app.js` 中增加：
- `loadPrecheck()`
- 页面初始化时并行加载
- 点击按钮后重新拉取 `/api/system/precheck`

要求：
- 继续只用原生 JS
- 不引入前端工程化
- 样式保持极简

### 5. 最小 CSS 状态样式

在 `app.css` 中给状态做最小区分即可，例如：
- `ok`
- `warn`
- `fail`
- `pending`

不需要复杂设计。

### 6. 补测试

至少新增或修改：
- `tests/webapp/test_precheck_api.py`
- `tests/webapp/test_ui_shell.py`
- 如你把 precheck 逻辑放到独立函数，也请为其补最小单测

覆盖：
- `GET /api/system/precheck` 返回 200
- `dev_mock` 下 sqlite/artifact/replay dataset 至少为 `ok`
- 页面 HTML 中包含 precheck 区域关键 hook
- 静态 JS 中包含 `/api/system/precheck` 调用痕迹，或页面测试验证 hook 存在
- 缺少 replay 路径或存储配置时，至少有一条 warn/fail 测试

---

## 允许修改

- `src/webapp/schemas.py`
- `src/webapp/deps.py`
- `src/webapp/routes/` 下新增或修改 system/precheck 路由
- `src/webapp/templates/index.html`
- `src/webapp/static/app.js`
- `src/webapp/static/app.css`
- 相关测试文件
- 如你认为合适，可少量使用 `src/workflow/precheck.py`

## 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要接真实设备
- 不要把 precheck 变成真机连接诊断
- 不要引入前端工程化
- 不要新增 `frontend/` 顶层目录

---

## 设计要求

1. 预检查是“就绪性检查”，不是最终在线诊断。
2. 路由层不能直接去打开相机、PLC、Modbus 连接。
3. 继续保持 `src.*` 绝对导入。
4. 相对路径兼容 Mac / Windows 源码运行。
5. 尽量小改动，便于后续扩展成真机 preflight。

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
- precheck 区域的预期表现

---

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
