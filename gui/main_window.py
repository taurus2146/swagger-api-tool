#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主窗口模块 - 集成所有功能
"""

import json
import logging
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFileDialog, QSplitter, QTabWidget, QStatusBar, QAction, QMessageBox, QInputDialog, QMenu
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QCursor

from core.swagger_parser import SwaggerParser
from core.auth_manager import AuthManager
from core.api_tester import ApiTester

from .api_list_widget import ApiListWidget
from .api_param_editor import ApiParamEditor
from .test_result_widget import TestResultWidget
from .auth_config_dialog_login import AuthConfigDialog
from .styles import get_stylesheet
from .api_test_thread import ApiTestThread
from .icon_generator import get_app_icon
from .theme_manager import theme_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """应用程序主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Swagger API测试工具")
        self.resize(1200, 800)
        
        # 设置现代化图标
        self.setWindowIcon(get_app_icon())

        # 核心对象
        self.swagger_parser = SwaggerParser()
        self.auth_manager = AuthManager()
        self.api_tester = ApiTester(auth_manager=self.auth_manager)
        
        # 确保数据生成器可以访问Swagger数据
        self.param_editor = None  # 将在_build_ui中初始化
        
        # 测试线程
        self.test_thread = None

        self._build_ui()
        self._load_settings()
        
        # 应用主题样式
        self._apply_theme()

    # ------------------------- UI 构建 ------------------------- #
    def _build_ui(self):
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # 顶部栏
        top_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入Swagger文档URL …")
        top_layout.addWidget(self.url_input)

        btn_load_url = QPushButton("加载URL")
        btn_load_url.clicked.connect(self._load_from_url)
        top_layout.addWidget(btn_load_url)

        btn_load_file = QPushButton("加载文件")
        btn_load_file.clicked.connect(self._load_from_file)
        top_layout.addWidget(btn_load_file)

        btn_auth = QPushButton("认证配置")
        btn_auth.clicked.connect(self._show_auth_dialog)
        top_layout.addWidget(btn_auth)

        main_layout.addLayout(top_layout)

        # 中间分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        self.splitter = splitter

        # 左侧 API 列表
        self.api_list_widget = ApiListWidget()
        splitter.addWidget(self.api_list_widget)

        # 右侧 tab
        right_tabs = QTabWidget()
        splitter.addWidget(right_tabs)
        self.right_tabs = right_tabs

        # 参数编辑器
        self.param_editor = ApiParamEditor()
        # 在参数编辑器中设置Swagger解析器，以便它可以访问Swagger数据
        self.param_editor.set_swagger_parser(self.swagger_parser)
        right_tabs.addTab(self.param_editor, "参数编辑")

        # 测试结果
        self.result_widget = TestResultWidget()
        right_tabs.addTab(self.result_widget, "测试结果")

        # 连接信号
        self.api_list_widget.api_selected.connect(self._on_api_selected)  # 使用统一的处理函数
        self.api_list_widget.export_apis_requested.connect(self._export_api_list)
        self.param_editor.test_requested.connect(self._test_with_params)
        self.param_editor.export_curl_requested.connect(self._export_curl)
        self.param_editor.export_postman_requested.connect(self._export_postman)
        self.result_widget.export_curl_requested.connect(self._export_curl)
        self.result_widget.export_postman_requested.connect(self._export_postman)
        self.result_widget.history_selected.connect(self._on_history_selected)

        # 状态栏
        status = QStatusBar()
        self.setStatusBar(status)
        self.status_label = QLabel("就绪")
        status.addWidget(self.status_label)

        # 菜单
        self._build_menu()
        
        # 连接重新发送信号
        self.result_widget.resend_requested.connect(self._resend_request)

    def _build_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        file_menu.addAction("从URL加载", self._load_from_url)
        file_menu.addAction("从文件加载", self._load_from_file)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

        tools_menu = menu_bar.addMenu("工具")
        tools_menu.addAction("认证配置", self._show_auth_dialog)
        tools_menu.addAction("清空历史", self.result_widget.clear_history)
        
        # 主题菜单
        theme_menu = menu_bar.addMenu("主题")
        theme_menu.addAction("主题预览", self._show_theme_preview)
        theme_menu.addSeparator()
        self._build_theme_menu(theme_menu)

    # ------------------------- Swagger 加载 ------------------------- #
    def _load_from_url(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "提示", "请输入URL")
            return
        self.status_label.setText("正在加载 URL …")
        QApplication.processEvents()
        if self.swagger_parser.load_from_url(url):
            self._after_doc_loaded()
        else:
            QMessageBox.warning(self, "错误", "加载失败，请检查网址或网络")
        self.status_label.setText("就绪")

    def _load_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择Swagger文档", "", "Swagger 文件 (*.json *.yaml *.yml)")
        if not file_path:
            return
        self.status_label.setText("正在加载文件 …")
        QApplication.processEvents()
        if self.swagger_parser.load_from_file(file_path):
            self._after_doc_loaded()
        else:
            QMessageBox.warning(self, "错误", "文件格式不正确或无法读取")
        self.status_label.setText("就绪")

    def _after_doc_loaded(self):
        apis = self.swagger_parser.get_api_list()
        self.api_list_widget.set_api_list(apis)
        self.api_tester.set_base_url(self.swagger_parser.get_base_url())
        
        # 将公共前缀传递给参数编辑器
        if hasattr(self.api_list_widget, 'common_prefix'):
            self.param_editor.set_common_prefix(self.api_list_widget.common_prefix)
        
        self.status_label.setText(f"已加载 {len(apis)} 个接口")

    # ------------------------- API选择处理 ------------------------- #
    def _on_api_selected(self, api_info):
        """
        当选择API时的统一处理函数
        
        Args:
            api_info (dict): API信息
        """
        # 更新参数编辑器
        self.param_editor.set_api(api_info)
        
        # 更新测试结果组件的当前API
        self.result_widget.set_current_api(api_info)
        
        # 切换到参数编辑标签页
        self.right_tabs.setCurrentWidget(self.param_editor)

    # ------------------------- 测试执行 ------------------------- #
    def _test_with_params(self, payload):
        api_info = payload['api_info']
        custom_data = payload['custom_data']
        use_auth = payload['use_auth']
        auth_type = payload['auth_type']
        self._run_test(api_info, custom_data, use_auth, auth_type)

    def _run_test(self, api_info, custom_data=None, use_auth=True, auth_type="bearer"):
        # 立即切换到结果页面
        self.right_tabs.setCurrentWidget(self.result_widget)
        
        # 显示加载状态
        self.result_widget.show_loading_state()
        self.status_label.setText("测试中 …")
        
        # 禁用测试按钮，避免重复点击
        if hasattr(self.param_editor, 'test_button'):
            self.param_editor.test_button.setEnabled(False)
        
        # 如果有旧的线程在运行，先停止它
        if self.test_thread and self.test_thread.isRunning():
            self.test_thread.quit()
            self.test_thread.wait()
        
        # 创建新的测试线程
        self.test_thread = ApiTestThread(self.api_tester, self)
        self.test_thread.set_test_params(api_info, custom_data, use_auth, auth_type)
        
        # 连接信号
        self.test_thread.test_completed.connect(self._on_test_completed)
        self.test_thread.test_error.connect(self._on_test_error)
        
        # 启动线程
        self.test_thread.start()
    
    def _on_test_completed(self, result):
        """测试完成的处理"""
        self.result_widget.display_test_result(result)
        self.status_label.setText("测试完成")
        
        # 重新启用测试按钮
        if hasattr(self.param_editor, 'test_button'):
            self.param_editor.test_button.setEnabled(True)
    
    def _on_test_error(self, error_msg):
        """测试错误的处理"""
        self.result_widget.show_error(error_msg)
        self.status_label.setText("测试失败")
        
        # 重新启用测试按钮
        if hasattr(self.param_editor, 'test_button'):
            self.param_editor.test_button.setEnabled(True)

    # ------------------------- 认证配置 ------------------------- #
    def _show_auth_dialog(self):
        # 获取当前加载的API列表
        api_list = self.swagger_parser.get_api_list() if self.swagger_parser else []
        dlg = AuthConfigDialog(self.auth_manager, self, api_list)
        dlg.exec_()
        
    def _on_history_selected(self, test_result):
        """
        当选择历史记录时的处理
        
        Args:
            test_result (dict): 历史测试结果
        """
        logger.info(f"历史记录被选中: {test_result.get('api', {}).get('path', 'Unknown')}")
        logger.debug(f"历史测试数据: custom_data={test_result.get('custom_data')}, use_auth={test_result.get('use_auth')}, auth_type={test_result.get('auth_type')}")
        
        api_info = test_result.get('api')
        if api_info:
            # 切换到参数编辑标签页
            self.right_tabs.setCurrentWidget(self.param_editor)
            # 设置API信息并回显历史数据
            self.param_editor.set_api_with_history_data(api_info, test_result)
    
    def _resend_request(self, test_result):
        """处理重新发送请求的逻辑"""
        logger.info(f"重新发送请求: {test_result.get('api', {}).get('path', 'Unknown')}")
        api_info = test_result.get('api')
        if api_info:
            custom_data = test_result.get('custom_data')
            use_auth = test_result.get('use_auth', True)
            auth_type = test_result.get('auth_type', "bearer")
            self._run_test(api_info, custom_data, use_auth, auth_type)

    # ------------------------- 导出 ------------------------- #
    def _export_curl(self, result, button=None):
        try:
            curl = self.api_tester.generate_curl_command(result)
            if not curl:
                QMessageBox.warning(self, "错误", "无法生成cURL")
                return
            # 直接复制到剪贴板
            QApplication.clipboard().setText(curl)
            # 在按钮上显示提示
            if button:
                self._show_button_feedback(button, "已复制", "导出为cURL")
        except Exception as e:
            logger.error(f"导出cURL时出错: {e}", exc_info=True)
            QMessageBox.warning(self, "导出错误", f"导出 cURL 命令时出错: {str(e)}")

    def _export_postman(self, results):
        try:
            name, ok = QInputDialog.getText(self, "Postman集合", "集合名称：", text="API Tests")
            if not ok or not name:
                return
            collection = self.api_tester.generate_postman_collection(results, name)
            path, _ = QFileDialog.getSaveFileName(self, "保存集合", f"{name}.json", "JSON 文件 (*.json)")
            if not path:
                return
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(collection, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "成功", "已导出 Postman 集合")
            except Exception as e:
                QMessageBox.warning(self, "失败", str(e))
        except Exception as e:
            logger.error(f"导出Postman时出错: {e}", exc_info=True)
            QMessageBox.warning(self, "导出错误", f"导出 Postman 集合时出错: {str(e)}")
    
    def _export_api_list(self, api_list):
        """
        导出API列表
        
        Args:
            api_list (list): 要导出的API列表
        """
        if not api_list:
            QMessageBox.warning(self, "提示", "没有可导出的API")
            return
            
        # 直接导出为Swagger JSON
        self._export_as_swagger(api_list)
    
    def _export_as_swagger(self, api_list):
        """导出为 Swagger JSON"""
        try:
            path, _ = QFileDialog.getSaveFileName(self, "保存 Swagger 文档", "filtered_apis.json", "JSON 文件 (*.json)")
            if not path:
                return
                
            # 构建简化的 Swagger 文档
            swagger_doc = {
                "openapi": "3.0.0",
                "info": {
                    "title": "Filtered APIs",
                    "version": "1.0.0"
                },
                "paths": {}
            }
            
            for api in api_list:
                path_key = api.get('path', '')
                method = api.get('method', 'get').lower()
                
                if path_key not in swagger_doc["paths"]:
                    swagger_doc["paths"][path_key] = {}
                    
                swagger_doc["paths"][path_key][method] = {
                    "summary": api.get('summary', ''),
                    "description": api.get('description', ''),
                    "tags": api.get('tags', []),
                    "operationId": api.get('operationId', ''),
                    "parameters": api.get('parameters', []),
                    "requestBody": api.get('requestBody', {}),
                    "responses": api.get('responses', {})
                }
                
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(swagger_doc, f, ensure_ascii=False, indent=2)
                
            QMessageBox.information(self, "成功", f"已导出 {len(api_list)} 个API到 Swagger 文档")
            
        except Exception as e:
            logger.error(f"导出 Swagger 时出错: {e}", exc_info=True)
            QMessageBox.warning(self, "导出错误", f"导出 Swagger 文档时出错: {str(e)}")

    # ------------------------- 设置保存/恢复 ------------------------- #
    def _load_settings(self):
        s = QSettings("swagger-api-tool", "app")
        self.url_input.setText(s.value("last_url", ""))
        geo = s.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        split = s.value("splitter")
        if split:
            self.splitter.restoreState(split)

    def closeEvent(self, event):
        s = QSettings("swagger-api-tool", "app")
        s.setValue("last_url", self.url_input.text())
        s.setValue("geometry", self.saveGeometry())
        s.setValue("splitter", self.splitter.saveState())
        super().closeEvent(event)
    
    def _show_button_feedback(self, button, temp_text, original_text):
        """
        在按钮上显示临时反馈文本
        
        Args:
            button: 按钮对象
            temp_text: 临时显示的文本
            original_text: 原始文本
        """
        button.setText(temp_text)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, lambda: button.setText(original_text))
    
    # ------------------------- 主题管理 ------------------------- #
    def _build_theme_menu(self, theme_menu):
        """构建主题菜单"""
        from PyQt5.QtWidgets import QActionGroup
        
        # 创建动作组，确保只能选择一个主题
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        
        current_theme = theme_manager.get_current_theme_name()
        
        for theme_name in theme_manager.get_theme_names():
            display_name = theme_manager.get_theme_display_name(theme_name)
            action = theme_menu.addAction(display_name)
            action.setCheckable(True)
            action.setChecked(theme_name == current_theme)
            action.setData(theme_name)  # 存储主题名称
            action.triggered.connect(lambda checked, name=theme_name: self._change_theme(name))
            theme_group.addAction(action)
    
    def _change_theme(self, theme_name):
        """切换主题"""
        try:
            # 保存主题偏好
            theme_manager.save_theme_preference(theme_name)
            
            # 应用新主题
            self._apply_theme()
            
            # 显示切换成功消息
            display_name = theme_manager.get_theme_display_name(theme_name)
            self.status_label.setText(f"已切换到{display_name}")
            
            # 2秒后恢复状态栏
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.status_label.setText("就绪"))
            
        except Exception as e:
            logger.error(f"切换主题时出错: {e}", exc_info=True)
            QMessageBox.warning(self, "主题切换失败", f"切换主题时出错: {str(e)}")
    
    def _apply_theme(self):
        """应用当前主题"""
        try:
            stylesheet = theme_manager.get_stylesheet()
            self.setStyleSheet(stylesheet)
            logger.info(f"已应用主题: {theme_manager.get_current_theme_name()}")
        except Exception as e:
            logger.error(f"应用主题时出错: {e}", exc_info=True)
            # 如果主题应用失败，回退到默认样式
            self.setStyleSheet(get_stylesheet())
    
    def _show_theme_preview(self):
        """显示主题预览对话框"""
        try:
            from .theme_preview_dialog import show_theme_preview
            show_theme_preview(self)
        except Exception as e:
            logger.error(f"显示主题预览时出错: {e}", exc_info=True)
            QMessageBox.warning(self, "错误", f"显示主题预览时出错: {str(e)}")

