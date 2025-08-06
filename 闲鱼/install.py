'''
Author: 择安网络
Date: 2025-08-05 16:12:56
LastEditTime: 2025-08-05 20:26:16
FilePath: /咸鱼商品自动化采集/install.py
'''
import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description=""):
    print(f"\n{'='*50}")
    print(f"🔄 {description}")
    print(f"命令: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    print(f"{'='*50}")
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=isinstance(cmd, str)
        )
        print(f"✅ {description} 成功")
        if result.stdout:
            print(f"输出: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失败")
        print(f"错误代码: {e.returncode}")
        if e.stderr:
            print(f"错误信息: {e.stderr}")
        if e.stdout:
            print(f"标准输出: {e.stdout}")
        return False
def check_python_version():
    print(f"\n{'='*50}")
    print("🔍 检查Python版本")
    print(f"{'='*50}")
    version = sys.version_info
    print(f"当前Python版本: {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ 需要Python 3.7或更高版本")
        return False
    else:
        print("✅ Python版本符合要求")
        return True
def install_pip_packages():
    packages = [
        "playwright",
        "python-dotenv",
        "asyncio"
    ]
    for package in packages:
        cmd = [sys.executable, "-m", "pip", "install", package, "-i", "https://mirrors.aliyun.com/pypi/simple/"]
        if not run_command(cmd, f"安装 {package}"):
            print(f"⚠️  {package} 安装失败，尝试使用默认源")
            cmd = [sys.executable, "-m", "pip", "install", package]
            if not run_command(cmd, f"安装 {package}（默认源）"):
                return False
    return True
def install_playwright_browsers():
    print(f"\n{'='*50}")
    print("🌐 安装Playwright浏览器")
    print(f"{'='*50}")
    cmd = [sys.executable, "-m", "playwright", "install"]
    return run_command(cmd, "安装Playwright浏览器")
def main():
    if not check_python_version():
        sys.exit(1)
    if not install_pip_packages():
        print("❌ pip包安装失败")
        sys.exit(1)
    if not install_playwright_browsers():
        print("❌ Playwright浏览器安装失败")
        sys.exit(1)
if __name__ == "__main__":
    main()