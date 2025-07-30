#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Swagger API测试工具主程序
"""

import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow


def main():
    """程序入口点"""
    app = QApplication(sys.argv)
    app.setApplicationName("Swagger API测试工具")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
