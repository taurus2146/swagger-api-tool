#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
异步数据操作对话框
提供异步操作监控、管理和配置的GUI界面
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QPushButton, QLabel, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QMessageBox, QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QHeaderView, QSplitter, QFrame, QProgressBar, QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from core.async_data_operations import (
    AsyncDataOperationSystem, DatabaseOperation, OperationType, 
    OperationStatus, OperationPriority, BatchOperation
)

logger = logging.getLogger(__name__)


class AsyncOperationsDialog(QDialog):
    """异步数据操作对话框"""
    
    def __init__(self, async_system: AsyncDataOperationSystem = None, parent=None):
        """
        初始化对话框
        
        Args:
            async_system: 异步数据操作系统实例
            parent: 父窗口
        """
        super().__init__(parent)
        self.async_system = async_system
        
        self.setWindowTitle("异步数据操作管理")
        self.setModal(True)
        self.resize(1000, 800)
        
        # 初始化UI
        self._init_ui()
        
        # 加载数据
        self._load_data()
        
        # 设置定时器更新状态
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_status)
        self._update_timer.start(1000)  # 每秒更新一次
    
    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        
        # 系统状态
        status_layout = QHBoxLayout()
        
        self.system_status_label = QLabel("系统状态: 未知")
        self.system_status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.system_status_label)
        
        # 系统控制按钮
        if self.async_system:
            self.start_btn = QPushButton("启动系统")
            self.start_btn.clicked.connect(self._start_system)
            status_layout.addWidget(self.start_btn)
            
            self.stop_btn = QPushButton("停止系统")
            self.stop_btn.clicked.connect(self._stop_system)
            status_layout.addWidget(self.stop_btn)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 操作队列标签页
        self._create_queue_tab()
        
        # 工作线程标签页
        self._create_workers_tab()
        
        # 批量操作标签页
        self._create_batch_tab()
        
        # 系统统计标签页
        self._create_stats_tab()
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self._load_data)
        button_layout.addWidget(self.refresh_btn)
        
        self.cleanup_btn = QPushButton("清理已完成操作")
        self.cleanup_btn.clicked.connect(self._cleanup_operations)
        button_layout.addWidget(self.cleanup_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_queue_tab(self):
        """创建操作队列标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 队列状态
        queue_status_group = QGroupBox("队列状态")
        queue_status_layout = QFormLayout(queue_status_group)
        
        self.queue_size_label = QLabel("0")
        queue_status_layout.addRow("队列大小:", self.queue_size_label)
        
        self.pending_ops_label = QLabel("0")
        queue_status_layout.addRow("等待操作:", self.pending_ops_label)
        
        self.running_ops_label = QLabel("0")
        queue_status_layout.addRow("运行中操作:", self.running_ops_label)
        
        layout.addWidget(queue_status_group)
        
        # 操作列表
        self.operations_table = QTableWidget()
        self.operations_table.setColumnCount(8)
        self.operations_table.setHorizontalHeaderLabels([
            "ID", "类型", "状态", "优先级", "创建时间", "执行时间", "重试次数", "操作"
        ])
        
        # 设置表格属性
        header = self.operations_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)  # ID
        header.setSectionResizeMode(1, QHeaderView.Fixed)        # 类型
        header.setSectionResizeMode(2, QHeaderView.Fixed)        # 状态
        header.setSectionResizeMode(3, QHeaderView.Fixed)        # 优先级
        header.setSectionResizeMode(4, QHeaderView.Fixed)        # 创建时间
        header.setSectionResizeMode(5, QHeaderView.Fixed)        # 执行时间
        header.setSectionResizeMode(6, QHeaderView.Fixed)        # 重试次数
        header.setSectionResizeMode(7, QHeaderView.Fixed)        # 操作
        
        self.operations_table.setColumnWidth(1, 100)
        self.operations_table.setColumnWidth(2, 80)
        self.operations_table.setColumnWidth(3, 80)
        self.operations_table.setColumnWidth(4, 120)
        self.operations_table.setColumnWidth(5, 100)
        self.operations_table.setColumnWidth(6, 80)
        self.operations_table.setColumnWidth(7, 100)
        
        self.operations_table.setAlternatingRowColors(True)
        self.operations_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(QLabel("操作列表:"))
        layout.addWidget(self.operations_table)
        
        self.tab_widget.addTab(tab, "操作队列")
    
    def _create_workers_tab(self):
        """创建工作线程标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 工作线程表格
        self.workers_table = QTableWidget()
        self.workers_table.setColumnCount(7)
        self.workers_table.setHorizontalHeaderLabels([
            "线程ID", "状态", "已处理操作", "总执行时间", "平均执行时间", "错误次数", "当前操作"
        ])
        
        # 设置表格属性
        workers_header = self.workers_table.horizontalHeader()
        workers_header.setSectionResizeMode(0, QHeaderView.Fixed)        # 线程ID
        workers_header.setSectionResizeMode(1, QHeaderView.Fixed)        # 状态
        workers_header.setSectionResizeMode(2, QHeaderView.Fixed)        # 已处理操作
        workers_header.setSectionResizeMode(3, QHeaderView.Fixed)        # 总执行时间
        workers_header.setSectionResizeMode(4, QHeaderView.Fixed)        # 平均执行时间
        workers_header.setSectionResizeMode(5, QHeaderView.Fixed)        # 错误次数
        workers_header.setSectionResizeMode(6, QHeaderView.Stretch)      # 当前操作
        
        self.workers_table.setColumnWidth(0, 80)
        self.workers_table.setColumnWidth(1, 80)
        self.workers_table.setColumnWidth(2, 100)
        self.workers_table.setColumnWidth(3, 120)
        self.workers_table.setColumnWidth(4, 120)
        self.workers_table.setColumnWidth(5, 80)
        
        self.workers_table.setAlternatingRowColors(True)
        
        layout.addWidget(QLabel("工作线程状态:"))
        layout.addWidget(self.workers_table)
        
        self.tab_widget.addTab(tab, "工作线程")
    
    def _create_batch_tab(self):
        """创建批量操作标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 批量操作创建
        batch_create_group = QGroupBox("创建批量操作")
        batch_create_layout = QFormLayout(batch_create_group)
        
        self.batch_type_combo = QComboBox()
        self.batch_type_combo.addItems([
            "BATCH_INSERT", "BATCH_UPDATE", "BATCH_DELETE"
        ])
        batch_create_layout.addRow("操作类型:", self.batch_type_combo)
        
        self.batch_table_edit = QLineEdit()
        self.batch_table_edit.setPlaceholderText("表名")
        batch_create_layout.addRow("表名:", self.batch_table_edit)
        
        self.create_batch_btn = QPushButton("创建批量操作")
        self.create_batch_btn.clicked.connect(self._create_batch_operation)
        batch_create_layout.addRow(self.create_batch_btn)
        
        layout.addWidget(batch_create_group)
        
        # 批量操作列表
        self.batch_table = QTableWidget()
        self.batch_table.setColumnCount(5)
        self.batch_table.setHorizontalHeaderLabels([
            "ID", "类型", "表名", "操作数量", "创建时间"
        ])
        
        batch_header = self.batch_table.horizontalHeader()
        batch_header.setSectionResizeMode(0, QHeaderView.Interactive)
        batch_header.setSectionResizeMode(1, QHeaderView.Fixed)
        batch_header.setSectionResizeMode(2, QHeaderView.Fixed)
        batch_header.setSectionResizeMode(3, QHeaderView.Fixed)
        batch_header.setSectionResizeMode(4, QHeaderView.Stretch)
        
        self.batch_table.setColumnWidth(1, 120)
        self.batch_table.setColumnWidth(2, 100)
        self.batch_table.setColumnWidth(3, 100)
        
        self.batch_table.setAlternatingRowColors(True)
        
        layout.addWidget(QLabel("批量操作列表:"))
        layout.addWidget(self.batch_table)
        
        self.tab_widget.addTab(tab, "批量操作")
    
    def _create_stats_tab(self):
        """创建系统统计标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 总体统计
        overall_group = QGroupBox("总体统计")
        overall_layout = QFormLayout(overall_group)
        
        self.total_operations_label = QLabel("0")
        overall_layout.addRow("总操作数:", self.total_operations_label)
        
        self.completed_operations_label = QLabel("0")
        overall_layout.addRow("已完成操作:", self.completed_operations_label)
        
        self.failed_operations_label = QLabel("0")
        overall_layout.addRow("失败操作:", self.failed_operations_label)
        
        self.success_rate_label = QLabel("0%")
        overall_layout.addRow("成功率:", self.success_rate_label)
        
        layout.addWidget(overall_group)
        
        # 性能统计
        performance_group = QGroupBox("性能统计")
        performance_layout = QVBoxLayout(performance_group)
        
        self.performance_text = QTextEdit()
        self.performance_text.setReadOnly(True)
        self.performance_text.setMaximumHeight(200)
        performance_layout.addWidget(self.performance_text)
        
        layout.addWidget(performance_group)
        
        # 系统配置
        config_group = QGroupBox("系统配置")
        config_layout = QFormLayout(config_group)
        
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 10)
        self.max_workers_spin.setValue(3)
        config_layout.addRow("最大工作线程:", self.max_workers_spin)
        
        self.queue_size_spin = QSpinBox()
        self.queue_size_spin.setRange(100, 10000)
        self.queue_size_spin.setValue(1000)
        config_layout.addRow("队列大小:", self.queue_size_spin)
        
        self.cleanup_hours_spin = QSpinBox()
        self.cleanup_hours_spin.setRange(1, 168)  # 1小时到1周
        self.cleanup_hours_spin.setValue(24)
        self.cleanup_hours_spin.setSuffix(" 小时")
        config_layout.addRow("清理间隔:", self.cleanup_hours_spin)
        
        layout.addWidget(config_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "系统统计")    def
 _load_data(self):
        """加载数据"""
        if not self.async_system:
            return
        
        try:
            # 更新系统状态
            self._update_system_status()
            
            # 更新操作列表
            self._update_operations_table()
            
            # 更新工作线程状态
            self._update_workers_table()
            
            # 更新批量操作
            self._update_batch_table()
            
            # 更新统计信息
            self._update_stats()
            
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            QMessageBox.critical(self, "错误", f"加载数据失败:\n{str(e)}")
    
    def _update_system_status(self):
        """更新系统状态"""
        if not self.async_system:
            self.system_status_label.setText("系统状态: 未连接")
            self.system_status_label.setStyleSheet("color: red; font-weight: bold;")
            return
        
        if self.async_system.running:
            self.system_status_label.setText("系统状态: 运行中")
            self.system_status_label.setStyleSheet("color: green; font-weight: bold;")
            if hasattr(self, 'start_btn'):
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)
        else:
            self.system_status_label.setText("系统状态: 已停止")
            self.system_status_label.setStyleSheet("color: red; font-weight: bold;")
            if hasattr(self, 'start_btn'):
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
    
    def _update_operations_table(self):
        """更新操作表格"""
        if not self.async_system:
            self.operations_table.setRowCount(0)
            return
        
        operations = list(self.async_system.operations.values())
        # 按创建时间排序，最新的在前
        operations.sort(key=lambda x: x.created_at, reverse=True)
        
        # 只显示最近的100个操作
        operations = operations[:100]
        
        self.operations_table.setRowCount(len(operations))
        
        for i, operation in enumerate(operations):
            # ID
            self.operations_table.setItem(i, 0, QTableWidgetItem(operation.id))
            
            # 类型
            self.operations_table.setItem(i, 1, QTableWidgetItem(operation.operation_type.value))
            
            # 状态
            status_item = QTableWidgetItem(operation.status.value)
            if operation.status == OperationStatus.COMPLETED:
                status_item.setForeground(Qt.darkGreen)
            elif operation.status == OperationStatus.FAILED:
                status_item.setForeground(Qt.red)
            elif operation.status == OperationStatus.RUNNING:
                status_item.setForeground(Qt.blue)
            self.operations_table.setItem(i, 2, status_item)
            
            # 优先级
            self.operations_table.setItem(i, 3, QTableWidgetItem(operation.priority.name))
            
            # 创建时间
            created_str = operation.created_at.strftime("%m-%d %H:%M:%S")
            self.operations_table.setItem(i, 4, QTableWidgetItem(created_str))
            
            # 执行时间
            if operation.execution_time:
                exec_time = f"{operation.execution_time:.3f}s"
            else:
                exec_time = "-"
            self.operations_table.setItem(i, 5, QTableWidgetItem(exec_time))
            
            # 重试次数
            retry_item = QTableWidgetItem(f"{operation.retry_count}/{operation.max_retries}")
            if operation.retry_count > 0:
                retry_item.setForeground(Qt.darkYellow)
            self.operations_table.setItem(i, 6, retry_item)
            
            # 操作按钮（简化处理）
            if operation.status == OperationStatus.PENDING:
                self.operations_table.setItem(i, 7, QTableWidgetItem("可取消"))
            else:
                self.operations_table.setItem(i, 7, QTableWidgetItem("-"))
        
        # 更新队列状态
        queue_status = self.async_system.get_queue_status()
        self.queue_size_label.setText(f"{queue_status['queue_size']}/{queue_status['max_queue_size']}")
        self.pending_ops_label.setText(str(queue_status['pending_operations']))
        self.running_ops_label.setText(str(queue_status['running_operations']))
    
    def _update_workers_table(self):
        """更新工作线程表格"""
        if not self.async_system:
            self.workers_table.setRowCount(0)
            return
        
        worker_stats = self.async_system.get_worker_stats()
        self.workers_table.setRowCount(len(worker_stats))
        
        for i, stats in enumerate(worker_stats):
            # 线程ID
            self.workers_table.setItem(i, 0, QTableWidgetItem(str(stats['worker_id'])))
            
            # 状态
            status_text = "运行中" if stats['running'] else "已停止"
            status_item = QTableWidgetItem(status_text)
            if stats['running']:
                status_item.setForeground(Qt.darkGreen)
            else:
                status_item.setForeground(Qt.red)
            self.workers_table.setItem(i, 1, status_item)
            
            # 已处理操作
            processed_item = QTableWidgetItem(str(stats['operations_processed']))
            processed_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.workers_table.setItem(i, 2, processed_item)
            
            # 总执行时间
            total_time_item = QTableWidgetItem(f"{stats['total_execution_time']:.3f}s")
            total_time_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.workers_table.setItem(i, 3, total_time_item)
            
            # 平均执行时间
            avg_time_item = QTableWidgetItem(f"{stats['average_execution_time']:.3f}s")
            avg_time_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.workers_table.setItem(i, 4, avg_time_item)
            
            # 错误次数
            errors_item = QTableWidgetItem(str(stats['errors_count']))
            errors_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if stats['errors_count'] > 0:
                errors_item.setForeground(Qt.red)
            self.workers_table.setItem(i, 5, errors_item)
            
            # 当前操作
            current_op = stats['current_operation'] or "-"
            self.workers_table.setItem(i, 6, QTableWidgetItem(current_op))
    
    def _update_batch_table(self):
        """更新批量操作表格"""
        if not self.async_system:
            self.batch_table.setRowCount(0)
            return
        
        batches = list(self.async_system.batch_operations.values())
        batches.sort(key=lambda x: x.created_at, reverse=True)
        
        self.batch_table.setRowCount(len(batches))
        
        for i, batch in enumerate(batches):
            # ID
            self.batch_table.setItem(i, 0, QTableWidgetItem(batch.id))
            
            # 类型
            self.batch_table.setItem(i, 1, QTableWidgetItem(batch.operation_type.value))
            
            # 表名
            self.batch_table.setItem(i, 2, QTableWidgetItem(batch.table_name))
            
            # 操作数量
            count_item = QTableWidgetItem(str(len(batch)))
            count_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.batch_table.setItem(i, 3, count_item)
            
            # 创建时间
            created_str = batch.created_at.strftime("%m-%d %H:%M:%S")
            self.batch_table.setItem(i, 4, QTableWidgetItem(created_str))
    
    def _update_stats(self):
        """更新统计信息"""
        if not self.async_system:
            self.total_operations_label.setText("0")
            self.completed_operations_label.setText("0")
            self.failed_operations_label.setText("0")
            self.success_rate_label.setText("0%")
            self.performance_text.clear()
            return
        
        queue_status = self.async_system.get_queue_status()
        worker_stats = self.async_system.get_worker_stats()
        
        # 基本统计
        total_ops = queue_status['total_operations']
        completed_ops = queue_status['completed_operations']
        failed_ops = queue_status['failed_operations']
        
        self.total_operations_label.setText(str(total_ops))
        self.completed_operations_label.setText(str(completed_ops))
        self.failed_operations_label.setText(str(failed_ops))
        
        # 成功率
        if total_ops > 0:
            success_rate = (completed_ops / total_ops) * 100
            self.success_rate_label.setText(f"{success_rate:.1f}%")
        else:
            self.success_rate_label.setText("0%")
        
        # 性能统计
        performance_lines = [
            "性能统计信息:",
            "",
            f"队列使用率: {queue_status['queue_size']}/{queue_status['max_queue_size']} ({queue_status['queue_size']/queue_status['max_queue_size']*100:.1f}%)",
            f"活跃工作线程: {queue_status['running_workers']}/{queue_status['total_workers']}",
            f"等待操作: {queue_status['pending_operations']}",
            f"运行中操作: {queue_status['running_operations']}",
            "",
            "工作线程性能:"
        ]
        
        total_processed = sum(stats['operations_processed'] for stats in worker_stats)
        total_time = sum(stats['total_execution_time'] for stats in worker_stats)
        total_errors = sum(stats['errors_count'] for stats in worker_stats)
        
        performance_lines.extend([
            f"总处理操作数: {total_processed}",
            f"总执行时间: {total_time:.3f}秒",
            f"平均操作时间: {total_time/total_processed:.3f}秒" if total_processed > 0 else "平均操作时间: 0秒",
            f"总错误数: {total_errors}",
            f"错误率: {total_errors/total_processed*100:.2f}%" if total_processed > 0 else "错误率: 0%"
        ])
        
        self.performance_text.setPlainText("\n".join(performance_lines))
    
    def _update_status(self):
        """定时更新状态"""
        try:
            self._update_system_status()
            self._update_operations_table()
            self._update_workers_table()
            self._update_stats()
        except Exception as e:
            logger.debug(f"更新状态时发生错误: {e}")
    
    def _start_system(self):
        """启动系统"""
        if self.async_system and not self.async_system.running:
            try:
                self.async_system.start()
                QMessageBox.information(self, "成功", "异步操作系统已启动")
                self._update_system_status()
            except Exception as e:
                logger.error(f"启动系统失败: {e}")
                QMessageBox.critical(self, "错误", f"启动系统失败:\n{str(e)}")
    
    def _stop_system(self):
        """停止系统"""
        if self.async_system and self.async_system.running:
            reply = QMessageBox.question(
                self, "确认停止",
                "确定要停止异步操作系统吗?\n\n正在运行的操作将被中断。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                try:
                    self.async_system.stop()
                    QMessageBox.information(self, "成功", "异步操作系统已停止")
                    self._update_system_status()
                except Exception as e:
                    logger.error(f"停止系统失败: {e}")
                    QMessageBox.critical(self, "错误", f"停止系统失败:\n{str(e)}")
    
    def _create_batch_operation(self):
        """创建批量操作"""
        if not self.async_system:
            QMessageBox.warning(self, "警告", "异步操作系统未连接")
            return
        
        operation_type_str = self.batch_type_combo.currentText()
        table_name = self.batch_table_edit.text().strip()
        
        if not table_name:
            QMessageBox.warning(self, "警告", "请输入表名")
            return
        
        try:
            operation_type = OperationType(operation_type_str.lower())
            batch = self.async_system.create_batch_operation(operation_type, table_name)
            
            QMessageBox.information(
                self, "成功", 
                f"批量操作已创建: {batch.id}\n\n"
                f"类型: {operation_type.value}\n"
                f"表名: {table_name}\n\n"
                f"现在可以向批量操作添加具体的SQL操作。"
            )
            
            # 清空输入
            self.batch_table_edit.clear()
            
            # 刷新批量操作列表
            self._update_batch_table()
            
        except Exception as e:
            logger.error(f"创建批量操作失败: {e}")
            QMessageBox.critical(self, "错误", f"创建批量操作失败:\n{str(e)}")
    
    def _cleanup_operations(self):
        """清理已完成的操作"""
        if not self.async_system:
            return
        
        hours = self.cleanup_hours_spin.value()
        
        reply = QMessageBox.question(
            self, "确认清理",
            f"确定要清理 {hours} 小时前的已完成操作吗?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                cleaned_count = self.async_system.cleanup_completed_operations(hours)
                QMessageBox.information(
                    self, "清理完成", 
                    f"已清理 {cleaned_count} 个已完成的操作"
                )
                self._load_data()
            except Exception as e:
                logger.error(f"清理操作失败: {e}")
                QMessageBox.critical(self, "错误", f"清理操作失败:\n{str(e)}")
    
    def closeEvent(self, event):
        """关闭事件"""
        if self._update_timer:
            self._update_timer.stop()
        super().closeEvent(event)