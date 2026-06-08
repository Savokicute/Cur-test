# 热榜总览页 — 页面设计覆盖

> 继承 `design-system/MASTER.md`；本页规则优先。

## 布局

- **桌面 (≥1024px)**：左侧筛选抽屉 300px + 主内容区 `max-w-7xl`；工具栏 sticky `top-16`
- **平板 (768–1023px)**：筛选折叠为顶部 `Drawer` 触发按钮
- **移动 (<768px)**：单列卡片流；工具栏横向滚动；底部安全区内边距 `pb-20`

## 组件映射

| 区域 | Ant Design | 自定义 |
|------|-----------|--------|
| 分组 Tab | `Tabs` type="card" | — |
| 筛选模式 | `Segmented` | — |
| 视图切换 | `Radio.Group` + Lucide `LayoutGrid` / `List` | — |
| 热榜卡片 | `Card` hoverable | `HotspotCard` + `TrendIndicator` + `HeatScoreBar` |
| 采集状态 | `Tag` + `Tooltip` | — |
| 搜索 | `Input.Search` + `Modal`（`/` 快捷键） | — |

## 交互

- 卡片 hover：`shadow-md` + 边框 `primary/20`，**禁止 translate 导致布局抖动**
- 列表项 hover：行背景 `#F1F5F9`（暗色 `#1E293B`）
- 收藏：`Heart` 图标填充动画 200ms；`message.success` 反馈
- 复制序号：`Copy` 按钮 opacity 0→1；成功 `Check` 1.5s 后恢复
- 空态：`Empty` + 引导启动 daemon 文档链接

## 无障碍

- 趋势状态：`aria-label="排名上升"` 等，不仅依赖颜色
- 工具栏控件均有 `aria-label`
- 虚拟列表容器 `role="feed"`，`aria-busy` 于加载态
