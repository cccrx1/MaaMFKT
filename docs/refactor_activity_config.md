# 体力活动配置改造方案

## 动机

当前「消耗体力」任务的关卡配置全部手写在 `assets/interface.json` 的 `option["体力消耗关卡"].pipeline_override` 中。每个关卡需要约 60 行 JSON（10 个 Preset 节点），5 个同活动关卡就是 300 行，其中 90% 的字段完全相同。

**痛点：**

1. **新增关卡繁琐**——复制粘贴一个大 JSON 块，只改其中两三个字段（关卡标题/副标题），容易漏改或改错。
2. **删除活动困难**——需要找到对应 case 块精确删除，中间不留尾逗号。
3. **公共配置冗余**——同一活动的 RouteStart / ActivitySection / StageEntry / StaminaCost 等完全一致的字段在每个关卡都重复一遍。
4. **代码审查不友好**——diff 中一眼望去全是 JSON，难以看出「只改了关卡名称」。

## 方案：YAML 配置 + 构建脚本生成

### 核心思路

```
activities.yaml           build_activities.py         interface.json
（人编辑）      ──►        （Python 脚本）      ──►     （机器生成）
 简洁、有模板、             读取 YAML，展开模板，         完整 JSON，结构
 无冗余的配置               生成 pipeline_override        不变，UI / CI 兼容
```

**interface.json 的结构不变**——它仍然是 MaaFramework 直接读取的最终产物。只是不再手写其中的 `option["体力消耗关卡"].cases`，而是由脚本从 YAML 生成。

### 数据流

```
用户修改 activities.yaml
        │
        ▼
运行 python tools/build_activities.py
        │
        ▼
脚本读取 activities.yaml + 现有 interface.json
→ 生成新的 cases 数组
→ 替换 interface.json 中 option["体力消耗关卡"].cases
→ 写出 interface.json（保持 JSON 格式合法）
        │
        ▼
提交 activities.yaml + interface.json 到仓库
        │
        ▼
CI 检查：跑脚本 → git diff --exit-code → 生成文件与源配置是否一致
```

## YAML 配置格式

### 设计原则

- **模板（templates）**：把同一活动的公共配置抽成一个命名模板，关卡只引用模板名 + 覆盖标题/副标题。
- **平铺字段**：不嵌套太深，新增模板时一目了然。
- **支持所有路由类型**：special_ui / challenge_ui / normal_list / rerun_ui / daily_affairs。

### 完整示例

```yaml
# assets/resource/activities.yaml

templates:
  # ── 冰霜下的残响 · 钓鱼活动（特殊 UI） ──
  frost-echo:
    route_type: special_ui           # 路由类型，决定 InnerRouteStart.next
    activity_section:
      expected: ["限时活动"]
      roi: [480, 90, 150, 80]
    activity_name:
      expected: ["冰霜下的残响"]
      roi: [60, 740, 260, 100]
    inner_ui_title:
      expected: ["冰霜下的残响"]
      roi: [0, 90, 240, 100]
    stage_entry:                     # 仅 special_ui 需要
      type: TemplateMatch
      template: "DailyStamina/FrostEchoStageIcon.png"
      roi: [400, 880, 250, 270]
      threshold: 0.72
    stage_list_roi: [70, 90, 580, 1000]
    stamina:
      cost: 45
      roi: [500, 0, 180, 45]

  # ── 未来活动示例：挑战 UI ──
  # some-challenge-event:
  #   route_type: challenge_ui
  #   activity_section:
  #     expected: ["限时活动"]
  #     roi: [480, 90, 150, 80]
  #   activity_name:
  #     expected: ["某挑战活动"]
  #     roi: [60, 740, 260, 100]
  #   inner_ui_title:
  #     expected: ["某挑战活动"]
  #     roi: [0, 90, 240, 100]
  #   stage_list_roi: [70, 90, 580, 1000]
  #   stamina:
  #     cost: 50
  #     roi: [500, 0, 180, 45]

activities:
  - name: "冰霜下的残响 - 钓鱼-01"
    description: "限时活动 → 冰霜下的残响 → 钓鱼-01"
    template: frost-echo
    stage_titles: ["Lv.10 钓鱼-01", "10钓鱼-01", "钓鱼-01"]
    stage_subtitles: ["鱼儿鱼儿冰中游"]

  - name: "冰霜下的残响 - 钓鱼-02"
    description: "限时活动 → 冰霜下的残响 → 钓鱼-02"
    template: frost-echo
    stage_titles: ["Lv.10 钓鱼-02", "10钓鱼-02", "钓鱼-02"]
    stage_subtitles: ["鱼儿鱼儿冰中游I"]

  - name: "冰霜下的残响 - 钓鱼-03"
    description: "限时活动 → 冰霜下的残响 → 钓鱼-03"
    template: frost-echo
    stage_titles: ["Lv.10 钓鱼-03", "10钓鱼-03", "钓鱼-03"]
    stage_subtitles: ["鱼儿鱼儿冰中游Ⅲ"]

  - name: "冰霜下的残响 - 钓鱼-04"
    description: "限时活动 → 冰霜下的残响 → 钓鱼-04"
    template: frost-echo
    stage_titles: ["Lv.10 钓鱼-04", "10钓鱼-04", "钓鱼-04"]
    stage_subtitles: ["鱼儿鱼儿冰中游IV"]

  - name: "冰霜下的残响 - 钓鱼-05"
    description: "限时活动 → 冰霜下的残响 → 钓鱼-05"
    template: frost-echo
    stage_titles: ["Lv.10 钓鱼-05", "10钓鱼-05", "钓鱼-05"]
    stage_subtitles: ["鱼儿鱼儿冰中游V"]
```

### 字段说明

| 字段 | 层级 | 必填 | 说明 |
|------|------|------|------|
| `name` | activity | ✅ | UI 下拉菜单中显示的名称 |
| `description` | activity | ✅ | UI 中显示的描述文本 |
| `template` | activity | ✅ | 引用的模板名（`templates` 中的 key） |
| `stage_titles` | activity | ✅ | 关卡标题 OCR expected 列表 |
| `stage_subtitles` | activity | ✅ | 关卡副标题 OCR expected 列表 |
| `route_type` | template | ✅ | 路由类型：`special_ui` / `challenge_ui` / `normal_list` / `rerun_ui` / `daily_affairs` |
| `activity_section` | template | ✅ | 活动区标签 OCR |
| `activity_name` | template | ✅ | 活动列表中识别活动名的 OCR |
| `inner_ui_title` | template | 条件 | 活动内标题 OCR（special_ui / challenge_ui 需要） |
| `stage_entry` | template | 条件 | 关卡入口模板匹配（仅 special_ui 需要） |
| `stage_list_roi` | template | ✅ | 关卡列表 OCR 扫描区域 |
| `stamina` | template | ✅ | 体力消耗 cost 和读取 ROI |

### 新增一个同活动关卡（如钓鱼-06）

只需在 `activities` 列表末尾加 4 行：

```yaml
  - name: "冰霜下的残响 - 钓鱼-06"
    description: "限时活动 → 冰霜下的残响 → 钓鱼-06"
    template: frost-echo
    stage_titles: ["Lv.10 钓鱼-06", "10钓鱼-06", "钓鱼-06"]
    stage_subtitles: ["鱼儿鱼儿冰中游VI"]
```

### 新增一个全新活动

先在 `templates` 下加一个新模板（约 20 行），再在 `activities` 下加关卡条目（各 4 行）。

## build_activities.py 脚本职责

1. 读取 `assets/resource/activities.yaml`
2. 校验：每个 activity 引用的 template 必须存在，route_type 必须合法
3. 读取 `assets/interface.json`
4. 对每个 activity，根据其 template 生成对应的 `pipeline_override` 块：
   - 生成 10 个 Preset 节点的覆盖（RouteStart / ActivitySection / InnerRouteStart / ActivityName / InnerUiTitle / StageEntry / StageListTargetTitle / StageListTargetSubtitle / StaminaEnough / StaminaLow）
   - 根据 `route_type` 决定 `InnerRouteStart.next` 指向哪个路由节点
   - `special_ui` → `DailyStaminaRouteInnerSpecialUiStart`
   - `challenge_ui` → `DailyStaminaRouteInnerChallengeUiStart`
   - `normal_list` → `DailyStaminaRouteInnerNormalListStart`
   - 等等
5. 将生成的 cases 数组写入 `interface.json` 的 `option["体力消耗关卡"].cases`
6. 保持 interface.json 其余部分完全不变
7. 可选：自动生成 `DailyStaminaPresetStageListAnySelectable` 的 expected 列表（汇总所有关卡的 title/subtitle）

## CI 集成

在 `.github/workflows/check.yml` 中增加一步：

```yaml
- name: Verify interface.json is up to date
  run: |
    python tools/build_activities.py
    git diff --exit-code assets/interface.json
```

如果开发者修改了 `activities.yaml` 但忘记运行 `build_activities.py` 并提交更新后的 `interface.json`，CI 会报错，阻止合并。

## 迁移计划

### 阶段 1：创建脚本和 YAML（不影响现有功能）

1. 创建 `assets/resource/activities.yaml`，写入当前 5 个关卡的配置
2. 创建 `tools/build_activities.py`
3. 运行脚本，验证输出的 `interface.json` 与当前手写版**完全一致**
4. 更新 `docs/dev_guide.md`：将「新增体力关卡 Preset」章节改为指向 YAML 配置
5. 更新 `CLAUDE.md`：增加 activities.yaml 维护说明

### 阶段 2：CI 守卫

6. 修改 `.github/workflows/check.yml`，加生成同步检查

### 阶段 3：后续迭代（可选）

- 支持活动级别的 `enabled: false`，一键隐藏过期活动而不删除配置
- 脚本增加 `--check` 模式，只校验不写入
- 支持模板继承（一个模板基于另一个模板微调）

## 不做的事

- **不改动 Pipeline JSON 本身**——`daily_stamina_presets.json` 和 `daily_stamina_routes.json` 保持不变，它们仍然是固定逻辑层。
- **不改动 interface.json 的其他 option**——派遣、调教等配置暂不纳入生成，等体力活动方案验证成功后按需扩展。
- **不引入新的依赖**——Python 标准库 `json` + `yaml`（PyYAML）即可；PyYAML 在 CI 环境中已可用（`validate_schema.py` 同样依赖外部包）。

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| 脚本生成的 JSON 格式与手写不一致 | 迁移时先做 byte-for-byte 对比，确保等价 |
| YAML 语法错误导致生成失败 | CI 中 `python tools/build_activities.py` 失败会阻止合并 |
| 未来 MaaFramework 更新 pipeline_override 机制 | 只需改脚本的生成逻辑，activities.yaml 无需变动 |
| 模板字段不够灵活（某些关卡需要微调模板外的字段） | activity 级别支持 `extra_overrides` 字段，可追加任意节点覆盖 |
