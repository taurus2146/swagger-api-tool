#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
加密密钥管理器
提供安全的密钥存储、管理和轮换功能
"""
import os
import sys
import json
import base64
import logging
import secrets
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.master_password_manager import MasterPasswordManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class KeyInfo:
    """密钥信息"""
    key_id: str
    algorithm: str
    created_at: str
    expires_at: Optional[str] = None
    is_active: bool = True
    usage_count: int = 0
    max_usage: Optional[int] = None

class EncryptionKeyManager:
    """加密密钥管理器"""
    
    def __init__(self, master_password_manager: MasterPasswordManager = None, 
                 config_dir: str = None):
        """
        初始化密钥管理器
        
        Args:
            master_password_manager: 主密码管理器
            config_dir: 配置目录
        """
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".swagger_tool")
        
        self.config_dir = config_dir
        self.keys_file = os.path.join(config_dir, "encryption_keys.json")
        
        # 主密码管理器
        if master_password_manager is None:
            self.master_password_manager = MasterPasswordManager(config_dir)
        else:
            self.master_password_manager = master_password_manager
        
        # 密钥存储
        self.keys_data = {}
        self._master_key = None
        
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        # 加载密钥数据
        self._load_keys()
        
        logger.info(f"加密密钥管理器初始化完成: {config_dir}")
    
    def _get_master_key(self) -> bytes:
        """获取主密钥用于加密存储的密钥"""
        if self._master_key is not None:
            return self._master_key
        
        # 检查主密码是否设置
        if not self.master_password_manager.has_master_password():
            raise ValueError("尚未设置主密码，无法管理加密密钥")
        
        # 使用固定盐值派生密钥管理主密钥
        salt = b"key_manager_salt_v1_32bytes_long"
        master_password = "dummy_password"  # 实际应用中应从安全输入获取
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        self._master_key = kdf.derive(master_password.encode('utf-8'))
        return self._master_key    

    def _encrypt_key_data(self, data: bytes) -> str:
        """加密密钥数据"""
        from cryptography.fernet import Fernet
        
        master_key = self._get_master_key()
        fernet_key = base64.urlsafe_b64encode(master_key)
        fernet = Fernet(fernet_key)
        
        encrypted_data = fernet.encrypt(data)
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def _decrypt_key_data(self, encrypted_data: str) -> bytes:
        """解密密钥数据"""
        from cryptography.fernet import Fernet
        
        master_key = self._get_master_key()
        fernet_key = base64.urlsafe_b64encode(master_key)
        fernet = Fernet(fernet_key)
        
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        return fernet.decrypt(encrypted_bytes)
    
    def _load_keys(self):
        """加载密钥数据"""
        if os.path.exists(self.keys_file):
            try:
                with open(self.keys_file, 'r', encoding='utf-8') as f:
                    self.keys_data = json.load(f)
                logger.info("密钥数据加载成功")
            except Exception as e:
                logger.error(f"加载密钥数据失败: {e}")
                self.keys_data = {}
        else:
            self.keys_data = {}
    
    def _save_keys(self):
        """保存密钥数据"""
        try:
            with open(self.keys_file, 'w', encoding='utf-8') as f:
                json.dump(self.keys_data, f, indent=2, ensure_ascii=False)
            logger.info("密钥数据保存成功")
        except Exception as e:
            logger.error(f"保存密钥数据失败: {e}")
            raise
    
    def generate_symmetric_key(self, key_id: str, algorithm: str = "AES-256", 
                             expires_days: int = None) -> bool:
        """
        生成对称加密密钥
        
        Args:
            key_id: 密钥ID
            algorithm: 加密算法
            expires_days: 过期天数
            
        Returns:
            是否生成成功
        """
        try:
            # 生成32字节的随机密钥（AES-256）
            key_bytes = secrets.token_bytes(32)
            
            # 加密密钥数据
            encrypted_key = self._encrypt_key_data(key_bytes)
            
            # 计算过期时间
            expires_at = None
            if expires_days:
                expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
            
            # 存储密钥信息
            key_info = {
                'key_id': key_id,
                'algorithm': algorithm,
                'encrypted_key': encrypted_key,
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at,
                'is_active': True,
                'usage_count': 0,
                'key_type': 'symmetric'
            }
            
            self.keys_data[key_id] = key_info
            self._save_keys()
            
            logger.info(f"对称密钥 {key_id} 生成成功")
            return True
            
        except Exception as e:
            logger.error(f"生成对称密钥 {key_id} 失败: {e}")
            return False
    
    def generate_asymmetric_key_pair(self, key_id: str, key_size: int = 2048,
                                   expires_days: int = None) -> bool:
        """
        生成非对称密钥对
        
        Args:
            key_id: 密钥ID
            key_size: 密钥长度
            expires_days: 过期天数
            
        Returns:
            是否生成成功
        """
        try:
            # 生成RSA密钥对
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )
            
            public_key = private_key.public_key()
            
            # 序列化私钥
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            # 序列化公钥
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            # 加密私钥
            encrypted_private_key = self._encrypt_key_data(private_pem)
            encrypted_public_key = self._encrypt_key_data(public_pem)
            
            # 计算过期时间
            expires_at = None
            if expires_days:
                expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
            
            # 存储密钥信息
            key_info = {
                'key_id': key_id,
                'algorithm': f'RSA-{key_size}',
                'encrypted_private_key': encrypted_private_key,
                'encrypted_public_key': encrypted_public_key,
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at,
                'is_active': True,
                'usage_count': 0,
                'key_type': 'asymmetric'
            }
            
            self.keys_data[key_id] = key_info
            self._save_keys()
            
            logger.info(f"非对称密钥对 {key_id} 生成成功")
            return True
            
        except Exception as e:
            logger.error(f"生成非对称密钥对 {key_id} 失败: {e}")
            return False
    
    def get_key(self, key_id: str) -> Optional[bytes]:
        """
        获取对称密钥
        
        Args:
            key_id: 密钥ID
            
        Returns:
            密钥字节数据
        """
        if key_id not in self.keys_data:
            logger.warning(f"密钥 {key_id} 不存在")
            return None
        
        key_info = self.keys_data[key_id]
        
        # 检查密钥是否有效
        if not key_info.get('is_active', False):
            logger.warning(f"密钥 {key_id} 已禁用")
            return None
        
        # 检查是否过期
        if key_info.get('expires_at'):
            expires_at = datetime.fromisoformat(key_info['expires_at'])
            if datetime.now() > expires_at:
                logger.warning(f"密钥 {key_id} 已过期")
                return None
        
        try:
            # 解密并返回密钥
            if key_info.get('key_type') == 'symmetric':
                key_bytes = self._decrypt_key_data(key_info['encrypted_key'])
            else:
                logger.error(f"密钥 {key_id} 不是对称密钥")
                return None
            
            # 更新使用计数
            key_info['usage_count'] = key_info.get('usage_count', 0) + 1
            self._save_keys()
            
            return key_bytes
            
        except Exception as e:
            logger.error(f"获取密钥 {key_id} 失败: {e}")
            return None
    
    def get_private_key(self, key_id: str):
        """
        获取私钥
        
        Args:
            key_id: 密钥ID
            
        Returns:
            私钥对象
        """
        if key_id not in self.keys_data:
            logger.warning(f"密钥 {key_id} 不存在")
            return None
        
        key_info = self.keys_data[key_id]
        
        if key_info.get('key_type') != 'asymmetric':
            logger.error(f"密钥 {key_id} 不是非对称密钥")
            return None
        
        try:
            # 解密私钥
            private_pem = self._decrypt_key_data(key_info['encrypted_private_key'])
            
            # 加载私钥
            private_key = serialization.load_pem_private_key(
                private_pem,
                password=None,
                backend=default_backend()
            )
            
            # 更新使用计数
            key_info['usage_count'] = key_info.get('usage_count', 0) + 1
            self._save_keys()
            
            return private_key
            
        except Exception as e:
            logger.error(f"获取私钥 {key_id} 失败: {e}")
            return None
    
    def get_public_key(self, key_id: str):
        """
        获取公钥
        
        Args:
            key_id: 密钥ID
            
        Returns:
            公钥对象
        """
        if key_id not in self.keys_data:
            logger.warning(f"密钥 {key_id} 不存在")
            return None
        
        key_info = self.keys_data[key_id]
        
        if key_info.get('key_type') != 'asymmetric':
            logger.error(f"密钥 {key_id} 不是非对称密钥")
            return None
        
        try:
            # 解密公钥
            public_pem = self._decrypt_key_data(key_info['encrypted_public_key'])
            
            # 加载公钥
            public_key = serialization.load_pem_public_key(
                public_pem,
                backend=default_backend()
            )
            
            return public_key
            
        except Exception as e:
            logger.error(f"获取公钥 {key_id} 失败: {e}")
            return None
    
    def list_keys(self) -> List[KeyInfo]:
        """
        列出所有密钥信息
        
        Returns:
            密钥信息列表
        """
        key_list = []
        
        for key_id, key_data in self.keys_data.items():
            key_info = KeyInfo(
                key_id=key_id,
                algorithm=key_data.get('algorithm', 'unknown'),
                created_at=key_data.get('created_at', ''),
                expires_at=key_data.get('expires_at'),
                is_active=key_data.get('is_active', False),
                usage_count=key_data.get('usage_count', 0),
                max_usage=key_data.get('max_usage')
            )
            key_list.append(key_info)
        
        return key_list
    
    def deactivate_key(self, key_id: str) -> bool:
        """
        禁用密钥
        
        Args:
            key_id: 密钥ID
            
        Returns:
            是否禁用成功
        """
        if key_id not in self.keys_data:
            logger.warning(f"密钥 {key_id} 不存在")
            return False
        
        try:
            self.keys_data[key_id]['is_active'] = False
            self.keys_data[key_id]['deactivated_at'] = datetime.now().isoformat()
            self._save_keys()
            
            logger.info(f"密钥 {key_id} 已禁用")
            return True
            
        except Exception as e:
            logger.error(f"禁用密钥 {key_id} 失败: {e}")
            return False
    
    def delete_key(self, key_id: str) -> bool:
        """
        删除密钥
        
        Args:
            key_id: 密钥ID
            
        Returns:
            是否删除成功
        """
        if key_id not in self.keys_data:
            logger.warning(f"密钥 {key_id} 不存在")
            return False
        
        try:
            del self.keys_data[key_id]
            self._save_keys()
            
            logger.info(f"密钥 {key_id} 已删除")
            return True
            
        except Exception as e:
            logger.error(f"删除密钥 {key_id} 失败: {e}")
            return False
    
    def rotate_key(self, key_id: str) -> bool:
        """
        轮换密钥（生成新密钥并禁用旧密钥）
        
        Args:
            key_id: 密钥ID
            
        Returns:
            是否轮换成功
        """
        if key_id not in self.keys_data:
            logger.warning(f"密钥 {key_id} 不存在")
            return False
        
        try:
            old_key_info = self.keys_data[key_id]
            key_type = old_key_info.get('key_type', 'symmetric')
            algorithm = old_key_info.get('algorithm', 'AES-256')
            
            # 创建新密钥ID
            new_key_id = f"{key_id}_v{int(datetime.now().timestamp())}"
            
            # 生成新密钥
            if key_type == 'symmetric':
                success = self.generate_symmetric_key(new_key_id, algorithm)
            else:
                key_size = int(algorithm.split('-')[1]) if '-' in algorithm else 2048
                success = self.generate_asymmetric_key_pair(new_key_id, key_size)
            
            if success:
                # 禁用旧密钥
                self.deactivate_key(key_id)
                logger.info(f"密钥 {key_id} 轮换成功，新密钥ID: {new_key_id}")
                return True
            else:
                logger.error(f"密钥 {key_id} 轮换失败")
                return False
                
        except Exception as e:
            logger.error(f"轮换密钥 {key_id} 失败: {e}")
            return False
    
    def cleanup_expired_keys(self) -> int:
        """
        清理过期密钥
        
        Returns:
            清理的密钥数量
        """
        cleaned_count = 0
        current_time = datetime.now()
        
        keys_to_remove = []
        
        for key_id, key_info in self.keys_data.items():
            expires_at = key_info.get('expires_at')
            if expires_at:
                try:
                    expire_time = datetime.fromisoformat(expires_at)
                    if current_time > expire_time:
                        keys_to_remove.append(key_id)
                except ValueError:
                    logger.warning(f"密钥 {key_id} 的过期时间格式无效")
        
        # 删除过期密钥
        for key_id in keys_to_remove:
            if self.delete_key(key_id):
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"清理了 {cleaned_count} 个过期密钥")
        
        return cleaned_count
    
    def get_key_statistics(self) -> Dict[str, Any]:
        """
        获取密钥统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'total_keys': len(self.keys_data),
            'active_keys': 0,
            'inactive_keys': 0,
            'expired_keys': 0,
            'symmetric_keys': 0,
            'asymmetric_keys': 0,
            'total_usage': 0
        }
        
        current_time = datetime.now()
        
        for key_info in self.keys_data.values():
            # 统计活跃状态
            if key_info.get('is_active', False):
                stats['active_keys'] += 1
            else:
                stats['inactive_keys'] += 1
            
            # 统计过期状态
            expires_at = key_info.get('expires_at')
            if expires_at:
                try:
                    expire_time = datetime.fromisoformat(expires_at)
                    if current_time > expire_time:
                        stats['expired_keys'] += 1
                except ValueError:
                    pass
            
            # 统计密钥类型
            key_type = key_info.get('key_type', 'symmetric')
            if key_type == 'symmetric':
                stats['symmetric_keys'] += 1
            else:
                stats['asymmetric_keys'] += 1
            
            # 统计使用次数
            stats['total_usage'] += key_info.get('usage_count', 0)
        
        return stats

def main():
    """测试加密密钥管理器"""
    print("加密密钥管理器测试")
    print("=" * 50)
    
    # 创建临时目录
    import tempfile
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 创建密钥管理器
        key_manager = EncryptionKeyManager(config_dir=temp_dir)
        
        # 生成对称密钥
        print("\n生成对称密钥...")
        success = key_manager.generate_symmetric_key("test_aes_key", "AES-256", 30)
        print(f"生成结果: {'成功' if success else '失败'}")
        
        # 生成非对称密钥对
        print("\n生成非对称密钥对...")
        success = key_manager.generate_asymmetric_key_pair("test_rsa_key", 2048, 60)
        print(f"生成结果: {'成功' if success else '失败'}")
        
        # 列出所有密钥
        print("\n密钥列表:")
        keys = key_manager.list_keys()
        for key_info in keys:
            print(f"  ID: {key_info.key_id}")
            print(f"  算法: {key_info.algorithm}")
            print(f"  创建时间: {key_info.created_at}")
            print(f"  是否活跃: {key_info.is_active}")
            print(f"  使用次数: {key_info.usage_count}")
            print()
        
        # 获取对称密钥
        print("获取对称密钥...")
        aes_key = key_manager.get_key("test_aes_key")
        if aes_key:
            print(f"密钥长度: {len(aes_key)} 字节")
        
        # 获取非对称密钥
        print("\n获取非对称密钥...")
        private_key = key_manager.get_private_key("test_rsa_key")
        public_key = key_manager.get_public_key("test_rsa_key")
        
        if private_key and public_key:
            print("私钥和公钥获取成功")
            
            # 测试加密解密
            message = b"Hello, World!"
            encrypted = public_key.encrypt(
                message,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            decrypted = private_key.decrypt(
                encrypted,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            print(f"加密解密测试: {'成功' if message == decrypted else '失败'}")
        
        # 获取统计信息
        print("\n密钥统计信息:")
        stats = key_manager.get_key_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print("\n测试完成!")
        
    finally:
        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()