# Task-013：Replay Session 最小闭环

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目中的：
  - `src/workflow/session.py`
  - `src/vision/metric_end_displacement.py`
  - `src/curve/af95.py`
  - `src/webapp/routes/session.py`
  - `configs/dev_mock.yaml`
  - `configs/dev_lab.yaml`
  - `configs/prod_win.yaml`

## 任务目标

在当前“mock 闭环已可用”的基础上，再补一条**replay 闭环**：

- 从本地固定样例数据读取图像序列与温度序列
- 生成 `SyncPoint`
- 走现有 `vision -> curve -> af95 -> storage -> webapp`
- 通过 Web API 触发一次 replay session
- 页面可看到 replay 结果和历史新增

这轮仍然不接真实设备，不做上传大文件，不做实时流。

---

## 背景约束

1. 当前已经有：
   - 浏览器页面壳
   - `/health`
   - `/api/system/profile`
   - `/api/session`
   - `/api/session/run-mock`
   - `/api/session/{session_id}`
2. 当前已具备：
   - 最小视觉提取器
   - Af95 计算
   - workflow offline session
   - SQLite 持久化
3. 最终运行形态仍然是：
   - Mac 上开发调试
   - Windows 上最终运行
   - 浏览器作为统一交互入口
4. 这轮的 replay 主要用于“接近真实链路”的验证，不替代未来真机联调。

---

## 本轮要做的事

### 1. 增加最小 replay 数据目录与样例

建议在项目中新增：

```text
examples/replay/
  README.md
  temp_series.csv
  frames/
    frame_0001.json
    frame_0002.json
    frame_0003.json
    ...
```

说明：
- 为了避免引入 OpenCV 文件读写复杂度，这轮允许用 JSON 保存二维灰度数组
- `temp_series.csv` 至少包含：
  - `timestamp_ms`
  - `celsius`
- 每个 frame JSON 至少包含：
  - `timestamp_ms`
  - `image`
- 图像内容可沿用当前最小二维灰度数组结构
- 样例数据要能跑出一条可计算 Af95 的曲线

### 2. 在 workflow 中增加 replay runner

建议在 `src/workflow/session.py` 中增加最小 replay 能力，例如：

- `build_replay_sync_points(...)`
- `run_replay(session_id, dataset_path, ...)`

要求：
- 从固定 replay 样例目录读取 frame 和 temp 数据
- 使用现有 `EndDisplacementMetricExtractor`
- 生成 `list[SyncPoint]`
- 调用现有 `estimate_af95(...)`
- 复用已有 summary + SQLite 落盘逻辑
- 不要改现有 mock runner 的核心语义

如你认为更适合提取少量私有 helper，也可以，但不要扩大设计范围。

### 3. 增加 replay 配置段

建议：
- 在 `configs/dev_mock.yaml` 中增加 replay 配置段，或新增一个 `dev_replay` profile
- 这轮更推荐**直接在 `dev_mock.yaml` 里加 replay 样例路径**，减少 profile 扩散

例如：

```yaml
replay:
  dataset_path: examples/replay
```

要求：
- 路径尽量相对项目根目录
- Mac 与 Windows 都能从源码运行
- 不要把路径写死成绝对路径

### 4. 新增 replay API

建议新增：

- `POST /api/session/run-replay`

返回结构可与 `run-mock` 相同，即 session summary。

要求：
- 默认使用运行配置里的 replay dataset_path
- 若未配置 replay 数据路径，可返回 400/500 中你认为更合理的一种，但要有清晰错误信息
- 仍然只通过 `workflow` 间接调用，不要让 route 直接做 vision/curve 运算

### 5. 页面增加 replay 按钮

在当前 `index.html` 页面上增加一个最小按钮，例如：
- `Run Replay Session`

并在 `app.js` 中增加：
- 调 `POST /api/session/run-replay`
- 成功后展示结果
- 成功后刷新历史列表

要求：
- 继续只用原生 JS
- 不引入前端工程化
- 不做文件上传控件
- 不做复杂可视化

### 6. 补测试

至少新增或修改：
- `tests/workflow/test_session.py`
- `tests/webapp/test_session_api.py`
- 如你为 replay 读取写了辅助函数，可为其补最小测试

覆盖：
- replay dataset 可生成有效 `SyncPoint`
- `run_replay(...)` 能返回 summary 并落盘
- `/api/session/run-replay` 返回 200
- replay 成功后历史列表能包含新增记录
- 配置缺失或数据集不存在时，错误路径有最小测试

---

## 允许修改

- `examples/replay/**`
- `configs/dev_mock.yaml`（或你明确说明的 replay profile）
- `src/workflow/session.py`
- `src/webapp/deps.py`
- `src/webapp/routes/session.py`
- `src/webapp/templates/index.html`
- `src/webapp/static/app.js`
- 相关测试文件

## 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要接真实设备
- 不要引入 OpenCV 读视频作为本轮前提
- 不要引入前端工程化
- 不要新增 `frontend/` 顶层目录
- 不要把 replay 路由写成直接读设备适配器

---

## 设计要求

1. replay 是“准真实数据闭环”，不是最终在线模式。
2. 尽量复用现有 vision / curve / workflow / storage。
3. 页面只能通过 API 触发 replay。
4. 路径配置尽量相对化，兼容 Mac 和 Windows 源码运行。
5. 继续保持 `src.*` 绝对导入。
6. 优先小改动，避免一次性做太重。

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
- 启动后访问地址
- 页面点击 replay 后的预期效果

---

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
