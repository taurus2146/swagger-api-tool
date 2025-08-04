#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库升级工具
用于升级数据库结构和数据格式到新版本
"""

import os
import sys
import sqlite3
import logging
import json
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database_manager import DatabaseManager
from core.database_version_manager import DatabaseVersionManager
from core.database_schema import DatabaseSchema

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseUpgrader:
    """数据库升级器"""
    
    def __init__(self, db_path):
        """
        初始化数据库升级器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.backup_path = None
        
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"数据库文件不存在: {db_path}")
        
        logger.info(f"数据库路径: {self.db_path}")
    
    def create_backup(self):
        """创建数据库备份"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = os.path.join(os.path.dirname(self.db_path), 'upgrade_backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            self.backup_path = os.path.join(backup_dir, f'database_backup_{timestamp}.db')
            
            import shutil
            shutil.copy2(self.db_path, self.backup_path)
            
            logger.info(f"数据库备份创建成功: {self.backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"创建数据库备份失败: {e}")
            return False
    
    def get_current_version(self):
        """获取当前数据库版本"""
        try:
            version_manager = DatabaseVersionManager(self.db_path)
            current_version = version_manager.get_current_version()
            version_manager.close()
            return current_version
        except Exception as e:
            logger.error(f"获取数据库版本失败: {e}")
            return None
    
    def get_target_version(self):
        """获取目标版本"""
        return DatabaseSchema.CURRENT_VERSION
    
    def check_upgrade_needed(self):
        """检查是否需要升级"""
        current_version = self.get_current_version()
        target_version = self.get_target_version()
        
        if current_version is None:
            logger.warning("无法确定当前数据库版本")
            return False
        
        logger.info(f"当前版本: {current_version}")
        logger.info(f"目标版本: {target_version}")
        
        return current_version != target_version
    
    def upgrade_from_v1_to_v2(self):
        """从版本1.0升级到2.0"""
        logger.info("执行 v1.0 -> v2.0 升级...")
        
        try:
            db_manager = DatabaseManager(self.db_path)
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 添加新字段到projects表
                try:
                    cursor.execute("ALTER TABLE projects ADD COLUMN priority INTEGER DEFAULT 0")
                    logger.info("添加priority字段到projects表")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e).lower():
                        raise
                
                try:
                    cursor.execute("ALTER TABLE projects ADD COLUMN status TEXT DEFAULT 'active'")
                    logger.info("添加status字段到projects表")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e).lower():
                        raise
                
                # 创建新的索引
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_projects_status 
                    ON projects(status)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_projects_priority 
                    ON projects(priority)
                """)
                
                # 更新数据库信息
                cursor.execute("""
                    UPDATE database_info 
                    SET value = '2.0' 
                    WHERE key = 'version'
                """)
                
                conn.commit()
                logger.info("v1.0 -> v2.0 升级完成")
            
            db_manager.close()
            return True
            
        except Exception as e:
            logger.error(f"v1.0 -> v2.0 升级失败: {e}")
            return False
    
    def upgrade_from_v2_to_v3(self):
        """从版本2.0升级到3.0"""
        logger.info("执行 v2.0 -> v3.0 升级...")
        
        try:
            db_manager = DatabaseManager(self.db_path)
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建新的表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS project_categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        description TEXT,
                        color TEXT DEFAULT '#007ACC',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS project_templates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        template_data TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 添加新字段
                try:
                    cursor.execute("ALTER TABLE projects ADD COLUMN category_id INTEGER")
                    cursor.execute("ALTER TABLE projects ADD COLUMN template_id INTEGER")
                    logger.info("添加category_id和template_id字段到projects表")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e).lower():
                        raise
                
                # 创建外键关系
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_projects_category 
                    ON projects(category_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_projects_template 
                    ON projects(template_id)
                """)
                
                # 插入默认分类
                cursor.execute("""
                    INSERT OR IGNORE INTO project_categories (name, description, color)
                    VALUES 
                    ('Web开发', 'Web应用程序项目', '#007ACC'),
                    ('移动开发', '移动应用程序项目', '#28A745'),
                    ('桌面应用', '桌面应用程序项目', '#FFC107'),
                    ('数据分析', '数据分析和机器学习项目', '#DC3545'),
                    ('其他', '其他类型项目', '#6C757D')
                """)
                
                # 更新版本信息
                cursor.execute("""
                    UPDATE database_info 
                    SET value = '3.0' 
                    WHERE key = 'version'
                """)
                
                conn.commit()
                logger.info("v2.0 -> v3.0 升级完成")
            
            db_manager.close()
            return True
            
        except Exception as e:
            logger.error(f"v2.0 -> v3.0 升级失败: {e}")
            return False
    
    def run_upgrade(self):
        """运行数据库升级"""
        logger.info("开始数据库升级过程...")
        
        try:
            # 检查是否需要升级
            if not self.check_upgrade_needed():
                logger.info("数据库已是最新版本，无需升级")
                return True
            
            # 创建备份
            if not self.create_backup():
                logger.error("创建备份失败，升级中止")
                return False
            
            current_version = self.get_current_version()
            target_version = self.get_target_version()
            
            # 根据版本执行相应的升级步骤
            upgrade_success = True
            
            if current_version == "1.0" and target_version >= "2.0":
                if not self.upgrade_from_v1_to_v2():
                    upgrade_success = False
                else:
                    current_version = "2.0"
            
            if current_version == "2.0" and target_version >= "3.0":
                if not self.upgrade_from_v2_to_v3():
                    upgrade_success = False
                else:
                    current_version = "3.0"
            
            if upgrade_success:
                # 记录升级历史
                self.record_upgrade_history(self.get_current_version(), target_version)
                logger.info(f"数据库升级成功: {self.get_current_version()} -> {target_version}")
                return True
            else:
                # 升级失败，恢复备份
                logger.error("升级失败，正在恢复备份...")
                self.restore_backup()
                return False
                
        except Exception as e:
            logger.error(f"数据库升级过程中出错: {e}")
            if self.backup_path:
                logger.info("正在恢复备份...")
                self.restore_backup()
            return False
    
    def restore_backup(self):
        """从备份恢复数据库"""
        if not self.backup_path or not os.path.exists(self.backup_path):
            logger.error("备份文件不存在，无法恢复")
            return False
        
        try:
            import shutil
            shutil.copy2(self.backup_path, self.db_path)
            logger.info(f"数据库已从备份恢复: {self.backup_path}")
            return True
        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return False
    
    def record_upgrade_history(self, from_version, to_version):
        """记录升级历史"""
        try:
            version_manager = DatabaseVersionManager(self.db_path)
            version_manager.record_upgrade(
                from_version, 
                to_version, 
                f"Automated upgrade from {from_version} to {to_version}"
            )
            version_manager.close()
            logger.info(f"升级历史记录完成: {from_version} -> {to_version}")
        except Exception as e:
            logger.error(f"记录升级历史失败: {e}")
    
    def validate_upgrade(self):
        """验证升级结果"""
        try:
            logger.info("验证升级结果...")
            
            db_manager = DatabaseManager(self.db_path)
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查数据库完整性
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]
                
                if integrity_result != "ok":
                    logger.error(f"数据库完整性检查失败: {integrity_result}")
                    return False
                
                # 检查表结构
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                required_tables = ['projects', 'global_config', 'database_info', 'project_history']
                for table in required_tables:
                    if table not in tables:
                        logger.error(f"必需的表 {table} 不存在")
                        return False
                
                # 检查版本信息
                current_version = self.get_current_version()
                target_version = self.get_target_version()
                
                if current_version != target_version:
                    logger.error(f"版本不匹配: 当前 {current_version}, 期望 {target_version}")
                    return False
                
                logger.info("升级验证通过")
                return True
            
        except Exception as e:
            logger.error(f"升级验证失败: {e}")
            return False
        finally:
            if 'db_manager' in locals():
                db_manager.close()
    
    def cleanup_old_backups(self, keep_count=5):
        """清理旧的备份文件"""
        try:
            backup_dir = os.path.join(os.path.dirname(self.db_path), 'upgrade_backups')
            if not os.path.exists(backup_dir):
                return
            
            # 获取所有备份文件
            backup_files = []
            for filename in os.listdir(backup_dir):
                if filename.startswith('database_backup_') and filename.endswith('.db'):
                    file_path = os.path.join(backup_dir, filename)
                    backup_files.append((file_path, os.path.getmtime(file_path)))
            
            # 按修改时间排序，保留最新的几个
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            if len(backup_files) > keep_count:
                for file_path, _ in backup_files[keep_count:]:
                    os.remove(file_path)
                    logger.info(f"删除旧备份文件: {file_path}")
                
                logger.info(f"清理完成，保留了 {keep_count} 个最新备份")
            
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库升级工具')
    parser.add_argument('db_path', help='数据库文件路径')
    parser.add_argument('--check-only', action='store_true', help='只检查是否需要升级')
    parser.add_argument('--force', action='store_true', help='强制升级（即使版本相同）')
    parser.add_argument('--no-backup', action='store_true', help='跳过备份创建')
    parser.add_argument('--verbose', action='store_true', help='显示详细日志')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not os.path.exists(args.db_path):
        print(f"错误: 数据库文件不存在: {args.db_path}")
        sys.exit(1)
    
    try:
        # 创建升级器
        upgrader = DatabaseUpgrader(args.db_path)
        
        if args.check_only:
            # 只检查是否需要升级
            if upgrader.check_upgrade_needed():
                current = upgrader.get_current_version()
                target = upgrader.get_target_version()
                print(f"需要升级: {current} -> {target}")
                sys.exit(0)
            else:
                print("数据库已是最新版本")
                sys.exit(0)
        
        # 执行升级
        if args.force or upgrader.check_upgrade_needed():
            if args.no_backup:
                logger.warning("跳过备份创建（--no-backup）")
            
            success = upgrader.run_upgrade()
            
            if success:
                # 验证升级结果
                if upgrader.validate_upgrade():
                    print("数据库升级成功！")
                    
                    # 清理旧备份
                    upgrader.cleanup_old_backups()
                    
                    sys.exit(0)
                else:
                    print("升级验证失败！")
                    sys.exit(1)
            else:
                print("数据库升级失败！")
                sys.exit(1)
        else:
            print("数据库已是最新版本，无需升级")
            sys.exit(0)
    
    except Exception as e:
        logger.error(f"升级工具执行失败: {e}")
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()