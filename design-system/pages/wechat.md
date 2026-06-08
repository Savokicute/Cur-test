# 微信公众号页 — 页面设计覆盖

> 继承 `design-system/MASTER.md`；本页规则优先。

## 布局

- **主从视图**：公众号列表 ↔ 文章列表（`Routes` 或内部 state 切换）
- **桌面**：左侧公众号侧栏 280px + 右侧文章网格
- **移动**：列表 → 详情全屏栈式导航

## 组件映射

| 区域 | 组件 |
|------|------|
| 公众号卡片 | `Card` + 头像 `Avatar` + 状态 `Badge` |
| 分组 Tab | `Tabs` |
| 文章卡片 | `Card` cover 可选 + `Meta` |
| 抓取 | `Button` + `SyncOutlined` loading |

## 视觉

- 在线状态：`Badge status="success"`，不用 emoji 圆点
- 文章图标：`Newspaper` (Lucide)
- 阅读量/点赞：次要文字 `#475569`，数字用 `font-family-heading`

## 交互

- 手动抓取：`notification` 进度反馈
- 导出：`Dropdown` 格式选择 md/docx/pdf/json
