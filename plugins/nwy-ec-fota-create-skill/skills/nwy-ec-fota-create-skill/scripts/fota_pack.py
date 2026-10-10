#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EC(Eigencomm) FOTA 双向差分包打包脚本

封装 FotaToolkit.exe CLI 的 -d（差分）与 -l（校验）能力：
  一次调用产出 正向升级包 {base}-{target}.par 和 反向回退包 {target}-{base}.par

用法示例:
  python fota_pack.py --base-bin 004.bin --target-bin 005.bin
  python fota_pack.py --base-bin old.bin --target-bin new.bin --base-ver V001 --target-ver V002 --direction forward
  python fota_pack.py --base-bin a.binpkg --target-bin b.binpkg --attr BINPKG
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_TOOL_DIR = Path(r"G:\EC626\FotaToolkit_V3.6.4.0")
# skill 自带的完整工具副本（skill 自包含，拷到任何机器可用）
BUNDLED_TOOL_DIR = Path(__file__).resolve().parent.parent / "tool"

FAIL_PATTERNS = [
    r">>>+\s*FAIL\s*<<<+",
    r"\(E\)\s*err",
    r"err! ",
    r"error! ",
    r"failure!",
]


VER_RE = re.compile(r"^V\d{3}\.\d{3}\.\d{3}$")


def run_delta(tool_exe, config, attr, out_par, base_bin, target_bin, base_ver, target_ver, pem):
    """执行一次 -d 差分，返回 (成功?, 命令输出文本)"""
    cmd = [str(tool_exe), "-d", str(config), attr, str(out_par), str(base_bin), str(target_bin)]
    # 版本号仅支持 Vmmm.nnn.ppp 格式（且仅做包头记录）；短标签提示已在主流程打印
    cmd.extend([v for v in (base_ver, target_ver) if v and VER_RE.match(v)])
    # pem 是第 3 个可选位置参数，必须先有版本号占位才安全
    if pem:
        if base_ver and target_ver and VER_RE.match(base_ver) and VER_RE.match(target_ver):
            cmd.append(pem)
        else:
            print("[!] 使用 pem 签名时必须同时提供 Vmmm.nnn.ppp 格式的两个版本号，本次已忽略签名")

    proc = subprocess.run(
        cmd,
        cwd=str(tool_exe.parent),
        capture_output=True,
        text=True,
        errors="replace",  # 编码跟随系统区域设置（Windows 中文环境为 cp936/gbk），避免原生 exe 输出乱码
        timeout=600,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return cmd, output, proc.returncode


def analyze_output(output):
    """从工具输出中提取失败信息；返回失败行列表（空列表=未见显式失败标记）"""
    fails = []
    for line in output.splitlines():
        for pat in FAIL_PATTERNS:
            if re.search(pat, line):
                fails.append(line.strip())
                break
    return fails


def verify_par(tool_exe, config, par_path):
    """用 -l 解析生成的 par，返回解析输出文本"""
    cmd = [str(tool_exe), "-l", str(config), str(par_path)]
    proc = subprocess.run(
        cmd,
        cwd=str(tool_exe.parent),
        capture_output=True,
        text=True,
        errors="replace",
        timeout=120,
    )
    return (proc.stdout or "") + (proc.stderr or "")


def delta_limit(config_path):
    """读取配置中的差分包下载区上限 deltaMemSize（字节）"""
    try:
        raw = Path(config_path).read_text(encoding="utf-8")
        m = re.search(r'"deltaMemSize"\s*:\s*(\d+)', raw)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="EC FOTA 双向差分包打包")
    ap.add_argument("--base-bin", required=True, help="基线（旧）版本镜像文件路径")
    ap.add_argument("--target-bin", required=True, help="目标（新）版本镜像文件路径")
    ap.add_argument("--base-ver", default=None, help="基线版本号（可选，仅记录用）")
    ap.add_argument("--target-ver", default=None, help="目标版本号（可选，仅记录用）")
    ap.add_argument("--attr", default=None, help="镜像属性，默认按扩展名推断：.binpkg->BINPKG，其余->APP")
    ap.add_argument("--config", default=None, help="FOTA 配置 json，默认 <tool_dir>/config/ec626.json")
    ap.add_argument("--tool-dir", default=None, help="FotaToolkit 所在目录，默认按 探测链 查找")
    ap.add_argument("--out-dir", default=None, help="输出目录，默认为工具目录（skill 自带 tool/）下的 fota-create-output/")
    ap.add_argument("--prefix", default=None, help="输出包名前缀（项目/型号标识，如 QJ、N306-E08），默认取 config 文件名（芯片平台，如 ec626）")
    ap.add_argument("--pem", default=None, help="签名 pem 文件（可选）")
    ap.add_argument(
        "--direction", choices=["both", "forward", "reverse"], default="both",
        help="both=双向(默认) forward=仅升级包 reverse=仅回退包",
    )
    args = ap.parse_args()

    # 工具目录探测链：显式参数 > 环境变量 > skill 自带 tool/ > 默认 G 盘路径
    if args.tool_dir:
        tool_dir = Path(args.tool_dir)
    elif os.environ.get("FOTATOOLKIT_DIR"):
        tool_dir = Path(os.environ["FOTATOOLKIT_DIR"])
    elif BUNDLED_TOOL_DIR.exists():
        tool_dir = BUNDLED_TOOL_DIR
    else:
        tool_dir = DEFAULT_TOOL_DIR
    print(f"[i] 使用工具目录: {tool_dir}")
    tool_exe = tool_dir / "FotaToolkit.exe"
    if not tool_exe.exists():
        print(f"[X] 未找到工具: {tool_exe}")
        sys.exit(2)

    config = Path(args.config) if args.config else tool_dir / "config" / "ec626.json"
    if not config.exists():
        print(f"[X] 未找到配置文件: {config}")
        sys.exit(2)

    base_bin = Path(args.base_bin).resolve()
    target_bin = Path(args.target_bin).resolve()
    for f in (base_bin, target_bin):
        if not f.exists():
            print(f"[X] 文件不存在: {f}")
            sys.exit(2)

    # 预检1：两个输入是同一文件（路径相同或内容一致）——工具会拒绝差分，属正常情况而非失败
    def file_md5(p):
        h = hashlib.md5()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    if base_bin == target_bin or (
        base_bin.stat().st_size == target_bin.stat().st_size
        and file_md5(base_bin) == file_md5(target_bin)
    ):
        print("[i] 两个输入文件相同，无需差分（回退包与升级包在此场景下无意义），未生成任何文件。")
        sys.exit(0)

    # 预检2：混合输入（bin 与 binpkg 混用）无法共用同一 memAttr，直接拒绝
    if base_bin.suffix.lower() != target_bin.suffix.lower():
        print(f"[X] 两个输入文件类型不一致（{base_bin.suffix} vs {target_bin.suffix}），"
              f"bin 与 binpkg 不能混用差分，请检查输入。")
        sys.exit(2)

    attr = args.attr or ("BINPKG" if base_bin.suffix.lower() == ".binpkg" else "APP")
    # 默认输出到工具目录（skill 自带 tool/）下的 fota-create-output/，产物集中、清理只看一处
    out_dir = Path(args.out_dir).resolve() if args.out_dir else tool_dir / "fota-create-output"
    # 陷阱：FotaToolkit.exe 每次运行会清空并重建 tool_dir/tmp/，
    # 输出目录若放在其下会在打包中途被删掉，导致最终写文件失败
    if tool_dir.resolve() / "tmp" in out_dir.parents or out_dir == tool_dir.resolve() / "tmp":
        safe_dir = tool_dir / "fota_out"
        print(f"[!] 输出目录位于工具 tmp/ 下（会被工具清空），已改用: {safe_dir}")
        out_dir = safe_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    base_label = args.base_ver or base_bin.stem
    target_label = args.target_ver or target_bin.stem
    # 包名前缀：显式 --prefix > config 文件名（芯片平台）；智能选取规范见 SKILL.md，脚本只做兜底
    prefix = args.prefix or config.stem
    # 短标签提示只在主流程打印一次（双向打包时 run_delta 会跑两遍，避免重复刷屏）
    if args.base_ver or args.target_ver:
        import re as _re
        if not (_re.match(VER_RE, args.base_ver or "") and _re.match(VER_RE, args.target_ver or "")):
            print(f"[i] 版本标签 {args.base_ver}/{args.target_ver} 按短标签处理：仅用于输出文件命名（如 {prefix}-{base_label}-{target_label}.par），包头不含版本号——这是预期行为，不影响包功能。如需包头记录版本，请用 Vmmm.nnn.ppp 格式（如 V000.005.000）")
    limit = delta_limit(config)

    results = []
    jobs = []
    if args.direction in ("both", "forward"):
        jobs.append((f"{prefix}-{base_label}-{target_label}.par", base_bin, target_bin, args.base_ver, args.target_ver))
    if args.direction in ("both", "reverse"):
        jobs.append((f"{prefix}-{target_label}-{base_label}.par", target_bin, base_bin, args.target_ver, args.base_ver))

    overall_ok = True
    for name, old, new, v_old, v_new in jobs:
        out_par = out_dir / name
        print(f"\n===== 差分: {old.name} -> {new.name} =====")
        cmd, output, rc = run_delta(tool_exe, config, attr, out_par, old, new, v_old, v_new, args.pem)
        print(output.strip())
        fails = analyze_output(output)
        if rc != 0 or fails or not out_par.exists():
            overall_ok = False
            print(f"\n[X] 打包失败: {out_par.name} (exit={rc})")
            for fl in fails[:5]:
                print(f"    失败信息: {fl}")
            continue
        size = out_par.stat().st_size
        warn = ""
        if limit and size > limit:
            warn = f"  [!] 超过配置的差分包下载区上限 deltaMemSize={limit} 字节，设备端可能无法下载！"
            overall_ok = False
        print(f"\n[OK] 生成: {out_par}  ({size} bytes){warn}")
        lv = verify_par(tool_exe, config, out_par)
        print(f"----- -l 校验输出 ({name}) -----")
        print(lv.strip())
        results.append((out_par, size))

    print("\n========== 汇总 ==========")
    if results:
        for p, s in results:
            print(f"  [OK] {p}  ({s} bytes)")
    if not overall_ok:
        print("  存在失败/超限项，请检查上方日志。")
        sys.exit(1)
    print("  全部完成。")


if __name__ == "__main__":
    main()
