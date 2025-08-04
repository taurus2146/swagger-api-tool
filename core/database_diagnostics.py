#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库诊断和维护工具
提供数据库健康检查、性能诊断和自动维护功能
"""
import os
import sys
import sqlite3
import time
import logging
import threading
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """健康状态"""
    EXCELLENT = "excellent"
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"


class MaintenanceType(Enum):
    """维护类型"""
    VACUUM = "vacuum"
    REINDEX = "reindex"
    ANALYZE = "analyze"
    INTEGRITY_CHECK = "integrity_check"
    OPTIMIZE = "optimize"
    CLEANUP = "cleanup"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    overall_status: HealthStatus
    score: int  # 0-100
    checks_performed: int
    checks_passed: int
    checks_failed: int
    issues: List[str]
    recommendations: List[str]
    performance_metrics: Dict[str, Any]
    timestamp: str
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class PerformanceMetrics:
    """性能指标"""
    database_size: int
    page_count: int
    page_size: int
    fragmentation_ratio: float
    index_usage_ratio: float
    query_performance_score: int
    cache_hit_ratio: float
    connection_count: int
    average_query_time: float
    slow_queries_count: int
    timestamp: str
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class MaintenanceTask:
    """维护任务"""
    task_id: str
    task_type: MaintenanceType
    name: str
    description: str
    priority: int  # 1-10, 10 is highest
    estimated_duration: int  # seconds
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    enabled: bool = True
    auto_run: bool = False


class DatabaseHealthChecker:
    """数据库健康检查器"""
    
    def __init__(self):
        self.checks = [
            self._check_database_size,
            self._check_fragmentation,
            self._check_index_usage,
            self._check_query_performance,
            self._check_connection_health,
            self._check_disk_space,
            self._check_backup_status,
            self._check_schema_integrity
        ]
    
    def perform_health_check(self, db_path: str) -> HealthCheckResult:
        """
        执行完整的健康检查
        Args:
            db_path: 数据库文件路径
        Returns:
            健康检查结果
        """
        logger.info(f"开始数据库健康检查: {db_path}")
        
        issues = []
        recommendations = []
        performance_metrics = {}
        checks_passed = 0
        checks_failed = 0
        
        if not os.path.exists(db_path):
            return HealthCheckResult(
                overall_status=HealthStatus.FAILED,
                score=0,
                checks_performed=1,
                checks_passed=0,
                checks_failed=1,
                issues=["数据库文件不存在"],
                recommendations=["检查数据库路径或从备份恢复"],
                performance_metrics={},
                timestamp=datetime.now().isoformat()
            )
        
        # 执行各项检查
        for check in self.checks:
            try:
                result = check(db_path)
                if result['passed']:
                    checks_passed += 1
                else:
                    checks_failed += 1
                    issues.extend(result.get('issues', []))
                    recommendations.extend(result.get('recommendations', []))
                
                # 收集性能指标
                if 'metrics' in result:
                    performance_metrics.update(result['metrics'])
                    
            except Exception as e:
                checks_failed += 1
                issues.append(f"检查失败: {check.__name__} - {e}")
                logger.error(f"健康检查失败: {check.__name__} - {e}")
        
        # 计算总体健康分数
        total_checks = checks_passed + checks_failed
        score = int((checks_passed / total_checks) * 100) if total_checks > 0 else 0
        
        # 根据分数确定健康状态
        if score >= 90:
            overall_status = HealthStatus.EXCELLENT
        elif score >= 75:
            overall_status = HealthStatus.GOOD
        elif score >= 60:
            overall_status = HealthStatus.WARNING
        elif score >= 30:
            overall_status = HealthStatus.CRITICAL
        else:
            overall_status = HealthStatus.FAILED
        
        result = HealthCheckResult(
            overall_status=overall_status,
            score=score,
            checks_performed=total_checks,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            issues=issues,
            recommendations=recommendations,
            performance_metrics=performance_metrics,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"健康检查完成: {overall_status.value}, 分数: {score}")
        return result
    
    def _check_database_size(self, db_path: str) -> Dict[str, Any]:
        """检查数据库大小"""
        try:
            size = os.path.getsize(db_path)
            size_mb = size / (1024 * 1024)
            
            issues = []
            recommendations = []
            
            # 检查大小是否合理
            if size_mb > 1000:  # 大于1GB
                issues.append(f"数据库文件较大: {size_mb:.2f} MB")
                recommendations.append("考虑数据归档或分库")
            elif size_mb > 500:  # 大于500MB
                recommendations.append("监控数据库增长趋势")
            
            return {
                'passed': len(issues) == 0,
                'issues': issues,
                'recommendations': recommendations,
                'metrics': {
                    'database_size_bytes': size,
                    'database_size_mb': size_mb
                }
            }
        except Exception as e:
            return {
                'passed': False,
                'issues': [f"无法获取数据库大小: {e}"],
                'recommendations': ["检查文件权限"]
            }
    
    def _check_fragmentation(self, db_path: str) -> Dict[str, Any]:
        """检查数据库碎片化"""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # 获取页面信息
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA freelist_count")
                freelist_count = cursor.fetchone()[0]
                
                # 计算碎片化比率
                fragmentation_ratio = (freelist_count / page_count) * 100 if page_count > 0 else 0
                
                issues = []
                recommendations = []
                
                if fragmentation_ratio > 20:
                    issues.append(f"数据库碎片化严重: {fragmentation_ratio:.2f}%")
                    recommendations.append("运行 VACUUM 命令整理数据库")
                elif fragmentation_ratio > 10:
                    recommendations.append("考虑定期运行 VACUUM 命令")
                
                return {
                    'passed': fragmentation_ratio <= 20,
                    'issues': issues,
                    'recommendations': recommendations,
                    'metrics': {
                        'page_count': page_count,
                        'page_size': page_size,
                        'freelist_count': freelist_count,
                        'fragmentation_ratio': fragmentation_ratio
                    }
                }
        except Exception as e:
            return {
                'passed': False,
                'issues': [f"碎片化检查失败: {e}"],
                'recommendations': ["检查数据库连接"]
            }
    
    def _check_index_usage(self, db_path: str) -> Dict[str, Any]:
        """检查索引使用情况"""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # 获取所有索引
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
                indexes = [row[0] for row in cursor.fetchall()]
                
                # 获取表信息
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                issues = []
                recommendations = []
                
                # 检查是否有足够的索引
                if len(indexes) < len(tables):
                    recommendations.append("考虑为常用查询字段添加索引")
                
                # 检查索引是否过多
                if len(indexes) > len(tables) * 3:
                    issues.append("索引数量可能过多，影响写入性能")
                    recommendations.append("检查并删除不必要的索引")
                
                index_usage_ratio = (len(indexes) / len(tables)) if len(tables) > 0 else 0
                
                return {
                    'passed': len(issues) == 0,
                    'issues': issues,
                    'recommendations': recommendations,
                    'metrics': {
                        'index_count': len(indexes),
                        'table_count': len(tables),
                        'index_usage_ratio': index_usage_ratio
                    }
                }
        except Exception as e:
            return {
                'passed': False,
                'issues': [f"索引检查失败: {e}"],
                'recommendations': ["检查数据库结构"]
            }
    
    def _check_query_performance(self, db_path: str) -> Dict[str, Any]:
        """检查查询性能"""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # 执行一些测试查询来评估性能
                test_queries = [
                    "SELECT COUNT(*) FROM sqlite_master",
                    "SELECT name FROM sqlite_master WHERE type='table'",
                    "PRAGMA table_info(sqlite_master)"
                ]
                
                total_time = 0
                query_count = 0
                
                for query in test_queries:
                    try:
                        start_time = time.time()
                        cursor.execute(query)
                        cursor.fetchall()
                        end_time = time.time()
                        
                        query_time = end_time - start_time
                        total_time += query_time
                        query_count += 1
                    except Exception:
                        continue
                
                average_query_time = total_time / query_count if query_count > 0 else 0
                
                issues = []
                recommendations = []
                
                if average_query_time > 1.0:  # 超过1秒
                    issues.append(f"查询性能较慢: 平均 {average_query_time:.3f} 秒")
                    recommendations.append("检查查询优化和索引使用")
                elif average_query_time > 0.1:  # 超过100毫秒
                    recommendations.append("监控查询性能趋势")
                
                # 简单的性能评分 (0-100)
                if average_query_time < 0.01:
                    performance_score = 100
                elif average_query_time < 0.1:
                    performance_score = 90
                elif average_query_time < 0.5:
                    performance_score = 70
                elif average_query_time < 1.0:
                    performance_score = 50
                else:
                    performance_score = 30
                
                return {
                    'passed': average_query_time <= 1.0,
                    'issues': issues,
                    'recommendations': recommendations,
                    'metrics': {
                        'average_query_time': average_query_time,
                        'query_performance_score': performance_score,
                        'test_queries_count': query_count
                    }
                }
        except Exception as e:
            return {
                'passed': False,
                'issues': [f"性能检查失败: {e}"],
                'recommendations': ["检查数据库状态"]
            }
    
    def _check_connection_health(self, db_path: str) -> Dict[str, Any]:
        """检查连接健康状况"""
        try:
            # 测试连接
            start_time = time.time()
            with sqlite3.connect(db_path, timeout=5.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
            end_time = time.time()
            
            connection_time = end_time - start_time
            
            issues = []
            recommendations = []
            
            if connection_time > 2.0:
                issues.append(f"数据库连接较慢: {connection_time:.3f} 秒")
                recommendations.append("检查数据库锁定状态")
            elif connection_time > 0.5:
                recommendations.append("监控连接性能")
            
            return {
                'passed': connection_time <= 2.0,
                'issues': issues,
                'recommendations': recommendations,
                'metrics': {
                    'connection_time': connection_time,
                    'connection_timeout': 5.0
                }
            }
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                return {
                    'passed': False,
                    'issues': ["数据库被锁定"],
                    'recommendations': ["等待其他进程释放锁定或重启应用"]
                }
            else:
                return {
                    'passed': False,
                    'issues': [f"连接失败: {e}"],
                    'recommendations': ["检查数据库文件和权限"]
                }
        except Exception as e:
            return {
                'passed': False,
                'issues': [f"连接检查失败: {e}"],
                'recommendations': ["检查数据库配置"]
            }
    
    def _check_disk_space(self, db_path: str) -> Dict[str, Any]:
        """检查磁盘空间"""
        try:
            # 获取数据库所在目录
            db_dir = os.path.dirname(os.path.abspath(db_path))
            
            # 获取磁盘使用情况
            if os.name == 'nt':  # Windows
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(db_dir),
                    ctypes.pointer(free_bytes),
                    ctypes.pointer(total_bytes),
                    None
                )
                free_space = free_bytes.value
                total_space = total_bytes.value
            else:  # Unix/Linux
                statvfs = os.statvfs(db_dir)
                free_space = statvfs.f_frsize * statvfs.f_bavail
                total_space = statvfs.f_frsize * statvfs.f_blocks
            
            free_space_mb = free_space / (1024 * 1024)
            total_space_mb = total_space / (1024 * 1024)
            usage_ratio = ((total_space - free_space) / total_space) * 100
            
            issues = []
            recommendations = []
            
            if free_space_mb < 100:  # 少于100MB
                issues.append(f"磁盘空间不足: 剩余 {free_space_mb:.2f} MB")
                recommendations.append("清理磁盘空间或移动数据库")
            elif free_space_mb < 500:  # 少于500MB
                recommendations.append("监控磁盘空间使用情况")
            
            if usage_ratio > 95:
                issues.append(f"磁盘使用率过高: {usage_ratio:.1f}%")
            
            return {
                'passed': free_space_mb >= 100 and usage_ratio <= 95,
                'issues': issues,
                'recommendations': recommendations,
                'metrics': {
                    'free_space_mb': free_space_mb,
                    'total_space_mb': total_space_mb,
                    'disk_usage_ratio': usage_ratio
                }
            }
        except Exception as e:
            return {
                'passed': False,
                'issues': [f"磁盘空间检查失败: {e}"],
                'recommendations': ["手动检查磁盘空间"]
            }
    
    def _check_backup_status(self, db_path: str) -> Dict[str, Any]:
        """检查备份状态"""
        try:
            # 查找备份文件
            db_dir = os.path.dirname(db_path)
            db_name = os.path.basename(db_path)
            backup_dir = os.path.join(db_dir, 'backups')
            
            backup_files = []
            if os.path.exists(backup_dir):
                for file in os.listdir(backup_dir):
                    if file.startswith(f"{db_name}.backup."):
                        backup_path = os.path.join(backup_dir, file)
                        backup_files.append({
                            'path': backup_path,
                            'mtime': os.path.getmtime(backup_path)
                        })
            
            issues = []
            recommendations = []
            
            if not backup_files:
                issues.append("未找到数据库备份文件")
                recommendations.append("创建数据库备份")
            else:
                # 检查最新备份的时间
                latest_backup = max(backup_files, key=lambda x: x['mtime'])
                backup_age = time.time() - latest_backup['mtime']
                backup_age_hours = backup_age / 3600
                
                if backup_age_hours > 168:  # 超过7天
                    issues.append(f"备份文件过旧: {backup_age_hours:.1f} 小时前")
                    recommendations.append("创建新的数据库备份")
                elif backup_age_hours > 24:  # 超过1天
                    recommendations.append("考虑更频繁的备份策略")
            
            return {
                'passed': len(issues) == 0,
                'issues': issues,
                'recommendations': recommendations,
                'metrics': {
                    'backup_count': len(backup_files),
                    'latest_backup_age_hours': backup_age_hours if backup_files else None
                }
            }
        except Exception as e:
            return {
                'passed': False,
                'issues': [f"备份状态检查失败: {e}"],
                'recommendations': ["检查备份配置"]
            }
    
    def _check_schema_integrity(self, db_path: str) -> Dict[str, Any]:
        """检查架构完整性"""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # 检查必要的表
                required_tables = ['projects', 'apis', 'global_config']
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                missing_tables = [table for table in required_tables if table not in existing_tables]
                
                issues = []
                recommendations = []
                
                if missing_tables:
                    issues.append(f"缺少必要的表: {', '.join(missing_tables)}")
                    recommendations.append("重新初始化数据库架构")
                
                # 检查外键约束
                cursor.execute("PRAGMA foreign_key_check")
                fk_violations = cursor.fetchall()
                
                if fk_violations:
                    issues.append(f"发现 {len(fk_violations)} 个外键约束违反")
                    recommendations.append("修复数据一致性问题")
                
                return {
                    'passed': len(issues) == 0,
                    'issues': issues,
                    'recommendations': recommendations,
                    'metrics': {
                        'table_count': len(existing_tables),
                        'missing_tables_count': len(missing_tables),
                        'fk_violations_count': len(fk_violations)
                    }
                }
        except Exception as e:
            return {
                'passed': False,
                'issues': [f"架构检查失败: {e}"],
                'recommendations': ["检查数据库结构"]
            }


class DatabaseMaintenanceManager:
    """数据库维护管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.maintenance_tasks = self._initialize_maintenance_tasks()
        self._lock = threading.Lock()
    
    def _initialize_maintenance_tasks(self) -> List[MaintenanceTask]:
        """初始化维护任务"""
        return [
            MaintenanceTask(
                task_id="vacuum",
                task_type=MaintenanceType.VACUUM,
                name="数据库整理",
                description="清理数据库碎片，回收未使用空间",
                priority=8,
                estimated_duration=300,
                auto_run=True
            ),
            MaintenanceTask(
                task_id="reindex",
                task_type=MaintenanceType.REINDEX,
                name="重建索引",
                description="重建所有索引以提高查询性能",
                priority=6,
                estimated_duration=120,
                auto_run=True
            ),
            MaintenanceTask(
                task_id="analyze",
                task_type=MaintenanceType.ANALYZE,
                name="统计信息更新",
                description="更新查询优化器统计信息",
                priority=5,
                estimated_duration=60,
                auto_run=True
            ),
            MaintenanceTask(
                task_id="integrity_check",
                task_type=MaintenanceType.INTEGRITY_CHECK,
                name="完整性检查",
                description="检查数据库完整性",
                priority=9,
                estimated_duration=180,
                auto_run=False
            ),
            MaintenanceTask(
                task_id="optimize",
                task_type=MaintenanceType.OPTIMIZE,
                name="性能优化",
                description="执行综合性能优化",
                priority=7,
                estimated_duration=240,
                auto_run=False
            )
        ]
    
    def run_maintenance_task(self, task_id: str) -> Dict[str, Any]:
        """
        运行维护任务
        Args:
            task_id: 任务ID
        Returns:
            执行结果
        """
        task = self._find_task(task_id)
        if not task:
            return {
                'success': False,
                'error': f'未找到任务: {task_id}'
            }
        
        if not task.enabled:
            return {
                'success': False,
                'error': f'任务已禁用: {task_id}'
            }
        
        logger.info(f"开始执行维护任务: {task.name}")
        start_time = time.time()
        
        try:
            with self._lock:
                if task.task_type == MaintenanceType.VACUUM:
                    result = self._run_vacuum()
                elif task.task_type == MaintenanceType.REINDEX:
                    result = self._run_reindex()
                elif task.task_type == MaintenanceType.ANALYZE:
                    result = self._run_analyze()
                elif task.task_type == MaintenanceType.INTEGRITY_CHECK:
                    result = self._run_integrity_check()
                elif task.task_type == MaintenanceType.OPTIMIZE:
                    result = self._run_optimize()
                else:
                    result = {
                        'success': False,
                        'error': f'未知的任务类型: {task.task_type}'
                    }
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 更新任务执行时间
            task.last_run = datetime.now().isoformat()
            
            result.update({
                'task_id': task_id,
                'task_name': task.name,
                'duration': duration,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"维护任务完成: {task.name}, 耗时: {duration:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f"维护任务失败: {task.name} - {e}")
            return {
                'success': False,
                'error': str(e),
                'task_id': task_id,
                'task_name': task.name,
                'timestamp': datetime.now().isoformat()
            }
    
    def run_auto_maintenance(self) -> Dict[str, Any]:
        """运行自动维护任务"""
        logger.info("开始自动维护")
        
        auto_tasks = [task for task in self.maintenance_tasks if task.auto_run and task.enabled]
        auto_tasks.sort(key=lambda x: x.priority, reverse=True)  # 按优先级排序
        
        results = []
        total_duration = 0
        
        for task in auto_tasks:
            result = self.run_maintenance_task(task.task_id)
            results.append(result)
            
            if result['success']:
                total_duration += result.get('duration', 0)
        
        successful_tasks = [r for r in results if r['success']]
        failed_tasks = [r for r in results if not r['success']]
        
        return {
            'success': len(failed_tasks) == 0,
            'total_tasks': len(auto_tasks),
            'successful_tasks': len(successful_tasks),
            'failed_tasks': len(failed_tasks),
            'total_duration': total_duration,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def _find_task(self, task_id: str) -> Optional[MaintenanceTask]:
        """查找维护任务"""
        for task in self.maintenance_tasks:
            if task.task_id == task_id:
                return task
        return None
    
    def _run_vacuum(self) -> Dict[str, Any]:
        """运行VACUUM命令"""
        try:
            # 获取VACUUM前的数据库大小
            size_before = os.path.getsize(self.db_path)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("VACUUM")
            
            # 获取VACUUM后的数据库大小
            size_after = os.path.getsize(self.db_path)
            space_saved = size_before - size_after
            
            return {
                'success': True,
                'message': 'VACUUM执行成功',
                'details': {
                    'size_before_mb': size_before / (1024 * 1024),
                    'size_after_mb': size_after / (1024 * 1024),
                    'space_saved_mb': space_saved / (1024 * 1024)
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'VACUUM执行失败: {e}'
            }
    
    def _run_reindex(self) -> Dict[str, Any]:
        """重建索引"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取所有索引
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
                indexes = [row[0] for row in cursor.fetchall()]
                
                # 重建每个索引
                for index in indexes:
                    cursor.execute(f"REINDEX {index}")
                
                return {
                    'success': True,
                    'message': '索引重建成功',
                    'details': {
                        'indexes_rebuilt': len(indexes),
                        'index_names': indexes
                    }
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'索引重建失败: {e}'
            }
    
    def _run_analyze(self) -> Dict[str, Any]:
        """更新统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取所有表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # 为每个表运行ANALYZE
                for table in tables:
                    cursor.execute(f"ANALYZE {table}")
                
                return {
                    'success': True,
                    'message': '统计信息更新成功',
                    'details': {
                        'tables_analyzed': len(tables),
                        'table_names': tables
                    }
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'统计信息更新失败: {e}'
            }
    
    def _run_integrity_check(self) -> Dict[str, Any]:
        """运行完整性检查"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 运行完整性检查
                cursor.execute("PRAGMA integrity_check")
                results = cursor.fetchall()
                
                issues = []
                for result in results:
                    if result[0] != "ok":
                        issues.append(result[0])
                
                return {
                    'success': len(issues) == 0,
                    'message': '完整性检查完成',
                    'details': {
                        'issues_found': len(issues),
                        'issues': issues
                    }
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'完整性检查失败: {e}'
            }
    
    def _run_optimize(self) -> Dict[str, Any]:
        """运行综合优化"""
        try:
            results = []
            
            # 运行VACUUM
            vacuum_result = self._run_vacuum()
            results.append(('VACUUM', vacuum_result))
            
            # 重建索引
            reindex_result = self._run_reindex()
            results.append(('REINDEX', reindex_result))
            
            # 更新统计信息
            analyze_result = self._run_analyze()
            results.append(('ANALYZE', analyze_result))
            
            # 检查成功的操作数量
            successful_ops = sum(1 for _, result in results if result['success'])
            
            return {
                'success': successful_ops == len(results),
                'message': f'优化完成，{successful_ops}/{len(results)} 个操作成功',
                'details': {
                    'operations': results,
                    'successful_operations': successful_ops,
                    'total_operations': len(results)
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'优化执行失败: {e}'
            }
    
    def get_maintenance_schedule(self) -> List[Dict[str, Any]]:
        """获取维护计划"""
        schedule = []
        for task in self.maintenance_tasks:
            schedule.append({
                'task_id': task.task_id,
                'name': task.name,
                'description': task.description,
                'priority': task.priority,
                'estimated_duration': task.estimated_duration,
                'last_run': task.last_run,
                'next_run': task.next_run,
                'enabled': task.enabled,
                'auto_run': task.auto_run
            })
        return schedule
    
    def update_task_settings(self, task_id: str, settings: Dict[str, Any]) -> bool:
        """更新任务设置"""
        task = self._find_task(task_id)
        if not task:
            return False
        
        if 'enabled' in settings:
            task.enabled = settings['enabled']
        if 'auto_run' in settings:
            task.auto_run = settings['auto_run']
        if 'priority' in settings:
            task.priority = settings['priority']
        
        return True


def main():
    """测试诊断和维护工具"""
    print("数据库诊断和维护工具测试")
    print("=" * 50)
    
    # 创建测试数据库
    test_db_path = "test_diagnostics.db"
    
    try:
        # 创建简单的测试数据库
        with sqlite3.connect(test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            cursor.execute("INSERT INTO test (name) VALUES ('test1'), ('test2')")
            conn.commit()
        
        print("✓ 测试数据库创建成功")
        
        # 测试健康检查
        health_checker = DatabaseHealthChecker()
        health_result = health_checker.perform_health_check(test_db_path)
        
        print(f"✓ 健康检查完成: {health_result.overall_status.value}")
        print(f"  健康分数: {health_result.score}/100")
        print(f"  检查项目: {health_result.checks_performed}")
        print(f"  通过: {health_result.checks_passed}, 失败: {health_result.checks_failed}")
        
        # 测试维护管理器
        maintenance_manager = DatabaseMaintenanceManager(test_db_path)
        
        # 运行单个维护任务
        vacuum_result = maintenance_manager.run_maintenance_task("vacuum")
        if vacuum_result['success']:
            print("✓ VACUUM任务执行成功")
        else:
            print(f"❌ VACUUM任务失败: {vacuum_result.get('error')}")
        
        # 运行自动维护
        auto_result = maintenance_manager.run_auto_maintenance()
        print(f"✓ 自动维护完成: {auto_result['successful_tasks']}/{auto_result['total_tasks']} 任务成功")
        
        # 获取维护计划
        schedule = maintenance_manager.get_maintenance_schedule()
        print(f"✓ 维护计划包含 {len(schedule)} 个任务")
        
    finally:
        # 清理测试文件
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
    
    print("\n测试完成!")


if __name__ == "__main__":
    main()