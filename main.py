#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Swagger API测试工具主程序
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
from version import __app_name__, __version__


def main():
    """程序入口点"""
    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    
    # 设置应用图标（如果存在）
    icon_path = os.path.join("assets", "icon.ico")
    if os.path.exists(icon_path):
        from PyQt5.QtGui import QIcon
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
