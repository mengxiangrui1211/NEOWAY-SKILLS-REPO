#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
find_mcp_ip.py — 从已注册的 MCP 配置里反解 firmware-flash server 的 IP/URL。

为什么：烧录 skill 需要"本地烧录机器 IP"才能 push .lod / curl :9870/health。
MCP 已注册过的话，这个 IP 就嵌在客户端配置文件里，应自动解析，
不要再 AskUserQuestion 让用户手填（2026-08-24 截图坑）。

用法（在 rda8909b-flash skill Step 0.0 优先级 C 调用）:
    python find_mcp_ip.py                 # 输出形如: IP=192.168.66.126 (source=...)
    python find_mcp_ip.py --json          # JSON 输出供 shell 解析
退出码:
    0 = 找到
    1 = 没找到（再去 AskUserQuestion 兜底或跑优先级 B 的 CLI）

支持的客户端与其配置路径（按顺序扫，命中即停）:
- Claude Code 项目级 .mcp.json、用户级 ~/.claude.json、~/.config/claude/mcp.json
- WorkBuddy ~/.workbuddy/mcp.json
- Codex ~/.codex/config.toml (TOML)
- Z Code ~/.zcode/cli/config.json、.agents/mcp.json
- Cursor 项目/用户 .cursor/mcp.json
- VS Code .vscode/mcp.json
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
from typing import Iterable, Optional, Tuple

# 匹配 http(s)://<ip>:<port>/mcp；IP 是 v4 或 IPv6([::1]:port)
URL_RE = re.compile(r"https?://(\[[0-9A-Fa-f:]+\]|[0-9]{1,3}(?:\.[0-9]{1,3}){3})(?::\d+)?(?:/mcp)?\b")

# 各客户端可能的 firmware-flash server 所在 JSON 键（递归找）
TARGET_NAME = "firmware-flash"


def _expand(p: str | os.PathLike) -> pathlib.Path:
    return pathlib.Path(os.path.expanduser(os.path.expandvars(str(p))))


def _candidate_paths(cwd: pathlib.Path, home: pathlib.Path) -> list[pathlib.Path]:
    """按优先级扫的路径列表（早命中早返回）"""
    return [
        # Claude Code 项目级
        cwd / ".mcp.json",
        # Claude Code 用户级（claude mcp add --scope user 写入这里）
        home / ".claude.json",
        home / ".config" / "claude" / "mcp.json",
        # WorkBuddy
        home / ".workbuddy" / "mcp.json",
        # Codex（TOML，独立处理）
        home / ".codex" / "config.toml",
        # Z Code
        home / ".zcode" / "cli" / "config.json",
        cwd / ".zcode" / "config.json",
        cwd / ".agents" / "mcp.json",
        # Cursor
        cwd / ".cursor" / "mcp.json",
        home / ".cursor" / "mcp.json",
        # VS Code
        cwd / ".vscode" / "mcp.json",
    ]


def _from_url(url: str) -> Optional[Tuple[str, str]]:
    """提取 (host, source_label)"""
    m = URL_RE.search(url)
    if not m:
        return None
    host = m.group(1)
    # 去 IPv6 的方括号
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return host, url


def _walk_json(obj, name_hint: str = "", path: Tuple[str, ...] = ()) -> Iterable[Tuple[str, str, Tuple[str, ...]]]:
    """在 JSON 树里找含 firmware-flash 的节点, yield (name, url, key_path)
    携带 key_path 是为了在 source label 里看到 URL 实际嵌套位置。
    Claude Code 实际 schema: projects.<path>.mcpServers.firmware-flash.url
    """
    if isinstance(obj, dict):
        node_name = obj.get("name") or obj.get("serverName") or ""
        # 启发式 1: 当前节点直接有 url + 名字相关
        if isinstance(obj.get("url"), str) and (
            name_hint == TARGET_NAME
            or node_name == TARGET_NAME
            or TARGET_NAME in (obj.get("type") or "")
            or TARGET_NAME in str(obj.get("command") or "")
        ):
            yield (node_name or TARGET_NAME, obj["url"], path)

        # 启发式 2: mcpServers 字典下有 firmware-flash 子节点
        for k in ("mcpServers", "servers", "mcp.servers"):
            if k in obj and isinstance(obj[k], dict):
                inner = obj[k].get(TARGET_NAME)
                if isinstance(inner, dict) and isinstance(inner.get("url"), str):
                    yield (TARGET_NAME, inner["url"], path + (k, TARGET_NAME))
                # stdio 类型无 url, 跳过

        # 递归子节点
        for k, v in obj.items():
            yield from _walk_json(v, name_hint=node_name, path=path + (str(k),))


def _scan_json(path: pathlib.Path) -> Optional[Tuple[str, str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    for name, url, key_path in _walk_json(data):
        hit = _from_url(url)
        if hit:
            host, _ = hit
            # source label: 文件路径 + JSON 键路径(末 5 段), 让用户/agent 看得见 URL 在哪
            label_parts = [f"file={path}"]
            if key_path:
                label_parts.append(f"path=...{'.'.join(key_path[-5:])}")
            return host, " ".join(label_parts)
    return None


def _scan_toml(path: pathlib.Path) -> Optional[Tuple[str, str]]:
    """Codex 的 config.toml 是 TOML, 没装 tomllib/3rd 库也尽量裸抓 url=
    形如:
        [mcp_servers.firmware-flash]
        url = "http://192.168.66.126:8909/mcp"
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    # 简单匹配: 在 firmware-flash 节附近找 url =
    lines = text.splitlines()
    in_section = False
    section_re = re.compile(r"\[(?:mcp_servers|mcp)\.firmware-flash\]", re.IGNORECASE)
    url_re = re.compile(r'url\s*=\s*["\']([^"\']+)["\']')
    for line in lines:
        if section_re.search(line):
            in_section = True
            continue
        if in_section and line.strip().startswith("["):
            in_section = False
        if in_section:
            m = url_re.search(line)
            if m:
                hit = _from_url(m.group(1))
                if hit:
                    return hit[0], f"source={path}"
    return None


def find(cwd: Optional[pathlib.Path] = None,
         home: Optional[pathlib.Path] = None) -> Optional[Tuple[str, str]]:
    cwd = cwd or pathlib.Path.cwd()
    home = home or pathlib.Path(os.path.expanduser("~"))
    for p in _candidate_paths(cwd, home):
        if not p.exists():
            continue
        if p.suffix == ".toml":
            hit = _scan_toml(p)
        else:
            hit = _scan_json(p)
        if hit:
            return hit
    return None


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    hit = find()
    if not hit:
        if as_json:
            print(json.dumps({"found": False}))
        else:
            print("NOTFOUND", file=sys.stderr)
        return 1
    host, source = hit
    if as_json:
        print(json.dumps({"found": True, "ip": host, "source": source}))
    else:
        print(f"IP={host} ({source})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
