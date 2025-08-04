# 数据库存储系统设计文档

## 概述

本设计文档描述了将现有JSON文件存储系统升级为SQLite数据库存储系统的技术方案。系统将提供更好的数据完整性、查询性能和用户体验，同时保持向后兼容性。

## 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    GUI Layer                                │
├─────────────────────────────────────────────────────────────┤
│  DatabaseSettingsDialog  │  StorageInfoDialog  │ MainWindow │
├─────────────────────────────────────────────────────────────┤
│                  Business Logic Layer                       │
├─────────────────────────────────────────────────────────────┤
│  ProjectManager  │  DatabaseManager  │  MigrationService   │
├─────────────────────────────────────────────────────────────┤
│                   Data Access Layer                         │
├─────────────────────────────────────────────────────────────┤
│  DatabaseStorage │  ProjectRepository │  ConfigRepository  │
├─────────────────────────────────────────────────────────────┤
│                    Database Layer                           │
├─────────────────────────────────────────────────────────────┤
│              SQLite Database Engine                         │
└─────────────────────────────────────────────────────────────┘
```

## 组件设计

### 1. DatabaseManager

负责数据库连接管理、初始化和配置。

```python
class DatabaseManager:
    def __init__(self, db_path: str = None)
    def connect(self) -> bool
    def disconnect(self) -> None
    def initialize_database(self) -> bool
    def migrate_database(self) -> bool
    def backup_database(self, backup_path: str) -> bool
    def restore_database(self, backup_path: str) -> bool
    def get_connection_info(self) -> dict
    def test_connection(self) -> bool
```

### 2. DatabaseStorage

替代现有的ProjectStorage，提供基于SQLite的数据存储。

```python
class DatabaseStorage:
    def __init__(self, db_manager: DatabaseManager)
    def save_project(self, project: Project) -> bool
    def load_project(self, project_id: str) -> Optional[Project]
    def load_all_projects(self) -> List[Project]
    def delete_project(self, project_id: str) -> bool
    def search_projects(self, query: str) -> List[Project]
    def save_global_config(self, config: GlobalConfig) -> bool
    def load_global_config(self) -> GlobalConfig
```

### 3. ProjectRepository

提供项目数据的CRUD操作和高级查询功能。

```python
class ProjectRepository:
    def __init__(self, db_manager: DatabaseManager)
    def create(self, project: Project) -> bool
    def read(self, project_id: str) -> Optional[Project]
    def update(self, project: Project) -> bool
    def delete(self, project_id: str) -> bool
    def find_by_name(self, name: str) -> List[Project]
    def find_recent(self, limit: int = 10) -> List[Project]
    def find_by_tag(self, tag: str) -> List[Project]
```

### 4. MigrationService

处理从JSON文件到数据库的数据迁移。

```python
class MigrationService:
    def __init__(self, db_manager: DatabaseManager)
    def detect_legacy_data(self) -> bool
    def migrate_from_json(self, json_path: str) -> bool
    def validate_migration(self) -> bool
    def backup_legacy_data(self) -> bool
```

### 5. DatabaseSettingsDialog

提供数据库设置和管理的GUI界面。

```python
class DatabaseSettingsDialog(QDialog):
    def __init__(self, parent=None)
    def init_ui(self) -> None
    def load_current_settings(self) -> None
    def browse_database_file(self) -> None
    def test_connection(self) -> None
    def backup_database(self) -> None
    def restore_database(self) -> None
    def migrate_data(self) -> None
```

## 数据模型设计

### 数据库表结构

#### projects 表
```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    swagger_source_type TEXT NOT NULL,
    swagger_source_location TEXT NOT NULL,
    swagger_source_last_modified DATETIME,
    base_url TEXT,
    auth_config TEXT, -- JSON格式，加密存储
    created_at DATETIME NOT NULL,
    last_accessed DATETIME NOT NULL,
    api_count INTEGER DEFAULT 0,
    ui_state TEXT, -- JSON格式
    tags TEXT, -- JSON数组格式
    version INTEGER DEFAULT 1
);
```

#### global_config 表
```sql
CREATE TABLE global_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    type TEXT NOT NULL, -- 'string', 'json', 'encrypted'
    updated_at DATETIME NOT NULL
);
```

#### database_info 表
```sql
CREATE TABLE database_info (
    version INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    last_migration DATETIME,
    schema_hash TEXT
);
```

#### project_history 表
```sql
CREATE TABLE project_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    action TEXT NOT NULL, -- 'created', 'updated', 'accessed', 'deleted'
    timestamp DATETIME NOT NULL,
    details TEXT, -- JSON格式
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

### 索引设计

```sql
-- 项目查询优化
CREATE INDEX idx_projects_name ON projects(name);
CREATE INDEX idx_projects_last_accessed ON projects(last_accessed DESC);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);

-- 历史记录查询优化
CREATE INDEX idx_history_project_id ON project_history(project_id);
CREATE INDEX idx_history_timestamp ON project_history(timestamp DESC);

-- 配置查询优化
CREATE INDEX idx_config_key ON global_config(key);
```

## 安全设计

### 数据加密

1. **敏感字段加密**：
   - API密钥和认证信息使用AES-256加密
   - 使用PBKDF2派生加密密钥
   - 每个敏感字段使用独立的初始化向量

2. **密钥管理**：
   - 主密码存储在系统密钥环中
   - 支持密码提示和安全问题
   - 提供密码重置机制

### 数据完整性

1. **事务管理**：
   - 所有写操作使用事务
   - 支持回滚和错误恢复
   - 定期数据完整性检查

2. **备份策略**：
   - 自动定期备份
   - 增量备份支持
   - 备份文件完整性验证

## 性能优化

### 查询优化

1. **索引策略**：
   - 为常用查询字段创建索引
   - 复合索引优化复杂查询
   - 定期分析查询性能

2. **连接池**：
   - 使用连接池管理数据库连接
   - 支持连接复用和超时管理
   - 异步操作支持

### 缓存策略

1. **内存缓存**：
   - 热点数据内存缓存
   - LRU缓存淘汰策略
   - 缓存一致性保证

2. **查询缓存**：
   - 频繁查询结果缓存
   - 智能缓存失效
   - 缓存命中率监控

## 错误处理

### 异常分类

1. **连接异常**：
   - 数据库文件不存在
   - 权限不足
   - 磁盘空间不足

2. **数据异常**：
   - 数据格式错误
   - 约束违反
   - 数据损坏

3. **操作异常**：
   - 并发冲突
   - 事务失败
   - 超时错误

### 恢复策略

1. **自动恢复**：
   - 连接重试机制
   - 事务自动回滚
   - 数据自动修复

2. **用户干预**：
   - 错误信息展示
   - 手动恢复选项
   - 技术支持信息

## 测试策略

### 单元测试

1. **数据访问层测试**：
   - CRUD操作测试
   - 事务处理测试
   - 异常处理测试

2. **业务逻辑测试**：
   - 项目管理功能测试
   - 数据迁移测试
   - 配置管理测试

### 集成测试

1. **数据库集成测试**：
   - 多表关联查询测试
   - 数据一致性测试
   - 性能基准测试

2. **GUI集成测试**：
   - 用户界面交互测试
   - 数据绑定测试
   - 错误处理测试

### 性能测试

1. **负载测试**：
   - 大量数据处理测试
   - 并发操作测试
   - 内存使用测试

2. **压力测试**：
   - 极限数据量测试
   - 长时间运行测试
   - 资源耗尽测试

## 部署考虑

### 数据库文件管理

1. **默认位置**：
   - Windows: `%APPDATA%\SwaggerAPITester\database.db`
   - macOS: `~/Library/Application Support/SwaggerAPITester/database.db`
   - Linux: `~/.local/share/SwaggerAPITester/database.db`

2. **便携模式**：
   - 数据库文件位于应用程序目录
   - 支持相对路径配置
   - 便于整体迁移

### 版本兼容性

1. **向前兼容**：
   - 支持旧版本数据库
   - 自动数据库升级
   - 升级失败回滚

2. **向后兼容**：
   - 保留JSON导出功能
   - 数据格式转换工具
   - 降级支持（有限）

## 监控和维护

### 运行时监控

1. **性能监控**：
   - 查询执行时间
   - 数据库文件大小
   - 内存使用情况

2. **错误监控**：
   - 异常发生频率
   - 错误类型统计
   - 用户操作日志

### 维护工具

1. **数据库维护**：
   - 数据库压缩工具
   - 索引重建工具
   - 数据完整性检查

2. **诊断工具**：
   - 连接诊断工具
   - 性能分析工具
   - 数据导出工具