#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
项目数据仓储类
提供项目数据的高级查询和操作功能，实现仓储模式
"""

import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .database_manager import DatabaseManager
from .project_models import Project, SwaggerSource

logger = logging.getLogger(__name__)


class SortOrder(Enum):
    """排序方向枚举"""
    ASC = "ASC"
    DESC = "DESC"


class ProjectSortField(Enum):
    """项目排序字段枚举"""
    NAME = "name"
    CREATED_AT = "created_at"
    LAST_ACCESSED = "last_accessed"
    LAST_MODIFIED = "last_modified"
    API_COUNT = "api_count"


@dataclass
class ProjectFilter:
    """项目过滤条件"""
    name_pattern: Optional[str] = None
    description_pattern: Optional[str] = None
    swagger_source_type: Optional[str] = None
    base_url_pattern: Optional[str] = None
    tags: Optional[List[str]] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    accessed_after: Optional[datetime] = None
    accessed_before: Optional[datetime] = None
    min_api_count: Optional[int] = None
    max_api_count: Optional[int] = None


@dataclass
class ProjectStats:
    """项目统计信息"""
    total_projects: int
    active_projects: int
    deleted_projects: int
    total_apis: int
    avg_apis_per_project: float
    most_recent_access: Optional[datetime]
    oldest_project: Optional[datetime]
    projects_by_source_type: Dict[str, int]
    projects_created_last_30_days: int


@dataclass
class PageResult:
    """分页查询结果"""
    items: List[Project]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ProjectRepository:
    """项目数据仓储类"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        初始化项目仓储
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
    
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
    
    def create(self, project: Project) -> bool:
        """
        创建新项目
        
        Args:
            project: 项目对象
            
        Returns:
            bool: 创建是否成功
        """
        try:
            sql = '''
                INSERT INTO projects (
                    id, name, description, swagger_source_type, swagger_source_location,
                    swagger_source_last_modified, base_url, auth_config, created_at,
                    last_accessed, api_count, ui_state, tags, version, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            params = (
                project.id, project.name, project.description,
                project.swagger_source.type, project.swagger_source.location,
                project.swagger_source.last_modified.isoformat() if project.swagger_source.last_modified else None,
                project.base_url,
                json.dumps(project.auth_config) if project.auth_config else None,
                project.created_at.isoformat(), project.last_accessed.isoformat(),
                project.api_count,
                json.dumps(project.ui_state) if project.ui_state else None,
                json.dumps(project.tags) if project.tags else None,
                getattr(project, 'version', 1), True
            )
            
            success = self.db_manager.execute_update(sql, params)
            if success:
                logger.info(f"项目创建成功: {project.name} ({project.id})")
            
            return success
            
        except Exception as e:
            logger.error(f"创建项目失败: {e}")
            return False
    
    def read(self, project_id: str) -> Optional[Project]:
        """
        根据ID读取项目
        
        Args:
            project_id: 项目ID
            
        Returns:
            Optional[Project]: 项目对象，不存在返回None
        """
        try:
            result = self.db_manager.execute_query(
                "SELECT * FROM projects WHERE id = ? AND is_active = 1", (project_id,)
            )
            
            if not result:
                return None
            
            data = dict(result[0])
            return self._dict_to_project(data)
            
        except Exception as e:
            logger.error(f"读取项目失败: {e}")
            return None
    
    def update(self, project: Project) -> bool:
        """
        更新项目
        
        Args:
            project: 项目对象
            
        Returns:
            bool: 更新是否成功
        """
        try:
            sql = '''
                UPDATE projects SET 
                    name = ?, description = ?, swagger_source_type = ?, 
                    swagger_source_location = ?, swagger_source_last_modified = ?,
                    base_url = ?, auth_config = ?, last_accessed = ?,
                    api_count = ?, ui_state = ?, tags = ?, version = ?
                WHERE id = ? AND is_active = 1
            '''
            
            params = (
                project.name, project.description,
                project.swagger_source.type, project.swagger_source.location,
                project.swagger_source.last_modified.isoformat() if project.swagger_source.last_modified else None,
                project.base_url,
                json.dumps(project.auth_config) if project.auth_config else None,
                project.last_accessed.isoformat(), project.api_count,
                json.dumps(project.ui_state) if project.ui_state else None,
                json.dumps(project.tags) if project.tags else None,
                getattr(project, 'version', 1), project.id
            )
            
            success = self.db_manager.execute_update(sql, params)
            if success:
                logger.info(f"项目更新成功: {project.name} ({project.id})")
            
            return success
            
        except Exception as e:
            logger.error(f"更新项目失败: {e}")
            return False
    
    def delete(self, project_id: str) -> bool:
        """
        删除项目（软删除）
        
        Args:
            project_id: 项目ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            success = self.db_manager.execute_update(
                "UPDATE projects SET is_active = 0 WHERE id = ? AND is_active = 1", 
                (project_id,)
            )
            
            if success:
                logger.info(f"项目删除成功: {project_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除项目失败: {e}")
            return False
    
    def find_by_name(self, name: str, exact_match: bool = False) -> List[Project]:
        """
        根据名称查找项目
        
        Args:
            name: 项目名称
            exact_match: 是否精确匹配
            
        Returns:
            List[Project]: 匹配的项目列表
        """
        try:
            if exact_match:
                sql = "SELECT * FROM projects WHERE name = ? AND is_active = 1 ORDER BY last_accessed DESC"
                params = (name,)
            else:
                sql = "SELECT * FROM projects WHERE name LIKE ? AND is_active = 1 ORDER BY last_accessed DESC"
                params = (f"%{name}%",)
            
            results = self.db_manager.execute_query(sql, params)
            
            if not results:
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
            
            return projects
            
        except Exception as e:
            logger.error(f"按名称查找项目失败: {e}")
            return []
    
    def find_recent(self, limit: int = 10) -> List[Project]:
        """
        查找最近访问的项目
        
        Args:
            limit: 返回数量限制
            
        Returns:
            List[Project]: 最近访问的项目列表
        """
        try:
            results = self.db_manager.execute_query(
                "SELECT * FROM projects WHERE is_active = 1 ORDER BY last_accessed DESC LIMIT ?",
                (limit,)
            )
            
            if not results:
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
            
            return projects
            
        except Exception as e:
            logger.error(f"查找最近项目失败: {e}")
            return []
    
    def find_by_tag(self, tag: str) -> List[Project]:
        """
        根据标签查找项目
        
        Args:
            tag: 标签名称
            
        Returns:
            List[Project]: 包含该标签的项目列表
        """
        try:
            # 使用JSON函数查询标签
            sql = '''
                SELECT * FROM projects 
                WHERE is_active = 1 AND tags IS NOT NULL 
                AND json_extract(tags, '$') LIKE ?
                ORDER BY last_accessed DESC
            '''
            params = (f'%"{tag}"%',)
            
            results = self.db_manager.execute_query(sql, params)
            
            if not results:
                return []
            
            projects = []
            for row in results:
                try:
                    data = dict(row)
                    project = self._dict_to_project(data)
                    # 双重验证标签是否真的存在
                    if tag in project.tags:
                        projects.append(project)
                except Exception as e:
                    logger.error(f"解析项目数据失败: {e}")
                    continue
            
            return projects
            
        except Exception as e:
            logger.error(f"按标签查找项目失败: {e}")
            return []
    
    def find_by_source_type(self, source_type: str) -> List[Project]:
        """
        根据Swagger源类型查找项目
        
        Args:
            source_type: 源类型 ('url' 或 'file')
            
        Returns:
            List[Project]: 匹配的项目列表
        """
        try:
            results = self.db_manager.execute_query(
                "SELECT * FROM projects WHERE swagger_source_type = ? AND is_active = 1 ORDER BY last_accessed DESC",
                (source_type,)
            )
            
            if not results:
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
            
            return projects
            
        except Exception as e:
            logger.error(f"按源类型查找项目失败: {e}")
            return []
    
    def find_with_filter(self, filter_obj: ProjectFilter, 
                        sort_field: ProjectSortField = ProjectSortField.LAST_ACCESSED,
                        sort_order: SortOrder = SortOrder.DESC,
                        limit: Optional[int] = None) -> List[Project]:
        """
        使用过滤条件查找项目
        
        Args:
            filter_obj: 过滤条件对象
            sort_field: 排序字段
            sort_order: 排序方向
            limit: 结果数量限制
            
        Returns:
            List[Project]: 匹配的项目列表
        """
        try:
            # 构建WHERE子句
            where_conditions = ["is_active = 1"]
            params = []
            
            if filter_obj.name_pattern:
                where_conditions.append("name LIKE ?")
                params.append(f"%{filter_obj.name_pattern}%")
            
            if filter_obj.description_pattern:
                where_conditions.append("description LIKE ?")
                params.append(f"%{filter_obj.description_pattern}%")
            
            if filter_obj.swagger_source_type:
                where_conditions.append("swagger_source_type = ?")
                params.append(filter_obj.swagger_source_type)
            
            if filter_obj.base_url_pattern:
                where_conditions.append("base_url LIKE ?")
                params.append(f"%{filter_obj.base_url_pattern}%")
            
            if filter_obj.created_after:
                where_conditions.append("created_at >= ?")
                params.append(filter_obj.created_after.isoformat())
            
            if filter_obj.created_before:
                where_conditions.append("created_at <= ?")
                params.append(filter_obj.created_before.isoformat())
            
            if filter_obj.accessed_after:
                where_conditions.append("last_accessed >= ?")
                params.append(filter_obj.accessed_after.isoformat())
            
            if filter_obj.accessed_before:
                where_conditions.append("last_accessed <= ?")
                params.append(filter_obj.accessed_before.isoformat())
            
            if filter_obj.min_api_count is not None:
                where_conditions.append("api_count >= ?")
                params.append(filter_obj.min_api_count)
            
            if filter_obj.max_api_count is not None:
                where_conditions.append("api_count <= ?")
                params.append(filter_obj.max_api_count)
            
            # 构建SQL查询
            sql = f"SELECT * FROM projects WHERE {' AND '.join(where_conditions)}"
            sql += f" ORDER BY {sort_field.value} {sort_order.value}"
            
            if limit:
                sql += " LIMIT ?"
                params.append(limit)
            
            results = self.db_manager.execute_query(sql, tuple(params))
            
            if not results:
                return []
            
            projects = []
            for row in results:
                try:
                    data = dict(row)
                    project = self._dict_to_project(data)
                    
                    # 额外的标签过滤（因为JSON查询比较复杂）
                    if filter_obj.tags:
                        if not any(tag in project.tags for tag in filter_obj.tags):
                            continue
                    
                    projects.append(project)
                except Exception as e:
                    logger.error(f"解析项目数据失败: {e}")
                    continue
            
            return projects
            
        except Exception as e:
            logger.error(f"过滤查找项目失败: {e}")
            return []
    
    def find_with_pagination(self, page: int = 1, page_size: int = 20,
                           filter_obj: Optional[ProjectFilter] = None,
                           sort_field: ProjectSortField = ProjectSortField.LAST_ACCESSED,
                           sort_order: SortOrder = SortOrder.DESC) -> PageResult:
        """
        分页查询项目
        
        Args:
            page: 页码（从1开始）
            page_size: 每页大小
            filter_obj: 过滤条件
            sort_field: 排序字段
            sort_order: 排序方向
            
        Returns:
            PageResult: 分页结果
        """
        try:
            # 构建WHERE子句
            where_conditions = ["is_active = 1"]
            params = []
            
            if filter_obj:
                if filter_obj.name_pattern:
                    where_conditions.append("name LIKE ?")
                    params.append(f"%{filter_obj.name_pattern}%")
                
                if filter_obj.description_pattern:
                    where_conditions.append("description LIKE ?")
                    params.append(f"%{filter_obj.description_pattern}%")
                
                if filter_obj.swagger_source_type:
                    where_conditions.append("swagger_source_type = ?")
                    params.append(filter_obj.swagger_source_type)
                
                # 添加其他过滤条件...
            
            where_clause = " AND ".join(where_conditions)
            
            # 获取总数
            count_sql = f"SELECT COUNT(*) FROM projects WHERE {where_clause}"
            count_result = self.db_manager.execute_query(count_sql, tuple(params))
            total_count = count_result[0][0] if count_result else 0
            
            # 计算分页信息
            total_pages = (total_count + page_size - 1) // page_size
            offset = (page - 1) * page_size
            
            # 获取分页数据
            data_sql = f'''
                SELECT * FROM projects WHERE {where_clause}
                ORDER BY {sort_field.value} {sort_order.value}
                LIMIT ? OFFSET ?
            '''
            data_params = list(params) + [page_size, offset]
            
            results = self.db_manager.execute_query(data_sql, tuple(data_params))
            
            projects = []
            if results:
                for row in results:
                    try:
                        data = dict(row)
                        project = self._dict_to_project(data)
                        projects.append(project)
                    except Exception as e:
                        logger.error(f"解析项目数据失败: {e}")
                        continue
            
            return PageResult(
                items=projects,
                total_count=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1
            )
            
        except Exception as e:
            logger.error(f"分页查询项目失败: {e}")
            return PageResult(
                items=[], total_count=0, page=page, page_size=page_size,
                total_pages=0, has_next=False, has_prev=False
            )
    
    def get_statistics(self) -> ProjectStats:
        """
        获取项目统计信息
        
        Returns:
            ProjectStats: 统计信息对象
        """
        try:
            stats = ProjectStats(
                total_projects=0, active_projects=0, deleted_projects=0,
                total_apis=0, avg_apis_per_project=0.0,
                most_recent_access=None, oldest_project=None,
                projects_by_source_type={}, projects_created_last_30_days=0
            )
            
            # 基本统计
            basic_stats = self.db_manager.execute_query('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as deleted,
                    SUM(CASE WHEN is_active = 1 THEN api_count ELSE 0 END) as total_apis,
                    AVG(CASE WHEN is_active = 1 THEN api_count ELSE NULL END) as avg_apis
                FROM projects
            ''')
            
            if basic_stats:
                row = basic_stats[0]
                stats.total_projects = row[0] or 0
                stats.active_projects = row[1] or 0
                stats.deleted_projects = row[2] or 0
                stats.total_apis = row[3] or 0
                stats.avg_apis_per_project = float(row[4] or 0)
            
            # 时间统计
            time_stats = self.db_manager.execute_query('''
                SELECT 
                    MAX(last_accessed) as most_recent,
                    MIN(created_at) as oldest
                FROM projects WHERE is_active = 1
            ''')
            
            if time_stats and time_stats[0][0]:
                stats.most_recent_access = datetime.fromisoformat(time_stats[0][0])
                stats.oldest_project = datetime.fromisoformat(time_stats[0][1])
            
            # 按源类型统计
            source_stats = self.db_manager.execute_query('''
                SELECT swagger_source_type, COUNT(*) 
                FROM projects WHERE is_active = 1 
                GROUP BY swagger_source_type
            ''')
            
            if source_stats:
                stats.projects_by_source_type = {row[0]: row[1] for row in source_stats}
            
            # 最近30天创建的项目
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_stats = self.db_manager.execute_query('''
                SELECT COUNT(*) FROM projects 
                WHERE is_active = 1 AND created_at >= ?
            ''', (thirty_days_ago.isoformat(),))
            
            if recent_stats:
                stats.projects_created_last_30_days = recent_stats[0][0]
            
            return stats
            
        except Exception as e:
            logger.error(f"获取项目统计失败: {e}")
            return ProjectStats(
                total_projects=0, active_projects=0, deleted_projects=0,
                total_apis=0, avg_apis_per_project=0.0,
                most_recent_access=None, oldest_project=None,
                projects_by_source_type={}, projects_created_last_30_days=0
            )
    
    def get_all_tags(self) -> List[Tuple[str, int]]:
        """
        获取所有标签及其使用次数
        
        Returns:
            List[Tuple[str, int]]: 标签和使用次数的列表
        """
        try:
            # 获取所有项目的标签
            results = self.db_manager.execute_query(
                "SELECT tags FROM projects WHERE is_active = 1 AND tags IS NOT NULL"
            )
            
            if not results:
                return []
            
            # 统计标签使用次数
            tag_counts = {}
            for row in results:
                try:
                    tags = json.loads(row[0])
                    if isinstance(tags, list):
                        for tag in tags:
                            if isinstance(tag, str) and tag.strip():
                                tag = tag.strip()
                                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # 按使用次数排序
            sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_tags
            
        except Exception as e:
            logger.error(f"获取标签统计失败: {e}")
            return []
    
    def exists(self, project_id: str) -> bool:
        """
        检查项目是否存在
        
        Args:
            project_id: 项目ID
            
        Returns:
            bool: 项目是否存在
        """
        try:
            result = self.db_manager.execute_query(
                "SELECT 1 FROM projects WHERE id = ? AND is_active = 1", (project_id,)
            )
            return bool(result)
            
        except Exception as e:
            logger.error(f"检查项目存在性失败: {e}")
            return False
    
    def count_active_projects(self) -> int:
        """
        获取活跃项目数量
        
        Returns:
            int: 活跃项目数量
        """
        try:
            result = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM projects WHERE is_active = 1"
            )
            return result[0][0] if result else 0
            
        except Exception as e:
            logger.error(f"获取活跃项目数量失败: {e}")
            return 0