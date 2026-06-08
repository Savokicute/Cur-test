// src/router/index.jsx
import { createBrowserRouter } from 'react-router-dom';
import App from '../App';
import Hotspots from '../pages/Hotspots';
import ArticleDetail from '../pages/ArticleDetail';
import WeChat from '../pages/WeChat';
import Materials from '../pages/Materials';
import Sources from '../pages/Sources';
import Settings from '../pages/Settings';
import MediaTest from '../pages/MediaTest';
import Keywords from '../pages/Keywords';
import AIConfig from '../pages/AIConfig';
import ContentPolicy from '../pages/ContentPolicy';
import NotifyStorage from '../pages/NotifyStorage';
import Assistant from '../pages/Assistant';
import AIAnalysis from '../pages/AIAnalysis';
import Notifications from '../pages/Notifications';
import UserManagement from '../pages/UserManagement';
import Login from '../pages/Login';
import AuthGuard from '../components/common/AuthGuard';
import ProfilePage from '../pages/ProfilePage';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <Hotspots />,
      },
      {
        path: 'hotspots',
        element: <Hotspots />,
      },
      {
        path: 'articles/:id',
        element: <ArticleDetail />,
      },
      {
        path: 'wechat',
        element: <WeChat />,
      },
      {
        path: 'materials',
        element: <Materials />,
      },
      {
        path: 'sources',
        element: <Sources />,
      },
      {
        path: 'settings',
        element: <Settings />,
      },
      {
        path: 'ai-config',
        element: <AIConfig />,
      },
      {
        path: 'content',
        element: <ContentPolicy />,
      },
      {
        path: 'notify',
        element: <NotifyStorage />,
      },
      {
        path: 'notifications',
        element: <Notifications />,
      },
      {
        path: 'media-test',
        element: <MediaTest />,
      },
      {
        path: 'keywords',
        element: <Keywords />,
      },
      {
        path: 'assistant',
        element: <Assistant />,
      },
      {
        path: 'ai-analysis',
        element: <AIAnalysis />,
      },
      {
        path: 'users',
        element: (
          <AuthGuard>
            <UserManagement />
          </AuthGuard>
        ),
      },
      {
        path: 'profile',
        element: (
          <AuthGuard>
            <ProfilePage />
          </AuthGuard>
        ),
      },
      {
        path: 'login',
        element: <Login />,
      },
    ],
  },
]);

export default router;
