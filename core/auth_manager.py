#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
认证管理模块
"""

import json
import logging
import os
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AuthManager:
    """
    认证管理器，用于管理API认证信息和处理认证请求
    """
    
    def __init__(self, config_dir="./config"):
        """
        初始化认证管理器
        
        Args:
            config_dir (str): 配置文件目录
        """
        self.config_dir = config_dir
        self.auth_config = {
            'bearer': {
                'login_url': '',
                'method': 'POST',
                'headers': {},
                'data': {},
                'token_path': 'token',
                'use_prefix': False,  # 默认不使用前缀
                'custom_prefix': 'Bearer '  # 默认前缀值
            }
        }
        
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        # 尝试加载配置
        self.load_config()
        
        # 如果没有配置，设置一些默认值以便演示
        if not self.auth_config or 'bearer' not in self.auth_config:
            self.set_default_auth_config()
        
    def load_config(self):
        """
        从文件加载认证配置
        
        Returns:
            bool: 是否成功加载
        """
        config_path = os.path.join(self.config_dir, "auth_config.json")
        
        if not os.path.exists(config_path):
            logger.info("认证配置文件不存在，使用默认配置")
            return False
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.auth_config = json.load(f)
            logger.info("成功加载认证配置")
            return True
        except Exception as e:
            logger.error(f"加载认证配置失败: {e}")
            return False
            
    def save_config(self):
        """
        保存认证配置到文件
        
        Returns:
            bool: 是否成功保存
        """
        config_path = os.path.join(self.config_dir, "auth_config.json")
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.auth_config, f, ensure_ascii=False, indent=2)
            logger.info("成功保存认证配置")
            return True
        except Exception as e:
            logger.error(f"保存认证配置失败: {e}")
            return False
            
    def set_auth_config(self, auth_type, config):
        """
        设置认证配置
        
        Args:
            auth_type (str): 认证类型，如 'bearer', 'basic', 'api_key'
            config (dict): 认证配置信息
            
        Returns:
            bool: 是否成功设置
        """
        self.auth_config[auth_type] = config
        return self.save_config()
        
    def get_auth_config(self, auth_type=None):
        """
        获取认证配置

        Args:
            auth_type (str, optional): 认证类型，如果为None则返回所有配置

        Returns:
            dict: 认证配置信息
        """
        if auth_type:
            return self.auth_config.get(auth_type, {})
        return self.auth_config

    def set_config(self, config: dict):
        """
        设置完整的认证配置（用于项目级别的配置）

        Args:
            config (dict): 完整的认证配置字典
        """
        if config and isinstance(config, dict):
            # 更新内存中的配置
            self.auth_config.update(config)
            logger.info(f"已加载项目认证配置，包含认证类型: {list(config.keys())}")
        else:
            logger.warning("项目认证配置为空或格式不正确")

    def get_config(self):
        """
        获取完整的认证配置

        Returns:
            dict: 完整的认证配置字典
        """
        return self.auth_config.copy()
        
    def login(self, auth_type="bearer"):
        """
        执行登录请求获取认证token

        Args:
            auth_type (str): 认证类型

        Returns:
            tuple: (是否成功, 详细消息)
        """
        config = self.auth_config.get(auth_type, {})

        if not config or not config.get('login_url'):
            error_msg = f"未找到{auth_type}类型的登录配置或登录URL为空"
            logger.error(error_msg)
            return False, error_msg

        login_url = config['login_url']
        method = config.get('method', 'POST').upper()

        # 获取Bearer Token配置中的基础headers
        base_headers = config.get('headers', {})

        # 获取自定义请求头
        custom_headers = self.auth_config.get('custom_headers', {})

        # 合并所有请求头
        headers = {}
        headers.update(base_headers)  # 先添加基础headers
        headers.update(custom_headers)  # 再添加自定义headers（会覆盖同名的基础headers）

        data = config.get('data', {})

        logger.info(f"开始登录请求: {method} {login_url}")
        logger.debug(f"基础请求头: {base_headers}")
        logger.debug(f"自定义请求头: {custom_headers}")
        logger.debug(f"合并后请求头: {headers}")
        logger.debug(f"请求数据: {data}")

        try:
            if method == 'POST':
                response = requests.post(login_url, json=data, headers=headers, timeout=10)
            elif method == 'GET':
                response = requests.get(login_url, params=data, headers=headers, timeout=10)
            else:
                error_msg = f"不支持的请求方法: {method}"
                logger.error(error_msg)
                return False, error_msg

            logger.info(f"登录响应状态码: {response.status_code}")

            # 检查HTTP状态码
            if response.status_code != 200:
                error_msg = f"登录请求失败，HTTP状态码: {response.status_code}\n响应内容: {response.text[:500]}"
                logger.error(error_msg)
                return False, error_msg

            # 解析响应获取token
            try:
                response_data = response.json()
                logger.debug(f"登录响应数据: {response_data}")
            except json.JSONDecodeError as e:
                error_msg = f"登录响应不是有效的JSON格式\n响应内容: {response.text[:500]}\n错误: {str(e)}"
                logger.error(error_msg)
                return False, error_msg

            token_path = config.get('token_path', 'token').split('.')
            logger.debug(f"Token路径: {token_path}")

            # 遍历token路径获取token值
            token_value = response_data
            for key in token_path:
                if isinstance(token_value, dict) and key in token_value:
                    token_value = token_value[key]
                else:
                    error_msg = f"无法从响应中提取token，找不到路径: {'.'.join(token_path)}\n当前路径: {key}\n响应数据结构: {list(response_data.keys()) if isinstance(response_data, dict) else type(response_data)}"
                    logger.error(error_msg)
                    return False, error_msg

            if not token_value:
                error_msg = f"Token值为空，路径: {'.'.join(token_path)}\n响应数据: {response_data}"
                logger.error(error_msg)
                return False, error_msg

            # 保存token
            config['token'] = token_value
            self.save_config()  # 保存token到配置
            success_msg = f"成功获取{auth_type}认证token: {str(token_value)[:50]}..."
            logger.info(success_msg)
            return True, success_msg

        except requests.ConnectionError as e:
            error_msg = f"网络连接错误，无法连接到登录服务器\nURL: {login_url}\n错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except requests.Timeout as e:
            error_msg = f"登录请求超时（10秒）\nURL: {login_url}\n错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except requests.RequestException as e:
            error_msg = f"登录请求失败\nURL: {login_url}\n错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"登录过程中发生未知错误: {str(e)}\nURL: {login_url}"
            logger.error(error_msg)
            return False, error_msg
            
    def get_auth_headers(self, auth_type="bearer"):
        """
        获取认证头信息
        
        Args:
            auth_type (str): 认证类型
            
        Returns:
            dict: 认证头信息
        """
        if auth_type not in self.auth_config:
            return {}
            
        config = self.auth_config[auth_type]
        
        # 根据不同认证类型生成头信息
        if auth_type == 'bearer':
            # 直接从配置获取token
            token = config.get('token', '')
            use_prefix = config.get('use_prefix', False)  # 默认不使用前缀
            custom_prefix = config.get('custom_prefix', 'Bearer ')  # 默认前缀

            if token:
                if use_prefix:
                    # 确保前缀以空格结尾（如果用户没有添加的话）
                    prefix = custom_prefix if custom_prefix.endswith(' ') else custom_prefix + ' '
                    return {"Authorization": f"{prefix}{token}"}
                else:
                    return {"Authorization": token}
            return {}
        elif auth_type == 'basic':
            username = config.get('username', '')
            password = config.get('password', '')
            import base64
            auth_str = base64.b64encode(f"{username}:{password}".encode()).decode()
            return {"Authorization": f"Basic {auth_str}"}
        elif auth_type == 'api_key':
            key_name = config.get('key_name', 'api_key')
            key_value = config.get('key_value', '')
            key_in = config.get('in', 'header')
            
            if key_in.lower() == 'header':
                return {key_name: key_value}
            else:
                # 如果API key在query或其他位置，返回空头信息
                return {}
                
        return {}

    def get_all_headers(self, auth_type="bearer"):
        """
        获取所有请求头（包括认证头和自定义请求头）

        Args:
            auth_type (str): 认证类型

        Returns:
            dict: 所有请求头信息
        """
        headers = {}

        # 获取认证头
        auth_headers = self.get_auth_headers(auth_type)
        headers.update(auth_headers)

        # 获取自定义请求头
        custom_headers_config = self.auth_config.get('custom_headers', {})
        if 'headers' in custom_headers_config:
            headers.update(custom_headers_config['headers'])

        return headers

    def apply_auth(self, request_kwargs, auth_type="bearer"):
        """
        将认证信息应用到请求参数中
        
        Args:
            request_kwargs (dict): 请求参数字典
            auth_type (str): 认证类型
            
        Returns:
            dict: 应用认证信息后的请求参数
        """
        if auth_type not in self.auth_config:
            return request_kwargs
            
        config = self.auth_config[auth_type]
        
        # 复制请求参数，避免修改原始参数
        kwargs = request_kwargs.copy()
        
        # 获取所有头信息（认证头 + 自定义请求头）
        all_headers = self.get_all_headers(auth_type)

        # 合并头信息
        headers = kwargs.get('headers', {})
        headers.update(all_headers)
        kwargs['headers'] = headers
        
        # 如果是API key且在query中
        if auth_type == 'api_key' and config.get('in', '').lower() == 'query':
            key_name = config.get('key_name', 'api_key')
            key_value = config.get('key_value', '')
            
            # 获取查询参数
            params = kwargs.get('params', {})
            if isinstance(params, dict):
                params[key_name] = key_value
                kwargs['params'] = params
                
        return kwargs
        
    def test_auth_config(self, auth_type="bearer"):
        """
        测试认证配置是否有效

        Args:
            auth_type (str): 认证类型

        Returns:
            tuple: (是否成功, 消息)
        """
        if auth_type not in self.auth_config:
            return False, f"未找到{auth_type}类型的认证配置"

        # 对于bearer认证，检查是否有token
        if auth_type == 'bearer':
            success, message = self.login(auth_type)
            return success, message
                
        # 对于basic认证，检查是否有用户名和密码
        elif auth_type == 'basic':
            config = self.auth_config[auth_type]
            if 'username' in config and 'password' in config:
                return True, "Basic认证配置有效"
            else:
                return False, "Basic认证配置无效，缺少用户名或密码"
                
        # 对于API key认证，检查是否有key名称和值
        elif auth_type == 'api_key':
            config = self.auth_config[auth_type]
            if 'key_name' in config and 'key_value' in config:
                return True, "API Key认证配置有效"
            else:
                return False, "API Key认证配置无效，缺少key名称或值"
                
        return False, "不支持的认证类型"
    
    def get_bearer_token(self):
        """
        获取Bearer token
        
        Returns:
            str: Bearer token或空字符串
        """
        return self.auth_config.get('bearer', {}).get('token', '')
    
    def get_basic_username(self):
        """
        获取Basic认证用户名
        
        Returns:
            str: 用户名或空字符串
        """
        return self.auth_config.get('basic', {}).get('username', '')
    
    def get_basic_password(self):
        """
        获取Basic认证密码
        
        Returns:
            str: 密码或空字符串
        """
        return self.auth_config.get('basic', {}).get('password', '')
    
    def get_api_key(self):
        """
        获取API Key
        
        Returns:
            str: API Key或空字符串
        """
        return self.auth_config.get('api_key', {}).get('key_value', '')
    
    def get_api_key_header(self):
        """
        获取API Key的header名称
        
        Returns:
            str: Header名称或默认值'api_key'
        """
        return self.auth_config.get('api_key', {}).get('key_name', 'api_key')
    
    def set_default_auth_config(self):
        """
        设置默认的认证配置（仅用于演示）
        """
        # Bearer Token配置
        self.auth_config['bearer'] = {
            'token': 'demo-bearer-token-123456',
            'use_prefix': False,  # 默认不使用前缀
            'custom_prefix': 'Bearer '  # 默认前缀值
        }
        
        # Basic认证配置
        self.auth_config['basic'] = {
            'username': 'demo_user',
            'password': 'demo_pass'
        }
        
        # API Key配置
        self.auth_config['api_key'] = {
            'key_name': 'X-API-Key',
            'key_value': 'demo-api-key-789',
            'in': 'header'
        }
        
        logger.info("已设置默认认证配置")
