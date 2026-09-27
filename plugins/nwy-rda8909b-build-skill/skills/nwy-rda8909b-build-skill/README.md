# nwy-rda8909b-build-skill

RDA8909B 平台编译工具 Skill，支持底层固件和上层APP的交互式编译。

## 做得不错的部分

| 维度 | 说明 |
|------|------|
| **交互设计** | 两步问答选类型+项目，用户不需要记任何命令 |
| **实时反馈** | PowerShell 日志窗口弹出，编译进度一目了然 |
| **智能判断** | 能识别 APP 脚本的 Success/Fail 同时输出 bug |
| **自动修复** | 简单错误自动修、重新编，不用人工介入 |
| **通知闭环** | 编译完自动飞书通知，带完整信息 |
| **可扩展** | `$PWD` 动态路径，换项目告诉 AI 脚本名就行 |

## 当前适配项目

| 序号 | 项目名 | 说明 | 底版本脚本 | APP脚本 |
|------|--------|------|-----------|---------|
| a | N25_EU_BZ | 标准项目 | `neoway_build_N25_opencpu.bat` | `neoway_build_N25_app.bat` |
| 1 | N25-EU-NIC | 定制项目 | `neoway_build_N25_opencpu.bat` | `neoway_build_N25_app.bat` |

项目配置存储在 `config.yaml` 中，新增项目只需添加配置条目，AI 自动识别。

## 文件结构

```
nwy-rda8909b-build-skill/
├── SKILL.md                    ← 技能定义主文件
├── README.md                   ← 本文件
├── config.yaml                 ← 项目配置文件
└── scripts/
    └── watch_build_log.ps1     ← PowerShell 日志监控脚本
```

## 文件结构

```
nwy-rda8909b-build-skill/
├── SKILL.md                    ← 技能定义主文件
├── README.md                   ← 本文件
└── scripts/
    └── watch_build_log.ps1     ← PowerShell 日志监控脚本
```

## 开发者

mengxiangrui (mengxiangrui@neoway.com)
