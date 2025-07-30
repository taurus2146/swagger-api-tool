#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API列表控件
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLineEdit, QLabel, QComboBox, QHeaderView, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from .styles import HTTP_METHOD_COLORS


class ApiListWidget(QWidget):
    """
    API列表控件，用于显示和管理API列表
    """
    
    # 自定义信号
    api_selected = pyqtSignal(dict)  # 当API被选中时发出信号
    export_apis_requested = pyqtSignal(list)  # 请求导出API列表
    
    def __init__(self, parent=None):
        """
        初始化API列表控件
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.api_list = []
        self.filtered_api_list = []
        self.init_ui()
        
        
    def init_ui(self):
        """
        初始化界面
        """
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 顶部搜索和过滤栏
        filter_layout = QHBoxLayout()
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索API路径、摘要或标签...")
        self.search_input.textChanged.connect(self.filter_apis)
        filter_layout.addWidget(self.search_input)
        
        # 标签过滤下拉框
        tag_label = QLabel("标签:")
        filter_layout.addWidget(tag_label)
        
        self.tag_filter = QComboBox()
        self.tag_filter.addItem("全部")
        self.tag_filter.setMinimumWidth(200)  # 设置最小宽度
        self.tag_filter.setSizeAdjustPolicy(QComboBox.AdjustToContents)  # 自动调整宽度以适应内容
        self.tag_filter.currentTextChanged.connect(self.filter_apis)
        filter_layout.addWidget(self.tag_filter)
        
        # 添加弹性空间
        filter_layout.addStretch()
        
        # 导出按钮
        self.export_button = QPushButton("导出API")
        self.export_button.setToolTip("选择标签导出API")
        self.export_button.clicked.connect(self._show_export_dialog)
        filter_layout.addWidget(self.export_button)
        
        main_layout.addLayout(filter_layout)
        
        # API树形结构
        self.api_tree = QTreeWidget()
        self.api_tree.setHeaderLabels(["标签", "方法", "路径", "摘要"])
        self.api_tree.setColumnWidth(0, 150)  # 标签列宽度
        self.api_tree.setColumnWidth(1, 80)   # 方法列宽度
        
        self.api_tree.setSelectionBehavior(QTreeWidget.SelectRows)
        self.api_tree.setSelectionMode(QTreeWidget.SingleSelection)
        self.api_tree.itemSelectionChanged.connect(self.on_api_selected)
        
        main_layout.addWidget(self.api_tree)
        
    def set_api_list(self, api_list):
        """
        设置API列表
        
        Args:
            api_list (list): API信息列表
        """
        self.api_list = api_list
        self.filtered_api_list = api_list.copy()
        
        # 计算公共前缀
        self._calculate_common_prefix()
        
        # 更新标签过滤器
        self.update_tag_filter()
        
        # 更新表格
        self.update_table()
        
    def update_tag_filter(self):
        """
        更新标签过滤器
        """
        # 清空当前项
        self.tag_filter.clear()
        self.tag_filter.addItem("全部")
        
        # 收集所有唯一标签
        tags = set()
        max_width = 0
        for api in self.api_list:
            api_tags = api.get('tags', [])
            if api_tags:  # 只处理非空的标签列表
                for tag in api_tags:
                    if tag and isinstance(tag, str):  # 确保标签是有效的字符串
                        tags.add(tag)
                        # 计算标签长度
                        max_width = max(max_width, len(tag))
        
        # 添加所有标签到下拉框
        if tags:  # 只有在有标签时才添加
            for tag in sorted(tags):
                self.tag_filter.addItem(tag)
            
            # 根据最长标签调整下拉框宽度
            # 每个字符大约8像素，加上一些边距
            estimated_width = max(200, min(400, max_width * 8 + 50))
            self.tag_filter.setMinimumWidth(estimated_width)
            
    def filter_apis(self):
        """
        根据过滤条件筛选API
        """
        search_text = self.search_input.text().lower()
        tag_filter = self.tag_filter.currentText()
        
        self.filtered_api_list = []
        
        for api in self.api_list:
            # 搜索文本过滤（搜索路径、摘要和标签）
            if search_text:
                path = api.get('path', '').lower()
                summary = api.get('summary', '').lower()
                description = api.get('description', '').lower()
                # 获取API的所有标签并转为小写
                api_tags = api.get('tags', [])
                tags_text = ' '.join(tag.lower() for tag in api_tags if tag)
                
                # 搜索路径、摘要、描述或标签
                if (search_text not in path and 
                    search_text not in summary and 
                    search_text not in description and
                    search_text not in tags_text):
                    continue
                
            # 标签过滤
            if tag_filter != "全部":
                api_tags = api.get('tags', [])
                if tag_filter not in api_tags:
                    continue
                
            self.filtered_api_list.append(api)
            
        # 更新表格
        self.update_table()
            
    def _show_export_dialog(self):
        """
        显示多标签选择导出的对话框
        """
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout, QLabel, QMessageBox
        
        # 获取所有标签
        all_tags = set()
        for api in self.api_list:
            for tag in api.get('tags', ['未分类']):
                if tag:
                    all_tags.add(tag)
        
        if not all_tags:
            QMessageBox.warning(self, "提示", "没有可用的标签")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("选择要导出的标签")
        dialog.resize(400, 500)
        layout = QVBoxLayout(dialog)
        
        # 添加说明文字
        label = QLabel("请选择一个或多个标签进行导出：")
        layout.addWidget(label)
        
        # 标签列表
        tag_list = QListWidget()
        tag_list.setSelectionMode(QListWidget.MultiSelection)
        
        # 添加所有标签并显示API数量
        for tag in sorted(all_tags):
            # 统计每个标签的API数量
            api_count = sum(1 for api in self.api_list if tag in api.get('tags', []))
            item = QListWidgetItem(f"{tag} ({api_count} 个API)")
            item.setData(Qt.UserRole, tag)  # 存储实际的标签名
            tag_list.addItem(item)
            
        layout.addWidget(tag_list)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 全选按钮
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(lambda: tag_list.selectAll())
        button_layout.addWidget(select_all_btn)
        
        # 取消全选按钮
        clear_btn = QPushButton("取消全选")
        clear_btn.clicked.connect(lambda: tag_list.clearSelection())
        button_layout.addWidget(clear_btn)
        
        # 导出按钮
        export_btn = QPushButton("导出")
        export_btn.clicked.connect(lambda: self._export_selected_tags(dialog, tag_list))
        button_layout.addWidget(export_btn)
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec_()

    def _export_selected_tags(self, dialog, tag_list):
        """
        处理选中的标签并进行导出
        """
        # 从选中项中获取实际的标签名（存储在UserRole中）
        selected_tags = [item.data(Qt.UserRole) for item in tag_list.selectedItems()]
        
        if not selected_tags:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "提示", "请至少选择一个标签")
            return
            
        # 筛选出属于选中标签的API
        filtered_apis = []
        for api in self.api_list:
            api_tags = api.get('tags', [])
            if any(tag in api_tags for tag in selected_tags):
                filtered_apis.append(api)
        
        if filtered_apis:
            self.export_apis_requested.emit(filtered_apis)
            dialog.accept()
        else:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", "没有找到匹配的API。")
        
    def update_table(self):
        """
        更新API树形结构
        """
        self.api_tree.clear()
        
        tag_nodes = {}
        for idx, api in enumerate(self.filtered_api_list):
            for tag in api.get('tags', ['未分类']):
                # 创建标签节点
                if tag not in tag_nodes:
                    tag_node = QTreeWidgetItem(self.api_tree)
                    tag_node.setText(0, tag)
                    tag_nodes[tag] = tag_node
                else:
                    tag_node = tag_nodes[tag]
                
                # 添加API节点
                api_node = QTreeWidgetItem(tag_node)
                api_node.setText(0, tag)
                method = api.get('method', '').upper()
                api_node.setText(1, method)
                api_node.setText(2, self._get_display_path(api.get('path', '')))
                api_node.setText(3, api.get('summary', ''))
                api_node.setData(0, Qt.UserRole, idx)
                
                # 设置HTTP方法颜色
                method_color = HTTP_METHOD_COLORS.get(method, '#666666')
                api_node.setForeground(1, QColor(method_color))
                
        self.api_tree.expandAll()  # 默认展开所有节点
            
    def on_api_selected(self):
        """
        当API被选中时的处理
        """
        selected_item = self.api_tree.currentItem()
        if selected_item and selected_item.childCount() == 0:  # 确保选中的是API节点，而不是标签节点
            original_index = selected_item.data(0, Qt.UserRole)
            if original_index is not None and 0 <= original_index < len(self.filtered_api_list):
                selected_api = self.filtered_api_list[original_index]
                self.api_selected.emit(selected_api)
    
    def _calculate_common_prefix(self):
        """
        计算所有API路径的公共前缀
        """
        if not self.api_list:
            self.common_prefix = ''
            return
        
        # 获取所有路径
        paths = [api.get('path', '') for api in self.api_list if api.get('path')]
        
        if not paths:
            self.common_prefix = ''
            return
        
        # 找出最短路径
        min_path = min(paths, key=len)
        
        # 逐字符比较找出公共前缀
        common_prefix = ''
        for i, char in enumerate(min_path):
            if all(len(path) > i and path[i] == char for path in paths):
                common_prefix += char
            else:
                break
        
        # 确保公共前缀在最后一个 '/' 处截断
        last_slash = common_prefix.rfind('/')
        if last_slash > 0:
            self.common_prefix = common_prefix[:last_slash]
        else:
            self.common_prefix = ''
    
    def _get_display_path(self, full_path):
        """
        获取显示路径（去除公共前缀）
        
        Args:
            full_path (str): 完整路径
            
        Returns:
            str: 显示路径
        """
        if hasattr(self, 'common_prefix') and self.common_prefix and full_path.startswith(self.common_prefix):
            # 去除公共前缀，但保留开头的 '/'
            display_path = full_path[len(self.common_prefix):]
            if not display_path.startswith('/'):
                display_path = '/' + display_path
            return display_path
        return full_path
    
    def _on_export_clicked(self):
        """
        当点击导出按钮时
        """
        if self.filtered_api_list:
            self.export_apis_requested.emit(self.filtered_api_list)
