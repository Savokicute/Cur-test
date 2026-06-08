import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { RouterProvider } from 'react-router-dom';
import { PreferencesProvider, usePreferences } from './contexts/PreferencesContext';
import { FavoritesProvider } from './contexts/FavoritesContext';
import { buildAntdTheme } from './theme/antdTheme';
import router from './router';
import './index.css';

function ThemedApp() {
  const { isDark } = usePreferences();
  return (
    <ConfigProvider theme={buildAntdTheme(isDark)} locale={zhCN}>
      <AntApp>
        <RouterProvider router={router} />
      </AntApp>
    </ConfigProvider>
  );
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <PreferencesProvider>
      <FavoritesProvider>
        <ThemedApp />
      </FavoritesProvider>
    </PreferencesProvider>
  </StrictMode>,
);
