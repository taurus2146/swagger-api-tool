#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主题预览对话框
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTextEdit, QLineEdit, QCheckBox, QProgressBar, QTabWidget, QWidget,
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
    QGroupBox, QSpinBox
)
from PyQt5.QtCore import Qt
from .theme_manager import theme_manager


class ThemePreviewDialog(QDialog):
    """主题预览对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("主题预览")
        self.setModal(True)
        self.resize(800, 600)
        
        self.current_preview_theme = theme_manager.get_current_theme_name()
        self._build_ui()
        self._update_preview()
    
    def _build_ui(self):
        """构建UI"""
        layout = QVBoxLayout(self)
        
        # 主题选择区域
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("选择主题:"))
        
        self.theme_combo = QComboBox()
        for theme_name in theme_manager.get_theme_names():
            display_name = theme_manager.get_theme_display_name(theme_name)
            self.theme_combo.addItem(display_name, theme_name)
        
        # 设置当前主题
        current_index = self.theme_combo.findData(self.current_preview_theme)
        if current_index >= 0:
            self.theme_combo.setCurrentIndex(current_index)
        
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        
        layout.addLayout(theme_layout)
        
        # 预览区域
        self.preview_widget = self._create_preview_widget()
        layout.addWidget(self.preview_widget)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.apply_button = QPushButton("应用主题")
        self.apply_button.clicked.connect(self._apply_theme)
        button_layout.addWidget(self.apply_button)
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def _create_preview_widget(self):
        """创建预览组件"""
        # 使用标签页来展示不同的组件
        tab_widget = QTabWidget()
        
        # 基础组件标签页
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        
        # 按钮组
        button_group = QGroupBox("按钮组件")
        button_layout = QHBoxLayout(button_group)
        
        primary_btn = QPushButton("主要按钮")
        primary_btn.setObjectName("test_button")
        button_layout.addWidget(primary_btn)
        
        secondary_btn = QPushButton("次要按钮")
        secondary_btn.setObjectName("export_curl_button")
        button_layout.addWidget(secondary_btn)
        
        danger_btn = QPushButton("危险按钮")
        danger_btn.setObjectName("clear_history_button")
        button_layout.addWidget(danger_btn)
        
        disabled_btn = QPushButton("禁用按钮")
        disabled_btn.setEnabled(False)
        button_layout.addWidget(disabled_btn)
        
        basic_layout.addWidget(button_group)
        
        # 输入组件组
        input_group = QGroupBox("输入组件")
        input_layout = QVBoxLayout(input_group)
        
        line_edit = QLineEdit()
        line_edit.setPlaceholderText("这是一个文本输入框...")
        input_layout.addWidget(line_edit)
        
        combo_box = QComboBox()
        combo_box.addItems(["选项1", "选项2", "选项3"])
        input_layout.addWidget(combo_box)
        
        spin_box = QSpinBox()
        spin_box.setRange(0, 100)
        spin_box.setValue(50)
        input_layout.addWidget(spin_box)
        
        check_box = QCheckBox("这是一个复选框")
        check_box.setChecked(True)
        input_layout.addWidget(check_box)
        
        basic_layout.addWidget(input_group)
        
        # 进度条
        progress_group = QGroupBox("进度条")
        progress_layout = QVBoxLayout(progress_group)
        
        progress_bar = QProgressBar()
        progress_bar.setValue(65)
        progress_layout.addWidget(progress_bar)
        
        basic_layout.addWidget(progress_group)
        
        tab_widget.addTab(basic_tab, "基础组件")
        
        # 数据展示标签页
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        
        # 树形控件
        tree_widget = QTreeWidget()
        tree_widget.setHeaderLabels(["API", "方法", "路径"])
        
        # 添加示例数据
        root_item = QTreeWidgetItem(tree_widget, ["用户管理", "", ""])
        QTreeWidgetItem(root_item, ["获取用户列表", "GET", "/api/users"])
        QTreeWidgetItem(root_item, ["创建用户", "POST", "/api/users"])
        QTreeWidgetItem(root_item, ["更新用户", "PUT", "/api/users/{id}"])
        QTreeWidgetItem(root_item, ["删除用户", "DELETE", "/api/users/{id}"])
        
        tree_widget.expandAll()
        data_layout.addWidget(tree_widget)
        
        # 表格控件
        table_widget = QTableWidget(3, 4)
        table_widget.setHorizontalHeaderLabels(["名称", "类型", "必需", "描述"])
        
        # 添加示例数据
        table_data = [
            ["id", "integer", "是", "用户ID"],
            ["name", "string", "是", "用户名称"],
            ["email", "string", "否", "邮箱地址"]
        ]
        
        for row, row_data in enumerate(table_data):
            for col, cell_data in enumerate(row_data):
                item = QTableWidgetItem(str(cell_data))
                table_widget.setItem(row, col, item)
        
        table_widget.resizeColumnsToContents()
        data_layout.addWidget(table_widget)
        
        tab_widget.addTab(data_tab, "数据展示")
        
        # 文本编辑标签页
        text_tab = QWidget()
        text_layout = QVBoxLayout(text_tab)
        
        text_edit = QTextEdit()
        text_edit.setPlainText("""这是一个文本编辑器的示例内容。

您可以在这里输入多行文本，
测试主题的文本显示效果。

支持的功能：
• 语法高亮
• 代码折叠
• 自动补全
• 搜索替换

这个预览可以帮助您选择最适合的主题。""")
        
        text_layout.addWidget(text_edit)
        
        tab_widget.addTab(text_tab, "文本编辑")
        
        return tab_widget
    
    def _on_theme_changed(self):
        """主题选择改变时的处理"""
        theme_name = self.theme_combo.currentData()
        if theme_name:
            self.current_preview_theme = theme_name
            self._update_preview()
    
    def _update_preview(self):
        """更新预览"""
        try:
            stylesheet = theme_manager.get_stylesheet(self.current_preview_theme)
            self.setStyleSheet(stylesheet)
        except Exception as e:
            print(f"更新预览时出错: {e}")
    
    def _apply_theme(self):
        """应用选中的主题"""
        theme_manager.save_theme_preference(self.current_preview_theme)
        
        # 通知父窗口更新主题
        if self.parent():
            self.parent()._apply_theme()
        
        self.accept()


def show_theme_preview(parent=None):
    """显示主题预览对话框"""
    dialog = ThemePreviewDialog(parent)
    return dialog.exec_()