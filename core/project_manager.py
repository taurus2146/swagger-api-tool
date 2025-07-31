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
from .project_storage import ProjectStorage

logger = logging.getLogger(__name__)


class ProjectManager:
    """核心管理类，协调所有项目相关操作"""

    def __init__(self, storage_path: str = "./projects"):
        self.storage = ProjectStorage(storage_path)
        self.projects = {p.id: p for p in self.storage.load_all_projects()}
        self.global_config = self.storage.load_global_config()
        self.current_project: Optional[Project] = None
        
        self._load_current_project_on_startup()
        
        # 自动保存线程
        self._stop_autosave = threading.Event()
        self._autosave_thread = threading.Thread(target=self._autosave_loop, daemon=True)
        self._autosave_thread.start()
        logger.info("自动保存线程已启动")

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

