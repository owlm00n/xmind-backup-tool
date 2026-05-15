#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量备份/恢复 XMind 文件。
用法:
  python xmind_batch.py backup <input_dir> <output_dir>  [ -b <backup_script> ] [ -r <restore_script> ]
  python xmind_batch.py restore <input_dir> <output_dir> [ -b <backup_script> ] [ -r <restore_script> ]

Default exclusion: AI subdirectory.
脚本默认路径: 同目录下的 AI/xmind2md.py 和 AI/md2xmind.py
如不在默认位置，可用 -b / -r 手动指定。
"""

import os
import sys
import pathlib
import subprocess
import json

# --- 排除规则 ---
EXCLUDE_DIRS = {"AI"}  # 排除名为 AI 的子目录

SCRIPT_DIR = pathlib.Path(__file__).parent

# 查找顺序: 1) 批量脚本同级目录  2) 同级 AI/ 子目录
CANDIDATE_BACKUP = [SCRIPT_DIR / "AI" / "xmind2md.py"]
CANDIDATE_RESTORE = [SCRIPT_DIR / "AI" / "md2xmind.py"]

BACKUP_SCRIPT = None
RESTORE_SCRIPT = None


def find_script(path: pathlib.Path, label: str) -> pathlib.Path:
    """查找脚本，存在返回路径，不存在打印提示后退出"""
    if path.exists():
        return path
    print(f"错误: 找不到 {label}: {path}")
    print(f"请将脚本放到默认位置，或用 -b / -r 参数手动指定。")
    sys.exit(1)


def parse_args():
    """解析命令行参数，支持 -b 和 -r 自定义脚本路径"""
    global BACKUP_SCRIPT, RESTORE_SCRIPT

    args = sys.argv[3:]  # 跳过 action, input, output
    for i, a in enumerate(args):
        if a == "-b" and i + 1 < len(args):
            BACKUP_SCRIPT = pathlib.Path(args[i + 1])
        elif a == "-r" and i + 1 < len(args):
            RESTORE_SCRIPT = pathlib.Path(args[i + 1])
        else:
            print(f"警告: 未知参数 '{a}'")

    # 未手动指定则按优先级查找
    if BACKUP_SCRIPT is None:
        for p in CANDIDATE_BACKUP:
            if p.exists():
                BACKUP_SCRIPT = p
                break
        if BACKUP_SCRIPT is None:
            BACKUP_SCRIPT = CANDIDATE_BACKUP[0]  # 保留第一个路径用于报错
    if RESTORE_SCRIPT is None:
        for p in CANDIDATE_RESTORE:
            if p.exists():
                RESTORE_SCRIPT = p
                break
        if RESTORE_SCRIPT is None:
            RESTORE_SCRIPT = CANDIDATE_RESTORE[0]

    return BACKUP_SCRIPT, RESTORE_SCRIPT


def scan_files(root: pathlib.Path, suffix: str, exclude_dirs: set) -> list:
    """递归扫描文件，跳过排除目录"""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for fn in filenames:
            if fn.endswith(suffix):
                files.append(pathlib.Path(dirpath) / fn)
    return sorted(files)


def build_output_path(input_file: pathlib.Path, input_root: pathlib.Path, output_root: pathlib.Path, suffix: str) -> pathlib.Path:
    """计算输出路径，保持目录结构"""
    rel = input_file.relative_to(input_root)
    return output_root / rel.with_suffix(suffix)


def do_backup(input_root: pathlib.Path, output_root: pathlib.Path):
    files = scan_files(input_root, ".xmind", EXCLUDE_DIRS)
    if not files:
        print(f"未找到 .xmind 文件: {input_root}")
        return

    print(f"找到 {len(files)} 个 .xmind 文件\n")
    ok = err = 0
    for f in files:
        out = build_output_path(f, input_root, output_root, ".md")
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, str(BACKUP_SCRIPT), str(f), str(out)]
        print(f"[{ok + err + 1}/{len(files)}] {f.relative_to(input_root)} -> {out.relative_to(output_root)}")
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            ok += 1
        else:
            err += 1
            print(f"  ERROR: {r.stderr[:500]}")
    print(f"\n完成: {ok} 成功, {err} 失败")


def do_restore(input_root: pathlib.Path, output_root: pathlib.Path):
    files = scan_files(input_root, ".md", EXCLUDE_DIRS)
    if not files:
        print(f"未找到 .md 文件: {input_root}")
        return

    print(f"找到 {len(files)} 个 .md 文件\n")
    ok = err = 0
    for f in files:
        out = build_output_path(f, input_root, output_root, ".xmind")
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, str(RESTORE_SCRIPT), str(f), str(out)]
        print(f"[{ok + err + 1}/{len(files)}] {f.relative_to(input_root)} -> {out.relative_to(output_root)}")
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            ok += 1
        else:
            err += 1
            print(f"  ERROR: {r.stderr[:500]}")
    print(f"\n完成: {ok} 成功, {err} 失败")


def main():
    # 先解析可能的 -b / -r 参数
    # 需要区分 action/output 和 -b/-r，手动处理
    if len(sys.argv) < 3:
        if "--help" in sys.argv or "-h" in sys.argv:
            print("Usage:")
            print("  python xmind_batch.py backup <input_dir> <output_dir>")
            print("  python xmind_batch.py restore <input_dir> <output_dir>")
            print("  Optional: -b <backup_script>  -r <restore_script>")
            print(f"\nDefault excluded dirs: {EXCLUDE_DIRS}")
            sys.exit(0)
        print("Error: insufficient arguments")
        print()
        print("Usage:")
        print("  python xmind_batch.py backup <input_dir> <output_dir>")
        print("  python xmind_batch.py restore <input_dir> <output_dir>")
        print("  Optional: -b <backup_script>  -r <restore_script>")
        print()
        print("Examples:")
        print("  python xmind_batch.py backup . D:\\xmind_output")
        print("  python xmind_batch.py restore D:\\xmind_output D:\\restored")
        print("  python xmind_batch.py backup . D:\\out -b D:\\custom\\backup.py -r D:\\custom\\restore.py")
        print(f"\nDefault excluded dirs: {EXCLUDE_DIRS}")
        sys.exit(1)

    action = sys.argv[1].lower()
    if action not in ("backup", "restore"):
        print(f"Error: unknown action '{sys.argv[1]}'")
        print()
        print("Usage: python xmind_batch.py <backup|restore> <input_dir> [output_dir] [-b <backup_script>] [-r <restore_script>]")
        sys.exit(1)

    input_root = pathlib.Path(sys.argv[2])
    output_root = pathlib.Path(sys.argv[3]) if len(sys.argv) >= 4 else input_root

    if not input_root.is_dir():
        print(f"输入目录不存在: {input_root}")
        sys.exit(1)

    # Check -b / -r
    _find_script = parse_args()

    print(f"Backup script: {BACKUP_SCRIPT}")
    print(f"Restore script: {RESTORE_SCRIPT}")
    print()

    if not BACKUP_SCRIPT.exists():
        print(f"Error: backup script not found: {BACKUP_SCRIPT}")
        print("Put xmind2md.py in the default location, or use -b to specify the path.")
        sys.exit(1)
    if not RESTORE_SCRIPT.exists():
        print(f"Error: restore script not found: {RESTORE_SCRIPT}")
        print("Put md2xmind.py in the default location, or use -r to specify the path.")
        sys.exit(1)

    if action == "backup":
        do_backup(input_root, output_root)
    else:
        do_restore(input_root, output_root)


if __name__ == "__main__":
    main()
