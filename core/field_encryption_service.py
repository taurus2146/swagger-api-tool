#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
字段加密服务
提供敏感字段的自动加密、解密和透明访问功能
"""
import os
import sys
import json
import base64
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import secrets

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.master_password_manager import MasterPasswordManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EncryptionAlgorithm(Enum):
    """加密算法类型"""
    FERNET = "fernet"  # 对称加密，适合小数据
    AES_GCM = "aes_gcm"  # AES-GCM，适合大数据
    CHACHA20_POLY1305 = "chacha20_poly1305"  # ChaCha20-Poly1305，高性能

@dataclass
class EncryptionConfig:
    """加密配置"""
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.FERNET
    key_derivation_iterations: int = 100000
    salt_length: int = 32
    nonce_length: int = 12
    tag_length: int = 16

@dataclass
class EncryptedField:
    """加密字段数据结构"""
    algorithm: str
    encrypted_data: str
    salt: str
    nonce: Optional[str] = None
    tag: Optional[str] = None
    version: int = 1
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

class FieldEncryptionService:
    """字段加密服务"""
    
    def __init__(self, master_password_manager: MasterPasswordManager = None, config_dir: str = None):
        """
        初始化字段加密服务
        
        Args:
            master_password_manager: 主密码管理器实例
            config_dir: 配置目录
        """
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".swagger_tool")
        
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "field_encryption.json")
        self.config = EncryptionConfig()
        
        # 主密码管理器
        if master_password_manager is None:
            self.master_password_manager = MasterPasswordManager(config_dir)
        else:
            self.master_password_manager = master_password_manager
        
        # 加密密钥缓存
        self._key_cache = {}
        self._master_key = None
        
        # 敏感字段配置
        self.sensitive_fields = {
            'api_key', 'secret_key', 'password', 'token', 'credential',
            'private_key', 'certificate', 'connection_string', 'database_url'
        }
        
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        # 加载配置
        self._load_config()
        
        logger.info(f"字段加密服务初始化完成: {config_dir}")
    
    def _load_config(self):
        """加载加密配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    
                # 更新配置
                if 'algorithm' in config_data:
                    self.config.algorithm = EncryptionAlgorithm(config_data['algorithm'])
                if 'key_derivation_iterations' in config_data:
                    self.config.key_derivation_iterations = config_data['key_derivation_iterations']
                if 'sensitive_fields' in config_data:
                    self.sensitive_fields.update(config_data['sensitive_fields'])
                    
                logger.info("字段加密配置加载成功")
            except Exception as e:
                logger.error(f"加载字段加密配置失败: {e}")
    
    def _save_config(self):
        """保存加密配置"""
        try:
            config_data = {
                'algorithm': self.config.algorithm.value,
                'key_derivation_iterations': self.config.key_derivation_iterations,
                'sensitive_fields': list(self.sensitive_fields),
                'updated_at': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
            logger.info("字段加密配置保存成功")
        except Exception as e:
            logger.error(f"保存字段加密配置失败: {e}")
            raise
    
    def _get_master_key(self) -> bytes:
        """获取主加密密钥"""
        if self._master_key is not None:
            return self._master_key
        
        # 检查是否设置了主密码
        if not self.master_password_manager.has_master_password():
            raise ValueError("尚未设置主密码，无法进行字段加密")
        
        # 从主密码派生加密密钥
        # 注意：这里需要用户输入主密码，在实际应用中应该通过GUI获取
        # 这里为了演示，我们假设已经验证了主密码
        master_password = "dummy_password"  # 实际应用中应该从安全输入获取
        
        # 使用固定的盐值派生主密钥（在实际应用中应该安全存储）
        salt = b"field_encryption_salt_v1"  # 32字节盐值
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.config.key_derivation_iterations,
            backend=default_backend()
        )
        
        self._master_key = kdf.derive(master_password.encode('utf-8'))
        return self._master_key
    
    def _derive_field_key(self, field_name: str, salt: bytes) -> bytes:
        """为特定字段派生加密密钥"""
        master_key = self._get_master_key()
        
        # 使用字段名和盐值派生字段专用密钥
        field_info = f"field:{field_name}".encode('utf-8')
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt + field_info,
            iterations=10000,  # 较少的迭代次数，因为已经有主密钥保护
            backend=default_backend()
        )
        
        return kdf.derive(master_key)
    
    def _encrypt_with_fernet(self, data: str, field_name: str) -> EncryptedField:
        """使用Fernet算法加密数据"""
        # 生成盐值
        salt = secrets.token_bytes(self.config.salt_length)
        
        # 派生字段密钥
        field_key = self._derive_field_key(field_name, salt)
        
        # 创建Fernet实例
        fernet_key = base64.urlsafe_b64encode(field_key)
        fernet = Fernet(fernet_key)
        
        # 加密数据
        encrypted_data = fernet.encrypt(data.encode('utf-8'))
        
        return EncryptedField(
            algorithm=EncryptionAlgorithm.FERNET.value,
            encrypted_data=base64.b64encode(encrypted_data).decode('utf-8'),
            salt=base64.b64encode(salt).decode('utf-8')
        )
    
    def _decrypt_with_fernet(self, encrypted_field: EncryptedField, field_name: str) -> str:
        """使用Fernet算法解密数据"""
        # 解码盐值
        salt = base64.b64decode(encrypted_field.salt.encode('utf-8'))
        
        # 派生字段密钥
        field_key = self._derive_field_key(field_name, salt)
        
        # 创建Fernet实例
        fernet_key = base64.urlsafe_b64encode(field_key)
        fernet = Fernet(fernet_key)
        
        # 解密数据
        encrypted_data = base64.b64decode(encrypted_field.encrypted_data.encode('utf-8'))
        decrypted_data = fernet.decrypt(encrypted_data)
        
        return decrypted_data.decode('utf-8')
    
    def _encrypt_with_aes_gcm(self, data: str, field_name: str) -> EncryptedField:
        """使用AES-GCM算法加密数据"""
        # 生成盐值和随机数
        salt = secrets.token_bytes(self.config.salt_length)
        nonce = secrets.token_bytes(self.config.nonce_length)
        
        # 派生字段密钥
        field_key = self._derive_field_key(field_name, salt)
        
        # 创建AES-GCM加密器
        cipher = Cipher(
            algorithms.AES(field_key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # 加密数据
        ciphertext = encryptor.update(data.encode('utf-8')) + encryptor.finalize()
        
        return EncryptedField(
            algorithm=EncryptionAlgorithm.AES_GCM.value,
            encrypted_data=base64.b64encode(ciphertext).decode('utf-8'),
            salt=base64.b64encode(salt).decode('utf-8'),
            nonce=base64.b64encode(nonce).decode('utf-8'),
            tag=base64.b64encode(encryptor.tag).decode('utf-8')
        )
    
    def _decrypt_with_aes_gcm(self, encrypted_field: EncryptedField, field_name: str) -> str:
        """使用AES-GCM算法解密数据"""
        # 解码数据
        salt = base64.b64decode(encrypted_field.salt.encode('utf-8'))
        nonce = base64.b64decode(encrypted_field.nonce.encode('utf-8'))
        tag = base64.b64decode(encrypted_field.tag.encode('utf-8'))
        ciphertext = base64.b64decode(encrypted_field.encrypted_data.encode('utf-8'))
        
        # 派生字段密钥
        field_key = self._derive_field_key(field_name, salt)
        
        # 创建AES-GCM解密器
        cipher = Cipher(
            algorithms.AES(field_key),
            modes.GCM(nonce, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # 解密数据
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        return plaintext.decode('utf-8')
    
    def is_sensitive_field(self, field_name: str) -> bool:
        """检查字段是否为敏感字段"""
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in self.sensitive_fields)
    
    def encrypt_field(self, field_name: str, data: str) -> Dict[str, Any]:
        """
        加密字段数据
        
        Args:
            field_name: 字段名称
            data: 要加密的数据
            
        Returns:
            加密后的字段数据字典
        """
        if not data:
            return None
        
        try:
            # 根据配置选择加密算法
            if self.config.algorithm == EncryptionAlgorithm.FERNET:
                encrypted_field = self._encrypt_with_fernet(data, field_name)
            elif self.config.algorithm == EncryptionAlgorithm.AES_GCM:
                encrypted_field = self._encrypt_with_aes_gcm(data, field_name)
            else:
                raise ValueError(f"不支持的加密算法: {self.config.algorithm}")
            
            # 转换为字典格式
            result = {
                'algorithm': encrypted_field.algorithm,
                'encrypted_data': encrypted_field.encrypted_data,
                'salt': encrypted_field.salt,
                'version': encrypted_field.version,
                'created_at': encrypted_field.created_at
            }
            
            if encrypted_field.nonce:
                result['nonce'] = encrypted_field.nonce
            if encrypted_field.tag:
                result['tag'] = encrypted_field.tag
            
            logger.debug(f"字段 {field_name} 加密成功")
            return result
            
        except Exception as e:
            logger.error(f"加密字段 {field_name} 失败: {e}")
            raise
    
    def decrypt_field(self, field_name: str, encrypted_data: Dict[str, Any]) -> str:
        """
        解密字段数据
        
        Args:
            field_name: 字段名称
            encrypted_data: 加密的字段数据字典
            
        Returns:
            解密后的原始数据
        """
        if not encrypted_data:
            return None
        
        try:
            # 创建EncryptedField对象
            encrypted_field = EncryptedField(
                algorithm=encrypted_data['algorithm'],
                encrypted_data=encrypted_data['encrypted_data'],
                salt=encrypted_data['salt'],
                nonce=encrypted_data.get('nonce'),
                tag=encrypted_data.get('tag'),
                version=encrypted_data.get('version', 1),
                created_at=encrypted_data.get('created_at')
            )
            
            # 根据算法解密
            if encrypted_field.algorithm == EncryptionAlgorithm.FERNET.value:
                result = self._decrypt_with_fernet(encrypted_field, field_name)
            elif encrypted_field.algorithm == EncryptionAlgorithm.AES_GCM.value:
                result = self._decrypt_with_aes_gcm(encrypted_field, field_name)
            else:
                raise ValueError(f"不支持的加密算法: {encrypted_field.algorithm}")
            
            logger.debug(f"字段 {field_name} 解密成功")
            return result
            
        except Exception as e:
            logger.error(f"解密字段 {field_name} 失败: {e}")
            raise
    
    def encrypt_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        加密记录中的敏感字段
        
        Args:
            record: 原始记录字典
            
        Returns:
            加密后的记录字典
        """
        if not record:
            return record
        
        encrypted_record = record.copy()
        
        for field_name, value in record.items():
            if self.is_sensitive_field(field_name) and value is not None:
                try:
                    encrypted_value = self.encrypt_field(field_name, str(value))
                    encrypted_record[field_name] = encrypted_value
                    logger.debug(f"记录中的敏感字段 {field_name} 已加密")
                except Exception as e:
                    logger.error(f"加密记录字段 {field_name} 失败: {e}")
                    # 继续处理其他字段
        
        return encrypted_record
    
    def decrypt_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        解密记录中的敏感字段
        
        Args:
            record: 加密的记录字典
            
        Returns:
            解密后的记录字典
        """
        if not record:
            return record
        
        decrypted_record = record.copy()
        
        for field_name, value in record.items():
            if (self.is_sensitive_field(field_name) and 
                isinstance(value, dict) and 
                'algorithm' in value):
                try:
                    decrypted_value = self.decrypt_field(field_name, value)
                    decrypted_record[field_name] = decrypted_value
                    logger.debug(f"记录中的敏感字段 {field_name} 已解密")
                except Exception as e:
                    logger.error(f"解密记录字段 {field_name} 失败: {e}")
                    # 保留原始加密数据
        
        return decrypted_record
    
    def add_sensitive_field(self, field_name: str):
        """添加敏感字段"""
        self.sensitive_fields.add(field_name.lower())
        self._save_config()
        logger.info(f"添加敏感字段: {field_name}")
    
    def remove_sensitive_field(self, field_name: str):
        """移除敏感字段"""
        self.sensitive_fields.discard(field_name.lower())
        self._save_config()
        logger.info(f"移除敏感字段: {field_name}")
    
    def get_sensitive_fields(self) -> List[str]:
        """获取所有敏感字段列表"""
        return list(self.sensitive_fields)
    
    def upgrade_encryption_algorithm(self, new_algorithm: EncryptionAlgorithm):
        """
        升级加密算法
        
        Args:
            new_algorithm: 新的加密算法
        """
        if new_algorithm == self.config.algorithm:
            logger.info("加密算法已是最新版本")
            return
        
        old_algorithm = self.config.algorithm
        self.config.algorithm = new_algorithm
        
        try:
            self._save_config()
            logger.info(f"加密算法已从 {old_algorithm.value} 升级到 {new_algorithm.value}")
        except Exception as e:
            # 回滚配置
            self.config.algorithm = old_algorithm
            logger.error(f"升级加密算法失败: {e}")
            raise
    
    def reencrypt_field(self, field_name: str, encrypted_data: Dict[str, Any], 
                       new_algorithm: EncryptionAlgorithm = None) -> Dict[str, Any]:
        """
        重新加密字段数据（用于算法升级）
        
        Args:
            field_name: 字段名称
            encrypted_data: 当前加密的数据
            new_algorithm: 新的加密算法（可选）
            
        Returns:
            使用新算法加密的数据
        """
        # 解密原始数据
        original_data = self.decrypt_field(field_name, encrypted_data)
        
        # 临时切换算法
        if new_algorithm:
            old_algorithm = self.config.algorithm
            self.config.algorithm = new_algorithm
        
        try:
            # 使用新算法重新加密
            new_encrypted_data = self.encrypt_field(field_name, original_data)
            logger.info(f"字段 {field_name} 重新加密成功")
            return new_encrypted_data
        finally:
            # 恢复原算法配置
            if new_algorithm:
                self.config.algorithm = old_algorithm
    
    def get_encryption_info(self) -> Dict[str, Any]:
        """获取加密配置信息"""
        return {
            'algorithm': self.config.algorithm.value,
            'key_derivation_iterations': self.config.key_derivation_iterations,
            'sensitive_fields_count': len(self.sensitive_fields),
            'sensitive_fields': list(self.sensitive_fields),
            'supported_algorithms': [alg.value for alg in EncryptionAlgorithm]
        }
    
    def clear_key_cache(self):
        """清除密钥缓存"""
        self._key_cache.clear()
        self._master_key = None
        logger.info("加密密钥缓存已清除")

def main():
    """测试字段加密服务"""
    print("字段加密服务测试")
    print("=" * 50)
    
    # 创建服务实例
    service = FieldEncryptionService()
    
    # 测试数据
    test_data = {
        'name': 'Test Project',
        'description': 'A test project',
        'api_key': 'sk-1234567890abcdef',
        'secret_key': 'secret_abcdef1234567890',
        'database_url': 'postgresql://user:pass@localhost/db',
        'normal_field': 'This is not sensitive'
    }
    
    print("\n原始数据:")
    for key, value in test_data.items():
        sensitive = service.is_sensitive_field(key)
        print(f"  {key}: {value} {'(敏感)' if sensitive else ''}")
    
    # 加密记录
    print("\n加密记录...")
    encrypted_record = service.encrypt_record(test_data)
    
    print("\n加密后的数据:")
    for key, value in encrypted_record.items():
        if isinstance(value, dict) and 'algorithm' in value:
            print(f"  {key}: [已加密] 算法={value['algorithm']}")
        else:
            print(f"  {key}: {value}")
    
    # 解密记录
    print("\n解密记录...")
    decrypted_record = service.decrypt_record(encrypted_record)
    
    print("\n解密后的数据:")
    for key, value in decrypted_record.items():
        print(f"  {key}: {value}")
    
    # 验证数据一致性
    print("\n数据一致性验证:")
    for key in test_data:
        original = test_data[key]
        decrypted = decrypted_record[key]
        match = original == decrypted
        print(f"  {key}: {'✓' if match else '✗'}")
    
    # 显示加密信息
    print("\n加密配置信息:")
    info = service.get_encryption_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print("\n测试完成!")

if __name__ == "__main__":
    main()