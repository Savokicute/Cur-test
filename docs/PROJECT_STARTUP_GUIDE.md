# 热点发现平台 - 项目启动文档

> **版本**: v1.0 | **更新日期**: 2026-06-02 | **适用环境**: Windows 10/11, macOS, Linux

---

## 📋 目录

1. [快速开始](#-快速开始)
2. [环境要求](#-环境要求)
3. [安装与初始化](#-安装与初始化)
4. [启动方式](#-启动方式)
5. [功能模块说明](#-功能模块说明)
6. [开发工作流](#-开发工作流)
7. [常见问题排查](#-常见问题排查)
8. [架构概览](#-架构概览)

---

## 🚀 快速开始（3步启动）

```bash
# 1️⃣ 进入项目目录
cd d:\chao-TrendRadar\Cur-test - v3

# 2️⃣ 安装依赖（首次）
uv sync --group dev

# 3️⃣ 一键启动全部服务
uv run python scripts/start_platform.py

# 另开终端，启动 Web 后端
uv run uvicorn app.main:app --reload --port 8000

# 再开终端，启动前端
cd web/frontend && npm run dev
```

访问地址：
- 前端界面: http://localhost:5173
- API 文档: http://localhost:8000/docs

---

## 💻 环境要求

### 必需软件

| 软件 | 版本要求 | 用途 |
|------|----------|------|
| **Python** | >= 3.12 | 后端运行时 |
| **Node.js** | >= 20 | 前端构建工具 |
| **uv** | 最新版 | Python 包管理器 |
| **npm** | >= 10 | Node 包管理器 |

### 可选软件

| 软件 | 用途 | 安装命令 |
|------|------|----------|
| **Playwright Chromium** | 浏览器爬虫 | `uv run playwright install chromium` |
| **Git** | 版本控制 | https://git-scm.com/ |

### 验证环境

```bash
# 检查 Python 版本
python --version  # 应显示 Python 3.12.x

# 检查 Node 版本
node --version    # 应显示 v20.x.x

# 检查 uv 是否安装
uv --version       # 应显示 uv x.y.z

# 运行环境自检脚本
uv run python scripts/verify_environment.py
# 退出码 0 表示环境正常
```

---

## 🔧 安装与初始化

### 首次安装（全新环境）

```bash
# 1. 克隆项目（如果从 Git 仓库）
git clone <repository-url>
cd Cur-test - v3

# 2. 安装 Python 依赖（使用 uv）
uv sync --group dev

# 3. 安装 Playwright 浏览器（用于文章爬取）
uv run playwright install chromium

# 4. 安装前端依赖
cd web/frontend
npm ci
cd ../..

# 5. 验证安装成功
uv run python scripts/verify_environment.py
```

### 依赖说明

#### Python 依赖（pyproject.toml）

```toml
核心依赖:
- trendradar        # 热榜采集引擎
- crawl4ai          # AI 浏览器爬虫
- fastapi>=0.115.0   # Web API 框架
- uvicorn>=0.32.0    # ASGI 服务器
- sqlalchemy>=2.0.0   # ORM 数据库
- httpx>=0.27.0      # 异步 HTTP 客户端
- Pillow             # 图片处理

开发依赖:
- pytest>=8.0        # 单元测试
- pytest-asyncio     # 异步测试支持
```

#### 前端依赖（package.json）

```json
核心框架:
- react ^18          # UI 框架
- react-dom ^18      # DOM 渲染
- antd ^5            # UI 组件库
- @ant-design/icons ^5 # 图标库
- lucide-react       # 轻量图标
- react-router-dom ^6 # 路由管理
- dayjs              # 日期处理
- react-markdown     # Markdown 渲染
- remark-gfm         # GFM 语法支持

构建工具:
- vite ^5            # 构建工具
- @vitejs/plugin-react  # React 插件
```

---

## ▶️ 启动方式

### 方式一：一键启动（推荐开发使用）

**启动采集层 + 微信公众号RSS**

```bash
# 完整启动（daemon + we-mp-rss）
uv run python scripts/start_platform.py

# 仅启动采集层（不启动微信公众号）
uv run python scripts/start_platform.py --no-wemp

# 单轮测试（运行一次后退出）
uv run python scripts/start_platform.py --once

# 仅启动微信公众号（不启动采集层）
uv run python scripts/start_platform.py --no-daemon
```

**输出示例**：

```
[start] python -m hot_content_bridge.cli daemon  (cwd=d:\chao-TrendRadar\Cur-test - v3)
[start] python main.py -job True  (cwd=d:\chao-TrendRadar\Cur-test - v3\we-mp-rss)
[start] Services running. Press Ctrl+C to stop all.
2026-06-02 10:00:00 [INFO] Pipeline cycle started...
2026-06-02 10:00:01 [INFO] Hot list: OK (fetched 12 platforms)
2026-06-02 10:00:05 [INFO] Article crawl: crawled=15, failed=2
```

### 方式二：分步启动（生产环境推荐）

#### Step 1: 启动采集层（热榜 + 文章爬取）

```bash
# 方式 A: 使用 CLI
uv run hot-content-bridge daemon

# 方式 B: 直接运行模块
uv run python -m hot_content_bridge.cli daemon

# 方式 C: 单轮测试
uv run hot-content-bridge run-pipeline --quick-hotlist
```

**配置文件位置**: `hot_content_bridge/config.yaml`

```yaml
pipeline_daemon:
  hotlist_interval_minutes: 30    # 热榜采集间隔
  article_crawl_enabled: true     # 是否启用正文爬取
  full_trendradar_sync: false     # 完整同步（建议关闭）
```

#### Step 2: 启动微信公众号 RSS（可选）

```bash
cd we-mp-rss
uv run python main.py -job True
```

**端口**: 默认 8001

#### Step 3: 启动 Web 后端 API

```bash
# 开发模式（热重载）
uv run uvicorn app.main:app --reload --port 8000

# 生产模式
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**API 文档**: http://localhost:8000/docs （Swagger UI）

**主要 API 端点**:

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/hotspots` | GET | 获取热榜列表 |
| `/api/hotspots/dates` | GET | 获取可用日期 |
| `/api/articles/{id}` | GET | 获取文章详情 |
| `/api/articles/{id}/refetch` | POST | 重新抓取文章 |
| `/api/wechat/feeds` | GET | 公众号列表 |
| `/api/wechat/articles` | GET | 公众号文章 |
| `/api/media/items` | GET | 媒体文件列表 |
| `/api/media/files/{path}` | GET | 访问媒体文件 |
| `/api/sources/*` | CRUD | 采集源配置 |
| `/api/config/*` | CRUD | 系统配置 |
| `/api/keywords/*` | CRUD | 关键词配置 |

#### Step 4: 启动前端开发服务器

```bash
cd web/frontend

# 开发模式
npm run dev

# 生产构建
npm run build

# 预览生产构建
npm run preview
```

**访问地址**: http://localhost:5173

### 方式三：Windows PowerShell 一键脚本

创建 `start-dev.ps1`:

```powershell
# start-dev.ps1 - 开发环境一键启动

Write-Host "🚀 启动热点发现平台开发环境..." -ForegroundColor Cyan

# 终端 1: 采集层
Start-Process powershell -ArgumentList "-NoExit", "-Command", "uv run python scripts/start_platform.py"

# 等待 3 秒让采集层先启动
Start-Sleep -Seconds 3

# 终端 2: Web 后端
Start-Process powershell -ArgumentList "-NoExit", "-Command", "uv run uvicorn app.main:app --reload --port 8000"

# 终端 3: 前端
Set-Location web/frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev"
Set-Location ..

Write-Host ""
Write-Host "✅ 所有服务已启动！" -ForegroundColor Green
Write-Host "   前端: http://localhost:5173" -ForegroundColor White
Write-Host "   API:  http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "按 Ctrl+C 停止对应终端的服务" -ForegroundColor Yellow
```

**使用**:

```powershell
.\start-dev.ps1
```

---

## 📦 功能模块说明

### 已完成的核心功能

#### 1️⃣ 热榜总览页 (`/`)
- ✅ 多平台热榜聚合展示（百度、微博、知乎、抖音等 12+ 平台）
- ✅ 卡片/列表视图切换（快捷键 `V`）
- ✅ 趋势箭头展示（上升🔺、下降🔻、持平➖、新增🆕）
- ✅ AI 相关性分数可视化
- ✅ 关键词分组筛选
- ✅ 实时搜索（防抖 300ms，快捷键 `/`）
- ✅ 一键复制（标题/URL/Markdown，悬停序号）
- ✅ 收藏功能（本地持久化）
- ✅ 日期范围选择
- ✅ 分页加载（每页 20 条）

#### 2️⃣ 内容详情页 (`/content/:type/:id`)
- ✅ Markdown 内容渲染
- ✅ 图片点击放大预览（懒加载 + 骨架屏）
- ✅ 视频封面展示 + 播放按钮
- ✅ 重新抓取按钮
- ✅ 查看原文链接
- ✅ 收藏 + 标签备注

#### 3️⃣ 素材中心页 (`/materials`)
- ✅ 收藏内容列表
- ✅ 多维度筛选（类型、来源、时间、标签）
- ✅ 编辑标签和备注
- ✅ 取消收藏

#### 4️⃣ 采集源配置页 (`/sources`)
- ✅ 热榜源管理（启用/禁用/权重）
- ✅ 网站/RSS 源管理
- ✅ 微信公众号管理
- ✅ 浏览器配置文件管理
- ✅ 手动触发抓取

#### 5️⃣ 关键词配置页 (`/keywords`)
- ✅ 分组编辑器（语法高亮）
- ✅ 实时测试匹配结果
- ✅ 语法帮助文档

#### 6️⃣ 微信公众号页 (`/wechat`)
- ✅ 公众号列表展示
- ✅ 文章列表浏览
- ✅ 手动触发抓取

#### 7️⃣ AI 模型配置页 (`/ai-config`)
- ✅ 模型参数配置
- ✅ 备用模型设置
- ✅ 连接测试功能

#### 8️⃣ 推送渠道配置页 (`/notify-storage`)
- ✅ 多渠道通知配置
- ✅ 存储策略设置

#### 9️⃣ 内容策略页 (`/content-policy`)
- ✅ 报告模式配置
- ✅ 筛选策略管理
- ✅ 推送内容控制

#### 🔟 媒体文件系统
- ✅ 图片下载/压缩/存储
- ✅ 视频封面提取（YouTube、Bilibili、微信公众号）
- ✅ SHA256 哈希去重
- ✅ 静态文件服务（路径安全防护）
- ✅ 存储统计 API

#### 1️⃣1️⃣ 前端交互增强（刚完成）
- ✅ 视图模式切换（卡片/列表）
- ✅ 趋势箭头动画效果
- ✅ AI 分数指示器（三级颜色）
- ✅ 全局状态管理扩展
- ✅ 键盘快捷键系统
- ✅ 增强搜索与复制

---

## 🛠️ 开发工作流

### 目录结构

```
Cur-test - v3/
├── app/                          # Web 后端
│   ├── api/                      # API 路由
│   │   ├── hotspots.py           # 热榜 API
│   │   ├── articles.py           # 文章 API
│   │   ├── sources.py            # 采集源 API
│   │   ├── media.py              # 媒体文件 API
│   │   ├── keywords.py           # 关键词 API
│   │   ├── config.py             # 配置 API
│   │   └── wechat.py             # 微信 API
│   ├── models.py                 # 数据库模型
│   ├── services/                 # 业务服务
│   │   ├── media_service.py      # 媒体处理服务
│   │   └── media_processor.py    # 媒体集成处理器
│   ├── integrations/             # 数据集成层
│   └── main.py                   # FastAPI 入口
│
├── web/frontend/src/             # 前端源码
│   ├── pages/                    # 页面组件
│   │   ├── Hotspots.jsx          # 热榜总览
│   │   ├── ArticleDetail.jsx     # 内容详情
│   │   ├── Materials.jsx         # 素材中心
│   │   ├── Sources.jsx           # 采集源配置
│   │   ├── Keywords.jsx          # 关键词配置
│   │   ├── WeChat.jsx            # 微信公众号
│   │   ├── AIConfig.jsx          # AI模型配置
│   │   ├── NotifyStorage.jsx     # 推送渠道
│   │   └── ContentPolicy.jsx     # 内容策略
│   ├── components/               # 通用组件
│   │   ├── common/               # 基础组件
│   │   │   ├── PageHeader.jsx
│   │   │   ├── TrendIndicator.jsx      # ← 已增强
│   │   │   ├── HeatScoreBar.jsx
│   │   │   ├── ViewModeSwitcher.jsx     # ← 新增
│   │   │   └── AIScoreIndicator.jsx     # ← 新增
│   │   ├── hotspots/             # 热榜组件
│   │   │   ├── HotspotCard.jsx
│   │   │   └── HotspotToolbar.jsx      # ← 已增强
│   │   └── layout/               # 布局组件
│   │       └── AppShell.jsx
│   ├── contexts/                 # React Context
│   │   ├── PreferencesContext.jsx        # ← 已扩展
│   │   └── FavoritesContext.jsx
│   ├── hooks/                    # 自定义 Hooks
│   │   ├── usePageState.js
│   │   ├── useScrollPosition.js
│   │   ├── useKeyboardShortcuts.js      # ← 新增
│   │   └── useEnhancedInteractions.js   # ← 新增
│   ├── services/                 # API 服务
│   └── router/                   # 路由配置
│
├── hot_content_bridge/           # 采集桥接层
│   ├── cli.py                    # CLI 入口
│   ├── daemon.py                 # 守护进程
│   ├── pipeline_runner.py        # 流水线
│   ├── article_crawler.py        # 文章爬虫
│   └── config.yaml               # 配置文件
│
├── trendRadar/                   # 热榜采集引擎
├── crawl4ai/                     # AI 爬虫框架
├── we-mp-rss/                    # 微信公众号 RSS
├── scripts/                      # 工具脚本
│   ├── start_platform.py         # 一键启动脚本
│   └── verify_environment.py     # 环境自检
│
├── storage/                      # 本地存储
│   ├── images/                   # 图片文件
│   └── videos/                   # 视频封面
│
└── docs/                         # 项目文档
    └── 开发任务清单.md            # 任务追踪
```

### 常用开发命令

#### 后端开发

```bash
# 启动 API 服务（热重载）
uv run uvicorn app.main:app --reload --port 8000

# 运行单元测试
uv run pytest hot_content_bridge/tests/ -v

# 运行特定测试文件
uv run pytest hot_content_bridge/tests/test_pipeline_daemon_config.py -v

# 查看测试覆盖率
uv run pytest --cov=hot_content_bridge
```

#### 前端开发

```bash
cd web/frontend

# 启动开发服务器
npm run dev

# 类型检查（如果使用 TypeScript）
npx tsc --noEmit

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

#### 数据库操作

```bash
# 查看 SQLite 数据库
sqlite3 storage/hotspot_platform.db ".tables"

# 查看媒体文件记录
sqlite3 storage/hotspot_platform.db "SELECT * FROM media_items LIMIT 10;"

# 清理过期数据（保留 7 天）
uv run python -c "
from app.models import init_db, get_session_factory
from datetime import datetime, timedelta
from app.models import MediaItem

init_db()
session = get_session_factory()()
cutoff = datetime.utcnow() - timedelta(days=7)
deleted = session.query(MediaItem).filter(
    MediaItem.created_at < cutoff,
    MediaItem.status == 'success'
).delete()
session.commit()
print(f'Cleaned up {deleted} old media items')
"
```

### Git 工作流

```bash
# 创建功能分支
git checkout -b feature/frontend-interaction-enhance

# 提交代码
git add .
git commit -m "feat: add frontend interaction enhancements (14.1-14.6)

- ViewModeSwitcher component for card/list toggle
- Enhanced TrendIndicator with animations
- AIScoreIndicator for AI relevance scores
- Extended PreferencesContext for global state
- Keyboard shortcuts system (/ V W D ...)
- Enhanced search and copy functionality"

# 推送到远程
git push origin feature/frontend-interaction-enhance

# 合并到主分支
git checkout main
git merge feature/frontend-interaction-enhance
```

---

## ❓ 常见问题排查

### 问题 1: `uv sync` 失败

**症状**:
```
error: failed to synchronize: No matching python version
```

**解决方案**:
```bash
# 确认 Python 版本 >= 3.12
python --version

# 如果版本不对，安装正确的版本
# Windows: 从 python.org 下载
# macOS: brew install python@3.12
# Linux: apt install python3.12

# 重新同步
uv sync --group dev
```

### 问题 2: Playwright 浏览器未安装

**症状**:
```
playwright._impl._api_types.Error: Executable doesn't exist
```

**解决方案**:
```bash
uv run playwright install chromium

# 如果网络问题，使用镜像
PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright uv run playwright install chromium
```

### 问题 3: 端口被占用

**症状**:
```
OSError: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)
```

**解决方案**:
```bash
# Windows: 查找占用端口的进程
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :8000
kill -9 <PID>

# 或者使用其他端口
uv run uvicorn app.main:app --reload --port 8080
```

### 问题 4: 前端无法连接后端 API

**症状**:
浏览器控制台显示 `CORS error` 或 `Network Error`

**解决方案**:
```bash
# 确认后端正在运行
curl http://localhost:8000/api/health

# 检查前端代理配置
# web/frontend/vite.config.js 应包含:
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

### 问题 5: 数据库锁定

**症状**:
```
sqlalchemy.exc.OperationalError: database is locked
```

**解决方案**:
```bash
# 确保没有多个进程同时写入数据库
# 停止所有服务后删除锁文件
del storage\*.db-journal  # Windows
rm storage/*.db-journal      # Unix
```

### 问题 6: 内存不足

**症状**:
```
MemoryError: Unable to allocate array
```

**解决方案**:
```bash
# 减少并发爬虫数量
# 编辑 hot_content_bridge/config.yaml
article_crawl:
  max_concurrent: 3  # 降低并发数

# 增加系统虚拟内存（Windows）
# 系统属性 → 高级 → 性能 → 设置 → 虚拟内存
```

---

## 🏗️ 架构概览

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     用户浏览器                              │
│              (React + Ant Design + Vite)                    │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP / WebSocket
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI 后端 (Port 8000)                    │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │ 热榜 API  │ 文章 API │ 媒体 API │ 配置 API │ 微信 API │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
│  ┌──────────┬──────────┬──────────┐                          │
│  │ SQLAlchemy│ MediaService│ TrendRadarReader │              │
│  └──────────┴──────────┴──────────┘                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ 采集守护进程 │ │ 微信RSS服务 │ │ SQLite DB   │
│ (daemon.py) │ │ (we-mp-rss) │ │ (storage/)  │
└──────┬──────┘ └─────────────┘ └─────────────┘
       │
       ▼
┌─────────────┐ ┌─────────────┐
│ TrendRadar  │ │  Crawl4AI   │
│ (热榜采集)  │ │ (文章爬取)  │
└─────────────┘ └─────────────┘
```

### 数据流图

```
1. 热榜采集流程:
   TrendRadar → hotlist_reader → pipeline_runner → SQLite DB
                                                    ↓
2. 文章爬取流程:                                  FastAPI → 前端
   热榜数据 → article_crawler (crawl4ai) → Markdown → 存储
                                              ↓
3. 媒体处理流程:                             MediaService
   文章内容 → media_processor → 图片/视频提取 → 下载压缩 → 存储
                                                  ↓
4. API 访问流程:                               Static Files
   前端请求 → FastAPI → 查询数据库 → 返回 JSON/图片
```

### 技术栈总结

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | React 18 + Vite 5 | 现代化构建工具链 |
| | Ant Design 5 | 企业级 UI 组件库 |
| | lucide-react | 轻量 SVG 图标 |
| | react-markdown | Markdown 渲染 |
| **后端** | FastAPI 0.115+ | 高性能异步 Web 框架 |
| | SQLAlchemy 2.0 | ORM 数据库操作 |
| | Uvicorn | ASGI 服务器 |
| | httpx | 异步 HTTP 客户端 |
| **采集** | TrendRadar | 热榜采集引擎 |
| | Crawl4ai | AI 浏览器爬虫 |
| | Playwright | 浏览器自动化 |
| **数据** | SQLite | 轻量级数据库 |
| | Pillow | 图片处理 |
| **部署** | Docker (可选) | 容器化部署 |
| | nginx (可选) | 反向代理 |

---

## 📞 技术支持

### 日志查看

```bash
# 采集层日志（实时）
# 输出在终端或日志文件

# API 服务日志
# 终端直接显示或通过 journalctl (Linux)

# 前端控制台
# F12 打开开发者工具 → Console 标签
```

### 性能监控

```bash
# API 响应时间
curl -w "\nTime: %{time_total}s\n" http://localhost:8000/api/health

# 数据库查询性能
# 在代码中启用 SQL echo:
# engine = create_engine(..., echo=True)
```

### 常用调试技巧

```python
# 1. FastAPI 自动文档
# 访问 http://localhost:8000/docs 查看 Swagger UI

# 2. 前端 React DevTools
# 安装 React Developer Tools 浏览器扩展

# 3. 数据库可视化
# 使用 DB Browser for SQLite 打开 storage/*.db

# 4. 网络请求分析
# F12 → Network 标签 → 过滤 XHR/Fetch
```

---

## 📝 更新日志

### v1.0 (2026-06-02)

#### 新增功能
- ✨ **阶段八**: 图片和视频爬取存储系统
  - MediaService: 图片下载/压缩/存储
  - 视频封面提取（YouTube/Bilibili/微信）
  - MediaProcessor: 集成到抓取流程
  - 完整的媒体文件 API
  - 前端图片/视频优化展示

- ✨ **阶段十三**: 前端交互增强
  - ViewModeSwitcher: 卡片/列表视图切换
  - TrendIndicator 增强: 动画趋势箭头
  - AIScoreIndicator: AI 相关性分数可视化
  - 全局状态管理扩展
  - 键盘快捷键系统（/ V W D ...）
  - 增强实时搜索与一键复制

#### 优化改进
- 🎨 UI 组件库完善（12 个通用组件）
- ⚡ 性能优化（懒加载、防抖、虚拟滚动准备）
- 🔧 开发体验改善（热重载、类型检查）

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

感谢以下开源项目：
- [TrendRadar](https://github.com) - 热榜采集引擎
- [Crawl4AI](https://github.com/unclecode/crawl4ai) - AI 爬虫框架
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Web 框架
- [Ant Design](https://ant.design/) - 企业级 UI 组件库
- [React](https://react.dev/) - 前端 UI 库

---

**🎉 感谢使用热点发现平台！如有问题请提交 Issue 或联系开发团队。**
