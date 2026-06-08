# 媒体文件 API 使用示例

## 概述

媒体文件 API 提供了完整的媒体管理功能，包括：
- 媒体文件列表查询
- 单个媒体详情获取
- 静态文件访问服务
- 手动触发下载
- 文件删除
- 存储统计信息

## API 端点列表

基础路径: `/api/media`

### 1. 获取媒体文件列表
```
GET /api/media/items
```

**Query 参数:**
- `article_id` (可选): 文章ID过滤
- `media_type` (可选): 媒体类型过滤 (`image` 或 `video`)
- `status` (可选): 状态过滤 (`pending`, `success`, `failed`)
- `limit` (可选): 返回数量限制 (1-100, 默认 20)
- `offset` (可选): 偏移量 (默认 0)

**响应示例:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "article_id": 123,
        "original_url": "https://example.com/image.jpg",
        "stored_path": "images/2026/05/29/abc123.jpg",
        "media_type": "image",
        "file_size": 102400,
        "file_size_human": "100.00 KB",
        "width": 1920,
        "height": 1080,
        "format": "jpg",
        "status": "success",
        "hash_value": "sha256_hash...",
        "source_platform": "wechat",
        "created_at": "2026-05-29T10:30:00",
        "updated_at": "2026-05-29T10:30:00"
      }
    ],
    "total": 1,
    "limit": 20,
    "offset": 0
  },
  "message": "获取成功"
}
```

### 2. 获取单个媒体文件详情
```
GET /api/media/items/{item_id}
```

**响应示例:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "article_id": 123,
    "original_url": "https://example.com/image.jpg",
    "stored_path": "images/2026/05/29/abc123.jpg",
    "media_type": "image",
    "file_size": 102400,
    "status": "success"
  },
  "message": "获取成功"
}
```

### 3. 访问静态媒体文件（核心接口）
```
GET /api/media/files/{file_path:path}
```

**说明:**
- 这是核心的静态文件访问接口
- 支持图片和视频封面的直接访问
- 路径是相对于 storage 目录的相对路径
- 自动设置正确的 Content-Type 和缓存头

**示例请求:**
```
GET /api/media/files/images/2026/05/29/abc123.jpg
```

**响应:**
- 成功: 返回文件内容（二进制），Content-Type 根据扩展名自动设置
- 缓存头: `Cache-Control: public, max-age=86400` (24小时)
- 错误:
  - 400: 非法路径、非文件、文件过大
  - 404: 文件不存在

**安全特性:**
- 路径遍历防护：阻止 `../../../etc/passwd` 等攻击
- URL 编码解码：正确处理 `%20` 等编码
- 文件大小限制：最大 100MB
- 只允许访问 storage 目录下的文件

### 4. 手动触发媒体下载
```
POST /api/media/download
```

**请求体:**
```json
{
  "url": "https://example.com/image.jpg",
  "media_type": "image",
  "source_platform": "wechat",
  "article_id": 123
}
```

**必填字段:**
- `url`: 要下载的媒体 URL
- `media_type`: 媒体类型 (`"image"` 或 `"video"`)

**可选字段:**
- `source_platform`: 来源平台标识
- `article_id`: 关联的文章ID

**响应示例:**
```json
{
  "success": true,
  "data": {
    "id": 2,
    "original_url": "https://example.com/image.jpg",
    "stored_path": "images/2026/05/29/def456.png",
    "media_type": "image",
    "status": "success",
    "file_size": 51200,
    "width": 800,
    "height": 600,
    "format": "png",
    "hash_value": "sha256_hash..."
  },
  "message": "文件下载成功"
}
```

**特性:**
- 图片自动压缩和优化
- 自动计算 SHA256 哈希值
- 按日期组织存储目录
- 视频封面自动提取（支持 YouTube、B站等平台）
- 完整的错误处理和状态跟踪

### 5. 删除媒体文件
```
DELETE /api/media/items/{item_id}
```

**响应示例:**
```json
{
  "success": true,
  "data": {"id": 1},
  "message": "删除成功"
}
```

**说明:**
- 同时删除数据库记录和物理文件
- 如果物理文件删除失败，仍会删除数据库记录
- 文件不存在时返回 404

### 6. 获取存储统计信息
```
GET /api/media/stats
```

**响应示例:**
```json
{
  "success": true,
  "data": {
    "total_files": 150,
    "total_size": 52428800,
    "total_size_human": "50.00 MB",
    "by_type": [
      {
        "type": "image",
        "count": 120,
        "total_size": 31457280,
        "total_size_human": "30.00 MB"
      },
      {
        "type": "video",
        "count": 30,
        "total_size": 20971520,
        "total_size_human": "20.00 MB"
      }
    ],
    "by_status": [
      {"status": "success", "count": 145},
      {"status": "pending", "count": 3},
      {"status": "failed", "count": 2}
    ],
    "storage_path": "D:\\project\\storage"
  },
  "message": "获取统计成功"
}
```

### 7. 健康检查
```
GET /api/media/health
```

**响应示例:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "storage_path": "D:\\project\\storage",
    "storage_exists": true
  },
  "message": "媒体服务运行正常"
}
```

## 使用场景示例

### 场景 1: 在前端显示文章图片

```javascript
// 假设从 API 获取到文章数据，包含 media_items
const article = await fetch('/api/articles/123').then(r => r.json());

// 渲染图片列表
article.data.media_items.forEach(item => {
  if (item.status === 'success' && item.stored_path) {
    // 使用静态文件访问接口
    const imageUrl = `/api/media/files/${item.stored_path}`;
    console.log('Image URL:', imageUrl);
    // <img src={imageUrl} alt="Article image" />
  }
});
```

### 场景 2: 手动下载并关联图片

```bash
# 下载图片并关联到文章 ID 456
curl -X POST http://localhost:8000/api/media/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/photo.jpg",
    "media_type": "image",
    "source_platform": "manual",
    "article_id": 456
  }'
```

### 场景 3: 获取存储使用情况

```bash
# 查看存储统计
curl http://localhost:8000/api/media/stats
```

### 圆景 4: 批量查询某篇文章的所有图片

```bash
# 查询文章 ID 789 的所有图片
curl "http://localhost:8000/api/media/items?article_id=789&media_type=image&status=success"
```

## 安全注意事项

1. **路径安全**: 所有文件访问都经过路径验证，防止目录遍历攻击
2. **大小限制**: 单个文件最大 100MB，防止资源耗尽
3. **缓存策略**: 静态文件设置 24 小时缓存，减少服务器负载
4. **MIME 类型**: 正确设置 Content-Type，防止 MIME 嗅探攻击
5. **错误处理**: 统一的错误响应格式，不泄露敏感信息

## 存储结构

媒体文件按以下结构存储：

```
storage/
├── images/
│   └── {YYYY}/
│       └── {MM}/
│           └── {DD}/
│               ├── {sha256_hash}.jpg
│               ├── {sha256_hash}.png
│               └── ...
└── videos/
    └── {YYYY}/
        └── {MM}/
            └── {DD}/
                ├── {sha256_hash}_cover.jpg
                └── ...
```

## 技术特性

- **图片处理**: 自动压缩、格式转换、尺寸优化
- **哈希去重**: 使用 SHA256 哈希值避免重复存储
- **异步下载**: 使用 httpx 异步客户端，支持高并发
- **错误恢复**: 完整的状态跟踪和错误日志
- **平台适配**: 支持多种视频平台的封面提取
