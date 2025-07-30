#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试主题功能
"""

import sys
from PyQt5.QtWidgets import QApplication
from gui.theme_preview_dialog import ThemePreviewDialog
from gui.theme_manager import theme_manager


def test_themes():
    """测试主题功能"""
    app = QApplication(sys.argv)
    
    print("可用主题:")
    for theme_name in theme_manager.get_theme_names():
        display_name = theme_manager.get_theme_display_name(theme_name)
        print(f"  {theme_name}: {display_name}")
    
    print(f"\n当前主题: {theme_manager.get_current_theme_name()}")
    
    # 显示主题预览对话框
    dialog = ThemePreviewDialog()
    dialog.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    test_themes()