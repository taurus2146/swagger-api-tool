#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置数据仓储类
提供全局配置的类型化访问、加密存储和变更通知功能
"""

import json
import logging
from typing import Optional, Dict, Any, List, Callable, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .database_manager import DatabaseManager
from .encryption_service import EncryptionService, EncryptionError

logger = logging.getLogger(__name__)


class ConfigType(Enum):
    """配置值类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    ENCRYPTED = "encrypted"


@dataclass
class ConfigItem:
    """配置项数据类"""
    key: str
    value: Any
    type: ConfigType
    description: Optional[str] = None
    is_system: bool = False
    updated_at: Optional[datetime] = None


class ConfigRepository:
    """配置数据仓储类"""
    
    def __init__(self, db_manager: DatabaseManager, encryption_service: Optional[EncryptionService] = None):
        """
        初始化配置仓储
        
        Args:
            db_manager: 数据库管理器实例
            encryption_service: 加密服务实例，用于处理敏感配置
        """
        self.db_manager = db_manager
        self.encryption_service = encryption_service or EncryptionService()
        self._change_listeners: Dict[str, List[Callable[[str, Any, Any], None]]] = {}
        self._cache: Dict[str, ConfigItem] = {}
        self._cache_loaded = False
    
    def _load_cache(self) -> None:
        """加载配置缓存"""
        if self._cache_loaded:
            return
        
        try:
            results = self.db_manager.execute_query(
                "SELECT key, value, type, description, is_system, updated_at FROM global_config"
            )
            
            if results:
                for row in results:
                    key, value_str, type_str, description, is_system, updated_at = row
                    
                    # 转换值类型
                    config_type = ConfigType(type_str)
                    value = self._parse_value(value_str, config_type)
                    
                    # 解析更新时间
                    updated_time = None
                    if updated_at:
                        try:
                            updated_time = datetime.fromisoformat(updated_at)
                        except ValueError:
                            pass
                    
                    self._cache[key] = ConfigItem(
                        key=key,
                        value=value,
                        type=config_type,
                        description=description,
                        is_system=bool(is_system),
                        updated_at=updated_time
                    )
            
            self._cache_loaded = True
            logger.debug(f"配置缓存已加载，共 {len(self._cache)} 项")
            
        except Exception as e:
            logger.error(f"加载配置缓存失败: {e}")
    
    def _parse_value(self, value_str: str, config_type: ConfigType) -> Any:
        """
        解析配置值
        
        Args:
            value_str: 字符串形式的值
            config_type: 配置类型
            
        Returns:
            Any: 解析后的值
        """
        try:
            if config_type == ConfigType.BOOLEAN:
                return value_str.lower() in ('true', '1', 'yes', 'on')
            elif config_type == ConfigType.INTEGER:
                return int(value_str)
            elif config_type == ConfigType.FLOAT:
                return float(value_str)
            elif config_type == ConfigType.JSON:
                return json.loads(value_str)
            elif config_type == ConfigType.ENCRYPTED:
                try:
                    return self.encryption_service.decrypt_data(value_str)
                except EncryptionError as e:
                    logger.error(f"解密配置失败: {e}")
                    return value_str  # 解密失败时返回原值
            else:  # STRING
                return value_str
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"解析配置值失败 {value_str}: {e}")
            return value_str
    
    def _serialize_value(self, value: Any, config_type: ConfigType) -> str:
        """
        序列化配置值
        
        Args:
            value: 要序列化的值
            config_type: 配置类型
            
        Returns:
            str: 序列化后的字符串
        """
        try:
            if config_type == ConfigType.BOOLEAN:
                return 'true' if value else 'false'
            elif config_type in (ConfigType.INTEGER, ConfigType.FLOAT):
                return str(value)
            elif config_type == ConfigType.JSON:
                return json.dumps(value, ensure_ascii=False)
            elif config_type == ConfigType.ENCRYPTED:
                try:
                    return self.encryption_service.encrypt_data(str(value))
                except EncryptionError as e:
                    logger.error(f"加密配置失败: {e}")
                    return str(value)  # 加密失败时返回原值
            else:  # STRING
                return str(value)
        except Exception as e:
            logger.error(f"序列化配置值失败 {value}: {e}")
            return str(value)
    
    def _notify_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """
        通知配置变更
        
        Args:
            key: 配置键
            old_value: 旧值
            new_value: 新值
        """
        # 通知特定键的监听器
        if key in self._change_listeners:
            for listener in self._change_listeners[key]:
                try:
                    listener(key, old_value, new_value)
                except Exception as e:
                    logger.error(f"配置变更通知失败 {key}: {e}")
        
        # 通知通用监听器
        if '*' in self._change_listeners:
            for listener in self._change_listeners['*']:
                try:
                    listener(key, old_value, new_value)
                except Exception as e:
                    logger.error(f"通用配置变更通知失败 {key}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        self._load_cache()
        
        if key in self._cache:
            return self._cache[key].value
        
        return default
    
    def get_string(self, key: str, default: str = "") -> str:
        """
        获取字符串配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            str: 字符串值
        """
        value = self.get(key, default)
        return str(value) if value is not None else default
    
    def get_int(self, key: str, default: int = 0) -> int:
        """
        获取整数配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            int: 整数值
        """
        value = self.get(key, default)
        try:
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        获取浮点数配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            float: 浮点数值
        """
        value = self.get(key, default)
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        获取布尔配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            bool: 布尔值
        """
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value) if value is not None else default
    
    def get_json(self, key: str, default: Any = None) -> Any:
        """
        获取JSON配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            Any: JSON解析后的值
        """
        value = self.get(key, default)
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return default
        return value if value is not None else default
    
    def set(self, key: str, value: Any, config_type: ConfigType = ConfigType.STRING,
            description: str = None, is_system: bool = False) -> bool:
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            config_type: 配置类型
            description: 配置描述
            is_system: 是否为系统配置
            
        Returns:
            bool: 设置是否成功
        """
        try:
            self._load_cache()
            
            # 获取旧值用于通知
            old_value = self._cache[key].value if key in self._cache else None
            
            # 序列化值
            value_str = self._serialize_value(value, config_type)
            
            # 更新数据库
            sql = '''
                INSERT OR REPLACE INTO global_config 
                (key, value, type, description, is_system, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            '''
            params = (
                key, value_str, config_type.value, description,
                is_system, datetime.now().isoformat()
            )
            
            success = self.db_manager.execute_update(sql, params)
            
            if success:
                # 更新缓存
                self._cache[key] = ConfigItem(
                    key=key,
                    value=value,
                    type=config_type,
                    description=description,
                    is_system=is_system,
                    updated_at=datetime.now()
                )
                
                # 通知变更
                self._notify_change(key, old_value, value)
                
                logger.debug(f"配置已设置: {key} = {value}")
            
            return success
            
        except Exception as e:
            logger.error(f"设置配置失败 {key}: {e}")
            return False
    
    def set_string(self, key: str, value: str, description: str = None) -> bool:
        """设置字符串配置"""
        return self.set(key, value, ConfigType.STRING, description)
    
    def set_int(self, key: str, value: int, description: str = None) -> bool:
        """设置整数配置"""
        return self.set(key, value, ConfigType.INTEGER, description)
    
    def set_float(self, key: str, value: float, description: str = None) -> bool:
        """设置浮点数配置"""
        return self.set(key, value, ConfigType.FLOAT, description)
    
    def set_bool(self, key: str, value: bool, description: str = None) -> bool:
        """设置布尔配置"""
        return self.set(key, value, ConfigType.BOOLEAN, description)
    
    def set_json(self, key: str, value: Any, description: str = None) -> bool:
        """设置JSON配置"""
        return self.set(key, value, ConfigType.JSON, description)
    
    def set_encrypted(self, key: str, value: str, description: str = None) -> bool:
        """设置加密配置"""
        return self.set(key, value, ConfigType.ENCRYPTED, description)
    
    def get_encrypted(self, key: str, default: str = "") -> str:
        """获取加密配置值"""
        value = self.get(key, default)
        return str(value) if value is not None else default
    
    def delete(self, key: str) -> bool:
        """
        删除配置项
        
        Args:
            key: 配置键
            
        Returns:
            bool: 删除是否成功
        """
        try:
            self._load_cache()
            
            # 检查是否为系统配置
            if key in self._cache and self._cache[key].is_system:
                logger.warning(f"尝试删除系统配置: {key}")
                return False
            
            # 获取旧值用于通知
            old_value = self._cache[key].value if key in self._cache else None
            
            # 从数据库删除
            success = self.db_manager.execute_update(
                "DELETE FROM global_config WHERE key = ? AND is_system = 0", (key,)
            )
            
            if success:
                # 从缓存删除
                if key in self._cache:
                    del self._cache[key]
                
                # 通知变更
                self._notify_change(key, old_value, None)
                
                logger.debug(f"配置已删除: {key}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除配置失败 {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        检查配置是否存在
        
        Args:
            key: 配置键
            
        Returns:
            bool: 配置是否存在
        """
        self._load_cache()
        return key in self._cache
    
    def get_all(self, include_system: bool = False) -> Dict[str, ConfigItem]:
        """
        获取所有配置项
        
        Args:
            include_system: 是否包含系统配置
            
        Returns:
            Dict[str, ConfigItem]: 配置项字典
        """
        self._load_cache()
        
        if include_system:
            return self._cache.copy()
        else:
            return {k: v for k, v in self._cache.items() if not v.is_system}
    
    def get_by_prefix(self, prefix: str, include_system: bool = False) -> Dict[str, ConfigItem]:
        """
        根据前缀获取配置项
        
        Args:
            prefix: 键前缀
            include_system: 是否包含系统配置
            
        Returns:
            Dict[str, ConfigItem]: 匹配的配置项字典
        """
        self._load_cache()
        
        result = {}
        for key, item in self._cache.items():
            if key.startswith(prefix):
                if include_system or not item.is_system:
                    result[key] = item
        
        return result
    
    def get_by_type(self, config_type: ConfigType, include_system: bool = False) -> Dict[str, ConfigItem]:
        """
        根据类型获取配置项
        
        Args:
            config_type: 配置类型
            include_system: 是否包含系统配置
            
        Returns:
            Dict[str, ConfigItem]: 匹配的配置项字典
        """
        self._load_cache()
        
        result = {}
        for key, item in self._cache.items():
            if item.type == config_type:
                if include_system or not item.is_system:
                    result[key] = item
        
        return result
    
    def add_change_listener(self, key: str, listener: Callable[[str, Any, Any], None]) -> None:
        """
        添加配置变更监听器
        
        Args:
            key: 配置键，使用 '*' 监听所有配置变更
            listener: 监听器函数，参数为 (key, old_value, new_value)
        """
        if key not in self._change_listeners:
            self._change_listeners[key] = []
        
        self._change_listeners[key].append(listener)
        logger.debug(f"已添加配置变更监听器: {key}")
    
    def remove_change_listener(self, key: str, listener: Callable[[str, Any, Any], None]) -> bool:
        """
        移除配置变更监听器
        
        Args:
            key: 配置键
            listener: 监听器函数
            
        Returns:
            bool: 移除是否成功
        """
        if key in self._change_listeners:
            try:
                self._change_listeners[key].remove(listener)
                if not self._change_listeners[key]:
                    del self._change_listeners[key]
                logger.debug(f"已移除配置变更监听器: {key}")
                return True
            except ValueError:
                pass
        
        return False
    
    def backup_config(self, backup_path: str, include_system: bool = True) -> bool:
        """
        备份配置到文件
        
        Args:
            backup_path: 备份文件路径
            include_system: 是否包含系统配置
            
        Returns:
            bool: 备份是否成功
        """
        try:
            configs = self.get_all(include_system)
            
            # 转换为可序列化的格式
            backup_data = {
                'timestamp': datetime.now().isoformat(),
                'configs': {}
            }
            
            for key, item in configs.items():
                backup_data['configs'][key] = {
                    'value': item.value,
                    'type': item.type.value,
                    'description': item.description,
                    'is_system': item.is_system,
                    'updated_at': item.updated_at.isoformat() if item.updated_at else None
                }
            
            # 写入文件
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置备份成功: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"配置备份失败: {e}")
            return False
    
    def restore_config(self, backup_path: str, overwrite_existing: bool = False) -> bool:
        """
        从文件恢复配置
        
        Args:
            backup_path: 备份文件路径
            overwrite_existing: 是否覆盖现有配置
            
        Returns:
            bool: 恢复是否成功
        """
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            if 'configs' not in backup_data:
                logger.error("备份文件格式无效")
                return False
            
            success_count = 0
            total_count = len(backup_data['configs'])
            
            for key, config_data in backup_data['configs'].items():
                # 检查是否已存在
                if not overwrite_existing and self.exists(key):
                    continue
                
                # 恢复配置
                config_type = ConfigType(config_data['type'])
                success = self.set(
                    key=key,
                    value=config_data['value'],
                    config_type=config_type,
                    description=config_data.get('description'),
                    is_system=config_data.get('is_system', False)
                )
                
                if success:
                    success_count += 1
            
            logger.info(f"配置恢复完成: {success_count}/{total_count}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"配置恢复失败: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """
        重置为默认配置（仅删除非系统配置）
        
        Returns:
            bool: 重置是否成功
        """
        try:
            # 获取所有非系统配置
            user_configs = self.get_all(include_system=False)
            
            success_count = 0
            for key in user_configs.keys():
                if self.delete(key):
                    success_count += 1
            
            logger.info(f"已重置 {success_count} 个用户配置")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            return False
    
    def get_config_info(self) -> Dict[str, Any]:
        """
        获取配置统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            self._load_cache()
            
            total_configs = len(self._cache)
            system_configs = sum(1 for item in self._cache.values() if item.is_system)
            user_configs = total_configs - system_configs
            
            # 按类型统计
            type_stats = {}
            for item in self._cache.values():
                type_name = item.type.value
                type_stats[type_name] = type_stats.get(type_name, 0) + 1
            
            # 最近更新时间
            recent_updates = [item.updated_at for item in self._cache.values() 
                            if item.updated_at is not None]
            most_recent = max(recent_updates) if recent_updates else None
            
            return {
                'total_configs': total_configs,
                'system_configs': system_configs,
                'user_configs': user_configs,
                'type_distribution': type_stats,
                'most_recent_update': most_recent.isoformat() if most_recent else None,
                'cache_loaded': self._cache_loaded,
                'active_listeners': sum(len(listeners) for listeners in self._change_listeners.values())
            }
            
        except Exception as e:
            logger.error(f"获取配置信息失败: {e}")
            return {}
    
    def clear_cache(self) -> None:
        """清空配置缓存"""
        self._cache.clear()
        self._cache_loaded = False
        logger.debug("配置缓存已清空")