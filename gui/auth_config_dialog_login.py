#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Bearer Token认证配置对话框（支持登录接口）
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QMessageBox, QCheckBox,
    QComboBox, QTextEdit, QGroupBox, QGridLayout,
    QListWidget, QListWidgetItem, QTabWidget, QWidget,
    QProgressDialog, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import json


class LoginTestThread(QThread):
    """异步登录测试线程"""
    finished = pyqtSignal(bool, str)  # 成功标志, 消息

    def __init__(self, auth_manager, config):
        super().__init__()
        self.auth_manager = auth_manager
        self.config = config

    def run(self):
        try:
            # 临时保存配置用于测试
            self.auth_manager.set_auth_config('bearer', self.config)
            # 测试登录
            success, message = self.auth_manager.test_auth_config('bearer')
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, f"登录测试失败: {str(e)}")


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
        
        self.setWindowTitle("认证配置")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        """
        初始化界面
        """
        layout = QVBoxLayout(self)

        # 创建标签页控件
        self.tab_widget = QTabWidget()

        # 创建各个标签页
        self.create_bearer_token_tab()
        self.create_custom_headers_tab()

        layout.addWidget(self.tab_widget)

        # 不再需要底部按钮区域，每个标签页自己管理按钮



    def create_bearer_token_tab(self):
        """创建Bearer Token标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

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
        prefix_layout = QHBoxLayout()

        self.use_prefix_checkbox = QCheckBox("使用Token前缀")
        self.use_prefix_checkbox.setChecked(False)  # 默认不勾选
        self.use_prefix_checkbox.setToolTip(
            "勾选时会在请求头中添加自定义前缀，\n"
            "生成格式：Authorization: [前缀]your-token\n"
            "取消勾选则直接使用Token，\n"
            "生成格式：Authorization: your-token"
        )
        prefix_layout.addWidget(self.use_prefix_checkbox)

        # 前缀输入框
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("Bearer ")
        self.prefix_input.setText("Bearer ")  # 默认值
        self.prefix_input.setMaximumWidth(100)
        self.prefix_input.setEnabled(False)  # 默认禁用
        self.prefix_input.setToolTip("自定义Token前缀，如：Bearer 、Token 、JWT 等")
        prefix_layout.addWidget(self.prefix_input)

        prefix_layout.addStretch()

        # 连接复选框事件
        self.use_prefix_checkbox.toggled.connect(self.on_prefix_checkbox_toggled)

        token_layout.addRow("Token前缀:", prefix_layout)

        # 当前Token显示和编辑
        self.current_token_label = QLabel("当前Token:")
        token_input_layout = QHBoxLayout()
        self.current_token_text = QLineEdit()
        self.current_token_text.setPlaceholderText("可以手动输入Token或通过登录接口获取")
        self.current_token_text.setToolTip("您可以手动输入Token，也可以通过测试登录接口自动获取")
        token_input_layout.addWidget(self.current_token_text)

        # 保存Token按钮
        self.save_token_button = QPushButton("保存Token")
        self.save_token_button.setToolTip("保存当前输入的Token")
        self.save_token_button.clicked.connect(self.save_token)
        self.save_token_button.setMaximumWidth(100)
        token_input_layout.addWidget(self.save_token_button)

        token_layout.addRow(self.current_token_label, token_input_layout)

        token_group.setLayout(token_layout)
        layout.addWidget(token_group)

        # 操作按钮行
        action_layout = QHBoxLayout()

        # 清空Token按钮
        self.bearer_clear_button = QPushButton("清空Token")
        self.bearer_clear_button.setToolTip("清空当前保存的Token")
        self.bearer_clear_button.clicked.connect(self.clear_token)
        self.bearer_clear_button.setMaximumWidth(100)
        action_layout.addWidget(self.bearer_clear_button)

        # 测试登录按钮
        self.bearer_test_button = QPushButton("测试登录")
        self.bearer_test_button.setToolTip("测试登录接口并获取Token")
        self.bearer_test_button.clicked.connect(self.test_login)
        self.bearer_test_button.setMaximumWidth(100)
        action_layout.addWidget(self.bearer_test_button)

        # 添加弹性空间，让按钮靠左对齐
        action_layout.addStretch()

        layout.addLayout(action_layout)

        # 添加到标签页
        self.tab_widget.addTab(tab, "Bearer Token认证")

    def on_prefix_checkbox_toggled(self, checked):
        """处理前缀复选框切换事件"""
        self.prefix_input.setEnabled(checked)
        if checked and not self.prefix_input.text().strip():
            self.prefix_input.setText("Bearer ")  # 勾选时设置默认值



    def create_custom_headers_tab(self):
        """创建自定义请求头标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 说明标签
        info_label = QLabel("自定义请求头配置")
        info_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # 请求头列表区域
        self.headers_scroll_area = QWidget()
        self.headers_layout = QVBoxLayout(self.headers_scroll_area)

        # 存储请求头输入框的列表
        self.header_inputs = []

        # 不添加初始的空请求头输入框，等待加载配置时决定

        layout.addWidget(self.headers_scroll_area)

        # 添加按钮
        add_button_layout = QHBoxLayout()
        self.add_header_btn = QPushButton("+ 添加请求头")
        self.add_header_btn.clicked.connect(self.add_header_input)
        add_button_layout.addWidget(self.add_header_btn)
        add_button_layout.addStretch()
        layout.addLayout(add_button_layout)

        layout.addStretch()

        # 按钮区域
        button_layout = QHBoxLayout()

        # 保存配置按钮
        self.save_headers_button = QPushButton("保存配置")
        self.save_headers_button.setToolTip("保存自定义请求头配置")
        self.save_headers_button.clicked.connect(self.save_headers_config)
        button_layout.addWidget(self.save_headers_button)

        # 关闭按钮
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # 添加到标签页
        self.tab_widget.addTab(tab, "自定义请求头")

    def add_header_input(self):
        """添加一个新的请求头输入框"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 5, 0, 5)

        # 请求头名称输入框
        name_input = QLineEdit()
        name_input.setPlaceholderText("请求头名称 (如: X-API-Key)")
        name_input.setMaximumWidth(200)
        header_layout.addWidget(name_input)

        # 冒号标签
        colon_label = QLabel(":")
        header_layout.addWidget(colon_label)

        # 请求头值输入框
        value_input = QLineEdit()
        value_input.setPlaceholderText("请求头值 (如: your-api-key-here)")
        header_layout.addWidget(value_input)

        # 删除按钮
        delete_btn = QPushButton("删除")
        delete_btn.setMaximumWidth(60)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        delete_btn.clicked.connect(lambda: self.remove_header_input(header_widget))
        header_layout.addWidget(delete_btn)

        # 保存输入框引用
        header_data = {
            'widget': header_widget,
            'name_input': name_input,
            'value_input': value_input
        }
        self.header_inputs.append(header_data)

        # 添加到布局
        self.headers_layout.addWidget(header_widget)

    def remove_header_input(self, header_widget):
        """删除指定的请求头输入框"""
        # 从列表中移除
        self.header_inputs = [h for h in self.header_inputs if h['widget'] != header_widget]

        # 从布局中移除
        self.headers_layout.removeWidget(header_widget)
        header_widget.deleteLater()

        # 不自动添加空输入框，让用户通过"添加请求头"按钮主动添加
        
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

            # 加载前缀配置
            use_prefix = config.get('use_prefix', False)  # 默认不使用前缀
            self.use_prefix_checkbox.setChecked(use_prefix)

            # 加载自定义前缀
            custom_prefix = config.get('custom_prefix', 'Bearer ')
            self.prefix_input.setText(custom_prefix)
            self.prefix_input.setEnabled(use_prefix)
            
            # 显示当前token
            current_token = config.get('token', '')
            if current_token:
                self.current_token_text.setText(current_token)
            else:
                self.current_token_text.setText("<未获取>")

        # 加载自定义请求头
        custom_headers = self.auth_manager.get_auth_config('custom_headers')

        # 清空现有的输入框
        for header_data in self.header_inputs[:]:
            self.remove_header_input(header_data['widget'])

        if custom_headers:
            # 为每个请求头创建输入框
            for key, value in custom_headers.items():
                self.add_header_input()
                # 设置最后添加的输入框的值
                last_header = self.header_inputs[-1]
                last_header['name_input'].setText(key)
                last_header['value_input'].setText(value)

        # 如果没有任何输入框，添加一个空的
        if not self.header_inputs:
            self.add_header_input()
        
    def test_login(self):
        """
        测试登录获取Token
        """
        # 验证必要的配置
        login_url = self.login_url_input.text().strip()
        if not login_url:
            QMessageBox.warning(self, "警告", "请输入登录URL")
            return

        # 解析请求体
        request_body_text = self.request_body_text.toPlainText().strip()
        data = {}
        if request_body_text:
            try:
                data = json.loads(request_body_text)
            except json.JSONDecodeError:
                QMessageBox.warning(self, "错误", "请求体不是有效的JSON格式")
                return

        # 构建临时配置进行测试
        token_field = self.token_path_input.text().strip() or 'token'

        temp_config = {
            'login_url': login_url,
            'method': self.method_combo.currentText(),
            'headers': {'Content-Type': 'application/json'},
            'data': data,
            'token_path': token_field,
            'use_prefix': self.use_prefix_checkbox.isChecked(),
            'custom_prefix': self.prefix_input.text().strip() if self.use_prefix_checkbox.isChecked() else ''
        }

        # 禁用测试按钮，防止重复点击
        self.bearer_test_button.setEnabled(False)
        self.bearer_test_button.setText("测试中...")

        # 创建进度对话框
        self.progress_dialog = QProgressDialog("正在测试登录...", "取消", 0, 0, self)
        self.progress_dialog.setWindowTitle("登录测试")
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()

        # 创建并启动异步登录测试线程
        self.login_thread = LoginTestThread(self.auth_manager, temp_config)
        self.login_thread.finished.connect(self.on_login_test_finished)
        self.login_thread.start()

        # 连接取消按钮
        self.progress_dialog.canceled.connect(self.cancel_login_test)

    def cancel_login_test(self):
        """取消登录测试"""
        if hasattr(self, 'login_thread') and self.login_thread.isRunning():
            self.login_thread.terminate()
            self.login_thread.wait()
        self.reset_login_test_ui()

    def on_login_test_finished(self, success, message):
        """登录测试完成回调"""
        # 关闭进度对话框
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()

        # 重置UI状态
        self.reset_login_test_ui()

        if success:
            # 重新加载配置以显示新的token
            self.load_config()
            QMessageBox.information(self, "登录成功", message + "\n\nToken已自动获取并保存。")
        else:
            QMessageBox.warning(self, "登录失败", message)

    def reset_login_test_ui(self):
        """重置登录测试UI状态"""
        self.bearer_test_button.setEnabled(True)
        self.bearer_test_button.setText("测试登录")
        

    
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
    
    def save_token(self):
        """
        保存当前输入的Token
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
                'use_prefix': False,
                'custom_prefix': ''
            }

        # 更新Token和前缀配置
        config['token'] = token
        config['use_prefix'] = self.use_prefix_checkbox.isChecked()
        config['custom_prefix'] = self.prefix_input.text().strip() if self.use_prefix_checkbox.isChecked() else ''

        # 保存配置
        self.auth_manager.set_auth_config('bearer', config)

        QMessageBox.information(self, "保存成功", f"Token已保存\n\n{token[:30]}...")

    def save_headers_config(self):
        """
        保存自定义请求头配置
        """
        # 收集所有请求头
        headers = {}
        for header_data in self.header_inputs:
            name = header_data['name_input'].text().strip()
            value = header_data['value_input'].text().strip()
            if name and value:  # 只保存非空的请求头
                headers[name] = value

        # 保存配置
        self.auth_manager.set_auth_config('custom_headers', headers)

        # 显示成功消息
        if headers:
            message = f"自定义请求头配置已保存！\n\n共保存了 {len(headers)} 个请求头：\n"
            for name, value in headers.items():
                message += f"✅ {name}: {value}\n"
        else:
            message = "自定义请求头配置已清空！"

        QMessageBox.information(self, "保存成功", message)
