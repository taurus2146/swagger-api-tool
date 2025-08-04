#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系统集成测试
测试GUI组件和ProjectManager与数据库的集成
"""
import os
import sys
import tempfile
import shutil

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.project_manager import ProjectManager
from core.project_models import SwaggerSource


def test_project_manager_integration():
    """测试ProjectManager与数据库集成"""
    print("测试ProjectManager与数据库集成...")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    
    try:
        # 创建ProjectManager
        pm = ProjectManager(db_path)
        
        # 测试项目创建
        project_data = {
            'name': '集成测试项目',
            'path': '/test/integration',
            'description': '用于集成测试的项目',
            'swagger_sources': [
                SwaggerSource(
                    name='测试API',
                    url='http://test.com/swagger.json',
                    type='url'
                )
            ]
        }
        
        project_id = pm.create_project(project_data)
        assert project_id is not None, "项目创建失败"
        
        # 测试项目加载
        project = pm.get_project(project_id)
        assert project is not None, "项目加载失败"
        assert project.name == '集成测试项目', "项目名称不匹配"
        
        # 测试项目列表
        projects = pm.get_all_projects()
        assert len(projects) == 1, "项目列表长度不正确"
        
        # 测试项目删除
        pm.delete_project(project_id)
        projects = pm.get_all_projects()
        assert len(projects) == 0, "项目删除失败"
        
        print("✓ ProjectManager集成测试通过")
        return True
        
    except Exception as e:
        print(f"✗ ProjectManager集成测试失败: {e}")
        return False
    finally:
        # 清理临时文件
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def test_gui_integration():
    """测试GUI组件集成"""
    print("测试GUI组件集成...")
    
    try:
        # 导入GUI相关模块
        from PyQt5.QtWidgets import QApplication
        from gui.main_window import MainWindow
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test.db')
        
        try:
            # 创建QApplication（如果不存在）
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            # 创建主窗口
            main_window = MainWindow()
            
            # 测试数据库相关功能是否可用
            assert hasattr(main_window, 'project_manager'), "主窗口缺少project_manager属性"
            
            print("✓ GUI集成测试通过")
            return True
            
        except Exception as e:
            print(f"✗ GUI集成测试失败: {e}")
            return False
        finally:
            # 清理临时文件
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                
    except ImportError:
        print("⚠ PyQt5不可用，跳过GUI集成测试")
        return True


def run_all_integration_tests():
    """运行所有集成测试"""
    print("开始运行系统集成测试...")
    print("=" * 50)
    
    tests = [
        test_project_manager_integration,
        test_gui_integration
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ 测试 {test.__name__} 异常: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"集成测试结果: {passed} 通过, {failed} 失败")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_integration_tests()
    sys.exit(0 if success else 1)