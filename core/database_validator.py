#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库验证和修复工具
提供数据完整性检查、损坏数据修复、一致性验证和数据库优化功能
"""

import os
import json
import logging
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """验证级别枚举"""
    BASIC = "basic"          # 基本检查
    STANDARD = "standard"    # 标准检查
    THOROUGH = "thorough"    # 彻底检查


class IssueType(Enum):
    """问题类型枚举"""
    MISSING_TABLE = "missing_table"
    MISSING_INDEX = "missing_index"
    MISSING_TRIGGER = "missing_trigger"
    MISSING_VIEW = "missing_view"
    ORPHANED_RECORD = "orphaned_record"
    INVALID_DATA = "invalid_data"
    CONSTRAINT_VIOLATION = "constraint_violation"
    PERFORMANCE_ISSUE = "performance_issue"
    CORRUPTION = "corruption"


class IssueSeverity(Enum):
    """问题严重程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """验证问题"""
    issue_type: IssueType
    severity: IssueSeverity
    table: Optional[str]
    column: Optional[str]
    description: str
    details: Dict[str, Any]
    auto_fixable: bool = False
    fix_sql: Optional[str] = None


@dataclass
class ValidationResult:
    """验证结果"""
    success: bool
    total_checks: int
    passed_checks: int
    failed_checks: int
    issues: List[ValidationIssue]
    start_time: datetime
    end_time: datetime
    duration: float
    
    @property
    def has_critical_issues(self) -> bool:
        """是否有严重问题"""
        return any(issue.severity == IssueSeverity.CRITICAL for issue in self.issues)
    
    @property
    def has_high_issues(self) -> bool:
        """是否有高级问题"""
        return any(issue.severity == IssueSeverity.HIGH for issue in self.issues)


class DatabaseValidator:
    """数据库验证器"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        初始化验证器
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
        self.issues = []
        
    def validate_database(self, level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationResult:
        """
        验证数据库
        
        Args:
            level: 验证级别
            
        Returns:
            ValidationResult: 验证结果
        """
        start_time = datetime.now()
        self.issues = []
        
        logger.info(f"开始数据库验证，级别: {level.value}")
        
        # 执行不同级别的检查
        checks = []
        
        if level in [ValidationLevel.BASIC, ValidationLevel.STANDARD, ValidationLevel.THOROUGH]:
            checks.extend([
                self._check_database_structure,
                self._check_data_integrity,
                self._check_foreign_keys
            ])
        
        if level in [ValidationLevel.STANDARD, ValidationLevel.THOROUGH]:
            checks.extend([
                self._check_data_consistency,
                self._check_orphaned_records,
                self._check_constraint_violations
            ])
        
        if level == ValidationLevel.THOROUGH:
            checks.extend([
                self._check_performance_issues,
                self._check_data_corruption,
                self._analyze_table_statistics
            ])
        
        # 执行检查
        total_checks = len(checks)
        passed_checks = 0
        
        for check in checks:
            try:
                if check():
                    passed_checks += 1
                logger.debug(f"检查完成: {check.__name__}")
            except Exception as e:
                logger.error(f"检查失败 {check.__name__}: {e}")
                self.issues.append(ValidationIssue(
                    issue_type=IssueType.CORRUPTION,
                    severity=IssueSeverity.HIGH,
                    table=None,
                    column=None,
                    description=f"检查过程异常: {check.__name__}",
                    details={'error': str(e)}
                ))
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result = ValidationResult(
            success=len(self.issues) == 0,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=total_checks - passed_checks,
            issues=self.issues.copy(),
            start_time=start_time,
            end_time=end_time,
            duration=duration
        )
        
        logger.info(f"数据库验证完成，发现 {len(self.issues)} 个问题")
        return result
    
    def _check_database_structure(self) -> bool:
        """检查数据库结构"""
        logger.debug("检查数据库结构")
        
        try:
            # 获取版本管理器
            version_manager = self.db_manager.get_version_manager()
            
            # 验证schema完整性
            integrity_result = version_manager.verify_schema_integrity()
            
            if not integrity_result['valid']:
                for issue in integrity_result['issues']:
                    self.issues.append(ValidationIssue(
                        issue_type=IssueType.MISSING_TABLE,
                        severity=IssueSeverity.HIGH,
                        table=None,
                        column=None,
                        description=f"Schema完整性问题: {issue}",
                        details=integrity_result
                    ))
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查数据库结构失败: {e}")
            return False
    
    def _check_data_integrity(self) -> bool:
        """检查数据完整性"""
        logger.debug("检查数据完整性")
        
        try:
            # 检查projects表的数据完整性
            result = self.db_manager.execute_query('''
                SELECT id, name, created_at, last_accessed 
                FROM projects 
                WHERE id IS NULL OR name IS NULL OR name = '' 
                   OR created_at IS NULL OR last_accessed IS NULL
            ''')
            
            if result:
                for row in result:
                    self.issues.append(ValidationIssue(
                        issue_type=IssueType.INVALID_DATA,
                        severity=IssueSeverity.MEDIUM,
                        table='projects',
                        column=None,
                        description=f"项目记录缺少必需字段: {row[0]}",
                        details={'record': dict(row)},
                        auto_fixable=True,
                        fix_sql="DELETE FROM projects WHERE id IS NULL OR name IS NULL OR name = ''"
                    ))
            
            # 检查日期字段的有效性
            result = self.db_manager.execute_query('''
                SELECT id, created_at, last_accessed 
                FROM projects 
                WHERE created_at > last_accessed
            ''')
            
            if result:
                for row in result:
                    self.issues.append(ValidationIssue(
                        issue_type=IssueType.INVALID_DATA,
                        severity=IssueSeverity.LOW,
                        table='projects',
                        column='last_accessed',
                        description=f"项目最后访问时间早于创建时间: {row[0]}",
                        details={'record': dict(row)},
                        auto_fixable=True,
                        fix_sql=f"UPDATE projects SET last_accessed = created_at WHERE id = '{row[0]}'"
                    ))
            
            return len([issue for issue in self.issues if issue.table == 'projects']) == 0
            
        except Exception as e:
            logger.error(f"检查数据完整性失败: {e}")
            return False
    
    def _check_foreign_keys(self) -> bool:
        """检查外键约束"""
        logger.debug("检查外键约束")
        
        try:
            # 检查project_history表的外键
            result = self.db_manager.execute_query('''
                SELECT h.id, h.project_id 
                FROM project_history h 
                LEFT JOIN projects p ON h.project_id = p.id 
                WHERE p.id IS NULL
            ''')
            
            if result:
                for row in result:
                    self.issues.append(ValidationIssue(
                        issue_type=IssueType.ORPHANED_RECORD,
                        severity=IssueSeverity.MEDIUM,
                        table='project_history',
                        column='project_id',
                        description=f"历史记录引用不存在的项目: {row[1]}",
                        details={'history_id': row[0], 'project_id': row[1]},
                        auto_fixable=True,
                        fix_sql=f"DELETE FROM project_history WHERE project_id = '{row[1]}'"
                    ))
            
            # 检查api_cache表的外键
            result = self.db_manager.execute_query('''
                SELECT c.id, c.project_id 
                FROM api_cache c 
                LEFT JOIN projects p ON c.project_id = p.id 
                WHERE p.id IS NULL
            ''')
            
            if result:
                for row in result:
                    self.issues.append(ValidationIssue(
                        issue_type=IssueType.ORPHANED_RECORD,
                        severity=IssueSeverity.LOW,
                        table='api_cache',
                        column='project_id',
                        description=f"缓存记录引用不存在的项目: {row[1]}",
                        details={'cache_id': row[0], 'project_id': row[1]},
                        auto_fixable=True,
                        fix_sql=f"DELETE FROM api_cache WHERE project_id = '{row[1]}'"
                    ))
            
            return len([issue for issue in self.issues if issue.issue_type == IssueType.ORPHANED_RECORD]) == 0
            
        except Exception as e:
            logger.error(f"检查外键约束失败: {e}")
            return False
    
    def _check_data_consistency(self) -> bool:
        """检查数据一致性"""
        logger.debug("检查数据一致性")
        
        try:
            # 检查项目API数量与实际记录的一致性
            result = self.db_manager.execute_query('''
                SELECT p.id, p.name, p.api_count, 
                       COALESCE(cache_count.count, 0) as actual_count
                FROM projects p
                LEFT JOIN (
                    SELECT project_id, COUNT(*) as count 
                    FROM api_cache 
                    GROUP BY project_id
                ) cache_count ON p.id = cache_count.project_id
                WHERE p.api_count != COALESCE(cache_count.count, 0)
            ''')
            
            if result:
                for row in result:
                    self.issues.append(ValidationIssue(
                        issue_type=IssueType.INVALID_DATA,
                        severity=IssueSeverity.LOW,
                        table='projects',
                        column='api_count',
                        description=f"项目API数量不一致: {row[1]} (记录:{row[2]}, 实际:{row[3]})",
                        details={'project_id': row[0], 'recorded': row[2], 'actual': row[3]},
                        auto_fixable=True,
                        fix_sql=f"UPDATE projects SET api_count = {row[3]} WHERE id = '{row[0]}'"
                    ))
            
            return True
            
        except Exception as e:
            logger.error(f"检查数据一致性失败: {e}")
            return False
    
    def _check_orphaned_records(self) -> bool:
        """检查孤立记录"""
        logger.debug("检查孤立记录")
        
        try:
            # 检查过期的缓存记录
            result = self.db_manager.execute_query('''
                SELECT id, project_id, expires_at 
                FROM api_cache 
                WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
            ''')
            
            if result:
                expired_count = len(result)
                self.issues.append(ValidationIssue(
                    issue_type=IssueType.ORPHANED_RECORD,
                    severity=IssueSeverity.LOW,
                    table='api_cache',
                    column='expires_at',
                    description=f"发现 {expired_count} 个过期的缓存记录",
                    details={'count': expired_count},
                    auto_fixable=True,
                    fix_sql="DELETE FROM api_cache WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP"
                ))
            
            return True
            
        except Exception as e:
            logger.error(f"检查孤立记录失败: {e}")
            return False
    
    def _check_constraint_violations(self) -> bool:
        """检查约束违反"""
        logger.debug("检查约束违反")
        
        try:
            # 检查项目版本约束
            result = self.db_manager.execute_query('''
                SELECT id, name, version 
                FROM projects 
                WHERE version IS NULL OR version <= 0
            ''')
            
            if result:
                for row in result:
                    self.issues.append(ValidationIssue(
                        issue_type=IssueType.CONSTRAINT_VIOLATION,
                        severity=IssueSeverity.MEDIUM,
                        table='projects',
                        column='version',
                        description=f"项目版本违反约束: {row[1]} (版本: {row[2]})",
                        details={'project_id': row[0], 'version': row[2]},
                        auto_fixable=True,
                        fix_sql=f"UPDATE projects SET version = 1 WHERE id = '{row[0]}'"
                    ))
            
            # 检查API数量约束
            result = self.db_manager.execute_query('''
                SELECT id, name, api_count 
                FROM projects 
                WHERE api_count < 0
            ''')
            
            if result:
                for row in result:
                    self.issues.append(ValidationIssue(
                        issue_type=IssueType.CONSTRAINT_VIOLATION,
                        severity=IssueSeverity.MEDIUM,
                        table='projects',
                        column='api_count',
                        description=f"项目API数量违反约束: {row[1]} (数量: {row[2]})",
                        details={'project_id': row[0], 'api_count': row[2]},
                        auto_fixable=True,
                        fix_sql=f"UPDATE projects SET api_count = 0 WHERE id = '{row[0]}'"
                    ))
            
            return True
            
        except Exception as e:
            logger.error(f"检查约束违反失败: {e}")
            return False
    
    def _check_performance_issues(self) -> bool:
        """检查性能问题"""
        logger.debug("检查性能问题")
        
        try:
            # 检查缺失的索引使用情况
            result = self.db_manager.execute_query('''
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name LIKE 'idx_%'
            ''')
            
            existing_indexes = {row[0] for row in result} if result else set()
            
            # 检查是否有推荐的索引缺失
            recommended_indexes = {
                'idx_projects_name',
                'idx_projects_last_accessed',
                'idx_projects_created_at',
                'idx_history_project_id',
                'idx_cache_project_id'
            }
            
            missing_indexes = recommended_indexes - existing_indexes
            if missing_indexes:
                self.issues.append(ValidationIssue(
                    issue_type=IssueType.PERFORMANCE_ISSUE,
                    severity=IssueSeverity.LOW,
                    table=None,
                    column=None,
                    description=f"缺少推荐的索引: {', '.join(missing_indexes)}",
                    details={'missing_indexes': list(missing_indexes)},
                    auto_fixable=False
                ))
            
            # 检查表统计信息
            result = self.db_manager.execute_query('''
                SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'
            ''')
            
            if result:
                for row in result:
                    table_name = row[0]
                    count_result = self.db_manager.execute_query(f'SELECT COUNT(*) FROM {table_name}')
                    if count_result and count_result[0][0] > 10000:
                        self.issues.append(ValidationIssue(
                            issue_type=IssueType.PERFORMANCE_ISSUE,
                            severity=IssueSeverity.LOW,
                            table=table_name,
                            column=None,
                            description=f"表 {table_name} 记录数量较大: {count_result[0][0]}",
                            details={'record_count': count_result[0][0]},
                            auto_fixable=False
                        ))
            
            return True
            
        except Exception as e:
            logger.error(f"检查性能问题失败: {e}")
            return False
    
    def _check_data_corruption(self) -> bool:
        """检查数据损坏"""
        logger.debug("检查数据损坏")
        
        try:
            # 使用SQLite的PRAGMA integrity_check
            result = self.db_manager.execute_query('PRAGMA integrity_check')
            
            if result:
                for row in result:
                    if row[0] != 'ok':
                        self.issues.append(ValidationIssue(
                            issue_type=IssueType.CORRUPTION,
                            severity=IssueSeverity.CRITICAL,
                            table=None,
                            column=None,
                            description=f"数据库完整性检查失败: {row[0]}",
                            details={'integrity_check': row[0]},
                            auto_fixable=False
                        ))
                        return False
            
            # 检查JSON字段的有效性
            result = self.db_manager.execute_query('''
                SELECT id, name, auth_config, ui_state, tags 
                FROM projects 
                WHERE auth_config IS NOT NULL OR ui_state IS NOT NULL OR tags IS NOT NULL
            ''')
            
            if result:
                for row in result:
                    project_id, name, auth_config, ui_state, tags = row
                    
                    # 检查JSON字段
                    for field_name, field_value in [('auth_config', auth_config), ('ui_state', ui_state), ('tags', tags)]:
                        if field_value:
                            try:
                                json.loads(field_value)
                            except json.JSONDecodeError:
                                self.issues.append(ValidationIssue(
                                    issue_type=IssueType.INVALID_DATA,
                                    severity=IssueSeverity.MEDIUM,
                                    table='projects',
                                    column=field_name,
                                    description=f"项目 {name} 的 {field_name} 字段包含无效JSON",
                                    details={'project_id': project_id, 'field': field_name},
                                    auto_fixable=True,
                                    fix_sql=f"UPDATE projects SET {field_name} = NULL WHERE id = '{project_id}'"
                                ))
            
            return True
            
        except Exception as e:
            logger.error(f"检查数据损坏失败: {e}")
            return False
    
    def _analyze_table_statistics(self) -> bool:
        """分析表统计信息"""
        logger.debug("分析表统计信息")
        
        try:
            # 分析表大小和记录数
            tables = ['projects', 'project_history', 'api_cache', 'global_config', 'user_preferences']
            
            for table in tables:
                try:
                    # 获取记录数
                    count_result = self.db_manager.execute_query(f'SELECT COUNT(*) FROM {table}')
                    record_count = count_result[0][0] if count_result else 0
                    
                    # 获取表信息
                    info_result = self.db_manager.execute_query(f'PRAGMA table_info({table})')
                    column_count = len(info_result) if info_result else 0
                    
                    logger.debug(f"表 {table}: {record_count} 条记录, {column_count} 个字段")
                    
                    # 如果表为空但应该有数据，标记为问题
                    if table == 'global_config' and record_count == 0:
                        self.issues.append(ValidationIssue(
                            issue_type=IssueType.INVALID_DATA,
                            severity=IssueSeverity.MEDIUM,
                            table=table,
                            column=None,
                            description=f"表 {table} 为空，可能缺少初始数据",
                            details={'record_count': record_count},
                            auto_fixable=False
                        ))
                
                except Exception as e:
                    logger.warning(f"分析表 {table} 失败: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"分析表统计信息失败: {e}")
            return False
    
    def auto_fix_issues(self, issues: List[ValidationIssue] = None) -> Dict[str, Any]:
        """
        自动修复问题
        
        Args:
            issues: 要修复的问题列表，如果为None则修复所有可修复的问题
            
        Returns:
            Dict[str, Any]: 修复结果
        """
        if issues is None:
            issues = [issue for issue in self.issues if issue.auto_fixable]
        else:
            issues = [issue for issue in issues if issue.auto_fixable]
        
        if not issues:
            return {
                'success': True,
                'message': '没有可自动修复的问题',
                'fixed_count': 0,
                'failed_count': 0,
                'errors': []
            }
        
        logger.info(f"开始自动修复 {len(issues)} 个问题")
        
        fixed_count = 0
        failed_count = 0
        errors = []
        
        try:
            with self.db_manager.transaction() as cursor:
                for issue in issues:
                    try:
                        if issue.fix_sql:
                            cursor.execute(issue.fix_sql)
                            fixed_count += 1
                            logger.debug(f"修复问题: {issue.description}")
                        else:
                            logger.warning(f"问题缺少修复SQL: {issue.description}")
                            failed_count += 1
                    
                    except Exception as e:
                        error_msg = f"修复问题失败 '{issue.description}': {e}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        failed_count += 1
            
            result = {
                'success': failed_count == 0,
                'message': f'修复完成: {fixed_count} 个成功, {failed_count} 个失败',
                'fixed_count': fixed_count,
                'failed_count': failed_count,
                'errors': errors
            }
            
            logger.info(result['message'])
            return result
            
        except Exception as e:
            error_msg = f"自动修复过程异常: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg,
                'fixed_count': 0,
                'failed_count': len(issues),
                'errors': [error_msg]
            }
    
    def optimize_database(self) -> Dict[str, Any]:
        """
        优化数据库
        
        Returns:
            Dict[str, Any]: 优化结果
        """
        logger.info("开始数据库优化")
        
        operations = []
        errors = []
        
        try:
            # 1. 清理过期缓存
            result = self.db_manager.execute_query('''
                SELECT COUNT(*) FROM api_cache 
                WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
            ''')
            
            if result and result[0][0] > 0:
                expired_count = result[0][0]
                if self.db_manager.execute_update('''
                    DELETE FROM api_cache 
                    WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
                '''):
                    operations.append(f"清理了 {expired_count} 个过期缓存记录")
                else:
                    errors.append("清理过期缓存失败")
            
            # 2. 更新统计信息
            if self.db_manager.execute_update('ANALYZE'):
                operations.append("更新了数据库统计信息")
            else:
                errors.append("更新统计信息失败")
            
            # 3. 重建索引
            result = self.db_manager.execute_query('''
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name LIKE 'idx_%'
            ''')
            
            if result:
                for row in result:
                    index_name = row[0]
                    if self.db_manager.execute_update(f'REINDEX {index_name}'):
                        operations.append(f"重建索引: {index_name}")
                    else:
                        errors.append(f"重建索引失败: {index_name}")
            
            # 4. 压缩数据库
            if self.db_manager.execute_update('VACUUM'):
                operations.append("压缩了数据库文件")
            else:
                errors.append("数据库压缩失败")
            
            result = {
                'success': len(errors) == 0,
                'message': f'优化完成: {len(operations)} 个操作成功, {len(errors)} 个失败',
                'operations': operations,
                'errors': errors
            }
            
            logger.info(result['message'])
            return result
            
        except Exception as e:
            error_msg = f"数据库优化异常: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg,
                'operations': operations,
                'errors': errors + [error_msg]
            }
    
    def get_database_health_report(self) -> Dict[str, Any]:
        """
        获取数据库健康报告
        
        Returns:
            Dict[str, Any]: 健康报告
        """
        logger.info("生成数据库健康报告")
        
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'database_info': {},
                'table_statistics': {},
                'performance_metrics': {},
                'recommendations': []
            }
            
            # 数据库基本信息
            db_info = self.db_manager.get_connection_info()
            report['database_info'] = {
                'file_path': db_info.get('db_path'),
                'file_size_bytes': db_info.get('file_size', 0),
                'file_size_mb': round(db_info.get('file_size', 0) / 1024 / 1024, 2),
                'is_connected': db_info.get('is_connected'),
                'version': db_info.get('version'),
                'table_count': db_info.get('table_count'),
                'record_count': db_info.get('record_count')
            }
            
            # 表统计信息
            tables = ['projects', 'project_history', 'api_cache', 'global_config', 'user_preferences']
            for table in tables:
                try:
                    count_result = self.db_manager.execute_query(f'SELECT COUNT(*) FROM {table}')
                    record_count = count_result[0][0] if count_result else 0
                    
                    report['table_statistics'][table] = {
                        'record_count': record_count
                    }
                    
                    # 如果是projects表，获取更多统计信息
                    if table == 'projects' and record_count > 0:
                        stats = self.db_manager.execute_query('''
                            SELECT 
                                COUNT(*) as total,
                                COUNT(CASE WHEN is_active = 1 THEN 1 END) as active,
                                AVG(api_count) as avg_api_count,
                                MAX(last_accessed) as last_activity
                            FROM projects
                        ''')
                        
                        if stats:
                            stat_row = stats[0]
                            report['table_statistics'][table].update({
                                'active_projects': stat_row[1],
                                'inactive_projects': stat_row[0] - stat_row[1],
                                'avg_api_count': round(stat_row[2] or 0, 2),
                                'last_activity': stat_row[3]
                            })
                
                except Exception as e:
                    logger.warning(f"获取表 {table} 统计信息失败: {e}")
            
            # 性能指标
            try:
                # 检查索引使用情况
                index_result = self.db_manager.execute_query('''
                    SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'
                ''')
                
                report['performance_metrics']['index_count'] = index_result[0][0] if index_result else 0
                
                # 检查缓存命中率（如果有缓存数据）
                cache_result = self.db_manager.execute_query('SELECT COUNT(*) FROM api_cache')
                report['performance_metrics']['cache_entries'] = cache_result[0][0] if cache_result else 0
                
            except Exception as e:
                logger.warning(f"获取性能指标失败: {e}")
            
            # 生成建议
            recommendations = []
            
            # 基于文件大小的建议
            file_size_mb = report['database_info']['file_size_mb']
            if file_size_mb > 100:
                recommendations.append("数据库文件较大，建议定期清理过期数据")
            
            # 基于记录数的建议
            total_records = sum(stats.get('record_count', 0) for stats in report['table_statistics'].values())
            if total_records > 50000:
                recommendations.append("数据库记录数较多，建议优化查询和索引")
            
            # 基于缓存的建议
            cache_count = report['performance_metrics'].get('cache_entries', 0)
            if cache_count > 10000:
                recommendations.append("API缓存记录较多，建议清理过期缓存")
            
            # 基于项目活跃度的建议
            project_stats = report['table_statistics'].get('projects', {})
            if project_stats.get('inactive_projects', 0) > project_stats.get('active_projects', 0):
                recommendations.append("非活跃项目较多，建议清理或归档")
            
            report['recommendations'] = recommendations
            
            return report
            
        except Exception as e:
            logger.error(f"生成健康报告失败: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'database_info': {},
                'table_statistics': {},
                'performance_metrics': {},
                'recommendations': ['无法生成完整报告，请检查数据库连接']
            }