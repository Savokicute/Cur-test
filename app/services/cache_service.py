# coding=utf-8
"""多级缓存系统 - 三级缓存架构

L1: 内存缓存 (进程内) - 使用 TTLCache
L2: Redis 缓存 (可选) - 用于分布式场景
L3: 文件系统缓存 - 用于静态数据和模板

缓存键命名规范:
  - hotspots:{platform}:{date} - 热榜列表
  - article:{id} - 文章详情
  - stats:{type}:{date} - 统计数据
  - config:{section} - 配置数据
  - subscription:* - 订阅相关数据
"""

import asyncio
import functools
import hashlib
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Set, Union
from cachetools import TTLCache
import threading

logger = logging.getLogger(__name__)


# ========== 缓存配置常量 ==========
class CacheConfig:
    """缓存配置"""
    # L1 内存缓存配置
    L1_MAX_SIZE = 1000  # 最大缓存条目数
    L1_DEFAULT_TTL = 300  # 默认TTL (秒)

    # 各类数据的默认TTL (秒)
    HOTSPOTS_TTL = 5 * 60      # 热榜数据: 5分钟
    STATS_TTL = 10 * 60        # 平台统计: 10分钟
    CONFIG_TTL = 30 * 60       # 配置数据: 30分钟
    ARTICLE_TTL = 10 * 60      # 文章详情: 10分钟
    MEDIA_META_TTL = 60 * 60   # 媒体元数据: 1小时
    TEMPLATE_TTL = 24 * 60 * 60 # 模板渲染结果: 24小时

    # L2 Redis 配置
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_ENABLED = False  # 默认禁用，需要Redis时设置为True

    # L3 文件缓存配置
    FILE_CACHE_DIR = Path("./cache")  # 文件缓存目录


# ========== 缓存键命名工具 ==========

class CacheKey:
    """缓存键生成工具类"""

    @staticmethod
    def hotspots(platform: str, date: str) -> str:
        return f"hotspots:{platform}:{date}"

    @staticmethod
    def article(article_id: Union[int, str]) -> str:
        return f"article:{article_id}"

    @staticmethod
    def stats(stats_type: str, date: str = "") -> str:
        if date:
            return f"stats:{stats_type}:{date}"
        return f"stats:{stats_type}"

    @staticmethod
    def config(section: str) -> str:
        return f"config:{section}"

    @staticmethod
    def subscription(subscription_id: int = None) -> str:
        if subscription_id:
            return f"subscription:{subscription_id}"
        return "subscription:list"

    @staticmethod
    def notification_logs(subscription_id: int = None) -> str:
        if subscription_id:
            return f"notification_logs:{subscription_id}"
        return "notification_logs:list"

    @staticmethod
    def task(task_id: str = None) -> str:
        if task_id:
            return f"task:{task_id}"
        return "task:list"

    @staticmethod
    def generate_key(prefix: str, **kwargs) -> str:
        """生成带参数的缓存键"""
        if kwargs:
            param_str = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
            hash_suffix = hashlib.md5(param_str.encode()).hexdigest()[:8]
            return f"{prefix}:{hash_suffix}"
        return prefix


# ========== 抽象缓存后端 ==========

class CacheBackend(ABC):
    """缓存后端抽象基类"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        pass


# ========== L1: 内存缓存实现 ==========

class MemoryCacheBackend(CacheBackend):
    """
    L1 内存缓存后端

    使用 cachetools.TTLCache 实现，支持自动过期
    """

    def __init__(self, max_size: int = CacheConfig.L1_MAX_SIZE):
        self._cache: TTLCache = TTLCache(maxsize=max_size, ttl=CacheConfig.L1_DEFAULT_TTL)
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[Any]:
        with self._lock:
            try:
                value = self._cache.get(key)
                if value is not None:
                    self._hits += 1
                    logger.debug(f"L1 命中: {key}")
                    return value
                else:
                    self._misses += 1
                    logger.debug(f"L1 未命中: {key}")
                    return None
            except Exception as e:
                logger.error(f"L1 缓存读取失败 {key}: {e}")
                return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            with self._lock:
                if ttl and ttl != CacheConfig.L1_DEFAULT_TTL:
                    # 对于自定义TTL，我们需要特殊处理
                    # 这里简化处理，使用默认TTL
                    self._cache[key] = value
                else:
                    self._cache[key] = value
                logger.debug(f"L1 设置: {key}")
                return True
        except Exception as e:
            logger.error(f"L1 缓存写入失败 {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        with self._lock:
            try:
                if key in self._cache:
                    del self._cache[key]
                    logger.debug(f"L1 删除: {key}")
                    return True
                return False
            except Exception as e:
                logger.error(f"L1 缓存删除失败 {key}: {e}")
                return False

    async def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的缓存键"""
        count = 0
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_delete:
                try:
                    del self._cache[key]
                    count += 1
                except KeyError:
                    pass
        logger.info(f"L1 清除模式 '{pattern}': 删除了 {count} 个键")
        return count

    async def exists(self, key: str) -> bool:
        with self._lock:
            return key in self._cache

    async def get_stats(self) -> Dict[str, Any]:
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "backend": "memory",
            "current_size": len(self._cache),
            "max_size": self._cache.maxsize,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
        }


# ========== L2: Redis 缓存实现（可选）==========

class RedisCacheBackend(CacheBackend):
    """
    L2 Redis 缓存后端（可选）

    需要安装 redis 包并且 Redis 服务可用
    """

    def __init__(self, url: str = CacheConfig.REDIS_URL):
        self._url = url
        self._redis = None
        self._enabled = False
        self._hits = 0
        self._misses = 0

    async def _get_redis(self):
        """懒加载 Redis 连接"""
        if self._redis is None:
            try:
                import aioredis
                self._redis = await aioredis.from_url(self._url)
                self._enabled = True
                logger.info("Redis 连接成功")
            except ImportError:
                logger.warning("aioredis 未安装，Redis 缓存不可用")
                self._enabled = False
            except Exception as e:
                logger.error(f"Redis 连接失败: {e}")
                self._enabled = False
        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        if not self._enabled:
            return None

        try:
            redis = await self._get_redis()
            data = await redis.get(key)
            if data:
                self._hits += 1
                return json.loads(data)
            else:
                self._misses += 1
                return None
        except Exception as e:
            logger.error(f"Redis 读取失败 {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if not self._enabled:
            return False

        try:
            redis = await self._get_redis()
            data = json.dumps(value, ensure_ascii=False)
            if ttl:
                await redis.setex(key, ttl, data)
            else:
                await redis.set(key, data)
            return True
        except Exception as e:
            logger.error(f"Redis 写入失败 {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        if not self._enabled:
            return False

        try:
            redis = await self._get_redis()
            result = await redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis 删除失败 {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        if not self._enabled:
            return 0

        try:
            redis = await self._get_redis()
            keys = await redis.keys(pattern)
            if keys:
                count = await redis.delete(*keys)
                return count
            return 0
        except Exception as e:
            logger.error(f"Redis 模式删除失败 {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        if not self._enabled:
            return False

        try:
            redis = await self._get_redis()
            return await redis.exists(key) > 0
        except Exception:
            return False

    async def get_stats(self) -> Dict[str, Any]:
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        stats = {
            "backend": "redis",
            "enabled": self._enabled,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
        }

        if self._enabled:
            try:
                redis = await self._get_redis()
                info = await redis.info("memory")
                stats.update({
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "connected_clients": info.get("connected_clients", 0),
                })
            except Exception:
                pass

        return stats


# ========== L3: 文件系统缓存实现 ==========

class FileCacheBackend(CacheBackend):
    """
    L3 文件系统缓存后端

    适用于缓存大型对象或需要持久化的数据
    """

    def __init__(self, cache_dir: Union[str, Path] = CacheConfig.FILE_CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径（使用哈希避免文件名问题）"""
        safe_key = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"

    def _is_expired(self, file_path: Path, ttl: int) -> bool:
        """检查文件是否已过期"""
        if not file_path.exists():
            return True

        file_age = time.time() - file_path.stat().st_mtime
        return file_age > ttl

    async def get(self, key: str, ttl: int = 3600) -> Optional[Any]:
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        if self._is_expired(cache_path, ttl):
            try:
                cache_path.unlink()
            except Exception:
                pass
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"L3 文件命中: {key}")
            return data
        except Exception as e:
            logger.error(f"L3 文件读取失败 {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            cache_path = self._get_cache_path(key)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(value, f, ensure_ascii=False, default=str)
            logger.debug(f"L3 文件设置: {key}")
            return True
        except Exception as e:
            logger.error(f"L3 文件写入失败 {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                cache_path.unlink()
                logger.debug(f"L3 文件删除: {key}")
                return True
            except Exception as e:
                logger.error(f"L3 文件删除失败 {key}: {e}")
        return False

    async def clear_pattern(self, pattern: str) -> int:
        """文件缓存不支持模式匹配，返回0"""
        logger.warning("L3 文件缓存不支持模式匹配清除")
        return 0

    async def exists(self, key: str) -> bool:
        return self._get_cache_path(key).exists()

    async def get_stats(self) -> Dict[str, Any]:
        try:
            file_count = len(list(self.cache_dir.glob("*.cache")))
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.cache"))
        except Exception:
            file_count = 0
            total_size = 0

        return {
            "backend": "file",
            "cache_dir": str(self.cache_dir),
            "file_count": file_count,
            "total_size_bytes": total_size,
            "total_size_human": f"{total_size / 1024:.1f} KB",
        }


# ========== 主缓存服务类 ==========

class CacheService:
    """
    多级缓存服务

    提供统一的缓存接口，自动在 L1/L2/L3 之间协调
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 初始化各级缓存后端
        self.l1 = MemoryCacheBackend()
        self.l2 = RedisCacheBackend() if CacheConfig.REDIS_ENABLED else None
        self.l3 = FileCacheBackend()

        self._initialized = True
        logger.info("多级缓存服务初始化完成")

    async def get(
        self,
        key: str,
        ttl: Optional[int] = None,
        use_l2: bool = False,
        use_l3: bool = False,
        l3_ttl: int = 3600
    ) -> Optional[Any]:
        """
        获取缓存值（优先从L1读取）

        Args:
            key: 缓存键
            ttl: L1缓存的TTL（秒）
            use_l2: 是否尝试从L2读取
            use_l3: 是否尝试从L3读取
            l3_ttl: L3缓存的TTL（秒）

        Returns:
            缓存的值，如果不存在则返回None
        """
        # L1: 内存缓存（最快）
        value = await self.l1.get(key)
        if value is not None:
            return value

        # L2: Redis缓存（分布式场景）
        if use_l2 and self.l2:
            value = await self.l2.get(key)
            if value is not None:
                # 回填到L1
                await self.l1.set(key, value, ttl)
                return value

        # L3: 文件缓存（持久化）
        if use_l3:
            value = await self.l3.get(key, ttl=l3_ttl)
            if value is not None:
                # 回填到L1
                await self.l1.set(key, value, ttl)
                return value

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        persist_to_l2: bool = False,
        persist_to_l3: bool = False,
        l3_ttl: int = 3600
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: L1缓存的TTL（秒）
            persist_to_l2: 是否同时写入L2
            persist_to_l3: 是否同时写入L3
            l3_ttl: L3缓存的TTL（秒）

        Returns:
            是否成功
        """
        success = True

        # 写入L1
        if not await self.l1.set(key, value, ttl):
            success = False

        # 写入L2（可选）
        if persist_to_l2 and self.l2:
            if not await self.l2.set(key, value, ttl):
                logger.warning(f"L2 写入失败: {key}")

        # 写入L3（可选）
        if persist_to_l3:
            if not await self.l3.set(key, value, l3_ttl):
                logger.warning(f"L3 写入失败: {key}")

        return success

    async def delete(self, key: str, delete_from_all: bool = True) -> bool:
        """
        删除缓存值

        Args:
            key: 缓存键
            delete_from_all: 是否从所有层级删除

        Returns:
            是否成功
        """
        deleted = False

        # 从L1删除
        if await self.l1.delete(key):
            deleted = True

        if delete_from_all:
            # 从L2删除
            if self.l2:
                await self.l2.delete(key)

            # 从L3删除
            await self.l3.delete(key)

        return deleted

    async def clear_pattern(self, pattern: str) -> Dict[str, int]:
        """
        清除匹配模式的所有缓存

        Args:
            pattern: 匹配模式（支持子串匹配）

        Returns:
            各层删除的条目数
        """
        results = {
            "l1": await self.l1.clear_pattern(pattern),
            "l2": 0,
            "l3": 0,
        }

        if self.l2:
            results["l2"] = await self.l2.clear_pattern(f"*{pattern}*")

        results["l3"] = await self.l3.clear_pattern(pattern)

        total = sum(results.values())
        logger.info(f"清除模式 '{pattern}': 共删除 {total} 条缓存")

        return results

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[int] = None,
        use_l2: bool = False,
        use_l3: bool = False
    ) -> Any:
        """
        获取缓存或通过工厂函数创建并缓存（穿透保护）

        Args:
            key: 缓存键
            factory: 数据工厂函数（在缓存未命中时调用）
            ttl: 缓存TTL（秒）
            use_l2: 是否使用L2缓存
            use_l3: 是否使用L3缓存

        Returns:
            缓存或新创建的值
        """
        # 尝试从缓存获取
        value = await self.get(key, ttl=ttl, use_l2=use_l2, use_l3=use_l3)
        if value is not None:
            return value

        # 缓存未命中，调用工厂函数创建数据
        try:
            if asyncio.iscoroutinefunction(factory):
                value = await factory()
            else:
                value = factory()

            # 写入缓存
            await self.set(key, value, ttl=ttl, persist_to_l2=use_l2, persist_to_l3=use_l3)

            return value

        except Exception as e:
            logger.error(f"缓存工厂函数执行失败 {key}: {e}", exc_info=True)
            raise

    # ========== 特定领域的便捷方法 ==========

    async def invalidate_hotspots(self, platform: Optional[str] = None, date: Optional[str] = None):
        """使热榜缓存失效"""
        if platform and date:
            key = CacheKey.hotspots(platform, date)
            await self.delete(key)
        else:
            await self.clear_pattern("hotspots:")

    async def invalidate_article(self, article_id: Union[int, str]):
        """使文章缓存失效"""
        key = CacheKey.article(article_id)
        await self.delete(key)

    async def invalidate_subscriptions(self):
        """使所有订阅缓存失效"""
        await self.clear_pattern("subscription:")

    async def invalidate_notification_logs(self, subscription_id: Optional[int] = None):
        """使通知日志缓存失效"""
        if subscription_id:
            key = CacheKey.notification_logs(subscription_id)
            await self.delete(key)
        else:
            await self.clear_pattern("notification_logs:")

    async def get_stats(self) -> Dict[str, Any]:
        """获取所有缓存层的统计信息"""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "l1": await self.l1.get_stats(),
        }

        if self.l2:
            stats["l2"] = await self.l2.get_stats()

        stats["l3"] = await self.l3.get_stats()

        return stats

    async def clear_all(self) -> Dict[str, int]:
        """清空所有缓存"""
        results = {
            "l1": await self.l1.clear_pattern(""),  # 清空所有
            "l2": 0,
            "l3": 0,
        }

        if self.l2:
            results["l2"] = await self.l2.clear_pattern("*")

        # L3文件缓存：删除所有缓存文件
        try:
            count = 0
            for f in self.l3.cache_dir.glob("*.cache"):
                f.unlink()
                count += 1
            results["l3"] = count
        except Exception as e:
            logger.error(f"清空L3缓存失败: {e}")

        logger.info(f"已清空所有缓存层")
        return results


# ========== 全局单例实例 ==========
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """获取全局缓存服务实例"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


# ========== 缓存装饰器 ==========

def cached(
    ttl: int = CacheConfig.L1_DEFAULT_TTL,
    key_prefix: str = "",
    use_l2: bool = False,
    use_l3: bool = False
):
    """
    缓存装饰器

    用法:
        @cached(ttl=300, key_prefix="user:")
        async def get_user(user_id):
            ...

    Args:
        ttl: 缓存有效期（秒）
        key_prefix: 键前缀
        use_l2: 是否使用L2缓存
        use_l3: 是否使用L3缓存
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}{func.__name__}"
            if args or kwargs:
                key_args = [str(a) for a in args[1:]]  # 跳过self
                key_kwargs = [f"{k}={v}" for k, v in sorted(kwargs.items())]
                hash_str = hashlib.md5(":".join(key_args + key_kwargs).encode()).hexdigest()[:12]
                cache_key = f"{cache_key}:{hash_str}"

            cache = get_cache_service()

            # 尝试获取缓存
            value = await cache.get(cache_key, ttl=ttl, use_l2=use_l2, use_l3=use_l3)
            if value is not None:
                return value

            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl=ttl, persist_to_l2=use_l2, persist_to_l3=use_l3)

            return result

        return wrapper
    return decorator


# ========== 导出的便捷函数 ==========

async def get_cached_hotspots(platform: str, date: str):
    """获取缓存的热榜数据"""
    cache = get_cache_service()
    key = CacheKey.hotspots(platform, date)
    return await cache.get(key, ttl=CacheConfig.HOTSPOTS_TTL)


async def set_cached_hotspots(platform: str, date: str, data: Any):
    """设置热榜数据到缓存"""
    cache = get_cache_service()
    key = CacheKey.hotspots(platform, date)
    return await cache.set(key, data, ttl=CacheConfig.HOTSPOTS_TTL)


async def get_cached_article(article_id: Union[int, str]):
    """获取缓存的文章详情"""
    cache = get_cache_service()
    key = CacheKey.article(article_id)
    return await cache.get(key, ttl=CacheConfig.ARTICLE_TTL)


async def set_cached_article(article_id: Union[int, str], data: Any):
    """设置文章详情到缓存"""
    cache = get_cache_service()
    key = CacheKey.article(article_id)
    return await cache.set(key, data, ttl=CacheConfig.ARTICLE_TTL)


async def get_cached_config(section: str):
    """获取缓存的配置数据"""
    cache = get_cache_service()
    key = CacheKey.config(section)
    return await cache.get(key, ttl=CacheConfig.CONFIG_TTL)


async def set_cached_config(section: str, data: Any):
    """设置配置数据到缓存"""
    cache = get_cache_service()
    key = CacheKey.config(section)
    return await cache.set(key, data, ttl=CacheConfig.CONFIG_TTL)
