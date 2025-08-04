# 数据库故障排除指南

## 概述

本指南提供了数据库存储系统常见问题的诊断和解决方案。通过系统化的故障排除流程，帮助用户快速定位和解决数据库相关问题。

## 快速诊断

### 自动诊断工具
使用内置的数据库诊断工具进行快速检查：

1. **启动诊断工具**
   - 菜单：工具 → 数据库诊断
   - 快捷键：Ctrl+Shift+D
   - 命令行：`python -m core.database_diagnostics`

2. **运行健康检查**
   ```
   数据库健康检查报告
   ==================
   ✓ 数据库文件存在
   ✓ 文件权限正常
   ✓ 数据库结构完整
   ✗ 发现3个损坏的索引
   ⚠ 数据库文件较大，建议清理
   
   总体状态: 需要维护
   ```

3. **查看详细信息**
   - 点击"详细报告"查看完整诊断信息
   - 导出诊断报告用于技术支持

### 系统状态检查
```bash
# 检查数据库文件状态
ls -la ~/.projectmanager/database.db

# 检查磁盘空间
df -h ~/.projectmanager/

# 检查进程状态
ps aux | grep projectmanager

# 检查日志文件
tail -n 50 ~/.projectmanager/logs/database.log
```

## 常见问题分类

### 1. 连接问题

#### 问题1.1: 数据库连接失败
**症状**:
- 启动时提示"无法连接到数据库"
- 应用程序无法启动或崩溃
- 错误代码: DB_CONNECTION_FAILED

**可能原因**:
- 数据库文件不存在或损坏
- 文件权限不正确
- 磁盘空间不足
- 数据库被其他进程锁定

**诊断步骤**:
```bash
# 1. 检查数据库文件是否存在
ls -la ~/.projectmanager/database.db

# 2. 检查文件权限
stat ~/.projectmanager/database.db

# 3. 检查磁盘空间
df -h ~/.projectmanager/

# 4. 检查文件锁定
lsof ~/.projectmanager/database.db
```

**解决方案**:
```bash
# 方案1: 重新创建数据库文件
rm ~/.projectmanager/database.db
python -m core.database_manager --init

# 方案2: 修复文件权限
chmod 644 ~/.projectmanager/database.db
chown $USER:$USER ~/.projectmanager/database.db

# 方案3: 清理磁盘空间
# 删除临时文件和日志
rm ~/.projectmanager/logs/*.log.old
rm ~/.projectmanager/temp/*

# 方案4: 终止锁定进程
pkill -f projectmanager
```

#### 问题1.2: 连接超时
**症状**:
- 操作响应缓慢
- 偶尔出现超时错误
- 错误代码: DB_TIMEOUT

**诊断步骤**:
```python
# 检查连接池状态
from core.database_manager import DatabaseManager
db = DatabaseManager()
print(f"活动连接数: {db.get_active_connections()}")
print(f"连接池大小: {db.get_pool_size()}")
```

**解决方案**:
```python
# 调整连接超时设置
db.set_connection_timeout(60)  # 增加到60秒

# 调整连接池大小
db.set_pool_size(min_connections=2, max_connections=10)

# 启用连接重试
db.enable_connection_retry(max_attempts=3, delay=1.0)
```

### 2. 性能问题

#### 问题2.1: 查询速度慢
**症状**:
- 搜索项目耗时过长
- 界面响应缓慢
- CPU使用率高

**诊断步骤**:
```sql
-- 检查慢查询
.timer on
SELECT * FROM projects WHERE name LIKE '%test%';

-- 检查查询计划
EXPLAIN QUERY PLAN SELECT * FROM projects WHERE name LIKE '%test%';

-- 检查索引使用情况
.schema projects
```

**解决方案**:
```sql
-- 重建索引
DROP INDEX IF EXISTS idx_projects_name;
CREATE INDEX idx_projects_name ON projects(name);

-- 分析表统计信息
ANALYZE projects;

-- 清理数据库
VACUUM;
```

#### 问题2.2: 内存使用过高
**症状**:
- 系统内存占用过高
- 应用程序响应缓慢
- 系统出现卡顿

**诊断步骤**:
```python
# 检查内存使用情况
import psutil
process = psutil.Process()
print(f"内存使用: {process.memory_info().rss / 1024 / 1024:.2f} MB")

# 检查缓存大小
from core.memory_cache_system import MemoryCacheSystem
cache = MemoryCacheSystem()
print(f"缓存大小: {cache.get_cache_size()} MB")
```

**解决方案**:
```python
# 调整缓存大小
cache.set_max_size(128)  # 限制为128MB

# 启用内存清理
cache.enable_auto_cleanup(interval=300)  # 每5分钟清理一次

# 调整数据库缓存
db.execute("PRAGMA cache_size = -64000")  # 64MB缓存
```

### 3. 数据完整性问题

#### 问题3.1: 数据库损坏
**症状**:
- 数据显示异常或缺失
- 查询返回错误结果
- 错误代码: DB_CORRUPTION

**诊断步骤**:
```sql
-- 检查数据库完整性
PRAGMA integrity_check;

-- 检查外键约束
PRAGMA foreign_key_check;

-- 检查表结构
.schema
```

**解决方案**:
```bash
# 方案1: 自动修复
python -m core.database_recovery --auto-repair

# 方案2: 从备份恢复
python -m core.database_recovery --restore-from-backup

# 方案3: 重建数据库
python -m core.database_recovery --rebuild-database
```

#### 问题3.2: 数据不一致
**症状**:
- 项目计数不正确
- 关联数据缺失
- 重复数据

**诊断步骤**:
```sql
-- 检查数据一致性
SELECT COUNT(*) FROM projects;
SELECT COUNT(DISTINCT id) FROM projects;

-- 检查外键关系
SELECT p.id, p.name 
FROM projects p 
LEFT JOIN project_history h ON p.id = h.project_id 
WHERE h.project_id IS NULL;
```

**解决方案**:
```python
# 运行数据一致性修复
from core.database_validator import DatabaseValidator
validator = DatabaseValidator()
validator.fix_inconsistencies()

# 清理重复数据
validator.remove_duplicates()

# 重建关联关系
validator.rebuild_relationships()
```

### 4. 备份和恢复问题

#### 问题4.1: 备份失败
**症状**:
- 自动备份不工作
- 手动备份出错
- 错误代码: BACKUP_FAILED

**诊断步骤**:
```bash
# 检查备份目录权限
ls -la ~/.projectmanager/backups/

# 检查磁盘空间
df -h ~/.projectmanager/backups/

# 检查备份日志
cat ~/.projectmanager/logs/backup.log
```

**解决方案**:
```bash
# 创建备份目录
mkdir -p ~/.projectmanager/backups/
chmod 755 ~/.projectmanager/backups/

# 手动执行备份
python -m core.database_backup --manual

# 修复备份配置
python -m core.database_backup --reset-config
```

#### 问题4.2: 恢复失败
**症状**:
- 无法从备份恢复数据
- 恢复过程中断
- 恢复后数据不完整

**诊断步骤**:
```bash
# 检查备份文件完整性
sqlite3 backup.db "PRAGMA integrity_check;"

# 检查备份文件大小
ls -lh backup.db

# 验证备份内容
sqlite3 backup.db ".tables"
```

**解决方案**:
```python
# 验证备份文件
from core.database_backup import DatabaseBackup
backup = DatabaseBackup()
if backup.verify_backup("backup.db"):
    backup.restore_from_backup("backup.db")
else:
    print("备份文件损坏，尝试其他备份")
```

### 5. 加密问题

#### 问题5.1: 密码验证失败
**症状**:
- 无法输入正确的主密码
- 加密数据无法解密
- 错误代码: ENCRYPTION_FAILED

**诊断步骤**:
```python
# 检查加密状态
from core.encryption_service import EncryptionService
encryption = EncryptionService()
print(f"加密启用: {encryption.is_enabled()}")
print(f"加密算法: {encryption.get_algorithm()}")
```

**解决方案**:
```python
# 重置主密码
encryption.reset_master_password()

# 禁用加密（临时）
encryption.disable_encryption()

# 重新加密数据
encryption.re_encrypt_data(new_password="new_password")
```

#### 问题5.2: 密钥丢失
**症状**:
- 忘记主密码
- 密钥文件损坏
- 无法访问加密数据

**解决方案**:
```python
# 使用安全问题重置
encryption.reset_with_security_questions()

# 使用备份密钥
encryption.restore_from_backup_key()

# 最后手段：重新初始化（会丢失加密数据）
encryption.reinitialize()
```

## 高级故障排除

### 数据库修复工具

#### 使用SQLite内置工具
```bash
# 导出数据
sqlite3 database.db .dump > database_dump.sql

# 重建数据库
sqlite3 new_database.db < database_dump.sql

# 替换原数据库
mv database.db database_backup.db
mv new_database.db database.db
```

#### 使用自定义修复工具
```python
from core.database_recovery import DatabaseRecovery

recovery = DatabaseRecovery("database.db")

# 检查可修复性
if recovery.can_repair():
    # 执行修复
    result = recovery.repair()
    print(f"修复结果: {result}")
else:
    # 尝试数据恢复
    recovered_data = recovery.recover_data()
    print(f"恢复了 {len(recovered_data)} 条记录")
```

### 性能调优

#### 数据库配置优化
```sql
-- 启用WAL模式
PRAGMA journal_mode = WAL;

-- 调整缓存大小
PRAGMA cache_size = -64000;  -- 64MB

-- 设置同步模式
PRAGMA synchronous = NORMAL;

-- 启用内存临时存储
PRAGMA temp_store = MEMORY;
```

#### 查询优化
```sql
-- 创建复合索引
CREATE INDEX idx_projects_name_tags ON projects(name, tags);

-- 创建部分索引
CREATE INDEX idx_active_projects ON projects(name) WHERE active = 1;

-- 更新表统计信息
ANALYZE projects;
```

### 监控和预警

#### 设置监控脚本
```python
import time
import logging
from core.database_monitor import DatabaseMonitor

monitor = DatabaseMonitor()

while True:
    # 检查数据库状态
    status = monitor.check_status()
    
    if status.has_issues():
        logging.warning(f"数据库问题: {status.issues}")
        
        # 发送警报
        monitor.send_alert(status.issues)
        
        # 尝试自动修复
        if status.can_auto_fix():
            monitor.auto_fix()
    
    time.sleep(300)  # 每5分钟检查一次
```

#### 日志分析
```bash
# 分析错误日志
grep "ERROR" ~/.projectmanager/logs/database.log | tail -20

# 分析性能日志
grep "SLOW" ~/.projectmanager/logs/database.log | tail -20

# 统计错误类型
grep "ERROR" ~/.projectmanager/logs/database.log | cut -d' ' -f4 | sort | uniq -c
```

## 预防措施

### 定期维护

#### 每日维护
```bash
#!/bin/bash
# daily_maintenance.sh

# 检查数据库完整性
sqlite3 database.db "PRAGMA integrity_check;"

# 更新统计信息
sqlite3 database.db "ANALYZE;"

# 清理临时文件
rm -f ~/.projectmanager/temp/*

# 检查日志大小
find ~/.projectmanager/logs/ -name "*.log" -size +100M -exec gzip {} \;
```

#### 每周维护
```bash
#!/bin/bash
# weekly_maintenance.sh

# 数据库清理
sqlite3 database.db "VACUUM;"

# 重建索引
sqlite3 database.db "REINDEX;"

# 创建备份
python -m core.database_backup --weekly

# 性能报告
python -m core.database_diagnostics --report
```

#### 每月维护
```bash
#!/bin/bash
# monthly_maintenance.sh

# 完整数据库检查
python -m core.database_validator --full-check

# 清理旧备份
find ~/.projectmanager/backups/ -name "*.db" -mtime +30 -delete

# 更新配置
python -m core.database_config --optimize

# 生成维护报告
python -m core.maintenance_report --monthly
```

### 监控指标

#### 关键指标
- **数据库大小**: 监控文件大小增长
- **查询性能**: 监控平均查询时间
- **连接数**: 监控活动连接数量
- **错误率**: 监控数据库错误频率
- **备份状态**: 监控备份成功率

#### 警报阈值
```python
# 设置监控阈值
monitor.set_thresholds({
    'database_size': 1000,      # 1GB
    'query_time': 5.0,          # 5秒
    'error_rate': 0.01,         # 1%
    'connection_count': 50,     # 50个连接
    'backup_age': 86400         # 24小时
})
```

## 应急响应

### 紧急情况处理

#### 数据库完全损坏
1. **立即停止应用程序**
2. **备份损坏的数据库文件**
3. **从最新备份恢复**
4. **验证恢复的数据**
5. **重新启动应用程序**

```bash
# 应急恢复脚本
#!/bin/bash
echo "开始应急恢复..."

# 停止应用程序
pkill -f projectmanager

# 备份损坏文件
cp database.db database_corrupted_$(date +%Y%m%d_%H%M%S).db

# 从备份恢复
cp backups/latest_backup.db database.db

# 验证恢复
sqlite3 database.db "PRAGMA integrity_check;"

echo "应急恢复完成"
```

#### 数据丢失
1. **评估丢失范围**
2. **检查可用备份**
3. **尝试数据恢复**
4. **重建丢失数据**

```python
# 数据恢复脚本
from core.data_recovery import DataRecovery

recovery = DataRecovery()

# 扫描可恢复数据
recoverable = recovery.scan_recoverable_data()
print(f"发现 {len(recoverable)} 条可恢复记录")

# 恢复数据
for record in recoverable:
    recovery.recover_record(record)

print("数据恢复完成")
```

### 联系技术支持

#### 收集诊断信息
在联系技术支持前，请收集以下信息：

```bash
# 生成诊断报告
python -m core.database_diagnostics --full-report > diagnostic_report.txt

# 收集日志文件
tar -czf logs.tar.gz ~/.projectmanager/logs/

# 收集配置文件
cp ~/.projectmanager/config.json config_backup.json

# 收集系统信息
uname -a > system_info.txt
df -h >> system_info.txt
free -h >> system_info.txt
```

#### 支持渠道
- **紧急热线**: +86-400-xxx-xxxx
- **技术邮箱**: database-support@projectmanager.com
- **在线工单**: https://support.projectmanager.com
- **远程协助**: 预约远程诊断服务

## 常见问题FAQ

### Q1: 数据库文件可以手动编辑吗？
**A**: 不建议手动编辑数据库文件。请使用应用程序提供的界面或API进行数据操作。

### Q2: 如何迁移到其他数据库系统？
**A**: 目前只支持SQLite。如需迁移到其他数据库，请联系技术支持。

### Q3: 数据库文件可以在不同操作系统间共享吗？
**A**: 可以。SQLite数据库文件是跨平台的，但需要注意文件路径的差异。

### Q4: 如何提高大数据量的查询性能？
**A**: 
- 创建适当的索引
- 使用分页查询
- 启用查询缓存
- 定期维护数据库

### Q5: 忘记主密码怎么办？
**A**: 
- 尝试使用安全问题重置
- 使用备份密钥恢复
- 联系技术支持协助

---

*本文档最后更新时间: 2024年1月*
*文档版本: 1.0*
*适用软件版本: ProjectManager 2.0+*