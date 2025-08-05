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
except:
    pass

# 添加模板文件
if os.path.exists('templates'):
    datas += [('templates', 'templates')]

# 添加配置文件
if os.path.exists('config'):
    datas += [('config', 'config')]

# 添加资源文件
if os.path.exists('assets'):
    datas += [('assets', 'assets')]

# 添加便携模式配置文件（可选）
if os.path.exists('portable.txt'):
    datas += [('portable.txt', '.')]

# 添加数据库相关文件
if os.path.exists('docs'):
    datas += [('docs', 'docs')]

# 添加数据库初始化脚本
if os.path.exists('scripts'):
    datas += [('scripts', 'scripts')]

# 添加数据库迁移脚本
migration_files = []
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('_migration.sql') or file.endswith('_migration.py'):
            migration_files.append((os.path.join(root, file), os.path.dirname(file)))
datas += migration_files

# 收集隐藏导入
hiddenimports = [
    # PyQt5 核心模块
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui', 
    'PyQt5.QtWidgets',
    'PyQt5.QtNetwork',
    'PyQt5.sip',
    'sip',
    'requests',
    'json',
    'yaml',
    'jsonschema',
    'swagger_parser',
    'faker',
    'dateutil',
    'urllib3',
    # 数据库相关模块
    'sqlite3',
    'threading',
    'queue',
    'hashlib',
    'base64',
    'secrets',
    'psutil',
    'chardet',
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
    # 可选的数据处理模块
    'pandas',
    'openpyxl',
    # 测试相关（开发环境）
    'unittest',
    'unittest.mock',
    'coverage'
]

# 收集所有子模块
hiddenimports += collect_submodules('core')
hiddenimports += collect_submodules('gui')
hiddenimports += collect_submodules('utils')

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
    excludes=[],
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
    console=False,  # 设置为False隐藏控制台窗口
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