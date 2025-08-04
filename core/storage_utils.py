#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
存储路径工具
为打包后的应用提供合适的数据存储位置
"""

import os
import sys
import platform
from pathlib import Path


def get_app_data_dir() -> str:
    """
    获取应用数据存储目录
    根据不同操作系统返回合适的用户数据目录
    """
    app_name = "SwaggerAPITester"
    
    system = platform.system()
    
    if system == "Windows":
        # Windows: %APPDATA%\SwaggerAPITester
        base_dir = os.environ.get('APPDATA', os.path.expanduser('~'))
        return os.path.join(base_dir, app_name)
    
    elif system == "Darwin":  # macOS
        # macOS: ~/Library/Application Support/SwaggerAPITester
        base_dir = os.path.expanduser('~/Library/Application Support')
        return os.path.join(base_dir, app_name)
    
    else:  # Linux and others
        # Linux: ~/.local/share/SwaggerAPITester or ~/.SwaggerAPITester
        xdg_data_home = os.environ.get('XDG_DATA_HOME')
        if xdg_data_home:
            return os.path.join(xdg_data_home, app_name)
        else:
            # Fallback to ~/.local/share/SwaggerAPITester
            base_dir = os.path.expanduser('~/.local/share')
            return os.path.join(base_dir, app_name)


def get_portable_data_dir() -> str:
    """
    获取便携式数据目录（exe文件同目录下）
    用于便携式部署
    """
    if getattr(sys, 'frozen', False):
        # 打包后的exe文件
        exe_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境
        exe_dir = os.path.dirname(os.path.abspath(__file__))
        exe_dir = os.path.dirname(exe_dir)  # 回到项目根目录
    
    return os.path.join(exe_dir, "data")


def get_storage_path(portable: bool = False) -> str:
    """
    获取存储路径
    
    Args:
        portable: 是否使用便携式模式
        
    Returns:
        存储路径
    """
    if portable:
        return get_portable_data_dir()
    else:
        return get_app_data_dir()


def is_portable_mode() -> bool:
    """
    检测是否应该使用便携式模式
    如果exe文件目录下存在 'portable.txt' 文件，则使用便携式模式
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        portable_flag = os.path.join(exe_dir, 'portable.txt')
        return os.path.exists(portable_flag)
    
    # 开发环境默认不使用便携式模式
    return False


def ensure_storage_dir(storage_path: str) -> bool:
    """
    确保存储目录存在
    
    Args:
        storage_path: 存储路径
        
    Returns:
        是否成功创建或已存在
    """
    try:
        os.makedirs(storage_path, exist_ok=True)
        return True
    except OSError as e:
        print(f"Failed to create storage directory {storage_path}: {e}")
        return False


def get_default_storage_path() -> str:
    """
    获取默认存储路径
    自动检测是否使用便携式模式
    """
    portable = is_portable_mode()
    storage_path = get_storage_path(portable)
    
    # 确保目录存在
    if ensure_storage_dir(storage_path):
        return storage_path
    else:
        # 如果创建失败，回退到便携式模式
        fallback_path = get_portable_data_dir()
        ensure_storage_dir(fallback_path)
        return fallback_path


def get_default_database_path() -> str:
    """
    获取默认数据库文件路径
    
    Returns:
        str: 数据库文件的完整路径
    """
    storage_dir = get_default_storage_path()
    return os.path.join(storage_dir, "database.db")


def get_storage_info() -> dict:
    """
    获取存储信息，用于调试和用户了解
    """
    portable = is_portable_mode()
    current_path = get_default_storage_path()
    database_path = get_default_database_path()
    
    return {
        "portable_mode": portable,
        "storage_path": current_path,
        "database_path": database_path,
        "app_data_path": get_app_data_dir(),
        "portable_path": get_portable_data_dir(),
        "is_frozen": getattr(sys, 'frozen', False),
        "executable_path": sys.executable if getattr(sys, 'frozen', False) else __file__
    }