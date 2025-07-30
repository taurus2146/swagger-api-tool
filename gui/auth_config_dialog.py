#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
认证配置对话框
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QTabWidget, QWidget, QFormLayout,
    QMessageBox, QGroupBox, QCheckBox, QGridLayout
)
from PyQt5.QtCore import Qt

from core.auth_manager import AuthManager


class AuthConfigDialog(QDialog):
    """
    认证配置对话框，用于配置API认证信息
    """
    
    def __init__(self, auth_manager=None, parent=None):
        """
        初始化认证配置对话框
        
        Args:
            auth_manager (AuthManager, optional): 认证管理器实例
            parent: 父窗口
        """
        super().__init__(parent)
        self.auth_manager = auth_manager or AuthManager()
        
        self.setWindowTitle("认证配置")
        self.setMinimumWidth(500)
        self.init_ui()
        
        # 加载现有配置
        self.load_config()
        
    def init_ui(self):
        """
        初始化界面
        """
        layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # Bearer Token认证标签页
        self.bearer_widget = QWidget()
        self.setup_bearer_tab()
        self.tab_widget.addTab(self.bearer_widget, "Bearer Token")
        
        # Basic认证标签页
        self.basic_widget = QWidget()
        self.setup_basic_tab()
        self.tab_widget.addTab(self.basic_widget, "Basic认证")
        
        # API Key认证标签页
        self.api_key_widget = QWidget()
        self.setup_api_key_tab()
        self.tab_widget.addTab(self.api_key_widget, "API Key")
        
        layout.addWidget(self.tab_widget)
        
        # 底部按钮区域
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("测试认证")
        self.test_button.clicked.connect(self.test_auth)
        button_layout.addWidget(self.test_button)
        
        self.save_button = QPushButton("保存配置")
        self.save_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_button)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
    def setup_bearer_tab(self):
        """
        设置Bearer Token标签页
        """
        layout = QVBoxLayout(self.bearer_widget)
        
        # 创建表单布局
        form_layout = QFormLayout()
        
        # 添加输入控件
        self.bearer_login_group = QGroupBox("自动获取Token")
        self.bearer_login_group.setCheckable(True)
        self.bearer_login_group.setChecked(False)
        bearer_login_layout = QFormLayout(self.bearer_login_group)
        
        self.bearer_login_url = QLineEdit()
        bearer_login_layout.addRow("登录URL:", self.bearer_login_url)
        
        self.bearer_login_method = QComboBox()
        self.bearer_login_method.addItems(["POST", "GET"])
        bearer_login_layout.addRow("请求方法:", self.bearer_login_method)
        
        self.bearer_username_field = QLineEdit()
        bearer_login_layout.addRow("用户名字段:", self.bearer_username_field)
        
        self.bearer_username = QLineEdit()
        bearer_login_layout.addRow("用户名:", self.bearer_username)
        
        self.bearer_password_field = QLineEdit()
        bearer_login_layout.addRow("密码字段:", self.bearer_password_field)
        
        self.bearer_password = QLineEdit()
        self.bearer_password.setEchoMode(QLineEdit.Password)
        bearer_login_layout.addRow("密码:", self.bearer_password)
        
        self.bearer_token_path = QLineEdit()
        self.bearer_token_path.setPlaceholderText("例如: data.token 或 access_token")
        bearer_login_layout.addRow("Token路径:", self.bearer_token_path)
        
        form_layout.addRow(self.bearer_login_group)
        
        # 手动设置Token区域
        self.bearer_manual_group = QGroupBox("手动设置Token")
        self.bearer_manual_group.setCheckable(True)
        self.bearer_manual_group.setChecked(True)
        bearer_manual_layout = QFormLayout(self.bearer_manual_group)
        
        self.bearer_token = QLineEdit()
        bearer_manual_layout.addRow("Token:", self.bearer_token)
        
        form_layout.addRow(self.bearer_manual_group)
        
        layout.addLayout(form_layout)
        
    def setup_basic_tab(self):
        """
        设置Basic认证标签页
        """
        layout = QFormLayout(self.basic_widget)
        
        self.basic_username = QLineEdit()
        layout.addRow("用户名:", self.basic_username)
        
        self.basic_password = QLineEdit()
        self.basic_password.setEchoMode(QLineEdit.Password)
        layout.addRow("密码:", self.basic_password)
        
    def setup_api_key_tab(self):
        """
        设置API Key标签页
        """
        layout = QFormLayout(self.api_key_widget)
        
        self.api_key_name = QLineEdit()
        layout.addRow("Key名称:", self.api_key_name)
        
        self.api_key_value = QLineEdit()
        layout.addRow("Key值:", self.api_key_value)
        
        self.api_key_in = QComboBox()
        self.api_key_in.addItems(["header", "query"])
        layout.addRow("位置:", self.api_key_in)
        
    def load_config(self):
        """
        加载现有配置
        """
        # Bearer Token配置
        bearer_config = self.auth_manager.get_auth_config("bearer")
        if bearer_config:
            if "login_url" in bearer_config:
                self.bearer_login_group.setChecked(True)
                self.bearer_login_url.setText(bearer_config.get("login_url", ""))
                self.bearer_login_method.setCurrentText(bearer_config.get("method", "POST"))
                
                data = bearer_config.get("data", {})
                username_field = next((k for k, v in data.items() if "user" in k.lower()), "")
                password_field = next((k for k, v in data.items() if "pass" in k.lower()), "")
                
                self.bearer_username_field.setText(username_field)
                self.bearer_password_field.setText(password_field)
                
                self.bearer_username.setText(data.get(username_field, ""))
                self.bearer_password.setText(data.get(password_field, ""))
                
                self.bearer_token_path.setText(bearer_config.get("token_path", "token"))
            else:
                self.bearer_manual_group.setChecked(True)
                self.bearer_token.setText(self.auth_manager.tokens.get("bearer", ""))
        
        # Basic认证配置
        basic_config = self.auth_manager.get_auth_config("basic")
        if basic_config:
            self.basic_username.setText(basic_config.get("username", ""))
            self.basic_password.setText(basic_config.get("password", ""))
            
        # API Key配置
        api_key_config = self.auth_manager.get_auth_config("api_key")
        if api_key_config:
            self.api_key_name.setText(api_key_config.get("key_name", ""))
            self.api_key_value.setText(api_key_config.get("key_value", ""))
            self.api_key_in.setCurrentText(api_key_config.get("in", "header"))
            
    def save_config(self):
        """
        保存配置
        """
        # Bearer Token配置
        if self.bearer_login_group.isChecked():
            bearer_config = {
                "login_url": self.bearer_login_url.text(),
                "method": self.bearer_login_method.currentText(),
                "data": {
                    self.bearer_username_field.text(): self.bearer_username.text(),
                    self.bearer_password_field.text(): self.bearer_password.text()
                },
                "token_path": self.bearer_token_path.text()
            }
            self.auth_manager.set_auth_config("bearer", bearer_config)
        elif self.bearer_manual_group.isChecked():
            # 保存手动设置的token
            token = self.bearer_token.text()
            if token:
                self.auth_manager.tokens["bearer"] = token
                self.auth_manager.set_auth_config("bearer", {"manual": True})
                
        # Basic认证配置
        basic_config = {
            "username": self.basic_username.text(),
            "password": self.basic_password.text()
        }
        self.auth_manager.set_auth_config("basic", basic_config)
        
        # API Key配置
        api_key_config = {
            "key_name": self.api_key_name.text(),
            "key_value": self.api_key_value.text(),
            "in": self.api_key_in.currentText()
        }
        self.auth_manager.set_auth_config("api_key", api_key_config)
        
        QMessageBox.information(self, "保存成功", "认证配置已保存")
        self.accept()
        
    def test_auth(self):
        """
        测试认证配置
        """
        # 获取当前标签页
        current_tab = self.tab_widget.currentWidget()
        auth_type = ""
        
        if current_tab == self.bearer_widget:
            auth_type = "bearer"
            
            # 如果是自动获取token，需要先保存配置
            if self.bearer_login_group.isChecked():
                bearer_config = {
                    "login_url": self.bearer_login_url.text(),
                    "method": self.bearer_login_method.currentText(),
                    "data": {
                        self.bearer_username_field.text(): self.bearer_username.text(),
                        self.bearer_password_field.text(): self.bearer_password.text()
                    },
                    "token_path": self.bearer_token_path.text()
                }
                self.auth_manager.set_auth_config("bearer", bearer_config)
            
        elif current_tab == self.basic_widget:
            auth_type = "basic"
            
            # 先保存配置
            basic_config = {
                "username": self.basic_username.text(),
                "password": self.basic_password.text()
            }
            self.auth_manager.set_auth_config("basic", basic_config)
            
        elif current_tab == self.api_key_widget:
            auth_type = "api_key"
            
            # 先保存配置
            api_key_config = {
                "key_name": self.api_key_name.text(),
                "key_value": self.api_key_value.text(),
                "in": self.api_key_in.currentText()
            }
            self.auth_manager.set_auth_config("api_key", api_key_config)
            
        # 测试认证
        success, message = self.auth_manager.test_auth_config(auth_type)
        
        if success:
            QMessageBox.information(self, "测试成功", message)
        else:
            QMessageBox.warning(self, "测试失败", message)
