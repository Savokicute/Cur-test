import { Outlet, useLocation } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import AppShell from './components/layout/AppShell';

export default function App() {
  const location = useLocation();
  const isLoginPage = location.pathname === '/login';

  return (
    <AuthProvider>
      {isLoginPage ? (
        <Outlet />
      ) : (
        <AppShell />
      )}
    </AuthProvider>
  );
}
