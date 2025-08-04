# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from PyInstaller.utils.hooks import collect_all, copy_metadata

# 收集数据文件
datas = []

# 收集PyQt5相关数据
try:
    pyqt5_datas, pyqt5_binaries, pyqt5_hiddenimports = collect_all('PyQt5')
    datas += pyqt5_datas
    print(f"SUCCESS: Collected {len(pyqt5_datas)} PyQt5 data files")
except Exception as e:
    print(f"WARNING: Cannot collect PyQt5 data files: {e}")
    pyqt5_datas, pyqt5_binaries, pyqt5_hiddenimports = [], [], []

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
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.QtNetwork',
    'PyQt5.sip',
    'sip',
    # 应用依赖
    'requests',
    'json',
    'yaml',
    'jsonschema',
    'swagger_parser',
    'faker',
    'dateutil',
    'urllib3',
    'sqlite3',
    'threading',
    'queue',
    'hashlib',
    'base64',
    'secrets',
    'chardet',
    'psutil',
    'tqdm',
    'bcrypt',
    'keyring',
    # 加密相关
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.kdf',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
    'cryptography.hazmat.primitives.hashes',
    'cryptography.hazmat.backends',
    'cryptography.hazmat.backends.openssl',
]

# 收集所有子模块
hiddenimports += collect_submodules('core')
hiddenimports += collect_submodules('gui')
hiddenimports += collect_submodules('utils')

# 添加从 collect_all 获取的 PyQt5 隐藏导入
try:
    hiddenimports += pyqt5_hiddenimports
    print(f"SUCCESS: Added {len(pyqt5_hiddenimports)} PyQt5 hidden imports")
except Exception as e:
    print(f"WARNING: Cannot add PyQt5 hidden imports: {e}")

block_cipher = None

# 收集二进制文件
binaries = []
try:
    binaries += pyqt5_binaries
    print(f"SUCCESS: Added {len(pyqt5_binaries)} PyQt5 binary files")
except Exception as e:
    print(f"WARNING: Cannot add PyQt5 binary files: {e}")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的包（但保留必要的依赖）
        'torch',
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
