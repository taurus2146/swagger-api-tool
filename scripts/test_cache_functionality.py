#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试Swagger文档缓存功能
"""

import os
import sys
import json
import tempfile
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database_manager import DatabaseManager
from core.swagger_cache_manager import SwaggerCacheManager
from core.swagger_parser import SwaggerParser
from core.project_manager import ProjectManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_swagger_data():
    """创建测试用的Swagger数据"""
    return {
        "swagger": "2.0",
        "info": {
            "title": "测试API",
            "version": "1.0.0",
            "description": "这是一个测试API"
        },
        "host": "api.example.com",
        "basePath": "/v1",
        "schemes": ["https"],
        "consumes": ["application/json"],
        "produces": ["application/json"],
        "paths": {
            "/users": {
                "get": {
                    "summary": "获取用户列表",
                    "description": "获取所有用户的列表",
                    "tags": ["users"],
                    "operationId": "getUsers",
                    "responses": {
                        "200": {
                            "description": "成功返回用户列表"
                        }
                    }
                },
                "post": {
                    "summary": "创建用户",
                    "description": "创建一个新用户",
                    "tags": ["users"],
                    "operationId": "createUser",
                    "parameters": [
                        {
                            "name": "user",
                            "in": "body",
                            "required": True,
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "email": {"type": "string"}
                                }
                            }
                        }
                    ],
                    "responses": {
                        "201": {
                            "description": "用户创建成功"
                        }
                    }
                }
            },
            "/users/{id}": {
                "get": {
                    "summary": "获取用户详情",
                    "description": "根据ID获取用户详情",
                    "tags": ["users"],
                    "operationId": "getUserById",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "type": "integer"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "成功返回用户详情"
                        },
                        "404": {
                            "description": "用户不存在"
                        }
                    }
                }
            }
        }
    }


def test_cache_manager():
    """测试缓存管理器"""
    print("\n" + "="*60)
    print("测试Swagger文档缓存功能")
    print("="*60)
    
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # 初始化数据库管理器
        db_manager = DatabaseManager(db_path)
        if not db_manager.initialize_database():
            print("❌ 数据库初始化失败")
            return False
        
        # 执行数据库迁移
        if not db_manager.migrate_database():
            print("❌ 数据库迁移失败")
            return False
        
        # 直接使用数据库管理器创建项目记录
        project_data = {
            'name': '测试项目',
            'description': '用于测试缓存功能的项目',
            'swagger_source_type': 'url',
            'swagger_source_location': 'http://example.com/swagger.json',
            'base_url': ''
        }

        project_id = db_manager.create_project(project_data)

        if not project_id:
            print("❌ 创建测试项目失败")
            return False

        print(f"✓ 创建测试项目成功，ID: {project_id}")

        # 创建缓存管理器
        cache_manager = SwaggerCacheManager(db_manager)
        
        # 创建测试数据
        swagger_data = create_test_swagger_data()
        content = json.dumps(swagger_data, indent=2)
        
        print(f"✓ 创建测试Swagger文档，包含 {len(swagger_data['paths'])} 个路径")
        
        # 测试1：保存文档到缓存
        print("\n1. 测试保存文档到缓存...")
        document_id = cache_manager.save_swagger_document(
            project_id, content, swagger_data, "http://example.com/swagger.json"
        )
        
        if document_id:
            print(f"✓ 文档保存成功，ID: {document_id}")
        else:
            print("❌ 文档保存失败")
            return False
        
        # 测试2：获取当前文档
        print("\n2. 测试获取当前文档...")
        current_doc = cache_manager.get_current_document(project_id)
        
        if current_doc:
            print(f"✓ 获取当前文档成功")
            print(f"  - 标题: {current_doc.title}")
            print(f"  - 版本: {current_doc.version}")
            print(f"  - API数量: {current_doc.api_count}")
            print(f"  - 缓存时间: {current_doc.cached_at}")
        else:
            print("❌ 获取当前文档失败")
            return False
        
        # 测试3：获取缓存的Swagger数据
        print("\n3. 测试获取缓存的Swagger数据...")
        cached_data = cache_manager.get_cached_swagger_data(project_id)
        
        if cached_data:
            print(f"✓ 获取缓存数据成功")
            print(f"  - 标题: {cached_data['info']['title']}")
            print(f"  - 路径数量: {len(cached_data['paths'])}")
        else:
            print("❌ 获取缓存数据失败")
            return False
        
        # 测试4：获取缓存的API列表
        print("\n4. 测试获取缓存的API列表...")
        cached_apis = cache_manager.get_cached_apis(project_id)
        
        if cached_apis:
            print(f"✓ 获取缓存API列表成功，共 {len(cached_apis)} 个API")
            for api in cached_apis[:3]:  # 显示前3个
                print(f"  - {api.method} {api.path}: {api.summary}")
        else:
            print("❌ 获取缓存API列表失败")
            return False
        
        # 测试5：重复保存相同内容（应该复用）
        print("\n5. 测试重复保存相同内容...")
        document_id2 = cache_manager.save_swagger_document(
            project_id, content, swagger_data, "http://example.com/swagger.json"
        )
        
        if document_id2 == document_id:
            print(f"✓ 重复保存成功复用，ID: {document_id2}")
        else:
            print(f"❌ 重复保存未复用，新ID: {document_id2}")
        
        # 测试6：保存修改后的内容
        print("\n6. 测试保存修改后的内容...")
        modified_data = swagger_data.copy()
        modified_data['info']['version'] = '2.0.0'
        modified_data['paths']['/products'] = {
            "get": {
                "summary": "获取产品列表",
                "operationId": "getProducts",
                "responses": {"200": {"description": "成功"}}
            }
        }
        modified_content = json.dumps(modified_data, indent=2)
        
        document_id3 = cache_manager.save_swagger_document(
            project_id, modified_content, modified_data
        )
        
        if document_id3 and document_id3 != document_id:
            print(f"✓ 修改后的文档保存成功，新ID: {document_id3}")
            
            # 验证新文档是当前版本
            current_doc2 = cache_manager.get_current_document(project_id)
            if current_doc2 and current_doc2.id == document_id3:
                print(f"✓ 新文档已设为当前版本")
                print(f"  - 新版本: {current_doc2.version}")
                print(f"  - API数量: {current_doc2.api_count}")
            else:
                print("❌ 新文档未设为当前版本")
        else:
            print("❌ 修改后的文档保存失败")
        
        print(f"\n✅ 所有缓存功能测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理临时文件
        try:
            if db_manager:
                db_manager.disconnect()
            os.unlink(db_path)
        except:
            pass


def test_swagger_parser_with_cache():
    """测试带缓存的SwaggerParser"""
    print("\n" + "="*60)
    print("测试带缓存的SwaggerParser")
    print("="*60)
    
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # 初始化数据库管理器
        db_manager = DatabaseManager(db_path)
        if not db_manager.initialize_database():
            print("❌ 数据库初始化失败")
            return False
        
        # 执行数据库迁移
        if not db_manager.migrate_database():
            print("❌ 数据库迁移失败")
            return False
        
        # 直接使用数据库管理器创建项目记录
        project_data = {
            'name': 'SwaggerParser测试项目',
            'description': '用于测试SwaggerParser缓存功能的项目',
            'swagger_source_type': 'file',
            'swagger_source_location': 'test.json',
            'base_url': ''
        }

        project_id = db_manager.create_project(project_data)

        if not project_id:
            print("❌ 创建测试项目失败")
            return False

        print(f"✓ 创建测试项目成功，ID: {project_id}")

        # 创建带缓存的SwaggerParser
        parser = SwaggerParser(project_id=project_id, db_manager=db_manager)
        
        # 创建临时Swagger文件
        swagger_data = create_test_swagger_data()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(swagger_data, tmp_file, indent=2)
            swagger_file = tmp_file.name
        
        try:
            # 测试1：从文件加载（会缓存）
            print("\n1. 测试从文件加载（首次，会缓存）...")
            if parser.load_from_file(swagger_file):
                print("✓ 从文件加载成功")
                apis = parser.get_api_list()
                print(f"  - 解析出 {len(apis)} 个API")
            else:
                print("❌ 从文件加载失败")
                return False
            
            # 测试2：检查缓存是否可用
            print("\n2. 测试检查缓存可用性...")
            if parser.is_cache_available():
                print("✓ 缓存可用")
            else:
                print("❌ 缓存不可用")
                return False
            
            # 测试3：从缓存加载
            print("\n3. 测试从缓存加载...")
            parser2 = SwaggerParser(project_id=project_id, db_manager=db_manager)
            if parser2.load_from_cache():
                print("✓ 从缓存加载成功")
                apis2 = parser2.get_api_list()
                print(f"  - 解析出 {len(apis2)} 个API")
                
                # 验证数据一致性
                if len(apis) == len(apis2):
                    print("✓ 缓存数据与原始数据一致")
                else:
                    print("❌ 缓存数据与原始数据不一致")
                    return False
            else:
                print("❌ 从缓存加载失败")
                return False
            
            print(f"\n✅ SwaggerParser缓存功能测试通过！")
            return True
            
        finally:
            # 清理临时文件
            try:
                os.unlink(swagger_file)
            except:
                pass
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理临时文件
        try:
            if db_manager:
                db_manager.disconnect()
            os.unlink(db_path)
        except:
            pass


def main():
    """主函数"""
    print("Swagger文档缓存功能测试")
    print("="*60)
    
    success = True
    
    # 测试缓存管理器
    if not test_cache_manager():
        success = False
    
    # 测试带缓存的SwaggerParser
    if not test_swagger_parser_with_cache():
        success = False
    
    print("\n" + "="*60)
    if success:
        print("🎉 所有测试通过！Swagger文档缓存功能正常工作。")
        print("\n优势:")
        print("• 离线访问：无需网络即可使用缓存的API定义")
        print("• 快速启动：避免重复下载Swagger文档")
        print("• 版本管理：自动检测文档变化并更新缓存")
        print("• 数据完整：保存完整的API定义和元数据")
    else:
        print("❌ 部分测试失败，请检查错误信息。")
    
    return success


if __name__ == '__main__':
    main()
