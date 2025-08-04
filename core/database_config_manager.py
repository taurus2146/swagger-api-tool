#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库配置管理器
负责多数据库配置的存储、加载、历史记录管理和默认设置
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

from .storage_utils import get_default_storage_path, get_default_database_path

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """数据库配置"""
    id: str  # 配置唯一标识
    name: str  # 显示名称
    path: str  # 数据库文件路径
    description: str = ""  # 描述信息
    created_at: str = ""  # 创建时间
    last_accessed: str = ""  # 最后访问时间
    is_default: bool = False  # 是否为默认数据库
    connection_count: int = 0  # 连接次数
    file_size: int = 0  # 文件大小（字节）
    version: Optional[int] = None  # 数据库版本
    tags: List[str] = None  # 标签
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_accessed:
            self.last_accessed = self.created_at
    
    @property
    def exists(self) -> bool:
        """检查数据库文件是否存在"""
        return os.path.exists(self.path)
    
    @property
    def size_mb(self) -> float:
        """获取文件大小（MB）"""
        return self.file_size / 1024 / 1024 if self.file_size > 0 else 0.0
    
    def update_file_info(self):
        """更新文件信息"""
        if self.exists:
            try:
                stat = os.stat(self.path)
                self.file_size = stat.st_size
            except Exception as e:
                logger.warning(f"更新文件信息失败 {self.path}: {e}")
                self.file_size = 0
        else:
            self.file_size = 0
    
    def update_access_time(self):
        """更新访问时间"""
        self.last_accessed = datetime.now().isoformat()
        self.connection_count += 1


@dataclass
class ConnectionHistory:
    """连接历史记录"""
    database_id: str
    database_name: str
    database_path: str
    connected_at: str
    duration: float = 0.0  # 连接持续时间（秒）
    success: bool = True
    error_message: str = ""
    
    def __post_init__(self):
        if not self.connected_at:
            self.connected_at = datetime.now().isoformat()


class DatabaseConfigManager:
    """数据库配置管理器"""
    
    CONFIG_FILE = "database_configs.json"
    HISTORY_FILE = "connection_history.json"
    MAX_HISTORY_RECORDS = 1000  # 最大历史记录数
    
    def __init__(self, config_dir: str = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，默认使用应用数据目录
        """
        self.config_dir = config_dir or get_default_storage_path()
        self.config_file = os.path.join(self.config_dir, self.CONFIG_FILE)
        self.history_file = os.path.join(self.config_dir, self.HISTORY_FILE)
        
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 加载配置
        self._configs: Dict[str, DatabaseConfig] = {}
        self._history: List[ConnectionHistory] = []
        self._load_configs()
        self._load_history()
        
        # 确保有默认配置
        self._ensure_default_config()
    
    def _load_configs(self):
        """加载数据库配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._configs = {}
                for config_data in data.get('configs', []):
                    config = DatabaseConfig(**config_data)
                    self._configs[config.id] = config
                
                logger.info(f"加载了 {len(self._configs)} 个数据库配置")
            else:
                logger.info("配置文件不存在，将创建新的配置")
                
        except Exception as e:
            logger.error(f"加载数据库配置失败: {e}")
            self._configs = {}
    
    def _save_configs(self):
        """保存数据库配置"""
        try:
            # 更新文件信息
            for config in self._configs.values():
                config.update_file_info()
            
            data = {
                'version': '1.0',
                'updated_at': datetime.now().isoformat(),
                'configs': [asdict(config) for config in self._configs.values()]
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"保存了 {len(self._configs)} 个数据库配置")
            
        except Exception as e:
            logger.error(f"保存数据库配置失败: {e}")
            raise
    
    def _load_history(self):
        """加载连接历史"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._history = []
                for history_data in data.get('history', []):
                    history = ConnectionHistory(**history_data)
                    self._history.append(history)
                
                # 按时间排序（最新的在前）
                self._history.sort(key=lambda x: x.connected_at, reverse=True)
                
                logger.debug(f"加载了 {len(self._history)} 条连接历史")
            else:
                self._history = []
                
        except Exception as e:
            logger.error(f"加载连接历史失败: {e}")
            self._history = []
    
    def _save_history(self):
        """保存连接历史"""
        try:
            # 限制历史记录数量
            if len(self._history) > self.MAX_HISTORY_RECORDS:
                self._history = self._history[:self.MAX_HISTORY_RECORDS]
            
            data = {
                'version': '1.0',
                'updated_at': datetime.now().isoformat(),
                'history': [asdict(history) for history in self._history]
            }
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"保存了 {len(self._history)} 条连接历史")
            
        except Exception as e:
            logger.error(f"保存连接历史失败: {e}")
    
    def _ensure_default_config(self):
        """确保有默认配置"""
        if not self._configs:
            # 创建默认配置
            default_config = DatabaseConfig(
                id="default",
                name="默认数据库",
                path=get_default_database_path(),
                description="系统默认数据库",
                is_default=True,
                tags=["默认", "系统"]
            )
            
            self._configs[default_config.id] = default_config
            self._save_configs()
            logger.info("创建了默认数据库配置")
        else:
            # 确保有一个默认配置
            has_default = any(config.is_default for config in self._configs.values())
            if not has_default:
                # 将第一个配置设为默认
                first_config = next(iter(self._configs.values()))
                first_config.is_default = True
                self._save_configs()
                logger.info(f"将配置 '{first_config.name}' 设为默认")
    
    def add_config(self, name: str, path: str, description: str = "", 
                   tags: List[str] = None, set_as_default: bool = False) -> str:
        """
        添加数据库配置
        
        Args:
            name: 配置名称
            path: 数据库文件路径
            description: 描述信息
            tags: 标签列表
            set_as_default: 是否设为默认
            
        Returns:
            str: 配置ID
        """
        # 生成唯一ID
        config_id = self._generate_config_id(name)
        
        # 检查路径是否已存在
        existing_config = self.get_config_by_path(path)
        if existing_config:
            raise ValueError(f"数据库路径已存在于配置 '{existing_config.name}' 中")
        
        # 创建配置
        config = DatabaseConfig(
            id=config_id,
            name=name,
            path=os.path.abspath(path),
            description=description,
            tags=tags or [],
            is_default=set_as_default
        )
        
        # 如果设为默认，取消其他默认配置
        if set_as_default:
            self._clear_default_flags()
        
        # 更新文件信息
        config.update_file_info()
        
        # 保存配置
        self._configs[config_id] = config
        self._save_configs()
        
        logger.info(f"添加数据库配置: {name} -> {path}")
        return config_id
    
    def update_config(self, config_id: str, **kwargs) -> bool:
        """
        更新数据库配置
        
        Args:
            config_id: 配置ID
            **kwargs: 要更新的字段
            
        Returns:
            bool: 是否成功
        """
        if config_id not in self._configs:
            return False
        
        config = self._configs[config_id]
        
        # 更新字段
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # 如果设为默认，取消其他默认配置
        if kwargs.get('is_default'):
            self._clear_default_flags()
            config.is_default = True
        
        # 更新文件信息
        config.update_file_info()
        
        # 保存配置
        self._save_configs()
        
        logger.info(f"更新数据库配置: {config.name}")
        return True
    
    def remove_config(self, config_id: str) -> bool:
        """
        删除数据库配置
        
        Args:
            config_id: 配置ID
            
        Returns:
            bool: 是否成功
        """
        if config_id not in self._configs:
            return False
        
        config = self._configs[config_id]
        
        # 不能删除默认配置（如果只有一个配置）
        if config.is_default and len(self._configs) == 1:
            raise ValueError("不能删除唯一的默认配置")
        
        # 删除配置
        del self._configs[config_id]
        
        # 如果删除的是默认配置，设置新的默认配置
        if config.is_default and self._configs:
            first_config = next(iter(self._configs.values()))
            first_config.is_default = True
        
        # 保存配置
        self._save_configs()
        
        logger.info(f"删除数据库配置: {config.name}")
        return True
    
    def get_config(self, config_id: str) -> Optional[DatabaseConfig]:
        """
        获取数据库配置
        
        Args:
            config_id: 配置ID
            
        Returns:
            Optional[DatabaseConfig]: 配置对象
        """
        return self._configs.get(config_id)
    
    def get_config_by_path(self, path: str) -> Optional[DatabaseConfig]:
        """
        根据路径获取配置
        
        Args:
            path: 数据库文件路径
            
        Returns:
            Optional[DatabaseConfig]: 配置对象
        """
        abs_path = os.path.abspath(path)
        for config in self._configs.values():
            if os.path.abspath(config.path) == abs_path:
                return config
        return None
    
    def get_all_configs(self) -> List[DatabaseConfig]:
        """
        获取所有配置
        
        Returns:
            List[DatabaseConfig]: 配置列表
        """
        configs = list(self._configs.values())
        # 按最后访问时间排序（最近的在前）
        configs.sort(key=lambda x: x.last_accessed, reverse=True)
        return configs
    
    def get_default_config(self) -> Optional[DatabaseConfig]:
        """
        获取默认配置
        
        Returns:
            Optional[DatabaseConfig]: 默认配置
        """
        for config in self._configs.values():
            if config.is_default:
                return config
        return None
    
    def set_default_config(self, config_id: str) -> bool:
        """
        设置默认配置
        
        Args:
            config_id: 配置ID
            
        Returns:
            bool: 是否成功
        """
        if config_id not in self._configs:
            return False
        
        # 清除所有默认标志
        self._clear_default_flags()
        
        # 设置新的默认配置
        self._configs[config_id].is_default = True
        
        # 保存配置
        self._save_configs()
        
        logger.info(f"设置默认数据库配置: {self._configs[config_id].name}")
        return True
    
    def add_connection_history(self, config_id: str, success: bool = True, 
                             duration: float = 0.0, error_message: str = ""):
        """
        添加连接历史记录
        
        Args:
            config_id: 配置ID
            success: 是否成功
            duration: 连接持续时间
            error_message: 错误信息
        """
        config = self.get_config(config_id)
        if not config:
            return
        
        # 创建历史记录
        history = ConnectionHistory(
            database_id=config_id,
            database_name=config.name,
            database_path=config.path,
            connected_at=datetime.now().isoformat(),
            duration=duration,
            success=success,
            error_message=error_message
        )
        
        # 添加到历史列表开头
        self._history.insert(0, history)
        
        # 更新配置的访问信息
        if success:
            config.update_access_time()
            self._save_configs()
        
        # 保存历史
        self._save_history()
        
        logger.debug(f"添加连接历史: {config.name} ({'成功' if success else '失败'})")
    
    def get_connection_history(self, config_id: str = None, limit: int = 100) -> List[ConnectionHistory]:
        """
        获取连接历史
        
        Args:
            config_id: 配置ID，为None时返回所有历史
            limit: 返回记录数限制
            
        Returns:
            List[ConnectionHistory]: 历史记录列表
        """
        if config_id:
            history = [h for h in self._history if h.database_id == config_id]
        else:
            history = self._history
        
        return history[:limit]
    
    def clear_history(self, config_id: str = None, days: int = None):
        """
        清理连接历史
        
        Args:
            config_id: 配置ID，为None时清理所有历史
            days: 保留天数，为None时清理所有
        """
        if days is not None:
            # 计算截止时间
            cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
            
            # 过滤历史记录
            self._history = [
                h for h in self._history
                if datetime.fromisoformat(h.connected_at).timestamp() > cutoff_time
            ]
        elif config_id:
            # 清理指定配置的历史
            self._history = [h for h in self._history if h.database_id != config_id]
        else:
            # 清理所有历史
            self._history = []
        
        # 保存历史
        self._save_history()
        
        logger.info(f"清理连接历史: config_id={config_id}, days={days}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        total_configs = len(self._configs)
        existing_configs = sum(1 for config in self._configs.values() if config.exists)
        total_connections = sum(config.connection_count for config in self._configs.values())
        total_size = sum(config.file_size for config in self._configs.values())
        
        # 最近连接的配置
        recent_config = None
        if self._configs:
            recent_config = max(self._configs.values(), key=lambda x: x.last_accessed)
        
        # 连接成功率
        if self._history:
            success_count = sum(1 for h in self._history if h.success)
            success_rate = success_count / len(self._history) * 100
        else:
            success_rate = 0.0
        
        return {
            'total_configs': total_configs,
            'existing_configs': existing_configs,
            'missing_configs': total_configs - existing_configs,
            'total_connections': total_connections,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / 1024 / 1024,
            'recent_config': recent_config.name if recent_config else None,
            'recent_access_time': recent_config.last_accessed if recent_config else None,
            'history_records': len(self._history),
            'connection_success_rate': success_rate
        }
    
    def search_configs(self, query: str) -> List[DatabaseConfig]:
        """
        搜索配置
        
        Args:
            query: 搜索关键词
            
        Returns:
            List[DatabaseConfig]: 匹配的配置列表
        """
        query = query.lower()
        results = []
        
        for config in self._configs.values():
            # 搜索名称、描述、路径、标签
            if (query in config.name.lower() or
                query in config.description.lower() or
                query in config.path.lower() or
                any(query in tag.lower() for tag in config.tags)):
                results.append(config)
        
        # 按相关性排序（名称匹配优先）
        results.sort(key=lambda x: (
            query not in x.name.lower(),  # 名称匹配优先
            -x.connection_count,  # 连接次数多的优先
            x.last_accessed  # 最近访问的优先
        ))
        
        return results
    
    def export_configs(self, file_path: str, include_history: bool = False):
        """
        导出配置
        
        Args:
            file_path: 导出文件路径
            include_history: 是否包含历史记录
        """
        try:
            data = {
                'version': '1.0',
                'exported_at': datetime.now().isoformat(),
                'configs': [asdict(config) for config in self._configs.values()]
            }
            
            if include_history:
                data['history'] = [asdict(history) for history in self._history]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"导出配置到: {file_path}")
            
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            raise
    
    def import_configs(self, file_path: str, merge: bool = True) -> int:
        """
        导入配置
        
        Args:
            file_path: 导入文件路径
            merge: 是否合并（True）还是替换（False）
            
        Returns:
            int: 导入的配置数量
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported_configs = data.get('configs', [])
            imported_count = 0
            
            if not merge:
                # 替换模式：清空现有配置
                self._configs = {}
            
            for config_data in imported_configs:
                try:
                    config = DatabaseConfig(**config_data)
                    
                    # 检查ID冲突
                    if config.id in self._configs:
                        if merge:
                            # 生成新ID
                            config.id = self._generate_config_id(config.name)
                        else:
                            # 替换模式直接覆盖
                            pass
                    
                    self._configs[config.id] = config
                    imported_count += 1
                    
                except Exception as e:
                    logger.warning(f"导入配置失败: {e}")
            
            # 确保有默认配置
            self._ensure_default_config()
            
            # 保存配置
            self._save_configs()
            
            # 导入历史记录（如果有）
            if 'history' in data:
                imported_history = data['history']
                for history_data in imported_history:
                    try:
                        history = ConnectionHistory(**history_data)
                        self._history.append(history)
                    except Exception as e:
                        logger.warning(f"导入历史记录失败: {e}")
                
                # 排序并保存历史
                self._history.sort(key=lambda x: x.connected_at, reverse=True)
                self._save_history()
            
            logger.info(f"导入了 {imported_count} 个配置")
            return imported_count
            
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            raise
    
    def _generate_config_id(self, name: str) -> str:
        """
        生成配置ID
        
        Args:
            name: 配置名称
            
        Returns:
            str: 唯一ID
        """
        import uuid
        import hashlib
        
        # 基于名称和时间戳生成ID
        base_string = f"{name}_{datetime.now().isoformat()}"
        hash_object = hashlib.md5(base_string.encode())
        return hash_object.hexdigest()[:8]
    
    def _clear_default_flags(self):
        """清除所有默认标志"""
        for config in self._configs.values():
            config.is_default = False