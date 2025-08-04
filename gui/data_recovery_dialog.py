#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据恢复向导对话框
提供用户友好的数据库恢复界面
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
        QGroupBox, QRadioButton, QButtonGroup, QMessageBox,
        QFileDialog, QTabWidget, QWidget, QTableWidget,
        QTableWidgetItem, QHeaderView, QSplitter
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt5.QtGui import QFont, QIcon, QPixmap
except ImportError:
    print("PyQt5 not available, GUI components will not work")
    # 创建空的基类以避免导入错误
    class QDialog: pass
    class QThread: pass
    class pyqtSignal: 
        def __init__(self, *args): pass
        def emit(self, *args): pass
        def connect(self, *args): pass

from core.data_recovery import (
    DataRecoveryWizard, DatabaseCorruptionDetector,
    RecoveryProgress, RecoveryStatus, CorruptionReport,
    CorruptionLevel
)


class RecoveryWorkerThread(QThread):
    """恢复工作线程"""
    progress_updated = pyqtSignal(object)  # RecoveryProgress
    wizard_completed = pyqtSignal(dict)    # 向导完成结果
    recovery_completed = pyqtSignal(dict)  # 恢复完成结果
    error_occurred = pyqtSignal(str)       # 错误信息
    
    def __init__(self, wizard: DataRecoveryWizard, db_path: str):
        super().__init__()
        self.wizard = wizard
        self.db_path = db_path
        self.recovery_plan = None
        self.operation = 'wizard'  # 'wizard' or 'recovery'
        
        # 设置进度回调
        self.wizard.set_progress_callback(self.on_progress_update)
    
    def set_recovery_plan(self, recovery_plan: Dict[str, Any]):
        """设置恢复计划"""
        self.recovery_plan = recovery_plan
        self.operation = 'recovery'
    
    def on_progress_update(self, progress: RecoveryProgress):
        """进度更新回调"""
        self.progress_updated.emit(progress)
    
    def run(self):
        """运行工作线程"""
        try:
            if self.operation == 'wizard':
                # 运行恢复向导
                result = self.wizard.start_recovery_wizard(self.db_path)
                self.wizard_completed.emit(result)
            elif self.operation == 'recovery':
                # 执行恢复计划
                result = self.wizard.execute_recovery_plan(self.db_path, self.recovery_plan)
                self.recovery_completed.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))


class DataRecoveryDialog(QDialog):
    """数据恢复向导对话框"""
    
    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.wizard = DataRecoveryWizard()
        self.worker_thread = None
        self.corruption_report = None
        self.recovery_options = []
        self.available_backups = []
        self.recovery_plan = None
        
        self.init_ui()
        self.setWindowTitle("数据库恢复向导")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 检测标签页
        self.detection_tab = self.create_detection_tab()
        self.tab_widget.addTab(self.detection_tab, "损坏检测")
        
        # 恢复选项标签页
        self.options_tab = self.create_options_tab()
        self.tab_widget.addTab(self.options_tab, "恢复选项")
        
        # 恢复进度标签页
        self.progress_tab = self.create_progress_tab()
        self.tab_widget.addTab(self.progress_tab, "恢复进度")
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("开始检测")
        self.start_button.clicked.connect(self.start_detection)
        button_layout.addWidget(self.start_button)
        
        self.recover_button = QPushButton("开始恢复")
        self.recover_button.clicked.connect(self.start_recovery)
        self.recover_button.setEnabled(False)
        button_layout.addWidget(self.recover_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        # 初始状态
        self.tab_widget.setTabEnabled(1, False)  # 恢复选项
        self.tab_widget.setTabEnabled(2, False)  # 恢复进度
    
    def create_detection_tab(self) -> QWidget:
        """创建检测标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 数据库信息
        info_group = QGroupBox("数据库信息")
        info_layout = QVBoxLayout(info_group)
        
        self.db_path_label = QLabel(f"数据库路径: {self.db_path}")
        info_layout.addWidget(self.db_path_label)
        
        self.db_size_label = QLabel("数据库大小: 未知")
        info_layout.addWidget(self.db_size_label)
        
        layout.addWidget(info_group)
        
        # 检测结果
        result_group = QGroupBox("检测结果")
        result_layout = QVBoxLayout(result_group)
        
        self.corruption_level_label = QLabel("损坏程度: 未检测")
        self.corruption_level_label.setFont(QFont("Arial", 10, QFont.Bold))
        result_layout.addWidget(self.corruption_level_label)
        
        self.corruption_summary_label = QLabel("检测摘要: 等待检测...")
        result_layout.addWidget(self.corruption_summary_label)
        
        # 问题列表
        self.issues_list = QListWidget()
        result_layout.addWidget(QLabel("发现的问题:"))
        result_layout.addWidget(self.issues_list)
        
        # 建议列表
        self.recommendations_list = QListWidget()
        result_layout.addWidget(QLabel("恢复建议:"))
        result_layout.addWidget(self.recommendations_list)
        
        layout.addWidget(result_group)
        
        # 更新数据库信息
        self.update_database_info()
        
        return widget
    
    def create_options_tab(self) -> QWidget:
        """创建恢复选项标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 恢复选项
        options_group = QGroupBox("恢复选项")
        options_layout = QVBoxLayout(options_group)
        
        self.option_button_group = QButtonGroup()
        self.option_buttons = []
        
        # 选项将在检测完成后动态添加
        self.options_container = QWidget()
        self.options_container_layout = QVBoxLayout(self.options_container)
        options_layout.addWidget(self.options_container)
        
        layout.addWidget(options_group)
        
        # 备份信息
        backup_group = QGroupBox("可用备份")
        backup_layout = QVBoxLayout(backup_group)
        
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(4)
        self.backup_table.setHorizontalHeaderLabels(["文件名", "大小", "创建时间", "修改时间"])
        self.backup_table.horizontalHeader().setStretchLastSection(True)
        backup_layout.addWidget(self.backup_table)
        
        layout.addWidget(backup_group)
        
        return widget
    
    def create_progress_tab(self) -> QWidget:
        """创建恢复进度标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 进度信息
        progress_group = QGroupBox("恢复进度")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.current_step_label = QLabel("当前步骤: 等待开始")
        progress_layout.addWidget(self.current_step_label)
        
        self.progress_details_label = QLabel("进度详情: 0/0 (0%)")
        progress_layout.addWidget(self.progress_details_label)
        
        self.estimated_time_label = QLabel("预计剩余时间: 未知")
        progress_layout.addWidget(self.estimated_time_label)
        
        layout.addWidget(progress_group)
        
        # 日志输出
        log_group = QGroupBox("恢复日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        return widget
    
    def update_database_info(self):
        """更新数据库信息"""
        try:
            if os.path.exists(self.db_path):
                size = os.path.getsize(self.db_path)
                size_mb = size / (1024 * 1024)
                self.db_size_label.setText(f"数据库大小: {size_mb:.2f} MB")
            else:
                self.db_size_label.setText("数据库大小: 文件不存在")
        except Exception as e:
            self.db_size_label.setText(f"数据库大小: 获取失败 ({e})")
    
    def start_detection(self):
        """开始损坏检测"""
        self.start_button.setEnabled(False)
        self.start_button.setText("检测中...")
        
        # 清空之前的结果
        self.issues_list.clear()
        self.recommendations_list.clear()
        
        # 创建工作线程
        self.worker_thread = RecoveryWorkerThread(self.wizard, self.db_path)
        self.worker_thread.progress_updated.connect(self.on_progress_updated)
        self.worker_thread.wizard_completed.connect(self.on_wizard_completed)
        self.worker_thread.error_occurred.connect(self.on_error_occurred)
        
        # 启动线程
        self.worker_thread.start()
        
        # 切换到进度标签页
        self.tab_widget.setCurrentIndex(2)
        self.tab_widget.setTabEnabled(2, True)
    
    def start_recovery(self):
        """开始数据恢复"""
        if not self.recovery_plan:
            QMessageBox.warning(self, "警告", "请先选择恢复选项")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认恢复", 
            f"确定要执行 '{self.recovery_plan['strategy']}' 恢复策略吗？\n\n"
            f"预计时间: {self.recovery_plan['estimated_time']} 秒\n"
            f"风险级别: {self.recovery_plan['risk_level']}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.recover_button.setEnabled(False)
        self.recover_button.setText("恢复中...")
        
        # 创建工作线程
        self.worker_thread = RecoveryWorkerThread(self.wizard, self.db_path)
        self.worker_thread.set_recovery_plan(self.recovery_plan)
        self.worker_thread.progress_updated.connect(self.on_progress_updated)
        self.worker_thread.recovery_completed.connect(self.on_recovery_completed)
        self.worker_thread.error_occurred.connect(self.on_error_occurred)
        
        # 启动线程
        self.worker_thread.start()
        
        # 切换到进度标签页
        self.tab_widget.setCurrentIndex(2)
    
    def on_progress_updated(self, progress: RecoveryProgress):
        """进度更新处理"""
        self.progress_bar.setValue(int(progress.progress_percentage))
        self.current_step_label.setText(f"当前步骤: {progress.current_step}")
        self.progress_details_label.setText(
            f"进度详情: {progress.completed_steps}/{progress.total_steps} "
            f"({progress.progress_percentage:.1f}%)"
        )
        
        if progress.estimated_time_remaining:
            self.estimated_time_label.setText(
                f"预计剩余时间: {progress.estimated_time_remaining:.0f} 秒"
            )
        
        # 添加到日志
        self.log_text.append(f"[{progress.status.value}] {progress.current_step}")
        
        if progress.error_message:
            self.log_text.append(f"错误: {progress.error_message}")
    
    def on_wizard_completed(self, result: Dict[str, Any]):
        """向导完成处理"""
        self.start_button.setEnabled(True)
        self.start_button.setText("重新检测")
        
        if result['success']:
            self.corruption_report = result['corruption_report']
            self.recovery_options = result['recovery_options']
            self.available_backups = result['available_backups']
            self.recovery_plan = result['recovery_plan']
            
            # 更新检测结果
            self.update_detection_results()
            
            # 更新恢复选项
            self.update_recovery_options()
            
            # 更新备份信息
            self.update_backup_info()
            
            # 启用相关标签页
            self.tab_widget.setTabEnabled(1, True)
            self.recover_button.setEnabled(True)
            
            # 切换到检测结果标签页
            self.tab_widget.setCurrentIndex(0)
            
            self.log_text.append("检测完成，请查看检测结果和恢复选项")
        else:
            error_msg = result.get('error', '未知错误')
            self.log_text.append(f"检测失败: {error_msg}")
            QMessageBox.critical(self, "检测失败", f"数据库检测失败:\n{error_msg}")
    
    def on_recovery_completed(self, result: Dict[str, Any]):
        """恢复完成处理"""
        self.recover_button.setEnabled(True)
        self.recover_button.setText("开始恢复")
        
        if result['success']:
            strategy = result['strategy']
            self.log_text.append(f"恢复完成，使用策略: {strategy}")
            
            success_msg = "数据库恢复成功！\n\n"
            if strategy == 'backup_restore':
                backup_used = result.get('backup_used', '未知')
                success_msg += f"使用的备份: {backup_used}"
            elif strategy == 'partial_recovery':
                recovered_tables = result.get('recovered_tables', [])
                success_msg += f"恢复的表: {', '.join(recovered_tables)}"
            
            QMessageBox.information(self, "恢复成功", success_msg)
        else:
            error_msg = result.get('error', '未知错误')
            self.log_text.append(f"恢复失败: {error_msg}")
            QMessageBox.critical(self, "恢复失败", f"数据库恢复失败:\n{error_msg}")
    
    def on_error_occurred(self, error_msg: str):
        """错误处理"""
        self.start_button.setEnabled(True)
        self.start_button.setText("开始检测")
        self.recover_button.setEnabled(True)
        self.recover_button.setText("开始恢复")
        
        self.log_text.append(f"发生错误: {error_msg}")
        QMessageBox.critical(self, "错误", f"操作失败:\n{error_msg}")
    
    def update_detection_results(self):
        """更新检测结果"""
        if not self.corruption_report:
            return
        
        # 更新损坏程度
        level = self.corruption_report.corruption_level
        level_text = {
            CorruptionLevel.NONE: "无损坏",
            CorruptionLevel.MINOR: "轻微损坏",
            CorruptionLevel.MODERATE: "中等损坏",
            CorruptionLevel.SEVERE: "严重损坏",
            CorruptionLevel.TOTAL: "完全损坏"
        }.get(level, "未知")
        
        self.corruption_level_label.setText(f"损坏程度: {level_text}")
        
        # 设置颜色
        if level == CorruptionLevel.NONE:
            self.corruption_level_label.setStyleSheet("color: green;")
        elif level in [CorruptionLevel.MINOR, CorruptionLevel.MODERATE]:
            self.corruption_level_label.setStyleSheet("color: orange;")
        else:
            self.corruption_level_label.setStyleSheet("color: red;")
        
        # 更新摘要
        summary = (
            f"总记录数: {self.corruption_report.total_records}, "
            f"可恢复记录: {self.corruption_report.recoverable_records}, "
            f"损坏表数: {len(self.corruption_report.corrupted_tables)}"
        )
        self.corruption_summary_label.setText(f"检测摘要: {summary}")
        
        # 更新问题列表
        self.issues_list.clear()
        for issue in self.corruption_report.issues_found:
            self.issues_list.addItem(issue)
        
        # 更新建议列表
        self.recommendations_list.clear()
        for recommendation in self.corruption_report.recommendations:
            self.recommendations_list.addItem(recommendation)
    
    def update_recovery_options(self):
        """更新恢复选项"""
        # 清空现有选项
        for button in self.option_buttons:
            button.setParent(None)
        self.option_buttons.clear()
        
        # 添加新选项
        for i, option in enumerate(self.recovery_options):
            radio_button = QRadioButton()
            radio_button.setText(
                f"{option['name']} - {option['description']}\n"
                f"风险: {option['risk']}, 预计时间: {option['estimated_time']}秒"
            )
            radio_button.setProperty('option_data', option)
            
            if i == 0:  # 默认选择第一个选项
                radio_button.setChecked(True)
            
            self.option_button_group.addButton(radio_button, i)
            self.option_buttons.append(radio_button)
            self.options_container_layout.addWidget(radio_button)
        
        # 连接信号
        self.option_button_group.buttonClicked.connect(self.on_option_selected)
        
        # 默认选择第一个选项
        if self.option_buttons:
            self.on_option_selected(self.option_buttons[0])
    
    def update_backup_info(self):
        """更新备份信息"""
        self.backup_table.setRowCount(len(self.available_backups))
        
        for i, backup in enumerate(self.available_backups):
            self.backup_table.setItem(i, 0, QTableWidgetItem(backup['filename']))
            
            size_mb = backup['size'] / (1024 * 1024)
            self.backup_table.setItem(i, 1, QTableWidgetItem(f"{size_mb:.2f} MB"))
            
            self.backup_table.setItem(i, 2, QTableWidgetItem(backup['created_time']))
            self.backup_table.setItem(i, 3, QTableWidgetItem(backup['modified_time']))
    
    def on_option_selected(self, button):
        """恢复选项选择处理"""
        option_data = button.property('option_data')
        if option_data and self.recovery_plan:
            # 更新恢复计划
            self.recovery_plan['strategy'] = option_data['type']
            self.recovery_plan['estimated_time'] = option_data['estimated_time']
            self.recovery_plan['risk_level'] = option_data['risk']
    
    def closeEvent(self, event):
        """关闭事件处理"""
        if self.worker_thread and self.worker_thread.isRunning():
            reply = QMessageBox.question(
                self, "确认关闭", 
                "恢复操作正在进行中，确定要关闭吗？",
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
    """测试数据恢复对话框"""
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建测试数据库
    test_db_path = "test_recovery_dialog.db"
    
    try:
        import sqlite3
        with sqlite3.connect(test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            cursor.execute("INSERT INTO test (name) VALUES ('test1'), ('test2')")
            conn.commit()
        
        # 显示对话框
        dialog = DataRecoveryDialog(test_db_path)
        dialog.show()
        
        sys.exit(app.exec_())
        
    finally:
        # 清理测试文件
        if os.path.exists(test_db_path):
            os.remove(test_db_path)


if __name__ == "__main__":
    main()