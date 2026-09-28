# nwy-requirements-analysis-skill

飞书项目（Meegle / Lark Project）工作项查询 + 需求分析 Skill。

> **本文件只是指针，不复制正文**，一切以 [SKILL.md](SKILL.md) 为准。

## 解决的问题

本地安装了 `meegle` CLI，但 agent 每次查询飞书项目单都需要反复试错：
- 不知道要先 `project search` 拿 project_key
- 直接用 `workitem get` 报错 "project_key is empty"
- 猜测 project_key 导致多次失败

更重要的是：**只拿到单子需求是不够的** —— 还要自己翻代码才能确定要改哪里，而这一步常常靠猜。

封装为 skill 后，agent 按固定流程执行，**一次命中**；并可继续做需求拆解与源码定位，直接给出候选改动点。

## 工作流

```
输入单号 → project search → 遍历 workitem get → 格式化输出 → [询问是否分析] → 需求拆解 → 通用源码检索 → 改动点结论 + 落盘 docs/nwy-NNN-<名字>.md
```

## 触发词

**查单**：
- "飞书项目单 + 单号"
- "meegle 单子 + 单号"
- "查一下 XXX 单号"

**需求分析**（查单后继续）：
- "分析需求单 + 单号"
- "这个单子要改哪些代码"
- "结合代码分析需求" / "定位改动点"

## 去 SKILL.md 哪节

| 快速索引 | 去 SKILL.md 哪节 |
|---------|-----------------|
| 查单四步流程 | `## 强制标准流程` Step 1-4 |
| 何时问用户要不要分析 | Step 4.5 |
| 需求怎么拆（功能点/影响范围/验收点/疑点） | Step 5 |
| 源码怎么定位改动点（通用检索法） | Step 6 |
| 报告落盘路径与骨架 | `## 分析文档落盘规范` |
| 对话里输出什么 | `## 对话输出模板` |
| 出错怎么处理 | `## 错误处理` |

## 文件结构

```
nwy-requirements-analysis-skill/
├── SKILL.md       ← 技能定义主文件（正文以它为准）
└── README.md      ← 本文件（指针）
```

## 开发者

mengxiangrui (mengxiangrui@neoway.com)
