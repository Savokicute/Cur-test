import { Button, Card, Tooltip, Typography } from 'antd';
import { Copy, ExternalLink, Heart } from 'lucide-react';
import { useState } from 'react';
import HeatScoreBar from '../common/HeatScoreBar';
import PlatformTag from '../common/PlatformTag';
import TrendIndicator, { AnimatedTrendIndicator } from '../common/TrendIndicator';
import AIScoreIndicator, { HighRelevanceIndicator } from '../common/AIScoreIndicator';
import { useCopyToClipboard } from '../../hooks/useEnhancedInteractions';
import './HotspotCard.css';

const { Text, Paragraph } = Typography;

export default function HotspotCard({ item, index, onNavigate, onFavorite }) {
  const favorited = item.favorited || false;
  const { copied, copying, copy } = useCopyToClipboard({
    successMessage: `已复制: ${item.title?.slice(0, 20)}...`,
  });

  const handleCopy = (e) => {
    e.stopPropagation();
    copy(item);
  };

  const handleFavorite = (e) => {
    e.stopPropagation();
    onFavorite?.(item, favorited, e);
  };

  // 获取趋势值（如果有）
  const trendValue = item.rank_change ?? item.trend_value ?? 0;

  return (
    <Card
      className="hotspot-card"
      hoverable
      onClick={() => onNavigate?.(item)}
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onNavigate?.(item)}
      aria-label={`热榜：${item.title}`}
    >
      <div className="hotspot-card-header">
        <AnimatedTrendIndicator
          trend={item.trend || 'flat'}
          value={trendValue}
        />
        <Paragraph className="hotspot-title" ellipsis={{ rows: 2 }}>
          {item.title || '无标题'}
        </Paragraph>
        
        {/* AI 高相关性标识 */}
        {(item.ai_score ?? 0) >= 80 && (
          <HighRelevanceIndicator score={item.ai_score} />
        )}
        
        <Tooltip title={copied ? '已复制' : '复制标题与链接'}>
          <button
            type="button"
            className={`hotspot-rank-btn ${copied ? 'copied' : ''}`}
            onClick={handleCopy}
            disabled={copying}
            aria-label={`复制第 ${index + 1} 条`}
            aria-busy={copying}
          >
            #{index + 1}
          </button>
        </Tooltip>
      </div>

      <div className="hotspot-meta">
        <Text type="secondary" className="meta-label">热度</Text>
        <HeatScoreBar score={item.score ?? item.hot_score ?? 0} />
        
        {/* AI 分数指示器 */}
        {item.ai_score != null && (
          <AIScoreIndicator
            score={item.ai_score}
            size="small"
            showProgress={false}
          />
        )}
      </div>

      <div className="hotspot-platforms">
        {(item.platforms || [item.platform_name || item.platform].filter(Boolean)).slice(0, 4).map((p, i) => (
          <PlatformTag key={p.id || i} platform={typeof p === 'string' ? p : p.id} label={typeof p === 'object' ? p.name : undefined} />
        ))}
      </div>

      <div className="hotspot-actions">
        <Button
          type="text"
          size="small"
          icon={<ExternalLink size={14} />}
          onClick={(e) => {
            e.stopPropagation();
            onNavigate?.(item);
          }}
        >
          详情
        </Button>
        <Button
          type="text"
          size="small"
          icon={<Heart size={14} fill={favorited ? 'currentColor' : 'none'} />}
          className={favorited ? 'favorited' : ''}
          onClick={handleFavorite}
          aria-pressed={favorited}
        >
          收藏
        </Button>
        <Tooltip title={`复制 (${copied ? '已复制' : 'Ctrl+C'})`}>
          <Button
            type="text"
            size="small"
            icon={
              <Copy 
                size={14} 
                className={copied ? 'copy-feedback-icon' : ''}
              />
            }
            onClick={handleCopy}
            loading={copying}
            className={copied ? 'copied-btn' : ''}
          >
            复制
          </Button>
        </Tooltip>
      </div>
    </Card>
  );
}
