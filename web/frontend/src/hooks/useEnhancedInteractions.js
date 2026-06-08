import { useState, useEffect, useRef, useCallback } from 'react';
import { usePreferences } from '../contexts/PreferencesContext';
import { message } from 'antd';

/**
 * 防抖 Hook
 * @param {*} value - 需要防抖的值
 * @param {number} delay - 延迟时间（毫秒）
 * @returns {*} 防抖后的值
 */
export function useDebounce(value, delay = 300) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

/**
 * 带历史记录的搜索 Hook
 * @param {Object} options - 配置选项
 * @returns {Object} 搜索相关状态和方法
 */
export function useEnhancedSearch(options = {}) {
  const {
    onSearch,
    debounceMs: defaultDebounce = 300,
    minLength = 0,
    maxHistory = 20,
    placeholder = '搜索...',
  } = options;

  const {
    searchDebounceMs,
    searchHistory,
    addSearchHistory,
    clearSearchHistory,
    removeSearchHistoryItem,
    showCopyFeedback,
  } = usePreferences();

  const [query, setQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const inputRef = useRef(null);
  const debounceTimerRef = useRef(null);

  // 使用配置的防抖时间或默认值
  const effectiveDebounce = searchDebounceMs || defaultDebounce;

  // 防抖后的查询值
  const debouncedQuery = useDebounce(query, effectiveDebounce);

  // 当防抖值变化时触发搜索
  useEffect(() => {
    if (debouncedQuery.length >= minLength) {
      onSearch?.(debouncedQuery);
      
      // 添加到搜索历史（仅在用户停止输入后）
      if (debouncedQuery.trim()) {
        // 延迟添加，避免频繁更新
        const timer = setTimeout(() => {
          addSearchHistory(debouncedQuery.trim());
        }, effectiveDebounce + 100);
        return () => clearTimeout(timer);
      }
    } else if (debouncedQuery.length === 0) {
      onSearch?.('');
    }
  }, [debouncedQuery, onSearch, minLength, effectiveDebounce, addSearchHistory]);

  /**
   * 处理输入变化
   */
  const handleChange = useCallback((e) => {
    const value = e.target.value;
    setQuery(value);
    setShowHistory(value.length > 0 && (searchHistory?.length > 0));
  }, [searchHistory]);

  /**
   * 处理搜索提交
   */
  const handleSearch = useCallback((value) => {
    const searchValue = value ?? query;
    
    if (searchValue.trim()) {
      addSearchHistory(searchValue.trim());
      onSearch?.(searchValue.trim());
    } else {
      onSearch?.('');
    }
    
    setShowHistory(false);
  }, [query, onSearch, addSearchHistory]);

  /**
   * 清空搜索
   */
  const handleClear = useCallback(() => {
    setQuery('');
    setShowHistory(false);
    onSearch?.('');
  }, [onSearch]);

  /**
   * 聚焦输入框
   */
  const focus = useCallback(() => {
    inputRef.current?.focus();
  }, []);

  /**
   * 从历史记录中选择
   */
  const selectFromHistory = useCallback((historyItem) => {
    setQuery(historyItem);
    handleSearch(historyItem);
    setShowHistory(false);
  }, [handleSearch]);

  return {
    // 状态
    query,
    debouncedQuery,
    isFocused,
    showHistory,
    searchHistory: searchHistory || [],

    // Ref
    inputRef,

    // 方法
    setQuery,
    handleChange,
    handleSearch,
    handleClear,
    focus,
    selectFromHistory,

    // 历史记录管理
    clearSearchHistory,
    removeSearchHistoryItem,

    // 焦点控制
    onFocus: () => setIsFocused(true),
    onBlur: () => {
      setIsFocused(false);
      // 延迟隐藏历史，允许点击历史项
      setTimeout(() => setShowHistory(false), 200);
    },
    onHistoryToggle: () => setShowHistory(prev => !prev),

    // Props for Input component
    inputProps: {
      ref: inputRef,
      value: query,
      onChange: handleChange,
      onPressEnter: () => handleSearch(),
      onFocus: () => setIsFocused(true),
      onBlur: () => {
        setIsFocused(false);
        setTimeout(() => setShowHistory(false), 200);
      },
      placeholder,
      allowClear: true,
    },
  };
}

/**
 * 增强的一键复制 Hook
 * @param {Object} options - 配置选项
 * @returns {Object} 复制相关状态和方法
 */
export function useCopyToClipboard(options = {}) {
  const {
    showFeedback = true,
    feedbackDuration = 1500,
    successMessage = '已复制到剪贴板',
    errorMessage = '复制失败，请重试',
  } = options;

  const { copyFormat, formatContent } = usePreferences();
  const [copied, setCopied] = useState(false);
  const [copying, setCopying] = useState(false);
  const timerRef = useRef(null);

  // 清除定时器
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  /**
   * 执行复制操作
   * @param {Object|string} item - 数据项或纯文本
   * @param {string} customFormat - 自定义格式（覆盖全局设置）
   * @returns {Promise<boolean>} 是否成功
   */
  const copy = useCallback(async (item, customFormat) => {
    if (copying) return false;
    
    setCopying(true);
    
    try {
      let textToCopy;
      
      if (typeof item === 'string') {
        textToCopy = item;
      } else {
        // 使用自定义格式或全局格式
        textToCopy = customFormat 
          ? formatContentWithFormat(item, customFormat)
          : formatContent(item);
      }

      await navigator.clipboard.writeText(textToCopy);
      
      setCopied(true);
      
      if (showFeedback) {
        message.success({
          content: successMessage,
          duration: feedbackDuration / 1000,
          key: 'copy-feedback',
        });
      }

      // 自动重置状态
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        setCopied(false);
      }, feedbackDuration);

      return true;
    } catch (err) {
      console.error('[useCopyToClipboard] Copy failed:', err);
      
      if (showFeedback) {
        message.error({
          content: errorMessage,
          duration: feedbackDuration / 1000,
          key: 'copy-error',
        });
      }
      
      return false;
    } finally {
      setCopying(false);
    }
  }, [copying, showFeedback, feedbackDuration, successMessage, errorMessage, formatContent]);

  /**
   * 重置复制状态
   */
  const reset = useCallback(() => {
    setCopied(false);
    setCopying(false);
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
  }, []);

  return {
    copied,
    copying,
    copy,
    reset,
    currentFormat: copyFormat,
  };
}

/**
 * 根据格式化类型生成内容
 */
function formatContentWithFormat(item, format) {
  const title = item.title || '';
  const url = item.url_norm || item.url || '';

  switch (format) {
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
}

/**
 * 搜索高亮工具函数
 * 用于生成高亮文本的片段数据
 * @param {string} text - 原始文本
 * @param {string} query - 搜索关键词
 * @returns {Array<{text: string, highlight: boolean}>} 高亮片段数组
 */
export function getHighlightedParts(text, query) {
  if (!query || !text) return [{ text: text || '', highlight: false }];

  const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
  const parts = text.split(regex);

  return parts.map((part) => ({
    text: part,
    highlight: regex.test(part),
  }));
}

/**
 * 转义正则表达式特殊字符
 */
function escapeRegex(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export default {
  useDebounce,
  useEnhancedSearch,
  useCopyToClipboard,
  getHighlightedParts,
};
