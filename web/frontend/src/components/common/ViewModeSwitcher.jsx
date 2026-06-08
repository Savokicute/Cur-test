import { Tooltip } from 'antd';
import { LayoutGrid, List } from 'lucide-react';
import './ViewModeSwitcher.css';

const MODES = [
  {
    value: 'card',
    Icon: LayoutGrid,
    label: '卡片视图',
    shortcut: 'V',
  },
  {
    value: 'list',
    Icon: List,
    label: '列表视图',
    shortcut: 'V',
  },
];

export default function ViewModeSwitcher({ value = 'card', onChange, size = 16, disabled = false }) {
  const handleClick = (modeValue) => {
    if (!disabled && modeValue !== value) {
      onChange?.(modeValue);
    }
  };

  return (
    <div
      className="view-mode-switcher"
      role="radiogroup"
      aria-label="视图模式切换"
      data-mode={value}
    >
      {MODES.map(({ value: modeValue, Icon, label, shortcut }) => (
        <Tooltip
          key={modeValue}
          title={`${label} (${shortcut})`}
          placement="top"
        >
          <button
            type="button"
            className={`view-mode-btn ${value === modeValue ? 'active' : ''}`}
            onClick={() => handleClick(modeValue)}
            disabled={disabled}
            aria-pressed={value === modeValue}
            aria-label={label}
            tabIndex={0}
          >
            <Icon size={size} aria-hidden="true" />
          </button>
        </Tooltip>
      ))}
    </div>
  );
}
