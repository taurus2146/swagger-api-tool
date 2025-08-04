#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主题管理器 - 管理多套UI主题
"""

import json
import os
from PyQt5.QtCore import QSettings


class ThemeManager:
    """主题管理器"""
    
    def __init__(self):
        self.themes = {
            'default': self._get_default_theme(),
            'blue': self._get_blue_theme(),
            'purple': self._get_purple_theme(),
            'green': self._get_green_theme(),
            'sunset': self._get_sunset_theme(),
            'ocean': self._get_ocean_theme(),
            'forest': self._get_forest_theme(),
            'coral': self._get_coral_theme()
        }
        self.current_theme = 'default'
        self.settings = QSettings("swagger-api-tool", "themes")
        self._load_theme_preference()
    
    def _load_theme_preference(self):
        """加载用户的主题偏好"""
        saved_theme = self.settings.value("current_theme", "default")
        if saved_theme in self.themes:
            self.current_theme = saved_theme
    
    def save_theme_preference(self, theme_name):
        """保存用户的主题偏好"""
        self.settings.setValue("current_theme", theme_name)
        self.current_theme = theme_name
    
    def get_theme_names(self):
        """获取所有主题名称"""
        return list(self.themes.keys())
    
    def get_current_theme_name(self):
        """获取当前主题名称"""
        return self.current_theme
    
    def get_theme_display_name(self, theme_name):
        """获取主题的显示名称"""
        display_names = {
            'default': '默认主题',
            'blue': '蓝色主题',
            'purple': '紫色主题',
            'green': '绿色主题',
            'sunset': '日落主题',
            'ocean': '海洋主题',
            'forest': '森林主题',
            'coral': '珊瑚主题'
        }
        return display_names.get(theme_name, theme_name)
    
    def get_stylesheet(self, theme_name=None):
        """获取指定主题的样式表"""
        if theme_name is None:
            theme_name = self.current_theme
        
        if theme_name not in self.themes:
            theme_name = 'default'
        
        return self.themes[theme_name]['stylesheet']
    
    def get_theme_colors(self, theme_name=None):
        """获取指定主题的颜色配置"""
        if theme_name is None:
            theme_name = self.current_theme
        
        if theme_name not in self.themes:
            theme_name = 'default'
        
        return self.themes[theme_name]['colors']
    
    def is_dark_theme(self, theme_name=None):
        """判断是否为深色主题"""
        if theme_name is None:
            theme_name = self.current_theme
            
        # 深色主题列表
        dark_themes = ['dark', 'yaak']
        return theme_name in dark_themes
    
    def get_title_bar_color(self, theme_name=None):
        """获取标题栏颜色（Windows 10/11 支持）"""
        if theme_name is None:
            theme_name = self.current_theme
            
        colors = self.get_theme_colors(theme_name)
        
        # 返回标题栏的背景颜色
        if self.is_dark_theme(theme_name):
            return colors.get('background', '#121212')
        else:
            return colors.get('surface', '#f5f5f5')
    
    def _get_default_theme(self):
        """默认主题（绿色系）"""
        return {
            'name': '默认主题',
            'colors': {
                'primary': '#4CAF50',
                'primary_hover': '#45a049',
                'primary_pressed': '#3d8b40',
                'secondary': '#2196F3',
                'secondary_hover': '#1976D2',
                'warning': '#FF9800',
                'warning_hover': '#F57C00',
                'danger': '#f44336',
                'danger_hover': '#d32f2f',
                'background': '#ffffff',
                'surface': '#f5f5f5',
                'text': '#333333',
                'text_secondary': '#666666',
                'border': '#ddd',
                'selection': '#e8f5e9'
            },
            'stylesheet': self._generate_stylesheet({
                'primary': '#4CAF50',
                'primary_hover': '#45a049',
                'primary_pressed': '#3d8b40',
                'secondary': '#2196F3',
                'secondary_hover': '#1976D2',
                'warning': '#FF9800',
                'warning_hover': '#F57C00',
                'danger': '#f44336',
                'danger_hover': '#d32f2f',
                'background': '#ffffff',
                'surface': '#f5f5f5',
                'text': '#333333',
                'text_secondary': '#666666',
                'border': '#ddd',
                'selection': '#e8f5e9'
            })
        }
    
    def _get_blue_theme(self):
        """蓝色主题"""
        return {
            'name': '蓝色主题',
            'colors': {
                'primary': '#2196F3',
                'primary_hover': '#1976D2',
                'primary_pressed': '#1565C0',
                'secondary': '#03A9F4',
                'secondary_hover': '#0288D1',
                'warning': '#FF9800',
                'warning_hover': '#F57C00',
                'danger': '#f44336',
                'danger_hover': '#d32f2f',
                'background': '#ffffff',
                'surface': '#f8fbff',
                'text': '#1a1a1a',
                'text_secondary': '#555555',
                'border': '#e3f2fd',
                'selection': '#e3f2fd'
            },
            'stylesheet': self._generate_stylesheet({
                'primary': '#2196F3',
                'primary_hover': '#1976D2',
                'primary_pressed': '#1565C0',
                'secondary': '#03A9F4',
                'secondary_hover': '#0288D1',
                'warning': '#FF9800',
                'warning_hover': '#F57C00',
                'danger': '#f44336',
                'danger_hover': '#d32f2f',
                'background': '#ffffff',
                'surface': '#f8fbff',
                'text': '#1a1a1a',
                'text_secondary': '#555555',
                'border': '#e3f2fd',
                'selection': '#e3f2fd'
            })
        }
    
    def _get_purple_theme(self):
        """紫色主题"""
        return {
            'name': '紫色主题',
            'colors': {
                'primary': '#9C27B0',
                'primary_hover': '#7B1FA2',
                'primary_pressed': '#6A1B9A',
                'secondary': '#E91E63',
                'secondary_hover': '#C2185B',
                'warning': '#FF9800',
                'warning_hover': '#F57C00',
                'danger': '#f44336',
                'danger_hover': '#d32f2f',
                'background': '#ffffff',
                'surface': '#faf8ff',
                'text': '#1a1a1a',
                'text_secondary': '#555555',
                'border': '#f3e5f5',
                'selection': '#f3e5f5'
            },
            'stylesheet': self._generate_stylesheet({
                'primary': '#9C27B0',
                'primary_hover': '#7B1FA2',
                'primary_pressed': '#6A1B9A',
                'secondary': '#E91E63',
                'secondary_hover': '#C2185B',
                'warning': '#FF9800',
                'warning_hover': '#F57C00',
                'danger': '#f44336',
                'danger_hover': '#d32f2f',
                'background': '#ffffff',
                'surface': '#faf8ff',
                'text': '#1a1a1a',
                'text_secondary': '#555555',
                'border': '#f3e5f5',
                'selection': '#f3e5f5'
            })
        }
    
    def _get_green_theme(self):
        """绿色主题（深绿色系）"""
        return {
            'name': '绿色主题',
            'colors': {
                'primary': '#388E3C',
                'primary_hover': '#2E7D32',
                'primary_pressed': '#1B5E20',
                'secondary': '#00796B',
                'secondary_hover': '#00695C',
                'warning': '#F57C00',
                'warning_hover': '#E65100',
                'danger': '#D32F2F',
                'danger_hover': '#B71C1C',
                'background': '#ffffff',
                'surface': '#f8fff8',
                'text': '#1a1a1a',
                'text_secondary': '#555555',
                'border': '#e8f5e8',
                'selection': '#e8f5e8'
            },
            'stylesheet': self._generate_stylesheet({
                'primary': '#388E3C',
                'primary_hover': '#2E7D32',
                'primary_pressed': '#1B5E20',
                'secondary': '#00796B',
                'secondary_hover': '#00695C',
                'warning': '#F57C00',
                'warning_hover': '#E65100',
                'danger': '#D32F2F',
                'danger_hover': '#B71C1C',
                'background': '#ffffff',
                'surface': '#f8fff8',
                'text': '#1a1a1a',
                'text_secondary': '#555555',
                'border': '#e8f5e8',
                'selection': '#e8f5e8'
            })
        }
    

    def _get_sunset_theme(self):
        """日落主题"""
        return {
            'name': '日落主题',
            'colors': {
                'primary': '#FF4500',
                'primary_hover': '#FF6347',
                'primary_pressed': '#FF7F50',
                'secondary': '#FFD700',
                'secondary_hover': '#FFA500',
                'warning': '#FF8C00',
                'warning_hover': '#FF4500',
                'danger': '#DC143C',
                'danger_hover': '#B22222',
                'background': '#FFEDCC',
                'surface': '#FFE4B5',
                'text': '#8B4513',
                'text_secondary': '#A0522D',
                'border': '#DEB887',
                'selection': '#FFDEAD'
            },
            'stylesheet': self._generate_stylesheet({
                'primary': '#FF4500',
                'primary_hover': '#FF6347',
                'primary_pressed': '#FF7F50',
                'secondary': '#FFD700',
                'secondary_hover': '#FFA500',
                'warning': '#FF8C00',
                'warning_hover': '#FF4500',
                'danger': '#DC143C',
                'danger_hover': '#B22222',
                'background': '#FFEDCC',
                'surface': '#FFE4B5',
                'text': '#8B4513',
                'text_secondary': '#A0522D',
                'border': '#DEB887',
                'selection': '#FFDEAD'
            })
        }

    def _get_ocean_theme(self):
        """海洋主题"""
        return {
            'name': '海洋主题',
            'colors': {
                'primary': '#4682B4',
                'primary_hover': '#5F9EA0',
                'primary_pressed': '#00CED1',
                'secondary': '#20B2AA',
                'secondary_hover': '#7FFFD4',
                'warning': '#48D1CC',
                'warning_hover': '#008B8B',
                'danger': '#00BFFF',
                'danger_hover': '#1E90FF',
                'background': '#E0FFFF',
                'surface': '#AFEEEE',
                'text': '#2F4F4F',
                'text_secondary': '#696969',
                'border': '#B0E0E6',
                'selection': '#ADD8E6'
            },
            'stylesheet': self._generate_stylesheet({
                'primary': '#4682B4',
                'primary_hover': '#5F9EA0',
                'primary_pressed': '#00CED1',
                'secondary': '#20B2AA',
                'secondary_hover': '#7FFFD4',
                'warning': '#48D1CC',
                'warning_hover': '#008B8B',
                'danger': '#00BFFF',
                'danger_hover': '#1E90FF',
                'background': '#E0FFFF',
                'surface': '#AFEEEE',
                'text': '#2F4F4F',
                'text_secondary': '#696969',
                'border': '#B0E0E6',
                'selection': '#ADD8E6'
            })
        }

    def _get_forest_theme(self):
        """森林主题"""
        return {
            'name': '森林主题',
            'colors': {
                'primary': '#228B22',
                'primary_hover': '#2E8B57',
                'primary_pressed': '#006400',
                'secondary': '#556B2F',
                'secondary_hover': '#6B8E23',
                'warning': '#8B4513',
                'warning_hover': '#CD853F',
                'danger': '#8B0000',
                'danger_hover': '#B22222',
                'background': '#F0FFF0',
                'surface': '#F5FFFA',
                'text': '#008000',
                'text_secondary': '#2E8B57',
                'border': '#98FB98',
                'selection': '#90EE90'
            },
            'stylesheet': self._generate_stylesheet({
                'primary': '#228B22',
                'primary_hover': '#2E8B57',
                'primary_pressed': '#006400',
                'secondary': '#556B2F',
                'secondary_hover': '#6B8E23',
                'warning': '#8B4513',
                'warning_hover': '#CD853F',
                'danger': '#8B0000',
                'danger_hover': '#B22222',
                'background': '#F0FFF0',
                'surface': '#F5FFFA',
                'text': '#008000',
                'text_secondary': '#2E8B57',
                'border': '#98FB98',
                'selection': '#90EE90'
            })
        }


    def _get_coral_theme(self):
        """珊瑚主题"""
        return {
            'name': '珊瑚主题',
            'colors': {
                'primary': '#FF7F50',
                'primary_hover': '#FF6347',
                'primary_pressed': '#FF4500',
                'secondary': '#FF8C00',
                'secondary_hover': '#FFA07A',
                'warning': '#FF4500',
                'warning_hover': '#FF6347',
                'danger': '#B22222',
                'danger_hover': '#8B0000',
                'background': '#FFF5EE',
                'surface': '#FDF5E6',
                'text': '#8B4513',
                'text_secondary': '#A0522D',
                'border': '#FFE4C4',
                'selection': '#FFDAB9'
            },
            'stylesheet': self._generate_stylesheet({
                'primary': '#FF7F50',
                'primary_hover': '#FF6347',
                'primary_pressed': '#FF4500',
                'secondary': '#FF8C00',
                'secondary_hover': '#FFA07A',
                'warning': '#FF4500',
                'warning_hover': '#FF6347',
                'danger': '#B22222',
                'danger_hover': '#8B0000',
                'background': '#FFF5EE',
                'surface': '#FDF5E6',
                'text': '#8B4513',
                'text_secondary': '#A0522D',
                'border': '#FFE4C4',
                'selection': '#FFDAB9'
            })
        }

    
    def _generate_stylesheet(self, colors):
        """生成样式表"""
        return f"""
/* 全局样式 */
QWidget {{
    background-color: {colors['surface']};
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: {colors['text']};
}}

/* 主窗口背景 */
QMainWindow {{
    background-color: {colors['background']};
}}

/* 标签样式 */
QLabel {{
    color: {colors['text_secondary']};
    padding: 2px;
}}

/* 按钮样式 */
QPushButton {{
    background-color: {colors['primary']};
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
    min-width: 80px;
}}

QPushButton:hover {{
    background-color: {colors['primary_hover']};
}}

QPushButton:pressed {{
    background-color: {colors['primary_pressed']};
}}

QPushButton:disabled {{
    background-color: #cccccc;
    color: #666666;
}}

/* 特殊按钮样式 */
QPushButton#export_curl_button, QPushButton#export_postman_button {{
    background-color: {colors['secondary']};
}}

QPushButton#export_curl_button:hover, QPushButton#export_postman_button:hover {{
    background-color: {colors['secondary_hover']};
}}

QPushButton#test_button {{
    background-color: {colors['warning']};
    min-width: 100px;
}}

QPushButton#test_button:hover {{
    background-color: {colors['warning_hover']};
}}

QPushButton#clear_history_button {{
    background-color: {colors['danger']};
    min-width: 60px;
    padding: 4px 12px;
}}

QPushButton#clear_history_button:hover {{
    background-color: {colors['danger_hover']};
}}

/* 输入框样式 */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {colors['background']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    padding: 6px;
    selection-background-color: {colors['primary']};
    selection-color: white;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 2px solid {colors['primary']};
    outline: none;
}}

/* 下拉框样式 */
QComboBox {{
    background-color: {colors['background']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    padding: 6px;
    min-width: 120px;
}}

QComboBox:hover {{
    border: 1px solid {colors['primary']};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 8px solid {colors['text_secondary']};
    margin-right: 5px;
}}

QComboBox QAbstractItemView {{
    background-color: {colors['background']};
    border: 1px solid {colors['border']};
    selection-background-color: {colors['primary']};
    selection-color: white;
}}

/* 标签页样式 */
QTabWidget::pane {{
    background-color: {colors['background']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    margin-top: -1px;
}}

QTabBar::tab {{
    background-color: {colors['surface']};
    color: {colors['text_secondary']};
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}

QTabBar::tab:selected {{
    background-color: {colors['background']};
    color: {colors['primary']};
    font-weight: bold;
    border: 1px solid {colors['border']};
    border-bottom: 1px solid {colors['background']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {colors['selection']};
    color: {colors['text']};
}}

/* 树形控件样式 */
QTreeWidget, QTreeView {{
    background-color: {colors['background']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    padding: 4px;
    alternate-background-color: {colors['selection']};
}}

QTreeWidget::item {{
    padding: 4px;
    border-radius: 2px;
}}

QTreeWidget::item:hover {{
    background-color: {colors['selection']};
}}

QTreeWidget::item:selected {{
    background-color: {colors['primary']};
    color: white;
}}

QHeaderView::section {{
    background-color: {colors['surface']};
    color: {colors['text_secondary']};
    padding: 6px;
    border: none;
    border-bottom: 2px solid {colors['border']};
    font-weight: bold;
}}

/* 表格样式 */
QTableWidget {{
    background-color: {colors['background']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    gridline-color: {colors['border']};
}}

QTableWidget::item {{
    padding: 6px;
}}

QTableWidget::item:hover {{
    background-color: {colors['selection']};
}}

QTableWidget::item:selected {{
    background-color: {colors['primary']};
    color: white;
}}

/* 滚动条样式 */
QScrollBar:vertical {{
    background-color: {colors['surface']};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {colors['border']};
    border-radius: 6px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {colors['text_secondary']};
}}

QScrollBar:horizontal {{
    background-color: {colors['surface']};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {colors['border']};
    border-radius: 6px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {colors['text_secondary']};
}}

/* 分组框样式 */
QGroupBox {{
    background-color: {colors['background']};
    border: 1px solid {colors['border']};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 8px;
    background-color: {colors['background']};
    color: {colors['primary']};
}}

/* 复选框样式 */
QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {colors['border']};
    border-radius: 3px;
    background-color: {colors['background']};
}}

QCheckBox::indicator:checked {{
    background-color: {colors['primary']};
    border-color: {colors['primary']};
    image: none;
}}

QCheckBox::indicator:hover {{
    border-color: {colors['primary']};
}}

/* 进度条样式 */
QProgressBar {{
    background-color: {colors['surface']};
    border: none;
    border-radius: 10px;
    height: 20px;
    text-align: center;
    color: {colors['text']};
}}

QProgressBar::chunk {{
    background-color: {colors['primary']};
    border-radius: 10px;
}}

/* 状态栏样式 */
QStatusBar {{
    background-color: {colors['surface']};
    border-top: 1px solid {colors['border']};
    color: {colors['text_secondary']};
}}

/* 工具提示样式 */
QToolTip {{
    background-color: {colors['text']};
    color: {colors['background']};
    border: none;
    border-radius: 4px;
    padding: 6px;
    font-size: 12px;
}}

/* 菜单样式 */
QMenu {{
    background-color: {colors['background']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px;
    border-radius: 2px;
}}

QMenu::item:selected {{
    background-color: {colors['primary']};
    color: white;
}}

/* 特殊标签样式 */
QLabel#api_path {{
    color: {colors['secondary']};
    font-weight: bold;
    font-size: 14px;
}}

QLabel#api_method {{
    font-weight: bold;
    padding: 4px 8px;
    border-radius: 4px;
    color: white;
}}

/* HTTP方法颜色 */
QLabel[method="GET"] {{
    background-color: #4CAF50;
}}

QLabel[method="POST"] {{
    background-color: #2196F3;
}}

QLabel[method="PUT"] {{
    background-color: #FF9800;
}}

QLabel[method="DELETE"] {{
    background-color: #f44336;
}}

QLabel[method="PATCH"] {{
    background-color: #9C27B0;
}}

/* 分割器样式 */
QSplitter::handle {{
    background-color: {colors['border']};
}}

QSplitter::handle:hover {{
    background-color: {colors['primary']};
}}

QSplitter::handle:horizontal {{
    width: 4px;
}}

QSplitter::handle:vertical {{
    height: 4px;
}}

/* 旋转框样式 */
QSpinBox, QDoubleSpinBox {{
    background-color: {colors['background']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    padding: 4px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {colors['primary']};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background-color: {colors['surface']};
    border: none;
    width: 20px;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {colors['primary']};
}}

/* 列表样式 */
QListWidget {{
    background-color: {colors['background']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    padding: 4px;
}}

QListWidget::item {{
    padding: 6px;
    border-radius: 2px;
}}

QListWidget::item:hover {{
    background-color: {colors['selection']};
}}

QListWidget::item:selected {{
    background-color: {colors['primary']};
    color: white;
}}
"""


# 全局主题管理器实例
theme_manager = ThemeManager()
