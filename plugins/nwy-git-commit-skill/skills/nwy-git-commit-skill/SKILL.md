---
name: nwy-git-commit-skill
description: 本公司 Git 代码提交入库流程（Gerrit）：git status 确认改动 → 展示拟 add 文件清单等用户确认 → git add → 按公司模板组织提交信息等用户确认 → git commit -F（绕开弹框）→ 用户确认后 git push origin HEAD:refs/for/<当前分支>。当用户说"提交""代码入库""入库""push""push gerrit""提交代码""推代码""推到 gerrit"，或明确授权提交时使用。编译副产物与本次功能无关的修改默认不 add。
developer: mengxiangrui (mengxiangrui@neoway.com)
---

# Git 代码提交入库 Skill（Gerrit）

将公司标准提交流程自动化：**两处强制确认**（add 清单、提交信息），commit 绕开弹框，push 必须用户点头后执行。

## 流程总览

```
Step 1  git status / diff --stat 展示改动
Step 2  分类：相关源码 vs 编译副产物 → 🚨展示拟 add 清单 → AskUserQuestion 确认
Step 3  确认后 git add
Step 4  按公司模板组织提交信息 → 🚨全文展示 → AskUserQuestion 确认
Step 5  git commit -F <临时文件>（不启动编辑器 → 不弹框）
Step 6  汇报 commit 结果 → 🚨等用户确认 → git push origin HEAD:refs/for/<当前分支>
```

## 🚨 强制规则（违反任何一条即流程失败）

1. **git add 前必须展示拟添加文件清单并经 AskUserQuestion 确认**，禁止直接 add
2. **git commit 前必须展示提交信息全文并经 AskUserQuestion 确认**，禁止直接 commit
3. **git push 前必须等用户明确同意**（push 是外发动作，永不自动执行）
4. **编译副产物、与本次功能无关的修改一律不 add**（历史入库状态≠提交习惯）
5. 提交信息临时文件放 `%TEMP%`，提交成功后删除，**不进工程树**
6. 多步操作**每步先汇报结论**再启动下一步，禁止一条命令串到底
7. 任何一步用户说取消 → 立即停止，已执行的 git add 用 `git restore --staged <file>` 撤销（不动工作区）
8. 选择题**一次弹完**（AskUserQuestion 最多 4 题），禁止连环追问；缺文本信息时先问齐再执行

## Step 1: 确认改动

```bash
cd <git仓库根>   # git rev-parse --show-toplevel 定位，不写死路径
git status --porcelain
git diff --stat
```

向用户展示：分支名、改动文件列表、每个文件一行 diff 摘要。

## Step 2: 分类并确认 add 清单 🚨

把 `git status` 的改动分两类：

| 类别 | 判定 | 处理 |
|------|------|------|
| **相关源码** | 与本次功能/修复直接相关的手写代码 | 候选 add |
| **编译副产物 / 无关** | 构建生成、无关改动 | 默认排除 |

**判定按任务上下文，不维护排除清单**：只 add 与本次功能/修复直接相关的手写源码；构建生成物（debug_log.h、comdb*.txt 等）、工具自动改写的配置（nwy_project.mk 等）、无关改动一律排除。被排除的文件**逐个列在"默认排除"区**让用户过目。拿不准的文件归入"待定"，问用户。

AskUserQuestion 示例：
```
问：拟 git add 以下文件，确认吗？
  ──拟添加──
  PLAT/.../nwy_tcpudpBC28_at.c   ← AT+NSOST 修复
  ──默认排除（编译副产物）──
  PLAT/tools/debug_log.h / comdb.txt / ...（列全）
选项：
  确认添加
  我要增删文件（选此后告知具体增删）
  取消
```

用户选"我要增删文件" → 按要求调整清单 → **再次展示并确认**。用户说取消 → 停止流程。

## Step 3: 执行 git add

**仅在 Step 2 确认后**执行，只 add 清单内文件（逐个显式列出，禁用 `git add .` / `git add -A`）：

```bash
git add <file1> <file2> ...
git status --porcelain   # 复核：A/M 状态符合预期
```

add 后复核结果并汇报（确认没有多加/漏加）。

## Step 4: 组织提交信息并确认 🚨

**模板来源**：`git config --get commit.template`（全局配置指向的明文文件，直接读）。拿不到时看 `git log -3 --format=%B` 依样组织。

**模板与字段**（Change-Id 禁止手写，Gerrit 的 commit-msg 钩子自动追加）：

```
#----------------------------------------------------------------
Feishu-ID  : <单号,简述>

Model-Custom : <项目名>

Reasons    : <修改原因/内容>
CppCheck   : <YES/NA>
AI-CRatio  : <0%~100%>
#----------------------------------------------------------------
```

**Feishu-ID 字段习惯（重要）**：不是裸单号，是 **`单号 + 逗号或空格 + 简述`**：
- 发版类：`7125356598,release N25-R04-STDOPEN_NIC-20`
- 修复类：`7062167960,fix AT+NSOST send length limit (1358->1400)`
- 多单号：`7097441267 7083930736 7061955724 modified BC28 AT command manuals...`

**字段填充**：
- `Feishu-ID`：从当前上下文（飞书项目单）取单号 + 按上述习惯写简述
- `Patch/Feature`：模板注释行，属补丁提交/功能开发时去掉 `#` 启用
- `Model-Custom`：项目名（如 N306_CN_C2_BC28_QJ），与本次改动所属项目一致
- `Reasons`：改动原因与内容，一两行说清
- `CppCheck`：静态检查结果，做了写 YES，没做写 NA
- `AI-CRatio`：本次提交 AI 代码占比（0%~100%），如实评估

**信息不足时**：把缺的字段合并成**一轮** AskUserQuestion/文本询问，问齐再组织，禁止逐字段连环问。

**确认弹窗**（全文放问题描述里，选项是确认动作）：
```
问：提交信息如下，确认吗？
  <提交信息全文>
选项：
  确认，按此提交
  我要改字段（选此后告知改哪）
  取消
```

## Step 5: 执行 git commit（绕开弹框）

公司环境 `git commit` 会弹出信息框（编辑器预填模板）。**用 `-F` 传入组织好的信息文件，编辑器不启动、弹框不出现**：

```bash
MSGFILE="$TEMP/nwy_commit_msg_$(date +%Y%m%d_%H%M%S).txt"
# Windows 路径：用 cygpath -w 或 %TEMP% 直接拼；消息文件必须放 %TEMP%，不进工程树
git commit -F "$MSGFILE"
git log -1 --format=%B   # 复核：Change-Id 已被钩子自动追加
rm -f "$MSGFILE"          # 成功后清理临时文件
```

**注意**：
- 禁用 `git commit -m`（多段模板易乱）、禁用不带 `-F` 的裸 `git commit`（会弹框）
- commit 后必须复核 `git log -1`：Change-Id 存在；不存在说明 `.git/hooks/commit-msg`（Gerrit 钩子）缺失，**停下提醒用户**，不要继续 push
- 失败（钩子校验不过等）→ 读报错修正信息后重新确认，最多重试 2 次

## Step 6: 汇报并等待确认，再 push 🚨

commit 成功后**先汇报**：分支、commit hash、提交信息摘要、下一步 push 目标。然后停下：

```
下一步：git push origin HEAD:refs/for/<当前分支>
确认后执行。
```

**push 目标分支** = 当前分支（Gerrit 评审流）：
```bash
BRANCH=$(git branch --show-current)          # 如 master_QIANJIA_20260714
git push origin HEAD:refs/for/$BRANCH
```

**用户明确同意后才执行 push**。push 输出里的 Gerrit 评审链接要抓取并回报给用户。

**异常**：
- push 被拒（权限/Change-Id/评审冲突）→ 报告完整报错，等用户处理，禁止自行改远端
- 用户说"先不推" → commit 保留在本地，流程正常结束

## 常见场景速查

| 场景 | 处理 |
|------|------|
| 只想 commit 不 push | Step 5 后正常结束，明示"本地已提交，未 push" |
| 提交信息要改 | 撤销重来：`git commit --amend` 同样走 `-F` + 重新确认；未 push 前可 amend，**已 push 到 Gerrit 的禁止 amend 追推**（会产生新 patchset，需用户明确要求） |
| add 加错了 | `git restore --staged <file>`（不动工作区），回 Step 2 |
| 不在仓库根 | `git rev-parse --show-toplevel` 定位后 cd 过去 |
| 多个仓库改动 | 一次只提交一个仓库的改动，第二个仓库重新走全流程 |

## 环境依赖

- Git + Gerrit：`origin` 指向 Gerrit，push 走 `refs/for/<分支>` 评审流
- 提交模板：`git config --get commit.template`（全局指向明文模板文件）
- Gerrit 钩子：`.git/hooks/commit-msg` 自动生成 Change-Id（提交后必须复核存在）
- 无需弹框/编辑器交互：一律 `-F` 传文件
