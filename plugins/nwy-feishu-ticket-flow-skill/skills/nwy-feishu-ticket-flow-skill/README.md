# nwy-feishu-ticket-flow-skill

飞书项目单子流转收口 Skill：开发+验证完成后，把缺陷单一次性流转到**回归**，兼顾需求单/ITR（节点流）的节点确认流转。

## 流程

```
链式两跳：Open → Fixed → Regression（循环到 Regression 才算完）
第 1 跳 Open→Fixed：
  查流转路径 → 必填项一次查全（不带 --mode）→ 与 16 项对照表对账（返回为唯一事实源）
  → 一轮收集（决策类①归属②问题类型… 一个不漏 + 起草文本确认）
  → 写字段 + 必填角色（软件PL）→ 流转
第 2 跳 Fixed→Regression：
  重查流转路径（transition_id 已失效）→ 关联回归版本（MQL 查 version ID，整数组覆盖写）
  → 流转 → 显式带 --fields 复核=Regression → 交接测试部
中途失败 → 断点续跑（记录已完成跳，不重复收集、不回滚已写字段）
```

## 设计要点

| 维度 | 说明 |
|------|------|
| **一轮收齐** | 全部"问用户"项+起草文本一次收集（超 4 题同消息拆两轮），杜绝挤牙膏式补字段 |
| **必填全景 + 对账** | issue→Fixed 实测 16 项表作对照，list-state-required 返回为唯一事实源，防表单改版过时 |
| **决策不代填** | 归属/问题类型/时间/人员等业务字段必须用户拍板 |
| **上下文起草** | 根因/修改点/自测/Gerrit 链接从会话上下文自动组织 |
| **断点续跑** | 两跳中途失败可接着走，不重复问、不回滚 |
| **节点流写入分流** | 普通字段走 update、节点字段走 update-node 且一次一个（多写静默丢） |
| **坑内置** | mode 漏项、transition_id 过期、MQL 反引号、get-node 畸形 JSON、终态版本锁编辑等都进了坑表 |

## 边界

- ✅ Open/Fixed/Reopen 起步 → Regression（回归）
- ✅ 需求单/ITR 节点流 confirm
- ❌ 代码修复/编译（走 nwy-ec626-build-skill）/ 提交（走 nwy-git-commit-skill）
- ❌ 回归通过后的关闭（测试部处理）
- ❌ 版本侧挂单（走 nwy-meegle-version-tickets-skill；本技能只写缺陷侧 resolve_version）

## 文件结构

```
nwy-feishu-ticket-flow-skill/
├── SKILL.md      ← 技能定义主文件（含实测案例）
└── README.md     ← 本文件
```

## 开发者

mengxiangrui (mengxiangrui@neoway.com)
