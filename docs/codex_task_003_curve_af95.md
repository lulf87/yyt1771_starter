# Task-003：离线曲线归一化与 Af95 最小实现

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目里的 `src/core/models.py`
- 当前项目里的 `src/curve/af95.py`
- 当前项目里的 `tests/curve/`

## 任务目标

在**不修改 core 契约**的前提下，实现当前项目的最小离线曲线链路：

1. 从 `list[SyncPoint]` 中提取可用的 `(temperature, metric_raw)` 序列。
2. 对 `metric_raw` 做 0~1 归一化。
3. 基于归一化后的曲线，计算 `Af95`。
4. 用单元测试把边界行为锁住。

这次任务仍然是**离线算法最小实现**，不是 GUI、不是 PLC、不是数据库。

---

## 范围

### 优先修改文件

- `src/curve/af95.py`
- `tests/curve/` 下新增或补充测试
- `examples/offline_demo.py`（如有必要，可小改，展示 Af95 结果）

### 尽量不要改动

- `src/core/models.py`
- `src/core/contracts.py`
- `src/vision/metric_end_displacement.py`
- `src/sync/hub.py`

除非你发现阻塞性问题，否则这轮**不要再改 core 契约**。

---

## 功能要求

### 1. 输入来源

`estimate_af95(...)` 的主要输入应当基于 `list[SyncPoint]`，不要新发明顶层模块或绕开当前主链。

可用点的定义：

- `sync_point.temp` 不为 `None`
- `sync_point.metric` 不为 `None`
- `sync_point.metric.metric_raw` 不为 `None`

缺失这些字段的点，应被过滤掉，而不是直接报错。

### 2. 归一化

对可用点的 `metric_raw` 做最小-最大归一化：

```text
norm = (value - min) / (max - min)
```

要求：

- 若没有可用点，返回空结果或 `None`
- 若只有一个可用值，或 `max == min`，则归一化不可成立，应返回一个明确的不可计算结果，而不是伪造 0.95
- 归一化结果必须落在 `0.0 ~ 1.0`

### 3. Af95 计算

默认阈值为 `0.95`。

最小实现要求：

- 在按输入顺序形成的有效曲线中，寻找归一化值首次达到或跨过 `0.95` 的位置
- 若正好命中某点的 `norm == 0.95`，可直接返回该点温度
- 若在相邻两点之间跨过 `0.95`，使用**线性插值**估算温度
- 若整个曲线从未达到 `0.95`，返回不可计算结果

线性插值按下面理解：

```text
给定 (T1, N1), (T2, N2)，且 N1 < 0.95 <= N2
Af95 = T1 + (0.95 - N1) / (N2 - N1) * (T2 - T1)
```

### 4. 输出形式

你可以自行选择最小但清晰的 API 形式，例如：

- `estimate_af95(sync_points: list[SyncPoint], threshold: float = 0.95) -> float | None`
- 再配合一个辅助函数返回归一化曲线

或者：

- 返回一个小型结果对象 / dataclass

但要求：

- API 要简单
- 测试要容易写
- 不要为了这一步去扩张 core 层模型

---

## 测试要求

至少覆盖下面这些场景：

1. **正常归一化**
   - 原始值 `[0, 10, 20]` 归一化后应得到 `[0.0, 0.5, 1.0]`

2. **插值求 Af95**
   - 例如温度 `[30, 40, 50]`，归一化值 `[0.0, 0.9, 1.0]`
   - `Af95` 应落在 `40 ~ 50` 之间，并按线性插值计算

3. **精确命中阈值**
   - 某点归一化后正好 `0.95`，应返回该点温度

4. **缺失点过滤**
   - 有些 `SyncPoint` 缺少温度或 `metric_raw`，应被跳过

5. **不可计算场景**
   - 空输入
   - 只有一个有效点
   - 所有 `metric_raw` 都相同
   - 归一化曲线始终达不到 `0.95`

### 可选但推荐

- 在 `examples/offline_demo.py` 中构造一个极小的离线曲线样例，并打印 `Af95`

---

## 约束

1. 不新增一级模块。
2. 不创建 `utils/`、`common/`、`shared/`。
3. 导入风格保持 `src.*` 绝对导入。
4. 不把曲线计算塞进 `vision` 或 `workflow`。
5. 尽量让实现保持可读、可测试，不要过早抽象。

---

## 验收命令

至少运行：

```bash
pytest -q
```

如果你修改了示例，请再运行：

```bash
python -m examples.offline_demo
```

---

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
