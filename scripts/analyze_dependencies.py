#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
依赖分析工具
分析当前依赖的大小和必要性，为优化提供数据支持
"""

import os
import sys
import subprocess
import importlib
from pathlib import Path

def get_package_size(package_name):
    """获取包的安装大小"""
    try:
        result = subprocess.run([
            sys.executable, '-c', 
            f"import {package_name}; import os; print(os.path.dirname({package_name}.__file__))"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            package_path = Path(result.stdout.strip())
            if package_path.exists():
                total_size = 0
                for file_path in package_path.rglob('*'):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
                return total_size / (1024 * 1024)  # MB
    except:
        pass
    return 0

def analyze_current_dependencies():
    """分析当前依赖"""
    print("分析当前依赖大小...")
    print("="*60)
    
    # 从 requirements.txt 读取依赖
    dependencies = []
    if os.path.exists('requirements.txt'):
        with open('requirements.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # 提取包名（去掉版本号）
                    package_name = line.split('==')[0].split('>=')[0].split('<=')[0]
                    dependencies.append(package_name)
    
    # 分析每个依赖的大小
    package_sizes = []
    total_size = 0
    
    for package in dependencies:
        try:
            # 尝试导入包
            importlib.import_module(package)
            size_mb = get_package_size(package)
            package_sizes.append((package, size_mb))
            total_size += size_mb
            
            if size_mb > 0:
                print(f"{package:20} {size_mb:8.1f} MB")
            else:
                print(f"{package:20} {'N/A':>8}")
        except ImportError:
            print(f"{package:20} {'未安装':>8}")
    
    print("="*60)
    print(f"{'总计':20} {total_size:8.1f} MB")
    
    # 按大小排序
    package_sizes.sort(key=lambda x: x[1], reverse=True)
    
    print("\n按大小排序（前10个）:")
    print("="*40)
    for package, size in package_sizes[:10]:
        if size > 0:
            print(f"{package:20} {size:8.1f} MB")
    
    return package_sizes, total_size

def categorize_dependencies():
    """分类依赖"""
    print("\n依赖分类分析:")
    print("="*60)
    
    # 核心依赖（必须保留）
    core_deps = {
        'PyQt5': '图形界面框架',
        'requests': 'HTTP请求',
        'PyYAML': 'YAML解析',
        'jsonschema': 'JSON验证',
        'swagger_parser': 'Swagger解析',
        'urllib3': 'HTTP底层库',
        'cryptography': '加密功能'
    }
    
    # 可选依赖（可以移除或替换）
    optional_deps = {
        'pandas': '数据分析（可移除）',
        'numpy': '数值计算（pandas依赖）',
        'openpyxl': 'Excel支持（可移除）',
        'pytest': '测试工具（可移除）',
        'coverage': '代码覆盖率（可移除）',
        'mock': '测试模拟（可移除）',
        'faker': '测试数据生成',
        'bcrypt': '密码哈希（可简化）',
        'keyring': '系统密钥环（可移除）',
        'psutil': '系统监控（可移除）',
        'tqdm': '进度条（可移除）',
        'chardet': '编码检测'
    }
    
    print("核心依赖（必须保留）:")
    for dep, desc in core_deps.items():
        size = get_package_size(dep)
        print(f"  {dep:15} {size:6.1f}MB - {desc}")
    
    print("\n可选依赖（可以优化）:")
    for dep, desc in optional_deps.items():
        size = get_package_size(dep)
        print(f"  {dep:15} {size:6.1f}MB - {desc}")
    
    return core_deps, optional_deps

def suggest_optimizations():
    """建议优化方案"""
    print("\n优化建议:")
    print("="*60)
    
    suggestions = [
        {
            'action': '移除数据分析库',
            'packages': ['pandas', 'numpy', 'openpyxl'],
            'savings': '80-100MB',
            'impact': '失去Excel导出功能'
        },
        {
            'action': '移除测试工具',
            'packages': ['pytest', 'coverage', 'mock'],
            'savings': '10-15MB',
            'impact': '无影响（运行时不需要）'
        },
        {
            'action': '简化系统集成',
            'packages': ['keyring', 'psutil'],
            'savings': '5-10MB',
            'impact': '失去系统密钥环和监控功能'
        },
        {
            'action': '优化PyQt5配置',
            'packages': ['PyQt5部分模块'],
            'savings': '20-30MB',
            'impact': '移除不需要的Qt组件'
        }
    ]
    
    total_savings = 0
    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion['action']}")
        print(f"   移除包: {', '.join(suggestion['packages'])}")
        print(f"   节省空间: {suggestion['savings']}")
        print(f"   影响: {suggestion['impact']}")
        print()
        
        # 估算节省空间
        if '80-100' in suggestion['savings']:
            total_savings += 90
        elif '20-30' in suggestion['savings']:
            total_savings += 25
        elif '10-15' in suggestion['savings']:
            total_savings += 12
        elif '5-10' in suggestion['savings']:
            total_savings += 7
    
    print(f"预计总节省空间: {total_savings}MB")
    print(f"优化后预计大小: {206 - total_savings}MB")

def main():
    """主函数"""
    print("依赖大小分析工具")
    print("="*60)
    
    # 检查当前目录
    if not os.path.exists('requirements.txt'):
        print("ERROR: requirements.txt not found")
        return False
    
    # 分析依赖大小
    package_sizes, total_size = analyze_current_dependencies()
    
    # 分类依赖
    core_deps, optional_deps = categorize_dependencies()
    
    # 建议优化
    suggest_optimizations()
    
    print("\n" + "="*60)
    print("分析完成！")
    print("建议：创建精简版requirements文件，移除大型可选依赖")
    
    return True

if __name__ == '__main__':
    main()
