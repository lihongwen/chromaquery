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

type SettingSection = 'connection' | 'theme' | 'notifications' | 'security' | 'advanced' | 'about';

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
  const { theme, toggleTheme } = useTheme();

  const menuItems: MenuProps['items'] = [
    {
      key: 'connection',
      icon: <LinkOutlined />,
      label: '连接设置',
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
            <Text type="secondary">自动备份查询历史和设置</Text>
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
    <Layout style={{ height: 'calc(100vh - 120px)', minHeight: '500px' }}>
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