# Task-006A：修正 Modbus 读寄存器调用兼容性

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目里的 `src/temp/modbus_temp.py`
- 当前项目里的 `tests/temp/test_modbus_temp.py`

## 任务目标

对 `ModbusTempReader` 做一个**小型热修正**，让它与当前 PyModbus 常见调用方式兼容，并补一条对 Modbus 异常响应的最小处理。

这轮不要扩大范围。

---

## 背景

当前实现里，寄存器读取是这样调用的：

```python
response = reader(self.register_address, self.register_count, self.unit_id)
```

但当前 PyModbus 文档中的 `read_holding_registers` / `read_input_registers` 常见签名已经是：

```python
read_holding_registers(address, *, count=1, device_id=1, no_response_expected=False)
read_input_registers(address, *, count=1, device_id=1, no_response_expected=False)
```

也就是说，`count` 和 `device_id` 常常是**关键字参数**，不应继续假定三位置参数调用必然成立。

同时，PyModbus 官方示例在读取后会检查：

```python
if rr.isError():
    ...
```

当前最小实现还没有覆盖这条路径。

---

## 范围

### 允许修改

- `src/temp/modbus_temp.py`
- `tests/temp/test_modbus_temp.py`

### 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要改 `camera / vision / curve / workflow / storage / report`
- 不要新增一级模块
- 不要改任务无关代码

---

## 功能要求

### 1. 修正读寄存器调用方式

把读寄存器调用改成**兼容当前 PyModbus**的方式。

优先目标：

```python
reader(address, count=self.register_count, device_id=self.unit_id)
```

为了兼容较旧风格客户端，你可以做一个很小的兼容层，例如按顺序尝试：

1. `device_id=`
2. `slave=`
3. 必要时最后再退回旧式位置参数

但不要把代码写得很重。

### 2. 补最小异常响应处理

如果返回对象存在 `isError()` 且结果为真，应抛出 `RuntimeError`，而不是继续按正常寄存器解析。

例如可接受：

```python
if callable(getattr(response, "isError", None)) and response.isError():
    raise RuntimeError("Modbus exception response while reading temperature register")
```

### 3. 测试修正

测试至少覆盖：

1. 使用**关键字参数风格**的 fake client 也能通过
2. 若 fake response 的 `isError()` 为真，会抛出 `RuntimeError`
3. 现有 holding / input / scale / close 等行为不退化

建议把 fake client 的 `read_holding_registers` / `read_input_registers` 改成更贴近真实库的形式，例如：

```python
def read_holding_registers(self, address: int, *, count: int = 1, device_id: int = 1, **kwargs):
    ...
```

如需兼容 fallback 测试，也可以再补一个旧风格 fake client。

---

## 设计约束

1. 仍遵守 `docs/architecture_lock.md`
2. 导入保持 `src.*` 绝对导入
3. 尽量小改动
4. 不要把这轮扩展成“多寄存器浮点解码”或“真实设备联调”

---

## 验收命令

至少运行：

```bash
pytest -q
```

可选补充：

```bash
pytest -q tests/temp/test_modbus_temp.py
```

---

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
