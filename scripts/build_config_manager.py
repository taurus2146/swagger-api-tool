#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
构建配置管理器
用于统一管理和同步 build.spec 和 build_simple.spec 的配置
"""

import os
import sys
from pathlib import Path

def compare_spec_files():
    """比较两个 spec 文件的差异"""
    print("比较 build.spec 和 build_simple.spec 配置...")
    
    build_spec = Path('build.spec')
    build_simple_spec = Path('build_simple.spec')
    
    if not build_spec.exists():
        print("✗ build.spec 不存在")
        return False
    
    if not build_simple_spec.exists():
        print("✗ build_simple.spec 不存在")
        return False
    
    # 读取文件内容
    with open(build_spec, 'r', encoding='utf-8') as f:
        build_content = f.read()
    
    with open(build_simple_spec, 'r', encoding='utf-8') as f:
        simple_content = f.read()
    
    # 检查关键配置项
    key_configs = [
        'collect_all',
        'hookspath',
        'PyQt5.QtCore',
        'PyQt5.QtWidgets',
        'PyQt5.QtGui',
        'cryptography'
    ]
    
    print("\n配置项检查:")
    for config in key_configs:
        in_build = config in build_content
        in_simple = config in simple_content
        
        if in_build and in_simple:
            print(f"✓ {config}: 两个文件都包含")
        elif in_build and not in_simple:
            print(f"⚠ {config}: 仅在 build.spec 中")
        elif not in_build and in_simple:
            print(f"⚠ {config}: 仅在 build_simple.spec 中")
        else:
            print(f"✗ {config}: 两个文件都不包含")
    
    return True

def validate_spec_syntax():
    """验证 spec 文件语法"""
    print("\n验证 spec 文件语法...")
    
    for spec_file in ['build.spec', 'build_simple.spec']:
        try:
            with open(spec_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 简单的语法检查
            if 'Analysis(' in content and 'EXE(' in content and 'COLLECT(' in content:
                print(f"✓ {spec_file}: 语法结构正确")
            else:
                print(f"✗ {spec_file}: 语法结构可能有问题")
                
        except Exception as e:
            print(f"✗ {spec_file}: 读取失败 - {e}")

def generate_build_report():
    """生成构建配置报告"""
    print("\n生成构建配置报告...")
    
    report = []
    report.append("# 构建配置报告")
    report.append(f"生成时间: {__import__('datetime').datetime.now()}")
    report.append("")
    
    # 检查依赖文件
    report.append("## 依赖文件检查")
    files_to_check = [
        'requirements.txt',
        'build.spec', 
        'build_simple.spec',
        'hooks/hook-PyQt5.py',
        'main.py'
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            report.append(f"✓ {file_path}")
        else:
            report.append(f"✗ {file_path} (缺失)")
    
    # 检查目录结构
    report.append("\n## 目录结构检查")
    dirs_to_check = ['core', 'gui', 'utils', 'assets', 'config', 'templates']
    
    for dir_path in dirs_to_check:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            report.append(f"✓ {dir_path}/")
        else:
            report.append(f"✗ {dir_path}/ (缺失)")
    
    # 保存报告
    report_content = '\n'.join(report)
    with open('build_config_report.md', 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print("✓ 报告已保存到 build_config_report.md")

def main():
    """主函数"""
    print("构建配置管理器")
    print("=" * 50)
    
    # 检查当前目录
    if not os.path.exists('build_simple.spec'):
        print("✗ 请在项目根目录运行此脚本")
        return False
    
    success = True
    
    # 比较配置文件
    if not compare_spec_files():
        success = False
    
    # 验证语法
    validate_spec_syntax()
    
    # 生成报告
    generate_build_report()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ 配置检查完成")
    else:
        print("⚠ 发现配置问题，请检查上述信息")
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
