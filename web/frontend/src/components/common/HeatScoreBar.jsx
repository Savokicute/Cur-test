import { Tooltip } from 'antd';
import './HeatScoreBar.css';

function scoreColor(score) {
  if (score >= 80) return 'var(--heat-high)';
  if (score >= 50) return 'var(--heat-mid)';
  return 'var(--heat-low)';
}

export default function HeatScoreBar({ score = 0, showValue = true }) {
  const clamped = Math.min(100, Math.max(0, Number(score) || 0));

  return (
    <div className="heat-score-bar" role="meter" aria-valuenow={clamped} aria-valuemin={0} aria-valuemax={100}>
      <div className="heat-track">
        <div
          className="heat-fill"
          style={{ width: `${clamped}%`, background: scoreColor(clamped) }}
        />
      </div>
      {showValue && (
        <Tooltip title={`热度 ${clamped} 分`}>
          <span className="heat-value">{clamped}</span>
        </Tooltip>
      )}
    </div>
  );
}
