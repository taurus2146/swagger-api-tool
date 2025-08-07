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
            'ocean': self._get_ocean_theme(),
            'deep_space': self._get_deep_space_theme(),
            'night_mode': self._get_night_mode_theme(),
            'forest': self._get_forest_theme(),
            'mint': self._get_mint_theme(),
            'lavender': self._get_lavender_theme(),
            'arctic': self._get_arctic_theme(),
            'rose': self._get_rose_theme()
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
            'ocean': '海洋主题',
            'deep_space': '深空主题',
            'night_mode': '夜间模式',
            'forest': '森林主题',
            'mint': '薄荷主题',
            'lavender': '薰衣草',
            'coffee': '咖啡主题',
            'arctic': '极地主题',
            'rose': '玫瑰主题'
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

    def _get_deep_space_theme(self):
        """深空主题（深色专业主题）"""
        return {
            'name': '深空主题',
            'colors': {
                'primary': '#1a1a2e',
                'primary_hover': '#16213e',
                'primary_pressed': '#0f3460',
                'secondary': '#533483',
                'secondary_hover': '#6c5ce7',
                'warning': '#fdcb6e',
                'warning_hover': '#e17055',
                'danger': '#d63031',
                'danger_hover': '#b71c1c',
                'background': '#0e0e23',
                'surface': '#16213e',
                'text': '#ddd',
                'text_secondary': '#aaa',
                'border': '#2d3748',
                'selection': '#1a1a2e'
            },
            'stylesheet': self._generate_stylesheet({
                'primary': '#1a1a2e',
                'primary_hover': '#16213e',
                'primary_pressed': '#0f3460',
                'secondary': '#533483',
                'secondary_hover': '#6c5ce7',
                'warning': '#fdcb6e',
                'warning_hover': '#e17055',
                'danger': '#d63031',
                'danger_hover': '#b71c1c',
                'background': '#0e0e23',
                'surface': '#16213e',
                'text': '#ddd',
                'text_secondary': '#aaa',
                'border': '#2d3748',
                'selection': '#1a1a2e'
            })
        }

    def _get_night_mode_theme(self):
        """夜间模式主题（护眼深色主题）"""
        return {
            'name': '夜间模式',
            'colors': {
                'primary': '#4a90e2',
                'primary_hover': '#357abd',
                'primary_pressed': '#2968a3',
                'secondary': '#5a6c7d',
                'secondary_hover': '#4a5a6b',
                'warning': '#f39c12',
                'warning_hover': '#e67e22',
                'danger': '#e74c3c',
                'danger_hover': '#c0392b',
                'background': '#1a1a1a',
                'surface': '#2d2d2d',
                'text': '#e0e0e0',
                'text_secondary': '#b0b0b0',
                'border': '#404040',
                'selection': '#4a90e2'
            },
            'stylesheet': self._generate_stylesheet({
                'primary': '#4a90e2',
                'primary_hover': '#357abd',
                'primary_pressed': '#2968a3',
                'secondary': '#5a6c7d',
                'secondary_hover': '#4a5a6b',
                'warning': '#f39c12',
                'warning_hover': '#e67e22',
                'danger': '#e74c3c',
                'danger_hover': '#c0392b',
                'background': '#1a1a1a',
                'surface': '#2d2d2d',
                'text': '#e0e0e0',
                'text_secondary': '#b0b0b0',
                'border': '#404040',
                'selection': '#4a90e2'
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



    def _get_mint_theme(self):
        """薄荷主题（清新绿色）"""
        return {
            'name': '薄荷主题',
            'colors': {
                'primary': '#00CED1',
                'primary_hover': '#20B2AA',
                'primary_pressed': '#008B8B',
                'secondary': '#7FFFD4',
                'secondary_hover': '#66CDAA',
                'warning': '#98FB98',
                'warning_hover': '#90EE90',
                'danger': '#F0E68C',
                'danger_hover': '#DAA520',
                'background': '#F0FFFF',
                'surface': '#E0FFFF',
                'text': '#006666',
                'text_secondary': '#008080',
                'border': '#AFEEEE',
                'selection': '#B0E0E6'
            },
            'stylesheet': self._generate_stylesheet({
                'primary': '#00CED1',
                'primary_hover': '#20B2AA',
                'primary_pressed': '#008B8B',
                'secondary': '#7FFFD4',
                'secondary_hover': '#66CDAA',
                'warning': '#98FB98',
                'warning_hover': '#90EE90',
                'danger': '#F0E68C',
                'danger_hover': '#DAA520',
                'background': '#F0FFFF',
                'surface': '#E0FFFF',
                'text': '#006666',
                'text_secondary': '#008080',
                'border': '#AFEEEE',
                'selection': '#B0E0E6'
            })
        }

    def _get_lavender_theme(self):
        """薰衣草主题（淡紫色）"""
        return {
            'name': '薰衣草主题',
            'colors': {
                'primary': '#9370DB',
                'primary_hover': '#8A2BE2',
                'primary_pressed': '#7B68EE',
                'secondary': '#DDA0DD',
                'secondary_hover': '#DA70D6',
                'warning': '#D8BFD8',
                'warning_hover': '#DDA0DD',
                'danger': '#BA55D3',
                'danger_hover': '#9932CC',
                'background': '#F8F8FF',
                'surface': '#F0F8FF',
                'text': '#4B0082',
                'text_secondary': '#663399',
                'border': '#E6E6FA',
                'selection': '#DDA0DD'
            },
            'stylesheet': self._generate_stylesheet({
                'primary': '#9370DB',
                'primary_hover': '#8A2BE2',
                'primary_pressed': '#7B68EE',
                'secondary': '#DDA0DD',
                'secondary_hover': '#DA70D6',
                'warning': '#D8BFD8',
                'warning_hover': '#DDA0DD',
                'danger': '#BA55D3',
                'danger_hover': '#9932CC',
                'background': '#F8F8FF',
                'surface': '#F0F8FF',
                'text': '#4B0082',
                'text_secondary': '#663399',
                'border': '#E6E6FA',
                'selection': '#DDA0DD'
            })
        }



    def _get_arctic_theme(self):
        """极地主题（冰蓝色）"""
        return {
            'name': '极地主题',
            'colors': {
                'primary': '#4169E1',
                'primary_hover': '#0000FF',
                'primary_pressed': '#0000CD',
                'secondary': '#87CEEB',
                'secondary_hover': '#87CEFA',
                'warning': '#ADD8E6',
                'warning_hover': '#B0C4DE',
                'danger': '#6495ED',
                'danger_hover': '#4682B4',
                'background': '#F0F8FF',
                'surface': '#E6F3FF',
                'text': '#191970',
                'text_secondary': '#4682B4',
                'border': '#B0E0E6',
                'selection': '#E0F6FF'
            },
            'stylesheet': self._generate_stylesheet({
                'primary': '#4169E1',
                'primary_hover': '#0000FF',
                'primary_pressed': '#0000CD',
                'secondary': '#87CEEB',
                'secondary_hover': '#87CEFA',
                'warning': '#ADD8E6',
                'warning_hover': '#B0C4DE',
                'danger': '#6495ED',
                'danger_hover': '#4682B4',
                'background': '#F0F8FF',
                'surface': '#E6F3FF',
                'text': '#191970',
                'text_secondary': '#4682B4',
                'border': '#B0E0E6',
                'selection': '#E0F6FF'
            })
        }

    def _get_rose_theme(self):
        """玫瑰主题（玫瑰红色）"""
        return {
            'name': '玫瑰主题',
            'colors': {
                'primary': '#C21807',
                'primary_hover': '#DC143C',
                'primary_pressed': '#B22222',
                'secondary': '#FFB6C1',
                'secondary_hover': '#FFC0CB',
                'warning': '#FF69B4',
                'warning_hover': '#FF1493',
                'danger': '#8B0000',
                'danger_hover': '#800000',
                'background': '#FFF5F5',
                'surface': '#FFEBEE',
                'text': '#8B0000',
                'text_secondary': '#CD5C5C',
                'border': '#FFB6C1',
                'selection': '#FFCDD2'
            },
            'stylesheet': self._generate_stylesheet({
                'primary': '#C21807',
                'primary_hover': '#DC143C',
                'primary_pressed': '#B22222',
                'secondary': '#FFB6C1',
                'secondary_hover': '#FFC0CB',
                'warning': '#FF69B4',
                'warning_hover': '#FF1493',
                'danger': '#8B0000',
                'danger_hover': '#800000',
                'background': '#FFF5F5',
                'surface': '#FFEBEE',
                'text': '#8B0000',
                'text_secondary': '#CD5C5C',
                'border': '#FFB6C1',
                'selection': '#FFCDD2'
            })
        }


# 全局主题管理器实例
theme_manager = ThemeManager()
