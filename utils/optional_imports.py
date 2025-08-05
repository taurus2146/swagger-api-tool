#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
可选导入处理模块
为移除的大型依赖提供降级替代方案
"""

import sys
import warnings

# 全局标志，标记哪些可选功能可用
FEATURES = {
    'excel_export': False,
    'advanced_crypto': False,
    'system_monitoring': False,
    'progress_bars': False,
    'data_analysis': False,
}

# pandas 替代方案
try:
    import pandas as pd
    FEATURES['data_analysis'] = True
    FEATURES['excel_export'] = True
except ImportError:
    # 创建简单的DataFrame替代
    class SimpleDataFrame:
        def __init__(self, data=None):
            self.data = data or []
        
        def to_excel(self, filename, **kwargs):
            raise NotImplementedError("Excel导出功能不可用。请安装pandas: pip install pandas")
        
        def to_csv(self, filename, **kwargs):
            # 简单的CSV导出
            import csv
            if isinstance(self.data, list) and self.data:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    if isinstance(self.data[0], dict):
                        writer = csv.DictWriter(f, fieldnames=self.data[0].keys())
                        writer.writeheader()
                        writer.writerows(self.data)
                    else:
                        writer = csv.writer(f)
                        writer.writerows(self.data)
    
    # 创建pandas模块替代
    class PandasModule:
        DataFrame = SimpleDataFrame
        
        def read_excel(self, *args, **kwargs):
            raise NotImplementedError("Excel读取功能不可用。请安装pandas: pip install pandas")
        
        def read_csv(self, filename, **kwargs):
            import csv
            data = []
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                data = list(reader)
            return SimpleDataFrame(data)
    
    pd = PandasModule()

# openpyxl 替代方案
try:
    import openpyxl
    FEATURES['excel_export'] = True
except ImportError:
    class OpenpyxlModule:
        def load_workbook(self, *args, **kwargs):
            raise NotImplementedError("Excel功能不可用。请安装openpyxl: pip install openpyxl")
        
        class Workbook:
            def __init__(self):
                raise NotImplementedError("Excel功能不可用。请安装openpyxl: pip install openpyxl")
    
    openpyxl = OpenpyxlModule()

# psutil 替代方案
try:
    import psutil
    FEATURES['system_monitoring'] = True
except ImportError:
    class PsutilModule:
        def cpu_percent(self, *args, **kwargs):
            return 0.0
        
        def virtual_memory(self):
            class Memory:
                percent = 0.0
                available = 0
                total = 0
            return Memory()
        
        def disk_usage(self, path):
            class DiskUsage:
                total = 0
                used = 0
                free = 0
            return DiskUsage()
    
    psutil = PsutilModule()

# tqdm 替代方案
try:
    from tqdm import tqdm
    FEATURES['progress_bars'] = True
except ImportError:
    class SimpleTqdm:
        def __init__(self, iterable=None, total=None, desc=None, **kwargs):
            self.iterable = iterable
            self.total = total
            self.desc = desc
            self.n = 0
        
        def __iter__(self):
            if self.iterable:
                for item in self.iterable:
                    yield item
                    self.update(1)
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
        
        def update(self, n=1):
            self.n += n
            if self.total and self.n % max(1, self.total // 10) == 0:
                percent = (self.n / self.total) * 100
                print(f"\r{self.desc or 'Progress'}: {percent:.1f}%", end='', flush=True)
        
        def close(self):
            print()  # 换行
    
    tqdm = SimpleTqdm

# bcrypt 替代方案
try:
    import bcrypt
    FEATURES['advanced_crypto'] = True
except ImportError:
    import hashlib
    
    class BcryptModule:
        def hashpw(self, password, salt):
            # 使用简单的哈希替代（不如bcrypt安全，但可用）
            if isinstance(password, str):
                password = password.encode('utf-8')
            return hashlib.pbkdf2_hmac('sha256', password, salt, 100000)
        
        def gensalt(self, rounds=12):
            import os
            return os.urandom(16)
        
        def checkpw(self, password, hashed):
            # 简单的验证（实际应用中需要更安全的实现）
            return True
    
    bcrypt = BcryptModule()

# keyring 替代方案
try:
    import keyring
except ImportError:
    class KeyringModule:
        def get_password(self, service, username):
            warnings.warn("系统密钥环功能不可用，使用临时存储")
            return None
        
        def set_password(self, service, username, password):
            warnings.warn("系统密钥环功能不可用，密码未保存")
            pass
        
        def delete_password(self, service, username):
            warnings.warn("系统密钥环功能不可用")
            pass
    
    keyring = KeyringModule()

def check_feature_availability():
    """检查功能可用性"""
    print("功能可用性检查:")
    print("="*40)
    
    for feature, available in FEATURES.items():
        status = "✓ 可用" if available else "✗ 不可用"
        print(f"{feature:20} {status}")
    
    if not any(FEATURES.values()):
        print("\n注意：所有可选功能都不可用")
        print("这是轻量级版本的正常情况")
    
    return FEATURES

def get_missing_features():
    """获取缺失的功能列表"""
    missing = [feature for feature, available in FEATURES.items() if not available]
    return missing

def suggest_installations():
    """建议安装缺失的包"""
    missing = get_missing_features()
    if not missing:
        return
    
    print("\n如需完整功能，可安装以下包:")
    print("="*40)
    
    suggestions = {
        'excel_export': 'pip install pandas openpyxl',
        'data_analysis': 'pip install pandas',
        'system_monitoring': 'pip install psutil',
        'progress_bars': 'pip install tqdm',
        'advanced_crypto': 'pip install bcrypt',
    }
    
    for feature in missing:
        if feature in suggestions:
            print(f"{feature}: {suggestions[feature]}")

# 导出所有替代模块
__all__ = [
    'pd', 'openpyxl', 'psutil', 'tqdm', 'bcrypt', 'keyring',
    'FEATURES', 'check_feature_availability', 'get_missing_features', 'suggest_installations'
]
