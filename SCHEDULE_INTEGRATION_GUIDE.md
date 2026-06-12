# TrendRadar 热榜获取与正文爬取联动机制说明

> **核心问题**：如何让正文爬取的时机完全跟随 TrendRadar 的热榜获取时机？

---

## 📊 一、当前架构的两套时间控制系统

### 架构总览图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Systemd / 手动启动                           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│              hot_content_bridge (Bridge Daemon)                      │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  定时器 A：hotlist_interval_minutes = 30 (分钟)              │    │
│  │                                                              │    │
│  │  ⏰ 每 30 分钟自动触发一次                                    │    │
│  └──────────────────────┬──────────────────────────────────────┘    │
│                         │                                           │
│                         ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  步骤 1：热榜获取                                            │    │
│  │  ─────────────────                                          │    │
│  │  if full_trendradar_sync == false (默认):                    │    │
│  │      → fetch_hotlist_only()  ← 快速API，不受timeline控制      │    │
│  │                                                                │    │
│  │  if full_trendradar_sync == true:                             │    │
│  │      → run_trendradar_full_sync()  ← 完整流程，受timeline控制  │    │
│  └──────────────────────┬──────────────────────────────────────┘    │
│                         │                                           │
│                         ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  步骤 2：正文爬取 (如果 crawl_after_hotlist == true)          │    │
│  │  ─────────────────────────────────────────                   │    │
│  │  run_crawl_step():                                          │    │
│  │      ① load_pending_from_latest_crawl()  读取最新热榜        │    │
│  │      ② filter_pending_for_crawl()     过滤已爬取URL ★       │    │
│  │      ③ crawl_pending_batch()         爬取未处理正文          │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                           │
                           ▼ (如果 full_trendradar_sync == true)
┌─────────────────────────────────────────────────────────────────────┐
│                    TrendRadar 主程序                                 │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  定时器 B：Scheduler (timeline.yaml)                        │    │
│  │                                                              │    │
│  │  基于 timeline.yaml 的时间段配置决定：                        │    │
│  │    • collect: 是否采集数据                                   │    │
│  │    • analyze: 是否AI分析                                     │    │
│  │    • push:    是否推送通知                                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### 关键发现：两套系统是**松耦合**的

| 特性 | Bridge Daemon | TrendRadar Scheduler |
|------|--------------|---------------------|
| **控制文件** | `hot_content_bridge/config.yaml` | `trendRadar/config/timeline.yaml` |
| **时间间隔** | `hotlist_interval_minutes: 30` | 由时间段(periods)定义 |
| **默认模式** | ✅ 独立运行（快速API） | ❌ 不被调用 |
| **联动模式** | `full_trendradar_sync: true` | 作为子进程被调用 |
| **控制粒度** | 固定间隔轮询 | 灵活时间段+行为开关 |

---

## 🔍 二、当前实现的3种运行模式

### 模式 1：快速热榜模式（默认）⚡️

```yaml
# hot_content_bridge/config.yaml
pipeline_daemon:
  full_trendradar_sync: false   # ← 默认值
  hotlist_interval_minutes: 30  # ← 每30分钟
```

**执行流程**：
```
时间轴:  0min    30min    60min    90min
          │       │       │       │
          ▼       ▼       ▼       ▼
        [热榜]  [热榜]   [热榜]   [热榜]   ← 每次都执行（无时间限制）
          │       │       │       │
          ▼       ▼       ▼       ▼
        [爬取]  [爬取]   [爬取]   [爬取]   ← 紧跟热榜（有去重）
```

**特点**：
- ✅ **简单高效**：每30分钟固定执行
- ✅ **不受timeline约束**：任何时间都可获取热榜
- ❌ **无法按时间段控制**：凌晨3点也会爬取（可能打扰目标网站）

---

### 模式 2：完整TrendRadar同步模式 🔄

```yaml
# hot_content_bridge/config.yaml
pipeline_daemon:
  full_trendradar_sync: true    # ← 改为true
  hotlist_interval_minutes: 30  # ← 轮询间隔
```

**执行流程**：
```
时间轴:  0min              30min             60min
          │                 │                │
          ▼                 ▼                ▼
    ┌─────────────┐   ┌─────────────┐  ┌─────────────┐
    │ 触发trendradar│   │ 触发trendradar│  │ 触发trendradar│
    └──────┬───────┘   └──────┬───────┘  └──────┬───────┘
           │                  │                 │
           ▼                  ▼                 ▼
    ┌─────────────┐   ┌─────────────┐  ┌─────────────┐
    │ Timeline判断 │   │ Timeline判断 │  │ Timeline判断 │
    │ collect?     │   │ collect?     │  │ collect?     │
    └──────┬───────┘   └──────┬───────┘  └──────┬───────┘
           │                  │                 │
     ┌─────┴─────┐      ┌─────┴─────┐      ┌─────┴─────┐
     │Yes: 采集   │      │No: 跳过   │      │Yes: 采集   │
     │No:  不采集 │      │(静默期)   │      │No:  不采集 │
     └─────┬─────┘      └─────┬─────┘      └─────┬─────┘
           │                  │                 │
           ▼                  ▼                 ▼
     [正文爬取★]            [跳过]           [正文爬取★]
```

**特点**：
- ✅ **受timeline控制**：只在允许的时间段采集
- ✅ **智能调度**：静默期只积累数据，不浪费资源
- ⚠️ **注意**：正文爬取**始终**在trendradar完成后立即执行（如果 `crawl_after_hotlist: true`）

---

### 模式 3：手动单次执行 🎯

```bash
# 测试或调试用
uv run python scripts/start_platform.py --once                    # 快速模式
uv run python scripts/start_platform.py --once --full             # 完整模式
uv run python -m hot_content_bridge.cli crawl-articles --limit 5  # 仅爬取
```

---

## 三、如何实现"热榜获取→正文爬取"的完全联动

### 方案 A：使用完整同步模式（推荐）⭐⭐⭐

#### 适用场景
- 希望完全遵循 TrendRadar 的时间段配置
- 避免在非工作时间爬取（减少被封风险）
- 需要AI分析、推送等完整功能

#### 配置步骤

**Step 1**: 修改 bridge 配置

编辑 `hot_content_bridge/config.yaml`：

```yaml
pipeline_daemon:
  enabled: true
  run_on_startup: true
  hotlist_interval_minutes: 30        # 轮询检查间隔（分钟）
  initial_delay_seconds: 5
  full_trendradar_sync: true         # ⭐ 关键改动：启用完整同步
  crawl_after_hotlist: true          # 热榜完成后自动爬取正文
  crawl_limit_per_run: 0
```

**Step 2**: 配置 TrendRadar 时间表

编辑 `trendRadar/config/timeline.yaml`：

```yaml
# 示例：工作日8-22点采集，周末10-23点采集
schedule:
  preset: "custom"  # 或选择预设模板

custom:
  default:
    collect: true              # 默认：允许采集（静默期也采集数据）
    analyze: false
    push: false
    report_mode: "current"

  periods:
    work_hours:
      name: "工作时间"
      start: "08:00"
      end: "22:00"
      collect: true            # 工作时间内采集
      push: true               # 并推送通知
      report_mode: "current"
    weekend_hours:
      name: "周末时间"
      start: "10:00"
      end: "23:00"
      collect: true
      push: true
      report_mode: "daily"     # 周末做全天汇总

  day_plans:
    weekday:
      periods: ["work_hours"]
    weekend:
      periods: ["weekend_hours"]

  week_map:
    1: "weekday"
    2: "weekday"
    3: "weekday"
    4: "weekday"
    5: "weekday"
    6: "weekend"
    7: "weekend"
```

**Step 3**: 启动服务

```bash
# 使用 Systemd 或直接启动
uv run python scripts/start_platform.py
# 或
uv run python -m hot_content_bridge.cli daemon --full-sync
```

#### 工作原理

```
Bridge Daemon 每30分钟轮询
         │
         ▼
   ┌──────────────┐
   │ 检查时间     │
   └──────┬───────┘
          │
          ▼
   ┌─────────────────────────────────────┐
   │ 调用 python -m trendradar (完整流程) │
   │                                     │
   │ ① TrendRadar 读取 timeline.yaml      │
   │ ② 判断当前时间是否在允许的时间段内    │
   │ ③ 如果 collect=true:                │
   │    → 爬取热榜平台 + RSS             │
   │    → 存入 SQLite 数据库             │
   │ ④ 如果 analyze=true:                │
   │    → AI 分析 + 筛选                 │
   │ ⑤ 如果 push=true:                  │
   │    → 推送通知到各渠道               │
   └──────────────┬──────────────────────┘
                  │
                  ▼ (trendradar完成后)
   ┌─────────────────────────────────────┐
   │ Bridge Daemon 继续执行               │
   │                                     │
   │ if crawl_after_hotlist == true:     │
   │   → 从数据库读取最新热榜条目         │
   │   → 过滤已成功爬取的URL (去重) ★    │
   │   → 爬取未处理的正文                 │
   │   → 结果持久化                       │
   └─────────────────────────────────────┘
```

#### 时间间隔调整方法

**调整 Bridge 轮询频率**：

```yaml
# hot_content_bridge/config.yaml
pipeline_daemon:
  hotlist_interval_minutes: 15   # 改为15分钟（更频繁检查）
  # 或
  hotlist_interval_minutes: 60   # 改为60分钟（更节省资源）
```

**调整 TrendRadar 采集时间窗口**：

```yaml
# trendRadar/config/timeline.yaml
custom:
  periods:
    morning:
      start: "07:00"    # 提前到7点开始
      end: "09:00"
    evening:
      start: "19:00"    # 推迟到19点开始
      end: "23:00"      # 延长到23点结束
```

---

### 方案 B：保持快速模式 + 自定义时间过滤（轻量级）⭐⭐

#### 适用场景
- 不需要AI分析和推送功能
- 只关心热榜获取和正文爬取
- 希望简单可控

#### 实现思路

修改 `daemon.py` 或 `pipeline_runner.py`，添加自定义时间判断逻辑。

**示例代码**（在 `pipeline_runner.py` 中添加时间过滤）：

```python
import datetime

def _should_run_now(cfg: BridgeConfig) -> bool:
    """判断当前时间是否允许执行"""
    now = datetime.datetime.now(datetime.timezone.utc)
    hour = now.hour
    
    # 示例：只在工作时间8-23点执行
    work_start = cfg.pipeline_daemon.get("work_hour_start", 8)
    work_end = cfg.pipeline_daemon.get("work_hour_end", 23)
    
    return work_start <= hour < work_end


def run_pipeline_once(cfg, **kwargs):
    # 添加时间过滤
    if not _should_run_now(cfg):
        logger.info("当前时间不在允许的工作时段内，跳过本次执行")
        return PipelineRunResult(
            hotlist_ran=False,
            hotlist_error=None,
            crawl_urls=0,
            crawl_skipped=0,
            crawl_error=None,
        )
    
    # ...原有逻辑...
```

**配置扩展**：

```yaml
# hot_content_bridge/config.yaml
pipeline_daemon:
  enabled: true
  run_on_startup: true
  hotlist_interval_minutes: 30
  full_trendradar_sync: false  # 保持快速模式
  
  # 新增：自定义时间窗口
  work_hour_start: 8           # 开始时间（小时，24小时制）
  work_hour_end: 23            # 结束时间（小时）
  
  crawl_after_hotlist: true
```

---

### 方案 C：外部Cron调度（最灵活）⭐⭐⭐

#### 适用场景
- 已有成熟的运维体系（如 Jenkins、Airflow）
- 需要与其他任务协调
- 希望完全掌控执行时机

#### 实现方式

**Step 1**: 禁用 Bridge 内置定时器

```yaml
# hot_content_bridge/config.yaml
pipeline_daemon:
  enabled: false   # 禁用内置daemon
```

**Step 2**: 创建 Cron 任务

```bash
# 编辑 crontab
crontab -e

# 格式: 分钟 小时 日 月 星期 命令
# 示例1：工作日每小时执行一次（8-23点）
0 8-23 * * 1-5 cd /opt/hotspot-platform && uv run python scripts/start_platform.py --once >> /var/log/hotspot.log 2>&1

# 示例2：每天早晚各一次（9点和21点）
0 9,21 * * * cd /opt/hotspot-platform && uv run python scripts/start_platform.py --once --full >> /var/log/hotspot.log 2>&1

# 示例3：每30分钟执行（全天候）
*/30 * * * * cd /opt/hotspot-platform && uv run python scripts/start_platform.py --once >> /var/log/hotspot.log 2>&1
```

**Step 3**: 使用 Systemd Timer（替代Cron，更可靠）

创建 `/etc/systemd/system/hotspot-platform.timer`：

```ini
[Unit]
Description=HotSpot Platform Schedule Timer
After=network.target

[Timer]
# 工作日每小时执行
OnCalendar=Mon-Fri *-*-* 08-23:00:00
# 或精确时间
# OnCalendar=*-*-* 09,21:00:00

[Install]
WantedBy=timers.target
```

创建 `/etc/systemd/system/hotspot-platform.service`：

```ini
[Unit]
Description=HotSpot Platform Pipeline
After=network.target

[Service]
Type=oneshot
User=root
WorkingDirectory=/opt/hotspot-platform
Environment="PYTHONUTF8=1"
ExecStart=/opt/hotspot-platform/.venv/bin/python scripts/start_platform.py --once
```

启用 Timer：

```bash
sudo systemctl enable hotspot-platform.timer
sudo systemctl start hotspot-platform.timer

# 查看下次执行时间
sudo systemctl list-timers hotspot-platform.timer
```

---

## 四、时间间隔调整速查表

### 场景推荐配置

| 使用场景 | 推荐方案 | 热榜间隔 | 正文爬取 | 说明 |
|---------|---------|---------|---------|------|
| **开发测试** | 单次手动 | - | 按需 | `--once --limit 5` |
| **轻度使用** | 快速模式 | 60分钟 | 自动跟随 | 节省资源，每日24次 |
| **常规运营** | 完整同步 | 30分钟 | 自动跟随 | 平衡实时性与负载 |
| **重度监控** | 完整同步 | 15分钟 | 自动跟随 | 高频更新，适合舆情监控 |
| **企业部署** | 外部Cron | 自定义 | 自动跟随 | 与业务系统协调 |

### 性能影响参考值

| 间隔 | 日执行次数 | 预估CPU占用 | 内存占用 | 网络请求 |
|------|----------|------------|---------|---------|
| 15分钟 | 96次 | 5-10% | 500MB-1GB | ~2000次/天 |
| 30分钟 | 48次 | 3-5% | 300-500MB | ~1000次/天 |
| 60分钟 | 24次 | 1-3% | 200-300MB | ~500次/天 |
| 2小时 | 12次 | <1% | 100-200MB | ~250次/天 |

> **注**：以上数值基于典型配置（5个平台，每个平台50条热榜），实际值取决于平台数量和文章数量。

---

## 五、验证联动效果的方法

### 1. 查看日志确认执行顺序

```bash
# 实时查看日志
sudo journalctl -u hotspot-platform -f

# 或查看日志文件
tail -f /var/log/hotspot-platform.log
```

**期望输出示例**：

```
2026-06-12 08:00:05 [INFO] Pipeline cycle start (2026-06-12 08:00:05)
2026-06-12 08:00:06 [INFO] Running full trendradar: cwd=/opt/hotspot-platform python -m trendradar
2026-06-12 08:00:07 [调度] 星期三，日计划: weekday
2026-06-12 08:00:07 [调度] 当前时间段: 工作时间 (08:00-22:00)
2026-06-12 08:00:07 [调度] 行为: 采集, 推送(模式:current)
2026-06-12 08:00:15 [INFO] 开始爬取数据，请求间隔 2000 毫秒
2026-06-12 08:01:30 [INFO] 数据已保存到存储后端: sqlite
2026-06-12 08:01:31 [推送] 准备发送：热榜 42 条，合计 42 条
2026-06-12 08:01:45 [INFO] Hot list: OK
2026-06-12 08:01:46 [INFO] Crawling 38 URLs (pending=42, skipped=4)  ← 4个已爬取被跳过★
2026-06-12 08:03:20 [INFO] Article crawl: crawled=35 skipped=4
2026-06-12 08:03:20 [INFO] Pipeline cycle end
```

**关键字段解读**：
- `[调度] 行为: 采集` → TrendRadar 决定执行热榜获取
- `skipped=4` → 正文爬取时发现4个URL已经成功爬取过（去重生效）★
- `crawled=35` → 本次新爬取了35个正文

### 2. 检查数据库确认去重效果

```bash
# 连接今日数据库
sqlite3 output/news/$(date +%Y-%m-%d).db

# 查看爬取统计
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success,
    SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
    MIN(fetched_at) as first_crawl,
    MAX(fetched_at) as last_crawl
FROM article_contents;

# 查看最近10次爬取记录
SELECT url_norm, status, fetched_at 
FROM article_contents 
ORDER BY fetched_at DESC 
LIMIT 10;

# 查看哪些URL被重复爬取过（应该很少或没有）
SELECT url_norm, COUNT(*) as times 
FROM article_contents 
GROUP BY url_norm 
HAVING times > 1 
ORDER BY times DESC;
```

### 3. 监控时间线是否符合预期

```bash
# 查看 TrendRadar 调度状态
cd /opt/hotspot-platform/trendRadar
uv run python -m trendradar --show-schedule

# 输出示例：
# ============================================================
# TrendRadar v2.2.0 调度状态
# ============================================================
#
# ⏰ 当前时间: 2026-06-12 14:30:00 (Asia/Shanghai)
# 📅 当前日期: 2026-06-12
#
# 📋 调度信息:
#   日计划: weekday
#   当前时间段: 工作时间 (08:00-22:00)
#
# 🔧 行为开关:
#   采集数据: ✅ 是
#   AI 分析:  ❌ 否
#   推送通知: ✅ 是
#   报告模式: current
#   AI 模式:  current
```

---

## 六、常见问题排查

### Q1: 为什么设置了timeline但还是在凌晨爬取？

**原因**：使用了快速模式（`full_trendradar_sync: false`），绕过了timeline

**解决**：
```yaml
# 改为完整同步模式
pipeline_daemon:
  full_trendradar_sync: true
```

### Q2: 为什么有些URL重复爬取了？

**可能原因**：
1. `recrawl_success: true`（强制重新爬取）
2. URL规范化不一致导致识别为新URL
3. 数据库路径错误（读取了错误的日期库）

**排查命令**：
```bash
# 检查配置
grep "recrawl_success" hot_content_bridge/config.yaml

# 检查数据库路径
ls -la output/news/
```

### Q3: 如何临时跳过某次正文爬取？

**方法 1**：设置环境变量
```bash
export CRAWL_AFTER_HOTLIST=false
uv run python scripts/start_platform.py --once
```

**方法 2**：修改配置后重启
```yaml
crawl_after_hotlist: false  # 临时关闭
```

### Q4: 如何只爬取特定平台的正文？

```bash
# 只爬取澎湃新闻的热榜
uv run python -m hot_content_bridge.cli fetch-hotlist-only --platform thepaper
uv run python -m hot_content_bridge.cli crawl-articles
```

---

## 七、推荐的生产环境配置模板

### 模板 1：稳健型（适合长期运行）

```yaml
# hot_content_bridge/config.yaml
pipeline_daemon:
  enabled: true
  run_on_startup: true
  hotlist_interval_minutes: 30
  initial_delay_seconds: 30
  full_trendradar_sync: true          # 使用完整同步
  crawl_after_hotlist: true
  crawl_limit_per_run: 0

article_crawl:
  concurrency: 2                     # 保守并发
  max_retries: 2
  recrawl_success: false             # 开启去重
  per_domain_min_delay_s: 2.0        # 增加延迟防封
  per_domain_max_delay_s: 5.0
```

```yaml
# trendRadar/config/timeline.yaml (简化版)
schedule:
  preset: "morning_evening"          # 使用预设模板
```

### 模板 2：激进型（高频监控）

```yaml
# hot_content_bridge/config.yaml
pipeline_daemon:
  enabled: true
  run_on_startup: true
  hotlist_interval_minutes: 15        # 更频繁
  initial_delay_seconds: 5
  full_trendradar_sync: true
  crawl_after_hotlist: true
  crawl_limit_per_run: 100            # 限制每轮数量

article_crawl:
  concurrency: 4                     # 更高并发
  max_retries: 3                     # 更多重试
  request_timeout_ms: 90000          # 更长超时
  recrawl_success: false
```

### 模板 3：经济型（节省资源）

```yaml
# hot_content_bridge/config.yaml
pipeline_daemon:
  enabled: true
  run_on_startup: true
  hotlist_interval_minutes: 60        # 降低频率
  initial_delay_seconds: 60
  full_trendradar_sync: false        # 使用快速模式（省资源）
  crawl_after_hotlist: true
  crawl_limit_per_run: 20            # 限制数量

article_crawl:
  concurrency: 1                     # 串行爬取（最稳）
  max_retries: 1
  recrawl_success: false
```

---

## 八、总结与建议

### 核心结论

✅ **项目已基本实现"热榜获取→正文爬取"的联动机制**，具体表现为：

1. **去重机制完善**：通过 SQLite 记录每个URL的爬取状态，自动跳过已成功的URL
2. **两种同步模式可选**：
   - 快速模式（默认）：独立定时，简单高效
   - 完整同步模式：受timeline控制，智能调度
3. **正文爬取紧跟热榜**：`crawl_after_hotlist: true` 保证热榜获取后立即触发正文爬取

### 最佳实践建议

对于你的需求（**由TrendRadar时间逻辑控制正文爬取**），推荐：

```bash
# 1. 启用完整同步模式
# 编辑 hot_content_bridge/config.yaml
pipeline_daemon:
  full_trendradar_sync: true
  hotlist_interval_minutes: 30   # 根据需要调整（15-60分钟）

# 2. 配置合适的时间窗口
# 编辑 trendRadar/config/timeline.yaml
# 选择预设模板或自定义时间段

# 3. 启动并观察日志
uv run python scripts/start_platform.py
journalctl -u hotspot-platform -f

# 4. 验证去重效果
sqlite3 output/news/$(date +%Y-%m-%d).db \
  "SELECT COUNT(*), SUM(status='success') FROM article_contents;"
```

### 时间间隔调整原则

- **越短（≤15分钟）**：实时性高，但增加服务器负载和被封风险
- **适中（30-60分钟）**：平衡性能和时效性，**推荐生产环境使用**
- **较长（≥2小时）**：节省资源，适合低频更新的场景

---

**文档版本**：v1.1
**最后更新**：2026-06-12
**适用版本**：Cur-test - v3 (热点发现平台)
