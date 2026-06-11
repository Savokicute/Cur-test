import { Navigate, useLocation } from 'react-router-dom';
import { Result, Button } from 'antd';
import { ShieldAlert } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

/**
 * 管理员路由守卫组件
 *
 * 用法：
 * <Route element={<AdminGuard><AdminPage /></AdminGuard>} />
 *
 * - 已登录 + 是管理员 → 渲染子组件
 * - 已登录 + 非管理员 → 显示权限不足提示
 * - 未登录 → 重定向到 /login
 * - 加载中 → 显示 Loading
 */
export default function AdminGuard({ children }) {
  const { isAuthenticated, isLoading, isAdmin } = useAuth();
  const location = useLocation();

  // 初始化加载中
  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
        }}
      >
        {/* eslint-disable-next-line jsx-a11y/aria-role */}
        <div style={{ textAlign: 'center' }}>
          {/* eslint-disable-next-line jsx-a11y/aria-role */}
          <div style={{ marginBottom: 16 }}>
            <ShieldAlert size={48} style={{ color: '#faad14' }} />
          </div>
          正在验证权限...
        </div>
      </div>
    );
  }

  // 未登录，重定向到登录页
  if (!isAuthenticated) {
    return (
      <Navigate
        to={`/login?from=${encodeURIComponent(location.pathname + location.search)}`}
        replace
        state={{ from: location }}
      />
    );
  }

  // 已登录但非管理员，显示权限不足页面
  if (!isAdmin) {
    return (
      <Result
        status="403"
        title="权限不足"
        subTitle="您没有权限访问此页面，该功能仅对管理员开放。"
        extra={
          <Button type="primary" onClick={() => window.history.back()}>
            返回上一页
          </Button>
        }
      />
    );
  }

  // 已登录且是管理员，渲染子组件
  return children;
}
