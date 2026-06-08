import { createContext, useContext, useEffect, useMemo, useState, useCallback } from 'react';

const STORAGE_KEY = 'hotspot-platform-preferences';

/**
 * 默认偏好设置
 */
const defaultPrefs = {
  // 主题
  theme: 'system',
  
  // 布局
  wideLayout: true,
  
  // 视图模式
  viewMode: 'card',
  
  // 搜索相关
  searchDebounceMs: 300,
  searchHistory: [],
  maxSearchHistory: 20,
  
  // 复制相关
  copyFormat: 'title-url', // 'title' | 'url' | 'title-url' | 'markdown'
  showCopyFeedback: true,
  copyFeedbackDuration: 1500,
  
  // 键盘快捷键
  keyboardShortcutsEnabled: true,
  
  // 动画
  animationsEnabled: true,
  
  // AI 相关
  aiScoreThreshold: 50, // AI 分数显示阈值
  
  // 趋势指示器
  trendShowValue: false,
};

const PreferencesContext = createContext(null);

function loadPrefs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...defaultPrefs, ...JSON.parse(raw) } : defaultPrefs;
  } catch {
    return defaultPrefs;
  }
}

function resolveDark(themePref) {
  if (themePref === 'dark') return true;
  if (themePref === 'light') return false;
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

export function PreferencesProvider({ children }) {
  const [prefs, setPrefs] = useState(loadPrefs);
  const [isDark, setIsDark] = useState(() => resolveDark(loadPrefs().theme));

  // 持久化到 localStorage
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    setIsDark(resolveDark(prefs.theme));
  }, [prefs]);

  // 监听系统主题变化
  useEffect(() => {
    if (prefs.theme !== 'system') return undefined;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => setIsDark(mq.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [prefs.theme]);

  // 应用主题到 DOM
  useEffect(() => {
    document.documentElement.dataset.theme = isDark ? 'dark' : 'light';
  }, [isDark]);

  // ========== 主题相关方法 ==========
  const setTheme = useCallback((theme) => setPrefs((p) => ({ ...p, theme })), []);
  
  const toggleTheme = useCallback(
    () =>
      setPrefs((p) => ({
        ...p,
        theme: resolveDark(p.theme) ? 'light' : 'dark',
      })),
    []
  );

  // ========== 布局相关方法 ==========
  const setWideLayout = useCallback(
    (wideLayout) => setPrefs((p) => ({ ...p, wideLayout })),
    []
  );

  const toggleWideLayout = useCallback(
    () => setPrefs((p) => ({ ...p, wideLayout: !p.wideLayout })),
    []
  );

  // ========== 视图模式相关方法 ==========
  const setViewMode = useCallback(
    (viewMode) => setPrefs((p) => ({ ...p, viewMode })),
    []
  );

  const toggleViewMode = useCallback(
    () =>
      setPrefs((p) => ({
        ...p,
        viewMode: p.viewMode === 'card' ? 'list' : 'card',
      })),
    []
  );

  // ========== 搜索历史管理 ==========
  const addSearchHistory = useCallback(
    (query) => {
      if (!query || !query.trim()) return;
      setPrefs((p) => {
        const history = [query.trim(), ...(p.searchHistory || [])].filter(
          (item, index, arr) => arr.indexOf(item) === index
        );
        return {
          ...p,
          searchHistory: history.slice(0, p.maxSearchHistory || 20),
        };
      });
    },
    []
  );

  const clearSearchHistory = useCallback(
    () => setPrefs((p) => ({ ...p, searchHistory: [] })),
    []
  );

  const removeSearchHistoryItem = useCallback(
    (index) =>
      setPrefs((p) => ({
        ...p,
        searchHistory: p.searchHistory.filter((_, i) => i !== index),
      })),
    []
  );

  // ========== 复制格式管理 ==========
  const setCopyFormat = useCallback(
    (format) => setPrefs((p) => ({ ...p, copyFormat: format })),
    []
  );

  // ========== 键盘快捷键管理 ==========
  const toggleKeyboardShortcuts = useCallback(
    () =>
      setPrefs((p) => ({
        ...p,
        keyboardShortcutsEnabled: !p.keyboardShortcutsEnabled,
      })),
    []
  );

  // ========== 动画控制 ==========
  const toggleAnimations = useCallback(
    () =>
      setPrefs((p) => ({
        ...p,
        animationsEnabled: !p.animationsEnabled,
      })),
    []
  );

  // ========== 重置所有设置 ==========
  const resetPreferences = useCallback(() => {
    setPrefs(defaultPrefs);
  }, []);

  const value = useMemo(
    () => ({
      // 状态
      ...prefs,
      isDark,

      // 主题
      setTheme,
      toggleTheme,

      // 布局
      setWideLayout,
      toggleWideLayout,

      // 视图模式
      setViewMode,
      toggleViewMode,

      // 搜索历史
      addSearchHistory,
      clearSearchHistory,
      removeSearchHistoryItem,

      // 复制格式
      setCopyFormat,

      // 键盘快捷键
      toggleKeyboardShortcuts,

      // 动画
      toggleAnimations,

      // 重置
      resetPreferences,
    }),
    [prefs, isDark]
  );

  return (
    <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>
  );
}

export function usePreferences() {
  const ctx = useContext(PreferencesContext);
  if (!ctx) throw new Error('usePreferences must be used within PreferencesProvider');
  return ctx;
}

/**
 * 格式化复制内容
 * @param {Object} item - 数据项
 * @param {string} format - 格式类型
 * @returns {string} 格式化后的文本
 */
export function useCopyFormatter() {
  const { copyFormat } = usePreferences();

  const formatContent = useCallback(
    (item) => {
      const title = item.title || '';
      const url = item.url_norm || item.url || '';

      switch (copyFormat) {
        case 'title':
          return title;
        case 'url':
          return url;
        case 'markdown':
          return `[${title}](${url})`;
        case 'title-url':
        default:
          return `${title}\n${url}`;
      }
    },
    [copyFormat]
  );

  return { formatContent, currentFormat: copyFormat };
}
