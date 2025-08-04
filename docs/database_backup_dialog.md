# 数据库备份和恢复对话框

## 概述

`DatabaseBackupDialog` 是一个专业的数据库备份和恢复管理界面，提供了完整的数据库备份、恢复、自动备份计划等功能。该对话框采用标签页设计，功能全面且易于使用。

## 主要功能

### 1. 数据库备份
- 手动备份数据库到指定位置
- 支持备份说明和元数据记录
- 后台异步备份，不阻塞用户界面
- 实时进度显示和状态反馈

### 2. 数据库恢复
- 从备份文件恢复数据库
- 备份文件列表管理和选择
- 恢复前自动备份当前数据库
- 详细的恢复进度显示

### 3. 自动备份计划
- 支持每日、每周、每月自动备份
- 可配置备份时间和保留数量
- 自动清理过期备份文件
- 备份计划状态监控

### 4. 备份管理
- 备份文件信息展示（大小、时间、说明）
- 备份文件验证和完整性检查
- 备份历史记录管理

## 使用方法

### 基本使用

```python
from gui.database_backup_dialog import DatabaseBackupDialog

# 创建对话框
db_path = "/path/to/database.db"
dialog = DatabaseBackupDialog(db_path, parent_window)

# 显示对话框
result = dialog.exec_()

if result == DatabaseBackupDialog.Accepted:
    print("备份和恢复操作完成")
```

### 集成到主应用程序

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_path = get_default_database_path()
        self._create_menu()
    
    def _create_menu(self):
        """创建菜单"""
        db_menu = self.menuBar().addMenu('数据库')
        
        backup_action = QAction('备份和恢复...', self)
        backup_action.setShortcut('Ctrl+B')
        backup_action.triggered.connect(self._open_backup_dialog)
        db_menu.addAction(backup_action)
    
    def _open_backup_dialog(self):
        """打开备份对话框"""
        dialog = DatabaseBackupDialog(self.db_path, self)
        dialog.exec_()
```

## 界面结构

### 标签页组织

对话框包含三个主要标签页：

#### 1. 数据库备份标签页
- **备份设置区域**
  - 源数据库路径显示
  - 备份文件路径选择
  - 备份说明输入
  
- **备份操作区域**
  - 开始备份按钮
  - 备份进度条
  - 备份状态显示

#### 2. 数据库恢复标签页
- **备份列表区域**（左侧）
  - 可用备份文件表格
  - 文件信息（名称、时间、大小、说明）
  - 刷新列表功能
  
- **恢复操作区域**（右侧）
  - 选中备份文件显示
  - 目标数据库路径
  - 恢复选项设置
  - 恢复进度和状态

#### 3. 自动备份标签页
- **自动备份设置**
  - 启用/禁用自动备份
  - 备份频率选择（每日/每周/每月）
  - 备份时间设置
  - 备份目录选择
  - 保留备份数量设置
  
- **备份状态显示**
  - 当前自动备份状态
  - 下次备份时间
  - 设置保存和测试功能

## 功能详解

### 数据库备份功能

#### 备份流程
1. 用户选择备份文件保存路径
2. 可选输入备份说明
3. 点击"开始备份"按钮
4. 后台线程执行备份操作
5. 实时显示备份进度
6. 备份完成后显示结果

#### 备份线程实现
```python
class BackupThread(QThread):
    backup_progress = pyqtSignal(int, str)  # 进度信号
    backup_completed = pyqtSignal(bool, str, str)  # 完成信号
    
    def run(self):
        # 后台执行备份操作
        db_manager = DatabaseManager(self.db_path)
        if db_manager.backup_database(self.backup_path):
            self.backup_completed.emit(True, "备份成功", self.backup_path)
        else:
            self.backup_completed.emit(False, "备份失败", "")
```

#### 备份信息保存
```python
def _save_backup_info(self):
    """保存备份元数据"""
    backup_info = {
        'file_path': self.backup_path,
        'created_at': datetime.now().isoformat(),
        'file_size': os.path.getsize(self.backup_path),
        'notes': self.notes,
        'source_db': self.db_path
    }
    
    # 保存到 .info 文件
    info_file = self.backup_path + '.info'
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(backup_info, f, indent=2, ensure_ascii=False)
```

### 数据库恢复功能

#### 恢复流程
1. 扫描并显示可用备份文件
2. 用户选择要恢复的备份
3. 确认恢复操作（包含警告）
4. 可选备份当前数据库
5. 执行恢复操作
6. 显示恢复结果

#### 备份列表管理
```python
def _refresh_backup_list(self):
    """刷新备份列表"""
    backup_dir = os.path.join(get_default_storage_path(), "backups")
    backups = []
    
    for file_name in os.listdir(backup_dir):
        if file_name.endswith('.db'):
            # 读取备份信息
            backup_info = self._load_backup_info(file_path)
            backups.append(backup_info)
    
    # 按时间排序并更新表格
    backups.sort(key=lambda x: x.created_at, reverse=True)
    self._update_backup_table(backups)
```

#### 恢复线程实现
```python
class RestoreThread(QThread):
    restore_progress = pyqtSignal(int, str)
    restore_completed = pyqtSignal(bool, str)
    
    def run(self):
        # 备份当前数据库
        if os.path.exists(self.target_db_path):
            backup_current = f"{self.target_db_path}.backup.{timestamp}"
            shutil.copy2(self.target_db_path, backup_current)
        
        # 执行恢复
        db_manager = DatabaseManager(self.target_db_path)
        success = db_manager.restore_database(self.backup_path)
        self.restore_completed.emit(success, "恢复完成" if success else "恢复失败")
```

### 自动备份计划

#### 备份计划配置
```python
@dataclass
class BackupSchedule:
    enabled: bool = False
    frequency: str = "daily"  # daily, weekly, monthly
    time: str = "02:00"  # HH:MM format
    keep_count: int = 7  # 保留备份数量
    backup_path: str = ""  # 备份目录
```

#### 下次备份时间计算
```python
def _calculate_next_backup_time(self) -> Optional[datetime]:
    """计算下次备份时间"""
    now = datetime.now()
    backup_time = datetime.strptime(self.backup_schedule.time, "%H:%M").time()
    
    if self.backup_schedule.frequency == "daily":
        next_backup = datetime.combine(now.date(), backup_time)
        if next_backup <= now:
            next_backup += timedelta(days=1)
    elif self.backup_schedule.frequency == "weekly":
        days_ahead = 7 - now.weekday()
        next_backup = datetime.combine(now.date() + timedelta(days=days_ahead), backup_time)
    # ... 其他频率计算
    
    return next_backup
```

#### 备份计划保存和加载
```python
def _save_backup_schedule(self):
    """保存备份计划到配置文件"""
    config = {
        'enabled': self.backup_schedule.enabled,
        'frequency': self.backup_schedule.frequency,
        'time': self.backup_schedule.time,
        'backup_path': self.backup_schedule.backup_path,
        'keep_count': self.backup_schedule.keep_count
    }
    
    config_file = os.path.join(get_default_storage_path(), "backup_schedule.json")
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
```

## 高级功能

### 备份文件验证

```python
def _validate_backup_file(self, backup_path: str) -> bool:
    """验证备份文件完整性"""
    try:
        # 检查文件是否存在且可读
        if not os.path.exists(backup_path):
            return False
        
        # 尝试连接数据库验证格式
        db_manager = DatabaseManager(backup_path)
        if db_manager.connect():
            # 执行简单查询验证数据库结构
            result = db_manager.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
            db_manager.disconnect()
            return result is not None
        
        return False
    except Exception:
        return False
```

### 备份文件清理

```python
def _cleanup_old_backups(self):
    """清理过期的备份文件"""
    if not self.backup_schedule.enabled:
        return
    
    backup_dir = self.backup_schedule.backup_path
    keep_count = self.backup_schedule.keep_count
    
    # 获取所有备份文件
    backup_files = []
    for file_name in os.listdir(backup_dir):
        if file_name.endswith('.db'):
            file_path = os.path.join(backup_dir, file_name)
            stat = os.stat(file_path)
            backup_files.append((file_path, stat.st_mtime))
    
    # 按时间排序，保留最新的几个
    backup_files.sort(key=lambda x: x[1], reverse=True)
    
    # 删除多余的备份文件
    for file_path, _ in backup_files[keep_count:]:
        try:
            os.remove(file_path)
            # 同时删除对应的 .info 文件
            info_file = file_path + '.info'
            if os.path.exists(info_file):
                os.remove(info_file)
        except Exception as e:
            logger.warning(f"删除备份文件失败 {file_path}: {e}")
```

### 快速备份功能

```python
def quick_backup(db_path: str, backup_dir: str = None) -> str:
    """快速备份功能"""
    if backup_dir is None:
        backup_dir = os.path.join(get_default_storage_path(), "backups")
    
    # 确保备份目录存在
    os.makedirs(backup_dir, exist_ok=True)
    
    # 生成备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"quick_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_name)
    
    # 执行备份
    db_manager = DatabaseManager(db_path)
    if db_manager.connect():
        success = db_manager.backup_database(backup_path)
        db_manager.disconnect()
        
        if success:
            return backup_path
    
    raise Exception("快速备份失败")
```

## 自定义和扩展

### 自定义备份格式

```python
class CustomBackupDialog(DatabaseBackupDialog):
    def _start_backup(self):
        """重写备份方法，支持自定义格式"""
        # 调用父类方法
        super()._start_backup()
        
        # 添加自定义备份格式处理
        self._create_custom_backup_format()
    
    def _create_custom_backup_format(self):
        """创建自定义备份格式"""
        # 实现自定义备份逻辑
        pass
```

### 添加备份加密

```python
def _encrypt_backup(self, backup_path: str, password: str):
    """加密备份文件"""
    from core.encryption_service import EncryptionService
    
    encryption_service = EncryptionService()
    
    # 读取备份文件
    with open(backup_path, 'rb') as f:
        data = f.read()
    
    # 加密数据
    encrypted_data = encryption_service.encrypt(data, password)
    
    # 保存加密文件
    encrypted_path = backup_path + '.encrypted'
    with open(encrypted_path, 'wb') as f:
        f.write(encrypted_data)
    
    return encrypted_path
```

### 云备份集成

```python
class CloudBackupDialog(DatabaseBackupDialog):
    def _upload_to_cloud(self, backup_path: str):
        """上传备份到云存储"""
        # 实现云存储上传逻辑
        # 例如：AWS S3, Google Drive, Dropbox 等
        pass
    
    def _download_from_cloud(self, cloud_backup_id: str) -> str:
        """从云存储下载备份"""
        # 实现云存储下载逻辑
        pass
```

## 最佳实践

### 1. 定期备份策略
```python
# 推荐的备份策略
backup_strategies = {
    "开发环境": {
        "frequency": "daily",
        "time": "23:00",
        "keep_count": 7
    },
    "生产环境": {
        "frequency": "daily", 
        "time": "02:00",
        "keep_count": 30
    },
    "重要项目": {
        "frequency": "daily",
        "time": "01:00", 
        "keep_count": 90
    }
}
```

### 2. 备份验证
```python
def verify_backup_integrity():
    """验证备份完整性"""
    # 定期验证备份文件
    # 检查文件大小、格式、可读性
    # 执行测试查询验证数据完整性
    pass
```

### 3. 错误处理
```python
def handle_backup_errors():
    """备份错误处理"""
    try:
        # 执行备份操作
        pass
    except Exception as e:
        # 记录错误日志
        logger.error(f"备份失败: {e}")
        
        # 通知用户
        QMessageBox.critical(self, "备份失败", str(e))
        
        # 清理临时文件
        self._cleanup_temp_files()
```

### 4. 性能优化
```python
def optimize_backup_performance():
    """优化备份性能"""
    # 使用后台线程避免界面冻结
    # 显示详细进度信息
    # 支持取消操作
    # 合理设置备份文件大小限制
    pass
```

## 故障排除

### 常见问题

1. **备份失败**
   - 检查磁盘空间是否充足
   - 确认目标目录有写入权限
   - 验证源数据库文件是否被锁定

2. **恢复失败**
   - 验证备份文件完整性
   - 检查目标数据库是否被其他程序占用
   - 确认有足够权限覆盖目标文件

3. **自动备份不工作**
   - 检查备份计划配置是否正确
   - 验证备份目录是否存在且可写
   - 查看系统任务调度器设置

4. **界面响应慢**
   - 检查备份文件数量是否过多
   - 优化备份列表刷新频率
   - 考虑分页显示大量备份文件

### 调试技巧

1. **启用详细日志**
```python
import logging
logging.getLogger('gui.database_backup_dialog').setLevel(logging.DEBUG)
```

2. **监控线程状态**
```python
def check_thread_status(self):
    if self.backup_thread:
        print(f"备份线程状态: {self.backup_thread.isRunning()}")
    if self.restore_thread:
        print(f"恢复线程状态: {self.restore_thread.isRunning()}")
```

3. **验证备份文件**
```python
def debug_backup_file(backup_path):
    print(f"备份文件: {backup_path}")
    print(f"文件大小: {os.path.getsize(backup_path)} 字节")
    print(f"文件存在: {os.path.exists(backup_path)}")
    
    # 尝试连接验证
    try:
        db_manager = DatabaseManager(backup_path)
        connected = db_manager.connect()
        print(f"可连接: {connected}")
        if connected:
            db_manager.disconnect()
    except Exception as e:
        print(f"连接错误: {e}")
```

## 总结

`DatabaseBackupDialog` 提供了一个完整的数据库备份和恢复解决方案，具有以下优势：

- **功能完整**: 涵盖手动备份、自动备份、恢复等全部功能
- **用户友好**: 直观的标签页设计和详细的状态反馈
- **性能优化**: 后台线程处理，支持进度显示和取消操作
- **安全可靠**: 恢复前自动备份，支持操作确认和回滚
- **扩展性强**: 支持自定义备份格式、加密、云存储等扩展
- **维护便利**: 自动清理过期备份，备份文件管理

通过合理使用这个对话框，可以为用户提供专业级的数据库备份和恢复体验，确保数据安全和业务连续性。