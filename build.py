#!/usr/bin/env python3
"""
图书库浏览器 - 打包脚本
封装 PyInstaller，支持 macOS 应用构建
用法: python build.py [--clean] [--output DIR]
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
APP_NAME = "图书库浏览器"
MAIN_SCRIPT = "library_browser.py"
SPEC_FILE = f"{APP_NAME}.spec"


def run_cmd(cmd, cwd=None):
    """执行命令并实时输出"""
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        sys.exit(result.returncode)


def check_pyinstaller():
    """检查 PyInstaller 是否安装"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"PyInstaller 版本: {result.stdout.strip()}")
            return True
    except Exception:
        pass
    print("未找到 PyInstaller，正在安装...")
    run_cmd([sys.executable, "-m", "pip", "install", "pyinstaller"])
    return True


def clean_build():
    """清理构建产物"""
    dirs_to_clean = ["build", "dist"]
    for d in dirs_to_clean:
        path = ROOT_DIR / d
        if path.exists():
            print(f"清理 {d}/ ...")
            shutil.rmtree(path, ignore_errors=True)

    # 清理 ._ 残留文件（AFP/SMB 网络盘常见）
    for f in ROOT_DIR.rglob("._*"):
        try:
            f.unlink()
        except Exception:
            pass

    print("清理完成")


def build_app(clean=False):
    """构建 macOS .app 应用"""
    if clean:
        clean_build()

    # 检查依赖
    check_pyinstaller()

    spec_path = ROOT_DIR / SPEC_FILE
    if not spec_path.exists():
        print(f"错误: 找不到 {SPEC_FILE}")
        sys.exit(1)

    main_script = ROOT_DIR / MAIN_SCRIPT
    if not main_script.exists():
        print(f"错误: 找不到 {MAIN_SCRIPT}")
        sys.exit(1)

    print("=" * 60)
    print(f"开始构建 {APP_NAME}")
    print("=" * 60)

    # 执行 PyInstaller
    run_cmd(
        [sys.executable, "-m", "PyInstaller", str(spec_path), "--clean", "--noconfirm"],
        cwd=str(ROOT_DIR)
    )

    # 清理 ._ 残留文件（避免签名问题）
    app_path = ROOT_DIR / "dist" / f"{APP_NAME}.app"
    if app_path.exists():
        for f in app_path.rglob("._*"):
            try:
                f.unlink()
            except Exception:
                pass

    print("=" * 60)
    print("构建完成！")
    print(f"应用路径: {app_path}")

    # 显示大小
    if app_path.exists():
        size_bytes = sum(f.stat().st_size for f in app_path.rglob("*") if f.is_file())
        size_mb = size_bytes / (1024 * 1024)
        print(f"应用大小: {size_mb:.1f} MB")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="图书库浏览器打包工具")
    parser.add_argument(
        "--clean", "-c",
        action="store_true",
        help="构建前清理旧的构建产物"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="输出目录（默认 dist/）"
    )
    args = parser.parse_args()

    build_app(clean=args.clean)


if __name__ == "__main__":
    main()
