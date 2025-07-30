#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Swagger文档解析器
"""

import json
import logging
import os
import yaml
import requests
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class SwaggerParser:
    """Swagger文档解析器，用于解析Swagger文档并提取API信息"""

    def __init__(self):
        """初始化解析器"""
        self.swagger_data = None
        self.api_list = []
        self.base_url = ""
        self.data_generator = None  # 数据生成器实例

    def load_from_url(self, url):
        """
        从URL加载Swagger文档
        
        Args:
            url (str): Swagger文档的URL
            
        Returns:
            bool: 是否成功加载
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # 尝试解析JSON
            try:
                self.swagger_data = response.json()
            except json.JSONDecodeError:
                # 如果不是JSON，尝试解析YAML
                try:
                    self.swagger_data = yaml.safe_load(response.text)
                except yaml.YAMLError as e:
                    logger.error(f"解析YAML格式失败: {e}")
                    return False
            
            # 设置基本URL
            parsed_url = urlparse(url)
            self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # 创建数据生成器并设置Swagger数据
            from core.data_generator import DataGenerator
            self.data_generator = DataGenerator(self.swagger_data)
            
            # 解析API列表
            self._parse_apis()
            return True
            
        except requests.RequestException as e:
            logger.error(f"从URL加载Swagger文档失败: {e}")
            return False

    def load_from_file(self, file_path):
        """
        从本地文件加载Swagger文档
        
        Args:
            file_path (str): Swagger文档的文件路径
            
        Returns:
            bool: 是否成功加载
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return False
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
                
            # 根据文件扩展名尝试不同的解析方法
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext in ['.json']:
                self.swagger_data = json.loads(file_content)
            elif file_ext in ['.yaml', '.yml']:
                self.swagger_data = yaml.safe_load(file_content)
            else:
                # 如果扩展名不明确，尝试两种方式
                try:
                    self.swagger_data = json.loads(file_content)
                except json.JSONDecodeError:
                    try:
                        self.swagger_data = yaml.safe_load(file_content)
                    except yaml.YAMLError as e:
                        logger.error(f"无法解析文件: {e}")
                        return False
            
            # 创建数据生成器并设置Swagger数据
            from core.data_generator import DataGenerator
            self.data_generator = DataGenerator(self.swagger_data)
            
            # 解析API列表
            self._parse_apis()
            return True
            
        except Exception as e:
            logger.error(f"从文件加载Swagger文档失败: {e}")
            return False

    def _parse_apis(self):
        """
        解析Swagger文档中的API信息
        """
        if not self.swagger_data:
            logger.error("没有可解析的Swagger数据")
            return
            
        self.api_list = []
        
        # 确定Swagger版本
        swagger_version = self.swagger_data.get('swagger', self.swagger_data.get('openapi', ''))
        
        # 基础URL获取
        if 'host' in self.swagger_data and not self.base_url:
            scheme = self.swagger_data.get('schemes', ['http'])[0]
            host = self.swagger_data.get('host', '')
            basePath = self.swagger_data.get('basePath', '/')
            self.base_url = f"{scheme}://{host}{basePath}"
        elif 'servers' in self.swagger_data and not self.base_url:
            # OpenAPI 3.0
            if self.swagger_data['servers'] and 'url' in self.swagger_data['servers'][0]:
                self.base_url = self.swagger_data['servers'][0]['url']
        
        # 解析路径和操作
        paths = self.swagger_data.get('paths', {})
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                    api_info = {
                        'path': path,
                        'method': method.upper(),
                        'summary': operation.get('summary', ''),
                        'description': operation.get('description', ''),
                        'tags': operation.get('tags', []),
                        'operationId': operation.get('operationId', ''),
                        'parameters': self._parse_parameters(operation, swagger_version),
                        'requestBody': self._parse_request_body(operation, swagger_version),
                        'responses': self._parse_responses(operation),
                        'requires_auth': self._check_auth_required(operation)
                    }
                    
                    self.api_list.append(api_info)

    def _parse_parameters(self, operation, swagger_version):
        """解析API参数"""
        print(f"正在解析参数，操作: {operation.get('operationId', '未知操作')}")
        """
        解析API参数
        
        Args:
            operation (dict): API操作定义
            swagger_version (str): Swagger版本
            
        Returns:
            list: 参数列表
        """
        parameters = []
        
        # 直接在操作中定义的参数
        for param in operation.get('parameters', []):
            # 对于引用的参数，需要解析引用
            if '$ref' in param:
                ref_param = self._resolve_reference(param['$ref'])
                if ref_param:
                    parameters.append(ref_param)
            else:
                parameters.append(param)
                
        return parameters

    def _parse_request_body(self, operation, swagger_version):
        """
        解析请求体
        
        Args:
            operation (dict): API操作定义
            swagger_version (str): Swagger版本
            
        Returns:
            dict: 请求体信息
        """
        # OpenAPI 3.0 使用 requestBody
        if 'requestBody' in operation:
            request_body = operation['requestBody']
            
            # 处理引用
            if '$ref' in request_body:
                resolved = self._resolve_reference(request_body['$ref'])
                if resolved:
                    request_body = resolved
            
            # 处理content中的引用
            if 'content' in request_body:
                for content_type, media_type in request_body['content'].items():
                    if 'schema' in media_type:
                        schema = media_type['schema']
                        # 处理schema引用
                        if '$ref' in schema:
                            resolved_schema = self._resolve_reference(schema['$ref'])
                            if resolved_schema:
                                media_type['schema'] = resolved_schema
            
            return request_body
            
        # Swagger 2.0 中，请求体是通过参数类型 "body" 定义的
        for param in operation.get('parameters', []):
            # 处理参数引用
            if '$ref' in param:
                param = self._resolve_reference(param['$ref']) or param
                
            if param.get('in') == 'body':
                schema = param.get('schema', {})
                
                # 处理schema引用
                if '$ref' in schema:
                    resolved_schema = self._resolve_reference(schema['$ref'])
                    if resolved_schema:
                        schema = resolved_schema
                
                return {
                    'content': {
                        'application/json': {
                            'schema': schema
                        }
                    },
                    'required': param.get('required', False)
                }
                
        return None

    def _parse_responses(self, operation):
        """
        解析响应
        
        Args:
            operation (dict): API操作定义
            
        Returns:
            dict: 响应信息
        """
        return operation.get('responses', {})

    def _check_auth_required(self, operation):
        """
        检查API是否需要认证
        
        Args:
            operation (dict): API操作定义
            
        Returns:
            bool: 是否需要认证
        """
        # 检查是否有安全定义
        if 'security' in operation and operation['security']:
            return True
            
        # 检查参数中是否有认证相关参数
        for param in operation.get('parameters', []):
            if param.get('name', '').lower() in ['authorization', 'token', 'api_key', 'apikey']:
                return True
                
        return False

    def _resolve_reference(self, ref_path):
        """
        解析引用
        
        Args:
            ref_path (str): 引用路径
            
        Returns:
            dict: 引用对象
        """
        if not ref_path.startswith('#/'):
            logger.warning(f"不支持的引用路径: {ref_path}")
            return None
            
        # 移除开头的 #/
        path_parts = ref_path[2:].split('/')
        
        # 从swagger数据中获取引用对象
        current = self.swagger_data
        for part in path_parts:
            if part in current:
                current = current[part]
            else:
                logger.warning(f"引用路径不存在: {ref_path}")
                return None
                
        return current

    def get_api_list(self):
        """
        获取API列表
        
        Returns:
            list: API信息列表
        """
        return self.api_list

    def get_api_by_index(self, index):
        """
        根据索引获取API信息
        
        Args:
            index (int): API索引
            
        Returns:
            dict: API信息
        """
        if 0 <= index < len(self.api_list):
            return self.api_list[index]
        return None

    def get_base_url(self):
        """
        获取基础URL
        
        Returns:
            str: 基础URL
        """
        return self.base_url
