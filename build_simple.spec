# -*- mode: python ; coding: utf-8 -*-

import os

# 收集数据文件
datas = []

# 添加模板文件
if os.path.exists('templates'):
    datas += [('templates', 'templates')]

# 添加配置文件
if os.path.exists('config'):
    datas += [('config', 'config')]

# 添加资源文件
if os.path.exists('assets'):
    datas += [('assets', 'assets')]

# 收集必要的隐藏导入
hiddenimports = [
    # PyQt5 核心模块
    'PyQt5.QtCore',
    'PyQt5.QtGui', 
    'PyQt5.QtWidgets',
    'PyQt5.QtNetwork',
    # 应用依赖
    'requests',
    'json',
    'yaml',
    'sqlite3',
    'threading',
    'queue',
    'hashlib',
    'base64',
    'secrets',
    'chardet',
    'urllib3',
]

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
        # 排除不需要的包
        'torch',
        'numpy',
        'pandas',
        'matplotlib',
        'scipy',
        'transformers',
        'tensorboard', 
        'sklearn',
        'IPython',
        'jupyter',
        'notebook',
        'sympy',
        'cv2',
        'PIL',
        'tkinter',
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
    [],
    exclude_binaries=True,
    name='SwaggerAPITester',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SwaggerAPITester',
)
