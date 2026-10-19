# nwy-git-commit-skill

公司 Git 代码提交入库流程（Gerrit）自动化 Skill。

## 流程

```
git status 确认改动
  → 🚨展示拟 add 文件清单 → 用户确认
  → git add（只加确认过的文件）
  → 按公司模板组织提交信息 → 🚨全文展示 → 用户确认
  → git commit -F %TEMP%/msg.txt（绕开弹框）
  → 汇报 → 🚨用户确认 → git push origin HEAD:refs/for/<当前分支>
```

## 设计要点

| 维度 | 说明 |
|------|------|
| **两处强制确认** | add 清单、提交信息全文，都必须用户点头才执行 |
| **push 永不自动** | 外发动作，commit 后停下等明确同意 |
| **编译副产物不 add** | 按任务上下文判断排除，排除项列出过目，不维护清单 |
| **绕开弹框** | `git commit -F` 不启动编辑器，弹框不出现；模板字段由 agent 组织 |
| **模板自动获取** | `git config --get commit.template` 读明文模板，无需测试摸索 |
| **Change-Id 免维护** | Gerrit commit-msg 钩子自动追加，提交后复核存在 |
| **临时文件进 %TEMP%** | 提交信息文件不进工程树，成功后即删 |
| **每步汇报** | 多步操作先报结论再走下一步 |

## Feishu-ID 字段习惯

`单号 + 逗号或空格 + 简述`，不是裸单号：

| 类型 | 示例 |
|------|------|
| 发版类 | `7125356598,release N25-R04-STDOPEN_NIC-20` |
| 修复类 | `7062167960,fix AT+NSOST send length limit (1358->1400)` |
| 多单号 | `7097441267 7083930736 7061955724 modified BC28 AT command manuals...` |

## 提交信息模板字段

```
Feishu-ID    单号,简述
Patch/Feature  补丁/功能点（按需启用）
Model-Custom 项目名（如 N306_CN_C2_BC28_QJ）
Reasons      修改原因/内容
CppCheck     YES/NA
AI-CRatio    0%~100%（AI 代码占比）
Change-Id    钩子自动追加，禁止手写
```

## 文件结构

```
nwy-git-commit-skill/
├── SKILL.md      ← 技能定义主文件
└── README.md     ← 本文件
```

## 开发者

mengxiangrui (mengxiangrui@neoway.com)
