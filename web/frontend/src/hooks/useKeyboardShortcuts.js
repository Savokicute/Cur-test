import { useEffect, useRef, useCallback } from 'react';
import { usePreferences } from '../contexts/PreferencesContext';

/**
 * 默认快捷键配置
 */
const DEFAULT_SHORTCUTS = {
  // 搜索
  '/': { label: '聚焦搜索', description: '聚焦到搜索框' },
  
  // 视图切换
  v: { label: '切换视图', description: '在卡片/列表视图间切换' },
  
  // 布局切换
  w: { label: '切换宽屏', description: '切换宽屏/窄屏布局' },
  
  // 主题切换
  d: { label: '切换主题', description: '切换深色/浅色主题' },
  
  // 复制当前项（选中状态时）
  c: { label: '复制', description: '复制选中的内容 (Ctrl/Cmd+C)' },
  
  // 收藏当前项
  f: { label: '收藏', description: '收藏/取消收藏当前项' },
  
  // 导航
  ArrowUp: { label: '上移', description: '向上选择上一项' },
  ArrowDown: { label: '下移', description: '向下选择下一项' },
  Enter: { label: '打开', description: '打开/查看当前选中项' },
  Escape: { label: '关闭/取消', description: '关闭弹窗或取消操作' },
};

/**
 * 检查按键组合是否匹配
 * @param {KeyboardEvent} event - 键盘事件
 * @param {string} key - 目标按键
 * @param {Object} options - 选项
 * @returns {boolean} 是否匹配
 */
function matchShortcut(event, key, options = {}) {
  const { ctrl = false, meta = false, shift = false, alt = false } = options;
  
  if (event.key !== key) return false;
  if (ctrl && !event.ctrlKey) return false;
  if (meta && !event.metaKey) return false;
  if (shift && !event.shiftKey) return false;
  if (alt && !event.altKey) return false;
  
  return true;
}

/**
 * 判断是否在输入框中
 * @param {EventTarget} target - 事件目标
 * @returns {boolean}
 */
function isInputElement(target) {
  const tag = target?.tagName;
  const isInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(tag);
  const isContentEditable = target?.isContentEditable;
  return isInput || isContentEditable;
}

/**
 * 键盘快捷键 Hook
 * @param {Object} shortcuts - 自定义快捷键配置
 * @param {Object} options - 配置选项
 * @returns {Object} 快捷键相关方法和状态
 */
export function useKeyboardShortcuts(shortcuts = {}, options = {}) {
  const {
    enabled: globalEnabled,
    ignoreInputs = true,
    preventDefault = true,
  } = options;

  const { keyboardShortcutsEnabled } = usePreferences();
  const shortcutsRef = useRef({ ...DEFAULT_SHORTCUTS, ...shortcuts });
  const handlersRef = useRef({});
  const enabledRef = useRef(globalEnabled !== undefined ? globalEnabled : true);

  // 更新快捷键配置
  useEffect(() => {
    shortcutsRef.current = { ...DEFAULT_SHORTCUTS, ...shortcuts };
  }, [shortcuts]);

  /**
   * 注册快捷键处理器
   * @param {string} key - 按键标识
   * @param {Function} handler - 处理函数
   * @param {Object} shortcutOptions - 快捷键选项
   */
  const registerHandler = useCallback((key, handler, shortcutOptions = {}) => {
    handlersRef.current[key] = { handler, options: shortcutOptions };
  }, []);

  /**
   * 注销快捷键处理器
   * @param {string} key - 按键标识
   */
  const unregisterHandler = useCallback((key) => {
    delete handlersRef.current[key];
  }, []);

  /**
   * 清除所有处理器
   */
  const clearHandlers = useCallback(() => {
    handlersRef.current = {};
  }, []);

  // 监听键盘事件
  useEffect(() => {
    const handleKeyDown = (event) => {
      // 检查是否启用
      const isEnabled = enabledRef.current && keyboardShortcutsEnabled;
      if (!isEnabled) return;

      // 在输入框中时，忽略大部分快捷键（除了 Escape）
      if (ignoreInputs && isInputElement(event.target) && event.key !== 'Escape') {
        return;
      }

      const key = event.key;
      const registeredHandler = handlersRef.current[key];

      if (registeredHandler) {
        const { handler, options: handlerOptions } = registeredHandler;
        
        // 检查是否满足条件
        if (
          matchShortcut(event, key, handlerOptions) &&
          (!handlerOptions.condition || handlerOptions.condition())
        ) {
          event.preventDefault?.();
          event.stopPropagation?.();
          
          try {
            handler(event);
          } catch (err) {
            console.error('[useKeyboardShortcuts] Handler error:', err);
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [keyboardShortcutsEnabled, ignoreInputs]);

  return {
    registerHandler,
    unregisterHandler,
    clearHandlers,
    shortcuts: shortcutsRef.current,
  };
}

/**
 * 预定义的常用快捷键组合 Hook
 * 适用于热榜页面等场景
 */
export function useHotspotShortcuts({
  onSearchFocus,
  onToggleViewMode,
  onToggleTheme,
  onToggleLayout,
  onNavigateUp,
  onNavigateDown,
  onOpenItem,
  onClose,
  onCopyItem,
  onFavoriteItem,
}) {
  const { registerHandler, unregisterHandler, clearHandlers } = useKeyboardShortcuts(
    {},
    { ignoreInputs: true }
  );

  useEffect(() => {
    // 注册常用快捷键
    if (onSearchFocus) registerHandler('/', onSearchFocus);
    if (onToggleViewMode) registerHandler('v', onToggleViewMode);
    if (onToggleTheme) registerHandler('d', onToggleTheme);
    if (onToggleLayout) registerHandler('w', onToggleLayout);
    if (onNavigateUp) registerHandler('ArrowUp', onNavigateUp);
    if (onNavigateDown) registerHandler('ArrowDown', onNavigateDown);
    if (onOpenItem) registerHandler('Enter', onOpenItem);
    if (onClose) registerHandler('Escape', onClose);

    return () => clearHandlers();
  }, [
    onSearchFocus,
    onToggleViewMode,
    onToggleTheme,
    onToggleLayout,
    onNavigateUp,
    onNavigateDown,
    onOpenItem,
    onClose,
    registerHandler,
    clearHandlers,
  ]);

  return { registerHandler, unregisterHandler, clearHandlers };
}

/**
 * 显示可用快捷键列表的辅助函数
 */
export function getShortcutHelp(shortcuts = DEFAULT_SHORTCUTS) {
  return Object.entries(shortcuts).map(([key, config]) => ({
    key,
    ...config,
  }));
}

export default useKeyboardShortcuts;
