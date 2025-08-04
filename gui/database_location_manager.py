#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库位置管理器
提供数据库文件浏览、选择、创建、移动、重命名和多数据库配置管理功能
"""

import os
import json
import shutil
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QPushButton, QLabel, QTextEdit, QListWidget, QListWidgetItem,
    QDialogButtonBox, QFileDialog, QMessageBox, QTabWidget, QWidget,
    QGridLayout, QFrame, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QSpinBox, QComboBox, QProgressBar,
    QWizard, QWizardPage, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QSettings
from PyQt5.QtGui import QFont, QIcon, QPalette

from core.database_manager import DatabaseManager
from core.storage_utils import get_default_database_path, get_app_data_dir, ensure_storage_dir

logger = logging.getLogger(__name__)


class DatabaseInfo:
    """数据库信息类"""
    
    def __init__(self, path: str, name: str = None, description: str = None):
        self.path = path
        self.name = name or os.path.splitext(os.path.basename(path))[0]
        self.description = description or ""
        self.last_accessed = None
        self.file_size = 0
        self.version = None
        self.is_valid = False
        
        self._update_info()
    
    def _update_info(self):
        """更新数据库信息"""
        try:
            if os.path.exists(self.path):
                stat = os.stat(self.path)
                self.file_size = stat.st_size
                self.last_accessed = datetime.fromtimestamp(stat.st_atime)
                
                # 尝试获取数据库版本
                db_manager = DatabaseManager(self.path)
                if db_manager.connect():
                    self.version = db_manager.get_database_version()
                    self.is_valid = db_manager.test_connection()
                    db_manager.disconnect()
        except Exception as e:
            logger.warning(f"更新数据库信息失败 {self.path}: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'path': self.path,
            'name': self.name,
            'description': self.description,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'file_size': self.file_size,
            'version': self.version,
            'is_valid': self.is_valid
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseInfo':
        """从字典创建实例"""
        db_info = cls(data['path'], data.get('name'), data.get('description'))
        if data.get('last_accessed'):
            db_info.last_accessed = datetime.fromisoformat(data['last_accessed'])
        return db_info


class DatabaseConfigManager:
    """数据库配置管理器"""
    
    def __init__(self):
        self.config_file = os.path.join(get_app_data_dir(), "database_configs.json")
        self.databases: List[DatabaseInfo] = []
        self.current_database = None
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 加载数据库列表
                    for db_data in data.get('databases', []):
                        db_info = DatabaseInfo.from_dict(db_data)
                        self.databases.append(db_info)
                    
                    # 设置当前数据库
                    current_path = data.get('current_database')
                    if current_path:
                        self.current_database = self.get_database_by_path(current_path)
            
            # 如果没有配置文件或当前数据库，使用默认数据库
            if not self.current_database:
                default_path = get_default_database_path()
                self.current_database = self.add_database(default_path, "默认数据库", "系统默认数据库")
                
        except Exception as e:
            logger.error(f"加载数据库配置失败: {e}")
            # 创建默认配置
            default_path = get_default_database_path()
            self.current_database = self.add_database(default_path, "默认数据库", "系统默认数据库")
    
    def _save_config(self):
        """保存配置"""
        try:
            # 确保配置目录存在
            ensure_storage_dir(os.path.dirname(self.config_file))
            
            data = {
                'databases': [db.to_dict() for db in self.databases],
                'current_database': self.current_database.path if self.current_database else None,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"保存数据库配置失败: {e}")
    
    def add_database(self, path: str, name: str = None, description: str = None) -> DatabaseInfo:
        """添加数据库"""
        # 检查是否已存在
        existing = self.get_database_by_path(path)
        if existing:
            return existing
        
        db_info = DatabaseInfo(path, name, description)
        self.databases.append(db_info)
        self._save_config()
        return db_info
    
    def remove_database(self, path: str) -> bool:
        """移除数据库"""
        db_info = self.get_database_by_path(path)
        if db_info:
            self.databases.remove(db_info)
            
            # 如果移除的是当前数据库，切换到第一个可用的数据库
            if self.current_database == db_info:
                self.current_database = self.databases[0] if self.databases else None
            
            self._save_config()
            return True
        return False
    
    def get_database_by_path(self, path: str) -> Optional[DatabaseInfo]:
        """根据路径获取数据库信息"""
        for db in self.databases:
            if db.path == path:
                return db
        return None
    
    def set_current_database(self, path: str) -> bool:
        """设置当前数据库"""
        db_info = self.get_database_by_path(path)
        if db_info:
            self.current_database = db_info
            self._save_config()
            return True
        return False
    
    def get_recent_databases(self, limit: int = 5) -> List[DatabaseInfo]:
        """获取最近使用的数据库"""
        # 按最后访问时间排序
        sorted_dbs = sorted(
            [db for db in self.databases if db.last_accessed],
            key=lambda x: x.last_accessed,
            reverse=True
        )
        return sorted_dbs[:limit]
    
    def update_database_info(self, path: str, name: str = None, description: str = None):
        """更新数据库信息"""
        db_info = self.get_database_by_path(path)
        if db_info:
            if name is not None:
                db_info.name = name
            if description is not None:
                db_info.description = description
            db_info._update_info()
            self._save_config()
    
    def refresh_all_databases(self):
        """刷新所有数据库信息"""
        for db in self.databases:
            db._update_info()
        self._save_config()

class DatabaseCreationWizard(QWizard):
    """数据库创建向导"""
    
    database_created = pyqtSignal(str, str, str)  # path, name, description
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("数据库创建向导")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(600, 400)
        
        # 添加向导页面
        self.addPage(self._create_welcome_page())
        self.addPage(self._create_location_page())
        self.addPage(self._create_settings_page())
        self.addPage(self._create_summary_page())
        
        # 设置按钮文本
        self.setButtonText(QWizard.NextButton, "下一步")
        self.setButtonText(QWizard.BackButton, "上一步")
        self.setButtonText(QWizard.FinishButton, "创建")
        self.setButtonText(QWizard.CancelButton, "取消")
    
    def _create_welcome_page(self) -> QWizardPage:
        """创建欢迎页面"""
        page = QWizardPage()
        page.setTitle("欢迎使用数据库创建向导")
        page.setSubTitle("此向导将帮助您创建一个新的数据库文件")
        
        layout = QVBoxLayout(page)
        
        welcome_text = QLabel("""
        <h3>数据库创建向导</h3>
        <p>此向导将引导您完成以下步骤：</p>
        <ul>
        <li>选择数据库文件位置</li>
        <li>配置数据库基本信息</li>
        <li>设置初始参数</li>
        <li>创建并初始化数据库</li>
        </ul>
        <p>点击"下一步"开始创建数据库。</p>
        """)
        welcome_text.setWordWrap(True)
        layout.addWidget(welcome_text)
        
        return page
    
    def _create_location_page(self) -> QWizardPage:
        """创建位置选择页面"""
        page = QWizardPage()
        page.setTitle("选择数据库位置")
        page.setSubTitle("请选择新数据库文件的保存位置")
        
        layout = QFormLayout(page)
        
        # 数据库路径
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("选择数据库文件路径...")
        path_layout.addWidget(self.path_edit)
        
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self._browse_database_path)
        path_layout.addWidget(browse_button)
        
        layout.addRow("数据库文件:", path_layout)
        
        # 位置类型选择
        location_group = QButtonGroup(page)
        
        self.default_location_radio = QRadioButton("使用默认位置")
        self.default_location_radio.setChecked(True)
        self.default_location_radio.toggled.connect(self._on_location_type_changed)
        location_group.addButton(self.default_location_radio)
        layout.addRow(self.default_location_radio)
        
        self.custom_location_radio = QRadioButton("自定义位置")
        self.custom_location_radio.toggled.connect(self._on_location_type_changed)
        location_group.addButton(self.custom_location_radio)
        layout.addRow(self.custom_location_radio)
        
        self.portable_location_radio = QRadioButton("便携式位置（程序目录）")
        self.portable_location_radio.toggled.connect(self._on_location_type_changed)
        location_group.addButton(self.portable_location_radio)
        layout.addRow(self.portable_location_radio)
        
        # 设置默认路径
        self._on_location_type_changed()
        
        # 注册字段
        page.registerField("database_path*", self.path_edit)
        
        return page
    
    def _create_settings_page(self) -> QWizardPage:
        """创建设置页面"""
        page = QWizardPage()
        page.setTitle("数据库设置")
        page.setSubTitle("配置数据库的基本信息")
        
        layout = QFormLayout(page)
        
        # 数据库名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入数据库名称...")
        layout.addRow("数据库名称:", self.name_edit)
        
        # 描述
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("输入数据库描述（可选）...")
        layout.addRow("描述:", self.description_edit)
        
        # 初始化选项
        init_group = QGroupBox("初始化选项")
        init_layout = QVBoxLayout(init_group)
        
        self.create_sample_data_check = QCheckBox("创建示例数据")
        init_layout.addWidget(self.create_sample_data_check)
        
        self.enable_encryption_check = QCheckBox("启用数据加密（实验性功能）")
        self.enable_encryption_check.setEnabled(False)  # 暂时禁用
        init_layout.addWidget(self.enable_encryption_check)
        
        layout.addRow(init_group)
        
        # 注册字段
        page.registerField("database_name*", self.name_edit)
        page.registerField("database_description", self.description_edit, "plainText")
        page.registerField("create_sample_data", self.create_sample_data_check)
        
        return page
    
    def _create_summary_page(self) -> QWizardPage:
        """创建摘要页面"""
        page = QWizardPage()
        page.setTitle("创建摘要")
        page.setSubTitle("请确认以下设置，然后点击"创建"按钮")
        
        layout = QVBoxLayout(page)
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(200)
        layout.addWidget(self.summary_text)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("准备创建数据库")
        layout.addWidget(self.status_label)
        
        return page
    
    def _browse_database_path(self):
        """浏览数据库路径"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择数据库文件位置",
            "",
            "SQLite数据库文件 (*.db);;所有文件 (*)"
        )
        
        if file_path:
            self.path_edit.setText(file_path)
            # 自动设置数据库名称
            if not self.name_edit.text():
                name = os.path.splitext(os.path.basename(file_path))[0]
                self.name_edit.setText(name)
    
    def _on_location_type_changed(self):
        """位置类型改变"""
        if self.default_location_radio.isChecked():
            default_path = get_default_database_path()
            # 生成唯一文件名
            base_name = "database"
            counter = 1
            while os.path.exists(default_path):
                name = f"{base_name}_{counter}.db"
                default_path = os.path.join(os.path.dirname(default_path), name)
                counter += 1
            self.path_edit.setText(default_path)
            
        elif self.portable_location_radio.isChecked():
            from core.storage_utils import get_portable_data_dir
            portable_dir = get_portable_data_dir()
            portable_path = os.path.join(portable_dir, "database.db")
            self.path_edit.setText(portable_path)
        
        # 自定义位置时不自动设置路径
    
    def initializePage(self, page_id: int):
        """初始化页面"""
        if page_id == 3:  # 摘要页面
            self._update_summary()
    
    def _update_summary(self):
        """更新摘要信息"""
        path = self.field("database_path")
        name = self.field("database_name")
        description = self.field("database_description")
        create_sample = self.field("create_sample_data")
        
        summary = f"""
<h4>数据库创建摘要</h4>
<table>
<tr><td><b>文件路径:</b></td><td>{path}</td></tr>
<tr><td><b>数据库名称:</b></td><td>{name}</td></tr>
<tr><td><b>描述:</b></td><td>{description or '无'}</td></tr>
<tr><td><b>文件大小:</b></td><td>约 50-100 KB（初始）</td></tr>
<tr><td><b>创建示例数据:</b></td><td>{'是' if create_sample else '否'}</td></tr>
</table>

<p><b>注意:</b> 如果指定的文件已存在，将会被覆盖。</p>
        """.strip()
        
        self.summary_text.setHtml(summary)
    
    def accept(self):
        """完成向导"""
        try:
            path = self.field("database_path")
            name = self.field("database_name")
            description = self.field("database_description")
            create_sample = self.field("create_sample_data")
            
            # 显示进度
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("正在创建数据库...")
            
            # 确保目录存在
            ensure_storage_dir(os.path.dirname(path))
            
            # 创建数据库
            db_manager = DatabaseManager(path)
            self.progress_bar.setValue(30)
            
            if db_manager.connect():
                self.status_label.setText("正在初始化数据库结构...")
                self.progress_bar.setValue(60)
                
                if db_manager.initialize_database():
                    self.progress_bar.setValue(80)
                    
                    # 创建示例数据
                    if create_sample:
                        self.status_label.setText("正在创建示例数据...")
                        self._create_sample_data(db_manager)
                    
                    self.progress_bar.setValue(100)
                    self.status_label.setText("数据库创建完成！")
                    
                    db_manager.disconnect()
                    
                    # 发出信号
                    self.database_created.emit(path, name, description)
                    
                    QMessageBox.information(self, "成功", f"数据库创建成功！\n\n路径: {path}")
                    super().accept()
                else:
                    raise Exception("数据库初始化失败")
            else:
                raise Exception("无法连接到数据库")
                
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.status_label.setText("创建失败")
            QMessageBox.critical(self, "错误", f"创建数据库失败:\n{str(e)}")
    
    def _create_sample_data(self, db_manager: DatabaseManager):
        """创建示例数据"""
        try:
            sample_queries = [
                '''
                INSERT INTO projects (id, name, description, swagger_source_type, swagger_source_location, created_at, last_accessed)
                VALUES ('sample1', '示例项目1', '这是一个示例项目', 'url', 'https://petstore.swagger.io/v2/swagger.json', datetime('now'), datetime('now'))
                ''',
                '''
                INSERT INTO projects (id, name, description, swagger_source_type, swagger_source_location, created_at, last_accessed)
                VALUES ('sample2', '示例项目2', '另一个示例项目', 'file', '/path/to/swagger.json', datetime('now'), datetime('now'))
                ''',
                '''
                INSERT INTO project_history (project_id, action, timestamp, details)
                VALUES ('sample1', 'created', datetime('now'), '{"name": "示例项目1"}')
                ''',
                '''
                INSERT INTO project_history (project_id, action, timestamp, details)
                VALUES ('sample2', 'created', datetime('now'), '{"name": "示例项目2"}')
                '''
            ]
            
            for query in sample_queries:
                db_manager.execute_update(query)
                
        except Exception as e:
            logger.warning(f"创建示例数据失败: {e}")
cl
ass DatabaseLocationManager(QDialog):
    """数据库位置管理对话框"""
    
    database_selected = pyqtSignal(str)  # 数据库路径
    database_changed = pyqtSignal(str, str)  # 旧路径, 新路径
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = DatabaseConfigManager()
        
        self.setWindowTitle("数据库位置管理")
        self.setModal(True)
        self.resize(800, 600)
        self.setMinimumSize(700, 500)
        
        self._init_ui()
        self._load_database_list()
        self._setup_connections()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("数据库位置管理")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 主要内容区域
        content_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：数据库列表
        left_widget = self._create_database_list_widget()
        content_splitter.addWidget(left_widget)
        
        # 右侧：数据库详情和操作
        right_widget = self._create_database_details_widget()
        content_splitter.addWidget(right_widget)
        
        content_splitter.setSizes([400, 400])
        layout.addWidget(content_splitter)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.new_database_button = QPushButton("新建数据库")
        self.new_database_button.setMinimumWidth(100)
        button_layout.addWidget(self.new_database_button)
        
        self.import_database_button = QPushButton("导入数据库")
        self.import_database_button.setMinimumWidth(100)
        button_layout.addWidget(self.import_database_button)
        
        button_layout.addStretch()
        
        # 标准对话框按钮
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_layout.addWidget(self.button_box)
        
        layout.addLayout(button_layout)
    
    def _create_database_list_widget(self) -> QWidget:
        """创建数据库列表部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 列表标题
        list_label = QLabel("数据库列表")
        list_font = QFont()
        list_font.setBold(True)
        list_label.setFont(list_font)
        layout.addWidget(list_label)
        
        # 数据库列表
        self.database_list = QListWidget()
        self.database_list.setAlternatingRowColors(True)
        layout.addWidget(self.database_list)
        
        # 列表操作按钮
        list_button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setMaximumWidth(80)
        list_button_layout.addWidget(self.refresh_button)
        
        self.remove_button = QPushButton("移除")
        self.remove_button.setMaximumWidth(80)
        self.remove_button.setEnabled(False)
        list_button_layout.addWidget(self.remove_button)
        
        list_button_layout.addStretch()
        layout.addLayout(list_button_layout)
        
        return widget
    
    def _create_database_details_widget(self) -> QWidget:
        """创建数据库详情部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 详情标题
        details_label = QLabel("数据库详情")
        details_font = QFont()
        details_font.setBold(True)
        details_label.setFont(details_font)
        layout.addWidget(details_label)
        
        # 基本信息组
        info_group = QGroupBox("基本信息")
        info_layout = QFormLayout(info_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("数据库名称")
        info_layout.addRow("名称:", self.name_edit)
        
        self.path_label = QLabel("未选择")
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("color: gray;")
        info_layout.addRow("路径:", self.path_label)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setPlaceholderText("数据库描述（可选）")
        info_layout.addRow("描述:", self.description_edit)
        
        layout.addWidget(info_group)
        
        # 状态信息组
        status_group = QGroupBox("状态信息")
        status_layout = QFormLayout(status_group)
        
        self.size_label = QLabel("N/A")
        status_layout.addRow("文件大小:", self.size_label)
        
        self.version_label = QLabel("N/A")
        status_layout.addRow("数据库版本:", self.version_label)
        
        self.last_accessed_label = QLabel("N/A")
        status_layout.addRow("最后访问:", self.last_accessed_label)
        
        self.status_label = QLabel("N/A")
        status_layout.addRow("状态:", self.status_label)
        
        layout.addWidget(status_group)
        
        # 操作按钮组
        operations_group = QGroupBox("操作")
        operations_layout = QGridLayout(operations_group)
        
        self.set_current_button = QPushButton("设为当前")
        self.set_current_button.setEnabled(False)
        operations_layout.addWidget(self.set_current_button, 0, 0)
        
        self.rename_button = QPushButton("重命名")
        self.rename_button.setEnabled(False)
        operations_layout.addWidget(self.rename_button, 0, 1)
        
        self.move_button = QPushButton("移动")
        self.move_button.setEnabled(False)
        operations_layout.addWidget(self.move_button, 1, 0)
        
        self.duplicate_button = QPushButton("复制")
        self.duplicate_button.setEnabled(False)
        operations_layout.addWidget(self.duplicate_button, 1, 1)
        
        layout.addWidget(operations_group)
        
        layout.addStretch()
        
        return widget
    
    def _setup_connections(self):
        """设置信号连接"""
        # 列表选择
        self.database_list.currentItemChanged.connect(self._on_database_selected)
        
        # 按钮连接
        self.new_database_button.clicked.connect(self._create_new_database)
        self.import_database_button.clicked.connect(self._import_database)
        self.refresh_button.clicked.connect(self._refresh_database_list)
        self.remove_button.clicked.connect(self._remove_database)
        
        # 操作按钮
        self.set_current_button.clicked.connect(self._set_current_database)
        self.rename_button.clicked.connect(self._rename_database)
        self.move_button.clicked.connect(self._move_database)
        self.duplicate_button.clicked.connect(self._duplicate_database)
        
        # 信息编辑
        self.name_edit.textChanged.connect(self._on_info_changed)
        self.description_edit.textChanged.connect(self._on_info_changed)
        
        # 对话框按钮
        self.button_box.accepted.connect(self._apply_changes)
        self.button_box.rejected.connect(self.reject)
    
    def _load_database_list(self):
        """加载数据库列表"""
        self.database_list.clear()
        
        for db_info in self.config_manager.databases:
            item = QListWidgetItem()
            
            # 设置显示文本
            display_text = db_info.name
            if db_info == self.config_manager.current_database:
                display_text += " (当前)"
            
            item.setText(display_text)
            item.setData(Qt.UserRole, db_info.path)
            
            # 设置图标和颜色
            if not db_info.is_valid:
                item.setForeground(Qt.red)
                display_text += " [无效]"
                item.setText(display_text)
            elif not os.path.exists(db_info.path):
                item.setForeground(Qt.gray)
                display_text += " [不存在]"
                item.setText(display_text)
            
            self.database_list.addItem(item)
        
        # 选择当前数据库
        if self.config_manager.current_database:
            for i in range(self.database_list.count()):
                item = self.database_list.item(i)
                if item.data(Qt.UserRole) == self.config_manager.current_database.path:
                    self.database_list.setCurrentItem(item)
                    break
    
    def _on_database_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """数据库选择改变"""
        if current:
            path = current.data(Qt.UserRole)
            db_info = self.config_manager.get_database_by_path(path)
            
            if db_info:
                self._update_database_details(db_info)
                self._enable_operation_buttons(True)
            else:
                self._clear_database_details()
                self._enable_operation_buttons(False)
        else:
            self._clear_database_details()
            self._enable_operation_buttons(False)
    
    def _update_database_details(self, db_info: DatabaseInfo):
        """更新数据库详情显示"""
        self.name_edit.setText(db_info.name)
        self.path_label.setText(db_info.path)
        self.description_edit.setPlainText(db_info.description)
        
        # 更新状态信息
        if db_info.file_size > 0:
            size_mb = db_info.file_size / 1024 / 1024
            self.size_label.setText(f"{size_mb:.2f} MB ({db_info.file_size:,} 字节)")
        else:
            self.size_label.setText("N/A")
        
        self.version_label.setText(str(db_info.version) if db_info.version else "N/A")
        
        if db_info.last_accessed:
            self.last_accessed_label.setText(db_info.last_accessed.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            self.last_accessed_label.setText("N/A")
        
        # 状态
        if not os.path.exists(db_info.path):
            self.status_label.setText("文件不存在")
            self.status_label.setStyleSheet("color: red;")
        elif not db_info.is_valid:
            self.status_label.setText("数据库无效")
            self.status_label.setStyleSheet("color: orange;")
        else:
            self.status_label.setText("正常")
            self.status_label.setStyleSheet("color: green;")
    
    def _clear_database_details(self):
        """清空数据库详情显示"""
        self.name_edit.clear()
        self.path_label.setText("未选择")
        self.path_label.setStyleSheet("color: gray;")
        self.description_edit.clear()
        
        self.size_label.setText("N/A")
        self.version_label.setText("N/A")
        self.last_accessed_label.setText("N/A")
        self.status_label.setText("N/A")
        self.status_label.setStyleSheet("")
    
    def _enable_operation_buttons(self, enabled: bool):
        """启用/禁用操作按钮"""
        self.remove_button.setEnabled(enabled)
        self.set_current_button.setEnabled(enabled)
        self.rename_button.setEnabled(enabled)
        self.move_button.setEnabled(enabled)
        self.duplicate_button.setEnabled(enabled)
    
    def _on_info_changed(self):
        """信息改变"""
        current_item = self.database_list.currentItem()
        if current_item:
            path = current_item.data(Qt.UserRole)
            name = self.name_edit.text()
            description = self.description_edit.toPlainText()
            
            # 更新配置
            self.config_manager.update_database_info(path, name, description)
            
            # 更新列表显示
            display_text = name
            if path == self.config_manager.current_database.path:
                display_text += " (当前)"
            current_item.setText(display_text)    
  
  def _create_new_database(self):
        """创建新数据库"""
        wizard = DatabaseCreationWizard(self)
        wizard.database_created.connect(self._on_database_created)
        wizard.exec_()
    
    def _on_database_created(self, path: str, name: str, description: str):
        """数据库创建完成"""
        # 添加到配置
        db_info = self.config_manager.add_database(path, name, description)
        
        # 刷新列表
        self._load_database_list()
        
        # 选择新创建的数据库
        for i in range(self.database_list.count()):
            item = self.database_list.item(i)
            if item.data(Qt.UserRole) == path:
                self.database_list.setCurrentItem(item)
                break
    
    def _import_database(self):
        """导入现有数据库"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择要导入的数据库文件",
            "",
            "SQLite数据库文件 (*.db);;所有文件 (*)"
        )
        
        if file_path:
            # 检查是否已存在
            if self.config_manager.get_database_by_path(file_path):
                QMessageBox.information(self, "提示", "该数据库已在列表中")
                return
            
            # 获取数据库信息
            name = os.path.splitext(os.path.basename(file_path))[0]
            
            # 添加到配置
            db_info = self.config_manager.add_database(file_path, name)
            
            # 刷新列表
            self._load_database_list()
            
            # 选择导入的数据库
            for i in range(self.database_list.count()):
                item = self.database_list.item(i)
                if item.data(Qt.UserRole) == file_path:
                    self.database_list.setCurrentItem(item)
                    break
            
            QMessageBox.information(self, "成功", f"数据库导入成功: {name}")
    
    def _refresh_database_list(self):
        """刷新数据库列表"""
        # 刷新所有数据库信息
        self.config_manager.refresh_all_databases()
        
        # 重新加载列表
        current_path = None
        current_item = self.database_list.currentItem()
        if current_item:
            current_path = current_item.data(Qt.UserRole)
        
        self._load_database_list()
        
        # 恢复选择
        if current_path:
            for i in range(self.database_list.count()):
                item = self.database_list.item(i)
                if item.data(Qt.UserRole) == current_path:
                    self.database_list.setCurrentItem(item)
                    break
    
    def _remove_database(self):
        """移除数据库"""
        current_item = self.database_list.currentItem()
        if not current_item:
            return
        
        path = current_item.data(Qt.UserRole)
        db_info = self.config_manager.get_database_by_path(path)
        
        if not db_info:
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认移除",
            f"确定要从列表中移除数据库 '{db_info.name}' 吗？\n\n注意：这只会从列表中移除，不会删除实际文件。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 如果是当前数据库，需要特殊处理
            if db_info == self.config_manager.current_database:
                if len(self.config_manager.databases) <= 1:
                    QMessageBox.warning(self, "警告", "不能移除唯一的数据库")
                    return
                
                reply2 = QMessageBox.question(
                    self,
                    "确认移除当前数据库",
                    "这是当前使用的数据库，移除后将自动切换到其他数据库。确定继续吗？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply2 != QMessageBox.Yes:
                    return
            
            # 移除数据库
            if self.config_manager.remove_database(path):
                self._load_database_list()
                QMessageBox.information(self, "成功", "数据库已从列表中移除")
    
    def _set_current_database(self):
        """设置当前数据库"""
        current_item = self.database_list.currentItem()
        if not current_item:
            return
        
        path = current_item.data(Qt.UserRole)
        db_info = self.config_manager.get_database_by_path(path)
        
        if not db_info:
            return
        
        if db_info == self.config_manager.current_database:
            QMessageBox.information(self, "提示", "该数据库已经是当前数据库")
            return
        
        # 检查数据库是否有效
        if not os.path.exists(path):
            QMessageBox.warning(self, "错误", "数据库文件不存在，无法设置为当前数据库")
            return
        
        if not db_info.is_valid:
            QMessageBox.warning(self, "错误", "数据库无效，无法设置为当前数据库")
            return
        
        # 设置为当前数据库
        if self.config_manager.set_current_database(path):
            self._load_database_list()
            self.database_changed.emit(
                self.config_manager.current_database.path if self.config_manager.current_database else "",
                path
            )
            QMessageBox.information(self, "成功", f"已切换到数据库: {db_info.name}")
    
    def _rename_database(self):
        """重命名数据库文件"""
        current_item = self.database_list.currentItem()
        if not current_item:
            return
        
        path = current_item.data(Qt.UserRole)
        db_info = self.config_manager.get_database_by_path(path)
        
        if not db_info:
            return
        
        if not os.path.exists(path):
            QMessageBox.warning(self, "错误", "数据库文件不存在，无法重命名")
            return
        
        # 获取新文件名
        old_name = os.path.basename(path)
        new_name, ok = QMessageBox.getText(
            self,
            "重命名数据库文件",
            "请输入新的文件名:",
            text=old_name
        )
        
        if ok and new_name and new_name != old_name:
            try:
                # 构建新路径
                new_path = os.path.join(os.path.dirname(path), new_name)
                
                # 检查新文件是否已存在
                if os.path.exists(new_path):
                    QMessageBox.warning(self, "错误", "目标文件已存在")
                    return
                
                # 重命名文件
                os.rename(path, new_path)
                
                # 更新配置
                self.config_manager.remove_database(path)
                new_db_info = self.config_manager.add_database(new_path, db_info.name, db_info.description)
                
                # 如果是当前数据库，更新当前数据库
                if db_info == self.config_manager.current_database:
                    self.config_manager.set_current_database(new_path)
                
                # 刷新列表
                self._load_database_list()
                
                # 选择重命名后的数据库
                for i in range(self.database_list.count()):
                    item = self.database_list.item(i)
                    if item.data(Qt.UserRole) == new_path:
                        self.database_list.setCurrentItem(item)
                        break
                
                QMessageBox.information(self, "成功", "数据库文件重命名成功")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重命名失败: {str(e)}")
    
    def _move_database(self):
        """移动数据库文件"""
        current_item = self.database_list.currentItem()
        if not current_item:
            return
        
        path = current_item.data(Qt.UserRole)
        db_info = self.config_manager.get_database_by_path(path)
        
        if not db_info:
            return
        
        if not os.path.exists(path):
            QMessageBox.warning(self, "错误", "数据库文件不存在，无法移动")
            return
        
        # 选择新位置
        new_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择新的数据库位置",
            os.path.basename(path),
            "SQLite数据库文件 (*.db);;所有文件 (*)"
        )
        
        if new_path and new_path != path:
            try:
                # 确保目录存在
                ensure_storage_dir(os.path.dirname(new_path))
                
                # 移动文件
                shutil.move(path, new_path)
                
                # 更新配置
                self.config_manager.remove_database(path)
                new_db_info = self.config_manager.add_database(new_path, db_info.name, db_info.description)
                
                # 如果是当前数据库，更新当前数据库
                if db_info == self.config_manager.current_database:
                    self.config_manager.set_current_database(new_path)
                
                # 刷新列表
                self._load_database_list()
                
                # 选择移动后的数据库
                for i in range(self.database_list.count()):
                    item = self.database_list.item(i)
                    if item.data(Qt.UserRole) == new_path:
                        self.database_list.setCurrentItem(item)
                        break
                
                QMessageBox.information(self, "成功", f"数据库已移动到: {new_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"移动失败: {str(e)}")
    
    def _duplicate_database(self):
        """复制数据库"""
        current_item = self.database_list.currentItem()
        if not current_item:
            return
        
        path = current_item.data(Qt.UserRole)
        db_info = self.config_manager.get_database_by_path(path)
        
        if not db_info:
            return
        
        if not os.path.exists(path):
            QMessageBox.warning(self, "错误", "数据库文件不存在，无法复制")
            return
        
        # 选择复制位置
        base_name = os.path.splitext(os.path.basename(path))[0]
        default_name = f"{base_name}_copy.db"
        
        new_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择复制位置",
            default_name,
            "SQLite数据库文件 (*.db);;所有文件 (*)"
        )
        
        if new_path:
            try:
                # 确保目录存在
                ensure_storage_dir(os.path.dirname(new_path))
                
                # 复制文件
                shutil.copy2(path, new_path)
                
                # 添加到配置
                copy_name = f"{db_info.name} (副本)"
                copy_description = f"{db_info.description}\n\n复制自: {path}"
                
                new_db_info = self.config_manager.add_database(new_path, copy_name, copy_description)
                
                # 刷新列表
                self._load_database_list()
                
                # 选择复制的数据库
                for i in range(self.database_list.count()):
                    item = self.database_list.item(i)
                    if item.data(Qt.UserRole) == new_path:
                        self.database_list.setCurrentItem(item)
                        break
                
                QMessageBox.information(self, "成功", f"数据库已复制到: {new_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"复制失败: {str(e)}")
    
    def _apply_changes(self):
        """应用更改"""
        # 发出当前选择的数据库信号
        current_item = self.database_list.currentItem()
        if current_item:
            path = current_item.data(Qt.UserRole)
            self.database_selected.emit(path)
        
        self.accept()
    
    def get_current_database_path(self) -> str:
        """获取当前数据库路径"""
        return self.config_manager.current_database.path if self.config_manager.current_database else ""
    
    def get_database_config_manager(self) -> DatabaseConfigManager:
        """获取数据库配置管理器"""
        return self.config_manager