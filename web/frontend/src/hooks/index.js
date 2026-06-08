/**
 * Hooks 导出索引
 */

// 页面状态管理
export { usePageState, useScrollPosition } from './usePageState';

// 键盘快捷键
export { useKeyboardShortcuts, useHotspotShortcuts, getShortcutHelp } from './useKeyboardShortcuts';

// 增强交互（搜索、复制、高亮）
export {
  useDebounce,
  useEnhancedSearch,
  useCopyToClipboard,
  getHighlightedParts,
} from './useEnhancedInteractions';
