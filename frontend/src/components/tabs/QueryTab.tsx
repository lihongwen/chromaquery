import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Layout,
  Input,
  Button,
  List,
  Avatar,
  Space,
  Card,
  Tag,
  Alert,
  Collapse,
  Form,
  Slider,
  InputNumber,
  Typography,
  message,
  Spin,
  Empty,
  Select,
  Tooltip,
  Drawer,
  FloatButton
} from 'antd';
import {
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  CopyOutlined,
  SearchOutlined,
  DatabaseOutlined,
  PlusOutlined,
  MessageOutlined,
  SettingOutlined,
  MenuOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import { useResponsive } from '../../hooks/useResponsive';
import { api } from '../../config/api';
import MarkdownRenderer from '../MarkdownRenderer';

const { Sider, Content } = Layout;
const { Panel } = Collapse;
const { Text } = Typography;

// 添加CSS样式来强制设置用户查询文字颜色
const userQueryTextStyle = `
  .user-query-text {
    color: #1f2937 !important;
    font-size: 14px !important;
    opacity: 1 !important;
    visibility: visible !important;
    -webkit-text-fill-color: #1f2937 !important;
    text-shadow: none !important;
  }
  .user-query-text * {
    color: #1f2937 !important;
    -webkit-text-fill-color: #1f2937 !important;
  }
  .message.user div, .message.assistant div {
    color: #1f2937 !important;
    -webkit-text-fill-color: #1f2937 !important;
  }
`;

// 将样式注入到页面中
if (typeof document !== 'undefined') {
  const existingStyle = document.getElementById('user-query-text-style');
  if (!existingStyle) {
    const styleElement = document.createElement('style');
    styleElement.id = 'user-query-text-style';
    styleElement.textContent = userQueryTextStyle;
    document.head.appendChild(styleElement);
  }
}

interface QueryMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
  results?: QueryResult[];
  llm_response?: string;
  is_streaming?: boolean;
  selected_collections?: string[];
  documents_found?: number;
}

// 对话相关接口
interface Conversation {
  id: string;
  title: string;
  created_at: string;
  messages: QueryMessage[];
}

interface QueryResult {
  id: string;
  document: string;
  distance: number;
  metadata: Record<string, any>;
  collection_name?: string;
}

interface QuerySettings {
  similarity_threshold: number;
  n_results: number;
}

interface CollectionInfo {
  name: string;
  display_name: string;
  count: number;
  metadata: Record<string, any>;
}

const QueryTab: React.FC = () => {
  // 对话管理状态
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  
  // 原有状态
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [settings, setSettings] = useState<QuerySettings>({
    similarity_threshold: 0.3,
    n_results: 10,
  });
  
  // 布局状态
  const [leftDrawerVisible, setLeftDrawerVisible] = useState(false);
  const [rightDrawerVisible, setRightDrawerVisible] = useState(false);
  const [siderCollapsed, setSiderCollapsed] = useState(false);
  
  // 其他状态
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());
  const [showResultsList, setShowResultsList] = useState<Set<string>>(new Set());
  const [collections, setCollections] = useState<CollectionInfo[]>([]);
  const [selectedCollections, setSelectedCollections] = useState<string[]>([]);
  const [collectionsLoading, setCollectionsLoading] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { isMobile } = useResponsive();

  // 添加CSS样式
  useEffect(() => {
    const styleId = 'query-tab-styles';
    let style = document.getElementById(styleId) as HTMLStyleElement;

    if (!style) {
      style = document.createElement('style');
      style.id = styleId;
      style.textContent = `
        .typing-cursor {
          opacity: 1;
          animation: blink 1s infinite;
        }
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0.3; }
        }
      `;
      document.head.appendChild(style);
    }

    return () => {
      const existingStyle = document.getElementById(styleId);
      if (existingStyle && document.head.contains(existingStyle)) {
        document.head.removeChild(existingStyle);
      }
    };
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [currentConversation?.messages]);

  useEffect(() => {
    fetchCollections();
    loadConversations();
  }, []);

  // 对话管理函数
  const createNewConversation = useCallback(() => {
    const newConversation: Conversation = {
      id: `conv_${Date.now()}`,
      title: '新对话',
      created_at: new Date().toISOString(),
      messages: []
    };
    const updatedConversations = [newConversation, ...conversations];
    setConversations(updatedConversations);
    setCurrentConversation(newConversation);
    saveConversations(updatedConversations);
  }, [conversations]);

  const clearConversations = useCallback(() => {
    setConversations([]);
    setCurrentConversation(null);
    localStorage.removeItem('chromadb_conversations');
    message.success('对话历史已清空');
  }, []);

  const loadConversations = () => {
    try {
      const saved = localStorage.getItem('chromadb_conversations');
      if (saved) {
        const parsed = JSON.parse(saved);
        setConversations(parsed);
      }
    } catch (error) {
      console.error('加载对话历史失败:', error);
    }
  };

  const saveConversations = useCallback((convs: Conversation[]) => {
    try {
      localStorage.setItem('chromadb_conversations', JSON.stringify(convs));
    } catch (error) {
      console.error('保存对话历史失败:', error);
    }
  }, []);

  // 监听对话变化自动保存
  useEffect(() => {
    if (conversations.length > 0) {
      saveConversations(conversations);
    }
  }, [conversations, saveConversations]);

  // 过滤对话列表
  const filteredConversations = conversations.filter(conv =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // 获取集合列表
  const fetchCollections = useCallback(async () => {
    setCollectionsLoading(true);
    try {
      const response = await api.collections.list();
      setCollections(response.data);

      // 如果没有集合，显示提示
      if (response.data.length === 0) {
        message.info('暂无可用集合，请先在集合管理页面创建集合');
      }
    } catch (error: any) {
      console.error('获取集合列表失败:', error);

      // 根据错误类型显示不同的提示
      if (error.code === 'NETWORK_ERROR' || error.message?.includes('fetch')) {
        message.error('网络连接失败，请检查后端服务是否正常运行');
      } else {
        message.error(`获取集合列表失败: ${error.message || '未知错误'}`);
      }
    } finally {
      setCollectionsLoading(false);
    }
  }, []);

  const handleQuery = async (query: string) => {
    if (!query.trim()) {
      message.warning('请输入查询内容');
      return;
    }

    if (selectedCollections.length === 0) {
      message.warning('请选择至少一个集合');
      return;
    }

    // 如果没有当前对话，创建一个新的
    let conversation = currentConversation;
    if (!conversation) {
      conversation = {
        id: `conv_${Date.now()}`,
        title: query.slice(0, 20) + (query.length > 20 ? '...' : ''),
        created_at: new Date().toISOString(),
        messages: []
      };
      const updatedConversations = [conversation, ...conversations];
      setConversations(updatedConversations);
      setCurrentConversation(conversation);
    } else if (conversation.title === '新对话' && conversation.messages.length === 0) {
      // 如果是新对话且还没有消息，更新标题
      conversation = {
        ...conversation,
        title: query.slice(0, 20) + (query.length > 20 ? '...' : '')
      };
      setCurrentConversation(conversation);
      setConversations(prev =>
        prev.map(conv => conv.id === conversation!.id ? conversation! : conv)
      );
    }

    const userMessage: QueryMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString(),
      selected_collections: [...selectedCollections],
    };

    // 更新当前对话的消息
    const updatedConversation = {
      ...conversation,
      messages: [...conversation.messages, userMessage]
    };
    setCurrentConversation(updatedConversation);
    setConversations(prev =>
      prev.map(conv => conv.id === conversation!.id ? updatedConversation : conv)
    );

    setInputValue('');
    setLoading(true);

    // 创建助手消息用于流式响应
    const assistantMessageId = `${Date.now()}_assistant`;
    setStreamingMessageId(assistantMessageId);

    const assistantMessage: QueryMessage = {
      id: assistantMessageId,
      type: 'assistant',
      content: '正在思考中...',
      timestamp: new Date().toLocaleTimeString(),
      llm_response: '',
      is_streaming: true,
    };

    // 添加助手消息到当前对话
    const conversationWithAssistant = {
      ...updatedConversation,
      messages: [...updatedConversation.messages, assistantMessage]
    };
    setCurrentConversation(conversationWithAssistant);
    setConversations(prev =>
      prev.map(conv => conv.id === conversation!.id ? conversationWithAssistant : conv)
    );

    try {
      // 调用LLM查询API（流式响应）
      const response = await api.query.llm({
        query: query,
        collections: selectedCollections,
        limit: settings.n_results,
        similarity_threshold: settings.similarity_threshold,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedResponse = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                // 处理元数据信息
                if (data.metadata) {
                  setCurrentConversation(prev => {
                    if (!prev) return prev;
                    const updatedMessages = prev.messages.map(msg =>
                      msg.id === assistantMessageId
                        ? {
                            ...msg,
                            documents_found: data.metadata.documents_found,
                            results: data.metadata.query_results || [],
                            content: `智能回答：（找到 ${data.metadata.documents_found} 个相关文档）`
                          }
                        : msg
                    );
                    const updatedConv = { ...prev, messages: updatedMessages };
                    
                    setConversations(prevConvs =>
                      prevConvs.map(conv => conv.id === prev.id ? updatedConv : conv)
                    );
                    
                    return updatedConv;
                  });
                }

                if (data.content) {
                  accumulatedResponse += data.content;

                  // 更新消息内容
                  setCurrentConversation(prev => {
                    if (!prev) return prev;
                    const updatedMessages = prev.messages.map(msg =>
                      msg.id === assistantMessageId
                        ? {
                            ...msg,
                            llm_response: accumulatedResponse,
                            is_streaming: true
                          }
                        : msg
                    );
                    const updatedConv = { ...prev, messages: updatedMessages };
                    
                    setConversations(prevConvs =>
                      prevConvs.map(conv => conv.id === prev.id ? updatedConv : conv)
                    );
                    
                    return updatedConv;
                  });
                }

                // 检查是否完成
                if (data.finish_reason) {
                  setCurrentConversation(prev => {
                    if (!prev) return prev;
                    const updatedMessages = prev.messages.map(msg =>
                      msg.id === assistantMessageId
                        ? {
                            ...msg,
                            is_streaming: false
                          }
                        : msg
                    );
                    const updatedConv = { ...prev, messages: updatedMessages };
                    
                    setConversations(prevConvs =>
                      prevConvs.map(conv => conv.id === prev.id ? updatedConv : conv)
                    );
                    
                    return updatedConv;
                  });
                  break;
                }
              } catch (e) {
                console.error('解析流式数据失败:', e);
              }
            }
          }
        }
      }
    } catch (error: any) {
      console.error('LLM查询失败:', error);

      let errorMessage = 'LLM查询失败';

      // 根据错误类型提供更具体的错误信息
      if (error.name === 'TypeError' && error.message?.includes('fetch')) {
        errorMessage = '网络连接失败，请检查后端服务是否正常运行';
      } else if (error.message?.includes('404')) {
        errorMessage = '选择的集合不存在，请刷新页面重新选择';
      } else if (error.message?.includes('500')) {
        errorMessage = '服务器内部错误，请稍后重试';
      } else if (error.message?.includes('timeout')) {
        errorMessage = '查询超时，请尝试简化查询内容';
      } else if (error.message) {
        errorMessage = error.message;
      }

      // 更新为错误消息
      setCurrentConversation(prev => {
        if (!prev) return prev;
        const updatedMessages = prev.messages.map(msg =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                content: `❌ 查询失败: ${errorMessage}`,
                is_streaming: false,
                llm_response: undefined
              }
            : msg
        );
        const updatedConv = { ...prev, messages: updatedMessages };
        
        setConversations(prevConvs =>
          prevConvs.map(conv => conv.id === prev.id ? updatedConv : conv)
        );
        
        return updatedConv;
      });

      message.error(errorMessage);
    } finally {
      setLoading(false);
      setStreamingMessageId(null);
    }
  };

  const handleCopyContent = (content: string) => {
    navigator.clipboard.writeText(content);
    message.success('内容已复制到剪贴板');
  };

  // 切换查询结果展开状态
  const toggleResultExpansion = (resultId: string) => {
    setExpandedResults(prev => {
      const newSet = new Set(prev);
      if (newSet.has(resultId)) {
        newSet.delete(resultId);
      } else {
        newSet.add(resultId);
      }
      return newSet;
    });
  };

  // 切换整体文档列表的显示/隐藏状态
  const toggleResultsList = (messageId: string) => {
    setShowResultsList(prev => {
      const newSet = new Set(prev);
      if (newSet.has(messageId)) {
        newSet.delete(messageId);
      } else {
        newSet.add(messageId);
      }
      return newSet;
    });
  };

  // 折叠状态下的侧边栏内容
  const collapsedSiderContent = (
    <div style={{
      padding: '16px 0',
      textAlign: 'center',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'flex-start'
    }}>
      <div style={{ flex: 1 }}>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Tooltip title="新建对话" placement="right">
            <div style={{
              fontSize: '18px',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '6px',
              transition: 'background-color 0.2s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--ant-color-fill-tertiary)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            onClick={createNewConversation}
            >💬</div>
          </Tooltip>
          
          <Tooltip title="搜索对话" placement="right">
            <div style={{
              fontSize: '18px',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '6px',
              transition: 'background-color 0.2s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--ant-color-fill-tertiary)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >🔍</div>
          </Tooltip>

          <Tooltip title="对话历史" placement="right">
            <div style={{
              fontSize: '18px',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '6px',
              transition: 'background-color 0.2s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--ant-color-fill-tertiary)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >📝</div>
          </Tooltip>
        </Space>
      </div>
    </div>
  );

  // 展开状态下的侧边栏内容
  const expandedSiderContent = (
    <div style={{ padding: 16 }}>
      {/* 新建对话按钮 */}
      <Button
        type="primary"
        icon={<PlusOutlined />}
        block
        onClick={createNewConversation}
        style={{
          marginBottom: 16,
          borderRadius: '8px',
          height: '40px',
          fontWeight: 600
        }}
      >
        新建对话
      </Button>

      {/* 搜索对话 */}
      <Input
        placeholder="搜索对话..."
        prefix={<SearchOutlined />}
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        style={{
          marginBottom: 16,
          borderRadius: '8px'
        }}
      />

      {/* 对话列表 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ 
          fontSize: '14px', 
          fontWeight: 600, 
          marginBottom: 8,
          color: 'var(--ant-color-text)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>过去对话</span>
          {conversations.length > 0 && (
            <Button
              type="text" 
              size="small" 
              icon={<DeleteOutlined />}
              onClick={clearConversations}
              danger
              style={{ padding: '2px 6px' }}
            >
              清空
            </Button>
          )}
        </div>
        
        <List
          size="small"
          dataSource={filteredConversations}
          locale={{
            emptyText: (
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                <MessageOutlined style={{ fontSize: 24, color: '#d9d9d9', marginBottom: 8 }} />
                <div style={{ color: '#999', fontSize: '12px' }}>暂无对话历史</div>
                <div style={{ color: '#ccc', fontSize: '11px' }}>点击"新建对话"开始查询</div>
              </div>
            )
          }}
          renderItem={(conversation) => (
            <List.Item
              style={{
                cursor: 'pointer',
                padding: '8px 12px',
                borderRadius: '8px',
                backgroundColor: currentConversation?.id === conversation.id
                  ? 'var(--ant-color-primary-bg)'
                  : 'transparent',
                border: currentConversation?.id === conversation.id
                  ? '1px solid var(--ant-color-primary-border)'
                  : '1px solid transparent',
                marginBottom: '4px',
                transition: 'all 0.2s ease',
              }}
              onClick={() => {
                setCurrentConversation(conversation);
                // 当选择历史对话时，自动设置该对话使用的集合
                const firstUserMessage = conversation.messages.find(msg => msg.type === 'user');
                if (firstUserMessage && firstUserMessage.selected_collections) {
                  setSelectedCollections(firstUserMessage.selected_collections);
                }
                if (isMobile) {
                  setLeftDrawerVisible(false);
                }
              }}
              onMouseEnter={(e) => {
                if (currentConversation?.id !== conversation.id) {
                  e.currentTarget.style.backgroundColor = 'var(--ant-color-fill-quaternary)';
                }
              }}
              onMouseLeave={(e) => {
                if (currentConversation?.id !== conversation.id) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }
              }}
            >
              <List.Item.Meta
                title={
                  <div style={{
                    fontSize: '13px',
                    fontWeight: currentConversation?.id === conversation.id ? 600 : 500,
                    color: currentConversation?.id === conversation.id 
                      ? 'var(--ant-color-primary)' 
                      : 'var(--ant-color-text)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}>
                    {conversation.title}
                  </div>
                }
                description={
                  <div style={{ fontSize: '11px', color: 'var(--ant-color-text-tertiary)' }}>
                    {conversation.messages.length} 条消息 · {new Date(conversation.created_at).toLocaleDateString()}
                  </div>
                }
              />
            </List.Item>
          )}
        />
      </div>

      <Collapse size="small" ghost>
        <Panel header="⚙️ 查询设置" key="settings">
          <Form layout="vertical" size="small">
            <Form.Item
              label="相似度阈值"
              tooltip="设置文档相关性的最低要求。值越高，返回的文档越相关但数量可能较少；值越低，返回更多文档但相关性可能较低。"
            >
              <Slider
                min={0}
                max={1}
                step={0.1}
                value={settings.similarity_threshold}
                onChange={(value) => {
                  if (typeof value === 'number' && value !== settings.similarity_threshold) {
                    setSettings(prev => ({ ...prev, similarity_threshold: value }));
                  }
                }}
                tooltip={{ formatter: (value) => `相关性: ${(value! * 100).toFixed(0)}%` }}
                marks={{
                  0: '宽松',
                  0.5: '适中',
                  1: '严格'
                }}
              />
            </Form.Item>

            <Form.Item label="返回结果数">
              <InputNumber
                min={1}
                max={100}
                value={settings.n_results}
                onChange={(value) => {
                  const newValue = value || 10;
                  if (newValue !== settings.n_results) {
                    setSettings(prev => ({ ...prev, n_results: newValue }));
                  }
                }}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Form>
        </Panel>
      </Collapse>
    </div>
  );

  // 根据折叠状态选择内容
  const siderContent = siderCollapsed ? collapsedSiderContent : expandedSiderContent;

  return (
    <Layout style={{ height: 'calc(100vh - 64px)', minHeight: '500px' }}>
      {!isMobile && (
        <Sider
          width={240}
          theme="light"
          collapsible
          collapsed={siderCollapsed}
          onCollapse={setSiderCollapsed}
          style={{
            backgroundColor: 'var(--ant-color-bg-container)',
            borderRight: '1px solid var(--ant-color-border)',
            height: '100%',
            overflow: 'auto',
          }}
        >
          {siderContent}
        </Sider>
      )}

      <Content>
        <div className="chat-container" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          {/* 聊天消息区域 */}
          <div 
            className="chat-messages" 
            style={{ 
              flex: 1, 
              overflowY: 'auto', 
              padding: 16,
              backgroundColor: 'var(--ant-color-bg-layout)',
            }}
          >
            {!currentConversation || currentConversation.messages.length === 0 ? (
              <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100%',
                flexDirection: 'column'
              }}>
                <div style={{ textAlign: 'center' }}>
                  {/* 主标题 */}
                  <div style={{
                    fontSize: '48px',
                    fontWeight: 600,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    marginBottom: 16
                  }}>
                    智能查询系统
                  </div>
                  
                  {/* 副标题 */}
                  <div style={{
                    fontSize: '18px',
                    color: 'var(--ant-color-text-secondary)', 
                    marginBottom: 32
                  }}>
                    基于ChromaDB的智能文档检索与问答系统
                  </div>

                  {/* 功能特性 */}
                  <div style={{
                    display: 'flex',
                    justifyContent: 'center',
                    gap: 32,
                    marginBottom: 32,
                    flexWrap: 'wrap'
                  }}>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '24px', marginBottom: 8 }}>🔍</div>
                      <div style={{ fontSize: '14px', fontWeight: 500 }}>智能检索</div>
                      <div style={{ fontSize: '12px', color: 'var(--ant-color-text-tertiary)' }}>语义搜索文档</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '24px', marginBottom: 8 }}>🤖</div>
                      <div style={{ fontSize: '14px', fontWeight: 500 }}>AI问答</div>
                      <div style={{ fontSize: '12px', color: 'var(--ant-color-text-tertiary)' }}>智能回答问题</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '24px', marginBottom: 8 }}>📚</div>
                      <div style={{ fontSize: '14px', fontWeight: 500 }}>多集合</div>
                      <div style={{ fontSize: '12px', color: 'var(--ant-color-text-tertiary)' }}>跨集合查询</div>
                    </div>
                  </div>

                  {/* 状态提示 */}
                  {selectedCollections.length === 0 ? (
                    <Alert
                      message="请先选择要查询的集合"
                      description="点击右下角的数据库图标选择一个或多个集合后即可开始查询"
                      type="info"
                      showIcon
                      style={{
                        maxWidth: 400,
                        margin: '0 auto',
                        textAlign: 'left'
                      }}
                    />
                  ) : (
                    <div style={{
                      padding: '12px 16px',
                      backgroundColor: 'var(--ant-color-success-bg)',
                      border: '1px solid var(--ant-color-success-border)',
                      borderRadius: '8px',
                      maxWidth: 400,
                      margin: '0 auto'
                    }}>
                      <div style={{ 
                        color: 'var(--ant-color-success)',
                        fontSize: '14px',
                        fontWeight: 500,
                        marginBottom: 4
                      }}>
                        ✅ 已选择 {selectedCollections.length} 个集合
                      </div>
                      <div style={{ 
                        fontSize: '12px', 
                        color: 'var(--ant-color-text-secondary)' 
                      }}>
                        {selectedCollections.join(', ')}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <>
                {currentConversation.messages.map((message) => (
                  <div
                    key={message.id}
                    className={`message ${message.type}`}
                    style={{
                      display: 'flex',
                      marginBottom: 16,
                      alignItems: 'flex-start',
                      flexDirection: message.type === 'user' ? 'row-reverse' : 'row',
                    }}
                  >
                    <Avatar
                      icon={message.type === 'user' ? <UserOutlined /> : <RobotOutlined />}
                      style={{
                        backgroundColor: message.type === 'user' ? 'var(--ant-color-primary)' : 'var(--ant-color-success)',
                        margin: message.type === 'user' ? '0 0 0 8px' : '0 8px 0 0',
                      }}
                    />
                    
                    <div style={{ maxWidth: '70%' }}>
                      <Card
                        size="small"
                        style={{
                          background: '#ffffff',
                          color: '#1f2937',
                          border: '1px solid #e5e7eb',
                          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
                        }}
                        bodyStyle={{
                          padding: '12px 16px',
                        }}
                      >
                        {/* 用户查询内容或AI回答内容 */}
                        {message.type === 'user' ? (
                          <>
                            <div
                              className="user-query-text"
                              style={{
                                color: '#1f2937 !important',
                                lineHeight: '1.6',
                                textShadow: 'none',
                                fontWeight: 'normal',
                                whiteSpace: 'pre-wrap',
                                fontSize: '14px',
                                opacity: 1,
                                visibility: 'visible',
                                WebkitTextFillColor: '#1f2937'
                              }}>
                              {message.content}
                            </div>
                            {message.selected_collections && (
                              <div style={{ marginTop: 8 }}>
                                <Text
                                  style={{
                                    fontSize: '12px',
                                    color: '#6b7280',
                                    fontWeight: 'normal'
                                  }}
                                >
                                  查询集合: {message.selected_collections.join(', ')}
                                </Text>
                              </div>
                            )}
                          </>
                        ) : (
                          <>
                            <div style={{
                              color: '#1f2937 !important',
                              lineHeight: '1.6',
                              textShadow: 'none',
                              fontWeight: 'normal',
                              WebkitTextFillColor: '#1f2937',
                              opacity: 1
                            }}>
                              <MarkdownRenderer 
                                content={message.llm_response || message.content}
                                style={{
                                  color: '#1f2937',
                                  fontSize: '14px'
                                }}
                              />
                              {message.is_streaming && (
                                <span className="typing-cursor">|</span>
                              )}
                            </div>
                          </>
                        )}

                        <div style={{
                          marginTop: 8,
                          fontSize: '12px',
                          opacity: 0.8,
                          color: '#6b7280',
                        }}>
                          {message.timestamp}
                          {message.is_streaming && (
                            <span style={{ marginLeft: 8 }}>
                              <Spin size="small" /> 正在生成回答...
                            </span>
                          )}
                        </div>
                      </Card>
                      
                      {message.results && message.results.length > 0 && (
                        <div style={{ marginTop: 12 }}>
                          {/* 查询结果汇总信息 */}
                          <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '12px 16px',
                            backgroundColor: '#f0f9ff',
                            border: '1px solid #bae6fd',
                            borderRadius: '8px',
                            marginBottom: '12px'
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span style={{ fontSize: '16px' }}>✅</span>
                              <Text strong style={{ color: '#0369a1', fontSize: '14px' }}>
                                找到 {message.results.length} 个相关文档
                              </Text>
                              {!showResultsList.has(message.id) && (
                                <Text type="secondary" style={{ fontSize: '12px', marginLeft: '8px' }}>
                                  点击"展开"查看详细结果
                                </Text>
                              )}
                            </div>
                            <Button
                              type="text"
                              size="small"
                              icon={showResultsList.has(message.id) ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                              onClick={() => toggleResultsList(message.id)}
                              style={{ color: '#0369a1' }}
                            >
                              {showResultsList.has(message.id) ? '收起详情' : '展开详情'}
                            </Button>
                          </div>

                          {/* 文档列表 - 只在展开时显示 */}
                          {showResultsList.has(message.id) && (
                            <List
                              size="small"
                              dataSource={message.results}
                            renderItem={(result) => {
                              const isExpanded = expandedResults.has(result.id);

                              return (
                                <List.Item>
                                  <Card
                                    size="small"
                                    style={{ width: '100%' }}
                                    title={
                                      <Space>
                                        <span style={{
                                          backgroundColor: '#e6f7ff',
                                          color: '#0050b3',
                                          padding: '4px 12px',
                                          borderRadius: '16px',
                                          fontSize: '13px',
                                          fontWeight: '600'
                                        }}>
                                          相似度: {(Math.max(0, Math.min(100, (1 / (1 + result.distance)) * 100))).toFixed(1)}%
                                        </span>
                                        <Tag color="blue">
                                          {result.metadata.source || result.collection_name}
                                        </Tag>
                                        {/* 默认状态下显示文档简要信息 */}
                                        {!isExpanded && result.metadata.file_name && (
                                          <Text type="secondary" style={{ fontSize: '12px' }}>
                                            📄 {result.metadata.file_name}
                                            {result.metadata.chunk_index !== undefined && ` • 第${result.metadata.chunk_index + 1}块`}
                                          </Text>
                                        )}
                                      </Space>
                                    }
                                    extra={
                                      <Space>
                                        <Button
                                          size="small"
                                          icon={isExpanded ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                                          type="text"
                                          onClick={() => toggleResultExpansion(result.id)}
                                          style={{ color: '#1890ff' }}
                                        >
                                          {isExpanded ? '收起' : '展开'}
                                        </Button>
                                        <Button
                                          size="small"
                                          icon={<CopyOutlined />}
                                          type="text"
                                          onClick={() => handleCopyContent(result.document)}
                                          style={{ color: '#52c41a' }}
                                        >
                                          复制
                                        </Button>
                                      </Space>
                                    }
                                  >
                                    {/* 只在展开时显示文档内容 */}
                                    {isExpanded && (
                                      <Text style={{ whiteSpace: 'pre-wrap', fontSize: '13px', lineHeight: '1.5' }}>
                                        {result.document}
                                      </Text>
                                    )}

                                    {/* 默认状态下不显示内容，只显示标题信息 */}
                                    {!isExpanded && (
                                      <Text type="secondary" style={{ fontSize: '12px', fontStyle: 'italic' }}>
                                        点击"展开"查看文档内容
                                      </Text>
                                    )}
                                  </Card>
                                </List.Item>
                              );
                            }}
                            />
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                
                {loading && (
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'center',
                    padding: 16,
                  }}>
                    <Spin tip="正在查询..." />
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </>
            )}
          </div>
          
          {/* 输入区域 */}
          <div
            className="chat-input"
            style={{
              padding: 16,
              borderTop: '1px solid var(--ant-color-border)',
              backgroundColor: 'var(--ant-color-bg-container)',
            }}
          >
            {selectedCollections.length === 0 && (
              <Alert
                message="请先点击数据库图标选择要查询的集合"
                type="warning"
                showIcon
                style={{ marginBottom: 12 }}
              />
            )}

            <div style={{ display: 'flex', alignItems: 'stretch', gap: 8 }}>
              {/* +号按钮 */}
              <Button
                icon={<PlusOutlined />}
                size="large"
                style={{
                  borderRadius: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '48px',
                  height: '48px'
                }}
                onClick={() => {
                  // 这里可以添加+号的功能，用户说保留后续开发
                  message.info('附加功能开发中...');
                }}
              />

              {/* 输入框 */}
              <Input.Search
                placeholder={selectedCollections.length > 0 ? "询问任何问题..." : "请先选择集合"}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onSearch={handleQuery}
                enterButton={
                  <Button
                    type="primary"
                    icon={<SendOutlined />}
                    style={{
                      borderRadius: '0 12px 12px 0',
                      height: '48px',
                      display: 'flex',
                      alignItems: 'center',
                      paddingLeft: 16,
                      paddingRight: 16
                    }}
                  />
                }
                size="large"
                loading={loading}
                disabled={loading || selectedCollections.length === 0}
                style={{
                  flex: 1,
                  color: '#1f2937',
                  backgroundColor: '#ffffff'
                }}
                styles={{
                  input: {
                    borderRadius: '12px 0 0 12px',
                    height: '48px',
                    fontSize: '16px',
                    padding: '0 16px'
                  }
                }}
                onPressEnter={(e) => {
                  if (!e.shiftKey) {
                    e.preventDefault();
                    handleQuery(inputValue);
                  }
                }}
              />

              {/* 集合选择按钮 */}
              <Tooltip title="选择集合">
                <Button
                  icon={<DatabaseOutlined />}
                  size="large"
                  style={{
                    borderRadius: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '48px',
                    height: '48px'
                  }}
                  onClick={() => {
                    setRightDrawerVisible(true);
                  }}
                />
              </Tooltip>
            </div>

            {selectedCollections.length > 0 && (
              <div style={{ marginTop: 8, fontSize: '12px', color: 'var(--ant-color-text-secondary)' }}>
                已选择 {selectedCollections.length} 个集合: {selectedCollections.join(', ')}
              </div>
            )}
          </div>
        </div>
      </Content>

      {/* 移动端抽屉 - 对话历史 */}
      <Drawer
        title="对话管理"
        placement="left"
        onClose={() => setLeftDrawerVisible(false)}
        open={leftDrawerVisible}
        width={isMobile ? '85%' : 320}
        bodyStyle={{ padding: 0 }}
      >
        {expandedSiderContent}
      </Drawer>

      {/* 移动端抽屉 - 集合选择 */}
      <Drawer
        title="集合选择"
        placement="right" 
        onClose={() => setRightDrawerVisible(false)}
        open={rightDrawerVisible}
        width={isMobile ? '90%' : 380}
        bodyStyle={{ padding: 16 }}
      >
        <Form layout="vertical" size="small">
          <Form.Item label="选择查询集合">
            <Select
              mode="multiple"
              placeholder="请选择要查询的集合"
              value={selectedCollections}
              onChange={setSelectedCollections}
              loading={collectionsLoading}
              style={{ width: '100%' }}
              maxTagCount="responsive"
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            >
              {collections.map((collection) => (
                <Select.Option
                  key={collection.display_name}
                  value={collection.display_name}
                  label={collection.display_name}
                >
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    width: '100%'
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      flex: 1,
                      overflow: 'hidden'
                    }}>
                      <DatabaseOutlined style={{ marginRight: 8, flexShrink: 0 }} />
                      <span style={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }} title={collection.display_name}>
                        {collection.display_name}
                      </span>
                    </div>
                    <Tag size="small" style={{ flexShrink: 0, marginLeft: 8 }}>
                      {collection.count}
                    </Tag>
                  </div>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          {selectedCollections.length === 0 && (
            <Alert
              message="请选择至少一个集合进行查询"
              type="warning"
              size="small"
              showIcon
            />
          )}

          {collections.length === 0 && !collectionsLoading && (
            <Alert
              message="暂无可用集合"
              description="请先在集合管理页面创建集合，然后刷新此页面"
              type="info"
              size="small"
              showIcon
              action={
                <Button size="small" onClick={fetchCollections}>
                  刷新
                </Button>
              }
            />
          )}
        </Form>
      </Drawer>

      {/* 移动端悬浮按钮组 */}
      {isMobile && (
        <>
          <FloatButton.Group
            shape="circle"
            style={{ right: 16, bottom: 80 }}
          >
            <FloatButton
              icon={<MessageOutlined />}
              tooltip="对话管理"
              onClick={() => setLeftDrawerVisible(true)}
            />
            <FloatButton
              icon={<DatabaseOutlined />}
              tooltip="集合选择"
              onClick={() => setRightDrawerVisible(true)}
            />
          </FloatButton.Group>
        </>
      )}

    </Layout>
  );
};

export default QueryTab;