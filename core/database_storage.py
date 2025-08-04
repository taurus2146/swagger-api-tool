#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于数据库的项目数据持久化存储
替代原有的基于JSON文件的ProjectStorage
"""

import json
import logging
import tempfile
import zipfile
import os
from typing import Optional, List, Dict, Any
from datetime import datetime

from .database_manager import DatabaseManager
from .project_models import Project, SwaggerSource, GlobalConfig
from .storage_utils import get_default_database_path

logger = logging.getLogger(__name__)


class DatabaseStorage:
    """基于SQLite数据库的项目数据存储类"""
    
    def __init__(self, db_path: str = None):
        """
        初始化数据库存储
        
        Args:
            db_path: 数据库文件路径，如果为None则使用默认路径
        """
        if db_path is None:
            db_path = get_default_database_path()
        
        self.db_manager = DatabaseManager(db_path)
        self._ensure_database_ready()
    
    def _ensure_database_ready(self) -> bool:
        """确保数据库已连接并初始化"""
        if not self.db_manager.connect():
            logger.error("数据库连接失败")
            return False
        
        if not self.db_manager.initialize_database():
            logger.error("数据库初始化失败")
            return False
        
        # 检查是否需要迁移
        current_version = self.db_manager.get_database_version()
        if current_version and current_version < self.db_manager.CURRENT_VERSION:
            if not self.db_manager.migrate_database():
                logger.error("数据库迁移失败")
                return False
        
        return True
    
    def _project_to_dict(self, project: Project) -> Dict[str, Any]:
        """
        将Project对象转换为数据库存储格式
        
        Args:
            project: Project对象
            
        Returns:
            Dict[str, Any]: 数据库存储格式的字典
        """
        return {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'swagger_source_type': project.swagger_source.type,
            'swagger_source_location': project.swagger_source.location,
            'swagger_source_last_modified': project.swagger_source.last_modified.isoformat() if project.swagger_source.last_modified else None,
            'base_url': project.base_url,
            'auth_config': json.dumps(project.auth_config) if project.auth_config else None,
            'created_at': project.created_at.isoformat(),
            'last_accessed': project.last_accessed.isoformat(),
            'api_count': project.api_count,
            'ui_state': json.dumps(project.ui_state) if project.ui_state else None,
            'tags': json.dumps(project.tags) if project.tags else None,
            'version': project.version if hasattr(project, 'version') else 1,
            'is_active': True
        }
    
    def _dict_to_project(self, data: Dict[str, Any]) -> Project:
        """
        将数据库记录转换为Project对象
        
        Args:
            data: 数据库记录字典
            
        Returns:
            Project: Project对象
        """
        # 创建SwaggerSource对象
        swagger_source = SwaggerSource(
            type=data['swagger_source_type'],
            location=data['swagger_source_location'],
            last_modified=datetime.fromisoformat(data['swagger_source_last_modified']) if data['swagger_source_last_modified'] else None
        )
        
        # 解析JSON字段
        auth_config = json.loads(data['auth_config']) if data['auth_config'] else {}
        ui_state = json.loads(data['ui_state']) if data['ui_state'] else {}
        tags = json.loads(data['tags']) if data['tags'] else []
        
        # 创建Project对象
        project = Project(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            swagger_source=swagger_source,
            base_url=data['base_url'],
            auth_config=auth_config,
            created_at=datetime.fromisoformat(data['created_at']),
            last_accessed=datetime.fromisoformat(data['last_accessed']),
            api_count=data['api_count'],
            ui_state=ui_state,
            tags=tags
        )
        
        return project
    
    def save_project(self, project: Project) -> bool:
        """
        保存项目配置
        
        Args:
            project: 要保存的项目对象
            
        Returns:
            bool: 保存是否成功
        """
        try:
            project_data = self._project_to_dict(project)
            
            # 检查项目是否已存在
            existing = self.db_manager.execute_query(
                "SELECT id FROM projects WHERE id = ?", (project.id,)
            )
            
            if existing:
                # 更新现有项目
                sql = '''
                    UPDATE projects SET 
                        name = ?, description = ?, swagger_source_type = ?, 
                        swagger_source_location = ?, swagger_source_last_modified = ?,
                        base_url = ?, auth_config = ?, last_accessed = ?,
                        api_count = ?, ui_state = ?, tags = ?, version = ?
                    WHERE id = ?
                '''
                params = (
                    project_data['name'], project_data['description'], 
                    project_data['swagger_source_type'], project_data['swagger_source_location'],
                    project_data['swagger_source_last_modified'], project_data['base_url'],
                    project_data['auth_config'], project_data['last_accessed'],
                    project_data['api_count'], project_data['ui_state'], 
                    project_data['tags'], project_data['version'], project.id
                )
            else:
                # 插入新项目
                sql = '''
                    INSERT INTO projects (
                        id, name, description, swagger_source_type, swagger_source_location,
                        swagger_source_last_modified, base_url, auth_config, created_at,
                        last_accessed, api_count, ui_state, tags, version, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                params = (
                    project_data['id'], project_data['name'], project_data['description'],
                    project_data['swagger_source_type'], project_data['swagger_source_location'],
                    project_data['swagger_source_last_modified'], project_data['base_url'],
                    project_data['auth_config'], project_data['created_at'],
                    project_data['last_accessed'], project_data['api_count'],
                    project_data['ui_state'], project_data['tags'], 
                    project_data['version'], project_data['is_active']
                )
            
            success = self.db_manager.execute_update(sql, params)
            if success:
                logger.info(f"项目配置已保存: {project.name} ({project.id})")
            else:
                logger.error(f"保存项目配置失败: {project.name} ({project.id})")
            
            return success
            
        except Exception as e:
            logger.error(f"保存项目时发生异常: {e}")
            return False
    
    def load_project(self, project_id: str) -> Optional[Project]:
        """
        加载项目配置
        
        Args:
            project_id: 项目ID
            
        Returns:
            Optional[Project]: 项目对象，如果不存在返回None
        """
        try:
            result = self.db_manager.execute_query(
                "SELECT * FROM projects WHERE id = ? AND is_active = 1", (project_id,)
            )
            
            if not result:
                logger.warning(f"项目不存在或已被删除: {project_id}")
                return None
            
            # 转换为字典格式
            row = result[0]
            data = dict(row)  # sqlite3.Row对象可以转换为字典
            
            project = self._dict_to_project(data)
            logger.info(f"项目配置加载成功: {project.name} ({project.id})")
            return project
            
        except Exception as e:
            logger.error(f"加载项目配置失败: {e}")
            return None
    
    def load_all_projects(self) -> List[Project]:
        """
        加载所有活跃项目
        
        Returns:
            List[Project]: 项目列表
        """
        try:
            results = self.db_manager.execute_query(
                "SELECT * FROM projects WHERE is_active = 1 ORDER BY last_accessed DESC"
            )
            
            if not results:
                logger.info("没有找到任何项目")
                return []
            
            projects = []
            for row in results:
                try:
                    data = dict(row)
                    project = self._dict_to_project(data)
                    projects.append(project)
                except Exception as e:
                    logger.error(f"解析项目数据失败: {e}")
                    continue
            
            logger.info(f"成功加载 {len(projects)} 个项目")
            return projects
            
        except Exception as e:
            logger.error(f"加载所有项目失败: {e}")
            return []
    
    def delete_project(self, project_id: str) -> bool:
        """
        删除项目（软删除）
        
        Args:
            project_id: 项目ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 检查项目是否存在
            existing = self.db_manager.execute_query(
                "SELECT id FROM projects WHERE id = ? AND is_active = 1", (project_id,)
            )
            
            if not existing:
                logger.warning(f"尝试删除不存在的项目: {project_id}")
                return False
            
            # 软删除：设置is_active为False
            success = self.db_manager.execute_update(
                "UPDATE projects SET is_active = 0 WHERE id = ?", (project_id,)
            )
            
            if success:
                logger.info(f"项目已删除: {project_id}")
            else:
                logger.error(f"删除项目失败: {project_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除项目时发生异常: {e}")
            return False
    
    def search_projects(self, query: str) -> List[Project]:
        """
        搜索项目
        
        Args:
            query: 搜索关键词
            
        Returns:
            List[Project]: 匹配的项目列表
        """
        try:
            # 使用LIKE进行模糊搜索
            search_pattern = f"%{query}%"
            results = self.db_manager.execute_query('''
                SELECT * FROM projects 
                WHERE is_active = 1 AND (
                    name LIKE ? OR 
                    description LIKE ? OR 
                    base_url LIKE ?
                )
                ORDER BY last_accessed DESC
            ''', (search_pattern, search_pattern, search_pattern))
            
            if not results:
                return []
            
            projects = []
            for row in results:
                try:
                    data = dict(row)
                    project = self._dict_to_project(data)
                    projects.append(project)
                except Exception as e:
                    logger.error(f"解析搜索结果失败: {e}")
                    continue
            
            logger.info(f"搜索 '{query}' 找到 {len(projects)} 个项目")
            return projects
            
        except Exception as e:
            logger.error(f"搜索项目失败: {e}")
            return []
    
    def export_project(self, project: Project, export_path: str) -> bool:
        """
        导出项目为zip文件
        
        Args:
            project: 要导出的项目
            export_path: 导出文件路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # 创建项目配置文件
                config_file = os.path.join(temp_dir, 'config.json')
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(project.to_json())
                
                # 创建项目历史文件
                history = self.get_project_history(project.id)
                if history:
                    history_file = os.path.join(temp_dir, 'history.json')
                    with open(history_file, 'w', encoding='utf-8') as f:
                        json.dump(history, f, ensure_ascii=False, indent=2, default=str)
                
                # 创建zip文件
                with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arcname)
            
            logger.info(f"项目 {project.name} 已导出至 {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出项目失败: {e}")
            return False
    
    def import_project(self, import_path: str) -> Optional[Project]:
        """
        从zip文件导入项目
        
        Args:
            import_path: 导入文件路径
            
        Returns:
            Optional[Project]: 导入的项目对象，失败返回None
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # 解压zip文件
                with zipfile.ZipFile(import_path, 'r') as zipf:
                    zipf.extractall(temp_dir)
                
                # 读取配置文件
                config_file = os.path.join(temp_dir, 'config.json')
                if not os.path.exists(config_file):
                    logger.error(f"导入失败: {import_path} 中缺少 config.json")
                    return None
                
                with open(config_file, 'r', encoding='utf-8') as f:
                    project = Project.from_json(f.read())
                
                # 检查项目是否已存在
                existing = self.load_project(project.id)
                if existing:
                    # 生成新的ID避免冲突
                    import uuid
                    old_id = project.id
                    project.id = str(uuid.uuid4())
                    logger.info(f"项目ID冲突，已生成新ID: {old_id} -> {project.id}")
                
                # 保存项目
                if self.save_project(project):
                    logger.info(f"项目 {project.name} 已从 {import_path} 导入")
                    return project
                else:
                    logger.error("保存导入的项目失败")
                    return None
                    
        except Exception as e:
            logger.error(f"导入项目失败: {e}")
            return None
    
    def get_project_history(self, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取项目操作历史
        
        Args:
            project_id: 项目ID
            limit: 返回记录数限制
            
        Returns:
            List[Dict[str, Any]]: 历史记录列表
        """
        try:
            results = self.db_manager.execute_query('''
                SELECT * FROM project_history 
                WHERE project_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (project_id, limit))
            
            if not results:
                return []
            
            history = []
            for row in results:
                record = dict(row)
                # 解析details字段
                if record['details']:
                    try:
                        record['details'] = json.loads(record['details'])
                    except json.JSONDecodeError:
                        pass
                history.append(record)
            
            return history
            
        except Exception as e:
            logger.error(f"获取项目历史失败: {e}")
            return []
    
    def save_global_config(self, config: GlobalConfig) -> bool:
        """
        保存全局配置
        
        Args:
            config: 全局配置对象
            
        Returns:
            bool: 保存是否成功
        """
        try:
            config_dict = config.to_dict()
            
            # 保存每个配置项
            for key, value in config_dict.items():
                # 确定值的类型
                if isinstance(value, bool):
                    value_str = 'true' if value else 'false'
                    value_type = 'boolean'
                elif isinstance(value, int):
                    value_str = str(value)
                    value_type = 'integer'
                elif isinstance(value, (list, dict)):
                    value_str = json.dumps(value, ensure_ascii=False)
                    value_type = 'json'
                else:
                    value_str = str(value)
                    value_type = 'string'
                
                # 插入或更新配置项
                self.db_manager.execute_update('''
                    INSERT OR REPLACE INTO global_config (key, value, type, updated_at)
                    VALUES (?, ?, ?, ?)
                ''', (key, value_str, value_type, datetime.now().isoformat()))
            
            logger.info("全局配置已保存")
            return True
            
        except Exception as e:
            logger.error(f"保存全局配置失败: {e}")
            return False
    
    def load_global_config(self) -> GlobalConfig:
        """
        加载全局配置
        
        Returns:
            GlobalConfig: 全局配置对象
        """
        try:
            results = self.db_manager.execute_query(
                "SELECT key, value, type FROM global_config WHERE is_system = 0"
            )
            
            config_data = {}
            
            if results:
                for row in results:
                    key, value_str, value_type = row['key'], row['value'], row['type']
                    
                    # 根据类型转换值
                    if value_type == 'boolean':
                        value = value_str.lower() == 'true'
                    elif value_type == 'integer':
                        value = int(value_str)
                    elif value_type == 'json':
                        value = json.loads(value_str)
                    else:
                        value = value_str
                    
                    config_data[key] = value
            
            # 创建GlobalConfig对象
            config = GlobalConfig(
                current_project_id=config_data.get('current_project_id'),
                recent_projects=config_data.get('recent_projects', []),
                settings=config_data.get('settings', {}),
                version=config_data.get('version', '1.0')
            )
            
            logger.info("全局配置加载成功")
            return config
            
        except Exception as e:
            logger.error(f"加载全局配置失败: {e}")
            return GlobalConfig()  # 返回默认配置
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        获取存储信息
        
        Returns:
            Dict[str, Any]: 存储信息字典
        """
        info = self.db_manager.get_connection_info()
        
        # 添加额外的统计信息
        try:
            # 获取活跃项目数量
            active_projects = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM projects WHERE is_active = 1"
            )
            info['active_projects'] = active_projects[0][0] if active_projects else 0
            
            # 获取总项目数量（包括已删除）
            total_projects = self.db_manager.execute_query("SELECT COUNT(*) FROM projects")
            info['total_projects'] = total_projects[0][0] if total_projects else 0
            
            # 获取历史记录数量
            history_count = self.db_manager.execute_query("SELECT COUNT(*) FROM project_history")
            info['history_records'] = history_count[0][0] if history_count else 0
            
            # 获取缓存记录数量
            cache_count = self.db_manager.execute_query("SELECT COUNT(*) FROM api_cache")
            info['cache_records'] = cache_count[0][0] if cache_count else 0
            
        except Exception as e:
            logger.error(f"获取存储统计信息失败: {e}")
        
        return info
    
    def cleanup_deleted_projects(self) -> int:
        """
        清理已删除的项目数据
        
        Returns:
            int: 清理的项目数量
        """
        try:
            # 获取已删除项目的ID列表
            deleted_projects = self.db_manager.execute_query(
                "SELECT id FROM projects WHERE is_active = 0"
            )
            
            if not deleted_projects:
                return 0
            
            deleted_ids = [row[0] for row in deleted_projects]
            
            # 删除相关的历史记录
            for project_id in deleted_ids:
                self.db_manager.execute_update(
                    "DELETE FROM project_history WHERE project_id = ?", (project_id,)
                )
                self.db_manager.execute_update(
                    "DELETE FROM api_cache WHERE project_id = ?", (project_id,)
                )
            
            # 删除项目记录
            deleted_count = len(deleted_ids)
            self.db_manager.execute_update("DELETE FROM projects WHERE is_active = 0")
            
            logger.info(f"已清理 {deleted_count} 个已删除的项目")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理已删除项目失败: {e}")
            return 0
    
    def close(self):
        """关闭数据库连接"""
        if self.db_manager:
            self.db_manager.disconnect()