# coding=utf-8
"""媒体处理集成器 - 将 MediaService 集成到内容抓取流程

在文章/热榜抓取完成后，自动提取并下载其中的图片和视频封面。
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from sqlalchemy.orm import Session

from app.models import MediaItem
from app.services.media_service import MediaService

logger = logging.getLogger(__name__)


class MediaProcessor:
    """
    媒体处理集成器

    负责从抓取的内容中提取媒体URL，并通过MediaService下载存储。
    """

    # 图片URL正则模式
    IMAGE_URL_PATTERNS = [
        r'https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|gif|webp)(?:\?[^\s"\'<>]*)?',
        r'https?://[^\s"\'<>]+/(?:image|img|photo|pic|thumb|avatar|cover|poster)[^\s"\'<>]*',
        r'!\[.*?\]\((https?://[^\)]+)\)',  # Markdown图片语法
        r'<img[^>]+src=["\'](https?://[^"\']+)["\']',  # HTML img标签
        r'url\(["\']?(https?://[^"\')\s]+\.(?:jpg|jpeg|png|gif|webp))',  # CSS背景图
    ]

    # 视频URL正则模式（用于提取封面）
    VIDEO_URL_PATTERNS = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[a-zA-Z0-9_-]{11}',
        r'https?://youtu\.be/[a-zA-Z0-9_-]{11}',
        r'https?://(?:www\.)?bilibili\.com/video/[BVa-zA-Z0-9]+',
        r'https?://b23\.tv/[a-zA-Z0-9]+',
        r'https?://(?:www\.)?douyin\.com/video/\d+',
        r'https?://v\.qq\.com/x/page/[a-zA-Z0-9]+',
        r'https?://(?:www\.)?iqiyi\.com/v_[a-zA-Z0-9]+',
        r'<video[^>]+src=["\'](https?://[^"\']+)["\']',  # HTML video标签
        r'<iframe[^>]+src=["\'](https?://[^"\']*?(?:youtube|bilibili|video|player)[^"\']*)["\']',
    ]

    # 最大处理的媒体数量限制
    MAX_IMAGES_PER_ARTICLE: int = 20
    MAX_VIDEOS_PER_ARTICLE: int = 5

    def __init__(self, media_service: Optional[MediaService] = None):
        """
        初始化媒体处理器

        Args:
            media_service: 媒体服务实例，如果为None则自动创建
        """
        self.media_service = media_service or MediaService()

    async def process_article_media(
        self,
        article_id: Optional[int],
        content: str,
        source_platform: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        处理单篇文章的媒体文件

        从文章内容（Markdown或HTML）中提取所有图片和视频URL，
        然后异步下载并存储。

        Args:
            article_id: 关联的文章ID（可为空，如热榜项）
            content: 文章内容（Markdown或HTML格式）
            source_platform: 来源平台标识
            db: 数据库会话（可选）

        Returns:
            dict: 处理结果统计
                {
                    "images_found": int,
                    "images_downloaded": int,
                    "images_failed": int,
                    "videos_found": int,
                    "video_covers_downloaded": int,
                    "media_items": list,  # 创建的MediaItem记录列表
                }
        """
        result = {
            "images_found": 0,
            "images_downloaded": 0,
            "images_failed": 0,
            "videos_found": 0,
            "video_covers_downloaded": 0,
            "media_items": [],
        }

        if not content or not isinstance(content, str):
            return result

        try:
            # 提取图片URLs
            image_urls = self._extract_image_urls(content)
            image_urls = self._deduplicate_urls(image_urls)[:self.MAX_IMAGES_PER_ARTICLE]
            result["images_found"] = len(image_urls)

            # 提取视频URLs
            video_urls = self._extract_video_urls(content)
            video_urls = self._deduplicate_urls(video_urls)[:self.MAX_VIDEOS_PER_ARTICLE]
            result["videos_found"] = len(video_urls)

            # 异步下载图片
            for url in image_urls:
                try:
                    download_result = await self.media_service.download_image(
                        url=url,
                        source_platform=source_platform,
                    )

                    # 创建数据库记录
                    media_item = self._create_media_record(
                        article_id=article_id,
                        original_url=url,
                        stored_path=download_result.get("stored_path"),
                        media_type="image",
                        is_video_cover=False,
                        download_result=download_result,
                        source_platform=source_platform,
                        db=db,
                    )

                    if media_item:
                        result["media_items"].append(media_item)
                        result["images_downloaded"] += 1

                except Exception as e:
                    logger.warning(f"图片下载失败 [{url}]: {e}")
                    result["images_failed"] += 1

                    # 创建失败记录
                    if db:
                        self._create_failed_record(
                            article_id=article_id,
                            original_url=url,
                            media_type="image",
                            error_msg=str(e),
                            source_platform=source_platform,
                            db=db,
                        )

            # 异步处理视频封面
            for url in video_urls:
                try:
                    download_result = await self.media_service.download_video_cover(
                        url=url,
                        source_platform=source_platform,
                    )

                    if download_result.get("cover_extracted"):
                        media_item = self._create_media_record(
                            article_id=article_id,
                            original_url=url,
                            stored_path=download_result.get("stored_path"),
                            media_type="video",
                            is_video_cover=True,
                            download_result=download_result,
                            source_platform=source_platform,
                            db=db,
                        )

                        if media_item:
                            result["media_items"].append(media_item)
                            result["video_covers_downloaded"] += 1

                except Exception as e:
                    logger.warning(f"视频封面提取失败 [{url}]: {e}")

            logger.info(
                f"文章媒体处理完成: 图片 {result['images_downloaded']}/{result['images_found']}, "
                f"视频封面 {result['video_covers_downloaded']}/{result['videos_found']}"
            )

        except Exception as e:
            logger.error(f"文章媒体处理异常: {e}", exc_info=True)

        return result

    async def process_hotspot_item(
        self,
        hotspot_data: Dict[str, Any],
        source_platform: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        处理热榜项的媒体文件

        从热榜数据中提取图片（如封面图、缩略图等）

        Args:
            hotspot_data: 热榜项数据字典
            source_platform: 来源平台标识
            db: 数据库会话（可选）

        Returns:
            dict: 处理结果统计
        """
        result = {
            "images_found": 0,
            "images_downloaded": 0,
            "images_failed": 0,
            "media_items": [],
        }

        if not hotspot_data or not isinstance(hotspot_data, dict):
            return result

        try:
            # 常见的图片字段名
            image_fields = [
                "image", "pic", "picture", "thumbnail", "thumb",
                "cover", "poster", "avatar", "icon", "img_url",
                "image_url", "pic_url", "cover_image",
            ]

            image_urls = []
            for field in image_fields:
                url = hotspot_data.get(field)
                if url and isinstance(url, str) and url.startswith(("http://", "https://")):
                    image_urls.append(url)

            # 也检查 extra/raw_extra 字段中的图片
            extra = hotspot_data.get("extra") or hotspot_data.get("raw_extra")
            if isinstance(extra, (str, dict)):
                extra_str = str(extra)
                extra_images = self._extract_image_urls(extra_str)
                image_urls.extend(extra_images[:5])  # 最多额外提取5张

            # 去重并限制数量
            image_urls = self._deduplicate_urls(image_urls)[:10]
            result["images_found"] = len(image_urls)

            for url in image_urls:
                try:
                    download_result = await self.media_service.download_image(
                        url=url,
                        source_platform=source_platform,
                    )

                    media_item = self._create_media_record(
                        article_id=None,  # 热榜项可能没有article_id
                        original_url=url,
                        stored_path=download_result.get("stored_path"),
                        media_type="image",
                        is_video_cover=False,
                        download_result=download_result,
                        source_platform=source_platform,
                        db=db,
                    )

                    if media_item:
                        result["media_items"].append(media_item)
                        result["images_downloaded"] += 1

                except Exception as e:
                    logger.warning(f"热榜图片下载失败 [{url}]: {e}")
                    result["images_failed"] += 1

        except Exception as e:
            logger.error(f"热榜媒体处理异常: {e}", exc_info=True)

        return result

    def _extract_image_urls(self, content: str) -> List[str]:
        """从内容中提取所有图片URL"""
        urls = []
        for pattern in self.IMAGE_URL_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            urls.extend(matches)

        # 清理URL（去除Markdown语法残留）
        cleaned_urls = []
        for url in urls:
            cleaned = url.strip().strip("'\"").rstrip(")")
            if cleaned.startswith("http"):
                cleaned_urls.append(cleaned)

        return cleaned_urls

    def _extract_video_urls(self, content: str) -> List[str]:
        """从内容中提取所有视频URL"""
        urls = []
        for pattern in self.VIDEO_URL_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            urls.extend(matches)

        # 清理URL
        cleaned_urls = []
        for url in urls:
            cleaned = url.strip().strip("'\"")
            if cleaned.startswith("http"):
                cleaned_urls.append(cleaned)

        return cleaned_urls

    @staticmethod
    def _deduplicate_urls(urls: List[str]) -> List[str]:
        """URL去重（保留顺序）"""
        seen = set()
        unique = []
        for url in urls:
            # 规范化URL（去除查询参数中的时间戳等）
            normalized = url.split("?")[0] if "?" in url else url
            if normalized not in seen:
                seen.add(normalized)
                unique.append(url)
        return unique

    def _create_media_record(
        self,
        article_id: Optional[int],
        original_url: str,
        stored_path: Optional[str],
        media_type: str,
        is_video_cover: bool,
        download_result: Dict[str, Any],
        source_platform: Optional[str],
        db: Optional[Session],
    ) -> Optional[MediaItem]:
        """创建媒体文件数据库记录"""
        if not db:
            return None

        try:
            media_item = MediaItem(
                article_id=article_id,
                original_url=original_url,
                stored_path=stored_path,
                media_type=media_type,
                is_video_cover=is_video_cover,
                file_size=download_result.get("file_size", 0),
                width=download_result.get("width"),
                height=download_result.get("height"),
                format=download_result.get("format"),
                status="success" if stored_path else "failed",
                hash_value=download_result.get("hash_value"),
                source_platform=source_platform,
            )
            db.add(media_item)

            if db.is_active:
                db.commit()
                db.refresh(media_item)

            return media_item

        except Exception as e:
            logger.error(f"创建媒体记录失败: {e}", exc_info=True)
            if db and db.is_active:
                db.rollback()
            return None

    @staticmethod
    def _create_failed_record(
        article_id: Optional[int],
        original_url: str,
        media_type: str,
        error_msg: str,
        source_platform: Optional[str],
        db: Session,
    ):
        """创建失败的媒体记录"""
        try:
            media_item = MediaItem(
                article_id=article_id,
                original_url=original_url,
                media_type=media_type,
                status="failed",
                error_msg=error_msg[:500],  # 截断过长的错误信息
                source_platform=source_platform,
            )
            db.add(media_item)
            if db.is_active:
                db.commit()

        except Exception as e:
            logger.error(f"创建失败记录异常: {e}")


async def process_content_media(
    content: str,
    article_id: Optional[int] = None,
    source_platform: Optional[str] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    便捷函数：处理内容的媒体文件

    Args:
        content: 文章内容（Markdown或HTML）
        article_id: 关联文章ID
        source_platform: 来源平台
        db: 数据库会话

    Returns:
        处理结果统计
    """
    processor = MediaProcessor()
    try:
        result = await processor.process_article_media(
            article_id=article_id,
            content=content,
            source_platform=source_platform,
            db=db,
        )
        return result
    finally:
        await processor.media_service.close()
