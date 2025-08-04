#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据恢复功能
提供数据库损坏检测、数据恢复向导和数据库重建工具
"""
import os
import sys
import sqlite3
import shutil
import logging
import threading
import time
import json
from typing import Dict, Any, Optional, List, Tuple, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import exception classes directly to avoid import issues
class DatabaseException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class DatabaseCorruptionException(DatabaseException):
    def __init__(self, message: str):
        super().__init__(message)

class ErrorContext:
    def __init__(self, operation: str, component: str):
        self.operation = operation
        self.component = component

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RecoveryStatus(Enum):
    """恢复状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CorruptionLevel(Enum):
    """损坏程度"""
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    TOTAL = "total"


@dataclass
class RecoveryProgress:
    """恢复进度信息"""
    status: RecoveryStatus
    current_step: str
    total_steps: int
    completed_steps: int
    progress_percentage: float
    estimated_time_remaining: Optional[float] = None
    error_message: Optional[str] = None
    
    def update_progress(self, step: str, completed: int, total: int):
        """更新进度"""
        self.current_step = step
        self.completed_steps = completed
        self.total_steps = total
        self.progress_percentage = (completed / total) * 100 if total > 0 else 0


@dataclass
class CorruptionReport:
    """损坏报告"""
    database_path: str
    corruption_level: CorruptionLevel
    corrupted_tables: List[str]
    recoverable_tables: List[str]
    total_records: int
    recoverable_records: int
    issues_found: List[str]
    recommendations: List[str]
    timestamp: str
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class DatabaseCorruptionDetector:
    """数据库损坏检测器"""
    
    def __init__(self):
        self.integrity_checks = [
            self._check_database_integrity,
            self._check_schema_consistency,
            self._check_foreign_key_constraints,
            self._check_index_integrity,
            self._check_table_structure
        ]
    
    def detect_corruption(self, db_path: str) -> CorruptionReport:
        """
        检测数据库损坏
        Args:
            db_path: 数据库文件路径
        Returns:
            损坏报告
        """
        logger.info(f"开始检测数据库损坏: {db_path}")
        
        if not os.path.exists(db_path):
            return CorruptionReport(
                database_path=db_path,
                corruption_level=CorruptionLevel.TOTAL,
                corrupted_tables=[],
                recoverable_tables=[],
                total_records=0,
                recoverable_records=0,
                issues_found=["数据库文件不存在"],
                recommendations=["从备份恢复或重新创建数据库"],
                timestamp=datetime.now().isoformat()
            )
        
        issues_found = []
        corrupted_tables = []
        recoverable_tables = []
        total_records = 0
        recoverable_records = 0
        
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # 获取所有表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                all_tables = [row[0] for row in cursor.fetchall()]
                
                # 执行各种完整性检查
                for check in self.integrity_checks:
                    try:
                        check_result = check(cursor, all_tables)
                        issues_found.extend(check_result.get('issues', []))
                        corrupted_tables.extend(check_result.get('corrupted_tables', []))
                        recoverable_tables.extend(check_result.get('recoverable_tables', []))
                    except Exception as e:
                        issues_found.append(f"检查失败: {check.__name__} - {e}")
                
                # 统计记录数
                for table in all_tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        total_records += count
                        
                        if table not in corrupted_tables:
                            recoverable_records += count
                    except Exception as e:
                        issues_found.append(f"无法统计表 {table} 的记录数: {e}")
                        corrupted_tables.append(table)
        
        except Exception as e:
            issues_found.append(f"无法连接到数据库: {e}")
            corruption_level = CorruptionLevel.TOTAL
        else:
            # 确定损坏程度
            corruption_level = self._determine_corruption_level(
                len(issues_found), len(corrupted_tables), len(all_tables)
            )
        
        # 去重
        corrupted_tables = list(set(corrupted_tables))
        recoverable_tables = list(set(recoverable_tables) - set(corrupted_tables))
        
        # 生成建议
        recommendations = self._generate_recommendations(corruption_level, issues_found)
        
        report = CorruptionReport(
            database_path=db_path,
            corruption_level=corruption_level,
            corrupted_tables=corrupted_tables,
            recoverable_tables=recoverable_tables,
            total_records=total_records,
            recoverable_records=recoverable_records,
            issues_found=issues_found,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"损坏检测完成: {corruption_level.value}, 发现 {len(issues_found)} 个问题")
        return report
    
    def _check_database_integrity(self, cursor: sqlite3.Cursor, tables: List[str]) -> Dict[str, Any]:
        """检查数据库完整性"""
        result = {'issues': [], 'corrupted_tables': [], 'recoverable_tables': []}
        
        try:
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchall()
            
            for row in integrity_result:
                if row[0] != "ok":
                    result['issues'].append(f"完整性检查失败: {row[0]}")
                    # 尝试从错误信息中提取表名
                    if "in table" in row[0].lower():
                        table_name = self._extract_table_name(row[0])
                        if table_name:
                            result['corrupted_tables'].append(table_name)
        except Exception as e:
            result['issues'].append(f"完整性检查异常: {e}")
        
        return result
    
    def _check_schema_consistency(self, cursor: sqlite3.Cursor, tables: List[str]) -> Dict[str, Any]:
        """检查架构一致性"""
        result = {'issues': [], 'corrupted_tables': [], 'recoverable_tables': []}
        
        try:
            # 检查必要的表是否存在
            required_tables = ['projects', 'apis', 'global_config']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                result['issues'].append(f"缺少必要的表: {', '.join(missing_tables)}")
                result['corrupted_tables'].extend(missing_tables)
            
            # 检查表结构
            for table in tables:
                try:
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = cursor.fetchall()
                    if not columns:
                        result['issues'].append(f"表 {table} 没有列定义")
                        result['corrupted_tables'].append(table)
                    else:
                        result['recoverable_tables'].append(table)
                except Exception as e:
                    result['issues'].append(f"无法获取表 {table} 的结构: {e}")
                    result['corrupted_tables'].append(table)
        
        except Exception as e:
            result['issues'].append(f"架构检查异常: {e}")
        
        return result
    
    def _check_foreign_key_constraints(self, cursor: sqlite3.Cursor, tables: List[str]) -> Dict[str, Any]:
        """检查外键约束"""
        result = {'issues': [], 'corrupted_tables': [], 'recoverable_tables': []}
        
        try:
            cursor.execute("PRAGMA foreign_key_check")
            fk_violations = cursor.fetchall()
            
            for violation in fk_violations:
                table_name = violation[0]
                result['issues'].append(f"外键约束违反: 表 {table_name}")
                result['corrupted_tables'].append(table_name)
        
        except Exception as e:
            result['issues'].append(f"外键检查异常: {e}")
        
        return result
    
    def _check_index_integrity(self, cursor: sqlite3.Cursor, tables: List[str]) -> Dict[str, Any]:
        """检查索引完整性"""
        result = {'issues': [], 'corrupted_tables': [], 'recoverable_tables': []}
        
        try:
            # 获取所有索引
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            for index in indexes:
                try:
                    cursor.execute(f"REINDEX {index}")
                except Exception as e:
                    result['issues'].append(f"索引 {index} 损坏: {e}")
        
        except Exception as e:
            result['issues'].append(f"索引检查异常: {e}")
        
        return result
    
    def _check_table_structure(self, cursor: sqlite3.Cursor, tables: List[str]) -> Dict[str, Any]:
        """检查表结构"""
        result = {'issues': [], 'corrupted_tables': [], 'recoverable_tables': []}
        
        for table in tables:
            try:
                # 尝试查询表
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                cursor.fetchone()
                result['recoverable_tables'].append(table)
            except Exception as e:
                result['issues'].append(f"表 {table} 无法访问: {e}")
                result['corrupted_tables'].append(table)
        
        return result
    
    def _extract_table_name(self, error_message: str) -> Optional[str]:
        """从错误信息中提取表名"""
        # 简单的表名提取逻辑
        words = error_message.split()
        for i, word in enumerate(words):
            if word.lower() == "table" and i + 1 < len(words):
                return words[i + 1].strip("'\"")
        return None
    
    def _determine_corruption_level(self, issue_count: int, corrupted_table_count: int, total_table_count: int) -> CorruptionLevel:
        """确定损坏程度"""
        if issue_count == 0:
            return CorruptionLevel.NONE
        elif corrupted_table_count == 0:
            return CorruptionLevel.MINOR
        elif corrupted_table_count < total_table_count * 0.3:
            return CorruptionLevel.MINOR
        elif corrupted_table_count < total_table_count * 0.7:
            return CorruptionLevel.MODERATE
        elif corrupted_table_count < total_table_count:
            return CorruptionLevel.SEVERE
        else:
            return CorruptionLevel.TOTAL
    
    def _generate_recommendations(self, corruption_level: CorruptionLevel, issues: List[str]) -> List[str]:
        """生成恢复建议"""
        recommendations = []
        
        if corruption_level == CorruptionLevel.NONE:
            recommendations.append("数据库状态良好，无需恢复")
        elif corruption_level == CorruptionLevel.MINOR:
            recommendations.extend([
                "运行数据库优化",
                "重建索引",
                "检查并修复外键约束"
            ])
        elif corruption_level == CorruptionLevel.MODERATE:
            recommendations.extend([
                "从最近的备份恢复损坏的表",
                "导出可恢复的数据",
                "重建数据库结构"
            ])
        elif corruption_level == CorruptionLevel.SEVERE:
            recommendations.extend([
                "立即从备份恢复",
                "如无备份，尝试部分数据恢复",
                "考虑重新创建数据库"
            ])
        else:  # TOTAL
            recommendations.extend([
                "从备份完全恢复数据库",
                "如无备份，重新创建数据库",
                "检查存储设备健康状况"
            ])
        
        return recommendations


class DataRecoveryWizard:
    """数据恢复向导"""
    
    def __init__(self, backup_dir: str = None):
        self.backup_dir = backup_dir or os.path.join(os.getcwd(), 'backups')
        self.detector = DatabaseCorruptionDetector()
        self.progress_callback = None
        self._lock = threading.Lock()
    
    def set_progress_callback(self, callback: Callable[[RecoveryProgress], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def start_recovery_wizard(self, db_path: str) -> Dict[str, Any]:
        """
        启动恢复向导
        Args:
            db_path: 数据库文件路径
        Returns:
            恢复向导结果
        """
        logger.info(f"启动数据恢复向导: {db_path}")
        
        # 初始化进度
        progress = RecoveryProgress(
            status=RecoveryStatus.IN_PROGRESS,
            current_step="检测数据库损坏",
            total_steps=5,
            completed_steps=0,
            progress_percentage=0.0
        )
        self._update_progress(progress)
        
        try:
            # 步骤1: 检测损坏
            corruption_report = self.detector.detect_corruption(db_path)
            progress.update_progress("分析损坏程度", 1, 5)
            self._update_progress(progress)
            
            # 步骤2: 分析恢复选项
            recovery_options = self._analyze_recovery_options(db_path, corruption_report)
            progress.update_progress("生成恢复选项", 2, 5)
            self._update_progress(progress)
            
            # 步骤3: 查找备份
            available_backups = self._find_available_backups(db_path)
            progress.update_progress("查找可用备份", 3, 5)
            self._update_progress(progress)
            
            # 步骤4: 生成恢复计划
            recovery_plan = self._generate_recovery_plan(corruption_report, recovery_options, available_backups)
            progress.update_progress("生成恢复计划", 4, 5)
            self._update_progress(progress)
            
            # 步骤5: 完成分析
            progress.update_progress("完成分析", 5, 5)
            progress.status = RecoveryStatus.COMPLETED
            self._update_progress(progress)
            
            result = {
                'success': True,
                'corruption_report': corruption_report,
                'recovery_options': recovery_options,
                'available_backups': available_backups,
                'recovery_plan': recovery_plan,
                'progress': progress
            }
            
            logger.info("数据恢复向导完成")
            return result
            
        except Exception as e:
            progress.status = RecoveryStatus.FAILED
            progress.error_message = str(e)
            self._update_progress(progress)
            
            logger.error(f"数据恢复向导失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'progress': progress
            }
    
    def execute_recovery_plan(self, db_path: str, recovery_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行恢复计划
        Args:
            db_path: 数据库文件路径
            recovery_plan: 恢复计划
        Returns:
            恢复结果
        """
        logger.info(f"执行数据恢复计划: {db_path}")
        
        strategy = recovery_plan.get('strategy')
        total_steps = len(recovery_plan.get('steps', []))
        
        progress = RecoveryProgress(
            status=RecoveryStatus.IN_PROGRESS,
            current_step="开始恢复",
            total_steps=total_steps,
            completed_steps=0,
            progress_percentage=0.0
        )
        self._update_progress(progress)
        
        try:
            if strategy == 'backup_restore':
                return self._execute_backup_restore(db_path, recovery_plan, progress)
            elif strategy == 'partial_recovery':
                return self._execute_partial_recovery(db_path, recovery_plan, progress)
            elif strategy == 'database_rebuild':
                return self._execute_database_rebuild(db_path, recovery_plan, progress)
            else:
                raise ValueError(f"未知的恢复策略: {strategy}")
                
        except Exception as e:
            progress.status = RecoveryStatus.FAILED
            progress.error_message = str(e)
            self._update_progress(progress)
            
            logger.error(f"恢复计划执行失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'progress': progress
            }
    
    def _analyze_recovery_options(self, db_path: str, corruption_report: CorruptionReport) -> List[Dict[str, Any]]:
        """分析恢复选项"""
        options = []
        
        if corruption_report.corruption_level == CorruptionLevel.NONE:
            options.append({
                'type': 'no_action',
                'name': '无需恢复',
                'description': '数据库状态良好',
                'risk': 'low',
                'estimated_time': 0
            })
        
        if corruption_report.corruption_level in [CorruptionLevel.MINOR, CorruptionLevel.MODERATE]:
            options.append({
                'type': 'repair',
                'name': '修复数据库',
                'description': '尝试修复损坏的部分',
                'risk': 'medium',
                'estimated_time': 300  # 5分钟
            })
        
        if corruption_report.recoverable_records > 0:
            options.append({
                'type': 'partial_recovery',
                'name': '部分数据恢复',
                'description': f'恢复 {corruption_report.recoverable_records} 条可用记录',
                'risk': 'medium',
                'estimated_time': 600  # 10分钟
            })
        
        options.append({
            'type': 'backup_restore',
            'name': '从备份恢复',
            'description': '使用最近的备份完全恢复',
            'risk': 'low',
            'estimated_time': 180  # 3分钟
        })
        
        options.append({
            'type': 'rebuild',
            'name': '重建数据库',
            'description': '创建新的空数据库',
            'risk': 'high',
            'estimated_time': 60  # 1分钟
        })
        
        return options
    
    def _find_available_backups(self, db_path: str) -> List[Dict[str, Any]]:
        """查找可用备份"""
        backups = []
        
        if not os.path.exists(self.backup_dir):
            return backups
        
        db_name = os.path.basename(db_path)
        backup_pattern = f"{db_name}.backup."
        
        try:
            for file in os.listdir(self.backup_dir):
                if file.startswith(backup_pattern):
                    backup_path = os.path.join(self.backup_dir, file)
                    stat_info = os.stat(backup_path)
                    
                    backups.append({
                        'path': backup_path,
                        'filename': file,
                        'size': stat_info.st_size,
                        'created_time': datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                        'modified_time': datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                    })
            
            # 按修改时间排序，最新的在前
            backups.sort(key=lambda x: x['modified_time'], reverse=True)
            
        except Exception as e:
            logger.warning(f"查找备份文件失败: {e}")
        
        return backups
    
    def _generate_recovery_plan(self, corruption_report: CorruptionReport, 
                               recovery_options: List[Dict[str, Any]], 
                               available_backups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成恢复计划"""
        plan = {
            'strategy': 'backup_restore',
            'steps': [],
            'estimated_time': 0,
            'risk_level': 'medium'
        }
        
        # 根据损坏程度选择策略
        if corruption_report.corruption_level == CorruptionLevel.NONE:
            plan['strategy'] = 'no_action'
            plan['steps'] = ['验证数据库完整性']
            plan['estimated_time'] = 30
            plan['risk_level'] = 'low'
            
        elif corruption_report.corruption_level in [CorruptionLevel.MINOR, CorruptionLevel.MODERATE]:
            if available_backups:
                plan['strategy'] = 'backup_restore'
                plan['steps'] = [
                    '备份当前数据库',
                    '从备份恢复',
                    '验证恢复结果'
                ]
                plan['estimated_time'] = 300
                plan['risk_level'] = 'low'
            else:
                plan['strategy'] = 'partial_recovery'
                plan['steps'] = [
                    '导出可恢复数据',
                    '重建数据库结构',
                    '导入恢复的数据',
                    '验证数据完整性'
                ]
                plan['estimated_time'] = 600
                plan['risk_level'] = 'medium'
                
        else:  # SEVERE or TOTAL
            if available_backups:
                plan['strategy'] = 'backup_restore'
                plan['steps'] = [
                    '备份损坏的数据库',
                    '从最新备份恢复',
                    '验证恢复结果'
                ]
                plan['estimated_time'] = 180
                plan['risk_level'] = 'low'
            else:
                plan['strategy'] = 'database_rebuild'
                plan['steps'] = [
                    '备份损坏的数据库',
                    '创建新数据库',
                    '初始化数据库结构'
                ]
                plan['estimated_time'] = 120
                plan['risk_level'] = 'high'
        
        return plan
    
    def _execute_backup_restore(self, db_path: str, recovery_plan: Dict[str, Any], 
                               progress: RecoveryProgress) -> Dict[str, Any]:
        """执行备份恢复"""
        steps = recovery_plan['steps']
        
        # 查找最新备份
        backups = self._find_available_backups(db_path)
        if not backups:
            raise Exception("没有找到可用的备份文件")
        
        latest_backup = backups[0]
        
        for i, step in enumerate(steps):
            progress.update_progress(step, i, len(steps))
            self._update_progress(progress)
            
            if step == '备份当前数据库':
                # 备份当前损坏的数据库
                backup_path = f"{db_path}.corrupted.{int(time.time())}"
                if os.path.exists(db_path):
                    shutil.copy2(db_path, backup_path)
                    logger.info(f"已备份损坏数据库: {backup_path}")
                
            elif step == '从备份恢复' or step == '从最新备份恢复':
                # 从备份恢复
                shutil.copy2(latest_backup['path'], db_path)
                logger.info(f"已从备份恢复: {latest_backup['path']}")
                
            elif step == '验证恢复结果':
                # 验证恢复的数据库
                corruption_report = self.detector.detect_corruption(db_path)
                if corruption_report.corruption_level != CorruptionLevel.NONE:
                    raise Exception("恢复后的数据库仍有问题")
                logger.info("数据库恢复验证通过")
            
            time.sleep(0.1)  # 模拟处理时间
        
        progress.update_progress("恢复完成", len(steps), len(steps))
        progress.status = RecoveryStatus.COMPLETED
        self._update_progress(progress)
        
        return {
            'success': True,
            'strategy': 'backup_restore',
            'backup_used': latest_backup['path'],
            'progress': progress
        }
    
    def _execute_partial_recovery(self, db_path: str, recovery_plan: Dict[str, Any], 
                                 progress: RecoveryProgress) -> Dict[str, Any]:
        """执行部分数据恢复"""
        steps = recovery_plan['steps']
        recovered_data = {}
        
        for i, step in enumerate(steps):
            progress.update_progress(step, i, len(steps))
            self._update_progress(progress)
            
            if step == '导出可恢复数据':
                # 导出可恢复的数据
                recovered_data = self._export_recoverable_data(db_path)
                logger.info(f"已导出 {len(recovered_data)} 个表的数据")
                
            elif step == '重建数据库结构':
                # 重建数据库结构
                self._rebuild_database_structure(db_path)
                logger.info("数据库结构重建完成")
                
            elif step == '导入恢复的数据':
                # 导入恢复的数据
                self._import_recovered_data(db_path, recovered_data)
                logger.info("恢复数据导入完成")
                
            elif step == '验证数据完整性':
                # 验证数据完整性
                corruption_report = self.detector.detect_corruption(db_path)
                logger.info(f"数据完整性验证完成: {corruption_report.corruption_level.value}")
            
            time.sleep(0.1)  # 模拟处理时间
        
        progress.update_progress("部分恢复完成", len(steps), len(steps))
        progress.status = RecoveryStatus.COMPLETED
        self._update_progress(progress)
        
        return {
            'success': True,
            'strategy': 'partial_recovery',
            'recovered_tables': list(recovered_data.keys()),
            'progress': progress
        }
    
    def _execute_database_rebuild(self, db_path: str, recovery_plan: Dict[str, Any], 
                                 progress: RecoveryProgress) -> Dict[str, Any]:
        """执行数据库重建"""
        steps = recovery_plan['steps']
        
        for i, step in enumerate(steps):
            progress.update_progress(step, i, len(steps))
            self._update_progress(progress)
            
            if step == '备份损坏的数据库':
                # 备份损坏的数据库
                if os.path.exists(db_path):
                    backup_path = f"{db_path}.corrupted.{int(time.time())}"
                    shutil.copy2(db_path, backup_path)
                    logger.info(f"已备份损坏数据库: {backup_path}")
                
            elif step == '创建新数据库':
                # 删除旧数据库，创建新的
                if os.path.exists(db_path):
                    os.remove(db_path)
                logger.info("已删除损坏的数据库文件")
                
            elif step == '初始化数据库结构':
                # 初始化数据库结构
                self._initialize_database_structure(db_path)
                logger.info("数据库结构初始化完成")
            
            time.sleep(0.1)  # 模拟处理时间
        
        progress.update_progress("数据库重建完成", len(steps), len(steps))
        progress.status = RecoveryStatus.COMPLETED
        self._update_progress(progress)
        
        return {
            'success': True,
            'strategy': 'database_rebuild',
            'progress': progress
        }
    
    def _export_recoverable_data(self, db_path: str) -> Dict[str, List]:
        """导出可恢复的数据"""
        recovered_data = {}
        
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # 获取所有表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    try:
                        # 尝试读取表数据
                        cursor.execute(f"SELECT * FROM {table}")
                        rows = cursor.fetchall()
                        
                        # 获取列信息
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = [col[1] for col in cursor.fetchall()]
                        
                        recovered_data[table] = {
                            'columns': columns,
                            'rows': rows
                        }
                        
                        logger.info(f"从表 {table} 导出了 {len(rows)} 行数据")
                        
                    except Exception as e:
                        logger.warning(f"无法导出表 {table} 的数据: {e}")
        
        except Exception as e:
            logger.error(f"导出数据失败: {e}")
        
        return recovered_data
    
    def _rebuild_database_structure(self, db_path: str):
        """重建数据库结构"""
        # 备份原数据库
        backup_path = f"{db_path}.backup.{int(time.time())}"
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
        
        # 删除并重新创建数据库
        if os.path.exists(db_path):
            os.remove(db_path)
        
        # 初始化新的数据库结构
        self._initialize_database_structure(db_path)
    
    def _initialize_database_structure(self, db_path: str):
        """初始化数据库结构"""
        try:
            from core.database_manager import DatabaseManager
            db_manager = DatabaseManager(db_path)
            db_manager.initialize_database()
            logger.info("数据库结构初始化成功")
        except Exception as e:
            logger.error(f"数据库结构初始化失败: {e}")
            raise
    
    def _import_recovered_data(self, db_path: str, recovered_data: Dict[str, List]):
        """导入恢复的数据"""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                for table_name, table_data in recovered_data.items():
                    columns = table_data['columns']
                    rows = table_data['rows']
                    
                    if rows:
                        placeholders = ','.join(['?' for _ in columns])
                        insert_sql = f"INSERT OR REPLACE INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
                        
                        cursor.executemany(insert_sql, rows)
                        logger.info(f"向表 {table_name} 导入了 {len(rows)} 行数据")
                
                conn.commit()
                logger.info("数据导入完成")
        
        except Exception as e:
            logger.error(f"数据导入失败: {e}")
            raise
    
    def _update_progress(self, progress: RecoveryProgress):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(progress)


def main():
    """测试数据恢复功能"""
    print("数据恢复功能测试")
    print("=" * 50)
    
    # 创建测试数据库
    test_db_path = "test_recovery.db"
    
    try:
        # 创建简单的测试数据库
        with sqlite3.connect(test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            cursor.execute("INSERT INTO test (name) VALUES ('test1'), ('test2')")
            conn.commit()
        
        print("✓ 测试数据库创建成功")
        
        # 测试损坏检测
        detector = DatabaseCorruptionDetector()
        corruption_report = detector.detect_corruption(test_db_path)
        print(f"✓ 损坏检测完成: {corruption_report.corruption_level.value}")
        
        # 测试恢复向导
        wizard = DataRecoveryWizard()
        
        def progress_callback(progress: RecoveryProgress):
            print(f"进度: {progress.current_step} ({progress.progress_percentage:.1f}%)")
        
        wizard.set_progress_callback(progress_callback)
        
        result = wizard.start_recovery_wizard(test_db_path)
        if result['success']:
            print("✓ 恢复向导测试成功")
        else:
            print(f"❌ 恢复向导测试失败: {result.get('error')}")
        
    finally:
        # 清理测试文件
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
    
    print("\n测试完成!")


if __name__ == "__main__":
    main()