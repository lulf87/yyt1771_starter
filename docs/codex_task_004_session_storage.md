# Task-004：离线会话编排与最小 SQLite 落盘

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目里的 `src/workflow/session.py`
- 当前项目里的 `src/storage/sqlite_repo.py`
- 当前项目里的 `src/storage/session_store.py`
- 当前项目里的 `src/curve/af95.py`
- 当前项目里的 `tests/workflow/` 和 `tests/storage/`（如果尚不存在，可新建）

## 任务目标

在**不修改 core 契约**的前提下，把当前项目从“离线算法零件”推进到“离线单次测试会话”：

1. 能以 `list[SyncPoint]` 作为输入，运行一次最小离线 session。
2. 在 session 内调用现有 `estimate_af95(...)`。
3. 产出最小结果摘要：`session_id / state / point_count / af95`。
4. 用标准库 `sqlite3` 把最小结果摘要落盘。
5. 用单元测试把会话与落盘的行为锁住。

这次任务仍然不是 GUI、不是 PLC 联调、不是实时流处理。

---

## 范围

### 优先修改文件

- `src/workflow/session.py`
- `src/storage/sqlite_repo.py`
- `tests/workflow/` 下新增测试
- `tests/storage/` 下新增测试
- `examples/offline_demo.py`（如有必要，可小改，展示 session 和 Af95 结果）

### 尽量不要改动

- `src/core/models.py`
- `src/core/contracts.py`
- `src/vision/metric_end_displacement.py`
- `src/sync/hub.py`
- `src/curve/af95.py`

除非你发现阻塞性问题，否则这轮**不要再改 core 契约**。

---

## 功能要求

### 1. workflow.session

请把目前的占位 `WorkflowSession` 升级成“最小离线会话编排器”，但保持简单可测。

推荐但不强制的 API 形式：

```python
runner = WorkflowSessionRunner(repo=repo)
result = runner.run_offline(session_id="demo-001", sync_points=sync_points)
```

或者：

```python
session = WorkflowSession(record=SessionRecord(...), repo=repo)
result = session.run_offline(sync_points)
```

要求：

- 输入基于 `list[SyncPoint]`
- 内部调用 `estimate_af95(sync_points)`
- `point_count` 统计的是输入 `sync_points` 总数，还是有效点数，你可以二选一，但要在测试里固定下来并在 docstring/注释里说清楚
- 会话状态至少体现：
  - 开始运行前
  - 运行完成
  - 异常失败
- 正常情况下，即使 `af95 is None`，也可以视为“完成但结果不可计算”，不必强行判定为失败

### 2. storage.sqlite_repo

实现一个**最小可用**的 SQLite repository，使用 Python 标准库 `sqlite3`。

最小要求：

- 能创建表（若不存在）
- 能保存一条 session 结果摘要
- 能按 `session_id` 读取结果摘要

建议表结构（可微调，但不要过度设计）：

- `session_id TEXT PRIMARY KEY`
- `state TEXT NOT NULL`
- `point_count INTEGER NOT NULL`
- `af95 REAL NULL`
- `created_at_ms INTEGER NOT NULL`

要求：

- 不引入 SQLAlchemy 等外部依赖
- 不把 workflow 逻辑塞进 storage
- 存储层只负责持久化，不负责计算 Af95

### 3. 输出形式

你可以选择返回一个简单 dataclass、dict，或 tuple，但要求：

- API 清晰
- 测试容易写
- 不为了这一步扩张 `core` 层模型

如果你新增了仅属于 `workflow` 或 `storage` 的局部 dataclass，请把它放在对应模块内部，不要塞进 `src/core/models.py`。

---

## 测试要求

至少覆盖下面这些场景：

1. **SQLite round-trip**
   - 保存一条 `session_id / state / point_count / af95`
   - 再读出来，字段一致

2. **离线 session 正常完成**
   - 给一组可计算 Af95 的 `SyncPoint`
   - `run_offline(...)` 返回完成状态
   - 结果里 `af95` 为可计算值
   - repo 中能读到对应记录

3. **结果不可计算但会话完成**
   - 给空曲线或不可计算曲线
   - `run_offline(...)` 仍可返回完成状态
   - `af95 is None`
   - repo 中也能保存 `af95 = NULL/None`

4. **异常失败路径**
   - 例如 repo 保存阶段故意抛错，或 runner 内部注入一个失败 repo
   - 会话状态进入失败
   - 测试固定该行为

### 可选但推荐

- `examples/offline_demo.py` 展示一次离线 session 的输出

---

## 约束

1. 不新增一级模块。
2. 不创建 `utils/`、`common/`、`shared/`。
3. 导入风格保持 `src.*` 绝对导入。
4. 不把会话状态机细节塞进 `storage`。
5. 不把 SQLite 代码塞进 `workflow`。
6. 尽量保持实现可读，不要过早抽象成复杂仓储模式。

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
