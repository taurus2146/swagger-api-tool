#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库管理工具
提供数据库重命名、删除、清理、导入导出、统计分析等功能
"""

import os
import shutil
import sqlite3
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

from .database_config_manager import DatabaseConfigManager, DatabaseConfig
from .database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class DatabaseAnalysisResult:
    """数据库分析结果"""
    
    def __init__(self):
        self.file_size = 0
        self.table_count = 0
        self.record_count = 0
        self.index_count = 0
        self.tables = {}
        self.indexes = {}
        self.schema_version = None
        self.last_modified = None
        self.integrity_check = True
        self.vacuum_needed = False
        self.recommendations = []


class DatabaseManagementTools:
    """数据库管理工具"""
    
    def __init__(self, config_manager: DatabaseConfigManager, 
                 database_manager: DatabaseManager = None):
        """
        初始化数据库管理工具
        
        Args:
            config_manager: 数据库配置管理器
            database_manager: 数据库管理器（可选）
        """
        self.config_manager = config_manager
        self.database_manager = database_manager
    
    def rename_database_config(self, config_id: str, new_name: str, 
                             new_description: str = None) -> bool:
        """
        重命名数据库配置
        
        Args:
            config_id: 配置ID
            new_name: 新名称
            new_description: 新描述（可选）
            
        Returns:
            bool: 是否成功
        """
        try:
            config = self.config_manager.get_config(config_id)
            if not config:
                logger.error(f"配置 {config_id} 不存在")
                return False
            
            # 检查名称是否已存在
            all_configs = self.config_manager.get_all_configs()
            for other_config in all_configs:
                if other_config.id != config_id and other_config.name == new_name:
                    logger.error(f"名称 '{new_name}' 已存在")
                    return False
            
            # 更新配置
            update_data = {'name': new_name}
            if new_description is not None:
                update_data['description'] = new_description
            
            success = self.config_manager.update_config(config_id, **update_data)
            
            if success:
                logger.info(f"数据库配置重命名成功: '{config.name}' -> '{new_name}'")
            else:
                logger.error("数据库配置重命名失败")
            
            return success
            
        except Exception as e:
            logger.error(f"重命名数据库配置时发生异常: {e}")
            return False
    
    def rename_database_file(self, config_id: str, new_file_name: str) -> bool:
        """
        重命名数据库文件
        
        Args:
            config_id: 配置ID
            new_file_name: 新文件名（不包含路径）
            
        Returns:
            bool: 是否成功
        """
        try:
            config = self.config_manager.get_config(config_id)
            if not config:
                logger.error(f"配置 {config_id} 不存在")
                return False
            
            if not config.exists:
                logger.error(f"数据库文件不存在: {config.path}")
                return False
            
            # 构建新路径
            old_path = config.path
            new_path = os.path.join(os.path.dirname(old_path), new_file_name)
            
            # 检查新文件是否已存在
            if os.path.exists(new_path):
                logger.error(f"目标文件已存在: {new_path}")
                return False
            
            # 如果当前正在使用这个数据库，需要先断开连接
            current_db_path = None
            if self.database_manager and self.database_manager.db_path == old_path:
                current_db_path = old_path
                self.database_manager.disconnect()
            
            try:
                # 重命名文件
                shutil.move(old_path, new_path)
                
                # 更新配置中的路径
                self.config_manager.update_config(config_id, path=new_path)
                
                # 如果之前断开了连接，重新连接到新路径
                if current_db_path and self.database_manager:
                    self.database_manager.db_path = new_path
                    self.database_manager.connect()
                
                logger.info(f"数据库文件重命名成功: {old_path} -> {new_path}")
                return True
                
            except Exception as e:
                # 如果重命名失败，尝试恢复连接
                if current_db_path and self.database_manager:
                    self.database_manager.db_path = current_db_path
                    self.database_manager.connect()
                raise e
                
        except Exception as e:
            logger.error(f"重命名数据库文件时发生异常: {e}")
            return False
    
    def delete_database_config(self, config_id: str, delete_file: bool = False) -> bool:
        """
        删除数据库配置
        
        Args:
            config_id: 配置ID
            delete_file: 是否同时删除数据库文件
            
        Returns:
            bool: 是否成功
        """
        try:
            config = self.config_manager.get_config(config_id)
            if not config:
                logger.error(f"配置 {config_id} 不存在")
                return False
            
            file_path = config.path
            
            # 删除配置
            success = self.config_manager.remove_config(config_id)
            if not success:
                logger.error("删除数据库配置失败")
                return False
            
            # 如果需要删除文件
            if delete_file and os.path.exists(file_path):
                try:
                    # 如果当前正在使用这个数据库，先断开连接
                    if self.database_manager and self.database_manager.db_path == file_path:
                        self.database_manager.disconnect()
                    
                    os.remove(file_path)
                    logger.info(f"数据库文件已删除: {file_path}")
                    
                except Exception as e:
                    logger.warning(f"删除数据库文件失败: {e}")
                    # 配置已删除，文件删除失败不影响整体结果
            
            logger.info(f"数据库配置删除成功: {config.name}")
            return True
            
        except Exception as e:
            logger.error(f"删除数据库配置时发生异常: {e}")
            return False
    
    def cleanup_missing_configs(self) -> int:
        """
        清理缺失文件的配置
        
        Returns:
            int: 清理的配置数量
        """
        try:
            all_configs = self.config_manager.get_all_configs()
            missing_configs = [config for config in all_configs if not config.exists]
            
            cleaned_count = 0
            for config in missing_configs:
                if self.config_manager.remove_config(config.id):
                    cleaned_count += 1
                    logger.info(f"清理缺失配置: {config.name}")
            
            logger.info(f"清理了 {cleaned_count} 个缺失文件的配置")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理缺失配置时发生异常: {e}")
            return 0
    
    def vacuum_database(self, config_id: str) -> bool:
        """
        压缩数据库文件
        
        Args:
            config_id: 配置ID
            
        Returns:
            bool: 是否成功
        """
        try:
            config = self.config_manager.get_config(config_id)
            if not config:
                logger.error(f"配置 {config_id} 不存在")
                return False
            
            if not config.exists:
                logger.error(f"数据库文件不存在: {config.path}")
                return False
            
            # 获取压缩前的文件大小
            old_size = os.path.getsize(config.path)
            
            # 执行VACUUM
            with sqlite3.connect(config.path) as conn:
                conn.execute("VACUUM")
                conn.commit()
            
            # 获取压缩后的文件大小
            new_size = os.path.getsize(config.path)
            saved_bytes = old_size - new_size
            
            # 更新配置中的文件信息
            config.update_file_info()
            self.config_manager.update_config(config_id, file_size=config.file_size)
            
            logger.info(f"数据库压缩完成: {config.name}, 节省空间: {saved_bytes} 字节")
            return True
            
        except Exception as e:
            logger.error(f"压缩数据库时发生异常: {e}")
            return False
    
    def export_database_config(self, config_id: str, export_path: str, 
                             include_data: bool = True) -> bool:
        """
        导出数据库配置和数据
        
        Args:
            config_id: 配置ID
            export_path: 导出路径
            include_data: 是否包含数据
            
        Returns:
            bool: 是否成功
        """
        try:
            config = self.config_manager.get_config(config_id)
            if not config:
                logger.error(f"配置 {config_id} 不存在")
                return False
            
            # 创建导出目录
            export_dir = os.path.dirname(export_path)
            os.makedirs(export_dir, exist_ok=True)
            
            export_data = {
                'version': '1.0',
                'exported_at': datetime.now().isoformat(),
                'config': {
                    'id': config.id,
                    'name': config.name,
                    'description': config.description,
                    'tags': config.tags,
                    'created_at': config.created_at,
                    'is_default': config.is_default
                },
                'include_data': include_data
            }
            
            if include_data and config.exists:
                # 复制数据库文件
                db_file_name = f"{config.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                db_export_path = os.path.join(export_dir, db_file_name)
                shutil.copy2(config.path, db_export_path)
                export_data['database_file'] = db_file_name
                
                # 添加数据库分析信息
                analysis = self.analyze_database(config_id)
                if analysis:
                    export_data['analysis'] = {
                        'file_size': analysis.file_size,
                        'table_count': analysis.table_count,
                        'record_count': analysis.record_count,
                        'tables': analysis.tables
                    }
            
            # 保存配置文件
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"数据库配置导出成功: {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出数据库配置时发生异常: {e}")
            return False
    
    def import_database_config(self, import_path: str, 
                             import_data: bool = True) -> Optional[str]:
        """
        导入数据库配置和数据
        
        Args:
            import_path: 导入文件路径
            import_data: 是否导入数据
            
        Returns:
            Optional[str]: 导入的配置ID，失败返回None
        """
        try:
            if not os.path.exists(import_path):
                logger.error(f"导入文件不存在: {import_path}")
                return None
            
            # 读取配置文件
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data_dict = json.load(f)
            
            config_data = import_data_dict.get('config', {})
            
            # 生成新的配置名称（避免冲突）
            base_name = config_data.get('name', '导入的数据库')
            new_name = base_name
            counter = 1
            
            while any(config.name == new_name for config in self.config_manager.get_all_configs()):
                new_name = f"{base_name}_{counter}"
                counter += 1
            
            # 确定数据库文件路径
            if import_data and import_data_dict.get('include_data') and 'database_file' in import_data_dict:
                # 导入数据库文件
                import_dir = os.path.dirname(import_path)
                source_db_path = os.path.join(import_dir, import_data_dict['database_file'])
                
                if os.path.exists(source_db_path):
                    # 复制到默认数据库目录
                    from .storage_utils import get_default_storage_path
                    target_dir = get_default_storage_path()
                    os.makedirs(target_dir, exist_ok=True)
                    
                    target_db_path = os.path.join(target_dir, f"{new_name}.db")
                    counter = 1
                    while os.path.exists(target_db_path):
                        target_db_path = os.path.join(target_dir, f"{new_name}_{counter}.db")
                        counter += 1
                    
                    shutil.copy2(source_db_path, target_db_path)
                    db_path = target_db_path
                else:
                    logger.warning(f"数据库文件不存在: {source_db_path}")
                    db_path = os.path.join(get_default_storage_path(), f"{new_name}.db")
            else:
                # 不导入数据，创建空数据库路径
                from .storage_utils import get_default_storage_path
                db_path = os.path.join(get_default_storage_path(), f"{new_name}.db")
            
            # 创建配置
            config_id = self.config_manager.add_config(
                name=new_name,
                path=db_path,
                description=config_data.get('description', ''),
                tags=config_data.get('tags', [])
            )
            
            logger.info(f"数据库配置导入成功: {new_name}")
            return config_id
            
        except Exception as e:
            logger.error(f"导入数据库配置时发生异常: {e}")
            return None
    
    def analyze_database(self, config_id: str) -> Optional[DatabaseAnalysisResult]:
        """
        分析数据库
        
        Args:
            config_id: 配置ID
            
        Returns:
            Optional[DatabaseAnalysisResult]: 分析结果
        """
        try:
            config = self.config_manager.get_config(config_id)
            if not config:
                logger.error(f"配置 {config_id} 不存在")
                return None
            
            if not config.exists:
                logger.error(f"数据库文件不存在: {config.path}")
                return None
            
            result = DatabaseAnalysisResult()
            
            # 文件信息
            stat = os.stat(config.path)
            result.file_size = stat.st_size
            result.last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            # 连接数据库分析
            with sqlite3.connect(config.path) as conn:
                cursor = conn.cursor()
                
                # 获取表信息
                cursor.execute("""
                    SELECT name, type FROM sqlite_master 
                    WHERE type IN ('table', 'index') 
                    ORDER BY type, name
                """)
                
                for name, obj_type in cursor.fetchall():
                    if obj_type == 'table':
                        if name.startswith('sqlite_'):
                            continue  # 跳过系统表
                        
                        # 获取表的记录数
                        cursor.execute(f"SELECT COUNT(*) FROM `{name}`")
                        record_count = cursor.fetchone()[0]
                        
                        # 获取表结构
                        cursor.execute(f"PRAGMA table_info(`{name}`)")
                        columns = cursor.fetchall()
                        
                        result.tables[name] = {
                            'record_count': record_count,
                            'columns': [
                                {
                                    'name': col[1],
                                    'type': col[2],
                                    'not_null': bool(col[3]),
                                    'default_value': col[4],
                                    'primary_key': bool(col[5])
                                }
                                for col in columns
                            ]
                        }
                        result.record_count += record_count
                        result.table_count += 1
                        
                    elif obj_type == 'index':
                        if name.startswith('sqlite_'):
                            continue  # 跳过系统索引
                        
                        # 获取索引信息
                        cursor.execute(f"PRAGMA index_info(`{name}`)")
                        index_columns = cursor.fetchall()
                        
                        result.indexes[name] = {
                            'columns': [col[2] for col in index_columns]
                        }
                        result.index_count += 1
                
                # 检查数据库完整性
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]
                result.integrity_check = (integrity_result == 'ok')
                
                # 检查是否需要VACUUM
                cursor.execute("PRAGMA freelist_count")
                free_pages = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_count")
                total_pages = cursor.fetchone()[0]
                
                if total_pages > 0:
                    free_ratio = free_pages / total_pages
                    result.vacuum_needed = free_ratio > 0.1  # 超过10%空闲页面建议VACUUM
                
                # 生成建议
                if not result.integrity_check:
                    result.recommendations.append("数据库完整性检查失败，建议修复")
                
                if result.vacuum_needed:
                    result.recommendations.append("建议执行VACUUM压缩数据库")
                
                if result.table_count == 0:
                    result.recommendations.append("数据库为空，可能需要初始化")
                
                if result.file_size > 100 * 1024 * 1024:  # 100MB
                    result.recommendations.append("数据库文件较大，考虑定期备份")
            
            logger.info(f"数据库分析完成: {config.name}")
            return result
            
        except Exception as e:
            logger.error(f"分析数据库时发生异常: {e}")
            return None
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            all_configs = self.config_manager.get_all_configs()
            
            stats = {
                'total_databases': len(all_configs),
                'existing_databases': 0,
                'missing_databases': 0,
                'total_size_bytes': 0,
                'total_records': 0,
                'total_tables': 0,
                'databases_by_tag': {},
                'largest_database': None,
                'most_used_database': None,
                'recent_activity': []
            }
            
            largest_size = 0
            most_connections = 0
            
            for config in all_configs:
                if config.exists:
                    stats['existing_databases'] += 1
                    stats['total_size_bytes'] += config.file_size
                    
                    # 记录最大数据库
                    if config.file_size > largest_size:
                        largest_size = config.file_size
                        stats['largest_database'] = {
                            'name': config.name,
                            'size_bytes': config.file_size,
                            'size_mb': config.size_mb
                        }
                    
                    # 分析数据库内容（可选，可能较慢）
                    try:
                        analysis = self.analyze_database(config.id)
                        if analysis:
                            stats['total_records'] += analysis.record_count
                            stats['total_tables'] += analysis.table_count
                    except:
                        pass  # 忽略分析错误
                        
                else:
                    stats['missing_databases'] += 1
                
                # 记录最常用数据库
                if config.connection_count > most_connections:
                    most_connections = config.connection_count
                    stats['most_used_database'] = {
                        'name': config.name,
                        'connections': config.connection_count
                    }
                
                # 按标签统计
                for tag in config.tags:
                    if tag not in stats['databases_by_tag']:
                        stats['databases_by_tag'][tag] = 0
                    stats['databases_by_tag'][tag] += 1
                
                # 最近活动
                stats['recent_activity'].append({
                    'name': config.name,
                    'last_accessed': config.last_accessed,
                    'connections': config.connection_count
                })
            
            # 排序最近活动
            stats['recent_activity'].sort(key=lambda x: x['last_accessed'], reverse=True)
            stats['recent_activity'] = stats['recent_activity'][:10]  # 只保留前10个
            
            # 计算平均值
            if stats['existing_databases'] > 0:
                stats['average_size_mb'] = (stats['total_size_bytes'] / stats['existing_databases']) / 1024 / 1024
                stats['average_records'] = stats['total_records'] / stats['existing_databases']
            else:
                stats['average_size_mb'] = 0
                stats['average_records'] = 0
            
            stats['total_size_mb'] = stats['total_size_bytes'] / 1024 / 1024
            
            return stats
            
        except Exception as e:
            logger.error(f"获取数据库统计信息时发生异常: {e}")
            return {}
    
    def repair_database(self, config_id: str) -> bool:
        """
        修复数据库
        
        Args:
            config_id: 配置ID
            
        Returns:
            bool: 是否成功
        """
        try:
            config = self.config_manager.get_config(config_id)
            if not config:
                logger.error(f"配置 {config_id} 不存在")
                return False
            
            if not config.exists:
                logger.error(f"数据库文件不存在: {config.path}")
                return False
            
            # 创建备份
            backup_path = f"{config.path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(config.path, backup_path)
            
            try:
                with sqlite3.connect(config.path) as conn:
                    cursor = conn.cursor()
                    
                    # 检查完整性
                    cursor.execute("PRAGMA integrity_check")
                    integrity_result = cursor.fetchall()
                    
                    if len(integrity_result) == 1 and integrity_result[0][0] == 'ok':
                        logger.info(f"数据库完整性正常: {config.name}")
                        os.remove(backup_path)  # 删除备份
                        return True
                    
                    # 尝试修复
                    logger.info(f"尝试修复数据库: {config.name}")
                    
                    # 重建数据库
                    cursor.execute("VACUUM")
                    cursor.execute("REINDEX")
                    
                    # 再次检查完整性
                    cursor.execute("PRAGMA integrity_check")
                    integrity_result = cursor.fetchall()
                    
                    if len(integrity_result) == 1 and integrity_result[0][0] == 'ok':
                        logger.info(f"数据库修复成功: {config.name}")
                        os.remove(backup_path)  # 删除备份
                        return True
                    else:
                        logger.error(f"数据库修复失败: {config.name}")
                        # 恢复备份
                        shutil.move(backup_path, config.path)
                        return False
                        
            except Exception as e:
                logger.error(f"修复数据库时发生错误: {e}")
                # 恢复备份
                if os.path.exists(backup_path):
                    shutil.move(backup_path, config.path)
                return False
                
        except Exception as e:
            logger.error(f"修复数据库时发生异常: {e}")
            return False
    
    def optimize_database(self, config_id: str) -> Dict[str, Any]:
        """
        优化数据库
        
        Args:
            config_id: 配置ID
            
        Returns:
            Dict[str, Any]: 优化结果
        """
        try:
            config = self.config_manager.get_config(config_id)
            if not config:
                return {'success': False, 'message': f'配置 {config_id} 不存在'}
            
            if not config.exists:
                return {'success': False, 'message': f'数据库文件不存在: {config.path}'}
            
            result = {
                'success': True,
                'operations': [],
                'old_size': os.path.getsize(config.path),
                'new_size': 0,
                'space_saved': 0
            }
            
            with sqlite3.connect(config.path) as conn:
                cursor = conn.cursor()
                
                # 分析数据库
                cursor.execute("ANALYZE")
                result['operations'].append('数据库统计信息已更新')
                
                # 重建索引
                cursor.execute("REINDEX")
                result['operations'].append('索引已重建')
                
                # 压缩数据库
                cursor.execute("VACUUM")
                result['operations'].append('数据库已压缩')
                
                conn.commit()
            
            # 计算优化效果
            result['new_size'] = os.path.getsize(config.path)
            result['space_saved'] = result['old_size'] - result['new_size']
            
            # 更新配置中的文件信息
            config.update_file_info()
            
            logger.info(f"数据库优化完成: {config.name}, 节省空间: {result['space_saved']} 字节")
            return result
            
        except Exception as e:
            logger.error(f"优化数据库时发生异常: {e}")
            return {'success': False, 'message': str(e)}