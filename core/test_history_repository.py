#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试历史数据库访问层
负责测试历史记录的数据库操作
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class TestHistoryRepository:
    """测试历史数据库访问类"""
    
    def __init__(self, db_manager):
        """
        初始化测试历史仓库
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
    
    @contextmanager
    def _get_cursor(self):
        """获取数据库游标的上下文管理器"""
        if not self.db_manager._is_connected:
            raise RuntimeError("数据库未连接")
        cursor = self.db_manager._connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    
    def add_test_history(self, project_id: str, test_result: Dict[str, Any]) -> Optional[int]:
        """
        添加测试历史记录
        
        Args:
            project_id: 项目ID
            test_result: 测试结果数据
            
        Returns:
            Optional[int]: 插入的记录ID，失败返回None
        """
        try:
            with self._get_cursor() as cursor:
                # 提取数据
                api_info = test_result.get('api', {})
                response = test_result.get('response', {})
                
                # 准备请求参数JSON
                request_params = {
                    'path_params': test_result.get('path_params', {}),
                    'query_params': test_result.get('query_params', {}),
                    'request_body': test_result.get('request_body', {})
                }
                
                # 准备插入数据
                cursor.execute('''
                    INSERT INTO test_history (
                        project_id, api_path, method, api_summary, url,
                        status_code, request_headers, request_params,
                        response_headers, response_body, response_time,
                        error_message, custom_data, test_timestamp,
                        use_auth, auth_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_id,
                    api_info.get('path', ''),
                    api_info.get('method', test_result.get('method', '')),
                    api_info.get('summary', ''),
                    test_result.get('url', ''),
                    response.get('status_code'),
                    json.dumps(test_result.get('headers', {}), ensure_ascii=False),
                    json.dumps(request_params, ensure_ascii=False),
                    json.dumps(response.get('headers', {}), ensure_ascii=False),
                    json.dumps(response.get('body'), ensure_ascii=False) if response.get('body') else None,
                    response.get('elapsed', 0),
                    test_result.get('error'),
                    json.dumps(test_result.get('custom_data', {}), ensure_ascii=False),
                    test_result.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    1 if test_result.get('use_auth') else 0,
                    test_result.get('auth_type')
                ))
                
                self.db_manager._connection.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"添加测试历史失败: {e}")
            self.db_manager._connection.rollback()
            return None
    
    def get_test_history(self, project_id: str = None, limit: int = 500) -> List[Dict[str, Any]]:
        """
        获取测试历史记录
        
        Args:
            project_id: 项目ID，如果为None则获取所有项目的历史
            limit: 返回记录数限制
            
        Returns:
            List[Dict[str, Any]]: 测试历史记录列表
        """
        try:
            with self._get_cursor() as cursor:
                if project_id:
                    cursor.execute('''
                        SELECT * FROM test_history 
                        WHERE project_id = ?
                        ORDER BY test_timestamp DESC
                        LIMIT ?
                    ''', (project_id, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM test_history 
                        ORDER BY test_timestamp DESC
                        LIMIT ?
                    ''', (limit,))
                
                rows = cursor.fetchall()
                return self._rows_to_test_results(rows)
                
        except Exception as e:
            logger.error(f"获取测试历史失败: {e}")
            return []
    
    def get_test_history_by_api(self, project_id: str, api_path: str, method: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        根据API获取测试历史
        
        Args:
            project_id: 项目ID
            api_path: API路径
            method: HTTP方法
            limit: 返回记录数限制
            
        Returns:
            List[Dict[str, Any]]: 测试历史记录列表
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute('''
                    SELECT * FROM test_history 
                    WHERE project_id = ? AND api_path = ? AND method = ?
                    ORDER BY test_timestamp DESC
                    LIMIT ?
                ''', (project_id, api_path, method, limit))
                
                rows = cursor.fetchall()
                return self._rows_to_test_results(rows)
                
        except Exception as e:
            logger.error(f"根据API获取测试历史失败: {e}")
            return []
    
    def clear_test_history(self, project_id: str = None, api_path: str = None) -> bool:
        """
        清空测试历史
        
        Args:
            project_id: 项目ID，如果为None则清空所有
            api_path: API路径，如果指定则只清空特定API的历史
            
        Returns:
            bool: 是否成功
        """
        try:
            with self._get_cursor() as cursor:
                if project_id and api_path:
                    cursor.execute('''
                        DELETE FROM test_history 
                        WHERE project_id = ? AND api_path = ?
                    ''', (project_id, api_path))
                elif project_id:
                    cursor.execute('''
                        DELETE FROM test_history 
                        WHERE project_id = ?
                    ''', (project_id,))
                else:
                    cursor.execute('DELETE FROM test_history')
                
                self.db_manager._connection.commit()
                logger.info(f"清空测试历史成功，删除了 {cursor.rowcount} 条记录")
                return True
                
        except Exception as e:
            logger.error(f"清空测试历史失败: {e}")
            self.db_manager._connection.rollback()
            return False
    
    def get_test_statistics(self, project_id: str) -> Dict[str, Any]:
        """
        获取测试统计信息
        
        Args:
            project_id: 项目ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            with self._get_cursor() as cursor:
                # 总测试数
                cursor.execute('''
                    SELECT COUNT(*) FROM test_history 
                    WHERE project_id = ?
                ''', (project_id,))
                total_tests = cursor.fetchone()[0]
                
                # 成功/失败统计
                cursor.execute('''
                    SELECT 
                        COUNT(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 END) as success_count,
                        COUNT(CASE WHEN status_code >= 400 THEN 1 END) as failure_count,
                        COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as error_count
                    FROM test_history 
                    WHERE project_id = ?
                ''', (project_id,))
                stats = cursor.fetchone()
                
                # 平均响应时间
                cursor.execute('''
                    SELECT AVG(response_time) FROM test_history 
                    WHERE project_id = ? AND response_time > 0
                ''', (project_id,))
                avg_response_time = cursor.fetchone()[0] or 0
                
                # 最常测试的API
                cursor.execute('''
                    SELECT api_path, method, COUNT(*) as test_count
                    FROM test_history 
                    WHERE project_id = ?
                    GROUP BY api_path, method
                    ORDER BY test_count DESC
                    LIMIT 10
                ''', (project_id,))
                most_tested_apis = [
                    {
                        'api_path': row[0],
                        'method': row[1],
                        'test_count': row[2]
                    }
                    for row in cursor.fetchall()
                ]
                
                return {
                    'total_tests': total_tests,
                    'success_count': stats[0],
                    'failure_count': stats[1],
                    'error_count': stats[2],
                    'avg_response_time': avg_response_time,
                    'most_tested_apis': most_tested_apis
                }
                
        except Exception as e:
            logger.error(f"获取测试统计失败: {e}")
            return {}
    
    def _rows_to_test_results(self, rows) -> List[Dict[str, Any]]:
        """
        将数据库行转换为测试结果格式
        
        Args:
            rows: 数据库查询结果行
            
        Returns:
            List[Dict[str, Any]]: 测试结果列表
        """
        results = []
        for row in rows:
            try:
                # 解析JSON字段
                request_params = json.loads(row['request_params'] or '{}')
                
                result = {
                    'id': row['id'],
                    'api': {
                        'path': row['api_path'],
                        'method': row['method'],
                        'summary': row['api_summary']
                    },
                    'url': row['url'],
                    'method': row['method'],
                    'headers': json.loads(row['request_headers'] or '{}'),
                    'path_params': request_params.get('path_params', {}),
                    'query_params': request_params.get('query_params', {}),
                    'request_body': request_params.get('request_body'),
                    'response': {
                        'status_code': row['status_code'],
                        'headers': json.loads(row['response_headers'] or '{}'),
                        'body': json.loads(row['response_body']) if row['response_body'] else None,
                        'elapsed': row['response_time']
                    },
                    'error': row['error_message'],
                    'custom_data': json.loads(row['custom_data'] or '{}'),
                    'timestamp': row['test_timestamp'],
                    'use_auth': bool(row['use_auth']),
                    'auth_type': row['auth_type']
                }
                results.append(result)
            except Exception as e:
                logger.error(f"转换测试结果失败: {e}")
                continue
        
        return results
    
    def migrate_from_json(self, json_file_path: str, project_id: str) -> int:
        """
        从JSON文件迁移测试历史数据
        
        Args:
            json_file_path: JSON文件路径
            project_id: 项目ID
            
        Returns:
            int: 迁移的记录数
        """
        try:
            import os
            if not os.path.exists(json_file_path):
                logger.warning(f"JSON文件不存在: {json_file_path}")
                return 0
            
            with open(json_file_path, 'r', encoding='utf-8') as f:
                test_history = json.load(f)
            
            migrated_count = 0
            for test_result in test_history:
                # 检查是否已经存在（根据时间戳和API路径）
                with self._get_cursor() as cursor:
                    cursor.execute('''
                        SELECT id FROM test_history 
                        WHERE project_id = ? AND test_timestamp = ? AND api_path = ?
                    ''', (
                        project_id,
                        test_result.get('timestamp'),
                        test_result.get('api', {}).get('path', '')
                    ))
                    
                    if cursor.fetchone():
                        continue  # 跳过已存在的记录
                
                # 添加到数据库
                if self.add_test_history(project_id, test_result):
                    migrated_count += 1
            
            logger.info(f"成功迁移 {migrated_count} 条测试历史记录")
            return migrated_count
            
        except Exception as e:
            logger.error(f"迁移测试历史失败: {e}")
            return 0
