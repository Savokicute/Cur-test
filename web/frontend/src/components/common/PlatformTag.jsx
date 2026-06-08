import { Tag } from 'antd';
import { platformColors } from '../../theme/tokens';

const LABELS = {
  weibo: '微博',
  zhihu: '知乎',
  toutiao: '今日头条',
  douyin: '抖音',
  bilibili: 'B站',
};

export default function PlatformTag({ platform, label }) {
  const key = (platform || '').toLowerCase();
  const palette = platformColors[key] || { bg: 'rgba(30, 64, 175, 0.08)', text: '#1E40AF' };
  const text = label || LABELS[key] || platform;

  return (
    <Tag
      style={{
        background: palette.bg,
        color: palette.text,
        border: 'none',
        borderRadius: 999,
        fontWeight: 500,
        fontSize: 12,
        margin: 0,
      }}
    >
      {text}
    </Tag>
  );
}
