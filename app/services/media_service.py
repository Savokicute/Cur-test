"""
媒体文件存储服务 - 图片和视频封面下载、压缩、存储

PRD §13: 媒体文件管理
- 图片: /storage/images/{year}/{month}/{day}/{hash}.{ext}
- 视频封面: /storage/videos/{year}/{month}/{day}/{hash}_cover.{ext}
- 使用 SHA256 哈希值命名避免冲突
"""

import os
import hashlib
import re
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse, unquote

import httpx
from PIL import Image


class MediaServiceError(Exception):
    """媒体服务异常基类"""
    pass


class DownloadError(MediaServiceError):
    """下载异常"""
    pass


class ImageProcessingError(MediaServiceError):
    """图片处理异常"""
    pass


class InvalidURLError(MediaServiceError):
    """无效URL异常"""
    pass


class MediaService:
    """
    媒体文件存储服务

    负责图片和视频封面的下载、压缩、哈希计算与本地存储。
    所有公开方法均为异步，内部辅助方法为同步。
    """

    # 支持的图片格式及 MIME 映射
    SUPPORTED_IMAGE_FORMATS: Dict[str, str] = {
        "jpg": "JPEG",
        "jpeg": "JPEG",
        "png": "PNG",
        "gif": "GIF",
        "webp": "WEBP",
    }

    # 最大文件大小: 10MB
    MAX_IMAGE_SIZE: int = 10 * 1024 * 1024

    # 最小尺寸阈值（过滤图标/广告图）
    MIN_IMAGE_DIMENSION: int = 50

    # 默认最大宽度（压缩目标）
    DEFAULT_MAX_WIDTH: int = 1920

    # 下载超时（秒）
    DOWNLOAD_TIMEOUT: float = 30.0

    # 允许的图片域名白名单（可选，留空则不限制）
    ALLOWED_DOMAINS: Optional[set] = None

    # 常见视频平台域名（用于识别视频URL）
    VIDEO_PLATFORM_DOMAINS = {
        "youtube.com", "youtu.be", "vimeo.com", "bilibili.com", "b23.tv",
        "douyin.com", "tiktok.com", "kuaishou.com", "iqiyi.com",
        "youku.com", "qq.com", "weibo.com", "mp.weixin.qq.com",
    }

    def __init__(self, storage_root: Optional[str] = None):
        """
        初始化媒体服务

        Args:
            storage_root: 存储根目录路径。
                         默认为项目根目录下的 `storage/` 文件夹。
        """
        if storage_root is None:
            # 默认: 项目根目录 / storage
            project_root = Path(__file__).resolve().parent.parent.parent
            self.storage_root = project_root / "storage"
        else:
            self.storage_root = Path(storage_root).resolve()

        # 确保存储根目录存在
        self.storage_root.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        (self.storage_root / "images").mkdir(exist_ok=True)
        (self.storage_root / "videos").mkdir(exist_ok=True)

        # 异步 HTTP 客户端（延迟初始化）
        self._client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------ #
    #  公开异步方法
    # ------------------------------------------------------------------ #

    async def download_image(
        self,
        url: str,
        source_platform: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        下载并存储图片

        流程: URL验证 -> 下载 -> 尺寸检查 -> 计算哈希 -> 压缩 -> 存储 -> 返回元信息

        Args:
            url: 图片 URL
            source_platform: 来源平台标识（用于日志）

        Returns:
            dict: {
                stored_path: 相对于 storage_root 的存储路径,
                file_size:   文件大小（字节）,
                width:       图片宽度（像素）,
                height:      图片高度（像素）,
                format:      图片格式（jpg/png/gif/webp）,
                hash_value:  SHA256 哈希值,
            }

        Raises:
            DownloadError: 下载失败或校验失败
            ImageProcessingError: 图片处理失败
            InvalidURLError: 无效的 URL
        """
        url = url.strip()

        # 1. URL 验证
        if not self._is_valid_image_url(url):
            raise InvalidURLError(f"无效的图片URL: {url}")

        client = await self._get_client()

        try:
            # 2. 下载图片数据
            response = await client.get(
                url,
                follow_redirects=True,
                timeout=self.DOWNLOAD_TIMEOUT,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                },
            )
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
            data = response.content

            # 3. 大小检查
            if len(data) > self.MAX_IMAGE_SIZE:
                raise DownloadError(
                    f"图片过大: {len(data)} 字节 > {self.MAX_IMAGE_SIZE} 字节限制"
                )

            if len(data) == 0:
                raise DownloadError("下载内容为空")

            # 4. 从 Content-Type 或 URL 推断格式
            ext = self._detect_format_from_url_or_content(url, content_type)
            if ext is None or ext not in self.SUPPORTED_IMAGE_FORMATS:
                # 尝试用 Pillow 检测
                ext = self._detect_format_from_bytes(data)
                if ext is None:
                    raise ImageProcessingError(f"无法识别图片格式: url={url}, content_type={content_type}")

            # 5. 临时保存用于 Pillow 处理
            temp_dir = self.storage_root / "_temp"
            temp_dir.mkdir(exist_ok=True)
            temp_path = temp_dir / f"temp_{os.urandom(8).hex()}.{ext}"

            try:
                temp_path.write_bytes(data)

                # 6. 打开图片并检查尺寸
                with Image.open(temp_path) as img:
                    width, height = img.size

                    # 过滤过小的图标/广告图
                    if width < self.MIN_IMAGE_DIMENSION or height < self.MIN_IMAGE_DIMENSION:
                        raise ImageProcessingError(
                            f"图片尺寸过小 ({width}x{height})，可能是图标或广告图"
                        )

                    # 确认实际格式
                    actual_format = img.format
                    if actual_format and actual_format.lower() in ["jpeg", "jpg"]:
                        ext = "jpg"
                    elif actual_format and actual_format.lower() in self.SUPPORTED_IMAGE_FORMATS:
                        ext = actual_format.lower()
                        if ext == "jpeg":
                            ext = "jpg"

                # 7. 计算 SHA256 哈希
                hash_value = self._compute_hash(data)

                # 8. 构建最终存储路径
                now = datetime.now(timezone.utc)
                stored_path = self._build_storage_path(
                    media_type="image",
                    hash_value=hash_value,
                    ext=ext,
                    dt=now,
                    is_cover=False,
                )

                output_full_path = self.storage_root / stored_path
                output_full_path.parent.mkdir(parents=True, exist_ok=True)

                # 9. 压缩并保存
                final_width, final_height, final_size = self._compress_image(
                    input_path=str(temp_path),
                    output_path=str(output_full_path),
                    max_width=self.DEFAULT_MAX_WIDTH,
                )

                return {
                    "stored_path": stored_path,
                    "file_size": final_size,
                    "width": final_width,
                    "height": final_height,
                    "format": ext,
                    "hash_value": hash_value,
                    "source_url": url,
                    "source_platform": source_platform,
                }

            finally:
                # 清理临时文件
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)

        except httpx.HTTPStatusError as e:
            raise DownloadError(f"HTTP错误 {e.response.status_code}: {url}") from e
        except httpx.RequestError as e:
            raise DownloadError(f"请求失败: {e}") from e
        except ImageProcessingError:
            raise
        except Exception as e:
            if isinstance(e, (DownloadError, InvalidURLError)):
                raise
            raise DownloadError(f"下载处理异常: {e}") from e

    async def download_video_cover(
        self,
        url: str,
        source_platform: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        下载视频封面图

        不下载视频本体，仅尝试获取第一帧作为封面。
        如果无法提取视频帧，则返回原始链接信息和占位状态。

        Args:
            url: 视频 URL
            source_platform: 来源平台标识

        Returns:
            dict: 与 download_image 格式一致，
                  若无法提取封面则包含 video_url 和 cover_extracted=False
        """
        url = url.strip()

        result: Dict[str, Any] = {
            "stored_path": None,
            "file_size": 0,
            "width": 0,
            "height": 0,
            "format": None,
            "hash_value": None,
            "video_url": url,
            "source_platform": source_platform,
            "cover_extracted": False,
        }

        # 尝试从常见模式提取封面 URL
        cover_url = await self._try_extract_cover_url(url)

        if cover_url:
            try:
                cover_result = await self.download_image(
                    url=cover_url,
                    source_platform=source_platform,
                )

                # 将结果标记为视频封面
                now = datetime.now(timezone.utc)
                hash_value = cover_result["hash_value"]
                ext = cover_result["format"]

                # 重新构建视频封面路径
                video_cover_path = self._build_storage_path(
                    media_type="video",
                    hash_value=hash_value,
                    ext=ext,
                    dt=now,
                    is_cover=True,
                )

                video_cover_full = self.storage_root / video_cover_path
                video_cover_full.parent.mkdir(parents=True, exist_ok=True)

                # 移动文件到视频封面目录
                old_path = self.storage_root / cover_result["stored_path"]
                if old_path.exists():
                    old_path.rename(video_cover_full)

                result.update({
                    "stored_path": video_cover_path,
                    "file_size": cover_result["file_size"],
                    "width": cover_result["width"],
                    "height": cover_result["height"],
                    "format": cover_result["format"],
                    "hash_value": hash_value,
                    "cover_extracted": True,
                })

            except (DownloadError, ImageProcessingError, InvalidURLError) as e:
                # 封面下载失败不影响主流程，记录后继续
                result["error"] = str(e)

        return result

    async def close(self):
        """关闭 HTTP 客户端连接"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # ------------------------------------------------------------------ #
    #  公开同步方法
    # ------------------------------------------------------------------ #

    def _compute_hash(self, data: bytes) -> str:
        """
        计算数据的 SHA256 哈希值

        Args:
            data: 原始字节数据

        Returns:
            64字符的十六进制哈希字符串
        """
        return hashlib.sha256(data).hexdigest()

    def _compress_image(
        self,
        input_path: str,
        output_path: str,
        max_width: int = DEFAULT_MAX_WIDTH,
    ) -> Tuple[int, int, int]:
        """
        压缩图片

        如果原图宽度已 <= max_width，则直接复制。
        否则按比例缩放并使用优化参数保存。

        Args:
            input_path: 输入图片路径
            output_path: 输出图片路径
            max_width: 最大宽度（像素）

        Returns:
            tuple: (width, height, file_size_bytes)

        Raises:
            ImageProcessingError: 压缩过程中发生错误
        """
        try:
            with Image.open(input_path) as img:
                # 转换 RGBA/其他模式以兼容 JPEG
                original_mode = img.mode
                original_width, original_height = img.size

                if original_width <= max_width:
                    # 无需缩放，直接复制
                    img.save(output_path, quality=95, optimize=True)
                else:
                    # 按比例缩放
                    ratio = max_width / original_width
                    new_height = int(original_height * ratio)
                    resized_img = img.resize(
                        (max_width, new_height),
                        Image.Resampling.LANCZOS,
                    )

                    # 根据输出格式决定处理方式
                    ext = Path(output_path).suffix.lstrip(".").lower()
                    pil_format = self.SUPPORTED_IMAGE_FORMATS.get(ext, "PNG")

                    if pil_format == "JPEG":
                        # JPEG 不支持透明通道
                        if resized_img.mode in ("RGBA", "LA", "P"):
                            background = Image.new("RGB", resized_img.size, (255, 255, 255))
                            if resized_img.mode == "P":
                                resized_img = resized_img.convert("RGBA")
                            background.paste(resized_img, mask=resized_img.split()[-1])
                            resized_img = background
                        elif resized_img.mode != "RGB":
                            resized_img = resized_img.convert("RGB")

                        resized_img.save(
                            output_path,
                            format=pil_format,
                            quality=85,
                            optimize=True,
                            progressive=True,
                        )
                    elif pil_format == "GIF":
                        resized_img.save(output_path, format=pil_format)
                    else:
                        resized_img.save(output_path, format=pil_format, optimize=True)

                final_width = min(original_width, max_width)
                final_height = int(original_height * (final_width / original_width)) if original_width > max_width else original_height
                file_size = os.path.getsize(output_path)

                return final_width, final_height, file_size

        except Exception as e:
            raise ImageProcessingError(f"图片压缩失败: {e}") from e

    def _is_valid_image_url(self, url: str) -> bool:
        """
        验证 URL 是否为有效图片链接

        检查项：
        - URL 格式合法性
        - 文件扩展名是否在支持列表中
        - （可选）域名是否在白名单中

        Args:
            url: 待验证的 URL 字符串

        Returns:
            bool: 是否为有效的图片 URL
        """
        if not url or not isinstance(url, str):
            return False

        url = url.strip()

        # 基本 URL 格式
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            if not parsed.netloc:
                return False
        except Exception:
            return False

        # 扩展名检查（从路径推断）
        path = unquote(parsed.path).lower()
        ext = Path(path).suffix.lstrip(".")
        if ext and ext not in self.SUPPORTED_IMAGE_FORMATS:
            # 如果有明确的不支持扩展名，拒绝
            blocked_exts = {"html", "htm", "php", "asp", "aspx", "js", "css", "json", "xml"}
            if ext in blocked_exts:
                return False
            # 其他未知扩展名不阻止（可能没有扩展名的图片API）

        # 域名白名单检查
        if self.ALLOWED_DOMAINS:
            domain = parsed.netloc.lower().split(":")[0]
            if domain not in self.ALLOWED_DOMAINS:
                return False

        return True

    def get_storage_path(
        self,
        url: str,
        media_type: str = "image",
        is_cover: bool = False,
    ) -> str:
        """
        根据 URL 预生成存储路径（不实际下载）

        用于提前规划存储位置，实际哈希需在下载后才能确定。

        Args:
            url: 媒体 URL
            media_type: "image" 或 "video"
            is_cover: 是否为视频封面

        Returns:
            str: 预期的存储相对路径（hash 部分为占位符）
        """
        now = datetime.now(timezone.utc)
        placeholder_hash = "pending"
        ext = self._detect_extension_from_url(url) or "jpg"

        return self._build_storage_path(
            media_type=media_type,
            hash_value=placeholder_hash,
            ext=ext,
            dt=now,
            is_cover=is_cover,
        )

    def get_local_url(self, stored_path: str) -> str:
        """
        将存储路径转换为可通过 API 访问的 URL

        Args:
            stored_path: 相对于 storage_root 的存储路径

        Returns:
            str: API 可访问的 URL，如 `/api/media/files/images/2026/05/29/abc123.jpg`
        """
        # 规范化路径分隔符
        normalized = stored_path.replace("\\", "/").lstrip("/")
        return f"/api/media/files/{normalized}"

    # ------------------------------------------------------------------ #
    #  内部辅助方法
    # ------------------------------------------------------------------ #

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建异步 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                follow_redirects=True,
                timeout=httpx.Timeout(self.DOWNLOAD_TIMEOUT, connect=10.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
            )
        return self._client

    def _build_storage_path(
        self,
        media_type: str,
        hash_value: str,
        ext: str,
        dt: datetime,
        is_cover: bool = False,
    ) -> str:
        """
        构建标准化的存储路径

        规则:
          image: images/{YYYY}/{MM}/{DD}/{hash}.{ext}
          video cover: videos/{YYYY}/{MM}/{DD}/{hash}_cover.{ext}

        Args:
            media_type: "image" 或 "video"
            hash_value: SHA256 哈希值
            ext: 文件扩展名（不含点）
            dt: 时间戳（用于日期目录）
            is_cover: 是否为视频封面

        Returns:
            str: 相对于 storage_root 的路径
        """
        folder = "images" if media_type == "image" else "videos"
        date_part = dt.strftime("%Y/%m/%d")

        if is_cover:
            filename = f"{hash_value}_cover.{ext}"
        else:
            filename = f"{hash_value}.{ext}"

        return f"{folder}/{date_part}/{filename}"

    def _detect_format_from_url_or_content(
        self,
        url: str,
        content_type: str,
    ) -> Optional[str]:
        """从 URL 或 Content-Type 推断图片格式"""

        # 先尝试 URL 扩展名
        url_ext = self._detect_extension_from_url(url)
        if url_ext and url_ext in self.SUPPORTED_IMAGE_FORMATS:
            return url_ext

        # 再尝试 Content-Type
        ct_map = {
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
        }
        return ct_map.get(content_type)

    def _detect_extension_from_url(self, url: str) -> Optional[str]:
        """从 URL 路径中提取文件扩展名"""
        try:
            path = urlparse(url).path
            ext = Path(path).suffix.lstrip(".").lower()
            if ext in self.SUPPORTED_IMAGE_FORMATS:
                return ext
        except Exception:
            pass
        return None

    def _detect_format_from_bytes(self, data: bytes) -> Optional[str]:
        """通过字节头（magic number）检测图片格式"""
        if len(data) < 8:
            return None

        # PNG: 89 50 4E 47
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return "png"

        # JPEG: FF D8 FF
        if data[:3] == b"\xff\xd8\xff":
            return "jpg"

        # GIF: GIF8
        if data[:4] in (b"GIF8", b"GIF87", b"GIF89"):
            return "gif"

        # WebP: RIFF .... WEBP
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "webp"

        return None

    async def _try_extract_cover_url(self, video_url: str) -> Optional[str]:
        """
        尝试从视频 URL 提取封面图 URL

        策略:
        - YouTube: 使用 ytimg.com 的默认封面
        - Bilibili: 使用 B站封面 API
        - 微信公众号: 从页面 HTML 中提取 og:image
        - 通用: 尝试追加常见封面路径模式

        Args:
            video_url: 视频 URL

        Returns:
            Optional[str]: 封面图 URL，若无法推断则返回 None
        """
        try:
            parsed = urlparse(video_url)
            domain = parsed.netloc.lower().replace("www.", "")

            # YouTube
            if "youtube.com" in domain or "youtu.be" in domain:
                video_id = self._extract_youtube_id(video_url)
                if video_id:
                    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

            # Bilibili
            if "bilibili.com" in domain or "b23.tv" in domain:
                bv_id = self._extract_bilibili_bvid(video_url)
                if bv_id:
                    return f"https://api.bilibili.com/x/web-interface/view?bvid={bv_id}"

            # 抖音
            if "douyin.com" in domain:
                # 抖音视频通常需要解析页面获取封面
                return None

            # 微信公众号文章中的视频
            if "mp.weixin.qq.com" in domain:
                return await self._fetch_wechat_og_image(video_url)

            # 通用策略：尝试常见的封面路径
            common_patterns = [
                "/cover.jpg", "/poster.jpg", "/snapshot.jpg",
                "?cover", "?poster",
            ]
            for pattern in common_patterns:
                candidate = video_url.rsplit("/", 1)[0] + pattern
                if self._is_valid_image_url(candidate):
                    return candidate

        except Exception:
            pass

        return None

    @staticmethod
    def _extract_youtube_id(url: str) -> Optional[str]:
        """从 YouTube URL 提取视频 ID"""
        patterns = [
            r"(?:v=|v\/|embed\/|youtu\.be\/)([a-zA-Z0-9_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _extract_bilibili_bvid(url: str) -> Optional[str]:
        """从 Bilibili URL 提取 BV 号"""
        match = re.search(r"(BV[a-zA-Z0-9]+)", url)
        return match.group(1) if match else None

    async def _fetch_wechat_og_image(self, url: str) -> Optional[str]:
        """
        从微信公众号页面提取 og:image

        Args:
            url: 微信公众号文章/视频 URL

        Returns:
            Optional[str]: og:image URL
        """
        client = await self._get_client()
        try:
            resp = await client.get(
                url,
                follow_redirects=True,
                timeout=self.DOWNLOAD_TIMEOUT,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            resp.raise_for_status()

            html = resp.text
            match = re.search(
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                html,
                re.IGNORECASE,
            )
            if match:
                og_image = match.group(1).replace("&amp;", "&")
                if self._is_valid_image_url(og_image):
                    return og_image

        except Exception:
            pass

        return None
