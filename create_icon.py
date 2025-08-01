#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
创建应用图标
将PNG图标转换为ICO格式供PyInstaller使用
"""

import os
import sys

def create_icon():
    """创建ICO图标文件"""
    png_path = "assets/app_icon.png"
    ico_path = "assets/icon.ico"
    
    # 检查PNG文件是否存在
    if not os.path.exists(png_path):
        print(f"⚠️  PNG图标文件不存在: {png_path}")
        print("将跳过图标创建，使用默认图标")
        return True  # 不阻止构建过程
    
    try:
        from PIL import Image
        
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
        
    except ImportError:
        print("⚠️  Pillow库未安装，跳过图标创建")
        return True  # 不阻止构建过程
    except Exception as e:
        print(f"⚠️  创建图标失败: {e}")
        print("将跳过图标创建，使用默认图标")
        return True  # 不阻止构建过程

def create_default_icon():
    """创建一个简单的默认图标"""
    ico_path = "assets/icon.ico"
    
    # 如果已经有图标文件，就不创建了
    if os.path.exists(ico_path):
        return True
    
    try:
        from PIL import Image, ImageDraw
        
        # 创建一个简单的默认图标
        size = 256
        img = Image.new('RGBA', (size, size), (70, 130, 180, 255))  # 钢蓝色背景
        draw = ImageDraw.Draw(img)
        
        # 绘制一个简单的API图标
        margin = size // 8
        draw.rectangle([margin, margin, size-margin, size-margin], 
                      outline=(255, 255, 255, 255), width=size//32)
        
        # 绘制API文字
        try:
            # 尝试使用系统字体
            from PIL import ImageFont
            font_size = size // 8
            font = ImageFont.load_default()
            text = "API"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (size - text_width) // 2
            y = (size - text_height) // 2
            draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
        except:
            # 如果字体加载失败，绘制简单图形
            center = size // 2
            radius = size // 6
            draw.ellipse([center-radius, center-radius, center+radius, center+radius], 
                        fill=(255, 255, 255, 255))
        
        # 创建多个尺寸
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        icons = []
        
        for icon_size in sizes:
            resized = img.resize(icon_size, Image.Resampling.LANCZOS)
            icons.append(resized)
        
        # 保存为ICO文件
        os.makedirs("assets", exist_ok=True)
        icons[0].save(ico_path, format='ICO', sizes=[icon.size for icon in icons])
        print(f"✅ 默认图标创建成功: {ico_path}")
        return True
        
    except Exception as e:
        print(f"⚠️  创建默认图标失败: {e}")
        return False

if __name__ == "__main__":
    # 首先尝试使用现有的PNG图标
    success = create_icon()
    
    # 如果没有PNG图标或创建失败，创建默认图标
    if success and not os.path.exists("assets/icon.ico"):
        create_default_icon()
    
    print("图标处理完成")