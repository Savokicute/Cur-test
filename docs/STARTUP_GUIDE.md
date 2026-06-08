# 热点发现平台 — 完整启动方案

> **版本**: v3.0 | **更新日期**: 2026-06-03
> **适用环境**: Windows 10/11 (PowerShell 5.1+) / macOS / Linux

---

## 目录

1. [系统要求](#1-系统要求)
2. [方案一：首次安装（从零开始）](#2-方案一首次安装从零开始)
3. [方案二：已安装依赖（快速启动）](#3-方案二已安装依赖快速启动)
4. [功能检测报告](#4-功能检测报告)
5. [已知问题与修复记录](#5-已知问题与修复记录)
6. [故障排查指南](#6-故障排查指南)

---

## 1. 系统要求

### 环境依赖

| 组件 | 最低版本 | 推荐版本 | 检查命令 |
|------|---------|---------|---------|
| **Python** | >=3.12 | 3.12+ | `python --version` |
| **Node.js** | >=18.0 | >=20 LTS | `node --version` |
| **npm** | >=9.0 | >=10 | `npm --version` |
| **uv** (包管理器) | >=0.4 | 最新版 | `uv --version` |
| **Git** | >=2.30 | 最新版 | `git --version` |

### 可选依赖（微信公众号功能）

| 组件 | 用途 | 安装方式 |
|------|------|---------|
| **Redis** | we-mp-rss 缓存队列 | Docker 或直接安装 |
| **Playwright** | 微信文章抓取浏览器引擎 | `pip install playwright && playwright install` |

---

## 2. 方案一：首次安装（从零开始）

### 步骤 0：环境准备

```powershell
# 1. 检查 Python 版本（需要 >=3.12）
python --version

# 2. 安装 uv 包管理器（如果未安装）
pip install uv

# 3. 检查 Node.js 版本
node --version
npm --version

# 4. 克隆项目（如果还没有）
git clone <your-repo-url>
cd "Cur-test - v3"
```

### 步骤 1：安装后端 Python 依赖

```powershell
# 进入项目根目录
cd "d:\chao-TrendRadar\Cur-test - v3"

# 使用 uv 创建虚拟环境并安装所有依赖（推荐）
uv sync

# 或者使用 pip 传统方式：
# python -m venv .venv
# .venv\Scripts\activate
# pip install -r pyproject.toml  # 或手动安装 requirements
```

**关键依赖清单（pyproject.toml 已声明）：**

```
trendradar        # 热榜采集核心引擎（本地路径）
crawl4ai          # 文章内容抓取（本地路径）
fastapi>=0.115    # Web框架
uvicorn[standard] # ASGI服务器
sqlalchemy>=2.0   # ORM数据库
httpx>=0.27       # HTTP客户端
PyYAML>=6.0       # 配置文件解析
jinja2>=3.1       # 模板引擎（通知服务）
apscheduler>=3.10 # 定时任务调度
cachetools>=5.3   # 缓存工具
aioredis>=2.0     # Redis异步客户端（可选）
python-multipart  # 文件上传支持
click>=8.1        # CLI框架
tenacity>=8.5     # 重试机制
markdown>=3.5     # Markdown解析
```

### 步骤 2：安装前端 Node.js 依赖

```powershell
# 进入前端目录
cd web\frontend

# 安装 npm 依赖
npm install

# 验证安装成功
npm run dev --version  # 或检查 node_modules 是否存在

# 返回项目根目录
cd ..\..
```

**前端关键依赖（package.json）：**

```
react^19.2 + react-dom^19.2   # UI框架
react-router-dom^6.30          # 路由
antd^5.29                      # UI组件库
axios^1.16                    # HTTP客户端
lucide-react^1.16             # 图标库
vite^8.0                      # 构建工具
dayjs^1.11                    # 日期处理
react-markdown^10.1           # Markdown渲染
remark-gfm^4.0                # GFM语法支持
```

### 步骤 3：初始化数据库

```powershell
# 首次运行会自动创建 SQLite 数据库文件
# 数据库位置: data/hotspot.db（自动生成）

# 手动触发一次数据采集以验证完整链路
uv run python -m hot_content_bridge.cli run-pipeline --quick-hotlist
```

### 步骤 4：启动服务

#### 方式 A：分别启动（推荐开发调试）

```powershell
# === 终端 1：启动后端 API 服务 ===
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# === 终端 2：启动前端开发服务 ===
cd web\frontend
npm run dev
```

#### 方式 B：使用平台启动脚本（可选含 we-mp-rss）

```powershell
# 仅启动热榜采集 + API（不含微信）
uv run python scripts/start_platform.py --no-wemp

# 启动全部服务（包含 we-mp-rss，需要先安装其依赖）
uv run python scripts/start_platform.py

# 单次运行采集后退出（不启动守护进程）
uv run python scripts/start_platform.py --once
```

### 步骤 5：验证启动成功

| 检查项 | 地址 | 预期结果 |
|--------|------|---------|
| 后端API根路径 | http://localhost:8000/ | 返回JSON: `{"name":"热点发现平台 API"}` |
| API文档(Swagger) | http://localhost:8000/docs | Swagger UI 页面 |
| 前端页面 | http://localhost:5173/ | 热榜总览页面，显示热点数据 |
| 系统状态 | http://localhost:8000/api/status | 返回状态JSON |

---

## 3. 方案二：已安装依赖（快速启动）

> 适用场景：已经完成过步骤0-2，虚拟环境和 node_modules 均已就绪。

### 快速启动命令（一键复制）

```powershell
# === 终端 1：后端（在项目根目录执行）===
cd "d:\chao-TrendRadar\Cur-test - v3"
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# === 终端 2：前端（在项目根目录执行）===
cd "d:\chao-TrendRadar\Cur-test - v3\web\frontend"
npm run dev
```

### 启动检查清单

```
□ 后端终端显示: "INFO: Uvicorn running on http://0.0.0.0:8000"
□ 后端终端显示: "管道调度已启动" / "MCP工具初始化完成"
□ 后端终端显示: "INFO: *.*.*:*:* - GET /api/hotspots/dates HTTP/1.1 200 OK"
□ 前端终端显示: "Local: http://localhost:5173/"
□ 浏览器打开 http://localhost:5173/ 能看到热榜数据列表
```

### 可选：启动 we-mp-rss 微信公众号服务

```powershell
# 前置条件：已安装 we-mp-rss 的全部依赖
cd we-mp-rss
uv pip install -r requirements.txt

# 启动微信服务（端口 8001）
uv run python main.py -job True
```

> **注意**：we-mp-rss 不是必须的。未启动时，微信公众号页面会自动进入 Mock 降级模式，显示演示数据。

---

## 4. 功能检测报告

> 检测时间: 2026-06-03 | 后端: localhost:8000 | 前端: localhost:5173

### 4.1 前端页面检测结果

| # | 页面路由 | 页面名称 | 状态 | 备注 |
|---|---------|---------|------|------|
| 1 | `/` | 热榜总览 | ✅ 正常 | 55条热点数据，关键词标签筛选正常 |
| 2 | `/assistant` | 智能助手 | ✅ 正常 | 聊天界面、快捷查询、输入框均正常 |
| 3 | `/ai-analysis` | AI分析 | ✅ 正常 | 统计卡片、工具栏、空状态引导正常 |
| 4 | `/wechat` | 微信公众号 | ✅ 正常(Mock) | we-mp-rss未启动时自动降级为演示数据 |
| 5 | `/materials` | 素材中心 | ✅ 正常 | 收藏列表加载正常 |
| 6 | `/sources` | 采集源配置 | ✅ 正常 | 5个平台配置，增删改查正常 |
| 7 | `/keywords` | 关键词配置 | ✅ 正常 | 编辑器加载5392字符配置，4个标签页正常 |
| 8 | `/notifications` | 通知配置 | ✅ 已修复 | 统计卡片+订阅列表正常（修复了Radio/Row导入缺失） |
| 9 | `/settings` | 系统设置 | ✅ 正常 | 3个标签页表单正常 |
| 10 | `/ai-config` | AI智能 | ✅ 正常 | 4个标签页模型配置正常 |
| 11 | `/content` | 内容策略 | ✅ 正常 | 报告模式/筛选策略/推送控制正常 |
| 12 | `/notify` | 通知存储 | ✅ 正常 | 9种通知渠道配置项完整 |
| 13 | `/media-test` | 媒体测试 | ⚠️ 警告 | 页面正常但缺少测试数据（非致命） |

**前端页面通过率: 12/13 正常 (92.3%)，1个警告（非致命）**

### 4.2 后端API检测结果

| API端点 | 方法 | 状态 | 功能 |
|---------|------|------|------|
| `/` | GET | ✅ 200 | API信息 |
| `/api/status` | GET | ✅ 200 | 系统状态（含管道调度信息） |
| `/api/hotspots/dates` | GET | ✅ 200 | 可用日期列表 |
| `/api/hotspots?date=xxx` | GET | ✅ 200 | 热榜数据查询 |
| `/api/sources/hot-sources` | GET | ✅ 200 | 热榜采集源列表 |
| `/api/sources/config-yaml` | GET | ✅ 200 | YAML配置原始内容 |
| `/api/keywords/config` | GET | ✅ 200 | 关键词配置内容 |
| `/api/keywords/parsed` | GET | ✅ 200 | 关键词解析结果 |
| `/api/keywords/batch-match` | POST | ✅ 200 | 批量关键词匹配 |
| `/api/config` | GET | ✅ 200 | 全局配置 |
| `/api/wechat/status` | GET | ✅ 200 | 微信服务状态(含mock标记) |
| `/api/ai-analysis/templates` | GET | ✅ 200 | AI分析预设模板 |
| `/api/ai-analysis/stats` | GET | ✅ 200 | AI分析统计 |
| `/api/ai-analysis/configs` | GET | ✅ 200 | 分析配置列表 |
| `/api/notifications/subscriptions` | GET | ✅ 200 | 订阅列表 |
| `/api/crawl/trigger` | POST | ✅ 405 | 手动触发爬取（POST专用） |
| `/docs` | GET | ✅ 200 | Swagger API文档 |

**后端API通过率: 15/15 正常 (100%)**

### 4.3 浏览器控制台

| 级别 | 数量 | 详情 |
|------|------|------|
| 🔴 Error | 0 | 无崩溃错误 |
| 🟡 Warning | 2 | antd 弃用提示（`destroyOnClose` → `destroyOnHidden`、`useForm`未连接Form） |

---

## 5. 已知问题与修复记录

### 问题 1：通知配置页面崩溃（已修复）

- **现象**: 访问 `/notifications` 显示 `Unexpected Application Error! Radio is not defined`
- **原因**: [CreateSubscriptionModal.jsx](web/frontend/src/components/notifications/CreateSubscriptionModal.jsx) 缺少 `Radio` 组件导入
- **修复**: 在 antd 导入中添加 `Radio`
- **状态**: ✅ 已修复

### 问题 2：通知日志面板崩溃（已修复）

- **现象**: 修复问题1后出现 `Row is not defined`
- **原因**: [NotificationLogPanel.jsx](web/frontend/src/components/notifications/NotificationLogPanel.jsx) 缺少 `Row` 和 `Col` 组件导入
- **修复**: 在 antd 导入中添加 `Row, Col`
- **状态**: ✅ 已修复

### 问题 3：媒体测试页面缺少数据（已知限制）

- **现象**: 访问 `/media-test` 显示 "Test data not found"
- **原因**: 未配置媒体测试数据
- **影响**: 非致命，不影响其他功能
- **处理**: 可在后续添加测试数据或忽略此页面

### 问题 4：微信公众号 Mock 模式超时提示（已知行为）

- **现象**: 微信公众号页面同时显示橙色降级横幅和红色超时错误
- **原因**: 首次加载时 we-mp-rss 连接超时（10s），随后Mock数据返回
- **影响**: 不影响使用，红色提示可手动关闭
- **优化建议**: 可在后续优化超时逻辑，避免重复展示错误

---

## 6. 故障排查指南

### 常见问题速查

#### Q1: 后端启动失败 `ModuleNotFoundError`

```powershell
# 确保使用 uv 运行（自动管理虚拟环境）
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 如果仍有问题，重新同步依赖
uv sync
```

#### Q2: 前端启动失败 `Cannot find module`

```powershell
# 进入前端目录重新安装依赖
cd web\frontend
rm -rf node_modules package-lock.json  # Linux/Mac
# Windows: rmdir /s /q node_modules & del package-lock.json
npm install
npm run dev
```

#### Q3: 前端页面能打开但数据显示空白

```powershell
# 1. 检查后端是否运行
curl http://localhost:8000/api/status

# 2. 检查浏览器控制台是否有CORS错误
#    Vite代理配置在 vite.config.js 中已设置 /api -> localhost:8000

# 3. 手动触发一次数据采集
curl -X POST http://localhost:8000/api/crawl/trigger
```

#### Q4: 微信公众号页面一直显示演示数据

```powershell
# 这是正常的降级行为。要启用真实数据：

# Step 1: 安装 we-mp-rss 依赖
cd we-mp-rss
uv pip install -r requirements.txt

# Step 2: 确保 Redis 可用（或修改 config.yaml 禁用Redis）

# Step 3: 启动 we-mp-rss
uv run python main.py -job True

# Step 4: 刷新微信公众号页面
```

#### Q5: 端口被占用

```powershell
# 查看8000端口占用
netstat -ano | findstr :8000

# 查看5173端口占用
netstat -ano | findstr :5173

# 杀掉占用进程（替换 PID）
taskkill /PID <pid> /F

# 或使用其他端口
uv run uvicorn app.main:app --port 8001
npm run dev -- --port 5174
```

### 日志查看

| 服务 | 日志位置 | 说明 |
|------|---------|------|
| 后端API | 终端输出 (stdout) | Uvicorn访问日志 + 应用日志 |
| 管道调度 | 终端输出 | 采集/抓取进度日志 |
| 前端 | 终端输出 + 浏览器F12 | Vite编译日志 + Console |

### 性能参考

| 指标 | 参考值 |
|------|--------|
| 后端冷启动 | ~5-10秒（含依赖导入+管道初始化） |
| 前端冷启动 | ~2-3秒（Vite HMR） |
| 热榜数据接口响应 | <200ms（SQLite本地数据库） |
| 文章详情接口响应 | <500ms（含远程抓取） |
| 首次全量采集 | ~60-120秒（取决于平台数量和网络） |

---

## 附录：服务架构图

```
┌─────────────────────────────────────────────────────┐
│                   用户浏览器                         │
│              http://localhost:5173                  │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP (Vite Dev Server)
                   ▼
┌─────────────────────────────────────────────────────┐
│              前端 (React 18 + Vite 5)               │
│   ┌─────────┐ ┌──────────┐ ┌──────────┐            │
│   │ 热榜总览 │ │ 智能助手  │ │ AI分析   │ ... 13页  │
│   └────┬────┘ └────┬─────┘ └────┬─────┘            │
│        │           │            │                    │
│        └───────────┴────────────┘                    │
│                   │                                  │
│           /api/* 代理转发                             │
└───────────────────┼──────────────────────────────────┘
                    │ HTTP (Proxy)
                    ▼
┌─────────────────────────────────────────────────────┐
│          后端 API (FastAPI :8000)                    │
│  ┌────────┐ ┌──────────┐ ┌──────────┐             │
│  │热榜API  │ │文章API    │ │微信API   │ ... 12路由  │
│  └───┬────┘ └───┬──────┘ └───┬──────┘             │
│      │          │           │                       │
│  ┌───▼──────────▼───────────▼──────────────────┐   │
│  │         业务服务层                             │   │
│  │  PipelineDaemon │ AIAnalysis │ Assistant      │   │
│  │  CacheService   │ TaskQueue  │ Notification   │   │
│  └───┬──────────┬──┴───────────┴────────────────┘   │
│      │          │                                    │
│  ┌───▼──┐  ┌───▼────┐                              │
│  │SQLite│  │TrendRadar│  crawl4ai                  │
│  │(DB)  │  │(采集引擎) │  (文章抓取)              │
│  └──────┘  └─────────┘                              │
└─────────────────────────────────────────────────────┘
                    │ (可选)
                    ▼
┌─────────────────────────────────────────────────────┐
│       we-mp-rss (:8001) — 微信公众号服务             │
│       (未启动时自动 Mock 降级)                        │
└─────────────────────────────────────────────────────┘
```
