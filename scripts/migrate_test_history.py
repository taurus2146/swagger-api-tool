#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试历史数据迁移脚本
将JSON文件中的历史记录迁移到SQLite数据库
"""

import os
import sys
import json
import logging
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database_manager import DatabaseManager
from core.test_history_repository import TestHistoryRepository

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_test_history():
    """执行测试历史数据迁移"""
    # JSON文件路径
    json_file_path = os.path.join('config', 'test_history.json')
    
    if not os.path.exists(json_file_path):
        logger.warning(f"历史记录文件不存在: {json_file_path}")
        return
    
    # 初始化数据库管理器
    db_manager = DatabaseManager()
    
    # 初始化测试历史仓库
    test_history_repo = TestHistoryRepository(db_manager)
    
    try:
        # 读取JSON文件
        with open(json_file_path, 'r', encoding='utf-8') as f:
            test_history = json.load(f)
        
        logger.info(f"读取到 {len(test_history)} 条历史记录")
        
        # 迁移计数
        migrated_count = 0
        error_count = 0
        
        # 按项目分组历史记录
        project_histories = {}
        
        for history_entry in test_history:
            # 尝试从API信息中提取项目ID（这里需要根据实际数据结构调整）
            # 如果历史记录中没有项目ID，可能需要使用默认项目ID
            project_id = history_entry.get('project_id', 'default')
            
            if project_id not in project_histories:
                project_histories[project_id] = []
            
            project_histories[project_id].append(history_entry)
        
        # 迁移每个项目的历史记录
        for project_id, histories in project_histories.items():
            logger.info(f"迁移项目 {project_id} 的 {len(histories)} 条记录...")
            
            for history_entry in histories:
                try:
                    # 确保有时间戳
                    if 'timestamp' not in history_entry:
                        history_entry['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 添加到数据库
                    test_history_repo.add_test_history(project_id, history_entry)
                    migrated_count += 1
                    
                except Exception as e:
                    logger.error(f"迁移记录失败: {e}")
                    logger.error(f"失败的记录: {history_entry}")
                    error_count += 1
        
        logger.info(f"迁移完成: 成功 {migrated_count} 条, 失败 {error_count} 条")
        
        # 备份原始JSON文件
        if migrated_count > 0:
            backup_path = json_file_path + '.backup'
            os.rename(json_file_path, backup_path)
            logger.info(f"原始文件已备份到: {backup_path}")
            
    except Exception as e:
        logger.error(f"迁移过程出错: {e}")
        raise
    finally:
        db_manager.close()


def verify_migration(project_id='default'):
    """验证迁移结果"""
    db_manager = DatabaseManager()
    test_history_repo = TestHistoryRepository(db_manager)
    
    try:
        # 获取统计信息
        stats = test_history_repo.get_test_history_stats(project_id)
        logger.info(f"项目 {project_id} 的统计信息:")
        logger.info(f"  总记录数: {stats['total_count']}")
        logger.info(f"  唯一API数: {stats['unique_apis']}")
        logger.info(f"  成功请求数: {stats['success_count']}")
        logger.info(f"  失败请求数: {stats['failure_count']}")
        
        # 获取最近的几条记录
        recent_records = test_history_repo.get_test_history(project_id, limit=5)
        logger.info(f"\n最近的 {len(recent_records)} 条记录:")
        for record in recent_records:
            api_info = record.get('api', {})
            response = record.get('response', {})
            logger.info(f"  - {record.get('timestamp')} | {api_info.get('method')} {api_info.get('path')} | Status: {response.get('status_code')}")
            
    finally:
        db_manager.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='测试历史数据迁移工具')
    parser.add_argument('--verify', action='store_true', help='验证迁移结果')
    parser.add_argument('--project', default='default', help='项目ID (默认: default)')
    
    args = parser.parse_args()
    
    if args.verify:
        verify_migration(args.project)
    else:
        migrate_test_history()
