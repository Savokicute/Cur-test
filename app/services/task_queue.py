# coding=utf-8
"""轻量级异步任务队列系统

基于 asyncio 实现的任务队列，支持：
- 优先级队列
- 任务状态跟踪
- 重试机制（指数退避）
- 并发控制
- 任务持久化（SQLite）
- 服务重启后恢复未完成任务

内置任务类型：
  - ArticleFetchTask: 文章抓取任务
  - MediaDownloadTask: 媒体下载任务
  - AIAnalysisTask: AI分析任务
  - NotificationTask: 通知发送任务
  - CleanupTask: 清理任务
"""

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

from sqlalchemy import text
from app.core.database import get_db_session
from app.models import Task as TaskModel, TaskStatus, TaskType, TaskPriority

logger = logging.getLogger(__name__)


# ========== 数据类定义 ==========

@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class TaskInfo:
    """任务信息"""
    id: str
    task_type: str
    params: Dict[str, Any]
    priority: int
    status: str
    progress: float
    result: Optional[Dict] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class WorkerStats:
    """Worker 统计信息"""
    worker_id: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_runtime: float = 0.0
    current_task: Optional[str] = None
    is_busy: bool = False


# ========== 抽象任务基类 ==========

class BaseTask(ABC):
    """任务基类"""

    def __init__(self, task_id: str, params: Dict[str, Any], priority: int = TaskPriority.NORMAL.value):
        self.task_id = task_id
        self.params = params
        self.priority = priority
        self.status = TaskStatus.PENDING.value
        self.progress = 0.0
        self.result = None
        self.error_message = None
        self.retry_count = 0
        self.max_retries = params.get("max_retries", 3)
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None

    @abstractmethod
    async def execute(self) -> TaskResult:
        """
        执行任务

        Returns:
            TaskResult: 执行结果
        """
        pass

    @abstractmethod
    def get_task_type(self) -> str:
        """返回任务类型标识"""
        pass

    async def update_progress(self, progress: float):
        """更新任务进度 (0.0 - 1.0)"""
        self.progress = min(1.0, max(0.0, progress))
        # 可以在这里发送进度更新事件

    async def on_success(self, result: TaskResult):
        """任务成功回调"""
        self.status = TaskStatus.COMPLETED.value
        self.result = result.result
        self.completed_at = datetime.utcnow()
        logger.info(f"任务 {self.task_id} 执行成功")

    async def on_failure(self, error: Exception):
        """任务失败回调"""
        self.error_message = str(error)
        self.retry_count += 1

        if self.retry_count >= self.max_retries:
            self.status = TaskStatus.FAILED.value
            self.completed_at = datetime.utcnow()
            logger.error(f"任务 {self.task_id} 最终失败: {error}")
        else:
            # 计算下次重试时间（指数退避）
            delay = min(2 ** self.retry_count * 5, 300)  # 最大5分钟
            next_retry = datetime.utcnow() + timedelta(seconds=delay)
            logger.warning(f"任务 {self.task_id} 失败，将在 {delay}s 后重试 ({self.retry_count}/{self.max_retries})")
            return next_retry


# ========== 内置任务实现 ==========

class ArticleFetchTask(BaseTask):
    """文章抓取任务"""

    def get_task_type(self) -> str:
        return TaskType.ARTICLE_FETCH.value

    async def execute(self) -> TaskResult:
        start_time = time.time()
        try:
            url = self.params.get("url")
            platform = self.params.get("platform")
            article_id = self.params.get("article_id")

            await self.update_progress(0.1)

            # 这里集成实际的文章抓取逻辑
            from hot_content_bridge.article_crawler import ArticleCrawler
            crawler = ArticleCrawler()

            await self.update_progress(0.3)
            result = await crawler.fetch_article(url, platform=platform)

            await self.update_progress(0.8)

            # 处理结果
            if result.get("success"):
                await self.update_progress(1.0)
                return TaskResult(
                    success=True,
                    result=result,
                    duration_seconds=time.time() - start_time
                )
            else:
                raise Exception(result.get("error", "抓取失败"))

        except Exception as e:
            await self.on_failure(e)
            return TaskResult(
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time
            )


class MediaDownloadTask(BaseTask):
    """媒体下载任务"""

    def get_task_type(self) -> str:
        return TaskType.MEDIA_DOWNLOAD.value

    async def execute(self) -> TaskResult:
        start_time = time.time()
        try:
            url = self.params.get("url")
            media_type = self.params.get("media_type", "image")
            article_id = self.params.get("article_id")

            await self.update_progress(0.1)

            # 集成媒体下载服务
            from app.services.media_service import MediaService
            media_service = MediaService()

            await self.update_progress(0.2)
            result = await media_service.download_media(url, media_type, article_id)

            await self.update_progress(0.8)

            if result.get("success"):
                await self.update_progress(1.0)
                return TaskResult(
                    success=True,
                    result=result,
                    duration_seconds=time.time() - start_time
                )
            else:
                raise Exception(result.get("error", "下载失败"))

        except Exception as e:
            await self.on_failure(e)
            return TaskResult(
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time
            )


class AIAnalysisTask(BaseTask):
    """AI分析任务"""

    def get_task_type(self) -> str:
        return TaskType.AI_ANALYSIS.value

    async def execute(self) -> TaskResult:
        start_time = time.time()
        try:
            config_id = self.params.get("config_id")
            input_data = self.params.get("input_data", {})

            await self.update_progress(0.1)

            # 集成AI分析服务
            from app.services.ai_analysis_service import AIAnalysisService
            ai_service = AIAnalysisService()

            await self.update_progress(0.2)
            report = await ai_service.run_analysis(config_id, input_data)

            await self.update_progress(0.9)

            if report and report.get("status") == "completed":
                await self.update_progress(1.0)
                return TaskResult(
                    success=True,
                    result=report,
                    duration_seconds=time.time() - start_time
                )
            else:
                raise Exception(report.get("error_message", "分析失败"))

        except Exception as e:
            await self.on_failure(e)
            return TaskResult(
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time
            )


class NotificationTask(BaseTask):
    """通知发送任务"""

    def get_task_type(self) -> str:
        return TaskType.NOTIFICATION.value

    async def execute(self) -> TaskResult:
        start_time = time.time()
        try:
            subscription_id = self.params.get("subscription_id")
            items = self.params.get("items", [])

            await self.update_progress(0.1)

            # 集成通知服务
            from app.services.notification_service import NotificationService
            notification_service = NotificationService()

            await self.update_progress(0.3)
            log = await notification_service.trigger_subscription(subscription_id, items)

            await self.update_progress(1.0)

            if log and log.get("status") == "sent":
                return TaskResult(
                    success=True,
                    result=log,
                    duration_seconds=time.time() - start_time
                )
            else:
                raise Exception(log.get("error_message", "通知发送失败"))

        except Exception as e:
            await self.on_failure(e)
            return TaskResult(
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time
            )


class CleanupTask(BaseTask):
    """清理任务"""

    def get_task_type(self) -> str:
        return TaskType.CLEANUP.value

    async def execute(self) -> TaskResult:
        start_time = time.time()
        try:
            cleanup_type = self.params.get("type", "old_logs")
            days = self.params.get("days", 30)

            await self.update_progress(0.1)

            with get_db_session() as db:
                if cleanup_type == "old_logs":
                    cutoff_date = datetime.utcnow() - timedelta(days=days)
                    deleted = db.query(TaskModel).filter(
                        TaskModel.status == TaskStatus.COMPLETED.value,
                        TaskModel.completed_at < cutoff_date
                    ).delete()
                    db.commit()
                    await self.update_progress(1.0)
                    return TaskResult(
                        success=True,
                        result={"deleted_count": deleted},
                        duration_seconds=time.time() - start_time
                    )

                elif cleanup_type == "failed_tasks":
                    deleted = db.query(TaskModel).filter(
                        TaskModel.status == TaskStatus.FAILED.value
                    ).delete()
                    db.commit()
                    await self.update_progress(1.0)
                    return TaskResult(
                        success=True,
                        result={"deleted_count": deleted},
                        duration_seconds=time.time() - start_time
                    )

            raise Exception(f"未知的清理类型: {cleanup_type}")

        except Exception as e:
            await self.on_failure(e)
            return TaskResult(
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time
            )


# ========== 任务工厂 ==========

TASK_REGISTRY: Dict[str, Type[BaseTask]] = {
    TaskType.ARTICLE_FETCH.value: ArticleFetchTask,
    TaskType.MEDIA_DOWNLOAD.value: MediaDownloadTask,
    TaskType.AI_ANALYSIS.value: AIAnalysisTask,
    TaskType.NOTIFICATION.value: NotificationTask,
    TaskType.CLEANUP.value: CleanupTask,
}


def create_task(task_type: str, task_id: str, params: Dict[str, Any], priority: int = TaskPriority.NORMAL.value) -> BaseTask:
    """根据类型创建任务实例"""
    task_class = TASK_REGISTRY.get(task_type)
    if not task_class:
        raise ValueError(f"未知的任务类型: {task_type}")

    return task_class(task_id=task_id, params=params, priority=priority)


# ========== 主任务队列类 ==========

class TaskQueue:
    """
    异步任务队列

    功能：
    - 基于优先级的任务调度
    - Worker 管理
    - 任务持久化与恢复
    - 状态监控
    """

    def __init__(self, max_workers: int = 4, max_concurrent: int = 10):
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._tasks: Dict[str, BaseTask] = {}
        self._workers: List[Dict] = []
        self._max_workers = max_workers
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running = False
        self._worker_stats: Dict[str, WorkerStats] = {}
        self._lock = asyncio.Lock()

        # 统计计数器
        self._total_submitted = 0
        self._total_completed = 0
        self._total_failed = 0

    async def submit(
        self,
        task_type: str,
        params: Dict[str, Any],
        priority: Union[int, TaskPriority] = TaskPriority.NORMAL,
        delay: float = 0
    ) -> str:
        """
        提交任务到队列

        Args:
            task_type: 任务类型
            params: 任务参数
            priority: 优先级（数值越高越优先）
            delay: 延迟执行时间（秒）

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())

        # 创建任务实例
        task = create_task(task_type, task_id, params, priority=priority if isinstance(priority, int) else priority.value)

        # 持久化到数据库
        await self._persist_task(task)

        # 添加到内存字典
        async with self._lock:
            self._tasks[task_id] = task

        # 如果有延迟，使用延迟队列
        if delay > 0:
            asyncio.create_task(self._delayed_submit(task, delay))
        else:
            # 使用负数优先级（因为 PriorityQueue 是最小堆）
            await self._queue.put((-task.priority, task_id))

        self._total_submitted += 1
        logger.info(f"任务已提交: {task_id} (type={task_type}, priority={priority})")

        return task_id

    async def _delayed_submit(self, task: BaseTask, delay: float):
        """延迟提交任务"""
        await asyncio.sleep(delay)
        await self._queue.put((-task.priority, task.task_id))
        logger.info(f"延迟任务已入队: {task.task_id}")

    async def _persist_task(self, task: BaseTask):
        """持久化任务到数据库"""
        try:
            with get_db_session() as db:
                task_record = TaskModel(
                    id=task.task_id,
                    task_type=task.get_task_type(),
                    priority=task.priority,
                    params=task.params,
                    status=task.status,
                    retry_count=task.retry_count,
                    max_retries=task.max_retries,
                    created_at=task.created_at,
                )
                db.add(task_record)
        except Exception as e:
            logger.error(f"任务持久化失败: {e}", exc_info=True)

    async def _update_task_status(self, task_id: str, **kwargs):
        """更新任务状态到数据库"""
        try:
            with get_db_session() as db:
                task = db.query(TaskModel).filter_by(id=task_id).first()
                if task:
                    for key, value in kwargs.items():
                        if hasattr(task, key):
                            setattr(task, key, value)
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}", exc_info=True)

    async def get_status(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务状态"""
        async with self._lock:
            task = self._tasks.get(task_id)

        if not task:
            # 从数据库查询
            with get_db_session() as db:
                record = db.query(TaskModel).filter_by(id=task_id).first()
                if record:
                    return TaskInfo(
                        id=record.id,
                        task_type=record.task_type,
                        params=record.params or {},
                        priority=record.priority,
                        status=record.status,
                        progress=record.progress or 0.0,
                        result=record.result,
                        error_message=record.error_message,
                        retry_count=record.retry_count,
                        max_retries=record.max_retries,
                        created_at=record.created_at,
                        started_at=record.started_at,
                        completed_at=record.completed_at,
                    )
            return None

        return TaskInfo(
            id=task.task_id,
            task_type=task.get_task_type(),
            params=task.params,
            priority=task.priority,
            status=task.status,
            progress=task.progress,
            result=task.result,
            error_message=task.error_message,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
        )

    async def cancel(self, task_id: str) -> bool:
        """取消任务"""
        async with self._lock:
            task = self._tasks.get(task_id)

        if task and task.status in [TaskStatus.PENDING.value, TaskStatus.RETRYING.value]:
            task.status = TaskStatus.CANCELLED.value
            task.completed_at = datetime.utcnow()
            await self._update_task_status(task_id, status=TaskStatus.CANCELLED.value, completed_at=datetime.utcnow())
            logger.info(f"任务已取消: {task_id}")
            return True

        return False

    async def list_tasks(
        self,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TaskInfo]:
        """列出任务"""
        with get_db_session() as db:
            query = db.query(TaskModel)

            if status:
                query = query.filter(TaskModel.status == status)
            if task_type:
                query = query.filter(TaskModel.task_type == task_type)

            records = query.order_by(TaskModel.created_at.desc()).offset(offset).limit(limit).all()

            return [
                TaskInfo(
                    id=r.id,
                    task_type=r.task_type,
                    params=r.params or {},
                    priority=r.priority,
                    status=r.status,
                    progress=r.progress or 0.0,
                    result=r.result,
                    error_message=r.error_message,
                    retry_count=r.retry_count,
                    max_retries=r.max_retries,
                    created_at=r.created_at,
                    started_at=r.started_at,
                    completed_at=r.completed_at,
                )
                for r in records
            ]

    async def get_result(self, task_id: str) -> Optional[Any]:
        """获取任务结果"""
        task_info = await self.get_status(task_id)
        if task_info and task_info.status == TaskStatus.COMPLETED.value:
            return task_info.result
        return None

    async def retry_failed_task(self, task_id: str) -> bool:
        """重试失败的任务"""
        task_info = await self.get_status(task_id)
        if task_info and task_info.status == TaskStatus.FAILED.value:
            # 重置状态并重新提交
            await self.submit(
                task_type=task_info.task_type,
                params=task_info.params,
                priority=task_info.priority
            )
            return True
        return False

    async def _worker(self, worker_id: str):
        """Worker 主循环"""
        stats = WorkerStats(worker_id=worker_id)
        self._worker_stats[worker_id] = stats

        logger.info(f"Worker {worker_id} 已启动")

        while self._running:
            try:
                # 从队列获取任务（带超时）
                try:
                    priority, task_id = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # 获取任务实例
                async with self._lock:
                    task = self._tasks.get(task_id)

                if not task or task.status == TaskStatus.CANCELLED.value:
                    continue

                # 并发控制
                async with self._semaphore:
                    stats.is_busy = True
                    stats.current_task = task_id

                    # 更新状态为运行中
                    task.status = TaskStatus.RUNNING.value
                    task.started_at = datetime.utcnow()
                    await self._update_task_status(
                        task_id,
                        status=TaskStatus.RUNNING.value,
                        started_at=datetime.utcnow()
                    )

                    start_time = time.time()

                    try:
                        # 执行任务
                        result = await task.execute()

                        if result.success:
                            await task.on_success(result)
                            self._total_completed += 1
                            stats.tasks_completed += 1
                        else:
                            retry_time = await task.on_failure(Exception(result.error))
                            if retry_time and task.status != TaskStatus.FAILED.value:
                                task.status = TaskStatus.RETRYING.value
                                await self._update_task_status(
                                    task_id,
                                    status=TaskStatus.RETRYING.value,
                                    retry_count=task.retry_count,
                                    error_message=task.error_message,
                                    next_retry_at=retry_time
                                )
                                # 重新加入队列
                                asyncio.create_task(self._delayed_submit(task, (retry_time - datetime.utcnow()).total_seconds()))
                            else:
                                self._total_failed += 1
                                stats.tasks_failed += 1

                        # 更新数据库记录
                        await self._update_task_status(
                            task_id,
                            status=task.status,
                            progress=task.progress,
                            result=task.result,
                            error_message=task.error_message,
                            completed_at=task.completed_at
                        )

                    except Exception as e:
                        logger.error(f"Worker {worker_id} 执行任务异常: {e}", exc_info=True)
                        task.error_message = str(e)
                        task.status = TaskStatus.FAILED.value
                        task.completed_at = datetime.utcnow()
                        self._total_failed += 1
                        stats.tasks_failed += 1

                        await self._update_task_status(
                            task_id,
                            status=TaskStatus.FAILED.value,
                            error_message=str(e),
                            completed_at=datetime.utcnow()
                        )

                    finally:
                        runtime = time.time() - start_time
                        stats.total_runtime += runtime
                        stats.is_busy = False
                        stats.current_task = None
                        self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} 发生错误: {e}", exc_info=True)
                await asyncio.sleep(1)  # 避免错误循环

        logger.info(f"Worker {worker_id} 已停止")

    async def start_workers(self, num_workers: int = None):
        """启动 Worker"""
        if self._running:
            logger.warning("任务队列已在运行")
            return

        num_workers = num_workers or self._max_workers
        self._running = True

        # 启动 workers
        for i in range(num_workers):
            worker_id = f"worker-{i+1}"
            worker_task = asyncio.create_task(self._worker(worker_id))
            self._workers.append({"id": worker_id, "task": worker_task})

        # 恢复未完成的任务
        await self._recover_pending_tasks()

        logger.info(f"任务队列已启动，共 {num_workers} 个 Worker")

    async def stop_workers(self):
        """停止所有 Worker"""
        if not self._running:
            return

        self._running = False

        # 取消所有 worker 任务
        for worker in self._workers:
            worker["task"].cancel()

        # 等待所有 worker 完成
        await asyncio.gather(*[w["task"] for w in self._workers], return_exceptions=True)

        self._workers.clear()
        logger.info("所有 Worker 已停止")

    async def _recover_pending_tasks(self):
        """恢复未完成的任务（从数据库）"""
        try:
            with get_db_session() as db:
                pending_tasks = db.query(TaskModel).filter(
                    TaskModel.status.in_([
                        TaskStatus.PENDING.value,
                        TaskStatus.RETRYING.value
                    ])
                ).all()

                recovered = 0
                for task_record in pending_tasks:
                    try:
                        task = create_task(
                            task_type=task_record.task_type,
                            task_id=task_record.id,
                            params=task_record.params or {},
                            priority=task_record.priority
                        )
                        task.retry_count = task_record.retry_count

                        async with self._lock:
                            self._tasks[task_record.id] = task

                        await self._queue.put((-task.priority, task_record.id))
                        recovered += 1
                    except Exception as e:
                        logger.error(f"恢复任务失败 {task_record.id}: {e}")

                if recovered > 0:
                    logger.info(f"已恢复 {recovered} 个未完成任务")

        except Exception as e:
            logger.error(f"恢复任务时出错: {e}", exc_info=True)

    async def get_worker_stats(self) -> Dict[str, Any]:
        """获取 Worker 统计信息"""
        active_workers = sum(1 for s in self._worker_stats.values() if s.is_busy)

        return {
            "queue_size": self._queue.qsize(),
            "total_workers": len(self._workers),
            "active_workers": active_workers,
            "worker_details": {
                wid: {
                    "is_busy": stats.is_busy,
                    "current_task": stats.current_task,
                    "tasks_completed": stats.tasks_completed,
                    "tasks_failed": stats.tasks_failed,
                    "total_runtime": round(stats.total_runtime, 2),
                }
                for wid, stats in self._worker_stats.items()
            },
            "total_submitted": self._total_submitted,
            "total_completed": self._total_completed,
            "total_failed": self._total_failed,
            "pending_tasks": self._queue.qsize(),
        }

    async def get_queue_info(self) -> Dict[str, Any]:
        """获取队列信息"""
        with get_db_session() as db:
            status_counts = {}
            for status in TaskStatus:
                count = db.query(TaskModel).filter(TaskModel.status == status.value).count()
                status_counts[status.value] = count

        return {
            "running": self._running,
            "queue_size": self._queue.qsize(),
            "status_distribution": status_counts,
            "worker_stats": await self.get_worker_stats(),
        }


# ========== 全局单例 ==========
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """获取全局任务队列实例"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue(max_workers=4)
    return _task_queue


async def init_task_queue():
    """初始化并启动任务队列"""
    queue = get_task_queue()
    await queue.start_workers()
    logger.info("全局任务队列已初始化")


async def shutdown_task_queue():
    """关闭任务队列"""
    global _task_queue
    if _task_queue:
        await _task_queue.stop_workers()
        _task_queue = None
        logger.info("全局任务队列已关闭")


# ========== 便捷函数 ==========

async def submit_article_fetch(url: str, platform: str = None, article_id: int = None, priority: int = TaskPriority.NORMAL.value) -> str:
    """提交文章抓取任务"""
    queue = get_task_queue()
    return await queue.submit(
        task_type=TaskType.ARTICLE_FETCH.value,
        params={
            "url": url,
            "platform": platform,
            "article_id": article_id,
        },
        priority=priority
    )


async def submit_media_download(url: str, media_type: str = "image", article_id: int = None, priority: int = TaskPriority.LOW.value) -> str:
    """提交媒体下载任务"""
    queue = get_task_queue()
    return await queue.submit(
        task_type=TaskType.MEDIA_DOWNLOAD.value,
        params={
            "url": url,
            "media_type": media_type,
            "article_id": article_id,
        },
        priority=priority
    )


async def submit_ai_analysis(config_id: int, input_data: dict, priority: int = TaskPriority.HIGH.value) -> str:
    """提交AI分析任务"""
    queue = get_task_queue()
    return await queue.submit(
        task_type=TaskType.AI_ANALYSIS.value,
        params={
            "config_id": config_id,
            "input_data": input_data,
        },
        priority=priority
    )


async def submit_notification(subscription_id: int, items: list = None, priority: int = TaskPriority.NORMAL.value) -> str:
    """提交通知发送任务"""
    queue = get_task_queue()
    return await queue.submit(
        task_type=TaskType.NOTIFICATION.value,
        params={
            "subscription_id": subscription_id,
            "items": items or [],
        },
        priority=priority
    )


async def submit_cleanup(cleanup_type: str = "old_logs", days: int = 30) -> str:
    """提交清理任务"""
    queue = get_task_queue()
    return await queue.submit(
        task_type=TaskType.CLEANUP.value,
        params={
            "type": cleanup_type,
            "days": days,
        },
        priority=TaskPriority.LOW.value
    )
