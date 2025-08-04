#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
用于在应用程序首次启动或部署时初始化数据库
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database_manager import DatabaseManager
from core.database_schema import DatabaseSchema
from core.migration_service import MigrationService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """数据库初始化器"""
    
    def __init__(self, db_path=None):
        """
        初始化数据库初始化器
        
        Args:
            db_path: 数据库文件路径，如果为None则使用默认路径
        """
        if db_path is None:
            # 确定默认数据库路径
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller打包环境
                app_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境
                app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # 检查是否为便携模式
            portable_file = os.path.join(app_dir, 'portable.txt')
            if os.path.exists(portable_file):
                # 便携模式：数据存储在应用程序目录
                data_dir = os.path.join(app_dir, 'data')
            else:
                # 标准模式：数据存储在用户文档目录
                if sys.platform == 'win32':
                    data_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'ProjectManager')
                else:
                    data_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'ProjectManager')
            
            # 确保数据目录存在
            os.makedirs(data_dir, exist_ok=True)
            self.db_path = os.path.join(data_dir, 'database.db')
        else:
            self.db_path = db_path
        
        self.data_dir = os.path.dirname(self.db_path)
        logger.info(f"数据库路径: {self.db_path}")
        logger.info(f"数据目录: {self.data_dir}")
    
    def check_existing_data(self):
        """检查是否存在旧的JSON数据文件"""
        json_files = []
        
        # 检查常见的JSON数据文件
        potential_files = [
            'projects.json',
            'config.json',
            'settings.json',
            'data.json'
        ]
        
        for filename in potential_files:
            file_path = os.path.join(self.data_dir, filename)
            if os.path.exists(file_path):
                json_files.append(file_path)
                logger.info(f"发现JSON数据文件: {file_path}")
        
        return json_files
    
    def initialize_database(self, force=False):
        """
        初始化数据库
        
        Args:
            force: 是否强制重新初始化（会删除现有数据库）
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 检查数据库是否已存在
            if os.path.exists(self.db_path) and not force:
                logger.info("数据库文件已存在，跳过初始化")
                return True
            
            if force and os.path.exists(self.db_path):
                logger.warning("强制重新初始化，删除现有数据库")
                os.remove(self.db_path)
            
            logger.info("开始初始化数据库...")
            
            # 创建数据库管理器
            db_manager = DatabaseManager(self.db_path)
            
            # 验证数据库创建成功
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                expected_tables = ['projects', 'global_config', 'database_info', 'project_history']
                for table in expected_tables:
                    if table not in tables:
                        logger.error(f"表 {table} 未创建成功")
                        return False
                
                logger.info(f"成功创建 {len(tables)} 个数据表")
            
            # 设置数据库信息
            db_info = {
                'version': '2.0.0',
                'created_at': datetime.now().isoformat(),
                'initialized_by': 'init_script',
                'schema_version': DatabaseSchema.CURRENT_VERSION
            }
            db_manager.update_database_info(db_info)
            
            db_manager.close()
            logger.info("数据库初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            return False
    
    def migrate_existing_data(self, json_files):
        """
        迁移现有的JSON数据
        
        Args:
            json_files: JSON文件列表
        
        Returns:
            bool: 迁移是否成功
        """
        if not json_files:
            logger.info("没有发现需要迁移的JSON数据文件")
            return True
        
        try:
            logger.info(f"开始迁移 {len(json_files)} 个JSON数据文件...")
            
            # 查找主要的项目数据文件
            projects_file = None
            for file_path in json_files:
                if 'projects' in os.path.basename(file_path).lower():
                    projects_file = file_path
                    break
            
            if not projects_file:
                # 如果没有找到projects文件，使用第一个JSON文件
                projects_file = json_files[0]
            
            logger.info(f"使用 {projects_file} 作为主数据文件")
            
            # 创建迁移服务
            migration_service = MigrationService(projects_file, self.db_path)
            
            # 执行迁移
            success = migration_service.migrate_to_database()
            
            if success:
                logger.info("数据迁移完成")
                
                # 创建备份目录
                backup_dir = os.path.join(self.data_dir, 'json_backup')
                os.makedirs(backup_dir, exist_ok=True)
                
                # 备份原始JSON文件
                import shutil
                for json_file in json_files:
                    backup_path = os.path.join(backup_dir, os.path.basename(json_file))
                    shutil.copy2(json_file, backup_path)
                    logger.info(f"备份JSON文件: {json_file} -> {backup_path}")
                
                return True
            else:
                logger.error("数据迁移失败")
                return False
                
        except Exception as e:
            logger.error(f"数据迁移过程中出错: {e}")
            return False
    
    def setup_directories(self):
        """设置必要的目录结构"""
        directories = [
            'backups',
            'logs',
            'temp',
            'exports'
        ]
        
        for dir_name in directories:
            dir_path = os.path.join(self.data_dir, dir_name)
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"创建目录: {dir_path}")
    
    def create_default_config(self):
        """创建默认配置"""
        try:
            from core.database_storage import DatabaseStorage
            
            storage = DatabaseStorage(self.db_path)
            
            # 设置默认全局配置
            default_config = {
                'theme': 'light',
                'language': 'zh-CN',
                'auto_backup': True,
                'backup_frequency': 'daily',
                'max_backups': 10,
                'enable_logging': True,
                'log_level': 'INFO',
                'database_cache_size': 64,  # MB
                'query_timeout': 30,  # 秒
                'enable_encryption': False
            }
            
            for key, value in default_config.items():
                storage.set_global_config(key, value)
                logger.info(f"设置默认配置: {key} = {value}")
            
            storage.close()
            logger.info("默认配置创建完成")
            
        except Exception as e:
            logger.error(f"创建默认配置失败: {e}")
    
    def run_full_initialization(self, force=False):
        """
        运行完整的初始化过程
        
        Args:
            force: 是否强制重新初始化
        
        Returns:
            bool: 初始化是否成功
        """
        logger.info("开始完整的数据库初始化过程...")
        
        try:
            # 1. 设置目录结构
            self.setup_directories()
            
            # 2. 检查现有数据
            json_files = self.check_existing_data()
            
            # 3. 初始化数据库
            if not self.initialize_database(force):
                return False
            
            # 4. 迁移现有数据
            if json_files:
                if not self.migrate_existing_data(json_files):
                    logger.warning("数据迁移失败，但数据库初始化成功")
            
            # 5. 创建默认配置
            self.create_default_config()
            
            logger.info("完整的数据库初始化过程完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化过程失败: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库初始化脚本')
    parser.add_argument('--db-path', help='数据库文件路径')
    parser.add_argument('--force', action='store_true', help='强制重新初始化')
    parser.add_argument('--verbose', action='store_true', help='显示详细日志')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 创建初始化器
    initializer = DatabaseInitializer(args.db_path)
    
    # 运行初始化
    success = initializer.run_full_initialization(args.force)
    
    if success:
        print("数据库初始化成功！")
        sys.exit(0)
    else:
        print("数据库初始化失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()