# 商城购买（DailyShop）

## 功能说明

从主界面进入商城，先进入交易所，根据「指定购买物品」输入项扫描并购买匹配到的目标，再进入协会商店购买固定目标：召唤契约、魔晶石、阿克色记录。点击链路前后都插入 `CommonWaitLoading` 作为通用加载缓冲。

## 流程概览

```
DailyShopStart
  ├─ [JumpBack] CommonWaitLoading
  ├─ DailyShopResetExchangeSession
  ├─ DailyShopOpenFromMain
  ├─ [JumpBack] DailyShopReturnMain
  └─ [JumpBack] CommonEnsureMain

DailyShopOpenFromMain
  └─ [JumpBack] CommonWaitLoading
     └─ DailyShopOpenDailyExchange
        └─ [JumpBack] CommonWaitLoading
           └─ DailyShopOpenExchangeTab
              └─ [JumpBack] CommonWaitLoading
                 └─ DailyShopExchangeScanTop/Middle/Bottom
                    ├─ [JumpBack] CommonWaitLoading
                    ├─ DailyShopExchangeTargetItem -> [JumpBack] DailyShopPurchaseCurrentItem -> 回 ScanTop
                    ├─ DailyShopExchangeSwipe1/2
                    └─ DailyShopOpenGuildShop

DailyShopOpenGuildShop
  └─ [JumpBack] CommonWaitLoading
     └─ DailyShopGuildScanTop/Middle/Bottom
        ├─ [JumpBack] CommonWaitLoading
        ├─ DailyShopGuildSummonContract / DailyShopGuildCrystal / DailyShopGuildAkseliRecord
        ├─ [JumpBack] DailyShopPurchaseCurrentItem -> 回 ScanTop
        ├─ DailyShopGuildSwipe1/2
        └─ DailyShopReturnMain -> DailyShopDone -> CommonStopOnMainWithRetries
```

## Option 配置

- `指定购买物品`：输入单行文本，默认 `紧急录用证|初级体力药水|招募命令`。
- 支持 `|`、逗号、分号、斜杠、反斜杠和换行作为分隔符；UI 校验当前限制为单行。
- 该选项通过 `pipeline_override` 写入 `DailyShopExchangeTargetItem.recognition.param.custom_recognition_param.target_names`。

## Agent Custom Recognition

`agent/daily_shop.py` 注册了两个自定义逻辑：

| 名称 | 类型 | 说明 |
|------|------|------|
| `DailyShopResetExchangeSession` | CustomAction | 每次商城任务开始时重置本次交易所购买状态。 |
| `DailyShopExchangeTargetItem` | CustomRecognition | OCR 读取交易所可见商品名，匹配用户输入清单，返回可点击商品框。 |

## 详细节点说明

| 节点 | 识别 | 说明 |
|------|------|------|
| `DailyShopOpenFromMain` | OCR「商城」roi[420,1160,115,80] | 主界面商城底栏入口。 |
| `DailyShopOpenDailyExchange` | OCR「商城」 | 点击 (430,135) 进入每日页。 |
| `DailyShopOpenExchangeTab` | OCR「交易所」roi[95,180,175,70] | 打开交易所子标签。 |
| `DailyShopExchangeTargetItem` | Custom | 从交易所列表中找用户输入的目标，点商品图标上方偏移 -80。 |
| `DailyShopPurchaseCurrentItem` | OCR「购买」roi[260,780,200,80] | 确认购买弹窗中的购买按钮，并通过 `CommonCloseReward` 关奖励弹窗。 |
| `DailyShopOpenGuildShop` | OCR「协会商店」roi[460,180,175,70] | 切换到协会商店标签。 |
| `DailyShopGuildSummonContract` | OCR「召唤契约」roi[80,300,540,760] | 固定购买目标，max_hit 1。 |
| `DailyShopGuildCrystal` | OCR「魔晶石」同上 | 固定购买目标，max_hit 1。 |
| `DailyShopGuildAkseliRecord` | OCR「阿克色记录」同上 | 固定购买目标，max_hit 1。 |
| `DailyShopGuildSwipe1/2` | DirectHit | 向下翻页（940 -> 570）。 |
| `DailyShopReturnMain` | OCR「城堡」roi[65,1160,120,80] | 底栏城堡按钮返回主界面。 |

## 边界情况

- 交易所目标由 Agent 去重；同一目标在一次商城任务内命中后不会重复购买。
- 交易所分 Top/Middle/Bottom 三段扫描，找不到目标后进入协会商店。
- 协会商店仍使用固定 OCR 目标和 `max_hit: 1`，每次购买后回到 `DailyShopGuildScanTop` 重扫。
- 所有进入页面、点击商品、购买确认前都通过 `CommonWaitLoading` 做加载兜底。
