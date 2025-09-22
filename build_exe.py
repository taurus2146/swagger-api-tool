#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Build script for exe file
"""

import os
import sys
import subprocess
import shutil

def build_exe():
    """Build exe file"""

    # Clean previous build files
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name=SwaggerAPITester',
        '--icon=assets/icon.ico',
        '--add-data=assets;assets',
        '--add-data=config;config',
        '--additional-hooks-dir=.',
        
        # Force include all necessary modules
        '--collect-all=PyQt5',
        '--collect-all=requests',
        '--collect-all=PyYAML',
        '--collect-all=yaml',
        '--collect-all=jsonschema',
        '--collect-all=swagger_parser',
        '--collect-all=python_dateutil',
        '--collect-all=urllib3',
        '--collect-all=faker',
        '--collect-all=cryptography',
        '--collect-submodules=PyYAML',
        '--collect-submodules=yaml',
        
        # Hidden imports
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
        
        # Project modules
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
    
    print("Starting to build exe file...")
    print("Command:", ' '.join(cmd))

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build successful!")
        print("Output:", result.stdout)

        # Check generated file
        exe_path = os.path.join('dist', 'SwaggerAPITester.exe')
        if os.path.exists(exe_path):
            size = os.path.getsize(exe_path)
            print(f"Generated exe file: {exe_path}")
            print(f"File size: {size / 1024 / 1024:.2f} MB")
        else:
            print("Warning: Generated exe file not found")

    except subprocess.CalledProcessError as e:
        print("Build failed!")
        print("Error:", e.stderr)
        sys.exit(1)

if __name__ == '__main__':
    build_exe()
