---
name: nwy-ec-fota-create-skill
author: mengxiangrui
description: 移芯 EC 系列模组 FOTA 差分包打包，支持 EC616/EC618/EC626/EC626E/EC716/EC718/QCX 全系平台（config 内置）。当用户要求"做 fota 包 / 打差分包 / 差分 / 生成升级包 / 回退包 / 004-005.par / 版本升级包 / delta 包"或提到 FotaToolkit / EC626 / binpkg / Eigencomm 打包等时使用。基于 FotaToolkit.exe CLI（工具已内置在 skill 的 tool/ 目录，自包含可迁移），一次产出正向升级包与反向回退包并自动校验。不涉及 GUI 操作、串口烧录和云端 FOTA。
---

# EC FOTA 双向差分包打包

## 工具背景

- **本 skill 自带完整工具副本**：`<skill目录>/tool/`（约 73MB，含 FotaToolkit.exe CLI 核心、dep 依赖、全芯片 config、GUI 与手册）。skill 目录整体拷走即可在其他机器使用，二进制不占用 agent 上下文。
- 工具目录探测链（脚本自动执行）：`--tool-dir` 参数 → 环境变量 `FOTATOOLKIT_DIR` → skill 自带 `tool/` → `G:\EC626\FotaToolkit_V3.6.4.0`
- 核心工具：`FotaToolkit.exe`（命令行核心，GUI `FotaToolKitGUI.exe` 只是壳，不要碰 GUI）
- 依赖：`dep\windows\deltagen.exe`（差分）、`fcelf.exe`（binpkg 解包）、`ecsecure.exe`（签名）——脚本会以 tool_dir 为工作目录自动调用，无需手动干预
- 差分命令：`FotaToolkit.exe -d <config> <memAttr> <out.par> <baseBin> <targetBin> [baseVer] [targetVer] [pem]`
- 校验命令：`FotaToolkit.exe -l <config> <par>`
- 回退包 = 把 base/target 互换再差分一次，同一个 `-d` 命令

## 工作流

1. **【强制第一步】skill 加载后立即通过 AskUserQuestion 收集并确认两个输入（旧版本包、新版本包），禁止跳过本步直接打包。**
   **通用原则：上下文可以"预填"候选项和默认值，但每一个输入都必须经用户确认后才能使用；上下文缺哪边就问哪边，已有的一侧以默认选项形式呈现供确认。**

   **【时序铁律】AskUserQuestion 必须是 skill 加载后的第一个动作，之前禁止执行任何文件搜索/ls/find 命令**：
   - "候选/预填"只能来自**对话上下文中已有的信息**（用户刚提到的路径、刚编译出的产物、之前查过的版本列表），绝不为了凑候选而现场扫描磁盘——新会话无上下文时更要直接问
   - 现场搜索（ls 版本流转服务器目录、找本机 bin 等）一律放在**用户选定"让我列出候选"类选项之后**再执行，搜完用第二轮 AskUserQuestion 呈现结果供选择
   - 典型反例（禁止）：用户说"给ec626做fota包" → agent 先 ls/find 扫了 3 轮磁盘 → 最后才弹问题。正确做法：加载完 skill 第一时间弹问题

   按场景处理：

   | 场景 | 处理方式 |
   |---|---|
   | A. 指令明确给出两个 bin 路径 | AskUserQuestion 把这两个路径作为默认选项让用户确认（确认即执行，用户可改选 Other 换路径） |
   | B. 上下文刚编译出新版本固件（如刚完成编译、产物路径已知） | 新包以"上下文已知"预填为默认选项；**旧版本包上下文通常没有，必须向用户索取**（候选项仅列上下文已有的路径；用户选"从共享/本机选取"时再去搜索） |
   | C. 用户提到版本流转服务器项目（如"千嘉"、"N306-CN-C2"） | 第一轮问题里提供"从该共享目录选取版本"选项；用户选中**之后**才 ls 该项目目录列出版本（QJ-001~006），第二轮问题供其选定，再从 `others\*-APP.rar` 用 7-Zip 解出 `app-demo-flash.bin` |
   | D. 裸关键词、新会话无上下文（最常见） | **加载完 skill 立即问**，不做任何搜索。两个问题开放收集：手动输入路径 / 从共享目录选取 / 从本机已知目录选取（用户选后者时才去搜索） |

   附加规则：
   - 两个输入必须同芯片同项目；config 按芯片型号取对应 json，不确定时在 AskUserQuestion 里一并问
   - 版本标签默认取 bin 文件名 stem，输出目录默认**工具目录（skill 自带 `tool/`）下的 `fota-create-output/`**——不单独追问，汇报时说明
   - **包名前缀（智能选取，规范如下）**：输出包名格式为 `<prefix>-<旧标签>-<新标签>.par`。prefix 按优先级选取：
     1. 用户明确指定 → 直接用
     2. 上下文有项目/客户/型号标识 → 从 bin 文件名 stem、共享目录名、用户提到的项目名中提取（如 `N306-E08-STD-BZ_CN_C2_BC28_QJ-005-APP.rar` → 提取 `QJ` 或 `N306-E08-QJ` 这类**短而有辨识度**的标识；不要整串照搬，也不要含版本号尾巴）
     3. 上下文无任何标识 → 兜底用 config 芯片名（脚本自动行为，如 `ec626-005-006.par`）
     裸标签 `005-006` 缺乏辨识度，混在多项目环境容易误用——prefix 必须存在，不允许产出无前缀包名
2. 执行打包脚本：脚本固定位于**本 skill 加载时给出的 base directory** 下的 `scripts/fota_pack.py`（下文模板与示例中统一写作 `<skill目录>`），不要硬编码绝对路径：

**命令模板**（尖括号 <> 为占位符，方括号 [] 为可选段，执行前替换成真实值）：

```
python "<skill目录>/scripts/fota_pack.py" \
  --base-bin "<旧版本bin的绝对路径>" \
  --target-bin "<新版本bin的绝对路径>" \
  [--base-ver <旧版本标签，如 005>] [--target-ver <新版本标签，如 006>] \
  [--prefix <项目/型号标识，如 QJ、N306-E08>] \
  [--direction both|forward|reverse] \
  [--attr APP|BINPKG] [--config <config json绝对路径>] [--out-dir <输出目录>]
```

**实际示例**（EC626，双向打包 005↔006，`<skill目录>` 替换为加载时给出的 base directory）：

```
python "<skill目录>/scripts/fota_pack.py" \
  --base-bin "G:\EC626\FotaToolkit_V3.6.4.0\005-app-flash.bin" \
  --target-bin "G:\EC626\FotaToolkit_V3.6.4.0\006-app-flash.bin" \
  --base-ver 005 --target-ver 006
```

3. 检查脚本输出：每个包生成后有 `[OK]`/`[X]` 标记和 `-l` 校验详情；`-l` 输出会列出包内镜像数量、各镜像尺寸与加载地址。
4. 向用户汇报：生成的 par 文件路径、大小、校验结果；如有 `[!] 超过 deltaMemSize` 警告必须明确提醒。脚本输出的 `[i] 版本标签...按短标签处理` 属预期行为，汇报时按「参数速查」的【汇报口径】处理，不要当成问题提示。
5. **【固定结尾提醒】汇报最后必须附一句环境清理提醒**（措辞可自然化，意思不可省）：
   > "包文件用完（FOTA 升级成功或验证结束）后记得删除 `tool/fota-create-output/` 目录，保持工作环境干净。"
   par 包是可随时重新生成的产物（重跑 skill 即可），不是需要长期归档的资产；长期留着容易混入后续版本造成误烧录风险。

## 参数速查

| 参数 | 说明 |
|---|---|
| `--base-bin` / `--target-bin` | 必填，旧/新版本镜像文件 |
| `--direction` | both(默认)=升级包+回退包；forward=仅升级包；reverse=仅回退包 |
| `--attr` | 镜像属性，默认按扩展名推断：`.binpkg`→BINPKG，其他→APP（EC626 用 APP） |
| `--config` | 默认 `<tool_dir>/config/ec626.json`；其他芯片型号换对应 config，**支持的平台见下方「支持的芯片平台」** |
| `--prefix` | 输出包名前缀（项目/型号标识）。**选取规范见工作流第 1 步**：用户指定 > 上下文智能提取（如 `QJ`）> 兜底 config 芯片名（如 `ec626-005-006.par`） |
| `--out-dir` | 默认输出到**工具目录下的 `fota-create-output/`**（即 skill 自带 `tool/fota-create-output/`；产物集中存放、不污染用户工作目录）；显式传参时以参数为准 |
| `--pem` | 可选签名，默认非签名；使用时必须提供符合格式的两个版本号 |
| `--base-ver/--target-ver` | 可选版本号。符合 `Vmmm.nnn.ppp`（如 `V000.005.000`）时写入包头；否则按**短标签**处理、仅用于输出文件命名（如 `005` → `005-006.par`）。工具不校验版本号与镜像的一致性 |

> **【汇报口径】短标签命名（如 `ec626-005-006.par`）是本 skill 的预期行为，不是缺陷**。向用户汇报时禁止使用"不规范/不符合/有问题/建议重新打包"等表述；只有用户**主动要求包头记录版本号**时，才提示改传 `Vmmm.nnn.ppp` 格式（如 `V000.005.000`）。

## 支持的芯片平台

以 `tool/config/` 下的配置文件为准（工具支持的芯片与 config 一一对应），共 16 个：

| 芯片系列 | config 文件 | 备注 |
|---|---|---|
| **EC616 系列** | `ec616(s).json`、`ec616(s)_2gc.json` | Cat.1；_2gc 为双 GNSS 变体 |
| **EC618** | `ec618.json` | Cat.1 |
| **EC626 系列** | `ec626.json`、`ec626e.json` | Cat.4；**本 skill 默认平台** |
| **EC716 系列** | `ec716e.json`、`ec716s.json` | |
| **EC718 系列** | `ec718hm.json`、`ec718p.json`、`ec718pm.json`、`ec718s.json`、`ec718u.json`、`ec718um.json` | p/pm 为高配变体 |
| **QCX 系列** | `qcx212.json`、`qcx216.json`、`qcx217.json` | 高精度定位模组 |

使用规则：
- **config 必须与镜像芯片匹配**（错配可能产出错误包且不报错，详见「边界与排错」）；芯片型号不确定时在 AskUserQuestion 中向用户确认
- 新增平台 = 把对应 config json 拷入 `tool/config/`（如后续有新芯片）
- 各平台的 deltaMemSize、加载区等具体数值以对应 json 内容为准（查阅方式见「参考规范」）

## 参考规范（随 skill 自带）

| 资料 | 位置 | 何时查阅 |
|---|---|---|
| **使用指南文本版** | `references/FotaToolkit使用指南_V2.2.md` | 查 JSON 配置字段含义（deltaMemSize / bkupMemSize / avlbRamSize / hasPkgHlc 等）、镜像属性释义与支持表（BINPKG/AP/CP/APP/APP2/SYSH/BL2）、par 与 fpar 格式约定、安全启动（bootCombo/pemUri）配置、差分 pmeth 升级方式、FAQ 章节 |
| 使用指南原版 PDF | `tool/FotaToolkit使用指南_V2.2.pdf`（中）/ `tool/FotaToolkit_User_Guide_V2.2.pdf`（英） | 权威原件；文本版有疑问时核对（含截图） |
| CLI 完整用法 | 运行 `FotaToolkit.exe -h` | 查 -a/-d/-f/-m/-s/-l/-u/-e/-r 全部参数格式 |
| 版本变更记录 | `tool/README` | 确认工具版本差异、已修复问题 |
| 芯片配置文件 | `tool/config/*.json` | 取具体芯片的 deltaMemSize、加载区 addr/size、FotaCoreVer 等实际数值 |

> 注意：PDF 在 agent 环境里不易直接读取（需 pypdf 等库解析），**遇文档问题优先读 `references/` 下的文本版**；文本版由原 PDF 逐页提取，已去除页眉页脚。

## 边界与排错

- **config 必须与镜像芯片匹配**：用 ec626.json 配 ec718 的 bin（或反之）可能产出错误的包而不报错。打包前务必确认 `--config` 对应的芯片型号与输入镜像一致（不确定时向用户确认芯片型号）。
- **差分包尺寸上限**：ec626 配置 `deltaMemSize=258048`（约 252KB），超过时脚本会警告——设备端 FOTA 下载区放不下，需减小版本间差异或改用全镜像包（`-f`，本 skill 未封装，可手动执行）。
- **镜像尺寸溢出**：日志出现 `err! target image(N) size(..) overflowed! max(..)` 表示目标镜像超过配置的加载区 size（ec626 APP 区 1620000 字节），需要换镜像或调配置，脚本会把该行提取出来。
- **两个输入文件相同**：脚本预检（路径相同或内容 hash 一致）会直接提示"无需差分"并正常退出（exit 0），不产出文件，不算失败。
- **成功标志**：exit code 0 且 par 文件生成且无 FAIL 行；不要只看 exit code。
- **输出目录禁止放在 `tool_dir/tmp/` 下**：工具每次运行会清空并重建自己的 `tmp/`，放在那里的输出会在打包中途被删，导致最终写文件报 `open @mode(wb) err(2)`。脚本已内置保护：检测到会自动改用 `<tool_dir>/fota_out/`。
- 打包过程会写 `tool_dir/tmp/` 中间文件与 `tool_dir/fota.log`，属正常现象，勿清理工具目录（skill 自带副本同样适用）。
- **工具副本升级**：skill 的 `tool/` 是 G 盘工具目录的完整镜像。若 G 盘工具升级了，把新版重新拷入 `tool/` 覆盖即可；G 盘目录不存在时 skill 也能独立工作。
- binpkg 文件用 BINPKG 属性时，包内各镜像 addr/size 以 binpkg 自带控制信息为准，config 中相应字段不生效。

## 明确不做（超范围时提示用户）

- 串口烧录升级（GUI Upgrader / `-u` 命令）——当前 skill 不封装
- 全镜像包 `-f`、合并 `-m`、独立签名 `-s`、AT 指令转换 `-a`——可手动执行 CLI，命令格式见 `FotaToolkit.exe -h`
