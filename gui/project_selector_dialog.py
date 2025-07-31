#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
项目选择和管理界面
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QDialogButtonBox, QMessageBox,
    QMenu, QAction, QSplitter, QComboBox, QTextBrowser, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from core.project_manager import ProjectManager
from .project_edit_dialog import ProjectEditDialog


class ProjectSelectorDialog(QDialog):
    """项目选择和管理对话框"""
    project_selected = pyqtSignal(str)  # 发送 project_id

    def __init__(self, project_manager: ProjectManager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.setWindowTitle("项目管理")
        self.setMinimumSize(800, 600)
        self._build_ui()
        self.refresh_project_list()

    def _build_ui(self):
        """构建UI"""
        layout = QVBoxLayout(self)

        # 工具栏
        toolbar_layout = QHBoxLayout()
        new_button = QPushButton("新建项目")
        new_button.clicked.connect(self.create_new_project)
        import_button = QPushButton("导入项目")
        import_button.clicked.connect(self.import_project)
        export_button = QPushButton("导出项目")
        export_button.clicked.connect(self.export_project)
        
        toolbar_layout.addWidget(new_button)
        toolbar_layout.addWidget(import_button)
        toolbar_layout.addWidget(export_button)
        toolbar_layout.addStretch()
        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self.refresh_project_list)
        toolbar_layout.addWidget(refresh_button)
        layout.addLayout(toolbar_layout)
        
        # 搜索和排序
        filter_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索项目...")
        self.search_input.textChanged.connect(self.filter_projects)
        filter_layout.addWidget(self.search_input)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("按最近使用排序", "last_accessed")
        self.sort_combo.addItem("按名称排序", "name")
        self.sort_combo.addItem("按创建时间排序", "created_at")
        self.sort_combo.currentIndexChanged.connect(self.refresh_project_list)
        filter_layout.addWidget(self.sort_combo)
        layout.addLayout(filter_layout)

        # 主分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 项目列表
        self.project_list = QListWidget()
        self.project_list.itemDoubleClicked.connect(self._load_selected_project)
        self.project_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(self._show_context_menu)
        self.project_list.itemSelectionChanged.connect(self._on_project_selection_changed)
        splitter.addWidget(self.project_list)
        
        # 项目详情
        self.project_details = QTextBrowser()
        self.project_details.setOpenExternalLinks(True)
        splitter.addWidget(self.project_details)
        
        splitter.setSizes([300, 500])

        # 底部按钮
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("加载项目")
        self.button_box.button(QDialogButtonBox.Cancel).setText("取消")
        self.button_box.accepted.connect(self._load_selected_project)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def refresh_project_list(self):
        """刷新项目列表"""
        self.project_list.clear()
        projects = self.project_manager.get_all_projects()
        
        # 排序 - 使用稳定的多级排序键以保证顺序一致性
        sort_key = self.sort_combo.currentData()
        if sort_key == 'last_accessed':
            # 按最近使用时间降序，相同时间则按名称升序，最后按ID升序
            projects.sort(key=lambda p: (p.last_accessed, p.name.lower(), p.id))
            projects.reverse()  # 最近使用的在前
        elif sort_key == 'name':
            # 按名称升序，相同名称则按创建时间升序，最后按ID升序
            projects.sort(key=lambda p: (p.name.lower(), p.created_at, p.id))
        elif sort_key == 'created_at':
            # 按创建时间降序，相同时间则按名称升序，最后按ID升序
            projects.sort(key=lambda p: (p.created_at, p.name.lower(), p.id))
            projects.reverse()  # 最新创建的在前
        else:
            # 默认按最近使用时间降序
            projects.sort(key=lambda p: (p.last_accessed, p.name.lower(), p.id))
            projects.reverse()  # 最近使用的在前
        
        for project in projects:
            self._add_project_list_item(project)
        
        self.filter_projects()

    def filter_projects(self):
        """根据搜索文本过滤项目"""
        search_text = self.search_input.text().lower()
        for i in range(self.project_list.count()):
            item = self.project_list.item(i)
            project_id = item.data(Qt.UserRole)
            project = self.project_manager.get_project(project_id)  # 使用get_project避免更新访问时间
            if project and search_text in project.name.lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def _add_project_list_item(self, project):
        """添加自定义项目列表项"""
        item = QListWidgetItem()
        item.setData(Qt.UserRole, project.id)
        
        # 自定义Widget来显示多行信息
        widget = QLabel(f"<b>{project.name}</b><br><small>类型: {project.swagger_source.type} | API: {project.api_count} | 最近访问: {project.last_accessed.strftime('%Y-%m-%d %H:%M')}</small>")
        widget.setWordWrap(True)
        item.setSizeHint(widget.sizeHint())
        self.project_list.addItem(item)
        self.project_list.setItemWidget(item, widget)

    def _on_project_selection_changed(self):
        """当项目选择变化时更新详情"""
        item = self.project_list.currentItem()
        if item:
            project_id = item.data(Qt.UserRole)
            project = self.project_manager.get_project(project_id)  # 使用get_project避免更新访问时间
            if project:
                details_html = f"""
                <h3>{project.name}</h3>
                <p><b>描述:</b> {project.description or '无'}</p>
                <p><b>来源类型:</b> {project.swagger_source.type}</p>
                <p><b>来源地址:</b> {project.swagger_source.location}</p>
                <p><b>基础URL:</b> {project.base_url or '未设置'}</p>
                <p><b>API数量:</b> {project.api_count}</p>
                <p><b>创建时间:</b> {project.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><b>最后访问:</b> {project.last_accessed.strftime('%Y-%m-%d %H:%M:%S')}</p>
                """
                self.project_details.setHtml(details_html)

    def create_new_project(self):
        """创建新项目"""
        dialog = ProjectEditDialog(parent=self)
        dialog.project_saved.connect(self._on_project_saved)
        dialog.exec_()

    def import_project(self):
        """导入项目"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择项目文件", "", "压缩文件 (*.zip)"
        )
        if file_path:
            try:
                project = self.project_manager.import_project(file_path)
                if project:
                    QMessageBox.information(self, "成功", f"项目 '{project.name}' 导入成功！")
                    self.refresh_project_list()
                else:
                    QMessageBox.warning(self, "失败", "导入项目失败，请检查文件格式。")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入项目时出错：{str(e)}")

    def export_project(self):
        """导出选中的项目"""
        item = self.project_list.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择一个项目")
            return
            
        project_id = item.data(Qt.UserRole)
        project = self.project_manager.load_project(project_id)
        if not project:
            QMessageBox.warning(self, "错误", "无法加载选中的项目")
            return
            
        # 选择保存位置
        default_name = f"{project.name}.zip"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出项目", default_name, "压缩文件 (*.zip)"
        )
        
        if file_path:
            try:
                if self.project_manager.export_project(project_id, file_path):
                    QMessageBox.information(self, "成功", f"项目 '{project.name}' 已导出到 {file_path}")
                else:
                    QMessageBox.warning(self, "失败", "导出项目失败")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出项目时出错：{str(e)}")

    def _edit_selected_project(self):
        """编辑选中项目"""
        item = self.project_list.currentItem()
        if item:
            project_id = item.data(Qt.UserRole)
            project = self.project_manager.load_project(project_id)
            if project:
                dialog = ProjectEditDialog(project, self)
                dialog.project_saved.connect(self._on_project_saved)
                dialog.exec_()

    def _delete_selected_project(self):
        """删除选中项目"""
        item = self.project_list.currentItem()
        if item:
            project_id = item.data(Qt.UserRole)
            project = self.project_manager.load_project(project_id)
            if project:
                reply = QMessageBox.question(self, "确认删除",
                                             f"确定要删除项目 \"{project.name}\" 吗？此操作不可撤销。",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    if self.project_manager.delete_project(project_id):
                        self.refresh_project_list()
                    else:
                        QMessageBox.warning(self, "错误", "删除项目失败")

    def _load_selected_project(self):
        """加载选中项目"""
        item = self.project_list.currentItem()
        if item:
            project_id = item.data(Qt.UserRole)
            self.project_selected.emit(project_id)
            self.accept()
        else:
            QMessageBox.warning(self, "提示", "请先选择一个项目")

    def _on_project_saved(self, project):
        """项目保存后的处理"""
        self.project_manager.update_project(project)
        self.refresh_project_list()

    def _show_context_menu(self, pos):
        """显示上下文菜单"""
        item = self.project_list.itemAt(pos)
        if item:
            menu = QMenu(self)
            load_action = QAction("加载项目", self)
            edit_action = QAction("编辑项目", self)
            delete_action = QAction("删除项目", self)
            export_action = QAction("导出项目", self)

            load_action.triggered.connect(self._load_selected_project)
            edit_action.triggered.connect(self._edit_selected_project)
            delete_action.triggered.connect(self._delete_selected_project)
            export_action.triggered.connect(self.export_project)

            menu.addAction(load_action)
            menu.addAction(edit_action)
            menu.addAction(delete_action)
            menu.addAction(export_action)
            menu.exec_(self.project_list.mapToGlobal(pos))

