# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 快速启动版本：优化启动速度，禁用压缩

# 收集数据文件（最小化）
datas = []

# 只添加必要的资源文件
if os.path.exists('config'):
    datas += [('config', 'config')]

if os.path.exists('templates'):
    datas += [('templates', 'templates')]

# 只添加必要的图标文件
if os.path.exists('assets/icon.ico'):
    datas += [('assets/icon.ico', 'assets')]
if os.path.exists('assets/app_icon.png'):
    datas += [('assets/app_icon.png', 'assets')]

# 精简的隐藏导入列表
hiddenimports = [
    # PyQt5 核心模块
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.QtNetwork',
    'PyQt5.QtSvg',
    
    # 应用核心依赖
    'requests',
    'json',
    'yaml',
    'jsonschema',
    'swagger_parser',
    'faker',
    'dateutil',
    'urllib3',
    'chardet',
    
    # Python标准库
    'sqlite3',
    'threading',
    'queue',
    'hashlib',
    'base64',
    'secrets',
    
    # 加密功能（精简）
    'cryptography.fernet',
    'cryptography.hazmat.primitives.hashes',
    'cryptography.hazmat.backends.openssl',
]

# 收集应用子模块
try:
    hiddenimports += collect_submodules('core')
    hiddenimports += collect_submodules('gui')
    hiddenimports += collect_submodules('utils')
except:
    pass

# 添加特定的GUI模块
gui_modules = [
    'gui.database_location_manager',
    'gui.async_operations_dialog',
    'gui.icon_generator',
    'gui.main_window',
    'gui.api_list_widget',
    'gui.api_param_editor',
    'gui.test_result_widget',
    'gui.auth_config_dialog_login',
    'gui.project_selector_dialog',
    'gui.project_edit_dialog',
    'gui.styles',
    'gui.api_test_thread',
    'gui.theme_manager',
]

hiddenimports.extend(gui_modules)

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 大型库排除列表
        'torch',
        'tensorflow',
        'numpy',
        'pandas',
        'matplotlib',
        'scipy',
        'sklearn',
        'transformers',
        'tensorboard',
        'IPython',
        'jupyter',
        'notebook',
        'sympy',
        'cv2',
        'PIL',
        'tkinter',
        
        # 测试工具
        'pytest',
        'coverage',
        'mock',
        'unittest',
        
        # 系统工具
        'psutil',
        'keyring',
        'bcrypt',
        'tqdm',
        
        # 开发工具
        'setuptools',
        'pip',
        'wheel',
        'distutils',
        
        # 文档工具
        'sphinx',
        'docutils',
        
        # 不需要的PyQt5模块
        'PyQt5.QtWebEngine',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtWebKit',
        'PyQt5.QtWebKitWidgets',
        'PyQt5.QtQuick',
        'PyQt5.QtQml',
        'PyQt5.QtMultimedia',
        'PyQt5.QtMultimediaWidgets',
        'PyQt5.QtOpenGL',
        'PyQt5.QtSql',
        'PyQt5.QtXml',
        'PyQt5.QtXmlPatterns',
        'PyQt5.QtDesigner',
        'PyQt5.QtHelp',
        'PyQt5.QtTest',
        'PyQt5.QtBluetooth',
        'PyQt5.QtNfc',
        'PyQt5.QtPositioning',
        'PyQt5.QtLocation',
        'PyQt5.QtSensors',
        'PyQt5.QtSerialPort',
        'PyQt5.QtWebChannel',
        'PyQt5.QtWebSockets',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SwaggerAPITester-Fast',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # 禁用strip以加快启动
    upx=False,    # 禁用UPX压缩以加快启动
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',  # 确保使用正确的图标
)
