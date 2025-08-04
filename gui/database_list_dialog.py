#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库列表管理对话框
提供数据库配置的列表显示、切换、管理功能
"""

import os
import logging
from typing import Optional, Callable
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView, QMenu, QAction,
    QGroupBox, QSplitter, QTextEdit, QProgressBar, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QFont

from core.database_config_manager import DatabaseConfigManager, DatabaseConfig
from core.database_switcher import DatabaseSwitcher, DatabaseSwitchResult

logger = logging.getLogger(__name__)


class DatabaseListDialog(QDialog):
    """数据库列表管理对话框"""
    
    # 信号
    database_switched = pyqtSignal(str)  # 数据库切换信号，参数为新的配置ID
    
    def __init__(self, config_manager: DatabaseConfigManager, 
                 database_switcher: DatabaseSwitcher, parent=None):
        """
        初始化对话框
        
        Args:
            config_manager: 数据库配置管理器
            database_switcher: 数据库切换服务
            parent: 父窗口
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.database_switcher = database_switcher
        
        # 设置切换回调
        self.database_switcher.set_pre_switch_callback(self._on_pre_switch)
        self.database_switcher.set_post_switch_callback(self._on_post_switch)
        
        self.setWindowTitle("数据库管理")
        self.setModal(True)
        self.resize(800, 600)
        
        # 初始化UI
        self._init_ui()
        
        # 加载数据
        self._load_database_list()
        
        # 设置定时器更新状态
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_status)
        self._update_timer.start(5000)  # 每5秒更新一次
    
    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧：数据库列表
        left_widget = self._create_database_list_widget()
        splitter.addWidget(left_widget)
        
        # 右侧：详细信息和操作
        right_widget = self._create_details_widget()
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([500, 300])
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self._load_database_list)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_database_list_widget(self):
        """创建数据库列表部件"""
        group = QGroupBox("数据库列表")
        layout = QVBoxLayout(group)
        
        # 当前数据库信息
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("当前数据库:"))
        
        self.current_db_label = QLabel("无")
        self.current_db_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        current_layout.addWidget(self.current_db_label)
        
        current_layout.addStretch()
        layout.addLayout(current_layout)
        
        # 数据库表格
        self.database_table = QTableWidget()
        self.database_table.setColumnCount(6)
        self.database_table.setHorizontalHeaderLabels([
            "名称", "路径", "状态", "大小", "最后访问", "连接次数"
        ])
        
        # 设置表格属性
        header = self.database_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)  # 名称
        header.setSectionResizeMode(1, QHeaderView.Stretch)      # 路径
        header.setSectionResizeMode(2, QHeaderView.Fixed)        # 状态
        header.setSectionResizeMode(3, QHeaderView.Fixed)        # 大小
        header.setSectionResizeMode(4, QHeaderView.Fixed)        # 最后访问
        header.setSectionResizeMode(5, QHeaderView.Fixed)        # 连接次数
        
        # 设置列宽
        self.database_table.setColumnWidth(2, 80)   # 状态
        self.database_table.setColumnWidth(3, 80)   # 大小
        self.database_table.setColumnWidth(4, 120)  # 最后访问
        self.database_table.setColumnWidth(5, 80)   # 连接次数
        
        self.database_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.database_table.setAlternatingRowColors(True)
        self.database_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.database_table.customContextMenuRequested.connect(self._show_context_menu)
        self.database_table.itemDoubleClicked.connect(self._on_double_click)
        self.database_table.itemSelectionChanged.connect(self._on_selection_changed)
        
        layout.addWidget(self.database_table)
        
        # 快速操作按钮
        button_layout = QHBoxLayout()
        
        self.switch_btn = QPushButton("切换到此数据库")
        self.switch_btn.setEnabled(False)
        self.switch_btn.clicked.connect(self._switch_to_selected)
        button_layout.addWidget(self.switch_btn)
        
        self.set_default_btn = QPushButton("设为默认")
        self.set_default_btn.setEnabled(False)
        self.set_default_btn.clicked.connect(self._set_as_default)
        button_layout.addWidget(self.set_default_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        return group
    
    def _create_details_widget(self):
        """创建详细信息部件"""
        group = QGroupBox("详细信息")
        layout = QVBoxLayout(group)
        
        # 基本信息
        info_frame = QFrame()
        info_layout = QVBoxLayout(info_frame)
        
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(200)
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)
        
        layout.addWidget(info_frame)
        
        # 操作按钮
        action_layout = QVBoxLayout()
        
        self.validate_btn = QPushButton("验证数据库")
        self.validate_btn.setEnabled(False)
        self.validate_btn.clicked.connect(self._validate_selected)
        action_layout.addWidget(self.validate_btn)
        
        self.open_folder_btn = QPushButton("打开文件夹")
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self._open_folder)
        action_layout.addWidget(self.open_folder_btn)
        
        action_layout.addStretch()
        
        self.remove_btn = QPushButton("删除配置")
        self.remove_btn.setEnabled(False)
        self.remove_btn.setStyleSheet("QPushButton { color: #f44336; }")
        self.remove_btn.clicked.connect(self._remove_selected)
        action_layout.addWidget(self.remove_btn)
        
        layout.addLayout(action_layout)
        
        # 进度条（用于显示操作进度）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        return group
    
    def _load_database_list(self):
        """加载数据库列表"""
        try:
            configs = self.config_manager.get_all_configs()
            current_config = self.database_switcher.get_current_config()
            
            # 更新当前数据库显示
            if current_config:
                self.current_db_label.setText(current_config.name)
            else:
                self.current_db_label.setText("无")
            
            # 清空表格
            self.database_table.setRowCount(0)
            
            # 添加数据
            for i, config in enumerate(configs):
                self.database_table.insertRow(i)
                
                # 名称
                name_item = QTableWidgetItem(config.name)
                if current_config and config.id == current_config.id:
                    name_item.setFont(QFont("", -1, QFont.Bold))
                    name_item.setForeground(Qt.blue)
                if config.is_default:
                    name_item.setText(f"{config.name} (默认)")
                self.database_table.setItem(i, 0, name_item)
                
                # 路径
                path_item = QTableWidgetItem(config.path)
                path_item.setToolTip(config.path)
                self.database_table.setItem(i, 1, path_item)
                
                # 状态
                status_item = QTableWidgetItem("存在" if config.exists else "缺失")
                status_item.setForeground(Qt.darkGreen if config.exists else Qt.red)
                self.database_table.setItem(i, 2, status_item)
                
                # 大小
                size_text = f"{config.size_mb:.1f} MB" if config.file_size > 0 else "0 MB"
                size_item = QTableWidgetItem(size_text)
                size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.database_table.setItem(i, 3, size_item)
                
                # 最后访问时间
                try:
                    last_accessed = datetime.fromisoformat(config.last_accessed)
                    time_text = last_accessed.strftime("%m-%d %H:%M")
                except:
                    time_text = "未知"
                time_item = QTableWidgetItem(time_text)
                time_item.setTextAlignment(Qt.AlignCenter)
                self.database_table.setItem(i, 4, time_item)
                
                # 连接次数
                count_item = QTableWidgetItem(str(config.connection_count))
                count_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.database_table.setItem(i, 5, count_item)
                
                # 存储配置ID
                name_item.setData(Qt.UserRole, config.id)
            
            logger.info(f"加载了 {len(configs)} 个数据库配置")
            
        except Exception as e:
            logger.error(f"加载数据库列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载数据库列表失败:\n{str(e)}")
    
    def _on_selection_changed(self):
        """选择变化处理"""
        selected_rows = self.database_table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0
        
        # 更新按钮状态
        self.switch_btn.setEnabled(has_selection)
        self.set_default_btn.setEnabled(has_selection)
        self.validate_btn.setEnabled(has_selection)
        self.open_folder_btn.setEnabled(has_selection)
        self.remove_btn.setEnabled(has_selection)
        
        # 更新详细信息
        if has_selection:
            self._update_details()
        else:
            self.info_text.clear()
    
    def _update_details(self):
        """更新详细信息"""
        selected_rows = self.database_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        config_id = self.database_table.item(row, 0).data(Qt.UserRole)
        config = self.config_manager.get_config(config_id)
        
        if not config:
            return
        
        # 构建详细信息文本
        info_lines = [
            f"配置ID: {config.id}",
            f"名称: {config.name}",
            f"描述: {config.description or '无'}",
            f"路径: {config.path}",
            f"创建时间: {config.created_at}",
            f"最后访问: {config.last_accessed}",
            f"连接次数: {config.connection_count}",
            f"文件大小: {config.size_mb:.2f} MB",
            f"是否默认: {'是' if config.is_default else '否'}",
            f"标签: {', '.join(config.tags) if config.tags else '无'}",
            ""
        ]
        
        # 添加连接历史
        history = self.config_manager.get_connection_history(config.id, limit=5)
        if history:
            info_lines.append("最近连接历史:")
            for h in history:
                status = "成功" if h.success else f"失败({h.error_message})"
                time_str = datetime.fromisoformat(h.connected_at).strftime("%m-%d %H:%M:%S")
                info_lines.append(f"  {time_str}: {status}")
        else:
            info_lines.append("无连接历史")
        
        self.info_text.setPlainText("\n".join(info_lines))
    
    def _show_context_menu(self, position):
        """显示右键菜单"""
        if not self.database_table.itemAt(position):
            return
        
        menu = QMenu(self)
        
        # 切换数据库
        switch_action = QAction("切换到此数据库", self)
        switch_action.triggered.connect(self._switch_to_selected)
        menu.addAction(switch_action)
        
        # 设为默认
        default_action = QAction("设为默认", self)
        default_action.triggered.connect(self._set_as_default)
        menu.addAction(default_action)
        
        menu.addSeparator()
        
        # 验证数据库
        validate_action = QAction("验证数据库", self)
        validate_action.triggered.connect(self._validate_selected)
        menu.addAction(validate_action)
        
        # 打开文件夹
        folder_action = QAction("打开文件夹", self)
        folder_action.triggered.connect(self._open_folder)
        menu.addAction(folder_action)
        
        menu.addSeparator()
        
        # 删除配置
        remove_action = QAction("删除配置", self)
        remove_action.triggered.connect(self._remove_selected)
        menu.addAction(remove_action)
        
        menu.exec_(self.database_table.mapToGlobal(position))
    
    def _on_double_click(self, item):
        """双击处理"""
        self._switch_to_selected()
    
    def _switch_to_selected(self):
        """切换到选中的数据库"""
        selected_rows = self.database_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        config_id = self.database_table.item(row, 0).data(Qt.UserRole)
        
        # 显示进度
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        
        try:
            result = self.database_switcher.switch_to_config(config_id)
            
            if result.success:
                QMessageBox.information(self, "成功", result.message)
                self.database_switched.emit(config_id)
                self._load_database_list()  # 刷新列表
            else:
                QMessageBox.warning(self, "切换失败", result.message)
        
        except Exception as e:
            logger.error(f"切换数据库时发生异常: {e}")
            QMessageBox.critical(self, "错误", f"切换数据库时发生异常:\n{str(e)}")
        
        finally:
            self.progress_bar.setVisible(False)
    
    def _set_as_default(self):
        """设为默认数据库"""
        selected_rows = self.database_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        config_id = self.database_table.item(row, 0).data(Qt.UserRole)
        
        try:
            if self.config_manager.set_default_config(config_id):
                QMessageBox.information(self, "成功", "已设为默认数据库")
                self._load_database_list()  # 刷新列表
            else:
                QMessageBox.warning(self, "失败", "设置默认数据库失败")
        
        except Exception as e:
            logger.error(f"设置默认数据库失败: {e}")
            QMessageBox.critical(self, "错误", f"设置默认数据库失败:\n{str(e)}")
    
    def _validate_selected(self):
        """验证选中的数据库"""
        selected_rows = self.database_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        config_id = self.database_table.item(row, 0).data(Qt.UserRole)
        
        try:
            result = self.database_switcher.validate_config(config_id)
            
            if result['valid']:
                QMessageBox.information(self, "验证结果", "数据库配置有效")
            else:
                QMessageBox.warning(self, "验证结果", f"数据库配置无效:\n{result['message']}")
        
        except Exception as e:
            logger.error(f"验证数据库失败: {e}")
            QMessageBox.critical(self, "错误", f"验证数据库失败:\n{str(e)}")
    
    def _open_folder(self):
        """打开数据库文件夹"""
        selected_rows = self.database_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        config_id = self.database_table.item(row, 0).data(Qt.UserRole)
        config = self.config_manager.get_config(config_id)
        
        if not config:
            return
        
        try:
            folder_path = os.path.dirname(config.path)
            if os.path.exists(folder_path):
                os.startfile(folder_path)  # Windows
            else:
                QMessageBox.warning(self, "警告", "文件夹不存在")
        
        except Exception as e:
            logger.error(f"打开文件夹失败: {e}")
            QMessageBox.critical(self, "错误", f"打开文件夹失败:\n{str(e)}")
    
    def _remove_selected(self):
        """删除选中的配置"""
        selected_rows = self.database_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        config_id = self.database_table.item(row, 0).data(Qt.UserRole)
        config = self.config_manager.get_config(config_id)
        
        if not config:
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除数据库配置 '{config.name}' 吗?\n\n"
            "注意：这只会删除配置信息，不会删除实际的数据库文件。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.config_manager.remove_config(config_id):
                    QMessageBox.information(self, "成功", "配置已删除")
                    self._load_database_list()  # 刷新列表
                else:
                    QMessageBox.warning(self, "失败", "删除配置失败")
            
            except Exception as e:
                logger.error(f"删除配置失败: {e}")
                QMessageBox.critical(self, "错误", f"删除配置失败:\n{str(e)}")
    
    def _update_status(self):
        """定时更新状态"""
        try:
            # 更新文件大小等信息
            for row in range(self.database_table.rowCount()):
                config_id = self.database_table.item(row, 0).data(Qt.UserRole)
                config = self.config_manager.get_config(config_id)
                
                if config:
                    # 更新文件大小
                    config.update_file_info()
                    size_text = f"{config.size_mb:.1f} MB" if config.file_size > 0 else "0 MB"
                    self.database_table.item(row, 3).setText(size_text)
                    
                    # 更新状态
                    status_text = "存在" if config.exists else "缺失"
                    status_item = self.database_table.item(row, 2)
                    status_item.setText(status_text)
                    status_item.setForeground(Qt.darkGreen if config.exists else Qt.red)
        
        except Exception as e:
            logger.debug(f"更新状态时发生错误: {e}")
    
    def _on_pre_switch(self, old_config, new_config) -> bool:
        """切换前确认回调"""
        if old_config and old_config.id != new_config.id:
            reply = QMessageBox.question(
                self, "确认切换",
                f"确定要从 '{old_config.name}' 切换到 '{new_config.name}' 吗?\n\n"
                "当前的未保存数据将会丢失。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            return reply == QMessageBox.Yes
        return True
    
    def _on_post_switch(self, result: DatabaseSwitchResult):
        """切换后通知回调"""
        if result.success:
            logger.info(f"数据库切换成功: {result.message}")
        else:
            logger.warning(f"数据库切换失败: {result.message}")
    
    def closeEvent(self, event):
        """关闭事件"""
        if self._update_timer:
            self._update_timer.stop()
        super().closeEvent(event)