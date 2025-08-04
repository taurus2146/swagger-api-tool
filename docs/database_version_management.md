# 数据库版本管理系统

## 概述

数据库版本管理系统提供了完整的数据库schema版本控制、自动升级和兼容性检查功能。它确保数据库结构能够安全地从旧版本升级到新版本，同时保持数据完整性。

## 主要功能

### 1. 版本检测和状态管理
- 自动检测当前数据库版本
- 提供版本状态（当前、过时、未来、未知）
- 支持版本兼容性检查

### 2. 自动迁移
- 智能迁移脚本执行
- 支持从旧版本数据库无缝升级
- 保持现有数据完整性

### 3. Schema完整性验证
- 验证数据库表、索引、触发器、视图的完整性
- 计算和验证schema哈希值
- 检测缺失或额外的数据库对象

### 4. 回滚支持
- 提供迁移失败时的回滚机制
- 支持数据库备份和恢复
- 确保升级过程的安全性

## 使用方法

### 基本使用

```python
from core.database_manager import DatabaseManager

# 创建数据库管理器
db_manager = DatabaseManager("path/to/database.db")

# 连接数据库
if db_manager.connect():
    # 获取版本管理器
    version_manager = db_manager.get_version_manager()
    
    # 检查版本状态
    version_info = version_manager.get_version_info()
    print(f"当前版本: {version_info['current_version']}")
    print(f"最新版本: {version_info['latest_version']}")
    print(f"状态: {version_info['status']}")
    
    # 自动升级到最新版本
    if version_info['upgrade_available']:
        result = version_manager.auto_upgrade_to_latest()
        if result['success']:
            print("升级成功")
        else:
            print(f"升级失败: {result['message']}")
```

### 高级功能

#### 1. 创建迁移计划

```python
# 创建迁移计划
plan = version_manager.create_migration_plan(target_version=1)
if plan:
    print(f"迁移计划: {plan.current_version} -> {plan.target_version}")
    print(f"需要执行 {len(plan.scripts)} 个脚本")
    print(f"预计时间: {plan.estimated_time} 秒")
```

#### 2. 执行迁移计划

```python
# 执行迁移计划（带备份）
backup_path = "backup/database_backup.db"
result = version_manager.execute_migration_plan(plan, backup_path)

if result['success']:
    print(f"迁移成功，执行了 {result['executed_scripts']} 个脚本")
else:
    print(f"迁移失败: {result['errors']}")
```

#### 3. Schema完整性验证

```python
# 验证schema完整性
integrity = version_manager.verify_schema_integrity()
if integrity['valid']:
    print("Schema完整性验证通过")
else:
    print(f"发现问题: {integrity['issues']}")
```

#### 4. 版本兼容性检查

```python
# 检查版本兼容性
compatibility = version_manager.check_compatibility(required_version=1)
if compatibility['compatible']:
    print("版本兼容")
else:
    print(f"版本不兼容: {compatibility['message']}")
    if compatibility['upgrade_needed']:
        print("需要升级数据库")
```

## 版本管理架构

### 版本信息存储

版本信息存储在 `database_info` 表中：

```sql
CREATE TABLE database_info (
    version INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    last_migration DATETIME,
    schema_hash TEXT,
    notes TEXT
);
```

### 迁移脚本结构

每个迁移脚本包含：
- 源版本和目标版本
- 迁移方向（升级/降级）
- SQL语句列表
- 回滚语句列表
- 描述信息

### 智能迁移处理

系统能够：
- 检测现有表结构
- 动态生成迁移语句
- 处理字段缺失情况
- 保持数据完整性

## 错误处理

### 常见错误类型

1. **连接错误**: 数据库文件不存在或权限不足
2. **版本错误**: 版本信息损坏或不一致
3. **迁移错误**: SQL语句执行失败
4. **完整性错误**: Schema验证失败

### 错误恢复

- 自动回滚失败的迁移
- 提供详细的错误信息
- 支持手动数据恢复
- 备份和恢复机制

## 最佳实践

### 1. 定期备份
在执行任何迁移之前，建议创建数据库备份：

```python
backup_path = f"backup/db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
db_manager.backup_database(backup_path)
```

### 2. 版本检查
在应用程序启动时检查数据库版本：

```python
def check_database_version():
    version_manager = db_manager.get_version_manager()
    compatibility = version_manager.check_compatibility(required_version=1)
    
    if not compatibility['compatible']:
        if compatibility['upgrade_needed']:
            # 提示用户升级
            result = version_manager.auto_upgrade_to_latest()
            return result['success']
        else:
            # 应用程序版本过低
            return False
    
    return True
```

### 3. 监控和日志
启用详细的日志记录来跟踪迁移过程：

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### 4. 测试迁移
在生产环境之前，在测试数据库上验证迁移：

```python
# 在测试数据库上执行迁移
test_db = DatabaseManager("test_database.db")
test_version_manager = test_db.get_version_manager()
result = test_version_manager.auto_upgrade_to_latest()
```

## 扩展新版本

当需要添加新的数据库版本时：

1. 更新 `DatabaseSchema.SCHEMA_VERSION`
2. 在 `DatabaseVersionManager._initialize_migration_scripts()` 中添加新的迁移脚本
3. 测试迁移过程
4. 更新文档

### 示例：添加版本2

```python
# 在 _initialize_migration_scripts 方法中添加
scripts[(1, 2)] = MigrationScript(
    from_version=1,
    to_version=2,
    direction=MigrationDirection.UPGRADE,
    description="升级到版本2：添加新功能",
    sql_statements=[
        "ALTER TABLE projects ADD COLUMN priority INTEGER DEFAULT 0",
        "CREATE INDEX IF NOT EXISTS idx_projects_priority ON projects(priority)"
    ],
    rollback_statements=[
        "DROP INDEX IF EXISTS idx_projects_priority",
        "ALTER TABLE projects DROP COLUMN priority"
    ]
)
```

## 故障排除

### 常见问题

1. **"no such table: database_info"**
   - 原因：数据库未初始化
   - 解决：调用 `db_manager.initialize_database()`

2. **"Schema哈希不匹配"**
   - 原因：数据库结构与预期不符
   - 解决：运行完整性验证并修复

3. **"NOT NULL constraint failed"**
   - 原因：迁移时缺少必需字段的默认值
   - 解决：检查迁移脚本中的默认值设置

4. **迁移失败**
   - 原因：SQL语句错误或数据冲突
   - 解决：检查日志，必要时从备份恢复

### 调试技巧

1. 启用详细日志：`logging.getLogger('core.database_version_manager').setLevel(logging.DEBUG)`
2. 检查数据库文件权限
3. 验证SQL语句语法
4. 使用SQLite工具检查数据库结构

## 总结

数据库版本管理系统提供了一个强大而灵活的解决方案来管理数据库schema的演进。通过自动化的迁移过程、完整性验证和错误恢复机制，它确保了数据库升级的安全性和可靠性。