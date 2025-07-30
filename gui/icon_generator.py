#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
动态生成现代化应用图标
"""

from PyQt5.QtGui import QPixmap, QPainter, QBrush, QPen, QFont, QLinearGradient, QColor, QIcon
from PyQt5.QtCore import Qt, QRect, QPointF, QRectF
from PyQt5.QtSvg import QSvgRenderer
import os


def create_modern_icon():
    """创建一个现代化的应用图标"""
    
    # 创建一个256x256的图标
    size = 256
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    
    # 绘制背景圆形（带渐变）
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0, QColor(33, 150, 243))  # 亮蓝色
    gradient.setColorAt(1, QColor(25, 118, 210))  # 深蓝色
    
    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(8, 8, size-16, size-16)
    
    # 设置画笔为白色，用于绘制内容
    painter.setPen(QPen(Qt.white, 8, Qt.SolidLine, Qt.RoundCap))
    painter.setBrush(Qt.NoBrush)
    
    # 绘制左花括号
    from PyQt5.QtGui import QPainterPath
    left_brace = QPainterPath()
    left_brace.moveTo(70, 80)
    left_brace.quadTo(50, 80, 50, 100)
    left_brace.lineTo(50, 110)
    left_brace.quadTo(50, 128, 35, 128)
    left_brace.moveTo(35, 128)
    left_brace.quadTo(50, 128, 50, 146)
    left_brace.lineTo(50, 156)
    left_brace.quadTo(50, 176, 70, 176)
    painter.drawPath(left_brace)
    
    # 绘制右花括号
    right_brace = QPainterPath()
    right_brace.moveTo(186, 80)
    right_brace.quadTo(206, 80, 206, 100)
    right_brace.lineTo(206, 110)
    right_brace.quadTo(206, 128, 221, 128)
    right_brace.moveTo(221, 128)
    right_brace.quadTo(206, 128, 206, 146)
    right_brace.lineTo(206, 156)
    right_brace.quadTo(206, 176, 186, 176)
    painter.drawPath(right_brace)
    
    # 绘制 API 文字
    font = QFont("Arial", 32, QFont.Bold)
    painter.setFont(font)
    painter.setPen(Qt.white)
    painter.drawText(QRect(0, 100, size, 50), Qt.AlignCenter, "API")
    
    # 绘制底部的测试图标（勾号）
    painter.setBrush(QBrush(Qt.white))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(size//2 - 18, 190 - 18, 36, 36)
    
    # 绘制勾号
    painter.setPen(QPen(QColor(33, 150, 243), 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(Qt.NoBrush)
    check_path = QPainterPath()
    check_path.moveTo(size//2 - 8, 190)
    check_path.lineTo(size//2 - 3, 195)
    check_path.lineTo(size//2 + 8, 184)
    painter.drawPath(check_path)
    
    # 绘制装饰性小圆点
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(255, 255, 255, 150)))
    painter.drawEllipse(80-4, 60-4, 8, 8)
    painter.drawEllipse(176-4, 60-4, 8, 8)
    painter.drawEllipse(80-4, 196-4, 8, 8)
    painter.drawEllipse(176-4, 196-4, 8, 8)
    
    painter.end()
    
    return pixmap


def get_app_icon():
    """获取应用图标"""
    # 检查是否已有保存的图标
    icon_path = os.path.join("assets", "app_icon.png")
    
    if os.path.exists(icon_path):
        return QIcon(icon_path)
    
    # 如果没有，动态生成
    pixmap = create_modern_icon()
    
    # 保存图标
    os.makedirs("assets", exist_ok=True)
    pixmap.save(icon_path, "PNG")
    
    # 创建多尺寸图标
    icon = QIcon()
    icon.addPixmap(pixmap)
    
    # 添加其他尺寸
    for size in [16, 32, 48, 64, 128]:
        scaled = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon.addPixmap(scaled)
    
    return icon
