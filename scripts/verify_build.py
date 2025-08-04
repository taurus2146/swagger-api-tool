#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
构建验证脚本
验证打包后的应用程序是否包含所有必要的数据库组件
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

def check_file_exists(file_path, description):
    """检查文件是否存在"""
    if os.path.exists(file_path):
        print(f"✓ {description}: {file_path}")
        return True
    else:
        print(f"✗ {description}: {file_path} (不存在)")
        return False

def check_directory_exists(dir_path, description):
    """检查目录是否存在"""
    if os.path.exists(dir_path) and os.path.isdir(dir_path):
        print(f"✓ {description}: {dir_path}")
        return True
    else:
        print(f"✗ {description}: {dir_path} (不存在)")
        return False

def check_python_modules(executable_path):
    """检查Python模块是否可用"""
    print("\n检查Python模块...")
    
    required_modules = [
        'sqlite3',
        'threading',
        'json',
        'hashlib',
        'base64',
        'datetime',
        'os',
        'sys',
        'logging',
        'pathlib'
    ]
    
    optional_modules = [
        'psutil',
        'chardet',
        'tqdm',
        'bcrypt',
        'keyring',
        'cryptography'
    ]
    
    all_passed = True
    
    for module in required_modules:
        try:
            result = subprocess.run([
                executable_path, '-c', f'import {module}; print("OK")'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and 'OK' in result.stdout:
                print(f"✓ 必需模块 {module}")
            else:
                print(f"✗ 必需模块 {module} (导入失败)")
                all_passed = False
        except Exception as e:
            print(f"✗ 必需模块 {module} (检查失败: {e})")
            all_passed = False
    
    for module in optional_modules:
        try:
            result = subprocess.run([
                executable_path, '-c', f'import {module}; print("OK")'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and 'OK' in result.stdout:
                print(f"✓ 可选模块 {module}")
            else:
                print(f"⚠ 可选模块 {module} (不可用)")
        except Exception as e:
            print(f"⚠ 可选模块 {module} (检查失败: {e})")
    
    return all_passed

def test_database_functionality(executable_path):
    """测试数据库功能"""
    print("\n测试数据库功能...")
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        test_db_path = os.path.join(temp_dir, 'test.db')
        
        # 测试数据库创建
        test_script = f"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from core.database_manager import DatabaseManager
    
    # 创建数据库
    db_manager = DatabaseManager('{test_db_path}')
    
    # 测试连接
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1
    
    db_manager.close()
    print("DATABASE_TEST_PASSED")
    
except Exception as e:
    print(f"DATABASE_TEST_FAILED: {{e}}")
    sys.exit(1)
"""
        
        # 写入测试脚本
        test_script_path = os.path.join(temp_dir, 'test_db.py')
        with open(test_script_path, 'w', encoding='utf-8') as f:
            f.write(test_script)
        
        try:
            result = subprocess.run([
                executable_path, test_script_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and 'DATABASE_TEST_PASSED' in result.stdout:
                print("✓ 数据库功能测试通过")
                return True
            else:
                print(f"✗ 数据库功能测试失败")
                print(f"  stdout: {result.stdout}")
                print(f"  stderr: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"✗ 数据库功能测试异常: {e}")
            return False

def verify_build(build_dir):
    """验证构建结果"""
    print(f"验证构建目录: {build_dir}")
    print("=" * 60)
    
    all_passed = True
    
    # 检查主要文件
    print("\n检查主要文件...")
    
    if sys.platform == 'win32':
        executable_name = 'SwaggerAPITester.exe'
    else:
        executable_name = 'SwaggerAPITester'
    
    executable_path = os.path.join(build_dir, executable_name)
    
    if not check_file_exists(executable_path, "主执行文件"):
        all_passed = False
    
    # 检查目录结构
    print("\n检查目录结构...")
    
    expected_dirs = [
        'docs',
        'scripts',
        'templates',
        'config',
        'assets'
    ]
    
    for dir_name in expected_dirs:
        dir_path = os.path.join(build_dir, dir_name)
        if not check_directory_exists(dir_path, f"{dir_name}目录"):
            # 某些目录可能是可选的
            if dir_name in ['docs', 'scripts']:
                print(f"  警告: {dir_name}目录缺失，但可能不影响核心功能")
    
    # 检查关键文件
    print("\n检查关键文件...")
    
    key_files = [
        ('scripts/init_database.py', '数据库初始化脚本'),
        ('scripts/upgrade_database.py', '数据库升级脚本'),
        ('docs/database_user_guide.md', '用户指南'),
        ('portable.txt', '便携模式标识文件')
    ]
    
    for file_path, description in key_files:
        full_path = os.path.join(build_dir, file_path)
        if not check_file_exists(full_path, description):
            if 'portable.txt' in file_path:
                print(f"  注意: {description}不存在，应用将以标准模式运行")
            else:
                print(f"  警告: {description}缺失")
    
    # 检查Python模块（如果可执行文件存在）
    if os.path.exists(executable_path):
        if not check_python_modules(executable_path):
            all_passed = False
        
        # 测试数据库功能
        if not test_database_functionality(executable_path):
            all_passed = False
    
    # 检查文件大小
    print("\n检查文件大小...")
    
    if os.path.exists(executable_path):
        file_size = os.path.getsize(executable_path)
        size_mb = file_size / (1024 * 1024)
        print(f"✓ 主执行文件大小: {size_mb:.1f} MB")
        
        if size_mb < 10:
            print("  警告: 执行文件可能过小，可能缺少依赖")
        elif size_mb > 200:
            print("  警告: 执行文件较大，可能包含不必要的依赖")
    
    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 构建验证通过！")
        return True
    else:
        print("✗ 构建验证失败！")
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='构建验证脚本')
    parser.add_argument('build_dir', help='构建输出目录')
    parser.add_argument('--verbose', action='store_true', help='显示详细信息')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.build_dir):
        print(f"错误: 构建目录不存在: {args.build_dir}")
        sys.exit(1)
    
    if not os.path.isdir(args.build_dir):
        print(f"错误: 指定路径不是目录: {args.build_dir}")
        sys.exit(1)
    
    # 执行验证
    success = verify_build(args.build_dir)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()