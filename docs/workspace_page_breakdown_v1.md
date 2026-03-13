# Workspace 页面拆解说明 v1（Task-017 对应）

## 目标
把 `/workspace/{session_id}` 从结构空壳推进为“replay 分析工作台第一版”。

这轮只接：
- session summary
- replay detail
- 曲线图
- 关键帧
- 轻量联动

不接：
- live 实时采集
- ROI 编辑
- 参数调整
- 手动点位覆写
- 导出复杂交互

---

## 页面布局

### 1. 顶部状态栏
显示：
- 系统名
- 当前 profile
- session_id
- state
- source（优先显示 replay / mock）
- 返回首页入口

### 2. 左侧步骤导航
固定六步：
1. 准备
2. 采集
3. 处理
4. 计算
5. 调整
6. 存储

Task-017 只做展示，不做真正步骤切换逻辑。  
建议默认高亮“计算”。

### 3. 中央主工作区
分上下两块：

#### 上半区：曲线区
- 读取 detail.points
- X 轴：celsius
- Y 轴：metric_raw
- 用 SVG 绘制折线
- 若存在 af95，则增加最小标记

#### 下半区：关键帧区
固定优先展示：
- first
- middle
- last

每张关键帧卡片显示：
- label
- timestamp_ms
- metric_raw
- feature_point_px
- 小型灰度图预览（Canvas）

### 4. 右侧 side panel
分三块：

#### A. Session Summary
- session_id
- state
- point_count
- af95

#### B. Replay Detail Summary
- source
- points 数量
- key_frames 数量
- artifact 是否存在

#### C. Quick Actions
- 返回首页
- 刷新 detail
- 打开原始 summary JSON（可选）
- 打开原始 detail JSON（可选）

---

## 交互规则

### 页面加载
并行请求：
- `GET /api/session/{session_id}`
- `GET /api/session/{session_id}/detail`

### 轻联动
建议先做：
- 点击关键帧卡片
- 高亮曲线中对应点

### 错误态
- summary 缺失：页面显示会话不存在或 404
- detail 缺失：页面可打开，但主区显示 “No replay detail available”

---

## 视觉方向
参考 `af-analyzer` 的风格：
- 深色背景
- 卡片式分区
- 低饱和工业风
- 结果高亮
- 曲线区优先级高于辅助信息

不做重动画，不做大改造。
