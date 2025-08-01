#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
版本信息
"""

__version__ = "1.0.0"
__app_name__ = "Swagger API测试工具"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__description__ = "一个基于 PyQt5 的图形化 Swagger API 测试工具"
__url__ = "https://github.com/taurus2146/swagger-api-tool"

# 构建信息
BUILD_DATE = "2025-08-01"
BUILD_COMMIT = "自动构建"

def get_version_info():
    """获取版本信息字符串"""
    return f"{__app_name__} v{__version__}"

def get_full_version_info():
    """获取完整版本信息"""
    return {
        "name": __app_name__,
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "description": __description__,
        "url": __url__,
        "build_date": BUILD_DATE,
        "build_commit": BUILD_COMMIT
    }