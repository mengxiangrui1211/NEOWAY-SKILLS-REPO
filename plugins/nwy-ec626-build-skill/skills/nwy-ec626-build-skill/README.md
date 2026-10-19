# nwy-ec626-build-skill

EC626 平台编译工具 Skill，支持固件和 Bootloader 的交互式编译。

移植自 `nwy-rda8909b-build-skill`，针对 EC626 编译体系做了适配；编译目标改为**推断优先**（弹窗分页扎堆、会话菜单本末倒置两次返工，见 SKILL.md 踩坑 10/11）。

## 做得不错的部分

| 维度 | 说明 |
|------|------|
| **推断优先** | 三级链定项目：工作流文件 → 静默侦察（工作区/编译指纹/Meegle 单）→ 才问人；冷启动也大多直接编，问也是带依据给候选（还可用单号定位项目） |
| **交互设计** | 操作默认增量固件，「全量/清理」等非默认才确认；AskUserQuestion 全流程最多一次；「有哪些项目」才出竖排清单 |
| **BL 优先** | 编固件前自动检查 bootloader.bin：缺失（新拉代码）才弹窗建议先编，已存在静默跳过不打扰 |
| **实时反馈** | PowerShell 日志窗口弹出，编译进度一目了然 |
| **动态菜单** | 菜单索引按 nwy_project 目录运行时计算，新增项目不会错位 |
| **智能判断** | 按 `build successfully` / FAIL 横幅判断结果，避开 make 噪声 |
| **自动修复** | 简单错误自动修、重新编，不用人工介入 |
| **通知闭环** | 编译完自动飞书通知，带完整信息 |
| **多分支安全** | 项目清单运行时枚举 `nwy_project/`，无静态配置文件；换分支 / 新增项目 / 同事换机器都不用改 skill |

## 适配范围

**不写死项目清单。** 每次编译都从当前分支的 `PLAT/nwy_project/` 目录实时枚举，磁盘上有什么就能编什么。

EC626 仓库**多分支并存**（`master` / `master_QIANJIA_*` / `EC_baseline` / `N306_EA_GCF_*` 等），**各分支的项目集互不相同**，任何静态名单都只是某一分支的快照，换到别的分支就会失效——列出磁盘上没有的项目，或者漏掉真正可编的项目。想看当前分支实际可编项目：

```powershell
(Get-ChildItem "PLAT\nwy_project" -Directory | Sort-Object Name).Name
```

菜单索引 = 目录字母序 0 基，脚本每次运行时动态计算。

菜单其他选项（技能均已支持）：`B` Bootloader、`U` Unilog 预解析（预解析后仍会编默认 at_command）、`C` 清理全部产物（clall，成功标记 `clean all done ok`）、`E` 退出（技能的每条命令都自动补 `E` 退出循环菜单）。

## 编译产物

| 编译类型 | 产物 |
|---------|------|
| 固件 | `gccout/ec626_0h00_ec626/at_command/app-demo-flash.bin` |
| Bootloader | `gccout/ec626_0h00_ec626/bootloader/bootloader.bin` |

**构建顺序约定**：固件与 Bootloader 独立编译（固件不依赖 BL 产物），但烧录需要两个镜像，且 gccout 不入仓库——**新拉代码后先编 Bootloader 再编固件**，技能在编固件前会自动检查并确认。多步组合（BL+固件等）**一步一个后台任务**：每步出结论先在会话汇报（"✅ Bootloader 编译成功…▶ 继续编译固件…"），再启动下一步，禁止串进同一条命令。

## 文件结构

```
nwy-ec626-build-skill/
├── SKILL.md                    ← 技能定义主文件
├── README.md                   ← 本文件
└── scripts/
    ├── build_once.ps1          ← 一键编译入口（枚举项目/输入文件/启动 bat/判定结果）
    └── watch_build_log.ps1     ← PowerShell 日志监控脚本
```

没有配置文件：项目清单来自 `PLAT/nwy_project/` 运行时枚举，不随分支漂移。

## 与 RDA8909B 技能的差异

| 维度 | nwy-rda8909b-build-skill | nwy-ec626-build-skill |
|------|--------------------------|----------------------|
| 入口脚本 | neoway_build_N25_*.bat | PLAT/build_nwy.bat |
| 工作目录 | 项目根目录 | PLAT 目录 |
| 菜单 | 固定 menu_key | 动态数字索引（运行时计算） |
| 编译类型 | opencpu + APP 分开编 | 单一固件镜像 + Bootloader |
| 成功/失败标记 | `build Success` / `build Fail` | `build successfully` / `fail` 横幅 |
| 工具链 | C:\CSDTK4 | 自带 PLAT/tools/gcc |

## 开发者

mengxiangrui (mengxiangrui@neoway.com)
