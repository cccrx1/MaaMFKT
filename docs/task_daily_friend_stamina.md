# 领取体力（DailyFriendStamina）

## 功能说明

从主界面进入玩家信息页，切换到好友清单，点击「一键领取」领取好友赠送的体力，然后关闭页面返回主界面。

## 流程概览

```
DailyFriendStaminaStart
  ├─[JumpBack] CommonWaitLoading
  ├─    DailyFriendStaminaOpenProfileFromMain  主界面 → 点头像(150,105)
  ├─[JumpBack] DailyFriendStaminaWaitFriendListLoading  好友列表加载中 → 等待
  ├─[JumpBack] DailyFriendStaminaCloseProfile  任意已进入个人信息页 → 点底栏返回（兜底）
  └─[JumpBack] CommonEnsureMain

DailyFriendStaminaOpenProfileFromMain（CommonMainReady）→ 点头像
  └─► DailyFriendStaminaOpenFriendList（OCR「玩家信息」）→ 点(360,219)切换好友清单
        └─► DailyFriendStaminaReceive（timeout 5s）
              ├─[JumpBack] DailyFriendStaminaWaitFriendListLoading  加载中 → 等待/重试
              ├─    DailyFriendStaminaClickReceive  OCR「一键领取」→ 点击（max_hit 1）
              └─    DailyFriendStaminaCloseProfile  关闭页面

DailyFriendStaminaWaitFriendListLoading（Or: LOADING OCR / 「能量获取：XX/YY」OCR）
  → 等待 700ms → 再次尝试 / DailyFriendStaminaCloseProfileForRetry（关页重进）

DailyFriendStaminaCloseProfile → DailyFriendStaminaDone → CommonStopOnMainWithRetries
```

## 详细节点说明

| 节点 | 识别 | 说明 |
|------|------|------|
| `DailyFriendStaminaOpenProfileFromMain` | `CommonMainReady` | 点头像进个人信息页 |
| `DailyFriendStaminaOpenFriendList` | OCR「玩家信息」 | 点「好友清单」入口位置 |
| `DailyFriendStaminaWaitFriendListLoading` | Or(LOADING / 「能量获取：XX/YY」) | 加载 placeholder 文本消失前一直等，并提供重新进入的路径 |
| `DailyFriendStaminaClickReceive` | OCR「一键领取/键领取」roi[390,1050,230,90] | max_hit 1，避免重复点 |
| `DailyFriendStaminaCloseProfile` | OCR「好友清单/玩家信息」roi[250,110,380,190] | 点(360,1220)底栏返回 |
| `DailyFriendStaminaCloseProfileForRetry` | 同上 | 关页面后重进（当 Loading 超时时走） |

## 边界情况

- 好友列表加载偶尔卡住，`WaitFriendListLoading` 最多等若干轮后走 `CloseProfileForRetry` 关掉重进一次。
- `一键领取` 未出现（好友无赠送体力时），直接走到 `CloseProfile` 关闭页面，正常结束。
