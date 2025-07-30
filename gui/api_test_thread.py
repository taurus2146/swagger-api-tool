#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API测试线程模块 - 异步执行API测试
"""

from PyQt5.QtCore import QThread, pyqtSignal

class ApiTestThread(QThread):
    """
    API测试线程，用于异步执行API测试
    """
    
    # 定义信号
    test_completed = pyqtSignal(dict)  # 测试完成信号，传递测试结果
    test_error = pyqtSignal(str)  # 测试错误信号，传递错误信息
    
    def __init__(self, api_tester, parent=None):
        """
        初始化测试线程
        
        Args:
            api_tester: API测试器实例
            parent: 父对象
        """
        super().__init__(parent)
        self.api_tester = api_tester
        self.api_info = None
        self.custom_data = None
        self.use_auth = True
        self.auth_type = "bearer"
        
    def set_test_params(self, api_info, custom_data=None, use_auth=True, auth_type="bearer"):
        """
        设置测试参数
        
        Args:
            api_info: API信息
            custom_data: 自定义数据
            use_auth: 是否使用认证
            auth_type: 认证类型
        """
        self.api_info = api_info
        self.custom_data = custom_data
        self.use_auth = use_auth
        self.auth_type = auth_type
        
    def run(self):
        """
        线程执行函数
        """
        try:
            if not self.api_info:
                self.test_error.emit("API信息为空")
                return
                
            # 执行API测试
            result = self.api_tester.test_api(
                self.api_info, 
                self.custom_data, 
                self.use_auth, 
                self.auth_type
            )
            
            # 发送完成信号
            self.test_completed.emit(result)
            
        except Exception as e:
            # 发送错误信号
            self.test_error.emit(str(e))
