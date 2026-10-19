---
name: nwy-feishu-ticket-flow-skill
description: 飞书项目单子流转收口：开发+验证完成后把缺陷单从 Open 链式流转到回归（Open→Fixed→Regression 两跳走完），补全必填表单、关联回归版本、填写必填角色。单子正常起点是 Open；已在 Fixed 的单子则只走 Fixed→Regression 一跳。兼顾需求单/ITR（节点流）的节点确认流转。当用户说"流转单子""走单""提测""单子收口""流转到回归""单子流转"时使用。不负责代码修复/编译（走 nwy-ec626-build-skill）/提交（走 nwy-git-commit-skill），也不负责回归通过后的关闭。
developer: mengxiangrui (mengxiangrui@neoway.com)
---

# 单子流转收口 Skill

开发验证完成后的"走单"最后一棒：把单子一次性流转到**回归（Regression）**，必填项一轮问完、不再挤牙膏。

## 适用范围

| 单子类型 | 流模式 | 处理方式 |
|---------|--------|---------|
| **缺陷 / issue**（主线） | 状态流 | Open → Fixed → Regression，`workflow transition-state` |
| 需求 / story / **ITR**（兼顾） | 节点流 | 节点确认流转，`workflow transition --action confirm`，见「需求单/ITR（节点流）分支」 |

**不在范围**：代码修复、编译（走 `nwy-ec626-build-skill`）、提交（走 `nwy-git-commit-skill`）、回归通过后的关闭。

## 前置条件（开跑前口头确认一句）

代码已入库（有 Gerrit 链接）、测试已验证。缺哪个先补哪个，别带着空洞流转。

## 🚨 强制规则

1. **业务决策类字段（归属部门/问题类型/时间/共性/人员）禁止代填**，一轮收集问完
2. **说明类文本**（根因/波及/修改点/自测/测试建议）从会话上下文（git log、Gerrit、根因分析）起草，一轮确认后写入
3. **必填项一次查全**：`workflow list-state-required` **不带 `--mode`**。实测 `--mode unfinished` 只返回 8/16 项（按文档语义它应只过滤已完成项，疑实现有坑，存疑）；要全景一轮收齐就**一律不带 mode**
4. **换状态后 transition_id 失效**（报 Illegal Operation）——每次流转前重新 `list-state-transitions`
5. 人员字段（如软件PL）用户不指定就问，**禁止默认填当前操作者**；姓名→userkey 走 `meegle user search`，同名多人必须让用户选
6. 每步先汇报结论再走下一步；任何一步失败先读 err_msg 再修，连续 2 次同类失败停
7. **实测集合是唯一事实源**：必填项以 `list-state-required` 返回为准，本文档的 16 项表只是预期对照（表单改版会过时）——见 Step 2 对账

## 流程（缺陷单主线）

### 链式流转（Open 起步的标准走法，先读这段）

**Open → Fixed → Regression 是两跳，不是一跳**，走单要循环到 Regression 才算完：

| 跳 | 流转 | 要做的事 |
|----|------|---------|
| 第 1 跳 | Open → Fixed | 补 16 项表单 + 软件PL 角色（Step 2~5），表单见下表 |
| — | 状态已变 | transition_id 全部失效 → **回 Step 1 重新 `list-state-transitions`** |
| 第 2 跳 | Fixed → Regression | confirm_form 只有 字段填写检查+回归版本（Step 4 关联好就绪），流转后复核状态=Regression |

- 每跳完成先汇报"XX → YY 成功"，再走下一跳
- 中途任何一跳失败 → 停下汇报，按「断点续跑」处理，别硬闯别回滚
- 到 Regression 为止收工（关闭不归本技能管）

**起点变体**：

| 当前状态 | 走法 |
|---------|------|
| Open / New / Assigned | 标准两跳：Open→Fixed→Regression |
| Fixed | 单跳：Fixed→Regression（Step 4 的回归版本是这跳唯一拦路石） |
| **Reopen / HCCB（打回）** | **视作 Open 起点重走两跳**：修改类/时间类字段（修改点、自测步骤、处理时间、代码修改等）按本轮修复**更新**，原因类文本补打回背景；打回原因字段属说明性文本可默认"重新打开后修复" |
| Rejected / Cancel / 已终止 | 已否决态，**停下确认**，不硬闯 |
| Regression | 已在目标态，告知用户无需流转 |

### Step 1: 定位单子 + 查流转路径

```bash
# 单子 ID/URL → project_key + work_item_id（URL 先 meegle url decode）
meegle auth status --format json                                   # 授权检查
meegle user search --user-keys '["current_login_user()"]' ...      # 当前 userkey
meegle workflow list-state-transitions --work-item-id <ID> --work-item-type issue \
  --user-key <当前userkey> --project-key <K> --format json          # 当前状态+候选路径
```

- 展示当前状态和所有可流转目标，**选唯一向前路径**：
  - Open 时向前 = **Fixed**（HCCB=打回、Rejected=拒绝都不要）
  - Fixed 时向前 = **Regression**（Open 退回那条不要）
- 目标不唯一时展示让用户选
- 返回里的目标 `state_key`（如 `RESOLVED`/`n3GA6iDsD`）记下来——Step 2 的 `--state-key` 就用它

### Step 2: 必填项一次查全 + 与 16 项表对账

```bash
meegle workflow list-state-required --work-item-id <ID> --state-key <Step1返回的目标state_key> \
  --project-key <K> --format json    # 🚨 不带 --mode！
```

**对账（必做）**：把返回集合与下面的 16 项表 diff——
- **返回多出的项**：现场按类型处理（枚举取 option 问用户、文本起草、事实类确认），**key 以返回为准**
- **返回少于表**：正常（部分项可能已填过），以返回集合为要填清单
- **role key**（软件PL）用 `workitem meta-roles` 核验，不照抄表里的 `role_343ed9`
- 表单改版（template_version 变化）后表会过时，**表是预期对照，不是圣经**

**SPM研发空间1 issue → Fixed 的必填全景（2026-10 实测 16 项，作对照用）**：

| # | 字段 | key | 类型 | 值来源 |
|---|------|-----|------|--------|
| 1 | 缺陷归属部门 | field_686bfd | select：软件/硬件/工具软件 | **问用户** |
| 2 | 问题类型 | field_8719e0 | select：自研非修改引入/自研修改引入/平台问题/第三方SDK/需求缺陷引入/其他 | **问用户** |
| 3 | 处理时间(天) | field_d95611 | number | **问用户**（数字题用 Other 自由输入） |
| 4 | 问题根因 | field_302d94 | text | 起草 |
| 5 | 波及内容 | field_77fa74 | text | 起草 |
| 6 | 测试建议 | field_17f66e | text | 起草 |
| 7 | 研发自测步骤 | field_16c79d | multi-text | 起草 |
| 8 | 研发修改点描述 | field_48c1dd | multi-text（含 Gerrit 链接） | 起草 |
| 9 | 入库链接 | field_ce2227 | text：Gerrit URL | git/会话上下文 |
| 10 | 更新自动化用例 | field_d982ec | radio：是/否 | 事实确认 |
| 11 | 代码修改 | field_686c46 | radio：是/否 | 事实确认 |
| 12 | 交付件文档是否更新 | field_bb927b | bool | 事实确认 |
| 13 | 上个版本是否存在 | field_fc670f | radio：是/否 | **问用户** |
| 14 | 是否为共性问题 | field_e51a05 | select：否/是-排查平台重点客户/是-排查所有平台 | **问用户** |
| 15 | 非格式化升级是否生效 | field_0ee3ef | bool | **问用户** |
| 16 | **软件PL 角色** | role_343ed9（以 meta-roles 为准） | role_operate 填人 | **问用户** |

> 枚举 option_id 用 `meta-fields --field-keys '[...]'` 批量取（选项在返回的 `option` 键下）。

### Step 3: 一轮收集全部信息

**所有"问用户"项 + 起草文本确认，一次收集完，禁止逐字段连环问。** 按类型打包成题（每轮 AskUserQuestion 最多 4 题，**超 4 题就在同一消息里拆成连续两轮弹出**，仍是"一轮收集"）：

| 题 | 覆盖字段 | 选项形式 |
|----|---------|---------|
| ① 归属部门 | 缺陷归属部门 | 软件/硬件/工具软件 |
| ② 问题类型 | 问题类型 | 六选项各一项 |
| ③ 事实类打包 | 更新自动化用例 / 代码修改 / 交付件文档 | "按事实填入"/"我要改"（说明里写明拟填值） |
| ④ 历史+共性打包 | 上个版本是否存在 / 是否为共性问题 | "按推荐填入"/"我要改" |
| ⑤ 数字+bool | 处理时间(天)（**数字题：选项给 0.5/1/2/3，其他走 Other 自由输入**）、非格式化升级是否生效 | 数字选项 + 是/否 |
| ⑥ 文本草稿确认 | 问题根因/波及内容/测试建议/研发修改点/研发自测步骤 | "按草稿填入"/"我要改" |
| ⑦ 人员 | 软件PL | "填我"/"指定他人（Other 输入姓名）"/"取消" |

①② 是**决策字段不能漏**（16 项表的"问用户"项一个都不能少）；Reopen 场景下④⑤的修改类字段要按本轮修复重新确认。

### Step 4: 关联回归版本（如目标含回归）

`resolve_version`（回归版本）是 `workitem_related_multi_select`，关联 `version` 工作项：

```bash
# 🚨 MQL 必须带项目限定且标识符加反引号：FROM `<project_key>`.`<类型>`
meegle workitem query --project-key <K> \
  --mql "SELECT work_item_id, name FROM `n58`.version WHERE name LIKE '%EA\_SX-002%'" --format json
# 写入：field_value = "[<version_id>]"（stringified 数字数组）
meegle workitem update --work-item-id <ID> --project-key <K> \
  --fields '[{"field_key":"resolve_version","field_value":"[7103556120]"}]'
```

- 项目限定用 `n58`（simple_name）或 project_key 均可，**来自 `project search`，不要凭记忆**；LIKE 里 `_`/`%` 要转义（`\_`）
- 同名版本多于一个时展示让用户选，禁止取第一个

**版本域边界（改挂/挂错怎么办）**：
- `workitem update` 是**整数组覆盖**，不是追加：改挂 = 读旧值 → 数组里替换目标 id → 整组回写；补挂 = 读旧值 ∪ 新 id
- 目标版本是**终态/冻结**（如"终止测试"）→ 写入报 `ErrEditFieldNoPermission` 或 `invalid value ... 选项值已失效`：**API 恢复不了，转用户页面操作或找管理员**，不要反复重试
- **分工**：本技能只写缺陷侧 `resolve_version`；往版本单挂缺陷/ITR（版本侧 `field_bb75b4`/`field_727455`）走 `nwy-meegle-version-tickets-skill`。两侧是同一条边，别两边都写

### Step 5: 写字段 + 角色，再流转

```bash
# 字段 STRING 协议：select/radio 传 option_id 字符串、bool "true"/"false"、multi-text 传 Markdown
meegle workitem update --work-item-id <ID> --project-key <K> \
  --fields '[{"field_key":"...","field_value":"..."}, ...]' \
  --role-operate '[{"op":"add","role_key":"<meta-roles核验的key>","user_keys":["<userkey>"]}]'

meegle workflow transition-state --work-item-id <ID> --project-key <K> \
  --transition-id <从 Step 1 取> --format json
```

- 报 `ErrFieldRequired` → 按 err_msg 补对应字段再试（Step 2 对账做全了基本不会遇到）
- 报 `Illegal Operation` → 状态已被别人动过，回 Step 1 重新查路径
- **复核必须显式带 `--fields`**（`workitem get` 默认返回**不含自定义字段**，裸复核形同虚设）：

```bash
meegle workitem get --work-item-id <ID> --project-key <K> \
  --fields '["resolve_version"]' -o json    # 状态看 work_item_attribute.work_item_status
```

### Step 6: 汇报并交接

展示：状态变更方向（如 Open → Fixed → Regression）、**实际的回归版本名**、写入的字段摘要、单子去向（测试部在 `<回归版本名>` 上回归 → 通过后关闭）。**到 Regression 为止，关闭不归本技能管**。

### 断点续跑（中途失败后怎么接着走）

- **记录进度**：已完成哪跳、已写入哪些字段/角色——流转**不回滚已写字段**，续跑从当前状态继续，**不重复收集**已写项
- 续跑三步：重新 `list-state-transitions`（拿新 transition_id）→ `list-state-required` 对账补缺 → 流转
- 第 1 跳成功第 2 跳失败是最常见断点：字段都还在，只需补 `resolve_version` 再流转
- 版本挂错要改挂：按 Step 4「版本域边界」的整数组覆盖写法替换，别叠加

## 需求单/ITR（节点流）分支

节点流单子**没有 transition-state**，用节点确认。**必填项写入路径与状态流不同，走错会静默丢数据**：

```bash
# 1. 看节点（🚨 输出可能是畸形 JSON，宽松解析，只取 name / node_key / status 三个键）
meegle workflow get-node --work-item-id <ID> --node-id-list _all --project-key <K> -o json

# 2. 目标节点必填项（--state-key 传节点的 node_key）
meegle workflow list-state-required --work-item-id <ID> --state-key <node_key> --project-key <K> --format json

# 3. 节点确认（🚨 --node-ids 只接受 node_key，不支持节点名——先从 get-node 结果解析 name→node_key）
meegle workflow transition --work-item-id <ID> --project-key <K> \
  --action confirm --node-ids '<node_key>' ...
```

**必填项写入分流（关键）**：
- `class=field` 的普通字段 → `workitem update`（同状态流）
- **节点字段（node_field）→ 必须 `workflow update-node --node-id <node_key> --fields '[...]'`**，且**一次只写一个字段**——多字段同写只落第一个、其余**静默丢弃**；每个字段写后 `get-node` 回读确认再写下一个
- **硬拦截类型直接中断转人工**：实际工时/投票类（vote-*）/复合明细表（compound_field）不支持 API 填写

**多节点顺序流转**：逐个节点"补必填→confirm→汇报"，不并行；节点流转后同样重查。

## 常见坑速查

| 坑 | 症状 | 解法 |
|----|------|------|
| list-state-required 带 mode 只回部分项 | 只报 8 项，流转仍报必填 | 不带 `--mode` 查全 |
| transition_id 过期 | Illegal Operation | 重新 list-state-transitions |
| 复核看不到字段 | get 返回里没有 resolve_version | 显式带 `--fields`（默认不含自定义字段） |
| MQL 缺项目限定/标识符 | ErrMoqlSemanticError | `FROM \`n58\`.\`表名\`` 全反引号 |
| field_value 格式错 | need STRING type | 数组/对象先 JSON.stringify |
| 枚举传 label | 值不合法 | 传 option_id 纯字符串 |
| 人员同名多人 | — | 展示列表让用户选 |
| update-node 多字段同写 | 只落第一个、其余静默丢 | 一次一个字段，写后回读 |
| --node-ids 传节点名 | 节点无效 | 只传 node_key（get-node 解析） |
| get-node 输出解析失败 | JSONDecodeError | 宽松解析，抽 name/node_key/status |
| 写终态/冻结版本关联 | ErrEditFieldNoPermission / 选项值已失效 | 转页面操作或找管理员，别重试 |
| update 写关联数组 | 报 data structure wrong | 字段值是"字符串包 int64 数组"`"[id1,id2]"` |

---

## 实测案例：版本下 5 条缺陷批量走单（2026-10-15）

场景：版本 **N306-E08-STD-BZ_EA_SX-002**（版本工作项 7103556120）下挂的缺陷要全部走到回归。

**1）查版本下挂的单**（版本侧 `field_bb75b4` 测试关联缺陷）→ 5 条缺陷 + 1 条 ITR。

**2）批量取状态**（`meegle workitem "+batch-get"`，子命令带 `+` 号在 Windows bash 下要加引号）→ 5 条缺陷全部 **Fixed**，即全部需要走 Fixed → Regression：

| 单号 | 标题（摘要） | 状态变化 | 回归版本 |
|---|---|---|---|
| 7058753448 | 【模块配置】双栈XIIC查询地址带 \r\n | Fixed → Regression | EA_SX-002 ✅ |
| 7061604660 | 【HTTPS】V6 服务器 HTTPS 连接失败 | Fixed → Regression | EA_SX-002 ✅ |
| 7062488651 | 【HTTPERR】CGATT=0 后报15，错误码取值 | Fixed → Regression | EA_SX-002 ✅ |
| 7063449110 | 【PSM】默认打开 PSM 取值是否合理 | Fixed → Regression | EA_SX-002 ✅ |
| 7060126311 | 【CPWD】AT+CPWD=? 上报范围与指令集不一致 | Fixed → Regression | EA_SX-002 ✅ |

**3）每条两步批量执行**：`resolve_version` 关联 N306-E08-STD-BZ_EA_SX-002（7103556120）→ `transition-state 33596784` 流转。**5 条一次过，无必填拦截**（Fixed→Regression 的 confirm_form 只有 字段填写检查+回归版本，前置已就绪），复核状态和回归版本均已落位。

**4）边界**：ITR 7057646515（NCONFIG 小区重选默认值）是节点流单，本流程不动；后续测试部在 EA_SX-002 上回归这 5 条 → 通过后关闭。

**可复用经验**：
- 同模板单子的 transition_id 一致（本例 Fixed→Regression = `33596784`），首条查到后批量套用，但**换状态后必须重查**
- Fixed→Regression 跳的表单只有两项，`resolve_version` 先挂好则流转零拦截——**先关联版本再流转**的顺序不能反
- 批量循环里逐条 `update → transition`，用 `"+batch-get"` 一次性复核全组状态（复核记得带 `--fields`）
