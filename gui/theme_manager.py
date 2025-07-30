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
            'dark': self._get_dark_theme(),
            'blue': self._get_blue_theme(),
            'purple': self._get_purple_theme(),
            'green': self._get_green_theme()
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
            'dark': '暗黑主题',
            'blue': '蓝色主题',
            'purple': '紫色主题',
            'green': '绿色主题'
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
    
    def _get_dark_theme(self):
        """暗黑主题"""
        return {
            'name': '暗黑主题',
            'colors': {
                'primary': '#bb86fc',
                'primary_hover': '#a370f7',
                'primary_pressed': '#8b5cf6',
                'secondary': '#03dac6',
                'secondary_hover': '#00bfa5',
                'warning': '#ff9800',
                'warning_hover': '#f57c00',
                'danger': '#cf6679',
                'danger_hover': '#b00020',
                'background': '#121212',
                'surface': '#1e1e1e',
                'text': '#ffffff',
                'text_secondary': '#b3b3b3',
                'border': '#333333',
                'selection': '#2d2d2d'
            },
            'stylesheet': self._generate_dark_stylesheet()
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
    
    def _generate_dark_stylesheet(self):
        """生成暗黑主题样式表"""
        return """
/* 全局样式 - 暗黑主题 */
QWidget {
    background-color: #1e1e1e;
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #ffffff;
}

/* 主窗口背景 */
QMainWindow {
    background-color: #121212;
}

/* 标签样式 */
QLabel {
    color: #b3b3b3;
    padding: 2px;
}

/* 按钮样式 */
QPushButton {
    background-color: #bb86fc;
    color: #000000;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #a370f7;
}

QPushButton:pressed {
    background-color: #8b5cf6;
}

QPushButton:disabled {
    background-color: #444444;
    color: #888888;
}

/* 特殊按钮样式 */
QPushButton#export_curl_button, QPushButton#export_postman_button {
    background-color: #03dac6;
}

QPushButton#export_curl_button:hover, QPushButton#export_postman_button:hover {
    background-color: #00bfa5;
}

QPushButton#test_button {
    background-color: #ff9800;
    color: #000000;
    min-width: 100px;
}

QPushButton#test_button:hover {
    background-color: #f57c00;
}

QPushButton#clear_history_button {
    background-color: #cf6679;
    min-width: 60px;
    padding: 4px 12px;
}

QPushButton#clear_history_button:hover {
    background-color: #b00020;
}

/* 输入框样式 */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #2d2d2d;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 6px;
    color: #ffffff;
    selection-background-color: #bb86fc;
    selection-color: #000000;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #bb86fc;
    outline: none;
}

/* 下拉框样式 */
QComboBox {
    background-color: #2d2d2d;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 6px;
    min-width: 120px;
    color: #ffffff;
}

QComboBox:hover {
    border: 1px solid #bb86fc;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 8px solid #b3b3b3;
    margin-right: 5px;
}

QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    border: 1px solid #444444;
    selection-background-color: #bb86fc;
    selection-color: #000000;
    color: #ffffff;
}

/* 标签页样式 */
QTabWidget::pane {
    background-color: #2d2d2d;
    border: 1px solid #444444;
    border-radius: 4px;
    margin-top: -1px;
}

QTabBar::tab {
    background-color: #1e1e1e;
    color: #b3b3b3;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #2d2d2d;
    color: #bb86fc;
    font-weight: bold;
    border: 1px solid #444444;
    border-bottom: 1px solid #2d2d2d;
}

QTabBar::tab:hover:!selected {
    background-color: #333333;
    color: #ffffff;
}

/* 树形控件样式 */
QTreeWidget, QTreeView {
    background-color: #2d2d2d;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 4px;
    alternate-background-color: #333333;
    color: #ffffff;
}

QTreeWidget::item {
    padding: 4px;
    border-radius: 2px;
}

QTreeWidget::item:hover {
    background-color: #404040;
}

QTreeWidget::item:selected {
    background-color: #bb86fc;
    color: #000000;
}

QHeaderView::section {
    background-color: #1e1e1e;
    color: #b3b3b3;
    padding: 6px;
    border: none;
    border-bottom: 2px solid #444444;
    font-weight: bold;
}

/* 表格样式 */
QTableWidget {
    background-color: #2d2d2d;
    border: 1px solid #444444;
    border-radius: 4px;
    gridline-color: #444444;
    color: #ffffff;
}

QTableWidget::item {
    padding: 6px;
}

QTableWidget::item:hover {
    background-color: #404040;
}

QTableWidget::item:selected {
    background-color: #bb86fc;
    color: #000000;
}

/* 滚动条样式 */
QScrollBar:vertical {
    background-color: #1e1e1e;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #555555;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #777777;
}

QScrollBar:horizontal {
    background-color: #1e1e1e;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #555555;
    border-radius: 6px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #777777;
}

/* 分组框样式 */
QGroupBox {
    background-color: #2d2d2d;
    border: 1px solid #444444;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
    color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 8px;
    background-color: #2d2d2d;
    color: #bb86fc;
}

/* 复选框样式 */
QCheckBox {
    spacing: 8px;
    color: #ffffff;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #444444;
    border-radius: 3px;
    background-color: #2d2d2d;
}

QCheckBox::indicator:checked {
    background-color: #bb86fc;
    border-color: #bb86fc;
    image: none;
}

QCheckBox::indicator:hover {
    border-color: #bb86fc;
}

/* 进度条样式 */
QProgressBar {
    background-color: #1e1e1e;
    border: none;
    border-radius: 10px;
    height: 20px;
    text-align: center;
    color: #ffffff;
}

QProgressBar::chunk {
    background-color: #bb86fc;
    border-radius: 10px;
}

/* 状态栏样式 */
QStatusBar {
    background-color: #1e1e1e;
    border-top: 1px solid #444444;
    color: #b3b3b3;
}

/* 工具提示样式 */
QToolTip {
    background-color: #444444;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px;
    font-size: 12px;
}

/* 菜单样式 */
QMenu {
    background-color: #2d2d2d;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 4px;
    color: #ffffff;
}

QMenu::item {
    padding: 6px 24px;
    border-radius: 2px;
}

QMenu::item:selected {
    background-color: #bb86fc;
    color: #000000;
}

/* 特殊标签样式 */
QLabel#api_path {
    color: #03dac6;
    font-weight: bold;
    font-size: 14px;
}

QLabel#api_method {
    font-weight: bold;
    padding: 4px 8px;
    border-radius: 4px;
    color: white;
}

/* HTTP方法颜色 */
QLabel[method="GET"] {
    background-color: #4CAF50;
}

QLabel[method="POST"] {
    background-color: #2196F3;
}

QLabel[method="PUT"] {
    background-color: #FF9800;
}

QLabel[method="DELETE"] {
    background-color: #f44336;
}

QLabel[method="PATCH"] {
    background-color: #9C27B0;
}

/* 分割器样式 */
QSplitter::handle {
    background-color: #444444;
}

QSplitter::handle:hover {
    background-color: #bb86fc;
}

QSplitter::handle:horizontal {
    width: 4px;
}

QSplitter::handle:vertical {
    height: 4px;
}

/* 旋转框样式 */
QSpinBox, QDoubleSpinBox {
    background-color: #2d2d2d;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 4px;
    color: #ffffff;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #bb86fc;
}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #1e1e1e;
    border: none;
    width: 20px;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #bb86fc;
}

/* 列表样式 */
QListWidget {
    background-color: #2d2d2d;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 4px;
    color: #ffffff;
}

QListWidget::item {
    padding: 6px;
    border-radius: 2px;
}

QListWidget::item:hover {
    background-color: #404040;
}

QListWidget::item:selected {
    background-color: #bb86fc;
    color: #000000;
}
"""


# 全局主题管理器实例
theme_manager = ThemeManager()