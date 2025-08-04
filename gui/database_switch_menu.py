#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
快速数据库切换菜单
提供快速切换数据库的菜单组件
"""

import logging
from typing import Optional, Callable
from datetime import datetime

from PyQt5.QtWidgets import (
    QMenu, QAction, QActionGroup, QMessageBox, QWidget
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QFont

from core.database_config_manager import DatabaseConfigManager, DatabaseConfig
from core.database_switcher import DatabaseSwitcher, DatabaseSwitchResult

logger = logging.getLogger(__name__)


class DatabaseSwitchMenu(QMenu):
    """快速数据库切换菜单"""
    
    # 信号
    database_switched = pyqtSignal(str)  # 数据库切换信号
    show_database_list = pyqtSignal()    # 显示数据库列表信号
    
    def __init__(self, config_manager: DatabaseConfigManager,
                 database_switcher: DatabaseSwitcher, parent: QWidget = None):
        """
        初始化菜单
        
        Args:
            config_manager: 数据库配置管理器
            database_switcher: 数据库切换服务
            parent: 父组件
        """
        super().__init__("数据库", parent)
        self.config_manager = config_manager
        self.database_switcher = database_switcher
        
        # 动作组（用于单选）
        self.database_action_group = QActionGroup(self)
        self.database_action_group.setExclusive(True)
        
        # 设置切换回调
        self.database_switcher.set_post_switch_callback(self._on_database_switched)
        
        # 初始化菜单
        self._init_menu()
        
        # 设置定时器定期更新菜单
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_menu)
        self._update_timer.start(10000)  # 每10秒更新一次
    
    def _init_menu(self):
        """初始化菜单"""
        self._update_menu()
    
    def _update_menu(self):
        """更新菜单内容"""
        try:
            # 清空现有菜单
            self.clear()
            
            # 清空动作组
            for action in self.database_action_group.actions():
                self.database_action_group.removeAction(action)
            
            # 获取菜单数据
            menu_data = self.database_switcher.create_quick_switch_menu_data()
            current_config_id = menu_data['current']['id']
            
            # 当前数据库信息
            current_action = QAction(f"当前: {menu_data['current']['name']}", self)
            current_action.setEnabled(False)
            current_font = QFont()
            current_font.setBold(True)
            current_action.setFont(current_font)
            self.addAction(current_action)
            
            self.addSeparator()
            
            # 最近使用的数据库
            if menu_data['recent']:
                recent_menu = self.addMenu("最近使用")
                
                for db_info in menu_data['recent'][:5]:  # 最多显示5个
                    action = QAction(db_info['name'], self)
                    action.setCheckable(True)
                    action.setChecked(db_info['is_current'])
                    action.setEnabled(db_info['exists'])
                    
                    if not db_info['exists']:
                        action.setText(f"{db_info['name']} (缺失)")
                        action.setToolTip(f"数据库文件不存在: {db_info['path']}")
                    else:
                        # 显示最后访问时间
                        try:
                            last_accessed = datetime.fromisoformat(db_info['last_accessed'])
                            time_str = last_accessed.strftime("%m-%d %H:%M")
                            action.setToolTip(f"路径: {db_info['path']}\n最后访问: {time_str}")
                        except:
                            action.setToolTip(f"路径: {db_info['path']}")
                    
                    action.setData(db_info['id'])
                    action.triggered.connect(lambda checked, config_id=db_info['id']: 
                                           self._switch_database(config_id))
                    
                    self.database_action_group.addAction(action)
                    recent_menu.addAction(action)
                
                self.addSeparator()
            
            # 所有数据库
            all_menu = self.addMenu("所有数据库")
            
            # 按类别分组
            default_configs = []
            normal_configs = []
            
            for db_info in menu_data['all']:
                if db_info['is_default']:
                    default_configs.append(db_info)
                else:
                    normal_configs.append(db_info)
            
            # 添加默认数据库
            if default_configs:
                for db_info in default_configs:
                    action = self._create_database_action(db_info, current_config_id)
                    all_menu.addAction(action)
                
                if normal_configs:
                    all_menu.addSeparator()
            
            # 添加其他数据库
            for db_info in normal_configs:
                action = self._create_database_action(db_info, current_config_id)
                all_menu.addAction(action)
            
            self.addSeparator()
            
            # 管理功能
            manage_action = QAction("管理数据库...", self)
            manage_action.triggered.connect(self.show_database_list.emit)
            self.addAction(manage_action)
            
            # 刷新菜单
            refresh_action = QAction("刷新", self)
            refresh_action.triggered.connect(self._update_menu)
            self.addAction(refresh_action)
            
            logger.debug("数据库切换菜单已更新")
            
        except Exception as e:
            logger.error(f"更新数据库切换菜单失败: {e}")
    
    def _create_database_action(self, db_info: dict, current_config_id: str) -> QAction:
        """
        创建数据库动作
        
        Args:
            db_info: 数据库信息
            current_config_id: 当前配置ID
            
        Returns:
            QAction: 数据库动作
        """
        # 构建显示名称
        display_name = db_info['name']
        if db_info['is_default']:
            display_name += " (默认)"
        if not db_info['exists']:
            display_name += " (缺失)"
        
        action = QAction(display_name, self)
        action.setCheckable(True)
        action.setChecked(db_info['is_current'])
        action.setEnabled(db_info['exists'])
        action.setData(db_info['id'])
        
        # 设置工具提示
        tooltip_lines = [
            f"路径: {db_info['path']}",
            f"描述: {db_info['description'] or '无'}"
        ]
        
        if db_info['tags']:
            tooltip_lines.append(f"标签: {', '.join(db_info['tags'])}")
        
        if not db_info['exists']:
            tooltip_lines.append("⚠️ 数据库文件不存在")
        
        action.setToolTip("\n".join(tooltip_lines))
        
        # 连接信号
        action.triggered.connect(lambda checked, config_id=db_info['id']: 
                               self._switch_database(config_id))
        
        # 添加到动作组
        self.database_action_group.addAction(action)
        
        return action
    
    def _switch_database(self, config_id: str):
        """
        切换数据库
        
        Args:
            config_id: 配置ID
        """
        try:
            # 获取配置信息
            config = self.config_manager.get_config(config_id)
            if not config:
                QMessageBox.warning(self.parent(), "错误", "数据库配置不存在")
                return
            
            # 检查文件是否存在
            if not config.exists:
                QMessageBox.warning(
                    self.parent(), "警告", 
                    f"数据库文件不存在:\n{config.path}\n\n请检查文件路径是否正确。"
                )
                return
            
            # 执行切换
            result = self.database_switcher.switch_to_config(config_id)
            
            if result.success:
                # 发射切换成功信号
                self.database_switched.emit(config_id)
                
                # 显示成功消息（可选）
                if self.parent():
                    # 可以在状态栏显示消息，而不是弹窗
                    pass
            else:
                QMessageBox.warning(self.parent(), "切换失败", result.message)
                
                # 恢复之前的选择
                self._update_menu()
        
        except Exception as e:
            logger.error(f"切换数据库时发生异常: {e}")
            QMessageBox.critical(
                self.parent(), "错误", 
                f"切换数据库时发生异常:\n{str(e)}"
            )
            
            # 恢复之前的选择
            self._update_menu()
    
    def _on_database_switched(self, result: DatabaseSwitchResult):
        """数据库切换后的回调"""
        if result.success:
            # 更新菜单以反映新的当前数据库
            self._update_menu()
            logger.info(f"数据库切换成功: {result.message}")
        else:
            logger.warning(f"数据库切换失败: {result.message}")
    
    def get_current_database_info(self) -> dict:
        """
        获取当前数据库信息
        
        Returns:
            dict: 当前数据库信息
        """
        current_config = self.database_switcher.get_current_config()
        if current_config:
            return {
                'id': current_config.id,
                'name': current_config.name,
                'path': current_config.path,
                'exists': current_config.exists,
                'size_mb': current_config.size_mb
            }
        else:
            return {
                'id': None,
                'name': '无',
                'path': '',
                'exists': False,
                'size_mb': 0.0
            }
    
    def refresh(self):
        """刷新菜单"""
        self._update_menu()
    
    def cleanup(self):
        """清理资源"""
        if self._update_timer:
            self._update_timer.stop()
            self._update_timer = None


class DatabaseSwitchToolButton:
    """数据库切换工具按钮（可以添加到工具栏）"""
    
    def __init__(self, config_manager: DatabaseConfigManager,
                 database_switcher: DatabaseSwitcher, parent: QWidget = None):
        """
        初始化工具按钮
        
        Args:
            config_manager: 数据库配置管理器
            database_switcher: 数据库切换服务
            parent: 父组件
        """
        from PyQt5.QtWidgets import QToolButton
        
        self.config_manager = config_manager
        self.database_switcher = database_switcher
        
        # 创建工具按钮
        self.button = QToolButton(parent)
        self.button.setText("数据库")
        self.button.setToolTip("切换数据库")
        self.button.setPopupMode(QToolButton.InstantPopup)
        
        # 创建菜单
        self.menu = DatabaseSwitchMenu(config_manager, database_switcher, parent)
        self.button.setMenu(self.menu)
        
        # 连接信号
        self.menu.database_switched.connect(self._on_database_switched)
        
        # 更新按钮文本
        self._update_button_text()
    
    def _update_button_text(self):
        """更新按钮文本"""
        current_config = self.database_switcher.get_current_config()
        if current_config:
            # 显示当前数据库名称（截断长名称）
            name = current_config.name
            if len(name) > 15:
                name = name[:12] + "..."
            self.button.setText(f"DB: {name}")
            self.button.setToolTip(f"当前数据库: {current_config.name}\n路径: {current_config.path}")
        else:
            self.button.setText("数据库")
            self.button.setToolTip("选择数据库")
    
    def _on_database_switched(self, config_id: str):
        """数据库切换后更新按钮"""
        self._update_button_text()
    
    def get_button(self):
        """获取工具按钮组件"""
        return self.button
    
    def get_menu(self):
        """获取菜单组件"""
        return self.menu