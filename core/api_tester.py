#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API测试执行模块
"""

import json
import logging
import time
import requests
from datetime import datetime
from urllib.parse import urljoin
from .auth_manager import AuthManager
from .data_generator import DataGenerator

logger = logging.getLogger(__name__)


class ApiTester:
    """
    API测试器，用于执行API测试并收集结果
    """
    
    def __init__(self, base_url="", auth_manager=None):
        """
        初始化API测试器
        
        Args:
            base_url (str): API的基础URL
            auth_manager (AuthManager, optional): 认证管理器实例
        """
        self.base_url = base_url
        self.auth_manager = auth_manager or AuthManager()
        self.data_generator = DataGenerator()
        self.test_history = []
        
    def set_base_url(self, base_url):
        """
        设置基础URL
        
        Args:
            base_url (str): API的基础URL
        """
        self.base_url = base_url
    
    def _build_full_url(self, base_url, path):
        """
        智能构建完整URL，避免路径重复
        
        Args:
            base_url (str): 基础URL
            path (str): API路径
            
        Returns:
            str: 完整的URL
        """
        if not base_url or not path:
            return base_url + path if base_url else path
        
        # 规范化URL
        base_url = base_url.rstrip('/')
        path = path.lstrip('/') if path.startswith('/') else path
        
        logger.debug(f"规范化后: base_url='{base_url}', path='{path}'")
        
        # 检查是否存在路径重复
        # 例如：base_url = "http://localhost:8081/customer" 和 path = "customer/work-register/export/detail/92"
        
        # 提取base_url中的路径部分
        from urllib.parse import urlparse
        parsed_base = urlparse(base_url)
        base_path_parts = [p for p in parsed_base.path.split('/') if p]  # 移除空字符串
        path_parts = [p for p in path.split('/') if p]  # 移除空字符串
        
        logger.debug(f"base_path_parts: {base_path_parts}, path_parts: {path_parts}")
        
        # 检查path是否以base_url中的路径部分开头
        if base_path_parts and path_parts:
            # 找到重复的部分
            common_start = 0
            min_len = min(len(base_path_parts), len(path_parts))
            
            for i in range(min_len):
                if base_path_parts[i] == path_parts[i]:
                    common_start = i + 1
                else:
                    break
            
            if common_start > 0:
                # 移除重复的部分
                path_parts = path_parts[common_start:]
                path = '/'.join(path_parts)
                logger.debug(f"检测到路径重复，移除{common_start}个重复段，新path: '{path}'")
        
        # 拼接URL
        if path:
            full_url = f"{base_url}/{path}"
        else:
            full_url = base_url
        
        logger.debug(f"最终URL: '{full_url}'")
        return full_url
        
    def test_api(self, api_info, custom_data=None, use_auth=True, auth_type="bearer"):
        """
        测试单个API
        
        Args:
            api_info (dict): API信息
            custom_data (dict, optional): 自定义请求数据，覆盖自动生成的数据
            use_auth (bool): 是否使用认证
            auth_type (str): 认证类型
            
        Returns:
            dict: 测试结果
        """
        # 记录开始时间
        start_time = time.time()
        
        # 初始化测试结果
        test_result = {
            "api": api_info,
            "timestamp": datetime.now().isoformat(),
            "request": {},
            "response": {},
            "duration_ms": 0,
            "success": False,
            "error": None,
            "custom_data": custom_data,  # 保存自定义数据以便历史回显
            "use_auth": use_auth,
            "auth_type": auth_type
        }
        
        try:
            # 构建请求URL
            path = api_info.get('path', '')
            
            # 智能URL拼接，避免路径重复
            full_url = self._build_full_url(self.base_url, path)
            
            logger.debug(f"URL拼接: base_url='{self.base_url}', path='{path}', full_url='{full_url}'")
            
            # 获取请求方法
            method = api_info.get('method', 'GET').upper()
            
            # 生成或使用自定义参数数据
            if custom_data:
                # 验证自定义数据格式
                if not isinstance(custom_data, dict):
                    logger.warning(f"自定义数据格式不正确，期望dict，实际: {type(custom_data)}")
                    custom_data = {}

                # 确保自定义数据包含所有必需的键
                request_data = {
                    'path_params': custom_data.get('path_params', {}),
                    'query_params': custom_data.get('query_params', {}),
                    'headers': custom_data.get('headers', {}),
                    'body': custom_data.get('body')
                }
                logger.debug(f"使用自定义数据: {request_data}")
            else:
                # 为路径参数、查询参数和请求体生成数据
                parameters = api_info.get('parameters', [])
                request_body_schema = api_info.get('requestBody', {})

                param_data = self.data_generator.generate_parameter_data(parameters)
                body_data = self.data_generator.generate_request_body(request_body_schema)

                request_data = {
                    'path_params': param_data.get('path', {}),
                    'query_params': param_data.get('query', {}),
                    'headers': param_data.get('header', {}),
                    'body': body_data or param_data.get('body')
                }
                logger.debug(f"使用生成数据: {request_data}")
            
            # 替换URL中的路径参数
            for param_name, param_value in request_data.get('path_params', {}).items():
                old_url = full_url
                full_url = full_url.replace(f"{{{param_name}}}", str(param_value))
                logger.debug(f"路径参数替换: {param_name}={param_value}, URL: {old_url} -> {full_url}")

            # 构建请求参数
            request_kwargs = {
                'url': full_url,
                'params': request_data.get('query_params', {}),
                'headers': request_data.get('headers', {}),
                'timeout': 30
            }

            # 添加请求体（如果有）
            body_data = request_data.get('body')
            logger.debug(f"请求体数据: {body_data}, 类型: {type(body_data)}")

            # 支持所有可能有请求体的方法，包括DELETE
            if body_data is not None and method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                if isinstance(body_data, dict):
                    request_kwargs['json'] = body_data
                    logger.debug(f"设置JSON请求体: {body_data}")
                elif isinstance(body_data, str) and body_data.strip():
                    request_kwargs['data'] = body_data
                    logger.debug(f"设置文本请求体: {body_data}")
                else:
                    request_kwargs['data'] = body_data
                    logger.debug(f"设置其他类型请求体: {body_data}")

            # 设置请求头的Content-Type
            if method in ['POST', 'PUT', 'PATCH', 'DELETE'] and isinstance(body_data, dict):
                request_kwargs['headers'].setdefault('Content-Type', 'application/json')
                logger.debug("设置Content-Type为application/json")
            
            # 应用认证（如果需要）
            if use_auth:
                request_kwargs = self.auth_manager.apply_auth(request_kwargs, auth_type)
                logger.debug(f"应用{auth_type}认证")
            
            # 记录请求信息
            test_result['request'] = {
                'method': method,
                'url': full_url,
                'headers': request_kwargs.get('headers', {}),
                'params': request_kwargs.get('params', {}),
                'data': request_kwargs.get('json', request_kwargs.get('data', None))
            }
            
            # 执行请求
            response = requests.request(method, **request_kwargs)
            
            # 记录响应时间
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            # 尝试解析响应JSON
            response_data = None
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = response.text
            
            # 记录响应信息
            test_result['response'] = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': response_data
            }
            
            # 更新测试结果
            test_result['duration_ms'] = round(duration_ms, 2)
            test_result['success'] = 200 <= response.status_code < 300
            
        except Exception as e:
            # 记录错误信息
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            test_result['duration_ms'] = round(duration_ms, 2)
            test_result['error'] = str(e)
            logger.error(f"测试API时发生错误: {e}", exc_info=True)
            
            # 在异常情况下确保request_data存在
            request_data = {
                'path_params': {},
                'query_params': {},
                'headers': {},
                'body': None
            }
        
        # 为测试结果构建更完整的数据
        full_result = {
            'api': api_info,  # 保留完整的API信息
            'url': test_result['request'].get('url', ''),
            'method': test_result['request'].get('method', ''),
            'headers': test_result['request'].get('headers', {}),
            'query_params': test_result['request'].get('params', {}),  # 添加查询参数
            'path_params': request_data.get('path_params', {}),  # 添加路径参数
            'request_body': test_result['request'].get('data'),
            'response': {
                'status_code': test_result['response'].get('status_code', 0),
                'headers': test_result['response'].get('headers', {}),
                'body': test_result['response'].get('body'),
                'elapsed': test_result['duration_ms'] / 1000.0  # 转换为秒
            },
            'error': test_result.get('error'),
            'custom_data': test_result.get('custom_data'),
            'use_auth': test_result.get('use_auth'),
            'auth_type': test_result.get('auth_type')
        }
        
        # 保存测试历史
        self.test_history.append(test_result)
        
        return full_result
    
    def batch_test(self, api_list, use_auth=True, auth_type="bearer", progress_callback=None):
        """
        批量测试多个API
        
        Args:
            api_list (list): API信息列表
            use_auth (bool): 是否使用认证
            auth_type (str): 认证类型
            progress_callback (callable, optional): 进度回调函数
            
        Returns:
            list: 测试结果列表
        """
        results = []
        total_apis = len(api_list)
        
        for i, api_info in enumerate(api_list):
            # 执行单个API测试
            result = self.test_api(api_info, use_auth=use_auth, auth_type=auth_type)
            results.append(result)
            
            # 调用进度回调
            if progress_callback:
                progress = (i + 1) / total_apis * 100
                progress_callback(progress, i + 1, total_apis, result)
        
        return results
    
    def get_test_history(self, limit=None):
        """
        获取测试历史记录
        
        Args:
            limit (int, optional): 限制返回的记录数量
            
        Returns:
            list: 测试历史记录
        """
        if limit:
            return self.test_history[-limit:]
        return self.test_history
    
    def clear_test_history(self):
        """
        清除测试历史记录
        """
        self.test_history = []
    
    def generate_curl_command(self, test_result):
        """
        生成cURL命令
        
        Args:
            test_result (dict): 测试结果
            
        Returns:
            str: cURL命令字符串
        """
        if not test_result:
            logger.error("test_result 为空")
            return ""
            
        # 判断是否是新格式（从结果页面来的）
        if 'request' not in test_result:
            # 尝试从新格式中构建request对象
            if all(key in test_result for key in ['url', 'method']):
                # 这是结果页面的格式，构建request对象
                request = {
                    'method': test_result.get('method', 'GET'),
                    'url': test_result.get('url', ''),
                    'headers': test_result.get('headers', {}),
                    'params': test_result.get('query_params', {}),
                    'data': test_result.get('request_body')
                }
                logger.debug(f"从结果格式构建request: {request}")
            else:
                logger.error(f"test_result 中没有 request 字段且无法从其他字段构建: {test_result.keys()}")
                return ""
        else:
            request = test_result['request']
            
        method = request.get('method', 'GET')
        url = request.get('url', '')
        
        # 如果有API信息，尝试重新构建URL以避免路径重复
        api_info = test_result.get('api', {})
        if api_info and 'path' in api_info and self.base_url:
            # 获取原始路径
            original_path = api_info['path']
            
            # 替换路径参数
            path_params = test_result.get('path_params', {})
            for param_name, param_value in path_params.items():
                original_path = original_path.replace(f"{{{param_name}}}", str(param_value))
            
            # 重新构建URL
            url = self._build_full_url(self.base_url, original_path)
            logger.debug(f"重新构建URL: base_url='{self.base_url}', path='{original_path}', new_url='{url}'")
        
        headers = request.get('headers', {}).copy()  # 复制以避免修改原始数据
        params = request.get('params', {})
        data = request.get('data')
        
        # 处理认证信息
        use_auth = test_result.get('use_auth', True)
        auth_type = test_result.get('auth_type', 'bearer')
        
        logger.debug(f"generate_curl_command - use_auth: {use_auth}, auth_type: {auth_type}")
        
        if use_auth and self.auth_manager:
            auth_config = self.auth_manager.get_auth_config('bearer')
            use_prefix = auth_config.get('use_prefix', True)
            
            if auth_type == 'bearer':
                token = self.auth_manager.get_bearer_token()
                logger.debug(f"Bearer token: {'[EXISTS]' if token else '[EMPTY]'}")
                if token:
                    if use_prefix:
                        headers['Authorization'] = f'Bearer {token}'
                    else:
                        headers['Authorization'] = token
            elif auth_type == 'basic':
                username = self.auth_manager.get_basic_username()
                password = self.auth_manager.get_basic_password()
                logger.debug(f"Basic auth - username: {'[EXISTS]' if username else '[EMPTY]'}, password: {'[EXISTS]' if password else '[EMPTY]'}")
                if username and password:
                    import base64
                    credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
                    headers['Authorization'] = f'Basic {credentials}'
            elif auth_type == 'api_key':
                api_key = self.auth_manager.get_api_key()
                api_key_header = self.auth_manager.get_api_key_header()
                logger.debug(f"API Key - key: {'[EXISTS]' if api_key else '[EMPTY]'}, header: {api_key_header}")
                if api_key and api_key_header:
                    headers[api_key_header] = api_key
        
        logger.debug(f"Final headers for cURL: {headers}")
        
        # 构建基本命令
        curl_command = f'curl -X {method}'
        
        # 添加请求头
        for header_name, header_value in headers.items():
            curl_command += f' -H "{header_name}: {header_value}"'
        
        # 处理URL参数
        if params:
            param_strings = []
            for key, value in params.items():
                param_strings.append(f"{key}={value}")
            
            if '?' in url:
                url += '&' + '&'.join(param_strings)
            else:
                url += '?' + '&'.join(param_strings)
        
        # 添加数据
        if data:
            if isinstance(data, dict):
                data_str = json.dumps(data)
                curl_command += f' -d \'{data_str}\''
            else:
                curl_command += f' -d \'{data}\''
        
        # 添加URL
        curl_command += f' "{url}"'
        
        return curl_command
    
    def generate_postman_collection(self, test_results, collection_name="API Tests"):
        """
        生成Postman集合
        
        Args:
            test_results (list): 测试结果列表
            collection_name (str): 集合名称
            
        Returns:
            dict: Postman集合JSON对象
        """
        collection = {
            "info": {
                "name": collection_name,
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": []
        }
        
        for test_result in test_results:
            # 判断是否是新格式（从结果页面来的）
            if 'request' not in test_result:
                # 尝试从新格式中构建request对象
                if all(key in test_result for key in ['url', 'method']):
                    # 这是结果页面的格式，构建request对象
                    request = {
                        'method': test_result.get('method', 'GET'),
                        'url': test_result.get('url', ''),
                        'headers': test_result.get('headers', {}),
                        'params': test_result.get('query_params', {}),
                        'data': test_result.get('request_body')
                    }
                else:
                    continue
            else:
                request = test_result['request']
                
            api = test_result.get('api', {})
            
            # 获取认证信息
            use_auth = test_result.get('use_auth', True)
            auth_type = test_result.get('auth_type', 'bearer')
            
            # 创建请求项
            item = {
                "name": api.get('summary', api.get('operationId', request.get('url', 'API Request'))),
                "request": {
                    "method": request.get('method', 'GET'),
                    "header": [],
                    "url": {
                        "raw": request.get('url', ''),
                        "query": []
                    }
                }
            }
            
            # 添加认证信息
            if use_auth and self.auth_manager:
                if auth_type == 'bearer':
                    token = self.auth_manager.get_bearer_token()
                    if token:
                        item['request']['auth'] = {
                            "type": "bearer",
                            "bearer": [{
                                "key": "token",
                                "value": token,
                                "type": "string"
                            }]
                        }
                elif auth_type == 'basic':
                    username = self.auth_manager.get_basic_username()
                    password = self.auth_manager.get_basic_password()
                    if username and password:
                        item['request']['auth'] = {
                            "type": "basic",
                            "basic": [
                                {
                                    "key": "username",
                                    "value": username,
                                    "type": "string"
                                },
                                {
                                    "key": "password",
                                    "value": password,
                                    "type": "string"
                                }
                            ]
                        }
                elif auth_type == 'api_key':
                    api_key = self.auth_manager.get_api_key()
                    api_key_header = self.auth_manager.get_api_key_header()
                    if api_key and api_key_header:
                        item['request']['auth'] = {
                            "type": "apikey",
                            "apikey": [
                                {
                                    "key": "key",
                                    "value": api_key_header,
                                    "type": "string"
                                },
                                {
                                    "key": "value",
                                    "value": api_key,
                                    "type": "string"
                                },
                                {
                                    "key": "in",
                                    "value": "header",
                                    "type": "string"
                                }
                            ]
                        }
            
            # 添加请求头
            for header_name, header_value in request.get('headers', {}).items():
                item['request']['header'].append({
                    "key": header_name,
                    "value": header_value,
                    "type": "text"
                })
            
            # 添加查询参数
            for param_name, param_value in request.get('params', {}).items():
                item['request']['url']['query'].append({
                    "key": param_name,
                    "value": str(param_value)
                })
            
            # 添加请求体
            data = request.get('data')
            if data:
                if isinstance(data, dict):
                    item['request']['body'] = {
                        "mode": "raw",
                        "raw": json.dumps(data),
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    }
                else:
                    item['request']['body'] = {
                        "mode": "raw",
                        "raw": str(data)
                    }
            
            collection['item'].append(item)
        
        return collection
