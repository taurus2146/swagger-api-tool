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

# 设置输出编码，避免Windows下的Unicode错误
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

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
    print("Swagger API Tester - Release Script")
    print("=" * 50)
    
    # 检查Git状态
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            print("ERROR: Working directory has uncommitted changes, please commit all changes first")
            return 1
    except:
        print("ERROR: Cannot check Git status, please ensure running in a Git repository")
        return 1
    
    # 获取当前版本
    current_version = get_current_version()
    print(f"Current version: {current_version}")
    
    # 输入新版本号
    while True:
        new_version = input(f"Enter new version number (format: v1.0.0): ").strip()
        if validate_version(new_version):
            break
        print("ERROR: Invalid version format, please use v1.0.0 format")
    
    # 确认发布
    print(f"\nPreparing to release version: {new_version}")
    print("This will:")
    print("1. Create Git tag")
    print("2. Push to remote repository")
    print("3. Trigger GitHub Actions automatic build")
    print("4. Automatically create Release")
    
    confirm = input("\nConfirm release? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Release cancelled")
        return 0
    
    try:
        # 创建标签
        print(f"\nCreating tag {new_version}...")
        subprocess.run(['git', 'tag', '-a', new_version, '-m', f'Release {new_version}'], 
                      check=True)
        
        # 推送标签
        print(f"Pushing tag to remote repository...")
        subprocess.run(['git', 'push', 'origin', new_version], check=True)
        
        # 创建发布说明
        notes_path = create_release_notes(new_version)
        if notes_path:
            print(f"Release notes created: {notes_path}")
            print("Please edit the release notes file and use it on GitHub Release page")
        
        print(f"\nSUCCESS: Version {new_version} released successfully!")
        print("GitHub Actions is building automatically...")
        print("Executable files will be automatically published to Releases page after build completion")
        print(f"View build status: https://github.com/your-username/your-repo/actions")
        
        return 0
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Release failed: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: An error occurred: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())