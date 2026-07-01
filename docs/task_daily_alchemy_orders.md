# 炼金订单（DailyAlchemyOrders）

## 功能说明

从主界面打开左侧抽屉，进入炼金页面，点击「一键收取」收取已完成的炼金收益，再逐一交付当前可交付的亮色订单，最后返回主界面。

## 流程概览

```
DailyAlchemyOrdersStart
  ├─[JumpBack] CommonWaitLoading
  ├─    DailyAlchemyOrdersOpenDrawer    主界面 → 点(35,630)打开左侧抽屉
  ├─[JumpBack] CommonCloseReward        收取/交付奖励弹窗 → 关闭（兜底）
  └─[JumpBack] CommonEnsureMain

DailyAlchemyOrdersOpenDrawer（CommonMainReady）→ 点抽屉
  └─► DailyAlchemyOrdersOpenAlchemy（OCR「派遣队1」确认抽屉已开）→ 点(116,510)炼金入口
        └─[JumpBack] CommonWaitLoading
              └─► DailyAlchemyOrdersCollect（OCR「一键收取/键收取」）→ 点击
                    ├─[JumpBack] CommonCloseReward
                    └─► DailyAlchemyOrdersScanOrder（timeout 5s）
                          ├─[JumpBack] CommonCloseReward
                          ├─[JumpBack] CommonWaitLoading
                          ├─    DailyAlchemyOrdersDeliverVisibleOrder  找亮色订单 → 点击（max_hit 7）
                          └─    DailyAlchemyOrdersReturnMain  OCR「炼金」→ 点(40,72)返回

DailyAlchemyOrdersDeliverVisibleOrder（ColorMatch 橙色区域，Horizontal 排序）
  → 点击命中框偏移(+70,+70) → [JumpBack]CommonCloseReward → 回 ScanOrder

DailyAlchemyOrdersReturnMain → DailyAlchemyOrdersDone → CommonStopOnMainWithRetries
```

## 详细节点说明

| 节点 | 识别 | 说明 |
|------|------|------|
| `DailyAlchemyOrdersOpenDrawer` | `CommonMainReady` | 点(35,630)打开左侧抽屉 |
| `DailyAlchemyOrdersOpenAlchemy` | OCR「派遣队1」（确认抽屉显示）| 点(116,510)炼金图标 |
| `DailyAlchemyOrdersCollect` | OCR「一键收取/键收取」roi[390,750,210,90] | 收取炼金收益 |
| `DailyAlchemyOrdersDeliverVisibleOrder` | ColorMatch 橙色（HSV method 40，lower[15,80,120] upper[45,255,255]，count 120，connected，Horizontal 排序）| 点亮色可交付订单，max_hit 7 |
| `DailyAlchemyOrdersReturnMain` | OCR「炼金」roi[70,120,120,70] | 点(40,72)左上角返回按钮 |

## 技术细节：ColorMatch 识别可交付订单

`DailyAlchemyOrdersDeliverVisibleOrder` 使用 ColorMatch 识别订单行中的**橙色可交付状态色块**（HSV 橙色范围，connected 连通，Horizontal 排序取最左侧），点击框中心偏移 (+70,+70) 定位到订单的交付按钮。max_hit 7 确保最多处理 7 个订单后跳出（防止无限循环）。

## 边界情况

- 若无可收取收益（一键收取按钮不存在），`DailyAlchemyOrdersCollect` 超时，直接进 `DailyAlchemyOrdersScanOrder`。
- 无可交付订单时，`DeliverVisibleOrder` 识别失败，直接走 `ReturnMain`。
