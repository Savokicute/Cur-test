import { Brain, Zap, Target, Sparkles } from 'lucide-react';
import { Tooltip, Progress } from 'antd';
import { colors } from '../../theme/tokens';
import './AIScoreIndicator.css';

/**
 * 根据 AI 分数获取配置
 */
function getScoreConfig(score) {
  if (score >= 80) {
    return {
      color: colors.success,
      bgColor: 'rgba(16, 185, 129, 0.1)',
      icon: Zap,
      label: '高度相关',
      level: 'high',
      percentColor: '#10B981',
    };
  }
  if (score >= 50) {
    return {
      color: colors.warning,
      bgColor: 'rgba(245, 158, 11, 0.1)',
      icon: Target,
      label: '中等相关',
      level: 'medium',
      percentColor: '#F59E0B',
    };
  }
  if (score > 0) {
    return {
      color: colors.textMuted,
      bgColor: 'rgba(100, 116, 139, 0.1)',
      icon: Brain,
      label: '低度相关',
      level: 'low',
      percentColor: '#64748B',
    };
  }
  return {
    color: colors.border,
    bgColor: 'transparent',
    icon: null,
    label: '无评分',
    level: 'none',
    percentColor: '#E2E8F0',
  };
}

/**
 * AI 相关性分数指示器组件
 * @param {number} score - AI 分数（0-100）
 * @param {string} size - 尺寸：'small' | 'medium' | 'large'
 * @param {boolean} showProgress - 是否显示进度条
 * @param {boolean} showLabel - 是否显示文字标签
 * @param {boolean} showIcon - 是否显示图标
 */
export default function AIScoreIndicator({
  score = 0,
  size = 'medium',
  showProgress = true,
  showLabel = true,
  showIcon = true,
}) {
  const normalizedScore = Math.min(100, Math.max(0, score || 0));
  const config = getScoreConfig(normalizedScore);
  const { Icon } = config;

  const sizeConfig = {
    small: { progressHeight: 4, fontSize: 11, iconSize: 12 },
    medium: { progressHeight: 6, fontSize: 12, iconSize: 14 },
    large: { progressHeight: 8, fontSize: 14, iconSize: 16 },
  };

  const currentSize = sizeConfig[size] || sizeConfig.medium;

  return (
    <Tooltip title={`AI 相关性评分: ${normalizedScore}分 - ${config.label}`}>
      <div
        className={`ai-score-indicator ai-score-${config.level}`}
        role="meter"
        aria-valuenow={normalizedScore}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${config.label} (${normalizedScore}分)`}
      >
        {/* 图标 */}
        {showIcon && Icon && (
          <span className="ai-score-icon" style={{ backgroundColor: config.bgColor }}>
            <Icon size={currentSize.iconSize} color={config.color} />
          </span>
        )}

        {/* 分数文字 */}
        {(showLabel || !showProgress) && (
          <span className="ai-score-text" style={{ fontSize: currentSize.fontSize }}>
            <span className="ai-score-value" style={{ color: config.color }}>
              {normalizedScore}
            </span>
            <span className="ai-score-unit">分</span>
          </span>
        )}

        {/* 进度条 */}
        {showProgress && normalizedScore > 0 && (
          <Progress
            percent={normalizedScore}
            size="small"
            strokeColor={{
              '0%': config.percentColor,
              '100%': config.percentColor,
            }}
            trailColor="rgba(0, 0, 0, 0.06)"
            strokeWidth={currentSize.progressHeight}
            showInfo={false}
            className="ai-score-progress"
          />
        )}
      </div>
    </Tooltip>
  );
}

/**
 * 紧凑型 AI 分数徽章，用于列表视图
 */
export function AIScoreBadge({ score, size = 14 }) {
  const normalizedScore = Math.min(100, Math.max(0, score || 0));
  const config = getScoreConfig(normalizedScore);

  return (
    <AIScoreIndicator
      score={normalizedScore}
      size="small"
      showProgress={false}
      showLabel={true}
      showIcon={true}
    />
  );
}

/**
 * 带闪烁效果的高相关性指示器
 */
export function HighRelevanceIndicator({ score }) {
  if ((score || 0) < 80) return null;

  return (
    <Tooltip title="高相关性内容">
      <span className="ai-high-relevance-badge">
        <Sparkles size={12} color={colors.success} />
        <span>AI 推荐</span>
      </span>
    </Tooltip>
  );
}
