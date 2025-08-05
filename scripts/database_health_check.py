#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库健康检查和修复工具
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database_manager import DatabaseManager
from core.database_lock_recovery import DatabaseLockRecovery
from core.storage_utils import get_default_database_path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def check_database_health(db_path: str = None):
    """检查数据库健康状态"""
    if not db_path:
        db_path = get_default_database_path()
    
    print("数据库健康检查")
    print("=" * 60)
    print(f"数据库路径: {db_path}")
    print()
    
    # 基本文件检查
    print("1. 基本文件检查")
    print("-" * 30)
    
    if os.path.exists(db_path):
        size = os.path.getsize(db_path)
        print(f"✓ 数据库文件存在")
        print(f"  文件大小: {format_size(size)}")
        print(f"  可读: {'是' if os.access(db_path, os.R_OK) else '否'}")
        print(f"  可写: {'是' if os.access(db_path, os.W_OK) else '否'}")
    else:
        print("✗ 数据库文件不存在")
        return False
    
    # 连接测试
    print("\n2. 连接测试")
    print("-" * 30)
    
    db_manager = DatabaseManager(db_path)
    
    try:
        if db_manager.connect():
            print("✓ 数据库连接成功")
            
            # 获取连接信息
            if hasattr(db_manager, 'connection_manager'):
                conn_info = db_manager.connection_manager.get_connection_info()
                print(f"  连接状态: {'已连接' if conn_info['is_connected'] else '未连接'}")
                if conn_info['last_activity']:
                    print(f"  最后活动: {conn_info['last_activity']}")
        else:
            print("✗ 数据库连接失败")
            return False
    except Exception as e:
        print(f"✗ 连接异常: {e}")
        return False
    
    # 数据库完整性检查
    print("\n3. 数据库完整性检查")
    print("-" * 30)
    
    try:
        # PRAGMA integrity_check
        result = db_manager.execute_query("PRAGMA integrity_check")
        if result and result[0][0] == 'ok':
            print("✓ 数据库完整性检查通过")
        else:
            print("✗ 数据库完整性检查失败")
            if result:
                for row in result[:5]:  # 显示前5个错误
                    print(f"  错误: {row[0]}")
    except Exception as e:
        print(f"✗ 完整性检查异常: {e}")
    
    # 表结构检查
    print("\n4. 表结构检查")
    print("-" * 30)
    
    try:
        tables = db_manager.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
        if tables:
            print(f"✓ 发现 {len(tables)} 个表:")
            for table in tables:
                table_name = table[0]
                count_result = db_manager.execute_query(f"SELECT COUNT(*) FROM {table_name}")
                count = count_result[0][0] if count_result else 0
                print(f"  - {table_name}: {count} 条记录")
        else:
            print("✗ 未发现任何表")
    except Exception as e:
        print(f"✗ 表结构检查异常: {e}")
    
    # WAL模式检查
    print("\n5. WAL模式检查")
    print("-" * 30)
    
    try:
        journal_mode = db_manager.execute_query("PRAGMA journal_mode")
        if journal_mode:
            mode = journal_mode[0][0]
            print(f"✓ 日志模式: {mode}")
            
            if mode.upper() == 'WAL':
                # 检查WAL文件
                wal_file = db_path + '-wal'
                shm_file = db_path + '-shm'
                
                if os.path.exists(wal_file):
                    wal_size = os.path.getsize(wal_file)
                    print(f"  WAL文件: {format_size(wal_size)}")
                
                if os.path.exists(shm_file):
                    shm_size = os.path.getsize(shm_file)
                    print(f"  SHM文件: {format_size(shm_size)}")
    except Exception as e:
        print(f"✗ WAL模式检查异常: {e}")
    
    # 锁定状态检查
    print("\n6. 锁定状态检查")
    print("-" * 30)
    
    recovery_tool = DatabaseLockRecovery(db_path)
    diagnosis = recovery_tool.diagnose_lock_issue()
    
    if diagnosis['database_accessible']:
        print("✓ 数据库无锁定问题")
    else:
        print("✗ 数据库可能被锁定")
        
        if diagnosis['processes_using_db']:
            print(f"  发现 {len(diagnosis['processes_using_db'])} 个进程在使用数据库:")
            for proc in diagnosis['processes_using_db']:
                print(f"    PID {proc['pid']}: {proc['name']}")
        
        if diagnosis['recommendations']:
            print("  建议:")
            for rec in diagnosis['recommendations']:
                print(f"    - {rec}")
    
    # 性能统计
    print("\n7. 性能统计")
    print("-" * 30)
    
    try:
        # 数据库大小
        page_count = db_manager.execute_query("PRAGMA page_count")
        page_size = db_manager.execute_query("PRAGMA page_size")
        
        if page_count and page_size:
            total_pages = page_count[0][0]
            page_size_bytes = page_size[0][0]
            total_size = total_pages * page_size_bytes
            
            print(f"✓ 数据库统计:")
            print(f"  页数: {total_pages}")
            print(f"  页大小: {format_size(page_size_bytes)}")
            print(f"  总大小: {format_size(total_size)}")
        
        # 缓存统计
        cache_size = db_manager.execute_query("PRAGMA cache_size")
        if cache_size:
            print(f"  缓存大小: {cache_size[0][0]} 页")
            
    except Exception as e:
        print(f"✗ 性能统计异常: {e}")
    
    db_manager.disconnect()
    
    print("\n" + "=" * 60)
    print("健康检查完成")
    
    return True


def repair_database(db_path: str = None):
    """修复数据库问题"""
    if not db_path:
        db_path = get_default_database_path()
    
    print("数据库修复工具")
    print("=" * 60)
    print(f"数据库路径: {db_path}")
    print()
    
    recovery_tool = DatabaseLockRecovery(db_path)
    
    # 诊断问题
    print("1. 诊断问题...")
    diagnosis = recovery_tool.diagnose_lock_issue()
    
    if diagnosis['database_accessible']:
        print("✓ 数据库访问正常，无需修复")
        return True
    
    print("✗ 发现数据库问题，开始修复...")
    
    # 尝试自动修复
    print("\n2. 尝试自动修复...")
    recovery_result = recovery_tool.attempt_recovery()
    
    if recovery_result['success']:
        print("✓ 自动修复成功")
        for action in recovery_result['actions_taken']:
            print(f"  - {action}")
        return True
    else:
        print("✗ 自动修复失败")
        for error in recovery_result['errors']:
            print(f"  错误: {error}")
    
    # 询问是否强制修复
    print("\n3. 强制修复选项")
    print("警告: 强制修复可能导致数据丢失")
    
    response = input("是否继续强制修复? (y/N): ").strip().lower()
    if response == 'y':
        print("执行强制修复...")
        if recovery_tool.force_unlock():
            print("✓ 强制修复成功")
            return True
        else:
            print("✗ 强制修复失败")
            return False
    else:
        print("取消强制修复")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库健康检查和修复工具")
    parser.add_argument("--db-path", help="数据库文件路径")
    parser.add_argument("--repair", action="store_true", help="修复数据库问题")
    parser.add_argument("--check", action="store_true", help="检查数据库健康状态")
    
    args = parser.parse_args()
    
    if not args.check and not args.repair:
        args.check = True  # 默认执行检查
    
    success = True
    
    if args.check:
        success = check_database_health(args.db_path)
    
    if args.repair and success:
        success = repair_database(args.db_path)
    
    if success:
        print("\n✅ 操作完成")
    else:
        print("\n❌ 操作失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
