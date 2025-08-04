#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主密码管理器
提供主密码设置、验证、强度检查和重置功能
"""
import os
import sys
import hashlib
import secrets
import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PasswordStrength(Enum):
    """密码强度等级"""
    VERY_WEAK = 1
    WEAK = 2
    MEDIUM = 3
    STRONG = 4
    VERY_STRONG = 5

@dataclass
class PasswordPolicy:
    """密码策略配置"""
    min_length: int = 8
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_special_chars: bool = True
    min_special_chars: int = 1
    forbidden_patterns: list = None
    max_attempts: int = 5
    lockout_duration_minutes: int = 30

@dataclass
class SecurityQuestion:
    """安全问题"""
    question: str
    answer_hash: str
    salt: str

@dataclass
class PasswordValidationResult:
    """密码验证结果"""
    is_valid: bool
    strength: PasswordStrength
    score: int
    issues: list
    suggestions: list

class MasterPasswordManager:
    """主密码管理器"""
    
    def __init__(self, config_dir: str = None):
        """
        初始化主密码管理器
        
        Args:
            config_dir: 配置文件目录，默认为用户目录下的.swagger_tool
        """
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".swagger_tool")
        
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "master_password.json")
        self.policy = PasswordPolicy()
        
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        # 加载配置
        self._load_config()
        
        logger.info(f"主密码管理器初始化完成: {config_dir}")
    
    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.config = config
                logger.info("主密码配置加载成功")
            except Exception as e:
                logger.error(f"加载主密码配置失败: {e}")
                self.config = {}
        else:
            self.config = {}
    
    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info("主密码配置保存成功")
        except Exception as e:
            logger.error(f"保存主密码配置失败: {e}")
            raise
    
    def _generate_salt(self) -> str:
        """生成随机盐值"""
        return secrets.token_hex(32)
    
    def _hash_password(self, password: str, salt: str) -> str:
        """
        使用PBKDF2算法哈希密码
        
        Args:
            password: 原始密码
            salt: 盐值
            
        Returns:
            哈希后的密码
        """
        # 使用PBKDF2-HMAC-SHA256，迭代100000次
        password_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        hash_bytes = hashlib.pbkdf2_hmac('sha256', password_bytes, salt_bytes, 100000)
        return hash_bytes.hex()
    
    def validate_password_strength(self, password: str) -> PasswordValidationResult:
        """
        验证密码强度
        
        Args:
            password: 要验证的密码
            
        Returns:
            密码验证结果
        """
        issues = []
        suggestions = []
        score = 0
        
        # 检查长度
        if len(password) < self.policy.min_length:
            issues.append(f"密码长度不足，至少需要{self.policy.min_length}个字符")
            suggestions.append(f"增加密码长度至{self.policy.min_length}个字符以上")
        elif len(password) >= self.policy.min_length:
            score += 10
            if len(password) >= 12:
                score += 10
            if len(password) >= 16:
                score += 10
        
        if len(password) > self.policy.max_length:
            issues.append(f"密码长度过长，最多{self.policy.max_length}个字符")
        
        # 检查字符类型
        has_uppercase = any(c.isupper() for c in password)
        has_lowercase = any(c.islower() for c in password)
        has_digits = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)
        
        if self.policy.require_uppercase and not has_uppercase:
            issues.append("密码必须包含大写字母")
            suggestions.append("添加至少一个大写字母")
        elif has_uppercase:
            score += 15
        
        if self.policy.require_lowercase and not has_lowercase:
            issues.append("密码必须包含小写字母")
            suggestions.append("添加至少一个小写字母")
        elif has_lowercase:
            score += 15
        
        if self.policy.require_digits and not has_digits:
            issues.append("密码必须包含数字")
            suggestions.append("添加至少一个数字")
        elif has_digits:
            score += 15
        
        if self.policy.require_special_chars and not has_special:
            issues.append("密码必须包含特殊字符")
            suggestions.append("添加至少一个特殊字符（如!@#$%^&*）")
        elif has_special:
            score += 15
            # 额外奖励多种特殊字符
            special_count = sum(1 for c in password if not c.isalnum())
            if special_count >= self.policy.min_special_chars:
                score += 10
        
        # 检查字符多样性
        unique_chars = len(set(password))
        if unique_chars >= len(password) * 0.7:  # 70%的字符都不重复
            score += 10
        
        # 检查常见模式
        common_patterns = [
            '123456', 'password', 'qwerty', 'abc123', '111111',
            '123123', 'admin', 'root', 'user', 'test'
        ]
        
        password_lower = password.lower()
        for pattern in common_patterns:
            if pattern in password_lower:
                issues.append(f"密码包含常见模式: {pattern}")
                suggestions.append("避免使用常见的密码模式")
                score -= 20
                break
        
        # 检查重复字符
        if len(set(password)) < len(password) * 0.5:  # 超过50%的字符重复
            issues.append("密码包含过多重复字符")
            suggestions.append("减少重复字符的使用")
            score -= 10
        
        # 检查键盘模式
        keyboard_patterns = ['qwerty', 'asdf', 'zxcv', '1234', 'abcd']
        for pattern in keyboard_patterns:
            if pattern in password_lower:
                issues.append("密码包含键盘序列模式")
                suggestions.append("避免使用键盘上连续的字符")
                score -= 15
                break
        
        # 确保分数在0-100之间
        score = max(0, min(100, score))
        
        # 确定强度等级
        if score >= 90:
            strength = PasswordStrength.VERY_STRONG
        elif score >= 70:
            strength = PasswordStrength.STRONG
        elif score >= 50:
            strength = PasswordStrength.MEDIUM
        elif score >= 30:
            strength = PasswordStrength.WEAK
        else:
            strength = PasswordStrength.VERY_WEAK
        
        is_valid = len(issues) == 0 and strength.value >= 3  # 至少中等强度
        
        return PasswordValidationResult(
            is_valid=is_valid,
            strength=strength,
            score=score,
            issues=issues,
            suggestions=suggestions
        )
    
    def set_master_password(self, password: str, hint: str = None) -> bool:
        """
        设置主密码
        
        Args:
            password: 主密码
            hint: 密码提示
            
        Returns:
            是否设置成功
        """
        # 验证密码强度
        validation = self.validate_password_strength(password)
        if not validation.is_valid:
            logger.error(f"密码强度不足: {validation.issues}")
            return False
        
        try:
            # 生成盐值
            salt = self._generate_salt()
            
            # 哈希密码
            password_hash = self._hash_password(password, salt)
            
            # 保存配置
            self.config.update({
                'password_hash': password_hash,
                'salt': salt,
                'hint': hint,
                'created_at': datetime.now().isoformat(),
                'last_changed': datetime.now().isoformat(),
                'failed_attempts': 0,
                'locked_until': None,
                'security_questions': []
            })
            
            self._save_config()
            logger.info("主密码设置成功")
            return True
            
        except Exception as e:
            logger.error(f"设置主密码失败: {e}")
            return False
    
    def verify_master_password(self, password: str) -> bool:
        """
        验证主密码
        
        Args:
            password: 要验证的密码
            
        Returns:
            是否验证成功
        """
        if not self.has_master_password():
            logger.warning("尚未设置主密码")
            return False
        
        # 检查是否被锁定
        if self._is_locked():
            logger.warning("账户已被锁定")
            return False
        
        try:
            # 获取存储的哈希值和盐值
            stored_hash = self.config.get('password_hash')
            salt = self.config.get('salt')
            
            if not stored_hash or not salt:
                logger.error("密码配置数据不完整")
                return False
            
            # 计算输入密码的哈希值
            input_hash = self._hash_password(password, salt)
            
            # 比较哈希值
            if secrets.compare_digest(stored_hash, input_hash):
                # 验证成功，重置失败计数
                self.config['failed_attempts'] = 0
                self.config['locked_until'] = None
                self._save_config()
                logger.info("主密码验证成功")
                return True
            else:
                # 验证失败，增加失败计数
                self._handle_failed_attempt()
                logger.warning("主密码验证失败")
                return False
                
        except Exception as e:
            logger.error(f"验证主密码时发生错误: {e}")
            return False
    
    def _is_locked(self) -> bool:
        """检查账户是否被锁定"""
        locked_until = self.config.get('locked_until')
        if locked_until:
            try:
                lock_time = datetime.fromisoformat(locked_until)
                if datetime.now() < lock_time:
                    return True
                else:
                    # 锁定时间已过，解除锁定
                    self.config['locked_until'] = None
                    self.config['failed_attempts'] = 0
                    self._save_config()
            except ValueError:
                # 时间格式错误，解除锁定
                self.config['locked_until'] = None
                self._save_config()
        
        return False
    
    def _handle_failed_attempt(self):
        """处理密码验证失败"""
        failed_attempts = self.config.get('failed_attempts', 0) + 1
        self.config['failed_attempts'] = failed_attempts
        
        if failed_attempts >= self.policy.max_attempts:
            # 锁定账户
            lock_until = datetime.now() + timedelta(minutes=self.policy.lockout_duration_minutes)
            self.config['locked_until'] = lock_until.isoformat()
            logger.warning(f"账户已被锁定 {self.policy.lockout_duration_minutes} 分钟")
        
        self._save_config()
    
    def has_master_password(self) -> bool:
        """检查是否已设置主密码"""
        return bool(self.config.get('password_hash') and self.config.get('salt'))
    
    def get_password_hint(self) -> Optional[str]:
        """获取密码提示"""
        return self.config.get('hint')
    
    def change_master_password(self, old_password: str, new_password: str, hint: str = None) -> bool:
        """
        更改主密码
        
        Args:
            old_password: 旧密码
            new_password: 新密码
            hint: 新密码提示
            
        Returns:
            是否更改成功
        """
        # 验证旧密码
        if not self.verify_master_password(old_password):
            logger.error("旧密码验证失败")
            return False
        
        # 验证新密码强度
        validation = self.validate_password_strength(new_password)
        if not validation.is_valid:
            logger.error(f"新密码强度不足: {validation.issues}")
            return False
        
        # 检查新密码是否与旧密码相同
        old_salt = self.config.get('salt')
        old_hash = self._hash_password(new_password, old_salt)
        if secrets.compare_digest(old_hash, self.config.get('password_hash', '')):
            logger.error("新密码不能与旧密码相同")
            return False
        
        try:
            # 生成新的盐值
            new_salt = self._generate_salt()
            
            # 哈希新密码
            new_hash = self._hash_password(new_password, new_salt)
            
            # 更新配置
            self.config.update({
                'password_hash': new_hash,
                'salt': new_salt,
                'hint': hint,
                'last_changed': datetime.now().isoformat(),
                'failed_attempts': 0,
                'locked_until': None
            })
            
            self._save_config()
            logger.info("主密码更改成功")
            return True
            
        except Exception as e:
            logger.error(f"更改主密码失败: {e}")
            return False
    
    def add_security_question(self, question: str, answer: str) -> bool:
        """
        添加安全问题
        
        Args:
            question: 安全问题
            answer: 答案
            
        Returns:
            是否添加成功
        """
        try:
            # 生成答案的盐值和哈希
            salt = self._generate_salt()
            answer_hash = self._hash_password(answer.lower().strip(), salt)
            
            security_question = {
                'question': question,
                'answer_hash': answer_hash,
                'salt': salt,
                'created_at': datetime.now().isoformat()
            }
            
            # 添加到配置
            if 'security_questions' not in self.config:
                self.config['security_questions'] = []
            
            self.config['security_questions'].append(security_question)
            self._save_config()
            
            logger.info("安全问题添加成功")
            return True
            
        except Exception as e:
            logger.error(f"添加安全问题失败: {e}")
            return False
    
    def verify_security_answer(self, question_index: int, answer: str) -> bool:
        """
        验证安全问题答案
        
        Args:
            question_index: 问题索引
            answer: 答案
            
        Returns:
            是否验证成功
        """
        try:
            security_questions = self.config.get('security_questions', [])
            
            if question_index < 0 or question_index >= len(security_questions):
                logger.error("安全问题索引无效")
                return False
            
            question_data = security_questions[question_index]
            stored_hash = question_data['answer_hash']
            salt = question_data['salt']
            
            # 计算输入答案的哈希值（转换为小写并去除空格）
            input_hash = self._hash_password(answer.lower().strip(), salt)
            
            # 比较哈希值
            return secrets.compare_digest(stored_hash, input_hash)
            
        except Exception as e:
            logger.error(f"验证安全问题答案失败: {e}")
            return False
    
    def get_security_questions(self) -> list:
        """获取所有安全问题（不包含答案）"""
        security_questions = self.config.get('security_questions', [])
        return [{'index': i, 'question': q['question']} 
                for i, q in enumerate(security_questions)]
    
    def reset_password_with_security_questions(self, answers: Dict[int, str], new_password: str, hint: str = None) -> bool:
        """
        通过安全问题重置密码
        
        Args:
            answers: 安全问题答案字典 {问题索引: 答案}
            new_password: 新密码
            hint: 新密码提示
            
        Returns:
            是否重置成功
        """
        security_questions = self.config.get('security_questions', [])
        
        if not security_questions:
            logger.error("没有设置安全问题")
            return False
        
        # 需要至少回答一半的安全问题
        required_answers = max(1, len(security_questions) // 2)
        
        if len(answers) < required_answers:
            logger.error(f"需要至少回答 {required_answers} 个安全问题")
            return False
        
        # 验证所有提供的答案
        correct_answers = 0
        for question_index, answer in answers.items():
            if self.verify_security_answer(question_index, answer):
                correct_answers += 1
        
        if correct_answers < required_answers:
            logger.error("安全问题答案验证失败")
            return False
        
        # 验证新密码强度
        validation = self.validate_password_strength(new_password)
        if not validation.is_valid:
            logger.error(f"新密码强度不足: {validation.issues}")
            return False
        
        try:
            # 生成新的盐值
            new_salt = self._generate_salt()
            
            # 哈希新密码
            new_hash = self._hash_password(new_password, new_salt)
            
            # 更新配置
            self.config.update({
                'password_hash': new_hash,
                'salt': new_salt,
                'hint': hint,
                'last_changed': datetime.now().isoformat(),
                'failed_attempts': 0,
                'locked_until': None,
                'reset_at': datetime.now().isoformat()
            })
            
            self._save_config()
            logger.info("密码重置成功")
            return True
            
        except Exception as e:
            logger.error(f"重置密码失败: {e}")
            return False
    
    def get_account_status(self) -> Dict[str, Any]:
        """获取账户状态信息"""
        status = {
            'has_password': self.has_master_password(),
            'failed_attempts': self.config.get('failed_attempts', 0),
            'is_locked': self._is_locked(),
            'locked_until': self.config.get('locked_until'),
            'last_changed': self.config.get('last_changed'),
            'security_questions_count': len(self.config.get('security_questions', [])),
            'max_attempts': self.policy.max_attempts,
            'lockout_duration_minutes': self.policy.lockout_duration_minutes
        }
        
        return status
    
    def generate_password_suggestion(self, length: int = 16) -> str:
        """
        生成符合策略的密码建议
        
        Args:
            length: 密码长度
            
        Returns:
            生成的密码
        """
        import string
        
        # 确保长度符合策略
        length = max(self.policy.min_length, min(length, self.policy.max_length))
        
        # 定义字符集
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        # 确保包含所需的字符类型
        password_chars = []
        
        if self.policy.require_lowercase:
            password_chars.append(secrets.choice(lowercase))
        if self.policy.require_uppercase:
            password_chars.append(secrets.choice(uppercase))
        if self.policy.require_digits:
            password_chars.append(secrets.choice(digits))
        if self.policy.require_special_chars:
            for _ in range(self.policy.min_special_chars):
                password_chars.append(secrets.choice(special_chars))
        
        # 填充剩余长度
        all_chars = lowercase + uppercase + digits + special_chars
        remaining_length = length - len(password_chars)
        
        for _ in range(remaining_length):
            password_chars.append(secrets.choice(all_chars))
        
        # 随机打乱字符顺序
        secrets.SystemRandom().shuffle(password_chars)
        
        return ''.join(password_chars)

def main():
    """测试主密码管理器"""
    print("主密码管理器测试")
    print("=" * 50)
    
    # 创建管理器实例
    manager = MasterPasswordManager()
    
    # 测试密码强度验证
    test_passwords = [
        "123456",
        "password",
        "Password123",
        "MyStr0ng!Pass",
        "Sup3r$3cur3P@ssw0rd!"
    ]
    
    print("\n密码强度测试:")
    for password in test_passwords:
        result = manager.validate_password_strength(password)
        print(f"密码: {password}")
        print(f"  强度: {result.strength.name} (分数: {result.score})")
        print(f"  有效: {result.is_valid}")
        if result.issues:
            print(f"  问题: {', '.join(result.issues)}")
        if result.suggestions:
            print(f"  建议: {', '.join(result.suggestions)}")
        print()
    
    # 测试密码生成
    print("密码生成测试:")
    for length in [12, 16, 20]:
        suggested = manager.generate_password_suggestion(length)
        validation = manager.validate_password_strength(suggested)
        print(f"长度 {length}: {suggested} (强度: {validation.strength.name})")
    
    print("\n测试完成!")

if __name__ == "__main__":
    main()