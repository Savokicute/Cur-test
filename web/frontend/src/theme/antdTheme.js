import { theme as antTheme } from 'antd';
import { colors, layout } from './tokens';

export function buildAntdTheme(isDark) {
  return {
    algorithm: isDark ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm,
    token: {
      colorPrimary: colors.primary,
      colorSuccess: colors.success,
      colorWarning: colors.warning,
      colorError: colors.error,
      colorInfo: colors.secondary,
      borderRadius: 8,
      fontFamily: "'Fira Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      fontFamilyCode: "'Fira Code', 'Consolas', monospace",
      colorBgContainer: isDark ? colors.dark.surface : colors.surface,
      colorBgLayout: isDark ? colors.dark.background : colors.background,
      colorText: isDark ? colors.dark.text : colors.text,
      colorTextSecondary: isDark ? colors.dark.textSecondary : colors.textSecondary,
      colorBorder: isDark ? colors.dark.border : colors.border,
      controlHeight: 36,
      motionDurationMid: '0.2s',
    },
    components: {
      Layout: {
        headerHeight: layout.headerHeight,
        siderBg: isDark ? colors.dark.surface : '#FFFFFF',
      },
      Menu: {
        itemBorderRadius: 8,
        itemMarginInline: 8,
      },
      Card: {
        borderRadiusLG: 12,
      },
      Button: {
        borderRadius: 8,
      },
    },
  };
}
