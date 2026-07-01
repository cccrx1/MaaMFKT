# 调教（DailyTraining）

## 功能说明

从主界面进入调教房间列表，筛选出「可调教」状态的房间，选择 NEXT 房间进入，根据配置选择道具栏（活动/通用）和道具（排除珍贵道具），按指定次数或全部点数消耗调教点，道具不足或点数用尽后返回主界面。

## 流程概览

```
DailyTrainingStart
  ├─[JumpBack] CommonWaitLoading
  ├─    DailyTrainingOpenFromMain  主界面（有调教次数）→ 点(640,1058)调教按钮
  ├─    DailyTrainingDoneNoCount  主界面（次数0/50）→ 直接 Done
  └─[JumpBack] CommonEnsureMain

DailyTrainingOpenFromMain（And: CommonMainReady + 调教次数非0）→ 点调教
  └─► DailyTrainingOpenFilter  OCR 筛选按钮 → 点(536,680)打开筛选面板
        → DailyTrainingFilterPanelTop  向上滑到「调教进度」区域 → SetProgressFilter

DailyTrainingSetProgressFilter（timeout 10s）
  ├─[JumpBack] DailyTrainingCycleProgressFilter  循环点右侧切换，直到「可调教」被选中（max_hit 4）
  ├─[JumpBack] DailyTrainingSwipeFilterToProgress  向上滑显示调教进度区域（max_hit 2）
  └─    DailyTrainingConfirmProgressFilter  And(调教进度标签 + 「可调教」选中) → 点(489,1085)确认

DailyTrainingConfirmProgressFilter → DailyTrainingEnterNextRoom
  → OCR「NEXT」→ 点框偏移(170,50)进房间 → DailyTrainingSelectConfiguredItem
  → on_error → DailyTrainingReturnMainFromRoomList（无可调教房间，返回）

DailyTrainingSelectConfiguredItem（识别调教道具界面）
  → next 被 override 改写（选 common 或 event 栏）
  → DailyTrainingSelectCommonTab/EventTab → DailyTrainingChooseCommonItem/EventItem
  → on_error → DailyTrainingReturnRoomListFromDetailFallback

DailyTrainingChooseCommonItem/EventItem（Custom「DailyTrainingChooseItem」）
  → 返回可用道具框 → 点击 → DailyTrainingClickCenterStart
  → on_error（无可用道具）→ ReturnRoomListFromDetailFallback

DailyTrainingClickCenterStart → DailyTrainingClickCenterSlow/AllPoints
  → 点(360,640) repeat N 次（指定次数模式）或长按3秒循环（全部点数模式）
  → next: CloseEnergyPrompt / CloseShortagePopup / CommonStopOnMain / ReturnRoomListFromDetail

DailyTrainingCloseEnergyPrompt（OCR「调教点不足/禁忌果实/补充能量」）→ 点(360,840)取消
  → next: CommonStopOnMain / ReturnRoomListFromDetail

DailyTrainingReturnMainFromRoomList → DailyTrainingDone → CommonStopOnMainWithRetries
```

## 详细节点说明

| 节点 | 识别 | 说明 |
|------|------|------|
| `__DailyTrainingMainHasCount` | OCR「/50」roi[595,1065,95,55]，inverse: false | 主界面调教按钮有次数 |
| `__DailyTrainingMainZeroCount` | OCR「0/50」同上 | 主界面调教次数为0 |
| `DailyTrainingOpenFilter` | OCR 稀有度/等级等筛选标签 | 点筛选按钮 |
| `DailyTrainingFilterPanelTop` | OCR「筛选排序」 | 向上滑到调教进度区域 |
| `__DailyTrainingProgressCanTrain` | OCR「可调教」roi[450,790,150,80] | 确认「可调教」被选中 |
| `DailyTrainingEnterNextRoom` | OCR「NEXT」roi[90,80,560,560] | 点框偏移(170,50) |
| `DailyTrainingSelectCommonTab` | OCR「通用」roi[390,930,130,85] | 点通用道具栏 |
| `DailyTrainingSelectEventTab` | OCR「活动」roi[520,930,130,85] | 点活动道具栏 |
| `DailyTrainingChooseCommonItem` | Custom「DailyTrainingChooseItem」tab: common | 选通用栏可用道具 |
| `DailyTrainingChooseEventItem` | Custom「DailyTrainingChooseItem」tab: event | 选活动栏可用道具 |
| `DailyTrainingClickCenterSlow` | OCR 调教道具界面 | 点(360,640) repeat 3（被 override 改写）、repeat_delay 2000 |
| `DailyTrainingClickCenterAllPoints` | 同上 | LongPress (360,640) 3000ms，循环 max_hit 12 |
| `DailyTrainingCloseShortagePopup` | OCR「道具不足/点数不足」 | 点取消 |

## Agent Custom Recognition

### DailyTrainingChooseItem（training.py）

- **输入参数**：`tab`（common/event）
- **读取配置**：`context.get_node_data("DailyTrainingConfigItemScope")` 获取用户选的道具范围；`context.get_node_data("DailyTrainingConfigAllowRare")` 获取珍贵道具开关。
- **逻辑**：遍历 `ITEMS[tab]` 固定位置列表，跳过 `rare=True` 且不允许珍贵道具的项，OCR 读道具下方数量文本，找到第一个 `count > 0 或 count=None（OCR失败视为可能有）` 的道具返回其 box。
- **返回**：box 非空 = 找到可用道具；box=None + detail.reason="no_usable_item" = 当前栏无可用道具。

**道具位置定义**：

- common: 120/240/600/2400（2400 为 rare）
- event: 600a/600b/600c/2000（2000 为 rare）

固定坐标 box 分别在 `(145,1065,90,105)`, `(260,1065,90,105)`, `(375,1065,90,105)`, `(490,1065,90,105)`，数量文本 ROI 为 box 下方偏移。

## Option 配置

### 调教目标

| Case | 改写节点 | 内容 |
|------|---------|------|
| 指定次数（默认） | `DailyTrainingClickCenterStart.next` → ClickCenterSlow | 慢速点击，repeat 从子 option「指定调教次数」注入 |
| 全部点数 | `DailyTrainingClickCenterStart.next` → ClickCenterAllPoints | 长按3秒，循环 max_hit 12 |

### 指定调教次数（input）

- 输入 1-100 整数，注入 `DailyTrainingClickCenterSlow.repeat: "{次数}"`。

### 调教道具范围

| Case | 改写节点 next 与 on_error | 说明 |
|------|------------------------|------|
| 优先通用道具（默认） | SelectConfiguredItem → SelectCommonTab，ChooseCommonItem on_error → SelectEventTab | 先通用，不足再活动 |
| 优先活动道具 | SelectConfiguredItem → SelectEventTab，ChooseEventItem on_error → SelectCommonTab | 先活动，不足再通用 |
| 活动和通用都可 | 同优先活动道具 | 两栏都允许 |

### 允许使用珍贵调教道具

| Case | 改写节点 | 内容 |
|------|---------|------|
| Yes | `DailyTrainingConfigAllowRare.enabled` = true | 2000/2400 道具也可用 |
| No（默认） | `DailyTrainingConfigAllowRare.enabled` = false | 跳过 rare 道具 |

## 边界情况

- 若主界面调教次数为 0，`DailyTrainingDoneNoCount` 直接结束。
- 无 NEXT 房间时 `EnterNextRoom` on_error 返回主界面。
- 道具不足或点数不足弹窗出现时，点取消返回房间列表 / 主界面。
