#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库组件单元测试套件
测试所有数据库相关组件的功能
"""

import os
import sys
import unittest
import tempfile
import shutil
import sqlite3
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database_manager import DatabaseManager
from core.database_storage import DatabaseStorage
from core.project_repository import ProjectRepository
from core.config_repository import ConfigRepository
from core.encryption_service import EncryptionService
from core.migration_service import MigrationService
from core.database_version_manager import DatabaseVersionManager
from core.project_models import Project


class TestDatabaseManager(unittest.TestCase):
    """数据库管理器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test.db")
        self.db_manager = DatabaseManager(self.db_path)
    
    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_database_initialization(self):
        """测试数据库初始化"""
        self.assertTrue(os.path.exists(self.db_path))
        
        # 检查表是否创建
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        expected_tables = ['projects', 'global_config', 'database_info', 'project_history']
        for table in expected_tables:
            self.assertIn(table, tables)
    
    def test_connection_management(self):
        """测试连接管理"""
        # 测试获取连接
        with self.db_manager.get_connection() as conn:
            self.assertIsNotNone(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)
    
    def test_transaction_management(self):
        """测试事务管理"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 开始事务
            cursor.execute("BEGIN")
            cursor.execute("INSERT INTO projects (name, path) VALUES (?, ?)", 
                         ("test_project", "/test/path"))
            
            # 回滚事务
            cursor.execute("ROLLBACK")
            
            # 验证数据未提交
            cursor.execute("SELECT COUNT(*) FROM projects WHERE name = ?", ("test_project",))
            count = cursor.fetchone()[0]
            self.assertEqual(count, 0)
    
    def test_database_info_storage(self):
        """测试数据库信息存储"""
        info = {
            'version': '1.0.0',
            'created_at': datetime.now().isoformat(),
            'last_backup': None
        }
        
        self.db_manager.update_database_info(info)
        retrieved_info = self.db_manager.get_database_info()
        
        self.assertEqual(retrieved_info['version'], '1.0.0')
        self.assertIsNotNone(retrieved_info['created_at'])


class TestDatabaseStorage(unittest.TestCase):
    """数据库存储测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test.db")
        self.storage = DatabaseStorage(self.db_path)
    
    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'storage'):
            self.storage.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_project_crud_operations(self):
        """测试项目CRUD操作"""
        # 创建项目
        project = Project(
            name="Test Project",
            path="/test/path",
            description="Test Description",
            tags=["test", "demo"]
        )
        
        project_id = self.storage.save_project(project)
        self.assertIsNotNone(project_id)
        
        # 读取项目
        loaded_project = self.storage.load_project(project_id)
        self.assertEqual(loaded_project.name, "Test Project")
        self.assertEqual(loaded_project.path, "/test/path")
        self.assertEqual(loaded_project.tags, ["test", "demo"])
        
        # 更新项目
        loaded_project.description = "Updated Description"
        self.storage.save_project(loaded_project)
        
        updated_project = self.storage.load_project(project_id)
        self.assertEqual(updated_project.description, "Updated Description")
        
        # 删除项目
        self.storage.delete_project(project_id)
        deleted_project = self.storage.load_project(project_id)
        self.assertIsNone(deleted_project)
    
    def test_project_search(self):
        """测试项目搜索"""
        # 创建测试项目
        projects = [
            Project(name="Web App", path="/web", tags=["web", "javascript"]),
            Project(name="Mobile App", path="/mobile", tags=["mobile", "react"]),
            Project(name="Desktop App", path="/desktop", tags=["desktop", "python"])
        ]
        
        for project in projects:
            self.storage.save_project(project)
        
        # 按名称搜索
        results = self.storage.search_projects("Web")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Web App")
        
        # 按标签搜索
        results = self.storage.search_projects_by_tag("python")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Desktop App")
    
    def test_global_config_operations(self):
        """测试全局配置操作"""
        # 设置配置
        self.storage.set_global_config("theme", "dark")
        self.storage.set_global_config("language", "zh-CN")
        
        # 获取配置
        theme = self.storage.get_global_config("theme")
        language = self.storage.get_global_config("language")
        
        self.assertEqual(theme, "dark")
        self.assertEqual(language, "zh-CN")
        
        # 获取所有配置
        all_config = self.storage.get_all_global_config()
        self.assertIn("theme", all_config)
        self.assertIn("language", all_config)


class TestProjectRepository(unittest.TestCase):
    """项目仓储测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test.db")
        self.db_manager = DatabaseManager(self.db_path)
        self.repository = ProjectRepository(self.db_manager)
    
    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_complex_queries(self):
        """测试复杂查询"""
        # 创建测试数据
        projects = [
            Project(name="Project A", path="/a", tags=["web"], created_at=datetime(2023, 1, 1)),
            Project(name="Project B", path="/b", tags=["mobile"], created_at=datetime(2023, 2, 1)),
            Project(name="Project C", path="/c", tags=["web", "api"], created_at=datetime(2023, 3, 1))
        ]
        
        for project in projects:
            self.repository.create(project)
        
        # 按时间范围查询
        results = self.repository.find_by_date_range(
            datetime(2023, 1, 15), 
            datetime(2023, 2, 15)
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Project B")
        
        # 按多个标签查询
        results = self.repository.find_by_tags(["web"])
        self.assertEqual(len(results), 2)
    
    def test_pagination(self):
        """测试分页查询"""
        # 创建多个项目
        for i in range(15):
            project = Project(name=f"Project {i}", path=f"/path{i}")
            self.repository.create(project)
        
        # 测试分页
        page1 = self.repository.find_all(page=1, page_size=5)
        page2 = self.repository.find_all(page=2, page_size=5)
        
        self.assertEqual(len(page1), 5)
        self.assertEqual(len(page2), 5)
        
        # 确保不同页面的数据不重复
        page1_names = {p.name for p in page1}
        page2_names = {p.name for p in page2}
        self.assertEqual(len(page1_names.intersection(page2_names)), 0)
    
    def test_batch_operations(self):
        """测试批量操作"""
        projects = [
            Project(name=f"Batch Project {i}", path=f"/batch{i}")
            for i in range(5)
        ]
        
        # 批量创建
        created_ids = self.repository.create_batch(projects)
        self.assertEqual(len(created_ids), 5)
        
        # 批量删除
        self.repository.delete_batch(created_ids[:3])
        
        # 验证删除结果
        remaining = self.repository.find_all()
        self.assertEqual(len(remaining), 2)


class TestConfigRepository(unittest.TestCase):
    """配置仓储测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test.db")
        self.db_manager = DatabaseManager(self.db_path)
        self.repository = ConfigRepository(self.db_manager)
    
    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_typed_config_access(self):
        """测试类型化配置访问"""
        # 设置不同类型的配置
        self.repository.set_string("app_name", "Test App")
        self.repository.set_int("max_projects", 100)
        self.repository.set_bool("enable_logging", True)
        self.repository.set_float("cache_size", 1.5)
        
        # 获取配置并验证类型
        app_name = self.repository.get_string("app_name")
        max_projects = self.repository.get_int("max_projects")
        enable_logging = self.repository.get_bool("enable_logging")
        cache_size = self.repository.get_float("cache_size")
        
        self.assertEqual(app_name, "Test App")
        self.assertEqual(max_projects, 100)
        self.assertTrue(enable_logging)
        self.assertEqual(cache_size, 1.5)
    
    def test_config_change_notification(self):
        """测试配置变更通知"""
        notifications = []
        
        def on_config_changed(key, old_value, new_value):
            notifications.append((key, old_value, new_value))
        
        self.repository.add_change_listener(on_config_changed)
        
        # 修改配置
        self.repository.set_string("test_key", "value1")
        self.repository.set_string("test_key", "value2")
        
        # 验证通知
        self.assertEqual(len(notifications), 2)
        self.assertEqual(notifications[0], ("test_key", None, "value1"))
        self.assertEqual(notifications[1], ("test_key", "value1", "value2"))
    
    def test_config_backup_restore(self):
        """测试配置备份和恢复"""
        # 设置初始配置
        self.repository.set_string("key1", "value1")
        self.repository.set_int("key2", 42)
        
        # 创建备份
        backup_id = self.repository.create_backup()
        self.assertIsNotNone(backup_id)
        
        # 修改配置
        self.repository.set_string("key1", "modified")
        self.repository.set_int("key2", 99)
        
        # 恢复备份
        self.repository.restore_backup(backup_id)
        
        # 验证恢复结果
        self.assertEqual(self.repository.get_string("key1"), "value1")
        self.assertEqual(self.repository.get_int("key2"), 42)


class TestEncryptionService(unittest.TestCase):
    """加密服务测试"""
    
    def setUp(self):
        """测试前准备"""
        self.encryption_service = EncryptionService()
    
    def test_basic_encryption_decryption(self):
        """测试基本加密解密"""
        plaintext = "This is a secret message"
        password = "test_password"
        
        # 加密
        encrypted = self.encryption_service.encrypt(plaintext, password)
        self.assertNotEqual(encrypted, plaintext)
        self.assertIsInstance(encrypted, str)
        
        # 解密
        decrypted = self.encryption_service.decrypt(encrypted, password)
        self.assertEqual(decrypted, plaintext)
    
    def test_wrong_password_decryption(self):
        """测试错误密码解密"""
        plaintext = "Secret data"
        correct_password = "correct_password"
        wrong_password = "wrong_password"
        
        encrypted = self.encryption_service.encrypt(plaintext, correct_password)
        
        # 使用错误密码解密应该失败
        with self.assertRaises(Exception):
            self.encryption_service.decrypt(encrypted, wrong_password)
    
    def test_key_derivation(self):
        """测试密钥派生"""
        password = "test_password"
        salt = b"test_salt_16byte"
        
        key1 = self.encryption_service.derive_key(password, salt)
        key2 = self.encryption_service.derive_key(password, salt)
        
        # 相同输入应产生相同密钥
        self.assertEqual(key1, key2)
        
        # 不同盐应产生不同密钥
        different_salt = b"different_salt16"
        key3 = self.encryption_service.derive_key(password, different_salt)
        self.assertNotEqual(key1, key3)
    
    def test_field_encryption(self):
        """测试字段级加密"""
        sensitive_data = {
            "username": "john_doe",
            "password": "secret123",
            "email": "john@example.com"
        }
        
        master_password = "master_key"
        
        # 加密敏感字段
        encrypted_data = self.encryption_service.encrypt_fields(
            sensitive_data, 
            ["password"], 
            master_password
        )
        
        # 验证只有指定字段被加密
        self.assertEqual(encrypted_data["username"], "john_doe")
        self.assertEqual(encrypted_data["email"], "john@example.com")
        self.assertNotEqual(encrypted_data["password"], "secret123")
        
        # 解密字段
        decrypted_data = self.encryption_service.decrypt_fields(
            encrypted_data,
            ["password"],
            master_password
        )
        
        self.assertEqual(decrypted_data["password"], "secret123")


class TestMigrationService(unittest.TestCase):
    """迁移服务测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.json_file = os.path.join(self.test_dir, "projects.json")
        self.db_path = os.path.join(self.test_dir, "migrated.db")
        
        # 创建测试JSON文件
        import json
        test_data = {
            "projects": [
                {
                    "id": "1",
                    "name": "Test Project 1",
                    "path": "/test/path1",
                    "description": "Test Description 1",
                    "tags": ["test", "demo"],
                    "created_at": "2023-01-01T00:00:00"
                },
                {
                    "id": "2", 
                    "name": "Test Project 2",
                    "path": "/test/path2",
                    "description": "Test Description 2",
                    "tags": ["test"],
                    "created_at": "2023-01-02T00:00:00"
                }
            ],
            "global_config": {
                "theme": "dark",
                "language": "en"
            }
        }
        
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2)
        
        self.migration_service = MigrationService(self.json_file, self.db_path)
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_json_data_detection(self):
        """测试JSON数据检测"""
        self.assertTrue(self.migration_service.has_json_data())
        
        # 测试不存在的文件
        non_existent_service = MigrationService("/non/existent/file.json", self.db_path)
        self.assertFalse(non_existent_service.has_json_data())
    
    def test_migration_process(self):
        """测试迁移过程"""
        # 执行迁移
        result = self.migration_service.migrate_to_database()
        self.assertTrue(result)
        
        # 验证数据库已创建
        self.assertTrue(os.path.exists(self.db_path))
        
        # 验证数据已迁移
        storage = DatabaseStorage(self.db_path)
        projects = storage.get_all_projects()
        
        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0].name, "Test Project 1")
        self.assertEqual(projects[1].name, "Test Project 2")
        
        # 验证全局配置已迁移
        theme = storage.get_global_config("theme")
        language = storage.get_global_config("language")
        
        self.assertEqual(theme, "dark")
        self.assertEqual(language, "en")
        
        storage.close()
    
    def test_migration_rollback(self):
        """测试迁移回滚"""
        # 先执行迁移
        self.migration_service.migrate_to_database()
        
        # 执行回滚
        result = self.migration_service.rollback_migration()
        self.assertTrue(result)
        
        # 验证数据库文件已删除或清空
        if os.path.exists(self.db_path):
            storage = DatabaseStorage(self.db_path)
            projects = storage.get_all_projects()
            self.assertEqual(len(projects), 0)
            storage.close()


class TestDatabaseVersionManager(unittest.TestCase):
    """数据库版本管理器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test.db")
        self.version_manager = DatabaseVersionManager(self.db_path)
    
    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'version_manager'):
            self.version_manager.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_version_detection(self):
        """测试版本检测"""
        # 新数据库应该是最新版本
        current_version = self.version_manager.get_current_version()
        latest_version = self.version_manager.get_latest_version()
        
        self.assertEqual(current_version, latest_version)
    
    def test_upgrade_check(self):
        """测试升级检查"""
        needs_upgrade = self.version_manager.needs_upgrade()
        self.assertFalse(needs_upgrade)  # 新数据库不需要升级
    
    def test_version_history(self):
        """测试版本历史"""
        # 模拟版本升级
        self.version_manager.record_upgrade("1.0.0", "1.1.0", "Added new features")
        
        history = self.version_manager.get_upgrade_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['from_version'], "1.0.0")
        self.assertEqual(history[0]['to_version'], "1.1.0")


class TestPerformanceAndStress(unittest.TestCase):
    """性能和压力测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "performance_test.db")
        self.storage = DatabaseStorage(self.db_path)
    
    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'storage'):
            self.storage.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_large_dataset_operations(self):
        """测试大数据集操作"""
        import time
        
        # 创建大量项目
        start_time = time.time()
        projects = []
        for i in range(1000):
            project = Project(
                name=f"Performance Test Project {i}",
                path=f"/test/path/{i}",
                description=f"Description for project {i}",
                tags=[f"tag{i%10}", f"category{i%5}"]
            )
            projects.append(project)
        
        # 批量插入
        for project in projects:
            self.storage.save_project(project)
        
        insert_time = time.time() - start_time
        print(f"插入1000个项目耗时: {insert_time:.2f}秒")
        
        # 测试查询性能
        start_time = time.time()
        all_projects = self.storage.get_all_projects()
        query_time = time.time() - start_time
        
        self.assertEqual(len(all_projects), 1000)
        print(f"查询1000个项目耗时: {query_time:.2f}秒")
        
        # 测试搜索性能
        start_time = time.time()
        search_results = self.storage.search_projects("Project 5")
        search_time = time.time() - start_time
        
        print(f"搜索耗时: {search_time:.2f}秒")
        self.assertGreater(len(search_results), 0)
    
    def test_concurrent_access(self):
        """测试并发访问"""
        import threading
        import time
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                # 每个线程创建一些项目
                for i in range(10):
                    project = Project(
                        name=f"Worker {worker_id} Project {i}",
                        path=f"/worker{worker_id}/project{i}"
                    )
                    project_id = self.storage.save_project(project)
                    results.append(project_id)
                    time.sleep(0.01)  # 模拟一些处理时间
            except Exception as e:
                errors.append(str(e))
        
        # 创建多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        self.assertEqual(len(errors), 0, f"并发访问出现错误: {errors}")
        self.assertEqual(len(results), 50)  # 5个线程 × 10个项目
        
        # 验证数据完整性
        all_projects = self.storage.get_all_projects()
        self.assertEqual(len(all_projects), 50)


class TestErrorHandling(unittest.TestCase):
    """错误处理测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "error_test.db")
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_invalid_database_path(self):
        """测试无效数据库路径"""
        invalid_path = "/invalid/path/that/does/not/exist/test.db"
        
        with self.assertRaises(Exception):
            DatabaseManager(invalid_path)
    
    def test_corrupted_database_handling(self):
        """测试损坏数据库处理"""
        # 创建一个无效的数据库文件
        with open(self.db_path, 'w') as f:
            f.write("This is not a valid SQLite database")
        
        with self.assertRaises(Exception):
            DatabaseStorage(self.db_path)
    
    def test_transaction_rollback_on_error(self):
        """测试错误时事务回滚"""
        storage = DatabaseStorage(self.db_path)
        
        try:
            with storage.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("BEGIN")
                
                # 插入有效数据
                cursor.execute(
                    "INSERT INTO projects (name, path) VALUES (?, ?)",
                    ("Test Project", "/test/path")
                )
                
                # 尝试插入无效数据（违反约束）
                cursor.execute(
                    "INSERT INTO projects (name, path) VALUES (?, ?)",
                    (None, "/test/path2")  # name不能为NULL
                )
                
                cursor.execute("COMMIT")
        except Exception:
            # 预期会出现异常
            pass
        
        # 验证事务已回滚
        projects = storage.get_all_projects()
        self.assertEqual(len(projects), 0)
        
        storage.close()
    
    def test_connection_recovery(self):
        """测试连接恢复"""
        storage = DatabaseStorage(self.db_path)
        
        # 正常操作
        project = Project(name="Test", path="/test")
        project_id = storage.save_project(project)
        self.assertIsNotNone(project_id)
        
        # 模拟连接中断（关闭数据库管理器）
        storage.db_manager.close()
        
        # 尝试重新连接和操作
        storage.db_manager = DatabaseManager(self.db_path)
        
        # 验证可以继续操作
        loaded_project = storage.load_project(project_id)
        self.assertIsNotNone(loaded_project)
        self.assertEqual(loaded_project.name, "Test")
        
        storage.close()


def create_test_suite():
    """创建测试套件"""
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestDatabaseManager,
        TestDatabaseStorage,
        TestProjectRepository,
        TestConfigRepository,
        TestEncryptionService,
        TestMigrationService,
        TestDatabaseVersionManager,
        TestPerformanceAndStress,
        TestErrorHandling
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


def run_tests():
    """运行所有测试"""
    print("开始运行数据库组件单元测试...")
    print("=" * 60)
    
    # 创建测试套件
    suite = create_test_suite()
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果摘要
    print("\n" + "=" * 60)
    print("测试结果摘要:")
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)