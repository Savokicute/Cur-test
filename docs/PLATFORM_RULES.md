# 热榜平台正文过滤规则

`hot_content_bridge` 为每个热榜平台维护一份独立规则文件，用于：

1. **爬取阶段**（crawl4ai）：正文 CSS 范围、额外排除选择器、是否启用 `target_elements`
2. **Markdown 后处理**：去掉导航标签、站点页脚等噪声行

规则目录：[`hot_content_bridge/platform_rules/`](../hot_content_bridge/platform_rules/)

---

## 爬取「全部」热榜文章

需同时满足：

| 项 | 说明 |
|----|------|
| `article_crawl.max_urls_per_run: 0` | 在 [`hot_content_bridge/config.yaml`](../hot_content_bridge/config.yaml) 中，`0` 表示不按条数截断热榜 URL |
| CLI `--limit 0` | 默认值；不额外限制本次任务条数 |

**推荐命令（先热榜、再正文、不截断）：**

```powershell
cd d:\chao-TrendRadar\Cur-test
uv sync
uv run playwright install chromium

# 1. 仅抓取热榜写入 SQLite（快，无 AI）
uv run hot-content-bridge fetch-hotlist-only

# 2. 爬取最新批次中的全部正文
uv run hot-content-bridge crawl-articles --limit 0

# 或一步：热榜 + 全部正文
uv run hot-content-bridge run-pipeline --quick-hotlist --limit 0

# 3. 浏览器查看
uv run hot-content-bridge serve-web --port 8765
```

说明：

- 已在 `article_contents` 中且 `status=success` 的 URL，默认会跳过；若要全部重爬，在 `config.yaml` 设置 `recrawl_success: true`。
- 正文爬取较慢，条数多时请适当调大 `request_timeout_ms`、域限速参数。
- trendRadar 里**未启用**的平台不会出现在热榜批次中，对应规则文件可提前写好，启用后即生效。

---

## 规则文件格式

示例：[`thepaper.yaml`](../hot_content_bridge/platform_rules/thepaper.yaml)

```yaml
platform_id: thepaper          # 必须与 trendRadar platforms.sources[].id 一致
display_name: 澎湃新闻
enabled: true

hosts:                         # 文章落地页域名（用于无 platform_id 时的兜底匹配）
  - thepaper.cn

crawl:
  primary_target: ".newscontent"   # 单一正文容器，避免多 selector 重复/截断
  content_filter: none             # 关闭 BM25，保留完整正文
  prefer_raw_markdown: true
  use_target_elements: true
  delay_before_return_html: 0.85
  excluded_selector_extra: >-      # 追加到全局 excluded_selector
    header,footer,[class*='nav']

markdown_post:
  dedupe_paragraphs: true          # 华尔街见闻等重复段落
  normalize_markdown: true         # 标题/段落/列表/图片格式规范化
  prepend_hot_summary: true        # 将 API 摘要置于文首
  nav_labels:                  # 额外当作导航噪声的标签
    - 要闻
    - 深度
  drop_line_patterns:          # 行内包含即删除（正则转义后 OR 匹配）
    - "互联网新闻信息服务许可证"
    - "东方报业"
```

`_default.yaml`：任意未单独配置的平台使用；文件名以 `_` 开头，**不是**平台 ID。

---

## 新平台接入步骤

1. **在 trendRadar 启用平台**  
   编辑 [`trendRadar/config/config.yaml`](../trendRadar/config/config.yaml) 的 `platforms.sources`，取消注释或新增：

   ```yaml
   - id: "zhihu"
     name: "知乎"
   ```

2. **新增规则文件**  
   复制 [`platform_rules/_default.yaml`](../hot_content_bridge/platform_rules/_default.yaml) 或同类站点模板，命名为 `{id}.yaml`，例如 `zhihu.yaml`。  
   **`platform_id` 与文件名（不含 `.yaml`）建议与 trendRadar 的 `id` 完全一致。**

3. **填写 `hosts`**  
   打开该平台热榜条目中的典型文章链接，把域名写入 `hosts`（如 `zhihu.com`）。热榜 API 的落地页域名可能与站点主域不同，以实际 URL 为准。

4. **调 crawl 段**  
   - 用浏览器开发者工具找到正文容器 class/id，写入 `css_selector` / `target_elements`。  
   - 页头导航、侧栏、评论仍出现时，在 `excluded_selector_extra` 追加选择器。  
   - 若开启 `use_target_elements: true` 后正文为空，改为 `false` 或放宽选择器。

5. **调 markdown_post 段**  
   爬一批样本后，把仍残留的导航词放进 `nav_labels`，页脚许可证等放进 `drop_line_patterns`。

6. **验证**

   ```powershell
   uv run hot-content-bridge list-platform-rules
   uv run hot-content-bridge fetch-hotlist-only
   uv run hot-content-bridge crawl-articles --limit 5
   uv run hot-content-bridge serve-web --port 8765
   ```

7. **改代码后重启 Web**  
   `serve-web` 不会热加载 Python 模块，修改规则后重新运行即可（规则在进程启动时加载；若需运行时重载可调用 `platform_rules_loader.reload_rules()`，CLI 每次新进程会自动加载）。

---

## 修改已有平台规则

1. 编辑 `hot_content_bridge/platform_rules/{platform_id}.yaml`。  
2. 仅改 Markdown 后处理：重爬非必须，Web 展示会对已存正文再跑 `strip_boilerplate_markdown(..., platform_id=...)`。  
3. 改了 `crawl` 段（CSS / excluded）：建议设置 `recrawl_success: true` 后重新执行 `crawl-articles`，或删除该 URL 在 `article_contents` 中的记录再爬。  
4. 运行 `uv run hot-content-bridge list-platform-rules` 确认 `enabled` 与 `hosts` 正确。

---

## 匹配优先级

对每条待爬文章 `(platform_id, url)`：

1. `platform_rules/{platform_id}.yaml` 且 `enabled: true`  
2. 否则按 URL 的 `hosts` 在全部规则中做最长后缀匹配  
3. 否则 `_default.yaml`

---

## 已实现规则的平台 ID

与 trendRadar 常见热榜 `id` 对齐（未在 trendRadar 启用的也可先保留文件）：

`thepaper`、`wallstreetcn-hot`、`cls-hot`、`ifeng`、`toutiao`、`baidu`、`weibo`、`zhihu`、`bilibili-hot-search`、`douyin`、`tieba`

---

## 相关代码

| 模块 | 作用 |
|------|------|
| [`platform_rules_loader.py`](../hot_content_bridge/platform_rules_loader.py) | 加载 YAML、查询规则 |
| [`article_crawler.py`](../hot_content_bridge/article_crawler.py) | 应用 `crawl` 段 |
| [`markdown_post.py`](../hot_content_bridge/markdown_post.py) | 应用 `markdown_post` 段 |
| [`hotlist_reader.py`](../hot_content_bridge/hotlist_reader.py) | 读取热榜 URL，`max_urls_per_run` |
