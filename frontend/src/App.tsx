import { useState } from 'react';
import { ConfigProvider, Layout } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Header from './components/Header';
import CollectionsTab from './components/tabs/CollectionsTab';
import QueryTab from './components/tabs/QueryTab';
import AnalyticsTab from './components/tabs/AnalyticsTab';
import SettingsTab from './components/tabs/SettingsTab';
import ErrorBoundary from './components/ErrorBoundary';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import { getThemeConfig } from './config/theme';
import './App.css';

function AppContent() {
  const { theme } = useTheme();
  const [activeTab, setActiveTab] = useState('query');

  const renderTabContent = () => {
    switch (activeTab) {
      case 'collections':
        return <CollectionsTab />;
      case 'query':
        return <QueryTab />;
      case 'analytics':
        return <AnalyticsTab />;
      case 'settings':
        return <SettingsTab />;
      default:
        return <CollectionsTab />;
    }
  };

  return (
    <ConfigProvider locale={zhCN} theme={getThemeConfig(theme)}>
      <ErrorBoundary>
        <Layout style={{ minHeight: '100vh' }}>
          <Header
            activeTab={activeTab}
            onTabChange={setActiveTab}
          />
          <Layout.Content
            style={{
              height: 'calc(100vh - 64px)',
              overflow: 'auto'
            }}
          >
            {renderTabContent()}
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
