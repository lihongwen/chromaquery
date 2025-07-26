import React, { useState, useEffect } from 'react';
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
  Alert,
  Spin,
  Tag,
  List,
  Badge,
  Tooltip
} from 'antd';
import {
  LinkOutlined,
  BgColorsOutlined,
  BellOutlined,
  SafetyOutlined,
  SettingOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  RobotOutlined,
  CloudOutlined,
  DesktopOutlined,
  ReloadOutlined,
  PlayCircleOutlined
} from '@ant-design/icons';
import axios from 'axios';
import { useTheme } from '../../contexts/ThemeContext';
import type { MenuProps } from 'antd';

const { Sider, Content } = Layout;
const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

type SettingSection = 'connection' | 'models' | 'theme' | 'notifications' | 'security' | 'advanced' | 'about';

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

interface EmbeddingModel {
  name: string;
  description: string;
  dimension?: number;
  recommended: boolean;
  available: boolean;
}

interface EmbeddingProvider {
  name: string;
  description: string;
  models: EmbeddingModel[];
  available: boolean;
  service_url?: string;
  error?: string;
}

interface EmbeddingConfig {
  default_provider: string;
  alibaba_config?: {
    model: string;
    dimension: number;
  };
  ollama_config?: {
    model: string;
    base_url: string;
    timeout: number;
  };
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

  // 模型设置相关状态
  const [embeddingProviders, setEmbeddingProviders] = useState<Record<string, EmbeddingProvider>>({});
  const [embeddingConfig, setEmbeddingConfig] = useState<EmbeddingConfig>({
    default_provider: 'alibaba',
    alibaba_config: {
      model: 'text-embedding-v4',
      dimension: 1024
    },
    ollama_config: {
      model: 'mxbai-embed-large',
      base_url: 'http://localhost:11434',
      timeout: 60
    }
  });
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelTesting, setModelTesting] = useState(false);
  const [modelTestResult, setModelTestResult] = useState<{success: boolean; message: string} | null>(null);

  const { theme, toggleTheme } = useTheme();

  // 组件加载时初始化数据
  useEffect(() => {
    if (selectedSection === 'models') {
      loadEmbeddingModels();
      loadEmbeddingConfig();
    }
  }, []);

  const menuItems: MenuProps['items'] = [
    {
      key: 'connection',
      icon: <LinkOutlined />,
      label: '连接设置',
    },
    {
      key: 'models',
      icon: <RobotOutlined />,
      label: '模型设置',
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
    // 当切换到模型设置时，加载模型数据
    if (key === 'models') {
      loadEmbeddingModels();
      loadEmbeddingConfig();
    }
  };

  // 加载嵌入模型列表
  const loadEmbeddingModels = async () => {
    setModelsLoading(true);
    try {
      const response = await axios.get('/api/embedding-models');
      setEmbeddingProviders(response.data);
    } catch (error) {
      console.error('加载模型列表失败:', error);
      message.error('加载模型列表失败');
    } finally {
      setModelsLoading(false);
    }
  };

  // 加载嵌入模型配置
  const loadEmbeddingConfig = async () => {
    try {
      const response = await axios.get('/api/embedding-config');
      if (response.data.current) {
        setEmbeddingConfig(response.data.full_config);
      }
    } catch (error) {
      console.error('加载模型配置失败:', error);
      message.error('加载模型配置失败');
    }
  };

  // 保存嵌入模型配置
  const saveEmbeddingConfig = async () => {
    try {
      await axios.post('/api/embedding-config', embeddingConfig);
      message.success('模型配置已保存');
    } catch (error) {
      console.error('保存模型配置失败:', error);
      message.error('保存模型配置失败');
    }
  };

  // 测试嵌入模型配置
  const testEmbeddingConfig = async (provider: string) => {
    setModelTesting(true);
    setModelTestResult(null);

    try {
      const config = provider === 'ollama' ? embeddingConfig.ollama_config : embeddingConfig.alibaba_config;
      const response = await axios.post('/api/embedding-config/test', {
        provider,
        config
      });

      setModelTestResult({
        success: response.data.success,
        message: response.data.message
      });

      if (response.data.success) {
        message.success('模型测试成功！');
      } else {
        message.error('模型测试失败');
      }
    } catch (error) {
      setModelTestResult({
        success: false,
        message: '测试请求失败'
      });
      message.error('模型测试失败');
    } finally {
      setModelTesting(false);
    }
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











  // 渲染模型设置
  const renderModelSettings = () => (
    <div>
      <Card title="🤖 嵌入模型设置" style={{ marginBottom: 16 }}>
        <Spin spinning={modelsLoading}>
          <Form layout="vertical">
            <Form.Item label="默认嵌入模型提供商">
              <Radio.Group
                value={embeddingConfig.default_provider}
                onChange={(e) => setEmbeddingConfig(prev => ({ ...prev, default_provider: e.target.value }))}
              >
                <Radio.Button value="alibaba">
                  <CloudOutlined /> 阿里云百炼
                </Radio.Button>
                <Radio.Button value="ollama">
                  <DesktopOutlined /> Ollama本地模型
                </Radio.Button>
              </Radio.Group>
            </Form.Item>

            {modelTestResult && (
              <Alert
                message={modelTestResult.success ? '测试成功' : '测试失败'}
                description={modelTestResult.message}
                type={modelTestResult.success ? 'success' : 'error'}
                style={{ marginBottom: 16 }}
                closable
                onClose={() => setModelTestResult(null)}
              />
            )}

            <Form.Item>
              <Space>
                <Button
                  type="primary"
                  onClick={saveEmbeddingConfig}
                >
                  保存配置
                </Button>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => {
                    loadEmbeddingModels();
                    loadEmbeddingConfig();
                  }}
                >
                  刷新
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Spin>
      </Card>

      {/* 阿里云模型配置 */}
      <Card
        title={
          <Space>
            <CloudOutlined />
            阿里云百炼模型配置
            <Badge
              status={embeddingProviders.alibaba?.available ? 'success' : 'error'}
              text={embeddingProviders.alibaba?.available ? '可用' : '不可用'}
            />
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Form layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="模型名称">
                <Select
                  value={embeddingConfig.alibaba_config?.model}
                  onChange={(value) => setEmbeddingConfig(prev => ({
                    ...prev,
                    alibaba_config: { ...prev.alibaba_config!, model: value }
                  }))}
                  style={{ width: '100%' }}
                >
                  {embeddingProviders.alibaba?.models?.map(model => (
                    <Select.Option key={model.name} value={model.name}>
                      <Space>
                        {model.name}
                        {model.recommended && <Tag color="blue">推荐</Tag>}
                      </Space>
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="向量维度">
                <InputNumber
                  value={embeddingConfig.alibaba_config?.dimension}
                  onChange={(value) => setEmbeddingConfig(prev => ({
                    ...prev,
                    alibaba_config: { ...prev.alibaba_config!, dimension: value || 1024 }
                  }))}
                  min={64}
                  max={2048}
                  step={64}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Button
              icon={<PlayCircleOutlined />}
              loading={modelTesting}
              onClick={() => testEmbeddingConfig('alibaba')}
            >
              测试阿里云模型
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* Ollama模型配置 */}
      <Card
        title={
          <Space>
            <DesktopOutlined />
            Ollama本地模型配置
            <Badge
              status={embeddingProviders.ollama?.available ? 'success' : 'error'}
              text={embeddingProviders.ollama?.available ? '可用' : '不可用'}
            />
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        {!embeddingProviders.ollama?.available && embeddingProviders.ollama?.error && (
          <Alert
            message="Ollama服务不可用"
            description={embeddingProviders.ollama.error}
            type="warning"
            style={{ marginBottom: 16 }}
          />
        )}

        <Form layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="模型名称">
                <Select
                  value={embeddingConfig.ollama_config?.model}
                  onChange={(value) => setEmbeddingConfig(prev => ({
                    ...prev,
                    ollama_config: { ...prev.ollama_config!, model: value }
                  }))}
                  style={{ width: '100%' }}
                  showSearch
                  placeholder="选择或输入模型名称"
                  optionFilterProp="children"
                  mode="combobox"
                >
                  {embeddingProviders.ollama?.models?.map(model => (
                    <Select.Option key={model.name} value={model.name}>
                      <Space>
                        {model.name}
                        {model.recommended && <Tag color="blue">推荐</Tag>}
                        {model.available && <Tag color="green">已安装</Tag>}
                      </Space>
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="服务器地址">
                <Input
                  value={embeddingConfig.ollama_config?.base_url}
                  onChange={(e) => setEmbeddingConfig(prev => ({
                    ...prev,
                    ollama_config: { ...prev.ollama_config!, base_url: e.target.value }
                  }))}
                  placeholder="http://localhost:11434"
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="请求超时时间">
            <InputNumber
              value={embeddingConfig.ollama_config?.timeout}
              onChange={(value) => setEmbeddingConfig(prev => ({
                ...prev,
                ollama_config: { ...prev.ollama_config!, timeout: value || 60 }
              }))}
              min={10}
              max={300}
              addonAfter="秒"
              style={{ width: 200 }}
            />
          </Form.Item>

          <Form.Item>
            <Button
              icon={<PlayCircleOutlined />}
              loading={modelTesting}
              onClick={() => testEmbeddingConfig('ollama')}
              disabled={!embeddingProviders.ollama?.available}
            >
              测试Ollama模型
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* 可用模型列表 */}
      {embeddingProviders.ollama?.available && embeddingProviders.ollama.available_models && (
        <Card title="📋 可用的Ollama嵌入模型" style={{ marginBottom: 16 }}>
          <List
            dataSource={embeddingProviders.ollama.available_models}
            renderItem={(model: any) => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <Space>
                      {model.name}
                      <Tag color="green">已安装</Tag>
                    </Space>
                  }
                  description={`大小: ${(model.size / 1024 / 1024 / 1024).toFixed(2)} GB`}
                />
                <Button
                  size="small"
                  onClick={() => setEmbeddingConfig(prev => ({
                    ...prev,
                    ollama_config: { ...prev.ollama_config!, model: model.name }
                  }))}
                >
                  使用此模型
                </Button>
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  );

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
      case 'models':
        return renderModelSettings();
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