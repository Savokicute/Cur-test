# 虚机从零部署指南 - 热点发现平台（完整版）

> **适用场景**：全新 Linux 虚拟机，从零开始部署热点发现平台  
> **预计耗时**：30-60分钟（取决于网络速度）  
> **文档版本**：v2.0 (2026-06-12 更新)

---

## 📋 完整部署流程总览

```
第1步: 系统基础环境安装 (5-10分钟)
    ↓
第2步: Python 3.12 + uv 安装 (5分钟)
    ↓
第3步: 项目代码上传/下载 (5-10分钟)
    ↓
第4步: 项目依赖安装 (10-15分钟)
    ↓
第5步: 浏览器引擎安装 (5-10分钟)
    ↓
第6步: 配置文件修改 (5分钟)
    ↓
第7步: 单轮测试验证 (5-10分钟)
    ↓
第8步: 配置 Systemd 长期运行 (5分钟)
    ↓
第9步: 监控与维护配置 (可选，5分钟)
```

---

## 第1步：系统基础环境安装

### 1.1 确认系统版本

```bash
# 查看系统版本
cat /etc/os-release

# 查看内核版本
uname -a

# 查看内存和磁盘
free -h
df -h /
```

**推荐配置**：
- Ubuntu 22.04 LTS / 24.04 LTS（推荐）或 Debian 12
- 内存 ≥ 2GB（建议 4GB）
- 磁盘 ≥ 20GB

### 1.2 更新系统并安装基础工具

```bash
# ===== Ubuntu/Debian =====

# 1) 更新软件包列表
sudo apt update

# 2) 升级已安装的包（可选，但推荐）
sudo apt upgrade -y

# 3) 安装基础工具
sudo apt install -y \
    build-essential \
    curl \
    wget \
    git \
    unzip \
    htop \
    tmux \
    vim \
    net-tools \
    ca-certificates \
    gnupg \
    lsb-release

# 4) 安装 Chromium 浏览器及其依赖（爬虫必需）
sudo apt install -y \
    chromium-browser \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils

# ===== CentOS/RHEL/Rocky Linux =====

# 1) 更新系统
sudo yum update -y

# 2) 安装 EPEL 和基础工具
sudo yum install -y epel-release
sudo yum groupinstall -y "Development Tools"
sudo yum install -y curl wget git unzip htop tmux vim net-tools

# 3) 安装 Chromium 及依赖
sudo yum install -y chromium \
    alsa-lib atk at-spi2-atk cups-libs dbus-libs \
    gtk3 libdrm libgbm nspr nss \
    libXcomposite libXdamage libXfixes libXrandr
```

### 1.3 验证基础环境

```bash
# 检查 Git 版本
git --version
# 期望输出: git version 2.x.x

# 检查 Chromium 是否安装成功
which chromium-browser || which chromium
chromium-browser --version || chromium --version
# 期望输出类似: Chromium 120.x.x.x

# 检查可用内存
free -h
# 确保可用内存 > 1GB
```

---

## 第2步：Python 3.12 + uv 安装

### 2.1 检查当前 Python 版本

```bash
python3 --version
# 如果显示 >= 3.12，可以跳过下一步
# 如果显示 < 3.12 或 "command not found"，继续安装
```

### 2.2 安装 Python 3.12（如果系统没有）

```bash
# ===== 方法 A：使用 deadsnakes PPA（Ubuntu 推荐）=====

# 1) 添加 PPA
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# 2) 安装 Python 3.12
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# 3) 验证安装
python3.12 --version
# 期望输出: Python 3.12.x

# ===== 方法 B：使用 conda/miniconda（通用）=====

# 1) 下载 Miniconda 安装脚本
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# 2) 运行安装（一路回车，最后输入 yes）
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3

# 3) 初始化 conda
~/miniconda3/bin/conda init bash
source ~/.bashrc

# 4) 创建 Python 3.12 环境
conda create -n hotspot python=3.12 -y
conda activate hotspot

python --version
# 期望输出: Python 3.12.x

# ===== 方法 C：从源码编译（高级用户）=====
# （略，一般不推荐）
```

### 2.3 安装 uv（Python 包管理器）

```bash
# 1) 安装 uv（一行命令）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2) 重新加载 shell 配置
source ~/.bashrc
# 或者
source ~/.zshrc

# 3) 验证安装
uv --version
# 期望输出: uv 0.x.x

# 4) 查看 uv 帮助（可选）
uv --help
```

> **为什么用 uv 而不是 pip？**
> - 速度快 10-100 倍
> - 自动创建和管理虚拟环境
> - 锁定依赖版本，保证可复现性
> - 类似 Node.js 的 npm/pnpm

---

## 第3步：项目代码上传/下载

### 3.1 创建项目目录

```bash
# 创建 /opt 目录下的项目文件夹
sudo mkdir -p /opt/hotspot-platform

# 设置权限（根据你的用户调整）
sudo chown $USER:$USER /opt/hotspot-platform

# 进入目录
cd /opt/hotspot-platform
```

### 3.2 上传项目代码（选择一种方式）

#### 方式 A：使用 Git 克隆（如果有仓库）

```bash
# 替换为你的实际仓库地址
git clone <your-git-repo-url> .

# 或者先克隆再移动
git clone <your-git-repo-url> temp_repo
cp -r temp_repo/* .
cp -r temp_repo/.* . 2>/dev/null  # 复制隐藏文件
rm -rf temp_repo
```

#### 方式 B：使用 scp/sftp 从本地上传

**在你的本地电脑（Windows/Mac/Linux）上执行**：

```bash
# Windows PowerShell / Mac / Linux 终端

# 1) 打包本地项目（在本地项目目录执行）
cd "d:\chao-TrendRadar\Cur-test - v3"
tar -czvf ../hotspot-platform.tar.gz .

# 2) 上传到服务器（替换 user@server-ip 为实际信息）
scp ../hotspot-platform.tar.gz user@your-server-ip:/opt/

# 3) SSH 登录到服务器
ssh user@your-server-ip

# 4) 解压
cd /opt/hotspot-platform
tar -xzvf ../hotspot-platform.tar.gz
rm ../hotspot-platform.tar.gz
```

#### 方式 C：使用 rsync 增量同步（适合大项目）

```bash
# 在本地电脑执行
rsync -avz --progress \
    -e "ssh" \
    "d:/chao-TrendRadar/Cur-test - v3/" \
    user@your-server-ip:/opt/hotspot-platform/
```

#### 方式 D：使用 SFTP 工具（图形界面）

推荐工具：
- **Windows**: WinSCP, FileZilla, MobaXterm
- **Mac**: Cyberduck, Transmit, FileZilla

操作步骤：
1. 连接到虚机 `user@your-server-ip`
2. 导航到 `/opt/`
3. 创建 `hotspot-platform` 文件夹
4. 将本地 `Cur-test - v3` 目录下所有文件拖拽上传

### 3.3 验证项目结构

```bash
# 确认关键文件存在
ls -la

# 应该能看到这些文件/目录：
# ✓ hot_content_bridge/
# ✓ trendRadar/
# ✓ crawl4ai/
# ✓ pyproject.toml
# ✓ scripts/
# ✓ hot_content_bridge/config.yaml
# ✓ trendRadar/config/config.yaml

# 统计文件数量
find . -type f | wc -l
```

---

## 第4步：项目依赖安装

### 4.1 使用 uv 安装所有依赖

```bash
cd /opt/hotspot-platform

# 1) 同步依赖（自动创建虚拟环境 .venv）
uv sync

# 这一步会：
# - 读取 pyproject.toml
# - 创建 .venv 虚拟环境
# - 安装所有依赖包（包括 crawl4ai, trendradar 等）
# - 生成 uv.lock 锁定文件

# 预计耗时：5-15分钟（取决于网络速度）
```

### 4.2 如果 uv sync 失败，手动安装

```bash
# 1) 手动创建虚拟环境
python3.12 -m venv .venv

# 2) 激活虚拟环境
source .venv/bin/activate

# 3) 升级 pip
pip install --upgrade pip setuptools wheel

# 4) 安装项目本身（开发模式）
pip install -e ".[dev]"

# 5) 安装 TrendRadar 子模块
pip install -e "./trendRadar"

# 6) 安装 crawl4ai 子模块
pip install -e "./crawl4ai"
```

### 4.3 验证依赖安装

```bash
# 激活虚拟环境
source .venv/bin/activate

# 测试导入核心模块
python -c "
import hot_content_bridge
import trendradar
import crawl4ai
print('✅ 所有核心模块导入成功')
print(f'  hot_content_bridge: {hot_content_bridge.__file__}')
print(f'  trendradar: {trendradar.__version__}')
print(f'  crawl4ai: {crawl4ai.__version__}')
"

# 期望输出：
# ✅ 所有核心模块导入成功
#   hot_content_bridge: /opt/hotspot-platform/hot_content_bridge/__init__.py
#   trendradar: 2.2.0
#   crawl4ai: 0.8.x
```

---

## 第5步：浏览器引擎安装（重要！）

### 5.1 安装 Playwright 浏览器

```bash
cd /opt/hotspot-platform
source .venv/bin/activate

# 1) 安装 Chromium 浏览器
uv run playwright install chromium

# 输出示例：
# Chromium xxx downloaded to /home/user/.cache/ms-playwright/

# 2) 安装浏览器的系统依赖
uv run playwright install-deps

# 这一步会自动安装 Chromium 运行所需的所有库
# 可能需要 sudo 权限
```

### 5.2 验证浏览器可用性

```bash
# 测试浏览器是否能正常启动
uv run python -c "
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig

async def test():
    config = BrowserConfig(headless=True, verbose=False)
    async with AsyncWebCrawler(config=config) as crawler:
        result = await crawler.arun(url='https://httpbin.org/get')
        if result.success:
            print('✅ 浏览器引擎工作正常')
            print(f'  状态码: {result.status_code}')
        else:
            print('❌ 浏览器测试失败')

asyncio.run(test())
"

# 期望输出：
# ✅ 浏览器引擎工作正常
#   状态码: 200
```

> **如果测试失败**，请查看 [常见问题排查](#第9步常见问题排查) 章节

---

## 第6步：配置文件修改

### 6.1 了解配置文件位置

```
/opt/hotspot-platform/
├── hot_content_bridge/config.yaml      ← 主配置（热榜+爬虫）
├── trendRadar/config/config.yaml       ← TrendRadar 配置（平台+AI+通知）
└── trendRadar/config/timeline.yaml     ← 时间调度表（何时执行）
```

### 6.2 修改桥接器配置（必须）

编辑 `hot_content_bridge/config.yaml`：

```bash
# 使用 vim 编辑（或 nano）
vim hot_content_bridge/config.yaml
```

**关键配置项说明**：

```yaml
# ============================================================
# ⭐ 核心配置：多长时间获取一次热榜？
# ============================================================
pipeline_daemon:
  enabled: true                     # 启用定时任务
  run_on_startup: true              # 启动后立即执行第一轮
  hotlist_interval_minutes: 60      # ⭐⭐⭐ 改这里！单位：分钟
                                   # 10 = 每10分钟（高频）
                                   # 30 = 每30分钟（推荐）
                                   # 60 = 每1小时（稳健）
                                   # 120 = 每2小时（省资源）
                                   
  initial_delay_seconds: 5          # 首次执行前等待时间
  
  full_trendradar_sync: false       # false=快速模式(推荐)
                                   # true=完整模式(含AI分析)
                                   
  crawl_after_hotlist: true         # 热榜获取后自动爬取正文 ★
  crawl_limit_per_run: 0            # 0=不限制，爬取全部

# ============================================================
# 正文爬取参数调优
# ============================================================
article_crawl:
  concurrency: 2                    # 并发数（建议 2-4）
  per_domain_min_delay_s: 1.5       # 最小延迟（防封）
  per_domain_max_delay_s: 3.5       # 最大延迟
  request_timeout_ms: 60000         # 超时时间（毫秒）
  max_retries: 2                    # 重试次数
  
  recrawl_success: false            # ⭐ false=跳过已爬取URL（去重）
                                   # true=强制重新爬取
```

### 6.3 修改 TrendRadar 配置（按需）

编辑 `trendRadar/config/config.yaml`：

```bash
vim trendRadar/config/config.yaml
```

**必须修改项**：

```yaml
# AI 模型配置（如果使用AI功能）
ai:
  model: "openai/glm-4-flash"        # 模型名称
  api_key: "你的API密钥"             # ← 必须替换！
  api_base: "https://open.bigmodel.cn/api/paas/v4"  # API地址
  timeout: 120

# 平台启用/禁用
platforms:
  enabled: true
  sources:
    - id: wallstreetcn-hot          # 华尔街见闻
      enabled: true                 # true=启用, false=禁用
    - id: thepaper                  # 澎湃新闻
      enabled: true
    - id: cls-hot                   # 财联社热门
      enabled: true
    - id: ifeng                     # 凤凰网
      enabled: false                # 不需要的平台设为false
```

### 6.4 保存配置

```bash
# 确认配置文件语法正确
uv run python -c "
from hot_content_bridge.config import BridgeConfig
cfg = BridgeConfig.load()
print('✅ 配置文件加载成功')
print(f'  热榜间隔: {cfg.pipeline_daemon.hotlist_interval_minutes} 分钟')
print(f'  自动爬取正文: {cfg.pipeline_daemon.crawl_after_hotlist}')
print(f'  并发数: {cfg.article_crawl.concurrency}')
print(f'  去重开关: recrawl_success={cfg.article_crawl.recrawl_success}')
"
```

---

## 第7步：单轮测试验证（非常重要！）

### 7.1 初始化数据库

```bash
cd /opt/hotspot-platform

# 创建数据目录
mkdir -p output/news output/rss output/html

# 初始化数据库表结构
uv run python -c "
from hot_content_bridge.storage import ensure_article_tables
from hot_content_bridge.config import BridgeConfig

cfg = BridgeConfig.load()
db_path = ensure_article_tables(cfg)
print(f'✅ 数据库初始化完成')
print(f'  数据库路径: {db_path}')
"
```

### 7.2 执行单轮测试（快速模式，无AI）

```bash
# 执行一轮完整的：热榜获取 + 正文爬取
# 加 --once 表示只执行一次就退出
uv run python scripts/start_platform.py --once

# 观察输出日志，应该看到：
# [start] 启动命令...
# [start] Services running...
# Pipeline cycle start ...
# Hot list: OK                          ← 热榜获取成功
# Crawling XX URLs (pending=YY, skipped=ZZ)  ← 开始爬取正文
# Article crawl: crawled=AA skipped=ZZ     ← 爬取完成
# Pipeline cycle end
```

**首次执行可能耗时较长（5-15分钟），因为要爬取所有热榜条目的正文。**

### 7.3 验证数据是否正确写入

```bash
# 查看今天的数据库名称
ls -lh output/news/

# 查看数据库内容
TODAY=$(date +%Y-%m-%d)
sqlite3 output/news/${TODAY}.db "

-- 1. 查看总体统计
SELECT 
    'article_contents' as table_name,
    COUNT(*) as total,
    SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed_count
FROM article_contents

UNION ALL

SELECT 
    'hotlist_items',
    COUNT(*),
    0,
    0
FROM hotlist_items;
"

# 期望看到类似输出：
# table_name        |total|success_count|failed_count|
# -----------------|-----|---------------|-----------|
# article_contents |  42 |            38 |          4|
# hotlist_items    |  50 |             0 |          0|
```

### 7.4 测试分步命令（用于调试）

```bash
# 仅获取热榜（不爬正文）- 快速，几秒钟
uv run python -m hot_content_bridge.cli fetch-hotlist-only

# 仅爬取正文（基于已有热榜）- 较慢
uv run python -m hot_content_bridge.cli crawl-articles

# 限制只爬取 3 条（用于快速验证）
uv run python -m hot_content_bridge.cli crawl-articles --limit 3

# 查看已加载的平台规则
uv run python -m hot_content_bridge.cli list-platform-rules
```

### 7.5 如果测试失败，排查问题

参见 [第9步：常见问题排查](#第9步常见问题排查)

---

## 第8步：配置 Systemd 长期运行（生产必备）

### 8.1 创建 Systemd 服务文件

```bash
# 创建服务配置文件
sudo tee /etc/systemd/system/hotspot-platform.service << 'EOF'
[Unit]
Description=HotSpot Platform Daemon
Documentation=https://github.com/your-repo/hotspot-platform
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hotspot-platform

# 环境变量
Environment="PATH=/opt/hotspot-platform/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONUTF8=1"
Environment="PYTHONIOENCODING=utf-8"

# 启动命令
ExecStart=/opt/hotspot-platform/.venv/bin/python scripts/start_platform.py

# 失败后自动重启策略
Restart=on-failure
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=5

# 日志输出
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hotspot-platform

# 资源限制（防止内存泄漏）
MemoryMax=4G
CPUQuota=80%

# 安全加固（可选，取消注释启用）
# NoNewPrivileges=true
# ProtectSystem=strict
# ProtectHome=true
# ReadWritePaths=/opt/hotspot-platform/output
# PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
```

### 8.2 启动和管理服务

```bash
# 1) 重新加载 systemd 配置
sudo systemctl daemon-reload

# 2) 设置开机自启
sudo systemctl enable hotspot-platform

# 3) 启动服务
sudo systemctl start hotspot-platform

# 4) 查看服务状态（应该显示 active (running)）
sudo systemctl status hotspot-platform

# 输出示例：
# ● hotspot-platform.service - HotSpot Platform Daemon
#      Loaded: loaded (/etc/systemd/system/hotspot-platform.service; enabled; vendor preset: enabled)
#      Active: active (running) since Mon 2026-06-12 08:00:05 CST; 5s ago
#    Main PID: 12345 (python)
#      CGroup: /system.slice/hotspot-platform.service
#              └─12345 /opt/hotspot-platform/.venv/bin/python scripts/start_platform.py
```

### 8.3 查看实时日志

```bash
# 实时跟踪日志（按 Ctrl+C 退出）
sudo journalctl -u hotspot-platform -f

# 查看最近 100 行日志
sudo journalctl -u hotspot-platform -n 100

# 查看今天的日志
sudo journalctl -u hotspot-platform --since today

# 只看错误日志
sudo journalctl -u hotspot-platform -p err
```

### 8.4 服务管理常用命令

```bash
# 停止服务
sudo systemctl stop hotspot-platform

# 重启服务（修改配置后）
sudo systemctl restart hotspot-platform

# 查看服务详细信息
sudo systemctl show hotspot-platform

# 禁止开机自启
sudo systemctl disable hotspot-platform

# 再次启用开机自启
sudo systemctl enable hotspot-platform
```

### 8.5 日志持久化配置（可选但推荐）

```bash
# 创建持久化日志目录
sudo mkdir -p /var/log/journal

# 配置 journald 持久化存储
sudo tee /etc/systemd/journald.conf.d/hotspot.conf << 'EOF'
[Journal]
Storage=persistent
Compress=yes
SystemMaxUse=500M
EOF

# 重启 journald 使配置生效
sudo systemctl restart systemd-journald
```

---

## 第9步：监控与维护配置（可选）

### 9.1 创建健康检查脚本

```bash
# 创建健康检查脚本
sudo tee /opt/hotspot-platform/scripts/health_check.sh << 'SCRIPT'
#!/bin/bash
# HotSpot Platform 健康检查脚本

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE="/var/log/hotspot-health.log"
SERVICE_NAME="hotspot-platform"

# 检查进程是否存在
if pgrep -f "start_platform.py" > /dev/null; then
    STATUS="RUNNING"
else
    STATUS="DOWN"
fi

# 检查最近是否有新的数据库生成（最近1小时内）
RECENT_DB=$(find /opt/hotspot-platform/output/news -name "*.db" -mmin -60 2>/dev/null | wc -l)

# 记录日志
echo "[$TIMESTAMP] Status=$STATUS RecentDBs_in_last_hour=$RECENT_DB" >> "$LOG_FILE"

# 如果进程挂了，尝试自动重启
if [ "$STATUS" = "DOWN" ]; then
    echo "[$TIMESTAMP] Service is DOWN, attempting restart..." >> "$LOG_FILE"
    systemctl restart "$SERVICE_NAME"
    
    # 等待5秒后再次检查
    sleep 5
    
    if pgrep -f "start_platform.py" > /dev/null; then
        echo "[$TIMESTAMP] Restart SUCCESS" >> "$LOG_FILE"
    else
        echo "[$TIMESTAMP] Restart FAILED - need manual intervention!" >> "$LOG_FILE"
        # 可以在这里添加告警通知逻辑（邮件/钉钉等）
    fi
fi
SCRIPT

# 设置执行权限
chmod +x /opt/hotspot-platform/scripts/health_check.sh
```

### 9.2 设置定时健康检查

```bash
# 编辑 crontab（当前用户的定时任务）
crontab -e

# 在文件末尾添加以下行（每5分钟检查一次）
*/5 * * * * /opt/hotspot-platform/scripts/health_check.sh

# 保存退出（vim 按 :wq）
```

### 9.3 创建备份脚本

```bash
sudo tee /opt/hotspot-platform/scripts/backup.sh << 'SCRIPT'
#!/bin/bash
# 数据备份脚本

BACKUP_DIR="/opt/backups/hotspot-platform"
DATE=$(date +%Y%m%d_%H%M%S)
SOURCE_DIR="/opt/hotspot-platform/output"
CONFIG_DIR="/opt/hotspot-platform"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 备份输出数据（SQLite数据库、HTML报告等）
tar -czf "${BACKUP_DIR}/data_${DATE}.tar.gz" \
    -C "$SOURCE_DIR" .

# 备份配置文件
tar -czf "${BACKUP_DIR}/config_${DATE}.tar.gz" \
    "${CONFIG_DIR}/hot_content_bridge/config.yaml" \
    "${CONFIG_DIR}/trendRadar/config/" 2>/dev/null

# 清理旧备份（保留最近7天）
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete

echo "$(date '+%Y-%m-%d %H:%M:%S') Backup completed: data_${DATE}.tar.gz + config_${DATE}.tar.gz"
SCRIPT

chmod +x /opt/hotspot-platform/scripts/backup.sh
```

### 9.4 设置自动备份（每天凌晨3点）

```bash
crontab -e

# 在末尾添加（每天凌晨3点执行备份）
0 3 * * * /opt/hotspot-platform/scripts/backup.sh >> /var/log/hotspot-backup.log 2>&1
```

### 9.5 性能监控命令速查

```bash
# 实时监控系统资源（按 q 退出）
htop

# 或使用 top
top -p $(pgrep -d',' -f "start_platform.py")

# 查看磁盘使用情况
du -sh /opt/hotspot-platform/*
df -h /

# 查看内存使用
free -h

# 查看网络连接
netstat -tulnp | grep python

# 查看 SQLite 数据库大小
ls -lh output/news/*.db
```

---

## 第10步：防火墙与安全配置（可选）

### 10.1 开放必要端口（如果需要远程访问 Web 界面）

```bash
# 使用 ufw（Ubuntu 默认防火墙）

# 允许 SSH（通常已允许）
sudo ufw allow 22/tcp

# 如果需要访问 Web 界面（端口 8765）
sudo ufw allow 8765/tcp

# 查看防火墙状态
sudo ufw status verbose
```

### 10.2 创建专用用户运行服务（安全加固）

```bash
# 1) 创建专用用户
sudo useradd -r -s /bin/false hotspot-user

# 2) 设置目录权限
sudo chown -R hotspot-user:hotspot-user /opt/hotspot-platform

# 3) 修改 systemd 服务文件中的 User
sudo sed -i 's/User=root/User=hotspot-user/' /etc/systemd/system/hotspot-platform.service

# 4) 重载并重启服务
sudo systemctl daemon-reload
sudo systemctl restart hotspot-platform
```

---

## 🚀 快速启动命令参考卡

### 日常运维命令

```bash
# ========== 查看状态 ==========
systemctl status hotspot-platform           # 服务状态
journalctl -u hotspot-platform -f             # 实时日志
du -sh /opt/hotspot-platform/output/*        # 磁盘占用
free -h                                       # 内存使用

# ========== 服务管理 ==========
systemctl restart hotspot-platform            # 重启服务
systemctl stop hotspot-platform               # 停止服务
systemctl start hotspot-platform              # 启动服务

# ========== 手动测试 ==========
cd /opt/hotspot-platform
uv run python scripts/start_platform.py --once              # 单轮测试
uv run python -m hot_content_bridge.cli fetch-hotlist-only  # 仅热榜
uv run python -m hot_content_bridge.cli crawl-articles      # 仅爬取
uv run python -m hot_content_bridge.cli crawl-articles --limit 5  # 爬取5条

# ========== 数据库查询 ==========
TODAY=$(date +%Y-%m-%d)
sqlite3 output/news/${TODAY}.db "SELECT COUNT(*) FROM article_contents;"  # 总数
sqlite3 output/news/${TODAY}.db "SELECT url_norm,status,fetched_at FROM article_contents ORDER BY fetched_at DESC LIMIT 10;"  # 最近记录

# ========== Web 界面（可选）==========
uv run python -m hot_content_bridge.cli serve-web --host 0.0.0.0 --port 8765
# 访问 http://服务器IP:8765
```

---

## 第11步：常见问题排查

### Q1: "Command not found: uv"

```bash
# 解决方案：重新安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
which uv
```

### Q2: "ModuleNotFoundError: No module named 'xxx'"

```bash
# 解决方案：重新安装依赖
cd /opt/hotspot-platform
rm -rf .venv
uv sync

# 或者手动检查
source .venv/bin/activate
pip list | grep 缺失的模块名
```

### Q3: Chromium 启动失败 / 显示错误

```bash
# 检查 Chromium 是否安装
which chromium-browser
chromium-browser --version

# 重新安装 Playwright 浏览器
uv run playwright install chromium
uv run playwright install-deps

# 检查缺失的库
ldd $(which chromium-browser) | grep "not found"
```

### Q4: 内存不足 (OOM Killed)

```bash
# 查看内存使用
free -h

# 增加 Swap 空间（临时）
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久生效
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 降低并发数（修改 config.yaml）
# article_crawl.concurrency: 1
```

### Q5: 爬取超时或被目标网站封禁

```yaml
# 调整 config.yaml
article_crawl:
  concurrency: 1                    # 降低并发
  per_domain_min_delay_s: 3.0       # 增加延迟
  per_domain_max_delay_s: 8.0
  request_timeout_ms: 120000        # 增加超时
  max_retries: 3                    # 增加重试次数
```

### Q6: 日志文件过大导致磁盘占满

```bash
# 清理旧日志
sudo journalctl --vacuum-size=500M
sudo journalctl --vacuum-time=30days

# 或者配置日志轮转（见第8.5节）
```

### Q7: 如何更新项目代码？

```bash
cd /opt/hotspot-platform

# 停止服务
sudo systemctl stop hotspot-platform

# 更新代码（如果是 Git 仓库）
git pull origin main

# 或者重新上传文件（方式 B/C/D）

# 更新依赖
uv sync

# 重启服务
sudo systemctl start hotspot-platform

# 检查状态
sudo systemctl status hotspot-platform
```

### Q8: 数据库损坏或异常

```bash
# 备份数据库
cp output/news/$(date +%Y-%m-%d).db output/news/$(date +%Y-%m-%d).db.bak

# 尝试修复 SQLite 数据库
sqlite3 output/news/$(date +%Y-%m-%d).db "PRAGMA integrity_check;"
```

---

## ✅ 最终部署检查清单

在完成以上步骤后，逐项确认：

### 基础环境
- [ ] 操作系统为 Ubuntu 22.04+/Debian 12+
- [ ] Python 3.12 已安装（`python3.12 --version`）
- [ ] uv 已安装（`uv --version`）
- [ ] Chromium 浏览器已安装（`chromium-browser --version`）

### 项目文件
- [ ] 项目代码已上传至 `/opt/hotspot-platform`
- [ ] 关键文件存在：`pyproject.toml`, `config.yaml`, `scripts/`
- [ ] 文件权限正确（`ls -la` 无异常）

### 依赖安装
- [ ] `uv sync` 执行成功无报错
- [ ] 虚拟环境 `.venv` 已创建
- [ ] 核心模块可正常导入（Python 测试通过）

### 浏览器引擎
- [ ] Playwright Chromium 已安装（`playwright install chromium`）
- [ ] 系统依赖已安装（`playwright install-deps`）
- [ ] 浏览器启动测试通过（返回 HTTP 200）

### 配置文件
- [ ] `hotlist_interval_minutes` 已设置为期望值
- [ ] `recrawl_success: false`（开启去重）
- [ ] `crawl_after_hotlist: true`（自动爬取正文）
- [ ] 如需AI功能，API Key 已填写

### 功能测试
- [ ] 单轮测试成功：`uv run python scripts/start_platform.py --once`
- [ ] 日志显示 `Hot list: OK`
- [ ] 日志显示 `Article crawl: crawled=N skipped=M`
- [ ] 数据库文件已生成：`output/news/YYYY-MM-DD.db`
- [ ] 数据库包含有效数据：`sqlite3 ... "SELECT COUNT(*) ..."` > 0

### 长期运行
- [ ] Systemd 服务文件已创建
- [ ] 服务已启用开机自启：`systemctl is-enabled hotspot-platform` → enabled
- [ ] 服务正在运行：`systemctl is-active hotspot-platform` → active
- [ ] 可查看实时日志：`journalctl -u hotspot-platform -f`

### 监控维护（可选）
- [ ] 健康检查脚本已配置（cron 每5分钟）
- [ ] 备份脚本已配置（每天凌晨3点）
- [ ] 日志持久化已配置
- [ ] 防火墙规则已设置（如需远程访问）

---

## 📊 架构总览图

```
┌─────────────────────────────────────────────────────────────┐
│                      Linux 虚拟机                            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Systemd 服务 (开机自启 + 自动重启)                   │  │
│  │  hotspot-platform.service                             │  │
│  └─────────────────────┬───────────────────────────────┘  │
│                        │                                   │
│                        ▼                                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Pipeline Daemon (每 N 分钟循环)                     │  │
│  │                                                     │  │
│  │  ┌─────────────────┐   ┌────────────────────────┐  │  │
│  │  │ ① 获取热榜      │   │ ② 爬取正文（去重）★     │  │  │
│  │  │                 │→→│                        │  │  │
│  │  │ • 华尔街见闻    │   │ • 过滤已爬取URL        │  │  │
│  │  │ • 澎湃新闻      │   │ • 并发爬取(crawl4ai)    │  │  │
│  │  │ • 财联社        │   │ • 结果存入SQLite        │  │  │
│  │  │ • 凤凰网        │   │                        │  │  │
│  │  └─────────────────┘   └────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────┘  │
│                        │                                   │
│                        ▼                                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  数据存储层 (/opt/hotspot-platform/output/)          │  │
│  │                                                     │  │
│  │  news/                                                │  │
│  │  ├── 2026-06-12.db  ← 今日数据库                   │  │
│  │  │   ├── hotlist_items     (热榜原始数据)            │  │
│  │  │   ├── article_contents  (正文爬取结果) ★          │  │
│  │  │   │   ├── url_norm (唯一索引)                    │  │
│  │  │   │   ├── status (success/failed)               │  │
│  │  │   │   ├── markdown (正文Markdown)               │  │
│  │  │   │   └── fetched_at (时间戳)                   │  │
│  │  │   └── ai_analysis_results                       │  │
│  │  └── 2026-06-11.db  ← 历史数据                     │  │
│  │                                                     │  │
│  │  html/                                               │  │
│  │  └── index.html  ← HTML报告                         │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  监控 & 维护                                         │  │
│  │                                                     │  │
│  │  • journalctl -u hotspot-platform -f  (日志)        │  │
│  │  • health_check.sh  (健康检查, 每5分钟)             │  │
│  │  • backup.sh  (自动备份, 每天凌晨3点)                │  │
│  │  • htop / free -h  (资源监控)                       │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ (可选)
                    ┌─────────────────┐
                    │  Web 界面       │
                    │  :8765          │
                    │  (serve-web)    │
                    └─────────────────┘
```

---

## 📞 技术支持与帮助

### 关键文件位置速查

| 用途 | 路径 |
|------|------|
| **项目根目录** | `/opt/hotspot-platform` |
| **主配置文件** | `/opt/hotspot-platform/hot_content_bridge/config.yaml` |
| **TrendRadar配置** | `/opt/hotspot-platform/trendRadar/config/config.yaml` |
| **时间调度配置** | `/opt/hotspot-platform/trendRadar/config/timeline.yaml` |
| **数据存储目录** | `/opt/hotspot-platform/output/` |
| **今日数据库** | `/opt/hotspot-platform/output/news/$(date +%Y-%m-%d).db` |
| **Systemd服务** | `/etc/systemd/system/hotspot-platform.service` |
| **日志文件** | `journalctl -u hotspot-platform` |
| **健康检查脚本** | `/opt/hotspot-platform/scripts/health_check.sh` |
| **备份脚本** | `/opt/hotspot-platform/scripts/backup.sh` |

### 常用命令速查

```bash
# 一键查看整体状态
echo "=== 服务状态 ===" && systemctl is-active hotspot-platform && \
echo "=== 最近日志 ===" && journalctl -u hotspot-platform -n 5 --no-pager && \
echo "=== 磁盘使用 ===" && du -sh /opt/hotspot-platform/output/ && \
echo "=== 内存使用 ===" && free -h | head -2 && \
echo "=== 今日数据库 ===" && ls -lh /opt/hotspot-platform/output/news/$(date +%Y-%m-%d).db 2>/dev/null || echo "今日暂无数据库"
```

---

## 🎉 恭喜！

如果你完成了以上所有步骤，特别是 **第7步的单轮测试** 和 **第8步的Systemd配置**，那么你的热点发现平台已经：

✅ **自动运行**：每 N 分钟自动获取热榜并爬取正文（N由你配置决定）  
✅ **智能去重**：已爬取过的URL不会重复爬取  
✅ **长期稳定**：开机自启 + 崩溃自动重启  
✅ **可监控**：完善的日志系统和健康检查  

**现在你可以安心让它长期运行了！**

---

**文档版本**：v2.0 (完整从零部署版)
**最后更新**：2026-06-12
**适用场景**：全新Linux虚机，从零开始部署
**预计部署时间**：30-60分钟
