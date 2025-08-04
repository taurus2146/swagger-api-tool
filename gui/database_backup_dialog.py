#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库备份和恢复对话框
提供数据库备份、恢复、自动备份计划等功能
"""

import os
import json
import logging
import shutil
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QPushButton, QLabel, QTextEdit, QProgressBar,
    QDialogButtonBox, QFileDialog, QMessageBox, QTabWidget,
    QWidget, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QSpinBox, QComboBox, QDateTimeEdit,
    QListWidget, QListWidgetItem, QSplitter, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QDateTime
from PyQt5.QtGui import QFont, QIcon, QPalette

from core.database_manager import DatabaseManager
from core.storage_utils import get_default_storage_path

logger = logging.getLogger(__name__)


@dataclass
class BackupInfo:
    """备份信息"""
    file_path: str
    created_at: datetime
    file_size: int
    database_version: Optional[int] = None
    notes: Optional[str] = None
    
    @property
    def file_name(self) -> str:
        return os.path.basename(self.file_path)
    
    @property
    def size_mb(self) -> float:
        return self.file_size / 1024 / 1024


@dataclass
class BackupSchedule:
    """备份计划"""
    enabled: bool = False
    frequency: str = "daily"  # daily, weekly, monthly
    time: str = "02:00"  # HH:MM format
    keep_count: int = 7  # 保留备份数量
    backup_path: str = ""  # 备份目录


class BackupThread(QThread):
    """备份线程"""
    backup_progress = pyqtSignal(int, str)  # progress, message
    backup_completed = pyqtSignal(bool, str, str)  # success, message, backup_path
    
    def __init__(self, db_path: str, backup_path: str, notes: str = ""):
        super().__init__()
        self.db_path = db_path
        self.backup_path = backup_path
        self.notes = notes
    
    def run(self):
        try:
            self.backup_progress.emit(10, "准备备份...")
            
            # 检查源数据库
            if not os.path.exists(self.db_path):
                self.backup_completed.emit(False, "源数据库文件不存在", "")
                return
            
            self.backup_progress.emit(30, "连接数据库...")
            
            # 创建数据库管理器
            db_manager = DatabaseManager(self.db_path)
            if not db_manager.connect():
                self.backup_completed.emit(False, "无法连接到数据库", "")
                return
            
            self.backup_progress.emit(50, "执行备份...")
            
            # 执行备份
            if db_manager.backup_database(self.backup_path):
                self.backup_progress.emit(80, "保存备份信息...")
                
                # 保存备份信息
                self._save_backup_info()
                
                self.backup_progress.emit(100, "备份完成")
                self.backup_completed.emit(True, "备份成功完成", self.backup_path)
            else:
                self.backup_completed.emit(False, "备份操作失败", "")
            
            db_manager.disconnect()
            
        except Exception as e:
            self.backup_completed.emit(False, f"备份异常: {str(e)}", "")
    
    def _save_backup_info(self):
        """保存备份信息"""
        try:
            backup_info = {
                'file_path': self.backup_path,
                'created_at': datetime.now().isoformat(),
                'file_size': os.path.getsize(self.backup_path),
                'notes': self.notes,
                'source_db': self.db_path
            }
            
            # 保存到备份信息文件
            info_file = self.backup_path + '.info'
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.warning(f"保存备份信息失败: {e}")


class RestoreThread(QThread):
    """恢复线程"""
    restore_progress = pyqtSignal(int, str)  # progress, message
    restore_completed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, backup_path: str, target_db_path: str):
        super().__init__()
        self.backup_path = backup_path
        self.target_db_path = target_db_path
    
    def run(self):
        try:
            self.restore_progress.emit(10, "验证备份文件...")
            
            # 检查备份文件
            if not os.path.exists(self.backup_path):
                self.restore_completed.emit(False, "备份文件不存在")
                return
            
            self.restore_progress.emit(30, "准备恢复...")
            
            # 备份当前数据库
            if os.path.exists(self.target_db_path):
                backup_current = f"{self.target_db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(self.target_db_path, backup_current)
                self.restore_progress.emit(50, f"当前数据库已备份到: {os.path.basename(backup_current)}")
            
            self.restore_progress.emit(70, "执行恢复...")
            
            # 创建数据库管理器
            db_manager = DatabaseManager(self.target_db_path)
            if db_manager.restore_database(self.backup_path):
                self.restore_progress.emit(100, "恢复完成")
                self.restore_completed.emit(True, "数据库恢复成功")
            else:
                self.restore_completed.emit(False, "恢复操作失败")
            
        except Exception as e:
            self.restore_completed.emit(False, f"恢复异常: {str(e)}")


class DatabaseBackupDialog(QDialog):
    """数据库备份和恢复对话框"""
    
    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.backup_thread = None
        self.restore_thread = None
        self.backup_schedule = BackupSchedule()
        
        self.setWindowTitle("数据库备份和恢复")
        self.setModal(True)
        self.resize(900, 700)
        self.setMinimumSize(800, 600)
        
        self._init_ui()
        self._load_backup_schedule()
        self._refresh_backup_list()
        self._setup_connections()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 备份标签页
        self.backup_tab = self._create_backup_tab()
        self.tab_widget.addTab(self.backup_tab, "数据库备份")
        
        # 恢复标签页
        self.restore_tab = self._create_restore_tab()
        self.tab_widget.addTab(self.restore_tab, "数据库恢复")
        
        # 自动备份标签页
        self.schedule_tab = self._create_schedule_tab()
        self.tab_widget.addTab(self.schedule_tab, "自动备份")
        
        layout.addWidget(self.tab_widget)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_layout.addWidget(self.button_box)
        
        layout.addLayout(button_layout)
    
    def _create_backup_tab(self) -> QWidget:
        """创建备份标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # 备份设置组
        backup_group = QGroupBox("备份设置")
        backup_layout = QFormLayout(backup_group)
        backup_layout.setSpacing(10)
        
        # 源数据库
        self.source_db_label = QLabel(self.db_path)
        self.source_db_label.setStyleSheet("color: blue; font-weight: bold;")
        backup_layout.addRow("源数据库:", self.source_db_label)
        
        # 备份路径
        backup_path_layout = QHBoxLayout()
        self.backup_path_input = QLineEdit()
        self.backup_path_input.setPlaceholderText("选择备份文件保存路径...")
        backup_path_layout.addWidget(self.backup_path_input)
        
        self.browse_backup_button = QPushButton("浏览...")
        self.browse_backup_button.setMaximumWidth(80)
        backup_path_layout.addWidget(self.browse_backup_button)
        
        backup_layout.addRow("备份路径:", backup_path_layout)
        
        # 备份说明
        self.backup_notes_input = QLineEdit()
        self.backup_notes_input.setPlaceholderText("备份说明（可选）...")
        backup_layout.addRow("备份说明:", self.backup_notes_input)
        
        layout.addWidget(backup_group)
        
        # 备份操作
        backup_action_layout = QHBoxLayout()
        self.start_backup_button = QPushButton("开始备份")
        self.start_backup_button.setMinimumHeight(40)
        self.start_backup_button.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        backup_action_layout.addWidget(self.start_backup_button)
        
        layout.addLayout(backup_action_layout)
        
        # 备份进度
        self.backup_progress = QProgressBar()
        self.backup_progress.setVisible(False)
        layout.addWidget(self.backup_progress)
        
        # 备份状态
        self.backup_status = QLabel("就绪")
        self.backup_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.backup_status)
        
        layout.addStretch()
        return widget
    
    def _create_restore_tab(self) -> QWidget:
        """创建恢复标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：备份列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        backup_list_group = QGroupBox("可用备份")
        backup_list_layout = QVBoxLayout(backup_list_group)
        
        # 备份列表
        self.backup_list = QTableWidget()
        self.backup_list.setColumnCount(4)
        self.backup_list.setHorizontalHeaderLabels(["文件名", "创建时间", "大小", "说明"])
        self.backup_list.horizontalHeader().setStretchLastSection(True)
        self.backup_list.setAlternatingRowColors(True)
        self.backup_list.setSelectionBehavior(QTableWidget.SelectRows)
        backup_list_layout.addWidget(self.backup_list)
        
        # 刷新按钮
        refresh_button = QPushButton("刷新列表")
        refresh_button.clicked.connect(self._refresh_backup_list)
        backup_list_layout.addWidget(refresh_button)
        
        left_layout.addWidget(backup_list_group)
        splitter.addWidget(left_widget)
        
        # 右侧：恢复操作
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 恢复设置
        restore_group = QGroupBox("恢复设置")
        restore_layout = QFormLayout(restore_group)
        
        # 选中的备份文件
        self.selected_backup_label = QLabel("未选择")
        self.selected_backup_label.setStyleSheet("color: gray;")
        restore_layout.addRow("备份文件:", self.selected_backup_label)
        
        # 目标数据库
        self.target_db_label = QLabel(self.db_path)
        self.target_db_label.setStyleSheet("color: blue; font-weight: bold;")
        restore_layout.addRow("目标数据库:", self.target_db_label)
        
        # 恢复选项
        self.backup_current_check = QCheckBox("恢复前备份当前数据库")
        self.backup_current_check.setChecked(True)
        restore_layout.addRow("安全选项:", self.backup_current_check)
        
        right_layout.addWidget(restore_group)
        
        # 恢复操作
        restore_action_layout = QHBoxLayout()
        self.start_restore_button = QPushButton("开始恢复")
        self.start_restore_button.setMinimumHeight(40)
        self.start_restore_button.setStyleSheet("font-weight: bold; background-color: #FF9800; color: white;")
        self.start_restore_button.setEnabled(False)
        restore_action_layout.addWidget(self.start_restore_button)
        
        right_layout.addLayout(restore_action_layout)
        
        # 恢复进度
        self.restore_progress = QProgressBar()
        self.restore_progress.setVisible(False)
        right_layout.addWidget(self.restore_progress)
        
        # 恢复状态
        self.restore_status = QLabel("请选择要恢复的备份文件")
        self.restore_status.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.restore_status)
        
        right_layout.addStretch()
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([400, 300])
        
        layout.addWidget(splitter)
        return widget
    
    def _create_schedule_tab(self) -> QWidget:
        """创建自动备份标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # 自动备份设置组
        schedule_group = QGroupBox("自动备份设置")
        schedule_layout = QFormLayout(schedule_group)
        schedule_layout.setSpacing(12)
        
        # 启用自动备份
        self.auto_backup_check = QCheckBox("启用自动备份")
        schedule_layout.addRow("自动备份:", self.auto_backup_check)
        
        # 备份频率
        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(["每日", "每周", "每月"])
        schedule_layout.addRow("备份频率:", self.frequency_combo)
        
        # 备份时间
        self.backup_time_edit = QDateTimeEdit()
        self.backup_time_edit.setDisplayFormat("HH:mm")
        self.backup_time_edit.setTime(QDateTime.currentDateTime().time())
        schedule_layout.addRow("备份时间:", self.backup_time_edit)
        
        # 备份目录
        backup_dir_layout = QHBoxLayout()
        self.backup_dir_input = QLineEdit()
        self.backup_dir_input.setPlaceholderText("选择自动备份保存目录...")
        backup_dir_layout.addWidget(self.backup_dir_input)
        
        self.browse_dir_button = QPushButton("浏览...")
        self.browse_dir_button.setMaximumWidth(80)
        backup_dir_layout.addWidget(self.browse_dir_button)
        
        schedule_layout.addRow("备份目录:", backup_dir_layout)
        
        # 保留备份数量
        self.keep_count_spin = QSpinBox()
        self.keep_count_spin.setRange(1, 100)
        self.keep_count_spin.setValue(7)
        self.keep_count_spin.setSuffix(" 个")
        schedule_layout.addRow("保留备份:", self.keep_count_spin)
        
        layout.addWidget(schedule_group)
        
        # 自动备份状态
        status_group = QGroupBox("备份状态")
        status_layout = QVBoxLayout(status_group)
        
        self.schedule_status_label = QLabel("自动备份未启用")
        self.schedule_status_label.setAlignment(Qt.AlignCenter)
        self.schedule_status_label.setStyleSheet("font-size: 14px; padding: 10px;")
        status_layout.addWidget(self.schedule_status_label)
        
        # 下次备份时间
        self.next_backup_label = QLabel("下次备份: 未设置")
        self.next_backup_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.next_backup_label)
        
        layout.addWidget(status_group)
        
        # 操作按钮
        action_layout = QHBoxLayout()
        
        self.save_schedule_button = QPushButton("保存设置")
        self.save_schedule_button.setMinimumHeight(35)
        action_layout.addWidget(self.save_schedule_button)
        
        self.test_backup_button = QPushButton("测试备份")
        self.test_backup_button.setMinimumHeight(35)
        action_layout.addWidget(self.test_backup_button)
        
        layout.addLayout(action_layout)
        
        layout.addStretch()
        return widget
    
    def _setup_connections(self):
        """设置信号连接"""
        # 备份相关
        self.browse_backup_button.clicked.connect(self._browse_backup_path)
        self.start_backup_button.clicked.connect(self._start_backup)
        
        # 恢复相关
        self.backup_list.itemSelectionChanged.connect(self._on_backup_selected)
        self.start_restore_button.clicked.connect(self._start_restore)
        
        # 自动备份相关
        self.browse_dir_button.clicked.connect(self._browse_backup_dir)
        self.save_schedule_button.clicked.connect(self._save_schedule)
        self.test_backup_button.clicked.connect(self._test_backup)
        self.auto_backup_check.toggled.connect(self._on_auto_backup_toggled)
        
        # 对话框按钮
        self.button_box.rejected.connect(self.reject)
    
    def _browse_backup_path(self):
        """浏览备份路径"""
        default_name = f"database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择备份文件保存位置",
            default_name,
            "SQLite数据库文件 (*.db);;所有文件 (*)"
        )
        
        if file_path:
            self.backup_path_input.setText(file_path)
    
    def _start_backup(self):
        """开始备份"""
        backup_path = self.backup_path_input.text().strip()
        if not backup_path:
            QMessageBox.warning(self, "警告", "请选择备份文件保存路径")
            return
        
        # 检查文件是否已存在
        if os.path.exists(backup_path):
            reply = QMessageBox.question(
                self,
                "文件已存在",
                f"文件 {os.path.basename(backup_path)} 已存在，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # 禁用按钮，显示进度条
        self.start_backup_button.setEnabled(False)
        self.backup_progress.setVisible(True)
        self.backup_progress.setValue(0)
        
        # 获取备份说明
        notes = self.backup_notes_input.text().strip()
        
        # 启动备份线程
        self.backup_thread = BackupThread(self.db_path, backup_path, notes)
        self.backup_thread.backup_progress.connect(self._on_backup_progress)
        self.backup_thread.backup_completed.connect(self._on_backup_completed)
        self.backup_thread.start()
    
    def _on_backup_progress(self, progress: int, message: str):
        """备份进度更新"""
        self.backup_progress.setValue(progress)
        self.backup_status.setText(message)
    
    def _on_backup_completed(self, success: bool, message: str, backup_path: str):
        """备份完成"""
        self.start_backup_button.setEnabled(True)
        self.backup_progress.setVisible(False)
        
        if success:
            self.backup_status.setText("备份完成")
            QMessageBox.information(self, "备份成功", f"{message}\n\n备份文件: {backup_path}")
            
            # 清空输入框
            self.backup_notes_input.clear()
            
            # 刷新备份列表
            self._refresh_backup_list()
        else:
            self.backup_status.setText("备份失败")
            QMessageBox.warning(self, "备份失败", message)
    
    def _refresh_backup_list(self):
        """刷新备份列表"""
        try:
            # 获取默认备份目录
            backup_dir = os.path.join(get_default_storage_path(), "backups")
            
            backups = []
            
            # 扫描备份文件
            if os.path.exists(backup_dir):
                for file_name in os.listdir(backup_dir):
                    if file_name.endswith('.db'):
                        file_path = os.path.join(backup_dir, file_name)
                        
                        try:
                            stat = os.stat(file_path)
                            created_at = datetime.fromtimestamp(stat.st_ctime)
                            file_size = stat.st_size
                            
                            # 尝试读取备份信息
                            info_file = file_path + '.info'
                            notes = ""
                            if os.path.exists(info_file):
                                try:
                                    with open(info_file, 'r', encoding='utf-8') as f:
                                        info = json.load(f)
                                        notes = info.get('notes', '')
                                except:
                                    pass
                            
                            backup_info = BackupInfo(
                                file_path=file_path,
                                created_at=created_at,
                                file_size=file_size,
                                notes=notes
                            )
                            backups.append(backup_info)
                            
                        except Exception as e:
                            logger.warning(f"读取备份文件信息失败 {file_path}: {e}")
            
            # 按创建时间排序（最新的在前）
            backups.sort(key=lambda x: x.created_at, reverse=True)
            
            # 更新表格
            self.backup_list.setRowCount(len(backups))
            
            for i, backup in enumerate(backups):
                self.backup_list.setItem(i, 0, QTableWidgetItem(backup.file_name))
                self.backup_list.setItem(i, 1, QTableWidgetItem(backup.created_at.strftime("%Y-%m-%d %H:%M:%S")))
                self.backup_list.setItem(i, 2, QTableWidgetItem(f"{backup.size_mb:.2f} MB"))
                self.backup_list.setItem(i, 3, QTableWidgetItem(backup.notes or ""))
                
                # 保存完整路径到第一列的数据中
                self.backup_list.item(i, 0).setData(Qt.UserRole, backup.file_path)
            
            # 调整列宽
            self.backup_list.resizeColumnsToContents()
            
        except Exception as e:
            logger.error(f"刷新备份列表失败: {e}")
    
    def _on_backup_selected(self):
        """备份文件选择改变"""
        current_row = self.backup_list.currentRow()
        if current_row >= 0:
            # 获取选中的备份文件路径
            item = self.backup_list.item(current_row, 0)
            if item:
                backup_path = item.data(Qt.UserRole)
                file_name = item.text()
                
                self.selected_backup_label.setText(file_name)
                self.selected_backup_label.setStyleSheet("color: blue; font-weight: bold;")
                self.start_restore_button.setEnabled(True)
                self.restore_status.setText("就绪")
                
                # 保存选中的备份路径
                self._selected_backup_path = backup_path
        else:
            self.selected_backup_label.setText("未选择")
            self.selected_backup_label.setStyleSheet("color: gray;")
            self.start_restore_button.setEnabled(False)
            self.restore_status.setText("请选择要恢复的备份文件")
            self._selected_backup_path = None  
  
    def _start_restore(self):
        """开始恢复"""
        if not hasattr(self, '_selected_backup_path') or not self._selected_backup_path:
            QMessageBox.warning(self, "警告", "请先选择要恢复的备份文件")
            return
        
        # 确认恢复操作
        reply = QMessageBox.question(
            self,
            "确认恢复",
            "恢复操作将覆盖当前数据库，所有未保存的数据将丢失。\n\n是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 禁用按钮，显示进度条
        self.start_restore_button.setEnabled(False)
        self.restore_progress.setVisible(True)
        self.restore_progress.setValue(0)
        
        # 启动恢复线程
        self.restore_thread = RestoreThread(self._selected_backup_path, self.db_path)
        self.restore_thread.restore_progress.connect(self._on_restore_progress)
        self.restore_thread.restore_completed.connect(self._on_restore_completed)
        self.restore_thread.start()
    
    def _on_restore_progress(self, progress: int, message: str):
        """恢复进度更新"""
        self.restore_progress.setValue(progress)
        self.restore_status.setText(message)
    
    def _on_restore_completed(self, success: bool, message: str):
        """恢复完成"""
        self.start_restore_button.setEnabled(True)
        self.restore_progress.setVisible(False)
        
        if success:
            self.restore_status.setText("恢复完成")
            QMessageBox.information(self, "恢复成功", message)
        else:
            self.restore_status.setText("恢复失败")
            QMessageBox.warning(self, "恢复失败", message)
    
    def _browse_backup_dir(self):
        """浏览备份目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择自动备份目录",
            self.backup_dir_input.text() or get_default_storage_path()
        )
        
        if dir_path:
            self.backup_dir_input.setText(dir_path)
    
    def _save_schedule(self):
        """保存自动备份计划"""
        try:
            # 更新备份计划
            self.backup_schedule.enabled = self.auto_backup_check.isChecked()
            
            frequency_map = {"每日": "daily", "每周": "weekly", "每月": "monthly"}
            self.backup_schedule.frequency = frequency_map[self.frequency_combo.currentText()]
            
            self.backup_schedule.time = self.backup_time_edit.time().toString("HH:mm")
            self.backup_schedule.backup_path = self.backup_dir_input.text().strip()
            self.backup_schedule.keep_count = self.keep_count_spin.value()
            
            # 验证设置
            if self.backup_schedule.enabled:
                if not self.backup_schedule.backup_path:
                    QMessageBox.warning(self, "警告", "请选择备份目录")
                    return
                
                if not os.path.exists(self.backup_schedule.backup_path):
                    try:
                        os.makedirs(self.backup_schedule.backup_path, exist_ok=True)
                    except Exception as e:
                        QMessageBox.warning(self, "错误", f"无法创建备份目录: {e}")
                        return
            
            # 保存到配置文件
            self._save_backup_schedule()
            
            # 更新状态显示
            self._update_schedule_status()
            
            QMessageBox.information(self, "设置保存", "自动备份设置已保存")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败: {e}")
    
    def _test_backup(self):
        """测试备份"""
        if not self.backup_schedule.backup_path:
            QMessageBox.warning(self, "警告", "请先设置备份目录")
            return
        
        # 生成测试备份文件名
        test_backup_path = os.path.join(
            self.backup_schedule.backup_path,
            f"test_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )
        
        # 设置备份路径并执行备份
        self.backup_path_input.setText(test_backup_path)
        self.backup_notes_input.setText("测试备份")
        
        # 切换到备份标签页
        self.tab_widget.setCurrentIndex(0)
        
        # 执行备份
        self._start_backup()
    
    def _on_auto_backup_toggled(self, enabled: bool):
        """自动备份开关切换"""
        # 启用/禁用相关控件
        self.frequency_combo.setEnabled(enabled)
        self.backup_time_edit.setEnabled(enabled)
        self.backup_dir_input.setEnabled(enabled)
        self.browse_dir_button.setEnabled(enabled)
        self.keep_count_spin.setEnabled(enabled)
        
        self._update_schedule_status()
    
    def _update_schedule_status(self):
        """更新自动备份状态显示"""
        if self.backup_schedule.enabled and self.auto_backup_check.isChecked():
            frequency_text = {"daily": "每日", "weekly": "每周", "monthly": "每月"}
            status_text = f"自动备份已启用 - {frequency_text.get(self.backup_schedule.frequency, '每日')} {self.backup_schedule.time}"
            self.schedule_status_label.setText(status_text)
            self.schedule_status_label.setStyleSheet("font-size: 14px; padding: 10px; color: green; font-weight: bold;")
            
            # 计算下次备份时间
            next_backup = self._calculate_next_backup_time()
            if next_backup:
                self.next_backup_label.setText(f"下次备份: {next_backup.strftime('%Y-%m-%d %H:%M')}")
            else:
                self.next_backup_label.setText("下次备份: 计算中...")
        else:
            self.schedule_status_label.setText("自动备份未启用")
            self.schedule_status_label.setStyleSheet("font-size: 14px; padding: 10px; color: gray;")
            self.next_backup_label.setText("下次备份: 未设置")
    
    def _calculate_next_backup_time(self) -> Optional[datetime]:
        """计算下次备份时间"""
        try:
            now = datetime.now()
            backup_time = datetime.strptime(self.backup_schedule.time, "%H:%M").time()
            
            if self.backup_schedule.frequency == "daily":
                next_backup = datetime.combine(now.date(), backup_time)
                if next_backup <= now:
                    next_backup += timedelta(days=1)
            elif self.backup_schedule.frequency == "weekly":
                # 每周同一天的同一时间
                days_ahead = 7 - now.weekday()  # 下周一
                next_backup = datetime.combine(now.date() + timedelta(days=days_ahead), backup_time)
            elif self.backup_schedule.frequency == "monthly":
                # 每月同一天的同一时间
                if now.month == 12:
                    next_month = now.replace(year=now.year + 1, month=1, day=1)
                else:
                    next_month = now.replace(month=now.month + 1, day=1)
                next_backup = datetime.combine(next_month.date(), backup_time)
            else:
                return None
            
            return next_backup
            
        except Exception as e:
            logger.error(f"计算下次备份时间失败: {e}")
            return None
    
    def _load_backup_schedule(self):
        """加载备份计划"""
        try:
            config_file = os.path.join(get_default_storage_path(), "backup_schedule.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                self.backup_schedule.enabled = config.get('enabled', False)
                self.backup_schedule.frequency = config.get('frequency', 'daily')
                self.backup_schedule.time = config.get('time', '02:00')
                self.backup_schedule.backup_path = config.get('backup_path', '')
                self.backup_schedule.keep_count = config.get('keep_count', 7)
            
            # 更新UI
            self.auto_backup_check.setChecked(self.backup_schedule.enabled)
            
            frequency_map = {"daily": "每日", "weekly": "每周", "monthly": "每月"}
            frequency_text = frequency_map.get(self.backup_schedule.frequency, "每日")
            self.frequency_combo.setCurrentText(frequency_text)
            
            time_obj = datetime.strptime(self.backup_schedule.time, "%H:%M").time()
            self.backup_time_edit.setTime(time_obj)
            
            self.backup_dir_input.setText(self.backup_schedule.backup_path)
            self.keep_count_spin.setValue(self.backup_schedule.keep_count)
            
            # 更新状态
            self._on_auto_backup_toggled(self.backup_schedule.enabled)
            
        except Exception as e:
            logger.error(f"加载备份计划失败: {e}")
            # 使用默认设置
            default_backup_dir = os.path.join(get_default_storage_path(), "backups")
            self.backup_dir_input.setText(default_backup_dir)
    
    def _save_backup_schedule(self):
        """保存备份计划"""
        try:
            config = {
                'enabled': self.backup_schedule.enabled,
                'frequency': self.backup_schedule.frequency,
                'time': self.backup_schedule.time,
                'backup_path': self.backup_schedule.backup_path,
                'keep_count': self.backup_schedule.keep_count,
                'last_updated': datetime.now().isoformat()
            }
            
            config_file = os.path.join(get_default_storage_path(), "backup_schedule.json")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"保存备份计划失败: {e}")
            raise
    
    def closeEvent(self, event):
        """关闭事件"""
        # 停止后台线程
        if self.backup_thread and self.backup_thread.isRunning():
            self.backup_thread.quit()
            self.backup_thread.wait()
        
        if self.restore_thread and self.restore_thread.isRunning():
            self.restore_thread.quit()
            self.restore_thread.wait()
        
        event.accept()