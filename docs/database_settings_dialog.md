# 数据库设置对话框

## 概述

`DatabaseSettingsDialog` 是一个功能完整的数据库设置和管理界面，提供了数据库配置、连接测试、信息展示、验证维护等全面的数据库管理功能。

## 主要功能

### 1. 基本设置
- 数据库文件路径选择和配置
- 连接状态实时显示
- 数据库连接测试
- 数据库创建、备份、恢复和优化

### 2. 数据库信息展示
- 实时显示数据库基本信息（版本、大小、表数量等）
- 详细的表统计信息
- 文件创建和修改时间
- 自动刷新机制

### 3. 验证和维护
- 多级数据库验证（基本、标准、彻底）
- 自动问题检测和修复
- 验证结果详细展示
- 后台异步处理

### 4. 高级设置
- 性能参数配置
- 维护计划设置
- 安全选项配置

## 使用方法

### 基本使用

```python
from gui.database_settings_dialog import DatabaseSettingsDialog
from core.storage_utils import get_default_database_path

# 创建对话框
current_db_path = get_default_database_path()
dialog = DatabaseSettingsDialog(current_db_path, parent_window)

# 连接信号
dialog.database_changed.connect(on_database_changed)

# 显示对话框
result = dialog.exec_()

if result == DatabaseSettingsDialog.Accepted:
    print("用户确认了设置")
else:
    print("用户取消了设置")
```

### 信号处理

```python
def on_database_changed(new_path: str):
    """处理数据库路径改变"""
    print(f"数据库路径已改变: {new_path}")
    # 在这里添加数据库切换逻辑
    # 例如：重新加载数据、更新UI等
```

### 集成到主应用程序

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_db_path = get_default_database_path()
        self._create_menu()
    
    def _create_menu(self):
        """创建菜单"""
        db_menu = self.menuBar().addMenu('数据库')
        
        settings_action = QAction('数据库设置...', self)
        settings_action.setShortcut('Ctrl+D')
        settings_action.triggered.connect(self._open_database_settings)
        db_menu.addAction(settings_action)
    
    def _open_database_settings(self):
        """打开数据库设置"""
        dialog = DatabaseSettingsDialog(self.current_db_path, self)
        dialog.database_changed.connect(self._on_database_changed)
        dialog.exec_()
    
    def _on_database_changed(self, new_path: str):
        """数据库改变处理"""
        self.current_db_path = new_path
        # 重新加载数据等操作
```

## 界面结构

### 标签页组织

对话框采用标签页结构，包含四个主要标签页：

#### 1. 基本设置标签页
- **数据库路径设置**
  - 路径输入框和浏览按钮
  - 连接状态实时显示
  
- **数据库操作**
  - 创建新数据库
  - 备份数据库
  - 恢复数据库
  - 优化数据库

#### 2. 数据库信息标签页
- **基本信息显示**
  - 数据库版本
  - 文件大小
  - 表数量和记录总数
  - 创建和修改时间
  
- **表统计信息**
  - 表格形式显示各表的记录数
  - 支持排序和选择
  - 自动刷新功能

#### 3. 验证维护标签页
- **验证设置**
  - 验证级别选择（基本/标准/彻底）
  - 验证按钮和进度显示
  
- **验证结果**
  - 详细的验证结果展示
  - 问题分类和严重程度显示
  - 自动修复功能

#### 4. 高级设置标签页
- **性能设置**
  - 缓存大小配置
  - 连接超时设置
  
- **维护设置**
  - 自动备份开关
  - 备份间隔配置
  - 自动优化设置
  
- **安全设置**
  - 数据加密选项
  - 审计日志设置

## 功能详解

### 数据库连接测试

```python
def _test_connection(self):
    """测试数据库连接"""
    # 在后台线程中执行测试，避免界面冻结
    self.test_thread = DatabaseTestThread(self.current_db_path)
    self.test_thread.test_completed.connect(self._on_test_completed)
    self.test_thread.start()
```

连接测试功能特点：
- 后台异步执行，不阻塞UI
- 实时状态更新
- 详细的测试结果反馈
- 自动刷新数据库信息

### 数据库验证

```python
def _validate_database(self):
    """验证数据库"""
    # 根据用户选择确定验证级别
    level = self._get_validation_level()
    
    # 后台执行验证
    self.validation_thread = DatabaseValidationThread(
        self.current_db_path, level
    )
    self.validation_thread.validation_completed.connect(
        self._on_validation_completed
    )
    self.validation_thread.start()
```

验证功能特点：
- 支持三种验证级别
- 进度条显示验证进度
- 详细的问题报告
- 自动修复建议
- 健康报告生成

### 自动修复

```python
def _auto_fix_issues(self):
    """自动修复问题"""
    # 获取可修复的问题
    auto_fixable_issues = [
        issue for issue in self._last_validation_result.issues 
        if issue.auto_fixable
    ]
    
    # 执行修复
    validator = DatabaseValidator(db_manager)
    result = validator.auto_fix_issues(auto_fixable_issues)
```

自动修复特点：
- 只修复安全的问题
- 事务性操作，失败自动回滚
- 详细的修复结果报告
- 修复后自动刷新信息

### 数据库操作

#### 创建数据库
```python
def _create_database(self):
    """创建新数据库"""
    file_path, _ = QFileDialog.getSaveFileName(...)
    
    if file_path:
        db_manager = DatabaseManager(file_path)
        if db_manager.connect():
            if db_manager.initialize_database():
                # 创建成功，更新界面
                self.path_input.setText(file_path)
```

#### 备份数据库
```python
def _backup_database(self):
    """备份数据库"""
    backup_path, _ = QFileDialog.getSaveFileName(...)
    
    if backup_path:
        db_manager = DatabaseManager(self.current_db_path)
        if db_manager.backup_database(backup_path):
            # 备份成功提示
```

#### 恢复数据库
```python
def _restore_database(self):
    """恢复数据库"""
    # 确认操作
    reply = QMessageBox.question(...)
    
    if reply == QMessageBox.Yes:
        db_manager = DatabaseManager(self.current_db_path)
        if db_manager.restore_database(backup_path):
            # 恢复成功，刷新信息
```

## 自定义和扩展

### 添加自定义验证规则

```python
class CustomDatabaseSettingsDialog(DatabaseSettingsDialog):
    def _validate_database(self):
        """重写验证方法，添加自定义验证"""
        # 调用父类验证
        super()._validate_database()
        
        # 添加自定义验证逻辑
        self._custom_validation()
    
    def _custom_validation(self):
        """自定义验证逻辑"""
        # 实现特定的业务验证规则
        pass
```

### 自定义设置保存

```python
def _apply_settings(self):
    """应用设置"""
    # 保存数据库路径
    if self.current_db_path != self.path_input.text():
        self.current_db_path = self.path_input.text()
        self.database_changed.emit(self.current_db_path)
    
    # 保存其他自定义设置
    settings = {
        'cache_size': self.cache_size_spin.value(),
        'timeout': self.timeout_spin.value(),
        'auto_backup': self.auto_backup_check.isChecked(),
        # ... 其他设置
    }
    
    # 保存到配置文件
    self._save_settings(settings)
```

### 添加自定义标签页

```python
def _create_custom_tab(self) -> QWidget:
    """创建自定义标签页"""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    
    # 添加自定义控件
    # ...
    
    return widget

def _init_ui(self):
    """初始化UI"""
    # 调用父类方法
    super()._init_ui()
    
    # 添加自定义标签页
    custom_tab = self._create_custom_tab()
    self.tab_widget.addTab(custom_tab, "自定义设置")
```

## 最佳实践

### 1. 错误处理
```python
def _database_operation(self):
    """数据库操作示例"""
    try:
        # 数据库操作
        result = some_database_operation()
        
        if result:
            QMessageBox.information(self, "成功", "操作完成")
        else:
            QMessageBox.warning(self, "警告", "操作失败")
            
    except Exception as e:
        QMessageBox.critical(self, "错误", f"操作异常: {str(e)}")
        logger.error(f"数据库操作失败: {e}")
```

### 2. 线程安全
```python
class DatabaseOperationThread(QThread):
    """数据库操作线程"""
    operation_completed = pyqtSignal(bool, str)
    
    def run(self):
        try:
            # 在后台线程中执行数据库操作
            result = self._perform_operation()
            self.operation_completed.emit(True, "操作成功")
        except Exception as e:
            self.operation_completed.emit(False, str(e))
```

### 3. 资源管理
```python
def closeEvent(self, event):
    """关闭事件处理"""
    # 停止定时器
    if hasattr(self, 'refresh_timer'):
        self.refresh_timer.stop()
    
    # 停止后台线程
    if self.test_thread and self.test_thread.isRunning():
        self.test_thread.quit()
        self.test_thread.wait()
    
    # 断开数据库连接
    if self.db_manager:
        self.db_manager.disconnect()
    
    event.accept()
```

### 4. 用户体验优化
```python
def _show_progress(self, message: str):
    """显示进度"""
    self.progress_bar.setVisible(True)
    self.status_label.setText(message)
    QApplication.processEvents()  # 刷新界面

def _hide_progress(self):
    """隐藏进度"""
    self.progress_bar.setVisible(False)
    self.status_label.setText("就绪")
```

## 故障排除

### 常见问题

1. **对话框无法打开**
   - 检查数据库路径是否有效
   - 确认数据库文件权限
   - 查看错误日志

2. **连接测试失败**
   - 验证数据库文件是否存在
   - 检查文件是否被其他程序锁定
   - 确认数据库文件格式正确

3. **验证过程卡住**
   - 检查数据库文件大小
   - 确认有足够的内存
   - 查看后台线程状态

4. **自动修复失败**
   - 检查数据库文件权限
   - 确认磁盘空间充足
   - 查看具体错误信息

### 调试技巧

1. **启用详细日志**
```python
import logging
logging.getLogger('gui.database_settings_dialog').setLevel(logging.DEBUG)
```

2. **监控线程状态**
```python
def _check_thread_status(self):
    """检查线程状态"""
    if self.test_thread:
        print(f"测试线程状态: {self.test_thread.isRunning()}")
    if self.validation_thread:
        print(f"验证线程状态: {self.validation_thread.isRunning()}")
```

3. **数据库连接诊断**
```python
def _diagnose_connection(self):
    """诊断数据库连接"""
    try:
        db_manager = DatabaseManager(self.current_db_path)
        info = db_manager.get_connection_info()
        print(f"连接诊断: {info}")
    except Exception as e:
        print(f"连接诊断失败: {e}")
```

## 总结

`DatabaseSettingsDialog` 提供了一个完整的数据库管理界面，具有以下优势：

- **功能完整**: 涵盖数据库配置、监控、维护的各个方面
- **用户友好**: 直观的标签页布局和实时状态反馈
- **性能优化**: 后台线程处理，不阻塞用户界面
- **扩展性强**: 支持自定义验证规则和设置项
- **错误处理**: 完善的异常处理和用户提示
- **资源安全**: 正确的资源管理和线程清理

通过合理使用这个对话框，可以为用户提供专业级的数据库管理体验。