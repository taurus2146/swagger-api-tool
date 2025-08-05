#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Swagger文档缓存管理器
负责Swagger文档的持久化存储、版本管理和缓存策略
"""

import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SwaggerDocument:
    """Swagger文档数据类"""
    id: Optional[int] = None
    project_id: str = ""
    content: str = ""
    content_hash: str = ""
    version: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    base_path: Optional[str] = None
    host: Optional[str] = None
    schemes: Optional[List[str]] = None
    consumes: Optional[List[str]] = None
    produces: Optional[List[str]] = None
    api_count: int = 0
    cached_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_current: bool = True
    source_url: Optional[str] = None
    source_etag: Optional[str] = None
    source_last_modified: Optional[datetime] = None


@dataclass
class SwaggerApi:
    """Swagger API数据类"""
    id: Optional[int] = None
    document_id: int = 0
    project_id: str = ""
    path: str = ""
    method: str = ""
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    parameters: Optional[Dict] = None
    request_body: Optional[Dict] = None
    responses: Optional[Dict] = None
    security: Optional[List[Dict]] = None
    deprecated: bool = False
    external_docs: Optional[Dict] = None
    created_at: Optional[datetime] = None


class SwaggerCacheManager:
    """Swagger文档缓存管理器"""
    
    def __init__(self, db_manager):
        """
        初始化缓存管理器
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
        self.cache_expiry_hours = 24  # 默认缓存24小时
        
    def calculate_content_hash(self, content: str) -> str:
        """
        计算内容哈希值
        
        Args:
            content: Swagger文档内容
            
        Returns:
            str: SHA256哈希值
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def extract_document_metadata(self, swagger_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从Swagger数据中提取元数据
        
        Args:
            swagger_data: 解析后的Swagger数据
            
        Returns:
            Dict[str, Any]: 提取的元数据
        """
        info = swagger_data.get('info', {})
        
        metadata = {
            'version': info.get('version'),
            'title': info.get('title'),
            'description': info.get('description'),
            'base_path': swagger_data.get('basePath'),
            'host': swagger_data.get('host'),
            'schemes': swagger_data.get('schemes', []),
            'consumes': swagger_data.get('consumes', []),
            'produces': swagger_data.get('produces', [])
        }
        
        # 计算API数量
        paths = swagger_data.get('paths', {})
        api_count = 0
        for path_data in paths.values():
            if isinstance(path_data, dict):
                api_count += len([k for k in path_data.keys() 
                                if k.lower() in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']])
        
        metadata['api_count'] = api_count
        
        return metadata
    
    def save_swagger_document(self, project_id: str, content: str, 
                            swagger_data: Dict[str, Any], source_url: Optional[str] = None,
                            source_etag: Optional[str] = None) -> Optional[int]:
        """
        保存Swagger文档到缓存
        
        Args:
            project_id: 项目ID
            content: 原始文档内容
            swagger_data: 解析后的Swagger数据
            source_url: 源URL（如果从URL加载）
            source_etag: HTTP ETag
            
        Returns:
            Optional[int]: 文档ID，失败返回None
        """
        try:
            content_hash = self.calculate_content_hash(content)
            
            # 检查是否已存在相同内容的文档
            existing = self.get_document_by_hash(project_id, content_hash)
            if existing:
                # 更新为当前版本
                self._set_current_document(project_id, existing.id)
                logger.info(f"Swagger文档已存在，更新为当前版本: {existing.id}")
                return existing.id
            
            # 提取元数据
            metadata = self.extract_document_metadata(swagger_data)
            
            # 设置缓存过期时间
            expires_at = datetime.now() + timedelta(hours=self.cache_expiry_hours)
            
            # 将当前文档设为非当前版本
            self._unset_current_documents(project_id)
            
            # 插入新文档
            sql = '''
                INSERT INTO swagger_documents (
                    project_id, content, content_hash, version, title, description,
                    base_path, host, schemes, consumes, produces, api_count,
                    cached_at, expires_at, is_current, source_url, source_etag
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            params = (
                project_id, content, content_hash, metadata.get('version'),
                metadata.get('title'), metadata.get('description'),
                metadata.get('base_path'), metadata.get('host'),
                json.dumps(metadata.get('schemes', [])),
                json.dumps(metadata.get('consumes', [])),
                json.dumps(metadata.get('produces', [])),
                metadata.get('api_count', 0),
                datetime.now(), expires_at, True, source_url, source_etag
            )
            
            # 使用事务执行插入并获取ID
            with self.db_manager.get_cursor() as cursor:
                cursor.execute(sql, params)
                document_id = cursor.lastrowid
            
            if document_id:
                # 保存API定义
                self._save_swagger_apis(document_id, project_id, swagger_data)
                logger.info(f"Swagger文档已缓存: {document_id}")
                
            return document_id
            
        except Exception as e:
            logger.error(f"保存Swagger文档失败: {e}")
            return None
    
    def get_current_document(self, project_id: str) -> Optional[SwaggerDocument]:
        """
        获取项目的当前Swagger文档
        
        Args:
            project_id: 项目ID
            
        Returns:
            Optional[SwaggerDocument]: 当前文档，不存在返回None
        """
        try:
            sql = '''
                SELECT * FROM swagger_documents 
                WHERE project_id = ? AND is_current = 1
                ORDER BY cached_at DESC LIMIT 1
            '''
            
            result = self.db_manager.execute_query(sql, (project_id,))
            
            if result:
                return self._row_to_document(result[0])
            
            return None
            
        except Exception as e:
            logger.error(f"获取当前Swagger文档失败: {e}")
            return None
    
    def get_document_by_hash(self, project_id: str, content_hash: str) -> Optional[SwaggerDocument]:
        """
        根据内容哈希获取文档
        
        Args:
            project_id: 项目ID
            content_hash: 内容哈希值
            
        Returns:
            Optional[SwaggerDocument]: 文档对象，不存在返回None
        """
        try:
            sql = '''
                SELECT * FROM swagger_documents 
                WHERE project_id = ? AND content_hash = ?
                ORDER BY cached_at DESC LIMIT 1
            '''
            
            result = self.db_manager.execute_query(sql, (project_id, content_hash))
            
            if result:
                return self._row_to_document(result[0])
            
            return None
            
        except Exception as e:
            logger.error(f"根据哈希获取Swagger文档失败: {e}")
            return None
    
    def is_document_expired(self, document: SwaggerDocument) -> bool:
        """
        检查文档是否过期
        
        Args:
            document: 文档对象
            
        Returns:
            bool: 是否过期
        """
        if not document.expires_at:
            return False
        
        return datetime.now() > document.expires_at
    
    def get_cached_swagger_data(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的Swagger数据
        
        Args:
            project_id: 项目ID
            
        Returns:
            Optional[Dict[str, Any]]: 解析后的Swagger数据，不存在或过期返回None
        """
        document = self.get_current_document(project_id)
        
        if not document:
            return None
        
        # 检查是否过期
        if self.is_document_expired(document):
            logger.info(f"Swagger文档已过期: {document.id}")
            return None
        
        try:
            return json.loads(document.content)
        except json.JSONDecodeError as e:
            logger.error(f"解析缓存的Swagger文档失败: {e}")
            return None

    def get_cached_apis(self, project_id: str) -> List[SwaggerApi]:
        """
        获取缓存的API列表

        Args:
            project_id: 项目ID

        Returns:
            List[SwaggerApi]: API列表
        """
        try:
            sql = '''
                SELECT sa.* FROM swagger_apis sa
                JOIN swagger_documents sd ON sa.document_id = sd.id
                WHERE sa.project_id = ? AND sd.is_current = 1
                ORDER BY sa.path, sa.method
            '''

            result = self.db_manager.execute_query(sql, (project_id,))

            if result:
                return [self._row_to_api(row) for row in result]

            return []

        except Exception as e:
            logger.error(f"获取缓存的API列表失败: {e}")
            return []

    def cleanup_expired_documents(self, project_id: Optional[str] = None) -> int:
        """
        清理过期的文档

        Args:
            project_id: 项目ID，None表示清理所有项目

        Returns:
            int: 清理的文档数量
        """
        try:
            if project_id:
                sql = '''
                    DELETE FROM swagger_documents
                    WHERE project_id = ? AND expires_at < ? AND is_current = 0
                '''
                params = (project_id, datetime.now())
            else:
                sql = '''
                    DELETE FROM swagger_documents
                    WHERE expires_at < ? AND is_current = 0
                '''
                params = (datetime.now(),)

            affected_rows = self.db_manager.execute_update(sql, params)

            if affected_rows > 0:
                logger.info(f"清理了 {affected_rows} 个过期的Swagger文档")

            return affected_rows

        except Exception as e:
            logger.error(f"清理过期文档失败: {e}")
            return 0

    def _set_current_document(self, project_id: str, document_id: int) -> bool:
        """设置当前文档"""
        try:
            # 先取消所有当前文档
            self._unset_current_documents(project_id)

            # 设置新的当前文档
            sql = 'UPDATE swagger_documents SET is_current = 1 WHERE id = ?'
            return self.db_manager.execute_update(sql, (document_id,)) > 0

        except Exception as e:
            logger.error(f"设置当前文档失败: {e}")
            return False

    def _unset_current_documents(self, project_id: str) -> bool:
        """取消项目的所有当前文档"""
        try:
            sql = 'UPDATE swagger_documents SET is_current = 0 WHERE project_id = ?'
            return self.db_manager.execute_update(sql, (project_id,)) >= 0

        except Exception as e:
            logger.error(f"取消当前文档失败: {e}")
            return False

    def _save_swagger_apis(self, document_id: int, project_id: str, swagger_data: Dict[str, Any]) -> bool:
        """保存API定义"""
        try:
            paths = swagger_data.get('paths', {})

            for path, path_data in paths.items():
                if not isinstance(path_data, dict):
                    continue

                for method, operation in path_data.items():
                    if method.lower() not in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                        continue

                    if not isinstance(operation, dict):
                        continue

                    # 提取API信息
                    api_data = {
                        'document_id': document_id,
                        'project_id': project_id,
                        'path': path,
                        'method': method.upper(),
                        'operation_id': operation.get('operationId'),
                        'summary': operation.get('summary'),
                        'description': operation.get('description'),
                        'tags': json.dumps(operation.get('tags', [])),
                        'parameters': json.dumps(operation.get('parameters', [])),
                        'request_body': json.dumps(operation.get('requestBody', {})),
                        'responses': json.dumps(operation.get('responses', {})),
                        'security': json.dumps(operation.get('security', [])),
                        'deprecated': operation.get('deprecated', False),
                        'external_docs': json.dumps(operation.get('externalDocs', {}))
                    }

                    # 插入API记录
                    sql = '''
                        INSERT INTO swagger_apis (
                            document_id, project_id, path, method, operation_id,
                            summary, description, tags, parameters, request_body,
                            responses, security, deprecated, external_docs
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    '''

                    params = (
                        api_data['document_id'], api_data['project_id'],
                        api_data['path'], api_data['method'], api_data['operation_id'],
                        api_data['summary'], api_data['description'], api_data['tags'],
                        api_data['parameters'], api_data['request_body'],
                        api_data['responses'], api_data['security'],
                        api_data['deprecated'], api_data['external_docs']
                    )

                    with self.db_manager.get_cursor() as cursor:
                        cursor.execute(sql, params)

            return True

        except Exception as e:
            logger.error(f"保存API定义失败: {e}")
            return False

    def _row_to_document(self, row) -> SwaggerDocument:
        """将数据库行转换为SwaggerDocument对象"""
        return SwaggerDocument(
            id=row['id'],
            project_id=row['project_id'],
            content=row['content'],
            content_hash=row['content_hash'],
            version=row['version'],
            title=row['title'],
            description=row['description'],
            base_path=row['base_path'],
            host=row['host'],
            schemes=json.loads(row['schemes']) if row['schemes'] else [],
            consumes=json.loads(row['consumes']) if row['consumes'] else [],
            produces=json.loads(row['produces']) if row['produces'] else [],
            api_count=row['api_count'],
            cached_at=datetime.fromisoformat(row['cached_at']) if row['cached_at'] else None,
            expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
            is_current=bool(row['is_current']),
            source_url=row['source_url'],
            source_etag=row['source_etag'],
            source_last_modified=datetime.fromisoformat(row['source_last_modified']) if row['source_last_modified'] else None
        )

    def _row_to_api(self, row) -> SwaggerApi:
        """将数据库行转换为SwaggerApi对象"""
        return SwaggerApi(
            id=row['id'],
            document_id=row['document_id'],
            project_id=row['project_id'],
            path=row['path'],
            method=row['method'],
            operation_id=row['operation_id'],
            summary=row['summary'],
            description=row['description'],
            tags=json.loads(row['tags']) if row['tags'] else [],
            parameters=json.loads(row['parameters']) if row['parameters'] else {},
            request_body=json.loads(row['request_body']) if row['request_body'] else {},
            responses=json.loads(row['responses']) if row['responses'] else {},
            security=json.loads(row['security']) if row['security'] else [],
            deprecated=bool(row['deprecated']),
            external_docs=json.loads(row['external_docs']) if row['external_docs'] else {},
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )
