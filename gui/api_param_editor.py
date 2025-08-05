#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API参数编辑器
"""

import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTabWidget, QScrollArea, QFormLayout,
    QTextEdit, QGroupBox, QCheckBox, QComboBox,
    QMessageBox, QSpinBox, QDoubleSpinBox, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal

from core.data_generator import DataGenerator


class ApiParamEditor(QWidget):
    """
    API参数编辑器，用于编辑API请求参数
    """
    
    # 定义信号
    test_requested = pyqtSignal(dict)
    export_curl_requested = pyqtSignal(dict, object)  # 第二个参数是按钮对象
    export_postman_requested = pyqtSignal(list, object)  # 第二个参数是按钮对象
    
    def __init__(self, parent=None):
        """
        初始化API参数编辑器
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.swagger_parser = None
        self.data_generator = None
        self.api_info = None
        self.param_widgets = {}  # 存储参数控件
        self.common_prefix = ''  # 添加公共前缀属性
        self.init_ui()
        
    def set_swagger_parser(self, swagger_parser):
        """
        设置Swagger解析器
        
        Args:
            swagger_parser (SwaggerParser): Swagger解析器实例
        """
        self.swagger_parser = swagger_parser
        
        # 设置数据生成器并确保它有swagger_data
        if swagger_parser:
            if swagger_parser.data_generator:
                self.data_generator = swagger_parser.data_generator
            else:
                # 如果SwaggerParser没有data_generator，创建一个新的并设置swagger_data
                self.data_generator = DataGenerator(swagger_data=swagger_parser.swagger_data)
            
            # 确保数据生成器有最新的swagger_data
            if self.data_generator and hasattr(swagger_parser, 'swagger_data'):
                self.data_generator.swagger_data = swagger_parser.swagger_data
        
    def init_ui(self):
        """
        初始化界面
        """
        layout = QVBoxLayout(self)
        
        # 顶部API信息
        self.api_info_group = QGroupBox("API信息")
        api_info_layout = QFormLayout(self.api_info_group)
        
        # 路径行：标签 + 复制按钮
        path_widget = QWidget()
        path_layout = QHBoxLayout(path_widget)
        path_layout.setContentsMargins(0, 0, 0, 0)
        
        self.api_path = QLabel()
        self.api_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        path_layout.addWidget(self.api_path)
        
        self.copy_path_button = QPushButton("复制")
        self.copy_path_button.setMaximumWidth(60)
        self.copy_path_button.clicked.connect(self.copy_path)
        path_layout.addWidget(self.copy_path_button)
        path_layout.addStretch()
        
        api_info_layout.addRow("路径:", path_widget)
        
        self.api_method = QLabel()
        api_info_layout.addRow("方法:", self.api_method)
        
        self.api_description = QLabel()
        self.api_description.setWordWrap(True)
        api_info_layout.addRow("描述:", self.api_description)
        
        layout.addWidget(self.api_info_group)
        
        # 参数编辑区
        self.param_tabs = QTabWidget()
        
        # 路径参数标签页
        self.path_param_tab = QScrollArea()
        self.path_param_tab.setWidgetResizable(True)
        self.path_param_widget = QWidget()
        self.path_param_layout = QFormLayout(self.path_param_widget)
        self.path_param_tab.setWidget(self.path_param_widget)
        self.param_tabs.addTab(self.path_param_tab, "路径参数")
        
        # 查询参数标签页
        self.query_param_tab = QScrollArea()
        self.query_param_tab.setWidgetResizable(True)
        self.query_param_widget = QWidget()
        self.query_param_layout = QFormLayout(self.query_param_widget)
        self.query_param_tab.setWidget(self.query_param_widget)
        self.param_tabs.addTab(self.query_param_tab, "查询参数")
        
        # 请求头标签页 - 只显示自定义请求头
        self.header_param_tab = QScrollArea()
        self.header_param_tab.setWidgetResizable(True)
        self.header_param_widget = QWidget()
        self.header_param_layout = QVBoxLayout(self.header_param_widget)
        

        
        # 添加请求头按钮
        add_header_button = QPushButton("+ 添加请求头")
        add_header_button.clicked.connect(self.add_custom_header)
        self.header_param_layout.addWidget(add_header_button)
        
        # 自定义请求头容器
        self.custom_headers_container = QWidget()
        self.custom_headers_container_layout = QVBoxLayout(self.custom_headers_container)
        self.custom_headers_container_layout.setContentsMargins(0, 0, 0, 0)
        self.header_param_layout.addWidget(self.custom_headers_container)
        
        # 添加弹性空间
        self.header_param_layout.addStretch()
        
        self.header_param_tab.setWidget(self.header_param_widget)
        self.param_tabs.addTab(self.header_param_tab, "请求头")
        
        # 存储自定义请求头的列表
        self.custom_headers = []
        
        # 请求体标签页
        self.body_param_tab = QWidget()
        self.body_param_layout = QVBoxLayout(self.body_param_tab)
        
        # JSON编辑器
        self.json_editor = QTextEdit()
        self.json_editor.setPlaceholderText("输入JSON请求体...")
        self.body_param_layout.addWidget(self.json_editor)
        
        self.param_tabs.addTab(self.body_param_tab, "请求体")
        
        layout.addWidget(self.param_tabs)
        
        # 底部按钮区域
        button_layout = QHBoxLayout()
        
        self.regenerate_button = QPushButton("重新生成测试数据")
        self.regenerate_button.clicked.connect(self.regenerate_test_data)
        button_layout.addWidget(self.regenerate_button)
        
        button_layout.addStretch()
        
        self.use_auth_checkbox = QCheckBox("是否认证")
        self.use_auth_checkbox.setChecked(True)
        self.use_auth_checkbox.setToolTip("勾选时请求会携带认证信息，适用于需要登录的接口\n取消勾选时不携带认证信息，适用于公开接口")
        button_layout.addWidget(self.use_auth_checkbox)
        
        self.test_button = QPushButton("测试API")
        self.test_button.setObjectName("test_button")  # 设置对象名称以应用样式
        self.test_button.clicked.connect(self.test_api)
        button_layout.addWidget(self.test_button)
        
        # 添加导出按钮
        self.export_curl_button = QPushButton("导出为cURL")
        self.export_curl_button.setObjectName("export_curl_button")  # 设置对象名称以应用样式
        self.export_curl_button.clicked.connect(self.export_as_curl)
        button_layout.addWidget(self.export_curl_button)
        
        layout.addLayout(button_layout)
        
    def set_api(self, api_info):
        """
        设置要编辑的API信息
        
        Args:
            api_info (dict): API信息
        """
        self.api_info = api_info
        self.update_ui()
        
    def set_api_with_history_data(self, api_info, test_result):
        """
        设置API信息并回显历史测试数据
        
        Args:
            api_info (dict): API信息
            test_result (dict): 历史测试结果
        """
        import logging
        from PyQt5.QtCore import QTimer
        logger = logging.getLogger(__name__)
        
        logger.info(f"设置API并回显历史数据: {api_info.get('path', 'Unknown')}")
        logger.debug(f"测试结果: {test_result}")
        
        self.api_info = api_info
        self.update_ui()
        
        # 使用QTimer延迟加载数据，确保界面已经更新完成
        def delayed_load():
            # 回显自定义数据
            custom_data = test_result.get('custom_data')
            logger.debug(f"延迟加载自定义数据: {custom_data}")
            if custom_data:
                self.load_custom_data(custom_data)
                
            # 回显认证设置
            self.use_auth_checkbox.setChecked(test_result.get('use_auth', True))
                
        # 延迟100毫秒执行，确保UI更新完成
        QTimer.singleShot(100, delayed_load)
        
    def update_ui(self):
        """
        更新界面显示
        """
        if not self.api_info:
            return
            
        # 更新API信息
        full_path = self.api_info.get('path', '')
        display_path = self._get_display_path(full_path)
        self.api_path.setText(display_path)
        self.api_path.setObjectName("api_path")  # 设置对象名称以应用样式
        self.api_path.setToolTip(full_path)  # 鼠标悬停时显示完整路径
        method = self.api_info.get('method', '')
        self.api_method.setText(method)
        self.api_method.setObjectName("api_method")  # 设置对象名称以应用样式
        self.api_method.setProperty("method", method.upper())  # 设置属性以应用HTTP方法颜色
        self.api_description.setText(self.api_info.get('description', self.api_info.get('summary', '')))
        
        # 根据Swagger文档中是否定义了请求体来决定是否显示请求体标签页
        request_body = self.api_info.get('requestBody')
        has_request_body = request_body is not None

        # 对于某些方法，即使没有在Swagger中定义请求体，也可能需要支持
        # 但我们主要根据Swagger文档的定义来决定
        if has_request_body:
            # 确保请求体标签页可见
            body_tab_index = self.param_tabs.indexOf(self.body_param_tab)
            if body_tab_index == -1:
                self.param_tabs.addTab(self.body_param_tab, "请求体")
        else:
            # 如果Swagger文档中没有定义请求体，隐藏请求体标签页
            body_tab_index = self.param_tabs.indexOf(self.body_param_tab)
            if body_tab_index != -1:
                self.param_tabs.removeTab(body_tab_index)
        
        # 清空参数控件
        self.clear_param_widgets()
        
        # 生成并显示参数
        self.generate_param_widgets()
    
    def add_custom_header(self):
        """添加自定义请求头"""
        header_widget = self.create_custom_header_widget()
        self.custom_headers_container_layout.addWidget(header_widget)
        self.custom_headers.append(header_widget)
    
    def create_custom_header_widget(self, name="", value=""):
        """
        创建自定义请求头控件
        
        Args:
            name (str): 请求头名称
            value (str): 请求头值
            
        Returns:
            QWidget: 请求头控件
        """
        # QHBoxLayout已经在顶部导入了
        
        header_widget = QWidget()
        layout = QHBoxLayout(header_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 请求头名称输入框
        name_input = QLineEdit()
        name_input.setPlaceholderText("请求头名称 (如: X-API-Key)")
        name_input.setText(name)
        layout.addWidget(name_input)
        
        # 请求头值输入框
        value_input = QLineEdit()
        value_input.setPlaceholderText("请求头值 (如: your-api-key)")
        value_input.setText(value)
        layout.addWidget(value_input)
        
        # 删除按钮
        delete_button = QPushButton("删除")
        delete_button.setMaximumWidth(60)
        delete_button.clicked.connect(lambda: self.remove_custom_header(header_widget))
        layout.addWidget(delete_button)
        
        # 存储输入框引用，方便后续获取值
        header_widget.name_input = name_input
        header_widget.value_input = value_input
        
        return header_widget
    
    def remove_custom_header(self, header_widget):
        """
        删除自定义请求头
        
        Args:
            header_widget (QWidget): 要删除的请求头控件
        """
        if header_widget in self.custom_headers:
            self.custom_headers.remove(header_widget)
            self.custom_headers_container_layout.removeWidget(header_widget)
            header_widget.deleteLater()
    
    def get_custom_headers(self):
        """
        获取所有自定义请求头
        
        Returns:
            dict: 自定义请求头字典
        """
        custom_headers = {}
        for header_widget in self.custom_headers:
            name = header_widget.name_input.text().strip()
            value = header_widget.value_input.text().strip()
            if name:  # 只有名称不为空才添加
                custom_headers[name] = value
        return custom_headers
    
    def clear_custom_headers(self):
        """清空所有自定义请求头"""
        for header_widget in self.custom_headers[:]:  # 使用切片复制列表，避免在迭代时修改列表
            self.remove_custom_header(header_widget)
        
    def clear_param_widgets(self):
        """
        清空参数控件
        """
        # 清空路径参数
        while self.path_param_layout.rowCount() > 0:
            self.path_param_layout.removeRow(0)
            
        # 清空查询参数
        while self.query_param_layout.rowCount() > 0:
            self.query_param_layout.removeRow(0)
            
        # 清空自定义请求头
        self.clear_custom_headers()
            
        # 清空JSON编辑器
        self.json_editor.clear()
        
        # 重置参数控件字典
        self.param_widgets = {
            'path': {},
            'query': {},
            'header': {},
            'body': None,
            'query_checkboxes': {}  # 添加查询参数勾选框字典
        }
        
    def generate_param_widgets(self):
        """
        生成参数控件
        """
        if not self.api_info or not self.data_generator:
            return
            
        parameters = self.api_info.get('parameters', [])
        request_body = self.api_info.get('requestBody', {})
        method = self.api_info.get('method', '').lower()
        
        # 检查是否有路径参数
        has_path_params = any(param.get('in') == 'path' for param in parameters)
        
        # 如果没有路径参数，隐藏路径参数标签页
        if not has_path_params:
            path_tab_index = self.param_tabs.indexOf(self.path_param_tab)
            if path_tab_index != -1:
                self.param_tabs.removeTab(path_tab_index)
        else:
            # 如果有路径参数，确保标签页可见
            path_tab_index = self.param_tabs.indexOf(self.path_param_tab)
            if path_tab_index == -1:
                self.param_tabs.insertTab(0, self.path_param_tab, "路径参数")
        
        # 检查是否有查询参数
        has_query_params = any(param.get('in') == 'query' for param in parameters)
        
        # 如果没有查询参数，无论什么方法都隐藏查询参数标签页
        if not has_query_params:
            query_tab_index = self.param_tabs.indexOf(self.query_param_tab)
            if query_tab_index != -1:
                self.param_tabs.removeTab(query_tab_index)
        else:
            # 如果有查询参数，确保查询参数标签页可见
            query_tab_index = self.param_tabs.indexOf(self.query_param_tab)
            if query_tab_index == -1:
                # 插入到合适的位置（在路径参数之后）
                path_index = self.param_tabs.indexOf(self.path_param_tab)
                insert_index = path_index + 1 if path_index != -1 else 0
                self.param_tabs.insertTab(insert_index, self.query_param_tab, "查询参数")
        
        # 确保请求头标签页始终可见（因为用户可以添加自定义请求头）
        header_tab_index = self.param_tabs.indexOf(self.header_param_tab)
        if header_tab_index == -1:
            # 插入到合适的位置（在查询参数之后，请求体之前）
            query_index = self.param_tabs.indexOf(self.query_param_tab)
            body_index = self.param_tabs.indexOf(self.body_param_tab)
            
            if query_index != -1:
                insert_index = query_index + 1
            elif body_index != -1:
                insert_index = body_index
            else:
                insert_index = self.param_tabs.count()
            
            self.param_tabs.insertTab(insert_index, self.header_param_tab, "请求头")
        
        # 处理参数
        for param in parameters:
            param_in = param.get('in', '')
            param_name = param.get('name', '')
            # 使用数据生成器的方法来获取正确的参数schema
            param_schema = self.data_generator._get_parameter_schema(param)
            param_required = param.get('required', False)
            param_description = param.get('description', '')
            
            # 生成参数值
            try:
                generated_value = self.data_generator.generate_data(param_schema)
            except Exception as e:
                logger.error(f"生成参数数据失败: {e}")
                # 提供备用值
                if param_schema.get('type') == 'integer':
                    generated_value = 1
                elif param_schema.get('type') == 'number':
                    generated_value = 1.0
                elif param_schema.get('type') == 'boolean':
                    generated_value = True
                else:
                    generated_value = "示例值"
            
            # 对于分页相关的参数，设置默认值
            if param_in == 'query':
                param_name_lower = param_name.lower()
                # 检查是否是分页大小相关参数
                if any(keyword in param_name_lower for keyword in ['pagesize', 'page_size', 'limit', 'size', 'perpage', 'per_page']):
                    generated_value = 10
                # 检查是否是当前页相关参数
                elif any(keyword in param_name_lower for keyword in ['page', 'pagenumber', 'page_number', 'pageindex', 'page_index', 'current']):
                    # 排除包含size的参数名
                    if 'size' not in param_name_lower:
                        generated_value = 1
            
            # 创建参数控件
            if param_in == 'path':
                self.add_param_widget(self.path_param_layout, param_in, param_name, param_schema, 
                                     param_required, param_description, generated_value)
            elif param_in == 'query':
                self.add_param_widget(self.query_param_layout, param_in, param_name, param_schema, 
                                     param_required, param_description, generated_value)
            elif param_in == 'header':
                # 跳过预定义请求头，这些应该在认证配置中处理
                pass
        
        # 处理请求体 - 根据Swagger文档中是否定义了请求体来决定
        if request_body:
            content = request_body.get('content', {})
            
            # 处理JSON请求体
            for content_type, media_type in content.items():
                json_schema = media_type.get('schema', {})
                if content_type == 'application/json' and json_schema:
                    # 设置正在生成请求体的标记
                    self.data_generator.is_generating_request_body = True
                    try:
                        generated_body = self.data_generator.generate_data(json_schema)
                    except Exception as e:
                        logger.error(f"生成请求体数据失败: {e}")
                        # 提供备用的请求体数据
                        generated_body = {"error": "无法生成示例数据", "message": str(e)}
                    finally:
                        self.data_generator.is_generating_request_body = False
                    
                    if isinstance(generated_body, (dict, list)):
                        self.json_editor.setText(json.dumps(generated_body, ensure_ascii=False, indent=2))
                        self.param_widgets['body'] = self.json_editor
                    break  # 只处理JSON格式
        
        # 如果没有任何自定义请求头，添加一个空的示例（仅在首次加载时）
        if not self.custom_headers:
            # 不自动添加，让用户根据需要手动添加
            pass
        
        # 智能切换到最重要的参数标签页
        self._switch_to_primary_tab()
                    
    def _switch_to_primary_tab(self):
        """
        智能切换到最重要的参数标签页
        优先级：请求体 > 查询参数 > 路径参数 > 请求头
        """
        if not self.api_info:
            return
        
        parameters = self.api_info.get('parameters', [])
        request_body = self.api_info.get('requestBody', {})
        method = self.api_info.get('method', '').lower()
        
        # 检查各种参数类型是否存在
        has_path_params = any(param.get('in') == 'path' for param in parameters)
        has_query_params = any(param.get('in') == 'query' for param in parameters)
        
        # 检查请求体标签页是否可见（在update_ui中根据HTTP方法决定是否显示）
        body_tab_visible = self.param_tabs.indexOf(self.body_param_tab) != -1
        
        # 按优先级切换标签页
        target_tab = None
        
        # 1. 最高优先级：请求体（如果标签页可见，说明方法支持请求体）
        if body_tab_visible:
            body_tab_index = self.param_tabs.indexOf(self.body_param_tab)
            if body_tab_index != -1:
                target_tab = body_tab_index
        
        # 2. 次高优先级：查询参数（通常是用户最关心的）
        elif has_query_params:
            query_tab_index = self.param_tabs.indexOf(self.query_param_tab)
            if query_tab_index != -1:
                target_tab = query_tab_index
        
        # 3. 第三优先级：路径参数（通常是必需的）
        elif has_path_params:
            path_tab_index = self.param_tabs.indexOf(self.path_param_tab)
            if path_tab_index != -1:
                target_tab = path_tab_index
        
        # 切换到目标标签页
        if target_tab is not None:
            self.param_tabs.setCurrentIndex(target_tab)
        
        # 如果没有任何参数，默认显示第一个可见的标签页
        elif self.param_tabs.count() > 0:
            self.param_tabs.setCurrentIndex(0)
                    
    def add_param_widget(self, layout, param_in, param_name, param_schema, required, description, value):
        """
        添加参数控件
        
        Args:
            layout (QFormLayout): 要添加到的布局
            param_in (str): 参数位置
            param_name (str): 参数名称
            param_schema (dict): 参数架构
            required (bool): 是否必需
            description (str): 参数描述
            value: 参数值
        """
        # 创建水平布局容器
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 对于查询参数，添加勾选框（除了分页相关参数）
        checkbox = None
        if param_in == 'query':
            param_name_lower = param_name.lower()
            # 分页相关参数默认勾选
            is_pagination = any(keyword in param_name_lower for keyword in 
                              ['page', 'size', 'limit', 'offset', 'pagesize', 'pageindex', 'pagenumber'])
            
            checkbox = QCheckBox()
            checkbox.setChecked(required or is_pagination)  # 必需参数和分页参数默认勾选
            checkbox.setToolTip("勾选以包含此参数")
            container_layout.addWidget(checkbox)
            
            # 保存勾选框引用
            if 'query_checkboxes' not in self.param_widgets:
                self.param_widgets['query_checkboxes'] = {}
            self.param_widgets['query_checkboxes'][param_name] = checkbox
        
        # 创建参数标签
        label_text = param_name
        if required:
            label_text += " *"
            
        # 创建标签控件
        label = QLabel(label_text)
        if description:
            # 如果描述太长，截断显示
            if len(description) > 50:
                short_desc = description[:47] + "..."
                label.setToolTip(f"{param_name}: {description}")  # 完整描述作为工具提示
            else:
                label.setToolTip(description)
            
        # 根据参数类型创建控件
        param_type = param_schema.get('type', 'string')
        
        if param_type == 'boolean':
            widget = QCheckBox()
            widget.setChecked(value if isinstance(value, bool) else False)
        elif param_type == 'integer':
            widget = QSpinBox()
            widget.setRange(-1000000, 1000000)
            widget.setValue(value if isinstance(value, int) else 0)
        elif param_type == 'number':
            widget = QDoubleSpinBox()
            widget.setRange(-1000000, 1000000)
            widget.setValue(value if isinstance(value, (int, float)) else 0)
        elif param_type == 'array':
            widget = QTextEdit()
            if isinstance(value, list):
                widget.setText(json.dumps(value, ensure_ascii=False))
            else:
                widget.setText("[]")
            widget.setMaximumHeight(80)
        elif param_type == 'object':
            widget = QTextEdit()
            if isinstance(value, dict):
                widget.setText(json.dumps(value, ensure_ascii=False, indent=2))
            else:
                widget.setText("{}")
            widget.setMaximumHeight(100)
        else:  # 默认为字符串
            if 'enum' in param_schema:
                widget = QComboBox()
                for enum_value in param_schema['enum']:
                    widget.addItem(str(enum_value))
                if value and str(value) in [widget.itemText(i) for i in range(widget.count())]:
                    widget.setCurrentText(str(value))
            else:
                widget = QLineEdit()
                widget.setText(str(value) if value is not None else "")
                
        # 如果有勾选框，将控件添加到容器
        if checkbox is not None:
            container_layout.addWidget(widget)
            container_layout.addStretch()
            # 将容器添加到布局
            layout.addRow(label, container)
            
            # 连接勾选框状态改变信号
            checkbox.stateChanged.connect(lambda state: widget.setEnabled(state == Qt.Checked))
            # 初始状态设置
            widget.setEnabled(checkbox.isChecked())
        else:
            # 没有勾选框的情况，直接添加控件
            layout.addRow(label, widget)
        
        # 保存控件引用
        if param_in in self.param_widgets:
            self.param_widgets[param_in][param_name] = widget
            
            
    def regenerate_test_data(self):
        """
        重新生成测试数据
        """
        if not self.api_info:
            return
            
        # 更新界面
        self.update_ui()
        
    def get_param_values(self):
        """
        获取参数值

        Returns:
            dict: 参数值字典
        """
        import logging
        logger = logging.getLogger(__name__)

        result = {
            'path_params': {},
            'query_params': {},
            'headers': {},
            'body': None
        }

        # 获取路径参数
        for param_name, widget in self.param_widgets.get('path', {}).items():
            result['path_params'][param_name] = self.get_widget_value(widget)

        # 获取查询参数（只获取勾选的参数）
        query_checkboxes = self.param_widgets.get('query_checkboxes', {})
        for param_name, widget in self.param_widgets.get('query', {}).items():
            # 检查是否有对应的勾选框
            if param_name in query_checkboxes:
                checkbox = query_checkboxes[param_name]
                # 只有勾选的参数才包含在结果中
                if checkbox.isChecked():
                    result['query_params'][param_name] = self.get_widget_value(widget)
            else:
                # 没有勾选框的参数直接包含
                result['query_params'][param_name] = self.get_widget_value(widget)

        # 获取自定义请求头
        result['headers'] = self.get_custom_headers()

        # 检查是否有请求体标签页可见（表示API支持请求体）
        # 仅当请求体标签页可见时才获取请求体内容
        if self.param_tabs.indexOf(self.body_param_tab) != -1:
            logger.debug(f"API方法: {method}, 请求体类型: JSON")
            try:
                json_text = self.json_editor.toPlainText()
                if json_text.strip():
                    result['body'] = json.loads(json_text)
                    logger.debug(f"获取JSON请求体: {result['body']}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON格式错误: {e}")
                QMessageBox.warning(self, "JSON格式错误", "请求体JSON格式不正确，请检查")

        # 记录最终结果用于调试
        logger.info(f"参数获取完成 - 路径参数: {result['path_params']}, 查询参数: {result['query_params']}, 请求头: {result['headers']}, 请求体: {result['body']}")

        return result
        
    def get_widget_value(self, widget):
        """
        获取控件的值
        
        Args:
            widget: 控件对象
            
        Returns:
            控件值
        """
        if isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, QTextEdit):
            text = widget.toPlainText()
            try:
                # 尝试解析JSON
                return json.loads(text)
            except:
                return text
        elif isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        elif isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
            return widget.value()
        else:
            return None
            
    def test_api(self):
        """
        测试API
        """
        if not self.api_info:
            return
            
        # 获取参数值
        custom_data = self.get_param_values()
        
        # 获取认证设置
        use_auth = self.use_auth_checkbox.isChecked()
        
        # 发送测试请求信号
        self.test_requested.emit({
            'api_info': self.api_info,
            'custom_data': custom_data,
            'use_auth': use_auth,
            'auth_type': 'bearer'  # 固定为bearer
        })
    
    def set_common_prefix(self, prefix):
        """
        设置公共前缀
        
        Args:
            prefix (str): 公共前缀
        """
        self.common_prefix = prefix
        # 如果已经有API信息，更新显示
        if self.api_info:
            self.update_ui()
    
    def _get_display_path(self, full_path):
        """
        获取显示路径（去除公共前缀）
        
        Args:
            full_path (str): 完整路径
            
        Returns:
            str: 显示路径
        """
        if self.common_prefix and full_path.startswith(self.common_prefix):
            # 去除公共前缀，但保留开头的 '/'
            display_path = full_path[len(self.common_prefix):]
            if not display_path.startswith('/'):
                display_path = '/' + display_path
            return display_path
        return full_path
    
    def copy_path(self):
        """
        复制路径到剪贴板
        """
        if self.api_info:
            full_path = self.api_info.get('path', '')
            QApplication.clipboard().setText(full_path)
            # 临时改变按钮文本以提供反馈
            self.copy_path_button.setText("已复制")
            # 1秒后恢复按钮文本
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1000, lambda: self.copy_path_button.setText("复制"))
    
    def load_custom_data(self, custom_data):
        """
        加载自定义数据到参数控件
        
        Args:
            custom_data (dict): 自定义数据
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not custom_data:
            logger.warning("自定义数据为空")
            return
            
        logger.info("开始加载自定义数据到参数控件")
        logger.debug(f"当前参数控件: {self.param_widgets}")
        
        # 加载路径参数
        for param_name, value in custom_data.get('path_params', {}).items():
            if param_name in self.param_widgets.get('path', {}):
                logger.debug(f"设置路径参数: {param_name} = {value}")
                self.set_widget_value(self.param_widgets['path'][param_name], value)
            else:
                logger.warning(f"路径参数 {param_name} 未找到对应控件")
                
        # 加载查询参数
        query_checkboxes = self.param_widgets.get('query_checkboxes', {})
        # 首先设置所有查询参数的勾选框状态
        for param_name, checkbox in query_checkboxes.items():
            # 如果历史数据中有该参数，则勾选；否则取消勾选
            checkbox.setChecked(param_name in custom_data.get('query_params', {}))
        
        # 然后设置参数值
        for param_name, value in custom_data.get('query_params', {}).items():
            if param_name in self.param_widgets.get('query', {}):
                logger.debug(f"设置查询参数: {param_name} = {value}")
                self.set_widget_value(self.param_widgets['query'][param_name], value)
            else:
                logger.warning(f"查询参数 {param_name} 未找到对应控件")
                
        # 加载自定义请求头
        for param_name, value in custom_data.get('headers', {}).items():
            logger.debug(f"添加自定义请求头: {param_name} = {value}")
            header_widget = self.create_custom_header_widget(param_name, value)
            self.custom_headers_container_layout.addWidget(header_widget)
            self.custom_headers.append(header_widget)
                
        # 加载请求体
        body = custom_data.get('body')
        if body is not None:
            logger.debug(f"设置请求体: {body}")
            if isinstance(body, (dict, list)):
                self.json_editor.setText(json.dumps(body, ensure_ascii=False, indent=2))
            elif isinstance(body, str):
                # 尝试解析为JSON
                try:
                    json_body = json.loads(body)
                    self.json_editor.setText(json.dumps(json_body, ensure_ascii=False, indent=2))
                except:
                    # 如果不是有效的JSON，直接显示文本
                    self.json_editor.setText(body)
                
    def set_widget_value(self, widget, value):
        """
        设置控件的值
        
        Args:
            widget: 控件对象
            value: 要设置的值
        """
        if isinstance(widget, QLineEdit):
            widget.setText(str(value) if value is not None else "")
        elif isinstance(widget, QTextEdit):
            if isinstance(value, (dict, list)):
                widget.setText(json.dumps(value, ensure_ascii=False, indent=2))
            else:
                widget.setText(str(value) if value is not None else "")
        elif isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QComboBox):
            index = widget.findText(str(value))
            if index >= 0:
                widget.setCurrentIndex(index)
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            try:
                widget.setValue(float(value))
            except:
                pass
    
    def build_request_data(self):
        """
        构建请求数据（不实际发送请求）
        
        Returns:
            dict: 包含请求信息的字典
        """
        if not self.api_info or not self.swagger_parser:
            return None
            
        # 获取参数值
        custom_data = self.get_param_values()
        
        # 构建请求URL
        base_url = self.swagger_parser.get_base_url()
        api_path = self.api_info.get('path', '')
        
        # 替换路径参数
        for param_name, param_value in custom_data.get('path_params', {}).items():
            api_path = api_path.replace(f'{{{param_name}}}', str(param_value))
        
        url = f"{base_url}{api_path}"
        
        # 构建请求对象
        request_data = {
            'url': url,
            'method': self.api_info.get('method', 'GET').upper(),
            'headers': custom_data.get('headers', {}),
            'params': custom_data.get('query_params', {}),
            'data': custom_data.get('body')
        }
        
        # 构建模拟的测试结果对象
        test_result = {
            'api': self.api_info,
            'request': request_data,
            'custom_data': custom_data,
            'use_auth': self.use_auth_checkbox.isChecked(),
            'auth_type': 'bearer'  # 固定为bearer
        }
        
        return test_result
    
    def export_as_curl(self):
        """
        导出为cURL命令
        """
        try:
            test_result = self.build_request_data()
            if test_result:
                self.export_curl_requested.emit(test_result, self.export_curl_button)
        except Exception as e:
            import logging
            logging.error(f"导出cURL 时出错: {e}", exc_info=True)
            QMessageBox.warning(self, "导出错误", f"导出 cURL 命令时出错: {str(e)}")
