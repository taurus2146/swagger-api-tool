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
import platform

def check_dependencies():
    """检查并安装必要的依赖"""
    required_packages = ['pyinstaller', 'pillow']
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} 已安装")
        except ImportError:
            print(f"📦 正在安装 {package}...")
            result = subprocess.run([sys.executable, "-m", "pip", "install", package])
            if result.returncode != 0:
                print(f"❌ 安装 {package} 失败")
                return False
    
    return True

def create_icon():
    """创建图标文件"""
    print("🎨 创建图标文件...")
    result = subprocess.run([sys.executable, "create_icon.py"])
    return result.returncode == 0

def clean_build():
    """清理之前的构建"""
    dirs_to_clean = ["build", "dist"]
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"🧹 清理 {dir_name} 目录...")
            try:
                shutil.rmtree(dir_name)
            except Exception as e:
                print(f"⚠️  清理 {dir_name} 失败: {e}")

def build_executable():
    """构建可执行文件"""
    print("🔨 开始构建可执行文件...")
    
    cmd = [sys.executable, "-m", "PyInstaller", "build.spec", "--clean"]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ 构建成功！")
        return True
    else:
        print("❌ 构建失败！")
        print("错误输出:")
        print(result.stderr)
        return False

def check_build_result():
    """检查构建结果"""
    system = platform.system()
    if system == "Windows":
        exe_path = "dist/SwaggerAPITester/SwaggerAPITester.exe"
    else:
        exe_path = "dist/SwaggerAPITester/SwaggerAPITester"
    
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"📊 可执行文件大小: {size_mb:.1f} MB")
        
        # 列出dist目录内容
        print("\n📁 构建产物:")
        dist_path = "dist/SwaggerAPITester"
        if os.path.exists(dist_path):
            for item in os.listdir(dist_path):
                item_path = os.path.join(dist_path, item)
                if os.path.isfile(item_path):
                    size_kb = os.path.getsize(item_path) / 1024
                    print(f"  📄 {item} ({size_kb:.1f} KB)")
                else:
                    print(f"  📁 {item}/")
        
        print(f"\n🚀 测试运行命令:")
        if system == "Windows":
            print(f"cd dist\\SwaggerAPITester && SwaggerAPITester.exe")
        else:
            print(f"cd dist/SwaggerAPITester && ./SwaggerAPITester")
        
        return True
    else:
        print(f"❌ 可执行文件不存在: {exe_path}")
        return False

def main():
    """主函数"""
    print("🚀 Swagger API测试工具 - 本地构建脚本")
    print("=" * 50)
    
    # 检查Python版本
    python_version = sys.version_info
    print(f"🐍 Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        return 1
    
    # 检查依赖
    if not check_dependencies():
        print("❌ 依赖检查失败")
        return 1
    
    # 创建图标
    create_icon()
    
    # 清理构建目录
    clean_build()
    
    # 构建可执行文件
    if not build_executable():
        return 1
    
    # 检查构建结果
    if not check_build_result():
        return 1
    
    print("\n🎉 本地构建完成！")
    return 0

if __name__ == "__main__":
    sys.exit(main())