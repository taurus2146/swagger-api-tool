#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
加密数据访问层
提供对加密数据的透明访问，自动处理加密和解密操作
"""
import os
import sys
import logging
from typing import Dict, Any, List, Optional, Union
from contextlib import contextmanager

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.field_encryption_service import FieldEncryptionService
from core.database_manager import DatabaseManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EncryptedDataAccess:
    """加密数据访问层"""
    
    def __init__(self, database_manager: DatabaseManager, 
                 encryption_service: FieldEncryptionService = None):
        """
        初始化加密数据访问层
        
        Args:
            database_manager: 数据库管理器
            encryption_service: 字段加密服务
        """
        self.db_manager = database_manager
        
        if encryption_service is None:
            self.encryption_service = FieldEncryptionService()
        else:
            self.encryption_service = encryption_service
        
        # 自动加密开关
        self.auto_encrypt = True
        self.auto_decrypt = True
        
        logger.info("加密数据访问层初始化完成")
    
    def set_auto_encryption(self, encrypt: bool = True, decrypt: bool = True):
        """
        设置自动加密/解密开关
        
        Args:
            encrypt: 是否自动加密
            decrypt: 是否自动解密
        """
        self.auto_encrypt = encrypt
        self.auto_decrypt = decrypt
        logger.info(f"自动加密设置: 加密={encrypt}, 解密={decrypt}")
    
    @contextmanager
    def encryption_disabled(self):
        """临时禁用加密的上下文管理器"""
        old_encrypt = self.auto_encrypt
        old_decrypt = self.auto_decrypt
        
        self.auto_encrypt = False
        self.auto_decrypt = False
        
        try:
            yield
        finally:
            self.auto_encrypt = old_encrypt
            self.auto_decrypt = old_decrypt
    
    def _prepare_record_for_storage(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """准备记录用于存储（加密敏感字段）"""
        if not self.auto_encrypt or not record:
            return record
        
        try:
            return self.encryption_service.encrypt_record(record)
        except Exception as e:
            logger.error(f"准备存储记录时加密失败: {e}")
            # 如果加密失败，返回原始记录（可能需要根据安全策略调整）
            return record
    
    def _prepare_record_for_access(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """准备记录用于访问（解密敏感字段）"""
        if not self.auto_decrypt or not record:
            return record
        
        try:
            return self.encryption_service.decrypt_record(record)
        except Exception as e:
            logger.error(f"准备访问记录时解密失败: {e}")
            # 如果解密失败，返回原始记录
            return record
    
    def _prepare_records_for_access(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """准备多个记录用于访问"""
        if not records:
            return records
        
        return [self._prepare_record_for_access(record) for record in records]
    
    # 项目相关操作
    def create_project(self, project_data: Dict[str, Any]) -> str:
        """
        创建项目（自动加密敏感字段）
        
        Args:
            project_data: 项目数据
            
        Returns:
            项目ID
        """
        encrypted_data = self._prepare_record_for_storage(project_data)
        return self.db_manager.create_project(encrypted_data)
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        获取项目（自动解密敏感字段）
        
        Args:
            project_id: 项目ID
            
        Returns:
            项目数据（解密后）
        """
        project = self.db_manager.get_project(project_id)
        return self._prepare_record_for_access(project)
    
    def get_all_projects(self) -> List[Dict[str, Any]]:
        """
        获取所有项目（自动解密敏感字段）
        
        Returns:
            项目列表（解密后）
        """
        projects = self.db_manager.get_all_projects()
        return self._prepare_records_for_access(projects)
    
    def update_project(self, project_id: str, project_data: Dict[str, Any]) -> bool:
        """
        更新项目（自动加密敏感字段）
        
        Args:
            project_id: 项目ID
            project_data: 更新的项目数据
            
        Returns:
            是否更新成功
        """
        encrypted_data = self._prepare_record_for_storage(project_data)
        return self.db_manager.update_project(project_id, encrypted_data)
    
    def delete_project(self, project_id: str) -> bool:
        """
        删除项目
        
        Args:
            project_id: 项目ID
            
        Returns:
            是否删除成功
        """
        return self.db_manager.delete_project(project_id)
    
    def search_projects(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        搜索项目（自动解密敏感字段）
        
        Args:
            query: 搜索查询
            limit: 结果限制
            
        Returns:
            搜索结果（解密后）
        """
        projects = self.db_manager.search_projects(query, limit)
        return self._prepare_records_for_access(projects)
    
    # API相关操作
    def create_api(self, api_data: Dict[str, Any]) -> int:
        """
        创建API（自动加密敏感字段）
        
        Args:
            api_data: API数据
            
        Returns:
            API ID
        """
        encrypted_data = self._prepare_record_for_storage(api_data)
        return self.db_manager.create_api(encrypted_data)
    
    def get_api(self, api_id: int) -> Optional[Dict[str, Any]]:
        """
        获取API（自动解密敏感字段）
        
        Args:
            api_id: API ID
            
        Returns:
            API数据（解密后）
        """
        api = self.db_manager.get_api(api_id)
        return self._prepare_record_for_access(api)
    
    def get_project_apis(self, project_id: str) -> List[Dict[str, Any]]:
        """
        获取项目的所有API（自动解密敏感字段）
        
        Args:
            project_id: 项目ID
            
        Returns:
            API列表（解密后）
        """
        apis = self.db_manager.get_project_apis(project_id)
        return self._prepare_records_for_access(apis)
    
    def update_api(self, api_id: int, api_data: Dict[str, Any]) -> bool:
        """
        更新API（自动加密敏感字段）
        
        Args:
            api_id: API ID
            api_data: 更新的API数据
            
        Returns:
            是否更新成功
        """
        encrypted_data = self._prepare_record_for_storage(api_data)
        return self.db_manager.update_api(api_id, encrypted_data)
    
    def delete_api(self, api_id: int) -> bool:
        """
        删除API
        
        Args:
            api_id: API ID
            
        Returns:
            是否删除成功
        """
        return self.db_manager.delete_api(api_id)
    
    # 配置相关操作
    def set_config(self, key: str, value: Any) -> bool:
        """
        设置配置（自动加密敏感配置）
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            是否设置成功
        """
        # 检查是否为敏感配置
        if self.encryption_service.is_sensitive_field(key):
            encrypted_value = self.encryption_service.encrypt_field(key, str(value))
            return self.db_manager.set_config(key, encrypted_value)
        else:
            return self.db_manager.set_config(key, value)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置（自动解密敏感配置）
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值（解密后）
        """
        value = self.db_manager.get_config(key, default)
        
        # 检查是否为加密的敏感配置
        if (isinstance(value, dict) and 
            'algorithm' in value and 
            self.encryption_service.is_sensitive_field(key)):
            try:
                return self.encryption_service.decrypt_field(key, value)
            except Exception as e:
                logger.error(f"解密配置 {key} 失败: {e}")
                return default
        
        return value
    
    def get_all_configs(self) -> Dict[str, Any]:
        """
        获取所有配置（自动解密敏感配置）
        
        Returns:
            配置字典（解密后）
        """
        configs = self.db_manager.get_all_configs()
        
        if not configs:
            return configs
        
        decrypted_configs = {}
        for key, value in configs.items():
            if (isinstance(value, dict) and 
                'algorithm' in value and 
                self.encryption_service.is_sensitive_field(key)):
                try:
                    decrypted_configs[key] = self.encryption_service.decrypt_field(key, value)
                except Exception as e:
                    logger.error(f"解密配置 {key} 失败: {e}")
                    decrypted_configs[key] = value
            else:
                decrypted_configs[key] = value
        
        return decrypted_configs
    
    def delete_config(self, key: str) -> bool:
        """
        删除配置
        
        Args:
            key: 配置键
            
        Returns:
            是否删除成功
        """
        return self.db_manager.delete_config(key)
    
    # 批量操作
    def bulk_encrypt_existing_data(self) -> Dict[str, int]:
        """
        批量加密现有数据中的敏感字段
        
        Returns:
            加密统计信息
        """
        stats = {
            'projects_processed': 0,
            'projects_encrypted': 0,
            'apis_processed': 0,
            'apis_encrypted': 0,
            'configs_processed': 0,
            'configs_encrypted': 0,
            'errors': 0
        }
        
        logger.info("开始批量加密现有数据")
        
        try:
            # 临时禁用自动加密，避免重复加密
            with self.encryption_disabled():
                # 加密项目数据
                projects = self.db_manager.get_all_projects()
                for project in projects:
                    stats['projects_processed'] += 1
                    try:
                        # 检查是否有敏感字段需要加密
                        has_sensitive = any(
                            self.encryption_service.is_sensitive_field(key) and 
                            not (isinstance(value, dict) and 'algorithm' in value)
                            for key, value in project.items()
                            if value is not None
                        )
                        
                        if has_sensitive:
                            encrypted_project = self.encryption_service.encrypt_record(project)
                            if self.db_manager.update_project(project['id'], encrypted_project):
                                stats['projects_encrypted'] += 1
                    except Exception as e:
                        logger.error(f"加密项目 {project.get('id', 'unknown')} 失败: {e}")
                        stats['errors'] += 1
                
                # 加密API数据
                # 注意：这里需要获取所有API，可能需要扩展数据库管理器的接口
                # 暂时跳过API批量加密
                
                # 加密配置数据
                configs = self.db_manager.get_all_configs()
                for key, value in configs.items():
                    stats['configs_processed'] += 1
                    try:
                        if (self.encryption_service.is_sensitive_field(key) and
                            not (isinstance(value, dict) and 'algorithm' in value)):
                            encrypted_value = self.encryption_service.encrypt_field(key, str(value))
                            if self.db_manager.set_config(key, encrypted_value):
                                stats['configs_encrypted'] += 1
                    except Exception as e:
                        logger.error(f"加密配置 {key} 失败: {e}")
                        stats['errors'] += 1
        
        except Exception as e:
            logger.error(f"批量加密过程中发生错误: {e}")
            stats['errors'] += 1
        
        logger.info(f"批量加密完成: {stats}")
        return stats
    
    def bulk_decrypt_data_for_migration(self) -> Dict[str, int]:
        """
        批量解密数据用于迁移（例如算法升级）
        
        Returns:
            解密统计信息
        """
        stats = {
            'projects_processed': 0,
            'projects_decrypted': 0,
            'configs_processed': 0,
            'configs_decrypted': 0,
            'errors': 0
        }
        
        logger.info("开始批量解密数据用于迁移")
        
        try:
            # 临时禁用自动解密
            with self.encryption_disabled():
                # 解密项目数据
                projects = self.db_manager.get_all_projects()
                for project in projects:
                    stats['projects_processed'] += 1
                    try:
                        # 检查是否有加密字段需要解密
                        has_encrypted = any(
                            isinstance(value, dict) and 'algorithm' in value
                            for value in project.values()
                        )
                        
                        if has_encrypted:
                            decrypted_project = self.encryption_service.decrypt_record(project)
                            if self.db_manager.update_project(project['id'], decrypted_project):
                                stats['projects_decrypted'] += 1
                    except Exception as e:
                        logger.error(f"解密项目 {project.get('id', 'unknown')} 失败: {e}")
                        stats['errors'] += 1
                
                # 解密配置数据
                configs = self.db_manager.get_all_configs()
                for key, value in configs.items():
                    stats['configs_processed'] += 1
                    try:
                        if isinstance(value, dict) and 'algorithm' in value:
                            decrypted_value = self.encryption_service.decrypt_field(key, value)
                            if self.db_manager.set_config(key, decrypted_value):
                                stats['configs_decrypted'] += 1
                    except Exception as e:
                        logger.error(f"解密配置 {key} 失败: {e}")
                        stats['errors'] += 1
        
        except Exception as e:
            logger.error(f"批量解密过程中发生错误: {e}")
            stats['errors'] += 1
        
        logger.info(f"批量解密完成: {stats}")
        return stats
    
    def get_encryption_status(self) -> Dict[str, Any]:
        """
        获取数据加密状态
        
        Returns:
            加密状态信息
        """
        status = {
            'auto_encrypt': self.auto_encrypt,
            'auto_decrypt': self.auto_decrypt,
            'encryption_service_info': self.encryption_service.get_encryption_info(),
            'encrypted_projects': 0,
            'total_projects': 0,
            'encrypted_configs': 0,
            'total_configs': 0
        }
        
        try:
            # 统计项目加密情况
            with self.encryption_disabled():
                projects = self.db_manager.get_all_projects()
                status['total_projects'] = len(projects)
                
                for project in projects:
                    has_encrypted = any(
                        isinstance(value, dict) and 'algorithm' in value
                        for value in project.values()
                    )
                    if has_encrypted:
                        status['encrypted_projects'] += 1
                
                # 统计配置加密情况
                configs = self.db_manager.get_all_configs()
                status['total_configs'] = len(configs)
                
                for value in configs.values():
                    if isinstance(value, dict) and 'algorithm' in value:
                        status['encrypted_configs'] += 1
        
        except Exception as e:
            logger.error(f"获取加密状态失败: {e}")
            status['error'] = str(e)
        
        return status

def main():
    """测试加密数据访问层"""
    print("加密数据访问层测试")
    print("=" * 50)
    
    # 创建临时数据库
    import tempfile
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    
    try:
        # 创建数据库管理器和加密数据访问层
        db_manager = DatabaseManager(db_path)
        db_manager.connect()
        db_manager.initialize_database()
        
        encrypted_access = EncryptedDataAccess(db_manager)
        
        # 测试项目操作
        print("\n测试项目操作:")
        
        project_data = {
            'name': 'Test Project',
            'description': 'A test project with sensitive data',
            'api_key': 'sk-1234567890abcdef',
            'secret_key': 'secret_abcdef1234567890',
            'base_url': 'https://api.example.com'
        }
        
        print("创建项目...")
        project_id = encrypted_access.create_project(project_data)
        print(f"项目ID: {project_id}")
        
        print("\n获取项目...")
        retrieved_project = encrypted_access.get_project(project_id)
        print("检索到的项目数据:")
        for key, value in retrieved_project.items():
            print(f"  {key}: {value}")
        
        # 验证敏感字段是否正确解密
        print("\n验证数据一致性:")
        for key in ['api_key', 'secret_key']:
            original = project_data[key]
            retrieved = retrieved_project[key]
            match = original == retrieved
            print(f"  {key}: {'✓' if match else '✗'}")
        
        # 测试配置操作
        print("\n测试配置操作:")
        
        print("设置敏感配置...")
        encrypted_access.set_config('database_password', 'super_secret_password')
        encrypted_access.set_config('normal_setting', 'normal_value')
        
        print("获取配置...")
        db_password = encrypted_access.get_config('database_password')
        normal_setting = encrypted_access.get_config('normal_setting')
        
        print(f"数据库密码: {db_password}")
        print(f"普通设置: {normal_setting}")
        
        # 获取加密状态
        print("\n加密状态:")
        status = encrypted_access.get_encryption_status()
        for key, value in status.items():
            if key != 'encryption_service_info':
                print(f"  {key}: {value}")
        
        print("\n测试完成!")
        
    finally:
        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()