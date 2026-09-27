# Neoway 标准模组团队技能仓库

Neoway 标准模组项目团队技能包分发仓库，由 mengxiangrui 发布维护。
团队同事推荐通过 AICom 一键安装；其他 Agent 工具（Claude Code / Trae / Cursor 等）可按手动方式安装。

## 技能列表

| 技能包 | 版本 | 说明 |
|---|---|---|
| nwy-rda8909b-build-skill | v1.0.0 | RDA8909B 平台编译工具：底层固件 / 上层 APP 交互式编译，自动处理菜单选择并弹出实时日志窗口，编译报错支持自行修复 |
| nwy-rda8909b-flash-skill | v1.0.0 | RDA8909B / Neoway N25 固件烧录流程规范：驱动 aicom-RDA-8909B-flasher MCP 连接器，强制「先询问端口与固件 → 写入配置 → 一键全自动闭环 → 监控至 idle」的标准烧录流程 |

> 最新版本以仓库根目录 `skills-index.json` 为准（每次发布自动更新）。

## 方式一：AICom 内安装（推荐）

1. 打开 AICom → Skills 管理 → 「团队仓库」tab
2. 首次使用点「配置技能仓库」，填入：`mengxiangrui1211/NEOWAY-SKILLS-REPO`
3. 列表按包显示「未安装 / 已安装 / 可更新」状态，点「安装」即自动下载解压到本机技能目录

安装后：AICom 内经 MCP 工具 `skill_read` 在线读取，「我的技能包」页可见。

## 方式二：手动安装到其他 Agent 工具

1. 从 [Releases](https://github.com/mengxiangrui1211/NEOWAY-SKILLS-REPO/releases) 下载对应技能包 zip（`skills-index.json` 中每个技能也有 asset 直链）
2. 解压后把 `<技能包名>/` 整个文件夹放入你的技能目录，目录名保持不变：
   - Claude Code：`~/.claude/skills/`
   - 其他工具（Trae / Cursor 等 VSCode 扩展类 Agent）：`.agents/skills/` 或各自的技能 / 知识目录
3. 确认 `<技能包名>/SKILL.md` 存在，之后按 SKILL.md 中的说明使用

Claude Code 也可走插件市场方式（本仓库已维护 `.claude-plugin/marketplace.json`）：

```
claude plugin marketplace add mengxiangrui1211/NEOWAY-SKILLS-REPO
claude plugin install <技能包名>@NEOWAY-SKILLS-REPO
```

## 目录结构

```
plugins/<技能包>/skills/<技能包>/    # 技能包源文件（SKILL.md、config.yaml、scripts/ 等）
plugins/<技能包>/.claude-plugin/    # plugin 清单（plugin.json）
.claude-plugin/marketplace.json    # Claude Code marketplace 索引
skills-index.json                  # AICom 团队仓库索引（版本 + zip 资产直链）
```

每个技能包同时发布一个 Release（tag 形如 `<技能包>-v<版本>`），zip 内为单层 `<技能包>/` 目录，解压即用。

## 发布 / 更新（维护者）

1. 修改技能包内容，把包内 `skill.json` 的 `version` 提升（如 1.0.0 → 1.0.1）
2. AICom → Skills 管理 → 我的技能包 → 选包点「发布」，目标仓库填 `mengxiangrui1211/NEOWAY-SKILLS-REPO`
3. 发布流程自动完成：打包 zip → 创建 Release → 同步目录树 → 更新 `skills-index.json`

注意：同一版本不能重复发布（release tag 冲突闸），发布报「版本号未升级 / Release 已存在」时先提升版本号。
