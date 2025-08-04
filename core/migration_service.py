#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据迁移服务
处理从JSON文件到数据库的数据迁移和数据库版本升级
"""

import os
import json
import logging
import shutil
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .database_manager import DatabaseManager
from .project_models import Project, SwaggerSource, GlobalConfig
from .database_storage import DatabaseStorage

logger = logging.getLogger(__name__)


class MigrationStatus(Enum):
    """迁移状态枚举"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationResult:
    """迁移结果"""
    status: MigrationStatus
    total_items: int = 0
    migrated_items: int = 0
    failed_items: int = 0
    errors: List[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    backup_path: Optional[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_items == 0:
            return 0.0
        return (self.migrated_items / self.total_items) * 100
    
    @property
    def duration(self) -> Optional[float]:
        """迁移耗时（秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


@dataclass
class LegacyDataInfo:
    """旧数据信息"""
    projects_dir: str
    global_config_path: str
    project_count: int = 0
    has_global_config: bool = False
    total_size: int = 0
    last_modified: Optional[datetime] = None


class MigrationService:
    """数据迁移服务类"""
    
    def __init__(self, db_manager: DatabaseManager, legacy_storage_path: str = "./projects"):
        """
        初始化迁移服务
        
        Args:
            db_manager: 数据库管理器实例
            legacy_storage_path: 旧数据存储路径
        """
        self.db_manager = db_manager
        self.legacy_storage_path = legacy_storage_path
        self.legacy_projects_dir = os.path.join(legacy_storage_path, "projects")
        self.legacy_config_path = os.path.join(legacy_storage_path, "global_config.json")
        self.db_storage = DatabaseStorage()
        self.db_storage.db_manager = db_manager  # 使用相同的数据库管理器
    
    def detect_legacy_data(self) -> Optional[LegacyDataInfo]:
        """
        检测旧的JSON数据文件
        
        Returns:
            Optional[LegacyDataInfo]: 旧数据信息，如果没有发现返回None
        """
        try:
            if not os.path.exists(self.legacy_storage_path):
                logger.info("未发现旧数据存储路径")
                return None
            
            info = LegacyDataInfo(
                projects_dir=self.legacy_projects_dir,
                global_config_path=self.legacy_config_path
            )
            
            # 检查项目目录
            if os.path.exists(self.legacy_projects_dir):
                project_dirs = [d for d in os.listdir(self.legacy_projects_dir) 
                              if os.path.isdir(os.path.join(self.legacy_projects_dir, d))]
                info.project_count = len(project_dirs)
                
                # 计算总大小和最后修改时间
                total_size = 0
                latest_modified = None
                
                for project_dir in project_dirs:
                    config_file = os.path.join(self.legacy_projects_dir, project_dir, "config.json")
                    if os.path.exists(config_file):
                        stat = os.stat(config_file)
                        total_size += stat.st_size
                        
                        modified_time = datetime.fromtimestamp(stat.st_mtime)
                        if latest_modified is None or modified_time > latest_modified:
                            latest_modified = modified_time
                
                info.total_size = total_size
                info.last_modified = latest_modified
            
            # 检查全局配置
            if os.path.exists(self.legacy_config_path):
                info.has_global_config = True
                stat = os.stat(self.legacy_config_path)
                info.total_size += stat.st_size
                
                config_modified = datetime.fromtimestamp(stat.st_mtime)
                if info.last_modified is None or config_modified > info.last_modified:
                    info.last_modified = config_modified
            
            # 如果没有发现任何数据，返回None
            if info.project_count == 0 and not info.has_global_config:
                logger.info("未发现可迁移的旧数据")
                return None
            
            logger.info(f"发现旧数据: {info.project_count}个项目, 全局配置: {info.has_global_config}")
            return info
            
        except Exception as e:
            logger.error(f"检测旧数据失败: {e}")
            return None
    
    def _load_legacy_project(self, project_id: str) -> Optional[Project]:
        """
        加载旧的项目配置
        
        Args:
            project_id: 项目ID
            
        Returns:
            Optional[Project]: 项目对象，失败返回None
        """
        try:
            config_file = os.path.join(self.legacy_projects_dir, project_id, "config.json")
            if not os.path.exists(config_file):
                return None
            
            with open(config_file, 'r', encoding='utf-8') as f:
                project = Project.from_json(f.read())
            
            return project
            
        except Exception as e:
            logger.error(f"加载旧项目配置失败 {project_id}: {e}")
            return None
    
    def _load_legacy_global_config(self) -> Optional[GlobalConfig]:
        """
        加载旧的全局配置
        
        Returns:
            Optional[GlobalConfig]: 全局配置对象，失败返回None
        """
        try:
            if not os.path.exists(self.legacy_config_path):
                return None
            
            with open(self.legacy_config_path, 'r', encoding='utf-8') as f:
                config = GlobalConfig.from_json(f.read())
            
            return config
            
        except Exception as e:
            logger.error(f"加载旧全局配置失败: {e}")
            return None
    
    def migrate_from_json(self, backup_before_migration: bool = True) -> MigrationResult:
        """
        从JSON文件迁移数据到数据库
        
        Args:
            backup_before_migration: 是否在迁移前备份旧数据
            
        Returns:
            MigrationResult: 迁移结果
        """
        result = MigrationResult(
            status=MigrationStatus.NOT_STARTED,
            start_time=datetime.now()
        )
        
        try:
            # 检测旧数据
            legacy_info = self.detect_legacy_data()
            if not legacy_info:
                result.status = MigrationStatus.COMPLETED
                result.end_time = datetime.now()
                logger.info("没有发现需要迁移的数据")
                return result
            
            result.status = MigrationStatus.IN_PROGRESS
            result.total_items = legacy_info.project_count + (1 if legacy_info.has_global_config else 0)
            
            logger.info(f"开始数据迁移，总计 {result.total_items} 项")
            
            # 备份旧数据
            if backup_before_migration:
                backup_path = self._backup_legacy_data()
                result.backup_path = backup_path
                if backup_path:
                    logger.info(f"旧数据已备份到: {backup_path}")
            
            # 迁移项目数据
            if legacy_info.project_count > 0:
                self._migrate_projects(result)
            
            # 迁移全局配置
            if legacy_info.has_global_config:
                self._migrate_global_config(result)
            
            # 检查迁移结果
            if result.failed_items == 0:
                result.status = MigrationStatus.COMPLETED
                logger.info(f"数据迁移完成，成功迁移 {result.migrated_items}/{result.total_items} 项")
            else:
                result.status = MigrationStatus.FAILED
                logger.warning(f"数据迁移部分失败，成功 {result.migrated_items}，失败 {result.failed_items}")
            
            result.end_time = datetime.now()
            return result
            
        except Exception as e:
            result.status = MigrationStatus.FAILED
            result.end_time = datetime.now()
            result.errors.append(f"迁移过程异常: {e}")
            logger.error(f"数据迁移失败: {e}")
            return result
    
    def _migrate_projects(self, result: MigrationResult) -> None:
        """
        迁移项目数据
        
        Args:
            result: 迁移结果对象
        """
        try:
            if not os.path.exists(self.legacy_projects_dir):
                return
            
            project_dirs = [d for d in os.listdir(self.legacy_projects_dir) 
                          if os.path.isdir(os.path.join(self.legacy_projects_dir, d))]
            
            for project_id in project_dirs:
                try:
                    # 加载旧项目
                    project = self._load_legacy_project(project_id)
                    if not project:
                        result.failed_items += 1
                        result.errors.append(f"无法加载项目: {project_id}")
                        continue
                    
                    # 检查项目是否已存在
                    existing = self.db_storage.load_project(project.id)
                    if existing:
                        logger.info(f"项目已存在，跳过: {project.name} ({project.id})")
                        result.migrated_items += 1
                        continue
                    
                    # 保存到数据库
                    success = self.db_storage.save_project(project)
                    if success:
                        result.migrated_items += 1
                        logger.debug(f"项目迁移成功: {project.name} ({project.id})")
                    else:
                        result.failed_items += 1
                        result.errors.append(f"保存项目失败: {project.name} ({project.id})")
                
                except Exception as e:
                    result.failed_items += 1
                    result.errors.append(f"迁移项目 {project_id} 失败: {e}")
                    logger.error(f"迁移项目失败 {project_id}: {e}")
            
        except Exception as e:
            result.errors.append(f"迁移项目数据异常: {e}")
            logger.error(f"迁移项目数据异常: {e}")
    
    def _migrate_global_config(self, result: MigrationResult) -> None:
        """
        迁移全局配置
        
        Args:
            result: 迁移结果对象
        """
        try:
            # 加载旧配置
            config = self._load_legacy_global_config()
            if not config:
                result.failed_items += 1
                result.errors.append("无法加载全局配置")
                return
            
            # 保存到数据库
            success = self.db_storage.save_global_config(config)
            if success:
                result.migrated_items += 1
                logger.debug("全局配置迁移成功")
            else:
                result.failed_items += 1
                result.errors.append("保存全局配置失败")
        
        except Exception as e:
            result.failed_items += 1
            result.errors.append(f"迁移全局配置异常: {e}")
            logger.error(f"迁移全局配置异常: {e}")
    
    def _backup_legacy_data(self) -> Optional[str]:
        """
        备份旧数据
        
        Returns:
            Optional[str]: 备份文件路径，失败返回None
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"legacy_data_backup_{timestamp}.zip"
            backup_path = os.path.join(os.path.dirname(self.legacy_storage_path), backup_filename)
            
            # 创建zip备份
            import zipfile
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 备份项目目录
                if os.path.exists(self.legacy_projects_dir):
                    for root, dirs, files in os.walk(self.legacy_projects_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, self.legacy_storage_path)
                            zipf.write(file_path, arcname)
                
                # 备份全局配置
                if os.path.exists(self.legacy_config_path):
                    arcname = os.path.relpath(self.legacy_config_path, self.legacy_storage_path)
                    zipf.write(self.legacy_config_path, arcname)
            
            return backup_path
            
        except Exception as e:
            logger.error(f"备份旧数据失败: {e}")
            return None
    
    def validate_migration(self) -> Dict[str, Any]:
        """
        验证迁移结果
        
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            validation_result = {
                'valid': True,
                'issues': [],
                'statistics': {
                    'legacy_projects': 0,
                    'db_projects': 0,
                    'missing_projects': [],
                    'legacy_has_config': False,
                    'db_has_config': False
                }
            }
            
            # 检查旧数据
            legacy_info = self.detect_legacy_data()
            if legacy_info:
                validation_result['statistics']['legacy_projects'] = legacy_info.project_count
                validation_result['statistics']['legacy_has_config'] = legacy_info.has_global_config
                
                # 检查每个项目是否已迁移
                if os.path.exists(self.legacy_projects_dir):
                    project_dirs = [d for d in os.listdir(self.legacy_projects_dir) 
                                  if os.path.isdir(os.path.join(self.legacy_projects_dir, d))]
                    
                    for project_id in project_dirs:
                        # 检查数据库中是否存在
                        db_project = self.db_storage.load_project(project_id)
                        if not db_project:
                            validation_result['statistics']['missing_projects'].append(project_id)
                            validation_result['issues'].append(f"项目未迁移: {project_id}")
            
            # 检查数据库数据
            db_projects = self.db_storage.load_all_projects()
            validation_result['statistics']['db_projects'] = len(db_projects)
            
            db_config = self.db_storage.load_global_config()
            validation_result['statistics']['db_has_config'] = bool(db_config.current_project_id or db_config.recent_projects)
            
            # 验证数据一致性
            if validation_result['statistics']['missing_projects']:
                validation_result['valid'] = False
            
            if legacy_info and legacy_info.has_global_config and not validation_result['statistics']['db_has_config']:
                validation_result['valid'] = False
                validation_result['issues'].append("全局配置未迁移")
            
            logger.info(f"迁移验证完成: {'通过' if validation_result['valid'] else '失败'}")
            return validation_result
            
        except Exception as e:
            logger.error(f"验证迁移失败: {e}")
            return {
                'valid': False,
                'issues': [f"验证过程异常: {e}"],
                'statistics': {}
            }
    
    def rollback_migration(self, backup_path: str) -> bool:
        """
        回滚迁移（从备份恢复旧数据）
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            bool: 回滚是否成功
        """
        try:
            if not os.path.exists(backup_path):
                logger.error(f"备份文件不存在: {backup_path}")
                return False
            
            # 删除当前旧数据目录
            if os.path.exists(self.legacy_storage_path):
                shutil.rmtree(self.legacy_storage_path)
            
            # 从备份恢复
            import zipfile
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(self.legacy_storage_path)
            
            logger.info(f"迁移已回滚，数据从 {backup_path} 恢复")
            return True
            
        except Exception as e:
            logger.error(f"回滚迁移失败: {e}")
            return False
    
    def cleanup_legacy_data(self, confirm: bool = False) -> bool:
        """
        清理旧数据文件
        
        Args:
            confirm: 确认清理
            
        Returns:
            bool: 清理是否成功
        """
        if not confirm:
            logger.warning("清理旧数据需要确认")
            return False
        
        try:
            if os.path.exists(self.legacy_storage_path):
                shutil.rmtree(self.legacy_storage_path)
                logger.info(f"旧数据已清理: {self.legacy_storage_path}")
                return True
            else:
                logger.info("没有发现需要清理的旧数据")
                return True
                
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
            return False
    
    def get_migration_status(self) -> Dict[str, Any]:
        """
        获取迁移状态信息
        
        Returns:
            Dict[str, Any]: 迁移状态信息
        """
        try:
            legacy_info = self.detect_legacy_data()
            db_projects = self.db_storage.load_all_projects()
            
            status = {
                'has_legacy_data': legacy_info is not None,
                'legacy_info': {
                    'project_count': legacy_info.project_count if legacy_info else 0,
                    'has_global_config': legacy_info.has_global_config if legacy_info else False,
                    'total_size': legacy_info.total_size if legacy_info else 0,
                    'last_modified': legacy_info.last_modified.isoformat() if legacy_info and legacy_info.last_modified else None
                },
                'database_info': {
                    'project_count': len(db_projects),
                    'has_data': len(db_projects) > 0
                },
                'migration_needed': legacy_info is not None and legacy_info.project_count > 0,
                'storage_paths': {
                    'legacy_storage': self.legacy_storage_path,
                    'legacy_projects': self.legacy_projects_dir,
                    'legacy_config': self.legacy_config_path
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"获取迁移状态失败: {e}")
            return {
                'has_legacy_data': False,
                'migration_needed': False,
                'error': str(e)
            }