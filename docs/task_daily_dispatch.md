# 每日派遣（DailyDispatch）

## 功能说明

打开左侧抽屉进入地城派遣总览，优先收回「派遣完成」的队伍，再为「闲置中」的队伍选择地点、时间、编队后派出。地点和时间优先级由 option 配置，编队逻辑为：先尝试「条件推荐」，失败则「人员补充」，仍失败则手动滑入四个位置填满队伍后出发。

## 流程概览

```
DailyDispatchStart
  ├─[JumpBack] CommonWaitLoading
  ├─    DailyDispatchOpenDrawerFromMain  主界面 → 点(35,630)抽屉 → 点(75,595)派遣入口
  ├─    DailyDispatchScanOverview  扫描总览页（循环处理完成/闲置队伍）
  ├─[JumpBack] DailyDispatchCloseReturnPopup  归来弹窗 → 关闭
  └─[JumpBack] CommonEnsureMain

DailyDispatchOpenDrawerFromMain → DailyDispatchEnterFromDrawer（timeout 5s）
  ├─ DailyDispatchClickActionableDrawerSlot  OCR「派遣完成/闲置中」→ 点击 → 进总览
  ├─ DailyDispatchOpenBusyDrawerSlot  And(派遣队1 + 倒计时)  → 点击 → 进总览
  └─ DailyDispatchCloseDrawerDone  已全忙 → 关抽屉 → Done

DailyDispatchScanOverview（OCR「地城派遣」，timeout 6s）
  ├─[JumpBack] DailyDispatchCloseReturnPopup
  ├─[JumpBack] CommonWaitLoading
  ├─    DailyDispatchOpenCompletedSlot  OCR「派遣完成」→ 点击 → 归来 → 关弹窗 → 回 ScanOverview
  ├─    DailyDispatchOpenIdleSlot  OCR「闲置中」→ 点击 → PrepareIdleSlot
  └─    DailyDispatchReturnMainWhenAllBusy  都忙 → 回主界面

DailyDispatchPrepareIdleSlot（timeout 8s）
  ├─    DailyDispatchNeedSelectRoom  OCR「请选择房间」→ 选地点
  ├─    DailyDispatchLaunchReady  And(出发按钮 + 队伍已填满颜色) → 点出发
  ├─    DailyDispatchOpenTeamFormation  OCR「Bonus奖励条件」→ 点编队入口
  └─    DailyDispatchSelectLocationStart  选地点流程

DailyDispatchSelectLocationStart（timeout 8s）→ 按 option 配置的优先级依次尝试各地点
  每个地点识别成功后 → 选时间按钮（按 option 优先级：Time1/2/3/4）→ DailyDispatchOpenTeamFormation
  on_error → DailyDispatchReturnOverviewFromSelection（选不到地点，返回总览）

DailyDispatchOpenTeamFormation → DailyDispatchAutoFormation（点「条件推荐」）
  ├─ DailyDispatchConfirmNoRecommendedTeam  OCR「没有满足需求的编队」→ ManualFillTeam
  ├─ DailyDispatchClickPersonnelSupplement  OCR「人员补充」→ 点击 → FormationReturn
  └─ on_error → DailyDispatchManualFillTeam

DailyDispatchManualFillTeam（识别「奖励条件」，确认在编队页）
  → Swipe1/2/3/4（依次在四个位置向上滑，填满队伍）→ FormationReturn

DailyDispatchFormationReturn / DailyDispatchLaunchReady → 回 ScanOverview
```

## 详细节点说明

| 节点 | 识别 | 说明 |
|------|------|------|
| `DailyDispatchOpenDrawerFromMain` | `CommonMainReady` | 点(35,630)抽屉 |
| `DailyDispatchEnterFromDrawer` | timeout 5s | 抽屉内识别派遣队状态 |
| `DailyDispatchClickActionableDrawerSlot` | OCR「派遣完成/闲置中」roi[0,520,175,280] | 点可操作栏位进总览 |
| `DailyDispatchReturnCompletedTeam` | OCR「队伍归来/隊伍歸來」 | 点归来按钮 |
| `DailyDispatchCloseReturnPopup` | OCR 归来弹窗文字 | 点(360,1065)关闭 |
| `DailyDispatchSelectBedroom` | OCR「魔王寝室」roi[130,200,470,560] | 识别到后进 next 选时间 |
| `DailyDispatchSelectBedroomTime1` | 同上 | 点框偏移(-155,125)选第1个时间 |
| `DailyDispatchAutoFormation` | OCR「条件推荐」roi[500,450,180,100] | 点条件推荐 |
| `DailyDispatchManualFillSwipe1` | DirectHit | Swipe (155,760)→(155,320) 持续1500ms |
| `__DailyDispatchTeamFilledColor` | ColorMatch 队伍槽蓝绿色 | count 9000，判断队伍已填满 |

## Option 配置

### 派遣地点优先级

改写 `DailyDispatchSelectLocationStart.next` 的顺序，决定先尝试哪个地点：

- 「寝室-地牢-训练所-宝藏库-封印密室」（默认）
- 「地牢-训练所-宝藏库-封印密室-寝室」
- 「训练所-宝藏库-封印密室-地牢-寝室」

### 派遣时间优先级

改写各地点节点的 next（如 `DailyDispatchSelectBedroom.next`），决定时间按钮顺序：

- 「最大时间优先」（默认）：Time1→Time2→Time3→Time4
- 「短时间优先」：Time4→Time3→Time2→Time1

## 边界情况

- 编队失败兜底：条件推荐无队 → 人员补充 → 手动滑入。
- 选地点时若所有地点都已派满（无可选时间），SelectLocationStart 超时走 on_error 返回总览。
- 总览若既无完成又无闲置，走 `ReturnMainWhenAllBusy`。
