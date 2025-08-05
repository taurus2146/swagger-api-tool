#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库锁定检测和恢复工具
"""

import os
import sqlite3
import logging
import time
import psutil
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseLockRecovery:
    """数据库锁定检测和恢复工具"""
    
    def __init__(self, db_path: str):
        """
        初始化锁定恢复工具
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = os.path.abspath(db_path)
        self.db_dir = os.path.dirname(self.db_path)
        self.db_name = os.path.basename(self.db_path)
    
    def diagnose_lock_issue(self) -> Dict[str, Any]:
        """
        诊断数据库锁定问题
        
        Returns:
            Dict[str, Any]: 诊断结果
        """
        diagnosis = {
            'database_exists': False,
            'database_accessible': False,
            'wal_files': [],
            'shm_files': [],
            'lock_files': [],
            'processes_using_db': [],
            'file_permissions': {},
            'disk_space': {},
            'recommendations': []
        }
        
        try:
            # 检查数据库文件是否存在
            if os.path.exists(self.db_path):
                diagnosis['database_exists'] = True
                
                # 检查文件权限
                stat_info = os.stat(self.db_path)
                diagnosis['file_permissions'] = {
                    'readable': os.access(self.db_path, os.R_OK),
                    'writable': os.access(self.db_path, os.W_OK),
                    'size': stat_info.st_size,
                    'mode': oct(stat_info.st_mode)
                }
                
                # 检查数据库是否可访问
                diagnosis['database_accessible'] = self._test_database_access()
            
            # 检查WAL和SHM文件
            diagnosis['wal_files'] = self._find_related_files('.wal')
            diagnosis['shm_files'] = self._find_related_files('.shm')
            diagnosis['lock_files'] = self._find_related_files('.lock')
            
            # 检查使用数据库的进程
            diagnosis['processes_using_db'] = self._find_processes_using_database()
            
            # 检查磁盘空间
            diagnosis['disk_space'] = self._check_disk_space()
            
            # 生成建议
            diagnosis['recommendations'] = self._generate_recommendations(diagnosis)
            
        except Exception as e:
            logger.error(f"诊断数据库锁定问题时出错: {e}")
            diagnosis['error'] = str(e)
        
        return diagnosis
    
    def _test_database_access(self) -> bool:
        """测试数据库访问"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=1.0)
            conn.execute('SELECT 1')
            conn.close()
            return True
        except sqlite3.Error:
            return False
    
    def _find_related_files(self, extension: str) -> List[Dict[str, Any]]:
        """查找相关文件"""
        files = []
        base_name = os.path.splitext(self.db_name)[0]
        
        for file_path in Path(self.db_dir).glob(f"{base_name}*{extension}"):
            try:
                stat_info = file_path.stat()
                files.append({
                    'path': str(file_path),
                    'size': stat_info.st_size,
                    'modified': stat_info.st_mtime,
                    'accessible': os.access(file_path, os.R_OK | os.W_OK)
                })
            except Exception as e:
                files.append({
                    'path': str(file_path),
                    'error': str(e)
                })
        
        return files
    
    def _find_processes_using_database(self) -> List[Dict[str, Any]]:
        """查找使用数据库的进程"""
        processes = []

        try:
            # 使用更安全的方式检查进程
            import time
            start_time = time.time()

            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    # 设置超时，避免卡死
                    if time.time() - start_time > 5:  # 5秒超时
                        logger.warning("进程检查超时，停止扫描")
                        break

                    # 只检查Python进程，减少扫描范围
                    if 'python' not in proc.info['name'].lower():
                        continue

                    # 检查进程是否打开了数据库文件
                    try:
                        for file_info in proc.open_files():
                            if file_info.path == self.db_path:
                                processes.append({
                                    'pid': proc.info['pid'],
                                    'name': proc.info['name'],
                                    'file_path': file_info.path
                                })
                                break
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        continue

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    # 忽略其他异常，继续处理
                    continue

        except Exception as e:
            logger.warning(f"查找使用数据库的进程时出错: {e}")

        return processes
    
    def _check_disk_space(self) -> Dict[str, Any]:
        """检查磁盘空间"""
        try:
            usage = psutil.disk_usage(self.db_dir)
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': (usage.used / usage.total) * 100
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _generate_recommendations(self, diagnosis: Dict[str, Any]) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        if not diagnosis['database_exists']:
            recommendations.append("数据库文件不存在，需要重新创建")
            return recommendations
        
        if not diagnosis['database_accessible']:
            recommendations.append("数据库无法访问，可能被锁定")
        
        if diagnosis['processes_using_db']:
            recommendations.append(f"发现 {len(diagnosis['processes_using_db'])} 个进程正在使用数据库")
            recommendations.append("建议关闭其他使用数据库的应用程序")
        
        if diagnosis['wal_files']:
            recommendations.append("发现WAL文件，可能存在未完成的事务")
            recommendations.append("考虑执行WAL检查点操作")
        
        if diagnosis['shm_files']:
            recommendations.append("发现共享内存文件，可能有其他进程在使用")
        
        disk_space = diagnosis.get('disk_space', {})
        if disk_space.get('percent', 0) > 95:
            recommendations.append("磁盘空间不足，可能影响数据库操作")
        
        file_perms = diagnosis.get('file_permissions', {})
        if not file_perms.get('writable', True):
            recommendations.append("数据库文件没有写权限")
        
        return recommendations
    
    def attempt_recovery(self) -> Dict[str, Any]:
        """
        尝试恢复数据库锁定
        
        Returns:
            Dict[str, Any]: 恢复结果
        """
        recovery_result = {
            'success': False,
            'actions_taken': [],
            'errors': []
        }
        
        try:
            # 1. 尝试WAL检查点
            if self._attempt_wal_checkpoint():
                recovery_result['actions_taken'].append("执行WAL检查点")
            
            # 2. 清理临时文件
            cleaned_files = self._cleanup_temp_files()
            if cleaned_files:
                recovery_result['actions_taken'].append(f"清理了 {len(cleaned_files)} 个临时文件")
            
            # 3. 测试数据库访问
            if self._test_database_access():
                recovery_result['success'] = True
                recovery_result['actions_taken'].append("数据库访问恢复正常")
            else:
                recovery_result['errors'].append("数据库仍然无法访问")
            
        except Exception as e:
            recovery_result['errors'].append(f"恢复过程中出错: {e}")
        
        return recovery_result
    
    def _attempt_wal_checkpoint(self) -> bool:
        """尝试执行WAL检查点"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            conn.close()
            logger.info("WAL检查点执行成功")
            return True
        except sqlite3.Error as e:
            logger.warning(f"WAL检查点执行失败: {e}")
            return False
    
    def _cleanup_temp_files(self) -> List[str]:
        """清理临时文件"""
        cleaned_files = []
        
        # 清理WAL和SHM文件（谨慎操作）
        temp_extensions = ['.wal-shm', '.wal-wal']
        
        for ext in temp_extensions:
            temp_file = self.db_path + ext
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    cleaned_files.append(temp_file)
                    logger.info(f"已删除临时文件: {temp_file}")
                except OSError as e:
                    logger.warning(f"无法删除临时文件 {temp_file}: {e}")
        
        return cleaned_files
    
    def force_unlock(self) -> bool:
        """
        强制解锁数据库（危险操作）
        
        Returns:
            bool: 是否成功
        """
        logger.warning("执行强制解锁操作，这可能导致数据丢失")
        
        try:
            # 备份数据库
            backup_path = f"{self.db_path}.backup.{int(time.time())}"
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"数据库已备份到: {backup_path}")
            
            # 删除WAL和SHM文件
            wal_file = self.db_path + '-wal'
            shm_file = self.db_path + '-shm'
            
            for file_path in [wal_file, shm_file]:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"已删除: {file_path}")
            
            # 测试访问
            return self._test_database_access()
            
        except Exception as e:
            logger.error(f"强制解锁失败: {e}")
            return False
