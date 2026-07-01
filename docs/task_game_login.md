# 启动游戏（GameLogin）

## 功能说明

关闭并重新启动游戏 App，等待游戏自主完成启动过程，处理公告、标题页点击、签到和礼包弹窗，最终停在主界面。

支持官服和 erolab 服务器两个包名，包名由 `assets/interface.json` 的“选择服务器”选项覆盖。

## 流程概览

```
GameLoginStart（StopApp）
  └─► GameLoginLaunch（StartApp，timeout 180s）
        ├─[JumpBack] CommonWaitLoading        通用 LOADING 缓冲
        ├─[JumpBack] GameCloseAnnouncement    启动公告/活动公告 → 关闭
        └─ GameTapTitleScreen                 标题页 TAP TO START / TOUCH SCREEN / Ver → 点击

GameTapTitleScreen（点击标题页，max_hit 10）
  └─► [JumpBack] CommonWaitLoading
  └─► [JumpBack] GameTapTitleScreen            点击无效时继续重试
  └─► GameAwaitGiftAfterTitle

GameAwaitGiftAfterTitle（等待登录后弹窗，timeout 120s）
  ├─[JumpBack] CommonWaitLoading
  ├─[JumpBack] GameCloseAnnouncement
  ├─[JumpBack] GameCloseSignIn                 签到弹窗 → 关闭后继续等礼包
  └─ GameCloseGift                             礼包弹窗 → 关闭

GameCloseGift
  ├─[JumpBack] CommonWaitLoading
  ├─[JumpBack] GameCloseGift                   多层礼包继续关闭
  └─ GameMainReady                             主界面 → StopTask
```

## 设计约定

- 启动 App 后，不再主动处理旧版的警告确认、SKIP、资源检查中、CONNECTING 等中间步骤；正常网络下这些过程由游戏自主完成。
- 所有会进入点击动作的路由前都优先尝试 `[JumpBack]CommonWaitLoading`，避免 Loading 期间点击无效或误触后续界面。
- 登录后礼包弹窗按“必定出现”处理：标题页点击后进入 `GameAwaitGiftAfterTitle`，不会在礼包出现前因为识别到主界面而直接结束。
- 网络故障、服务器错误等异常界面后续应加入 Common 类节点，再接入本任务路由。

## 关键节点

| 节点                    | 识别                                  | 动作               | 说明                                     |
| ----------------------- | ------------------------------------- | ------------------ | ---------------------------------------- |
| `GameLoginStart`        | 无                                    | `StopApp`          | 关闭已打开的游戏                         |
| `GameLoginLaunch`       | 无                                    | `StartApp`         | 启动所选服务器包名，然后等待公告或标题页 |
| `CommonWaitLoading`     | OCR `LOADING` / `LOAD ING`            | 无                 | 通用加载缓冲                             |
| `GameCloseAnnouncement` | OCR 王城公布栏 / 活动公告 / 最新公告  | Click `(360,1205)` | 关闭公告                                 |
| `GameTapTitleScreen`    | Or(TAP TO START / TOUCH SCREEN / Ver) | Click `(360,1135)` | 点击进入游戏，点击无效时自循环重试       |
| `GameCloseSignIn`       | OCR 签到相关文本                      | Click `(40,60)`    | 关闭签到弹窗后继续等待礼包               |
| `GameCloseGift`         | OCR STEP / 限时 / 精选 / 月卡         | Click `(40,60)`    | 关闭礼包，可处理多层礼包                 |
| `GameMainReady`         | And(出征 OCR, 调教 OCR)               | `StopTask`         | 主界面基准识别                           |

## Option 配置

| Case               | 覆盖节点                             | 包名                        |
| ------------------ | ------------------------------------ | --------------------------- |
| 工口服务器（默认） | `GameLoginStart` / `GameLoginLaunch` | `com.pinkcore.tkfm`         |
| erolab 服务器      | `GameLoginStart` / `GameLoginLaunch` | `com.pinkcore.tkfm.erolabs` |
