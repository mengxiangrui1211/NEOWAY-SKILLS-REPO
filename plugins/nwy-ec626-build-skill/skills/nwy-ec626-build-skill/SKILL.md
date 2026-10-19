---
name: nwy-ec626-build-skill
description: EC626 平台编译工具，支持固件、Bootloader、清理产物、Unilog 预解析的交互式编译，自动处理 build_nwy.bat 全部菜单项（数字选项目 / B / U / C / E）并弹出实时日志窗口，编译结束后自动终止 bat 进程树防止菜单死循环。项目列表每次运行时从当前分支 nwy_project/ 目录实时枚举，不维护任何静态项目清单（EC626 仓库多分支并存，写死的清单在别的分支必然失效），切换分支或新增项目目录后自动识别。用于用户要求"编译""构建""build" EC626/N306 项目时。
developer: mengxiangrui (mengxiangrui@neoway.com)
---

# EC626 平台编译 Skill

将 `build_nwy.bat` 的交互式菜单选择自动化：编译目标以**上下文推断**为主（工作流文件 → 静默侦察 → 问人三级链），确定后后台传入 bat 完成编译，同时弹出 PowerShell 窗口实时显示日志，编译报错支持自行修复。

## 与 RDA8909B skill 的差异（必读）

整体结构与 `nwy-rda8909b-build-skill` 一致（SKILL.md 工作流 + scripts/*.ps1 脚本）。仅以下几点因平台不同而不同：

| 维度 | RDA8909B | EC626（本 skill） |
|------|----------|----------------|
| 仓库分支 | 只有 master，项目集固定 | **多分支并存**（master / master_QIANJIA_* / EC_baseline / N306_EA_GCF_* 等），**各分支 nwy_project/ 项目集不同** |
| 项目清单 | 可用 config.yaml 写死 | **禁止静态清单**，运行时枚举 `nwy_project/` 目录（config.yaml 已于 2026-10-13 删除） |
| 入口脚本 | neoway_build_N25_*.bat | `PLAT/build_nwy.bat`（**循环菜单**，编完回菜单） |
| 工作目录 | 项目根目录 | **PLAT 目录**（含 build_nwy.bat 的目录，bat 以 %CD% 为 HOME_DIR） |
| 菜单 | 固定字母/数字键 | 动态数字索引（按 nwy_project 子目录字母序 0..n）+ B/U/C/E |
| 编译类型 | 底层固件 + 上层APP 分开编 | 单一固件镜像（业务已编进 app-demo-flash.bin），另有 Bootloader |
| 成功标记 | `build Success` | `build successfully` / 清理为 `clean all done ok` |
| 失败标记 | `make.*Error` / `build Fail` | `make.*Error` / `make.*\*\*\*` / `^fail` / `GCCLIB_PATH setting` |
| 工具链 | C:\CSDTK4 | 自带 `PLAT/tools/gcc` + `PLAT/tools/msys64` |

## 🚨 历史踩坑（2026-10-12 实测，设计依据，勿回退）

1. **build_nwy.bat 是循环菜单，且 `set /p` 在 EOF 时保持变量原值**：输入文件末尾的 `E` 一旦没被读到（长编译期间 stdin 偏移漂移），bat 会拿上一次的选择无限重编（实测 40+ 轮空增量）。因此：输入文件固定 **50 行 `E` 兜底**；`watch_build_log.ps1` 检测到编译结束（成功/失败/菜单回环/超时）后 **`taskkill /T /F` 强杀 bat 进程树**。不要改回"只传一行"或"编完不管"的写法。
2. **实测环境 Shell 是 PowerShell**（无 `printf`/`mkdir -p`/`env -u` 等 bash 命令），本文命令全部 PowerShell 语法。PowerShell 的 `>` 重定向默认 UTF-16，会损坏菜单输入文件——**必须用 `[System.IO.File]::WriteAllText` + ASCII 编码写输入文件**。
3. **临时文件放 `%TEMP%\ec626_skill_build\`，严禁写进 PLAT 工程树**（2026-10-13 用户反馈：编译后 PLAT 冒出 skill 产物不可接受）。旧规则"放 `PLAT\.skill_build\`"已废弃；成功后输入文件自动删除，日志保留在 TEMP 供排查。
4. cmd 启动 bat 必须满足：cwd = PLAT + 清除 `NoDefaultCurrentDirectoryInExePath` 环境变量（否则 bat 内部裸 `call GccBuild_ec626.bat` 报"不是内部或外部命令"）+ `cmd /c ""<bat完整路径>" < 输入 > 日志 2>&1"` 双引号形式。
5. **辅助 .ps1 文件编码坑（2026-10-12 实测，两次踩坑）**：PowerShell 5.1 把**无 BOM 的 UTF-8** .ps1 按 ANSI/CP936 解码，中文注释结尾的 `）` 等多字节字符（UTF-8 尾字节如 `0x89`）会被当作 GBK 前导字节**吞掉行尾换行，把下一行代码并进注释**。实测后果：`$wk` 未赋值（输入/日志文件写到盘根目录）+ `Remove-Item Env:\NoDefaultCurrentDirectoryInExePath` 整行被吞（GccBuild 报"不是内部或外部命令"）。因此：**辅助脚本必须纯 ASCII 编写（或存 UTF-8 with BOM）**；`Remove-Item Env:` 之后必须校验 `if ($env:NoDefaultCurrentDirectoryInExePath) { throw "env not cleared" }`；Step 3 命令块里的中文注释**不要连同代码存进无 BOM 的 .ps1**——直接在 PowerShell 控制台执行，或先把注释改成 ASCII。
6. **多步编译串进同一条后台命令 = 会话全程静默**（2026-10-13 用户反馈）：`build_once.ps1 -Mode bootloader; build_once.ps1 -Mode firmware` 这种写法两步之间没有任何会话输出，bootloader 日志窗一关固件窗直接弹出。必须一步一个后台任务，**收到通知先在会话汇报中间结论（"✅ Bootloader 编译成功…▶ 继续编译固件…"），再启动下一步**（对齐 nwy-rda8909b-build-skill 的节奏）。
7. **成功标记会被菜单回环刷出 tail 判定窗口**（2026-10-13 实测）：`build successfully` 之后 bat 回菜单、stdin 漂移又起一轮 logprepass，"Parsing file..." 刷屏把成功标记挤出 build_once.ps1 的 tail-300 窗口 → 误报 FAIL（artOk=True 却 FAIL 就是这个症状）。判定脚本已改为全日志匹配成功/失败标记；看门狗也改为**先杀进程树再复查尾部错误**，不给第二轮留窗口。
8. **PLAT 路径不要凭空拼**（2026-10-13 实测踩坑）：仓库实际结构是 `d:\ec626\EC626\PLAT`（build_nwy.bat 在这里），**没有** `d:\ec626\PLAT`。曾用 `Test-Path 'd:\ec626\PLAT\gccout\...\bootloader.bin'` 得到 False → 误报 BL 缺失、多弹一轮问题、白编一次 bootloader。任何针对 PLAT 的路径操作前，先定位真实 PLAT：`Get-ChildItem -Path <工作区> -Recurse -Filter build_nwy.bat` 取其所在目录，后续全部命令复用这个 `$PLAT`。
9. **禁止静态项目清单**（2026-10-13 用户反馈，config.yaml 已删除）：EC626 仓库**多分支并存**（`master` / `master_QIANJIA_*` / `EC_baseline` / `N306_EA_GCF_*` 等），各分支 `nwy_project/` 下的项目目录集合**互不相同**。任何写死的项目名单（config.yaml、README 里的索引表、脚本里的默认 `-Project`）都只是**某一个分支的快照**，拿到同事的分支上必然对不上：要么列出磁盘上没有的项目（选了直接编译失败），要么漏掉真正可编的项目。**唯一事实源是当前分支的 `PLAT\nwy_project\` 目录列表**——`build_nwy.bat` 的菜单本来就是按它实时生成的，skill 跟它对齐才不会漂移。同理，**分支名、项目系列名（CN C2 / EA / LA 之类）、项目中文描述都不要写进 skill**，它们同样会随分支失效。RDA8909B 仓库只有 master 一个分支、项目集固定，所以那边可以留 config.yaml；EC626 这边不可以。
10. **项目选择禁用弹窗分页**（2026-10-13 用户反馈：列举项目「扎堆」）：AskUserQuestion 每题最多 4 个选项，项目占 3 个 + 「更多项目...」翻页——18 个项目要翻 6 页，且前几页全是 `N306_CN_C2_*` 近名挤在一起；问题正文里 `A / B / C / …` 一行横排 18 个名字同样没法看。曾为此连续两次弹窗被用户点掉。因此：AskUserQuestion **不用于列项目**（只留给 ≤4 选项的操作多选与 BL 确认，且最多弹一次）；竖排清单仅作查询结果/最后兜底——选择主体是推断不是菜单（见踩坑 11）。
11. **会话里发编号菜单让用户点 = 本末倒置**（2026-10-13 用户二次反馈）：把项目清单塞进会话等回复「3 固件」，等于把 `build_nwy.bat` 菜单搬进更差的介质——用户直接点脚本反而快。选项目本不该是用户的事：编译目标可从上下文推断（工作流文件 / 飞书单「软件项目」/ 工作区改动 / 编译指纹），**agent 的价值在推断 + 编排 + 自动修复 + 通知，不在复刻菜单**。因此：推断优先（三级链见 Step 1），问人是最后手段且必须带依据给候选；「有哪些项目」类查询才输出清单。

## 工作流

> 🚨 **强制规则（2026-10-13 用户两次反馈后定稿：推断优先，菜单是兜底）**：
> 1. **确定编译项目以推断为主**——三级优先级：工作流文件 → 静默侦察 → 问人（见 Step 1）。禁止一触发就发编号菜单等用户点（踩坑 11）
> 2. **操作默认增量固件**——「编译」=增量固件；「全量/重编/清后编」=清理+固件；清理是破坏性动作**任何情况禁止默认执行**；BL/Unilog 用户没点名不执行
> 3. **AskUserQuestion 全流程最多一次**：Step 2（操作多选）+ Step 2.5（BL 确认）合并进同一次调用；弹之前先静默做 Step 2.5 的 bootloader.bin 检查，缺失才把 BL 问题加进去。多候选问项目用**一句话自然语言**，不弹窗
> 4. **禁止多轮连环追问**；但"看似明确"不算明确——项目名须与 `nwy_project/` 目录字面匹配，或由证据链（单号/改动/指纹）唯一推出；模糊指代（"EA 那个"）问一句，不猜
>
> **B/U/C/E 菜单不会原样弹出**——那四个键是 build_nwy.bat 的内部菜单，技能把它们映射为操作关键词/选项标签（带菜单字母便于对应），再由命令静默传入 bat。

### Step 1: 确定编译目标（三级优先级：缓存 → 回源 → 问人）

编译项目 = 某个 `nwy_project/` 目录名（唯一事实源见踩坑 9）。**能推断就不问**——一触发就发编号菜单让用户点，等于把 bat 菜单搬进会话（踩坑 11）。信息本身有活源头（工作流文件是缓存，不是信息源），冷启动 = 缓存未命中就回源查。

#### 一级 · 工作流上下文文件（缓存，有则先用）

约定路径 `docs/.nwy-build-context.json`，schema 最小集：

```json
{ "ticket_id": "...", "project": "...", "repo": "...", "branch": "...", "updated_at": "..." }
```

- `branch` 与当前分支**一致** → 直接采用 `project`，依据写「工作流上下文（单 <ticket_id>）」
- `branch` **不一致** → **降级为候选**，与二级侦察结果一起判定，不盲从（防切分支后拿旧信息编错项目）
- 文件不存在 → 静默跳过，进二级。写入方是需求分析/工作流（后补，skill 只读）；没有它回源照样能编

#### 二级 · 静默侦察（回源，全自动，不问人）

| 源 | 查法 | 证据强度 |
|---|---|---|
| **工作区指纹** | `git status` 看未提交改动落在哪个 `nwy_project/<X>/` 下 | **强**：正在改的代码 ≈ 要编的项目 |
| **编译指纹** | `%TEMP%\ec626_skill_build\*.log` 最近一份；`gccout/` 产物时间；PLAT 根 `nwy_project.mk`（bat 选项目时 xcopy 留下指纹） | 中：上次编的大概率继续编 |
| **Meegle 回源** | `meegle auth status` 已登录才查：我名下未关闭的缺陷/ITR 单 →「软件项目」字段（字段映射见 `nwy-meegle-version-tickets-skill`；缺陷侧该字段值与 `nwy_project/` 目录同名，已实测） | 中高：单是编译需求的源头 |

侦察**必须静默**，过程中不输出大段日志、不提问；把证据汇合后按三级表行动。

#### 三级 · 汇合判定（决定问不问）

| 证据汇合结果 | 行为 |
|---|---|
| **唯一**指向某项目 | **直接编**。会话声明一行 `▶ 编译项目：<名>（依据：<证据>）`，说「不对」可改 |
| 2-3 个候选 | **一句话自然语言问**（带依据给候选），如「编 N306_CN_C2_BC28_QJ（单 7062657421）还是 N306_EA_SX（上次编译）？」 |
| 全落空 | 问「编哪个？给**项目名或飞书单号**都行」；用户给单号 → meegle 查「软件项目」定位，**用户不用记项目名** |
| 用户明说"看下有哪些项目" | 输出**兜底清单**（格式见下），当查询结果用 |

**项目名匹配规则**：只有与某个 `nwy_project/` 目录名**字面精确一致**（大小写不敏感可接受，前缀猜配不行）才算明确；模糊指代（"EA 那个""上回那个"）按"全落空"问一句，不猜。

#### 操作判定（默认增量固件，不必问）

| 用户说法 | 操作 |
|---|---|
| 「编译」「构建」「build」 | **增量固件**（默认） |
| 「全量」「重编」「清后编」 | 清理产物 → 固件 |
| 关键词映射 | `固件`/`编译` → 固件；`B`/`Bootloader` → Bootloader；`C`/`清理` → 清理产物；`U`/`Unilog`/`预解析` → Unilog 预解析；组合用「+」并列（如「清理+固件」） |
| 组合不明 / 说法含糊 | 进 Step 2 弹窗（全流程唯一一次） |

非默认动作（清理/BL/Unilog）**用户没点名就不执行**；清理是破坏性动作，**任何情况禁止默认执行**。

#### 兜底清单格式（查询结果 / 最后手段，不是选择器）

**枚举命令**（`$PLAT` = build_nwy.bat 所在目录，见踩坑 8）：

```powershell
$projects = (Get-ChildItem "$PLAT\nwy_project" -Directory | Sort-Object Name).Name
$branch   = (git -C "<仓库根>" rev-parse --abbrev-ref HEAD).Trim()
```

- 一行一个项目，编号 `[1]..[N]` 仅用于回复点名，与 bat 菜单的 0 基索引无关（`build_once.ps1` 按项目名自算索引）
- 按运行时前缀归组：组名 = 目录名按 `_` 切分的**前两段**（不足两段单独成组）——现算的显示归类，**不是写死的系列名**，换分支自动变
- 目录名**原样展示**，不加人为描述（踩坑 9）；标题行标出分支名与总数

```
📦 EC626 可编译项目（分支: <当前分支>，共 <N> 个）

── <前缀组1>（<n1>）──
  [1] <项目名>
  ...
── <前缀组2>（<n2>）──
  [<k>] <项目名>
  ...

回复「编号或项目名 + 操作」，如：`3 固件`、`12 清理+固件`
```

**新增项目 / 切换分支**：**无需改任何文件**，`nwy_project/` 目录变即推断/清单跟着变。`build_once.ps1` 会二次校验目录真实存在，不存在直接报 `project not found` 而不是丢给 bat 编一堆 make 错误。

### Step 2: 操作确认（仅含糊时弹，全流程唯一一次）

操作判定主体在 Step 1（默认增量固件 + 关键词映射）。**只有组合不明/说法含糊时**才用 AskUserQuestion（**multiSelect: true**）弹**这一次**，可组合勾选：

- **固件（数字菜单选项目后编译）**: 编译完整固件镜像（含上层业务，产物 app-demo-flash.bin）
- **Bootloader（B）**: 仅编译 bootloader（产物 bootloader.bin）
- **清理产物（C）**: 清理全部旧编译产物（`GccBuild_ec626.bat clall`，成功标记 `clean all done ok`）
- **Unilog 预解析（U）**: 执行 LogPrePass 日志库预解析；注意预解析成功后会继续编默认 at_command 工程

**执行顺序规则**（与勾选/回复顺序无关）：**清理产物 → Bootloader → 固件**（Unilog 独立执行）。每步**独立启动、独立等待、独立汇报**（见 Step 3「多步骤组合」），上一步出结论并在会话中汇报后才启动下一步，前置失败则停止后续步骤。

常见组合：固件=日常增量；清理产物+固件=清后重编；固件+Bootloader=先BL后固件；三者全勾=全新全量构建（发版）。

### Step 2.5: 编译固件前确认 Bootloader（并进唯一那次弹窗）

固件与 Bootloader 是独立镜像、独立 flash 区域，但烧录一个可运行的模块必须两个都齐；`gccout/` 不入仓库，**新拉代码后 bootloader.bin 必然缺失**。**在任何提问之前**先静默检查（`<PLAT>` 必须是 build_nwy.bat 所在目录，见踩坑 8，不要凭空拼路径）：

```powershell
Test-Path "<PLAT>\gccout\ec626_0h00_ec626\bootloader\bootloader.bin"
```

- **缺失 + 计划编固件** → 必须问一次："bootloader.bin 缺失，新拉代码后建议先编 Bootloader"，推荐选项放第一位（先编 Bootloader 再编固件 / 只编固件 / 只编 Bootloader）。**Step 2 还要弹窗就并进同一次调用**；操作已由文字说清时单独弹这一个 question——两种情况都只弹一次
- **已存在** → 不问
- **缺失但用户没要固件**（只清理/只 BL/只 Unilog）→ 不问

### Step 3: 执行编译

**路径规则**：`$PLAT` = build_nwy.bat 所在 PLAT 目录绝对路径（**先搜索定位再用，禁止凭空拼**，见踩坑 8；本仓库实为 `d:\ec626\EC626\PLAT`）；`$SKILL_DIR` = 本 SKILL.md 所在目录；菜单索引由命令按 nwy_project 目录字母序动态计算（已实测与 bat 菜单 `[3]: N306_CN_C2_BC28_QJ` 一致），**不要写死**。

**统一入口 `scripts/build_once.ps1`**（内部完成：ASCII 输入文件 + 50 行 E 兜底 + 清环境变量 + 启动 bat + 弹日志窗口 + **等待编译结束** + 产物校验 + 输出结论行）。按 `-Mode` 区分操作，固件再传 `-Project`：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<SKILL_DIR>\scripts\build_once.ps1" -Mode firmware  -Project <项目名>
powershell -NoProfile -ExecutionPolicy Bypass -File "<SKILL_DIR>\scripts\build_once.ps1" -Mode bootloader
powershell -NoProfile -ExecutionPolicy Bypass -File "<SKILL_DIR>\scripts\build_once.ps1" -Mode clean
powershell -NoProfile -ExecutionPolicy Bypass -File "<SKILL_DIR>\scripts\build_once.ps1" -Mode unilog
```

**运行方式（关键，2026-10-13 用户反馈）**：必须用 **Bash 工具 `run_in_background: true`** 启动上面的命令。脚本会阻塞到编译结束并输出 `RESULT: SUCCESS|FAIL ...`，后台任务退出的瞬间会话即收到通知，**立刻**给用户结论。禁止"启动后长 sleep 轮询"再汇报——实测看门狗窗口早已 SUCCESS 关窗，会话还在 sleep 里等，用户只能追问"卡住了吗"。

**多步骤组合（关键，2026-10-13 用户反馈）**：勾选多项（如 Bootloader+固件）时，**禁止把多步串进同一条命令**（如 `build_once.ps1 -Mode bootloader; build_once.ps1 -Mode firmware ...`）——实测两步之间会话全程静默：bootloader 日志窗一关固件窗直接弹出，用户看不到任何中间结论。正确做法是**一步一个后台任务，收到通知先汇报、再启动下一步**：

1. 后台启动 `build_once.ps1 -Mode bootloader`，等任务通知
2. 会话输出中间结论，例如：
   `✅ Bootloader 编译成功，产物 gccout/ec626_0h00_ec626/bootloader/bootloader.bin`
   `▶ 继续编译固件（<项目名>）...`
3. 再后台启动 `build_once.ps1 -Mode firmware -Project <项目名>`

失败同理：先汇报 `❌ <步骤> 编译失败：<错误摘要>`，再停止后续步骤。中间结论是用户唯一能看到的进度，不能省。

**说明**:
- `build_once.ps1` 等到编译结束才退出，退出码 0=成功 1=失败，stdout 尾部有 `RESULT: SUCCESS|FAIL ...` 结论行（含产物校验，不会被循环菜单的横幅误判）；日志窗口实时显示编译输出
- **看门狗**（watch_build_log.ps1）：检测到 `build successfully` / `clean all done ok` / 失败标记 / 菜单回环（`Please select project` 第二次出现=某次编译已结束）/ 60 分钟超时 → `taskkill /T /F` 终止 bat 进程树 → 成功提示后 5 秒自动关窗，失败**保持窗口打开**
- 选中项目后 bat 会 `xcopy nwy_project\<项目名>\` 覆盖到 PLAT 根目录（nwy_project.mk、middleware 覆盖层），属正常行为
- 项目 mk 含 `BUILD_BP = y` 的（HNYT、EA 系列）会执行 `bp_init.bat` 从内网 git（192.168.68.210:8081）拉取 NWY_FRAMEWORK，需内网可达
- Bootloader（B）会先 `git checkout device/eigencomm/board/ec626_0h00/ec626_0h00.mk`，**丢弃该文件本地改动**，如有未提交修改需提醒用户
- EA_P203 / EA_P203_VDF / EA_T203_VDF / EA_T203_N02_VDF / LA_T203_N02_VDF 自动映射到 `nwy_emergency_light_*` 编译目标，bat 内部处理

### Step 4: 结果判断

编译结束后（`build_once.ps1` 后台任务退出）先看 `RESULT:` 结论行：`SUCCESS` 直接进 Step 5；`FAIL` 再读日志判断：

```powershell
Get-Content "<log路径>" -Tail 30 | Select-String -Pattern 'build successfully|clean all done ok|^fail|make.*(Error|\*\*\*)|GCCLIB_PATH'
```

| 编译类型 | 成功标记 | 失败标记 |
|---------|---------|---------|
| 固件 / Bootloader | `build successfully` | `make.*Error` / `make.*\*\*\*` / `^fail` |
| 清理产物 | `clean all done ok` | 同上 |
| Unilog 预解析 | `start logprepass` + `build successfully` | 同上 |

- 有成功标记且无失败标记 → 成功 → Step 5；有失败标记 → Step 4.1
- 成功时日志尾部还有 `Built took X hours Y minutes Z seconds` 和 BUILD SUCCESS 横幅可辅助确认

### Step 4.1: 编译失败自动分析

**4.1.1 提取错误日志**:
```powershell
Get-Content "$env:TEMP\ec626_skill_build\build_firmware.log" -Tail 50
Get-Content "<PLAT>\gccout\ec626_0h00_ec626\outbuildlog.txt" -Tail 50   # make 完整日志（bat 自带 tee）
```

**4.1.2 分析错误类型**：

| 错误类型 | 关键字 | 分析方式 |
|---------|--------|---------|
| 语法错误 | `error: expected` / `error: stray` / `syntax error` | 定位到文件:行号，分析代码语法问题 |
| 未定义符号 | `undefined reference` / `undeclared` | 查找缺失的函数声明或头文件引用 |
| 头文件缺失 | `No such file or directory` | 检查 include 路径或文件是否存在 |
| 类型不匹配 | `incompatible type` / `implicit declaration` | 检查函数参数和返回值类型 |
| 链接错误 | `multiple definition` / `ld returned` | 检查重复定义或库缺失 |
| Makefile 错误 | `No rule to make target` / `Stop` | 检查 Makefile 依赖关系 |
| 项目配置错误 | `nwy_project.mk` 相关 / FEATURE 宏冲突 | 检查项目 CFLAGS 宏定义与代码 `#ifdef` 匹配 |

**4.1.3 定位问题代码**: 从错误日志提取 `文件路径:行号`，用 Read 工具读取上下文分析。

**4.1.4 尝试自动修复**: 简单错误（拼写、缺分号、类型转换）直接修复重编；复杂错误汇报用户确认；最多自动尝试 **2 次**。

**4.1.5 修复后重新编译**: 回到 Step 3，用相同参数。

### Step 4.2: 失败分析结果分类

| 结果 | 处理方式 |
|------|---------|
| 自动修复成功 | 飞书通知：编译失败 → 已自动修复 → 重新编译成功 |
| 自动修复后仍失败 | 飞书通知：编译失败 → 错误摘要 → 需人工处理 |
| 复杂错误 | 飞书通知：编译失败 → 错误摘要 → 请用户确认后处理 |
| 超过2次重试 | 飞书通知：编译失败 → 多次修复未成功 → 请人工介入 |

### Step 5: 飞书通知

编译完成后，使用 `lark-cli` 以 **bot 身份**发送飞书通知（post 格式，开头加【公司端侧】标识）：

```bash
lark-cli im +messages-send --as bot --user-id "<open_id>" --msg-type post --content '<通知JSON>'
```

**通知模板（编译成功）**:
```
【公司端侧】编译成功通知
发送人: 孟相瑞 (mengxiangrui@neoway.com)
来源: Claude Code 自动化流程
时间: 2026-10-12
编译类型: 固件 / Bootloader
编译项目: N306_CN_C2_BC28_QJ
状态: 编译成功
产物: gccout/ec626_0h00_ec626/at_command/app-demo-flash.bin
```

**通知模板（编译失败 → 自动修复成功）**:
```
【公司端侧】编译自动修复通知
发送人: 孟相瑞 (mengxiangrui@neoway.com)
来源: Claude Code 自动化流程
时间: 2026-10-12
编译类型: 固件
编译项目: N306_CN_C2_BC28_QJ
首次编译: 失败
错误位置: nwy_tcpudpBC28_at.c:1068
错误原因: 'xxx' undeclared（未定义符号）
自动修复: xxx（修复方式）
修复结果: 编译成功
产物: gccout/ec626_0h00_ec626/at_command/app-demo-flash.bin
```

**通知模板（编译失败 → 需人工处理）**:
```
【公司端侧】编译失败通知
发送人: 孟相瑞 (mengxiangrui@neoway.com)
来源: Claude Code 自动化流程
时间: 2026-10-12
编译类型: 固件
编译项目: N306_CN_C2_BC28_QJ
状态: 编译失败
错误位置: nwy_tcpudpBC28_at.c:1068
错误原因: xxx（具体错误描述）
处理建议: xxx（需人工确认/多次修复未成功）
```

**必填字段**：发送人、来源、时间、编译类型、编译项目、产物/状态，缺一不可。

## 编译环境依赖

- 编译工具链: 自带 `PLAT/tools/gcc`（arm-none-eabi，GccBuild_ec626.bat 自动设置 GCCLIB_PATH）
- 构建工具: make + msys64（`PLAT/tools/msys64/usr/bin`，bat 自动加 PATH）
- 工作目录: PLAT 目录（包含 `build_nwy.bat`、`GccBuild_ec626.bat`、`nwy_project/`）
- 内网 git（仅 BUILD_BP 项目）: bp_init.bat 需访问 192.168.68.210:8081 拉取 NWY_FRAMEWORK

## 编译产物

| 编译类型 | 产物路径（相对 PLAT） |
|---------|----------------------|
| 固件 | `gccout/ec626_0h00_ec626/at_command/app-demo-flash.bin`（同目录 .hex/.elf/.map） |
| 固件（应急照明项目） | `gccout/ec626_0h00_ec626/nwy_emergency_light_*/` 下对应 bin |
| Bootloader | `gccout/ec626_0h00_ec626/bootloader/bootloader.bin` |
| make 日志 | `gccout/ec626_0h00_ec626/outbuildlog.txt` |

## 项目清单来源

**没有配置文件。** 项目清单的唯一事实源是 `PLAT\nwy_project\` 当前目录列表，由 `build_once.ps1` 与 Step 1 运行时枚举：

```powershell
(Get-ChildItem "$PLAT\nwy_project" -Directory | Sort-Object Name).Name
```

历史上有过 `config.yaml` 存项目名 + 中文描述，已于 2026-10-13 **删除**：EC626 仓库多分支并存、各分支项目集不同，静态清单在别的分支/同事机器上必然失效（见踩坑 9）。**不要再把它加回来。**

因此：新增项目、切换分支、同事换机器都**不需要改 skill 任何文件**。

## 注意事项

- **辅助 .ps1 必须纯 ASCII**（中文注释存进无 BOM UTF-8 会让 PS5.1 吞掉下一行，见踩坑 5）；启动后校验 `$env:NoDefaultCurrentDirectoryInExePath` 已清空
- 编译耗时：固件全量约 25 分钟、增量约 1 分钟、Bootloader 约 1-6 分钟；**会话侧结论以 `build_once.ps1` 退出为准（run_in_background 任务完成即通知）**，不要用长 sleep 轮询代替（看门狗窗口 SUCCESS 关窗后会话还在 sleep = 用户差评）
- **必须走 Step 3 的命令块**，禁止手工 `echo | cmd /c build_nwy.bat` 管道后台拼命令（会复现死循环）
- **菜单索引不要写死**，每次按 nwy_project 目录字母序动态计算
- PowerShell 的 `>` 默认 UTF-16，**禁止用它写菜单输入文件**
- Windows 无 `tail`，用 `Get-Content -Tail`；日志脚本预置在 `scripts/watch_build_log.ps1`，无需临时生成
