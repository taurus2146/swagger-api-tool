#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
本地构建脚本
用于在本地测试PyInstaller打包
"""

import os
import sys
import subprocess
import shutil

def main():
    """主函数"""
    print("开始本地构建...")
    
    # 检查是否安装了PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller版本: {PyInstaller.__version__}")
    except ImportError:
        print("未安装PyInstaller，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 清理之前的构建
    if os.path.exists("build"):
        print("清理build目录...")
        shutil.rmtree("build")
    if os.path.exists("dist"):
        print("清理dist目录...")
        shutil.rmtree("dist")
    
    # 运行PyInstaller
    print("开始打包...")
    result = subprocess.run([
        sys.executable, "-m", "PyInstaller", 
        "build.spec",
        "--clean"
    ])
    
    if result.returncode == 0:
        print("✅ 打包成功！")
        print("可执行文件位置: dist/SwaggerAPITester/")
        
        # 检查文件大小
        exe_path = "dist/SwaggerAPITester/SwaggerAPITester.exe"
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"可执行文件大小: {size_mb:.1f} MB")
        
        print("\n你可以运行以下命令测试:")
        print("cd dist/SwaggerAPITester && SwaggerAPITester.exe")
    else:
        print("❌ 打包失败！")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())