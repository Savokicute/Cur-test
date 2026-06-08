import { useCallback, useRef, useEffect } from 'react';
import { useLocation, useNavigationType } from 'react-router-dom';

const STATE_KEY_PREFIX = 'page_state_';

function serialize(value) {
  if (value === null || value === undefined) return null;
  return JSON.stringify(value);
}

function deserialize(str) {
  if (!str) return null;
  try {
    return JSON.parse(str);
  } catch {
    return null;
  }
}

export function usePageState(pageId, options = {}) {
  const {
    stateFields = [],
    ttl = 30 * 60 * 1000,
    restoreOnBack = true,
  } = options;

  const storageKey = STATE_KEY_PREFIX + pageId;
  const location = useLocation();
  const navigationType = useNavigationType();
  const isRestoringRef = useRef(false);
  const saveScheduledRef = useRef(null);

  const saveState = useCallback((stateSnapshot) => {
    try {
      const payload = {
        ...stateSnapshot,
        _savedAt: Date.now(),
        _fromPath: location.pathname,
      };
      sessionStorage.setItem(storageKey, serialize(payload));
    } catch (e) {
      console.warn('[usePageState] 保存状态失败:', e);
    }
  }, [storageKey, location.pathname]);

  const loadState = useCallback(() => {
    try {
      const raw = sessionStorage.getItem(storageKey);
      if (!raw) return null;
      const payload = deserialize(raw);
      if (!payload) return null;

      if (Date.now() - payload._savedAt > ttl) {
        sessionStorage.removeItem(storageKey);
        return null;
      }
      return payload;
    } catch (e) {
      console.warn('[usePageState] 读取状态失败:', e);
      return null;
    }
  }, [storageKey, ttl]);

  const clearState = useCallback(() => {
    sessionStorage.removeItem(storageKey);
  }, [storageKey]);

  const shouldRestore = restoreOnBack && navigationType === 'POP' && !isRestoringRef.current;

  useEffect(() => {
    if (shouldRestore) {
      isRestoringRef.current = true;
    }
  }, [shouldRestore]);

  return {
    saveState,
    loadState,
    clearState,
    shouldRestore,
    isRestoring: isRestoringRef.current,
  };
}

export function useScrollPosition() {
  const scrollRef = useRef(0);

  const saveScroll = useCallback(() => {
    scrollRef.current = window.scrollY;
  }, []);

  const restoreScroll = useCallback(() => {
    if (scrollRef.current > 0) {
      requestAnimationFrame(() => {
        window.scrollTo({ top: scrollRef.current, behavior: 'instant' });
      });
    }
  }, []);

  const captureAndSave = useCallback(() => {
    scrollRef.current = window.scrollY;
  }, []);

  return { saveScroll, restoreScroll, captureAndSave, scrollRef };
}
