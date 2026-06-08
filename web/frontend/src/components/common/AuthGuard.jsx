import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuth } from '../../contexts/AuthContext';

/**
 * 路由守卫组件
 *
 * 用法：
 * <Route element={<AuthGuard><SomePage /></AuthGuard>} />
 *
 * - 已登录 → 渲染子组件
 * - 未登录 → 重定向到 /login?from=当前路径
 * - 加载中 → 显示 Loading
 */
export default function AuthGuard({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
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
        <Spin size="large" tip="正在验证登录状态..." />
      </div>
    );
  }

  // 未登录，重定向到登录页（携带来源路径）
  if (!isAuthenticated) {
    return (
      <Navigate
        to={`/login?from=${encodeURIComponent(location.pathname + location.search)}`}
        replace
        state={{ from: location }}
      />
    );
  }

  // 已登录，渲染子组件
  return children;
}
