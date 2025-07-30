#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
应用程序样式表定义
"""

# 现代化的样式表
MODERN_STYLE = """
/* 全局样式 */
QWidget {
    background-color: #f5f5f5;
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #333333;
}

/* 主窗口背景 */
QMainWindow {
    background-color: #ffffff;
}

/* 标签样式 */
QLabel {
    color: #555555;
    padding: 2px;
}

/* 按钮样式 */
QPushButton {
    background-color: #4CAF50;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #45a049;
}

QPushButton:pressed {
    background-color: #3d8b40;
}

QPushButton:disabled {
    background-color: #cccccc;
    color: #666666;
}

/* 特殊按钮样式 */
QPushButton#export_curl_button, QPushButton#export_postman_button {
    background-color: #2196F3;
}

QPushButton#export_curl_button:hover, QPushButton#export_postman_button:hover {
    background-color: #1976D2;
}

QPushButton#test_button {
    background-color: #FF9800;
    min-width: 100px;
}

QPushButton#test_button:hover {
    background-color: #F57C00;
}

QPushButton#clear_history_button {
    background-color: #f44336;
    min-width: 60px;
    padding: 4px 12px;
}

QPushButton#clear_history_button:hover {
    background-color: #d32f2f;
}

/* 输入框样式 */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 6px;
    selection-background-color: #4CAF50;
    selection-color: white;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #4CAF50;
    outline: none;
}

/* 下拉框样式 */
QComboBox {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 6px;
    min-width: 120px;
}

QComboBox:hover {
    border: 1px solid #4CAF50;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 8px solid #666;
    margin-right: 5px;
}

QComboBox QAbstractItemView {
    background-color: white;
    border: 1px solid #ddd;
    selection-background-color: #4CAF50;
    selection-color: white;
}

/* 标签页样式 */
QTabWidget::pane {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    margin-top: -1px;
}

QTabBar::tab {
    background-color: #e0e0e0;
    color: #666666;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: white;
    color: #4CAF50;
    font-weight: bold;
    border: 1px solid #ddd;
    border-bottom: 1px solid white;
}

QTabBar::tab:hover:!selected {
    background-color: #f0f0f0;
    color: #333333;
}

/* 树形控件样式 */
QTreeWidget, QTreeView {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 4px;
    alternate-background-color: #f9f9f9;
}

QTreeWidget::item {
    padding: 4px;
    border-radius: 2px;
}

QTreeWidget::item:hover {
    background-color: #e8f5e9;
}

QTreeWidget::item:selected {
    background-color: #4CAF50;
    color: white;
}

QHeaderView::section {
    background-color: #f5f5f5;
    color: #666666;
    padding: 6px;
    border: none;
    border-bottom: 2px solid #ddd;
    font-weight: bold;
}

/* 表格样式 */
QTableWidget {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    gridline-color: #e0e0e0;
}

QTableWidget::item {
    padding: 6px;
}

QTableWidget::item:hover {
    background-color: #e8f5e9;
}

QTableWidget::item:selected {
    background-color: #4CAF50;
    color: white;
}

/* 滚动条样式 */
QScrollBar:vertical {
    background-color: #f0f0f0;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #cccccc;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #999999;
}

QScrollBar:horizontal {
    background-color: #f0f0f0;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #cccccc;
    border-radius: 6px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #999999;
}

/* 分组框样式 */
QGroupBox {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 8px;
    background-color: white;
    color: #4CAF50;
}

/* 复选框样式 */
QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #ddd;
    border-radius: 3px;
    background-color: white;
}

QCheckBox::indicator:checked {
    background-color: #4CAF50;
    border-color: #4CAF50;
    image: none;
}


QCheckBox::indicator:hover {
    border-color: #4CAF50;
}

/* 进度条样式 */
QProgressBar {
    background-color: #e0e0e0;
    border: none;
    border-radius: 10px;
    height: 20px;
    text-align: center;
    color: #333333;
}

QProgressBar::chunk {
    background-color: #4CAF50;
    border-radius: 10px;
}

/* 状态栏样式 */
QStatusBar {
    background-color: #f5f5f5;
    border-top: 1px solid #ddd;
    color: #666666;
}

/* 工具提示样式 */
QToolTip {
    background-color: #333333;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px;
    font-size: 12px;
}

/* 菜单样式 */
QMenu {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px;
    border-radius: 2px;
}

QMenu::item:selected {
    background-color: #4CAF50;
    color: white;
}

/* 特殊标签样式 */
QLabel#api_path {
    color: #2196F3;
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
    background-color: #e0e0e0;
}

QSplitter::handle:hover {
    background-color: #4CAF50;
}

QSplitter::handle:horizontal {
    width: 4px;
}

QSplitter::handle:vertical {
    height: 4px;
}

/* 旋转框样式 */
QSpinBox, QDoubleSpinBox {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 4px;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #4CAF50;
}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #f0f0f0;
    border: none;
    width: 20px;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #4CAF50;
}

/* 列表样式 */
QListWidget {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 4px;
}

QListWidget::item {
    padding: 6px;
    border-radius: 2px;
}

QListWidget::item:hover {
    background-color: #e8f5e9;
}

QListWidget::item:selected {
    background-color: #4CAF50;
    color: white;
}

"""

# 获取样式表
def get_stylesheet():
    """
    获取应用程序样式表
    
    Returns:
        str: 样式表字符串
    """
    return MODERN_STYLE

# HTTP方法对应的颜色
HTTP_METHOD_COLORS = {
    'GET': '#4CAF50',
    'POST': '#2196F3', 
    'PUT': '#FF9800',
    'DELETE': '#f44336',
    'PATCH': '#9C27B0',
    'HEAD': '#795548',
    'OPTIONS': '#607D8B'
}

# 状态码对应的颜色
STATUS_CODE_COLORS = {
    '2xx': '#4CAF50',  # 成功 - 绿色
    '3xx': '#FF9800',  # 重定向 - 橙色
    '4xx': '#f44336',  # 客户端错误 - 红色
    '5xx': '#9C27B0'   # 服务器错误 - 紫色
}
