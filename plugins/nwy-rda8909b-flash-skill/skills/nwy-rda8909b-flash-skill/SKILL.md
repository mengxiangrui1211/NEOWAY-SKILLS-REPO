---
name: nwy-rda8909b-flash-skill
description: 规范 RDA 8909B / Neoway N25 固件烧录流程。通过已安装的 aicom-RDA-8909B-flasher MCP 连接器驱动本地 fpupgrade.exe 时，强制"先询问端口与固件→写入配置→一键全自动闭环(auto_start+auto_exit)→监控至会话复位 idle"，防止模型随心所欲调用工具函数（如猜测端口、烧录中途误关窗口、自作聪明改点击逻辑、重复点火）。触发词：烧录、flash、升级（含烧录固件 / flash firmware / 升级 8909B / 烧写 .lod 等说法均命中）。
agent_created: true
---

# RDA 8909B 固件烧录流程规范

## Overview

本 skill 规范通过 `aicom-RDA-8909B-flasher` MCP 连接器驱动本地 `fpupgrade.exe` 烧录 RDA 8909B（Neoway N25 模组）固件的**唯一正确流程**。

历史测试证明：烧录纯靠大模型自由调用工具容易出现"随心所欲"——不询问就用默认端口/固件、烧录没跑完就关窗、重复点火、或对自动点击逻辑自作聪明加重试导致更糟。本 skill 把 2026-08-10 多次实测验证过的「一键全自动闭环」路径与硬约束固化下来，模型每次都必须**按步骤问、按闭环走、按 idle 收尾**。

前置条件（调用前确认，不属于本 skill 步骤）：
- MCP 服务已集成在 AICom 中（streamable-http :9870），MCP 客户端（Claude Code / WorkBuddy / Trae / Codex / Z Code 等）已连接 `aicom-RDA-8909B-flasher` 连接器。
- 硬件已上电、USB/串口线已接好，本地能识别到 COM 口。
- 本地已安装 `pywinauto`（自动点击"开始"按钮依赖它）。

⚠️ **硬性前置自检（必做，放 Step 1 之前）**：本 skill **自身不含任何烧录逻辑**，所有操作都靠 `aicom-RDA-8909B-flasher` 这组 MCP 工具（列端口 / 写配置 / 点火 / 监控）。**如果当前会话里根本没有任何 `aicom-RDA-8909B-flasher` 工具**（名称通常形如 `mcp__aicom-RDA-8909B-flasher__*` 或客户端面板里展示的 aicom-RDA-8909B-flasher 工具），说明 MCP 没注册上——**不要**停在半路报 "tool not found"，而是**先调用 `nwy-rda8909b-mcp-setup` skill**（或按该 skill 的步骤）自动注册：它会检测当前客户端、拿硬件机 IP、用原生方式写入 MCP 配置、并复用 `:9870/health` 确认 server 在跑。注册成功、工具出现后再回来继续本流程。若自动注册仍失败，再退化为把对应客户端的配置片段发给用户手动粘贴（见 nwy-rda8909b-mcp-setup 的兜底小节）。

## 项目级配置（`config.yaml`，与本文件同级）

- 本 skill 服务的 RDA 8909B 烧录场景中，"远程项目编译产物在哪"是**静态信息**（项目目录放哪、构建产物叫什么），不需要每次都让 agent 重新发现。
- 同目录的 `config.yaml` 中 `remote.build_dir` **默认留空**——agent 日常自动在远程机器 Glob 搜索最新 `.lod`，**不写死任何盘符**，开箱即用。
- 如需固定某目录，再把 `build_dir` 填成本机编译产物绝对路径（换机器/换盘符只改这一行）。用户在对话里临时给的路径仍可**临时覆盖**（最高优先级）。
- 字段语义详见 `config.yaml` 文件内注释。
- 配完之后，Step 3 分支 B 的"路径发现"绝大部分场景会**自动搜到候选 → 用户拍板 → push**，无需手动填路径。

## 强制标准流程（必须严格按顺序）

### Step 1 — 连通性预检 + 就绪检查（必做，且**先于任何 AskUserQuestion**——MCP 已注册就别再问用户要 IP）

> ⚠️ **关键约束（2026-08-24 Claude Code 实战坑）**：agent 在截图里跨过 Step 1 直接问用户"请输入本地烧录机器 IP"——但 MCP 本来就已注册（连 aicom-RDA-8909B-flasher 工具都用上了），IP 完全可以从 MCP 配置反解出来。**这等于把能自动解析出来的信息推给用户手填，浪费一次往返**。
>
> **HARD GATE**：从 Step 1.1（拿 IP）到 Step 1.2（curl 探活）这一步没跑完、且 `:9870/health` 没返 `ok:true` 之前，**不准发起任何 `AskUserQuestion`**。

**1.1 确定本地机器 IP（4 级 fallback，命中即停）**

⚠️ **核心原则：MCP 已注册就别再问用户。** 哪怕下面 4 级全部失败，最后的 `AskUserQuestion` 也必须是「让用户在硬件机执行 ipconfig 自己看」（最差情况），而不是让 agent 凭空让用户瞎填一个 IP。

**优先级 A — `config.yaml` 的 `local.host_ip`**：直接读，若非空即用。

**优先级 B — 直接问客户端 CLI（最权威，无歧义）**：
```bash
command -v claude >/dev/null 2>&1 && claude mcp list 2>/dev/null | grep -E 'aicom-RDA-8909B-flasher'
command -v codex  >/dev/null 2>&1 && codex  mcp list 2>/dev/null | grep -E 'aicom-RDA-8909B-flasher'
command -v zcode  >/dev/null 2>&1 && zcode  mcp list 2>/dev/null | grep -E 'aicom-RDA-8909B-flasher'
```
命中类似 `aicom-RDA-8909B-flasher: http://192.168.60.91:9870/mcp/RDA-8909B-flasher (HTTP)` → 正则取 `192.168.60.91` 即可（端口固定 9870）。

**优先级 C — 解析客户端配置文件**（B 没拿到或 CLI 不可用时）：
| 客户端 | 路径（按顺序：项目级 → 用户级 → 其它） |
|---|---|
| Claude Code | `<cwd>/.mcp.json` → `~/.claude.json` → `~/.config/claude/mcp.json` |
| WorkBuddy | `~/.workbuddy/mcp.json` |
| Codex | `~/.codex/config.toml` |
| Z Code | `~/.zcode/cli/config.json` → `.agents/mcp.json` |
| Cursor | `.cursor/mcp.json` → `~/.cursor/mcp.json` |
| VS Code | `.vscode/mcp.json` |

直接调 skill 同包脚本（一次性扫完所有路径，正则出 IP，含 TOML）：
```bash
python "<skill_dir>/scripts/find_mcp_ip.py"
# 输出形如: IP=192.168.66.126 (source=.mcp.json)
```

**优先级 D — 兜底**：用 Python `socket.gethostbyname` 反查 client 自己的 hostname 也算一种 introspection；都失败才用 `AskUserQuestion`——但**问题文案必须明确**：
- "请你在**烧录机器（跑 start_server.bat 那台）**开 cmd 跑 `ipconfig` 把 IPv4 贴回来"，并提供"在烧录机器上自动跑 ipconfig 取 IPv4"的可执行选项（让用户能点击让 agent 在硬件机执行命令，而不是让用户瞎编一个 IP）。
- ❌ **绝不允许**让用户「输入 `192.168.x.x` 占位符」（agent 明知不可靠还诱用户填，就是浪费往返）。

**1.2 探活（独立于 MCP 连接器，用 Bash `curl` 直连 server 的 `:9870/health`）**：
```bash
curl -s -m 3 http://<本地IP>:9870/health
```
这是 2026-08-20 实战沉淀的"安全机制 E 层"——MCP 连接器握手卡死时，curl 直连仍能告诉你"进程到底活没活、端口通不通"。按返回分类处置：

| 现象 | 判定 | 修复动作 |
|---|---|---|
| 返回 JSON `{"ok":true,...}` | server 活、端口通 | ✅ 进入 1.3 |
| `curl: (28) timeout` / `Connection timed out` | 要么**主机离线**（关机/断网/睡眠），要么**防火墙 DROP**（端口被墙） | 用 `ping -n 1 <本地IP>` 区分：能 ping 通但 `:9870` 仍超时 → **防火墙 DROP**，让用户以管理员重跑 `start_server.bat`（已内置 netsh 放行 8909/9870）；ping 也不通 → **主机离线**，让用户查电源/网线/唤醒。 |
| `curl: (7) Failed to connect` / `Connection refused` | 主机在线但**无监听** → server 进程崩溃/未启动 | 让用户以管理员重跑 `start_server.bat`（看门狗拉起）；反复崩看本地 `mcp_server.log` 末行。 |
| `curl` 命令不存在 | 远程机缺 curl | 改用 `powershell -c "Invoke-WebRequest -Uri http://<本地IP>:9870/health -TimeoutSec 3"`。 |

⚠️ 若 MCP 连接器面板已报 `streamableHttp connect failed ... handshake hung`（正是 2026-08-20 那次），**不要先怀疑 server.py 代码**——99% 是上面三类运维问题；用 1.2 的 curl 分类快速定位，把具体修复命令给用户。

**1.3 就绪检查（MCP 工具）**：确认连接器恢复后，调 `get_flash_tool_info()` 与 `check_flash_status()`。
- 若 `check_flash_status` 显示 fpupgrade 仍在运行（上一轮未复位）→ **不要**直接 `start_flash`，先确认上一轮已 idle（见 Step 7），或用户明确要强制停止再继续。
- 确认当前已配置的 `lodFname` / `portName`，作为后续询问的基线。

### Step 2 — 询问端口 + 固件来源（硬约束：必须问，不能猜，且必须显式区分来源 A/B）
1. 调用 `list_com_ports()` 列出系统**真实存在**的 COM 口及设备描述。
2. **一次 `AskUserQuestion` 同时问两项**（关键：用结构化提问强制分支，避免漏掉"push 远程"这一步）：
   - **Q1 烧录端口**：把 `list_com_ports()` 返回的端口作为选项（如 COM3 / COM4 / COM1），**必须等用户选择**具体端口后才能继续。
   - **Q2 固件来源**：二选一
     - **本地已有（来源 A）**：固件已在本机 `8909b-flash-files/`，后续走 `list_lod_files` 浏览选择。
     - **远程刚编译需 push（来源 B）**：固件在远程机器，需先用 Bash `curl` 推到本地 `:9870` 再选。
   ⚠️ **严禁跳过 Q2 默认走来源 A**（历史教训：2026-08-19 模型曾漏掉 push 直接选本地旧文件，被用户叫停）。
3. ⚠️ 严禁用猜测的端口（如 COM5）或"上次用的"直接 `set_com_port` / `start_flash`。端口插错线 server 无法拦截，必须用户确认。来源选择决定 Step 3 走哪条分支。

### Step 3 — 按来源分支确认固件（硬约束：必须问，不能默许）

**分支 A — 本地已有（来源 A，不需要 push）**：
1. 调用 `list_lod_files()` 浏览 `8909b-flash-files/` 下的 `.lod` 文件（含大小/修改时间）；如需限定子目录，调用 `list_lod_files(hex_subdir="<子目录名>")` 收窄范围。
2. 把可用固件呈现给用户，**必须等用户选择**具体 `.lod` 文件后才能继续。
3. ⚠️ 严禁不经确认就用配置里已有的或"最新的"固件直接 `start_flash`。

**分支 B — 远程刚编译（来源 B，需 push 到本地）**：
1. **按四层优先级确定远程固件路径**（高 → 低）：
   - **#1（最高）用户本次对话里临时给的绝对路径**：你直接说"烧 `D:\xxx\yyy.lod`" → 直接用，**仍然按 #1 走完用户拍板 → push 流程**。
   - **#2 `config.yaml` 中 `remote.lod_name` 显式指定**：agent 读同目录 `config.yaml`，若 `remote.lod_name` 非空 → 用 `remote.build_dir / remote.lod_name` 拼接为绝对路径。
   - **#3 `config.yaml` 中 `remote.build_dir` 非空时 + `remote.lod_glob` 自动取最新**：agent 用 `Glob(remote.build_dir + remote.lod_glob)` 找最新的 `.lod`。
   - **#4 `remote.build_dir` 为空（默认推荐）→ agent 自动在远程机器 Glob 最新 `.lod`**：不依赖任何写死盘符，换机器/换盘符自动适配；多候选仍必须由用户拍板选哪个。
   - ⚠️ 多候选时**必须由用户拍板选哪个**，模型不得替挑；auto_set 之前始终保留这一拍板环节（防止 config 写错直接 push 错文件）。
2. **这条 curl 跑在「远程编译机（= 运行 MCP 客户端 / agent 这台）」，推送到「本地烧录机（= 运行 server.py 的 `:9870` 端点）」**——两端在跨机器架构下不是同一台。`<本地IP>` 即 Step 1.1 确定的烧录机 IP；`<远程绝对路径>` 是编译机本地路径（你 Glob 搜到的那个）。若本地机兼作烧录机，则用 `127.0.0.1` 也成立。auto_set 自动写 lodFname；文件走数据面 `:9870`，**绝不进 LLM 上下文**：
   ```bash
   # 把编译产物推到本地烧录目录
   curl -F "file=@<上一步确定的远程绝对路径>/xxx.lod" "http://<本地IP>:9870/upload?auto_set=true"
   # 返回 {"ok": true, "path": "G:\\...\\8909b-flash-files\\xxx.lod", "auto_set": true}
   ```
   ⚠️ **严禁把 `.lod` 文件内容当 MCP 工具参数传递**（base64 后 14.5MB 会撑爆上下文）；curl 走 HTTP body，上下文只剩命令 + 短 JSON。
3. push 成功后**仍需调用 `list_lod_files()` 把刚推入的文件呈现给用户确认**（auto_set 已写 lodFname，但**仍必须让用户明确选该文件，不得跳过确认环节**），等用户选该 `.lod` 后才继续。

### Step 4 — 写入配置（set）
- 写端口：`set_com_port(port_name="<用户选的COM>")`（改 `checkseat.ini` 的 `portName`）。
- 写固件：`set_lod_path(config_name="upgrade", lod_path="<用户选的.lod完整路径>")`（自动备份原配置为 `.bak`，路径内部转双反斜杠供 GUI 识别）。
- 两项都需返回"已更新"才继续。

### Step 5 — 校验（read）
调用 `read_config(config_name="upgrade")` 与 `get_flash_tool_info()`，核对 `lodFname` / `portName` 已变成用户所选值。**只有校验一致才进入 Step 6**。

### Step 6 — 启动 + 一键全自动闭环（核心配方）
调用：
```
start_flash(tool="upgrade", auto_start=True, auto_exit=True)
```
- `auto_start=True`：server 自动坐标点击"开始"按钮点火。
- `auto_exit=True`：server 后台线程在烧录完成（日志 `Close port` / 失败）后自动 `WM_CLOSE` 关窗并处理"确认退出？"框，关窗后**会话自动复位 idle**，无需模型再干预。
- 这是 2026-08-10 16:56 实测全通的配方，不要拆成"手动点开始 + 手动关窗"。
- 启动后 `start_flash` 会返回进程 PID，记下来备用。

### Step 7 — 监控直到 idle（收尾）
- **按固件实际大小/耗时动态设轮询间隔**（关键，避免"本地早烧完、远程晚 1 分钟才发现"的睡过头问题）。实测各固件烧录耗时差异极大，**间隔必须跟着实际耗时走，不是跟着"小/大"粗略分**；Step 3 选定固件后已拿到文件大小/文件名，据此归类：
  - **APP 层小镜像**（≤ ~1 MB，如 `N25-...APP-19.lod`、`N25-EU-NIC...flash.lod`(492KB)）：实测 ~2~10 s 烧完 → **每 1 s** 调用 `get_flash_progress()`，贴着进度，烧完即刻发现。
  - **主 flash 中等镜像**（~10~14 MB，如 `8909b_dualmode..._flash.lod`(13.4MB)、`merge...`(13.6MB)）：实测几十秒级 → **每 5 s**。
  - **完整底版本大镜像**（≥ ~14 MB，如 `N25-R04-...NIC-19.lod`(14.5MB)、`full_..._flash.lod`(15.2MB)）：实测约 **1 分 20 秒（~80 s）** → **每 10 s**，10 s 的完成发现延迟在 80 s 长烧录里完全可接受，且相比 5 s 少一半工具调用，不过载也不漏关键态。
  - 间隔在 Step 3 选定固件后即可确定；**循环轮询**直到 idle，**不要**用固定长 `sleep`（如 75s）整段干等——那会让发现延迟达到分钟级。
- **收尾加速（tail-burst）**：一旦某次轮询显示 `stage` 进入 `Verify`，或 `percent_est ≥ 95%`（临近完成），立即把间隔切到 **1 s** 冲刺最后阶段——这样 10 s 间隔的长镜像也不会在"Verify→Close→Done"这最后几秒白白多等一个完整 10 s 周期（兼顾"少调用"与"完成即发现"）。
- 观察 `stage` 从 `Open→Download→Program→Verify→Close→Done`，`done=True`。
- ⚠️ **进行中 `stage` 可能为 `None`**：`get_flash_progress` 有已知展示 bug（`log_file:None` 时 `stage`/`percent_est` 偶发为空），**不要**因为看到 `stage=None / 0%` 就以为"没在烧"。本轮真实阶段请用 `get_recent_logs(count=1)` 的末行日志交叉验证（如 `Program` / `Verify` / `Close port`）。
- **判定一轮完成的标准**：`get_flash_progress` 显示 `idle`（"空闲 — 等待远程'烧录'指令"）且 `running=False`。此时本轮会话已复位，可安全接受下一次烧录指令，无需重启 server。
  ⚠️ **idle 语义歧义（关键，2026-08-20 Claude Code 实战坑）**：`idle` 既能表示"本轮还没开始"也能表示"上一轮已结束"，而 `get_flash_progress` 在 idle 时**固定返回 `done=False / success=None(未知)`**——光看结构化字段无法区分这两种状态。**判定"上一轮成功结束"必须看文本字段**：`get_recent_logs` 末行出现 `Close port` + `_end_flash_session ... last_flash_result=成功`，或 `get_flash_progress` 返回的末行日志含"上次结果: 成功"。**不要仅凭 `done=False` 就以为"还没烧完"而盲目反复轮询**——这是不够聪明的 agent 最容易踩的坑。
- 不要毫秒级狂刷（1s 已是 APP 场景上限）；也不要用 75s 级粗 sleep 整段等待。
- ⚠️ `auto_exit=True` 时**不要**再手动调 `auto_exit()`（后台线程已负责，重复调用会干扰）。

## 工具速查（真实签名，勿臆造参数）

| 工具 | 签名 | 用途 / 何时用 |
|---|---|---|
| `get_flash_tool_info` | `()` | 环境全貌：工具目录、当前 `lodFname` / `portName` / `useCom` |
| `list_com_ports` | `()` | 列出系统真实 COM 口+设备描述（Step 2 必用） |
| `list_lod_files` | `(hex_subdir="")` | 列出 `.lod` 固件；留空列子目录，传子目录名列该目录文件 |
| `read_config` | `(config_name="upgrade")` | 读配置原文，校验写入结果（Step 5） |
| `set_com_port` | `(port_name)` | 设串口（改 `checkseat.ini`） |
| `set_lod_path` | `(config_name, lod_path, sdk_path="", use_com=True, use_usb=False)` | 设固件路径（自动 `.bak` 备份） |
| `start_flash` | `(tool="upgrade", auto_start=True, start_btn_pos=None, auto_exit=False)` | 启动烧录；启动前校验端口真实存在+固件存在；推荐 workflow 在 docstring |
| `auto_exit` | `()` | 手动关窗（仅 `auto_exit=False` 时、且 `done=True` 后用；闭环模式勿调） |
| `preview_start_click` | `()` | 预览"开始"按钮落点坐标（需先 `start_flash`、已装 pywinauto） |
| `_auto_click_start` | `(pid, timeout=25, rel_pos=None)` | **手动补点**"开始"按钮（自动点击点空时用） |
| `get_flash_progress` | `()` | 结构化进度：`running/done/success/stage/percent_est/idle` + 末 15 行日志 |
| `check_flash_status` | `()` | 进程是否仍在运行 |
| `stop_flash` | `()` | **强制停止**进程并复位会话（仅用户明确要求中止时） |
| `debug_flash_gui` | `()` | 打印控件树（定位按钮标识用，调试时） |
| `get_recent_logs` | `(count=5)` | 最近日志文件末 30 行 |

## HARD RULES — 禁止"随心所欲"

**DO（必须遵守）**
1. 烧录前**必须**先用一次 `AskUserQuestion` 同时确认**端口（来自 `list_com_ports`）**与**固件来源（来源 A 本地 / 来源 B 远程需 push）**；再按来源分支展示固件选项，**等待用户明确选择**端口与固件后才 `set_*` 写入。严禁跳过来源询问默认走 A。
2. 一律用 `start_flash(auto_start=True, auto_exit=True)` 一键全自动闭环。
3. 一轮是否完成以 `get_flash_progress` 回到 `idle` 为准。
4. 自动点击点空时，用 `preview_start_click` 核对 + `_auto_click_start(pid)` 手动补点（这是 2026-08-10 14:10 验证可靠的补点路径）。
5. **Step 1（IP 解析 + /health 探活）必须先于任何 AskUserQuestion 完成**：哪怕用户只说一句"烧录"，也要先把 MCP 已注册信息里的 IP 反解出来，curl `:9870/health` 确认 server 活。先问 IP / 先问端口 / 先问"哪个固件"——任何 AskUserQuestion 出现在 Step 1.2 `{"ok":true,...}` 返回前都算违规（2026-08-24 截图事故：跨过 1.1 直接在分支 B 问 IP，等于把能自动解析的信息推给用户手填）。

**DON'T（严禁）**
1. ❌ 不询问就用猜测/默认端口（如 COM5）或默认固件直接 `start_flash`。
2. ❌ 在烧录进行中（`done=False`）调用 `auto_exit()` 或 `stop_flash()` —— 除非用户明确要求中止。
3. ❌ `auto_exit=True` 时重复调 `auto_exit()`（后台线程已负责，重复会干扰闭环）。
4. ❌ 对 `auto_start` 点击逻辑"自作聪明"加重试/改坐标/加时序 hack。窗口位移+点偏已多次实测：一次性 pywinauto 点击 `START_BTN_REL=(0.90,0.15)` 是验证可靠的；若首次落空，走手动补点（规则 DO#4），**不要改 server 自动重试逻辑**。
5. ❌ 一轮未 idle（旧窗口未关）就再次 `start_flash`（server 有进程守卫会拒绝，且易串烧）。
6. ❌ 凭 GUI 截图或用户转述猜想就改 `server.py`——必须先抓真实日志/控件树（用户铁律）。
7. ❌ **严禁用 Bash `curl` 模拟 MCP 协议去调 `start_flash` / `get_flash_progress` / `set_*` / `list_*` 等工具**——这些必须直接用 `mcp__aicom-RDA-8909B-flasher__*`（或客户端面板里的 aicom-RDA-8909B-flasher 工具）**工具名调用**。本文档里的 curl **只允许出现在两处**：① Step 1.2 的 `:9870/health` 探活；② Step 3 分支 B 的 `:9870/upload` 推固件。其余任何烧录操作若走 curl 就等于"手写 MCP HTTP 协议"，会被 MCP 客户端拒绝或绕过工具调用体系——这是 2026-08-20 Claude Code 实战事故的根因（它看到来源 B 的 push curl，误以为"调服务 = curl"，连点火/查进度都用 Bash 走了一遍 MCP 协议，结果脚本被拒、进度无反馈）。

## 已知坑（已实测，勿凭猜改 server）

- **Qt 自绘 GUI**：`fpupgrade.exe` 是 Qt 自绘，"开始"按钮无 `title`/`automation_id`，UIA 首次枚举控件树极慢（~26s/次）。只能屏幕坐标点击 `START_BTN_REL=(0.90,0.15)`。
- **主窗口关闭**：标题栏 X 是 non-client 按钮，模拟点击常"点了等于没点" → server 用 `win32gui.PostMessage(WM_CLOSE)`，亚秒级可靠。
- **"确认退出？"框**：其"是"按钮无原生 HWND，必须对话框相对坐标 `(0.28,0.78)` 真实鼠标点击（左侧"是"）；用 `0.717` 会点到右侧"否"关不掉。
- **点"是"被吞（时序）**：Qt 模态框刚弹出按钮未就绪，找到框后需等 ~0.5s 再点；server 已做自愈（等 0.5s + 框在则再点，最多 3 次）。**不要在外层再加时序 hack。**
- **"关闭失败"误报（已修）**：旧逻辑等窗仅 3s / 重试把"已退出"当失败 / 未复位会话。已修为等 20s + 进程不在即判成功 + `_end_flash_session()` 复位。MCP 侧以"进程退出 + idle 复位"为准；关窗序列细节看本地 `mcp_server.log`。
- **窗口位移**：fpupgrade 启动→点击之间窗口可能被系统重定位，导致一次性点击落空（x 偏移可达 ~875px）。命中则正常；落空走手动补点。
- **`get_flash_progress` 展示瑕疵**：`progress_poller` 偶报 `log_file:None`，不影响 `auto_exit`（自动关窗线程自带两目录扫盘判定）。属已知展示层问题，不阻塞成败。

## 异常处理

- **自动点击点空（GUI 干等、无日志生成）**：
  1. 调 `_auto_click_start(pid=启动返回的PID)` 手动补点；若仍不开始，用 `preview_start_click()` 核对坐标，必要时 `start_flash(start_btn_pos=[fx, fy])` 微调比例。
  2. 不要自改 server 重试逻辑。
- **烧录失败**（日志含 `Error`/`Fail`，`success=False`）：向用户报告失败阶段与末行日志；如需重烧，确认 idle 后从 Step 2 重走。
- **需紧急中止**：仅在用户明确要求时调 `stop_flash()`，它会强制结束进程并复位会话到 idle。
- **server 连接中断 / MCP 面板报 `streamableHttp connect failed`**：
  1. **先判断是"没注册"还是"连不上"**：若当前会话里**压根没有** `aicom-RDA-8909B-flasher` 工具（从未注册过）→ 直接跑 `nwy-rda8909b-mcp-setup` skill 完成注册，不要走下面的重启流程。若工具**在列表里但连接失败**（handshake hung）→ 才是下面的运维问题。
  2. **先不要改 server.py**——这非代码 bug，是运维脆弱性（进程无自启 + 防火墙不持久）。根因见 2026-08-20 复盘。
  3. 按 **Step 1.2** 用 `curl http://<本地IP>:9870/health` 分类定位（主机离线 / 端口被墙 / 进程崩）。
  4. 对应修复（把命令直接给用户）：
     - **端口被墙 / 防火墙 DROP**：让用户**以管理员身份**重跑本地 `start_server.bat`（已内置 netsh 放行 8909/9870 且跨重启保留）；或临时手动 `netsh advfirewall firewall add rule name=RDA8909B-MCP-9870 dir=in action=allow protocol=TCP localport=9870`。
     - **进程崩 / 未启动**：让用户重跑 `start_server.bat`（看门狗崩溃自启）；反复崩看本地 `mcp_server.log` 末行。
     - **主机离线**：让用户查本地机器电源 / 网线 / 是否睡眠唤醒。
  5. 修复后连接器一般自动重连；若不自动，让用户在所用 MCP 客户端的连接器/设置页"断开→重连"（如 WorkBuddy 连接器页、Trae MCP 面板等）。

## 会话生命周期（连烧无需重启）

server 维护单例会话：`start_flash` 置 active → 烧录/轮询 → 关窗（自动或手动或强停）触发 `_end_flash_session()` 复位为 `idle`。idle 时静默等待下一次"烧录"指令。因此**连续多次烧录只需重复本流程，不必每烧一次重启 server**。判定一轮边界的唯一标准是 `get_flash_progress` 回到 `idle`。
