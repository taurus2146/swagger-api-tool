#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
构建exe文件的脚本
"""

import os
import sys
import subprocess
import shutil

def build_exe():
    """构建exe文件"""
    
    # 清理之前的构建文件
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # PyInstaller命令
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name=SwaggerAPITester',
        '--icon=assets/icon.ico',
        '--add-data=assets;assets',
        '--add-data=config;config',
        
        # 强制包含所有必要模块
        '--collect-all=PyQt5',
        '--collect-all=requests',
        '--collect-all=PyYAML',
        '--collect-all=jsonschema',
        '--collect-all=swagger_parser',
        '--collect-all=python_dateutil',
        '--collect-all=urllib3',
        '--collect-all=faker',
        '--collect-all=cryptography',
        
        # 隐藏导入
        '--hidden-import=yaml',
        '--hidden-import=PyYAML',
        '--hidden-import=yaml.loader',
        '--hidden-import=yaml.dumper',
        '--hidden-import=yaml.constructor',
        '--hidden-import=yaml.representer',
        '--hidden-import=yaml.resolver',
        '--hidden-import=yaml.scanner',
        '--hidden-import=yaml.parser',
        '--hidden-import=yaml.composer',
        '--hidden-import=yaml.emitter',
        '--hidden-import=yaml.serializer',
        '--hidden-import=PyQt5.sip',
        '--hidden-import=sip',
        '--hidden-import=requests.packages',
        '--hidden-import=requests.packages.urllib3',
        '--hidden-import=requests.packages.urllib3.util',
        '--hidden-import=requests.packages.urllib3.util.retry',
        '--hidden-import=jsonschema.validators',
        '--hidden-import=jsonschema.exceptions',
        '--hidden-import=sqlite3',
        '--hidden-import=logging',
        '--hidden-import=threading',
        '--hidden-import=datetime',
        '--hidden-import=json',
        '--hidden-import=base64',
        '--hidden-import=hashlib',
        '--hidden-import=uuid',
        '--hidden-import=pathlib',
        '--hidden-import=functools',
        '--hidden-import=collections',
        '--hidden-import=itertools',
        '--hidden-import=copy',
        '--hidden-import=re',
        '--hidden-import=traceback',
        
        # 项目模块
        '--hidden-import=gui',
        '--hidden-import=gui.main_window',
        '--hidden-import=gui.api_param_editor',
        '--hidden-import=gui.auth_config_dialog',
        '--hidden-import=gui.auth_config_dialog_login',
        '--hidden-import=core',
        '--hidden-import=core.auth_manager',
        '--hidden-import=core.data_generator',
        '--hidden-import=core.swagger_parser',
        '--hidden-import=core.http_client',
        '--hidden-import=core.project_manager',
        '--hidden-import=core.database_manager',
        '--hidden-import=utils',
        '--hidden-import=utils.logger',
        '--hidden-import=version',
        
        'main.py'
    ]
    
    print("开始构建exe文件...")
    print("命令:", ' '.join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("构建成功!")
        print("输出:", result.stdout)
        
        # 检查生成的文件
        exe_path = os.path.join('dist', 'SwaggerAPITester.exe')
        if os.path.exists(exe_path):
            size = os.path.getsize(exe_path)
            print(f"生成的exe文件: {exe_path}")
            print(f"文件大小: {size / 1024 / 1024:.2f} MB")
        else:
            print("警告: 未找到生成的exe文件")
            
    except subprocess.CalledProcessError as e:
        print("构建失败!")
        print("错误:", e.stderr)
        sys.exit(1)

if __name__ == '__main__':
    build_exe()
