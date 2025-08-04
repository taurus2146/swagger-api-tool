#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库切换服务
负责运行时数据库切换、数据保存确认和切换状态管理
"""

import os
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from .database_config_manager import DatabaseConfigManager, DatabaseConfig
from .database_manager import DatabaseManager
from .project_manager import ProjectManager

logger = logging.getLogger(__name__)


class DatabaseSwitchResult:
    """数据库切换结果"""
    
    def __init__(self, success: bool, message: str = "", 
                 old_config: DatabaseConfig = None, 
                 new_config: DatabaseConfig = None):
        self.success = success
        self.message = message
        self.old_config = old_config
        self.new_config = new_config
        self.timestamp = datetime.now().isoformat()


class DatabaseSwitcher:
    """数据库切换服务"""
    
    def __init__(self, config_manager: DatabaseConfigManager, 
                 database_manager: DatabaseManager,
                 project_manager: ProjectManager = None):
        """
        初始化数据库切换服务
        
        Args:
            config_manager: 数据库配置管理器
            database_manager: 数据库管理器
            project_manager: 项目管理器（可选）
        """
        self.config_manager = config_manager
        self.database_manager = database_manager
        self.project_manager = project_manager
        
        # 当前活动的数据库配置
        self._current_config: Optional[DatabaseConfig] = None
        
        # 切换前确认回调
        self._pre_switch_callback: Optional[Callable[[DatabaseConfig, DatabaseConfig], bool]] = None
        
        # 切换后通知回调
        self._post_switch_callback: Optional[Callable[DatabaseSwitchResult], None] = None
        
        # 数据保存回调
        self._save_data_callback: Optional[Callable[[], bool]] = None
        
        # 初始化当前配置
        self._initialize_current_config()
    
    def _initialize_current_config(self):
        """初始化当前配置"""
        try:
            # 获取默认配置作为当前配置
            default_config = self.config_manager.get_default_config()
            if default_config:
                self._current_config = default_config
                logger.info(f"初始化当前数据库配置: {default_config.name}")
            else:
                logger.warning("没有找到默认数据库配置")
        except Exception as e:
            logger.error(f"初始化当前配置失败: {e}")
    
    def get_current_config(self) -> Optional[DatabaseConfig]:
        """
        获取当前数据库配置
        
        Returns:
            Optional[DatabaseConfig]: 当前配置
        """
        return self._current_config
    
    def set_pre_switch_callback(self, callback: Callable[[DatabaseConfig, DatabaseConfig], bool]):
        """
        设置切换前确认回调
        
        Args:
            callback: 回调函数，参数为(old_config, new_config)，返回是否允许切换
        """
        self._pre_switch_callback = callback
    
    def set_post_switch_callback(self, callback: Callable[[DatabaseSwitchResult], None]):
        """
        设置切换后通知回调
        
        Args:
            callback: 回调函数，参数为切换结果
        """
        self._post_switch_callback = callback
    
    def set_save_data_callback(self, callback: Callable[[], bool]):
        """
        设置数据保存回调
        
        Args:
            callback: 回调函数，返回保存是否成功
        """
        self._save_data_callback = callback
    
    def switch_to_config(self, config_id: str, force: bool = False) -> DatabaseSwitchResult:
        """
        切换到指定配置的数据库
        
        Args:
            config_id: 目标配置ID
            force: 是否强制切换（跳过确认）
            
        Returns:
            DatabaseSwitchResult: 切换结果
        """
        try:
            # 获取目标配置
            target_config = self.config_manager.get_config(config_id)
            if not target_config:
                return DatabaseSwitchResult(
                    success=False,
                    message=f"配置 {config_id} 不存在"
                )
            
            # 检查是否已经是当前配置
            if self._current_config and self._current_config.id == config_id:
                return DatabaseSwitchResult(
                    success=True,
                    message="已经是当前数据库",
                    old_config=self._current_config,
                    new_config=target_config
                )
            
            old_config = self._current_config
            
            # 切换前确认
            if not force and self._pre_switch_callback:
                if not self._pre_switch_callback(old_config, target_config):
                    return DatabaseSwitchResult(
                        success=False,
                        message="用户取消切换",
                        old_config=old_config,
                        new_config=target_config
                    )
            
            # 保存当前数据
            if self._save_data_callback:
                if not self._save_data_callback():
                    return DatabaseSwitchResult(
                        success=False,
                        message="保存当前数据失败",
                        old_config=old_config,
                        new_config=target_config
                    )
            
            # 断开当前数据库连接
            if old_config:
                try:
                    self.database_manager.disconnect()
                    logger.info(f"断开数据库连接: {old_config.name}")
                except Exception as e:
                    logger.warning(f"断开数据库连接失败: {e}")
            
            # 连接到新数据库
            connection_start_time = datetime.now()
            try:
                # 更新数据库管理器的路径
                self.database_manager.db_path = target_config.path
                
                # 尝试连接
                if not self.database_manager.connect():
                    return DatabaseSwitchResult(
                        success=False,
                        message=f"连接到数据库失败: {target_config.path}",
                        old_config=old_config,
                        new_config=target_config
                    )
                
                # 计算连接时长
                connection_duration = (datetime.now() - connection_start_time).total_seconds()
                
                # 更新当前配置
                self._current_config = target_config
                
                # 记录连接历史
                self.config_manager.add_connection_history(
                    config_id=target_config.id,
                    success=True,
                    duration=connection_duration
                )
                
                # 设置为默认配置（可选）
                self.config_manager.set_default_config(target_config.id)
                
                # 创建成功结果
                result = DatabaseSwitchResult(
                    success=True,
                    message=f"成功切换到数据库: {target_config.name}",
                    old_config=old_config,
                    new_config=target_config
                )
                
                # 切换后通知
                if self._post_switch_callback:
                    self._post_switch_callback(result)
                
                logger.info(f"成功切换数据库: {old_config.name if old_config else 'None'} -> {target_config.name}")
                return result
                
            except Exception as e:
                # 记录连接失败历史
                connection_duration = (datetime.now() - connection_start_time).total_seconds()
                self.config_manager.add_connection_history(
                    config_id=target_config.id,
                    success=False,
                    duration=connection_duration,
                    error_message=str(e)
                )
                
                # 尝试恢复到原数据库
                if old_config:
                    try:
                        self.database_manager.db_path = old_config.path
                        self.database_manager.connect()
                        self._current_config = old_config
                        logger.info(f"已恢复到原数据库: {old_config.name}")
                    except Exception as restore_error:
                        logger.error(f"恢复到原数据库失败: {restore_error}")
                
                return DatabaseSwitchResult(
                    success=False,
                    message=f"连接数据库时发生错误: {str(e)}",
                    old_config=old_config,
                    new_config=target_config
                )
                
        except Exception as e:
            logger.error(f"切换数据库时发生异常: {e}")
            return DatabaseSwitchResult(
                success=False,
                message=f"切换过程中发生异常: {str(e)}"
            )
    
    def switch_to_path(self, db_path: str, force: bool = False) -> DatabaseSwitchResult:
        """
        切换到指定路径的数据库
        
        Args:
            db_path: 数据库文件路径
            force: 是否强制切换
            
        Returns:
            DatabaseSwitchResult: 切换结果
        """
        # 查找对应的配置
        config = self.config_manager.get_config_by_path(db_path)
        if config:
            return self.switch_to_config(config.id, force)
        else:
            # 如果没有配置，创建临时配置
            try:
                config_id = self.config_manager.add_config(
                    name=f"临时数据库_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    path=db_path,
                    description="通过路径切换创建的临时配置",
                    tags=["临时"]
                )
                return self.switch_to_config(config_id, force)
            except Exception as e:
                return DatabaseSwitchResult(
                    success=False,
                    message=f"创建临时配置失败: {str(e)}"
                )
    
    def get_available_configs(self) -> list[DatabaseConfig]:
        """
        获取可用的数据库配置列表
        
        Returns:
            list[DatabaseConfig]: 配置列表
        """
        return self.config_manager.get_all_configs()
    
    def get_recent_configs(self, limit: int = 5) -> list[DatabaseConfig]:
        """
        获取最近使用的数据库配置
        
        Args:
            limit: 返回数量限制
            
        Returns:
            list[DatabaseConfig]: 最近使用的配置列表
        """
        all_configs = self.config_manager.get_all_configs()
        # 按最后访问时间排序
        all_configs.sort(key=lambda x: x.last_accessed, reverse=True)
        return all_configs[:limit]
    
    def validate_config(self, config_id: str) -> Dict[str, Any]:
        """
        验证数据库配置
        
        Args:
            config_id: 配置ID
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        config = self.config_manager.get_config(config_id)
        if not config:
            return {
                'valid': False,
                'message': '配置不存在',
                'details': {}
            }
        
        result = {
            'valid': True,
            'message': '配置有效',
            'details': {
                'file_exists': config.exists,
                'file_size': config.file_size,
                'path': config.path,
                'last_accessed': config.last_accessed
            }
        }
        
        # 检查文件是否存在
        if not config.exists:
            result['valid'] = False
            result['message'] = '数据库文件不存在'
        
        # 检查文件是否可读
        try:
            if config.exists and not os.access(config.path, os.R_OK):
                result['valid'] = False
                result['message'] = '数据库文件无法读取'
        except Exception as e:
            result['valid'] = False
            result['message'] = f'检查文件权限时出错: {str(e)}'
        
        return result
    
    def create_quick_switch_menu_data(self) -> Dict[str, Any]:
        """
        创建快速切换菜单数据
        
        Returns:
            Dict[str, Any]: 菜单数据
        """
        current_config = self.get_current_config()
        recent_configs = self.get_recent_configs(5)
        all_configs = self.get_available_configs()
        
        return {
            'current': {
                'id': current_config.id if current_config else None,
                'name': current_config.name if current_config else '无',
                'path': current_config.path if current_config else ''
            },
            'recent': [
                {
                    'id': config.id,
                    'name': config.name,
                    'path': config.path,
                    'last_accessed': config.last_accessed,
                    'is_current': current_config and config.id == current_config.id,
                    'exists': config.exists
                }
                for config in recent_configs
            ],
            'all': [
                {
                    'id': config.id,
                    'name': config.name,
                    'path': config.path,
                    'description': config.description,
                    'is_current': current_config and config.id == current_config.id,
                    'is_default': config.is_default,
                    'exists': config.exists,
                    'tags': config.tags
                }
                for config in all_configs
            ]
        }
    
    def get_switch_statistics(self) -> Dict[str, Any]:
        """
        获取切换统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        current_config = self.get_current_config()
        all_configs = self.get_available_configs()
        
        # 计算连接历史统计
        total_connections = 0
        successful_connections = 0
        
        for config in all_configs:
            history = self.config_manager.get_connection_history(config.id)
            total_connections += len(history)
            successful_connections += sum(1 for h in history if h.success)
        
        success_rate = (successful_connections / total_connections * 100) if total_connections > 0 else 0
        
        return {
            'current_database': current_config.name if current_config else '无',
            'total_databases': len(all_configs),
            'available_databases': sum(1 for config in all_configs if config.exists),
            'total_connections': total_connections,
            'success_rate': success_rate,
            'most_used': max(all_configs, key=lambda x: x.connection_count).name if all_configs else '无'
        }