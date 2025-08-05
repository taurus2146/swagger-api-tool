#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
本地构建脚本
提供多种打包选项：目录版、单文件版、便携版
"""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path

def clean_build_dirs():
    """清理构建目录"""
    print("Cleaning build directories...")
    for path in ['dist', 'build']:
        if os.path.exists(path):
            print(f"  Removing {path}...")
            shutil.rmtree(path)
    print("Build directories cleaned.")

def create_icon():
    """创建应用图标"""
    print("Creating application icon...")
    try:
        result = subprocess.run([sys.executable, 'create_icon.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("  Icon created successfully.")
            return True
        else:
            print(f"  Icon creation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  Icon creation error: {e}")
        return False

def build_directory_version():
    """构建目录版本"""
    print("\n" + "="*50)
    print("Building DIRECTORY version...")
    print("="*50)
    
    start_time = time.time()
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'PyInstaller',
            'build_simple.spec', '--clean'
        ], capture_output=True, text=True)
        
        build_time = time.time() - start_time
        
        if result.returncode == 0:
            print(f"SUCCESS: Directory version built in {build_time:.1f} seconds")
            
            # 检查输出
            dist_path = Path('dist/SwaggerAPITester')
            if dist_path.exists():
                exe_path = dist_path / 'SwaggerAPITester.exe'
                if exe_path.exists():
                    size_mb = exe_path.stat().st_size / (1024 * 1024)
                    print(f"  Executable: {exe_path}")
                    print(f"  Size: {size_mb:.1f} MB")
                    print(f"  Directory: {dist_path}")
                    return True
            
            print("ERROR: Build completed but executable not found")
            return False
        else:
            print(f"ERROR: Build failed")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"ERROR: Build process error: {e}")
        return False

def build_onefile_version():
    """构建单文件版本"""
    print("\n" + "="*50)
    print("Building SINGLE FILE version...")
    print("="*50)

    start_time = time.time()

    try:
        result = subprocess.run([
            sys.executable, '-m', 'PyInstaller',
            'build_onefile.spec', '--clean'
        ], capture_output=True, text=True)

        build_time = time.time() - start_time

        if result.returncode == 0:
            print(f"SUCCESS: Single file version built in {build_time:.1f} seconds")

            # 检查输出
            exe_path = Path('dist/SwaggerAPITester.exe')
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"  Executable: {exe_path}")
                print(f"  Size: {size_mb:.1f} MB")
                print(f"  Type: Single file (portable)")
                return True

            print("ERROR: Build completed but executable not found")
            return False
        else:
            print(f"ERROR: Build failed")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"ERROR: Build process error: {e}")
        return False

def build_lightweight_version():
    """构建轻量级版本"""
    print("\n" + "="*50)
    print("Building LIGHTWEIGHT version...")
    print("="*50)

    start_time = time.time()

    try:
        result = subprocess.run([
            sys.executable, '-m', 'PyInstaller',
            'build_lightweight.spec', '--clean'
        ], capture_output=True, text=True)

        build_time = time.time() - start_time

        if result.returncode == 0:
            print(f"SUCCESS: Lightweight version built in {build_time:.1f} seconds")

            # 检查输出
            exe_path = Path('dist/SwaggerAPITester-Lite.exe')
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"  Executable: {exe_path}")
                print(f"  Size: {size_mb:.1f} MB")
                print(f"  Type: Lightweight single file")
                print(f"  Features: Core functionality only")
                return True

            print("ERROR: Build completed but executable not found")
            return False
        else:
            print(f"ERROR: Build failed")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"ERROR: Build process error: {e}")
        return False

def build_fast_version():
    """构建快速启动版本"""
    print("\n" + "="*50)
    print("Building FAST STARTUP version...")
    print("="*50)

    start_time = time.time()

    try:
        result = subprocess.run([
            sys.executable, '-m', 'PyInstaller',
            'build_fast.spec', '--clean'
        ], capture_output=True, text=True)

        build_time = time.time() - start_time

        if result.returncode == 0:
            print(f"SUCCESS: Fast version built in {build_time:.1f} seconds")

            # 检查输出
            exe_path = Path('dist/SwaggerAPITester-Fast.exe')
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"  Executable: {exe_path}")
                print(f"  Size: {size_mb:.1f} MB")
                print(f"  Type: Fast startup single file")
                print(f"  Features: No compression, quick startup")
                return True

            print("ERROR: Build completed but executable not found")
            return False
        else:
            print(f"ERROR: Build failed")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"ERROR: Build process error: {e}")
        return False

def show_menu():
    """显示构建菜单"""
    print("\n" + "="*60)
    print("SwaggerAPITester Build Tool")
    print("="*60)
    print("1. Directory version (faster startup, needs full directory)")
    print("2. Single file version (portable, slower startup)")
    print("3. Lightweight version (small size, core features only)")
    print("4. Fast version (quick startup, no compression)")
    print("5. Build all versions")
    print("6. Clean build directories only")
    print("7. Exit")
    print("="*60)

def main():
    """主函数"""
    # 检查当前目录
    if not os.path.exists('main.py'):
        print("ERROR: Please run this script from the project root directory")
        return False
    
    while True:
        show_menu()
        choice = input("Select option (1-5): ").strip()
        
        if choice == '1':
            clean_build_dirs()
            create_icon()
            success = build_directory_version()
            if success:
                print("\nDirectory version ready!")
                print("Run: dist/SwaggerAPITester/SwaggerAPITester.exe")
        
        elif choice == '2':
            clean_build_dirs()
            create_icon()
            success = build_onefile_version()
            if success:
                print("\nSingle file version ready!")
                print("Run: dist/SwaggerAPITester.exe")
                print("You can copy this file anywhere and run it directly.")
        
        elif choice == '3':
            clean_build_dirs()
            create_icon()
            success = build_lightweight_version()
            if success:
                print("\nLightweight version ready!")
                print("Run: dist/SwaggerAPITester-Lite.exe")
                print("This version has reduced file size but core functionality.")

        elif choice == '4':
            clean_build_dirs()
            create_icon()
            success = build_fast_version()
            if success:
                print("\nFast version ready!")
                print("Run: dist/SwaggerAPITester-Fast.exe")
                print("This version starts quickly with no compression.")

        elif choice == '5':
            clean_build_dirs()
            create_icon()

            print("Building all versions...")
            dir_success = build_directory_version()

            # 重命名目录版本以避免冲突
            if dir_success:
                old_path = Path('dist/SwaggerAPITester')
                new_path = Path('dist/SwaggerAPITester-Directory')
                if old_path.exists():
                    old_path.rename(new_path)
                    print(f"Directory version moved to: {new_path}")

            file_success = build_onefile_version()
            lite_success = build_lightweight_version()
            fast_success = build_fast_version()

            if dir_success and file_success and lite_success and fast_success:
                print("\nAll versions built successfully!")
                print("Directory version: dist/SwaggerAPITester-Directory/")
                print("Single file version: dist/SwaggerAPITester.exe")
                print("Lightweight version: dist/SwaggerAPITester-Lite.exe")
                print("Fast version: dist/SwaggerAPITester-Fast.exe")

        elif choice == '6':
            clean_build_dirs()
            print("Build directories cleaned.")

        elif choice == '7':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please select 1-5.")
        
        input("\nPress Enter to continue...")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nBuild cancelled by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
