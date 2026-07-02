# 架构说明

MaaMFKT 由三层组成：**interface.json（配置层）→ Pipeline JSON（状态机层）→ Python Agent（决策层）**。本文说明三层职责、协作方式与全局公共组件。

## 1. 配置层：interface.json

面向用户的「控制面板」，由 MaaFW 上层 UI（如 MFA）读取并渲染。

### controller / resource / agent

```json
"controller": [{ "name": "安卓端", "type": "Adb", "display_short_side": 720 }],
"resource":   [{ "name": "官服", "path": ["./resource"] }],
"agent":      { "child_exec": "python", "child_args": ["./agent/main.py"] }
```

- `display_short_side: 720` 决定工作分辨率（720×1280 竖屏），所有 ROI / 坐标以此为准。
- `agent` 指定 MaaFW 启动 Python Agent 子进程的方式。运行任务前 MaaFW 会拉起 `agent/main.py` 并通过 socket 通信。

### task[]

每个任务声明入口节点（`entry`）、可选配置项（`option`）和说明（`doc`）：

```json
{ "name": "消耗体力", "entry": "DailyStaminaStart",
  "option": ["体力消耗关卡", "扫荡不足时手动补刷"],
  "doc": ["从主界面进入限时活动……"] }
```

### option{} 与 pipeline_override

option 是核心机制：**不复制 pipeline，而是在运行时按用户选择动态改写节点**。

| 类型 | 用途 | 示例 |
|------|------|------|
| `select` | 单选 | 「体力消耗关卡」切换每个关卡的 OCR 文本 / 模板；「派遣地点优先级」改写 `next` 顺序 |
| `switch` | 开关 | 「允许使用珍贵调教道具」切换 `DailyTrainingConfigAllowRare.enabled` |
| `input` | 文本输入 | 「指定调教次数」注入 `repeat: "{次数}"` |

`pipeline_override` 是一个「节点名 → 局部字段」的字典，会与 pipeline 中的同名节点**深度合并**。例如关卡切换只改 `DailyStaminaPresetStageListTargetTitle` 的 `recognition.param.expected`，其余逻辑不变。

> **设计原则**：用户可配置的差异走 override，固定逻辑留在 Pipeline。新增可选行为时优先考虑能否用 override 表达。

## 2. 状态机层：Pipeline JSON

MaaFramework 的执行模型是**节点图状态机**。每个节点：

```
recognition（识别：满足条件吗？） → action（动作：点击/滑动/等待…） → next（命中后尝试的后继节点列表）
```

执行时 MaaFW 从 `entry` 开始，对当前节点的 `next` 列表**按顺序**逐个做识别，第一个识别成功的节点被激活、执行其 action，再进入它的 `next`，如此推进，直到 `StopTask` 或超时。

### 关键字段

- `recognition.type`：`OCR` / `TemplateMatch` / `ColorMatch` / `Custom` / `DirectHit`（恒命中）/ `And` / `Or`（组合子识别）。
- `action.type`：`Click` / `Swipe` / `LongPress` / `StartApp` / `StopApp` / `StopTask`。
- `next` / `on_error`：后继节点；`on_error` 在本节点识别 / 动作失败时走。
- `post_wait_freezes`：动作后等画面稳定，避免动画期间误识别。
- `timeout` / `max_hit`：超时与命中次数上限，防止卡死 / 死循环。
- `target: true`：点击「当前识别命中的框」；`target_offset` 在其上偏移；`target: "节点名"` 点击另一节点识别到的框。

### 本项目的流程惯例

- **`[JumpBack]` 前缀**：命中并执行后跳回当前节点重评估，用于「只要弹窗 / Loading / 某状态还在就反复处理」。
- **锚点**：`CommonMainReady`（主界面）是几乎所有任务的起止基准。
- **结束链**：`<任务>Done → CommonStopOnMainWithRetries`，多次重试确认回到主界面后 `StopTask`。
- **辅助节点 `__xxx`**：只做识别，被组合或作为点击 target，不进流程主线。

## 3. 决策层：Python Agent

Pipeline 擅长「识别固定文本 / 图标后点固定位置」，但不擅长：

- 数值比较（体力是否 ≥ 消耗 + 保留）；
- 组合优化（多个招募词条选哪几个能保底 2 星）；
- 动态 ROI（道具数量随位置变化）。

这些交给 Agent。Pipeline 用 `recognition.type: "Custom"` 调用：

```json
"recognition": {
  "type": "Custom",
  "param": {
    "custom_recognition": "DailyStaminaCompare",
    "custom_recognition_param": { "mode": "enough", "cost": 45, "reserve": 0, "stamina_roi": [500,0,180,45] }
  }
}
```

Agent 侧返回 `AnalyzeResult(box, detail)`：`box` 非空 = 命中（可被点击或作为 And/Or 条件），`detail` 进日志便于调试。

三个 Custom Recognition：

| 名称 | 文件 | 职责 |
|------|------|------|
| `DailyStaminaCompare` | stamina.py | OCR 读体力数值，按 mode/cost/reserve 判断够不够刷 |
| `DailyTrainingChooseItem` | training.py | 在 common/event 道具栏按数量 + 珍贵开关选可用道具框 |
| `DailyRecruitDecision` | recruitment.py | 词条 OCR + 卡池表，算保底 2 星最优组合，给出招募决策 |

Agent 可用 `context.run_recognition_direct(...)` 复用 MaaFW 的 OCR，用 `context.get_node_data(节点名)` 反查 Pipeline 节点配置（training.py 借此读取用户在 interface 里选的道具范围 / 珍贵开关）。

## 4. 全局公共组件

### common.json

- `CommonMainReady`：`And(__CommonMainExpeditionButton 出征, __CommonMainTrainingButton 调教)` —— 主界面判定。
- `CommonStopOnMain` / `CommonStopOnMainWithRetries`：确认主界面后 `StopTask`，带多次等待重试。
- `CommonWaitLoading`：识别「LOADING」并等待。
- `CommonCloseReward`：识别「确定」关闭奖励弹窗。

### common_return.json

- `CommonEnsureMain`：兜底路由。从已知子页面（商城 / 任务页 / 玩家信息 / 炼金 / 召唤 / 调教详情 / 派遣 / 体力关卡等）各自识别并点返回，逐级回到主界面。任务开头若不在主界面，会借它归位。

## 数据流总览

```
用户在 UI 选择任务 + option
        │
        ▼
interface.json  ──pipeline_override──►  Pipeline 节点（运行时被改写）
        │                                      │
        │                                      ▼
        │                          MaaFW 状态机执行：识别→动作→跳转
        │                                      │
        └──agent.child_args 拉起──►  Python Agent ◄──Custom 识别请求──┘
                                     （返回 box + detail）
```
