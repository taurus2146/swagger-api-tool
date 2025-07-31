#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
项目数据模型
"""

import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class SwaggerSource:
    """Swagger文档来源配置"""
    type: str  # "url" or "file"
    location: str  # URL or file path
    last_modified: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            'type': self.type,
            'location': self.location
        }
        if self.last_modified:
            result['last_modified'] = self.last_modified.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SwaggerSource':
        """从字典创建对象"""
        last_modified = None
        if 'last_modified' in data and data['last_modified']:
            last_modified = datetime.fromisoformat(data['last_modified'])
        
        return cls(
            type=data['type'],
            location=data['location'],
            last_modified=last_modified
        )


@dataclass
class Project:
    """项目配置数据模型"""
    id: str
    name: str
    description: str
    swagger_source: SwaggerSource
    base_url: str
    auth_config: Dict[str, Any]
    created_at: datetime
    last_accessed: datetime
    api_count: int = 0
    ui_state: Optional[Dict[str, Any]] = None
    tags: Optional[list] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.ui_state is None:
            self.ui_state = {}
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> dict:
        """转换为字典用于序列化"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'swagger_source': self.swagger_source.to_dict(),
            'base_url': self.base_url,
            'auth_config': self.auth_config,
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'api_count': self.api_count,
            'ui_state': self.ui_state,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Project':
        """从字典创建项目对象"""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            swagger_source=SwaggerSource.from_dict(data['swagger_source']),
            base_url=data['base_url'],
            auth_config=data.get('auth_config', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            last_accessed=datetime.fromisoformat(data['last_accessed']),
            api_count=data.get('api_count', 0),
            ui_state=data.get('ui_state', {}),
            tags=data.get('tags', [])
        )
    
    @classmethod
    def create_new(cls, name: str, description: str, swagger_source: SwaggerSource, 
                   base_url: str = "", auth_config: Dict[str, Any] = None) -> 'Project':
        """创建新项目"""
        now = datetime.now()
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            swagger_source=swagger_source,
            base_url=base_url,
            auth_config=auth_config or {},
            created_at=now,
            last_accessed=now,
            api_count=0,
            ui_state={},
            tags=[]
        )
    
    def update_last_accessed(self):
        """更新最后访问时间"""
        self.last_accessed = datetime.now()
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Project':
        """从JSON字符串创建项目对象"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class GlobalConfig:
    """全局配置"""
    current_project_id: Optional[str] = None
    recent_projects: list = None
    settings: Dict[str, Any] = None
    version: str = "1.0"
    
    def __post_init__(self):
        """初始化后处理"""
        if self.recent_projects is None:
            self.recent_projects = []
        if self.settings is None:
            self.settings = {
                "auto_load_last_project": True,
                "max_recent_projects": 5,
                "backup_enabled": True
            }
    
    def add_recent_project(self, project_id: str):
        """添加最近使用的项目"""
        if project_id in self.recent_projects:
            self.recent_projects.remove(project_id)
        
        self.recent_projects.insert(0, project_id)
        
        # 限制最近项目数量
        max_recent = self.settings.get("max_recent_projects", 5)
        self.recent_projects = self.recent_projects[:max_recent]
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'current_project_id': self.current_project_id,
            'recent_projects': self.recent_projects,
            'settings': self.settings,
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GlobalConfig':
        """从字典创建全局配置对象"""
        return cls(
            current_project_id=data.get('current_project_id'),
            recent_projects=data.get('recent_projects', []),
            settings=data.get('settings', {}),
            version=data.get('version', '1.0')
        )
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'GlobalConfig':
        """从JSON字符串创建全局配置对象"""
        data = json.loads(json_str)
        return cls.from_dict(data)
