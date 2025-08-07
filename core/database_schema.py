#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库模式定义
定义所有数据库表结构、索引和约束
"""

from typing import Dict, List


class DatabaseSchema:
    """数据库模式类"""
    
    # 当前模式版本
    SCHEMA_VERSION = 2
    
    # 表创建SQL语句
    TABLES: Dict[str, str] = {
        'database_info': '''
            CREATE TABLE IF NOT EXISTS database_info (
                version INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                last_migration DATETIME,
                schema_hash TEXT,
                notes TEXT
            )
        ''',
        
        'projects': '''
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                swagger_source_type TEXT NOT NULL CHECK (swagger_source_type IN ('url', 'file')),
                swagger_source_location TEXT NOT NULL,
                swagger_source_last_modified DATETIME,
                base_url TEXT,
                auth_config TEXT,  -- JSON格式，可能加密
                created_at DATETIME NOT NULL,
                last_accessed DATETIME NOT NULL,
                api_count INTEGER DEFAULT 0 CHECK (api_count >= 0),
                ui_state TEXT,  -- JSON格式
                tags TEXT,  -- JSON数组格式
                version INTEGER DEFAULT 1 CHECK (version > 0),
                is_active BOOLEAN DEFAULT 1,
                last_modified DATETIME DEFAULT CURRENT_TIMESTAMP,
                swagger_data TEXT  -- JSON格式，缓存的Swagger文档数据
            )
        ''',
        
        'global_config': '''
            CREATE TABLE IF NOT EXISTS global_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('string', 'json', 'encrypted', 'boolean', 'integer', 'float')),
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                is_system BOOLEAN DEFAULT 0  -- 系统配置项不允许用户删除
            )
        ''',
        
        'project_history': '''
            CREATE TABLE IF NOT EXISTS project_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                action TEXT NOT NULL CHECK (action IN ('created', 'updated', 'accessed', 'deleted', 'exported', 'imported')),
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                details TEXT,  -- JSON格式，存储操作详情
                user_agent TEXT,  -- 操作来源信息
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        ''',
        
        'api_cache': '''
            CREATE TABLE IF NOT EXISTS api_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                endpoint_path TEXT NOT NULL,
                method TEXT NOT NULL CHECK (method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS')),
                request_hash TEXT NOT NULL,  -- 请求参数的哈希值
                response_data TEXT,  -- JSON格式的响应数据
                response_status INTEGER,
                response_time REAL,  -- 响应时间（毫秒）
                cached_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, endpoint_path, method, request_hash)
            )
        ''',
        
        'user_preferences': '''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,  -- 'ui', 'editor', 'network', etc.
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('string', 'json', 'boolean', 'integer', 'float')),
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, key)
            )
        ''',
        
        'test_history': '''
            CREATE TABLE IF NOT EXISTS test_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                api_path TEXT NOT NULL,
                method TEXT NOT NULL,
                api_summary TEXT,  -- API描述
                url TEXT NOT NULL,
                status_code INTEGER,
                request_headers TEXT,  -- JSON格式
                request_params TEXT,  -- JSON格式，包含path_params, query_params, request_body
                response_headers TEXT,  -- JSON格式
                response_body TEXT,  -- JSON格式
                response_time REAL,  -- 响应时间（秒）
                error_message TEXT,
                custom_data TEXT,  -- JSON格式，存储额外的自定义数据
                test_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                use_auth BOOLEAN DEFAULT 0,
                auth_type TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        ''',

        'swagger_documents': '''
            CREATE TABLE IF NOT EXISTS swagger_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                content TEXT NOT NULL,  -- 完整的Swagger文档内容（JSON/YAML）
                content_hash TEXT NOT NULL,  -- 内容哈希值，用于检测变化
                version TEXT,  -- Swagger文档版本（从info.version字段）
                title TEXT,  -- API标题（从info.title字段）
                description TEXT,  -- API描述（从info.description字段）
                base_path TEXT,  -- API基础路径
                host TEXT,  -- API主机
                schemes TEXT,  -- 支持的协议（JSON数组）
                consumes TEXT,  -- 支持的请求媒体类型（JSON数组）
                produces TEXT,  -- 支持的响应媒体类型（JSON数组）
                api_count INTEGER DEFAULT 0,  -- API数量
                cached_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,  -- 缓存过期时间
                is_current BOOLEAN DEFAULT 1,  -- 是否为当前版本
                source_url TEXT,  -- 原始URL（如果从URL加载）
                source_etag TEXT,  -- HTTP ETag（用于缓存验证）
                source_last_modified DATETIME,  -- 源文档最后修改时间
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        ''',

        'swagger_apis': '''
            CREATE TABLE IF NOT EXISTS swagger_apis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                project_id TEXT NOT NULL,
                path TEXT NOT NULL,
                method TEXT NOT NULL CHECK (method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS')),
                operation_id TEXT,  -- operationId字段
                summary TEXT,  -- API摘要
                description TEXT,  -- API详细描述
                tags TEXT,  -- 标签（JSON数组）
                parameters TEXT,  -- 参数定义（JSON）
                request_body TEXT,  -- 请求体定义（JSON）
                responses TEXT,  -- 响应定义（JSON）
                security TEXT,  -- 安全要求（JSON）
                deprecated BOOLEAN DEFAULT 0,  -- 是否已废弃
                external_docs TEXT,  -- 外部文档（JSON）
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES swagger_documents(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(document_id, path, method)
            )
        '''
    }
    
    # 索引创建SQL语句
    INDEXES: List[str] = [
        # projects表索引
        'CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name)',
        'CREATE INDEX IF NOT EXISTS idx_projects_last_accessed ON projects(last_accessed DESC)',
        'CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC)',
        'CREATE INDEX IF NOT EXISTS idx_projects_active ON projects(is_active)',
        'CREATE INDEX IF NOT EXISTS idx_projects_last_modified ON projects(last_modified DESC)',
        
        # project_history表索引
        'CREATE INDEX IF NOT EXISTS idx_history_project_id ON project_history(project_id)',
        'CREATE INDEX IF NOT EXISTS idx_history_timestamp ON project_history(timestamp DESC)',
        'CREATE INDEX IF NOT EXISTS idx_history_action ON project_history(action)',
        'CREATE INDEX IF NOT EXISTS idx_history_project_action ON project_history(project_id, action)',
        
        # global_config表索引
        'CREATE INDEX IF NOT EXISTS idx_config_key ON global_config(key)',
        'CREATE INDEX IF NOT EXISTS idx_config_type ON global_config(type)',
        'CREATE INDEX IF NOT EXISTS idx_config_system ON global_config(is_system)',
        
        # api_cache表索引
        'CREATE INDEX IF NOT EXISTS idx_cache_project_id ON api_cache(project_id)',
        'CREATE INDEX IF NOT EXISTS idx_cache_expires ON api_cache(expires_at)',
        'CREATE INDEX IF NOT EXISTS idx_cache_cached_at ON api_cache(cached_at DESC)',
        'CREATE INDEX IF NOT EXISTS idx_cache_endpoint ON api_cache(project_id, endpoint_path, method)',
        
        # user_preferences表索引
        'CREATE INDEX IF NOT EXISTS idx_preferences_category ON user_preferences(category)',
        'CREATE INDEX IF NOT EXISTS idx_preferences_updated ON user_preferences(updated_at DESC)',
        
        # test_history表索引
        'CREATE INDEX IF NOT EXISTS idx_test_history_project_id ON test_history(project_id)',
        'CREATE INDEX IF NOT EXISTS idx_test_history_timestamp ON test_history(test_timestamp DESC)',
        'CREATE INDEX IF NOT EXISTS idx_test_history_api_path ON test_history(api_path)',
        'CREATE INDEX IF NOT EXISTS idx_test_history_method ON test_history(method)',
        'CREATE INDEX IF NOT EXISTS idx_test_history_status_code ON test_history(status_code)',
        'CREATE INDEX IF NOT EXISTS idx_test_history_project_api ON test_history(project_id, api_path, method)',

        # swagger_documents表索引
        'CREATE INDEX IF NOT EXISTS idx_swagger_documents_project_id ON swagger_documents(project_id)',
        'CREATE INDEX IF NOT EXISTS idx_swagger_documents_hash ON swagger_documents(content_hash)',
        'CREATE INDEX IF NOT EXISTS idx_swagger_documents_current ON swagger_documents(project_id, is_current)',
        'CREATE INDEX IF NOT EXISTS idx_swagger_documents_cached_at ON swagger_documents(cached_at)',
        'CREATE INDEX IF NOT EXISTS idx_swagger_documents_expires_at ON swagger_documents(expires_at)',

        # swagger_apis表索引
        'CREATE INDEX IF NOT EXISTS idx_swagger_apis_document_id ON swagger_apis(document_id)',
        'CREATE INDEX IF NOT EXISTS idx_swagger_apis_project_id ON swagger_apis(project_id)',
        'CREATE INDEX IF NOT EXISTS idx_swagger_apis_path_method ON swagger_apis(path, method)',
        'CREATE INDEX IF NOT EXISTS idx_swagger_apis_tags ON swagger_apis(tags)',
        'CREATE INDEX IF NOT EXISTS idx_swagger_apis_operation_id ON swagger_apis(operation_id)'
    ]
    
    # 触发器创建SQL语句
    TRIGGERS: List[str] = [
        # 自动更新projects表的last_modified字段
        '''
        CREATE TRIGGER IF NOT EXISTS trigger_projects_update_timestamp
        AFTER UPDATE ON projects
        FOR EACH ROW
        BEGIN
            UPDATE projects SET last_modified = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END
        ''',
        
        # 自动记录项目操作历史
        '''
        CREATE TRIGGER IF NOT EXISTS trigger_projects_history_insert
        AFTER INSERT ON projects
        FOR EACH ROW
        BEGIN
            INSERT INTO project_history (project_id, action, details)
            VALUES (NEW.id, 'created', json_object('name', NEW.name, 'description', NEW.description));
        END
        ''',
        
        '''
        CREATE TRIGGER IF NOT EXISTS trigger_projects_history_update
        AFTER UPDATE ON projects
        FOR EACH ROW
        WHEN OLD.last_accessed != NEW.last_accessed OR OLD.name != NEW.name OR OLD.description != NEW.description
        BEGIN
            INSERT INTO project_history (project_id, action, details)
            VALUES (NEW.id, 'updated', json_object(
                'old_name', OLD.name, 'new_name', NEW.name,
                'old_description', OLD.description, 'new_description', NEW.description
            ));
        END
        ''',
        
        # 清理过期的API缓存
        '''
        CREATE TRIGGER IF NOT EXISTS trigger_cleanup_expired_cache
        AFTER INSERT ON api_cache
        FOR EACH ROW
        BEGIN
            DELETE FROM api_cache WHERE expires_at < CURRENT_TIMESTAMP;
        END
        '''
    ]
    
    # 视图创建SQL语句
    VIEWS: List[str] = [
        # 项目统计视图
        '''
        CREATE VIEW IF NOT EXISTS view_project_stats AS
        SELECT 
            p.id,
            p.name,
            p.description,
            p.created_at,
            p.last_accessed,
            p.api_count,
            COUNT(DISTINCT h.id) as history_count,
            COUNT(DISTINCT c.id) as cache_count,
            MAX(h.timestamp) as last_activity
        FROM projects p
        LEFT JOIN project_history h ON p.id = h.project_id
        LEFT JOIN api_cache c ON p.id = c.project_id
        WHERE p.is_active = 1
        GROUP BY p.id, p.name, p.description, p.created_at, p.last_accessed, p.api_count
        ''',
        
        # 最近活动视图
        '''
        CREATE VIEW IF NOT EXISTS view_recent_activity AS
        SELECT 
            h.id,
            h.project_id,
            p.name as project_name,
            h.action,
            h.timestamp,
            h.details
        FROM project_history h
        JOIN projects p ON h.project_id = p.id
        WHERE p.is_active = 1
        ORDER BY h.timestamp DESC
        LIMIT 100
        '''
    ]
    
    # 初始数据插入SQL语句
    INITIAL_DATA: List[str] = [
        # 插入系统配置项
        '''
        INSERT OR IGNORE INTO global_config (key, value, type, description, is_system)
        VALUES 
            ('app_version', '1.0.0', 'string', '应用程序版本', 1),
            ('database_version', '1', 'integer', '数据库版本', 1),
            ('auto_backup_enabled', 'true', 'boolean', '自动备份启用状态', 0),
            ('backup_interval_days', '7', 'integer', '备份间隔天数', 0),
            ('max_cache_size_mb', '100', 'integer', '最大缓存大小(MB)', 0),
            ('cache_expiry_hours', '24', 'integer', '缓存过期时间(小时)', 0),
            ('theme', 'default', 'string', '界面主题', 0),
            ('language', 'zh_CN', 'string', '界面语言', 0)
        ''',
        
        # 插入用户偏好设置
        '''
        INSERT OR IGNORE INTO user_preferences (category, key, value, type)
        VALUES 
            ('ui', 'window_width', '1200', 'integer'),
            ('ui', 'window_height', '800', 'integer'),
            ('ui', 'window_maximized', 'false', 'boolean'),
            ('editor', 'font_size', '12', 'integer'),
            ('editor', 'font_family', 'Consolas', 'string'),
            ('editor', 'tab_size', '4', 'integer'),
            ('network', 'timeout_seconds', '30', 'integer'),
            ('network', 'retry_count', '3', 'integer')
        '''
    ]
    
    @classmethod
    def get_all_creation_statements(cls) -> List[str]:
        """
        获取所有创建语句
        
        Returns:
            List[str]: 所有SQL创建语句的列表
        """
        statements = []
        
        # 添加表创建语句
        statements.extend(cls.TABLES.values())
        
        # 添加索引创建语句
        statements.extend(cls.INDEXES)
        
        # 添加触发器创建语句
        statements.extend(cls.TRIGGERS)
        
        # 添加视图创建语句
        statements.extend(cls.VIEWS)
        
        return statements
    
    @classmethod
    def get_table_names(cls) -> List[str]:
        """
        获取所有表名
        
        Returns:
            List[str]: 表名列表
        """
        return list(cls.TABLES.keys())
    
    @classmethod
    def validate_schema_version(cls, current_version: int) -> bool:
        """
        验证模式版本
        
        Args:
            current_version: 当前数据库版本
            
        Returns:
            bool: 版本是否兼容
        """
        return current_version <= cls.SCHEMA_VERSION
    
    @classmethod
    def get_migration_statements(cls, from_version: int, to_version: int) -> List[str]:
        """
        获取数据库迁移语句
        
        Args:
            from_version: 源版本
            to_version: 目标版本
            
        Returns:
            List[str]: 迁移SQL语句列表
        """
        migrations = []
        
        # 这里可以根据版本添加具体的迁移语句
        if from_version < 1 and to_version >= 1:
            # 从版本0迁移到版本1的语句
            migrations.extend([
                'ALTER TABLE projects ADD COLUMN is_active BOOLEAN DEFAULT 1',
                'ALTER TABLE projects ADD COLUMN last_modified DATETIME DEFAULT CURRENT_TIMESTAMP',
                'ALTER TABLE global_config ADD COLUMN description TEXT',
                'ALTER TABLE global_config ADD COLUMN is_system BOOLEAN DEFAULT 0'
            ])
        
        return migrations
    
    @classmethod
    def calculate_schema_hash(cls) -> str:
        """
        计算当前schema的哈希值
        
        Returns:
            str: schema哈希值
        """
        import json
        import hashlib
        
        try:
            # 收集所有schema定义
            schema_content = {
                'tables': cls.TABLES,
                'indexes': cls.INDEXES,
                'triggers': cls.TRIGGERS,
                'views': cls.VIEWS,
                'version': cls.SCHEMA_VERSION
            }
            
            # 转换为JSON字符串并计算哈希
            schema_json = json.dumps(schema_content, sort_keys=True, ensure_ascii=False)
            return hashlib.sha256(schema_json.encode('utf-8')).hexdigest()
            
        except Exception:
            return ""