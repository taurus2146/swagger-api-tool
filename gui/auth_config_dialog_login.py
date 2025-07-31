#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Bearer Token认证配置对话框（支持登录接口）
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFormLayout, QMessageBox, QCheckBox,
    QComboBox, QTextEdit, QGroupBox, QGridLayout,
    QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt
import json


class AuthConfigDialog(QDialog):
    """
    Bearer Token认证配置对话框
    """
    
    def __init__(self, auth_manager, parent=None, api_list=None):
        """
        初始化认证配置对话框
        
        Args:
            auth_manager: 认证管理器实例
            parent: 父窗口
        """
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.api_list = api_list or []  # 保存API列表
        
        self.setWindowTitle("Bearer Token 认证配置")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        """
        初始化界面
        """
        layout = QVBoxLayout(self)
        
        # 登录配置组
        login_group = QGroupBox("登录接口配置")
        login_layout = QFormLayout()
        
        # 登录URL
        url_layout = QHBoxLayout()
        self.login_url_input = QLineEdit()
        self.login_url_input.setPlaceholderText("http://example.com/api/login")
        url_layout.addWidget(self.login_url_input)
        
        # 从列表选择按钮
        if self.api_list:
            self.select_api_button = QPushButton("从API列表选择")
            self.select_api_button.clicked.connect(self.select_from_api_list)
            url_layout.addWidget(self.select_api_button)
        
        login_layout.addRow("登录URL:", url_layout)
        
        # 请求方法
        self.method_combo = QComboBox()
        self.method_combo.addItems(["POST", "GET"])
        login_layout.addRow("请求方法:", self.method_combo)
        
        # 请求体
        self.request_body_label = QLabel("请求体 (JSON):")
        self.request_body_text = QTextEdit()
        self.request_body_text.setMaximumHeight(100)
        self.request_body_text.setPlaceholderText('{\n  "username": "your_username",\n  "password": "your_password"\n}')
        login_layout.addRow(self.request_body_label, self.request_body_text)
        
        # Token路径
        self.token_path_input = QLineEdit()
        self.token_path_input.setPlaceholderText("token 或 data.token 或 result.access_token")
        self.token_path_input.setText("token")
        login_layout.addRow("Token路径:", self.token_path_input)
        
        login_group.setLayout(login_layout)
        layout.addWidget(login_group)
        
        # Token设置组
        token_group = QGroupBox("Token设置")
        token_layout = QFormLayout()
        
        # 前缀选项
        self.use_prefix_checkbox = QCheckBox("使用 'Bearer ' 前缀")
        self.use_prefix_checkbox.setChecked(True)
        self.use_prefix_checkbox.setToolTip(
            "勾选时会在请求头中添加 'Bearer ' 前缀，\n"
            "生成格式：Authorization: Bearer your-token\n"
            "取消勾选则直接使用Token，\n"
            "生成格式：Authorization: your-token"
        )
        token_layout.addRow("", self.use_prefix_checkbox)
        
        # 当前Token显示和编辑
        self.current_token_label = QLabel("当前Token:")
        token_input_layout = QHBoxLayout()
        self.current_token_text = QLineEdit()
        self.current_token_text.setPlaceholderText("可以手动输入Token或通过登录接口获取")
        self.current_token_text.setToolTip("您可以手动输入Token，也可以通过测试登录接口自动获取")
        token_input_layout.addWidget(self.current_token_text)
        
        # 手动保存Token按钮
        self.save_token_button = QPushButton("保存Token")
        self.save_token_button.setToolTip("保存手动输入的Token")
        self.save_token_button.clicked.connect(self.save_manual_token)
        self.save_token_button.setMaximumWidth(100)
        token_input_layout.addWidget(self.save_token_button)
        
        token_layout.addRow(self.current_token_label, token_input_layout)
        
        token_group.setLayout(token_layout)
        layout.addWidget(token_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.clear_token_button = QPushButton("清空Token")
        self.clear_token_button.setToolTip("清除当前保存的Token")
        self.clear_token_button.clicked.connect(self.clear_token)
        self.clear_token_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        button_layout.addWidget(self.clear_token_button)
        
        button_layout.addStretch()
        
        self.test_button = QPushButton("测试登录并保存")
        self.test_button.setToolTip("测试登录接口，成功后自动保存配置并关闭")
        self.test_button.clicked.connect(self.test_login)
        button_layout.addWidget(self.test_button)
        
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
            self.login_url_input.setText(config.get('login_url', ''))
            self.method_combo.setCurrentText(config.get('method', 'POST'))
            
            # 加载请求体
            data = config.get('data', {})
            if data:
                self.request_body_text.setText(json.dumps(data, ensure_ascii=False, indent=2))
            
            self.token_path_input.setText(config.get('token_path', 'token'))
            self.use_prefix_checkbox.setChecked(config.get('use_prefix', True))
            
            # 显示当前token
            current_token = config.get('token', '')
            if current_token:
                self.current_token_text.setText(current_token)
            else:
                self.current_token_text.setText("<未获取>")
        
    def test_login(self):
        """
        测试登录获取Token
        """
        # 先保存当前配置
        if not self.save_config(show_message=False):
            return
        
        # 测试登录
        success, message = self.auth_manager.test_auth_config('bearer')
        
        if success:
            # 重新加载配置以显示新的token
            self.load_config()
            QMessageBox.information(self, "成功", message + "\n\n配置已自动保存。")
            # 成功后自动关闭对话框
            self.accept()
        else:
            QMessageBox.warning(self, "失败", message)
        
    def save_config(self, show_message=True):
        """
        保存配置
        
        Args:
            show_message: 是否显示保存成功消息
            
        Returns:
            bool: 是否保存成功
        """
        login_url = self.login_url_input.text().strip()
        if not login_url:
            QMessageBox.warning(self, "警告", "请输入登录URL")
            return False
        
        # 解析请求体
        request_body_text = self.request_body_text.toPlainText().strip()
        data = {}
        if request_body_text:
            try:
                data = json.loads(request_body_text)
            except json.JSONDecodeError:
                QMessageBox.warning(self, "错误", "请求体不是有效的JSON格式")
                return False
        
        config = {
            'login_url': login_url,
            'method': self.method_combo.currentText(),
            'headers': {'Content-Type': 'application/json'},
            'data': data,
            'token_path': self.token_path_input.text().strip() or 'token',
            'use_prefix': self.use_prefix_checkbox.isChecked()
        }
        
        # 保留已有的token
        existing_config = self.auth_manager.get_auth_config('bearer')
        if existing_config and 'token' in existing_config:
            config['token'] = existing_config['token']
        
        self.auth_manager.set_auth_config('bearer', config)
        
        if show_message:
            QMessageBox.information(self, "成功", "认证配置已保存")
            self.accept()
        
        return True
    
    def select_from_api_list(self):
        """
        从API列表中选择登录接口
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("选择登录接口")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_input = QLineEdit()
        search_input.setPlaceholderText("搜索API（路径或描述）...")
        search_layout.addWidget(QLabel("搜索:"))
        search_layout.addWidget(search_input)
        layout.addLayout(search_layout)
        
        # API列表
        api_list_widget = QListWidget()
        
        # 填充API列表
        filtered_apis = []
        for api in self.api_list:
            # 通常登录接口是POST方法
            if api.get('method', '').upper() == 'POST':
                path = api.get('path', '')
                summary = api.get('summary', '')
                description = api.get('description', '')
                
                # 检查是否可能是登录接口
                keywords = ['login', 'auth', 'signin', 'token', '登录', '认证']
                text_to_check = (path + ' ' + summary + ' ' + description).lower()
                
                if any(keyword in text_to_check for keyword in keywords):
                    item_text = f"{api.get('method', '').upper()} {path}"
                    if summary:
                        item_text += f" - {summary}"
                    
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, api)
                    api_list_widget.addItem(item)
                    filtered_apis.append(api)
        
        # 如果没有找到可能的登录接口，显示所有POST接口
        if api_list_widget.count() == 0:
            for api in self.api_list:
                if api.get('method', '').upper() == 'POST':
                    path = api.get('path', '')
                    summary = api.get('summary', '')
                    
                    item_text = f"{api.get('method', '').upper()} {path}"
                    if summary:
                        item_text += f" - {summary}"
                    
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, api)
                    api_list_widget.addItem(item)
                    filtered_apis.append(api)
        
        layout.addWidget(api_list_widget)
        
        # 搜索功能
        def filter_list():
            search_text = search_input.text().lower()
            for i in range(api_list_widget.count()):
                item = api_list_widget.item(i)
                api = item.data(Qt.UserRole)
                path = api.get('path', '').lower()
                summary = api.get('summary', '').lower()
                description = api.get('description', '').lower()
                
                visible = (search_text in path or 
                          search_text in summary or 
                          search_text in description)
                item.setHidden(not visible)
        
        search_input.textChanged.connect(filter_list)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("选择")
        cancel_button = QPushButton("取消")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # 事件处理
        def on_ok():
            current_item = api_list_widget.currentItem()
            if current_item:
                api = current_item.data(Qt.UserRole)
                # 设置登录URL
                base_url = self.parent().swagger_parser.get_base_url() if hasattr(self.parent(), 'swagger_parser') else ''
                full_url = self.parent().api_tester._build_full_url(base_url, api.get('path', ''))
                self.login_url_input.setText(full_url)
                
                # 设置请求方法
                self.method_combo.setCurrentText(api.get('method', '').upper())
                
                # 如果有请求体示例，设置请求体
                request_body = api.get('requestBody', {})
                if request_body:
                    content = request_body.get('content', {})
                    if 'application/json' in content:
                        schema = content['application/json'].get('schema', {})
                        # 生成示例请求体
                        example_body = self._generate_example_body(schema)
                        self.request_body_text.setText(json.dumps(example_body, ensure_ascii=False, indent=2))
                
                dialog.accept()
        
        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(dialog.reject)
        api_list_widget.itemDoubleClicked.connect(on_ok)
        
        dialog.exec_()
    
    def _generate_example_body(self, schema):
        """
        根据schema生成示例请求体
        
        Args:
            schema (dict): OpenAPI schema
            
        Returns:
            dict: 示例请求体
        """
        if schema.get('type') == 'object':
            example = {}
            properties = schema.get('properties', {})
            for prop_name, prop_schema in properties.items():
                # 对于用户名和密码字段，提供默认值
                if any(keyword in prop_name.lower() for keyword in ['username', 'user', 'account', 'email']):
                    example[prop_name] = "your_username"
                elif any(keyword in prop_name.lower() for keyword in ['password', 'pwd', 'pass']):
                    example[prop_name] = "your_password"
                elif prop_schema.get('type') == 'string':
                    example[prop_name] = "string"
                elif prop_schema.get('type') == 'integer':
                    example[prop_name] = 0
                elif prop_schema.get('type') == 'boolean':
                    example[prop_name] = True
                elif prop_schema.get('type') == 'array':
                    example[prop_name] = []
                elif prop_schema.get('type') == 'object':
                    example[prop_name] = {}
            return example
        return {}
    
    def clear_token(self):
        """
        清空当前Token
        """
        reply = QMessageBox.question(
            self, 
            "确认清空", 
            "确定要清空当前保存的Token吗？\n清空后需要重新登录获取Token。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 获取当前配置
            config = self.auth_manager.get_auth_config('bearer')
            if config:
                # 清空token
                config['token'] = ''
                # 保存配置
                self.auth_manager.set_auth_config('bearer', config)
                # 更新显示
                self.current_token_text.setText("")
                self.current_token_text.setPlaceholderText("可以手动输入Token或通过登录接口获取")
                QMessageBox.information(self, "成功", "Token已清空")
    
    def save_manual_token(self):
        """
        保存手动输入的Token
        """
        token = self.current_token_text.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Token")
            return
            
        # 获取当前配置
        config = self.auth_manager.get_auth_config('bearer')
        if not config:
            config = {
                'login_url': '',
                'method': 'POST',
                'headers': {'Content-Type': 'application/json'},
                'data': {},
                'token_path': 'token',
                'use_prefix': self.use_prefix_checkbox.isChecked()
            }
        
        # 设置token
        config['token'] = token
        config['use_prefix'] = self.use_prefix_checkbox.isChecked()
        
        # 保存配置
        self.auth_manager.set_auth_config('bearer', config)
        
        QMessageBox.information(self, "成功", "Token已保存\n\n您现在可以使用该Token进行API测试。")
