#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库设置对话框使用示例
演示如何在应用程序中集成数据库设置功能
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenuBar, QAction, QMessageBox
from PyQt5.QtCore import Qt

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.database_settings_dialog import DatabaseSettingsDialog
from core.storage_utils import get_default_database_path


class ExampleMainWindow(QMainWindow):
    """示例主窗口"""
    
    def __init__(self):
        super().__init__()
        self.current_db_path = get_default_database_path()
        
        self.setWindowTitle("数据库设置示例应用")
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
        
        # 数据库设置
        settings_action = QAction('数据库设置...', self)
        settings_action.setShortcut('Ctrl+D')
        settings_action.setStatusTip('打开数据库设置对话框')
        settings_action.triggered.connect(self._open_database_settings)
        db_menu.addAction(settings_action)
        
        db_menu.addSeparator()
        
        # 数据库信息
        info_action = QAction('数据库信息', self)
        info_action.setStatusTip('显示当前数据库信息')
        info_action.triggered.connect(self._show_database_info)
        db_menu.addAction(info_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.statusBar().showMessage('就绪')
    
    def _open_database_settings(self):
        """打开数据库设置对话框"""
        dialog = DatabaseSettingsDialog(self.current_db_path, self)
        
        # 连接数据库路径改变信号
        dialog.database_changed.connect(self._on_database_changed)
        
        # 显示对话框
        result = dialog.exec_()
        
        if result == DatabaseSettingsDialog.Accepted:
            self.statusBar().showMessage('数据库设置已保存', 3000)
        else:
            self.statusBar().showMessage('数据库设置已取消', 3000)
    
    def _on_database_changed(self, new_path: str):
        """数据库路径改变处理"""
        old_path = self.current_db_path
        self.current_db_path = new_path
        
        # 更新状态栏
        self.statusBar().showMessage(f"数据库已切换: {os.path.basename(new_path)}")
        
        # 这里可以添加实际的数据库切换逻辑
        # 例如：重新加载数据、更新UI等
        print(f"数据库路径已从 {old_path} 切换到 {new_path}")
        
        # 显示确认消息
        QMessageBox.information(
            self,
            "数据库切换",
            f"数据库已成功切换到:\n{new_path}"
        )
    
    def _show_database_info(self):
        """显示数据库信息"""
        try:
            from core.database_manager import DatabaseManager
            
            db_manager = DatabaseManager(self.current_db_path)
            if db_manager.connect():
                db_info = db_manager.get_connection_info()
                
                info_text = f"""
数据库信息:

文件路径: {db_info.get('db_path', 'N/A')}
文件大小: {db_info.get('file_size', 0):,} 字节
数据库版本: {db_info.get('version', 'N/A')}
表数量: {db_info.get('table_count', 0)}
记录总数: {db_info.get('record_count', 0)}
连接状态: {'已连接' if db_info.get('is_connected') else '未连接'}
                """.strip()
                
                QMessageBox.information(self, "数据库信息", info_text)
                db_manager.disconnect()
            else:
                QMessageBox.warning(self, "错误", "无法连接到数据库")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取数据库信息失败:\n{str(e)}")
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            """
数据库设置示例应用

这是一个演示如何在PyQt5应用程序中
集成数据库设置功能的示例。

功能特性:
• 数据库路径配置
• 连接测试和状态显示
• 数据库信息查看
• 数据验证和修复
• 备份和恢复功能
• 性能优化工具

版本: 1.0
            """.strip()
        )


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("数据库设置示例")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("SwaggerAPITester")
    
    # 设置应用程序样式
    app.setStyle('Fusion')  # 使用现代样式
    
    # 创建主窗口
    window = ExampleMainWindow()
    window.show()
    
    # 显示欢迎消息
    window.statusBar().showMessage('欢迎使用数据库设置示例应用！按 Ctrl+D 打开数据库设置', 5000)
    
    # 运行应用程序
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())