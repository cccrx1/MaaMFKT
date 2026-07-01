# 全境征才（DailyRecruitment）

## 功能说明

从主界面进入召唤页的全境征才，依次处理 4 个招募栏位。空栏位显示「张贴榜单」和加号，点击后进入时间与条件选择页。每个栏位 OCR 识别词条并查询内置卡池表，计算保底 2 星最优组合，根据决策执行：跳过领袖、设 9 小时后招募保底 2 星、刷新、或兜底招募。所有栏位处理完后返回主界面。

## 流程概览

```
DailyRecruitmentStart（纯 router，无识别/动作，按优先级依次尝试 next 候选）
  ├─[JumpBack] CommonWaitLoading
  ├─[JumpBack] CommonCloseReward      关弹窗
  ├─    DailyRecruitmentCollectResults 总览页有「一键录取」→ 领取完成栏位奖励
  ├─    DailyRecruitmentSlot1Open      栏位1空 → 进决策
  ├─    DailyRecruitmentSlot2Open      栏位2空 → 进决策
  ├─    DailyRecruitmentSlot3Open      栏位3空 → 进决策
  ├─    DailyRecruitmentSlot4Open      栏位4空 → 进决策
  ├─    DailyRecruitmentOpenFromMain   主界面 → 点召唤 → 进全境征才
  └─[JumpBack] CommonEnsureMain       从任意子页面返回主界面

DailyRecruitmentCollectResults（OCR「一键录取」）
  → 点击 → CollectSkip（点 SKIP 动画）/ CollectClose（点「确定」关闭）
  → next/on_error 均兜底 [JumpBack]DailyRecruitmentStart，回到总览页重新评估

DailyRecruitmentOpenFromMain（TemplateMatch 右下「召唤」按钮）
  → 点击 → [JumpBack]CommonWaitLoading → DailyRecruitmentOpenFullRegion
  → on_error 兜底 [JumpBack]DailyRecruitmentStart（识别失败回到 router 重试）

DailyRecruitmentOpenFullRegion（OCR「全境征才」底栏）
  → 点击进入全境征才总览 → [JumpBack]DailyRecruitmentStart（让 router 重新评估）
  → on_error 同样兜底 [JumpBack]DailyRecruitmentStart

DailyRecruitmentSlot1Open（And: __DailyRecruitmentOverviewTitle + __DailyRecruitmentSlot1Empty）
  → 点「张贴榜单」→ DailyRecruitmentSlot1Decision（timeout 10s）
      ├─ DailyRecruitmentSlot1SkipLeader  Custom action="skip_leader" → 点(228,1045)跳过 → Slot2Open
      ├─ DailyRecruitmentSlot1RecruitGuaranteed  Custom action="recruit_guaranteed" → SetNineHours
      ├─ DailyRecruitmentSlot1Refresh  Custom action="refresh" → 点(604,640)刷新（max_hit 3）→ 重回 Decision
      └─ DailyRecruitmentSlot1RecruitFallback  Custom action="recruit_fallback" → SetNineHours

DailyRecruitmentSlot1SetNineHours（识别「招募时间」）→ 点向下箭头 1 次切到 9 小时
  → SelectTag1；若 SelectTag1 没有可点 tag，则直接 StartRecruit
DailyRecruitmentSlot1SelectTag1/2/3（Custom mode="select_tag" index=0/1/2）
  → 点 Custom 返回的 tag box → 下一 tag / StartRecruit
  → next 列表含 StartRecruit 兜底，避免作为父节点候选失败时反复重试

DailyRecruitmentSlot1StartRecruit（OCR「开始招募」）→ 点击 → Slot2Open
  → OCR 失败时固定点(500,1045)兜底
  → Slot2Open → Slot2Decision → ... → Slot3Open → ... → Slot4Open → ... → ReturnFromOverview

DailyRecruitmentReturnFromOverview（OCR「全境征才」标题）→ 点(40,75)返回
  → DailyRecruitmentDone
```

## 详细节点说明

| 节点 | 识别 | 说明 |
|------|------|------|
| `DailyRecruitmentCollectResults` | OCR「一键录取」roi[248,1016,218,63] | 总览页有一键录取按钮时点取，next 尝试 CollectSkip / CollectClose；on_error 兜底 `[JumpBack]Start` |
| `DailyRecruitmentCollectSkip` | OCR「SKIP」roi[511,37,142,80] | 跳过招募结果动画 |
| `DailyRecruitmentCollectClose` | OCR「确定/确认」roi[249,1164,230,74] | 关闭结果弹窗 → `[JumpBack]Start` 回到 router 重新评估 |
| `DailyRecruitmentOpenFromMain` | TemplateMatch 右下「召唤」按钮 | 点击识别到的召唤按钮进召唤页，max_hit 3；on_error 兜底 `[JumpBack]Start` |
| `DailyRecruitmentOpenFullRegion` | OCR「全境征才」roi[0,1120,210,90] | 点全境征才底栏入口 → `[JumpBack]Start` 让 router 重新评估；on_error 同样兜底 |
| `__DailyRecruitmentSlot1Empty` | OCR「张贴榜单」roi[250,250,220,100] | 栏位1空闲，可张贴 |
| 其他栏位同理 | Slot2 roi[250,460,220,100]，Slot3 roi[250,670,220,100]，Slot4 roi[250,880,220,100] | 依次检测 |
| `DailyRecruitmentSlot1SkipLeader` | Custom「DailyRecruitDecision」mode="skip_leader" | 决策为跳过领袖 → 点(228,1045)跳过 |
| `DailyRecruitmentSlot1Refresh` | Custom mode="refresh" | 决策为刷新 → 点(604,640)，max_hit 3 |
| `DailyRecruitmentSlot1SetNineHours` | OCR「招募时间」roi[80,160,560,240] | 点小时栏下箭头 `(188,352)` 1 次，调为 9 小时；OCR 失败也进入 SelectTag1 兜底 |
| `DailyRecruitmentSlot1SelectTag1` | Custom mode="select_tag" index=0 | 点第1个选中的 tag 框；若无 tag，则 next 继续识别 StartRecruit |
| `DailyRecruitmentSlot1StartRecruit` | OCR「开始招募」roi[390,1000,220,90] | 点确认开始；失败时 `StartRecruitClickFallback` 固定点 `(500,1045)` |

## Agent Custom Recognition

### DailyRecruitDecision（recruitment.py）

- **输入参数**：`mode`（空/skip_leader/recruit_guaranteed/recruit_fallback/refresh/select_tag）、`index`（select_tag 模式时的 tag 序号）
- **逻辑**：
  1. OCR 读取 `TAG_ROI` 内所有词条，清洗匹配 `KNOWN_TAGS`（内置词条表）。
  2. OCR 读取 `REFRESH_ROI` 内刷新次数。
  3. 枚举词条组合（3/2/1 个），查 `RECRUITMENT_POOL` 卡池表，计算每个组合的 min/max 星级、保底 2 星标志、候选卡数。
  4. 排序：`guaranteed_2_star` > `min_stars` > `max_stars` > 组合长度 > 负候选数。
  5. 决策逻辑：
     - 如果有「领袖」→ `skip_leader`
     - 否则如果最优组合保底 2 星 → `recruit_guaranteed`
     - 否则如果有刷新次数 → `refresh`
     - 否则 → `recruit_fallback`
- **返回**：
  - `box=None` 或 `box=(100,400,520,280)`（根据 mode 是否匹配 action）
  - `detail` 含 action/visible_tags/refresh_count/choice（最优组合）/ranked（前8组合）/tag_boxes（词条框位置映射）
  - `mode="select_tag"` 时复用上一次 recruit 分支缓存的 `choice`，返回 `choice.tags[index]` 对应的 box 用于点击。
  - tag box 会归一到全局坐标，并向外扩展，避免 OCR 只框中文字导致点击不到按钮。

**卡池表**：hardcode 73 个角色（3 星领袖 10 个、2 星菁英 14 个、1 星 9 个、0 星士兵等），每个角色有 `stars` 和 `tags` 集合。

## 边界情况

- 栏位已有招募进行中（无「张贴榜单」），`SlotXOpen` on_error 跳到下一栏位。
- 刷新 max_hit 3，超过次数强制走 `RecruitFallback`。
- 如果 Python 决策仍返回 `refresh`，但 pipeline 中 `Refresh` 已因 `max_hit` 跳过，`RecruitFallback` 会命中并继续招募，避免卡死。
- 无词条匹配（OCR 失败或无有效组合），`choice=None`，走 `recruit_fallback` 分支，同样先调到 9 小时再招募。
- fallback 且无 tag 可点时，`SelectTag1` 识别失败后由父节点 next 兜底到 `StartRecruit`，不会反复重试 `SelectTag1`。
- 招募开始后会回到四栏总览，继续处理下一个栏位。
- 4 个栏位全部处理完（无论跳过/招募）后，`ReturnFromOverview` 从全境征才总览左上角一次返回主界面并停止。
- **路由安全兜底**：`DailyRecruitmentStart` 是纯 router 节点，所有可能因页面状态变化而失效的出口（`CollectClose`、`CollectResults`、`OpenFromMain`、`OpenFullRegion`）的 `on_error` 和末位 `next` 均以 `[JumpBack]DailyRecruitmentStart` 收尾。这确保即使导航进入招募页后状态与预期不符（如已完成栏位数变化），流程也会跳回 router 重新按优先级评估全部候选路径，而非陷入 error handling loop。
