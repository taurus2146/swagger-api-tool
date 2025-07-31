#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
项目数据持久化存储
"""

import os
import json
import logging
import shutil
import tempfile
from typing import Optional, List

from .project_models import Project, GlobalConfig

logger = logging.getLogger(__name__)


class ProjectStorage:
    """负责项目数据的持久化存储"""

    def __init__(self, storage_path: str = "./projects"):
        self.storage_path = storage_path
        self.projects_dir = os.path.join(self.storage_path, "projects")
        self.global_config_path = os.path.join(self.storage_path, "global_config.json")
        self._ensure_dirs_exist()

    def _ensure_dirs_exist(self):
        """确保存储目录存在"""
        try:
            os.makedirs(self.projects_dir, exist_ok=True)
            logger.info(f"项目存储目录已创建: {self.projects_dir}")
        except OSError as e:
            logger.error(f"创建项目存储目录失败: {e}")

    def save_project(self, project: Project) -> bool:
        """保存项目配置"""
        project_path = os.path.join(self.projects_dir, project.id)
        os.makedirs(project_path, exist_ok=True)
        config_file = os.path.join(project_path, "config.json")
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(project.to_json())
            logger.info(f"项目配置已保存: {project.name} ({project.id})")
            return True
        except IOError as e:
            logger.error(f"保存项目配置失败: {e}")
            return False

    def load_project(self, project_id: str) -> Optional[Project]:
        """加载项目配置"""
        config_file = os.path.join(self.projects_dir, project_id, "config.json")
        if not os.path.exists(config_file):
            logger.warning(f"项目配置文件不存在: {config_file}")
            return None
            
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                project = Project.from_json(f.read())
            logger.info(f"项目配置加载成功: {project.name} ({project.id})")
            return project
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"加载项目配置失败: {e}")
            return None

    def load_all_projects(self) -> List[Project]:
        """加载所有项目"""
        projects = []
        if not os.path.exists(self.projects_dir):
            return projects

        for project_id in os.listdir(self.projects_dir):
            project = self.load_project(project_id)
            if project:
                projects.append(project)
        
        logger.info(f"成功加载 {len(projects)} 个项目")
        return projects

    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        project_path = os.path.join(self.projects_dir, project_id)
        if not os.path.exists(project_path):
            logger.warning(f"尝试删除不存在的项目: {project_id}")
            return False
            
        try:
            # 使用更安全的方式删除目录
            import shutil
            shutil.rmtree(project_path)
            logger.info(f"项目已删除: {project_id}")
            return True
        except OSError as e:
            logger.error(f"删除项目失败: {e}")
            return False

    def export_project(self, project: Project, export_path: str) -> bool:
        """导出项目为zip文件"""
        project_dir = os.path.join(self.projects_dir, project.id)
        try:
            shutil.make_archive(os.path.splitext(export_path)[0], 'zip', project_dir)
            logger.info(f"项目 {project.name} 已导出至 {export_path}")
            return True
        except Exception as e:
            logger.error(f"导出项目失败: {e}")
            return False

    def import_project(self, import_path: str) -> Optional[Project]:
        """从zip文件导入项目"""
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                shutil.unpack_archive(import_path, temp_dir, 'zip')
                config_file = os.path.join(temp_dir, 'config.json')
                if not os.path.exists(config_file):
                    logger.error(f"导入失败: {import_path} 中缺少 config.json")
                    return None

                with open(config_file, 'r', encoding='utf-8') as f:
                    project = Project.from_json(f.read())
                
                project_dir = os.path.join(self.projects_dir, project.id)
                if os.path.exists(project_dir):
                    # 这里可以添加覆盖确认逻辑，暂时直接覆盖
                    shutil.rmtree(project_dir)
                
                shutil.copytree(temp_dir, project_dir)
                logger.info(f"项目 {project.name} 已从 {import_path} 导入")
                return project

            except Exception as e:
                logger.error(f"导入项目失败: {e}")
                return None

    def save_global_config(self, config: GlobalConfig) -> bool:
        """保存全局配置"""
        try:
            with open(self.global_config_path, 'w', encoding='utf-8') as f:
                f.write(config.to_json())
            logger.info("全局配置已保存")
            return True
        except IOError as e:
            logger.error(f"保存全局配置失败: {e}")
            return False

    def load_global_config(self) -> GlobalConfig:
        """加载全局配置"""
        if not os.path.exists(self.global_config_path):
            logger.warning("全局配置文件不存在，将创建新的配置")
            return GlobalConfig()
            
        try:
            with open(self.global_config_path, 'r', encoding='utf-8') as f:
                config = GlobalConfig.from_json(f.read())
            logger.info("全局配置加载成功")
            return config
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"加载全局配置失败: {e}")
            return GlobalConfig()  # 返回默认配置
