#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
异步数据操作系统
提供异步数据库操作队列、后台数据保存、操作进度通知和批量操作优化
"""

import threading
import queue
import time
import logging
import sqlite3
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, Future

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """操作类型"""
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    SELECT = "select"
    BATCH_INSERT = "batch_insert"
    BATCH_UPDATE = "batch_update"
    BATCH_DELETE = "batch_delete"
    CUSTOM = "custom"


class OperationStatus(Enum):
    """操作状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OperationPriority(Enum):
    """操作优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class OperationResult:
    """操作结果"""
    success: bool
    result: Any = None
    error: Optional[str] = None
    affected_rows: int = 0
    execution_time: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DatabaseOperation:
    """数据库操作"""
    id: str
    operation_type: OperationType
    sql: str
    parameters: Optional[List[Any]] = None
    priority: OperationPriority = OperationPriority.NORMAL
    callback: Optional[Callable[[OperationResult], None]] = None
    progress_callback: Optional[Callable[[float, str], None]] = None
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = None
    
    # 运行时状态
    status: OperationStatus = OperationStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[OperationResult] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def execution_time(self) -> Optional[float]:
        """获取执行时间"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def wait_time(self) -> float:
        """获取等待时间"""
        if self.started_at:
            return (self.started_at - self.created_at).total_seconds()
        else:
            return (datetime.now() - self.created_at).total_seconds()


class BatchOperation:
    """批量操作"""
    
    def __init__(self, operation_type: OperationType, table_name: str):
        self.id = f"batch_{int(time.time() * 1000)}"
        self.operation_type = operation_type
        self.table_name = table_name
        self.operations: List[Tuple[str, List[Any]]] = []
        self.created_at = datetime.now()
        self.batch_size = 1000  # 默认批量大小
        
    def add_operation(self, sql: str, parameters: List[Any]):
        """添加操作到批量"""
        self.operations.append((sql, parameters))
    
    def get_batches(self) -> List[List[Tuple[str, List[Any]]]]:
        """将操作分批"""
        batches = []
        for i in range(0, len(self.operations), self.batch_size):
            batch = self.operations[i:i + self.batch_size]
            batches.append(batch)
        return batches
    
    def __len__(self):
        return len(self.operations)


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, operation_id: str, total_steps: int = 100):
        self.operation_id = operation_id
        self.total_steps = total_steps
        self.current_step = 0
        self.status_message = "初始化..."
        self.started_at = datetime.now()
        self.callbacks: List[Callable[[float, str], None]] = []
    
    def add_callback(self, callback: Callable[[float, str], None]):
        """添加进度回调"""
        self.callbacks.append(callback)
    
    def update(self, step: int, message: str = ""):
        """更新进度"""
        self.current_step = min(step, self.total_steps)
        if message:
            self.status_message = message
        
        progress = (self.current_step / self.total_steps) * 100
        
        # 调用所有回调
        for callback in self.callbacks:
            try:
                callback(progress, self.status_message)
            except Exception as e:
                logger.error(f"进度回调执行失败: {e}")
    
    def increment(self, message: str = ""):
        """递增进度"""
        self.update(self.current_step + 1, message)
    
    def complete(self, message: str = "完成"):
        """完成进度"""
        self.update(self.total_steps, message)
    
    @property
    def progress_percent(self) -> float:
        """获取进度百分比"""
        return (self.current_step / self.total_steps) * 100
    
    @property
    def elapsed_time(self) -> float:
        """获取已用时间"""
        return (datetime.now() - self.started_at).total_seconds()


class AsyncDatabaseWorker:
    """异步数据库工作线程"""
    
    def __init__(self, worker_id: int, db_path: str, operation_queue: queue.PriorityQueue):
        self.worker_id = worker_id
        self.db_path = db_path
        self.operation_queue = operation_queue
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.current_operation: Optional[DatabaseOperation] = None
        
        # 统计信息
        self.operations_processed = 0
        self.total_execution_time = 0.0
        self.errors_count = 0
    
    def start(self):
        """启动工作线程"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.thread.start()
            logger.info(f"异步数据库工作线程 {self.worker_id} 已启动")
    
    def stop(self):
        """停止工作线程"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
            logger.info(f"异步数据库工作线程 {self.worker_id} 已停止")
    
    def _worker_loop(self):
        """工作线程主循环"""
        while self.running:
            try:
                # 从队列获取操作（带超时）
                try:
                    priority, operation = self.operation_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                if operation is None:  # 停止信号
                    break
                
                self.current_operation = operation
                self._execute_operation(operation)
                self.current_operation = None
                
                # 标记任务完成
                self.operation_queue.task_done()
                
            except Exception as e:
                logger.error(f"工作线程 {self.worker_id} 发生异常: {e}")
                self.errors_count += 1
    
    def _execute_operation(self, operation: DatabaseOperation):
        """执行数据库操作"""
        operation.status = OperationStatus.RUNNING
        operation.started_at = datetime.now()
        
        try:
            # 创建进度跟踪器
            progress_tracker = None
            if operation.progress_callback:
                progress_tracker = ProgressTracker(operation.id)
                progress_tracker.add_callback(operation.progress_callback)
                progress_tracker.update(0, "开始执行操作...")
            
            # 执行操作
            start_time = time.time()
            result = self._execute_sql_operation(operation, progress_tracker)
            execution_time = time.time() - start_time
            
            # 创建操作结果
            operation.result = OperationResult(
                success=True,
                result=result,
                execution_time=execution_time,
                affected_rows=getattr(result, 'rowcount', 0) if hasattr(result, 'rowcount') else len(result) if isinstance(result, list) else 1
            )
            
            operation.status = OperationStatus.COMPLETED
            operation.completed_at = datetime.now()
            
            # 更新统计
            self.operations_processed += 1
            self.total_execution_time += execution_time
            
            # 完成进度
            if progress_tracker:
                progress_tracker.complete("操作完成")
            
            logger.debug(f"操作 {operation.id} 执行成功，耗时 {execution_time:.3f}秒")
            
        except Exception as e:
            # 处理错误
            operation.result = OperationResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time if 'start_time' in locals() else 0.0
            )
            
            operation.status = OperationStatus.FAILED
            operation.completed_at = datetime.now()
            
            self.errors_count += 1
            
            # 检查是否需要重试
            if operation.retry_count < operation.max_retries:
                operation.retry_count += 1
                operation.status = OperationStatus.PENDING
                operation.started_at = None
                operation.completed_at = None
                
                # 重新加入队列
                self.operation_queue.put((operation.priority.value, operation))
                logger.warning(f"操作 {operation.id} 执行失败，将重试 ({operation.retry_count}/{operation.max_retries}): {e}")
                return
            
            logger.error(f"操作 {operation.id} 执行失败: {e}")
        
        finally:
            # 调用回调
            if operation.callback and operation.result:
                try:
                    operation.callback(operation.result)
                except Exception as e:
                    logger.error(f"操作回调执行失败: {e}")
    
    def _execute_sql_operation(self, operation: DatabaseOperation, 
                             progress_tracker: Optional[ProgressTracker] = None) -> Any:
        """执行SQL操作"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if operation.operation_type in [OperationType.BATCH_INSERT, 
                                          OperationType.BATCH_UPDATE, 
                                          OperationType.BATCH_DELETE]:
                # 批量操作
                return self._execute_batch_operation(cursor, operation, progress_tracker)
            else:
                # 单个操作
                if progress_tracker:
                    progress_tracker.update(50, "执行SQL语句...")
                
                if operation.parameters:
                    cursor.execute(operation.sql, operation.parameters)
                else:
                    cursor.execute(operation.sql)
                
                if operation.operation_type == OperationType.SELECT:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount
                    conn.commit()
                
                if progress_tracker:
                    progress_tracker.update(100, "SQL执行完成")
                
                return result
    
    def _execute_batch_operation(self, cursor: sqlite3.Cursor, operation: DatabaseOperation,
                               progress_tracker: Optional[ProgressTracker] = None) -> int:
        """执行批量操作"""
        # 解析批量操作数据
        batch_data = operation.metadata.get('batch_data', [])
        if not batch_data:
            return 0
        
        total_operations = len(batch_data)
        processed = 0
        
        try:
            # 开始事务
            cursor.execute("BEGIN TRANSACTION")
            
            for i, (sql, params) in enumerate(batch_data):
                cursor.execute(sql, params)
                processed += 1
                
                # 更新进度
                if progress_tracker and i % 100 == 0:  # 每100个操作更新一次进度
                    progress = (i / total_operations) * 100
                    progress_tracker.update(int(progress), f"已处理 {i}/{total_operations} 个操作")
            
            # 提交事务
            cursor.execute("COMMIT")
            
            if progress_tracker:
                progress_tracker.complete(f"批量操作完成，处理了 {processed} 个操作")
            
            return processed
            
        except Exception as e:
            # 回滚事务
            cursor.execute("ROLLBACK")
            raise e


class AsyncDataOperationSystem:
    """异步数据操作系统"""
    
    def __init__(self, db_path: str, max_workers: int = 3, queue_size: int = 1000):
        """
        初始化异步数据操作系统
        
        Args:
            db_path: 数据库文件路径
            max_workers: 最大工作线程数
            queue_size: 队列最大大小
        """
        self.db_path = db_path
        self.max_workers = max_workers
        self.queue_size = queue_size
        
        # 操作队列（优先级队列）
        self.operation_queue = queue.PriorityQueue(maxsize=queue_size)
        
        # 工作线程池
        self.workers: List[AsyncDatabaseWorker] = []
        
        # 操作跟踪
        self.operations: Dict[str, DatabaseOperation] = {}
        self.completed_operations: List[DatabaseOperation] = []
        
        # 批量操作管理
        self.batch_operations: Dict[str, BatchOperation] = {}
        
        # 系统状态
        self.running = False
        self.stats_lock = threading.RLock()
        
        # 统计信息
        self.total_operations = 0
        self.completed_operations_count = 0
        self.failed_operations_count = 0
        
    def start(self):
        """启动异步操作系统"""
        if not self.running:
            self.running = True
            
            # 创建并启动工作线程
            for i in range(self.max_workers):
                worker = AsyncDatabaseWorker(i, self.db_path, self.operation_queue)
                worker.start()
                self.workers.append(worker)
            
            logger.info(f"异步数据操作系统已启动，{self.max_workers} 个工作线程")
    
    def stop(self, timeout: float = 10.0):
        """停止异步操作系统"""
        if self.running:
            self.running = False
            
            # 发送停止信号给所有工作线程
            for _ in self.workers:
                self.operation_queue.put((0, None))
            
            # 等待所有工作线程停止
            for worker in self.workers:
                worker.stop()
            
            self.workers.clear()
            logger.info("异步数据操作系统已停止")
    
    def submit_operation(self, operation: DatabaseOperation) -> str:
        """提交操作到队列"""
        if not self.running:
            raise RuntimeError("异步操作系统未启动")
        
        # 生成操作ID
        if not operation.id:
            operation.id = f"op_{int(time.time() * 1000)}_{len(self.operations)}"
        
        # 存储操作
        self.operations[operation.id] = operation
        
        # 加入队列
        try:
            self.operation_queue.put((operation.priority.value, operation), timeout=1.0)
            
            with self.stats_lock:
                self.total_operations += 1
            
            logger.debug(f"操作 {operation.id} 已提交到队列")
            return operation.id
            
        except queue.Full:
            raise RuntimeError("操作队列已满，请稍后重试")
    
    def get_operation_status(self, operation_id: str) -> Optional[DatabaseOperation]:
        """获取操作状态"""
        return self.operations.get(operation_id)
    
    def cancel_operation(self, operation_id: str) -> bool:
        """取消操作"""
        operation = self.operations.get(operation_id)
        if operation and operation.status == OperationStatus.PENDING:
            operation.status = OperationStatus.CANCELLED
            return True
        return False
    
    def create_batch_operation(self, operation_type: OperationType, 
                             table_name: str) -> BatchOperation:
        """创建批量操作"""
        batch = BatchOperation(operation_type, table_name)
        self.batch_operations[batch.id] = batch
        return batch
    
    def submit_batch_operation(self, batch: BatchOperation, 
                             callback: Optional[Callable[[OperationResult], None]] = None,
                             progress_callback: Optional[Callable[[float, str], None]] = None) -> str:
        """提交批量操作"""
        if len(batch) == 0:
            raise ValueError("批量操作为空")
        
        # 创建数据库操作
        operation = DatabaseOperation(
            id=batch.id,
            operation_type=batch.operation_type,
            sql="",  # 批量操作不需要单个SQL
            priority=OperationPriority.NORMAL,
            callback=callback,
            progress_callback=progress_callback,
            metadata={'batch_data': batch.operations}
        )
        
        return self.submit_operation(operation)
    
    def wait_for_operation(self, operation_id: str, timeout: Optional[float] = None) -> OperationResult:
        """等待操作完成"""
        start_time = time.time()
        
        while True:
            operation = self.operations.get(operation_id)
            if not operation:
                raise ValueError(f"操作 {operation_id} 不存在")
            
            if operation.status in [OperationStatus.COMPLETED, OperationStatus.FAILED, OperationStatus.CANCELLED]:
                return operation.result
            
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"等待操作 {operation_id} 超时")
            
            time.sleep(0.1)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            'queue_size': self.operation_queue.qsize(),
            'max_queue_size': self.queue_size,
            'running_workers': len([w for w in self.workers if w.running]),
            'total_workers': len(self.workers),
            'total_operations': self.total_operations,
            'completed_operations': self.completed_operations_count,
            'failed_operations': self.failed_operations_count,
            'pending_operations': len([op for op in self.operations.values() 
                                     if op.status == OperationStatus.PENDING]),
            'running_operations': len([op for op in self.operations.values() 
                                     if op.status == OperationStatus.RUNNING])
        }
    
    def get_worker_stats(self) -> List[Dict[str, Any]]:
        """获取工作线程统计"""
        stats = []
        for worker in self.workers:
            stats.append({
                'worker_id': worker.worker_id,
                'running': worker.running,
                'operations_processed': worker.operations_processed,
                'total_execution_time': worker.total_execution_time,
                'errors_count': worker.errors_count,
                'average_execution_time': (worker.total_execution_time / worker.operations_processed 
                                         if worker.operations_processed > 0 else 0),
                'current_operation': worker.current_operation.id if worker.current_operation else None
            })
        return stats
    
    def cleanup_completed_operations(self, max_age_hours: int = 24):
        """清理已完成的操作"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        operations_to_remove = []
        for op_id, operation in self.operations.items():
            if (operation.status in [OperationStatus.COMPLETED, OperationStatus.FAILED, OperationStatus.CANCELLED] 
                and operation.completed_at 
                and operation.completed_at.timestamp() < cutoff_time):
                operations_to_remove.append(op_id)
        
        for op_id in operations_to_remove:
            del self.operations[op_id]
        
        logger.info(f"清理了 {len(operations_to_remove)} 个已完成的操作")
        return len(operations_to_remove)