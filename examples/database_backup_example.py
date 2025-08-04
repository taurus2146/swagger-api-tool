#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库备份和恢复对话框使用示例
演示如何在应用程序中集成数据库备份和恢复功能
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenuBar, QAction, QMessageBox, QStatusBar
from PyQt5.QtCore import Qt

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.database_backup_dialog import DatabaseBackupDialog
from core.storage_utils import get_default_database_path


class ExampleMainWindow(QMainWindow):
    """示例主窗口"""
    
    def __init__(self):
        super().__init__()
        self.current_db_path = get_default_database_path()
        
        self.setWindowTitle("数据库备份和恢复示例应用")
        self.setGeometry(200, 200, 800, 600)
        
        self._create_menu()
        self._create_status_bar()
        
        # 显示当前数据库路径
        self.statusBar().showMessage(f"当前数据库: {self.current_db_path}")
    
    def _create_menu(self):
        """创建菜单"""
        menubar = self.menuBar()
        
        # 数据库菜单
        db_menu = menubar.addMenu('数据库')
        
        # 备份和恢复
        backup_action = QAction('备份和恢复...', self)
        backup_action.setShortcut('Ctrl+B')
        backup_action.setStatusTip('打开数据库备份和恢复对话框')
        backup_action.triggered.connect(self._open_backup_dialog)
        db_menu.addAction(backup_action)
        
        db_menu.addSeparator()
        
        # 快速备份
        quick_backup_action = QAction('快速备份', self)
        quick_backup_action.setShortcut('Ctrl+Shift+B')
        quick_backup_action.setStatusTip('执行快速备份')
        quick_backup_action.triggered.connect(self._quick_backup)
        db_menu.addAction(quick_backup_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.statusBar().showMessage('就绪')
    
    def _open_backup_dialog(self):
        """打开数据库备份和恢复对话框"""
        if not os.path.exists(self.current_db_path):
            QMessageBox.warning(
                self,
                "数据库不存在",
                f"数据库文件不存在: {self.current_db_path}\n\n请先创建或选择一个有效的数据库文件。"
            )
            return
        
        dialog = DatabaseBackupDialog(self.current_db_path, self)
        
        # 显示对话框
        result = dialog.exec_()
        
        if result == DatabaseBackupDialog.Accepted:
            self.statusBar().showMessage('备份和恢复操作完成', 3000)
        else:
            self.statusBar().showMessage('备份和恢复对话框已关闭', 3000)
    
    def _quick_backup(self):
        """快速备份"""
        if not os.path.exists(self.current_db_path):
            QMessageBox.warning(self, "错误", "数据库文件不存在")
            return
        
        try:
            from core.database_manager import DatabaseManager
            from datetime import datetime
            import tempfile
            
            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"quick_backup_{timestamp}.db"
            
            # 使用临时目录作为备份位置（实际应用中应该让用户选择）
            backup_path = os.path.join(tempfile.gettempdir(), backup_name)
            
            # 执行备份
            db_manager = DatabaseManager(self.current_db_path)
            if db_manager.connect():
                if db_manager.backup_database(backup_path):
                    QMessageBox.information(
                        self,
                        "快速备份成功",
                        f"数据库已成功备份到:\n{backup_path}"
                    )
                    self.statusBar().showMessage(f'快速备份完成: {backup_name}', 5000)
                else:
                    QMessageBox.warning(self, "备份失败", "快速备份操作失败")
                
                db_manager.disconnect()
            else:
                QMessageBox.warning(self, "错误", "无法连接到数据库")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"快速备份失败:\n{str(e)}")
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            """
数据库备份和恢复示例应用

这是一个演示如何在PyQt5应用程序中
集成数据库备份和恢复功能的示例。

功能特性:
• 完整的备份和恢复界面
• 自动备份计划设置
• 备份文件管理和验证
• 进度显示和状态反馈
• 快速备份功能
• 备份历史记录

版本: 1.0
            """.strip()
        )


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("数据库备份和恢复示例")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("SwaggerAPITester")
    
    # 设置应用程序样式
    app.setStyle('Fusion')  # 使用现代样式
    
    # 创建主窗口
    window = ExampleMainWindow()
    window.show()
    
    # 显示欢迎消息
    window.statusBar().showMessage('欢迎使用数据库备份和恢复示例应用！按 Ctrl+B 打开备份对话框', 5000)
    
    # 运行应用程序
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())