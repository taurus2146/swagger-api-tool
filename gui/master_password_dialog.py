#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主密码管理对话框
提供主密码设置、验证、修改和重置的图形界面
"""
import sys
import os
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar,
    QGroupBox, QCheckBox, QComboBox, QTabWidget, QWidget,
    QMessageBox, QFrame, QScrollArea, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.master_password_manager import MasterPasswordManager, PasswordStrength

class PasswordStrengthWidget(QWidget):
    """密码强度显示组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 强度标签
        self.strength_label = QLabel("密码强度: 未设置")
        self.strength_label.setFont(QFont("Arial", 9, QFont.Bold))
        layout.addWidget(self.strength_label)
        
        # 强度进度条
        self.strength_bar = QProgressBar()
        self.strength_bar.setRange(0, 100)
        self.strength_bar.setValue(0)
        self.strength_bar.setTextVisible(False)
        self.strength_bar.setFixedHeight(8)
        layout.addWidget(self.strength_bar)
        
        # 问题和建议显示
        self.feedback_text = QTextEdit()
        self.feedback_text.setMaximumHeight(80)
        self.feedback_text.setReadOnly(True)
        self.feedback_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f9f9f9;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.feedback_text)
    
    def update_strength(self, validation_result):
        """更新密码强度显示"""
        if validation_result is None:
            self.strength_label.setText("密码强度: 未设置")
            self.strength_bar.setValue(0)
            self.strength_bar.setStyleSheet("")
            self.feedback_text.clear()
            return
        
        # 更新强度标签和进度条
        strength_name = validation_result.strength.name.replace('_', ' ').title()
        self.strength_label.setText(f"密码强度: {strength_name} ({validation_result.score}/100)")
        self.strength_bar.setValue(validation_result.score)
        
        # 设置进度条颜色
        if validation_result.strength == PasswordStrength.VERY_WEAK:
            color = "#ff4444"
        elif validation_result.strength == PasswordStrength.WEAK:
            color = "#ff8800"
        elif validation_result.strength == PasswordStrength.MEDIUM:
            color = "#ffaa00"
        elif validation_result.strength == PasswordStrength.STRONG:
            color = "#88cc00"
        else:  # VERY_STRONG
            color = "#00cc44"
        
        self.strength_bar.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)
        
        # 更新反馈信息
        feedback_text = ""
        if validation_result.issues:
            feedback_text += "问题:\n" + "\n".join(f"• {issue}" for issue in validation_result.issues)
        
        if validation_result.suggestions:
            if feedback_text:
                feedback_text += "\n\n"
            feedback_text += "建议:\n" + "\n".join(f"• {suggestion}" for suggestion in validation_result.suggestions)
        
        self.feedback_text.setPlainText(feedback_text)

class MasterPasswordSetupDialog(QDialog):
    """主密码设置对话框"""
    
    def __init__(self, manager: MasterPasswordManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("设置主密码")
        self.setFixedSize(500, 600)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("设置主密码")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 说明文本
        info_label = QLabel(
            "主密码用于保护您的敏感数据。请设置一个强密码并妥善保管。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin: 10px 0;")
        layout.addWidget(info_label)
        
        # 密码输入组
        password_group = QGroupBox("密码设置")
        password_layout = QGridLayout(password_group)
        
        # 密码输入
        password_layout.addWidget(QLabel("密码:"), 0, 0)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("请输入主密码")
        password_layout.addWidget(self.password_edit, 0, 1)
        
        # 显示密码复选框
        self.show_password_cb = QCheckBox("显示密码")
        password_layout.addWidget(self.show_password_cb, 0, 2)
        
        # 确认密码
        password_layout.addWidget(QLabel("确认密码:"), 1, 0)
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.Password)
        self.confirm_password_edit.setPlaceholderText("请再次输入密码")
        password_layout.addWidget(self.confirm_password_edit, 1, 1, 1, 2)
        
        # 密码提示
        password_layout.addWidget(QLabel("密码提示:"), 2, 0)
        self.hint_edit = QLineEdit()
        self.hint_edit.setPlaceholderText("可选：输入密码提示（不要包含密码本身）")
        password_layout.addWidget(self.hint_edit, 2, 1, 1, 2)
        
        layout.addWidget(password_group)
        
        # 密码强度显示
        strength_group = QGroupBox("密码强度")
        strength_layout = QVBoxLayout(strength_group)
        
        self.strength_widget = PasswordStrengthWidget()
        strength_layout.addWidget(self.strength_widget)
        
        layout.addWidget(strength_group)
        
        # 密码生成器
        generator_group = QGroupBox("密码生成器")
        generator_layout = QHBoxLayout(generator_group)
        
        generator_layout.addWidget(QLabel("长度:"))
        self.length_combo = QComboBox()
        self.length_combo.addItems(["12", "16", "20", "24"])
        self.length_combo.setCurrentText("16")
        generator_layout.addWidget(self.length_combo)
        
        self.generate_btn = QPushButton("生成密码")
        generator_layout.addWidget(self.generate_btn)
        
        generator_layout.addStretch()
        
        layout.addWidget(generator_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("取消")
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setDefault(True)
        self.ok_btn.setEnabled(False)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
    
    def setup_connections(self):
        """设置信号连接"""
        self.password_edit.textChanged.connect(self.on_password_changed)
        self.confirm_password_edit.textChanged.connect(self.on_password_changed)
        self.show_password_cb.toggled.connect(self.on_show_password_toggled)
        self.generate_btn.clicked.connect(self.on_generate_password)
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.on_ok_clicked)
    
    def on_password_changed(self):
        """密码输入变化时的处理"""
        password = self.password_edit.text()
        confirm_password = self.confirm_password_edit.text()
        
        # 更新密码强度
        if password:
            validation = self.manager.validate_password_strength(password)
            self.strength_widget.update_strength(validation)
            
            # 检查密码是否匹配
            passwords_match = password == confirm_password if confirm_password else True
            is_valid = validation.is_valid and passwords_match
            
            self.ok_btn.setEnabled(is_valid and len(confirm_password) > 0)
        else:
            self.strength_widget.update_strength(None)
            self.ok_btn.setEnabled(False)
    
    def on_show_password_toggled(self, checked):
        """切换密码显示状态"""
        echo_mode = QLineEdit.Normal if checked else QLineEdit.Password
        self.password_edit.setEchoMode(echo_mode)
        self.confirm_password_edit.setEchoMode(echo_mode)
    
    def on_generate_password(self):
        """生成密码"""
        length = int(self.length_combo.currentText())
        password = self.manager.generate_password_suggestion(length)
        self.password_edit.setText(password)
        self.confirm_password_edit.setText(password)
    
    def on_ok_clicked(self):
        """确定按钮点击处理"""
        password = self.password_edit.text()
        confirm_password = self.confirm_password_edit.text()
        hint = self.hint_edit.text().strip() or None
        
        # 验证密码匹配
        if password != confirm_password:
            QMessageBox.warning(self, "错误", "两次输入的密码不匹配！")
            return
        
        # 设置主密码
        if self.manager.set_master_password(password, hint):
            QMessageBox.information(self, "成功", "主密码设置成功！")
            self.accept()
        else:
            QMessageBox.critical(self, "错误", "主密码设置失败！")

class MasterPasswordVerifyDialog(QDialog):
    """主密码验证对话框"""
    
    def __init__(self, manager: MasterPasswordManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setup_ui()
        self.setup_connections()
        self.load_account_status()
    
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("验证主密码")
        self.setFixedSize(400, 300)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("请输入主密码")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 账户状态
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666; margin: 10px 0;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 密码输入
        password_group = QGroupBox("密码验证")
        password_layout = QGridLayout(password_group)
        
        password_layout.addWidget(QLabel("密码:"), 0, 0)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("请输入主密码")
        password_layout.addWidget(self.password_edit, 0, 1)
        
        # 显示密码
        self.show_password_cb = QCheckBox("显示密码")
        password_layout.addWidget(self.show_password_cb, 1, 0, 1, 2)
        
        layout.addWidget(password_group)
        
        # 密码提示
        hint = self.manager.get_password_hint()
        if hint:
            hint_group = QGroupBox("密码提示")
            hint_layout = QVBoxLayout(hint_group)
            
            hint_label = QLabel(hint)
            hint_label.setWordWrap(True)
            hint_label.setStyleSheet("font-style: italic; color: #666;")
            hint_layout.addWidget(hint_label)
            
            layout.addWidget(hint_group)
        
        # 忘记密码链接
        self.forgot_password_btn = QPushButton("忘记密码？")
        self.forgot_password_btn.setStyleSheet("""
            QPushButton {
                border: none;
                color: #0066cc;
                text-decoration: underline;
                text-align: left;
            }
            QPushButton:hover {
                color: #0052a3;
            }
        """)
        layout.addWidget(self.forgot_password_btn)
        
        layout.addStretch()
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("取消")
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setDefault(True)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
    
    def setup_connections(self):
        """设置信号连接"""
        self.password_edit.textChanged.connect(self.on_password_changed)
        self.show_password_cb.toggled.connect(self.on_show_password_toggled)
        self.forgot_password_btn.clicked.connect(self.on_forgot_password)
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.on_ok_clicked)
        
        # 回车键验证
        self.password_edit.returnPressed.connect(self.on_ok_clicked)
    
    def load_account_status(self):
        """加载账户状态"""
        status = self.manager.get_account_status()
        
        if status['is_locked']:
            self.status_label.setText("账户已被锁定，请稍后再试")
            self.status_label.setStyleSheet("color: red; margin: 10px 0;")
            self.password_edit.setEnabled(False)
            self.ok_btn.setEnabled(False)
        elif status['failed_attempts'] > 0:
            remaining = status['max_attempts'] - status['failed_attempts']
            self.status_label.setText(f"密码错误 {status['failed_attempts']} 次，还有 {remaining} 次机会")
            self.status_label.setStyleSheet("color: orange; margin: 10px 0;")
        else:
            self.status_label.setText("请输入您的主密码以继续")
    
    def on_password_changed(self):
        """密码输入变化处理"""
        self.ok_btn.setEnabled(len(self.password_edit.text()) > 0)
    
    def on_show_password_toggled(self, checked):
        """切换密码显示状态"""
        echo_mode = QLineEdit.Normal if checked else QLineEdit.Password
        self.password_edit.setEchoMode(echo_mode)
    
    def on_forgot_password(self):
        """忘记密码处理"""
        # 检查是否有安全问题
        security_questions = self.manager.get_security_questions()
        
        if not security_questions:
            QMessageBox.information(
                self, "提示", 
                "您尚未设置安全问题。\n请联系管理员或重新安装应用程序。"
            )
            return
        
        # 打开密码重置对话框
        dialog = PasswordResetDialog(self.manager, self)
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "成功", "密码重置成功！请使用新密码登录。")
            self.reject()  # 关闭当前对话框
    
    def on_ok_clicked(self):
        """确定按钮点击处理"""
        password = self.password_edit.text()
        
        if self.manager.verify_master_password(password):
            self.accept()
        else:
            # 重新加载状态以显示最新的失败次数
            self.load_account_status()
            QMessageBox.warning(self, "错误", "密码错误！")
            self.password_edit.clear()
            self.password_edit.setFocus()

class SecurityQuestionDialog(QDialog):
    """安全问题设置对话框"""
    
    def __init__(self, manager: MasterPasswordManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("设置安全问题")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("设置安全问题")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 说明
        info_label = QLabel(
            "安全问题用于在忘记密码时重置密码。请设置至少一个安全问题。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin: 10px 0;")
        layout.addWidget(info_label)
        
        # 安全问题输入
        questions_group = QGroupBox("安全问题")
        questions_layout = QGridLayout(questions_group)
        
        questions_layout.addWidget(QLabel("问题:"), 0, 0)
        self.question_edit = QLineEdit()
        self.question_edit.setPlaceholderText("例如：您的第一只宠物叫什么名字？")
        questions_layout.addWidget(self.question_edit, 0, 1)
        
        questions_layout.addWidget(QLabel("答案:"), 1, 0)
        self.answer_edit = QLineEdit()
        self.answer_edit.setPlaceholderText("请输入答案")
        questions_layout.addWidget(self.answer_edit, 1, 1)
        
        # 添加按钮
        self.add_btn = QPushButton("添加问题")
        questions_layout.addWidget(self.add_btn, 2, 1)
        
        layout.addWidget(questions_group)
        
        # 已有问题列表
        existing_group = QGroupBox("已设置的安全问题")
        existing_layout = QVBoxLayout(existing_group)
        
        self.questions_list = QTextEdit()
        self.questions_list.setReadOnly(True)
        self.questions_list.setMaximumHeight(150)
        existing_layout.addWidget(self.questions_list)
        
        layout.addWidget(existing_group)
        
        # 更新问题列表
        self.update_questions_list()
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.close_btn = QPushButton("关闭")
        
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def setup_connections(self):
        """设置信号连接"""
        self.add_btn.clicked.connect(self.on_add_question)
        self.close_btn.clicked.connect(self.accept)
    
    def update_questions_list(self):
        """更新问题列表显示"""
        questions = self.manager.get_security_questions()
        
        if not questions:
            self.questions_list.setPlainText("尚未设置安全问题")
        else:
            text = ""
            for i, q in enumerate(questions, 1):
                text += f"{i}. {q['question']}\n"
            self.questions_list.setPlainText(text)
    
    def on_add_question(self):
        """添加安全问题"""
        question = self.question_edit.text().strip()
        answer = self.answer_edit.text().strip()
        
        if not question or not answer:
            QMessageBox.warning(self, "错误", "请输入问题和答案！")
            return
        
        if self.manager.add_security_question(question, answer):
            QMessageBox.information(self, "成功", "安全问题添加成功！")
            self.question_edit.clear()
            self.answer_edit.clear()
            self.update_questions_list()
        else:
            QMessageBox.critical(self, "错误", "添加安全问题失败！")

class PasswordResetDialog(QDialog):
    """密码重置对话框"""
    
    def __init__(self, manager: MasterPasswordManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.security_questions = manager.get_security_questions()
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("重置密码")
        self.setFixedSize(600, 500)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("通过安全问题重置密码")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 说明
        required_count = max(1, len(self.security_questions) // 2)
        info_label = QLabel(
            f"请回答以下安全问题（至少需要回答 {required_count} 个问题）："
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin: 10px 0;")
        layout.addWidget(info_label)
        
        # 安全问题
        questions_group = QGroupBox("安全问题")
        questions_layout = QVBoxLayout(questions_group)
        
        self.answer_edits = {}
        for q in self.security_questions:
            question_widget = QWidget()
            question_layout = QVBoxLayout(question_widget)
            question_layout.setContentsMargins(0, 5, 0, 5)
            
            # 问题标签
            question_label = QLabel(f"问题 {q['index'] + 1}: {q['question']}")
            question_label.setWordWrap(True)
            question_layout.addWidget(question_label)
            
            # 答案输入
            answer_edit = QLineEdit()
            answer_edit.setPlaceholderText("请输入答案")
            question_layout.addWidget(answer_edit)
            
            questions_layout.addWidget(question_widget)
            self.answer_edits[q['index']] = answer_edit
        
        layout.addWidget(questions_group)
        
        # 新密码设置
        password_group = QGroupBox("新密码")
        password_layout = QGridLayout(password_group)
        
        password_layout.addWidget(QLabel("新密码:"), 0, 0)
        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.new_password_edit, 0, 1)
        
        password_layout.addWidget(QLabel("确认密码:"), 1, 0)
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.confirm_password_edit, 1, 1)
        
        password_layout.addWidget(QLabel("密码提示:"), 2, 0)
        self.hint_edit = QLineEdit()
        self.hint_edit.setPlaceholderText("可选：新的密码提示")
        password_layout.addWidget(self.hint_edit, 2, 1)
        
        layout.addWidget(password_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("取消")
        self.reset_btn = QPushButton("重置密码")
        self.reset_btn.setDefault(True)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.reset_btn)
        
        layout.addLayout(button_layout)
    
    def setup_connections(self):
        """设置信号连接"""
        self.cancel_btn.clicked.connect(self.reject)
        self.reset_btn.clicked.connect(self.on_reset_password)
    
    def on_reset_password(self):
        """重置密码"""
        # 收集答案
        answers = {}
        for index, edit in self.answer_edits.items():
            answer = edit.text().strip()
            if answer:
                answers[index] = answer
        
        # 检查答案数量
        required_count = max(1, len(self.security_questions) // 2)
        if len(answers) < required_count:
            QMessageBox.warning(
                self, "错误", 
                f"请至少回答 {required_count} 个安全问题！"
            )
            return
        
        # 检查新密码
        new_password = self.new_password_edit.text()
        confirm_password = self.confirm_password_edit.text()
        
        if not new_password:
            QMessageBox.warning(self, "错误", "请输入新密码！")
            return
        
        if new_password != confirm_password:
            QMessageBox.warning(self, "错误", "两次输入的密码不匹配！")
            return
        
        # 重置密码
        hint = self.hint_edit.text().strip() or None
        if self.manager.reset_password_with_security_questions(answers, new_password, hint):
            self.accept()
        else:
            QMessageBox.critical(self, "错误", "密码重置失败！请检查安全问题答案是否正确。")

class MasterPasswordMainDialog(QDialog):
    """主密码管理主对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = MasterPasswordManager()
        self.setup_ui()
        self.setup_connections()
        self.update_status()
    
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("主密码管理")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("主密码管理")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 状态显示
        self.status_group = QGroupBox("当前状态")
        status_layout = QVBoxLayout(self.status_group)
        
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        layout.addWidget(self.status_group)
        
        # 操作按钮
        actions_group = QGroupBox("操作")
        actions_layout = QVBoxLayout(actions_group)
        
        self.setup_btn = QPushButton("设置主密码")
        self.setup_btn.setMinimumHeight(40)
        actions_layout.addWidget(self.setup_btn)
        
        self.change_btn = QPushButton("修改主密码")
        self.change_btn.setMinimumHeight(40)
        actions_layout.addWidget(self.change_btn)
        
        self.security_btn = QPushButton("管理安全问题")
        self.security_btn.setMinimumHeight(40)
        actions_layout.addWidget(self.security_btn)
        
        self.verify_btn = QPushButton("验证主密码")
        self.verify_btn.setMinimumHeight(40)
        actions_layout.addWidget(self.verify_btn)
        
        layout.addWidget(actions_group)
        
        layout.addStretch()
        
        # 关闭按钮
        button_layout = QHBoxLayout()
        
        self.close_btn = QPushButton("关闭")
        
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def setup_connections(self):
        """设置信号连接"""
        self.setup_btn.clicked.connect(self.on_setup_password)
        self.change_btn.clicked.connect(self.on_change_password)
        self.security_btn.clicked.connect(self.on_manage_security)
        self.verify_btn.clicked.connect(self.on_verify_password)
        self.close_btn.clicked.connect(self.accept)
    
    def update_status(self):
        """更新状态显示"""
        status = self.manager.get_account_status()
        
        if status['has_password']:
            status_text = "✓ 已设置主密码\n"
            
            if status['last_changed']:
                from datetime import datetime
                try:
                    last_changed = datetime.fromisoformat(status['last_changed'])
                    status_text += f"最后修改: {last_changed.strftime('%Y-%m-%d %H:%M')}\n"
                except:
                    pass
            
            status_text += f"安全问题数量: {status['security_questions_count']}\n"
            
            if status['is_locked']:
                status_text += "⚠️ 账户已被锁定"
                self.status_label.setStyleSheet("color: red;")
            elif status['failed_attempts'] > 0:
                remaining = status['max_attempts'] - status['failed_attempts']
                status_text += f"⚠️ 密码错误 {status['failed_attempts']} 次，还有 {remaining} 次机会"
                self.status_label.setStyleSheet("color: orange;")
            else:
                status_text += "✓ 状态正常"
                self.status_label.setStyleSheet("color: green;")
            
            self.setup_btn.setEnabled(False)
            self.change_btn.setEnabled(not status['is_locked'])
            self.verify_btn.setEnabled(not status['is_locked'])
        else:
            status_text = "❌ 尚未设置主密码\n请点击下方按钮设置主密码以保护您的数据。"
            self.status_label.setStyleSheet("color: #666;")
            
            self.setup_btn.setEnabled(True)
            self.change_btn.setEnabled(False)
            self.verify_btn.setEnabled(False)
        
        self.status_label.setText(status_text)
    
    def on_setup_password(self):
        """设置主密码"""
        dialog = MasterPasswordSetupDialog(self.manager, self)
        if dialog.exec_() == QDialog.Accepted:
            self.update_status()
    
    def on_change_password(self):
        """修改主密码"""
        # 首先验证当前密码
        verify_dialog = MasterPasswordVerifyDialog(self.manager, self)
        if verify_dialog.exec_() == QDialog.Accepted:
            # 验证成功，打开修改密码对话框
            setup_dialog = MasterPasswordSetupDialog(self.manager, self)
            setup_dialog.setWindowTitle("修改主密码")
            if setup_dialog.exec_() == QDialog.Accepted:
                self.update_status()
    
    def on_manage_security(self):
        """管理安全问题"""
        dialog = SecurityQuestionDialog(self.manager, self)
        dialog.exec_()
        self.update_status()
    
    def on_verify_password(self):
        """验证主密码"""
        dialog = MasterPasswordVerifyDialog(self.manager, self)
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "成功", "主密码验证成功！")
        self.update_status()

def main():
    """测试主密码管理对话框"""
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    dialog = MasterPasswordMainDialog()
    dialog.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()