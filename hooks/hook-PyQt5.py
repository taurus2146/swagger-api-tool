# -*- coding: utf-8 -*-
"""
PyInstaller hook for PyQt5
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# 收集所有PyQt5模块
datas, binaries, hiddenimports = collect_all('PyQt5')

# 添加额外的隐藏导入
hiddenimports += [
    'PyQt5.sip',
    'sip',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.QtNetwork',
]

# 收集PyQt5子模块
hiddenimports += collect_submodules('PyQt5')
