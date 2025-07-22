import React from 'react';
import { Layout, Space, Typography, Breadcrumb } from 'antd';
import { DatabaseOutlined, HomeOutlined } from '@ant-design/icons';
import GlobalSearch from './GlobalSearch';
import ThemeToggle from './ThemeToggle';

const { Header: AntHeader } = Layout;
const { Title } = Typography;

interface HeaderProps {
  breadcrumbs?: Array<{
    title: string;
    href?: string;
  }>;
}

const Header: React.FC<HeaderProps> = ({ breadcrumbs }) => {
  return (
    <AntHeader
      style={{
        padding: '0 24px',
        backgroundColor: 'var(--ant-color-bg-container)',
        borderBottom: '1px solid var(--ant-color-border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
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

      {/* 右侧：主题切换 */}
      <Space>
        <ThemeToggle />
      </Space>
    </AntHeader>
  );
};

export default Header;