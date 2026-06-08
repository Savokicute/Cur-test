import { ChevronDown, ChevronRight, ChevronUp, Sparkles, TrendingUp, TrendingDown } from 'lucide-react';
import { Tooltip } from 'antd';
import { colors } from '../../theme/tokens';
import './TrendIndicator.css';

const CONFIG = {
  up: {
    Icon: ChevronUp,
    TrendIcon: TrendingUp,
    color: colors.success,
    bgColor: 'rgba(16, 185, 129, 0.1)',
    label: '排名上升',
    shortLabel: '上升',
  },
  down: {
    Icon: ChevronDown,
    TrendIcon: TrendingDown,
    color: colors.error,
    bgColor: 'rgba(239, 68, 68, 0.1)',
    label: '排名下降',
    shortLabel: '下降',
  },
  flat: {
    Icon: ChevronRight,
    TrendIcon: null,
    color: colors.textMuted,
    bgColor: 'transparent',
    label: '排名持平',
    shortLabel: '持平',
  },
  new: {
    Icon: Sparkles,
    TrendIcon: Sparkles,
    color: colors.primary,
    bgColor: 'rgba(30, 64, 175, 0.1)',
    label: '首次上榜',
    shortLabel: '新增',
  },
};

/**
 * 趋势指示器组件
 * @param {string} trend - 趋势类型：'up' | 'down' | 'flat' | 'new'
 * @param {number} size - 图标尺寸（默认 18）
 * @param {boolean} showLabel - 是否显示文字标签
 * @param {boolean} showValue - 是否显示趋势数值（如 +5、-3）
 * @param {number} value - 趋势变化值
 * @param {string} variant - 样式变体：'default' | 'compact' | 'badge'
 * @param {boolean} animated - 是否启用动画效果
 */
export default function TrendIndicator({
  trend = 'flat',
  size = 18,
  showLabel = false,
  showValue = false,
  value = 0,
  variant = 'default',
  animated = true,
}) {
  const cfg = CONFIG[trend] || CONFIG.flat;
  const { Icon, TrendIcon, color, bgColor, label, shortLabel } = cfg;

  const formattedValue = value > 0 ? `+${value}` : `${value}`;
  const displayValue = value !== 0 ? formattedValue : '';

  return (
    <Tooltip title={`${label}${showValue && value !== 0 ? ` ${formattedValue}` : ''}`}>
      <span
        className={`trend-indicator trend-${trend} trend-variant-${variant}`}
        aria-label={label}
        title={label}
        data-animated={animated}
      >
        <span className="trend-icon-wrapper" style={{ backgroundColor: bgColor }}>
          <Icon
            size={size}
            color={color}
            strokeWidth={2.5}
            aria-hidden="true"
          />
        </span>

        {(showLabel || showValue) && (
          <span className="trend-info">
            {showValue && value !== 0 && (
              <span className="trend-value" style={{ color }}>
                {displayValue}
              </span>
            )}
            {showLabel && (
              <span className="trend-label">
                {variant === 'compact' ? shortLabel : label}
              </span>
            )}
          </span>
        )}
      </span>
    </Tooltip>
  );
}

/**
 * 紧凑型趋势徽章，用于列表视图等空间受限场景
 */
export function TrendBadge({ trend, value = 0, size = 14 }) {
  return (
    <TrendIndicator
      trend={trend}
      size={size}
      variant="badge"
      showValue={true}
      value={value}
      animated={false}
    />
  );
}

/**
 * 带动画的趋势指示器组，用于卡片头部强调显示
 */
export function AnimatedTrendIndicator({ trend, value = 0, size = 20 }) {
  return (
    <TrendIndicator
      trend={trend}
      size={size}
      variant="default"
      showValue={true}
      value={value}
      animated={true}
      showLabel={false}
    />
  );
}
