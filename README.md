<p align="center">
  <img src="assets/neoway-logo.png" alt="Neoway 有方科技" width="200">
</p>

# Neoway 标准模组团队技能仓库

Neoway 标准模组项目团队技能包分发仓库，由 mengxiangrui 发布维护。
团队同事推荐通过 AICom 一键安装；其他 Agent 工具（Claude Code / Trae / Cursor 等）可按手动方式安装。

## 技能列表

<!-- SKILLS:BEGIN 由 AICom 发布时自动更新，勿手工编辑 -->
| 技能包 | 版本 | 说明 | 更新时间 |
| --- | --- | --- | --- |
| nwy-requirements-analysis-skill | v1.0.0 | 查询飞书项目（Meegle/Lark Project）工作项，并可继续做需求分析与当前仓库源码定位。用户提到"查一下 XXX 单号""飞书项目单""meegle 单子""飞书需求单"时查详情，查完询问是否继续需求开发分析；说"分析这个需求单""需求分析""这个单子要改哪些代码""结合代码分析需求""定位改动点"时直接进入分析：需求拆解（功能点/影响范围/验收点/疑点）→ 当前工作仓库内通用源码检索 → 输出候选代码改动点与调用链，并把分析报告落盘为 docs/ 下的 nwy-<序号>-<自动生成名>.md。自动发现 project_key 一次命中；代码分析不写死任何仓库路径。 | 2026/9/28 |
| nwy-rda8909b-flash-skill | v1.0.0 | 规范 RDA 8909B / Neoway N25 固件烧录流程。通过 aicom-RDA-8909B-flasher MCP 连接器驱动本地 fpupgrade.exe 时，强制"先询问端口与固件→写入配置→一键全自动闭环→监控至会话复位 idle"，防止模型随心所欲调用工具。触发词：烧录、flash、升级。 | 2026/9/28 |
| nwy-rda8909b-build-skill | v1.0.0 | RDA8909B 平台编译工具，支持底层固件和上层APP的交互式编译，自动处理菜单选择并弹出实时日志窗口。当前适配 N25-EU-BZ（标准项目）和 N25-EU-NIC 项目，其他项目可扩展。用于用户要求"编译""构建""build"项目时。 | 2026/9/28 |
<!-- SKILLS:END -->
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
