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
  Tooltip,
  Table,
  Modal,
  Popconfirm,
  Statistic
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
  PlayCircleOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  UserOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  MessageOutlined
} from '@ant-design/icons';
import axios from 'axios';
import { useTheme } from '../../contexts/ThemeContext';
import type { MenuProps } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { roleApiService, type Role, type CreateRoleRequest, type UpdateRoleRequest } from '../../services/roleApi';

const { Sider, Content } = Layout;
const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;

// 工具函数：掩码显示API密钥
const maskApiKey = (apiKey: string): string => {
  if (!apiKey || apiKey.length <= 8) {
    return apiKey;
  }
  const start = apiKey.substring(0, 4);
  const end = apiKey.substring(apiKey.length - 4);
  return `${start}${'*'.repeat(Math.min(20, apiKey.length - 8))}${end}`;
};

// 工具函数：切换API密钥显示状态
const toggleApiKeyVisibility = (key: string, visible: Record<string, boolean>, setVisible: (value: Record<string, boolean>) => void) => {
  setVisible(prev => ({ ...prev, [key]: !prev[key] }));
};

type SettingSection = 'connection' | 'models' | 'llm' | 'roles' | 'theme' | 'notifications' | 'security' | 'advanced' | 'about';

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
    api_key?: string;
    verified?: boolean;
    last_verified?: string;
  };
  ollama_config?: {
    model: string;
    base_url: string;
    timeout: number;
    verified?: boolean;
    last_verified?: string;
  };
}

interface LLMModel {
  name: string;
  display_name: string;
  description: string;
  max_tokens: number;
  recommended: boolean;
}

interface LLMProviderConfig {
  api_key: string;
  api_endpoint: string;
  model: string;
  models: LLMModel[];
  verified: boolean;
  last_verified?: string;
  verification_error?: string;
}

interface LLMConfig {
  default_provider: string;
  deepseek?: LLMProviderConfig;
  alibaba?: LLMProviderConfig;
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
      dimension: 1024,
      api_key: '',
      verified: false
    },
    ollama_config: {
      model: 'mxbai-embed-large',
      base_url: 'http://localhost:11434',
      timeout: 60,
      verified: false
    }
  });

  // LLM配置相关状态
  const [llmConfig, setLlmConfig] = useState<LLMConfig>({
    default_provider: 'alibaba',
    deepseek: {
      api_key: '',
      api_endpoint: 'https://api.deepseek.com',
      model: 'deepseek-chat',
      models: [],
      verified: false
    },
    alibaba: {
      api_key: '',
      api_endpoint: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
      model: 'qwen-plus',
      models: [],
      verified: false
    }
  });
  const [llmTesting, setLlmTesting] = useState<Record<string, boolean>>({});
  const [llmTestResults, setLlmTestResults] = useState<Record<string, any>>({});

  // API密钥显示状态
  const [apiKeyVisible, setApiKeyVisible] = useState<Record<string, boolean>>({
    'llm-deepseek': false,
    'llm-alibaba': false,
    'embedding-alibaba': false,
    'embedding-ollama': false
  });
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelTesting, setModelTesting] = useState(false);
  const [modelTestResult, setModelTestResult] = useState<{success: boolean; message: string} | null>(null);
  const [verificationStatus, setVerificationStatus] = useState<Record<string, any>>({});

  // 角色管理相关状态
  const [roles, setRoles] = useState<Role[]>([]);
  const [rolesLoading, setRolesLoading] = useState(false);
  const [roleModalVisible, setRoleModalVisible] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [viewingRole, setViewingRole] = useState<Role | null>(null);
  const [roleForm] = Form.useForm();

  const { theme, toggleTheme } = useTheme();

  // 组件加载时初始化数据
  useEffect(() => {
    if (selectedSection === 'models') {
      loadEmbeddingModels();
      loadEmbeddingConfig();
      loadVerificationStatus();
    } else if (selectedSection === 'roles') {
      loadRoles();
    }
  }, [selectedSection]);

  const menuItems: MenuProps['items'] = [
    {
      key: 'connection',
      icon: <LinkOutlined />,
      label: '连接设置',
    },
    {
      key: 'models',
      icon: <RobotOutlined />,
      label: '嵌入模型',
    },
    {
      key: 'llm',
      icon: <RobotOutlined />,
      label: 'LLM模型',
    },
    {
      key: 'roles',
      icon: <UserOutlined />,
      label: '角色管理',
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
    // 当切换到LLM设置时，加载LLM数据
    if (key === 'llm') {
      loadLlmConfig();
      loadLlmModels();
    }
    // 当切换到角色管理时，加载角色数据
    if (key === 'roles') {
      loadRoles();
    }
  };

  // 加载嵌入模型列表（用于设置页面，包括未验证的）
  const loadEmbeddingModels = async () => {
    setModelsLoading(true);
    try {
      const response = await axios.get('/api/embedding-models/all');
      setEmbeddingProviders(response.data);
    } catch (error) {
      console.error('加载模型列表失败:', error);
      message.error('加载模型列表失败');
    } finally {
      setModelsLoading(false);
    }
  };

  // 加载验证状态
  const loadVerificationStatus = async () => {
    try {
      const response = await axios.get('/api/embedding-providers/status');
      setVerificationStatus(response.data);
    } catch (error) {
      console.error('加载验证状态失败:', error);
    }
  };

  // 加载嵌入模型配置
  const loadEmbeddingConfig = async () => {
    try {
      const response = await axios.get('/api/embedding-config');
      if (response.data.current) {
        setEmbeddingConfig(response.data.full_config);

        // 如果有API密钥，设置为隐藏状态
        setApiKeyVisible(prev => ({
          ...prev,
          'embedding-alibaba': false,
          'embedding-ollama': false
        }));
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

  // 加载LLM配置
  const loadLlmConfig = async () => {
    try {
      const response = await axios.get('/api/llm-config');
      if (response.data.current) {
        setLlmConfig(response.data.full_config);

        // 如果有API密钥，设置为隐藏状态
        const config = response.data.full_config;
        setApiKeyVisible(prev => ({
          ...prev,
          'llm-deepseek': false,
          'llm-alibaba': false
        }));
      }
    } catch (error) {
      console.error('加载LLM配置失败:', error);
      message.error('加载LLM配置失败');
    }
  };

  // 加载LLM模型列表
  const loadLlmModels = async () => {
    try {
      const response = await axios.get('/api/llm-models');
      // 更新LLM配置中的模型列表
      setLlmConfig(prev => ({
        ...prev,
        deepseek: {
          ...prev.deepseek!,
          models: response.data.models.deepseek || []
        },
        alibaba: {
          ...prev.alibaba!,
          models: response.data.models.alibaba || []
        }
      }));
    } catch (error) {
      console.error('加载LLM模型列表失败:', error);
      message.error('加载LLM模型列表失败');
    }
  };

  // 保存LLM配置
  const saveLlmConfig = async () => {
    try {
      await axios.post('/api/llm-config', {
        default_provider: llmConfig.default_provider,
        deepseek_config: llmConfig.deepseek,
        alibaba_config: llmConfig.alibaba
      });
      message.success('LLM配置已保存');
    } catch (error) {
      console.error('保存LLM配置失败:', error);
      message.error('保存LLM配置失败');
    }
  };

  // 测试LLM配置
  const testLlmConfig = async (provider: string) => {
    setLlmTesting(prev => ({ ...prev, [provider]: true }));
    setLlmTestResults(prev => ({ ...prev, [provider]: null }));

    try {
      const config = provider === 'deepseek' ? llmConfig.deepseek : llmConfig.alibaba;
      const response = await axios.post('/api/llm-config/test', {
        provider,
        config
      });

      setLlmTestResults(prev => ({
        ...prev,
        [provider]: {
          success: response.data.success,
          message: response.data.message
        }
      }));

      if (response.data.success) {
        message.success(`${provider === 'deepseek' ? 'DeepSeek' : '阿里云'} LLM测试成功！`);
      } else {
        message.error(`${provider === 'deepseek' ? 'DeepSeek' : '阿里云'} LLM测试失败：${response.data.message}`);
      }
    } catch (error) {
      console.error(`测试${provider} LLM配置失败:`, error);
      message.error(`测试${provider === 'deepseek' ? 'DeepSeek' : '阿里云'} LLM配置失败`);
      setLlmTestResults(prev => ({
        ...prev,
        [provider]: {
          success: false,
          message: '网络错误或服务器异常'
        }
      }));
    } finally {
      setLlmTesting(prev => ({ ...prev, [provider]: false }));
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

  // 验证提供商配置
  const verifyProvider = async (provider: string) => {
    setModelTesting(true);
    setModelTestResult(null);

    try {
      let requestData: any = {};

      if (provider === 'alibaba') {
        const apiKey = embeddingConfig.alibaba_config?.api_key;
        if (!apiKey || !apiKey.trim()) {
          message.error('请先输入API密钥');
          return;
        }
        requestData = {
          api_key: apiKey,
          model: embeddingConfig.alibaba_config?.model || 'text-embedding-v4'
        };
      } else if (provider === 'ollama') {
        requestData = {
          model: embeddingConfig.ollama_config?.model || 'mxbai-embed-large',
          base_url: embeddingConfig.ollama_config?.base_url || 'http://localhost:11434'
        };
      }

      const response = await axios.post(`/api/embedding-providers/${provider}/verify`, requestData);

      setModelTestResult({
        success: response.data.success,
        message: response.data.message
      });

      if (response.data.success) {
        message.success('验证成功！');
        // 重新加载验证状态
        await loadVerificationStatus();
        await loadEmbeddingConfig();
      } else {
        message.error('验证失败');
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || '验证请求失败';
      setModelTestResult({
        success: false,
        message: errorMessage
      });
      message.error(errorMessage);
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

  // 角色管理相关函数
  const loadRoles = async () => {
    setRolesLoading(true);
    try {
      const data = await roleApiService.getRoles();
      setRoles(data);
    } catch (error) {
      message.error('加载角色列表失败');
    } finally {
      setRolesLoading(false);
    }
  };

  const handleCreateRole = () => {
    setEditingRole(null);
    roleForm.resetFields();
    roleForm.setFieldsValue({ is_active: true });
    setRoleModalVisible(true);
  };

  const handleEditRole = (role: Role) => {
    setEditingRole(role);
    roleForm.setFieldsValue(role);
    setRoleModalVisible(true);
  };

  const handleViewRole = (role: Role) => {
    setViewingRole(role);
    setViewModalVisible(true);
  };

  const handleDeleteRole = async (roleId: string) => {
    try {
      await roleApiService.deleteRole(roleId);
      message.success('删除角色成功');
      loadRoles();
    } catch (error) {
      message.error('删除角色失败');
    }
  };

  const handleSubmitRole = async () => {
    try {
      const values = await roleForm.validateFields();

      if (editingRole) {
        // 更新角色
        await roleApiService.updateRole(editingRole.id, values as UpdateRoleRequest);
        message.success('更新角色成功');
      } else {
        // 创建角色
        await roleApiService.createRole(values as CreateRoleRequest);
        message.success('创建角色成功');
      }

      setRoleModalVisible(false);
      loadRoles();
    } catch (error) {
      message.error(editingRole ? '更新角色失败' : '创建角色失败');
    }
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
          <Form.Item
            label="API密钥"
            required
            help={
              <Space direction="vertical" size={4}>
                <span>请输入阿里云百炼平台的API密钥</span>
                {verificationStatus.alibaba?.verified && (
                  <span style={{ color: '#52c41a' }}>
                    ✓ 已验证 {verificationStatus.alibaba.last_verified &&
                      `(${new Date(verificationStatus.alibaba.last_verified).toLocaleString()})`}
                  </span>
                )}
                {verificationStatus.alibaba?.error && (
                  <span style={{ color: '#ff4d4f' }}>
                    ✗ {verificationStatus.alibaba.error}
                  </span>
                )}
              </Space>
            }
          >
            <Input.Password
              value={apiKeyVisible['embedding-alibaba']
                ? embeddingConfig.alibaba_config?.api_key
                : maskApiKey(embeddingConfig.alibaba_config?.api_key || '')}
              onChange={(e) => {
                // 如果当前是隐藏状态，先显示
                if (!apiKeyVisible['embedding-alibaba']) {
                  setApiKeyVisible(prev => ({ ...prev, 'embedding-alibaba': true }));
                }
                setEmbeddingConfig(prev => ({
                  ...prev,
                  alibaba_config: { ...prev.alibaba_config!, api_key: e.target.value }
                }));
              }}
              placeholder="请输入阿里云API密钥"
              style={{ width: '100%' }}
              addonAfter={
                <Button
                  type="text"
                  size="small"
                  icon={apiKeyVisible['embedding-alibaba'] ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                  onClick={() => toggleApiKeyVisibility('embedding-alibaba', apiKeyVisible, setApiKeyVisible)}
                />
              }
            />
          </Form.Item>

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
            <Space>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                loading={modelTesting}
                onClick={() => verifyProvider('alibaba')}
                disabled={!embeddingConfig.alibaba_config?.api_key?.trim()}
              >
                验证API密钥
              </Button>
              {verificationStatus.alibaba?.verified && (
                <Tag color="success">已验证</Tag>
              )}
            </Space>
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
            <Space>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                loading={modelTesting}
                onClick={() => verifyProvider('ollama')}
                disabled={!embeddingProviders.ollama?.available}
              >
                验证Ollama配置
              </Button>
              {verificationStatus.ollama?.verified && (
                <Tag color="success">已验证</Tag>
              )}
              {verificationStatus.ollama?.error && (
                <Tag color="error">验证失败</Tag>
              )}
            </Space>
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

  // 渲染LLM设置
  const renderLlmSettings = () => (
    <div>
      <Card title="🤖 LLM模型设置" style={{ marginBottom: 16 }}>
        <Form layout="vertical">
          <Form.Item label="默认LLM提供商">
            <Radio.Group
              value={llmConfig.default_provider}
              onChange={(e) => setLlmConfig(prev => ({ ...prev, default_provider: e.target.value }))}
            >
              <Radio.Button value="alibaba">
                <CloudOutlined /> 阿里云通义千问
              </Radio.Button>
              <Radio.Button value="deepseek">
                <RobotOutlined /> DeepSeek
              </Radio.Button>
            </Radio.Group>
          </Form.Item>

          <Divider />

          {/* 阿里云LLM配置 */}
          <Card
            title="阿里云通义千问配置"
            size="small"
            style={{ marginBottom: 16 }}
            extra={
              <Button
                size="small"
                loading={llmTesting.alibaba}
                onClick={() => testLlmConfig('alibaba')}
                disabled={!llmConfig.alibaba?.api_key}
              >
                测试连接
              </Button>
            }
          >
            <Form layout="vertical">
              <Form.Item label="API密钥" required>
                <Input.Password
                  value={apiKeyVisible['llm-alibaba']
                    ? llmConfig.alibaba?.api_key || ''
                    : maskApiKey(llmConfig.alibaba?.api_key || '')}
                  onChange={(e) => {
                    // 如果当前是隐藏状态，先显示
                    if (!apiKeyVisible['llm-alibaba']) {
                      setApiKeyVisible(prev => ({ ...prev, 'llm-alibaba': true }));
                    }
                    setLlmConfig(prev => ({
                      ...prev,
                      alibaba: { ...prev.alibaba!, api_key: e.target.value }
                    }));
                  }}
                  placeholder="请输入阿里云DashScope API密钥"
                  addonAfter={
                    <Button
                      type="text"
                      size="small"
                      icon={apiKeyVisible['llm-alibaba'] ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                      onClick={() => toggleApiKeyVisibility('llm-alibaba', apiKeyVisible, setApiKeyVisible)}
                    />
                  }
                />
              </Form.Item>

              <Form.Item label="API端点">
                <Input
                  value={llmConfig.alibaba?.api_endpoint || ''}
                  onChange={(e) => setLlmConfig(prev => ({
                    ...prev,
                    alibaba: { ...prev.alibaba!, api_endpoint: e.target.value }
                  }))}
                  placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
                />
              </Form.Item>

              <Form.Item label="模型">
                <Select
                  value={llmConfig.alibaba?.model || ''}
                  onChange={(value) => setLlmConfig(prev => ({
                    ...prev,
                    alibaba: { ...prev.alibaba!, model: value }
                  }))}
                  placeholder="选择模型"
                >
                  {llmConfig.alibaba?.models?.map((model) => (
                    <Select.Option key={model.name} value={model.name}>
                      <div>
                        <strong>{model.display_name}</strong>
                        {model.recommended && <Tag color="green" style={{ marginLeft: 8 }}>推荐</Tag>}
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          {model.description}
                        </div>
                      </div>
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>

              {llmTestResults.alibaba && (
                <Alert
                  type={llmTestResults.alibaba.success ? 'success' : 'error'}
                  message={llmTestResults.alibaba.message}
                  style={{ marginTop: 8 }}
                />
              )}
            </Form>
          </Card>

          {/* DeepSeek配置 */}
          <Card
            title="DeepSeek配置"
            size="small"
            style={{ marginBottom: 16 }}
            extra={
              <Button
                size="small"
                loading={llmTesting.deepseek}
                onClick={() => testLlmConfig('deepseek')}
                disabled={!llmConfig.deepseek?.api_key}
              >
                测试连接
              </Button>
            }
          >
            <Form layout="vertical">
              <Form.Item label="API密钥" required>
                <Input.Password
                  value={apiKeyVisible['llm-deepseek']
                    ? llmConfig.deepseek?.api_key || ''
                    : maskApiKey(llmConfig.deepseek?.api_key || '')}
                  onChange={(e) => {
                    // 如果当前是隐藏状态，先显示
                    if (!apiKeyVisible['llm-deepseek']) {
                      setApiKeyVisible(prev => ({ ...prev, 'llm-deepseek': true }));
                    }
                    setLlmConfig(prev => ({
                      ...prev,
                      deepseek: { ...prev.deepseek!, api_key: e.target.value }
                    }));
                  }}
                  placeholder="请输入DeepSeek API密钥"
                  addonAfter={
                    <Button
                      type="text"
                      size="small"
                      icon={apiKeyVisible['llm-deepseek'] ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                      onClick={() => toggleApiKeyVisibility('llm-deepseek', apiKeyVisible, setApiKeyVisible)}
                    />
                  }
                />
              </Form.Item>

              <Form.Item label="API端点">
                <Input
                  value={llmConfig.deepseek?.api_endpoint || ''}
                  onChange={(e) => setLlmConfig(prev => ({
                    ...prev,
                    deepseek: { ...prev.deepseek!, api_endpoint: e.target.value }
                  }))}
                  placeholder="https://api.deepseek.com"
                />
              </Form.Item>

              <Form.Item label="模型">
                <Select
                  value={llmConfig.deepseek?.model || ''}
                  onChange={(value) => setLlmConfig(prev => ({
                    ...prev,
                    deepseek: { ...prev.deepseek!, model: value }
                  }))}
                  placeholder="选择模型"
                >
                  {llmConfig.deepseek?.models?.map((model) => (
                    <Select.Option key={model.name} value={model.name}>
                      <div>
                        <strong>{model.display_name}</strong>
                        {model.recommended && <Tag color="green" style={{ marginLeft: 8 }}>推荐</Tag>}
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          {model.description}
                        </div>
                      </div>
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>

              {llmTestResults.deepseek && (
                <Alert
                  type={llmTestResults.deepseek.success ? 'success' : 'error'}
                  message={llmTestResults.deepseek.message}
                  style={{ marginTop: 8 }}
                />
              )}
            </Form>
          </Card>

          <Form.Item>
            <Button type="primary" onClick={saveLlmConfig}>
              保存LLM配置
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
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

  // 渲染角色管理
  const renderRoleSettings = () => {
    const columns: ColumnsType<Role> = [
      {
        title: '角色名称',
        dataIndex: 'name',
        key: 'name',
        render: (text: string, record: Role) => (
          <Space>
            <UserOutlined />
            <span style={{ fontWeight: 500 }}>{text}</span>
            {!record.is_active && <Tag color="default">已禁用</Tag>}
          </Space>
        ),
      },
      {
        title: '描述',
        dataIndex: 'description',
        key: 'description',
        ellipsis: true,
        render: (text: string) => text || '-',
      },
      {
        title: '状态',
        dataIndex: 'is_active',
        key: 'is_active',
        width: 100,
        render: (active: boolean) => (
          <Tag color={active ? 'success' : 'default'}>
            {active ? '启用' : '禁用'}
          </Tag>
        ),
      },
      {
        title: '创建时间',
        dataIndex: 'created_at',
        key: 'created_at',
        width: 180,
        render: (date: string) => new Date(date).toLocaleString(),
      },
      {
        title: '操作',
        key: 'actions',
        width: 200,
        render: (_, record: Role) => (
          <Space>
            <Tooltip title="查看详情">
              <Button
                type="text"
                icon={<EyeOutlined />}
                onClick={() => handleViewRole(record)}
              />
            </Tooltip>
            <Tooltip title="编辑">
              <Button
                type="text"
                icon={<EditOutlined />}
                onClick={() => handleEditRole(record)}
              />
            </Tooltip>
            <Popconfirm
              title="确定要删除这个角色吗？"
              onConfirm={() => handleDeleteRole(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Tooltip title="删除">
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Tooltip>
            </Popconfirm>
          </Space>
        ),
      },
    ];

    const activeRoles = roles.filter(role => role.is_active);
    const totalRoles = roles.length;

    return (
      <div>
        <Card title="👤 角色管理" style={{ marginBottom: 16 }}>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={8}>
              <Statistic
                title="总角色数"
                value={totalRoles}
                prefix={<UserOutlined />}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="启用角色"
                value={activeRoles.length}
                prefix={<UserOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="禁用角色"
                value={totalRoles - activeRoles.length}
                prefix={<UserOutlined />}
                valueStyle={{ color: '#cf1322' }}
              />
            </Col>
          </Row>

          <div style={{ marginBottom: 16 }}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateRole}
            >
              创建角色
            </Button>
          </div>

          <Table
            columns={columns}
            dataSource={roles}
            rowKey="id"
            loading={rolesLoading}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 个角色`,
            }}
          />
        </Card>

        {/* 创建/编辑角色模态框 */}
        <Modal
          title={editingRole ? '编辑角色' : '创建角色'}
          open={roleModalVisible}
          onOk={handleSubmitRole}
          onCancel={() => setRoleModalVisible(false)}
          width={600}
          okText="保存"
          cancelText="取消"
        >
          <Form
            form={roleForm}
            layout="vertical"
            initialValues={{ is_active: true }}
          >
            <Form.Item
              name="name"
              label="角色名称"
              rules={[
                { required: true, message: '请输入角色名称' },
                { max: 100, message: '角色名称不能超过100个字符' }
              ]}
            >
              <Input placeholder="请输入角色名称" />
            </Form.Item>

            <Form.Item
              name="description"
              label="角色描述"
              rules={[
                { max: 500, message: '角色描述不能超过500个字符' }
              ]}
            >
              <TextArea
                placeholder="请输入角色描述（可选）"
                rows={3}
                showCount
                maxLength={500}
              />
            </Form.Item>

            <Form.Item
              name="prompt"
              label="角色提示词"
              rules={[
                { required: true, message: '请输入角色提示词' }
              ]}
            >
              <TextArea
                placeholder="请输入角色提示词，用于指导AI的回答风格和重点方向"
                rows={6}
                showCount
              />
            </Form.Item>

            <Form.Item
              name="is_active"
              label="状态"
              valuePropName="checked"
            >
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
            </Form.Item>
          </Form>
        </Modal>

        {/* 查看角色详情模态框 */}
        <Modal
          title="角色详情"
          open={viewModalVisible}
          onCancel={() => setViewModalVisible(false)}
          footer={[
            <Button key="close" onClick={() => setViewModalVisible(false)}>
              关闭
            </Button>
          ]}
          width={600}
        >
          {viewingRole && (
            <div>
              <Paragraph>
                <strong>角色名称：</strong>{viewingRole.name}
              </Paragraph>
              <Paragraph>
                <strong>描述：</strong>{viewingRole.description || '无'}
              </Paragraph>
              <Paragraph>
                <strong>状态：</strong>
                <Tag color={viewingRole.is_active ? 'success' : 'default'}>
                  {viewingRole.is_active ? '启用' : '禁用'}
                </Tag>
              </Paragraph>
              <Paragraph>
                <strong>创建时间：</strong>{new Date(viewingRole.created_at).toLocaleString()}
              </Paragraph>
              <Paragraph>
                <strong>更新时间：</strong>{new Date(viewingRole.updated_at).toLocaleString()}
              </Paragraph>
              <Divider />
              <Paragraph>
                <strong>角色提示词：</strong>
              </Paragraph>
              <div style={{
                background: '#f5f5f5',
                padding: '12px',
                borderRadius: '6px',
                whiteSpace: 'pre-wrap',
                fontFamily: 'monospace',
                fontSize: '13px',
                lineHeight: '1.5'
              }}>
                {viewingRole.prompt}
              </div>
            </div>
          )}
        </Modal>
      </div>
    );
  };

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
      case 'llm':
        return renderLlmSettings();
      case 'roles':
        return renderRoleSettings();
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