#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
内存缓存系统
提供LRU缓存算法、热点数据自动缓存、缓存一致性保证和命中率监控
"""

import threading
import time
import logging
import hashlib
import pickle
from typing import Any, Dict, List, Optional, Callable, Set, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class CacheEventType(Enum):
    """缓存事件类型"""
    HIT = "hit"
    MISS = "miss"
    PUT = "put"
    EVICT = "evict"
    EXPIRE = "expire"
    INVALIDATE = "invalidate"


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    size_bytes: int
    ttl_seconds: Optional[int] = None
    tags: Set[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = set()
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl_seconds is None:
            return False
        return datetime.now() - self.created_at > timedelta(seconds=self.ttl_seconds)
    
    @property
    def age_seconds(self) -> float:
        """获取条目年龄（秒）"""
        return (datetime.now() - self.created_at).total_seconds()
    
    @property
    def idle_seconds(self) -> float:
        """获取空闲时间（秒）"""
        return (datetime.now() - self.last_accessed).total_seconds()
    
    def touch(self):
        """更新访问时间和计数"""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class CacheStats:
    """缓存统计信息"""
    hits: int = 0
    misses: int = 0
    puts: int = 0
    evictions: int = 0
    expirations: int = 0
    invalidations: int = 0
    
    @property
    def total_requests(self) -> int:
        return self.hits + self.misses
    
    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests * 100
    
    @property
    def miss_rate(self) -> float:
        return 100.0 - self.hit_rate


class HotDataDetector:
    """热点数据检测器"""
    
    def __init__(self, window_size: int = 1000, threshold_ratio: float = 0.1):
        """
        初始化热点数据检测器
        
        Args:
            window_size: 滑动窗口大小
            threshold_ratio: 热点阈值比例
        """
        self.window_size = window_size
        self.threshold_ratio = threshold_ratio
        self.access_history = []
        self.access_counts = defaultdict(int)
        self._lock = threading.RLock()
    
    def record_access(self, key: str):
        """记录访问"""
        with self._lock:
            # 添加到历史记录
            self.access_history.append((key, datetime.now()))
            self.access_counts[key] += 1
            
            # 维护滑动窗口
            if len(self.access_history) > self.window_size:
                old_key, _ = self.access_history.pop(0)
                self.access_counts[old_key] -= 1
                if self.access_counts[old_key] <= 0:
                    del self.access_counts[old_key]
    
    def get_hot_keys(self) -> List[str]:
        """获取热点键"""
        with self._lock:
            if not self.access_counts:
                return []
            
            # 计算阈值
            total_accesses = sum(self.access_counts.values())
            threshold = total_accesses * self.threshold_ratio
            
            # 找出热点键
            hot_keys = [
                key for key, count in self.access_counts.items()
                if count >= threshold
            ]
            
            # 按访问次数排序
            hot_keys.sort(key=lambda k: self.access_counts[k], reverse=True)
            return hot_keys
    
    def is_hot_key(self, key: str) -> bool:
        """检查是否为热点键"""
        return key in self.get_hot_keys()


class CacheConsistencyManager:
    """缓存一致性管理器"""
    
    def __init__(self):
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)  # key -> dependent_keys
        self.reverse_dependencies: Dict[str, Set[str]] = defaultdict(set)  # key -> keys_it_depends_on
        self.invalidation_callbacks: Dict[str, List[Callable[[str], None]]] = defaultdict(list)
        self._lock = threading.RLock()
    
    def add_dependency(self, key: str, depends_on: str):
        """添加依赖关系"""
        with self._lock:
            self.dependencies[depends_on].add(key)
            self.reverse_dependencies[key].add(depends_on)
    
    def remove_dependency(self, key: str, depends_on: str):
        """移除依赖关系"""
        with self._lock:
            self.dependencies[depends_on].discard(key)
            self.reverse_dependencies[key].discard(depends_on)
    
    def add_invalidation_callback(self, pattern: str, callback: Callable[[str], None]):
        """添加失效回调"""
        with self._lock:
            self.invalidation_callbacks[pattern].append(callback)
    
    def invalidate_key(self, key: str) -> Set[str]:
        """使键失效，返回所有需要失效的键"""
        with self._lock:
            invalidated_keys = set()
            keys_to_process = [key]
            
            while keys_to_process:
                current_key = keys_to_process.pop(0)
                if current_key in invalidated_keys:
                    continue
                
                invalidated_keys.add(current_key)
                
                # 添加依赖的键
                dependent_keys = self.dependencies.get(current_key, set())
                keys_to_process.extend(dependent_keys)
                
                # 调用失效回调
                for pattern, callbacks in self.invalidation_callbacks.items():
                    if self._matches_pattern(current_key, pattern):
                        for callback in callbacks:
                            try:
                                callback(current_key)
                            except Exception as e:
                                logger.error(f"缓存失效回调执行失败: {e}")
            
            return invalidated_keys
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """检查键是否匹配模式"""
        # 简单的通配符匹配
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return key.startswith(pattern[:-1])
        if pattern.startswith("*"):
            return key.endswith(pattern[1:])
        return key == pattern


class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: float = 100.0,
                 default_ttl: Optional[int] = None):
        """
        初始化LRU缓存
        
        Args:
            max_size: 最大条目数
            max_memory_mb: 最大内存使用量（MB）
            default_ttl: 默认TTL（秒）
        """
        self.max_size = max_size
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self.default_ttl = default_ttl
        
        # 缓存存储
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._current_memory = 0
        
        # 统计信息
        self.stats = CacheStats()
        
        # 热点数据检测
        self.hot_detector = HotDataDetector()
        
        # 一致性管理
        self.consistency_manager = CacheConsistencyManager()
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 事件监听器
        self._event_listeners: List[Callable[[CacheEventType, str, Any], None]] = []
    
    def _calculate_size(self, value: Any) -> int:
        """计算值的大小"""
        try:
            return len(pickle.dumps(value))
        except:
            # 如果无法序列化，使用估算
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (int, float)):
                return 8
            elif isinstance(value, (list, tuple)):
                return sum(self._calculate_size(item) for item in value)
            elif isinstance(value, dict):
                return sum(self._calculate_size(k) + self._calculate_size(v) 
                          for k, v in value.items())
            else:
                return 64  # 默认估算
    
    def _emit_event(self, event_type: CacheEventType, key: str, value: Any = None):
        """发射缓存事件"""
        for listener in self._event_listeners:
            try:
                listener(event_type, key, value)
            except Exception as e:
                logger.error(f"缓存事件监听器执行失败: {e}")
    
    def add_event_listener(self, listener: Callable[[CacheEventType, str, Any], None]):
        """添加事件监听器"""
        self._event_listeners.append(listener)
    
    def _evict_expired(self):
        """清理过期条目"""
        expired_keys = []
        for key, entry in self._cache.items():
            if entry.is_expired:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_entry(key, CacheEventType.EXPIRE)
    
    def _evict_lru(self):
        """LRU淘汰"""
        while (len(self._cache) >= self.max_size or 
               self._current_memory >= self.max_memory_bytes):
            if not self._cache:
                break
            
            # 移除最久未使用的条目
            lru_key = next(iter(self._cache))
            self._remove_entry(lru_key, CacheEventType.EVICT)
    
    def _remove_entry(self, key: str, event_type: CacheEventType):
        """移除条目"""
        if key in self._cache:
            entry = self._cache[key]
            del self._cache[key]
            self._current_memory -= entry.size_bytes
            
            # 更新统计
            if event_type == CacheEventType.EVICT:
                self.stats.evictions += 1
            elif event_type == CacheEventType.EXPIRE:
                self.stats.expirations += 1
            elif event_type == CacheEventType.INVALIDATE:
                self.stats.invalidations += 1
            
            # 发射事件
            self._emit_event(event_type, key, entry.value)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            # 记录访问
            self.hot_detector.record_access(key)
            
            # 清理过期条目
            self._evict_expired()
            
            if key in self._cache:
                entry = self._cache[key]
                
                # 检查是否过期
                if entry.is_expired:
                    self._remove_entry(key, CacheEventType.EXPIRE)
                    self.stats.misses += 1
                    self._emit_event(CacheEventType.MISS, key)
                    return None
                
                # 更新访问信息
                entry.touch()
                
                # 移到末尾（LRU）
                self._cache.move_to_end(key)
                
                # 更新统计
                self.stats.hits += 1
                self._emit_event(CacheEventType.HIT, key, entry.value)
                
                return entry.value
            else:
                self.stats.misses += 1
                self._emit_event(CacheEventType.MISS, key)
                return None
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None, 
            tags: Optional[Set[str]] = None) -> bool:
        """存储缓存值"""
        with self._lock:
            # 计算大小
            size_bytes = self._calculate_size(value)
            
            # 检查是否超过最大内存限制
            if size_bytes > self.max_memory_bytes:
                logger.warning(f"缓存值过大，无法存储: {key}")
                return False
            
            # 如果键已存在，先移除
            if key in self._cache:
                old_entry = self._cache[key]
                self._current_memory -= old_entry.size_bytes
                del self._cache[key]
            
            # 创建新条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=1,
                size_bytes=size_bytes,
                ttl_seconds=ttl or self.default_ttl,
                tags=tags or set()
            )
            
            # 确保有足够空间
            self._current_memory += size_bytes
            self._evict_lru()
            
            # 存储条目
            self._cache[key] = entry
            
            # 更新统计
            self.stats.puts += 1
            self._emit_event(CacheEventType.PUT, key, value)
            
            return True
    
    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self._lock:
            if key in self._cache:
                self._remove_entry(key, CacheEventType.INVALIDATE)
                return True
            return False
    
    def invalidate_by_tags(self, tags: Set[str]) -> int:
        """根据标签失效缓存"""
        with self._lock:
            keys_to_remove = []
            
            for key, entry in self._cache.items():
                if entry.tags.intersection(tags):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self._remove_entry(key, CacheEventType.INVALIDATE)
            
            return len(keys_to_remove)
    
    def invalidate_by_pattern(self, pattern: str) -> int:
        """根据模式失效缓存"""
        with self._lock:
            keys_to_remove = []
            
            for key in self._cache.keys():
                if self.consistency_manager._matches_pattern(key, pattern):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                invalidated_keys = self.consistency_manager.invalidate_key(key)
                for invalid_key in invalidated_keys:
                    if invalid_key in self._cache:
                        self._remove_entry(invalid_key, CacheEventType.INVALIDATE)
            
            return len(keys_to_remove)
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._current_memory = 0
            self.stats = CacheStats()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'memory_usage_mb': self._current_memory / 1024 / 1024,
                'max_memory_mb': self.max_memory_bytes / 1024 / 1024,
                'memory_usage_percent': (self._current_memory / self.max_memory_bytes * 100) 
                                      if self.max_memory_bytes > 0 else 0,
                'hits': self.stats.hits,
                'misses': self.stats.misses,
                'puts': self.stats.puts,
                'evictions': self.stats.evictions,
                'expirations': self.stats.expirations,
                'invalidations': self.stats.invalidations,
                'hit_rate': self.stats.hit_rate,
                'miss_rate': self.stats.miss_rate,
                'hot_keys': self.hot_detector.get_hot_keys()[:10]  # 前10个热点键
            }
    
    def get_entry_info(self, key: str) -> Optional[Dict[str, Any]]:
        """获取条目信息"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                return {
                    'key': entry.key,
                    'size_bytes': entry.size_bytes,
                    'created_at': entry.created_at.isoformat(),
                    'last_accessed': entry.last_accessed.isoformat(),
                    'access_count': entry.access_count,
                    'age_seconds': entry.age_seconds,
                    'idle_seconds': entry.idle_seconds,
                    'ttl_seconds': entry.ttl_seconds,
                    'is_expired': entry.is_expired,
                    'tags': list(entry.tags),
                    'is_hot': self.hot_detector.is_hot_key(key)
                }
            return None
    
    def get_all_keys(self) -> List[str]:
        """获取所有键"""
        with self._lock:
            return list(self._cache.keys())
    
    def get_keys_by_tag(self, tag: str) -> List[str]:
        """根据标签获取键"""
        with self._lock:
            return [
                key for key, entry in self._cache.items()
                if tag in entry.tags
            ]
    
    def optimize(self):
        """优化缓存"""
        with self._lock:
            # 清理过期条目
            self._evict_expired()
            
            # 如果内存使用过高，进行额外清理
            if self._current_memory > self.max_memory_bytes * 0.8:
                # 移除访问次数最少的条目
                entries_by_access = sorted(
                    self._cache.items(),
                    key=lambda x: (x[1].access_count, x[1].last_accessed)
                )
                
                # 移除最少访问的25%
                remove_count = max(1, len(entries_by_access) // 4)
                for key, _ in entries_by_access[:remove_count]:
                    self._remove_entry(key, CacheEventType.EVICT)


class MemoryCacheSystem:
    """内存缓存系统"""
    
    def __init__(self, default_cache_config: Optional[Dict[str, Any]] = None):
        """
        初始化内存缓存系统
        
        Args:
            default_cache_config: 默认缓存配置
        """
        self.default_config = default_cache_config or {
            'max_size': 1000,
            'max_memory_mb': 100.0,
            'default_ttl': 300
        }
        
        # 缓存实例
        self.caches: Dict[str, LRUCache] = {}
        
        # 全局统计
        self.global_stats = CacheStats()
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 创建默认缓存
        self.get_cache('default')
    
    def get_cache(self, name: str, config: Optional[Dict[str, Any]] = None) -> LRUCache:
        """获取或创建缓存实例"""
        with self._lock:
            if name not in self.caches:
                cache_config = {**self.default_config, **(config or {})}
                cache = LRUCache(**cache_config)
                
                # 添加全局统计监听器
                cache.add_event_listener(self._update_global_stats)
                
                self.caches[name] = cache
            
            return self.caches[name]
    
    def _update_global_stats(self, event_type: CacheEventType, key: str, value: Any):
        """更新全局统计"""
        if event_type == CacheEventType.HIT:
            self.global_stats.hits += 1
        elif event_type == CacheEventType.MISS:
            self.global_stats.misses += 1
        elif event_type == CacheEventType.PUT:
            self.global_stats.puts += 1
        elif event_type == CacheEventType.EVICT:
            self.global_stats.evictions += 1
        elif event_type == CacheEventType.EXPIRE:
            self.global_stats.expirations += 1
        elif event_type == CacheEventType.INVALIDATE:
            self.global_stats.invalidations += 1
    
    def get_global_stats(self) -> Dict[str, Any]:
        """获取全局统计"""
        with self._lock:
            total_size = sum(len(cache._cache) for cache in self.caches.values())
            total_memory = sum(cache._current_memory for cache in self.caches.values())
            
            return {
                'cache_count': len(self.caches),
                'total_entries': total_size,
                'total_memory_mb': total_memory / 1024 / 1024,
                'global_hits': self.global_stats.hits,
                'global_misses': self.global_stats.misses,
                'global_puts': self.global_stats.puts,
                'global_evictions': self.global_stats.evictions,
                'global_expirations': self.global_stats.expirations,
                'global_invalidations': self.global_stats.invalidations,
                'global_hit_rate': self.global_stats.hit_rate,
                'cache_names': list(self.caches.keys())
            }
    
    def optimize_all(self):
        """优化所有缓存"""
        with self._lock:
            for cache in self.caches.values():
                cache.optimize()
    
    def clear_all(self):
        """清空所有缓存"""
        with self._lock:
            for cache in self.caches.values():
                cache.clear()
            self.global_stats = CacheStats()
    
    def remove_cache(self, name: str) -> bool:
        """移除缓存实例"""
        with self._lock:
            if name in self.caches and name != 'default':
                del self.caches[name]
                return True
            return False