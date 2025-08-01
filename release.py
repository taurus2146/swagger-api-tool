#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
版本发布脚本
自动化版本标签创建和发布流程
"""

import os
import sys
import subprocess
import re
from datetime import datetime

def get_current_version():
    """获取当前版本号"""
    try:
        result = subprocess.run(['git', 'describe', '--tags', '--abbrev=0'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return "v0.0.0"

def validate_version(version):
    """验证版本号格式"""
    pattern = r'^v\d+\.\d+\.\d+$'
    return re.match(pattern, version) is not None

def create_release_notes(version):
    """创建发布说明"""
    template_path = "release_notes_template.md"
    if not os.path.exists(template_path):
        return None
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换版本号和日期
    content = content.replace('{version}', version)
    content = content.replace('{date}', datetime.now().strftime('%Y-%m-%d'))
    
    # 创建发布说明文件
    notes_path = f"release_notes_{version}.md"
    with open(notes_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return notes_path

def main():
    """主函数"""
    print("🚀 Swagger API测试工具 - 版本发布脚本")
    print("=" * 50)
    
    # 检查Git状态
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            print("❌ 工作目录有未提交的更改，请先提交所有更改")
            return 1
    except:
        print("❌ 无法检查Git状态，请确保在Git仓库中运行")
        return 1
    
    # 获取当前版本
    current_version = get_current_version()
    print(f"当前版本: {current_version}")
    
    # 输入新版本号
    while True:
        new_version = input(f"请输入新版本号 (格式: v1.0.0): ").strip()
        if validate_version(new_version):
            break
        print("❌ 版本号格式错误，请使用 v1.0.0 格式")
    
    # 确认发布
    print(f"\n准备发布版本: {new_version}")
    print("这将会:")
    print("1. 创建Git标签")
    print("2. 推送到远程仓库")
    print("3. 触发GitHub Actions自动构建")
    print("4. 自动创建Release")
    
    confirm = input("\n确认发布? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 发布已取消")
        return 0
    
    try:
        # 创建标签
        print(f"\n📝 创建标签 {new_version}...")
        subprocess.run(['git', 'tag', '-a', new_version, '-m', f'Release {new_version}'], 
                      check=True)
        
        # 推送标签
        print(f"📤 推送标签到远程仓库...")
        subprocess.run(['git', 'push', 'origin', new_version], check=True)
        
        # 创建发布说明
        notes_path = create_release_notes(new_version)
        if notes_path:
            print(f"📄 发布说明已创建: {notes_path}")
            print("请编辑发布说明文件，然后在GitHub Release页面使用")
        
        print(f"\n✅ 版本 {new_version} 发布成功！")
        print("🔄 GitHub Actions 正在自动构建...")
        print("📦 构建完成后，可执行文件将自动发布到 Releases 页面")
        print(f"🌐 查看构建状态: https://github.com/your-username/your-repo/actions")
        
        return 0
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 发布失败: {e}")
        return 1
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())