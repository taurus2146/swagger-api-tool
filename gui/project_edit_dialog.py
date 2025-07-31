#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
项目编辑对话框
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
    QTextEdit, QPushButton, QDialogButtonBox, QRadioButton, 
    QFileDialog, QGroupBox, QHBoxLayout
)
from PyQt5.QtCore import pyqtSignal, Qt

from core.project_models import Project, SwaggerSource


class ProjectEditDialog(QDialog):
    """用于新建和编辑项目的对话框"""
    project_saved = pyqtSignal(Project)

    def __init__(self, project: Project = None, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("编辑项目" if project else "新建项目")
        
        # 设置对话框尺寸，让元素更宽松舒适
        self.resize(620, 480)
        # 设置最小尺寸，确保内容能够完整显示
        self.setMinimumSize(580, 450)
        
        self._build_ui()
        if project:
            self._load_project_data()

    def _build_ui(self):
        """构建UI"""
        layout = QVBoxLayout(self)
        # 设置更宽松的布局边距和间距
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        # 项目基本信息组
        basic_group = QGroupBox("项目信息")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(12)
        basic_layout.setVerticalSpacing(15)

        # 项目信息
        self.name_input = QLineEdit()
        self.name_input.setMinimumHeight(28)
        basic_layout.addRow("项目名称:", self.name_input)
        
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(85)
        self.description_input.setMinimumHeight(65)
        # 设置文本框的显示属性，确保文本不会超出边界
        self.description_input.setLineWrapMode(QTextEdit.WidgetWidth)  # 按组件宽度折行
        self.description_input.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.description_input.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 禁用水平滚动条
        self.description_input.setPlaceholderText("请输入项目描述...")  # 添加提示文本
        
        # 设置文本框样式，确保内容不会超出边界
        self.description_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px;
                background-color: white;
                font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
                font-size: 13px;
                line-height: 1.4;
            }
            QTextEdit:focus {
                border: 2px solid #4CAF50;
                outline: none;
            }
        """)
        basic_layout.addRow("项目描述:", self.description_input)
        
        layout.addWidget(basic_group)

        # Swagger来源组
        source_group = QGroupBox("Swagger文档来源")
        source_layout = QVBoxLayout(source_group)
        source_layout.setSpacing(10)
        source_layout.setContentsMargins(15, 15, 15, 15)
        
        # 单选按钮
        radio_layout = QHBoxLayout()
        self.url_radio = QRadioButton("URL地址")
        self.file_radio = QRadioButton("本地文件")
        self.url_radio.setChecked(True)
        radio_layout.addWidget(self.url_radio)
        radio_layout.addWidget(self.file_radio)
        radio_layout.addStretch()  # 添加弹性空间
        source_layout.addLayout(radio_layout)
        
        # 文档路径输入
        location_layout = QHBoxLayout()
        location_layout.setSpacing(8)
        self.location_input = QLineEdit()
        self.location_input.setMinimumHeight(28)
        self.browse_button = QPushButton("浏览")
        self.browse_button.setFixedWidth(80)
        self.browse_button.setMinimumHeight(28)
        self.browse_button.clicked.connect(self._browse_file)
        location_layout.addWidget(self.location_input)
        location_layout.addWidget(self.browse_button)
        source_layout.addLayout(location_layout)
        
        layout.addWidget(source_group)
        
        # 连接单选按钮的信号，用于控制浏览按钮的启用状态
        self.url_radio.toggled.connect(self._on_source_type_changed)
        self.file_radio.toggled.connect(self._on_source_type_changed)
        
        # 初始设置浏览按钮状态
        self._on_source_type_changed()

        # 基础URL组
        url_group = QGroupBox("基础配置")
        url_layout = QFormLayout(url_group)
        url_layout.setSpacing(12)
        url_layout.setVerticalSpacing(15)
        
        self.base_url_input = QLineEdit()
        self.base_url_input.setMinimumHeight(28)
        self.base_url_input.setPlaceholderText("例如: https://api.example.com")
        url_layout.addRow("基础URL:", self.base_url_input)
        
        layout.addWidget(url_group)

        # 按钮区域
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Save).setText("保存")
        self.button_box.button(QDialogButtonBox.Cancel).setText("取消")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)

    def _browse_file(self):
        """浏览文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择Swagger文档", "", "Swagger 文件 (*.json *.yaml *.yml)")
        if file_path:
            self.location_input.setText(file_path)
    
    def _on_source_type_changed(self):
        """处理文档来源类型变化"""
        is_file_selected = self.file_radio.isChecked()
        # 只有选择文件时，浏览按钮才能点击
        self.browse_button.setEnabled(is_file_selected)
        
        # 更新输入框的提示文本
        if is_file_selected:
            self.location_input.setPlaceholderText("请选择Swagger文档文件...")
        else:
            self.location_input.setPlaceholderText("请输入Swagger文档URL...")

    def _load_project_data(self):
        """加载项目数据到UI"""
        self.name_input.setText(self.project.name)
        self.description_input.setText(self.project.description)
        self.base_url_input.setText(self.project.base_url)
        
        if self.project.swagger_source.type == "url":
            self.url_radio.setChecked(True)
        else:
            self.file_radio.setChecked(True)
        self.location_input.setText(self.project.swagger_source.location)
        
        # 加载数据后更新浏览按钮状态
        self._on_source_type_changed()

    def accept(self):
        """保存项目"""
        source_type = "url" if self.url_radio.isChecked() else "file"
        swagger_source = SwaggerSource(type=source_type, location=self.location_input.text())

        if not self.project:
            self.project = Project.create_new(
                name=self.name_input.text(),
                description=self.description_input.toPlainText(),
                swagger_source=swagger_source,
                base_url=self.base_url_input.text()
            )
        else:
            self.project.name = self.name_input.text()
            self.project.description = self.description_input.toPlainText()
            self.project.swagger_source = swagger_source
            self.project.base_url = self.base_url_input.text()

        self.project_saved.emit(self.project)
        super().accept()
