#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库连接管理器
实现单例模式和连接池管理，解决数据库锁定问题
"""

import os
import sqlite3
import logging
import threading
import time
import weakref
from typing import Optional, Dict, Any
from contextlib import contextmanager
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """数据库连接管理器 - 单例模式"""
    
    _instances = {}
    _lock = threading.RLock()
    
    def __new__(cls, db_path: str):
        """单例模式实现"""
        with cls._lock:
            # 规范化路径作为键
            normalized_path = os.path.abspath(db_path) if db_path else None
            
            if normalized_path not in cls._instances:
                instance = super().__new__(cls)
                cls._instances[normalized_path] = instance
                instance._initialized = False
            
            return cls._instances[normalized_path]
    
    def __init__(self, db_path: str):
        """初始化连接管理器"""
        if self._initialized:
            return
        
        self.db_path = os.path.abspath(db_path) if db_path else None
        self._connection = None
        self._connection_lock = threading.RLock()
        self._is_connected = False
        self._last_activity = None
        self._connection_timeout = 300  # 5分钟超时
        self._retry_attempts = 3
        self._retry_delay = 0.1
        self._initialized = True
        
        # 启动连接监控线程
        self._monitor_thread = threading.Thread(target=self._monitor_connection, daemon=True)
        self._monitor_thread.start()
        
        logger.info(f"数据库连接管理器已初始化: {self.db_path}")
    
    def connect(self) -> bool:
        """连接到数据库（带重试机制）"""
        with self._connection_lock:
            if self._is_connected and self._connection:
                try:
                    # 测试连接是否有效
                    self._connection.execute('SELECT 1')
                    self._last_activity = datetime.now()
                    return True
                except sqlite3.Error:
                    logger.warning("检测到无效连接，重新连接...")
                    self._cleanup_connection()
            
            # 重试连接
            for attempt in range(self._retry_attempts):
                try:
                    if self._attempt_connection():
                        return True
                except sqlite3.Error as e:
                    logger.warning(f"连接尝试 {attempt + 1} 失败: {e}")
                    if attempt < self._retry_attempts - 1:
                        time.sleep(self._retry_delay * (2 ** attempt))  # 指数退避
                    else:
                        logger.error(f"数据库连接失败，已尝试 {self._retry_attempts} 次")
            
            return False
    
    def _attempt_connection(self) -> bool:
        """尝试建立数据库连接"""
        if not self.db_path:
            raise sqlite3.Error("数据库路径未设置")
        
        # 确保数据库目录存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        # 检查是否有其他进程锁定数据库
        if self._is_database_locked():
            raise sqlite3.Error("数据库被其他进程锁定")
        
        # 建立连接
        self._connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0,
            isolation_level=None  # 自动提交模式
        )
        
        # 配置连接
        self._configure_connection()
        
        self._is_connected = True
        self._last_activity = datetime.now()
        
        logger.info(f"数据库连接成功: {self.db_path}")
        return True
    
    def _configure_connection(self):
        """配置数据库连接"""
        if not self._connection:
            return
        
        # 设置行工厂
        self._connection.row_factory = sqlite3.Row
        
        # 执行配置语句
        config_statements = [
            'PRAGMA foreign_keys = ON',
            'PRAGMA journal_mode = WAL',
            'PRAGMA synchronous = NORMAL',
            'PRAGMA cache_size = 10000',
            'PRAGMA temp_store = MEMORY',
            'PRAGMA mmap_size = 268435456',  # 256MB
            'PRAGMA busy_timeout = 30000',   # 30秒忙等待
        ]
        
        for statement in config_statements:
            try:
                self._connection.execute(statement)
            except sqlite3.Error as e:
                logger.warning(f"配置语句执行失败: {statement}, 错误: {e}")
    
    def _is_database_locked(self) -> bool:
        """检查数据库是否被锁定"""
        if not os.path.exists(self.db_path):
            return False
        
        try:
            # 尝试以独占模式打开数据库
            test_conn = sqlite3.connect(
                self.db_path,
                timeout=1.0
            )
            test_conn.execute('BEGIN IMMEDIATE')
            test_conn.rollback()
            test_conn.close()
            return False
        except sqlite3.Error:
            return True
    
    def disconnect(self):
        """断开数据库连接"""
        with self._connection_lock:
            self._cleanup_connection()
    
    def _cleanup_connection(self):
        """清理数据库连接"""
        if self._connection:
            try:
                self._connection.close()
                logger.debug("数据库连接已关闭")
            except sqlite3.Error as e:
                logger.warning(f"关闭数据库连接时出错: {e}")
            finally:
                self._connection = None
                self._is_connected = False
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        if not self.connect():
            raise sqlite3.Error("无法建立数据库连接")
        
        with self._connection_lock:
            try:
                yield self._connection
                self._last_activity = datetime.now()
            except Exception as e:
                logger.error(f"数据库操作异常: {e}")
                # 检查是否需要重新连接
                if "database is locked" in str(e).lower():
                    logger.warning("检测到数据库锁定，尝试重新连接...")
                    self._cleanup_connection()
                raise
    
    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('BEGIN')
                yield cursor
                cursor.execute('COMMIT')
                logger.debug("事务提交成功")
            except Exception as e:
                cursor.execute('ROLLBACK')
                logger.warning(f"事务回滚: {e}")
                raise
            finally:
                cursor.close()
    
    def execute_query(self, sql: str, params: tuple = None) -> Optional[list]:
        """执行查询SQL"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                result = cursor.fetchall()
                cursor.close()
                return result
        except sqlite3.Error as e:
            logger.error(f"执行查询失败: {e}")
            return None
    
    def execute_update(self, sql: str, params: tuple = None) -> bool:
        """执行更新SQL"""
        try:
            with self.transaction() as cursor:
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                return True
        except sqlite3.Error as e:
            logger.error(f"执行更新失败: {e}")
            return False
    
    def _monitor_connection(self):
        """监控连接状态"""
        while True:
            try:
                time.sleep(60)  # 每分钟检查一次
                
                with self._connection_lock:
                    if (self._is_connected and self._last_activity and 
                        datetime.now() - self._last_activity > timedelta(seconds=self._connection_timeout)):
                        logger.info("连接超时，关闭空闲连接")
                        self._cleanup_connection()
                        
            except Exception as e:
                logger.error(f"连接监控异常: {e}")
    
    @classmethod
    def cleanup_all_instances(cls):
        """清理所有实例"""
        with cls._lock:
            for instance in cls._instances.values():
                if hasattr(instance, 'disconnect'):
                    instance.disconnect()
            cls._instances.clear()
    
    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            'db_path': self.db_path,
            'is_connected': self._is_connected,
            'last_activity': self._last_activity,
            'connection_timeout': self._connection_timeout
        }
