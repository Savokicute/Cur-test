# 内容详情页 — 页面设计覆盖

> 继承 `design-system/MASTER.md`；本页规则优先。

## 布局

- **阅读宽度**：正文 `max-w-3xl` 居中；元数据与操作栏全宽 `max-w-5xl`
- **双栏 (≥1280px)**：主栏 2/3 正文 + 侧栏 1/3 相关新闻/元数据（可折叠）

## 组件映射

| 区域 | 组件 |
|------|------|
| 页头 | `PageHeader` + `Breadcrumb` |
| 操作 | `Button` group：原文 `ExternalLink`、重抓 `RefreshCw`、收藏 `Heart` |
| 正文 | `react-markdown` + `Typography` prose 样式 |
| 抓取状态 | `Alert` / `Spin` + `Progress` |
| 图片 | `Image` preview 组 |

## 交互

- 重抓：按钮 loading + 轮询状态；失败 `Alert` 可重试
- Markdown 图片懒加载 + 点击放大
- 返回：浏览器后退或面包屑「热榜总览」

## 无障碍

- 文章标题为页面唯一 `h1`
- 代码块可键盘聚焦；外链 `rel="noopener noreferrer"`
