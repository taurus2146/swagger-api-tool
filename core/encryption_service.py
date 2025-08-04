#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据加密服务
提供敏感数据的AES-256加密存储和密钥管理功能
"""

import os
import base64
import hashlib
import logging
from typing import Optional, Dict, Any, Union, List
from dataclasses import dataclass
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


@dataclass
class EncryptionConfig:
    """加密配置"""
    algorithm: str = "AES-256-GCM"
    key_derivation: str = "PBKDF2"
    iterations: int = 100000
    salt_length: int = 32
    iv_length: int = 12  # GCM模式推荐12字节
    tag_length: int = 16


class EncryptionService:
    """数据加密服务类"""
    
    def __init__(self, master_password: Optional[str] = None):
        """
        初始化加密服务
        
        Args:
            master_password: 主密码，如果为None则使用默认密码
        """
        self.config = EncryptionConfig()
        self._master_password = master_password or self._get_default_password()
        self._derived_keys: Dict[str, bytes] = {}  # 缓存派生密钥
        self._backend = default_backend()
    
    def _get_default_password(self) -> str:
        """
        获取默认主密码
        在实际应用中，这应该从安全的地方获取，比如系统密钥环
        
        Returns:
            str: 默认密码
        """
        # 这里使用一个基于机器信息的默认密码
        # 在生产环境中应该使用更安全的方式
        import platform
        machine_info = f"{platform.node()}-{platform.system()}-{platform.machine()}"
        return hashlib.sha256(machine_info.encode()).hexdigest()[:32]
    
    def _derive_key(self, password: str, salt: bytes, purpose: str = "default") -> bytes:
        """
        使用PBKDF2派生密钥
        
        Args:
            password: 密码
            salt: 盐值
            purpose: 密钥用途（用于缓存）
            
        Returns:
            bytes: 派生的密钥
        """
        cache_key = f"{purpose}:{base64.b64encode(salt).decode()}"
        
        if cache_key in self._derived_keys:
            return self._derived_keys[cache_key]
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # AES-256需要32字节密钥
            salt=salt,
            iterations=self.config.iterations,
            backend=self._backend
        )
        
        key = kdf.derive(password.encode())
        self._derived_keys[cache_key] = key
        
        logger.debug(f"派生密钥完成: {purpose}")
        return key
    
    def _generate_salt(self) -> bytes:
        """
        生成随机盐值
        
        Returns:
            bytes: 随机盐值
        """
        return os.urandom(self.config.salt_length)
    
    def _generate_iv(self) -> bytes:
        """
        生成随机初始化向量
        
        Returns:
            bytes: 随机IV
        """
        return os.urandom(self.config.iv_length)
    
    def encrypt_data(self, plaintext: Union[str, bytes], password: Optional[str] = None) -> str:
        """
        加密数据
        
        Args:
            plaintext: 要加密的明文数据
            password: 加密密码，如果为None则使用主密码
            
        Returns:
            str: Base64编码的加密数据（包含盐值、IV和密文）
        """
        try:
            # 转换为bytes
            if isinstance(plaintext, str):
                plaintext_bytes = plaintext.encode('utf-8')
            else:
                plaintext_bytes = plaintext
            
            # 使用指定密码或主密码
            password = password or self._master_password
            
            # 生成盐值和IV
            salt = self._generate_salt()
            iv = self._generate_iv()
            
            # 派生密钥
            key = self._derive_key(password, salt)
            
            # 创建加密器（使用AES-GCM模式）
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv),
                backend=self._backend
            )
            encryptor = cipher.encryptor()
            
            # 加密数据
            ciphertext = encryptor.update(plaintext_bytes) + encryptor.finalize()
            
            # 获取认证标签
            tag = encryptor.tag
            
            # 组合所有数据：盐值 + IV + 标签 + 密文
            encrypted_data = salt + iv + tag + ciphertext
            
            # Base64编码
            encoded_data = base64.b64encode(encrypted_data).decode('ascii')
            
            logger.debug(f"数据加密成功，长度: {len(plaintext_bytes)} -> {len(encoded_data)}")
            return encoded_data
            
        except Exception as e:
            logger.error(f"数据加密失败: {e}")
            raise EncryptionError(f"加密失败: {e}")
    
    def decrypt_data(self, encrypted_data: str, password: Optional[str] = None) -> str:
        """
        解密数据
        
        Args:
            encrypted_data: Base64编码的加密数据
            password: 解密密码，如果为None则使用主密码
            
        Returns:
            str: 解密后的明文数据
        """
        try:
            # Base64解码
            encrypted_bytes = base64.b64decode(encrypted_data.encode('ascii'))
            
            # 提取各部分
            salt = encrypted_bytes[:self.config.salt_length]
            iv = encrypted_bytes[self.config.salt_length:self.config.salt_length + self.config.iv_length]
            tag = encrypted_bytes[self.config.salt_length + self.config.iv_length:
                                self.config.salt_length + self.config.iv_length + self.config.tag_length]
            ciphertext = encrypted_bytes[self.config.salt_length + self.config.iv_length + self.config.tag_length:]
            
            # 使用指定密码或主密码
            password = password or self._master_password
            
            # 派生密钥
            key = self._derive_key(password, salt)
            
            # 创建解密器
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv, tag),
                backend=self._backend
            )
            decryptor = cipher.decryptor()
            
            # 解密数据
            plaintext_bytes = decryptor.update(ciphertext) + decryptor.finalize()
            
            # 转换为字符串
            plaintext = plaintext_bytes.decode('utf-8')
            
            logger.debug(f"数据解密成功，长度: {len(encrypted_data)} -> {len(plaintext)}")
            return plaintext
            
        except Exception as e:
            logger.error(f"数据解密失败: {e}")
            raise EncryptionError(f"解密失败: {e}")
    
    def encrypt_dict(self, data: Dict[str, Any], sensitive_keys: List[str], 
                    password: Optional[str] = None) -> Dict[str, Any]:
        """
        加密字典中的敏感字段
        
        Args:
            data: 要处理的字典
            sensitive_keys: 需要加密的键列表
            password: 加密密码
            
        Returns:
            Dict[str, Any]: 处理后的字典
        """
        try:
            result = data.copy()
            
            for key in sensitive_keys:
                if key in result and result[key] is not None:
                    # 将值转换为JSON字符串（如果不是字符串）
                    if not isinstance(result[key], str):
                        import json
                        value_str = json.dumps(result[key], ensure_ascii=False)
                    else:
                        value_str = result[key]
                    
                    # 加密值
                    encrypted_value = self.encrypt_data(value_str, password)
                    result[key] = f"encrypted:{encrypted_value}"
            
            return result
            
        except Exception as e:
            logger.error(f"字典加密失败: {e}")
            raise EncryptionError(f"字典加密失败: {e}")
    
    def decrypt_dict(self, data: Dict[str, Any], sensitive_keys: List[str],
                    password: Optional[str] = None) -> Dict[str, Any]:
        """
        解密字典中的敏感字段
        
        Args:
            data: 要处理的字典
            sensitive_keys: 需要解密的键列表
            password: 解密密码
            
        Returns:
            Dict[str, Any]: 处理后的字典
        """
        try:
            result = data.copy()
            
            for key in sensitive_keys:
                if key in result and isinstance(result[key], str):
                    value = result[key]
                    
                    # 检查是否为加密数据
                    if value.startswith("encrypted:"):
                        encrypted_data = value[10:]  # 移除"encrypted:"前缀
                        
                        try:
                            # 解密值
                            decrypted_value = self.decrypt_data(encrypted_data, password)
                            
                            # 尝试解析JSON
                            try:
                                import json
                                result[key] = json.loads(decrypted_value)
                            except json.JSONDecodeError:
                                result[key] = decrypted_value
                                
                        except EncryptionError:
                            logger.warning(f"解密字段失败: {key}")
                            # 保持原值不变
            
            return result
            
        except Exception as e:
            logger.error(f"字典解密失败: {e}")
            raise EncryptionError(f"字典解密失败: {e}")
    
    def generate_key_pair(self) -> tuple[str, str]:
        """
        生成RSA密钥对（用于非对称加密）
        
        Returns:
            tuple[str, str]: (私钥PEM, 公钥PEM)
        """
        try:
            # 生成私钥
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=self._backend
            )
            
            # 获取公钥
            public_key = private_key.public_key()
            
            # 序列化私钥
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
            
            # 序列化公钥
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
            
            logger.info("RSA密钥对生成成功")
            return private_pem, public_pem
            
        except Exception as e:
            logger.error(f"密钥对生成失败: {e}")
            raise EncryptionError(f"密钥对生成失败: {e}")
    
    def encrypt_with_public_key(self, plaintext: str, public_key_pem: str) -> str:
        """
        使用公钥加密数据
        
        Args:
            plaintext: 明文数据
            public_key_pem: 公钥PEM格式
            
        Returns:
            str: Base64编码的加密数据
        """
        try:
            # 加载公钥
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=self._backend
            )
            
            # 加密数据
            ciphertext = public_key.encrypt(
                plaintext.encode('utf-8'),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Base64编码
            encoded_data = base64.b64encode(ciphertext).decode('ascii')
            
            logger.debug("公钥加密成功")
            return encoded_data
            
        except Exception as e:
            logger.error(f"公钥加密失败: {e}")
            raise EncryptionError(f"公钥加密失败: {e}")
    
    def decrypt_with_private_key(self, encrypted_data: str, private_key_pem: str) -> str:
        """
        使用私钥解密数据
        
        Args:
            encrypted_data: Base64编码的加密数据
            private_key_pem: 私钥PEM格式
            
        Returns:
            str: 解密后的明文数据
        """
        try:
            # Base64解码
            ciphertext = base64.b64decode(encrypted_data.encode('ascii'))
            
            # 加载私钥
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None,
                backend=self._backend
            )
            
            # 解密数据
            plaintext_bytes = private_key.decrypt(
                ciphertext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # 转换为字符串
            plaintext = plaintext_bytes.decode('utf-8')
            
            logger.debug("私钥解密成功")
            return plaintext
            
        except Exception as e:
            logger.error(f"私钥解密失败: {e}")
            raise EncryptionError(f"私钥解密失败: {e}")
    
    def generate_fernet_key(self) -> str:
        """
        生成Fernet密钥（用于简单的对称加密）
        
        Returns:
            str: Base64编码的Fernet密钥
        """
        key = Fernet.generate_key()
        return key.decode('ascii')
    
    def encrypt_with_fernet(self, plaintext: str, key: str) -> str:
        """
        使用Fernet加密数据
        
        Args:
            plaintext: 明文数据
            key: Fernet密钥
            
        Returns:
            str: 加密后的数据
        """
        try:
            f = Fernet(key.encode('ascii'))
            encrypted_data = f.encrypt(plaintext.encode('utf-8'))
            return encrypted_data.decode('ascii')
            
        except Exception as e:
            logger.error(f"Fernet加密失败: {e}")
            raise EncryptionError(f"Fernet加密失败: {e}")
    
    def decrypt_with_fernet(self, encrypted_data: str, key: str) -> str:
        """
        使用Fernet解密数据
        
        Args:
            encrypted_data: 加密数据
            key: Fernet密钥
            
        Returns:
            str: 解密后的明文数据
        """
        try:
            f = Fernet(key.encode('ascii'))
            plaintext_bytes = f.decrypt(encrypted_data.encode('ascii'))
            return plaintext_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Fernet解密失败: {e}")
            raise EncryptionError(f"Fernet解密失败: {e}")
    
    def hash_password(self, password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
        """
        哈希密码
        
        Args:
            password: 密码
            salt: 盐值，如果为None则生成新的
            
        Returns:
            tuple[str, str]: (哈希值, 盐值) 都是Base64编码
        """
        try:
            if salt is None:
                salt = self._generate_salt()
            
            # 使用PBKDF2哈希密码
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=self.config.iterations,
                backend=self._backend
            )
            
            hash_value = kdf.derive(password.encode())
            
            # Base64编码
            hash_b64 = base64.b64encode(hash_value).decode('ascii')
            salt_b64 = base64.b64encode(salt).decode('ascii')
            
            return hash_b64, salt_b64
            
        except Exception as e:
            logger.error(f"密码哈希失败: {e}")
            raise EncryptionError(f"密码哈希失败: {e}")
    
    def verify_password(self, password: str, hash_value: str, salt: str) -> bool:
        """
        验证密码
        
        Args:
            password: 要验证的密码
            hash_value: Base64编码的哈希值
            salt: Base64编码的盐值
            
        Returns:
            bool: 密码是否正确
        """
        try:
            # Base64解码
            expected_hash = base64.b64decode(hash_value.encode('ascii'))
            salt_bytes = base64.b64decode(salt.encode('ascii'))
            
            # 计算密码哈希
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_bytes,
                iterations=self.config.iterations,
                backend=self._backend
            )
            
            try:
                kdf.verify(password.encode(), expected_hash)
                return True
            except Exception:
                return False
                
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False
    
    def change_master_password(self, new_password: str) -> None:
        """
        更改主密码
        
        Args:
            new_password: 新的主密码
        """
        self._master_password = new_password
        self._derived_keys.clear()  # 清空密钥缓存
        logger.info("主密码已更改")
    
    def clear_key_cache(self) -> None:
        """清空密钥缓存"""
        self._derived_keys.clear()
        logger.debug("密钥缓存已清空")
    
    def get_encryption_info(self) -> Dict[str, Any]:
        """
        获取加密服务信息
        
        Returns:
            Dict[str, Any]: 加密服务信息
        """
        return {
            'algorithm': self.config.algorithm,
            'key_derivation': self.config.key_derivation,
            'iterations': self.config.iterations,
            'salt_length': self.config.salt_length,
            'iv_length': self.config.iv_length,
            'cached_keys': len(self._derived_keys),
            'has_master_password': bool(self._master_password)
        }


class EncryptionError(Exception):
    """加密相关异常"""
    pass