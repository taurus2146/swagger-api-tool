#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
创建便携式安装包
无需额外工具，创建自解压的便携式安装包
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path

def create_portable_package():
    """创建便携式安装包"""
    print("Creating Portable Package...")
    print("="*50)
    
    # 检查必要文件
    exe_path = Path('dist/SwaggerAPITester.exe')
    if not exe_path.exists():
        print("ERROR: Single file executable not found!")
        print("Please run: python scripts/build_local.py")
        print("And select option 2 (Single file version)")
        return False
    
    # 创建包目录
    package_dir = Path('dist/portable_package')
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True)
    
    print(f"Creating package in: {package_dir}")
    
    # 复制主程序
    main_exe = package_dir / 'SwaggerAPITester.exe'
    shutil.copy2(exe_path, main_exe)
    print(f"✓ Copied main executable: {main_exe.name}")
    
    # 复制配置文件
    if Path('config').exists():
        shutil.copytree('config', package_dir / 'config')
        print("✓ Copied config directory")
    
    # 复制模板文件
    if Path('templates').exists():
        shutil.copytree('templates', package_dir / 'templates')
        print("✓ Copied templates directory")
    
    # 复制资源文件
    if Path('assets').exists():
        shutil.copytree('assets', package_dir / 'assets')
        print("✓ Copied assets directory")
    
    # 复制文档
    docs_to_copy = ['README.md', 'DEPLOYMENT.md', 'docs/packaging_guide.md']
    for doc in docs_to_copy:
        if Path(doc).exists():
            if '/' in doc:
                # 创建子目录
                dest_dir = package_dir / Path(doc).parent
                dest_dir.mkdir(exist_ok=True)
                shutil.copy2(doc, dest_dir / Path(doc).name)
            else:
                shutil.copy2(doc, package_dir / Path(doc).name)
            print(f"✓ Copied: {doc}")
    
    # 创建启动脚本
    create_launcher_script(package_dir)
    
    # 创建说明文件
    create_readme(package_dir)
    
    # 创建压缩包
    zip_path = create_zip_package(package_dir)
    
    # 显示结果
    show_package_info(package_dir, zip_path)
    
    return True

def create_launcher_script(package_dir):
    """创建启动脚本"""
    launcher_content = '''@echo off
title Swagger API Tester
echo Starting Swagger API Tester...
echo.

REM 检查主程序是否存在
if not exist "SwaggerAPITester.exe" (
    echo ERROR: SwaggerAPITester.exe not found!
    echo Please make sure all files are in the same directory.
    pause
    exit /b 1
)

REM 启动程序
start "" "SwaggerAPITester.exe"

REM 可选：等待程序启动后关闭此窗口
timeout /t 2 /nobreak >nul
'''
    
    launcher_path = package_dir / 'Start_SwaggerAPITester.bat'
    with open(launcher_path, 'w', encoding='utf-8') as f:
        f.write(launcher_content.strip())
    
    print("✓ Created launcher script: Start_SwaggerAPITester.bat")

def create_readme(package_dir):
    """创建说明文件"""
    readme_content = '''# Swagger API Tester - 便携版

## 快速开始

### 方法 1: 直接运行
双击 `SwaggerAPITester.exe` 启动程序

### 方法 2: 使用启动脚本
双击 `Start_SwaggerAPITester.bat` 启动程序

## 文件说明

- `SwaggerAPITester.exe` - 主程序（便携式单文件）
- `Start_SwaggerAPITester.bat` - 启动脚本
- `config/` - 配置文件目录
- `templates/` - 模板文件目录
- `assets/` - 资源文件目录
- `README.md` - 项目说明
- `docs/` - 详细文档

## 系统要求

- Windows 10/11 (64位)
- 无需安装 Python 或其他依赖

## 便携性

此版本为完全便携式：
- 可以复制到任意位置运行
- 可以在 USB 驱动器上运行
- 无需安装，解压即用

## 配置文件

程序会在以下位置查找配置文件：
1. 程序同目录下的 `config/` 文件夹
2. 用户文档目录（如果程序目录只读）

## 故障排除

### 程序无法启动
1. 确保是 64 位 Windows 系统
2. 检查是否被杀毒软件拦截
3. 尝试以管理员身份运行

### 配置丢失
1. 检查 `config/` 目录是否存在
2. 确保程序有写入权限

## 技术支持

如有问题，请访问项目主页获取帮助。

---
版本: 1.0.0
构建时间: ''' + str(__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    readme_path = package_dir / 'PORTABLE_README.txt'
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content.strip())
    
    print("✓ Created portable README: PORTABLE_README.txt")

def create_zip_package(package_dir):
    """创建压缩包"""
    zip_path = Path('dist/SwaggerAPITester-Portable.zip')
    
    print(f"Creating zip package: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in package_dir.rglob('*'):
            if file_path.is_file():
                # 计算相对路径
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)
    
    print("✓ Created zip package")
    return zip_path

def show_package_info(package_dir, zip_path):
    """显示包信息"""
    print("\n" + "="*60)
    print("PORTABLE PACKAGE CREATED")
    print("="*60)
    
    # 计算目录大小
    total_size = 0
    file_count = 0
    for file_path in package_dir.rglob('*'):
        if file_path.is_file():
            total_size += file_path.stat().st_size
            file_count += 1
    
    total_size_mb = total_size / (1024 * 1024)
    
    print(f"Package Directory: {package_dir}")
    print(f"Files: {file_count}")
    print(f"Total Size: {total_size_mb:.1f} MB")
    
    if zip_path.exists():
        zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"\nZip Package: {zip_path}")
        print(f"Compressed Size: {zip_size_mb:.1f} MB")
        print(f"Compression Ratio: {(1 - zip_size_mb/total_size_mb)*100:.1f}%")
    
    print("\n" + "="*60)
    print("USAGE INSTRUCTIONS")
    print("="*60)
    print("1. Extract the zip file to any location")
    print("2. Double-click 'SwaggerAPITester.exe' to run")
    print("3. Or use 'Start_SwaggerAPITester.bat' for guided startup")
    print("\nThe package is fully portable and self-contained!")

def main():
    """主函数"""
    # 检查当前目录
    if not os.path.exists('main.py'):
        print("ERROR: Please run this script from the project root directory")
        return False
    
    success = create_portable_package()
    
    if success:
        print("\n✓ Portable package created successfully!")
    else:
        print("\n✗ Failed to create portable package")
    
    return success

if __name__ == '__main__':
    main()
