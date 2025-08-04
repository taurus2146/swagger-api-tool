#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyQt5 构建验证脚本
用于验证 PyInstaller 构建是否包含所有必要的 PyQt5 依赖
"""

import os
import sys
import subprocess
from pathlib import Path

def check_pyqt5_installation():
    """检查 PyQt5 是否正确安装"""
    print("Checking PyQt5 installation...")

    modules_to_check = [
        'PyQt5.QtCore',
        'PyQt5.QtWidgets',
        'PyQt5.QtGui',
        'PyQt5.QtNetwork'
    ]

    success = True
    for module in modules_to_check:
        try:
            __import__(module)
            print(f"OK {module} imported successfully")
        except ImportError as e:
            print(f"ERROR {module} import failed: {e}")
            success = False

    # 检查 sip（可选）
    try:
        import PyQt5.sip
        print("OK PyQt5.sip imported successfully")
    except ImportError:
        print("WARNING PyQt5.sip not available (normal for some versions)")

    return success

def test_build():
    """测试构建过程"""
    print("\nTesting build process...")

    try:
        # 清理之前的构建
        for path in ['dist', 'build']:
            if os.path.exists(path):
                print(f"Cleaning {path}...")
                import shutil
                shutil.rmtree(path)

        # 运行构建
        print("Running PyInstaller build...")
        result = subprocess.run([
            sys.executable, '-m', 'PyInstaller',
            'build_simple.spec', '--clean'
        ], capture_output=True, text=True, cwd=os.getcwd())

        if result.returncode == 0:
            print("OK Build successful")
            return True
        else:
            print("ERROR Build failed:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"ERROR Build process error: {e}")
        return False

def check_build_output():
    """检查构建输出"""
    print("\n检查构建输出...")

    dist_path = Path('dist/SwaggerAPITester')
    if not dist_path.exists():
        print("✗ 构建输出目录不存在")
        return False

    exe_path = dist_path / 'SwaggerAPITester.exe'
    if not exe_path.exists():
        print("✗ 可执行文件不存在")
        return False

    print("✓ 可执行文件存在")

    # 检查文件大小
    exe_size = exe_path.stat().st_size / (1024 * 1024)  # MB
    print(f"✓ 可执行文件大小: {exe_size:.1f} MB")

    # 检查 PyQt5 相关文件
    internal_path = dist_path / '_internal'
    if internal_path.exists():
        qt_files = list(internal_path.glob('*Qt*'))
        pyqt_files = list(internal_path.glob('*PyQt*'))
        sip_files = list(internal_path.glob('*sip*'))

        # 检查关键 PyQt5 模块
        required_modules = ['PyQt5', 'PyQt5-5.15', 'PyQt5_Qt5', 'PyQt5_sip']
        found_modules = []

        for module in required_modules:
            module_files = list(internal_path.glob(f'*{module}*'))
            if module_files:
                found_modules.append(module)
                print(f"✓ 找到模块: {module}")

        if len(found_modules) >= 3:  # 至少找到3个关键模块
            print(f"✓ PyQt5 模块完整性检查通过 ({len(found_modules)}/{len(required_modules)})")
        else:
            print(f"⚠ PyQt5 模块可能不完整 ({len(found_modules)}/{len(required_modules)})")

        total_files = qt_files + pyqt_files + sip_files
        if total_files:
            print(f"✓ 总共找到 {len(total_files)} 个 Qt/PyQt/sip 相关文件")

            # 显示文件详情
            print("  关键文件:")
            for f in total_files[:8]:
                print(f"    - {f.name}")
            if len(total_files) > 8:
                print(f"    ... 还有 {len(total_files) - 8} 个文件")
        else:
            print("✗ 未找到 Qt/PyQt 相关文件")
            return False
    else:
        print("✗ _internal 目录不存在")
        return False

    return True

def main():
    """主函数"""
    print("PyQt5 构建验证脚本")
    print("=" * 50)
    
    # 检查当前目录
    if not os.path.exists('build_simple.spec'):
        print("✗ 未找到 build_simple.spec 文件")
        print("请在项目根目录运行此脚本")
        return False
    
    success = True
    
    # 步骤 1: 检查 PyQt5 安装
    if not check_pyqt5_installation():
        success = False
        print("\n请先安装 PyQt5: pip install PyQt5==5.15.9")
    
    # 步骤 2: 测试构建
    if success and not test_build():
        success = False
    
    # 步骤 3: 检查构建输出
    if success and not check_build_output():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✓ 所有检查通过！PyQt5 构建配置正确。")
        print("可执行文件应该能够正常运行。")
    else:
        print("✗ 发现问题，请检查上述错误信息。")
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
