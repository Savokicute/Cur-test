import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { message } from 'antd';

const AuthContext = createContext(null);

// localStorage keys
const AUTH_KEY = 'trendradar_user';
const TOKEN_KEY = 'trendradar_token';
const REMEMBER_KEY = 'trendradar_remember';

/**
 * 认证状态 Context - 独立用户体系版
 *
 * 使用本地 /api/auth/* 接口
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // ---- 初始化 ----
  useEffect(() => {
    try {
      const saved = localStorage.getItem(AUTH_KEY);
      const token = localStorage.getItem(TOKEN_KEY);
      if (saved && token) {
        const parsed = JSON.parse(saved);
        setUser(parsed);
        // 后台验证 Token 有效性
        verifyToken(token);
      }
    } catch (e) {
      console.warn('[Auth] 恢复登录状态失败:', e);
      clearAuth();
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ---- 验证 Token ----
  const verifyToken = async (token) => {
    try {
      const res = await fetch('/api/auth/me', {
        headers: { 'X-Session-Token': token },
      });
      if (res.ok) {
        const data = await res.json();
        const updated = { ...user, ...data };
        setUser(updated);
        localStorage.setItem(AUTH_KEY, JSON.stringify(updated));
      } else {
        clearAuth();
      }
    } catch (e) {
      console.warn('[Auth] Token 验证失败:', e);
      clearAuth();
    }
  };

  // ---- 清除认证 ----
  const clearAuth = () => {
    localStorage.removeItem(AUTH_KEY);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REMEMBER_KEY);
    setUser(null);
  };

  // ---- 登录（本地 API）----
  const login = useCallback(async ({ username, password, rememberMe = false }) => {
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, rememberMe }),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.message || '登录失败');
      }

      // 保存 Token
      localStorage.setItem(TOKEN_KEY, data.token);

      // 构建用户信息
      const userInfo = {
        ...data.user,
        loginTime: new Date().toISOString(),
        rememberMe,
      };

      setUser(userInfo);
      localStorage.setItem(AUTH_KEY, JSON.stringify(userInfo));

      if (rememberMe) {
        localStorage.setItem(REMEMBER_KEY, 'true');
      } else {
        localStorage.removeItem(REMEMBER_KEY);
      }

      message.success('登录成功');
      return { success: true, user: userInfo };
    } catch (err) {
      console.error('[Auth] 登录失败:', err);
      throw err;
    }
  }, []);

  // ---- 注册（本地 API）----
  const register = useCallback(async ({ username, password, confirm_password, email, nickname }) => {
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, confirm_password, email, nickname }),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.message || '注册失败');
      }

      return data;
    } catch (err) {
      console.error('[Auth] 注册失败:', err);
      throw err;
    }
  }, []);

  // ---- 退出登录 ----
  const logout = useCallback(async (notify = true) => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      try {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: { 'X-Session-Token': token },
        });
      } catch (e) {
        console.warn('[Auth] 退出请求失败:', e);
      }
    }

    clearAuth();
    if (notify) message.info('已退出登录');
  }, []);

  // ---- 刷新用户信息 ----
  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token || !user?.username) return;

    try {
      const res = await fetch('/api/auth/me', {
        headers: { 'X-Session-Token': token },
      });
      if (res.ok) {
        const data = await res.json();
        const updated = { ...user, ...data };
        setUser(updated);
        localStorage.setItem(AUTH_KEY, JSON.stringify(updated));
      }
    } catch (e) {
      console.warn('[Auth] 刷新用户信息失败:', e);
    }
  }, [user]);

  // ---- 权限检查 ----
  const hasPermission = useCallback((permissionId) => {
    return user?.role === 'super_admin';
  }, [user]);

  const isAdmin = user?.role === 'super_admin';

  // 强制改密检查
  const needChangePassword = user?.force_change_password === true;

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    isAdmin,
    needChangePassword,
    login,
    register,
    logout,
    refreshUser,
    hasPermission,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth 必须在 AuthProvider 内使用');
  return context;
}

export default AuthContext;
