import { ConfigProvider, Layout } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Header from './components/Header';
import TabManager from './components/TabManager';
import ErrorBoundary from './components/ErrorBoundary';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import { getThemeConfig } from './config/theme';
import './App.css';

function AppContent() {
  const { theme } = useTheme();

  return (
    <ConfigProvider locale={zhCN} theme={getThemeConfig(theme)}>
      <ErrorBoundary>
        <Layout style={{ minHeight: '100vh' }}>
          <Header />
          <Layout.Content>
            <TabManager />
          </Layout.Content>
        </Layout>
      </ErrorBoundary>
    </ConfigProvider>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;
