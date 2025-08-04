#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库设置对话框
提供数据库配置、连接测试、信息展示和管理功能
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QPushButton, QLabel, QTextEdit, QProgressBar,
    QDialogButtonBox, QFileDialog, QMessageBox, QTabWidget,
    QWidget, QGridLayout, QFrame, QSplitter, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QFont, QIcon, QPalette

from core.database_manager import DatabaseManager
from core.database_validator import DatabaseValidator, ValidationLevel
from core.storage_utils import get_default_database_path, ensure_storage_dir

logger = logging.getLogger(__name__)


class DatabaseTestThread(QThread):
    """数据库测试线程"""
    test_completed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
    
    def run(self):
        try:
            db_manager = DatabaseManager(self.db_path)
            if db_manager.connect():
                if db_manager.test_connection():
                    db_info = db_manager.get_connection_info()
                    message = f"连接成功！数据库版本: {db_info.get('version', 'N/A')}"
                    self.test_completed.emit(True, message)
                else:
                    self.test_completed.emit(False, "连接测试失败")
                db_manager.disconnect()
            else:
                self.test_completed.emit(False, "无法连接到数据库")
        except Exception as e:
            self.test_completed.emit(False, f"连接异常: {str(e)}")


class DatabaseValidationThread(QThread):
    """数据库验证线程"""
    validation_completed = pyqtSignal(dict)  # validation result
    progress_updated = pyqtSignal(int, str)  # progress, message
    
    def __init__(self, db_path: str, validation_level: ValidationLevel):
        super().__init__()
        self.db_path = db_path
        self.validation_level = validation_level
    
    def run(self):
        try:
            db_manager = DatabaseManager(self.db_path)
            if db_manager.connect():
                validator = DatabaseValidator(db_manager)
                
                self.progress_updated.emit(20, "开始验证...")
                result = validator.validate_database(self.validation_level)
                
                self.progress_updated.emit(80, "生成报告...")
                health_report = validator.get_database_health_report()
                
                self.progress_updated.emit(100, "验证完成")
                
                self.validation_completed.emit({
                    'validation_result': result,
                    'health_report': health_report
                })
                
                db_manager.disconnect()
            else:
                self.validation_completed.emit({
                    'error': '无法连接到数据库'
                })
        except Exception as e:
            self.validation_completed.emit({
                'error': f'验证异常: {str(e)}'
            })


class DatabaseSettingsDialog(QDialog):
    """数据库设置对话框"""
    
    database_changed = pyqtSignal(str)  # 数据库路径改变信号
    
    def __init__(self, current_db_path: str = None, parent=None):
        super().__init__(parent)
        self.current_db_path = current_db_path or get_default_database_path()
        self.db_manager = None
        self.test_thread = None
        self.validation_thread = None
        
        self.setWindowTitle("数据库设置")
        self.setModal(True)
        self.resize(800, 600)
        self.setMinimumSize(700, 500)
        
        self._init_ui()
        self._load_current_settings()
        self._setup_connections()
        
        # 定时刷新数据库信息
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_database_info)
        self.refresh_timer.start(5000)  # 每5秒刷新一次
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 基本设置标签页
        self.basic_tab = self._create_basic_tab()
        self.tab_widget.addTab(self.basic_tab, "基本设置")
        
        # 数据库信息标签页
        self.info_tab = self._create_info_tab()
        self.tab_widget.addTab(self.info_tab, "数据库信息")
        
        # 验证和维护标签页
        self.maintenance_tab = self._create_maintenance_tab()
        self.tab_widget.addTab(self.maintenance_tab, "验证维护")
        
        # 高级设置标签页
        self.advanced_tab = self._create_advanced_tab()
        self.tab_widget.addTab(self.advanced_tab, "高级设置")
        
        layout.addWidget(self.tab_widget)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("测试连接")
        self.test_button.setMinimumWidth(100)
        button_layout.addWidget(self.test_button)
        
        button_layout.addStretch()
        
        # 标准对话框按钮
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        # 设置按钮中文文本
        self.button_box.button(QDialogButtonBox.Ok).setText("确定")
        self.button_box.button(QDialogButtonBox.Cancel).setText("取消")
        self.button_box.button(QDialogButtonBox.Apply).setText("应用")
        button_layout.addWidget(self.button_box)
        
        layout.addLayout(button_layout)
    
    def _create_basic_tab(self) -> QWidget:
        """创建基本设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # 数据库路径设置组
        path_group = QGroupBox("数据库路径")
        path_layout = QFormLayout(path_group)
        path_layout.setSpacing(10)
        
        # 数据库路径输入
        path_input_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("选择数据库文件路径...")
        path_input_layout.addWidget(self.path_input)
        
        self.browse_button = QPushButton("浏览...")
        self.browse_button.setMaximumWidth(80)
        path_input_layout.addWidget(self.browse_button)
        
        path_layout.addRow("数据库文件:", path_input_layout)
        
        # 连接状态显示
        self.connection_status = QLabel("未连接")
        self.connection_status.setStyleSheet("color: gray;")
        path_layout.addRow("连接状态:", self.connection_status)
        
        layout.addWidget(path_group)
        
        # 数据库操作组
        operations_group = QGroupBox("数据库操作")
        operations_layout = QGridLayout(operations_group)
        operations_layout.setSpacing(10)
        
        self.create_button = QPushButton("创建新数据库")
        self.backup_button = QPushButton("备份数据库")
        self.restore_button = QPushButton("恢复数据库")
        self.optimize_button = QPushButton("优化数据库")
        
        operations_layout.addWidget(self.create_button, 0, 0)
        operations_layout.addWidget(self.backup_button, 0, 1)
        operations_layout.addWidget(self.restore_button, 1, 0)
        operations_layout.addWidget(self.optimize_button, 1, 1)
        
        layout.addWidget(operations_group)
        
        layout.addStretch()
        return widget
    
    def _create_info_tab(self) -> QWidget:
        """创建数据库信息标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 基本信息组
        basic_info_group = QGroupBox("基本信息")
        basic_info_layout = QFormLayout(basic_info_group)
        basic_info_layout.setSpacing(8)
        
        self.db_version_label = QLabel("N/A")
        self.db_size_label = QLabel("N/A")
        self.db_tables_label = QLabel("N/A")
        self.db_records_label = QLabel("N/A")
        self.db_created_label = QLabel("N/A")
        self.db_modified_label = QLabel("N/A")
        
        basic_info_layout.addRow("数据库版本:", self.db_version_label)
        basic_info_layout.addRow("文件大小:", self.db_size_label)
        basic_info_layout.addRow("表数量:", self.db_tables_label)
        basic_info_layout.addRow("记录总数:", self.db_records_label)
        basic_info_layout.addRow("创建时间:", self.db_created_label)
        basic_info_layout.addRow("修改时间:", self.db_modified_label)
        
        layout.addWidget(basic_info_group)
        
        # 表统计信息
        tables_group = QGroupBox("表统计信息")
        tables_layout = QVBoxLayout(tables_group)
        
        self.tables_table = QTableWidget()
        self.tables_table.setColumnCount(3)
        self.tables_table.setHorizontalHeaderLabels(["表名", "记录数", "大小"])
        self.tables_table.horizontalHeader().setStretchLastSection(True)
        self.tables_table.setAlternatingRowColors(True)
        self.tables_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        tables_layout.addWidget(self.tables_table)
        
        # 刷新按钮
        refresh_button = QPushButton("刷新信息")
        refresh_button.clicked.connect(self._refresh_database_info)
        tables_layout.addWidget(refresh_button)
        
        layout.addWidget(tables_group)
        
        return widget
    
    def _create_maintenance_tab(self) -> QWidget:
        """创建验证维护标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 验证设置组
        validation_group = QGroupBox("数据库验证")
        validation_layout = QVBoxLayout(validation_group)
        
        # 验证级别选择
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("验证级别:"))
        
        self.basic_radio = QCheckBox("基本验证")
        self.standard_radio = QCheckBox("标准验证")
        self.thorough_radio = QCheckBox("彻底验证")
        self.standard_radio.setChecked(True)  # 默认选择标准验证
        
        level_layout.addWidget(self.basic_radio)
        level_layout.addWidget(self.standard_radio)
        level_layout.addWidget(self.thorough_radio)
        level_layout.addStretch()
        
        validation_layout.addLayout(level_layout)
        
        # 验证按钮和进度条
        validation_controls_layout = QHBoxLayout()
        self.validate_button = QPushButton("开始验证")
        self.auto_fix_button = QPushButton("自动修复")
        self.auto_fix_button.setEnabled(False)
        
        validation_controls_layout.addWidget(self.validate_button)
        validation_controls_layout.addWidget(self.auto_fix_button)
        validation_controls_layout.addStretch()
        
        validation_layout.addLayout(validation_controls_layout)
        
        # 进度条
        self.validation_progress = QProgressBar()
        self.validation_progress.setVisible(False)
        validation_layout.addWidget(self.validation_progress)
        
        layout.addWidget(validation_group)
        
        # 验证结果显示
        results_group = QGroupBox("验证结果")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(200)
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
        
        layout.addStretch()
        return widget
    
    def _create_advanced_tab(self) -> QWidget:
        """创建高级设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 性能设置组
        performance_group = QGroupBox("性能设置")
        performance_layout = QFormLayout(performance_group)
        
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(1, 1000)
        self.cache_size_spin.setValue(100)
        self.cache_size_spin.setSuffix(" MB")
        performance_layout.addRow("缓存大小:", self.cache_size_spin)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" 秒")
        performance_layout.addRow("连接超时:", self.timeout_spin)
        
        layout.addWidget(performance_group)
        
        # 维护设置组
        maintenance_group = QGroupBox("维护设置")
        maintenance_layout = QFormLayout(maintenance_group)
        
        self.auto_backup_check = QCheckBox("启用自动备份")
        maintenance_layout.addRow("自动备份:", self.auto_backup_check)
        
        self.backup_interval_spin = QSpinBox()
        self.backup_interval_spin.setRange(1, 30)
        self.backup_interval_spin.setValue(7)
        self.backup_interval_spin.setSuffix(" 天")
        maintenance_layout.addRow("备份间隔:", self.backup_interval_spin)
        
        self.auto_optimize_check = QCheckBox("启用自动优化")
        maintenance_layout.addRow("自动优化:", self.auto_optimize_check)
        
        layout.addWidget(maintenance_group)
        
        # 安全设置组
        security_group = QGroupBox("安全设置")
        security_layout = QFormLayout(security_group)
        
        self.encrypt_sensitive_check = QCheckBox("加密敏感数据")
        security_layout.addRow("数据加密:", self.encrypt_sensitive_check)
        
        self.audit_log_check = QCheckBox("启用审计日志")
        security_layout.addRow("审计日志:", self.audit_log_check)
        
        layout.addWidget(security_group)
        
        layout.addStretch()
        return widget
    
    def _setup_connections(self):
        """设置信号连接"""
        # 基本设置
        self.browse_button.clicked.connect(self._browse_database_file)
        self.path_input.textChanged.connect(self._on_path_changed)
        self.test_button.clicked.connect(self._test_connection)
        
        # 数据库操作
        self.create_button.clicked.connect(self._create_database)
        self.backup_button.clicked.connect(self._backup_database)
        self.restore_button.clicked.connect(self._restore_database)
        self.optimize_button.clicked.connect(self._optimize_database)
        
        # 验证维护
        self.validate_button.clicked.connect(self._validate_database)
        self.auto_fix_button.clicked.connect(self._auto_fix_issues)
        
        # 对话框按钮
        self.button_box.accepted.connect(lambda: self._apply_settings(close_dialog=True))
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(lambda: self._apply_settings(close_dialog=False))
    
    def _load_current_settings(self):
        """加载当前设置"""
        self.path_input.setText(self.current_db_path)
        self._refresh_database_info()
    
    def _browse_database_file(self):
        """浏览数据库文件"""
        # 如果当前路径存在且是文件，使用其目录作为初始目录
        initial_path = self.current_db_path
        if os.path.exists(self.current_db_path) and os.path.isfile(self.current_db_path):
            initial_path = os.path.dirname(self.current_db_path)
        elif os.path.exists(self.current_db_path) and os.path.isdir(self.current_db_path):
            # 如果当前路径是目录，直接使用
            initial_path = self.current_db_path
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择数据库文件",
            initial_path,
            "SQLite数据库文件 (*.db);;所有文件 (*)"
        )
        
        if file_path:
            # 验证选择的是文件而不是目录
            if os.path.isfile(file_path):
                self.path_input.setText(file_path)
            else:
                QMessageBox.warning(self, "警告", "请选择一个数据库文件，而不是文件夹")
    
    def _on_path_changed(self, path: str):
        """路径改变时的处理"""
        self.current_db_path = path
        self._update_connection_status("未连接", "gray")
        
        # 延迟刷新信息，避免频繁更新
        if hasattr(self, '_path_change_timer'):
            self._path_change_timer.stop()
        
        self._path_change_timer = QTimer()
        self._path_change_timer.setSingleShot(True)
        self._path_change_timer.timeout.connect(self._refresh_database_info)
        self._path_change_timer.start(1000)  # 1秒后刷新
    
    def _test_connection(self):
        """测试数据库连接"""
        if not self.current_db_path:
            QMessageBox.warning(self, "警告", "请先选择数据库文件路径")
            return
        
        # 验证路径是否为文件
        if os.path.exists(self.current_db_path):
            if os.path.isdir(self.current_db_path):
                QMessageBox.warning(self, "警告", f"所选路径是一个文件夹而不是数据库文件:\n{self.current_db_path}\n\n请选择一个 .db 文件")
                return
            elif not os.path.isfile(self.current_db_path):
                QMessageBox.warning(self, "警告", f"所选路径不是一个有效的文件:\n{self.current_db_path}")
                return
        else:
            QMessageBox.warning(self, "警告", f"数据库文件不存在:\n{self.current_db_path}")
            return
        
        self.test_button.setEnabled(False)
        self.test_button.setText("测试中...")
        self._update_connection_status("测试中...", "orange")
        
        # 在后台线程中测试连接
        self.test_thread = DatabaseTestThread(self.current_db_path)
        self.test_thread.test_completed.connect(self._on_test_completed)
        self.test_thread.start()
    
    def _on_test_completed(self, success: bool, message: str):
        """连接测试完成"""
        self.test_button.setEnabled(True)
        self.test_button.setText("测试连接")
        
        if success:
            self._update_connection_status("连接成功", "green")
            QMessageBox.information(self, "连接测试", message)
        else:
            self._update_connection_status("连接失败", "red")
            QMessageBox.warning(self, "连接测试", message)
        
        self._refresh_database_info()
    
    def _update_connection_status(self, text: str, color: str):
        """更新连接状态显示"""
        self.connection_status.setText(text)
        self.connection_status.setStyleSheet(f"color: {color}; font-weight: bold;")
    
    def _refresh_database_info(self):
        """刷新数据库信息"""
        if not self.current_db_path or not os.path.exists(self.current_db_path):
            self._clear_database_info()
            return
        
        try:
            db_manager = DatabaseManager(self.current_db_path)
            if db_manager.connect():
                db_info = db_manager.get_connection_info()
                
                # 更新基本信息
                self.db_version_label.setText(str(db_info.get('version', 'N/A')))
                
                file_size = db_info.get('file_size', 0)
                if file_size > 0:
                    size_mb = file_size / 1024 / 1024
                    self.db_size_label.setText(f"{size_mb:.2f} MB ({file_size:,} 字节)")
                else:
                    self.db_size_label.setText("N/A")
                
                self.db_tables_label.setText(str(db_info.get('table_count', 0)))
                self.db_records_label.setText(str(db_info.get('record_count', 0)))
                
                # 文件时间信息
                if os.path.exists(self.current_db_path):
                    stat = os.stat(self.current_db_path)
                    created_time = datetime.fromtimestamp(stat.st_ctime)
                    modified_time = datetime.fromtimestamp(stat.st_mtime)
                    
                    self.db_created_label.setText(created_time.strftime("%Y-%m-%d %H:%M:%S"))
                    self.db_modified_label.setText(modified_time.strftime("%Y-%m-%d %H:%M:%S"))
                
                # 更新表统计信息
                self._update_tables_info(db_manager)
                
                db_manager.disconnect()
                
                if db_info.get('is_connected'):
                    self._update_connection_status("已连接", "green")
                
        except Exception as e:
            logger.error(f"刷新数据库信息失败: {e}")
            self._clear_database_info()
    
    def _update_tables_info(self, db_manager: DatabaseManager):
        """更新表信息"""
        try:
            tables = ['projects', 'project_history', 'api_cache', 'global_config', 'user_preferences', 'database_info']
            
            self.tables_table.setRowCount(len(tables))
            
            for i, table in enumerate(tables):
                try:
                    # 获取记录数
                    result = db_manager.execute_query(f"SELECT COUNT(*) FROM {table}")
                    record_count = result[0][0] if result else 0
                    
                    # 设置表格项
                    self.tables_table.setItem(i, 0, QTableWidgetItem(table))
                    self.tables_table.setItem(i, 1, QTableWidgetItem(str(record_count)))
                    self.tables_table.setItem(i, 2, QTableWidgetItem("N/A"))  # 大小信息需要更复杂的查询
                    
                except Exception as e:
                    logger.warning(f"获取表 {table} 信息失败: {e}")
                    self.tables_table.setItem(i, 0, QTableWidgetItem(table))
                    self.tables_table.setItem(i, 1, QTableWidgetItem("错误"))
                    self.tables_table.setItem(i, 2, QTableWidgetItem("N/A"))
            
            # 调整列宽
            self.tables_table.resizeColumnsToContents()
            
        except Exception as e:
            logger.error(f"更新表信息失败: {e}")
    
    def _clear_database_info(self):
        """清空数据库信息显示"""
        self.db_version_label.setText("N/A")
        self.db_size_label.setText("N/A")
        self.db_tables_label.setText("N/A")
        self.db_records_label.setText("N/A")
        self.db_created_label.setText("N/A")
        self.db_modified_label.setText("N/A")
        
        self.tables_table.setRowCount(0)
        self._update_connection_status("未连接", "gray")
    
    def _create_database(self):
        """创建新数据库"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "创建新数据库",
            "",
            "SQLite数据库文件 (*.db);;所有文件 (*)"
        )
        
        if file_path:
            try:
                # 确保目录存在
                ensure_storage_dir(os.path.dirname(file_path))
                
                # 创建数据库管理器并初始化
                db_manager = DatabaseManager(file_path)
                if db_manager.connect():
                    if db_manager.initialize_database():
                        QMessageBox.information(self, "成功", f"数据库创建成功: {file_path}")
                        self.path_input.setText(file_path)
                    else:
                        QMessageBox.warning(self, "错误", "数据库初始化失败")
                    db_manager.disconnect()
                else:
                    QMessageBox.warning(self, "错误", "无法创建数据库文件")
                    
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建数据库失败: {str(e)}")
    
    def _backup_database(self):
        """备份数据库"""
        if not self.current_db_path or not os.path.exists(self.current_db_path):
            QMessageBox.warning(self, "警告", "请先选择有效的数据库文件")
            return
        
        backup_path, _ = QFileDialog.getSaveFileName(
            self,
            "备份数据库",
            f"{os.path.splitext(self.current_db_path)[0]}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
            "SQLite数据库文件 (*.db);;所有文件 (*)"
        )
        
        if backup_path:
            try:
                db_manager = DatabaseManager(self.current_db_path)
                if db_manager.connect():
                    if db_manager.backup_database(backup_path):
                        QMessageBox.information(self, "成功", f"数据库备份成功: {backup_path}")
                    else:
                        QMessageBox.warning(self, "错误", "数据库备份失败")
                    db_manager.disconnect()
                else:
                    QMessageBox.warning(self, "错误", "无法连接到数据库")
                    
            except Exception as e:
                QMessageBox.critical(self, "错误", f"备份数据库失败: {str(e)}")
    
    def _restore_database(self):
        """恢复数据库"""
        backup_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择备份文件",
            "",
            "SQLite数据库文件 (*.db);;所有文件 (*)"
        )
        
        if backup_path:
            reply = QMessageBox.question(
                self,
                "确认恢复",
                "恢复操作将覆盖当前数据库，是否继续？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                try:
                    if not self.current_db_path:
                        QMessageBox.warning(self, "警告", "请先设置数据库路径")
                        return
                    
                    db_manager = DatabaseManager(self.current_db_path)
                    if db_manager.restore_database(backup_path):
                        QMessageBox.information(self, "成功", "数据库恢复成功")
                        self._refresh_database_info()
                    else:
                        QMessageBox.warning(self, "错误", "数据库恢复失败")
                        
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"恢复数据库失败: {str(e)}")
    
    def _optimize_database(self):
        """优化数据库"""
        if not self.current_db_path or not os.path.exists(self.current_db_path):
            QMessageBox.warning(self, "警告", "请先选择有效的数据库文件")
            return
        
        try:
            db_manager = DatabaseManager(self.current_db_path)
            if db_manager.connect():
                validator = DatabaseValidator(db_manager)
                result = validator.optimize_database()
                
                if result['success']:
                    message = f"优化完成！\n\n执行的操作:\n"
                    for operation in result['operations']:
                        message += f"• {operation}\n"
                    QMessageBox.information(self, "优化完成", message)
                else:
                    message = f"优化部分完成\n\n错误:\n"
                    for error in result['errors']:
                        message += f"• {error}\n"
                    QMessageBox.warning(self, "优化结果", message)
                
                db_manager.disconnect()
                self._refresh_database_info()
            else:
                QMessageBox.warning(self, "错误", "无法连接到数据库")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"优化数据库失败: {str(e)}")
    
    def _validate_database(self):
        """验证数据库"""
        if not self.current_db_path or not os.path.exists(self.current_db_path):
            QMessageBox.warning(self, "警告", "请先选择有效的数据库文件")
            return
        
        # 确定验证级别
        if self.thorough_radio.isChecked():
            level = ValidationLevel.THOROUGH
        elif self.standard_radio.isChecked():
            level = ValidationLevel.STANDARD
        else:
            level = ValidationLevel.BASIC
        
        # 显示进度条
        self.validation_progress.setVisible(True)
        self.validation_progress.setValue(0)
        self.validate_button.setEnabled(False)
        self.validate_button.setText("验证中...")
        
        # 在后台线程中执行验证
        self.validation_thread = DatabaseValidationThread(self.current_db_path, level)
        self.validation_thread.validation_completed.connect(self._on_validation_completed)
        self.validation_thread.progress_updated.connect(self._on_validation_progress)
        self.validation_thread.start()
    
    def _on_validation_progress(self, progress: int, message: str):
        """验证进度更新"""
        self.validation_progress.setValue(progress)
        self.results_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def _on_validation_completed(self, result: Dict[str, Any]):
        """验证完成"""
        self.validation_progress.setVisible(False)
        self.validate_button.setEnabled(True)
        self.validate_button.setText("开始验证")
        
        if 'error' in result:
            self.results_text.append(f"\n❌ 验证失败: {result['error']}")
            return
        
        validation_result = result['validation_result']
        health_report = result['health_report']
        
        # 显示验证结果
        self.results_text.append(f"\n{'='*50}")
        self.results_text.append(f"验证完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.results_text.append(f"{'='*50}")
        
        if validation_result.success:
            self.results_text.append("✅ 数据库验证通过，未发现问题")
        else:
            self.results_text.append(f"⚠️ 发现 {len(validation_result.issues)} 个问题:")
            
            for issue in validation_result.issues[:10]:  # 只显示前10个问题
                severity_icon = {
                    'low': '🟡',
                    'medium': '🟠', 
                    'high': '🔴',
                    'critical': '💀'
                }.get(issue.severity.value, '❓')
                
                self.results_text.append(f"  {severity_icon} {issue.description}")
                if issue.auto_fixable:
                    self.results_text.append(f"    💡 可自动修复")
            
            if len(validation_result.issues) > 10:
                self.results_text.append(f"  ... 还有 {len(validation_result.issues) - 10} 个问题")
        
        # 显示健康报告摘要
        db_info = health_report['database_info']
        self.results_text.append(f"\n📊 数据库概况:")
        self.results_text.append(f"  文件大小: {db_info.get('file_size_mb', 0):.2f} MB")
        self.results_text.append(f"  表数量: {db_info.get('table_count', 0)}")
        self.results_text.append(f"  记录总数: {db_info.get('record_count', 0)}")
        
        # 启用自动修复按钮（如果有可修复的问题）
        auto_fixable_count = sum(1 for issue in validation_result.issues if issue.auto_fixable)
        if auto_fixable_count > 0:
            self.auto_fix_button.setEnabled(True)
            self.auto_fix_button.setText(f"自动修复 ({auto_fixable_count})")
        else:
            self.auto_fix_button.setEnabled(False)
            self.auto_fix_button.setText("自动修复")
        
        # 保存验证结果供自动修复使用
        self._last_validation_result = validation_result
    
    def _auto_fix_issues(self):
        """自动修复问题"""
        if not hasattr(self, '_last_validation_result'):
            QMessageBox.warning(self, "警告", "请先执行数据库验证")
            return
        
        auto_fixable_issues = [
            issue for issue in self._last_validation_result.issues 
            if issue.auto_fixable
        ]
        
        if not auto_fixable_issues:
            QMessageBox.information(self, "信息", "没有可自动修复的问题")
            return
        
        reply = QMessageBox.question(
            self,
            "确认修复",
            f"将自动修复 {len(auto_fixable_issues)} 个问题，是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            try:
                db_manager = DatabaseManager(self.current_db_path)
                if db_manager.connect():
                    validator = DatabaseValidator(db_manager)
                    result = validator.auto_fix_issues(auto_fixable_issues)
                    
                    self.results_text.append(f"\n🔧 自动修复结果:")
                    self.results_text.append(f"  成功修复: {result['fixed_count']} 个")
                    self.results_text.append(f"  修复失败: {result['failed_count']} 个")
                    
                    if result['errors']:
                        self.results_text.append(f"  错误信息:")
                        for error in result['errors']:
                            self.results_text.append(f"    • {error}")
                    
                    if result['success']:
                        QMessageBox.information(self, "修复完成", "所有问题已成功修复")
                        self.auto_fix_button.setEnabled(False)
                    else:
                        QMessageBox.warning(self, "修复结果", "部分问题修复失败，请查看详细信息")
                    
                    db_manager.disconnect()
                    self._refresh_database_info()
                else:
                    QMessageBox.warning(self, "错误", "无法连接到数据库")
                    
            except Exception as e:
                QMessageBox.critical(self, "错误", f"自动修复失败: {str(e)}")
    
    def _apply_settings(self, close_dialog=False):
        """应用设置"""
        if self.current_db_path != self.path_input.text():
            self.current_db_path = self.path_input.text()
            self.database_changed.emit(self.current_db_path)
        
        # 这里可以保存其他设置到配置文件
        # TODO: 实现设置保存功能
        
        # 不显示弹出框，直接关闭
        if close_dialog:
            self.accept()
    
    def closeEvent(self, event):
        """关闭事件"""
        # 停止定时器
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        
        # 停止后台线程
        if self.test_thread and self.test_thread.isRunning():
            self.test_thread.quit()
            self.test_thread.wait()
        
        if self.validation_thread and self.validation_thread.isRunning():
            self.validation_thread.quit()
            self.validation_thread.wait()
        
        event.accept()