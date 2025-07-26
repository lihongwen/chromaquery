import React, { useState } from 'react';
import { 
  Layout, 
  Menu, 
  Card, 
  Form, 
  Input, 
  InputNumber, 
  Button, 
  Space, 
  Radio, 
  Switch, 
  Divider, 
  Typography,
  message,
  Row,
  Col,
  Select,
  Slider,
  Alert
} from 'antd';
import { 
  LinkOutlined, 
  BgColorsOutlined, 
  BellOutlined, 
  SafetyOutlined, 
  SettingOutlined, 
  InfoCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { useTheme } from '../../contexts/ThemeContext';
import type { MenuProps } from 'antd';

const { Sider, Content } = Layout;
const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

type SettingSection = 'connection' | 'storage' | 'theme' | 'notifications' | 'security' | 'advanced' | 'about';

interface ConnectionConfig {
  serverUrl: string;
  timeout: number;
  retries: number;
  apiKey?: string;
}

interface NotificationConfig {
  enableDesktop: boolean;
  enableEmail: boolean;
  enableQueryAlerts: boolean;
  enableSystemAlerts: boolean;
}

interface StorageConfig {
  currentPath: string;
  pathHistory: string[];
  lastUpdated: string;
}

interface PathInfo {
  path: string;
  exists: boolean;
  isDirectory: boolean;
  readable: boolean;
  writable: boolean;
  collectionsCount: number;
  sizeMb: number;
  error?: string;
}

const SettingsTab: React.FC = () => {
  const [selectedSection, setSelectedSection] = useState<SettingSection>('connection');
  const [connectionConfig, setConnectionConfig] = useState<ConnectionConfig>({
    serverUrl: 'http://localhost:8000',
    timeout: 30,
    retries: 3,
  });
  const [notificationConfig, setNotificationConfig] = useState<NotificationConfig>({
    enableDesktop: true,
    enableEmail: false,
    enableQueryAlerts: true,
    enableSystemAlerts: true,
  });
  const [connectionTesting, setConnectionTesting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'success' | 'error' | null>(null);
  const [storageConfig, setStorageConfig] = useState<StorageConfig>({
    currentPath: '',
    pathHistory: [],
    lastUpdated: '',
  });
  const [storageLoading, setStorageLoading] = useState(false);
  const [pathValidating, setPathValidating] = useState(false);
  const [customPath, setCustomPath] = useState('');
  const { theme, toggleTheme } = useTheme();

  const menuItems: MenuProps['items'] = [
    {
      key: 'connection',
      icon: <LinkOutlined />,
      label: '连接设置',
    },
    {
      key: 'storage',
      icon: <SettingOutlined />,
      label: '数据存储',
    },
    {
      key: 'theme',
      icon: <BgColorsOutlined />,
      label: '主题外观',
    },
    {
      key: 'notifications',
      icon: <BellOutlined />,
      label: '通知设置',
    },
    {
      key: 'security',
      icon: <SafetyOutlined />,
      label: '安全设置',
    },
    {
      key: 'advanced',
      icon: <SettingOutlined />,
      label: '高级设置',
    },
    {
      key: 'about',
      icon: <InfoCircleOutlined />,
      label: '关于',
    },
  ];

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    setSelectedSection(key as SettingSection);
  };

  const handleTestConnection = async () => {
    setConnectionTesting(true);
    setConnectionStatus(null);
    
    try {
      // TODO: 实现实际的连接测试逻辑
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // 模拟连接测试
      const isSuccess = Math.random() > 0.3;
      setConnectionStatus(isSuccess ? 'success' : 'error');
      
      if (isSuccess) {
        message.success('连接测试成功！');
      } else {
        message.error('连接测试失败，请检查配置');
      }
    } catch (error) {
      setConnectionStatus('error');
      message.error('连接测试失败');
    } finally {
      setConnectionTesting(false);
    }
  };

  const handleSaveSettings = () => {
    // TODO: 实现保存设置逻辑
    message.success('设置已保存');
  };

  // 数据存储相关函数
  const loadStorageConfig = async () => {
    try {
      setStorageLoading(true);
      console.log('开始加载存储配置...');

      const response = await fetch('http://localhost:8000/api/settings/storage');
      console.log('API响应状态:', response.status);

      if (response.ok) {
        const config = await response.json();
        console.log('加载的存储配置:', config);
        setStorageConfig(config);
        console.log('存储配置已设置到状态');
        message.success('存储配置加载成功');
      } else {
        console.error('API响应失败:', response.status, response.statusText);
        message.error(`加载存储配置失败: ${response.status}`);
      }
    } catch (error) {
      console.error('加载存储配置出错:', error);
      message.error(`加载存储配置失败: ${error.message}`);
    } finally {
      setStorageLoading(false);
    }
  };

  const validatePath = async (path: string): Promise<PathInfo | null> => {
    try {
      setPathValidating(true);
      const response = await fetch('http://localhost:8000/api/settings/storage/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });

      if (response.ok) {
        const result = await response.json();
        return result.path_info;
      }
      return null;
    } catch (error) {
      message.error('路径验证失败');
      return null;
    } finally {
      setPathValidating(false);
    }
  };

  const handleSetStoragePath = async (path: string) => {
    try {
      setStorageLoading(true);

      // 先验证路径
      const pathInfo = await validatePath(path);
      if (!pathInfo || !pathInfo.exists) {
        message.error('路径无效或不存在');
        return;
      }

      const response = await fetch('http://localhost:8000/api/settings/storage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });

      if (response.ok) {
        message.success('存储路径设置成功');
        await loadStorageConfig(); // 重新加载配置
        setCustomPath('');
      } else {
        const error = await response.json();
        message.error(error.detail || '设置存储路径失败');
      }
    } catch (error) {
      message.error('设置存储路径失败');
    } finally {
      setStorageLoading(false);
    }
  };

  const handleResetStorage = async () => {
    try {
      setStorageLoading(true);
      const response = await fetch('http://localhost:8000/api/settings/storage/reset', {
        method: 'POST',
      });

      if (response.ok) {
        message.success('已重置为默认配置');
        await loadStorageConfig();
      } else {
        message.error('重置配置失败');
      }
    } catch (error) {
      message.error('重置配置失败');
    } finally {
      setStorageLoading(false);
    }
  };

  const handleRemoveFromHistory = async (path: string) => {
    try {
      const response = await fetch('http://localhost:8000/api/settings/storage/history', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });

      if (response.ok) {
        message.success('已从历史记录中移除');
        await loadStorageConfig();
      } else {
        message.error('移除失败');
      }
    } catch (error) {
      message.error('移除失败');
    }
  };

  // 组件挂载时加载存储配置
  React.useEffect(() => {
    console.log('useEffect触发，selectedSection:', selectedSection);
    if (selectedSection === 'storage') {
      console.log('当前选中存储设置，开始加载配置');
      loadStorageConfig();
    }
  }, [selectedSection]);

  // 组件首次挂载时预加载存储配置
  React.useEffect(() => {
    console.log('组件首次挂载，预加载存储配置');
    loadStorageConfig();
  }, []);

  const renderConnectionSettings = () => (
    <Card title="🔗 ChromaDB连接设置">
      <Form layout="vertical">
        <Form.Item label="服务器地址" required>
          <Input
            value={connectionConfig.serverUrl}
            onChange={(e) => setConnectionConfig(prev => ({ ...prev, serverUrl: e.target.value }))}
            placeholder="http://localhost:8000"
            addonBefore="URL"
          />
        </Form.Item>
        
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="连接超时">
              <InputNumber
                value={connectionConfig.timeout}
                onChange={(value) => setConnectionConfig(prev => ({ ...prev, timeout: value || 30 }))}
                addonAfter="秒"
                min={1}
                max={300}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="最大重试次数">
              <InputNumber
                value={connectionConfig.retries}
                onChange={(value) => setConnectionConfig(prev => ({ ...prev, retries: value || 3 }))}
                min={0}
                max={10}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="API密钥 (可选)">
          <Input.Password
            value={connectionConfig.apiKey}
            onChange={(e) => setConnectionConfig(prev => ({ ...prev, apiKey: e.target.value }))}
            placeholder="输入API密钥"
          />
        </Form.Item>

        {connectionStatus && (
          <Alert
            message={connectionStatus === 'success' ? '连接成功' : '连接失败'}
            type={connectionStatus === 'success' ? 'success' : 'error'}
            icon={connectionStatus === 'success' ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
            style={{ marginBottom: 16 }}
          />
        )}
        
        <Form.Item>
          <Space>
            <Button 
              type="primary" 
              loading={connectionTesting}
              onClick={handleTestConnection}
            >
              测试连接
            </Button>
            <Button onClick={handleSaveSettings}>
              保存设置
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );

  const renderStorageSettings = () => (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card title="💾 数据存储设置"
            extra={
              <Button
                size="small"
                onClick={loadStorageConfig}
                loading={storageLoading}
              >
                刷新
              </Button>
            }>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Text strong>当前存储路径：</Text>
            <br />
            {storageLoading ? (
              <Text type="secondary">正在加载...</Text>
            ) : storageConfig?.currentPath ? (
              <>
                <Text code style={{ fontSize: '12px' }}>
                  {storageConfig.currentPath}
                </Text>
                <div style={{ marginTop: 4 }}>
                  <Text type="secondary" style={{ fontSize: '11px' }}>
                    状态：已加载 | 最后更新：{storageConfig.lastUpdated ?
                      new Date(storageConfig.lastUpdated).toLocaleString('zh-CN') :
                      '未知'
                    }
                  </Text>
                </div>
              </>
            ) : (
              <div>
                <Text type="warning">未能加载存储路径</Text>
                <br />
                <Button size="small" type="link" onClick={loadStorageConfig}>
                  点击重试
                </Button>
              </div>
            )}
          </div>

          <div>
            <Text strong>自定义存储路径：</Text>
            <Space.Compact style={{ width: '100%', marginTop: 8 }}>
              <Input
                placeholder="输入新的存储路径（绝对路径）"
                value={customPath}
                onChange={(e) => setCustomPath(e.target.value)}
                style={{ flex: 1 }}
              />
              <Button
                type="primary"
                loading={storageLoading}
                disabled={!customPath.trim()}
                onClick={() => handleSetStoragePath(customPath.trim())}
              >
                设置路径
              </Button>
            </Space.Compact>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              请输入绝对路径，如：/Users/username/Documents/chroma_data
            </Text>
          </div>

          <div>
            <Space>
              <Button
                onClick={handleResetStorage}
                loading={storageLoading}
              >
                重置为默认
              </Button>
              <Button
                onClick={loadStorageConfig}
                loading={storageLoading}
              >
                刷新配置
              </Button>
            </Space>
          </div>
        </Space>
      </Card>

      <Card title="📁 路径历史记录">
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          {storageConfig.pathHistory && storageConfig.pathHistory.length > 0 ? (
            storageConfig.pathHistory.map((path, index) => (
              <Card
                key={path}
                size="small"
                style={{
                  backgroundColor: path === storageConfig?.currentPath ? '#f6ffed' : undefined,
                  border: path === storageConfig?.currentPath ? '1px solid #52c41a' : undefined,
                }}
              >
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Text code style={{ fontSize: '12px', flex: 1 }}>
                      {path}
                    </Text>
                    <Space>
                      {path === storageConfig?.currentPath && (
                        <Text type="success" style={{ fontSize: '12px' }}>
                          当前使用
                        </Text>
                      )}
                      <Button
                        size="small"
                        type="link"
                        disabled={path === storageConfig?.currentPath}
                        onClick={() => handleSetStoragePath(path)}
                      >
                        切换
                      </Button>
                      {path !== storageConfig?.currentPath && (
                        <Button
                          size="small"
                          type="link"
                          danger
                          onClick={() => handleRemoveFromHistory(path)}
                        >
                          移除
                        </Button>
                      )}
                    </Space>
                  </div>
                </Space>
              </Card>
            ))
          ) : (
            <Text type="secondary">暂无历史记录</Text>
          )}
        </Space>
      </Card>

      <Card title="ℹ️ 存储信息">
        <Space direction="vertical" size="small">
          <Text>
            <Text strong>最后更新：</Text>
            {storageConfig?.lastUpdated ?
              new Date(storageConfig.lastUpdated).toLocaleString('zh-CN') :
              '未知'
            }
          </Text>
          <Alert
            message="数据安全提示"
            description="更改存储路径前，请确保新路径有足够的存储空间和读写权限。建议定期备份重要数据。"
            type="info"
            showIcon
          />
        </Space>
      </Card>
    </Space>
  );

  const renderThemeSettings = () => (
    <Card title="🎨 主题外观设置">
      <Form layout="vertical">
        <Form.Item label="主题模式">
          <Radio.Group value={theme} onChange={(e) => {
            if (e.target.value !== theme) {
              toggleTheme();
            }
          }}>
            <Radio.Button value="light">🌞 浅色模式</Radio.Button>
            <Radio.Button value="dark">🌙 深色模式</Radio.Button>
          </Radio.Group>
        </Form.Item>
        
        <Form.Item label="主色调">
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {[
              { name: '蓝色', color: '#3b82f6' },
              { name: '绿色', color: '#10b981' },
              { name: '紫色', color: '#8b5cf6' },
              { name: '红色', color: '#ef4444' },
              { name: '橙色', color: '#f59e0b' },
              { name: '青色', color: '#06b6d4' },
            ].map((item) => (
              <Button
                key={item.name}
                style={{
                  backgroundColor: item.color,
                  borderColor: item.color,
                  color: 'white',
                  marginBottom: 8,
                }}
              >
                {item.name}
              </Button>
            ))}
          </div>
        </Form.Item>

        <Form.Item label="界面缩放">
          <Slider
            min={80}
            max={120}
            defaultValue={100}
            tooltip={{ formatter: (value) => `${value}%` }}
            marks={{
              80: '80%',
              90: '90%',
              100: '100%',
              110: '110%',
              120: '120%',
            }}
          />
        </Form.Item>

        <Form.Item>
          <Button type="primary" onClick={handleSaveSettings}>
            保存设置
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );

  const renderNotificationSettings = () => (
    <Card title="🔔 通知设置">
      <Form layout="vertical">
        <Form.Item label="桌面通知">
          <Switch
            checked={notificationConfig.enableDesktop}
            onChange={(checked) => setNotificationConfig(prev => ({ ...prev, enableDesktop: checked }))}
          />
          <Text type="secondary" style={{ marginLeft: 8 }}>
            在浏览器中显示系统通知
          </Text>
        </Form.Item>

        <Form.Item label="邮件通知">
          <Switch
            checked={notificationConfig.enableEmail}
            onChange={(checked) => setNotificationConfig(prev => ({ ...prev, enableEmail: checked }))}
          />
          <Text type="secondary" style={{ marginLeft: 8 }}>
            通过邮件接收重要通知
          </Text>
        </Form.Item>

        <Divider />

        <Form.Item label="查询提醒">
          <Switch
            checked={notificationConfig.enableQueryAlerts}
            onChange={(checked) => setNotificationConfig(prev => ({ ...prev, enableQueryAlerts: checked }))}
          />
          <Text type="secondary" style={{ marginLeft: 8 }}>
            查询完成或出错时通知
          </Text>
        </Form.Item>

        <Form.Item label="系统提醒">
          <Switch
            checked={notificationConfig.enableSystemAlerts}
            onChange={(checked) => setNotificationConfig(prev => ({ ...prev, enableSystemAlerts: checked }))}
          />
          <Text type="secondary" style={{ marginLeft: 8 }}>
            系统错误或维护通知
          </Text>
        </Form.Item>

        <Form.Item>
          <Button type="primary" onClick={handleSaveSettings}>
            保存设置
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );

  const renderSecuritySettings = () => (
    <Card title="🔒 安全设置">
      <Alert
        message="安全提示"
        description="为了保护您的数据安全，请定期更换密码并启用双因素认证。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      
      <Form layout="vertical">
        <Form.Item label="会话超时">
          <Select defaultValue="30" style={{ width: 200 }}>
            <Option value="15">15分钟</Option>
            <Option value="30">30分钟</Option>
            <Option value="60">1小时</Option>
            <Option value="120">2小时</Option>
            <Option value="0">永不超时</Option>
          </Select>
        </Form.Item>

        <Form.Item label="数据备份">
          <Space direction="vertical">
            <Switch defaultChecked />
            <Text type="secondary">自动备份对话记录和设置</Text>
          </Space>
        </Form.Item>

        <Form.Item>
          <Button type="primary" onClick={handleSaveSettings}>
            保存设置
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );

  const renderAdvancedSettings = () => (
    <Card title="⚙️ 高级设置">
      <Alert
        message="警告"
        description="高级设置可能会影响系统性能，请谨慎修改。"
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
      />
      
      <Form layout="vertical">
        <Form.Item label="调试模式">
          <Switch />
          <Text type="secondary" style={{ marginLeft: 8 }}>
            启用详细的调试日志
          </Text>
        </Form.Item>

        <Form.Item label="缓存大小">
          <InputNumber
            defaultValue={100}
            min={10}
            max={1000}
            addonAfter="MB"
            style={{ width: 200 }}
          />
        </Form.Item>

        <Form.Item label="最大并发查询">
          <InputNumber
            defaultValue={5}
            min={1}
            max={20}
            style={{ width: 200 }}
          />
        </Form.Item>

        <Form.Item>
          <Button type="primary" onClick={handleSaveSettings}>
            保存设置
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );

  const renderAbout = () => (
    <Card title="ℹ️ 关于 ChromaDB Manager">
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Title level={4}>ChromaDB Web Manager</Title>
          <Paragraph>
            版本: 1.0.0
          </Paragraph>
          <Paragraph>
            一个现代化的 ChromaDB 管理界面，提供集合管理、智能查询、数据分析等功能。
          </Paragraph>
        </div>

        <Divider />

        <div>
          <Title level={5}>技术栈</Title>
          <Paragraph>
            <ul>
              <li>前端: React 18 + TypeScript + Vite</li>
              <li>UI框架: Ant Design</li>
              <li>后端: FastAPI + ChromaDB</li>
              <li>状态管理: React Context</li>
            </ul>
          </Paragraph>
        </div>

        <Divider />

        <div>
          <Title level={5}>更新日志</Title>
          <Paragraph>
            <ul>
              <li>v1.0.0: 初始版本发布</li>
              <li>- 集合管理功能</li>
              <li>- 智能查询界面</li>
              <li>- 数据分析面板</li>
              <li>- 主题切换支持</li>
            </ul>
          </Paragraph>
        </div>

        <div>
          <Space>
            <Button type="primary" href="https://github.com/lihongwen/chromaquery" target="_blank">
              GitHub 仓库
            </Button>
            <Button href="https://docs.trychroma.com/" target="_blank">
              官方文档
            </Button>
          </Space>
        </div>
      </Space>
    </Card>
  );

  const renderContent = () => {
    switch (selectedSection) {
      case 'connection':
        return renderConnectionSettings();
      case 'storage':
        return renderStorageSettings();
      case 'theme':
        return renderThemeSettings();
      case 'notifications':
        return renderNotificationSettings();
      case 'security':
        return renderSecuritySettings();
      case 'advanced':
        return renderAdvancedSettings();
      case 'about':
        return renderAbout();
      default:
        return renderConnectionSettings();
    }
  };

  return (
    <Layout style={{ height: 'calc(100vh - 64px)', minHeight: '500px' }}>
      <Sider
        width={250}
        theme="light"
        style={{
          backgroundColor: 'var(--ant-color-bg-container)',
          borderRight: '1px solid var(--ant-color-border)',
          height: '100%',
          overflow: 'auto',
        }}
      >
        <Menu
          mode="inline"
          selectedKeys={[selectedSection]}
          onClick={handleMenuClick}
          items={menuItems}
          style={{ borderRight: 0 }}
        />
      </Sider>

      <Content style={{ padding: 24, height: '100%', overflow: 'auto' }}>
        {renderContent()}
      </Content>
    </Layout>
  );
};

export default SettingsTab;