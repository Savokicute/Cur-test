import { useEffect, useState } from 'react';
import { Layout, Menu, Drawer, Button, theme, Avatar, Dropdown, Tag, Spin } from 'antd';
import {
  Flame,
  MessageSquare,
  Bookmark,
  Settings,
  Menu as MenuIcon,
  Radar,
  Search,
  SlidersHorizontal,
  Brain,
  FileText,
  Bell,
  Database,
  Bot,
  BarChart3,
  UserCircle,
  LogOut,
  ShieldCheck,
  ChevronDown,
} from 'lucide-react';
import { PictureOutlined, UserOutlined } from '@ant-design/icons';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { usePreferences } from '../../contexts/PreferencesContext';
import { useAuth } from '../../contexts/AuthContext';
import { layout } from '../../theme/tokens';
import './AppShell.css';

const { Header, Content, Sider } = Layout;

const NAV_ITEMS = [
  { key: '/', icon: <Flame size={18} />, label: '热榜总览' },
  { key: '/assistant', icon: <Bot size={18} />, label: '智能助手' },
  { key: '/ai-analysis', icon: <BarChart3 size={18} />, label: 'AI分析' },
  { key: '/wechat', icon: <MessageSquare size={18} />, label: '微信公众号' },
  { key: '/materials', icon: <Bookmark size={18} />, label: '素材中心' },
  { type: 'divider' },
  { key: '/sources', icon: <Radar size={18} />, label: '采集源配置' },
  { key: '/keywords', icon: <Search size={18} />, label: '关键词配置' },
  { key: '/notifications', icon: <Bell size={18} />, label: '通知配置' },
  { type: 'divider' },
  { key: '/settings', icon: <Settings size={18} />, label: '系统设置' },
  { key: '/ai-config', icon: <Brain size={18} />, label: 'AI 智能' },
  { key: '/content', icon: <FileText size={18} />, label: '内容策略' },
  { key: '/users', icon: <UserOutlined />, label: '用户管理' },
  { key: '/profile', icon: <UserOutlined />, label: '个人中心' },
  { type: 'divider' },
  { key: '/notify', icon: <Database size={18} />, label: '通知存储' },
  { key: '/media-test', icon: <PictureOutlined size={18} />, label: '媒体测试' },
];

function NavIcon({ icon }) {
  return <span className="nav-icon" aria-hidden>{icon}</span>;
}

export default function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const { wideLayout } = usePreferences();
  const { token } = theme.useToken();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  // 登录状态
  const { user, isAuthenticated, isLoading: authLoading, logout, isAdmin: isSuperAdmin } = useAuth();

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)');
    const update = () => setIsMobile(mq.matches);
    update();
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);

  // 检测当前用户是否为超级管理员
  useEffect(() => {
    setIsAdmin(isSuperAdmin);
  }, [isSuperAdmin]);

  const selectedKey =
    location.pathname === '/' || location.pathname.startsWith('/hotspots')
      ? '/'
      : location.pathname.startsWith('/assistant')
        ? '/assistant'
        : location.pathname.startsWith('/ai-analysis')
          ? '/ai-analysis'
          : location.pathname.startsWith('/wechat')
            ? '/wechat'
            : location.pathname.startsWith('/materials')
              ? '/materials'
              : location.pathname.startsWith('/users')
                ? '/users'
                : location.pathname;

  const menuItems = NAV_ITEMS.filter((item) => {
    // 过滤掉仅管理员可见的菜单项（非管理员隐藏）
    if (item.adminOnly && !isAdmin) return false;
    return true;
  }).map((item) => {
    if (item.type === 'divider') return { type: 'divider' };
    const { key, icon, label, disabled } = item;
    return {
      key,
      disabled,
      icon: <NavIcon icon={icon} />,
      label,
    };
  });

  const sidebar = (
    <Menu
      mode="inline"
      selectedKeys={[selectedKey]}
      items={menuItems}
      onClick={({ key }) => {
        navigate(key);
        setMobileOpen(false);
      }}
      style={{ border: 'none', padding: '8px 0' }}
    />
  );

  return (
    <Layout className="app-shell" style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: token.colorBgLayout, overflow: 'hidden' }}>
      <a href="#main-content" className="skip-link">
        跳转到主内容
      </a>

      <Header className="app-header">
        <div className="app-header-inner">
          <div className="app-brand">
            {isMobile && (
              <Button
                type="text"
                icon={<MenuIcon size={20} />}
                onClick={() => setMobileOpen(true)}
                aria-label="打开导航菜单"
                className="mobile-menu-trigger"
              />
            )}
            <Radar size={24} className="brand-icon" aria-hidden />
            <span className="brand-title">热点发现平台</span>
          </div>

          {/* 用户状态区域 */}
          <div className="header-user-area">
            {authLoading ? (
              <Spin size="small" />
            ) : isAuthenticated ? (
              <Dropdown
                menu={{
                  items: [
                    {
                      key: 'profile',
                      icon: <UserCircle size={16} />,
                      label: '个人中心',
                      onClick: () => navigate('/profile'),
                    },
                    { type: 'divider' },
                    {
                      key: 'logout',
                      icon: <LogOut size={16} />,
                      label: '退出登录',
                      danger: true,
                      onClick: () => {
                        logout();
                        navigate('/login');
                      },
                    },
                  ],
                }}
                placement="bottomRight"
                trigger={['click']}
                overlayClassName="user-dropdown-menu"
                dropdownRender={(menu) => (
                  <div className="user-dropdown-wrapper">
                    <div className="user-dropdown-header">
                      <div className="user-dropdown-name">
                        {user?.nickname || user?.username || '用户'}
                      </div>
                      {user?.role === 'super_admin' && (
                        <span className="user-dropdown-role">
                          <ShieldCheck size={12} />
                          超级管理员
                        </span>
                      )}
                    </div>
                    <div className="user-dropdown-divider" />
                    {menu}
                  </div>
                )}
              >
                <div className="user-avatar-trigger">
                  <Avatar
                    size={36}
                    className="user-header-avatar"
                    style={{
                      background:
                        user?.role === 'super_admin'
                          ? `linear-gradient(135deg, ${token.colorError}, ${token.colorErrorBg})`
                          : `linear-gradient(135deg, ${token.colorPrimary}, ${token.colorPrimaryBg})`,
                      fontSize: 15,
                      fontWeight: 600,
                    }}
                  >
                    {(user?.nickname || user?.username || 'U').charAt(0).toUpperCase()}
                  </Avatar>
                  {!isMobile && (
                    <div className="user-info-text">
                      <span className="user-nickname">
                        {user?.nickname || user?.username || '用户'}
                      </span>
                      {user?.role === 'super_admin' && (
                        <Tag color="error" className="admin-tag">
                          管理员
                        </Tag>
                      )}
                    </div>
                  )}
                  {!isMobile && (
                    <ChevronDown size={16} className="user-chevron" />
                  )}
                </div>
              </Dropdown>
            ) : (
              <Button
                type="primary"
                className="header-login-btn"
                onClick={() => navigate('/login')}
                size="middle"
              >
                登录
              </Button>
            )}
          </div>
        </div>
      </Header>

      <Layout className="app-body">
        {!isMobile && (
          <Sider
            width={layout.siderWidth}
            collapsedWidth={layout.siderCollapsed}
            collapsible
            collapsed={collapsed}
            onCollapse={setCollapsed}
            className="app-sider"
            theme="light"
          >
            {sidebar}
          </Sider>
        )}

        <Drawer
          title="导航"
          placement="left"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          styles={{ body: { padding: 0 } }}
        >
          {sidebar}
        </Drawer>

        <Content className="app-content">
          <main
            id="main-content"
            className={`app-main ${wideLayout ? 'wide' : 'narrow'}`}
            tabIndex={-1}
          >
            <Outlet />
          </main>
        </Content>
      </Layout>
    </Layout>
  );
}
