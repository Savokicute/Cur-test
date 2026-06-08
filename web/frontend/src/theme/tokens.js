/** Design tokens — aligned with PRD §6.2 and design-system/MASTER.md */
export const colors = {
  primary: '#1E40AF',
  secondary: '#3B82F6',
  cta: '#F59E0B',
  background: '#F8FAFC',
  surface: '#FFFFFF',
  text: '#0F172A',
  textSecondary: '#475569',
  textMuted: '#64748B',
  border: '#E2E8F0',
  success: '#10B981',
  warning: '#F59E0B',
  error: '#EF4444',
  dark: {
    background: '#0F172A',
    surface: '#1E293B',
    text: '#F8FAFC',
    textSecondary: '#CBD5E1',
    border: '#334155',
  },
};

export const platformColors = {
  weibo: { bg: 'rgba(230, 22, 45, 0.1)', text: '#E6162D' },
  zhihu: { bg: 'rgba(0, 132, 255, 0.1)', text: '#0084FF' },
  toutiao: { bg: 'rgba(210, 40, 42, 0.1)', text: '#D2282A' },
  douyin: { bg: 'rgba(0, 0, 0, 0.06)', text: '#0F172A' },
  bilibili: { bg: 'rgba(251, 114, 153, 0.1)', text: '#FB7299' },
};

export const layout = {
  headerHeight: 64,
  siderWidth: 260,
  siderCollapsed: 56,
  contentMaxWidth: 1280,
  contentNarrowWidth: 720,
};

export const motion = {
  fast: '150ms',
  base: '200ms',
  slow: '300ms',
  easing: 'cubic-bezier(0.4, 0, 0.2, 1)',
};
