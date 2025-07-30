import React, { useState } from 'react';
import { Tabs, type TabsProps } from 'antd';
import {
  DatabaseOutlined,
  SearchOutlined,
  BarChartOutlined,
  SettingOutlined
} from '@ant-design/icons';
import CollectionsTab from './tabs/CollectionsTab';
import QueryTab from './tabs/QueryTab';
import AnalyticsTab from './tabs/AnalyticsTab';
import SettingsTab from './tabs/SettingsTab';

const TabManager: React.FC = () => {
  const [activeTab, setActiveTab] = useState('collections');

  const tabItems: TabsProps['items'] = [
    {
      key: 'collections',
      label: (
        <span>
          <DatabaseOutlined />
          集合管理
        </span>
      ),
      children: <CollectionsTab />,
    },
    {
      key: 'query',
      label: (
        <span>
          <SearchOutlined />
          智能查询
        </span>
      ),
      children: <QueryTab />,
    },
    {
      key: 'analytics',
      label: (
        <span>
          <BarChartOutlined />
          数据分析
        </span>
      ),
      children: <AnalyticsTab />,
    },
    {
      key: 'settings',
      label: (
        <span>
          <SettingOutlined />
          系统设置
        </span>
      ),
      children: <SettingsTab />,
    },
  ];

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Tabs
        type="card"
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        className="main-tabs"
        size="large"
        destroyInactiveTabPane={true}
        style={{ height: '100%' }}
        tabBarStyle={{ marginBottom: 0 }}
      />
    </div>
  );
};

export default TabManager;