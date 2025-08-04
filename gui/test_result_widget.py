#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试结果显示组件
"""

import json
import logging
import os
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QListWidget, QListWidgetItem, QSplitter, QLabel, QGroupBox,
    QTabWidget, QComboBox, QCheckBox, QProgressBar, QMessageBox,
    QLineEdit, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QTextCursor, QColor, QTextCharFormat, QFont, QPalette

from core.test_history_repository import TestHistoryRepository

logger = logging.getLogger(__name__)


class TestResultWidget(QWidget):
    """测试结果显示组件"""
    
    # 信号定义
    export_curl_requested = pyqtSignal(dict, object)  # 导出cURL请求信号
    export_postman_requested = pyqtSignal(list)  # 导出Postman集合信号
    history_selected = pyqtSignal(dict)  # 选中历史记录信号
    resend_requested = pyqtSignal(dict)  # 重新发送请求信号
    
    def __init__(self, project_manager=None, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager  # 项目管理器
        self.test_history_repo = None  # 测试历史仓库
        self.current_result = None  # 当前测试结果
        self.current_api_path = None  # 当前选中的API路径
        self.click_timer = None  # 用于区分单击和双击的定时器
        self.clicked_item = None  # 记录被点击的项
        self.current_project_id = None  # 当前项目ID
        self.search_timer = None  # 搜索防抖定时器
        
        # 初始化数据库连接
        self._init_database()
        
        self.init_ui()
        self.load_history()  # 加载历史记录
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # 当前结果标签页
        current_widget = QWidget()
        current_layout = QVBoxLayout(current_widget)
        
        # 结果显示区域
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        current_layout.addWidget(self.result_text)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.resend_btn = QPushButton("重新发送")
        self.resend_btn.clicked.connect(self._on_resend)
        self.resend_btn.setEnabled(False)
        self.resend_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_layout.addWidget(self.resend_btn)
        
        self.copy_curl_btn = QPushButton("导出为cURL")
        self.copy_curl_btn.clicked.connect(self._on_export_curl)
        self.copy_curl_btn.setEnabled(False)
        button_layout.addWidget(self.copy_curl_btn)
        
        button_layout.addStretch()
        current_layout.addLayout(button_layout)
        
        self.tabs.addTab(current_widget, "当前结果")
        
        # 历史记录标签页
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        
        # 第一行筛选控件 - 接口筛选
        filter_layout1 = QHBoxLayout()
        
        # 显示所有或当前接口的选项
        self.show_all_checkbox = QCheckBox("显示所有接口历史")
        self.show_all_checkbox.setChecked(True)
        self.show_all_checkbox.stateChanged.connect(self._update_history_list)
        filter_layout1.addWidget(self.show_all_checkbox)
        
        filter_layout1.addWidget(QLabel("当前接口:"))
        self.current_api_label = QLabel("未选择")
        self.current_api_label.setStyleSheet("QLabel { color: #666; }")
        filter_layout1.addWidget(self.current_api_label)
        
        filter_layout1.addStretch()
        history_layout.addLayout(filter_layout1)
        
        # 第二行筛选控件 - 高级筛选
        filter_layout2 = QHBoxLayout()
        
        # 状态码筛选
        filter_layout2.addWidget(QLabel("状态码:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部", "成功 (2xx)", "客户端错误 (4xx)", "服务器错误 (5xx)", "错误 (非2xx)"])
        self.status_filter.currentIndexChanged.connect(self._update_history_list)
        self.status_filter.setMinimumWidth(120)
        filter_layout2.addWidget(self.status_filter)
        
        # 时间筛选
        filter_layout2.addWidget(QLabel("时间:"))
        self.time_filter = QComboBox()
        self.time_filter.addItems(["全部", "最近1小时", "今天", "最近7天", "最近30天"])
        self.time_filter.currentIndexChanged.connect(self._update_history_list)
        self.time_filter.setMinimumWidth(100)
        filter_layout2.addWidget(self.time_filter)
        
        # 搜索框
        filter_layout2.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索路径、描述或参数...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.setMinimumWidth(200)
        filter_layout2.addWidget(self.search_input)
        
        filter_layout2.addStretch()
        history_layout.addLayout(filter_layout2)
        
        # 添加操作提示
        tips_label = QLabel("💡 提示：单击查看结果，双击编辑参数")
        tips_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-style: italic;
                padding: 5px;
                background-color: #f0f0f0;
                border-radius: 3px;
            }
        """)
        history_layout.addWidget(tips_label)
        
        # 历史记录列表
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self._on_history_item_clicked_delayed)
        self.history_list.itemDoubleClicked.connect(self._on_history_item_double_clicked)
        self.history_list.setAlternatingRowColors(True)  # 交替行颜色
        self.history_list.setSpacing(3)  # 增加项之间的间距
        self.history_list.setWordWrap(True)  # 启用文字换行
        self.history_list.setTextElideMode(Qt.ElideNone)  # 禁用文本省略
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 需要时显示水平滚动条
        self.history_list.setResizeMode(QListWidget.Adjust)  # 自动调整大小
        self.history_list.setUniformItemSizes(False)  # 允许不同高度的项目
        # 设置样式，确保多行文本正确显示
        self.history_list.setStyleSheet("""
            QListWidget {
                outline: none;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #e0e0e0;
                margin: 2px 5px;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            QListWidget::item:selected {
                background-color: #3daee9;
                color: white;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #f0f0f0;
            }
        """)
        history_layout.addWidget(self.history_list)
        
        # 历史记录操作按钮
        history_button_layout = QHBoxLayout()
        
        self.clear_history_btn = QPushButton("清空历史")
        self.clear_history_btn.clicked.connect(self.clear_history)
        history_button_layout.addWidget(self.clear_history_btn)
        
        history_button_layout.addStretch()
        history_layout.addLayout(history_button_layout)
        
        self.tabs.addTab(history_widget, "历史记录")
        
    def _init_database(self):
        """初始化数据库连接"""
        if self.project_manager and hasattr(self.project_manager, 'db_manager'):
            self.test_history_repo = TestHistoryRepository(self.project_manager.db_manager)
        else:
            logger.warning("无法初始化测试历史数据库，将使用内存存储")
    
    def set_project_id(self, project_id: str):
        """设置当前项目ID"""
        self.current_project_id = project_id
        self.load_history()
        
    def display_test_result(self, result, add_to_history=True):
        """
        显示测试结果
        
        Args:
            result (dict): 测试结果数据
            add_to_history (bool): 是否添加到历史记录，默认为True
        """
        self.current_result = result
        self.result_text.clear()
        
        if not result:
            self.result_text.setPlainText("无测试结果")
            self.resend_btn.setEnabled(False)
            self.copy_curl_btn.setEnabled(False)
            return
            
        # 只有在需要时才添加到历史记录
        if add_to_history:
            self._add_to_history(result)
        
        # 格式化显示结果
        cursor = self.result_text.textCursor()
        
        # API信息
        api_info = result.get('api', {})
        self._append_colored_text(f"API: {api_info.get('method', 'UNKNOWN')} {api_info.get('path', '')}\n", QColor(0, 100, 200))
        
        if api_info.get('summary'):
            self._append_colored_text(f"描述: {api_info.get('summary')}\n", QColor(100, 100, 100))
            
        self._append_colored_text("\n" + "="*60 + "\n\n", QColor(200, 200, 200))
        
        # 请求信息
        self._append_colored_text("请求信息：\n", QColor(0, 150, 0))
        # 移除URL显示，因为它太长了
        # self._append_colored_text(f"URL: {result.get('url', '')}\n", QColor(50, 50, 50))
        self._append_colored_text(f"方法: {result.get('method', '')}\n", QColor(50, 50, 50))
        
        # 路径参数
        path_params = result.get('path_params', {})
        if path_params:
            self._append_colored_text("\n路径参数:\n", QColor(0, 150, 0))
            for key, value in path_params.items():
                self._append_colored_text(f"  {key}: {value}\n", QColor(50, 50, 50))
        
        # 查询参数
        query_params = result.get('query_params', {})
        if query_params:
            self._append_colored_text("\n查询参数:\n", QColor(0, 150, 0))
            for key, value in query_params.items():
                self._append_colored_text(f"  {key}: {value}\n", QColor(50, 50, 50))
        
        # 请求头
        headers = result.get('headers', {})
        if headers:
            self._append_colored_text("\n请求头:\n", QColor(0, 150, 0))
            for key, value in headers.items():
                self._append_colored_text(f"  {key}: {value}\n", QColor(50, 50, 50))
                
        # 请求体
        request_body = result.get('request_body')
        if request_body:
            self._append_colored_text("\n请求体:\n", QColor(0, 150, 0))
            if isinstance(request_body, (dict, list)):
                body_text = json.dumps(request_body, ensure_ascii=False, indent=2)
            else:
                body_text = str(request_body)
            self._append_colored_text(body_text + "\n", QColor(50, 50, 50))
            
        self._append_colored_text("\n" + "-"*60 + "\n\n", QColor(200, 200, 200))
        
        # 响应信息
        response = result.get('response', {})
        status_code = response.get('status_code', 0)
        
        # 根据状态码设置颜色
        if 200 <= status_code < 300:
            status_color = QColor(0, 150, 0)
        elif 400 <= status_code < 500:
            status_color = QColor(200, 100, 0)
        else:
            status_color = QColor(200, 0, 0)
            
        self._append_colored_text("响应信息:\n", QColor(0, 150, 0))
        self._append_colored_text(f"状态码: {status_code}\n", status_color)
        self._append_colored_text(f"耗时: {response.get('elapsed', 0):.3f}秒\n", QColor(50, 50, 50))
        
        # 响应头
        response_headers = response.get('headers', {})
        if response_headers:
            self._append_colored_text("\n响应头:\n", QColor(0, 150, 0))
            for key, value in response_headers.items():
                self._append_colored_text(f"  {key}: {value}\n", QColor(50, 50, 50))
                
        # 响应体
        response_body = response.get('body')
        if response_body:
            self._append_colored_text("\n响应体:\n", QColor(0, 150, 0))
            if isinstance(response_body, (dict, list)):
                body_text = json.dumps(response_body, ensure_ascii=False, indent=2)
            else:
                body_text = str(response_body)
            self._append_colored_text(body_text + "\n", QColor(50, 50, 50))
            
        # 错误信息
        error = result.get('error')
        if error:
            self._append_colored_text("\n错误信息:\n", QColor(200, 0, 0))
            self._append_colored_text(str(error) + "\n", QColor(150, 0, 0))
            
        # 启用按钮
        self.resend_btn.setEnabled(True)
        self.copy_curl_btn.setEnabled(True)
        
        # 切换到当前结果标签页
        self.tabs.setCurrentIndex(0)
        
    def _append_colored_text(self, text, color):
        """
        添加带颜色的文本
        
        Args:
            text (str): 文本内容
            color (QColor): 文本颜色
        """
        cursor = self.result_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        format = QTextCharFormat()
        
        # 检测是否为暗黑主题
        is_dark_theme = self._is_dark_theme()
        
        # 根据主题调整颜色亮度
        if is_dark_theme:
            # 暗黑主题下提高颜色亮度
            adjusted_color = self._adjust_color_for_dark_theme(color)
            format.setForeground(adjusted_color)
        else:
            format.setForeground(color)
        
        cursor.insertText(text, format)
        
        self.result_text.setTextCursor(cursor)
        
    def _add_to_history(self, result):
        """
        添加到历史记录
        
        Args:
            result (dict): 测试结果
        """
        if not self.current_project_id:
            logger.warning("无当前项目ID，无法保存历史记录")
            return
            

        # 创建结果的深拷贝，避免引用问题
        import copy
        history_entry = copy.deepcopy(result)
        
        # 添加时间戳
        history_entry['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 调试日志 - 检查API信息
        api_info = history_entry.get('api', {})
        logger.info(f"添加到历史记录 - API信息: method={api_info.get('method')}, path={api_info.get('path')}, summary='{api_info.get('summary')}'")
        
        # 保存到数据库
        if self.test_history_repo:
            self.test_history_repo.add_test_history(self.current_project_id, history_entry)
            
        # 更新历史记录列表显示
        self._update_history_list()
        
    def _update_history_list(self):
        """更新历史记录列表显示"""
        self.history_list.clear()
        
        if not self.test_history_repo or not self.current_project_id:
            return
            
        # 从数据库获取历史记录
        if self.show_all_checkbox.isChecked():
            # 显示所有历史
            filtered_history = self.test_history_repo.get_test_history(self.current_project_id)
        else:
            # 只显示当前接口的历史
            if self.current_api_path:
                # 从当前路径提取方法
                method = 'GET'  # 默认方法
                if hasattr(self, '_current_api_method'):
                    method = self._current_api_method
                filtered_history = self.test_history_repo.get_test_history_by_api(
                    self.current_project_id, self.current_api_path, method
                )
            else:
                filtered_history = []
        
        # 应用时间筛选
        time_filter_index = self.time_filter.currentIndex()
        if time_filter_index > 0:  # 不是"全部"
            now = datetime.now()
            if time_filter_index == 1:  # 最近1小时
                cutoff_time = now - timedelta(hours=1)
            elif time_filter_index == 2:  # 今天
                cutoff_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_filter_index == 3:  # 最近7天
                cutoff_time = now - timedelta(days=7)
            elif time_filter_index == 4:  # 最近30天
                cutoff_time = now - timedelta(days=30)
            
            # 过滤时间
            filtered_history = [
                h for h in filtered_history 
                if datetime.strptime(h.get('timestamp', ''), "%Y-%m-%d %H:%M:%S") >= cutoff_time
            ]
        
        # 应用状态码筛选
        status_filter_index = self.status_filter.currentIndex()
        if status_filter_index > 0:  # 不是"全部"
            filtered_by_status = []
            for h in filtered_history:
                status_code = h.get('response', {}).get('status_code', 0)
                if status_filter_index == 1 and 200 <= status_code < 300:  # 成功
                    filtered_by_status.append(h)
                elif status_filter_index == 2 and 400 <= status_code < 500:  # 客户端错误
                    filtered_by_status.append(h)
                elif status_filter_index == 3 and 500 <= status_code < 600:  # 服务器错误
                    filtered_by_status.append(h)
                elif status_filter_index == 4 and (status_code < 200 or status_code >= 300):  # 错误（非2xx）
                    filtered_by_status.append(h)
            filtered_history = filtered_by_status
        
        # 应用搜索筛选
        search_text = self.search_input.text().strip().lower()
        if search_text:
            filtered_by_search = []
            for h in filtered_history:
                # 搜索路径、描述、参数
                api_info = h.get('api', {})
                search_targets = [
                    api_info.get('path', '').lower(),
                    api_info.get('summary', '').lower(),
                    api_info.get('method', '').lower(),
                    json.dumps(h.get('query_params', {})).lower(),
                    json.dumps(h.get('path_params', {})).lower(),
                    json.dumps(h.get('request_body', {})).lower(),
                ]
                
                if any(search_text in target for target in search_targets):
                    filtered_by_search.append(h)
            filtered_history = filtered_by_search
        
        for result in filtered_history:
            api_info = result.get('api', {})
            response = result.get('response', {})
            status_code = response.get('status_code', 0)
            
            # 构建显示文本
            method = api_info.get('method', 'UNKNOWN')
            path = api_info.get('path', '')
            summary = api_info.get('summary', '')
            timestamp = result.get('timestamp', '')
            
            # 调试日志
            logger.info(f"更新历史列表 - Method: {method}, Path: {path}, Summary: '{summary}'")
            logger.info(f"Summary是否存在: {bool(summary)}, Summary类型: {type(summary)}, Summary长度: {len(summary) if summary else 0}")
            
            # 构建显示文本
            lines = []
            
            # 第一行：时间戳 + 状态码
            status_str = f"[{status_code}]" if status_code else "[---]"
            # 根据状态码设置颜色标记
            if 200 <= status_code < 300:
                status_emoji = "✅"
            elif 400 <= status_code < 500:
                status_emoji = "⚠️"
            else:
                status_emoji = "❌"
            lines.append(f"{timestamp} {status_emoji} {status_str}")
            
            # 第二行：方法 + 路径（完整显示）
            second_line = f"{method} {path}"
            lines.append(second_line)
            
            # 第三行：描述（如果有，完整显示）
            if summary:
                # 完整显示描述，不进行截断
                lines.append(f"📝 {summary}")
            else:
                # 如果没有描述，显示默认文本
                lines.append("📝 [无描述]")
            
            # 第四行：响应时间和大小（如果有）
            elapsed = response.get('elapsed', 0)
            response_size = len(str(response.get('body', '')))
            if elapsed > 0:
                perf_line = f"⏱️ {elapsed:.3f}s"
                if response_size > 0:
                    # 格式化响应大小
                    if response_size < 1024:
                        size_str = f"{response_size}B"
                    elif response_size < 1024 * 1024:
                        size_str = f"{response_size / 1024:.1f}KB"
                    else:
                        size_str = f"{response_size / (1024 * 1024):.1f}MB"
                    perf_line += f" | 📦 {size_str}"
                lines.append(perf_line)
            
            item_text = "\n".join(lines)
            logger.info(f"最终显示文本: {repr(item_text)}")
            
            item = QListWidgetItem(item_text)
            
            # 根据状态码设置颜色
            if 200 <= status_code < 300:
                item.setForeground(QColor(0, 150, 0))
            elif 400 <= status_code < 500:
                item.setForeground(QColor(200, 100, 0))
            else:
                item.setForeground(QColor(200, 0, 0))
                
            # 设置字体
            font = QFont()
            font.setFamily("Microsoft YaHei UI")  # 使用支持表情符号的字体
            font.setPointSize(9)
            item.setFont(font)
            
            # 设置项目高度 - 动态高度，根据行数
            line_count = len(lines)
            # 增加基础高度和每行高度，确保所有文本都能显示
            item_height = 30 + (line_count * 20)  # 增加基础高度和行高
            item.setSizeHint(QSize(0, item_height))
                
            # 存储完整的结果数据
            item.setData(Qt.UserRole, result)
            
            self.history_list.addItem(item)
            
    def _on_history_item_clicked_delayed(self, item):
        """
        延迟处理单击事件，用于区分单击和双击
        
        Args:
            item (QListWidgetItem): 被点击的项
        """
        from PyQt5.QtCore import QTimer
        
        # 记录被点击的项
        self.clicked_item = item
        
        # 如果已有定时器在运行，说明是双击，取消单击处理
        if self.click_timer and self.click_timer.isActive():
            self.click_timer.stop()
            self.click_timer = None
            return
            
        # 创建定时器，延迟处理单击
        self.click_timer = QTimer()
        self.click_timer.timeout.connect(self._process_single_click)
        self.click_timer.setSingleShot(True)
        self.click_timer.start(250)  # 250ms 延迟
        
    def _process_single_click(self):
        """
        处理单击事件
        """
        if self.clicked_item:
            result = self.clicked_item.data(Qt.UserRole)
            if result:
                # 切换到当前结果标签页并显示历史结果，不重复添加到历史
                self.display_test_result(result, add_to_history=False)
            self.clicked_item = None
            
    def _on_history_item_double_clicked(self, item):
        """
        历史记录项被双击
        
        Args:
            item (QListWidgetItem): 被双击的项
        """
        # 取消任何待处理的单击事件
        if self.click_timer and self.click_timer.isActive():
            self.click_timer.stop()
            self.click_timer = None
            self.clicked_item = None
            
        result = item.data(Qt.UserRole)
        if result:
            # 发送信号，通知主窗口将此历史数据加载到参数编辑器
            self.history_selected.emit(result)
            
    def clear_history(self):
        """清空历史记录"""
        if not self.test_history_repo or not self.current_project_id:
            return
            
        # 确认对话框
        reply = QMessageBox.question(
            self, '确认清空', 
            '确定要清空历史记录吗？此操作不可恢复。',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 根据筛选条件清空历史
            if self.show_all_checkbox.isChecked():
                # 清空所有历史
                self.test_history_repo.clear_test_history(self.current_project_id)
            else:
                # 只清空当前接口的历史
                if self.current_api_path:
                    self.test_history_repo.clear_test_history(self.current_project_id, self.current_api_path)
            
            self._update_history_list()
        
    def _on_export_curl(self):
        """导出当前结果为cURL命令"""
        if self.current_result:
            self.export_curl_requested.emit(self.current_result, self.copy_curl_btn)
    
    def _on_resend(self):
        """重新发送当前结果的请求"""
        if self.current_result:
            self.resend_requested.emit(self.current_result)
            
    def update_progress(self, current, total):
        """
        更新批量测试进度
        
        Args:
            current (int): 当前进度
            total (int): 总数
        """
        # 可以在这里实现进度显示
        pass
    
    def set_current_api(self, api_info):
        """
        设置当前选中的API
        
        Args:
            api_info (dict): API信息
        """
        if api_info:
            self.current_api_path = api_info.get('path', '')
            self._current_api_method = api_info.get('method', 'GET')
            summary = api_info.get('summary', '')
            display_text = f"{api_info.get('method', '')} {self.current_api_path}"
            if summary:
                display_text += f" - {summary}"
            self.current_api_label.setText(display_text)
            self.current_api_label.setToolTip(display_text)
            
            # 如果不是显示所有，更新列表
            if not self.show_all_checkbox.isChecked():
                self._update_history_list()
    
    def _on_search_text_changed(self):
        """搜索框文本变化时的处理（带防抖）"""
        # 取消之前的定时器
        if self.search_timer:
            self.search_timer.stop()
        
        # 创建新的定时器，300ms后执行搜索
        self.search_timer = QTimer()
        self.search_timer.timeout.connect(self._update_history_list)
        self.search_timer.setSingleShot(True)
        self.search_timer.start(300)
    
    def save_history(self):
        """保存历史记录到数据库（已由add_to_history处理，此方法保留用于兼容性）"""
        pass
    
    def load_history(self):
        """从数据库加载历史记录"""
        if self.test_history_repo and self.current_project_id:
            try:
                # 更新历史记录列表显示
                self._update_history_list()
                
                # 获取统计信息
                stats = self.test_history_repo.get_test_history_stats(self.current_project_id)
                logger.info(f"加载了项目 {self.current_project_id} 的历史记录，共 {stats.get('total_count', 0)} 条")
            except Exception as e:
                logger.error(f"加载历史记录失败: {e}")
    
    def show_loading_state(self):
        """显示加载状态"""
        self.result_text.clear()
        self.resend_btn.setEnabled(False)
        self.copy_curl_btn.setEnabled(False)
        
        # 显示加载动画
        loading_html = """
        <div style="text-align: center; padding: 50px;">
            <h2 style="color: #2196F3;">正在测试API...</h2>
            <p style="color: #666;">请稍候，正在发送请求并等待响应</p>
            <div style="margin-top: 20px;">
                <span style="color: #2196F3; font-size: 24px;">⏳</span>
            </div>
        </div>
        """
        self.result_text.setHtml(loading_html)
        
        # 切换到当前结果标签页
        self.tabs.setCurrentIndex(0)
    
    def show_error(self, error_msg):
        """
        显示错误信息
        
        Args:
            error_msg (str): 错误信息
        """
        self.result_text.clear()
        self.resend_btn.setEnabled(False)
        self.copy_curl_btn.setEnabled(False)
        
        # 显示错误信息
        error_html = f"""
        <div style="text-align: center; padding: 50px;">
            <h2 style="color: #f44336;">测试失败</h2>
            <p style="color: #666; margin-top: 20px;">{error_msg}</p>
            <div style="margin-top: 20px;">
                <span style="color: #f44336; font-size: 24px;">⚠</span>
            </div>
        </div>
        """
        self.result_text.setHtml(error_html)
        
        # 切换到当前结果标签页
        self.tabs.setCurrentIndex(0)
    
    def _is_dark_theme(self):
        """
        检测是否为暗黑主题
        
        Returns:
            bool: 如果是暗黑主题返回True
        """
        # 通过背景颜色的亮度来判断
        palette = QApplication.palette()
        background_color = palette.color(QPalette.Window)
        
        # 计算亮度 (0-255)
        brightness = (background_color.red() * 299 + 
                     background_color.green() * 587 + 
                     background_color.blue() * 114) / 1000
        
        # 如果亮度小于128，认为是暗黑主题
        return brightness < 128
    
    def _adjust_color_for_dark_theme(self, color):
        """
        为暗黑主题调整颜色亮度
        
        Args:
            color (QColor): 原始颜色
            
        Returns:
            QColor: 调整后的颜色
        """
        # 获取HSL值
        h, s, l, a = color.getHsl()
        
        # 如果颜色太暗，提高亮度
        if l < 150:  # 亮度范围是0-255
            # 提高亮度，但不要超过某个阈值以保持颜色特征
            new_l = min(l + 80, 220)
            new_color = QColor()
            new_color.setHsl(h, s, new_l, a)
            return new_color
        
        return color
