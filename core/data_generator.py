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
        self.recursion_depth = 0  # 递归深度计数器
        self.max_recursion_depth = 10  # 最大递归深度
        self.generating_schemas = set()  # 正在生成的schema，防止循环引用

        # 调试信息
        print(f"DataGenerator初始化: 实例ID={id(self)}")
        if swagger_data:
            print(f"DataGenerator初始化: swagger_data类型={type(swagger_data)}, 大小={len(str(swagger_data))}")
            if isinstance(swagger_data, dict):
                print(f"DataGenerator初始化: 包含definitions={bool(swagger_data.get('definitions'))}")
                print(f"DataGenerator初始化: 包含components={bool(swagger_data.get('components'))}")
        else:
            print("DataGenerator初始化: swagger_data为空")

    def set_swagger_data(self, swagger_data):
        """
        设置Swagger数据

        Args:
            swagger_data (dict): Swagger文档数据
        """
        print(f"DataGenerator.set_swagger_data: 实例ID={id(self)}")
        print(f"DataGenerator.set_swagger_data: 新数据类型={type(swagger_data)}")
        if swagger_data:
            print(f"DataGenerator.set_swagger_data: 新数据大小={len(str(swagger_data))}")
        else:
            print("DataGenerator.set_swagger_data: 新数据为空")

        self.swagger_data = swagger_data
        # 清空缓存，因为swagger_data已更改
        self.cache = {}

        print(f"DataGenerator.set_swagger_data: 设置完成，当前swagger_data类型={type(self.swagger_data)}")

    def get_swagger_data_status(self):
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
        # 检查递归深度
        if self.recursion_depth >= self.max_recursion_depth:
            print(f"达到最大递归深度 {self.max_recursion_depth}，返回简单值")
            return "递归深度限制"

        # 增加递归深度
        self.recursion_depth += 1

        try:
            print(f"开始生成数据，递归深度: {self.recursion_depth}, schema: {json.dumps(schema, ensure_ascii=False)}")
            if not schema:
                return None

            # 检查循环引用
            schema_key = json.dumps(schema, sort_keys=True) if isinstance(schema, dict) else str(schema)
            if schema_key in self.generating_schemas:
                print(f"检测到循环引用，返回简单值")
                return "循环引用"

            # 添加到正在生成的集合
            self.generating_schemas.add(schema_key)

            try:
                return self._generate_data_internal(schema)
            finally:
                # 移除正在生成的标记
                self.generating_schemas.discard(schema_key)

        finally:
            # 减少递归深度
            self.recursion_depth -= 1

    def _generate_data_internal(self, schema):
        """
        内部数据生成方法

        Args:
            schema (dict): 参数架构

        Returns:
            any: 生成的测试数据
        """
        
        # 处理引用
        if isinstance(schema, dict) and '$ref' in schema:
            ref_path = schema['$ref']
            print(f"发现引用: {ref_path}")
            if ref_path in self.cache:
                # 使用缓存的引用解析结果
                print(f"使用缓存的引用: {ref_path}")
                return self.cache[ref_path]
            
            # 解析引用
            print(f"检查swagger_data状态: 类型={type(self.swagger_data)}, 是否为空={self.swagger_data is None}")

            # 如果swagger_data为空，尝试从swagger_parser获取
            if not self.swagger_data and hasattr(self, 'swagger_parser') and self.swagger_parser:
                print("尝试从swagger_parser获取swagger_data")
                if hasattr(self.swagger_parser, 'swagger_data') and self.swagger_parser.swagger_data:
                    self.swagger_data = self.swagger_parser.swagger_data
                    print(f"从swagger_parser获取swagger_data成功: 类型={type(self.swagger_data)}")
                else:
                    print("swagger_parser没有有效的swagger_data")

            if self.swagger_data:
                print(f"swagger_data包含的顶级键: {list(self.swagger_data.keys()) if isinstance(self.swagger_data, dict) else 'not dict'}")
                if isinstance(self.swagger_data, dict) and 'components' in self.swagger_data:
                    components = self.swagger_data['components']
                    if isinstance(components, dict) and 'schemas' in components:
                        schemas = components['schemas']
                        print(f"schemas中包含的键: {list(schemas.keys())[:10]}...")  # 只显示前10个
                        if 'FunctionAreaDTO' in schemas:
                            print(f"找到FunctionAreaDTO: {schemas['FunctionAreaDTO']}")
                        else:
                            print("schemas中没有找到FunctionAreaDTO")
                    else:
                        print("components中没有schemas")
                else:
                    print("swagger_data中没有components")

            # 如果还是没有swagger_data，尝试从全局获取
            if not self.swagger_data:
                print("尝试从全局获取swagger_data")
                try:
                    # 尝试从应用的全局状态获取swagger_data
                    from gui.main_window import MainWindow
                    if hasattr(MainWindow, '_instance') and MainWindow._instance:
                        main_window = MainWindow._instance
                        if hasattr(main_window, 'swagger_parser') and main_window.swagger_parser:
                            if hasattr(main_window.swagger_parser, 'swagger_data'):
                                self.swagger_data = main_window.swagger_parser.swagger_data
                                print(f"从全局获取swagger_data成功: 类型={type(self.swagger_data)}")
                            else:
                                print("全局swagger_parser没有swagger_data属性")
                        else:
                            print("全局main_window没有swagger_parser")
                    else:
                        print("无法获取全局MainWindow实例")
                except Exception as e:
                    print(f"从全局获取swagger_data失败: {e}")

            if self.swagger_data:
                try:
                    print(f"尝试解析引用: {ref_path}")
                    resolved = self._resolve_reference(ref_path)
                    if resolved:
                        print(f"解析引用成功: {ref_path}, 解析结果类型: {type(resolved)}")
                        generated = self._generate_example_object(resolved)
                        # 缓存解析结果
                        self.cache[ref_path] = generated
                        return generated
                    else:
                        print(f"解析引用失败: {ref_path}")
                except Exception as e:
                    print(f"解析引用时出现异常: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"无法解析引用: swagger_data为空, self.swagger_data={self.swagger_data}")
                print(f"DataGenerator实例ID: {id(self)}")
                # 尝试从引用路径推断数据类型
                return self._generate_fallback_data_from_ref(ref_path)
            
            # 无法解析引用，返回示例对象
            print(f"生成默认示例对象，原始schema: {schema}")
            try:
                # 如果原始schema有properties，优先使用
                if isinstance(schema, dict) and 'properties' in schema:
                    print("使用原始schema的properties生成对象")
                    return self._generate_example_object(schema)
                else:
                    return self._generate_example_object()
            except Exception as e:
                print(f"生成默认示例对象失败: {e}")
                return {"error": "无法生成示例数据"}
        
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

    def _generate_fallback_data_from_ref(self, ref_path):
        """
        当无法解析引用时，根据引用路径生成备用数据

        Args:
            ref_path (str): 引用路径

        Returns:
            dict: 备用数据
        """
        print(f"生成备用数据: {ref_path}")

        # 从引用路径中提取可能的类型信息
        path_lower = ref_path.lower()

        # 专门处理FunctionAreaDTO
        if 'functionareadto' in path_lower or ref_path == '#/components/schemas/FunctionAreaDTO':
            print(f"为FunctionAreaDTO生成专用结构")
            return {
                "name": self._generate_string({"description": "功能区域名称"}),
                "imageUrl": self._generate_string({"description": "功能区域图片URL"})
            }
        elif 'user' in path_lower or '用户' in path_lower:
            return {
                "id": random.randint(1, 1000),
                "name": fake.name(),
                "email": fake.email(),
                "phone": fake.phone_number(),
                "createTime": fake.date_time().isoformat()
            }
        elif 'order' in path_lower or '订单' in path_lower:
            return {
                "id": random.randint(1000, 9999),
                "orderNo": f"ORD{random.randint(100000, 999999)}",
                "amount": round(random.uniform(10, 1000), 2),
                "status": random.choice(["pending", "paid", "shipped", "completed"]),
                "createTime": fake.date_time().isoformat()
            }
        elif 'product' in path_lower or '产品' in path_lower or '商品' in path_lower:
            return {
                "id": random.randint(1, 500),
                "name": fake.word(),
                "price": round(random.uniform(1, 500), 2),
                "category": fake.word(),
                "inStock": random.choice([True, False])
            }
        elif 'request' in path_lower or '请求' in path_lower:
            return {
                "id": random.randint(1, 100),
                "data": fake.text(max_nb_chars=50),
                "timestamp": fake.date_time().isoformat()
            }
        else:
            # 通用备用数据
            return {
                "id": random.randint(1, 1000),
                "name": fake.word(),
                "value": fake.text(max_nb_chars=30),
                "timestamp": fake.date_time().isoformat(),
                "active": random.choice([True, False])
            }
    
    def _generate_example_object(self, schema=None):
        """
        生成示例对象，主要用于无法解析引用时
        
        Args:
            schema (dict, optional): 参数架构
            
        Returns:
            dict: 示例对象
        """
        if schema and isinstance(schema, dict) and 'properties' in schema:
            print(f"使用schema properties生成对象: {list(schema['properties'].keys())}")
            result = {}
            required = schema.get('required', [])

            for prop_name, prop_schema in schema['properties'].items():
                try:
                    print(f"生成属性 {prop_name}, schema: {prop_schema}")
                    # 使用递归的generate_data方法，这样可以正确处理引用
                    result[prop_name] = self.generate_data(prop_schema)
                except Exception as e:
                    print(f"生成属性 {prop_name} 失败: {e}")
                    # 如果是必需属性，提供一个默认值
                    if prop_name in required:
                        if prop_schema.get('type') == 'string':
                            result[prop_name] = f"默认_{prop_name}"
                        elif prop_schema.get('type') in ['integer', 'number']:
                            result[prop_name] = 0
                        elif prop_schema.get('type') == 'boolean':
                            result[prop_name] = False
                        elif prop_schema.get('type') == 'array':
                            result[prop_name] = []
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

        # 处理长度，根据递归深度调整数组大小
        min_items = schema.get('minItems', 0)
        max_items = schema.get('maxItems', 5)

        # 根据递归深度限制数组大小，防止过度递归
        if self.recursion_depth > 5:
            max_items = min(max_items, 2)  # 深层递归时限制数组大小
        if self.recursion_depth > 8:
            max_items = 1  # 更深层时只生成1个元素

        if min_items > max_items:
            min_items = max_items

        # 生成随机长度数组
        count = random.randint(min_items, max_items)
        result = []
        for i in range(count):
            try:
                item = self.generate_data(items_schema)
                result.append(item)
            except Exception as e:
                print(f"生成数组元素失败: {e}")
                result.append(f"元素{i}")
                break  # 出错时停止生成更多元素

        return result
    
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

        # 根据递归深度限制生成的属性数量
        if self.recursion_depth > 8:
            # 深层递归时只生成必需属性
            properties_to_generate = {k: v for k, v in properties.items() if k in required}
            if not properties_to_generate and properties:
                # 如果没有必需属性，至少生成一个
                first_prop = next(iter(properties.items()))
                properties_to_generate = {first_prop[0]: first_prop[1]}
        elif self.recursion_depth > 5:
            # 中等深度时限制属性数量
            max_props = min(len(properties), 3)
            prop_items = list(properties.items())
            # 优先选择必需属性
            required_props = [(k, v) for k, v in prop_items if k in required]
            other_props = [(k, v) for k, v in prop_items if k not in required]
            selected_props = required_props + other_props[:max_props - len(required_props)]
            properties_to_generate = dict(selected_props[:max_props])
        else:
            properties_to_generate = properties

        # 判断是否需要生成所有字段
        should_generate_all = (
            self.is_generating_request_body or
            len(properties_to_generate) > 3 or
            'title' in schema or
            (len(required) > 0 and len(required) / len(properties_to_generate) > 0.5)
        )

        for prop_name, prop_schema in properties_to_generate.items():
            try:
                # 必需属性一定生成
                if prop_name in required:
                    result[prop_name] = self.generate_data(prop_schema)
                else:
                    # 根据条件和递归深度判断是否生成
                    if should_generate_all:
                        result[prop_name] = self.generate_data(prop_schema)
                    # 深层递归时降低生成概率
                    elif self.recursion_depth > 6:
                        if random.random() > 0.7:  # 30%概率生成
                            result[prop_name] = self.generate_data(prop_schema)
                    # 对于其他对象，95%的概率生成非必需属性
                    elif random.random() > 0.05:
                        result[prop_name] = self.generate_data(prop_schema)
            except Exception as e:
                print(f"生成对象属性 {prop_name} 失败: {e}")
                result[prop_name] = f"生成失败: {prop_name}"

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
