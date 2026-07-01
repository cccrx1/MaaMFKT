# 消耗体力（DailyStamina）

## 功能说明

从主界面进入「出征」，按 option 配置的关卡路由进入目标关卡详情页，优先使用「军团扫荡」扫荡体力；扫荡不可用或扫荡后仍有体力时，可选是否手动战斗补刷。通过 `pipeline_override` 机制支持多个限时活动关卡切换。

## 流程概览

```
DailyStaminaStart
  ├─[JumpBack] CommonWaitLoading
  ├─    DailyStaminaOpenExpeditionFromMain  主界面 → 点出征
  └─[JumpBack] CommonEnsureMain

DailyStaminaOpenExpeditionFromMain → DailyStaminaPresetRouteStart
  → （由 pipeline_override 改写 next）默认 → DailyStaminaRouteActivitySectionStart

DailyStaminaRouteActivitySectionStart（OCR「限时活动」标签）→ 点击
  → DailyStaminaRouteActivityListFindSelected（timeout 6s）
      ├─ DailyStaminaRouteActivityListEnterSelected（OCR 当前选中活动名）→ 固定点(360,1148)进入（max_hit 4）
      └─ DailyStaminaRouteActivityListSelectSlot2  未找到 → 跳过Slot1，直接点中间卡片

DailyStaminaRouteInnerSpecialUiStart（OCR 活动内标题 + TemplateMatch 关卡图标）
  → 点图标偏移(0,25) → [JumpBack]CommonWaitLoading → DailyStaminaOpenTargetStage

DailyStaminaRouteInnerRerunUiStart（复刻地图 UI：倒树形 2D 地图，按列定位 + 上下扫描）
  ├─ DailyStaminaRerunClickTarget（OCR 目标关卡名命中 → 点 box 中心 → 进详情页）
  └─ DailyStaminaRerunMainColumnStart（默认主线列；case 可 override next 改为 Left/Right 列）
       ├─ Left/RightColumnStart  横滑到底定位支线列（自循环 max_hit 4）→ ScanUp
       ├─ DailyStaminaRerunScanUp  上滑到顶（自循环）→ ScanDown
       ├─ DailyStaminaRerunScanDown  从顶向下扫整列（自循环 max_hit 18）→ GiveUp
       └─ DailyStaminaRerunGiveUp → [JumpBack]CommonEnsureMain 兜底返回主界面
  （每步都先试 DailyStaminaRerunClickTarget，命中即进 DailyStaminaStageDetailInitialDecision）

DailyStaminaOpenTargetStage（识别目标关卡标题 + 副标题，box_index 0 取第一个）
  → 点框偏移(120,0) → 进详情页 → DailyStaminaStageDetailInitialDecision（timeout 6s）

DailyStaminaStageDetailInitialDecision
  ├─ DailyStaminaReturnMainWhenLow  Custom「体力不足」→ 点返回
  └─ DailyStaminaOpenSweep  OCR「军团扫荡」→ 点击 → DailyStaminaSweepDialog

DailyStaminaSweepDialog（识别「自动扫荡设置」，timeout 4s）
  → DailyStaminaClickSweepMax（TemplateMatch SweepMaxButton）→ 点MAX
      → DailyStaminaStartSweep（OCR「扫荡开始」）→ 点击
          ├─[JumpBack] DailyStaminaSkipSweepAnimation  OCR「跳过/SKIP」→ 点跳过
          └─► DailyStaminaConfirmSweepResult（OCR「扫荡结果/完成」）→ 点(360,959)确认

DailyStaminaAfterSweepDecision（timeout 6s）
  ├─ DailyStaminaReturnMainWhenLow  体力不足 → 返回
  ├─ DailyStaminaManualStartAfterSweep（enabled: false，体力够 + 手动补刷开启）→ 点(360,1143)开始挑战
  └─ DailyStaminaReturnMainFromStageDetail  返回主界面

DailyStaminaManualStartAfterSweep → DailyStaminaWaitBattleResult（timeout 180s）
  ├─[JumpBack] CommonWaitLoading
  ├─[JumpBack] DailyStaminaBattleInProgress  识别「WAVE/TURN」→ 等3秒
  ├─ DailyStaminaBattleContinueWhenEnough  And(CLEAR + 再次挑战 + 体力够) → 点再次挑战
  └─ DailyStaminaBattleReturnMapWhenLow  And(CLEAR + 返回地图 + 体力低) → 返回

DailyStaminaDone → CommonStopOnMainWithRetries
```

## 详细节点说明

| 节点 | 识别 | 说明 |
|------|------|------|
| `DailyStaminaOpenExpeditionFromMain` | `CommonMainReady` | 点(571,912)出征按钮 |
| `DailyStaminaPresetRouteStart` | — | next 被 override 改写，指向活动区/复刻区等路由 |
| `DailyStaminaRouteActivitySectionStart` | OCR「限时活动」roi[480,90,150,80] | 点限时活动标签 |
| `DailyStaminaPresetActivityName` | OCR 活动名 roi[60,740,260,100]（如「冰霜下的残响」）| 用于确认当前选中的活动；进入按钮仍固定点 `(360,1148)` |
| `DailyStaminaRouteActivityListSelectSlot1/2/3` | DirectHit | 从 Slot2 开始（跳过最左），依次固定点 `(360,704)` / `(552,704)` / `(168,704)` |
| `DailyStaminaPresetStageEntry` | TemplateMatch 关卡图标 roi[400,880,250,270] | 活动内特殊 UI 用图标找入口，点击图标并下偏 `(0,25)` |
| `DailyStaminaOpenTargetStage` | And(目标关卡标题 + 副标题) box_index 0 | 点第一个命中的关卡，max_hit 4 |
| `DailyStaminaPresetStaminaEnough` | Custom「DailyStaminaCompare」mode: enough | cost/reserve 被 override 改写 |
| `DailyStaminaClickSweepMax` | TemplateMatch SweepMaxButton.png | 点MAX按钮 |
| `DailyStaminaConfirmSweepResult` | OCR「扫荡结果/完成」 | 点确认 |
| `DailyStaminaBattleStaminaEnough` | And(DailyStaminaPresetStaminaEnough) | 判断体力够继续刷 |
| `DailyStaminaManualStartAfterSweep` | enabled: false，And(体力够) | 手动补刷开关（默认关闭） |

## Agent Custom Recognition

### DailyStaminaCompare（stamina.py）

- **输入参数**：`mode`（enough/low）、`cost`（单次消耗）、`reserve`（保留值）、`stamina_roi`（体力数值 ROI）
- **逻辑**：OCR 读取 ROI 内文本，解析「当前/上限」格式（如「123/150」），判断 `当前 >= cost + reserve`。mode=enough 时够才命中；mode=low 时不够才命中。
- **返回**：box 非空 = 命中；detail 含 stamina/cost/reserve/hit 等调试信息。

## Option 配置

### 体力消耗关卡

改写 `DailyStaminaPreset*` 系列节点，切换活动、关卡名、图标、体力消耗等。每个 case 包含：

- `DailyStaminaPresetRouteStart.next`：路由起点（如 ActivitySectionStart）
- `DailyStaminaPresetActivitySection.recognition`：活动区标签 OCR
- `DailyStaminaPresetActivityName.recognition`：活动名 OCR
- `DailyStaminaPresetInnerUiTitle.recognition`：活动内页标题 OCR
- `DailyStaminaPresetStageEntry.recognition`：关卡图标 TemplateMatch
- `DailyStaminaPresetStageListTargetTitle.recognition`：关卡名 OCR
- `DailyStaminaPresetStageListTargetSubtitle.recognition`：关卡副标题 OCR
- `DailyStaminaPresetStaminaEnough/Low.recognition.param.custom_recognition_param`：cost/reserve 数值

## 寻路与点击策略

当前体力任务不是纯名称匹配，也不是纯固定坐标，而是分阶段混合：

1. **主界面到出征**：`DailyStaminaOpenExpeditionFromMain` 先用 `CommonMainReady` 确认主界面，再固定点 `(571,912)` 进入出征。
2. **活动区标签**：`DailyStaminaRouteActivitySectionStart` OCR「限时活动」标签，点击识别框。这里是名称匹配。
3. **活动列表选择**：`DailyStaminaRouteActivityListEnterSelected` OCR `DailyStaminaPresetActivityName`，ROI `[60,740,260,100]`，确认当前选中活动名；确认后固定点 `(360,1148)` 点击底部「进击」进入活动。当前活动名不匹配时，默认直接跳到 `SelectSlot2`（中间卡片 `(360,704)`）而非 `SelectSlot1`，因为大多数活动不在最左。依次 `SelectSlot2` → `SelectSlot3`，最后才 `SelectSlot1`。每点一次后重新 OCR 当前选中标题。
4. **活动内特殊 UI 入口**：`DailyStaminaRouteInnerSpecialUiStart` 同时 OCR 活动内标题 `[0,90,240,100]`，并用 `TemplateMatch` 找关卡图标 `DailyStamina/FrostEchoStageIcon.png`，ROI `[400,880,250,270]`。命中后点击图标框并下偏 `(0,25)`。这里不是活动名找入口，而是“标题确认 + 图标识别”。
5. **关卡列表目标关卡**：`DailyStaminaOpenTargetStage` 通过 `DailyStaminaPresetStageListTarget` 找目标关卡，目标是标题 OCR 或副标题 OCR，ROI `[70,90,580,1000]`。找不到时用 `DailyStaminaScanStageListDown/Up` 上下滑动，再继续找。这里是关卡名称/副标题匹配。
6. **关卡详情页**：体力用 `DailyStaminaCompare` 读 `stamina_roi` `[500,0,180,45]` 判断够不够；够则优先打开「军团扫荡」，不够则返回主界面。

因此你看到“找活动像固定位置”是对的：外层活动名只用于确认当前选中的活动，切换活动槽位和进入活动是固定点击。旧实现曾把上方大海报区域当成第三个活动槽位；现在槽位已改为同一行左/中/右三张小卡片。真正的目标关卡选择是在进入活动后的关卡列表里通过 OCR 名称/副标题匹配完成。

### 复刻地图 UI 寻路（replica_ui / `DailyStaminaRouteInnerRerunUiStart`）

部分活动进入后不是关卡列表，而是一张可上下左右拖动的**倒树形地图**：关卡作为节点散布其上。地图结构有固定规律：

- **主线**在屏幕中间一列竖直排布，全程可见，上下滑动即可遍历。
- **支线**从主线向下分叉，按编号分两类：**-01 在左侧、-02 在右侧**，每类各自排成独立一列。

因此寻路按目标关卡所在「列」分三种策略（列位是关卡固有属性，由 interface case 在开发侧写死，用户只看到关卡名）：

| 列位 | 入口节点（case 覆盖 `DailyStaminaRouteInnerRerunUiStart.next`） | 动作 |
|------|------|------|
| 主线 main（默认） | `DailyStaminaRerunMainColumnStart` | 不横滑，直接上下扫描 |
| 左侧支线 left（-01） | `DailyStaminaRerunLeftColumnStart` | 先左滑到底（手指右移），再上下扫描 |
| 右侧支线 right（-02） | `DailyStaminaRerunRightColumnStart` | 先右滑到底（手指左移），再上下扫描 |

节点链路：入口先试 `DailyStaminaRerunClickTarget`（OCR `DailyStaminaPresetStageListTarget` 命中目标关卡名即点 box 中心，无固定坐标）→ 否则进列定位 → 横滑节点自循环到底（`max_hit` 4，OCR 不变即到边界）→ `DailyStaminaRerunScanUp` 上滑到顶（自循环）→ `DailyStaminaRerunScanDown` 从顶扫到底（自循环 `max_hit` 18）→ 仍未命中则 `DailyStaminaRerunGiveUp` `[JumpBack]CommonEnsureMain` 返回主界面。每个滑动节点的 `next` 首位都是 `DailyStaminaRerunClickTarget`，即每滑一步都重新尝试点击目标。守卫 `DailyStaminaPresetRerunMapMarker`（OCR `Story`/`Free Quest`）确认仍在地图上。命中目标点击后直接进入关卡详情页，复用 `DailyStaminaStageDetailInitialDecision` 之后的全部扫荡/战斗逻辑。

注册新的此类活动只需在 interface「体力消耗关卡」加一个 case，覆盖：`DailyStaminaPresetInnerRouteStart.next` → `[DailyStaminaRouteInnerRerunUiStart]`、`DailyStaminaRouteInnerRerunUiStart.next`（选列）、活动名、目标关卡名 OCR、体力 cost。无需关卡图标模板。

### 扫荡不足时手动补刷

| Case | 改写节点 | 内容 |
|------|---------|------|
| Yes | `DailyStaminaManualStartWhenSweepUnavailable.enabled` = true，`DailyStaminaManualStartAfterSweep.enabled` = true | 开启手动战斗补刷 |
| No（默认） | 同上 = false | 只扫荡，不手动 |

## 边界情况

- 体力不足时 `DailyStaminaReturnMainWhenLow` 直接返回，不进扫荡。
- 扫荡弹窗若超时（券不足），走 on_error 到 `ManualStartWhenSweepUnavailable`（若开启手动补刷则打一次）。
- 手动战斗中识别「WAVE/TURN」等待 3 秒防动画误识别，战斗最长 180s 超时。
- **已修改 (2026-06-25)**：活动列表寻路 `DailyStaminaRouteActivityListFindSelected` 超时后跳过 Slot1（最左卡片）直接从 Slot2 开始，因为当前活动不在最左的概率更高。
