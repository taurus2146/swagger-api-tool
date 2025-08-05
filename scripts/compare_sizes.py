#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文件大小比较工具
比较不同版本的可执行文件大小
"""

import os
from pathlib import Path

def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def compare_file_sizes():
    """比较文件大小"""
    print("文件大小比较")
    print("=" * 60)
    
    files_to_check = [
        ('dist/SwaggerAPITester.exe', '标准单文件版本'),
        ('dist/SwaggerAPITester-Lite.exe', '轻量级版本'),
        ('dist/SwaggerAPITester-Portable.zip', '便携式安装包'),
    ]
    
    sizes = []
    
    for file_path, description in files_to_check:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            sizes.append((description, size))
            print(f"{description:25} {format_size(size):>12}")
        else:
            print(f"{description:25} {'不存在':>12}")
    
    if len(sizes) >= 2:
        print("\n" + "=" * 60)
        print("大小对比分析")
        print("=" * 60)
        
        # 找到最大和最小的文件
        sizes.sort(key=lambda x: x[1])
        smallest = sizes[0]
        largest = sizes[-1]
        
        print(f"最小文件: {smallest[0]} - {format_size(smallest[1])}")
        print(f"最大文件: {largest[0]} - {format_size(largest[1])}")
        
        if len(sizes) >= 2:
            reduction = largest[1] - smallest[1]
            reduction_percent = (reduction / largest[1]) * 100
            print(f"大小减少: {format_size(reduction)} ({reduction_percent:.1f}%)")
    
    # 检查目录版本
    dir_version = Path('dist/SwaggerAPITester')
    if dir_version.exists():
        print(f"\n目录版本分析:")
        print("=" * 30)
        
        total_size = 0
        file_count = 0
        
        for file_path in dir_version.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1
        
        print(f"目录版本总大小: {format_size(total_size)}")
        print(f"文件数量: {file_count}")
        
        # 与单文件版本比较
        for desc, size in sizes:
            if '单文件' in desc:
                overhead = size - total_size
                overhead_percent = (overhead / total_size) * 100
                print(f"单文件版本开销: {format_size(overhead)} ({overhead_percent:.1f}%)")
                break

def analyze_optimization():
    """分析优化效果"""
    print("\n" + "=" * 60)
    print("优化效果分析")
    print("=" * 60)
    
    standard_path = 'dist/SwaggerAPITester.exe'
    lite_path = 'dist/SwaggerAPITester-Lite.exe'
    
    if os.path.exists(standard_path) and os.path.exists(lite_path):
        standard_size = os.path.getsize(standard_path)
        lite_size = os.path.getsize(lite_path)
        
        reduction = standard_size - lite_size
        reduction_percent = (reduction / standard_size) * 100
        
        print(f"标准版本: {format_size(standard_size)}")
        print(f"轻量版本: {format_size(lite_size)}")
        print(f"减少大小: {format_size(reduction)}")
        print(f"减少比例: {reduction_percent:.1f}%")
        
        # 分析优化策略效果
        print(f"\n优化策略效果:")
        print(f"- 移除大型依赖库 (pandas, numpy等)")
        print(f"- 精简 PyQt5 模块")
        print(f"- 启用更激进的压缩")
        print(f"- 排除测试和开发工具")
        
        if reduction_percent > 50:
            print(f"\n✓ 优化效果显著！减少了超过50%的文件大小")
        elif reduction_percent > 30:
            print(f"\n✓ 优化效果良好！减少了{reduction_percent:.1f}%的文件大小")
        elif reduction_percent > 10:
            print(f"\n✓ 优化有效果，减少了{reduction_percent:.1f}%的文件大小")
        else:
            print(f"\n⚠ 优化效果有限，仅减少了{reduction_percent:.1f}%的文件大小")
    else:
        print("无法比较：缺少标准版本或轻量版本文件")

def main():
    """主函数"""
    compare_file_sizes()
    analyze_optimization()
    
    print("\n" + "=" * 60)
    print("建议")
    print("=" * 60)
    print("• 轻量版本适合：快速分发、网络传输、存储空间有限的场景")
    print("• 标准版本适合：需要完整功能的场景")
    print("• 便携包适合：专业分发、包含文档和说明的场景")

if __name__ == '__main__':
    main()
