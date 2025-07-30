#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试数据生成器
"""

import random
import string
import json
from faker import Faker

# 初始化Faker
fake = Faker('zh_CN')


class DataGenerator:
    """
    智能测试数据生成器，根据参数定义自动生成合理的测试数据
    """
    
    def __init__(self, swagger_data=None):
        """
        初始化数据生成器
        
        Args:
            swagger_data (dict, optional): Swagger文档数据，用于解析引用
        """
        self.swagger_data = swagger_data
        self.cache = {}  # 缓存已解析的引用
        self.is_generating_request_body = False  # 标记是否正在生成请求体
    
    def set_swagger_data(self, swagger_data):
        """
        设置Swagger文档数据
        
        Args:
            swagger_data (dict): Swagger文档数据
        """
        self.swagger_data = swagger_data
        self.cache = {}  # 清空缓存
    
    def generate_data(self, schema):
        """
        根据参数架构生成测试数据
        
        Args:
            schema (dict): 参数架构
            
        Returns:
            any: 生成的测试数据
        """
        print(f"开始生成数据，schema: {json.dumps(schema, ensure_ascii=False)}")
        if not schema:
            return None
        
        # 处理引用
        if isinstance(schema, dict) and '$ref' in schema:
            ref_path = schema['$ref']
            print(f"发现引用: {ref_path}")
            if ref_path in self.cache:
                # 使用缓存的引用解析结果
                print(f"使用缓存的引用: {ref_path}")
                return self.cache[ref_path]
            
            # 解析引用
            if self.swagger_data:
                resolved = self._resolve_reference(ref_path)
                if resolved:
                    print(f"解析引用成功: {ref_path}")
                    generated = self._generate_example_object(resolved)
                    # 缓存解析结果
                    self.cache[ref_path] = generated
                    return generated
                else:
                    print(f"解析引用失败: {ref_path}")
            else:
                print("无法解析引用: swagger_data为空")
            
            # 无法解析引用，返回示例对象
            print("生成默认示例对象")
            return self._generate_example_object()
        
        # 处理类型
        type_name = schema.get('type')
        if type_name == 'object':
            return self._generate_object(schema)
        elif type_name == 'array':
            return self._generate_array(schema)
        elif type_name == 'string':
            return self._generate_string(schema)
        elif type_name == 'integer':
            return self._generate_integer(schema)
        elif type_name == 'number':
            return self._generate_number(schema)
        elif type_name == 'boolean':
            return self._generate_boolean(schema)
        
        # 默认情况
        return self._generate_example_object()
    
    def _resolve_reference(self, ref_path):
        """
        解析引用
        
        Args:
            ref_path (str): 引用路径，格式如 '#/components/schemas/Model'
            
        Returns:
            dict: 解析后的对象
        """
        if not ref_path.startswith('#/'):
            print(f"不支持的引用路径格式: {ref_path}")
            return None
        
        parts = ref_path.replace('#/', '', 1).split('/')
        print(f"引用路径部分: {parts}")
        current = self.swagger_data
        
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                print(f"引用路径解析失败，找不到: {part}")
                return None
            current = current[part]
        
        print(f"引用解析成功: {type(current)}")
        return current
    
    def _generate_example_object(self, schema=None):
        """
        生成示例对象，主要用于无法解析引用时
        
        Args:
            schema (dict, optional): 参数架构
            
        Returns:
            dict: 示例对象
        """
        if schema and isinstance(schema, dict) and 'properties' in schema:
            result = {}
            for prop_name, prop_schema in schema['properties'].items():
                if prop_schema.get('type') == 'string':
                    # 使用完整的字符串生成逻辑
                    result[prop_name] = self._generate_string(prop_schema)
                elif prop_schema.get('type') == 'integer':
                    result[prop_name] = self._generate_integer(prop_schema)
                elif prop_schema.get('type') == 'number':
                    result[prop_name] = self._generate_number(prop_schema)
                elif prop_schema.get('type') == 'boolean':
                    result[prop_name] = self._generate_boolean(prop_schema)
                elif prop_schema.get('type') == 'array':
                    result[prop_name] = self._generate_array(prop_schema)
                elif prop_schema.get('type') == 'object':
                    result[prop_name] = self._generate_object(prop_schema)
                else:
                    result[prop_name] = None
            return result
        
        # 默认生成通用示例对象
        return {
            "id": random.randint(1, 1000),
            "name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "address": fake.address(),
            "createdTime": fake.date_time().isoformat(),
            "active": random.choice([True, False]),
            "score": round(random.uniform(0, 100), 2)
        }
    
    def _generate_string(self, schema):
        """
        生成字符串类型数据
        
        Args:
            schema (dict): 参数架构
            
        Returns:
            str: 生成的字符串
        """
        # 处理枚举
        if 'enum' in schema:
            return random.choice(schema['enum'])
        
        # 处理格式
        if 'format' in schema:
            format_type = schema['format']
            if format_type == 'date':
                return fake.date()
            elif format_type == 'date-time':
                return fake.date_time().isoformat()
            elif format_type == 'email':
                return fake.email()
            elif format_type == 'uuid':
                return fake.uuid4()
            elif format_type == 'uri':
                return fake.uri()
            elif format_type == 'hostname':
                return fake.domain_name()
            elif format_type == 'ipv4':
                return fake.ipv4()
            elif format_type == 'ipv6':
                return fake.ipv6()
            elif format_type == 'password':
                return fake.password()
        
        # 处理模式
        if 'pattern' in schema:
            pattern = schema['pattern']
            # 处理手机号模式
            if 'phone' in schema.get('description', '').lower() or 'phone' in schema.get('name', '').lower() or '^1[3-9]\\d{9}$' in pattern:
                return '1' + str(random.randint(3, 9)) + ''.join(str(random.randint(0, 9)) for _ in range(9))
            # 处理邮箱模式
            elif '@' in pattern:
                return fake.email()
            # 处理数字模式
            elif pattern.startswith('^\\d') or pattern.startswith('^[0-9]'):
                # 尝试从模式中提取长度
                import re
                length_match = re.search(r'\{(\d+)\}', pattern)
                if length_match:
                    length = int(length_match.group(1))
                    return ''.join(str(random.randint(0, 9)) for _ in range(length))
                else:
                    return ''.join(str(random.randint(0, 9)) for _ in range(6))  # 默认6位
            # 其他模式，返回合理的默认值
            else:
                # 生成字母数字组合
                length = random.randint(6, 12)
                return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
        
        # 处理长度
        min_length = schema.get('minLength', 1)
        max_length = schema.get('maxLength', 20)
        if min_length > max_length:
            min_length = max_length
        
        # 根据字段名生成更合理的数据
        field_name = schema.get('name', '').lower()
        field_title = schema.get('title', '').lower()
        field_desc = schema.get('description', '').lower()
        
        # 手机号检测 - 优先级最高
        phone_hints = ['phone', 'mobile', 'tel', '手机', '电话', '联系方式', 'phonenumber', 'mobilenumber']
        for hint in phone_hints:
            if hint in field_name or hint in field_title or hint in field_desc:
                return '1' + str(random.randint(3, 9)) + ''.join(str(random.randint(0, 9)) for _ in range(9))
        
        name_hints = ['name', 'username', '名称', '姓名', '用户名']
        for hint in name_hints:
            if hint in field_name or hint in field_title:
                return fake.name()
        
        email_hints = ['email', '邮箱', '邮件']
        for hint in email_hints:
            if hint in field_name or hint in field_title:
                return fake.email()
        
        address_hints = ['address', 'location', '地址', '位置']
        for hint in address_hints:
            if hint in field_name or hint in field_title:
                return fake.address()
        
        # 生成随机字符串
        length = random.randint(min_length, max_length)
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
    
    def _generate_integer(self, schema):
        """
        生成整数类型数据
        
        Args:
            schema (dict): 参数架构
            
        Returns:
            int: 生成的整数
        """
        # 处理枚举
        if 'enum' in schema:
            return random.choice(schema['enum'])
        
        # 处理范围
        minimum = schema.get('minimum', 0)
        maximum = schema.get('maximum', 1000)
        
        # 处理独占边界
        if schema.get('exclusiveMinimum') and minimum is not None:
            minimum += 1
        if schema.get('exclusiveMaximum') and maximum is not None:
            maximum -= 1
        
        # 确保范围有效
        if minimum > maximum:
            minimum, maximum = maximum, minimum
        
        return random.randint(int(minimum), int(maximum))
    
    def _generate_number(self, schema):
        """
        生成数字类型数据
        
        Args:
            schema (dict): 参数架构
            
        Returns:
            float: 生成的数字
        """
        # 处理枚举
        if 'enum' in schema:
            return random.choice(schema['enum'])
        
        # 处理范围
        minimum = schema.get('minimum', 0.0)
        maximum = schema.get('maximum', 1000.0)
        
        # 处理独占边界
        if schema.get('exclusiveMinimum') and minimum is not None:
            minimum += 0.1
        if schema.get('exclusiveMaximum') and maximum is not None:
            maximum -= 0.1
        
        # 确保范围有效
        if minimum > maximum:
            minimum, maximum = maximum, minimum
        
        return round(random.uniform(float(minimum), float(maximum)), 2)
    
    def _generate_boolean(self, schema):
        """
        生成布尔类型数据
        
        Args:
            schema (dict): 参数架构
            
        Returns:
            bool: 生成的布尔值
        """
        return random.choice([True, False])
    
    def _generate_array(self, schema):
        """
        生成数组类型数据
        
        Args:
            schema (dict): 参数架构
            
        Returns:
            list: 生成的数组
        """
        # 处理项目模式
        items_schema = schema.get('items', {})
        
        # 处理长度
        min_items = schema.get('minItems', 0)
        max_items = schema.get('maxItems', 5)
        if min_items > max_items:
            min_items = max_items
        
        # 生成随机长度数组
        count = random.randint(min_items, max_items)
        return [self.generate_data(items_schema) for _ in range(count)]
    
    def _generate_object(self, schema):
        """
        生成对象类型数据
        
        Args:
            schema (dict): 参数架构
            
        Returns:
            dict: 生成的对象
        """
        result = {}
        
        # 处理属性
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        # 判断是否需要生成所有字段
        # 1. 如果正在生成请求体，生成所有字段
        # 2. 如果对象有较多属性（>3个），通常是重要的业务对象，生成所有字段
        # 3. 如果是顽级schema（title字段存在），通常也是重要对象
        should_generate_all = (
            self.is_generating_request_body or 
            len(properties) > 3 or 
            'title' in schema or
            # 如果大部分字段都是必需的，那么剩下的也应该生成
            (len(required) > 0 and len(required) / len(properties) > 0.5)
        )
        
        for prop_name, prop_schema in properties.items():
            # 必需属性一定生成
            if prop_name in required:
                result[prop_name] = self.generate_data(prop_schema)
            else:
                # 根据上述条件判断是否生成
                if should_generate_all:
                    result[prop_name] = self.generate_data(prop_schema)
                # 对于其他对象，95%的概率生成非必需属性
                elif random.random() > 0.05:
                    result[prop_name] = self.generate_data(prop_schema)
        
        return result
    
    def generate_parameter_data(self, parameters):
        """
        为API参数生成测试数据
        
        Args:
            parameters (list): API参数列表
            
        Returns:
            dict: 参数名到测试数据的映射
        """
        result = {
            'path': {},
            'query': {},
            'header': {},
            'cookie': {},
            'body': None
        }
        
        for param in parameters:
            # 获取参数位置、名称和架构
            param_in = param.get('in', '')
            param_name = param.get('name', '')
            
            # 处理Swagger 2.0和OpenAPI 3.0的参数结构差异
            param_schema = self._get_parameter_schema(param)
            
            # 生成参数数据
            generated_data = self.generate_data(param_schema)
            
            # 根据参数位置存储数据
            if param_in == 'path':
                result['path'][param_name] = generated_data
            elif param_in == 'query':
                result['query'][param_name] = generated_data
            elif param_in == 'header':
                result['header'][param_name] = generated_data
            elif param_in == 'cookie':
                result['cookie'][param_name] = generated_data
            elif param_in == 'body':
                result['body'] = generated_data
        
        return result
    
    def _get_parameter_schema(self, param):
        """
        获取参数的schema，兼容Swagger 2.0和OpenAPI 3.0
        
        Args:
            param (dict): 参数定义
            
        Returns:
            dict: 参数schema
        """
        # OpenAPI 3.0: 参数有schema对象
        if 'schema' in param:
            schema = param['schema'].copy()
            # 将参数的name和description添加到schema中，便于生成更合理的数据
            schema['name'] = param.get('name', '')
            schema['description'] = param.get('description', '')
            return schema
        
        # Swagger 2.0: 参数直接有type等属性
        schema = {}
        
        # 复制类型相关属性
        type_fields = ['type', 'format', 'enum', 'minimum', 'maximum', 'minLength', 'maxLength', 
                      'pattern', 'items', 'default', 'example']
        
        for field in type_fields:
            if field in param:
                schema[field] = param[field]
        
        # 添加参数名和描述，便于生成更合理的数据
        schema['name'] = param.get('name', '')
        schema['description'] = param.get('description', '')
        
        # 如果没有type，默认为string
        if 'type' not in schema:
            schema['type'] = 'string'
            
        return schema
    
    def generate_request_body(self, request_body_schema):
        """
        为请求体生成测试数据
        
        Args:
            request_body_schema (dict): 请求体架构
            
        Returns:
            dict: 生成的请求体数据
        """
        if not request_body_schema:
            return None
        
        # 获取内容类型和对应的架构
        content = request_body_schema.get('content', {})
        
        # 处理不同内容类型
        for content_type, content_schema in content.items():
            schema = content_schema.get('schema', {})
            if schema:
                return self.generate_data(schema)
        
        return {}
