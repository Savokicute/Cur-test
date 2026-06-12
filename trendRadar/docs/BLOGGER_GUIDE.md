# 博主与微信公众号集成指南

## 📋 目录
1. [快速开始（推荐方式）](#-快速开始推荐方式)
2. [方式一：通过 RSS（最简单 ✅）](#-方式一通过-最简单)
3. [方式二：自定义爬虫模块（进阶）](#-方式二自定义爬虫模块进阶)
4. [配置示例](#-配置示例)
5. [常见问题](#-常见问题)

---

## 🚀 快速开始（推荐方式）

**最简单的方式是使用 RSS 源！** 大多数博主、公众号、平台都提供 RSS 订阅。

### 步骤 1: 配置 RSS 源

编辑 `config/config.yaml`，在 `rss` 部分添加：

```yaml
rss:
  enabled: true
  freshness_filter:
    enabled: true
    max_age_days: 7
  feeds:
    # GitHub 用户
    - id: "github-sansan0"
      name: "sansan0 的 GitHub"
      url: "https://github.com/sansan0.atom"
    
    # 微信公众号（通过 RSSHub）
    - id: "wechat-tech"
      name: "科技公众号"
      url: "https://rsshub.app/wechat/mp/profile/your_id_here"
    
    # 知乎作者
    - id: "zhihu-author"
      name: "知乎作者"
      url: "https://rsshub.app/zhihu/people/xxx/activities"
    
    # 掘金作者
    - id: "juejin-author"
      name: "掘金作者"
      url: "https://rsshub.app/juejin/user/xxx"
```

### 步骤 2: 部署或使用公共 RSSHub

微信公众号需要 RSSHub 服务：

| 选项 | 说明 |
|-----|------|
| **公共实例** | https://rsshub.app/ (但可能不稳定) |
| **自己部署** | https://docs.rsshub.app/deploy/ (推荐) |
| **其他服务** | https://feeddd.org/, https://werss.app/ |

### 步骤 3: 运行程序

```bash
python -m trendradar
```

就这么简单！不需要修改任何代码！

---

## 📡 方式一：通过 RSS（最简单 ✅）

### 1.1 GitHub 用户

**URL 格式**: `https://github.com/{username}.atom`

```yaml
- id: "github-sansan0"
  name: "sansan0 的 GitHub"
  url: "https://github.com/sansan0.atom"
```

### 1.2 知乎

**URL 格式** (RSSHub):
- 用户: `https://rsshub.app/zhihu/people/{user_id}/activities`
- 专栏: `https://rsshub.app/zhihu/zhuanlan/{id}`
- 热榜: `https://rsshub.app/zhihu/hot`

### 1.3 微信公众号

需要 RSSHub:
1. 在微信中打开公众号文章
2. 复制公众号的微信号或 id
3. 构造 RSSHub URL: `https://rsshub.app/wechat/mp/profile/{id}`

```yaml
- id: "wechat-tech"
  name: "科技公众号"
  url: "https://rsshub.app/wechat/mp/profile/your_id_here"
```

### 1.4 掘金

**URL 格式** (RSSHub):
- 用户: `https://rsshub.app/juejin/user/{user_id}`
- 热榜: `https://rsshub.app/juejin/hot`

### 1.5 CSDN

**URL 格式** (RSSHub):
- 博客: `https://rsshub.app/csdn/blog/{username}`

### 1.6 独立博客

大多数博客都有 RSS 订阅，通常在网站上找：
- RSS 图标
- "订阅" 链接
- `/feed` 或 `/rss` 路径

---

## 🔧 方式二：自定义爬虫模块（进阶）

如果你需要爬取不提供 RSS 的博主，可以使用自定义爬虫模块。

### 2.1 已创建的文件

本项目已为你创建了示例文件：
- `trendradar/crawler/blogger.py` - 博主爬虫模块
- `config/blogger_example.yaml` - 配置示例

### 2.2 集成到主程序（可选）

如果你想完全集成到 TrendRadar，需要修改几个文件：

#### 步骤 1: 修改存储数据模型

编辑 `trendradar/storage/base.py`，添加博主数据模型：

```python
# 在 NewsData 和 RSSData 之后添加
@dataclass
class BloggerData:
    date: str
    crawl_time: str
    items: Dict[str, List[Dict]]
    id_to_name: Dict[str, str]
    failed_ids: List[str]
```

#### 步骤 2: 添加入口点

编辑 `trendradar/__main__.py`，在 `_crawl_rss_data()` 之后添加：

```python
def _crawl_blogger_data(self):
    """抓取博主数据（可选）"""
    # 检查是否启用
    bloggers_config = self.ctx.config.get("BLOGGERS", {})
    if not bloggers_config.get("ENABLED", False):
        return None
    
    try:
        from trendradar.crawler.blogger import BloggerFetcher, BloggerConfig
        
        # 构建配置
        bloggers = []
        for config in bloggers_config.get("FEEDS", []):
            b = BloggerConfig(
                id=config.get("id", ""),
                name=config.get("name", ""),
                url=config.get("url", ""),
                type=config.get("type", "rss"),
                max_articles=config.get("max_articles", 50),
            )
            if b.id and b.url:
                bloggers.append(b)
        
        if not bloggers:
            print("[Blogger] 没有配置博主")
            return None
        
        # 抓取数据
        fetcher = BloggerFetcher(bloggers=bloggers)
        blogger_data = fetcher.fetch_all()
        
        # 这里可以添加存储逻辑
        print(f"[Blogger] 抓取完成: {len(blogger_data['items'])} 个博主")
        return blogger_data
        
    except Exception as e:
        print(f"[Blogger] 抓取失败: {e}")
        return None
```

#### 步骤 3: 在 run() 中调用

修改 `NewsAnalyzer.run()` 方法：

```python
def run(self):
    # ... 原有的热榜和 RSS 爬取代码 ...
    
    # 添加博主抓取调用
    blogger_data = self._crawl_blogger_data()
    
    # ... 后续分析和推送代码 ...
```

---

## 📝 配置示例

### 完整的 RSS 配置

编辑 `config/config.yaml`:

```yaml
rss:
  enabled: true
  freshness_filter:
    enabled: true
    max_age_days: 7
  request_interval: 2000
  timeout: 15
  feeds:
    # ==================== GitHub ====================
    - id: "github-sansan0"
      name: "sansan0 的 GitHub"
      url: "https://github.com/sansan0.atom"
      max_items: 20
    
    # ==================== 知乎 ====================
    - id: "zhihu-hot"
      name: "知乎热榜"
      url: "https://rsshub.app/zhihu/hot"
      max_items: 30
    
    - id: "zhihu-zhuanlan"
      name: "知乎某专栏"
      url: "https://rsshub.app/zhihu/zhuanlan/xxx"
      max_items: 15
    
    # ==================== 掘金 ====================
    - id: "juejin-hot"
      name: "掘金热榜"
      url: "https://rsshub.app/juejin/hot"
      max_items: 30
    
    # ==================== 微信公众号 ====================
    - id: "wechat-tech"
      name: "科技公众号"
      url: "https://rsshub.app/wechat/mp/profile/xxx"
      max_items: 10
    
    # ==================== 技术博客 ====================
    - id: "coolshell"
      name: "酷壳 - 陈皓"
      url: "https://coolshell.cn/feed"
      max_items: 20
    
    - id: "ruanyifeng"
      name: "阮一峰的网络日志"
      url: "https://www.ruanyifeng.com/blog/atom.xml"
      max_items: 10
    
    - id: "bytedance"
      name: "字节跳动技术博客"
      url: "https://juejin.cn/team/5538843675948837/rss"
      max_items: 15
```

### 关键词筛选配置

编辑 `config/frequency_words.txt`:

```ini
[AI人工智能]
AI
人工智能
大模型
/.*大语言模型.*/
GPT
LLM

[技术]
Python
/.*Python.*/
Java
JavaScript
前端
后端
架构

[投资]
股票
基金
投资
/.*A股.*/

[GLOBAL_FILTER]
!广告
!推广
!点击链接
!限时优惠
```

---

## ❓ 常见问题

### Q1: RSSHub 稳定吗？

**A**: 公共实例可能不稳定，建议自己部署：
- Docker: `docker run -d -p 1200:1200 diygod/rsshub`
- 完整文档: https://docs.rsshub.app/deploy/

### Q2: 微信公众号没有 RSS 怎么办？

**A**: 
1. 尝试 RSSHub (大多数公众号可通过 RSSHub 爬取)
2. 使用 FeedDD (https://feeddd.org/)
3. 使用 WeRSS (https://werss.app/)

### Q3: 可以自定义爬虫吗？

**A**: 可以！参考 `trendradar/crawler/blogger.py` 中的示例，你可以：
- 继承现有的类
- 实现自己的 `_fetch_custom()` 方法
- 在 `BloggerFetcher` 中注册新类型

### Q4: 博主数据会保存到数据库吗？

**A**: 
- 方式一（RSS）: 已集成，保存在 RSS 数据库中
- 方式二（自定义）: 需要自己实现存储逻辑

### Q5: 可以同时爬取多个博主吗？

**A**: 可以！配置多个 RSS 源即可，程序会自动处理。

### Q6: 博主文章会和热榜数据一起推送吗？

**A**: 是的！RSS 数据已经集成到推送流程中。

### Q7: 可以添加更多平台吗？

**A**: 可以！建议：
1. 先尝试找到该平台的 RSS 源
2. 如果没有，查看 RSSHub 是否支持
3. 如果都没有，再写自定义爬虫

---

## 📚 参考资源

| 资源 | 链接 |
|-----|------|
| **RSSHub 文档** | https://docs.rsshub.app/ |
| **RSSHub 支持的网站** | https://rsshub.app/ |
| **Awesome RSS Feeds** | https://github.com/plenaryapp/awesome-rss-feeds |
| **Blogtrottr** | https://blogtrottr.com/ (RSS 转邮件) |

---

## 🎯 快速配置检查清单

在 `config.yaml` 中：

- [ ] `rss.enabled: true`
- [ ] 添加了你的 RSS 源列表
- [ ] `platforms.enabled: true` (需要热榜的话)
- [ ] 配置了通知渠道（飞书/钉钉等）
- [ ] 配置了关键词筛选（`frequency_words.txt`）

运行测试：
```bash
python -m trendradar
```

---

## 💡 最佳实践

1. **优先用 RSS**: RSS 是最稳定和官方的方式
2. **自己部署 RSSHub**: 避免公共实例不稳定
3. **合理设置 `max_age_days`**: 避免重复推送旧文章
4. **设置 `request_interval`**: 避免请求过快被封禁
5. **用关键词筛选**: 只推送你真正关心的内容
6. **定期检查配置**: RSS 源 URL 可能会变化

---

## 🆘 需要帮助？

如果遇到问题：
1. 查看日志输出
2. 确认 RSS 源 URL 是否可以访问
3. 检查网络连接
4. 查看 Issue: https://github.com/sansan0/TrendRadar/issues

