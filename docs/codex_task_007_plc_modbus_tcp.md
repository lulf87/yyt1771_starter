# Task-007：PLC Modbus TCP 快照适配器最小实现

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目里的 `src/plc/modbus_tcp.py`
- 当前项目里的 `src/plc/__init__.py`

## 任务目标

把 `src/plc/modbus_tcp.py` 从占位实现升级成**最小可用的 PLC 快照读取适配器**。

这轮目标不是做复杂 PLC 点表系统，而是先让 PLC 层能通过 Modbus TCP 读取一组配置好的点位，并返回 `PlcSnapshot.values`。

---

## 设计原则

1. 只在 `plc` 模块内实现，不改 `core` 契约。
2. 这轮只做**读快照**，不做写线圈、写寄存器。
3. 先做最小、可测、稳定版本，不做块读取优化。
4. 继续沿用 `client_factory` 注入测试桩的方式。
5. 遵守 `docs/architecture_lock.md`，不要越界依赖。

---

## 范围

### 允许修改

- `src/plc/modbus_tcp.py`
- `src/plc/__init__.py`
- `tests/plc/test_modbus_tcp.py`（如不存在则新增）

### 不允许修改

- `src/core/models.py`
- `src/core/contracts.py`
- `vision / curve / workflow / storage / report`
- 不新增一级模块
- 不创建 `utils/`、`common/`、`shared/`

---

## 功能要求

### 1. 初始化参数

建议至少支持下面这些参数：

- `host: str`
- `port: int = 502`
- `unit_id: int = 1`
- `holding_register_map: dict[str, int] | None = None`
- `coil_map: dict[str, int] | None = None`
- `source_name: str = "modbus_plc"`
- `client_factory: Callable[[], Any] | None = None`
- `auto_open: bool = False`

约束：

- `host` 不能为空
- `port >= 1`
- `holding_register_map` 和 `coil_map` 不能同时为空

---

### 2. 连接行为

适配器至少实现：

- `open()`
- `is_opened()`
- `read()`
- `close()`

要求：

- `open()` 使用 `client_factory` 或默认 `pymodbus.client.ModbusTcpClient`
- 若 `connect()` 返回假值，应抛 `RuntimeError`
- `close()` 必须幂等

---

### 3. 快照读取行为

`read()` 需要：

1. 若未打开则自动 `open()`
2. 读取 `holding_register_map` 中每个点位的 holding register
3. 读取 `coil_map` 中每个点位的 coil
4. 合并成一个 `dict[str, bool | int | float | str]`
5. 返回：

```python
PlcSnapshot(
    timestamp_ms=..., 
    values={...},
    source="modbus_plc",
)
```

最小版本的值类型要求：

- holding register -> `int`
- coil -> `bool`

---

### 4. PyModbus 调用兼容性

请沿用 Temp 适配器当前已经修正过的兼容思路：

对 `read_holding_registers(...)` 和 `read_coils(...)`：

优先尝试：

```python
reader(address, count=1, device_id=self.unit_id)
```

若不兼容，再尝试：

```python
reader(address, count=1, slave=self.unit_id)
```

再不兼容，最后再回退到位置参数。

并且对响应补最小检查：

- `response is None` -> 抛 `RuntimeError`
- `response.isError()` 为真 -> 抛 `RuntimeError`
- holding response 缺 `registers` -> 抛 `RuntimeError`
- coil response 缺 `bits` -> 抛 `RuntimeError`

---

### 5. 导出行为

请把 `src/plc/__init__.py` 更新为能导出：

- `MockPlc`
- `ModbusTcpPlc`

---

## 测试要求

新增或更新 `tests/plc/test_modbus_tcp.py`，至少覆盖：

1. 只读 holding register 映射，返回正确 `values`
2. 只读 coil 映射，返回正确 `values`
3. 同时读取 holding + coil，能合并成一个快照
4. `open()` 连接失败时抛错
5. 读到 `None` 响应时抛错
6. `isError()` 响应时抛错
7. `close()` 幂等
8. 参数非法时抛 `ValueError`

建议你继续使用 fake client，并让 fake client 的方法签名采用当前 PyModbus 风格，例如：

```python
def read_holding_registers(self, address: int, *, count: int = 1, device_id: int = 1, **kwargs):
    ...

def read_coils(self, address: int, *, count: int = 1, device_id: int = 1, **kwargs):
    ...
```

---

## 非目标

这轮不要做：

- 点表文件解析
- 批量块读取优化
- 写寄存器/写线圈
- GUI 联动
- Workflow 联动

---

## 验收命令

至少运行：

```bash
pytest -q
```

如你增加了 PLC 专项测试，也可补充：

```bash
pytest -q tests/plc/test_modbus_tcp.py
```

---

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
