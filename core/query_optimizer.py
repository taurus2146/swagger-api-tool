#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
查询优化器
提供查询执行计划分析、慢查询检测、索引监控和查询缓存功能
"""

import sqlite3
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class QueryExecutionPlan:
    """查询执行计划"""
    query: str
    plan_steps: List[Dict[str, Any]]
    estimated_cost: float
    uses_index: bool
    table_scans: List[str]
    index_scans: List[str]
    recommendations: List[str]


@dataclass
class SlowQuery:
    """慢查询记录"""
    query: str
    execution_time: float
    timestamp: str
    parameters: Optional[List[Any]]
    execution_plan: Optional[QueryExecutionPlan]
    frequency: int = 1


@dataclass
class IndexUsageStats:
    """索引使用统计"""
    index_name: str
    table_name: str
    usage_count: int
    last_used: Optional[str]
    selectivity: float
    size_bytes: int
    is_unique: bool


class QueryCache:
    """查询缓存"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        """
        初始化查询缓存
        
        Args:
            max_size: 最大缓存条目数
            ttl_seconds: 缓存生存时间（秒）
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = OrderedDict()
        self._timestamps = {}
        self._lock = threading.RLock()
        
        # 统计信息
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def _generate_key(self, query: str, parameters: Optional[List[Any]] = None) -> str:
        """生成缓存键"""
        if parameters:
            param_str = str(tuple(parameters))
        else:
            param_str = ""
        return f"{query}|{param_str}"
    
    def _is_expired(self, timestamp: datetime) -> bool:
        """检查是否过期"""
        return datetime.now() - timestamp > timedelta(seconds=self.ttl_seconds)
    
    def _evict_expired(self):
        """清理过期条目"""
        now = datetime.now()
        expired_keys = []
        
        for key, timestamp in self._timestamps.items():
            if now - timestamp > timedelta(seconds=self.ttl_seconds):
                expired_keys.append(key)
        
        for key in expired_keys:
            if key in self._cache:
                del self._cache[key]
            if key in self._timestamps:
                del self._timestamps[key]
            self.evictions += 1
    
    def get(self, query: str, parameters: Optional[List[Any]] = None) -> Optional[Any]:
        """获取缓存结果"""
        with self._lock:
            key = self._generate_key(query, parameters)
            
            if key in self._cache:
                timestamp = self._timestamps.get(key)
                if timestamp and not self._is_expired(timestamp):
                    # 移到末尾（LRU）
                    self._cache.move_to_end(key)
                    self.hits += 1
                    return self._cache[key]
                else:
                    # 过期，删除
                    del self._cache[key]
                    if key in self._timestamps:
                        del self._timestamps[key]
                    self.evictions += 1
            
            self.misses += 1
            return None
    
    def put(self, query: str, result: Any, parameters: Optional[List[Any]] = None):
        """存储缓存结果"""
        with self._lock:
            key = self._generate_key(query, parameters)
            
            # 清理过期条目
            self._evict_expired()
            
            # 如果缓存已满，删除最旧的条目
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                if oldest_key in self._timestamps:
                    del self._timestamps[oldest_key]
                self.evictions += 1
            
            # 添加新条目
            self._cache[key] = result
            self._timestamps[key] = datetime.now()
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'evictions': self.evictions,
                'hit_rate': hit_rate,
                'ttl_seconds': self.ttl_seconds
            }


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self, db_path: str, slow_query_threshold: float = 0.1):
        """
        初始化查询优化器
        
        Args:
            db_path: 数据库文件路径
            slow_query_threshold: 慢查询阈值（秒）
        """
        self.db_path = db_path
        self.slow_query_threshold = slow_query_threshold
        
        # 查询缓存
        self.query_cache = QueryCache()
        
        # 慢查询记录
        self.slow_queries: Dict[str, SlowQuery] = {}
        
        # 索引使用统计
        self.index_stats: Dict[str, IndexUsageStats] = {}
        
        # 查询统计
        self.query_count = 0
        self.total_execution_time = 0.0
        
        # 线程锁
        self._lock = threading.RLock()
    
    def analyze_query_plan(self, query: str) -> Optional[QueryExecutionPlan]:
        """
        分析查询执行计划
        
        Args:
            query: SQL查询语句
            
        Returns:
            Optional[QueryExecutionPlan]: 执行计划分析结果
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取查询计划
                explain_query = f"EXPLAIN QUERY PLAN {query}"
                cursor.execute(explain_query)
                plan_rows = cursor.fetchall()
                
                # 解析计划步骤
                plan_steps = []
                uses_index = False
                table_scans = []
                index_scans = []
                estimated_cost = 0.0
                
                for row in plan_rows:
                    step = {
                        'id': row[0],
                        'parent': row[1],
                        'notused': row[2],
                        'detail': row[3]
                    }
                    plan_steps.append(step)
                    
                    detail = row[3].lower()
                    
                    # 检查是否使用索引
                    if 'using index' in detail or 'index' in detail:
                        uses_index = True
                        # 提取索引名
                        if 'index' in detail:
                            parts = detail.split()
                            for i, part in enumerate(parts):
                                if part == 'index' and i + 1 < len(parts):
                                    index_name = parts[i + 1]
                                    if index_name not in index_scans:
                                        index_scans.append(index_name)
                    
                    # 检查表扫描
                    if 'scan table' in detail:
                        parts = detail.split()
                        for i, part in enumerate(parts):
                            if part == 'table' and i + 1 < len(parts):
                                table_name = parts[i + 1]
                                if table_name not in table_scans:
                                    table_scans.append(table_name)
                    
                    # 估算成本（简单的启发式方法）
                    if 'scan table' in detail:
                        estimated_cost += 100  # 表扫描成本高
                    elif 'using index' in detail:
                        estimated_cost += 10   # 索引扫描成本低
                    else:
                        estimated_cost += 1    # 其他操作成本很低
                
                # 生成优化建议
                recommendations = self._generate_recommendations(
                    query, plan_steps, uses_index, table_scans, index_scans
                )
                
                return QueryExecutionPlan(
                    query=query,
                    plan_steps=plan_steps,
                    estimated_cost=estimated_cost,
                    uses_index=uses_index,
                    table_scans=table_scans,
                    index_scans=index_scans,
                    recommendations=recommendations
                )
                
        except Exception as e:
            logger.error(f"分析查询计划失败: {e}")
            return None
    
    def _generate_recommendations(self, query: str, plan_steps: List[Dict], 
                                uses_index: bool, table_scans: List[str], 
                                index_scans: List[str]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 如果有表扫描但没有使用索引
        if table_scans and not uses_index:
            recommendations.append(f"考虑为表 {', '.join(table_scans)} 添加索引以避免全表扫描")
        
        # 检查WHERE子句
        query_lower = query.lower()
        if 'where' in query_lower:
            # 简单的WHERE子句分析
            where_part = query_lower.split('where')[1].split('order by')[0].split('group by')[0]
            
            # 查找可能需要索引的列
            common_operators = ['=', '>', '<', '>=', '<=', 'like', 'in']
            for op in common_operators:
                if op in where_part:
                    recommendations.append(f"WHERE子句中使用了 '{op}' 操作符，确保相关列有适当的索引")
                    break
        
        # 检查ORDER BY
        if 'order by' in query_lower:
            recommendations.append("ORDER BY操作可能受益于相关列的索引")
        
        # 检查JOIN
        if 'join' in query_lower:
            recommendations.append("JOIN操作的关联列应该有索引以提高性能")
        
        # 如果估算成本很高
        total_cost = sum(1 for step in plan_steps if 'scan table' in step.get('detail', '').lower()) * 100
        if total_cost > 200:
            recommendations.append("查询成本较高，考虑优化查询结构或添加索引")
        
        return recommendations
    
    def execute_with_monitoring(self, query: str, parameters: Optional[List[Any]] = None) -> Any:
        """
        执行查询并监控性能
        
        Args:
            query: SQL查询语句
            parameters: 查询参数
            
        Returns:
            Any: 查询结果
        """
        # 检查缓存
        cached_result = self.query_cache.get(query, parameters)
        if cached_result is not None:
            return cached_result
        
        start_time = time.time()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if parameters:
                    cursor.execute(query, parameters)
                else:
                    cursor.execute(query)
                
                result = cursor.fetchall()
                
                # 记录执行时间
                execution_time = time.time() - start_time
                
                with self._lock:
                    self.query_count += 1
                    self.total_execution_time += execution_time
                
                # 检查是否为慢查询
                if execution_time > self.slow_query_threshold:
                    self._record_slow_query(query, execution_time, parameters)
                
                # 更新索引使用统计
                self._update_index_stats(query)
                
                # 缓存结果（只缓存SELECT查询）
                if query.strip().lower().startswith('select'):
                    self.query_cache.put(query, result, parameters)
                
                return result
                
        except Exception as e:
            logger.error(f"执行查询失败: {e}")
            raise
    
    def _record_slow_query(self, query: str, execution_time: float, 
                          parameters: Optional[List[Any]] = None):
        """记录慢查询"""
        with self._lock:
            query_key = query.strip()
            
            if query_key in self.slow_queries:
                # 更新现有记录
                slow_query = self.slow_queries[query_key]
                slow_query.frequency += 1
                slow_query.execution_time = max(slow_query.execution_time, execution_time)
                slow_query.timestamp = datetime.now().isoformat()
            else:
                # 创建新记录
                execution_plan = self.analyze_query_plan(query)
                
                self.slow_queries[query_key] = SlowQuery(
                    query=query,
                    execution_time=execution_time,
                    timestamp=datetime.now().isoformat(),
                    parameters=parameters,
                    execution_plan=execution_plan
                )
    
    def _update_index_stats(self, query: str):
        """更新索引使用统计"""
        try:
            # 分析查询计划以确定使用的索引
            plan = self.analyze_query_plan(query)
            if plan and plan.index_scans:
                with self._lock:
                    for index_name in plan.index_scans:
                        if index_name in self.index_stats:
                            self.index_stats[index_name].usage_count += 1
                            self.index_stats[index_name].last_used = datetime.now().isoformat()
                        else:
                            # 获取索引信息
                            index_info = self._get_index_info(index_name)
                            if index_info:
                                self.index_stats[index_name] = index_info
                                self.index_stats[index_name].usage_count = 1
                                self.index_stats[index_name].last_used = datetime.now().isoformat()
        
        except Exception as e:
            logger.debug(f"更新索引统计失败: {e}")
    
    def _get_index_info(self, index_name: str) -> Optional[IndexUsageStats]:
        """获取索引信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取索引信息
                cursor.execute("""
                    SELECT name, tbl_name, sql FROM sqlite_master 
                    WHERE type = 'index' AND name = ?
                """, (index_name,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                name, table_name, sql = row
                is_unique = sql and 'unique' in sql.lower() if sql else False
                
                # 估算索引大小（简化方法）
                cursor.execute(f"PRAGMA index_info(`{index_name}`)")
                columns = cursor.fetchall()
                
                # 估算选择性（简化方法）
                if columns:
                    column_name = columns[0][2]  # 第一个列名
                    cursor.execute(f"SELECT COUNT(DISTINCT `{column_name}`) FROM `{table_name}`")
                    distinct_count = cursor.fetchone()[0]
                    
                    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                    total_count = cursor.fetchone()[0]
                    
                    selectivity = distinct_count / total_count if total_count > 0 else 0.0
                else:
                    selectivity = 0.0
                
                return IndexUsageStats(
                    index_name=name,
                    table_name=table_name,
                    usage_count=0,
                    last_used=None,
                    selectivity=selectivity,
                    size_bytes=0,  # 实际计算较复杂，这里简化
                    is_unique=is_unique
                )
                
        except Exception as e:
            logger.error(f"获取索引信息失败: {e}")
            return None
    
    def get_slow_queries(self, limit: int = 10) -> List[SlowQuery]:
        """
        获取慢查询列表
        
        Args:
            limit: 返回数量限制
            
        Returns:
            List[SlowQuery]: 慢查询列表
        """
        with self._lock:
            # 按执行时间排序
            sorted_queries = sorted(
                self.slow_queries.values(),
                key=lambda x: x.execution_time,
                reverse=True
            )
            return sorted_queries[:limit]
    
    def get_index_usage_stats(self) -> List[IndexUsageStats]:
        """
        获取索引使用统计
        
        Returns:
            List[IndexUsageStats]: 索引使用统计列表
        """
        with self._lock:
            return list(self.index_stats.values())
    
    def get_unused_indexes(self) -> List[str]:
        """
        获取未使用的索引
        
        Returns:
            List[str]: 未使用的索引名称列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取所有索引
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
                """)
                
                all_indexes = {row[0] for row in cursor.fetchall()}
                used_indexes = set(self.index_stats.keys())
                
                return list(all_indexes - used_indexes)
                
        except Exception as e:
            logger.error(f"获取未使用索引失败: {e}")
            return []
    
    def suggest_indexes(self, query: str) -> List[str]:
        """
        为查询建议索引
        
        Args:
            query: SQL查询语句
            
        Returns:
            List[str]: 索引建议列表
        """
        suggestions = []
        
        try:
            # 分析查询计划
            plan = self.analyze_query_plan(query)
            if plan:
                suggestions.extend(plan.recommendations)
            
            # 简单的查询分析
            query_lower = query.lower()
            
            # 分析WHERE子句
            if 'where' in query_lower:
                where_part = query_lower.split('where')[1]
                
                # 查找可能的索引列
                import re
                # 简单的列名匹配（实际应该更复杂）
                column_pattern = r'\b(\w+)\s*[=<>]'
                matches = re.findall(column_pattern, where_part)
                
                for column in matches:
                    if column not in ['and', 'or', 'not', 'in', 'like']:
                        suggestions.append(f"考虑为列 '{column}' 创建索引")
            
            # 分析ORDER BY子句
            if 'order by' in query_lower:
                order_part = query_lower.split('order by')[1].split('limit')[0]
                columns = [col.strip().split()[0] for col in order_part.split(',')]
                
                for column in columns:
                    suggestions.append(f"考虑为ORDER BY列 '{column}' 创建索引")
            
        except Exception as e:
            logger.error(f"生成索引建议失败: {e}")
        
        return list(set(suggestions))  # 去重
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计信息
        
        Returns:
            Dict[str, Any]: 性能统计信息
        """
        with self._lock:
            avg_execution_time = (
                self.total_execution_time / self.query_count 
                if self.query_count > 0 else 0.0
            )
            
            cache_stats = self.query_cache.get_stats()
            
            return {
                'total_queries': self.query_count,
                'total_execution_time': self.total_execution_time,
                'average_execution_time': avg_execution_time,
                'slow_queries_count': len(self.slow_queries),
                'slow_query_threshold': self.slow_query_threshold,
                'cache_stats': cache_stats,
                'indexes_monitored': len(self.index_stats),
                'unused_indexes': len(self.get_unused_indexes())
            }
    
    def clear_stats(self):
        """清空统计信息"""
        with self._lock:
            self.slow_queries.clear()
            self.index_stats.clear()
            self.query_count = 0
            self.total_execution_time = 0.0
            self.query_cache.clear()
    
    def optimize_database(self) -> Dict[str, Any]:
        """
        优化数据库
        
        Returns:
            Dict[str, Any]: 优化结果
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 更新统计信息
                cursor.execute("ANALYZE")
                
                # 重建索引
                cursor.execute("REINDEX")
                
                # 压缩数据库
                cursor.execute("VACUUM")
                
                conn.commit()
                
                return {
                    'success': True,
                    'message': '数据库优化完成',
                    'operations': ['ANALYZE', 'REINDEX', 'VACUUM']
                }
                
        except Exception as e:
            logger.error(f"数据库优化失败: {e}")
            return {
                'success': False,
                'message': f'数据库优化失败: {str(e)}',
                'operations': []
            }