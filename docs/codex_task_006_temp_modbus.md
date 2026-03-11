# Task-006：Modbus 温度采集适配器最小实现

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目里的 `src/temp/modbus_temp.py`
- 当前项目里的 `src/temp/mock_temp.py`
- 当前项目里的 `src/core/models.py`

## 任务目标

把 `src/temp/modbus_temp.py` 从占位实现升级为**最小可用的 Modbus 温度读取适配器**。

这轮仍然不接真实设备，但要把“如何读取一个温度值并转换为 `TempReading`”的代码路径做通。

---

## 范围

### 允许修改

- `src/temp/modbus_temp.py`
- `src/temp/__init__.py`
- `tests/temp/test_modbus_temp.py`
- 如有必要，可补少量模块注释

### 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要改 `camera / vision / curve / workflow / storage / report`
- 不要新增一级模块
- 不要引入真实设备依赖作为测试前提
- 不要修改任务无关代码

---

## 功能要求

### 1. 支持客户端注入

`ModbusTempReader` 必须支持注入一个 `client_factory` 或等价机制，用于测试时替代真实 Modbus 客户端。

目标是：

- 生产环境可走真实客户端
- 测试环境可走 fake client

### 2. 最小读取流程

适配器至少应支持这条路径：

1. 打开客户端连接（可惰性打开）
2. 读取一个保持寄存器或输入寄存器
3. 取第一个寄存器值
4. 经 `scale` / `offset` 转换为摄氏温度
5. 返回 `TempReading(timestamp_ms=..., celsius=..., source=...)`

建议支持的初始化参数至少包括：

- `host`
- `port`
- `unit_id`
- `register_address`
- `register_count`
- `function`（例如 `holding` 或 `input`）
- `scale`
- `offset`
- `source_name`
- `client_factory`
- `auto_open`

### 3. 最小错误处理

至少覆盖下面这些失败场景：

- 配置值非法（例如 host 为空，port < 1，register_count < 1）
- 客户端无法打开
- 读取失败
- 返回空寄存器

失败时请抛出明确异常，异常消息要能区分大致原因。

### 4. close() 可重复调用

和相机适配器一致，关闭操作应可重复调用，不因二次关闭报错。

### 5. 不修改 core 契约

返回值仍然必须是：

- `TempReading(timestamp_ms=..., celsius=..., source=...)`

不要新增临时字段去绕过现有模型。

---

## 实现建议

可以采用下面这种最小结构：

- `open()`：创建 client，必要时调用 connect
- `is_opened()`：判断 client 是否可用
- `read()`：读取寄存器并返回 `TempReading`
- `close()`：释放连接

推荐支持两种读取函数：

- `holding` -> `read_holding_registers`
- `input` -> `read_input_registers`

寄存器转温度可先用最小规则：

```python
celsius = raw_value * scale + offset
```

当前阶段不要扩展成 32 位浮点拼接、字节序切换、多寄存器解码。

---

## 测试要求

至少覆盖这些测试：

1. 成功读取 holding register 并返回 `TempReading`
2. 成功读取 input register 并返回 `TempReading`
3. `scale / offset` 生效
4. `read()` 多次调用时都能返回温度
5. 打开失败时抛错
6. 读取失败时抛错
7. 空寄存器时抛错
8. `close()` 可重复调用
9. 非法初始化参数会抛 `ValueError`

测试应使用 fake client，不要求安装真实 Modbus 库。

---

## 设计约束

1. 遵守 `docs/architecture_lock.md`
2. 只在 `temp` 模块内落地
3. 导入保持 `src.*` 绝对导入
4. 尽量小改动，不做“通用工业通讯框架”
5. 不要为了这轮改 `workflow` 或 `storage`

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
