# 开发者指南

## 开发前准备

1. 确保 MaaMFKT 已连接到安卓模拟器/真机（ADB）。
2. 使用 MaaMcp MCP server 连接设备：`find_adb_device_list` → `connect_adb_device`，拿到 `controller_id`。
3. 基本调试循环：`ocr/screencap` 量取坐标 → 编辑 Pipeline JSON → `run_pipeline` 验证单节点 → 迭代。

修改 ROI / 坐标前，**先截图 + OCR 在真机当前画面上确认**，不要凭空估算。

---

## 新增日常任务（完整流程）

### 1. 新建 Pipeline 文件

在 `assets/resource/pipeline/` 下创建 `daily_<task_name>.json`，遵循命名约定：`<TaskPrefix><Semantic>`，如 `DailyNewTaskOpenFromMain`。

### 2. 连接公共组件

- 入口节点的 `next` 包含 `[JumpBack]CommonWaitLoading`（处理进入时的 LOADING 画面）。
- 从主界面开始：识别 `CommonMainReady`（出征 + 调教按钮同时存在）再执行导航点击。
- 任务结束：`<Task>Done → CommonStopOnMainWithRetries`。
- 若需要兜底回主界面，在 `common_return.json` 的 `CommonEnsureMain` 的 `next` 里追加对应页面的识别节点。

### 3. 注册到 interface.json

```json
{
  "name": "新任务",
  "entry": "DailyNewTaskStart",
  "option": [],
  "doc": ["一句话功能说明。", "边界条件说明。"]
}
```

若有可配置项，在 `option{}` 中追加，用 `pipeline_override` 表达差异。

### 4. 测试

```
run_pipeline(controller_id, pipeline_path="daily_new_task.json", entry="DailyNewTaskStart")
```

### 5. 补充文档

在 `docs/` 下创建 `task_daily_<name>.md`，结构参考本目录其他任务文档。

---

## 新增体力关卡 Preset

体力关卡通过 `interface.json` 的 `pipeline_override` 覆盖 `daily_stamina_presets.json` 中的 Preset 节点来切换。**不需要新建 Pipeline 文件。**

### 步骤

1. 在 `interface.json` 的「体力消耗关卡」option 的 `cases` 数组中，**复制一个现有 case**，修改以下字段：

| Preset 节点 | 要改的内容 |
|-------------|-----------|
| `DailyStaminaPresetRouteStart.next` | 进入活动的路由（通常保持 `DailyStaminaRouteActivitySectionStart`） |
| `DailyStaminaPresetInnerRouteStart.next` | 进入活动内 UI 的路由（特殊 UI / 挑战 UI / 普通列表）|
| `DailyStaminaPresetActivitySection.recognition` | 活动区标签 OCR 文本 + ROI |
| `DailyStaminaPresetActivityName.recognition` | 活动名称 OCR 文本 + ROI |
| `DailyStaminaPresetInnerUiTitle.recognition` | 活动内标题 OCR 文本 + ROI |
| `DailyStaminaPresetStageEntry.recognition` | 关卡入口图标模板 + ROI（TemplateMatch）|
| `DailyStaminaPresetStageListTargetTitle.recognition` | 关卡列表目标关卡名 OCR 文本 + ROI |
| `DailyStaminaPresetStageListTargetSubtitle.recognition` | 目标关卡副标题 OCR 文本 + ROI |
| `DailyStaminaPresetStaminaEnough` / `Low` | `cost`（单次体力消耗）和 `reserve`（保留值）|

2. 若需要 TemplateMatch 的关卡图标，截取清晰图标（无高亮状态），保存到 `assets/resource/image/DailyStamina/` 下（PNG 格式）。

3. 测试：`run_pipeline` 跑 `DailyStaminaStart`，观察路由是否正确进入目标关卡。

---

## 新增 Custom Recognition

### 1. 新建或扩展 agent/ 模块

```python
# agent/my_module.py
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.pipeline import JOCR
from common import safe_json_loads

@AgentServer.custom_recognition("MyCustomRecog")
class MyCustomRecog(CustomRecognition):
    def analyze(self, context, argv):
        param = safe_json_loads(argv.custom_recognition_param, {})
        # ... 识别逻辑 ...
        # box 非 None 表示命中，返回给 Pipeline 用于点击或条件判断
        return CustomRecognition.AnalyzeResult(box=(x, y, w, h), detail={"debug": "info"})
```

### 2. 在 agent/main.py 导入该模块

```python
import my_module  # noqa: F401
```

### 3. 在 Pipeline JSON 中引用

```json
{
  "recognition": {
    "type": "Custom",
    "param": {
      "custom_recognition": "MyCustomRecog",
      "custom_recognition_param": { "key": "value" }
    }
  }
}
```

### 读取 Pipeline 配置

如果需要读用户在 interface 里配的开关 / 选项，用 `context.get_node_data("节点名")` 反查节点字段，参考 `training.py` 中的 `_read_config(context)` 实现。

### 调用 OCR

```python
detail = context.run_recognition_direct(
    "OCR",
    JOCR(expected=[], roi=(x, y, w, h), threshold=0.3, only_rec=True),
    argv.image,
)
for result in detail.all_results:
    text = result.text
    box = result.box   # (x, y, w, h)
```

---

## 文档结构

```
docs/
├── architecture.md              # 三层架构与全局约定
├── dev_guide.md                 # 本文件
├── task_game_login.md           # 启动游戏
├── task_daily_shop.md           # 商城购买
├── task_daily_friend_stamina.md # 领取体力
├── task_daily_alchemy_orders.md # 炼金订单
├── task_daily_dispatch.md       # 每日派遣
├── task_daily_stamina.md        # 消耗体力
├── task_daily_training.md       # 调教
├── task_daily_recruitment.md    # 全境征才
└── task_daily_task_rewards.md   # 奖励领取
```

每个任务文档的结构：

```markdown
# 任务名

## 功能说明
## 流程概览（状态机文字图）
## 详细节点说明（表格）
## Option 配置
## Agent Custom Recognition（如有）
## 边界情况与已知问题
```

---

## Pipeline 调试技巧

- **单节点验证**：`run_pipeline` 指定 `entry` 只跑目标子流程，不必跑完整任务。
- **看识别结果**：返回值 `nodes[i].recognition.all_results` 含每个候选框的 `box` 和 `score`。
- **`[JumpBack]` 死循环**：检查对应节点是否设置了 `max_hit`；或 next 列表中是否有超时跳出分支。
- **`on_error` 无效**：`on_error` 只在识别失败时触发，动作失败（如 Click 失败）不走 `on_error`。
- **OCR 匹配失败**：先用 `ocr()` 在真机画面上拿实际 OCR 文本，核对 `expected` 里的字符串（注意繁简体、空格、罗马数字）。
- **TemplateMatch 阈值**：建议从 0.8 开始，若漏匹配逐步降到 0.7，低于 0.65 需考虑是否图片质量有问题。
