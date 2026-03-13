# 手动调整数据契约与版本追踪骨架 v1（Task-021 对应）

## 目标
在不开放真正手动调整 UI 的前提下，先冻结“自动结果 / 草稿调整 / 已应用版本”的后端契约。

本轮重点：
- 定义 adjustment state 的最小结构
- 区分 auto result 与 latest result
- 支持 draft 保存
- 支持 apply 形成版本历史
- 为后续 UI 开放真正编辑能力打基础

本轮不做：
- 前端编辑界面
- 曲线拖拽
- ROI 编辑
- 真实手动修正逻辑
- 复杂审批流

---

## 一、为什么先做后端契约
当前 workspace 已经有：
- 自动 summary
- replay detail
- Adjustment Preview（只读）
- Active Selection
- Workflow Stage

下一步如果直接开放编辑，很容易出现：
- 自动结果与人工结果混淆
- 无法追踪是谁、何时、因为什么改了结果
- 无版本历史
- 后续导出/报告难以解释

所以先把契约和版本追踪骨架定住，再考虑开放 UI。

---

## 二、建议的数据结构

### 1. 结果槽位 Result Slots
先统一定义一组结果槽位，即便当前真正有值的主要还是 `af95`：

```json
{
  "af95": 42.3,
  "as_value": null,
  "af_value": null,
  "af_tan": null
}
```

说明：
- 当前阶段允许多数槽位为 `null`
- 这样后面扩展 As / Af / Af-tan 时不必推翻结构

---

### 2. Draft Adjustment
用于保存“用户正在准备应用，但尚未正式生效”的草稿。

```json
{
  "overrides": {
    "af95": 43.1
  },
  "reason": "visual confirmation",
  "updated_at_ms": 1730000000000
}
```

约束：
- `overrides` 只允许已知结果槽位
- 值为 number 或 `null`
- 本轮可先优先支持 `af95`
- `reason` 为必填或最小非空字符串（建议）

---

### 3. Applied Version
用于记录一次真正“应用”的人工版本。

```json
{
  "version": 1,
  "result_before": {
    "af95": 42.3,
    "as_value": null,
    "af_value": null,
    "af_tan": null
  },
  "overrides": {
    "af95": 43.1
  },
  "result_after": {
    "af95": 43.1,
    "as_value": null,
    "af_value": null,
    "af_tan": null
  },
  "reason": "visual confirmation",
  "created_at_ms": 1730000000000
}
```

说明：
- `result_before` 是应用前的 latest result
- `result_after` 是应用后的结果
- `version` 单调递增

---

### 4. Adjustment State（API 视图）
建议对外返回的聚合结构：

```json
{
  "session_id": "session-001",
  "auto_result": {
    "af95": 42.3,
    "as_value": null,
    "af_value": null,
    "af_tan": null
  },
  "latest_result": {
    "af95": 43.1,
    "as_value": null,
    "af_value": null,
    "af_tan": null
  },
  "draft": {
    "overrides": {
      "af95": 43.1
    },
    "reason": "visual confirmation",
    "updated_at_ms": 1730000000000
  },
  "applied_versions": [
    {
      "version": 1,
      "result_before": {
        "af95": 42.3,
        "as_value": null,
        "af_value": null,
        "af_tan": null
      },
      "overrides": {
        "af95": 43.1
      },
      "result_after": {
        "af95": 43.1,
        "as_value": null,
        "af_value": null,
        "af_tan": null
      },
      "reason": "visual confirmation",
      "created_at_ms": 1730000000000
    }
  ]
}
```

说明：
- 若没有 applied version，则 `latest_result == auto_result`
- 若没有 draft，则 `draft = null`

---

## 三、持久化建议

建议在 artifact 目录下增加一个子目录：

```text
var/artifacts/adjustments/
  <session_id>.json
```

说明：
- 不改现有 summary SQLite 存储方式
- adjustment 版本历史先用 JSON artifact 存
- 与 replay detail artifact 风格保持一致

建议文件内容只保存：
- `session_id`
- `draft`
- `applied_versions`

其中 `auto_result` 可从 session summary 派生，避免重复写入。

---

## 四、后端行为建议

### GET adjustment state
输入：
- `session_id`

行为：
- 读取 session summary
- 若 summary 不存在 -> 404
- 读取 adjustment artifact（若存在）
- 组装：
  - auto_result
  - latest_result
  - draft
  - applied_versions

### PUT draft
输入：
- `session_id`
- `overrides`
- `reason`

行为：
- 校验 session 是否存在
- 校验 override keys
- 保存/覆盖当前 draft
- 不修改 summary
- 不写 applied_versions

### POST apply
输入：
- `session_id`

行为：
- 校验 session 是否存在
- 若 draft 不存在 -> 400
- 取当前 latest_result 作为 `result_before`
- 应用 draft.overrides 得到 `result_after`
- 生成新的 applied version
- draft 清空
- 保存 artifact
- 不直接回写 SQLite summary（本轮先不改 summary）

---

## 五、当前阶段的重要边界

1. 本轮只建立“版本追踪骨架”，不改现有自动 summary。
2. 自动结果与人工结果必须明确区分。
3. 本轮不要求 workspace 立刻显示这些 adjustment 版本。
4. 后续 UI 开放编辑时，直接复用本契约。

---

## 六、推荐 API

建议新增：

- `GET /api/session/{session_id}/adjustment`
- `PUT /api/session/{session_id}/adjustment/draft`
- `POST /api/session/{session_id}/adjustment/apply`

可选后续再补：
- `DELETE /api/session/{session_id}/adjustment/draft`

本轮不强求删除 draft。

---

## 七、验收标准
完成后，应能回答：

1. 当前会话的自动结果是什么？
2. 当前是否存在未应用的草稿？
3. 当前最新结果是否已被人工覆盖？
4. 历史上应用过几次人工版本？
5. 每次调整的原因和时间能否追溯？
