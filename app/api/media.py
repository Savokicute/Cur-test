# coding=utf-8
"""媒体文件访问 API 路由"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import os

from app.models import get_db, MediaItem
from app.services.media_service import MediaService

router = APIRouter(prefix="/media", tags=["media"])

# 初始化媒体服务（单例）
media_service = MediaService()


# MIME 类型映射表
MIME_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.svg': 'image/svg+xml',
    '.mp4': 'video/mp4',
    '.webm': 'video/webp',
    '.mov': 'video/quicktime',
    '.avi': 'video/x-msvideo',
}


def _get_mime_type(file_path: str) -> str:
    """根据文件扩展名获取 MIME 类型"""
    ext = Path(file_path).suffix.lower()
    return MIME_TYPES.get(ext, 'application/octet-stream')


def _validate_path(file_path: str) -> tuple:
    """
    验证并规范化文件路径，防止路径遍历攻击

    Args:
        file_path: 请求的文件路径

    Returns:
        (完整路径, 是否有效)
    """
    try:
        from urllib.parse import unquote

        # 解码 URL 编码（处理 %20 等编码）
        decoded_path = unquote(file_path)

        # 构建完整路径
        storage_root = media_service.storage_root
        full_path = (storage_root / decoded_path).resolve()

        # 验证路径是否在 storage 目录下
        try:
            full_path.relative_to(storage_root.resolve())
            return full_path, True
        except ValueError:
            # 路径遍历攻击检测
            return full_path, False

    except Exception as e:
        print(f"Path validation error: {e}")
        return Path(file_path), False


@router.get("/items")
async def get_media_items(
    article_id: Optional[int] = Query(None, description="文章ID过滤"),
    media_type: Optional[str] = Query(None, description="媒体类型过滤 (image/video)"),
    status: Optional[str] = Query(None, description="状态过滤 (pending/success/failed)"),
    limit: int = Query(default=20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: Session = Depends(get_db)
):
    """获取媒体文件列表"""
    try:
        query = db.query(MediaItem)

        if article_id is not None:
            query = query.filter(MediaItem.article_id == article_id)

        if media_type:
            query = query.filter(MediaItem.media_type == media_type)

        if status:
            query = query.filter(MediaItem.status == status)

        total = query.count()

        items = (
            query
            .order_by(MediaItem.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        # 转换为字典格式
        items_list = []
        for item in items:
            item_dict = {
                "id": item.id,
                "article_id": item.article_id,
                "original_url": item.original_url,
                "stored_path": item.stored_path,
                "media_type": item.media_type,
                "is_video_cover": item.is_video_cover,
                "file_size": item.file_size,
                "file_size_human": _format_size(item.file_size) if item.file_size else "0 B",
                "width": item.width,
                "height": item.height,
                "format": item.format,
                "status": item.status,
                "error_msg": item.error_msg,
                "hash_value": item.hash_value,
                "source_platform": item.source_platform,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            }
            items_list.append(item_dict)

        return {
            "success": True,
            "data": {
                "items": items_list,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
            "message": "获取成功",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取媒体列表失败: {str(e)}")


@router.get("/items/{item_id}")
async def get_media_item(item_id: int, db: Session = Depends(get_db)):
    """获取单个媒体文件详情"""
    try:
        item = db.query(MediaItem).filter(MediaItem.id == item_id).first()

        if not item:
            raise HTTPException(status_code=404, detail="媒体文件不存在")

        item_dict = {
            "id": item.id,
            "article_id": item.article_id,
            "original_url": item.original_url,
            "stored_path": item.stored_path,
            "media_type": item.media_type,
            "is_video_cover": item.is_video_cover,
            "file_size": item.file_size,
            "file_size_human": _format_size(item.file_size) if item.file_size else "0 B",
            "width": item.width,
            "height": item.height,
            "format": item.format,
            "status": item.status,
            "error_msg": item.error_msg,
            "hash_value": item.hash_value,
            "source_platform": item.source_platform,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }

        return {
            "success": True,
            "data": item_dict,
            "message": "获取成功",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取媒体详情失败: {str(e)}")


@router.get("/files/{file_path:path}")
async def serve_media_file(file_path: str):
    """
    提供媒体文件的静态访问服务

    支持图片和视频封面的直接访问
    路径格式: /api/media/files/images/2026/05/28/abc123.jpg

    Args:
        file_path: 相对于存储根目录的文件路径
    """
    try:
        # 验证路径安全性
        full_path, is_valid = _validate_path(file_path)

        if not is_valid:
            raise HTTPException(status_code=400, detail="非法的文件路径")

        # 检查文件是否存在
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        # 检查是否为文件
        if not full_path.is_file():
            raise HTTPException(status_code=400, detail="请求的路径不是文件")

        # 获取文件大小
        file_size = full_path.stat().st_size

        # 限制最大文件大小 (100MB)
        max_size = 100 * 1024 * 1024  # 100MB
        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"文件过大 ({_format_size(file_size)}，最大允许 {_format_size(max_size)})"
            )

        # 获取 MIME 类型
        mime_type = _get_mime_type(str(full_path))

        # 返回文件响应，设置缓存头
        return FileResponse(
            path=str(full_path),
            media_type=mime_type,
            filename=full_path.name,
            headers={
                "Cache-Control": "public, max-age=86400",  # 缓存 24 小时
                "Content-Length": str(file_size),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件服务错误: {str(e)}")


@router.post("/download")
async def trigger_download(request: Dict[str, Any], db: Session = Depends(get_db)):
    """
    手动触发媒体文件下载

    接收请求体:
    {
        "url": string,           // 必填：要下载的URL
        "media_type": "image"|"video",  // 必填：媒体类型
        "source_platform": string,      // 可选：来源平台
        "article_id": int               // 可选：关联的文章ID
    }

    Returns:
        下载结果
    """
    try:
        # 验证必填字段
        url = request.get("url")
        media_type = request.get("media_type")

        if not url:
            raise HTTPException(status_code=400, detail="缺少必填参数: url")

        if not media_type:
            raise HTTPException(status_code=400, detail="缺少必填参数: media_type")

        if media_type not in ["image", "video"]:
            raise HTTPException(
                status_code=400,
                detail=f"无效的 media_type: {media_type}，必须是 image 或 video"
            )

        # 可选参数
        source_platform = request.get("source_platform")
        article_id = request.get("article_id")

        # 创建数据库记录
        media_item = MediaItem(
            article_id=article_id,
            original_url=url,
            media_type=media_type,
            status="pending",
            source_platform=source_platform,
        )
        db.add(media_item)
        db.commit()
        db.refresh(media_item)

        try:
            # 根据类型调用不同的下载方法
            if media_type == "image":
                download_result = await media_service.download_image(
                    url=url,
                    source_platform=source_platform,
                )
            else:  # video
                download_result = await media_service.download_video_cover(
                    url=url,
                    source_platform=source_platform,
                )

            # 更新数据库记录
            if download_result.get("stored_path"):
                media_item.stored_path = download_result["stored_path"]
                media_item.file_size = download_result.get("file_size", 0)
                media_item.width = download_result.get("width")
                media_item.height = download_result.get("height")
                media_item.format = download_result.get("format")
                media_item.hash_value = download_result.get("hash_value")
                media_item.status = "success"

                if media_type == "video" and download_result.get("cover_extracted"):
                    media_item.is_video_cover = True
            else:
                media_item.status = "failed"
                media_item.error_msg = download_result.get("error", "无法下载或提取媒体文件")

            db.commit()
            db.refresh(media_item)

            return {
                "success": True,
                "data": {
                    "id": media_item.id,
                    "original_url": media_item.original_url,
                    "stored_path": media_item.stored_path,
                    "media_type": media_item.media_type,
                    "status": media_item.status,
                    "file_size": media_item.file_size,
                    **download_result,
                },
                "message": "文件下载成功" if media_item.status == "success" else "下载完成但可能存在问题",
            }

        except Exception as download_error:
            # 更新失败状态
            media_item.status = "failed"
            media_item.error_msg = str(download_error)
            db.commit()

            return {
                "success": False,
                "data": {"id": media_item.id},
                "message": f"下载失败: {str(download_error)}",
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发下载失败: {str(e)}")


@router.delete("/items/{item_id}")
async def delete_media_item(item_id: int, db: Session = Depends(get_db)):
    """删除媒体文件记录和对应文件"""
    try:
        item = db.query(MediaItem).filter(MediaItem.id == item_id).first()

        if not item:
            raise HTTPException(status_code=404, detail="媒体文件不存在")

        # 删除物理文件
        if item.stored_path:
            file_path = media_service.storage_root / item.stored_path
            if file_path.exists():
                try:
                    file_path.unlink()
                    print(f"Deleted file: {file_path}")
                except Exception as e:
                    print(f"Failed to delete file: {e}")

        # 删除数据库记录
        db.delete(item)
        db.commit()

        return {
            "success": True,
            "data": {"id": item_id},
            "message": "删除成功",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除媒体文件失败: {str(e)}")


@router.get("/stats")
async def get_storage_stats(db: Session = Depends(get_db)):
    """
    获取存储统计信息

    返回：
    - 总文件数
    - 总大小（字节和人类可读格式）
    - 按类型分组统计
    - 按状态分组统计
    - 存储路径
    """
    try:
        from sqlalchemy import func

        # 总文件数
        total_count = db.query(MediaItem).count()

        # 按类型分组
        type_stats = db.query(
            MediaItem.media_type,
            func.count(MediaItem.id).label('count'),
            func.sum(MediaItem.file_size).label('total_size')
        ).group_by(MediaItem.media_type).all()

        # 按状态分组
        status_stats = db.query(
            MediaItem.status,
            func.count(MediaItem.id).label('count')
        ).group_by(MediaItem.status).all()

        # 计算总大小
        total_size = db.query(func.sum(MediaItem.file_size)).scalar() or 0

        # 格式化结果
        type_breakdown = []
        for stat in type_stats:
            type_breakdown.append({
                "type": stat.media_type,
                "count": stat.count,
                "total_size": stat.total_size or 0,
                "total_size_human": _format_size(stat.total_size or 0),
            })

        status_breakdown = []
        for stat in status_stats:
            status_breakdown.append({
                "status": stat.status,
                "count": stat.count,
            })

        stats = {
            "total_files": total_count,
            "total_size": total_size,
            "total_size_human": _format_size(total_size),
            "by_type": type_breakdown,
            "by_status": status_breakdown,
            "storage_path": str(media_service.storage_root),
        }

        return {
            "success": True,
            "data": stats,
            "message": "获取统计成功",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取存储统计失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "storage_path": str(media_service.storage_root),
            "storage_exists": media_service.storage_root.exists(),
        },
        "message": "媒体服务运行正常",
    }


def _format_size(size_bytes: int) -> str:
    """格式化文件大小为人类可读格式"""
    if size_bytes == 0:
        return "0 B"

    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"
