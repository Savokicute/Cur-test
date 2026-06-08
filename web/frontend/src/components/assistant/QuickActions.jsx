import React, { memo } from 'react';
import { Tag } from 'antd';
import {
  TrendingUp,
  Search,
  BarChart3,
  Star,
  Zap,
  Globe,
} from 'lucide-react';
import './QuickActions.css';

/**
 * 快捷查询预设组件
 *
 * 提供常用查询的快捷按钮，点击后自动填充并发送消息。
 * 使用 memo 优化性能，避免不必要的重渲染。
 */
const QuickActions = memo(({ onSelect }) => {
  /**
   * 预设的快捷查询配置
   * 每个配置包含：文本、图标、描述、标签
   */
  const quickActions = [
    {
      id: 'today-hot',
      text: '今天最热的10条新闻',
      icon: <TrendingUp size={16} />,
      description: '查看今日各平台热门话题',
      tag: '热门',
      tagColor: 'red',
    },
    {
      id: 'tech-hotspots',
      text: '科技领域热点',
      icon: <Zap size={16} />,
      description: '搜索科技相关的热点内容',
      tag: '科技',
      tagColor: 'blue',
    },
    {
      id: 'trend-summary',
      text: '帮我总结今天的趋势',
      icon: <BarChart3 size={16} />,
      description: '获取今日趋势分析和总结',
      tag: '分析',
      tagColor: 'green',
    },
    {
      id: 'recommend-news',
      text: '推荐值得关注的新闻',
      icon: <Star size={16} />,
      description: '智能推荐高质量新闻内容',
      tag: '推荐',
      tagColor: 'gold',
    },
    {
      id: 'platform-stats',
      text: '各平台数据统计',
      icon: <Globe size={16} />,
      description: '查看各平台数据分布情况',
      tag: '统计',
      tagColor: 'purple',
    },
    {
      id: 'search-keywords',
      text: '当前热门关键词',
      icon: <Search size={16} />,
      description: '获取当前最热的关键词',
      tag: '关键词',
      tagColor: 'cyan',
    },
  ];

  /**
   * 处理快捷操作点击
   * @param {Object} action - 选中的快捷操作
   */
  const handleActionClick = (action) => {
    if (onSelect && typeof onSelect === 'function') {
      onSelect(action.text);
    }
  };

  return (
    <div className="quick-actions">
      <div className="quick-actions-header">
        <span className="quick-actions-title">快捷查询</span>
        <span className="quick-actions-subtitle">点击快速发送</span>
      </div>

      <div className="quick-actions-grid">
        {quickActions.map((action) => (
          <div
            key={action.id}
            className="quick-action-item"
            onClick={() => handleActionClick(action)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleActionClick(action);
              }
            }}
          >
            <div className="quick-action-icon">{action.icon}</div>

            <div className="quick-action-content">
              <div className="quick-action-text">{action.text}</div>
              <div className="quick-action-description">{action.description}</div>
            </div>

            {action.tag && (
              <Tag color={action.tagColor} className="quick-action-tag">
                {action.tag}
              </Tag>
            )}
          </div>
        ))}
      </div>
    </div>
  );
});

QuickActions.displayName = 'QuickActions';

export default QuickActions;
