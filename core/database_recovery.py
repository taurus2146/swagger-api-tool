#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库恢复机制
提供数据库连接自动恢复、健康检查和故障转移功能
"""
import os
import sys
import time
import logging
import sqlite3
import threading
import shutil
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.exception_handler import (
    DatabaseException, DatabaseConnectionException, 
    DatabaseCorruptionException, ErrorContext
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY = "retry"
    BACKUP_RESTORE = "backup_restore"
    RECREATE = "recreate"
    FAILOVER = "failover"


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"


@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool
    strategy_used: RecoveryStrategy
    time_taken: float
    error_message: str = None
    backup_used: str = None


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    status: HealthStatus
    checks_passed: int
    checks_failed: int
    issues: List[str]
    recommendations: List[str]
    timestamp: str


class DatabaseHealthChecker:
    """数据库健康检查器"""
    
    def __init__(self):
        self.checks = []
        self._register_default_checks()
    
    def _register_default_checks(self):
        """注册默认检查项"""
        self.checks = [
            self._check_file_exists,
            self._check_file_readable,
            self._check_file_writable,
            self._check_database_integrity,
            self._check_schema_validity,
            self._check_connection_available,
            self._check_disk_space,
            self._check_file_permissions
        ]
    
    def check_health(self, db_path: str) -> HealthCheckResult:
        """
        执行健康检查
        Args:
            db_path: 数据库文件路径
        Returns:
            健康检查结果
        """
        logger.info(f"开始数据库健康检查: {db_path}")
        issues = []
        recommendations = []
        checks_passed = 0
        checks_failed = 0
        
        for check in self.checks:
            try:
                result = check(db_path)
                if result['passed']:
                    checks_passed += 1
                else:
                    checks_failed += 1
                    issues.append(result['issue'])
                    if result.get('recommendation'):
                        recommendations.append(result['recommendation'])
            except Exception as e:
                checks_failed += 1
                issues.append(f"检查失败: {check.__name__} - {e}")
        
        # 确定整体健康状态
        if checks_failed == 0:
            status = HealthStatus.HEALTHY
        elif checks_failed <= 2:
            status = HealthStatus.WARNING
        elif checks_failed <= 4:
            status = HealthStatus.CRITICAL
        else:
            status = HealthStatus.FAILED
        
        result = HealthCheckResult(
            status=status,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            issues=issues,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"健康检查完成: {status.value}, 通过 {checks_passed}/{checks_passed + checks_failed}")
        return result
    
    def _check_file_exists(self, db_path: str) -> Dict[str, Any]:
        """检查数据库文件是否存在"""
        exists = os.path.exists(db_path)
        return {
            'passed': exists,
            'issue': f"数据库文件不存在: {db_path}" if not exists else None,
            'recommendation': "检查数据库路径是否正确" if not exists else None
        }
    
    def _check_file_readable(self, db_path: str) -> Dict[str, Any]:
        """检查数据库文件是否可读"""
        if not os.path.exists(db_path):
            return {'passed': False, 'issue': "文件不存在，无法检查可读性"}
        
        readable = os.access(db_path, os.R_OK)
        return {
            'passed': readable,
            'issue': f"数据库文件不可读: {db_path}" if not readable else None,
            'recommendation': "检查文件权限" if not readable else None
        }
    
    def _check_file_writable(self, db_path: str) -> Dict[str, Any]:
        """检查数据库文件是否可写"""
        if not os.path.exists(db_path):
            # 检查目录是否可写
            dir_path = os.path.dirname(db_path)
            writable = os.access(dir_path, os.W_OK)
            return {
                'passed': writable,
                'issue': f"数据库目录不可写: {dir_path}" if not writable else None,
                'recommendation': "检查目录权限" if not writable else None
            }
        
        writable = os.access(db_path, os.W_OK)
        return {
            'passed': writable,
            'issue': f"数据库文件不可写: {db_path}" if not writable else None,
            'recommendation': "检查文件权限" if not writable else None
        }
    
    def _check_database_integrity(self, db_path: str) -> Dict[str, Any]:
        """检查数据库完整性"""
        if not os.path.exists(db_path):
            return {'passed': True, 'issue': None}  # 文件不存在时跳过此检查
        
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                if result and result[0] == "ok":
                    return {'passed': True, 'issue': None}
                else:
                    return {
                        'passed': False,
                        'issue': f"数据库完整性检查失败: {result[0] if result else '未知错误'}",
                        'recommendation': "考虑从备份恢复数据库"
                    }
        except Exception as e:
            return {
                'passed': False,
                'issue': f"无法执行完整性检查: {e}",
                'recommendation': "数据库可能已损坏，需要修复或恢复"
            }
    
    def _check_schema_validity(self, db_path: str) -> Dict[str, Any]:
        """检查数据库架构有效性"""
        if not os.path.exists(db_path):
            return {'passed': True, 'issue': None}
        
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                # 检查必要的表是否存在
                required_tables = ['projects', 'apis', 'global_config']
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                missing_tables = [table for table in required_tables if table not in existing_tables]
                if missing_tables:
                    return {
                        'passed': False,
                        'issue': f"缺少必要的表: {', '.join(missing_tables)}",
                        'recommendation': "重新初始化数据库架构"
                    }
                return {'passed': True, 'issue': None}
        except Exception as e:
            return {
                'passed': False,
                'issue': f"架构检查失败: {e}",
                'recommendation': "检查数据库架构完整性"
            }
    
    def _check_connection_available(self, db_path: str) -> Dict[str, Any]:
        """检查数据库连接是否可用"""
        if not os.path.exists(db_path):
            return {'passed': True, 'issue': None}
        
        try:
            with sqlite3.connect(db_path, timeout=5.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                return {'passed': True, 'issue': None}
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                return {
                    'passed': False,
                    'issue': "数据库被锁定",
                    'recommendation': "等待其他进程释放锁定或重启应用"
                }
            else:
                return {
                    'passed': False,
                    'issue': f"数据库连接失败: {e}",
                    'recommendation': "检查数据库状态和权限"
                }
        except Exception as e:
            return {
                'passed': False,
                'issue': f"连接测试失败: {e}",
                'recommendation': "检查数据库文件和配置"
            }
    
    def _check_disk_space(self, db_path: str) -> Dict[str, Any]:
        """检查磁盘空间"""
        try:
            if os.path.exists(db_path):
                dir_path = os.path.dirname(db_path)
            else:
                dir_path = os.path.dirname(db_path)
            
            # 获取磁盘使用情况
            if os.name == 'nt':  # Windows
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(dir_path), 
                    ctypes.pointer(free_bytes), 
                    None, 
                    None
                )
                free_space = free_bytes.value
            else:  # Unix/Linux
                statvfs = os.statvfs(dir_path)
                free_space = statvfs.f_frsize * statvfs.f_bavail
            
            # 检查是否有足够空间（至少100MB）
            min_space = 100 * 1024 * 1024  # 100MB
            if free_space < min_space:
                return {
                    'passed': False,
                    'issue': f"磁盘空间不足: 剩余 {free_space // (1024*1024)}MB",
                    'recommendation': "清理磁盘空间或移动数据库到其他位置"
                }
            
            # 警告空间不足（少于1GB）
            warning_space = 1024 * 1024 * 1024  # 1GB
            if free_space < warning_space:
                return {
                    'passed': True,
                    'issue': f"磁盘空间较少: 剩余 {free_space // (1024*1024)}MB",
                    'recommendation': "考虑清理磁盘空间"
                }
            
            return {'passed': True, 'issue': None}
        except Exception as e:
            return {
                'passed': False,
                'issue': f"磁盘空间检查失败: {e}",
                'recommendation': "手动检查磁盘空间"
            }
    
    def _check_file_permissions(self, db_path: str) -> Dict[str, Any]:
        """检查文件权限"""
        try:
            if os.path.exists(db_path):
                # 检查文件权限
                stat_info = os.stat(db_path)
                mode = stat_info.st_mode
                
                # 检查是否有读写权限
                if not (os.access(db_path, os.R_OK) and os.access(db_path, os.W_OK)):
                    return {
                        'passed': False,
                        'issue': "数据库文件权限不足",
                        'recommendation': "修改文件权限以允许读写访问"
                    }
            else:
                # 检查目录权限
                dir_path = os.path.dirname(db_path)
                if not os.access(dir_path, os.W_OK):
                    return {
                        'passed': False,
                        'issue': "数据库目录权限不足",
                        'recommendation': "修改目录权限以允许创建文件"
                    }
            
            return {'passed': True, 'issue': None}
        except Exception as e:
            return {
                'passed': False,
                'issue': f"权限检查失败: {e}",
                'recommendation': "手动检查文件和目录权限"
            }


class DatabaseRecoveryManager:
    """数据库恢复管理器"""
    
    def __init__(self, backup_dir: str = None):
        """
        初始化恢复管理器
        Args:
            backup_dir: 备份目录路径
        """
        self.backup_dir = backup_dir or os.path.join(os.getcwd(), 'backups')
        self.health_checker = DatabaseHealthChecker()
        self.recovery_strategies = {}
        self._lock = threading.Lock()
        
        # 注册默认恢复策略
        self._register_default_strategies()
        logger.info("数据库恢复管理器初始化完成")
    
    def _register_default_strategies(self):
        """注册默认恢复策略"""
        self.recovery_strategies = {
            'connection_retry': self._retry_connection_strategy,
            'backup_restore': self._backup_restore_strategy,
            'database_recreate': self._recreate_database_strategy,
            'corruption_repair': self._repair_corruption_strategy
        }
    
    def recover_database(self, db_path: str, strategy: RecoveryStrategy = None) -> RecoveryResult:
        """
        恢复数据库
        Args:
            db_path: 数据库文件路径
            strategy: 恢复策略
        Returns:
            恢复结果
        """
        start_time = time.time()
        logger.info(f"开始数据库恢复: {db_path}")
        
        with self._lock:
            try:
                # 首先进行健康检查
                health_result = self.health_checker.check_health(db_path)
                
                # 根据健康状态选择恢复策略
                if strategy is None:
                    strategy = self._select_recovery_strategy(health_result)
                
                # 执行恢复策略
                success = False
                error_message = None
                backup_used = None
                
                if strategy == RecoveryStrategy.RETRY:
                    success = self._retry_connection_strategy(db_path)
                elif strategy == RecoveryStrategy.BACKUP_RESTORE:
                    success, backup_used = self._backup_restore_strategy(db_path)
                elif strategy == RecoveryStrategy.RECREATE:
                    success = self._recreate_database_strategy(db_path)
                elif strategy == RecoveryStrategy.FAILOVER:
                    success = self._failover_strategy(db_path)
                
                time_taken = time.time() - start_time
                
                result = RecoveryResult(
                    success=success,
                    strategy_used=strategy,
                    time_taken=time_taken,
                    error_message=error_message,
                    backup_used=backup_used
                )
                
                logger.info(f"数据库恢复完成: {'成功' if success else '失败'}, 耗时 {time_taken:.2f}秒")
                return result
                
            except Exception as e:
                time_taken = time.time() - start_time
                logger.error(f"数据库恢复异常: {e}")
                return RecoveryResult(
                    success=False,
                    strategy_used=strategy or RecoveryStrategy.RETRY,
                    time_taken=time_taken,
                    error_message=str(e)
                )
    
    def _select_recovery_strategy(self, health_result: HealthCheckResult) -> RecoveryStrategy:
        """根据健康检查结果选择恢复策略"""
        if health_result.status == HealthStatus.HEALTHY:
            return RecoveryStrategy.RETRY
        elif health_result.status == HealthStatus.WARNING:
            return RecoveryStrategy.RETRY
        elif health_result.status == HealthStatus.CRITICAL:
            # 检查是否有损坏相关问题
            corruption_issues = [issue for issue in health_result.issues 
                               if 'corruption' in issue.lower() or 'malformed' in issue.lower()]
            if corruption_issues:
                return RecoveryStrategy.BACKUP_RESTORE
            else:
                return RecoveryStrategy.RETRY
        else:  # FAILED
            return RecoveryStrategy.BACKUP_RESTORE
    
    def _retry_connection_strategy(self, db_path: str, max_retries: int = 3) -> bool:
        """重试连接策略"""
        logger.info(f"执行重试连接策略: {db_path}")
        
        for attempt in range(max_retries):
            try:
                # 等待一段时间再重试
                if attempt > 0:
                    time.sleep(1.0 * attempt)
                
                # 尝试连接
                with sqlite3.connect(db_path, timeout=10.0) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                    logger.info(f"重试连接成功: 尝试 {attempt + 1}")
                    return True
                    
            except Exception as e:
                logger.warning(f"重试连接失败 {attempt + 1}: {e}")
        
        logger.error("重试连接策略失败")
        return False
    
    def _backup_restore_strategy(self, db_path: str) -> tuple[bool, str]:
        """备份恢复策略"""
        logger.info(f"执行备份恢复策略: {db_path}")
        
        try:
            # 查找最新的备份文件
            backup_file = self._find_latest_backup(db_path)
            if not backup_file:
                logger.error("未找到可用的备份文件")
                return False, None
            
            # 备份当前损坏的文件
            if os.path.exists(db_path):
                corrupted_backup = f"{db_path}.corrupted.{int(time.time())}"
                shutil.copy2(db_path, corrupted_backup)
                logger.info(f"已备份损坏文件: {corrupted_backup}")
            
            # 从备份恢复
            shutil.copy2(backup_file, db_path)
            logger.info(f"从备份恢复成功: {backup_file}")
            
            # 验证恢复的数据库
            health_result = self.health_checker.check_health(db_path)
            if health_result.status in [HealthStatus.HEALTHY, HealthStatus.WARNING]:
                return True, backup_file
            else:
                logger.error("恢复的数据库仍有问题")
                return False, backup_file
                
        except Exception as e:
            logger.error(f"备份恢复策略失败: {e}")
            return False, None
    
    def _recreate_database_strategy(self, db_path: str) -> bool:
        """重建数据库策略"""
        logger.info(f"执行重建数据库策略: {db_path}")
        
        try:
            # 备份现有文件（如果存在）
            if os.path.exists(db_path):
                backup_path = f"{db_path}.old.{int(time.time())}"
                shutil.move(db_path, backup_path)
                logger.info(f"已备份旧数据库: {backup_path}")
            
            # 创建新数据库
            from core.database_manager import DatabaseManager
            db_manager = DatabaseManager(db_path)
            db_manager.initialize_database()
            
            logger.info("数据库重建成功")
            return True
            
        except Exception as e:
            logger.error(f"重建数据库策略失败: {e}")
            return False
    
    def _failover_strategy(self, db_path: str) -> bool:
        """故障转移策略"""
        logger.info(f"执行故障转移策略: {db_path}")
        
        try:
            # 创建临时数据库
            temp_db_path = f"{db_path}.temp.{int(time.time())}"
            
            from core.database_manager import DatabaseManager
            temp_db_manager = DatabaseManager(temp_db_path)
            temp_db_manager.initialize_database()
            
            # 将临时数据库设为主数据库
            if os.path.exists(db_path):
                backup_path = f"{db_path}.failed.{int(time.time())}"
                shutil.move(db_path, backup_path)
            
            shutil.move(temp_db_path, db_path)
            logger.info("故障转移成功")
            return True
            
        except Exception as e:
            logger.error(f"故障转移策略失败: {e}")
            return False
    
    def _repair_corruption_strategy(self, db_path: str) -> bool:
        """修复损坏策略"""
        logger.info(f"执行修复损坏策略: {db_path}")
        
        try:
            # 尝试使用SQLite的.recover命令
            temp_db_path = f"{db_path}.recovered.{int(time.time())}"
            
            # 创建恢复脚本
            recovery_sql = f"""
            .open {temp_db_path}
            .recover {db_path}
            """
            
            # 这里需要调用sqlite3命令行工具
            # 由于Python的sqlite3模块不支持.recover命令，
            # 我们使用其他方法尝试恢复数据
            
            # 尝试读取可恢复的数据
            recovered_data = self._extract_recoverable_data(db_path)
            if recovered_data:
                # 创建新数据库并插入恢复的数据
                self._create_database_with_data(temp_db_path, recovered_data)
                
                # 替换原数据库
                backup_path = f"{db_path}.corrupted.{int(time.time())}"
                shutil.move(db_path, backup_path)
                shutil.move(temp_db_path, db_path)
                
                logger.info("数据库修复成功")
                return True
            else:
                logger.error("无法恢复任何数据")
                return False
                
        except Exception as e:
            logger.error(f"修复损坏策略失败: {e}")
            return False
    
    def _find_latest_backup(self, db_path: str) -> Optional[str]:
        """查找最新的备份文件"""
        try:
            if not os.path.exists(self.backup_dir):
                return None
            
            db_name = os.path.basename(db_path)
            backup_pattern = f"{db_name}.backup."
            
            backup_files = []
            for file in os.listdir(self.backup_dir):
                if file.startswith(backup_pattern):
                    backup_path = os.path.join(self.backup_dir, file)
                    backup_files.append((backup_path, os.path.getmtime(backup_path)))
            
            if backup_files:
                # 返回最新的备份文件
                latest_backup = max(backup_files, key=lambda x: x[1])
                return latest_backup[0]
            
            return None
        except Exception as e:
            logger.error(f"查找备份文件失败: {e}")
            return None
    
    def _extract_recoverable_data(self, db_path: str) -> Optional[Dict[str, List]]:
        """提取可恢复的数据"""
        try:
            recoverable_data = {}
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # 获取所有表名
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    try:
                        cursor.execute(f"SELECT * FROM {table}")
                        rows = cursor.fetchall()
                        
                        # 获取列信息
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = [col[1] for col in cursor.fetchall()]
                        
                        recoverable_data[table] = {
                            'columns': columns,
                            'rows': rows
                        }
                        logger.info(f"从表 {table} 恢复了 {len(rows)} 行数据")
                        
                    except Exception as e:
                        logger.warning(f"无法从表 {table} 恢复数据: {e}")
            
            return recoverable_data if recoverable_data else None
            
        except Exception as e:
            logger.error(f"提取可恢复数据失败: {e}")
            return None
    
    def _create_database_with_data(self, db_path: str, data: Dict[str, List]):
        """使用恢复的数据创建新数据库"""
        try:
            # 首先创建标准的数据库结构
            from core.database_manager import DatabaseManager
            db_manager = DatabaseManager(db_path)
            db_manager.initialize_database()
            
            # 插入恢复的数据
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                for table_name, table_data in data.items():
                    columns = table_data['columns']
                    rows = table_data['rows']
                    
                    if rows:
                        placeholders = ','.join(['?' for _ in columns])
                        insert_sql = f"INSERT OR REPLACE INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
                        
                        cursor.executemany(insert_sql, rows)
                        logger.info(f"向表 {table_name} 插入了 {len(rows)} 行数据")
                
                conn.commit()
            
            logger.info("使用恢复数据创建数据库成功")
            
        except Exception as e:
            logger.error(f"使用恢复数据创建数据库失败: {e}")
            raise


def main():
    """测试数据库恢复功能"""
    print("数据库恢复系统测试")
    print("=" * 50)
    
    # 创建测试数据库路径
    test_db_path = "test_recovery.db"
    
    # 创建恢复管理器
    recovery_manager = DatabaseRecoveryManager()
    
    # 执行健康检查
    print("\n1. 执行健康检查:")
    health_result = recovery_manager.health_checker.check_health(test_db_path)
    print(f"健康状态: {health_result.status.value}")
    print(f"通过检查: {health_result.checks_passed}")
    print(f"失败检查: {health_result.checks_failed}")
    
    if health_result.issues:
        print("发现问题:")
        for issue in health_result.issues:
            print(f"  - {issue}")
    
    if health_result.recommendations:
        print("建议:")
        for rec in health_result.recommendations:
            print(f"  - {rec}")
    
    # 测试恢复功能
    print("\n2. 测试数据库恢复:")
    recovery_result = recovery_manager.recover_database(test_db_path)
    print(f"恢复结果: {'成功' if recovery_result.success else '失败'}")
    print(f"使用策略: {recovery_result.strategy_used.value}")
    print(f"耗时: {recovery_result.time_taken:.2f}秒")
    
    if recovery_result.error_message:
        print(f"错误信息: {recovery_result.error_message}")
    
    # 清理测试文件
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    print("\n测试完成!")


if __name__ == "__main__":
    main()