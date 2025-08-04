#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库诊断和维护对话框
提供数据库健康检查和维护工具的图形界面
"""
import os
import sys
import threading
from typing import Dict, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QProgressBar, QTextEdit, QListWidget, QListWidgetItem,
        QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
        QTabWidget, QWidget, QCheckBox, QSpinBox, QMessageBox,
        QSplitter, QFrame
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt5.QtGui import QFont, QColor, QPalette
except ImportError:
    print("PyQt5 not available, GUI components will not work")
    # 创建空的基类以避免导入错误
    class QDialog: pass
    class QThread: pass
    class pyqtSignal: 
        def __init__(self, *args): pass
        def emit(self, *args): pass
        def connect(self, *args): pass

from core.database_diagnostics import (
    DatabaseHealthChecker, DatabaseMaintenanceManager,
    HealthCheckResult, HealthStatus, MaintenanceTask
)


class DiagnosticsWorkerThread(QThread):
    """诊断工作线程"""
    health_check_completed = pyqtSignal(object)  # HealthCheckResult
    maintenance_completed = pyqtSignal(dict)     # 维护结果
    error_occurred = pyqtSignal(str)             # 错误信息
    
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self.health_checker = DatabaseHealthChecker()
        self.maintenance_manager = DatabaseMaintenanceManager(db_path)
        self.operation = 'health_check'  # 'health_check', 'maintenance', 'auto_maintenance'
        self.task_id = None
    
    def set_operation(self, operation: str, task_id: str = None):
        """设置操作类型"""
        self.operation = operation
        self.task_id = task_id
    
    def run(self):
        """运行工作线程"""
        try:
            if self.operation == 'health_check':
                result = self.health_checker.perform_health_check(self.db_path)
                self.health_check_completed.emit(result)
            elif self.operation == 'maintenance':
                result = self.maintenance_manager.run_maintenance_task(self.task_id)
                self.maintenance_completed.emit(result)
            elif self.operation == 'auto_maintenance':
                result = self.maintenance_manager.run_auto_maintenance()
                self.maintenance_completed.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))


class DatabaseDiagnosticsDialog(QDialog):
    """数据库诊断和维护对话框"""
    
    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.health_checker = DatabaseHealthChecker()
        self.maintenance_manager = DatabaseMaintenanceManager(db_path)
        self.worker_thread = None
        self.current_health_result = None
        
        self.init_ui()
        self.setWindowTitle("数据库诊断和维护")
        self.setMinimumSize(900, 700)
        self.resize(1000, 800)
        
        # 自动执行初始健康检查
        QTimer.singleShot(500, self.start_health_check)
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        
        # 数据库信息
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"数据库: {os.path.basename(self.db_path)}"))
        info_layout.addStretch()
        
        self.refresh_button = QPushButton("刷新检查")
        self.refresh_button.clicked.connect(self.start_health_check)
        info_layout.addWidget(self.refresh_button)
        
        layout.addLayout(info_layout)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 健康检查标签页
        self.health_tab = self.create_health_tab()
        self.tab_widget.addTab(self.health_tab, "健康检查")
        
        # 维护任务标签页
        self.maintenance_tab = self.create_maintenance_tab()
        self.tab_widget.addTab(self.maintenance_tab, "维护任务")
        
        # 性能指标标签页
        self.metrics_tab = self.create_metrics_tab()
        self.tab_widget.addTab(self.metrics_tab, "性能指标")
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.auto_maintenance_button = QPushButton("自动维护")
        self.auto_maintenance_button.clicked.connect(self.start_auto_maintenance)
        button_layout.addWidget(self.auto_maintenance_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def create_health_tab(self) -> QWidget:
        """创建健康检查标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 总体健康状态
        status_group = QGroupBox("总体健康状态")
        status_layout = QVBoxLayout(status_group)
        
        self.overall_status_label = QLabel("状态: 检查中...")
        self.overall_status_label.setFont(QFont("Arial", 12, QFont.Bold))
        status_layout.addWidget(self.overall_status_label)
        
        self.health_score_label = QLabel("健康分数: --/100")
        status_layout.addWidget(self.health_score_label)
        
        self.checks_summary_label = QLabel("检查摘要: --")
        status_layout.addWidget(self.checks_summary_label)
        
        layout.addWidget(status_group)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 问题列表
        issues_group = QGroupBox("发现的问题")
        issues_layout = QVBoxLayout(issues_group)
        
        self.issues_list = QListWidget()
        issues_layout.addWidget(self.issues_list)
        
        splitter.addWidget(issues_group)
        
        # 建议列表
        recommendations_group = QGroupBox("改进建议")
        recommendations_layout = QVBoxLayout(recommendations_group)
        
        self.recommendations_list = QListWidget()
        recommendations_layout.addWidget(self.recommendations_list)
        
        splitter.addWidget(recommendations_group)
        
        return widget
    
    def create_maintenance_tab(self) -> QWidget:
        """创建维护任务标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 维护任务表格
        tasks_group = QGroupBox("维护任务")
        tasks_layout = QVBoxLayout(tasks_group)
        
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(7)
        self.tasks_table.setHorizontalHeaderLabels([
            "任务名称", "描述", "优先级", "预计时间", "上次运行", "启用", "自动运行"
        ])
        self.tasks_table.horizontalHeader().setStretchLastSection(True)
        tasks_layout.addWidget(self.tasks_table)
        
        # 任务操作按钮
        task_buttons_layout = QHBoxLayout()
        
        self.run_task_button = QPushButton("运行选中任务")
        self.run_task_button.clicked.connect(self.run_selected_task)
        task_buttons_layout.addWidget(self.run_task_button)
        
        task_buttons_layout.addStretch()
        
        self.update_tasks_button = QPushButton("更新任务设置")
        self.update_tasks_button.clicked.connect(self.update_task_settings)
        task_buttons_layout.addWidget(self.update_tasks_button)
        
        tasks_layout.addLayout(task_buttons_layout)
        layout.addWidget(tasks_group)
        
        # 维护日志
        log_group = QGroupBox("维护日志")
        log_layout = QVBoxLayout(log_group)
        
        self.maintenance_log = QTextEdit()
        self.maintenance_log.setReadOnly(True)
        self.maintenance_log.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.maintenance_log)
        
        layout.addWidget(log_group)
        
        # 加载维护任务
        self.load_maintenance_tasks()
        
        return widget
    
    def create_metrics_tab(self) -> QWidget:
        """创建性能指标标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 性能指标表格
        metrics_group = QGroupBox("性能指标")
        metrics_layout = QVBoxLayout(metrics_group)
        
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(3)
        self.metrics_table.setHorizontalHeaderLabels(["指标名称", "当前值", "状态"])
        self.metrics_table.horizontalHeader().setStretchLastSection(True)
        metrics_layout.addWidget(self.metrics_table)
        
        layout.addWidget(metrics_group)
        
        # 性能趋势（占位符）
        trend_group = QGroupBox("性能趋势")
        trend_layout = QVBoxLayout(trend_group)
        
        self.trend_label = QLabel("性能趋势图表将在此显示")
        self.trend_label.setAlignment(Qt.AlignCenter)
        self.trend_label.setStyleSheet("color: gray; font-style: italic;")
        trend_layout.addWidget(self.trend_label)
        
        layout.addWidget(trend_group)
        
        return widget
    
    def start_health_check(self):
        """开始健康检查"""
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("检查中...")
        
        # 清空之前的结果
        self.issues_list.clear()
        self.recommendations_list.clear()
        self.overall_status_label.setText("状态: 检查中...")
        
        # 创建工作线程
        self.worker_thread = DiagnosticsWorkerThread(self.db_path)
        self.worker_thread.set_operation('health_check')
        self.worker_thread.health_check_completed.connect(self.on_health_check_completed)
        self.worker_thread.error_occurred.connect(self.on_error_occurred)
        
        # 启动线程
        self.worker_thread.start()
    
    def start_auto_maintenance(self):
        """开始自动维护"""
        reply = QMessageBox.question(
            self, "确认自动维护",
            "确定要运行自动维护任务吗？这可能需要几分钟时间。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.auto_maintenance_button.setEnabled(False)
        self.auto_maintenance_button.setText("维护中...")
        
        # 创建工作线程
        self.worker_thread = DiagnosticsWorkerThread(self.db_path)
        self.worker_thread.set_operation('auto_maintenance')
        self.worker_thread.maintenance_completed.connect(self.on_maintenance_completed)
        self.worker_thread.error_occurred.connect(self.on_error_occurred)
        
        # 启动线程
        self.worker_thread.start()
        
        # 切换到维护标签页
        self.tab_widget.setCurrentIndex(1)
    
    def run_selected_task(self):
        """运行选中的维护任务"""
        current_row = self.tasks_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请先选择一个维护任务")
            return
        
        task_name = self.tasks_table.item(current_row, 0).text()
        
        # 获取任务ID（简化处理，使用任务名称的小写形式）
        task_id_map = {
            "数据库整理": "vacuum",
            "重建索引": "reindex",
            "统计信息更新": "analyze",
            "完整性检查": "integrity_check",
            "性能优化": "optimize"
        }
        
        task_id = task_id_map.get(task_name)
        if not task_id:
            QMessageBox.warning(self, "警告", f"未知的任务: {task_name}")
            return
        
        reply = QMessageBox.question(
            self, "确认运行任务",
            f"确定要运行 '{task_name}' 任务吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.run_task_button.setEnabled(False)
        self.run_task_button.setText("运行中...")
        
        # 创建工作线程
        self.worker_thread = DiagnosticsWorkerThread(self.db_path)
        self.worker_thread.set_operation('maintenance', task_id)
        self.worker_thread.maintenance_completed.connect(self.on_maintenance_completed)
        self.worker_thread.error_occurred.connect(self.on_error_occurred)
        
        # 启动线程
        self.worker_thread.start()
    
    def update_task_settings(self):
        """更新任务设置"""
        # 遍历表格，更新任务设置
        for row in range(self.tasks_table.rowCount()):
            task_name = self.tasks_table.item(row, 0).text()
            
            # 获取复选框状态
            enabled_item = self.tasks_table.cellWidget(row, 5)
            auto_run_item = self.tasks_table.cellWidget(row, 6)
            
            if isinstance(enabled_item, QCheckBox) and isinstance(auto_run_item, QCheckBox):
                enabled = enabled_item.isChecked()
                auto_run = auto_run_item.isChecked()
                
                # 获取任务ID
                task_id_map = {
                    "数据库整理": "vacuum",
                    "重建索引": "reindex",
                    "统计信息更新": "analyze",
                    "完整性检查": "integrity_check",
                    "性能优化": "optimize"
                }
                
                task_id = task_id_map.get(task_name)
                if task_id:
                    settings = {
                        'enabled': enabled,
                        'auto_run': auto_run
                    }
                    self.maintenance_manager.update_task_settings(task_id, settings)
        
        QMessageBox.information(self, "信息", "任务设置已更新")
    
    def load_maintenance_tasks(self):
        """加载维护任务"""
        schedule = self.maintenance_manager.get_maintenance_schedule()
        
        self.tasks_table.setRowCount(len(schedule))
        
        for i, task in enumerate(schedule):
            # 任务名称
            self.tasks_table.setItem(i, 0, QTableWidgetItem(task['name']))
            
            # 描述
            self.tasks_table.setItem(i, 1, QTableWidgetItem(task['description']))
            
            # 优先级
            self.tasks_table.setItem(i, 2, QTableWidgetItem(str(task['priority'])))
            
            # 预计时间
            duration_text = f"{task['estimated_duration']}秒"
            self.tasks_table.setItem(i, 3, QTableWidgetItem(duration_text))
            
            # 上次运行
            last_run = task['last_run'] or "从未运行"
            self.tasks_table.setItem(i, 4, QTableWidgetItem(last_run))
            
            # 启用复选框
            enabled_checkbox = QCheckBox()
            enabled_checkbox.setChecked(task['enabled'])
            self.tasks_table.setCellWidget(i, 5, enabled_checkbox)
            
            # 自动运行复选框
            auto_run_checkbox = QCheckBox()
            auto_run_checkbox.setChecked(task['auto_run'])
            self.tasks_table.setCellWidget(i, 6, auto_run_checkbox)
        
        # 调整列宽
        self.tasks_table.resizeColumnsToContents()
    
    def on_health_check_completed(self, result: HealthCheckResult):
        """健康检查完成处理"""
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("刷新检查")
        
        self.current_health_result = result
        
        # 更新总体状态
        status_text = {
            HealthStatus.EXCELLENT: "优秀",
            HealthStatus.GOOD: "良好",
            HealthStatus.WARNING: "警告",
            HealthStatus.CRITICAL: "严重",
            HealthStatus.FAILED: "失败"
        }.get(result.overall_status, "未知")
        
        self.overall_status_label.setText(f"状态: {status_text}")
        
        # 设置状态颜色
        if result.overall_status == HealthStatus.EXCELLENT:
            self.overall_status_label.setStyleSheet("color: green;")
        elif result.overall_status == HealthStatus.GOOD:
            self.overall_status_label.setStyleSheet("color: blue;")
        elif result.overall_status == HealthStatus.WARNING:
            self.overall_status_label.setStyleSheet("color: orange;")
        else:
            self.overall_status_label.setStyleSheet("color: red;")
        
        # 更新健康分数
        self.health_score_label.setText(f"健康分数: {result.score}/100")
        
        # 更新检查摘要
        self.checks_summary_label.setText(
            f"检查摘要: {result.checks_passed} 通过, {result.checks_failed} 失败"
        )
        
        # 更新问题列表
        self.issues_list.clear()
        for issue in result.issues:
            self.issues_list.addItem(issue)
        
        # 更新建议列表
        self.recommendations_list.clear()
        for recommendation in result.recommendations:
            self.recommendations_list.addItem(recommendation)
        
        # 更新性能指标
        self.update_performance_metrics(result.performance_metrics)
    
    def on_maintenance_completed(self, result: Dict[str, Any]):
        """维护完成处理"""
        self.auto_maintenance_button.setEnabled(True)
        self.auto_maintenance_button.setText("自动维护")
        self.run_task_button.setEnabled(True)
        self.run_task_button.setText("运行选中任务")
        
        # 添加到维护日志
        timestamp = result.get('timestamp', 'Unknown')
        if result['success']:
            if 'total_tasks' in result:  # 自动维护结果
                log_message = (
                    f"[{timestamp}] 自动维护完成\n"
                    f"  总任务数: {result['total_tasks']}\n"
                    f"  成功: {result['successful_tasks']}\n"
                    f"  失败: {result['failed_tasks']}\n"
                    f"  总耗时: {result.get('total_duration', 0):.2f}秒\n"
                )
            else:  # 单个任务结果
                task_name = result.get('task_name', 'Unknown')
                duration = result.get('duration', 0)
                log_message = f"[{timestamp}] {task_name} 执行成功，耗时: {duration:.2f}秒\n"
            
            self.maintenance_log.append(log_message)
            QMessageBox.information(self, "维护完成", "维护任务执行成功！")
        else:
            error_msg = result.get('error', '未知错误')
            log_message = f"[{timestamp}] 维护失败: {error_msg}\n"
            self.maintenance_log.append(log_message)
            QMessageBox.critical(self, "维护失败", f"维护任务执行失败:\n{error_msg}")
        
        # 刷新健康检查
        self.start_health_check()
    
    def on_error_occurred(self, error_msg: str):
        """错误处理"""
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("刷新检查")
        self.auto_maintenance_button.setEnabled(True)
        self.auto_maintenance_button.setText("自动维护")
        self.run_task_button.setEnabled(True)
        self.run_task_button.setText("运行选中任务")
        
        QMessageBox.critical(self, "错误", f"操作失败:\n{error_msg}")
    
    def update_performance_metrics(self, metrics: Dict[str, Any]):
        """更新性能指标"""
        if not metrics:
            return
        
        # 准备指标数据
        metric_items = []
        
        if 'database_size_mb' in metrics:
            size_mb = metrics['database_size_mb']
            status = "正常" if size_mb < 500 else "注意" if size_mb < 1000 else "警告"
            metric_items.append(("数据库大小", f"{size_mb:.2f} MB", status))
        
        if 'fragmentation_ratio' in metrics:
            frag_ratio = metrics['fragmentation_ratio']
            status = "优秀" if frag_ratio < 5 else "良好" if frag_ratio < 10 else "需要优化"
            metric_items.append(("碎片化比率", f"{frag_ratio:.2f}%", status))
        
        if 'average_query_time' in metrics:
            query_time = metrics['average_query_time']
            status = "优秀" if query_time < 0.01 else "良好" if query_time < 0.1 else "需要优化"
            metric_items.append(("平均查询时间", f"{query_time:.3f}秒", status))
        
        if 'connection_time' in metrics:
            conn_time = metrics['connection_time']
            status = "优秀" if conn_time < 0.1 else "良好" if conn_time < 0.5 else "需要优化"
            metric_items.append(("连接时间", f"{conn_time:.3f}秒", status))
        
        if 'free_space_mb' in metrics:
            free_space = metrics['free_space_mb']
            status = "充足" if free_space > 1000 else "注意" if free_space > 100 else "不足"
            metric_items.append(("可用磁盘空间", f"{free_space:.2f} MB", status))
        
        # 更新表格
        self.metrics_table.setRowCount(len(metric_items))
        
        for i, (name, value, status) in enumerate(metric_items):
            self.metrics_table.setItem(i, 0, QTableWidgetItem(name))
            self.metrics_table.setItem(i, 1, QTableWidgetItem(value))
            
            status_item = QTableWidgetItem(status)
            if status in ["优秀", "充足"]:
                status_item.setBackground(QColor(144, 238, 144))  # 浅绿色
            elif status in ["良好", "正常"]:
                status_item.setBackground(QColor(173, 216, 230))  # 浅蓝色
            elif status in ["注意"]:
                status_item.setBackground(QColor(255, 255, 224))  # 浅黄色
            else:
                status_item.setBackground(QColor(255, 182, 193))  # 浅红色
            
            self.metrics_table.setItem(i, 2, status_item)
        
        # 调整列宽
        self.metrics_table.resizeColumnsToContents()
    
    def closeEvent(self, event):
        """关闭事件处理"""
        if self.worker_thread and self.worker_thread.isRunning():
            reply = QMessageBox.question(
                self, "确认关闭",
                "诊断操作正在进行中，确定要关闭吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.worker_thread.terminate()
                self.worker_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """测试诊断对话框"""
    import sys
    from PyQt5.QtWidgets import QApplication
    import sqlite3
    
    app = QApplication(sys.argv)
    
    # 创建测试数据库
    test_db_path = "test_diagnostics_dialog.db"
    
    try:
        with sqlite3.connect(test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            cursor.execute("INSERT INTO test (name) VALUES ('test1'), ('test2')")
            conn.commit()
        
        # 显示对话框
        dialog = DatabaseDiagnosticsDialog(test_db_path)
        dialog.show()
        
        sys.exit(app.exec_())
        
    finally:
        # 清理测试文件
        if os.path.exists(test_db_path):
            os.remove(test_db_path)


if __name__ == "__main__":
    main()