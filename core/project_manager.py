#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
项目工作区核心管理类
"""

import logging
from typing import List, Optional
import threading
import time

from .project_models import Project, SwaggerSource
from .database_storage import DatabaseStorage
from .storage_utils import get_default_storage_path
from .database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ProjectManager:
    """核心管理类，协调所有项目相关操作"""

    def __init__(self, storage_path: str = None):
        if storage_path is None:
            storage_path = get_default_storage_path()

        # 获取数据库文件的完整路径（优先使用配置的路径）
        db_path = self._get_configured_database_path()
        
        # 初始化数据库管理器
        self.db_manager = DatabaseManager(db_path)
        if not self.db_manager.connect():
            logger.error("数据库连接失败")
        else:
            self.db_manager.initialize_database()
        
        # 检查并执行数据迁移（向后兼容性）
        self._check_and_migrate_legacy_data(storage_path)
        
        # 使用新的DatabaseStorage（传入数据库文件路径）
        self.storage = DatabaseStorage(db_path)
        
        # 加载项目和配置
        try:
            self.projects = {p.id: p for p in self.storage.load_all_projects()}
            self.global_config = self.storage.load_global_config()
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            # 如果加载失败，初始化空数据
            self.projects = {}
            from .project_models import GlobalConfig
            self.global_config = GlobalConfig()
        
        self.current_project: Optional[Project] = None
        
        self._load_current_project_on_startup()
        
        # 自动保存线程
        self._stop_autosave = threading.Event()
        self._autosave_thread = threading.Thread(target=self._autosave_loop, daemon=True)
        self._autosave_thread.start()
        logger.info("项目管理器已初始化，使用数据库存储")

    def _get_configured_database_path(self):
        """获取配置的数据库路径"""
        import json
        import os
        from .storage_utils import get_default_storage_path, get_default_database_path

        try:
            config_dir = get_default_storage_path()
            config_file = os.path.join(config_dir, "database_path.json")

            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    configured_path = config_data.get("database_path")
                    if configured_path and os.path.isabs(configured_path):
                        logger.info(f"使用配置的数据库路径: {configured_path}")
                        return configured_path
        except Exception as e:
            logger.warning(f"加载数据库路径配置失败: {e}")

        # 返回默认路径
        default_path = get_default_database_path()
        logger.info(f"使用默认数据库路径: {default_path}")
        return default_path

    def _load_current_project_on_startup(self):
        """启动时加载当前项目"""
        if self.global_config.settings.get("auto_load_last_project", True):
            if self.global_config.current_project_id in self.projects:
                self.set_current_project(self.global_config.current_project_id)

    def create_project(self, name: str, description: str, swagger_source: SwaggerSource, 
                       base_url: str = "", auth_config: dict = None) -> Project:
        """创建新项目"""
        project = Project.create_new(name, description, swagger_source, base_url, auth_config)
        self.projects[project.id] = project
        self.storage.save_project(project)
        logger.info(f"新项目已创建: {name} ({project.id})")
        return project

    def load_project(self, project_id: str) -> Optional[Project]:
        """加载项目"""
        if project_id in self.projects:
            project = self.projects[project_id]
            project.update_last_accessed()
            self.storage.save_project(project)  # 更新访问时间
            logger.info(f"项目加载成功: {project.name} ({project.id})")
            return project
        logger.warning(f"尝试加载不存在的项目: {project_id}")
        return None

    def get_all_projects(self) -> List[Project]:
        """获取所有项目"""
        return list(self.projects.values())
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """获取项目（不更新访问时间）"""
        return self.projects.get(project_id)

    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        if project_id in self.projects:
            del self.projects[project_id]
            if self.global_config.current_project_id == project_id:
                self.global_config.current_project_id = None
                self.current_project = None
            if project_id in self.global_config.recent_projects:
                self.global_config.recent_projects.remove(project_id)
            
            self.save_global_config()
            return self.storage.delete_project(project_id)
        return False

    def import_project(self, import_path: str) -> Optional[Project]:
        """导入项目"""
        project = self.storage.import_project(import_path)
        if project:
            self.projects[project.id] = project
            logger.info(f"项目 {project.name} 已成功导入")
        return project

    def export_project(self, project_id: str, export_path: str) -> bool:
        """导出项目"""
        if project_id in self.projects:
            project = self.projects[project_id]
            return self.storage.export_project(project, export_path)
        logger.warning(f"尝试导出不存在的项目: {project_id}")
        return False

    def get_recent_projects(self, limit: int = 5) -> List[Project]:
        """获取最近使用的项目"""
        recent_ids = self.global_config.recent_projects[:limit]
        return [self.projects[pid] for pid in recent_ids if pid in self.projects]

    def set_current_project(self, project_id: str) -> Optional[Project]:
        """设置当前项目"""
        project = self.load_project(project_id)
        if project:
            self.current_project = project
            self.global_config.current_project_id = project_id
            self.global_config.add_recent_project(project_id)
            self.save_global_config()
            logger.info(f"当前项目已设置为: {project.name} ({project.id})")
        return project

    def get_current_project(self) -> Optional[Project]:
        """获取当前项目"""
        return self.current_project
    
    def update_project(self, project: Project) -> bool:
        """更新项目信息"""
        if project.id in self.projects:
            self.projects[project.id] = project
            logger.info(f"项目更新成功: {project.name} ({project.id})")
            return self.storage.save_project(project)
        return False
    
    def save_global_config(self):
        """保存全局配置"""
        self.storage.save_global_config(self.global_config)
    
    def _autosave_loop(self):
        """自动保存循环"""
        while not self._stop_autosave.is_set():
            time.sleep(30)  # 每30秒保存一次
            self.save_global_config()
            if self.current_project:
                self.update_project(self.current_project)
    
    def shutdown(self):
        """关闭项目管理器"""
        logger.info("正在关闭项目管理器...")
        self._stop_autosave.set()
        self._autosave_thread.join()
        # 最后保存一次
        self.save_global_config()
        if self.current_project:
            self.update_project(self.current_project)
        logger.info("项目管理器已关闭")
    
    def _check_and_migrate_legacy_data(self, storage_path: str):
        """检查并迁移旧版本数据"""
        try:
            import os
            from .migration_service import MigrationService
            
            # 检查是否存在旧的JSON数据文件
            legacy_files = [
                os.path.join(os.path.dirname(storage_path), 'projects.json'),
                os.path.join(os.path.dirname(storage_path), 'global_config.json')
            ]
            
            has_legacy_data = any(os.path.exists(f) for f in legacy_files)
            
            if has_legacy_data:
                logger.info("检测到旧版本数据文件，开始迁移...")
                migration_service = MigrationService(storage_path)
                
                # 执行迁移
                migration_result = migration_service.migrate_from_json(
                    os.path.dirname(storage_path)
                )
                
                if migration_result['success']:
                    logger.info(f"数据迁移成功: {migration_result['migrated_projects']} 个项目已迁移")
                else:
                    logger.error(f"数据迁移失败: {migration_result.get('error', '未知错误')}")
            
        except Exception as e:
            logger.warning(f"数据迁移检查失败: {e}")
    
    def get_database_info(self) -> dict:
        """获取数据库信息"""
        try:
            return {
                'database_path': self.db_manager.db_path,
                'database_version': self.db_manager.get_database_version(),
                'total_projects': len(self.projects),
                'current_project': self.current_project.name if self.current_project else None,
                'storage_type': 'SQLite Database'
            }
        except Exception as e:
            logger.error(f"获取数据库信息失败: {e}")
            return {
                'error': str(e),
                'storage_type': 'Unknown'
            }
    
    def perform_database_maintenance(self) -> dict:
        """执行数据库维护"""
        try:
            from .database_diagnostics import DatabaseMaintenanceManager
            
            maintenance_manager = DatabaseMaintenanceManager(self.db_manager.db_path)
            result = maintenance_manager.run_auto_maintenance()
            
            logger.info(f"数据库维护完成: {result['successful_tasks']}/{result['total_tasks']} 任务成功")
            return result
        except Exception as e:
            logger.error(f"数据库维护失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

