#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库管理器
负责SQLite数据库的连接管理、初始化和配置
"""

import os
import sqlite3
import logging
import threading
import shutil
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from datetime import datetime

from .database_schema import DatabaseSchema
from .database_connection_manager import DatabaseConnectionManager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器类"""
    
    # 数据库版本
    CURRENT_VERSION = DatabaseSchema.SCHEMA_VERSION
    
    def __init__(self, db_path: str = None):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径，如果为None则使用默认路径
        """
        self.db_path = db_path
        self.schema = DatabaseSchema()

        # 使用连接管理器
        self.connection_manager = DatabaseConnectionManager(db_path) if db_path else None
    
    def connect(self) -> bool:
        """
        连接到数据库

        Returns:
            bool: 连接是否成功
        """
        if not self.connection_manager:
            logger.error("连接管理器未初始化")
            return False

        return self.connection_manager.connect()
    
    def disconnect(self) -> None:
        """断开数据库连接"""
        if self.connection_manager:
            self.connection_manager.disconnect()
    
    def initialize_database(self) -> bool:
        """
        初始化数据库，创建表和索引
        
        Returns:
            bool: 初始化是否成功
        """
        if not self.connect():
            return False

        try:
            with self.connection_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 执行所有创建语句（表、索引、触发器、视图）
                creation_statements = self.schema.get_all_creation_statements()
                for statement in creation_statements:
                    cursor.execute(statement)
                    logger.debug(f"执行创建语句成功")
                
                # 检查是否需要初始化database_info表
                cursor.execute('SELECT COUNT(*) FROM database_info')
                if cursor.fetchone()[0] == 0:
                    # 计算schema哈希
                    schema_hash = self.schema.calculate_schema_hash()
                    
                    # 插入初始版本信息
                    cursor.execute('''
                        INSERT INTO database_info (version, created_at, last_migration, schema_hash, notes)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (self.CURRENT_VERSION, datetime.now(), datetime.now(), schema_hash, 'Initial database creation'))
                
                # 插入初始数据
                for initial_sql in self.schema.INITIAL_DATA:
                    cursor.execute(initial_sql)

                conn.commit()
                logger.info("数据库初始化完成")
                return True

        except sqlite3.Error as e:
            logger.error(f"数据库初始化失败: {e}")
            return False
    
    def get_database_version(self) -> Optional[int]:
        """
        获取数据库版本
        
        Returns:
            Optional[int]: 数据库版本号，如果获取失败返回None
        """
        if not self.connection_manager:
            return None

        try:
            with self.connection_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT version FROM database_info LIMIT 1')
                result = cursor.fetchone()
                cursor.close()
                return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"获取数据库版本失败: {e}")
            return None
    
    def migrate_database(self) -> bool:
        """
        执行数据库迁移（使用版本管理器）
        
        Returns:
            bool: 迁移是否成功
        """
        try:
            # 延迟导入避免循环依赖
            from .database_version_manager import DatabaseVersionManager
            
            version_manager = DatabaseVersionManager(self)
            result = version_manager.auto_upgrade_to_latest()
            
            if result['success']:
                logger.info(f"数据库迁移成功: {result.get('message', '')}")
                return True
            else:
                logger.error(f"数据库迁移失败: {result.get('message', '')}")
                return False
                
        except Exception as e:
            logger.error(f"数据库迁移异常: {e}")
            return False
    
    def backup_database(self, backup_path: str) -> bool:
        """
        备份数据库
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            bool: 备份是否成功
        """
        if not self.connection_manager or not self.db_path:
            logger.error("数据库未连接或路径无效")
            return False
        
        try:
            # 确保备份目录存在
            backup_dir = os.path.dirname(backup_path)
            if backup_dir and not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)
            
            # 使用SQLite的备份API
            with sqlite3.connect(backup_path) as backup_conn:
                self._connection.backup(backup_conn)
            
            logger.info(f"数据库备份成功: {backup_path}")
            return True
            
        except (sqlite3.Error, OSError) as e:
            logger.error(f"数据库备份失败: {e}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """
        从备份恢复数据库
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            bool: 恢复是否成功
        """
        if not os.path.exists(backup_path):
            logger.error(f"备份文件不存在: {backup_path}")
            return False
        
        try:
            # 断开当前连接
            self.disconnect()
            
            # 备份当前数据库文件（如果存在）
            if self.db_path and os.path.exists(self.db_path):
                backup_current = f"{self.db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(self.db_path, backup_current)
                logger.info(f"当前数据库已备份到: {backup_current}")
            
            # 复制备份文件到数据库位置
            shutil.copy2(backup_path, self.db_path)
            
            # 重新连接并验证
            if self.connect() and self.test_connection():
                logger.info(f"数据库恢复成功: {backup_path}")
                return True
            else:
                logger.error("恢复后的数据库连接测试失败")
                return False
                
        except (OSError, sqlite3.Error) as e:
            logger.error(f"数据库恢复失败: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        获取数据库连接信息
        
        Returns:
            Dict[str, Any]: 连接信息字典
        """
        info = {
            'db_path': self.db_path,
            'is_connected': self.connection_manager is not None,
            'version': self.get_database_version(),
            'file_exists': os.path.exists(self.db_path) if self.db_path else False,
            'file_size': 0,
            'table_count': 0,
            'record_count': 0
        }
        
        if self.db_path and os.path.exists(self.db_path):
            info['file_size'] = os.path.getsize(self.db_path)
        
        if self.connection_manager:
            try:
                with self.connection_manager.get_connection() as conn:
                    cursor = conn.cursor()

                    # 获取表数量
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                    info['table_count'] = cursor.fetchone()[0]

                    # 获取项目记录数量
                    cursor.execute("SELECT COUNT(*) FROM projects")
                    info['record_count'] = cursor.fetchone()[0]

                    cursor.close()
            except sqlite3.Error as e:
                logger.error(f"获取数据库信息失败: {e}")
        
        return info
    
    def test_connection(self) -> bool:
        """
        测试数据库连接
        
        Returns:
            bool: 连接测试是否成功
        """
        if not self.connection_manager:
            return False

        try:
            with self.connection_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                cursor.close()
                return True
        except sqlite3.Error as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False
    
    @contextmanager
    def get_cursor(self):
        """
        获取数据库游标的上下文管理器

        Yields:
            sqlite3.Cursor: 数据库游标
        """
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()

    @contextmanager
    def transaction(self):
        """
        事务上下文管理器

        Yields:
            sqlite3.Cursor: 数据库游标
        """
        with self.connection_manager.transaction() as cursor:
            yield cursor
    
    def execute_query(self, sql: str, params: tuple = None) -> Optional[list]:
        """
        执行查询SQL

        Args:
            sql: SQL语句
            params: 参数元组

        Returns:
            Optional[list]: 查询结果列表，失败返回None
        """
        if not self.connection_manager:
            return None

        return self.connection_manager.execute_query(sql, params)
    
    def execute_update(self, sql: str, params: tuple = None) -> bool:
        """
        执行更新SQL

        Args:
            sql: SQL语句
            params: 参数元组

        Returns:
            bool: 执行是否成功
        """
        if not self.connection_manager:
            return False

        return self.connection_manager.execute_update(sql, params)
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def get_version_manager(self):
        """
        获取数据库版本管理器实例
        
        Returns:
            DatabaseVersionManager: 版本管理器实例
        """
        from .database_version_manager import DatabaseVersionManager
        return DatabaseVersionManager(self)
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()   
 # 项目相关方法
    def create_project(self, project_data: Dict[str, Any]) -> str:
        """
        创建项目
        
        Args:
            project_data: 项目数据字典
            
        Returns:
            项目ID
        """
        import uuid
        
        project_id = str(uuid.uuid4())
        
        sql = """
        INSERT INTO projects (id, name, description, base_url, swagger_source_type, swagger_source_location, created_at, last_accessed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        current_time = datetime.now().isoformat()
        params = (
            project_id,
            project_data.get('name', ''),
            project_data.get('description', ''),
            project_data.get('base_url', ''),
            project_data.get('swagger_source_type', 'url'),
            project_data.get('swagger_source_location', ''),
            current_time,
            current_time
        )
        
        if self.execute_update(sql, params):
            return project_id
        return None
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        获取项目
        
        Args:
            project_id: 项目ID
            
        Returns:
            项目数据字典
        """
        sql = "SELECT * FROM projects WHERE id = ?"
        result = self.execute_query(sql, (project_id,))
        
        if result and len(result) > 0:
            row = result[0]
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'swagger_source_type': row[3],
                'swagger_source_location': row[4],
                'swagger_source_last_modified': row[5],
                'base_url': row[6],
                'auth_config': row[7],
                'created_at': row[8],
                'last_accessed': row[9]
            }
        return None
    
    def get_all_projects(self) -> List[Dict[str, Any]]:
        """
        获取所有项目
        
        Returns:
            项目列表
        """
        sql = "SELECT * FROM projects ORDER BY created_at DESC"
        result = self.execute_query(sql)
        
        projects = []
        if result:
            for row in result:
                projects.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'swagger_source_type': row[3],
                    'swagger_source_location': row[4],
                    'swagger_source_last_modified': row[5],
                    'base_url': row[6],
                    'auth_config': row[7],
                    'created_at': row[8],
                    'last_accessed': row[9]
                })
        
        return projects
    
    def update_project(self, project_id: str, project_data: Dict[str, Any]) -> bool:
        """
        更新项目
        
        Args:
            project_id: 项目ID
            project_data: 更新的项目数据
            
        Returns:
            是否更新成功
        """
        sql = """
        UPDATE projects 
        SET name = ?, description = ?, base_url = ?, last_modified = ?
        WHERE id = ?
        """
        
        params = (
            project_data.get('name', ''),
            project_data.get('description', ''),
            project_data.get('base_url', ''),
            datetime.now().isoformat(),
            project_id
        )
        
        return self.execute_update(sql, params)
    
    def delete_project(self, project_id: str) -> bool:
        """
        删除项目
        
        Args:
            project_id: 项目ID
            
        Returns:
            是否删除成功
        """
        sql = "DELETE FROM projects WHERE id = ?"
        return self.execute_update(sql, (project_id,))
    
    def search_projects(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        搜索项目
        
        Args:
            query: 搜索查询
            limit: 结果限制
            
        Returns:
            搜索结果
        """
        sql = """
        SELECT * FROM projects 
        WHERE name LIKE ? OR description LIKE ?
        ORDER BY created_at DESC
        LIMIT ?
        """
        
        search_pattern = f"%{query}%"
        result = self.execute_query(sql, (search_pattern, search_pattern, limit))
        
        projects = []
        if result:
            for row in result:
                projects.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'swagger_source_type': row[3],
                    'swagger_source_location': row[4],
                    'swagger_source_last_modified': row[5],
                    'base_url': row[6],
                    'auth_config': row[7],
                    'created_at': row[8],
                    'last_accessed': row[9]
                })
        
        return projects
    
    # API相关方法
    def create_api(self, api_data: Dict[str, Any]) -> int:
        """
        创建API
        
        Args:
            api_data: API数据字典
            
        Returns:
            API ID
        """
        sql = """
        INSERT INTO apis (project_id, path, method, name, description, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        params = (
            api_data.get('project_id', ''),
            api_data.get('path', ''),
            api_data.get('method', ''),
            api_data.get('name', ''),
            api_data.get('description', ''),
            datetime.now().isoformat()
        )
        
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.lastrowid
    
    def get_api(self, api_id: int) -> Optional[Dict[str, Any]]:
        """
        获取API
        
        Args:
            api_id: API ID
            
        Returns:
            API数据字典
        """
        sql = "SELECT * FROM apis WHERE id = ?"
        result = self.execute_query(sql, (api_id,))
        
        if result and len(result) > 0:
            row = result[0]
            return {
                'id': row[0],
                'project_id': row[1],
                'path': row[2],
                'method': row[3],
                'name': row[4],
                'description': row[5],
                'created_at': row[6]
            }
        return None
    
    def get_project_apis(self, project_id: str) -> List[Dict[str, Any]]:
        """
        获取项目的所有API
        
        Args:
            project_id: 项目ID
            
        Returns:
            API列表
        """
        sql = "SELECT * FROM apis WHERE project_id = ? ORDER BY created_at DESC"
        result = self.execute_query(sql, (project_id,))
        
        apis = []
        if result:
            for row in result:
                apis.append({
                    'id': row[0],
                    'project_id': row[1],
                    'path': row[2],
                    'method': row[3],
                    'name': row[4],
                    'description': row[5],
                    'created_at': row[6]
                })
        
        return apis
    
    def update_api(self, api_id: int, api_data: Dict[str, Any]) -> bool:
        """
        更新API
        
        Args:
            api_id: API ID
            api_data: 更新的API数据
            
        Returns:
            是否更新成功
        """
        sql = """
        UPDATE apis 
        SET path = ?, method = ?, name = ?, description = ?
        WHERE id = ?
        """
        
        params = (
            api_data.get('path', ''),
            api_data.get('method', ''),
            api_data.get('name', ''),
            api_data.get('description', ''),
            api_id
        )
        
        return self.execute_update(sql, params)
    
    def delete_api(self, api_id: int) -> bool:
        """
        删除API
        
        Args:
            api_id: API ID
            
        Returns:
            是否删除成功
        """
        sql = "DELETE FROM apis WHERE id = ?"
        return self.execute_update(sql, (api_id,))
    
    # 配置相关方法
    def set_config(self, key: str, value: Any) -> bool:
        """
        设置配置
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            是否设置成功
        """
        import json
        
        # 将值序列化为JSON
        if isinstance(value, (dict, list)):
            json_value = json.dumps(value, ensure_ascii=False)
        else:
            json_value = json.dumps(value, ensure_ascii=False)
        
        sql = """
        INSERT OR REPLACE INTO global_config (key, value, type, updated_at)
        VALUES (?, ?, ?, ?)
        """
        
        # 确定数据类型
        if isinstance(value, dict):
            value_type = 'json'
        elif isinstance(value, list):
            value_type = 'json'
        elif isinstance(value, bool):
            value_type = 'boolean'
        elif isinstance(value, int):
            value_type = 'integer'
        elif isinstance(value, float):
            value_type = 'float'
        else:
            value_type = 'string'
        
        params = (key, json_value, value_type, datetime.now().isoformat())
        return self.execute_update(sql, params)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        import json
        
        sql = "SELECT value FROM global_config WHERE key = ?"
        result = self.execute_query(sql, (key,))
        
        if result and len(result) > 0:
            try:
                return json.loads(result[0][0])
            except (json.JSONDecodeError, TypeError):
                return default
        
        return default
    
    def get_all_configs(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            配置字典
        """
        import json
        
        sql = "SELECT key, value FROM global_config"
        result = self.execute_query(sql)
        
        configs = {}
        if result:
            for row in result:
                key, value = row
                try:
                    configs[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    configs[key] = value
        
        return configs
    
    def delete_config(self, key: str) -> bool:
        """
        删除配置
        
        Args:
            key: 配置键
            
        Returns:
            是否删除成功
        """
        sql = "DELETE FROM global_config WHERE key = ?"
        return self.execute_update(sql, (key,))