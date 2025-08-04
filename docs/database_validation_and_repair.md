# 数据库验证和修复工具

## 概述

数据库验证和修复工具提供了全面的数据库健康检查、问题诊断和自动修复功能。它能够检测数据完整性问题、性能问题、数据损坏等各种数据库问题，并提供自动修复和优化建议。

## 主要功能

### 1. 数据完整性检查
- 验证数据库表结构完整性
- 检查数据字段的有效性和约束
- 验证外键关系的一致性
- 检测孤立记录和无效数据

### 2. 数据一致性验证
- 检查数据之间的逻辑一致性
- 验证统计数据的准确性
- 检测数据冲突和矛盾

### 3. 性能问题诊断
- 分析索引使用情况
- 检测性能瓶颈
- 提供优化建议

### 4. 自动修复功能
- 修复可自动处理的数据问题
- 清理孤立和过期数据
- 更新不一致的统计信息

### 5. 数据库优化
- 重建索引
- 压缩数据库文件
- 清理过期缓存
- 更新统计信息

## 使用方法

### 基本使用

```python
from core.database_manager import DatabaseManager
from core.database_validator import DatabaseValidator, ValidationLevel

# 创建数据库管理器
db_manager = DatabaseManager("path/to/database.db")

# 连接数据库
if db_manager.connect():
    # 创建验证器
    validator = DatabaseValidator(db_manager)
    
    # 执行标准验证
    result = validator.validate_database(ValidationLevel.STANDARD)
    
    print(f"验证结果: {'通过' if result.success else '失败'}")
    print(f"发现问题: {len(result.issues)} 个")
    
    # 显示问题详情
    for issue in result.issues:
        print(f"- {issue.severity.value.upper()}: {issue.description}")
```

### 验证级别

系统提供三种验证级别：

#### 1. 基本验证 (BASIC)
- 数据库结构检查
- 基本数据完整性检查
- 外键约束验证

```python
result = validator.validate_database(ValidationLevel.BASIC)
```

#### 2. 标准验证 (STANDARD)
- 包含基本验证的所有检查
- 数据一致性验证
- 孤立记录检测
- 约束违反检查

```python
result = validator.validate_database(ValidationLevel.STANDARD)
```

#### 3. 彻底验证 (THOROUGH)
- 包含标准验证的所有检查
- 性能问题分析
- 数据损坏检测
- 详细统计分析

```python
result = validator.validate_database(ValidationLevel.THOROUGH)
```

### 自动修复

```python
# 获取可自动修复的问题
auto_fixable_issues = [issue for issue in result.issues if issue.auto_fixable]

if auto_fixable_issues:
    # 执行自动修复
    fix_result = validator.auto_fix_issues(auto_fixable_issues)
    
    print(f"修复结果: {fix_result['message']}")
    print(f"成功修复: {fix_result['fixed_count']} 个问题")
    print(f"修复失败: {fix_result['failed_count']} 个问题")
    
    # 显示错误信息
    for error in fix_result['errors']:
        print(f"错误: {error}")
```

### 数据库优化

```python
# 执行数据库优化
optimize_result = validator.optimize_database()

print(f"优化结果: {optimize_result['message']}")

# 显示执行的操作
for operation in optimize_result['operations']:
    print(f"✓ {operation}")

# 显示错误
for error in optimize_result['errors']:
    print(f"✗ {error}")
```

### 健康报告

```python
# 生成数据库健康报告
health_report = validator.get_database_health_report()

print("=== 数据库健康报告 ===")
print(f"生成时间: {health_report['timestamp']}")

# 数据库基本信息
db_info = health_report['database_info']
print(f"文件大小: {db_info['file_size_mb']} MB")
print(f"数据库版本: {db_info['version']}")
print(f"表数量: {db_info['table_count']}")

# 表统计信息
print("\n表统计:")
for table, stats in health_report['table_statistics'].items():
    print(f"  {table}: {stats['record_count']} 条记录")

# 建议
print("\n优化建议:")
for recommendation in health_report['recommendations']:
    print(f"  - {recommendation}")
```

## 问题类型

### 数据完整性问题

#### 1. 缺失必需字段
```
问题: 项目记录缺少必需字段
严重程度: MEDIUM
可修复: 是
修复方法: 删除无效记录或补充默认值
```

#### 2. 日期逻辑错误
```
问题: 项目最后访问时间早于创建时间
严重程度: LOW
可修复: 是
修复方法: 将最后访问时间设置为创建时间
```

#### 3. 外键约束违反
```
问题: 历史记录引用不存在的项目
严重程度: MEDIUM
可修复: 是
修复方法: 删除孤立的历史记录
```

### 数据一致性问题

#### 1. 统计数据不一致
```
问题: 项目API数量与实际记录不符
严重程度: LOW
可修复: 是
修复方法: 重新计算并更新统计数据
```

#### 2. 缓存数据过期
```
问题: 发现过期的缓存记录
严重程度: LOW
可修复: 是
修复方法: 清理过期缓存
```

### 性能问题

#### 1. 缺失索引
```
问题: 缺少推荐的索引
严重程度: LOW
可修复: 否（需要手动创建）
建议: 创建相应的索引以提高查询性能
```

#### 2. 表记录数量过大
```
问题: 表记录数量较大，可能影响性能
严重程度: LOW
可修复: 否
建议: 考虑数据归档或分区
```

### 数据损坏问题

#### 1. JSON格式错误
```
问题: 项目配置字段包含无效JSON
严重程度: MEDIUM
可修复: 是
修复方法: 清空无效的JSON字段
```

#### 2. 数据库完整性检查失败
```
问题: SQLite完整性检查发现问题
严重程度: CRITICAL
可修复: 否
建议: 从备份恢复数据库
```

## 最佳实践

### 1. 定期验证
建议定期执行数据库验证，特别是在以下情况：

```python
def scheduled_validation():
    """定期验证任务"""
    validator = DatabaseValidator(db_manager)
    
    # 执行标准验证
    result = validator.validate_database(ValidationLevel.STANDARD)
    
    if not result.success:
        # 记录问题
        logger.warning(f"发现 {len(result.issues)} 个数据库问题")
        
        # 自动修复可修复的问题
        auto_fixable = [issue for issue in result.issues if issue.auto_fixable]
        if auto_fixable:
            validator.auto_fix_issues(auto_fixable)
        
        # 发送通知（如果有严重问题）
        if result.has_critical_issues:
            send_alert("数据库发现严重问题，需要立即处理")
```

### 2. 应用启动时检查
在应用程序启动时执行基本验证：

```python
def startup_check():
    """启动时检查"""
    validator = DatabaseValidator(db_manager)
    
    # 执行基本验证
    result = validator.validate_database(ValidationLevel.BASIC)
    
    if result.has_critical_issues:
        # 严重问题，阻止启动
        raise RuntimeError("数据库存在严重问题，无法启动应用")
    
    if not result.success:
        # 非严重问题，记录日志
        logger.warning("数据库存在一些问题，建议进行维护")
```

### 3. 数据迁移后验证
在数据迁移或升级后执行验证：

```python
def post_migration_validation():
    """迁移后验证"""
    validator = DatabaseValidator(db_manager)
    
    # 执行彻底验证
    result = validator.validate_database(ValidationLevel.THOROUGH)
    
    if not result.success:
        logger.error("迁移后验证发现问题")
        
        # 尝试自动修复
        fix_result = validator.auto_fix_issues()
        
        if not fix_result['success']:
            # 修复失败，可能需要回滚
            logger.critical("自动修复失败，考虑回滚迁移")
```

### 4. 性能监控
定期监控数据库性能：

```python
def performance_monitoring():
    """性能监控"""
    validator = DatabaseValidator(db_manager)
    
    # 生成健康报告
    report = validator.get_database_health_report()
    
    # 检查关键指标
    db_info = report['database_info']
    
    if db_info['file_size_mb'] > 100:
        logger.warning("数据库文件较大，建议优化")
        
        # 执行优化
        validator.optimize_database()
    
    # 检查表记录数
    for table, stats in report['table_statistics'].items():
        if stats['record_count'] > 50000:
            logger.info(f"表 {table} 记录数较多: {stats['record_count']}")
```

## 配置选项

### 日志配置
```python
import logging

# 配置验证器日志
logging.getLogger('core.database_validator').setLevel(logging.INFO)
```

### 自定义验证规则
可以通过继承 `DatabaseValidator` 类来添加自定义验证规则：

```python
class CustomDatabaseValidator(DatabaseValidator):
    def _check_custom_business_rules(self) -> bool:
        """检查自定义业务规则"""
        # 实现自定义检查逻辑
        pass
    
    def validate_database(self, level: ValidationLevel = ValidationLevel.STANDARD):
        # 调用父类方法
        result = super().validate_database(level)
        
        # 添加自定义检查
        if level == ValidationLevel.THOROUGH:
            self._check_custom_business_rules()
        
        return result
```

## 故障排除

### 常见问题

1. **验证过程中出现异常**
   - 检查数据库连接状态
   - 确认数据库文件权限
   - 查看详细错误日志

2. **自动修复失败**
   - 检查数据库是否被锁定
   - 确认有足够的磁盘空间
   - 手动执行修复SQL语句

3. **性能问题检测不准确**
   - 更新数据库统计信息：`ANALYZE`
   - 重建索引
   - 检查查询计划

4. **健康报告生成失败**
   - 检查数据库表是否存在
   - 确认有查询权限
   - 查看具体错误信息

### 调试技巧

1. **启用详细日志**
```python
logging.getLogger('core.database_validator').setLevel(logging.DEBUG)
```

2. **单独执行检查**
```python
validator = DatabaseValidator(db_manager)
# 只执行特定检查
validator._check_data_integrity()
```

3. **手动验证SQL**
```python
# 直接执行验证SQL
result = db_manager.execute_query("SELECT COUNT(*) FROM projects WHERE name IS NULL")
```

## 总结

数据库验证和修复工具提供了一个全面的数据库健康管理解决方案。通过定期验证、自动修复和性能优化，它能够确保数据库的稳定性、完整性和性能。结合适当的监控和维护策略，可以大大降低数据库问题的风险，提高系统的可靠性。