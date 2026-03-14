# 架构冻结说明（Architecture Lock）

这份文件是当前项目的**唯一结构约束源**。
在后续所有 Codex 工单里，目录层级、命名方式、依赖方向、测试布局，都必须以本文件为准。

## 1. 总原则

1. 先冻结边界，再写业务代码。
2. 硬件适配层只负责采集/读写，不做业务判断。
3. 算法层只做计算，不直接控制设备。
4. 流程层只做调度，不实现具体视觉算法。
5. GUI 不得反向决定算法结构。
6. **不允许自由新增顶层目录，不允许创建 `utils/`、`common/` 这类无边界的公共垃圾桶。**
7. 任何结构变化都必须先更新本文件，再改代码。

---

## 2. 顶层目录固定

项目根目录下只允许保留这些一级目录：

```text
configs/
docs/
examples/
src/
tests/
```

允许保留：

- `README.md`
- 打包与工具配置文件（如 `pyproject.toml`、`pytest.ini`、`.gitignore`）

不允许未经批准新增：

- `scripts/`
- `common/`
- `shared/`
- `misc/`
- `temp_files/`
- 其他语义不清晰的目录

---

## 3. 代码目录固定

`src/` 下的一级模块固定为：

```text
src/
  core/
  camera/
  temp/
  plc/
  vision/
  sync/
  curve/
  workflow/
  storage/
  report/
  webapp/
```

禁止新增新的一级业务模块，除非我明确批准。

---

## 4. 当前目标目录树

下面这棵树是当前阶段的**标准目标形态**。可以先创建占位文件，不要求一次性实现完全部业务逻辑。

```text
project-root/
  README.md
  pyproject.toml
  .gitignore
  configs/
    recipe_example.yaml
    dev_mock.yaml
    dev_lab.yaml
    prod_win.yaml
  docs/
    architecture_lock.md
    module_map.md
    master_control_plan.md
    requirements_overview.md
    codex_task_000_scaffold_freeze.md
    codex_response_contract.md
  examples/
    __init__.py
    offline_demo.py
    replay/
    runtime/
      README.md
  src/
    __init__.py
    core/
      __init__.py
      models.py
      contracts.py
      enums.py
      errors.py
      config_models.py
    camera/
      __init__.py
      README.md
      mock_camera.py
      hik_gige_mvs.py
      hik_rtsp_opencv.py
    temp/
      __init__.py
      README.md
      mock_temp.py
      modbus_temp.py
    plc/
      __init__.py
      README.md
      mock_plc.py
      modbus_tcp.py
    vision/
      __init__.py
      README.md
      metric_end_displacement.py
      normalizer.py
      quality.py
      roi.py
    sync/
      __init__.py
      hub.py
    curve/
      __init__.py
      buffer.py
      af95.py
    workflow/
      __init__.py
      README.md
      adjustments.py
      camera_probe.py
      session.py
      state_machine.py
      precheck.py
    storage/
      __init__.py
      README.md
      probe_diagnostics.py
      session_artifacts.py
      session_adjustments.py
      sqlite_repo.py
      csv_exporter.py
      session_store.py
    report/
      __init__.py
      README.md
      summary.py
      plotter.py
    webapp/
      __init__.py
      app.py
      config.py
      deps.py
      schemas.py
      serve.py
      routes/
        __init__.py
        health.py
        profile.py
        session.py
        ui.py
      static/
      templates/
  tests/
    conftest.py
    architecture/
      test_import_rules.py
      test_model_contracts.py
      test_repository_layout.py
    camera/
      test_hik_gige_mvs.py
      test_hik_rtsp_opencv.py
    curve/
      test_af95.py
      test_curve_buffer.py
    plc/
      test_modbus_tcp.py
    storage/
      test_probe_diagnostics.py
      test_session_adjustments.py
      test_session_artifacts.py
      test_sqlite_repo.py
    sync/
      test_sync_hub.py
    temp/
      test_modbus_temp.py
    vision/
      test_vision_end_displacement.py
    webapp/
      test_adjustment_api.py
      test_camera_probe_api.py
      test_config_loader.py
      test_health.py
      test_precheck_api.py
      test_profile_api.py
      test_session_api.py
      test_ui_shell.py
      test_workspace_ui.py
    workflow/
      test_adjustments.py
      test_precheck.py
      test_session.py
```

说明：

- 这棵树反映当前已经落地的仓库基线，而不再只是 Task-000 初始骨架。
- 其中仍有部分文件保留最小实现或占位行为，但它们已经属于当前受保护的目录结构。

---

## 5. 每个模块的职责边界

### core
只放跨模块共享的：
- 数据模型
- 协议接口
- 枚举
- 错误码
- 配置模型

禁止：
- OpenCV 逻辑
- PLC 通讯
- 工作流状态机

### camera
只负责取图像帧，输出 `FramePacket`。

禁止：
- 做视觉识别
- 做曲线计算
- 做流程判断

### temp
只负责取温度，输出 `TempReading`。

### plc
只负责 PLC 点位读写，输出 `PlcSnapshot`。

### vision
只把图像转成 `ShapeMetric`。

禁止：
- 直接控制 PLC
- 直接输出 As/Af/Af95

### sync
只负责多源数据按时间统一成 `SyncPoint`。

### curve
只负责缓存曲线点、归一化、结果计算。

### workflow
只负责会话、状态机、预检查、调度。

### storage
只负责落盘、索引、回放。

### report
只负责结果摘要与图表导出。

### webapp
只负责 HTTP 路由、请求响应模型、依赖注入与服务装配。

禁止：
- 直接读取相机 RTSP
- 直接读写 Modbus 温度或 PLC
- 把视觉/曲线算法塞进路由函数

---

## 6. 依赖规则（必须遵守）

允许：

- `camera -> core`
- `temp -> core`
- `plc -> core`
- `vision -> core`
- `sync -> core`
- `curve -> core`
- `storage -> core`
- `report -> core`
- `webapp -> core/workflow/storage/report`
- `workflow -> core/camera/temp/plc/vision/sync/curve/storage/report`
- `examples -> src` 公共 API
- `tests -> 被测模块`

禁止：

- `vision -> plc`
- `vision -> workflow`
- `curve -> camera`
- `curve -> plc`
- `storage -> workflow`（控制反向依赖）
- `camera/temp/plc -> gui`
- `report -> camera/temp/plc`
- `webapp -> camera/temp/plc/vision/curve/sync`
- 任意业务模块横向随意互相调用

一句话：

**硬件层只采集，算法层只计算，流程层只调度。**

---

## 7. 命名约束

### 文件命名

- 适配器：`hik_rtsp_opencv.py`、`modbus_temp.py`、`modbus_tcp.py`
- 测试桩：`mock_camera.py`、`mock_temp.py`、`mock_plc.py`
- 算法文件：`metric_end_displacement.py`、`normalizer.py`
- 状态/流程：`session.py`、`state_machine.py`

### 类命名

- 协议/接口：`XXXPort` 或 `XXXReader`/`XXXWriter`
- 适配器实现：`HikRtspCamera`、`ModbusTempReader`
- 算法类：`EndDisplacementMetricExtractor`

### 导入风格

统一使用**绝对导入**，根路径从 `src` 开始，例如：

```python
from src.core.models import FramePacket
from src.sync.hub import SyncHub
```

除同文件夹内部的非常短引用外，不建议使用复杂相对导入。

---

## 8. 测试目录规则

`tests/` 要镜像业务目录，而不是全部平铺。

固定方式：

```text
tests/
  architecture/
  camera/
  curve/
  plc/
  storage/
  sync/
  temp/
  vision/
  webapp/
  workflow/
```

要求：

- `tests/` 根目录下除 `conftest.py` 外，不应继续新增平铺 `test_*.py`。
- 新测试应优先进入对应的镜像子目录。
- `tests/architecture/` 负责结构守卫、导入守卫、契约守卫。

---

## 9. 占位文件规则

架构冻结阶段允许创建占位文件，但占位文件必须满足：

1. 文件名符合本架构。
2. 文件内写清职责注释。
3. 若尚未实现，可显式抛出 `NotImplementedError`。
4. 不允许写与文件名无关的临时代码。

---

## 10. 变更控制规则

Codex 在任何任务中：

1. 不得重命名一级目录。
2. 不得新增一级模块。
3. 不得把算法逻辑塞进 hardware adapter。
4. 不得在未说明的情况下移动大量文件。
5. 若发现当前结构与实现冲突，应在输出中列出冲突点，而不是自行发明新结构。

---

## 11. 当前阶段的执行顺序

按下面顺序推进并在当前基线上继续扩展：

1. **Task-000 ~ Task-007：离线主链与设备适配器最小实现**
2. **Task-008 ~ Task-015：Web 架构冻结、profile、session、replay、precheck**
3. **Task-016 ~ Task-021 / WP-A：workspace、adjustment contract、Adjustment MVP**
4. **后续任务：在当前 Web/workspace 基线上继续增强，不回退到早期骨架叙事**

当前仓库已经到达 Web/workspace/replay/adjustment MVP 基线，不应再把结构文档描述回退到 Task-000 阶段。
