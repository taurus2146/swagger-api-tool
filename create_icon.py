#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
创建应用图标
将PNG图标转换为ICO格式供PyInstaller使用
"""

import os
from PIL import Image

def create_icon():
    """创建ICO图标文件"""
    png_path = "assets/app_icon.png"
    ico_path = "assets/icon.ico"
    
    if not os.path.exists(png_path):
        print(f"PNG图标文件不存在: {png_path}")
        return False
    
    try:
        # 打开PNG图像
        img = Image.open(png_path)
        
        # 转换为RGBA模式（如果不是的话）
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # 创建多个尺寸的图标
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        icons = []
        
        for size in sizes:
            resized = img.resize(size, Image.Resampling.LANCZOS)
            icons.append(resized)
        
        # 保存为ICO文件
        icons[0].save(ico_path, format='ICO', sizes=[icon.size for icon in icons])
        print(f"✅ 图标创建成功: {ico_path}")
        return True
        
    except Exception as e:
        print(f"❌ 创建图标失败: {e}")
        return False

if __name__ == "__main__":
    try:
        from PIL import Image
    except ImportError:
        print("需要安装Pillow库: pip install Pillow")
        exit(1)
    
    create_icon()