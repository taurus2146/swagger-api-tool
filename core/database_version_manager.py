#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库版本管理器
提供数据库schema版本控制、自动升级和兼容性检查功能
"""

import os
import json
import logging
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .database_manager import DatabaseManager
from .database_schema import DatabaseSchema

logger = logging.getLogger(__name__)


class VersionStatus(Enum):
    """版本状态枚举"""
    CURRENT = "current"
    OUTDATED = "outdated"
    FUTURE = "future"
    UNKNOWN = "unknown"


class MigrationDirection(Enum):
    """迁移方向枚举"""
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"


@dataclass
class VersionInfo:
    """版本信息"""
    version: int
    schema_hash: str
    created_at: datetime
    notes: Optional[str] = None
    migration_scripts: List[str] = None
    
    def __post_init__(self):
        if self.migration_scripts is None:
            self.migration_scripts = []


@dataclass
class MigrationScript:
    """迁移脚本"""
    from_version: int
    to_version: int
    direction: MigrationDirection
    sql_statements: List[str]
    description: str
    rollback_statements: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.rollback_statements is None:
            self.rollback_statements = []


@dataclass
class MigrationPlan:
    """迁移计划"""
    current_version: int
    target_version: int
    direction: MigrationDirection
    scripts: List[MigrationScript]
    estimated_time: float = 0.0
    backup_required: bool = True


class DatabaseVersionManager:
    """数据库版本管理器"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        初始化版本管理器
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
        self.schema = DatabaseSchema()
        self.current_schema_version = DatabaseSchema.SCHEMA_VERSION
        
        # 定义迁移脚本
        self._migration_scripts = self._initialize_migration_scripts()
    
    def _initialize_migration_scripts(self) -> Dict[Tuple[int, int], MigrationScript]:
        """
        初始化迁移脚本
        
        Returns:
            Dict[Tuple[int, int], MigrationScript]: 迁移脚本字典
        """
        scripts = {}
        
        # 版本0到版本1的升级脚本
        scripts[(0, 1)] = MigrationScript(
            from_version=0,
            to_version=1,
            direction=MigrationDirection.UPGRADE,
            description="初始化数据库schema到版本1",
            sql_statements=self._get_v0_to_v1_migration_statements(),
            rollback_statements=[
                # 删除所有视图
                "DROP VIEW IF EXISTS view_project_stats",
                "DROP VIEW IF EXISTS view_recent_activity",
                # 删除所有表（外键约束会自动处理）
                "DROP TABLE IF EXISTS project_history",
                "DROP TABLE IF EXISTS api_cache",
                "DROP TABLE IF EXISTS user_preferences",
                "DROP TABLE IF EXISTS global_config",
                "DROP TABLE IF EXISTS projects",
                "DROP TABLE IF EXISTS database_info"
            ]
        )
        
        # 未来版本的迁移脚本可以在这里添加
        # 例如：版本1到版本2
        # scripts[(1, 2)] = MigrationScript(
        #     from_version=1,
        #     to_version=2,
        #     direction=MigrationDirection.UPGRADE,
        #     description="升级到版本2：添加新功能",
        #     sql_statements=[
        #         # 示例：添加新表或字段
        #         "ALTER TABLE projects ADD COLUMN priority INTEGER DEFAULT 0",
        #         "CREATE INDEX IF NOT EXISTS idx_projects_priority ON projects(priority)"
        #     ],
        #     rollback_statements=[
        #         # 回滚操作
        #         "DROP INDEX IF EXISTS idx_projects_priority",
        #         "ALTER TABLE projects DROP COLUMN priority"
        #     ]
        # )
        
        return scripts
    
    def _get_v0_to_v1_migration_statements(self) -> List[str]:
        """
        获取从版本0到版本1的迁移语句
        
        Returns:
            List[str]: 迁移SQL语句列表
        """
        statements = []
        
        # 首先创建所有新表（使用IF NOT EXISTS）
        for table_name, table_sql in self.schema.TABLES.items():
            statements.append(table_sql)
        
        # 创建所有索引
        statements.extend(self.schema.INDEXES)
        
        # 创建所有触发器
        statements.extend(self.schema.TRIGGERS)
        
        # 创建所有视图
        statements.extend(self.schema.VIEWS)
        
        # 插入初始数据
        statements.extend(self.schema.INITIAL_DATA)
        
        return statements
    
    def get_current_version(self) -> Optional[int]:
        """
        获取当前数据库版本
        
        Returns:
            Optional[int]: 当前版本号，如果无法获取返回None
        """
        try:
            result = self.db_manager.execute_query(
                "SELECT version FROM database_info ORDER BY version DESC LIMIT 1"
            )
            
            if result:
                return result[0][0]
            else:
                # 如果没有版本信息，检查是否有表存在
                tables = self.db_manager.execute_query(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
                )
                
                if tables and len(tables) > 0:
                    # 有表但没有版本信息，可能是旧版本
                    return 0
                else:
                    # 空数据库
                    return None
                    
        except Exception as e:
            logger.error(f"获取数据库版本失败: {e}")
            return None
    
    def get_version_status(self) -> VersionStatus:
        """
        获取版本状态
        
        Returns:
            VersionStatus: 版本状态
        """
        current_version = self.get_current_version()
        
        if current_version is None:
            return VersionStatus.UNKNOWN
        elif current_version < self.current_schema_version:
            return VersionStatus.OUTDATED
        elif current_version > self.current_schema_version:
            return VersionStatus.FUTURE
        else:
            return VersionStatus.CURRENT
    
    def calculate_schema_hash(self) -> str:
        """
        计算当前schema的哈希值
        
        Returns:
            str: schema哈希值
        """
        try:
            # 收集所有schema定义
            schema_content = {
                'tables': self.schema.TABLES,
                'indexes': self.schema.INDEXES,
                'triggers': self.schema.TRIGGERS,
                'views': self.schema.VIEWS,
                'version': self.current_schema_version
            }
            
            # 转换为JSON字符串并计算哈希
            schema_json = json.dumps(schema_content, sort_keys=True, ensure_ascii=False)
            return hashlib.sha256(schema_json.encode('utf-8')).hexdigest()
            
        except Exception as e:
            logger.error(f"计算schema哈希失败: {e}")
            return ""
    
    def verify_schema_integrity(self) -> Dict[str, Any]:
        """
        验证数据库schema完整性
        
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            result = {
                'valid': True,
                'issues': [],
                'missing_tables': [],
                'missing_indexes': [],
                'missing_triggers': [],
                'missing_views': [],
                'extra_objects': [],
                'schema_hash_match': False
            }
            
            # 检查表
            existing_tables = self.db_manager.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
            )
            existing_table_names = {row[0] for row in existing_tables} if existing_tables else set()
            expected_table_names = set(self.schema.TABLES.keys())
            
            result['missing_tables'] = list(expected_table_names - existing_table_names)
            extra_tables = existing_table_names - expected_table_names
            if extra_tables:
                result['extra_objects'].extend([f"table:{name}" for name in extra_tables])
            
            # 检查索引
            existing_indexes = self.db_manager.execute_query(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            )
            existing_index_names = {row[0] for row in existing_indexes} if existing_indexes else set()
            
            # 从索引SQL中提取索引名
            expected_index_names = set()
            for index_sql in self.schema.INDEXES:
                # 简单的正则匹配提取索引名
                import re
                match = re.search(r'CREATE INDEX IF NOT EXISTS (\w+)', index_sql)
                if match:
                    expected_index_names.add(match.group(1))
            
            result['missing_indexes'] = list(expected_index_names - existing_index_names)
            
            # 检查触发器
            existing_triggers = self.db_manager.execute_query(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
            existing_trigger_names = {row[0] for row in existing_triggers} if existing_triggers else set()
            
            # 从触发器SQL中提取触发器名
            expected_trigger_names = set()
            for trigger_sql in self.schema.TRIGGERS:
                match = re.search(r'CREATE TRIGGER IF NOT EXISTS (\w+)', trigger_sql)
                if match:
                    expected_trigger_names.add(match.group(1))
            
            result['missing_triggers'] = list(expected_trigger_names - existing_trigger_names)
            
            # 检查视图
            existing_views = self.db_manager.execute_query(
                "SELECT name FROM sqlite_master WHERE type='view'"
            )
            existing_view_names = {row[0] for row in existing_views} if existing_views else set()
            
            # 从视图SQL中提取视图名
            expected_view_names = set()
            for view_sql in self.schema.VIEWS:
                match = re.search(r'CREATE VIEW IF NOT EXISTS (\w+)', view_sql)
                if match:
                    expected_view_names.add(match.group(1))
            
            result['missing_views'] = list(expected_view_names - existing_view_names)
            
            # 检查schema哈希
            current_hash = self.calculate_schema_hash()
            stored_hash = self.db_manager.execute_query(
                "SELECT schema_hash FROM database_info ORDER BY version DESC LIMIT 1"
            )
            
            if stored_hash and stored_hash[0][0]:
                result['schema_hash_match'] = current_hash == stored_hash[0][0]
            
            # 汇总问题
            if (result['missing_tables'] or result['missing_indexes'] or 
                result['missing_triggers'] or result['missing_views'] or 
                result['extra_objects'] or not result['schema_hash_match']):
                result['valid'] = False
                
                if result['missing_tables']:
                    result['issues'].append(f"缺少表: {', '.join(result['missing_tables'])}")
                if result['missing_indexes']:
                    result['issues'].append(f"缺少索引: {', '.join(result['missing_indexes'])}")
                if result['missing_triggers']:
                    result['issues'].append(f"缺少触发器: {', '.join(result['missing_triggers'])}")
                if result['missing_views']:
                    result['issues'].append(f"缺少视图: {', '.join(result['missing_views'])}")
                if result['extra_objects']:
                    result['issues'].append(f"额外对象: {', '.join(result['extra_objects'])}")
                if not result['schema_hash_match']:
                    result['issues'].append("Schema哈希不匹配")
            
            return result
            
        except Exception as e:
            logger.error(f"验证schema完整性失败: {e}")
            return {
                'valid': False,
                'issues': [f"验证过程异常: {e}"],
                'error': str(e)
            }
    
    def create_migration_plan(self, target_version: int) -> Optional[MigrationPlan]:
        """
        创建迁移计划
        
        Args:
            target_version: 目标版本
            
        Returns:
            Optional[MigrationPlan]: 迁移计划，无法创建返回None
        """
        try:
            current_version = self.get_current_version()
            if current_version is None:
                current_version = 0
            
            if current_version == target_version:
                logger.info("当前版本已是目标版本，无需迁移")
                return None
            
            # 确定迁移方向
            direction = MigrationDirection.UPGRADE if target_version > current_version else MigrationDirection.DOWNGRADE
            
            # 构建迁移路径
            scripts = []
            if direction == MigrationDirection.UPGRADE:
                # 升级路径
                for version in range(current_version, target_version):
                    script_key = (version, version + 1)
                    if script_key in self._migration_scripts:
                        scripts.append(self._migration_scripts[script_key])
                    else:
                        logger.error(f"缺少迁移脚本: {version} -> {version + 1}")
                        return None
            else:
                # 降级路径
                for version in range(current_version, target_version, -1):
                    script_key = (version - 1, version)
                    if script_key in self._migration_scripts:
                        # 创建降级脚本
                        original_script = self._migration_scripts[script_key]
                        downgrade_script = MigrationScript(
                            from_version=version,
                            to_version=version - 1,
                            direction=MigrationDirection.DOWNGRADE,
                            description=f"降级从版本{version}到{version-1}",
                            sql_statements=original_script.rollback_statements,
                            rollback_statements=original_script.sql_statements
                        )
                        scripts.append(downgrade_script)
                    else:
                        logger.error(f"缺少降级脚本: {version} -> {version - 1}")
                        return None
            
            # 估算迁移时间（简单估算）
            estimated_time = len(scripts) * 0.5  # 每个脚本估算0.5秒
            
            plan = MigrationPlan(
                current_version=current_version,
                target_version=target_version,
                direction=direction,
                scripts=scripts,
                estimated_time=estimated_time,
                backup_required=True
            )
            
            logger.info(f"迁移计划已创建: {current_version} -> {target_version}, {len(scripts)}个脚本")
            return plan
            
        except Exception as e:
            logger.error(f"创建迁移计划失败: {e}")
            return None
    
    def _execute_smart_migration(self, script: MigrationScript) -> bool:
        """
        智能执行迁移脚本，处理现有表结构
        
        Args:
            script: 迁移脚本
            
        Returns:
            bool: 执行是否成功
        """
        try:
            with self.db_manager.transaction() as cursor:
                # 如果是从版本0到版本1的迁移，需要特殊处理
                if script.from_version == 0 and script.to_version == 1:
                    # 检查现有表结构
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    existing_tables = {row[0] for row in cursor.fetchall()}
                    
                    # 如果projects表已存在，需要检查其结构
                    if 'projects' in existing_tables:
                        cursor.execute("PRAGMA table_info(projects)")
                        existing_columns = {row[1] for row in cursor.fetchall()}
                        
                        # 获取期望的列
                        expected_columns = {
                            'id', 'name', 'description', 'swagger_source_type', 
                            'swagger_source_location', 'swagger_source_last_modified',
                            'base_url', 'auth_config', 'created_at', 'last_accessed',
                            'api_count', 'ui_state', 'tags', 'version', 'is_active', 'last_modified'
                        }
                        
                        missing_columns = expected_columns - existing_columns
                        
                        if missing_columns:
                            logger.info(f"需要添加缺失的列: {missing_columns}")
                            
                            # 备份现有数据
                            cursor.execute("SELECT * FROM projects")
                            existing_data = cursor.fetchall()
                            
                            # 重建表
                            cursor.execute("DROP TABLE projects")
                            cursor.execute(self.schema.TABLES['projects'])
                            
                            # 恢复数据
                            if existing_data:
                                for row in existing_data:
                                    # 构建完整的INSERT语句，为缺失字段提供默认值
                                    values = {
                                        'id': row[0] if len(row) > 0 else '',
                                        'name': row[1] if len(row) > 1 else '',
                                        'description': row[2] if len(row) > 2 and 'description' in existing_columns else '',
                                        'swagger_source_type': 'url',  # 默认值
                                        'swagger_source_location': '',  # 默认值
                                        'swagger_source_last_modified': None,
                                        'base_url': '',
                                        'auth_config': None,
                                        'created_at': row[len(row)-1] if len(row) > 0 else datetime.now().isoformat(),  # 假设最后一个是created_at
                                        'last_accessed': row[len(row)-1] if len(row) > 0 else datetime.now().isoformat(),
                                        'api_count': 0,
                                        'ui_state': None,
                                        'tags': None,
                                        'version': 1,
                                        'is_active': 1,
                                        'last_modified': datetime.now().isoformat()
                                    }
                                    
                                    # 如果原始数据有created_at字段，使用它
                                    if 'created_at' in existing_columns:
                                        created_at_index = list(existing_columns).index('created_at')
                                        if created_at_index < len(row):
                                            values['created_at'] = row[created_at_index]
                                            values['last_accessed'] = row[created_at_index]
                                    
                                    cursor.execute('''
                                        INSERT INTO projects (
                                            id, name, description, swagger_source_type, swagger_source_location,
                                            swagger_source_last_modified, base_url, auth_config, created_at, last_accessed,
                                            api_count, ui_state, tags, version, is_active, last_modified
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        values['id'], values['name'], values['description'], values['swagger_source_type'],
                                        values['swagger_source_location'], values['swagger_source_last_modified'],
                                        values['base_url'], values['auth_config'], values['created_at'], values['last_accessed'],
                                        values['api_count'], values['ui_state'], values['tags'], values['version'],
                                        values['is_active'], values['last_modified']
                                    ))
                    
                    # 创建其他表
                    for table_name, table_sql in self.schema.TABLES.items():
                        if table_name not in existing_tables:
                            cursor.execute(table_sql)
                    
                    # 创建索引、触发器、视图
                    for sql in self.schema.INDEXES + self.schema.TRIGGERS + self.schema.VIEWS:
                        try:
                            cursor.execute(sql)
                        except Exception as e:
                            if "already exists" not in str(e).lower():
                                logger.warning(f"创建对象时出错: {e}")
                    
                    # 插入初始数据
                    for sql in self.schema.INITIAL_DATA:
                        try:
                            cursor.execute(sql)
                        except Exception as e:
                            if "UNIQUE constraint failed" not in str(e):
                                logger.warning(f"插入初始数据时出错: {e}")
                
                else:
                    # 对于其他版本的迁移，直接执行语句
                    for sql_statement in script.sql_statements:
                        if sql_statement.strip():
                            cursor.execute(sql_statement)
            
            return True
            
        except Exception as e:
            logger.error(f"智能迁移执行失败: {e}")
            return False
    
    def execute_migration_plan(self, plan: MigrationPlan, backup_path: Optional[str] = None) -> Dict[str, Any]:
        """
        执行迁移计划
        
        Args:
            plan: 迁移计划
            backup_path: 备份文件路径
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        result = {
            'success': False,
            'executed_scripts': 0,
            'total_scripts': len(plan.scripts),
            'errors': [],
            'start_time': datetime.now(),
            'end_time': None,
            'backup_path': backup_path
        }
        
        try:
            logger.info(f"开始执行迁移计划: {plan.current_version} -> {plan.target_version}")
            
            # 创建备份
            if plan.backup_required and backup_path:
                backup_success = self.db_manager.backup_database(backup_path)
                if not backup_success:
                    result['errors'].append("数据库备份失败")
                    return result
                logger.info(f"数据库已备份到: {backup_path}")
            
            # 执行迁移脚本
            for i, script in enumerate(plan.scripts):
                try:
                    logger.info(f"执行迁移脚本 {i+1}/{len(plan.scripts)}: {script.description}")
                    
                    # 使用智能迁移执行
                    if self._execute_smart_migration(script):
                        result['executed_scripts'] += 1
                        logger.debug(f"迁移脚本执行成功: {script.from_version} -> {script.to_version}")
                    else:
                        error_msg = f"智能迁移执行失败 {script.from_version} -> {script.to_version}"
                        result['errors'].append(error_msg)
                        logger.error(error_msg)
                        break
                    
                except Exception as e:
                    error_msg = f"执行迁移脚本失败 {script.from_version} -> {script.to_version}: {e}"
                    result['errors'].append(error_msg)
                    logger.error(error_msg)
                    break
            
            # 更新版本信息
            if result['executed_scripts'] == result['total_scripts']:
                try:
                    schema_hash = self.calculate_schema_hash()
                    
                    # 检查database_info表是否有数据
                    existing_info = self.db_manager.execute_query("SELECT COUNT(*) FROM database_info")
                    if existing_info and existing_info[0][0] > 0:
                        # 更新现有记录
                        self.db_manager.execute_update('''
                            UPDATE database_info 
                            SET version = ?, last_migration = ?, schema_hash = ?, notes = ?
                        ''', (
                            plan.target_version,
                            datetime.now().isoformat(),
                            schema_hash,
                            f"Migrated from version {plan.current_version} to {plan.target_version}"
                        ))
                    else:
                        # 插入新记录
                        self.db_manager.execute_update('''
                            INSERT INTO database_info (version, created_at, last_migration, schema_hash, notes)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            plan.target_version,
                            datetime.now().isoformat(),
                            datetime.now().isoformat(),
                            schema_hash,
                            f"Migrated from version {plan.current_version} to {plan.target_version}"
                        ))
                    
                    result['success'] = True
                    logger.info(f"迁移完成: {plan.current_version} -> {plan.target_version}")
                    
                except Exception as e:
                    result['errors'].append(f"更新版本信息失败: {e}")
            
            result['end_time'] = datetime.now()
            return result
            
        except Exception as e:
            result['errors'].append(f"迁移执行异常: {e}")
            result['end_time'] = datetime.now()
            logger.error(f"迁移执行异常: {e}")
            return result
    
    def auto_upgrade_to_latest(self, backup_path: Optional[str] = None) -> Dict[str, Any]:
        """
        自动升级到最新版本
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            Dict[str, Any]: 升级结果
        """
        try:
            current_version = self.get_current_version()
            if current_version is None:
                current_version = 0
            
            if current_version >= self.current_schema_version:
                return {
                    'success': True,
                    'message': '数据库已是最新版本',
                    'current_version': current_version,
                    'target_version': self.current_schema_version
                }
            
            # 创建迁移计划
            plan = self.create_migration_plan(self.current_schema_version)
            if not plan:
                return {
                    'success': False,
                    'message': '无法创建迁移计划',
                    'current_version': current_version,
                    'target_version': self.current_schema_version
                }
            
            # 执行迁移
            result = self.execute_migration_plan(plan, backup_path)
            result['current_version'] = current_version
            result['target_version'] = self.current_schema_version
            
            return result
            
        except Exception as e:
            logger.error(f"自动升级失败: {e}")
            return {
                'success': False,
                'message': f'自动升级异常: {e}',
                'errors': [str(e)]
            }
    
    def get_version_info(self) -> Dict[str, Any]:
        """
        获取版本信息
        
        Returns:
            Dict[str, Any]: 版本信息
        """
        try:
            current_version = self.get_current_version()
            version_status = self.get_version_status()
            
            # 获取数据库信息
            db_info = self.db_manager.execute_query(
                "SELECT * FROM database_info ORDER BY version DESC LIMIT 1"
            )
            
            info = {
                'current_version': current_version,
                'latest_version': self.current_schema_version,
                'status': version_status.value,
                'schema_hash': self.calculate_schema_hash(),
                'upgrade_available': current_version < self.current_schema_version if current_version else True,
                'database_info': None
            }
            
            if db_info:
                row = db_info[0]
                info['database_info'] = {
                    'version': row[0],
                    'created_at': row[1],
                    'last_migration': row[2],
                    'schema_hash': row[3],
                    'notes': row[4] if len(row) > 4 else None
                }
            
            return info
            
        except Exception as e:
            logger.error(f"获取版本信息失败: {e}")
            return {
                'current_version': None,
                'latest_version': self.current_schema_version,
                'status': VersionStatus.UNKNOWN.value,
                'error': str(e)
            }
    
    def check_compatibility(self, required_version: int) -> Dict[str, Any]:
        """
        检查版本兼容性
        
        Args:
            required_version: 需要的最低版本
            
        Returns:
            Dict[str, Any]: 兼容性检查结果
        """
        try:
            current_version = self.get_current_version()
            
            result = {
                'compatible': False,
                'current_version': current_version,
                'required_version': required_version,
                'upgrade_needed': False,
                'can_upgrade': False,
                'message': ''
            }
            
            if current_version is None:
                result['message'] = '数据库未初始化'
                result['upgrade_needed'] = True
                result['can_upgrade'] = True
            elif current_version < required_version:
                result['message'] = f'数据库版本过低，需要升级到版本{required_version}'
                result['upgrade_needed'] = True
                result['can_upgrade'] = required_version <= self.current_schema_version
            elif current_version > self.current_schema_version:
                result['message'] = '数据库版本过高，应用程序需要升级'
                result['compatible'] = False
            else:
                result['compatible'] = True
                result['message'] = '版本兼容'
            
            return result
            
        except Exception as e:
            logger.error(f"检查版本兼容性失败: {e}")
            return {
                'compatible': False,
                'error': str(e),
                'message': f'兼容性检查异常: {e}'
            }