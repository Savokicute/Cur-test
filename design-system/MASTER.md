# 热点发现平台 - 设计系统 (MASTER)

## 项目信息

- **产品名称:** 热点发现平台 (Hotspot Discovery Platform)
- **产品类型:** Dashboard / Data Analytics Platform
- **行业:** Technology / Content Discovery
- **技术栈:** React + Vite + Ant Design

---

## 设计模式

### Pattern: Data-Dense Dashboard
**适用:** Business intelligence dashboards, financial analytics, enterprise reporting, operational dashboards, data warehousing

**特点:**
- Multiple charts/widgets
- Data tables
- KPI cards
- Minimal padding
- Grid layout
- Space-efficient
- Maximum data visibility

**性能:** ⚡ Excellent | **无障碍:** ✓ WCAG AA

---

## 色彩系统

| 角色 | 颜色值 | 说明 |
|------|--------|------|
| Primary | #1E40AF | 主色调 - 深蓝 |
| Secondary | #3B82F6 | 辅助色 - 中蓝 |
| CTA | #F59E0B | 行动召唤 - 琥珀 |
| Background | #F8FAFC | 背景色 - 浅灰蓝 |
| Text | #1E3A8A | 文字色 - 深蓝 |

**策略:** Blue data + amber highlights

---

## 字体系统

### Heading (标题)
- **字体:** Fira Code
- **权重:** 400, 500, 600, 700
- **适用:** 页面标题、卡片标题、重要文本

### Body (正文)
- **字体:** Fira Sans
- **权重:** 300, 400, 500, 600, 700
- **适用:** 段落、正文、描述文本

**风格:** dashboard, data, analytics, code, technical, precise

**Google Fonts:** https://fonts.google.com/share?selection.family=Fira+Code:wght@400;500;600;700|Fira+Sans:wght@300;400;500;600;700

```css
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');
```

---

## 交互效果

### Hover (悬停)
- 悬停工具提示
- 卡片悬停高亮
- 平滑颜色过渡 (150-300ms)
- 不使用会导致布局偏移的缩放变换

### Loading (加载)
- 数据加载旋转动画
- 骨架屏占位
- 加载过程中提供视觉反馈

### Filtering (筛选)
- 平滑的筛选动画
- 行悬停高亮

---

## 页面级覆盖索引

构建具体页面时，**优先**阅读 `design-system/pages/[page].md`；若不存在则使用本文档。

| 页面 | 覆盖文件 | 状态 |
|------|---------|------|
| 热榜总览 | `pages/hotspots.md` | ✅ |
| 内容详情 | `pages/content-detail.md` | ✅ |
| 微信公众号 | `pages/wechat.md` | ✅ |

---

## 需要避免的反模式 (Anti-patterns)

❌ 华丽的装饰性设计
❌ 没有筛选功能
❌ 使用 emoji 作为图标（使用 SVG 图标）
❌ 悬停效果只在桌面有效（移动端要提供点击反馈）
❌ 持续动画（只用于加载指示器）

---

## 交付前检查清单

### 视觉质量
- [ ] 不使用 emoji 作为图标（使用 SVG: Heroicons/Lucide）
- [ ] 所有图标来自一致的图标库
- [ ] 悬停状态不会导致布局偏移
- [ ] 直接使用主题颜色

### 交互体验
- [ ] 所有可点击元素有 `cursor-pointer`
- [ ] 悬停状态提供清晰的视觉反馈
- [ ] 过渡动画平滑 (150-300ms)
- [ ] 键盘导航的聚焦状态可见

### 对比度与可访问性
- [ ] 浅色模式文字对比度最低 4.5:1
- [ ] 玻璃/透明元素在浅色模式可见
- [ ] 边框在两种模式都可见
- [ ] 交付前测试两种模式

### 布局与间距
- [ ] 浮动元素距离边缘有适当间距
- [ ] 没有内容被固定导航栏隐藏
- [ ] 在 375px, 768px, 1024px, 1440px 响应式
- [ ] 移动端没有横向滚动

### 无障碍
- [ ] 所有图片有 alt 文本
- [ ] 表单输入有标签
- [ ] 颜色不是唯一的指示方式
- [ ] 尊重 `prefers-reduced-motion`
