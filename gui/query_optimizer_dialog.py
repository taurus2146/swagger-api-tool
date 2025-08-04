#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
查询优化器对话框
提供查询性能分析、慢查询监控、索引优化建议的GUI界面
"""

import logging
from typing import Optional
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QPushButton, QLabel, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QMessageBox, QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QHeaderView, QSplitter, QFrame, QProgressBar, QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCharFormat, QSyntaxHighlighter

from core.query_optimizer import QueryOptimizer, SlowQuery, IndexUsageStats
from core.database_config_manager import DatabaseConfigManager

logger = logging.getLogger(__name__)


class SQLHighlighter(QSyntaxHighlighter):
    """SQL语法高亮器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 定义高亮规则
        self.highlighting_rules = []
        
        # SQL关键字
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(Qt.blue)
        keyword_format.setFontWeight(QFont.Bold)
        
        keywords = [
            'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER',
            'ON', 'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET',
            'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER',
            'TABLE', 'INDEX', 'VIEW', 'DATABASE', 'SCHEMA',
            'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'LIKE', 'BETWEEN',
            'IS', 'NULL', 'DISTINCT', 'AS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END'
        ]
        
        for keyword in keywords:
            pattern = f'\\b{keyword}\\b'
            self.highlighting_rules.append((pattern, keyword_format))
        
        # 字符串
        string_format = QTextCharFormat()
        string_format.setForeground(Qt.darkGreen)
        self.highlighting_rules.append(("'[^']*'", string_format))
        self.highlighting_rules.append(('"[^"]*"', string_format))
        
        # 注释
        comment_format = QTextCharFormat()
        comment_format.setForeground(Qt.gray)
        comment_format.setFontItalic(True)
        self.highlighting_rules.append(("--[^\n]*", comment_format))
    
    def highlightBlock(self, text):
        import re
        for pattern, format in self.highlighting_rules:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start, end = match.span()
                self.setFormat(start, end - start, format)


class QueryAnalysisThread(QThread):
    """查询分析线程"""
    
    analysis_completed = pyqtSignal(str, object)  # query, analysis_result
    analysis_failed = pyqtSignal(str, str)  # query, error_message
    
    def __init__(self, optimizer: QueryOptimizer, query: str):
        super().__init__()
        self.optimizer = optimizer
        self.query = query
    
    def run(self):
        try:
            plan = self.optimizer.analyze_query_plan(self.query)
            if plan:
                self.analysis_completed.emit(self.query, plan)
            else:
                self.analysis_failed.emit(self.query, "分析失败")
        except Exception as e:
            self.analysis_failed.emit(self.query, str(e))


class QueryOptimizerDialog(QDialog):
    """查询优化器对话框"""
    
    def __init__(self, config_manager: DatabaseConfigManager, parent=None):
        """
        初始化对话框
        
        Args:
            config_manager: 数据库配置管理器
            parent: 父窗口
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.optimizer: Optional[QueryOptimizer] = None
        
        self.setWindowTitle("查询优化器")
        self.setModal(True)
        self.resize(1000, 800)
        
        # 初始化UI
        self._init_ui()
        
        # 加载数据库配置
        self._load_database_configs()
        
        # 设置定时器更新统计信息
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_stats)
        self._update_timer.start(5000)  # 每5秒更新一次
    
    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        
        # 数据库选择
        db_layout = QHBoxLayout()
        db_layout.addWidget(QLabel("选择数据库:"))
        
        self.db_combo = QComboBox()
        self.db_combo.currentTextChanged.connect(self._on_database_changed)
        db_layout.addWidget(self.db_combo)
        
        # 配置按钮
        self.config_btn = QPushButton("配置优化器")
        self.config_btn.clicked.connect(self._show_config_dialog)
        db_layout.addWidget(self.config_btn)
        
        db_layout.addStretch()
        layout.addLayout(db_layout)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 查询分析标签页
        self._create_query_analysis_tab()
        
        # 慢查询监控标签页
        self._create_slow_query_tab()
        
        # 索引优化标签页
        self._create_index_optimization_tab()
        
        # 缓存管理标签页
        self._create_cache_management_tab()
        
        # 性能统计标签页
        self._create_performance_stats_tab()
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self._refresh_data)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_query_analysis_tab(self):
        """创建查询分析标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 查询输入组
        query_group = QGroupBox("查询分析")
        query_layout = QVBoxLayout(query_group)
        
        # SQL输入框
        self.query_input = QTextEdit()
        self.query_input.setMaximumHeight(150)
        self.query_input.setPlaceholderText("输入SQL查询语句...")
        
        # 添加语法高亮
        self.sql_highlighter = SQLHighlighter(self.query_input.document())
        
        query_layout.addWidget(QLabel("SQL查询:"))
        query_layout.addWidget(self.query_input)
        
        # 分析按钮
        analyze_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("分析查询")
        self.analyze_btn.clicked.connect(self._analyze_query)
        analyze_layout.addWidget(self.analyze_btn)
        
        self.execute_btn = QPushButton("执行查询")
        self.execute_btn.clicked.connect(self._execute_query)
        analyze_layout.addWidget(self.execute_btn)
        
        analyze_layout.addStretch()
        query_layout.addLayout(analyze_layout)
        
        layout.addWidget(query_group)
        
        # 分析结果组
        result_group = QGroupBox("分析结果")
        result_layout = QVBoxLayout(result_group)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 执行计划
        plan_widget = QWidget()
        plan_layout = QVBoxLayout(plan_widget)
        plan_layout.addWidget(QLabel("执行计划:"))
        
        self.plan_text = QTextEdit()
        self.plan_text.setReadOnly(True)
        plan_layout.addWidget(self.plan_text)
        
        splitter.addWidget(plan_widget)
        
        # 优化建议
        suggestions_widget = QWidget()
        suggestions_layout = QVBoxLayout(suggestions_widget)
        suggestions_layout.addWidget(QLabel("优化建议:"))
        
        self.suggestions_text = QTextEdit()
        self.suggestions_text.setReadOnly(True)
        suggestions_layout.addWidget(self.suggestions_text)
        
        splitter.addWidget(suggestions_widget)
        
        # 设置分割器比例
        splitter.setSizes([500, 500])
        result_layout.addWidget(splitter)
        
        layout.addWidget(result_group)
        
        self.tab_widget.addTab(tab, "查询分析")
    
    def _create_slow_query_tab(self):
        """创建慢查询监控标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 慢查询表格
        self.slow_query_table = QTableWidget()
        self.slow_query_table.setColumnCount(5)
        self.slow_query_table.setHorizontalHeaderLabels([
            "查询", "执行时间(秒)", "频次", "时间戳", "操作"
        ])
        
        # 设置表格属性
        header = self.slow_query_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 查询列自适应
        header.setSectionResizeMode(1, QHeaderView.Fixed)    # 执行时间
        header.setSectionResizeMode(2, QHeaderView.Fixed)    # 频次
        header.setSectionResizeMode(3, QHeaderView.Fixed)    # 时间戳
        header.setSectionResizeMode(4, QHeaderView.Fixed)    # 操作
        
        self.slow_query_table.setColumnWidth(1, 100)
        self.slow_query_table.setColumnWidth(2, 60)
        self.slow_query_table.setColumnWidth(3, 150)
        self.slow_query_table.setColumnWidth(4, 100)
        
        self.slow_query_table.setAlternatingRowColors(True)
        self.slow_query_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(QLabel("慢查询记录:"))
        layout.addWidget(self.slow_query_table)
        
        # 操作按钮
        slow_query_btn_layout = QHBoxLayout()
        
        self.clear_slow_queries_btn = QPushButton("清空记录")
        self.clear_slow_queries_btn.clicked.connect(self._clear_slow_queries)
        slow_query_btn_layout.addWidget(self.clear_slow_queries_btn)
        
        slow_query_btn_layout.addStretch()
        layout.addLayout(slow_query_btn_layout)
        
        self.tab_widget.addTab(tab, "慢查询监控")
    
    def _create_index_optimization_tab(self):
        """创建索引优化标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)
        
        # 索引使用统计
        index_widget = QWidget()
        index_layout = QVBoxLayout(index_widget)
        
        index_layout.addWidget(QLabel("索引使用统计:"))
        
        self.index_table = QTableWidget()
        self.index_table.setColumnCount(6)
        self.index_table.setHorizontalHeaderLabels([
            "索引名", "表名", "使用次数", "最后使用", "选择性", "是否唯一"
        ])
        
        # 设置表格属性
        index_header = self.index_table.horizontalHeader()
        index_header.setSectionResizeMode(0, QHeaderView.Interactive)
        index_header.setSectionResizeMode(1, QHeaderView.Interactive)
        index_header.setSectionResizeMode(2, QHeaderView.Fixed)
        index_header.setSectionResizeMode(3, QHeaderView.Fixed)
        index_header.setSectionResizeMode(4, QHeaderView.Fixed)
        index_header.setSectionResizeMode(5, QHeaderView.Fixed)
        
        self.index_table.setColumnWidth(2, 80)
        self.index_table.setColumnWidth(3, 120)
        self.index_table.setColumnWidth(4, 80)
        self.index_table.setColumnWidth(5, 80)
        
        self.index_table.setAlternatingRowColors(True)
        index_layout.addWidget(self.index_table)
        
        splitter.addWidget(index_widget)
        
        # 索引建议
        suggestion_widget = QWidget()
        suggestion_layout = QVBoxLayout(suggestion_widget)
        
        suggestion_layout.addWidget(QLabel("索引优化建议:"))
        
        self.index_suggestions_text = QTextEdit()
        self.index_suggestions_text.setReadOnly(True)
        self.index_suggestions_text.setMaximumHeight(200)
        suggestion_layout.addWidget(self.index_suggestions_text)
        
        # 未使用索引
        unused_layout = QHBoxLayout()
        unused_layout.addWidget(QLabel("未使用的索引:"))
        
        self.unused_indexes_text = QTextEdit()
        self.unused_indexes_text.setReadOnly(True)
        self.unused_indexes_text.setMaximumHeight(100)
        unused_layout.addWidget(self.unused_indexes_text)
        
        suggestion_layout.addLayout(unused_layout)
        
        splitter.addWidget(suggestion_widget)
        
        # 设置分割器比例
        splitter.setSizes([400, 300])
        
        self.tab_widget.addTab(tab, "索引优化")
    
    def _create_cache_management_tab(self):
        """创建缓存管理标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 缓存统计
        cache_stats_group = QGroupBox("缓存统计")
        cache_stats_layout = QFormLayout(cache_stats_group)
        
        self.cache_size_label = QLabel("0")
        cache_stats_layout.addRow("缓存大小:", self.cache_size_label)
        
        self.cache_hits_label = QLabel("0")
        cache_stats_layout.addRow("缓存命中:", self.cache_hits_label)
        
        self.cache_misses_label = QLabel("0")
        cache_stats_layout.addRow("缓存未命中:", self.cache_misses_label)
        
        self.cache_hit_rate_label = QLabel("0%")
        cache_stats_layout.addRow("命中率:", self.cache_hit_rate_label)
        
        self.cache_evictions_label = QLabel("0")
        cache_stats_layout.addRow("缓存淘汰:", self.cache_evictions_label)
        
        layout.addWidget(cache_stats_group)
        
        # 缓存配置
        cache_config_group = QGroupBox("缓存配置")
        cache_config_layout = QFormLayout(cache_config_group)
        
        self.cache_max_size_spin = QSpinBox()
        self.cache_max_size_spin.setRange(100, 10000)
        self.cache_max_size_spin.setValue(1000)
        cache_config_layout.addRow("最大缓存条目:", self.cache_max_size_spin)
        
        self.cache_ttl_spin = QSpinBox()
        self.cache_ttl_spin.setRange(60, 3600)
        self.cache_ttl_spin.setValue(300)
        self.cache_ttl_spin.setSuffix(" 秒")
        cache_config_layout.addRow("缓存生存时间:", self.cache_ttl_spin)
        
        layout.addWidget(cache_config_group)
        
        # 缓存操作
        cache_btn_layout = QHBoxLayout()
        
        self.clear_cache_btn = QPushButton("清空缓存")
        self.clear_cache_btn.clicked.connect(self._clear_cache)
        cache_btn_layout.addWidget(self.clear_cache_btn)
        
        self.apply_cache_config_btn = QPushButton("应用配置")
        self.apply_cache_config_btn.clicked.connect(self._apply_cache_config)
        cache_btn_layout.addWidget(self.apply_cache_config_btn)
        
        cache_btn_layout.addStretch()
        layout.addLayout(cache_btn_layout)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "缓存管理")
    
    def _create_performance_stats_tab(self):
        """创建性能统计标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 总体统计
        overall_group = QGroupBox("总体统计")
        overall_layout = QFormLayout(overall_group)
        
        self.total_queries_label = QLabel("0")
        overall_layout.addRow("总查询数:", self.total_queries_label)
        
        self.total_time_label = QLabel("0.0 秒")
        overall_layout.addRow("总执行时间:", self.total_time_label)
        
        self.avg_time_label = QLabel("0.0 秒")
        overall_layout.addRow("平均执行时间:", self.avg_time_label)
        
        self.slow_queries_count_label = QLabel("0")
        overall_layout.addRow("慢查询数量:", self.slow_queries_count_label)
        
        layout.addWidget(overall_group)
        
        # 优化器配置
        optimizer_group = QGroupBox("优化器配置")
        optimizer_layout = QFormLayout(optimizer_group)
        
        self.slow_query_threshold_spin = QDoubleSpinBox()
        self.slow_query_threshold_spin.setRange(0.01, 10.0)
        self.slow_query_threshold_spin.setValue(0.1)
        self.slow_query_threshold_spin.setSingleStep(0.01)
        self.slow_query_threshold_spin.setSuffix(" 秒")
        optimizer_layout.addRow("慢查询阈值:", self.slow_query_threshold_spin)
        
        layout.addWidget(optimizer_group)
        
        # 操作按钮
        stats_btn_layout = QHBoxLayout()
        
        self.clear_stats_btn = QPushButton("清空统计")
        self.clear_stats_btn.clicked.connect(self._clear_stats)
        stats_btn_layout.addWidget(self.clear_stats_btn)
        
        self.optimize_db_btn = QPushButton("优化数据库")
        self.optimize_db_btn.clicked.connect(self._optimize_database)
        stats_btn_layout.addWidget(self.optimize_db_btn)
        
        stats_btn_layout.addStretch()
        layout.addLayout(stats_btn_layout)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "性能统计")
    
    def _load_database_configs(self):
        """加载数据库配置"""
        try:
            configs = self.config_manager.get_all_configs()
            
            self.db_combo.clear()
            for config in configs:
                if config.exists:
                    display_text = f"{config.name} ({config.path})"
                    self.db_combo.addItem(display_text, config.path)
            
            # 选择默认数据库
            default_config = self.config_manager.get_default_config()
            if default_config and default_config.exists:
                for i in range(self.db_combo.count()):
                    if self.db_combo.itemData(i) == default_config.path:
                        self.db_combo.setCurrentIndex(i)
                        break
            
        except Exception as e:
            logger.error(f"加载数据库配置失败: {e}")
            QMessageBox.critical(self, "错误", f"加载数据库配置失败:\n{str(e)}")
    
    def _on_database_changed(self):
        """数据库选择变化处理"""
        db_path = self.db_combo.currentData()
        if db_path:
            try:
                # 创建新的优化器实例
                threshold = self.slow_query_threshold_spin.value()
                self.optimizer = QueryOptimizer(db_path, threshold)
                
                # 刷新数据
                self._refresh_data()
                
            except Exception as e:
                logger.error(f"切换数据库失败: {e}")
                QMessageBox.critical(self, "错误", f"切换数据库失败:\n{str(e)}")
    
    def _show_config_dialog(self):
        """显示配置对话框"""
        if not self.optimizer:
            QMessageBox.warning(self, "警告", "请先选择数据库")
            return
        
        # 这里可以实现更详细的配置对话框
        QMessageBox.information(self, "提示", "配置功能正在开发中")
    
    def _analyze_query(self):
        """分析查询"""
        if not self.optimizer:
            QMessageBox.warning(self, "警告", "请先选择数据库")
            return
        
        query = self.query_input.toPlainText().strip()
        if not query:
            QMessageBox.warning(self, "警告", "请输入查询语句")
            return
        
        # 启动分析线程
        self.analysis_thread = QueryAnalysisThread(self.optimizer, query)
        self.analysis_thread.analysis_completed.connect(self._on_analysis_completed)
        self.analysis_thread.analysis_failed.connect(self._on_analysis_failed)
        
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("分析中...")
        
        self.analysis_thread.start()
    
    def _execute_query(self):
        """执行查询"""
        if not self.optimizer:
            QMessageBox.warning(self, "警告", "请先选择数据库")
            return
        
        query = self.query_input.toPlainText().strip()
        if not query:
            QMessageBox.warning(self, "警告", "请输入查询语句")
            return
        
        try:
            # 执行查询（带监控）
            result = self.optimizer.execute_with_monitoring(query)
            
            # 显示结果
            if result:
                result_text = f"查询执行成功，返回 {len(result)} 行结果"
                if len(result) <= 10:  # 只显示前10行
                    result_text += ":\n\n"
                    for row in result:
                        result_text += str(row) + "\n"
            else:
                result_text = "查询执行成功，无返回结果"
            
            QMessageBox.information(self, "执行结果", result_text)
            
            # 刷新统计信息
            self._update_stats()
            
        except Exception as e:
            logger.error(f"执行查询失败: {e}")
            QMessageBox.critical(self, "错误", f"执行查询失败:\n{str(e)}")
    
    def _on_analysis_completed(self, query: str, plan):
        """分析完成处理"""
        try:
            # 显示执行计划
            plan_lines = [
                f"查询: {query}",
                f"估算成本: {plan.estimated_cost}",
                f"使用索引: {'是' if plan.uses_index else '否'}",
                "",
                "执行计划步骤:"
            ]
            
            for i, step in enumerate(plan.plan_steps):
                plan_lines.append(f"{i+1}. {step['detail']}")
            
            if plan.table_scans:
                plan_lines.append("")
                plan_lines.append(f"表扫描: {', '.join(plan.table_scans)}")
            
            if plan.index_scans:
                plan_lines.append(f"索引扫描: {', '.join(plan.index_scans)}")
            
            self.plan_text.setPlainText("\n".join(plan_lines))
            
            # 显示优化建议
            if plan.recommendations:
                suggestions_text = "优化建议:\n\n"
                for i, rec in enumerate(plan.recommendations):
                    suggestions_text += f"{i+1}. {rec}\n"
            else:
                suggestions_text = "查询已经很好优化，无需额外建议。"
            
            # 添加索引建议
            index_suggestions = self.optimizer.suggest_indexes(query)
            if index_suggestions:
                suggestions_text += "\n索引建议:\n\n"
                for i, suggestion in enumerate(index_suggestions):
                    suggestions_text += f"{i+1}. {suggestion}\n"
            
            self.suggestions_text.setPlainText(suggestions_text)
            
        except Exception as e:
            logger.error(f"处理分析结果失败: {e}")
        
        finally:
            self.analyze_btn.setEnabled(True)
            self.analyze_btn.setText("分析查询")
    
    def _on_analysis_failed(self, query: str, error_message: str):
        """分析失败处理"""
        self.plan_text.setPlainText(f"分析失败: {error_message}")
        self.suggestions_text.setPlainText("无法生成建议")
        
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("分析查询")
    
    def _refresh_data(self):
        """刷新数据"""
        if not self.optimizer:
            return
        
        try:
            # 刷新慢查询
            self._refresh_slow_queries()
            
            # 刷新索引统计
            self._refresh_index_stats()
            
            # 刷新缓存统计
            self._refresh_cache_stats()
            
            # 刷新性能统计
            self._refresh_performance_stats()
            
        except Exception as e:
            logger.error(f"刷新数据失败: {e}")
    
    def _refresh_slow_queries(self):
        """刷新慢查询表格"""
        if not self.optimizer:
            return
        
        slow_queries = self.optimizer.get_slow_queries(50)
        
        self.slow_query_table.setRowCount(len(slow_queries))
        
        for i, slow_query in enumerate(slow_queries):
            # 查询（截断显示）
            query_text = slow_query.query[:100] + "..." if len(slow_query.query) > 100 else slow_query.query
            self.slow_query_table.setItem(i, 0, QTableWidgetItem(query_text))
            
            # 执行时间
            time_item = QTableWidgetItem(f"{slow_query.execution_time:.3f}")
            time_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.slow_query_table.setItem(i, 1, time_item)
            
            # 频次
            freq_item = QTableWidgetItem(str(slow_query.frequency))
            freq_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.slow_query_table.setItem(i, 2, freq_item)
            
            # 时间戳
            try:
                timestamp = datetime.fromisoformat(slow_query.timestamp)
                time_str = timestamp.strftime("%m-%d %H:%M:%S")
            except:
                time_str = slow_query.timestamp
            self.slow_query_table.setItem(i, 3, QTableWidgetItem(time_str))
            
            # 操作按钮（这里简化处理）
            self.slow_query_table.setItem(i, 4, QTableWidgetItem("详情"))
    
    def _refresh_index_stats(self):
        """刷新索引统计表格"""
        if not self.optimizer:
            return
        
        index_stats = self.optimizer.get_index_usage_stats()
        
        self.index_table.setRowCount(len(index_stats))
        
        for i, stat in enumerate(index_stats):
            # 索引名
            self.index_table.setItem(i, 0, QTableWidgetItem(stat.index_name))
            
            # 表名
            self.index_table.setItem(i, 1, QTableWidgetItem(stat.table_name))
            
            # 使用次数
            usage_item = QTableWidgetItem(str(stat.usage_count))
            usage_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.index_table.setItem(i, 2, usage_item)
            
            # 最后使用
            if stat.last_used:
                try:
                    last_used = datetime.fromisoformat(stat.last_used)
                    time_str = last_used.strftime("%m-%d %H:%M")
                except:
                    time_str = stat.last_used
            else:
                time_str = "从未使用"
            self.index_table.setItem(i, 3, QTableWidgetItem(time_str))
            
            # 选择性
            selectivity_item = QTableWidgetItem(f"{stat.selectivity:.3f}")
            selectivity_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.index_table.setItem(i, 4, selectivity_item)
            
            # 是否唯一
            unique_text = "是" if stat.is_unique else "否"
            self.index_table.setItem(i, 5, QTableWidgetItem(unique_text))
        
        # 更新未使用索引
        unused_indexes = self.optimizer.get_unused_indexes()
        if unused_indexes:
            unused_text = "以下索引未被使用，考虑删除:\n\n"
            unused_text += "\n".join(f"- {index}" for index in unused_indexes)
        else:
            unused_text = "所有索引都在使用中"
        
        self.unused_indexes_text.setPlainText(unused_text)
        
        # 更新索引建议
        suggestions_text = "索引优化建议:\n\n"
        suggestions_text += "1. 定期监控索引使用情况\n"
        suggestions_text += "2. 删除未使用的索引以节省空间\n"
        suggestions_text += "3. 为高频查询的WHERE条件列创建索引\n"
        suggestions_text += "4. 考虑为ORDER BY列创建索引\n"
        
        if unused_indexes:
            suggestions_text += f"\n发现 {len(unused_indexes)} 个未使用的索引，建议删除"
        
        self.index_suggestions_text.setPlainText(suggestions_text)
    
    def _refresh_cache_stats(self):
        """刷新缓存统计"""
        if not self.optimizer:
            return
        
        cache_stats = self.optimizer.query_cache.get_stats()
        
        self.cache_size_label.setText(f"{cache_stats['size']} / {cache_stats['max_size']}")
        self.cache_hits_label.setText(str(cache_stats['hits']))
        self.cache_misses_label.setText(str(cache_stats['misses']))
        self.cache_hit_rate_label.setText(f"{cache_stats['hit_rate']:.1f}%")
        self.cache_evictions_label.setText(str(cache_stats['evictions']))
    
    def _refresh_performance_stats(self):
        """刷新性能统计"""
        if not self.optimizer:
            return
        
        stats = self.optimizer.get_performance_stats()
        
        self.total_queries_label.setText(str(stats['total_queries']))
        self.total_time_label.setText(f"{stats['total_execution_time']:.3f} 秒")
        self.avg_time_label.setText(f"{stats['average_execution_time']:.3f} 秒")
        self.slow_queries_count_label.setText(str(stats['slow_queries_count']))
    
    def _update_stats(self):
        """定时更新统计信息"""
        try:
            self._refresh_cache_stats()
            self._refresh_performance_stats()
        except Exception as e:
            logger.debug(f"更新统计信息时发生错误: {e}")
    
    def _clear_slow_queries(self):
        """清空慢查询记录"""
        if not self.optimizer:
            return
        
        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有慢查询记录吗?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.optimizer.slow_queries.clear()
            self._refresh_slow_queries()
            QMessageBox.information(self, "成功", "慢查询记录已清空")
    
    def _clear_cache(self):
        """清空缓存"""
        if not self.optimizer:
            return
        
        self.optimizer.query_cache.clear()
        self._refresh_cache_stats()
        QMessageBox.information(self, "成功", "查询缓存已清空")
    
    def _apply_cache_config(self):
        """应用缓存配置"""
        if not self.optimizer:
            return
        
        # 更新缓存配置
        self.optimizer.query_cache.max_size = self.cache_max_size_spin.value()
        self.optimizer.query_cache.ttl_seconds = self.cache_ttl_spin.value()
        
        QMessageBox.information(self, "成功", "缓存配置已应用")
    
    def _clear_stats(self):
        """清空统计信息"""
        if not self.optimizer:
            return
        
        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有统计信息吗?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.optimizer.clear_stats()
            self._refresh_data()
            QMessageBox.information(self, "成功", "统计信息已清空")
    
    def _optimize_database(self):
        """优化数据库"""
        if not self.optimizer:
            return
        
        reply = QMessageBox.question(
            self, "确认优化",
            "确定要优化数据库吗?\n\n这将执行ANALYZE、REINDEX和VACUUM操作。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                result = self.optimizer.optimize_database()
                
                if result['success']:
                    operations = ", ".join(result['operations'])
                    QMessageBox.information(
                        self, "成功", 
                        f"数据库优化完成\n\n执行的操作: {operations}"
                    )
                else:
                    QMessageBox.warning(self, "失败", f"数据库优化失败:\n{result['message']}")
                    
            except Exception as e:
                logger.error(f"优化数据库失败: {e}")
                QMessageBox.critical(self, "错误", f"优化数据库失败:\n{str(e)}")
    
    def closeEvent(self, event):
        """关闭事件"""
        if self._update_timer:
            self._update_timer.stop()
        super().closeEvent(event)