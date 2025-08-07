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
from PyQt5.QtCore import Qt, QSettings, QTimer
from PyQt5.QtGui import QCursor

from core.swagger_parser import SwaggerParser
from core.auth_manager import AuthManager
from core.api_tester import ApiTester
from core.project_manager import ProjectManager
from core.project_models import SwaggerSource, Project

from .api_list_widget import ApiListWidget
from .api_param_editor import ApiParamEditor
from .test_result_widget import TestResultWidget
from .auth_config_dialog_login import AuthConfigDialog
from .project_selector_dialog import ProjectSelectorDialog
from .project_edit_dialog import ProjectEditDialog
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
        self.project_manager = ProjectManager()
        self.swagger_parser = SwaggerParser(db_manager=self.project_manager.db_manager)
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
        
        # 自动加载上次的项目状态
        self._restore_last_project_state()

    # ------------------------- UI 构建 ------------------------- #
    def _build_ui(self):
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # 顶部栏
        top_layout = QHBoxLayout()
        
        # 项目管理区域
        project_layout = QHBoxLayout()
        
        # 当前项目显示
        self.current_project_label = QLabel("无项目")
        self.current_project_label.setStyleSheet("font-weight: bold; color: #2196F3; padding: 5px;")
        project_layout.addWidget(QLabel("当前项目:"))
        project_layout.addWidget(self.current_project_label)
        
        # 项目管理按钮
        self.project_menu_btn = QPushButton("项目管理 ▼")
        self.project_menu_btn.clicked.connect(self._show_project_selector)
        project_layout.addWidget(self.project_menu_btn)
        
        top_layout.addLayout(project_layout)
        top_layout.addWidget(QLabel("|"))  # 分隔符
        
        # Swagger文档加载区域
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入Swagger文档URL …")
        top_layout.addWidget(self.url_input)

        btn_load_url = QPushButton("加载URL")
        btn_load_url.clicked.connect(lambda: self._load_from_url(use_cache=True))
        btn_load_url.setToolTip("优先从缓存加载，缓存不存在时从URL加载")
        top_layout.addWidget(btn_load_url)

        btn_force_refresh = QPushButton("强制刷新")
        btn_force_refresh.clicked.connect(lambda: self._load_from_url(use_cache=False))
        btn_force_refresh.setToolTip("跳过缓存，直接从URL重新加载最新文档")
        btn_force_refresh.setStyleSheet("QPushButton { color: #ff6b35; font-weight: bold; }")
        top_layout.addWidget(btn_force_refresh)

        btn_load_file = QPushButton("加载文件")
        btn_load_file.clicked.connect(lambda: self._load_from_file())
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
        self.result_widget = TestResultWidget(project_manager=self.project_manager)
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
        
        # 数据库状态显示
        status.addPermanentWidget(QLabel("|"))
        self.db_status_label = QLabel("数据库: 连接中...")
        self.db_status_label.setStyleSheet("color: #666;")
        status.addPermanentWidget(self.db_status_label)
        
        # 更新数据库状态
        self._update_database_status()

        # 菜单
        self._build_menu()

        # 设置快捷键
        self._setup_shortcuts()

        # 连接重新发送信号
        self.result_widget.resend_requested.connect(self._resend_request)

    def _build_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        file_menu.addAction("从URL加载", lambda: self._load_from_url(use_cache=True))
        file_menu.addAction("从文件加载", lambda: self._load_from_file())
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

        # 项目菜单
        project_menu = menu_bar.addMenu("项目")
        project_menu.addAction("项目管理", self._show_project_selector)
        project_menu.addAction("保存当前为项目", self._save_current_as_project)
        project_menu.addSeparator()
        
        # 最近使用项目子菜单
        self.recent_projects_menu = project_menu.addMenu("最近使用")
        self._update_recent_projects_menu()
        
        tools_menu = menu_bar.addMenu("工具")
        tools_menu.addAction("认证配置", self._show_auth_dialog)
        tools_menu.addAction("数据库路径", self._show_database_path_dialog)
        tools_menu.addAction("清空历史", self.result_widget.clear_history)
        
        # 主题菜单
        theme_menu = menu_bar.addMenu("主题")
        theme_menu.addAction("主题预览", self._show_theme_preview)
        theme_menu.addSeparator()
        self._build_theme_menu(theme_menu)

    def _setup_shortcuts(self):
        """设置快捷键"""
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence

        # F5: 普通加载（缓存优先）
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(lambda: self._load_from_url(use_cache=True))

        # Ctrl+F5: 强制刷新
        force_refresh_shortcut = QShortcut(QKeySequence("Ctrl+F5"), self)
        force_refresh_shortcut.activated.connect(lambda: self._load_from_url(use_cache=False))

    # ------------------------- Swagger 加载 ------------------------- #
    def _load_from_url(self, url=None, use_cache=False):
        """
        从URL加载Swagger文档

        Args:
            url: Swagger文档URL
            use_cache: 是否优先使用缓存（默认False，直接从URL加载）
        """
        if url is None:
            url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "提示", "请输入URL")
            return

        if use_cache:
            self.status_label.setText("正在加载（优先缓存）...")
        else:
            self.status_label.setText("正在从URL加载最新文档...")

        QApplication.processEvents()

        # 根据use_cache参数决定是否跳过缓存
        force_refresh = not use_cache
        if self.swagger_parser.load_from_url(url, force_refresh=force_refresh):
            self._after_doc_loaded(source_type="url", location=url)
        else:
            QMessageBox.warning(self, "错误", "加载失败，请检查网址或网络")

        self.status_label.setText("就绪")

    def _load_from_cache_first(self, url=None):
        """缓存优先加载：优先从缓存加载，缓存不存在时从URL加载"""
        if url is None:
            url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "提示", "请输入URL")
            return

        # 使用缓存优先的加载方式
        self._load_from_url(url, use_cache=True)

    def _force_refresh_from_url(self, url=None):
        """强制刷新：跳过缓存，直接从URL加载最新文档（保持向后兼容）"""
        self._load_from_url(url, use_cache=False)

    def _load_from_file(self, file_path=None):
        if file_path is None:
            file_path, _ = QFileDialog.getOpenFileName(self, "选择Swagger文档", "", "Swagger 文件 (*.json *.yaml *.yml)")
        if not file_path:
            return
        self.status_label.setText("正在加载文件 …")
        QApplication.processEvents()
        if self.swagger_parser.load_from_file(file_path):
            self._after_doc_loaded(source_type="file", location=file_path)
        else:
            QMessageBox.warning(self, "错误", "文件格式不正确或无法读取")
        self.status_label.setText("就绪")

    def _after_doc_loaded(self, source_type: str, location: str, from_cache: bool = False, force_refreshed: bool = False):
        apis = self.swagger_parser.get_api_list()
        self.api_list_widget.set_api_list(apis)

        # 显示加载状态
        if force_refreshed:
            self.status_label.setText(f"✅ 强制刷新完成，已加载 {len(apis)} 个API")
            self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
            # 3秒后恢复默认样式
            QTimer.singleShot(3000, lambda: self.status_label.setStyleSheet(""))
        elif from_cache:
            self.status_label.setText(f"已从缓存加载 {len(apis)} 个API")
        else:
            self.status_label.setText(f"已加载 {len(apis)} 个API")
        
        # 检查是否需要提示保存为项目
        current_project = self.project_manager.get_current_project()
        should_prompt_save = False

        # 优先使用项目的基础URL，如果项目没有设置基础URL，则使用Swagger文档的基础URL
        if current_project and current_project.base_url:
            # 使用项目设置的基础URL
            self.api_tester.set_base_url(current_project.base_url)
            logger.info(f"使用项目基础URL: {current_project.base_url}")
        else:
            # 使用Swagger文档的基础URL
            swagger_base_url = self.swagger_parser.get_base_url()
            self.api_tester.set_base_url(swagger_base_url)
            logger.info(f"使用Swagger文档基础URL: {swagger_base_url}")

        if hasattr(self.api_list_widget, 'common_prefix'):
            self.param_editor.set_common_prefix(self.api_list_widget.common_prefix)

        self.status_label.setText(f"已加载 {len(apis)} 个接口")

        if not current_project:
            # 没有当前项目，提示保存（但不包括从缓存加载的情况）
            if not from_cache:
                should_prompt_save = True
        else:
            # 有当前项目，检查加载的源是否与当前项目匹配
            if (current_project.swagger_source.type != source_type or
                current_project.swagger_source.location != location):
                # 加载的源与当前项目不匹配，提示保存为新项目（但不包括从缓存加载的情况）
                if not from_cache:
                    should_prompt_save = True
            else:
                # 匹配当前项目，更新API数量
                current_project.api_count = len(apis)
                self.project_manager.update_project(current_project)

        # 提示保存为项目
        if should_prompt_save:
            self._prompt_save_as_project(source_type, location)

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
        if dlg.exec_() == dlg.Accepted:
            # 认证配置修改后，保存到当前项目
            self._save_current_auth_to_project()

    def _save_current_auth_to_project(self):
        """保存当前认证配置到项目"""
        current_project = self.project_manager.get_current_project()
        if current_project:
            # 获取当前的认证配置
            current_auth_config = self.auth_manager.get_config()

            # 更新项目的认证配置
            current_project.auth_config = current_auth_config

            # 保存项目
            if self.project_manager.update_project(current_project):
                logger.info(f"已保存认证配置到项目: {current_project.name}")
            else:
                logger.error(f"保存认证配置到项目失败: {current_project.name}")




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

    # ------------------------- 项目管理 ------------------------- #
    def _show_project_selector(self):
        """显示项目选择器"""
        dialog = ProjectSelectorDialog(self.project_manager, self)
        dialog.project_selected.connect(self._load_project)
        dialog.project_updated.connect(self._update_current_project_display)
        dialog.exec_()

    def _load_project(self, project_id: str):
        """加载项目"""
        # 在切换项目前，保存当前项目的认证配置
        self._save_current_auth_to_project()

        project = self.project_manager.set_current_project(project_id)
        if project:
            self.current_project_label.setText(project.name)
            self.setWindowTitle(f"Swagger API测试工具 - {project.name}")

            # 设置测试结果组件的项目ID
            self.result_widget.set_project_id(project_id)

            # 设置SwaggerParser的项目ID以启用缓存
            self.swagger_parser.project_id = project_id

            # 更新URL输入框为Swagger文档地址
            if project.swagger_source.type == "url":
                # 如果是URL来源，显示Swagger文档URL
                self.url_input.setText(project.swagger_source.location)
            else:
                # 文件来源，清空URL输入框
                self.url_input.clear()

            # 设置项目的基础URL（如果有的话）
            if project.base_url:
                self.api_tester.set_base_url(project.base_url)
                logger.info(f"加载项目时设置基础URL: {project.base_url}")

            # 优先尝试从缓存加载Swagger文档
            cache_loaded = False
            if self.swagger_parser.is_cache_available():
                self.status_label.setText("从缓存加载Swagger文档...")
                QApplication.processEvents()
                if self.swagger_parser.load_from_cache():
                    cache_loaded = True
                    # 使用项目的原始源信息，而不是"缓存"
                    self._after_doc_loaded(
                        source_type=project.swagger_source.type,
                        location=project.swagger_source.location,
                        from_cache=True  # 添加标记表示来自缓存
                    )
                    logger.info("从缓存成功加载Swagger文档")

            # 如果缓存加载失败，从原始源加载
            if not cache_loaded:
                if project.swagger_source.type == "url":
                    self._load_from_url(project.swagger_source.location)
                else:
                    self._load_from_file(project.swagger_source.location)

            # 恢复认证配置
            if project.auth_config:
                self.auth_manager.set_config(project.auth_config)
                logger.info(f"已加载项目认证配置: {list(project.auth_config.keys())}")
            else:
                # 如果项目没有认证配置，清空当前配置
                self.auth_manager.set_config({})
                logger.info("项目无认证配置，已清空当前认证配置")

            self._update_recent_projects_menu()

    def _save_current_as_project(self):
        """将当前配置保存为项目"""
        # 实现保存当前配置为项目的逻辑
        pass
    
    def _prompt_save_as_project(self, source_type: str, location: str):
        """提示用户保存为项目"""
        reply = QMessageBox.question(self, "保存项目", "是否要将当前配置保存为一个新项目？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            # 自动带入 SwaggerSource 和 baseUrl
            swagger_source = SwaggerSource(type=source_type, location=location)
            base_url = self.swagger_parser.get_base_url() or ""
            
            # 从location中提取一个建议的项目名称
            suggested_name = ""
            if source_type == "url":
                # 从URL中提取域名作为建议名称
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(location)
                    suggested_name = parsed.netloc or "API项目"
                except:
                    suggested_name = "API项目"
            else:
                # 从文件路径中提取文件名（不含扩展名）作为建议名称
                import os
                suggested_name = os.path.splitext(os.path.basename(location))[0] or "API项目"
            
            # 获取当前加载的API数量
            api_count = len(self.swagger_parser.get_api_list()) if self.swagger_parser else 0
            
            # 创建预填充的项目对象
            project = Project.create_new(
                name=suggested_name,
                description=f"从 {location} 导入的API项目",
                swagger_source=swagger_source,
                base_url=base_url
            )
            project.api_count = api_count
            
            dialog = ProjectEditDialog(project=project, parent=self)
            dialog.project_saved.connect(self._on_project_saved)
            dialog.exec_()

    def _on_project_saved(self, project):
        """项目保存后的处理"""
        # 先将项目添加到项目管理器的内存中（新项目或更新现有项目）
        self.project_manager.projects[project.id] = project
        # 然后保存到磁盘
        self.project_manager.storage.save_project(project)
        
        self.current_project_label.setText(project.name)
        self.setWindowTitle(f"Swagger API测试工具 - {project.name}")
        self.project_manager.set_current_project(project.id)
        self._update_recent_projects_menu()
        
        # 设置测试结果组件的项目ID
        self.result_widget.set_project_id(project.id)
        
        # 如果保存的项目有基础URL，立即应用它
        if project.base_url:
            self.api_tester.set_base_url(project.base_url)
            logger.info(f"项目保存后应用基础URL: {project.base_url}")
        
    def _show_project_menu(self):
        """显示项目管理菜单"""
        menu = QMenu(self)
        menu.addAction("项目管理...", self._show_project_selector)
        menu.addAction("保存当前为项目", self._save_current_as_project)
        menu.addSeparator()
        self._update_recent_projects_menu(menu)
        menu.exec_(QCursor.pos())

    def _update_recent_projects_menu(self, menu=None):
        """更新最近使用项目菜单"""
        if menu is None:
            menu = self.recent_projects_menu
            
        menu.clear()
        recent_projects = self.project_manager.get_recent_projects()
        for project in recent_projects:
            action = QAction(project.name, self)
            action.triggered.connect(lambda checked, pid=project.id: self._load_project(pid))
            menu.addAction(action)
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
    
    def _restore_last_project_state(self):
        """恢复上次的项目状态"""
        s = QSettings("swagger-api-tool", "app")
        last_project_id = s.value("last_project_id", "")
        
        if last_project_id:
            logger.info(f"尝试恢复上次的项目: {last_project_id}")
            # 使用项目管理器加载当前项目
            if self.project_manager.set_current_project(last_project_id):
                project = self.project_manager.get_current_project()
                if project:
                    logger.info(f"成功恢复项目: {project.name}")
                    self.current_project_label.setText(project.name)
                    self.setWindowTitle(f"Swagger API测试工具 - {project.name}")
                    
                    # 设置测试结果组件的项目ID
                    self.result_widget.set_project_id(project.id)

                    # 设置SwaggerParser的项目ID以启用缓存
                    self.swagger_parser.project_id = project.id

                    # 更新URL输入框为Swagger文档地址
                    if project.swagger_source.type == "url":
                        # 如果是URL来源，显示Swagger文档URL
                        self.url_input.setText(project.swagger_source.location)
                    else:
                        # 文件来源，清空URL输入框
                        self.url_input.clear()

                    try:
                        # 优先尝试从缓存加载Swagger文档
                        cache_loaded = False
                        if self.swagger_parser.is_cache_available():
                            self.status_label.setText("从缓存加载Swagger文档...")
                            QApplication.processEvents()
                            if self.swagger_parser.load_from_cache():
                                cache_loaded = True
                                # 使用项目的原始源信息，而不是"缓存"
                                self._after_doc_loaded(
                                    source_type=project.swagger_source.type,
                                    location=project.swagger_source.location,
                                    from_cache=True  # 添加标记表示来自缓存
                                )
                                logger.info("启动时从缓存成功加载Swagger文档")

                        # 如果缓存加载失败，从原始源加载
                        if not cache_loaded:
                            if project.swagger_source.type == "url":
                                self._load_from_url(project.swagger_source.location)
                            else:
                                self._load_from_file(project.swagger_source.location)

                        # 加载认证信息
                        if project.auth_config:
                            self.auth_manager.set_config(project.auth_config)
                            logger.info(f"启动时已加载项目认证配置: {list(project.auth_config.keys())}")
                        else:
                            # 如果项目没有认证配置，清空当前配置
                            self.auth_manager.set_config({})
                            logger.info("启动时项目无认证配置，已清空当前认证配置")

                        # 更新最近使用项目菜单
                        self._update_recent_projects_menu()

                        if cache_loaded:
                            self.status_label.setText(f"已从缓存加载项目: {project.name}")
                        else:
                            self.status_label.setText(f"已自动加载项目: {project.name}")

                    except Exception as e:
                        logger.error(f"恢复项目时出错: {e}", exc_info=True)
                        self.status_label.setText(f"项目恢复失败: {str(e)}")
                else:
                    logger.warning(f"项目ID {last_project_id} 对应的项目不存在")
            else:
                logger.warning(f"无法设置项目ID {last_project_id} 为当前项目")

    def closeEvent(self, event):
        s = QSettings("swagger-api-tool", "app")
        s.setValue("last_url", self.url_input.text())
        s.setValue("geometry", self.saveGeometry())
        s.setValue("splitter", self.splitter.saveState())
        
        # 保存当前项目ID
        current_project = self.project_manager.get_current_project()
        if current_project:
            s.setValue("last_project_id", current_project.id)
            logger.info(f"保存最后使用的项目ID: {current_project.id}")
        else:
            s.setValue("last_project_id", "")
            logger.info("清空最后使用的项目ID")
        
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
            self._update_title_bar_color()
            logger.info(f"已应用主题: {theme_manager.get_current_theme_name()}")
        except Exception as e:
            logger.error(f"应用主题时出错: {e}", exc_info=True)
            # 如果主题应用失败，回退到默认样式
            self.setStyleSheet(get_stylesheet())

    def _update_title_bar_color(self):
        """更新标题栏颜色（仅在 Windows 10/11 有效）"""
        try:
            import ctypes
            color = theme_manager.get_title_bar_color()
            # Convert color to RGB int
            color_int = int(color.lstrip('#'), 16)
            # Set the color for Windows title bar (only works on Windows 10/11)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                int(self.winId()), 35, ctypes.byref(ctypes.c_int(color_int)), ctypes.sizeof(ctypes.c_int)
            )
        except Exception as e:
            logger.error(f"无法设置标题栏颜色: {e}", exc_info=True)
    
    # ------------------------- 数据库管理 ------------------------- #
    def _update_database_status(self):
        """更新数据库状态显示"""
        try:
            db_info = self.project_manager.get_database_info()
            if 'error' in db_info:
                self.db_status_label.setText("数据库: 错误")
                self.db_status_label.setStyleSheet("color: red;")
            else:
                project_count = db_info.get('total_projects', 0)
                self.db_status_label.setText(f"数据库: {project_count} 个项目")
                self.db_status_label.setStyleSheet("color: green;")
        except Exception as e:
            self.db_status_label.setText("数据库: 未知")
            self.db_status_label.setStyleSheet("color: orange;")
            logger.warning(f"更新数据库状态失败: {e}")
    



    def _show_database_path_dialog(self):
        """显示数据库路径设置对话框"""
        from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                     QPushButton, QMessageBox, QLineEdit, QFileDialog)
        import os

        dialog = QDialog(self)
        dialog.setWindowTitle("数据库路径设置")
        dialog.setFixedSize(500, 280)

        # 应用主题样式
        colors = theme_manager.get_theme_colors()
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {colors.get('background', '#ffffff')};
                color: {colors.get('text', '#333333')};
            }}
            QLabel {{
                color: {colors.get('text', '#333333')};
            }}
            QLineEdit {{
                background-color: {colors.get('background', '#ffffff')};
                border: 1px solid {colors.get('border', '#ddd')};
                border-radius: 4px;
                padding: 8px;
                color: {colors.get('text', '#333333')};
            }}
            QLineEdit:focus {{
                border-color: {colors.get('primary', '#4CAF50')};
            }}
            QLineEdit:read-only {{
                background-color: {colors.get('surface', '#f5f5f5')};
                color: {colors.get('text_secondary', '#666666')};
            }}
            QPushButton {{
                background-color: {colors.get('primary', '#4CAF50')};
                color: white;
                border: 1px solid {colors.get('primary', '#4CAF50')};
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {colors.get('primary_hover', '#45a049')};
                color: white;
                border-color: {colors.get('primary_hover', '#45a049')};
            }}
            QPushButton:pressed {{
                background-color: {colors.get('primary_pressed', '#3d8b40')};
                color: white;
                border-color: {colors.get('primary_pressed', '#3d8b40')};
            }}
            QCheckBox {{
                color: {colors.get('text', '#333333')};
                font-weight: bold;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
            }}
            QCheckBox::indicator:unchecked {{
                border: 2px solid {colors.get('border', '#ddd')};
                border-radius: 3px;
                background-color: {colors.get('background', '#ffffff')};
            }}
            QCheckBox::indicator:checked {{
                border: 2px solid {colors.get('primary', '#4CAF50')};
                border-radius: 3px;
                background-color: {colors.get('primary', '#4CAF50')};
            }}
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 当前数据库路径显示
        current_path = self.project_manager.db_manager.db_path
        info_label = QLabel(f"当前数据库路径:")
        info_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(info_label)

        current_path_edit = QLineEdit(current_path)
        current_path_edit.setReadOnly(True)
        layout.addWidget(current_path_edit)

        # 新路径设置
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("新数据库路径:"))

        self.path_input = QLineEdit()
        self.path_input.setText(current_path)

        path_layout.addWidget(self.path_input)

        browse_btn = QPushButton("浏览...")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_database_path)
        path_layout.addWidget(browse_btn)

        layout.addLayout(path_layout)

        # 数据迁移选项
        from PyQt5.QtWidgets import QCheckBox
        self.migrate_data_checkbox = QCheckBox("迁移当前数据库的数据到新数据库")
        self.migrate_data_checkbox.setChecked(True)  # 默认选中
        layout.addWidget(self.migrate_data_checkbox)

        # 按钮区域
        button_layout = QHBoxLayout()

        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")

        def apply_path():
            new_path = self.path_input.text().strip()
            if not new_path:
                QMessageBox.warning(dialog, "输入错误", "请输入有效的数据库路径")
                return

            if new_path == current_path:
                QMessageBox.information(dialog, "提示", "路径未发生变化")
                dialog.accept()
                return

            # 确认更改
            reply = QMessageBox.question(
                dialog, "确认更改",
                f"确定要将数据库路径更改为:\n{new_path}\n\n注意：更改后需要重启应用程序才能生效。",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                try:
                    # 检查是否需要迁移数据
                    migrate_data = self.migrate_data_checkbox.isChecked()

                    if migrate_data:
                        # 执行数据迁移
                        success = self._migrate_database_data(current_path, new_path)
                        if not success:
                            return  # 迁移失败，不继续

                    # 保存新的数据库路径到配置文件
                    self._save_database_path_config(new_path)

                    message = f"数据库路径已设置为:\n{new_path}\n\n"
                    if migrate_data:
                        message += "数据迁移完成！\n\n"
                    message += "请重启应用程序使设置生效。"

                    QMessageBox.information(dialog, "设置成功", message)
                    dialog.accept()
                except Exception as e:
                    QMessageBox.critical(dialog, "设置失败", f"无法设置数据库路径:\n{str(e)}")

        ok_button.clicked.connect(apply_path)
        cancel_button.clicked.connect(dialog.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        dialog.exec_()

    def _browse_database_path(self):
        """浏览选择数据库文件"""
        import os
        from PyQt5.QtWidgets import QFileDialog

        current_path = self.path_input.text()
        current_dir = os.path.dirname(current_path) if current_path else os.path.expanduser("~")

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择数据库文件",
            os.path.join(current_dir, "database.db"),
            "SQLite数据库文件 (*.db);;所有文件 (*)"
        )

        if file_path:
            self.path_input.setText(file_path)

    def _save_database_path_config(self, new_path: str):
        """保存数据库路径配置"""
        import json
        import os
        from datetime import datetime
        from core.storage_utils import get_default_storage_path

        # 配置文件路径
        config_dir = get_default_storage_path()
        config_file = os.path.join(config_dir, "database_path.json")

        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)

        # 保存配置
        config_data = {
            "database_path": os.path.abspath(new_path),
            "updated_at": datetime.now().isoformat(),
            "version": "1.0"
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        logger.info(f"数据库路径配置已保存: {new_path}")

    @staticmethod
    def _load_database_path_config():
        """加载数据库路径配置"""
        import json
        import os
        from core.storage_utils import get_default_storage_path, get_default_database_path

        try:
            config_dir = get_default_storage_path()
            config_file = os.path.join(config_dir, "database_path.json")

            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    return config_data.get("database_path")
        except Exception as e:
            logger.warning(f"加载数据库路径配置失败: {e}")

        # 返回默认路径
        return get_default_database_path()

    def _migrate_database_data(self, source_path: str, target_path: str) -> bool:
        """迁移数据库数据"""
        from PyQt5.QtWidgets import QProgressDialog, QApplication, QMessageBox
        import shutil
        import sqlite3
        import os

        try:
            # 检查源数据库是否存在
            if not os.path.exists(source_path):
                QMessageBox.warning(self, "迁移失败", f"源数据库文件不存在:\n{source_path}")
                return False

            # 检查目标路径
            target_dir = os.path.dirname(target_path)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)

            # 如果目标文件已存在，询问是否覆盖
            if os.path.exists(target_path):
                reply = QMessageBox.question(
                    self, "文件已存在",
                    f"目标数据库文件已存在:\n{target_path}\n\n是否覆盖？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return False

            # 显示进度对话框
            progress = QProgressDialog("正在迁移数据库数据...", "取消", 0, 100, self)
            progress.setWindowTitle("数据迁移")
            progress.setModal(True)
            progress.setValue(0)
            progress.show()
            QApplication.processEvents()

            # 复制数据库文件
            progress.setLabelText("正在复制数据库文件...")
            progress.setValue(20)
            QApplication.processEvents()

            shutil.copy2(source_path, target_path)

            progress.setValue(60)
            QApplication.processEvents()

            # 验证目标数据库
            progress.setLabelText("正在验证数据库完整性...")
            progress.setValue(80)
            QApplication.processEvents()

            # 简单验证：尝试连接并查询
            conn = sqlite3.connect(target_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            conn.close()

            progress.setValue(100)
            progress.close()

            logger.info(f"数据库迁移成功: {source_path} -> {target_path}")
            logger.info(f"迁移的表数量: {len(tables)}")

            return True

        except Exception as e:
            if 'progress' in locals():
                progress.close()

            logger.error(f"数据库迁移失败: {e}")
            QMessageBox.critical(
                self, "迁移失败",
                f"数据库迁移失败:\n{str(e)}\n\n请检查文件权限和磁盘空间。"
            )
            return False
    

    
    def _refresh_project_data(self):
        """刷新项目数据"""
        try:
            # 重新加载项目数据
            self.project_manager.projects = {p.id: p for p in self.project_manager.storage.load_all_projects()}
            self.project_manager.global_config = self.project_manager.storage.load_global_config()
            
            # 更新UI显示
            self._update_current_project_display()
            self._update_recent_projects_menu()
            self._update_database_status()
            
            logger.info("项目数据已刷新")
        except Exception as e:
            logger.error(f"刷新项目数据时出错: {e}")
    
    def _update_current_project_display(self):
        """更新当前项目显示"""
        try:
            current_project = self.project_manager.get_current_project()
            if current_project:
                self.current_project_label.setText(current_project.name)
                self.setWindowTitle(f"Swagger API测试工具 - {current_project.name}")
                # 如果项目有基础URL，更新API测试器的基础URL
                if current_project.base_url:
                    self.api_tester.set_base_url(current_project.base_url)
                    logger.info(f"更新项目显示时应用基础URL: {current_project.base_url}")
            else:
                self.current_project_label.setText("无项目")
                self.setWindowTitle("Swagger API测试工具")
        except Exception as e:
            logger.error(f"更新当前项目显示时出错: {e}")
            self.current_project_label.setText("错误")
            self.setWindowTitle("Swagger API测试工具")

    def _show_theme_preview(self):
        """显示主题预览对话框"""
        try:
            from .theme_preview_dialog import show_theme_preview
            show_theme_preview(self)
        except Exception as e:
            logger.error(f"显示主题预览时出错: {e}", exc_info=True)
            QMessageBox.warning(self, "错误", f"显示主题预览时出错: {str(e)}")

