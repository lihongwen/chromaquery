import React from 'react';
import { Layout, Space, Typography, Breadcrumb, Menu } from 'antd';
import {
  DatabaseOutlined,
  HomeOutlined,
  SearchOutlined,
  BarChartOutlined,
  SettingOutlined
} from '@ant-design/icons';
import GlobalSearch from './GlobalSearch';
import ThemeToggle from './ThemeToggle';

const { Header: AntHeader } = Layout;
const { Title } = Typography;

interface HeaderProps {
  breadcrumbs?: Array<{
    title: string;
    href?: string;
  }>;
  activeTab?: string;
  onTabChange?: (key: string) => void;
}

const Header: React.FC<HeaderProps> = ({ breadcrumbs, activeTab, onTabChange }) => {
  const menuItems = [
    {
      key: 'collections',
      icon: <DatabaseOutlined />,
      label: '集合管理',
    },
    {
      key: 'query',
      icon: <SearchOutlined />,
      label: '智能查询',
    },
    {
      key: 'analytics',
      icon: <BarChartOutlined />,
      label: '数据分析',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
  ];
  return (
    <AntHeader
      style={{
        padding: '0 24px',
        backgroundColor: 'var(--ant-color-bg-container)',
        borderBottom: '1px solid var(--ant-color-border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '64px',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}
    >
      {/* 左侧：Logo + 应用名称 + 面包屑 */}
      <Space size="large">
        <Space>
          <DatabaseOutlined style={{ fontSize: '24px', color: 'var(--ant-color-primary)' }} />
          <Title level={4} style={{ margin: 0, color: 'var(--ant-color-text)' }}>
            ChromaDB Manager
          </Title>
        </Space>

        {breadcrumbs && breadcrumbs.length > 0 && (
          <Breadcrumb>
            <Breadcrumb.Item>
              <HomeOutlined />
            </Breadcrumb.Item>
            {breadcrumbs.map((item, index) => (
              <Breadcrumb.Item key={index} href={item.href}>
                {item.title}
              </Breadcrumb.Item>
            ))}
          </Breadcrumb>
        )}
      </Space>

      {/* 中间：全局搜索 */}
      <GlobalSearch />

      {/* 右侧：标签页导航 + 主题切换 */}
      <Space size="large">
        <Menu
          mode="horizontal"
          selectedKeys={activeTab ? [activeTab] : ['collections']}
          onClick={({ key }) => onTabChange?.(key)}
          items={menuItems}
          style={{
            border: 'none',
            backgroundColor: 'transparent',
            lineHeight: '62px',
          }}
          className="header-nav-menu"
        />
        <ThemeToggle />
      </Space>
    </AntHeader>
  );
};

export default Header;