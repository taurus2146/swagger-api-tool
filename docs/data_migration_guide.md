# 数据迁移操作指南

## 概述

本指南详细说明如何将数据从旧版本的JSON文件格式迁移到新的SQLite数据库格式。数据迁移是一个重要的过程，确保您的项目数据安全地转移到新的存储系统中。

## 迁移前准备

### 1. 数据备份
在开始迁移之前，强烈建议备份您的现有数据：

```bash
# 备份整个数据目录
cp -r ~/.projectmanager/data ~/.projectmanager/data_backup_$(date +%Y%m%d)

# 或者只备份关键文件
cp ~/.projectmanager/projects.json ~/.projectmanager/projects_backup.json
cp ~/.projectmanager/config.json ~/.projectmanager/config_backup.json
```

### 2. 检查数据完整性
确保现有的JSON文件格式正确：

```bash
# 检查JSON文件语法
python -m json.tool ~/.projectmanager/projects.json > /dev/null
echo "JSON文件格式检查完成"
```

### 3. 系统要求确认
- 确保有足够的磁盘空间（建议至少是原数据大小的3倍）
- 确保应用程序已更新到支持数据库的版本
- 关闭所有正在运行的应用程序实例

## 自动迁移

### 启动自动迁移
1. **启动应用程序**
   - 首次启动新版本时，系统会自动检测旧数据
   - 如果检测到JSON格式的数据文件，会显示迁移向导

2. **迁移向导步骤**
   
   **步骤1: 数据检测**
   ```
   检测到以下数据文件：
   ✓ projects.json (125个项目)
   ✓ config.json (12个配置项)
   ✓ history.json (450条历史记录)
   
   预计迁移时间: 约2分钟
   ```
   
   **步骤2: 迁移选项**
   - [ ] 迁移项目数据
   - [ ] 迁移配置数据
   - [ ] 迁移历史记录
   - [ ] 保留原始文件作为备份
   - [ ] 创建迁移日志
   
   **步骤3: 目标数据库**
   ```
   数据库位置: C:\Users\用户名\Documents\ProjectManager\database.db
   [浏览...] [新建数据库...]
   ```
   
   **步骤4: 开始迁移**
   ```
   迁移进度:
   [████████████████████████████████] 100%
   
   迁移完成！
   - 成功迁移 125 个项目
   - 成功迁移 12 个配置项
   - 成功迁移 450 条历史记录
   - 0 个错误
   ```

### 迁移结果验证
迁移完成后，系统会自动验证数据完整性：

1. **数据统计对比**
   ```
   迁移前 (JSON):     迁移后 (数据库):
   项目数量: 125      项目数量: 125      ✓
   配置项: 12         配置项: 12         ✓
   历史记录: 450      历史记录: 450      ✓
   ```

2. **数据抽样检查**
   - 随机选择10%的项目进行详细对比
   - 验证项目名称、路径、标签等关键信息
   - 检查特殊字符和Unicode字符处理

3. **功能测试**
   - 测试项目搜索功能
   - 测试项目编辑和保存
   - 测试配置读取和修改

## 手动迁移

### 使用迁移工具
如果自动迁移失败或需要更多控制，可以使用命令行迁移工具：

```bash
# 基本迁移命令
python -m core.migration_service \
  --source /path/to/projects.json \
  --target /path/to/database.db \
  --verbose

# 带选项的迁移命令
python -m core.migration_service \
  --source /path/to/projects.json \
  --target /path/to/database.db \
  --backup \
  --validate \
  --log-file migration.log
```

### 迁移选项说明

#### 基本选项
- `--source`: 源JSON文件路径
- `--target`: 目标数据库文件路径
- `--verbose`: 显示详细进度信息

#### 高级选项
- `--backup`: 迁移前自动备份源文件
- `--validate`: 迁移后验证数据完整性
- `--log-file`: 指定日志文件路径
- `--batch-size`: 批量处理大小（默认100）
- `--timeout`: 操作超时时间（默认300秒）

#### 过滤选项
- `--include-projects`: 只迁移项目数据
- `--include-config`: 只迁移配置数据
- `--include-history`: 只迁移历史数据
- `--exclude-tags`: 排除特定标签的项目

### 分步迁移

#### 步骤1: 准备目标数据库
```python
from core.database_manager import DatabaseManager

# 创建新数据库
db_manager = DatabaseManager("/path/to/new_database.db")
print("数据库初始化完成")
```

#### 步骤2: 读取源数据
```python
import json
from core.migration_service import MigrationService

# 读取JSON数据
migration_service = MigrationService(
    source_file="/path/to/projects.json",
    target_db="/path/to/database.db"
)

# 验证源数据
if migration_service.validate_source_data():
    print("源数据验证通过")
else:
    print("源数据存在问题，请检查")
```

#### 步骤3: 执行迁移
```python
# 开始迁移
try:
    result = migration_service.migrate_projects()
    print(f"项目迁移完成: {result['success_count']} 成功, {result['error_count']} 失败")
    
    result = migration_service.migrate_config()
    print(f"配置迁移完成: {result['success_count']} 成功, {result['error_count']} 失败")
    
except Exception as e:
    print(f"迁移失败: {e}")
```

#### 步骤4: 验证结果
```python
# 验证迁移结果
validation_result = migration_service.validate_migration()
if validation_result['success']:
    print("迁移验证通过")
else:
    print(f"验证失败: {validation_result['errors']}")
```

## 特殊情况处理

### 大数据量迁移
对于包含大量项目（>10000个）的数据：

1. **分批处理**
   ```bash
   python -m core.migration_service \
     --source projects.json \
     --target database.db \
     --batch-size 500 \
     --progress
   ```

2. **内存优化**
   ```python
   # 在迁移脚本中设置
   migration_service.set_memory_limit(512)  # 限制内存使用为512MB
   migration_service.enable_streaming_mode()  # 启用流式处理
   ```

3. **并行处理**
   ```bash
   # 分割数据文件
   python split_json.py projects.json --chunks 4
   
   # 并行迁移
   python -m core.migration_service --source projects_1.json --target db1.db &
   python -m core.migration_service --source projects_2.json --target db2.db &
   python -m core.migration_service --source projects_3.json --target db3.db &
   python -m core.migration_service --source projects_4.json --target db4.db &
   
   # 合并数据库
   python merge_databases.py db1.db db2.db db3.db db4.db --output final.db
   ```

### 损坏数据修复
如果源JSON文件损坏：

1. **自动修复**
   ```python
   from core.data_repair import JSONRepair
   
   repair_tool = JSONRepair("corrupted_projects.json")
   if repair_tool.can_repair():
       repair_tool.repair("repaired_projects.json")
       print("数据修复完成")
   ```

2. **手动修复**
   ```bash
   # 检查JSON语法错误
   python -m json.tool projects.json
   
   # 使用文本编辑器修复语法错误
   # 常见问题：缺少逗号、括号不匹配、非法字符
   ```

3. **部分恢复**
   ```python
   # 尝试恢复可读取的部分
   migration_service.set_error_handling("skip")  # 跳过错误记录
   migration_service.set_recovery_mode(True)     # 启用恢复模式
   ```

### 字符编码问题
处理不同字符编码的数据：

```python
# 检测文件编码
import chardet

with open("projects.json", "rb") as f:
    encoding = chardet.detect(f.read())['encoding']
    print(f"检测到编码: {encoding}")

# 转换编码
migration_service.set_source_encoding(encoding)
migration_service.set_target_encoding("utf-8")
```

### 版本兼容性
处理不同版本的JSON格式：

```python
# 检测JSON格式版本
version = migration_service.detect_json_version()
print(f"JSON格式版本: {version}")

# 应用版本特定的迁移策略
if version == "1.0":
    migration_service.apply_v1_migration()
elif version == "1.5":
    migration_service.apply_v15_migration()
```

## 迁移后操作

### 1. 数据验证
```python
from core.database_validator import DatabaseValidator

validator = DatabaseValidator("/path/to/database.db")

# 完整性检查
integrity_result = validator.check_integrity()
print(f"数据完整性: {'通过' if integrity_result.success else '失败'}")

# 一致性检查
consistency_result = validator.check_consistency()
print(f"数据一致性: {'通过' if consistency_result.success else '失败'}")

# 性能检查
performance_result = validator.check_performance()
print(f"性能状态: {performance_result.status}")
```

### 2. 索引优化
```sql
-- 重建索引以优化性能
REINDEX;

-- 分析表统计信息
ANALYZE;

-- 清理数据库
VACUUM;
```

### 3. 配置更新
更新应用程序配置以使用新数据库：

```json
{
  "database": {
    "type": "sqlite",
    "path": "/path/to/database.db",
    "backup_enabled": true,
    "auto_vacuum": true
  },
  "migration": {
    "completed": true,
    "version": "2.0",
    "date": "2024-01-15T10:30:00Z"
  }
}
```

### 4. 清理旧文件
迁移成功后，可以清理旧文件：

```bash
# 移动旧文件到备份目录
mkdir -p ~/.projectmanager/legacy_backup
mv ~/.projectmanager/*.json ~/.projectmanager/legacy_backup/

# 或者删除旧文件（谨慎操作）
# rm ~/.projectmanager/*.json
```

## 故障排除

### 常见错误及解决方案

#### 错误1: "JSON文件格式错误"
**原因**: JSON语法错误或文件损坏
**解决方案**:
```bash
# 检查JSON语法
python -m json.tool projects.json

# 使用修复工具
python -m core.data_repair projects.json --output repaired.json
```

#### 错误2: "数据库创建失败"
**原因**: 权限不足或磁盘空间不够
**解决方案**:
```bash
# 检查磁盘空间
df -h

# 检查目录权限
ls -la ~/.projectmanager/

# 手动创建目录
mkdir -p ~/.projectmanager/
chmod 755 ~/.projectmanager/
```

#### 错误3: "迁移中断"
**原因**: 系统资源不足或网络问题
**解决方案**:
```python
# 从中断点继续迁移
migration_service.resume_migration()

# 或者重新开始
migration_service.restart_migration()
```

#### 错误4: "数据验证失败"
**原因**: 数据在迁移过程中损坏
**解决方案**:
```python
# 详细验证报告
validation_report = migration_service.get_validation_report()
print(validation_report)

# 修复数据
migration_service.repair_migrated_data()
```

### 日志分析
查看迁移日志以诊断问题：

```bash
# 查看迁移日志
tail -f ~/.projectmanager/logs/migration.log

# 搜索错误信息
grep "ERROR" ~/.projectmanager/logs/migration.log

# 分析性能问题
grep "SLOW" ~/.projectmanager/logs/migration.log
```

### 性能优化
如果迁移速度慢：

1. **调整批处理大小**
   ```python
   migration_service.set_batch_size(1000)  # 增加批处理大小
   ```

2. **禁用实时验证**
   ```python
   migration_service.disable_realtime_validation()  # 迁移完成后再验证
   ```

3. **使用内存数据库**
   ```python
   migration_service.use_memory_database()  # 先迁移到内存，再写入磁盘
   ```

## 回滚操作

### 自动回滚
如果迁移失败，可以自动回滚：

```python
# 检查是否可以回滚
if migration_service.can_rollback():
    # 执行回滚
    rollback_result = migration_service.rollback()
    if rollback_result.success:
        print("回滚成功，已恢复到迁移前状态")
    else:
        print(f"回滚失败: {rollback_result.error}")
```

### 手动回滚
```bash
# 删除新数据库
rm /path/to/database.db

# 恢复备份文件
cp ~/.projectmanager/data_backup/* ~/.projectmanager/

# 重启应用程序
```

## 最佳实践

### 迁移前
1. **完整备份**: 备份所有数据文件
2. **测试环境**: 先在测试环境中进行迁移
3. **资源准备**: 确保足够的磁盘空间和内存
4. **时间安排**: 选择业务低峰期进行迁移

### 迁移中
1. **监控进度**: 实时监控迁移进度和系统资源
2. **日志记录**: 启用详细日志记录
3. **错误处理**: 设置合适的错误处理策略
4. **中断恢复**: 准备中断恢复方案

### 迁移后
1. **全面验证**: 进行完整的数据验证
2. **性能测试**: 测试新系统的性能
3. **用户培训**: 培训用户使用新功能
4. **监控观察**: 持续监控系统稳定性

## 技术支持

如果在迁移过程中遇到问题，可以通过以下方式获取帮助：

### 自助资源
- **在线文档**: https://docs.projectmanager.com/migration
- **视频教程**: https://tutorials.projectmanager.com/migration
- **常见问题**: https://faq.projectmanager.com/migration

### 技术支持
- **邮件支持**: migration-support@projectmanager.com
- **在线客服**: 工作日 9:00-18:00
- **远程协助**: 预约远程迁移协助

### 紧急支持
- **24小时热线**: +86-400-xxx-xxxx
- **紧急邮箱**: emergency@projectmanager.com
- **在线工单**: https://support.projectmanager.com

---

*本文档最后更新时间: 2024年1月*
*文档版本: 1.0*
*适用软件版本: ProjectManager 2.0+*