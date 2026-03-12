# Task-014：Replay 结果详情与关键帧/曲线可视化

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目中的：
  - `src/workflow/session.py`
  - `src/storage/sqlite_repo.py`
  - `src/webapp/routes/session.py`
  - `src/webapp/templates/index.html`
  - `src/webapp/static/app.js`
  - `examples/replay/**`

## 任务目标

在当前“replay 闭环已可用”的基础上，再补一条**replay 结果详情展示**能力：

- replay 运行后，除了 summary，还能获取一份最小 detail 数据
- detail 至少包含：
  - 曲线点
  - Af95
  - 若干关键帧
- 浏览器页面可以展示：
  - 一张最小曲线图
  - 若干关键帧预览

这轮仍然不接真实设备，不做复杂前端工程，不做视频流播放器。

---

## 背景约束

1. 当前已经有：
   - `POST /api/session/run-replay`
   - `GET /api/session`
   - `GET /api/session/{session_id}`
   - 最小浏览器页面壳
2. replay 数据目前来自 `examples/replay/`
3. 仍然要保持：
   - Mac 上开发调试
   - Windows 上最终运行
   - 浏览器作为统一交互入口
4. 不允许让 UI 直接碰设备适配器
5. 不修改 `core` 契约

---

## 本轮要做的事

### 1. 为 replay 结果增加最小 detail artifact

建议在 `storage/` 内增加一个最小 artifact 存储能力，例如：

```text
src/storage/
  session_artifacts.py
```

或在你认为更合适的现有文件中补充，但不要扩大范围。

推荐行为：
- replay session 成功后，生成一个 `session detail` artifact
- artifact 可存成 JSON 文件
- 路径尽量从配置读取，例如：
  - `storage.artifact_dir`
  - 若未配置，可给一个相对默认值，如 `var/artifacts`

detail 至少包含：

```json
{
  "session_id": "...",
  "source": "replay",
  "af95": 42.3,
  "points": [
    {
      "timestamp_ms": 1000,
      "celsius": 20.0,
      "metric_raw": 0.0,
      "metric_norm": 0.0,
      "quality": 0.9
    }
  ],
  "key_frames": [
    {
      "label": "first",
      "timestamp_ms": 1000,
      "image": [[0, 0, 255], ...],
      "feature_point_px": [6, 4],
      "metric_raw": 0.0
    }
  ]
}
```

说明：
- 本轮允许 key frame 的 `image` 直接保存为二维灰度数组，因为 replay 样例很小
- 不需要为真实大图做最终设计
- key_frames 建议至少保存：
  - first
  - last
  - 如果方便，可补 middle

### 2. 在 workflow 中生成并保存 detail artifact

建议在 replay runner 中：
- 构造 `points`
- 选出关键帧
- 生成 detail payload
- 调用 artifact store 落盘

要求：
- 不破坏已有 `run_replay(...)` summary 行为
- 不影响 `run_mock(...)`
- 若 artifact 保存失败，你可以：
  - 让 replay 整体失败，或
  - 保持 summary 成功但 detail 缺失
  任选一种，但请在输出里说明
- 尽量小改动

### 3. 新增 detail API

建议新增：

- `GET /api/session/{session_id}/detail`

要求：
- 返回 replay detail artifact
- 若 detail 不存在，返回 404
- 不要让 route 自己去做 replay 计算
- 通过 deps / storage 层读取 artifact

### 4. 页面增加 detail 展示区域

在当前 `index.html` 中增加：
- “Replay Detail” 区域
- 一个曲线图容器
- 一个关键帧容器

最小展示要求：
- 曲线图：用 SVG 或 Canvas 画一条折线即可
- 关键帧：用 Canvas 或简单 DOM 网格渲染二维灰度数组即可
- 不引入前端框架
- 保持极简

建议页面交互：
- 点击 `Run Replay Session` 成功后，自动请求：
  - `GET /api/session/{session_id}/detail`
- 页面显示：
  - Af95
  - 点数量
  - 曲线
  - first / middle / last 关键帧（如果有）

### 5. 配置补最小 artifact_dir

建议在 `configs/dev_mock.yaml` 中补：
```yaml
storage:
  sqlite_path: var/dev_mock.sqlite3
  artifact_dir: var/artifacts
```

如果当前已有 `storage.sqlite_path`，只补 `artifact_dir` 即可。

要求：
- 使用相对路径
- 兼容 Mac 与 Windows 源码运行
- 不写死绝对路径

### 6. 补测试

至少新增或修改：
- `tests/storage/test_session_artifacts.py` 或你对应的测试文件
- `tests/workflow/test_session.py`
- `tests/webapp/test_session_api.py`
- `tests/webapp/test_ui_shell.py`

覆盖：
- replay 成功后生成 detail artifact
- artifact 可读回
- `GET /api/session/{session_id}/detail` 返回 200
- detail 不存在时返回 404
- 页面 HTML 中包含 detail 区域关键 hook
- 若静态 JS/页面可以验证 detail 挂钩，也请补最小断言

---

## 允许修改

- `configs/dev_mock.yaml`
- `src/storage/**`
- `src/workflow/session.py`
- `src/webapp/deps.py`
- `src/webapp/routes/session.py`
- `src/webapp/templates/index.html`
- `src/webapp/static/app.js`
- `src/webapp/static/app.css`
- 相关测试文件

## 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要接真实设备
- 不要引入前端工程化
- 不要新增 `frontend/` 顶层目录
- 不要把 detail API 写成现场重算 replay

---

## 设计要求

1. detail 是 replay 阶段的调试/验证资产，不是最终线上大文件方案。
2. UI 仍然只能通过 API 获取 detail。
3. 尽量复用现有 workflow / storage / webapp。
4. 保持 `src.*` 绝对导入。
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
- 点击 replay 后 detail 区域的预期表现

---

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
