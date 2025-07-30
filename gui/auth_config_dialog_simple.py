#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Bearer Token认证配置对话框（简化版）
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFormLayout, QMessageBox, QCheckBox
)
from PyQt5.QtCore import Qt


class AuthConfigDialog(QDialog):
    """
    Bearer Token认证配置对话框
    """
    
    def __init__(self, auth_manager, parent=None):
        """
        初始化认证配置对话框
        
        Args:
            auth_manager: 认证管理器实例
            parent: 父窗口
        """
        super().__init__(parent)
        self.auth_manager = auth_manager
        
        self.setWindowTitle("Bearer Token 认证配置")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        """
        初始化界面
        """
        layout = QVBoxLayout(self)
        
        # 表单布局
        form_layout = QFormLayout()
        
        # Token输入框
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("输入您的Bearer Token")
        form_layout.addRow("Token:", self.token_input)
        
        # 前缀选项
        self.use_prefix_checkbox = QCheckBox("使用 'Bearer ' 前缀")
        self.use_prefix_checkbox.setChecked(True)
        self.use_prefix_checkbox.setToolTip(
            "勾选时会在请求头中添加 'Bearer ' 前缀，\n"
            "生成格式：Authorization: Bearer your-token\n"
            "取消勾选则直接使用Token，\n"
            "生成格式：Authorization: your-token"
        )
        form_layout.addRow("", self.use_prefix_checkbox)
        
        # 启用选项
        self.enabled_checkbox = QCheckBox("启用认证")
        self.enabled_checkbox.setChecked(True)
        form_layout.addRow("", self.enabled_checkbox)
        
        layout.addLayout(form_layout)
        
        # 预览区域
        preview_label = QLabel("请求头预览：")
        layout.addWidget(preview_label)
        
        self.preview_text = QLineEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setStyleSheet("QLineEdit { background-color: #f0f0f0; }")
        layout.addWidget(self.preview_text)
        
        # 连接信号以更新预览
        self.token_input.textChanged.connect(self.update_preview)
        self.use_prefix_checkbox.stateChanged.connect(self.update_preview)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_button)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addStretch()
        layout.addLayout(button_layout)
        
    def load_config(self):
        """
        加载现有配置
        """
        config = self.auth_manager.get_auth_config('bearer')
        if config:
            self.token_input.setText(config.get('token', ''))
            self.use_prefix_checkbox.setChecked(config.get('use_prefix', True))
            self.enabled_checkbox.setChecked(config.get('enabled', True))
            
        self.update_preview()
        
    def update_preview(self):
        """
        更新请求头预览
        """
        token = self.token_input.text().strip()
        use_prefix = self.use_prefix_checkbox.isChecked()
        
        if token:
            if use_prefix:
                preview = f"Authorization: Bearer {token}"
            else:
                preview = f"Authorization: {token}"
        else:
            preview = "Authorization: <空>"
            
        self.preview_text.setText(preview)
        
    def save_config(self):
        """
        保存配置
        """
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Token")
            return
            
        config = {
            'token': token,
            'use_prefix': self.use_prefix_checkbox.isChecked(),
            'enabled': self.enabled_checkbox.isChecked()
        }
        
        self.auth_manager.set_auth_config('bearer', config)
        
        QMessageBox.information(self, "成功", "认证配置已保存")
        self.accept()
