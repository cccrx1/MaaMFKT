# 奖励领取（DailyTaskRewards）

## 功能说明

从主界面进入任务页，依次切换「每日」「每周」「每月」「个人」「活动」「协会」6 个页签，每个页签识别到可领取任务时点击「一键领取」并关闭奖励弹窗，全部页签处理完后返回主界面。

## 流程概览

```
DailyTaskRewardsStart
  ├─[JumpBack] CommonWaitLoading
  ├─    DailyTaskRewardsOpenFromMain  主界面 → 点(653,86)任务入口
  └─[JumpBack] CommonEnsureMain

DailyTaskRewardsOpenFromMain → DailyTaskRewardsSelectDaily（点「每日」页签）
  └─► DailyTaskRewardsClaimDaily（timeout 10s）
        ├─[JumpBack] CommonCloseReward
        ├─    DailyTaskRewardsClaimDailyAvailable（And: 任务页标题 + 「可领取」+ 「一键领取」按钮）→ 点击（max_hit 3）
        └─    DailyTaskRewardsSelectWeekly

DailyTaskRewardsSelectWeekly → DailyTaskRewardsClaimWeekly（同上结构）
  └─► DailyTaskRewardsSelectMonthly → DailyTaskRewardsClaimMonthly
        └─► DailyTaskRewardsSelectPersonal → DailyTaskRewardsClaimPersonal
              └─► DailyTaskRewardsSelectActivity → DailyTaskRewardsClaimActivity
                    └─► DailyTaskRewardsSelectGuild → DailyTaskRewardsClaimGuild
                          └─► DailyTaskRewardsReturnMainFromTaskPage

DailyTaskRewardsReturnMainFromTaskPage（OCR「任务」）→ 点(360,1187)底栏返回
  └─► DailyTaskRewardsDone → CommonStopOnMainWithRetries
```

## 详细节点说明

| 节点 | 识别 | 说明 |
|------|------|------|
| `DailyTaskRewardsOpenFromMain` | `CommonMainReady` | 点(653,86)右上角任务图标 |
| `__DailyTaskRewardsPageTitle` | OCR「任务」roi[260,140,200,90] | 辅助识别：确认在任务页 |
| `__DailyTaskRewardsClaimable` | OCR「可领取」roi[90,350,540,670] | 辅助识别：页面内有可领取任务 |
| `__DailyTaskRewardsOneClickClaimButton` | OCR「一键领取」roi[250,1015,220,100] | 辅助识别：一键领取按钮存在 |
| `DailyTaskRewardsSelectDaily` | OCR「每日」roi[80,215,190,70] | 点切换到每日页签 |
| `DailyTaskRewardsClaimDailyAvailable` | And(PageTitle, Claimable, Button, **box_index: 2**) | 三个条件都满足后取 Button 的坐标点击（`target: true`），max_hit 3 |
| 其他页签的 Select / Claim 节点 | 同上，ROI 不同，均使用 box_index:2 + target:true | 每周 roi[265,215,190,70]；每月 roi[450,215,190,70]；个人 roi[80,275,190,70]；活动 roi[265,275,190,70]；协会 roi[450,275,190,70] |
| `DailyTaskRewardsReturnMainFromTaskPage` | OCR「任务」 | 点(360,1187)底栏返回键 |

## 边界情况

- 每个页签的 Claim 节点用 `And` 组合三个条件（页面标题 + 可领取文本 + 一键领取按钮），避免误识别。
- 每个页签最多点击 3 次（max_hit 3），防止奖励弹窗关不掉时死循环。
- `[JumpBack]CommonCloseReward` 兜底关闭奖励「确定」弹窗。
- 若某页签无可领取任务，ClaimXxxAvailable 识别失败，直接 timeout 跳到下一页签。
- **已修复 (2026-06-25)**：6 个 `ClaimXxxAvailable` 节点的 And 识别中 `target: "__DailyTaskRewardsOneClickClaimButton"` 参照子节点名查找坐标，MaaFramework v5.9.0-alpha.4 无法在 And 内解析子节点名称，导致 `action:""` `box:[0,0,0,0]` 点击失败。改为 `box_index: 2`（取第三个子节点 = 一键领取按钮）+ `target: true`（点自己的识别框）。
