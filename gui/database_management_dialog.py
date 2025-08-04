#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库管理工具对话框
提供数据库重命名、删除、清理、导入导出、统计分析等功能的GUI界面
"""

import os
import logging
from typing import Optional
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QPushButton, QLabel, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QProgressBar, QGroupBox, QFormLayout,
    QCheckBox, QSpinBox, QComboBox, QHeaderView, QSplitter, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon

from core.database_config_manager import DatabaseConfigManager, DatabaseConfig
from core.database_management_tools import DatabaseManagementTools, DatabaseAnalysisResult
from core.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class DatabaseAnalysisThread(QThread):
    """数据库分析线程"""
    
    analysis_completed = pyqtSignal(str, object)  # config_id, analysis_result
    analysis_failed = pyqtSignal(str, str)  # config_id, error_message
    
    def __init__(self, management_tools: DatabaseManagementTools, config_id: str):
        super().__init__()
        self.management_tools = management_tools
        self.config_id = config_id
    
    def run(self):
        try:
            result = self.management_tools.analyze_database(self.config_id)
            if result:
                self.analysis_completed.emit(self.config_id, result)
            else:
                self.analysis_failed.emit(self.config_id, "分析失败")
        except Exception as e:
            self.analysis_failed.emit(self.config_id, str(e))


class DatabaseManagementDialog(QDialog):
    """数据库管理工具对话框"""
    
    def __init__(self, config_manager: DatabaseConfigManager,
                 database_manager: DatabaseManager = None, parent=None):
        """
        初始化对话框
        
        Args:
            config_manager: 数据库配置管理器
            database_manager: 数据库管理器
            parent: 父窗口
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.database_manager = database_manager
        self.management_tools = DatabaseManagementTools(config_manager, database_manager)
        
        self.setWindowTitle("数据库管理工具")
        self.setModal(True)
        self.resize(900, 700)
        
        # 初始化UI
        self._init_ui()
        
        # 加载数据
        self._load_data()
    
    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 重命名和删除标签页
        self._create_rename_delete_tab()
        
        # 导入导出标签页
        self._create_import_export_tab()
        
        # 分析和统计标签页
        self._create_analysis_tab()
        
        # 优化和维护标签页
        self._create_optimization_tab()
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self._load_data)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_rename_delete_tab(self):
        """创建重命名和删除标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 重命名组
        rename_group = QGroupBox("重命名数据库")
        rename_layout = QFormLayout(rename_group)
        
        self.rename_config_combo = QComboBox()
        rename_layout.addRow("选择数据库:", self.rename_config_combo)
        
        self.new_name_edit = QLineEdit()
        rename_layout.addRow("新名称:", self.new_name_edit)
        
        self.new_description_edit = QLineEdit()
        rename_layout.addRow("新描述:", self.new_description_edit)
        
        rename_btn_layout = QHBoxLayout()
        self.rename_config_btn = QPushButton("重命名配置")
        self.rename_config_btn.clicked.connect(self._rename_config)
        rename_btn_layout.addWidget(self.rename_config_btn)
        
        self.rename_file_btn = QPushButton("重命名文件")
        self.rename_file_btn.clicked.connect(self._rename_file)
        rename_btn_layout.addWidget(self.rename_file_btn)
        
        rename_btn_layout.addStretch()
        rename_layout.addRow(rename_btn_layout)
        
        layout.addWidget(rename_group)
        
        # 删除组
        delete_group = QGroupBox("删除数据库")
        delete_layout = QFormLayout(delete_group)
        
        self.delete_config_combo = QComboBox()
        delete_layout.addRow("选择数据库:", self.delete_config_combo)
        
        self.delete_file_checkbox = QCheckBox("同时删除数据库文件")
        delete_layout.addRow(self.delete_file_checkbox)
        
        delete_btn_layout = QHBoxLayout()
        self.delete_config_btn = QPushButton("删除配置")
        self.delete_config_btn.setStyleSheet("QPushButton { color: #f44336; }")
        self.delete_config_btn.clicked.connect(self._delete_config)
        delete_btn_layout.addWidget(self.delete_config_btn)
        
        delete_btn_layout.addStretch()
        delete_layout.addRow(delete_btn_layout)
        
        layout.addWidget(delete_group)
        
        # 清理组
        cleanup_group = QGroupBox("清理工具")
        cleanup_layout = QVBoxLayout(cleanup_group)
        
        cleanup_info = QLabel("清理缺失文件的数据库配置")
        cleanup_layout.addWidget(cleanup_info)
        
        cleanup_btn_layout = QHBoxLayout()
        self.cleanup_btn = QPushButton("清理缺失配置")
        self.cleanup_btn.clicked.connect(self._cleanup_missing)
        cleanup_btn_layout.addWidget(self.cleanup_btn)
        
        cleanup_btn_layout.addStretch()
        cleanup_layout.addLayout(cleanup_btn_layout)
        
        layout.addWidget(cleanup_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "重命名和删除")
    
    def _create_import_export_tab(self):
        """创建导入导出标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 导出组
        export_group = QGroupBox("导出数据库")
        export_layout = QFormLayout(export_group)
        
        self.export_config_combo = QComboBox()
        export_layout.addRow("选择数据库:", self.export_config_combo)
        
        self.export_data_checkbox = QCheckBox("包含数据")
        self.export_data_checkbox.setChecked(True)
        export_layout.addRow(self.export_data_checkbox)
        
        export_btn_layout = QHBoxLayout()
        self.export_btn = QPushButton("导出")
        self.export_btn.clicked.connect(self._export_database)
        export_btn_layout.addWidget(self.export_btn)
        
        export_btn_layout.addStretch()
        export_layout.addRow(export_btn_layout)
        
        layout.addWidget(export_group)
        
        # 导入组
        import_group = QGroupBox("导入数据库")
        import_layout = QFormLayout(import_group)
        
        self.import_data_checkbox = QCheckBox("导入数据")
        self.import_data_checkbox.setChecked(True)
        import_layout.addRow(self.import_data_checkbox)
        
        import_btn_layout = QHBoxLayout()
        self.import_btn = QPushButton("选择文件导入")
        self.import_btn.clicked.connect(self._import_database)
        import_btn_layout.addWidget(self.import_btn)
        
        import_btn_layout.addStretch()
        import_layout.addRow(import_btn_layout)
        
        layout.addWidget(import_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "导入导出")
    
    def _create_analysis_tab(self):
        """创建分析和统计标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧：数据库选择和分析
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 分析组
        analysis_group = QGroupBox("数据库分析")
        analysis_layout = QFormLayout(analysis_group)
        
        self.analysis_config_combo = QComboBox()
        analysis_layout.addRow("选择数据库:", self.analysis_config_combo)
        
        analysis_btn_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("分析")
        self.analyze_btn.clicked.connect(self._analyze_database)
        analysis_btn_layout.addWidget(self.analyze_btn)
        
        self.analyze_all_btn = QPushButton("分析所有")
        self.analyze_all_btn.clicked.connect(self._analyze_all_databases)
        analysis_btn_layout.addWidget(self.analyze_all_btn)
        
        analysis_btn_layout.addStretch()
        analysis_layout.addRow(analysis_btn_layout)
        
        left_layout.addWidget(analysis_group)
        
        # 统计信息组
        stats_group = QGroupBox("统计信息")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(200)
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)
        
        self.refresh_stats_btn = QPushButton("刷新统计")
        self.refresh_stats_btn.clicked.connect(self._refresh_statistics)
        stats_layout.addWidget(self.refresh_stats_btn)
        
        left_layout.addWidget(stats_group)
        
        splitter.addWidget(left_widget)
        
        # 右侧：分析结果
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        result_group = QGroupBox("分析结果")
        result_layout = QVBoxLayout(result_group)
        
        self.analysis_result_text = QTextEdit()
        self.analysis_result_text.setReadOnly(True)
        result_layout.addWidget(self.analysis_result_text)
        
        right_layout.addWidget(result_group)
        
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([400, 500])
        
        self.tab_widget.addTab(tab, "分析统计")
    
    def _create_optimization_tab(self):
        """创建优化和维护标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 优化组
        optimize_group = QGroupBox("数据库优化")
        optimize_layout = QFormLayout(optimize_group)
        
        self.optimize_config_combo = QComboBox()
        optimize_layout.addRow("选择数据库:", self.optimize_config_combo)
        
        optimize_btn_layout = QHBoxLayout()
        
        self.vacuum_btn = QPushButton("压缩数据库")
        self.vacuum_btn.clicked.connect(self._vacuum_database)
        optimize_btn_layout.addWidget(self.vacuum_btn)
        
        self.optimize_btn = QPushButton("全面优化")
        self.optimize_btn.clicked.connect(self._optimize_database)
        optimize_btn_layout.addWidget(self.optimize_btn)
        
        optimize_btn_layout.addStretch()
        optimize_layout.addRow(optimize_btn_layout)
        
        layout.addWidget(optimize_group)
        
        # 修复组
        repair_group = QGroupBox("数据库修复")
        repair_layout = QFormLayout(repair_group)
        
        self.repair_config_combo = QComboBox()
        repair_layout.addRow("选择数据库:", self.repair_config_combo)
        
        repair_btn_layout = QHBoxLayout()
        self.repair_btn = QPushButton("修复数据库")
        self.repair_btn.clicked.connect(self._repair_database)
        repair_btn_layout.addWidget(self.repair_btn)
        
        repair_btn_layout.addStretch()
        repair_layout.addRow(repair_btn_layout)
        
        layout.addWidget(repair_group)
        
        # 操作结果
        result_group = QGroupBox("操作结果")
        result_layout = QVBoxLayout(result_group)
        
        self.operation_result_text = QTextEdit()
        self.operation_result_text.setMaximumHeight(200)
        self.operation_result_text.setReadOnly(True)
        result_layout.addWidget(self.operation_result_text)
        
        layout.addWidget(result_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "优化维护")
    
    def _load_data(self):
        """加载数据"""
        try:
            configs = self.config_manager.get_all_configs()
            
            # 清空所有下拉框
            combos = [
                self.rename_config_combo,
                self.delete_config_combo,
                self.export_config_combo,
                self.analysis_config_combo,
                self.optimize_config_combo,
                self.repair_config_combo
            ]
            
            for combo in combos:
                combo.clear()
            
            # 添加配置到下拉框
            for config in configs:
                display_text = f"{config.name} ({config.path})"
                for combo in combos:
                    combo.addItem(display_text, config.id)
            
            # 刷新统计信息
            self._refresh_statistics()
            
            logger.info(f"加载了 {len(configs)} 个数据库配置")
            
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            QMessageBox.critical(self, "错误", f"加载数据失败:\n{str(e)}")
    
    def _rename_config(self):
        """重命名配置"""
        try:
            config_id = self.rename_config_combo.currentData()
            new_name = self.new_name_edit.text().strip()
            new_description = self.new_description_edit.text().strip()
            
            if not config_id:
                QMessageBox.warning(self, "警告", "请选择要重命名的数据库")
                return
            
            if not new_name:
                QMessageBox.warning(self, "警告", "请输入新名称")
                return
            
            success = self.management_tools.rename_database_config(
                config_id, new_name, new_description or None
            )
            
            if success:
                QMessageBox.information(self, "成功", "数据库配置重命名成功")
                self.new_name_edit.clear()
                self.new_description_edit.clear()
                self._load_data()
            else:
                QMessageBox.warning(self, "失败", "数据库配置重命名失败")
        
        except Exception as e:
            logger.error(f"重命名配置失败: {e}")
            QMessageBox.critical(self, "错误", f"重命名配置失败:\n{str(e)}")
    
    def _rename_file(self):
        """重命名文件"""
        try:
            config_id = self.rename_config_combo.currentData()
            
            if not config_id:
                QMessageBox.warning(self, "警告", "请选择要重命名的数据库")
                return
            
            config = self.config_manager.get_config(config_id)
            if not config:
                QMessageBox.warning(self, "警告", "配置不存在")
                return
            
            current_filename = os.path.basename(config.path)
            new_filename, ok = QFileDialog.getSaveFileName(
                self, "选择新文件名", 
                os.path.join(os.path.dirname(config.path), current_filename),
                "数据库文件 (*.db);;所有文件 (*)"
            )
            
            if ok and new_filename:
                new_filename = os.path.basename(new_filename)
                success = self.management_tools.rename_database_file(config_id, new_filename)
                
                if success:
                    QMessageBox.information(self, "成功", "数据库文件重命名成功")
                    self._load_data()
                else:
                    QMessageBox.warning(self, "失败", "数据库文件重命名失败")
        
        except Exception as e:
            logger.error(f"重命名文件失败: {e}")
            QMessageBox.critical(self, "错误", f"重命名文件失败:\n{str(e)}")
    
    def _delete_config(self):
        """删除配置"""
        try:
            config_id = self.delete_config_combo.currentData()
            delete_file = self.delete_file_checkbox.isChecked()
            
            if not config_id:
                QMessageBox.warning(self, "警告", "请选择要删除的数据库")
                return
            
            config = self.config_manager.get_config(config_id)
            if not config:
                QMessageBox.warning(self, "警告", "配置不存在")
                return
            
            # 确认删除
            message = f"确定要删除数据库配置 '{config.name}' 吗?"
            if delete_file:
                message += "\n\n注意：这将同时删除数据库文件，操作不可恢复！"
            else:
                message += "\n\n注意：这只会删除配置信息，不会删除数据库文件。"
            
            reply = QMessageBox.question(
                self, "确认删除", message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                success = self.management_tools.delete_database_config(config_id, delete_file)
                
                if success:
                    QMessageBox.information(self, "成功", "数据库配置删除成功")
                    self._load_data()
                else:
                    QMessageBox.warning(self, "失败", "数据库配置删除失败")
        
        except Exception as e:
            logger.error(f"删除配置失败: {e}")
            QMessageBox.critical(self, "错误", f"删除配置失败:\n{str(e)}")
    
    def _cleanup_missing(self):
        """清理缺失配置"""
        try:
            reply = QMessageBox.question(
                self, "确认清理",
                "确定要清理所有缺失文件的数据库配置吗?\n\n这将删除文件不存在的配置记录。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                cleaned_count = self.management_tools.cleanup_missing_configs()
                
                QMessageBox.information(
                    self, "清理完成", 
                    f"已清理 {cleaned_count} 个缺失文件的配置"
                )
                self._load_data()
        
        except Exception as e:
            logger.error(f"清理缺失配置失败: {e}")
            QMessageBox.critical(self, "错误", f"清理缺失配置失败:\n{str(e)}")
    
    def _export_database(self):
        """导出数据库"""
        try:
            config_id = self.export_config_combo.currentData()
            include_data = self.export_data_checkbox.isChecked()
            
            if not config_id:
                QMessageBox.warning(self, "警告", "请选择要导出的数据库")
                return
            
            config = self.config_manager.get_config(config_id)
            if not config:
                QMessageBox.warning(self, "警告", "配置不存在")
                return
            
            # 选择导出路径
            default_filename = f"{config.name}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            export_path, ok = QFileDialog.getSaveFileName(
                self, "选择导出路径", default_filename,
                "JSON文件 (*.json);;所有文件 (*)"
            )
            
            if ok and export_path:
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)  # 不确定进度
                
                try:
                    success = self.management_tools.export_database_config(
                        config_id, export_path, include_data
                    )
                    
                    if success:
                        QMessageBox.information(self, "成功", f"数据库导出成功:\n{export_path}")
                    else:
                        QMessageBox.warning(self, "失败", "数据库导出失败")
                
                finally:
                    self.progress_bar.setVisible(False)
        
        except Exception as e:
            logger.error(f"导出数据库失败: {e}")
            QMessageBox.critical(self, "错误", f"导出数据库失败:\n{str(e)}")
            self.progress_bar.setVisible(False)
    
    def _import_database(self):
        """导入数据库"""
        try:
            import_data = self.import_data_checkbox.isChecked()
            
            # 选择导入文件
            import_path, ok = QFileDialog.getOpenFileName(
                self, "选择导入文件", "",
                "JSON文件 (*.json);;所有文件 (*)"
            )
            
            if ok and import_path:
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)  # 不确定进度
                
                try:
                    config_id = self.management_tools.import_database_config(
                        import_path, import_data
                    )
                    
                    if config_id:
                        config = self.config_manager.get_config(config_id)
                        QMessageBox.information(
                            self, "成功", 
                            f"数据库导入成功:\n{config.name if config else config_id}"
                        )
                        self._load_data()
                    else:
                        QMessageBox.warning(self, "失败", "数据库导入失败")
                
                finally:
                    self.progress_bar.setVisible(False)
        
        except Exception as e:
            logger.error(f"导入数据库失败: {e}")
            QMessageBox.critical(self, "错误", f"导入数据库失败:\n{str(e)}")
            self.progress_bar.setVisible(False)
    
    def _analyze_database(self):
        """分析数据库"""
        try:
            config_id = self.analysis_config_combo.currentData()
            
            if not config_id:
                QMessageBox.warning(self, "警告", "请选择要分析的数据库")
                return
            
            # 启动分析线程
            self.analysis_thread = DatabaseAnalysisThread(self.management_tools, config_id)
            self.analysis_thread.analysis_completed.connect(self._on_analysis_completed)
            self.analysis_thread.analysis_failed.connect(self._on_analysis_failed)
            
            self.analyze_btn.setEnabled(False)
            self.analyze_btn.setText("分析中...")
            
            self.analysis_thread.start()
        
        except Exception as e:
            logger.error(f"启动数据库分析失败: {e}")
            QMessageBox.critical(self, "错误", f"启动数据库分析失败:\n{str(e)}")
    
    def _analyze_all_databases(self):
        """分析所有数据库"""
        try:
            configs = self.config_manager.get_all_configs()
            existing_configs = [config for config in configs if config.exists]
            
            if not existing_configs:
                QMessageBox.information(self, "提示", "没有可分析的数据库")
                return
            
            reply = QMessageBox.question(
                self, "确认分析",
                f"确定要分析所有 {len(existing_configs)} 个数据库吗?\n\n这可能需要一些时间。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 这里可以实现批量分析逻辑
                QMessageBox.information(self, "提示", "批量分析功能正在开发中")
        
        except Exception as e:
            logger.error(f"批量分析失败: {e}")
            QMessageBox.critical(self, "错误", f"批量分析失败:\n{str(e)}")
    
    def _on_analysis_completed(self, config_id: str, result: DatabaseAnalysisResult):
        """分析完成处理"""
        try:
            config = self.config_manager.get_config(config_id)
            
            # 构建分析结果文本
            result_lines = [
                f"数据库: {config.name if config else config_id}",
                f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "=== 基本信息 ===",
                f"文件大小: {result.file_size / 1024 / 1024:.2f} MB",
                f"最后修改: {result.last_modified}",
                f"表数量: {result.table_count}",
                f"记录总数: {result.record_count}",
                f"索引数量: {result.index_count}",
                "",
                "=== 表信息 ===",
            ]
            
            for table_name, table_info in result.tables.items():
                result_lines.append(f"表 '{table_name}': {table_info['record_count']} 条记录")
                for col in table_info['columns']:
                    pk_mark = " (主键)" if col['primary_key'] else ""
                    null_mark = " NOT NULL" if col['not_null'] else ""
                    result_lines.append(f"  - {col['name']}: {col['type']}{null_mark}{pk_mark}")
            
            if result.indexes:
                result_lines.append("")
                result_lines.append("=== 索引信息 ===")
                for index_name, index_info in result.indexes.items():
                    columns = ", ".join(index_info['columns'])
                    result_lines.append(f"索引 '{index_name}': {columns}")
            
            result_lines.append("")
            result_lines.append("=== 健康状态 ===")
            result_lines.append(f"完整性检查: {'通过' if result.integrity_check else '失败'}")
            result_lines.append(f"需要压缩: {'是' if result.vacuum_needed else '否'}")
            
            if result.recommendations:
                result_lines.append("")
                result_lines.append("=== 建议 ===")
                for recommendation in result.recommendations:
                    result_lines.append(f"- {recommendation}")
            
            self.analysis_result_text.setPlainText("\n".join(result_lines))
            
        except Exception as e:
            logger.error(f"处理分析结果失败: {e}")
        
        finally:
            self.analyze_btn.setEnabled(True)
            self.analyze_btn.setText("分析")
    
    def _on_analysis_failed(self, config_id: str, error_message: str):
        """分析失败处理"""
        self.analysis_result_text.setPlainText(f"分析失败: {error_message}")
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("分析")
    
    def _refresh_statistics(self):
        """刷新统计信息"""
        try:
            stats = self.management_tools.get_database_statistics()
            
            stats_lines = [
                f"数据库总数: {stats.get('total_databases', 0)}",
                f"存在的数据库: {stats.get('existing_databases', 0)}",
                f"缺失的数据库: {stats.get('missing_databases', 0)}",
                f"总大小: {stats.get('total_size_mb', 0):.2f} MB",
                f"平均大小: {stats.get('average_size_mb', 0):.2f} MB",
                f"总记录数: {stats.get('total_records', 0)}",
                f"总表数: {stats.get('total_tables', 0)}",
                ""
            ]
            
            if stats.get('largest_database'):
                largest = stats['largest_database']
                stats_lines.append(f"最大数据库: {largest['name']} ({largest['size_mb']:.2f} MB)")
            
            if stats.get('most_used_database'):
                most_used = stats['most_used_database']
                stats_lines.append(f"最常用数据库: {most_used['name']} ({most_used['connections']} 次连接)")
            
            if stats.get('databases_by_tag'):
                stats_lines.append("")
                stats_lines.append("按标签统计:")
                for tag, count in stats['databases_by_tag'].items():
                    stats_lines.append(f"  {tag}: {count}")
            
            self.stats_text.setPlainText("\n".join(stats_lines))
            
        except Exception as e:
            logger.error(f"刷新统计信息失败: {e}")
            self.stats_text.setPlainText(f"获取统计信息失败: {str(e)}")
    
    def _vacuum_database(self):
        """压缩数据库"""
        try:
            config_id = self.optimize_config_combo.currentData()
            
            if not config_id:
                QMessageBox.warning(self, "警告", "请选择要压缩的数据库")
                return
            
            config = self.config_manager.get_config(config_id)
            if not config:
                QMessageBox.warning(self, "警告", "配置不存在")
                return
            
            reply = QMessageBox.question(
                self, "确认压缩",
                f"确定要压缩数据库 '{config.name}' 吗?\n\n这可能需要一些时间。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                success = self.management_tools.vacuum_database(config_id)
                
                if success:
                    self.operation_result_text.append(f"数据库 '{config.name}' 压缩成功")
                    QMessageBox.information(self, "成功", "数据库压缩成功")
                else:
                    self.operation_result_text.append(f"数据库 '{config.name}' 压缩失败")
                    QMessageBox.warning(self, "失败", "数据库压缩失败")
        
        except Exception as e:
            logger.error(f"压缩数据库失败: {e}")
            QMessageBox.critical(self, "错误", f"压缩数据库失败:\n{str(e)}")
    
    def _optimize_database(self):
        """优化数据库"""
        try:
            config_id = self.optimize_config_combo.currentData()
            
            if not config_id:
                QMessageBox.warning(self, "警告", "请选择要优化的数据库")
                return
            
            config = self.config_manager.get_config(config_id)
            if not config:
                QMessageBox.warning(self, "警告", "配置不存在")
                return
            
            reply = QMessageBox.question(
                self, "确认优化",
                f"确定要优化数据库 '{config.name}' 吗?\n\n这将执行分析、重建索引和压缩操作。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                result = self.management_tools.optimize_database(config_id)
                
                if result['success']:
                    operations = "\n".join(f"- {op}" for op in result['operations'])
                    space_saved = result['space_saved']
                    
                    result_text = f"数据库 '{config.name}' 优化成功:\n{operations}\n节省空间: {space_saved} 字节"
                    self.operation_result_text.append(result_text)
                    
                    QMessageBox.information(self, "成功", "数据库优化成功")
                else:
                    error_text = f"数据库 '{config.name}' 优化失败: {result['message']}"
                    self.operation_result_text.append(error_text)
                    QMessageBox.warning(self, "失败", f"数据库优化失败:\n{result['message']}")
        
        except Exception as e:
            logger.error(f"优化数据库失败: {e}")
            QMessageBox.critical(self, "错误", f"优化数据库失败:\n{str(e)}")
    
    def _repair_database(self):
        """修复数据库"""
        try:
            config_id = self.repair_config_combo.currentData()
            
            if not config_id:
                QMessageBox.warning(self, "警告", "请选择要修复的数据库")
                return
            
            config = self.config_manager.get_config(config_id)
            if not config:
                QMessageBox.warning(self, "警告", "配置不存在")
                return
            
            reply = QMessageBox.question(
                self, "确认修复",
                f"确定要修复数据库 '{config.name}' 吗?\n\n修复前会自动创建备份。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                success = self.management_tools.repair_database(config_id)
                
                if success:
                    self.operation_result_text.append(f"数据库 '{config.name}' 修复成功")
                    QMessageBox.information(self, "成功", "数据库修复成功")
                else:
                    self.operation_result_text.append(f"数据库 '{config.name}' 修复失败")
                    QMessageBox.warning(self, "失败", "数据库修复失败")
        
        except Exception as e:
            logger.error(f"修复数据库失败: {e}")
            QMessageBox.critical(self, "错误", f"修复数据库失败:\n{str(e)}")