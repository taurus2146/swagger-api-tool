#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成应用图标
将SVG转换为ICO和PNG格式
"""

import os
import sys

try:
    from PIL import Image
    import cairosvg
except ImportError:
    print("需要安装依赖：pip install Pillow cairosvg")
    sys.exit(1)

def generate_icons():
    """生成各种格式的图标"""
    
    # 确保assets目录存在
    if not os.path.exists('assets'):
        os.makedirs('assets')
    
    svg_path = 'assets/app_icon.svg'
    
    # 检查SVG文件是否存在
    if not os.path.exists(svg_path):
        print(f"错误：找不到 {svg_path}")
        return
    
    # 生成不同尺寸的PNG
    sizes = [16, 32, 48, 64, 128, 256]
    png_files = []
    
    for size in sizes:
        png_path = f'assets/icon_{size}.png'
        print(f"生成 {size}x{size} PNG...")
        
        # 将SVG转换为PNG
        cairosvg.svg2png(
            url=svg_path,
            write_to=png_path,
            output_width=size,
            output_height=size
        )
        png_files.append(png_path)
    
    # 创建ICO文件（包含多个尺寸）
    ico_path = 'assets/app_icon.ico'
    print("生成ICO文件...")
    
    # 打开所有PNG文件
    images = []
    for png_path in png_files:
        img = Image.open(png_path)
        images.append(img)
    
    # 保存为ICO
    images[0].save(
        ico_path, 
        format='ICO', 
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        append_images=images[1:]
    )
    
    print(f"图标生成完成！ICO文件保存在: {ico_path}")
    
    # 生成一个主PNG图标（用于显示）
    main_png_path = 'assets/app_icon.png'
    cairosvg.svg2png(
        url=svg_path,
        write_to=main_png_path,
        output_width=256,
        output_height=256
    )
    
    # 清理临时PNG文件（可选）
    # for png_path in png_files:
    #     os.remove(png_path)

if __name__ == '__main__':
    generate_icons()
