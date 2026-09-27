---
name: nwy-rda8909b-build-skill
description: RDA8909B 平台编译工具，支持底层固件和上层APP的交互式编译，自动处理菜单选择并弹出实时日志窗口。当前适配 N25-EU-BZ（标准项目）和 N25-EU-NIC 项目（底版本: neoway_build_N25_opencpu.bat / APP: neoway_build_N25_app.bat），其他项目可扩展，告诉 AI 编译脚本路径即可自动适配。用于用户要求"编译""构建""build"项目时。
developer: mengxiangrui (mengxiangrui@neoway.com)
---

# RDA8909B 平台编译 Skill

将编译脚本的交互式菜单选择自动化，通过 AskUserQuestion 获取用户选择，管道传入 bat 脚本完成编译，同时弹出 PowerShell 窗口实时显示编译日志,编译报错支持自行修复。

## 工作流

### Step 1: 询问编译项目

**读取配置文件** `config.yaml`（位于本 skill 目录下），获取项目列表，然后用 AskUserQuestion 让用户选择要编译的项目。

**展示规则**：
- 从 config.yaml 中读取每个项目的 `name`、`desc`
- 展示格式：`<name> (<desc>)`，不展示 menu_key（menu_key 是给脚本用的，用户不需要看到）
- 选项简洁明了
- **AskUserQuestion 最多支持 4 个选项**，项目超过 4 个时分组展示：
  - 第一轮：展示常用的 3 个项目 + "更多项目..." 选项
  - 第二轮：如果用户选"更多项目..."，展示剩余项目

AskUserQuestion 示例（项目 ≤ 4 个）：
```
问：编译哪个项目？
选项：
  N25-EU-NIC (EU open - 定制项目)
  N25_EU_BZ (EU open - 标准项目)
  N25-CN-OPEN (CN open - 标准项目)
  N25-India (印度电力定制)
```

AskUserQuestion 示例（项目 > 4 个，分组展示）：
```
第一轮：
问：编译哪个项目？
选项：
  N25-EU-NIC (EU open - 定制项目)
  N25_EU_BZ (EU open - 标准项目)
  N25-CN-OPEN (CN open - 标准项目)
  更多项目...

第二轮（用户选"更多项目..."时）：
问：选择哪个项目？
选项：
  N25-CN-STD (CN 标准版本)
  N25-EU-STD (EU 标准版本)
  N25-India (印度电力定制)
```

**新增项目**：只需在 config.yaml 中添加条目，AI 自动识别，无需修改 SKILL.md 或脚本。

### Step 2: 询问编译类型

确定项目后，使用 AskUserQuestion 让用户选择要编译的类型：

- **底层固件 (opencpu)**: 运行项目的 `opencpu` 脚本
- **上层业务APP**: 运行项目的 `app` 脚本
- **两个都编**: 先编底层，成功后再编APP

AskUserQuestion 示例：
```
问：要编译哪个？
选项：
  底层固件 (opencpu)
  上层业务APP
  两个都编
```

### Step 3: 执行编译

从 config.yaml 中获取选定项目的 `menu_key`、`opencpu` 脚本名、`app` 脚本名，然后执行编译。

**路径规则**：
- **不要使用硬编码绝对路径**，使用 `$PWD` 获取当前工作目录
- Claude Code 的工作目录已经是项目根目录，直接使用 `.` 或 `$PWD` 即可

**脚本约定**：日志监控脚本位于本 skill 目录下的 `scripts/watch_build_log.ps1`，Claude 执行时需先定位 SKILL.md 所在目录，再拼接 `scripts/watch_build_log.ps1` 获取完整路径。

**判断脚本是否有菜单**：
- 从 config.yaml 获取项目的 `menu_key` 字段
- 有 `menu_key`：用 `echo <menu_key> | cmd //c` 管道传入选择
- 无 `menu_key`：直接 `cmd //c` 运行脚本（无菜单交互）

**底层固件**:
```bash
# 有 menu_key 的情况
mkdir -p build && echo <menu_key> | cmd //c "$PWD\<opencpu脚本>" > build/build_opencpu.log 2>&1 &
# 无 menu_key 的情况（直接运行）
mkdir -p build && cmd //c "$PWD\<opencpu脚本>" > build/build_opencpu.log 2>&1 &
# 弹出日志窗口
SKILL_DIR="<SKILL.md所在目录的绝对路径>"
start powershell -ExecutionPolicy Bypass -File "$SKILL_DIR/scripts/watch_build_log.ps1" -LogPath "$PWD\build\build_opencpu.log"
```

**上层业务APP**:
```bash
# 有 menu_key 的情况
mkdir -p build && echo <menu_key> | cmd //c "$PWD\<app脚本>" > build/build_app.log 2>&1 &
# 无 menu_key 的情况（直接运行）
mkdir -p build && cmd //c "$PWD\<app脚本>" > build/build_app.log 2>&1 &
# 弹出日志窗口
SKILL_DIR="<SKILL.md所在目录的绝对路径>"
start powershell -ExecutionPolicy Bypass -File "$SKILL_DIR/scripts/watch_build_log.ps1" -LogPath "$PWD\build\build_app.log"
```

**两个都编**:
先执行底层固件编译（打开日志窗口），**等待底层编译成功后**再执行APP编译（打开第二个日志窗口）。

```bash
# 1. 编译底层固件（根据有无 menu_key 选择命令）
mkdir -p build && echo <menu_key> | cmd //c "$PWD\<opencpu脚本>" > build/build_opencpu.log 2>&1 &
SKILL_DIR="<SKILL.md所在目录的绝对路径>"
start powershell -ExecutionPolicy Bypass -File "$SKILL_DIR/scripts/watch_build_log.ps1" -LogPath "$PWD\build\build_opencpu.log"

# 2. 等待底层编译完成
while ! grep -q "build Success" build/build_opencpu.log 2>/dev/null; do sleep 5; done

# 3. 确认底层编译成功后，编译APP
grep -q "make.*Error" build/build_opencpu.log && echo "底层编译失败，跳过APP编译" && exit 1
mkdir -p build && echo <menu_key> | cmd //c "$PWD\<app脚本>" > build/build_app.log 2>&1 &
start powershell -ExecutionPolicy Bypass -File "$SKILL_DIR/scripts/watch_build_log.ps1" -LogPath "$PWD\build\build_app.log"
```

**说明**:
- 日志脚本位于 `.claude/skills/build-skill/scripts/watch_build_log.ps1`，通过 `-LogPath` 参数传入日志文件路径
- `> build/xxx.log 2>&1` — 将编译输出重定向到日志文件
- `&` — 后台运行编译进程
- `start powershell -ExecutionPolicy Bypass -File <脚本路径> -LogPath <日志路径>` — 弹出新 PowerShell 窗口执行日志脚本（`-ExecutionPolicy Bypass` 是必要的，因为 Windows 默认禁止脚本执行）
- **编译成功**: 日志窗口检测到 `build Success` 后等待 3 秒确认无后续 Error，显示提示，5 秒后自动关闭
- **编译失败**: 日志窗口**保持打开**，用户自行查看错误日志
- 日志窗口有 30 秒超时保护，路径错误时不会永久挂起

### Step 4: 结果判断

编译完成后读取日志文件判断结果：
- 日志中包含 `build Success` 且**不包含** `make.*Error` → 编译成功 → 跳到 Step 5
- 日志中包含 `make.*Error` 或 `build Fail` → 编译失败 → 执行 Step 4.1 失败分析
- **注意**：APP 编译脚本有 bug，编译失败时也会输出 "build Success"，所以必须同时检查 Error 关键字

### Step 4.1: 编译失败自动分析

当编译失败时，按以下流程自动分析和修复：

**4.1.1 提取错误日志**:
```bash
# 底层固件
tail -50 build/build_opencpu.log
# 上层APP
tail -50 build/build_app.log
```

**4.1.2 分析错误类型**，常见错误分类：

| 错误类型 | 关键字 | 分析方式 |
|---------|--------|---------|
| 语法错误 | `error: expected` / `error: stray` / `syntax error` | 定位到文件:行号，分析代码语法问题 |
| 未定义符号 | `undefined reference` / `undeclared` | 查找缺失的函数声明或头文件引用 |
| 头文件缺失 | `No such file or directory` | 检查 include 路径或文件是否存在 |
| 类型不匹配 | `incompatible type` / `implicit declaration` | 检查函数参数和返回值类型 |
| 链接错误 | `multiple definition` / `ld returned` | 检查重复定义或库缺失 |
| Makefile 错误 | `No rule to make target` / `Stop` | 检查 Makefile 依赖关系 |

**4.1.3 定位问题代码**:
- 从错误日志中提取文件路径和行号（格式如 `src/xxx.c:123`）
- 使用 Read 工具读取问题代码上下文
- 分析具体原因

**4.1.4 尝试自动修复**:
- 如果是简单错误（拼写错误、缺少分号、类型转换等）→ 直接修复，重新编译
- 如果是复杂错误（架构问题、缺失模块等）→ **不自动修复**，汇报错误摘要给用户，等用户确认后再处理
- 自动修复最多尝试 **2 次**，超过则停止，交给用户处理

**4.1.5 修复后重新编译**:
修复后自动触发编译（回到 Step 3），使用相同的编译参数

### Step 4.2: 失败分析结果分类

| 结果 | 处理方式 |
|------|---------|
| 自动修复成功 | 飞书通知：编译失败 → 已自动修复 → 重新编译成功 |
| 简单错误自动修复后仍失败 | 飞书通知：编译失败 → 错误摘要 → 需人工处理 |
| 复杂错误 | 飞书通知：编译失败 → 错误摘要 → 请用户确认后处理 |
| 超过2次重试 | 飞书通知：编译失败 → 多次修复未成功 → 请人工介入 |

### Step 5: 飞书通知

编译完成后，使用 `lark-cli` 以 **bot 身份**发送飞书通知（post 格式，开头加【公司端侧】标识）。

**发送命令**：
```bash
lark-cli im +messages-send --as bot --user-id "<open_id>" --msg-type post --content '<通知JSON>'
```

**注意**：必须使用 `--as bot`，不要用 user 身份，否则是自己给自己发消息，不像通知。

**通知模板（编译成功）**:
```
【公司端侧】编译成功通知
发送人: 孟相瑞 (mengxiangrui@neoway.com)
来源: Claude Code 自动化流程
时间: 2026-07-30
编译类型: 底层固件 (opencpu) / 上层业务APP
编译项目: N25-EU-NIC
状态: 编译成功
产物: full_8909b_dualmode_modem_N25_EU_NIC_opencpu_V3_release_flash.lod
```

**通知模板（编译失败 → 自动修复成功）**:
```
【公司端侧】编译自动修复通知
发送人: 孟相瑞 (mengxiangrui@neoway.com)
来源: Claude Code 自动化流程
时间: 2026-07-30
编译类型: 上层业务APP
编译项目: N25-EU-NIC
首次编译: 失败
错误位置: extapp.c:4674
错误原因: 'undefined_variable' undeclared（未定义变量）
自动修复: 删除错误行，重新编译
修复结果: 编译成功
产物: N25-EU-NIC_8909b_dualmode_modem_N25_EU_NIC_opencpu_V3_release_flash.lod
```

**通知模板（编译失败 → 需人工处理）**:
```
【公司端侧】编译失败通知
发送人: 孟相瑞 (mengxiangrui@neoway.com)
来源: Claude Code 自动化流程
时间: 2026-07-30
编译类型: 上层业务APP
编译项目: N25-EU-NIC
状态: 编译失败
错误位置: extapp.c:4674
错误原因: xxx（具体错误描述）
处理建议: xxx（需人工确认/多次修复未成功）
```

**必填字段**：发送人、来源、时间、编译类型、编译项目、产物/状态，缺一不可。

## 编译环境依赖

- 编译工具链: `C:\CSDTK4\CSDTKvars.bat`
- 构建工具: make (CSDTK 自带)
- 工作目录: 项目根目录（包含 `neoway_build_N25_opencpu.bat` 的目录）

## 编译项目配置

项目配置存储在 `config.yaml` 文件中，新增项目只需添加配置条目：

```yaml
projects:
  N25-EU-NIC:
    name: N25-EU-NIC
    desc: 定制项目
    opencpu: neoway_build_N25_opencpu.bat
    app: neoway_build_N25_app.bat
    menu_key: "1"
```

**字段说明**：
- `name`: 项目名称
- `desc`: 项目描述
- `opencpu`: 底版本编译脚本
- `app`: APP 编译脚本
- `menu_key`: 脚本菜单中的选择序号

## 注意事项

- 编译耗时较长（约3-10分钟），需要设置足够的 timeout（建议 600000ms）
- 底层固件和上层APP是分开编译的，APP编译依赖底层固件的产物（sdk_api_stub.o）
- 如果是全链路流程，应先编底层固件，再编APP
- cmd //c 执行 bat 文件时必须使用完整路径（通过 `$PWD` 拼接）
- Windows cmd 没有 `tail` 命令，使用 PowerShell 的 `Get-Content -Wait` 替代
- **所有路径使用 `$PWD` 动态获取**，确保项目在任意目录下都能正常编译
- 日志脚本预置在 `scripts/watch_build_log.ps1`，无需临时生成
