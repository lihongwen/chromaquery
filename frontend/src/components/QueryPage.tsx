import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Layout, Card, List, Input, Button, Select, Space, Typography, message, Empty, Result, Drawer, FloatButton, Collapse, Tooltip } from 'antd';
import { SearchOutlined, SendOutlined, MessageOutlined, DatabaseOutlined, ArrowLeftOutlined, DeleteOutlined, PlusOutlined, MenuOutlined, SettingOutlined, EyeOutlined, EyeInvisibleOutlined, CopyOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import ThemeToggle from './ThemeToggle';
import { useResponsive } from '../hooks/useResponsive';
import { api, API_BASE_URL } from '../config/api';
import MarkdownRenderer from './MarkdownRenderer';

const { Sider, Content } = Layout;
const { Title, Text } = Typography;
const { TextArea } = Input;
const { Panel } = Collapse;

// 接口定义
interface CollectionInfo {
  name: string;
  display_name: string;
  count: number;
  metadata: Record<string, any>;
}

interface QueryResult {
  id: string;
  document: string;
  metadata: Record<string, any>;
  distance: number;
  collection_name: string;
}

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  messages: ConversationMessage[];
}

interface ConversationMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
  query_results?: QueryResult[];
  selected_collections?: string[];
  // LLM相关字段
  llm_response?: string;
  is_streaming?: boolean;
  processing_time?: number;
}

interface QueryPageProps {
  hasCollections?: boolean | null;
  onCollectionsChange?: () => void;
  onNavigateToCollections?: () => void;
}

const QueryPage: React.FC<QueryPageProps> = ({ hasCollections, onNavigateToCollections }) => {
  const responsive = useResponsive();
  const navigate = useNavigate();

  // 响应式状态管理
  const [leftDrawerVisible, setLeftDrawerVisible] = useState(false);
  const [rightDrawerVisible, setRightDrawerVisible] = useState(false);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);

  // 简化的CSS样式
  useEffect(() => {
    const styleId = 'query-page-styles';
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
        /* 强制设置对话框文字颜色 */
        .ant-list-item div[style*="color"] {
          color: #1f2937 !important;
          -webkit-text-fill-color: #1f2937 !important;
        }
        .ant-card-body div {
          color: #1f2937 !important;
          -webkit-text-fill-color: #1f2937 !important;
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

  // 响应式布局控制
  useEffect(() => {
    if (responsive.isMobile) {
      setLeftCollapsed(true);
      setRightCollapsed(true);
    } else if (responsive.isTablet) {
      setLeftCollapsed(true);
      setRightCollapsed(true);
    } else {
      setLeftCollapsed(true);
      setRightCollapsed(false);
    }
  }, [responsive.isMobile, responsive.isTablet]);

  // 状态管理
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [collections, setCollections] = useState<CollectionInfo[]>([]);
  const [selectedCollections, setSelectedCollections] = useState<string[]>([]);
  const [queryText, setQueryText] = useState('');
  const [loading, setLoading] = useState(false);
  const [collectionsLoading, setCollectionsLoading] = useState(false);
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());
  const [showResultsList, setShowResultsList] = useState<Set<string>>(new Set());
  const [, setStreamingMessageId] = useState<string | null>(null);

  // 用于滚动到最新消息的引用
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const conversationContentRef = useRef<HTMLDivElement>(null);
  const latestMessageRef = useRef<HTMLDivElement>(null);

  // 获取集合列表 - 优化性能
  const fetchCollections = useCallback(async () => {
    setCollectionsLoading(true);
    try {
      const response = await api.collections.list();
      setCollections(response.data);
    } catch (error) {
      console.error('获取集合列表失败:', error);
      // 错误已在api拦截器中处理，这里不需要重复显示
    } finally {
      setCollectionsLoading(false);
    }
  }, []);

  // 创建新对话 - 优化性能
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
  }, [conversations]);

  // 清空对话历史 - 优化性能
  const clearConversations = useCallback(() => {
    setConversations([]);
    setCurrentConversation(null);
    localStorage.removeItem('chromadb_conversations');
    message.success('对话历史已清空');
  }, []);

  // 切换查询结果的展开/收起状态 - 优化性能
  const toggleResultExpansion = useCallback((resultId: string) => {
    setExpandedResults(prev => {
      const newSet = new Set(prev);
      if (newSet.has(resultId)) {
        newSet.delete(resultId);
      } else {
        newSet.add(resultId);
      }
      return newSet;
    });
  }, []);

  // 切换整体文档列表的显示/隐藏状态
  const toggleResultsList = useCallback((messageId: string) => {
    setShowResultsList(prev => {
      const newSet = new Set(prev);
      if (newSet.has(messageId)) {
        newSet.delete(messageId);
      } else {
        newSet.add(messageId);
      }
      return newSet;
    });
  }, []);

  // 滚动到最新消息（让最新消息显示在对话框顶部）
  const scrollToLatestMessage = () => {
    // 使用更长的延迟确保DOM完全更新，包括查询结果的渲染
    setTimeout(() => {
      if (latestMessageRef.current) {
        console.log('滚动到最新消息:', latestMessageRef.current);
        // 获取对话容器和最新消息的位置信息
        const container = conversationContentRef.current;
        const latestMessage = latestMessageRef.current;

        if (container && latestMessage) {
          // 计算最新消息相对于容器的位置
          const containerRect = container.getBoundingClientRect();
          const messageRect = latestMessage.getBoundingClientRect();

          // 计算需要滚动的距离，让最新消息显示在容器顶部
          const scrollTop = container.scrollTop + (messageRect.top - containerRect.top);

          container.scrollTo({
            top: scrollTop,
            behavior: 'smooth'
          });
        }
      } else {
        console.log('latestMessageRef.current 为空');
      }
    }, 300);  // 增加延迟时间到300ms
  };

  // 滚动到对话开头
  const scrollToConversationTop = () => {
    // 使用setTimeout确保DOM已更新
    setTimeout(() => {
      if (conversationContentRef.current) {
        conversationContentRef.current.scrollTo({
          top: 0,
          behavior: 'smooth'
        });
      }
    }, 100);
  };

  // 处理流式LLM响应
  const handleStreamingResponse = async (
    conversation: Conversation,
    userMessage: ConversationMessage,
    queryText: string,
    selectedCollections: string[]
  ) => {
    const assistantMessageId = `msg_${Date.now()}_assistant`;
    setStreamingMessageId(assistantMessageId);

    // 创建初始的助手消息
    const assistantMessage: ConversationMessage = {
      id: assistantMessageId,
      type: 'assistant',
      content: '正在思考中...',
      timestamp: new Date().toISOString(),
      llm_response: '',
      is_streaming: true
    };

    const updatedConversation = {
      ...conversation,
      messages: [...conversation.messages, userMessage, assistantMessage]
    };

    setCurrentConversation(updatedConversation);
    setConversations(prev =>
      prev.map(conv => conv.id === conversation.id ? updatedConversation : conv)
    );

    try {
      // 调用新的LLM查询API（流式响应）
      const response = await api.query.llm({
        query: queryText,
        collections: selectedCollections,
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
                            content: '智能回答：',
                            is_streaming: true
                          }
                        : msg
                    );
                    return { ...prev, messages: updatedMessages };
                  });

                  setConversations(prev =>
                    prev.map(conv => {
                      if (conv.id === conversation.id) {
                        const updatedMessages = conv.messages.map(msg =>
                          msg.id === assistantMessageId
                            ? {
                                ...msg,
                                llm_response: accumulatedResponse,
                                content: '智能回答：',
                                is_streaming: true
                              }
                            : msg
                        );
                        return { ...conv, messages: updatedMessages };
                      }
                      return conv;
                    })
                  );
                }
              } catch (e) {
                console.error('解析流式数据失败:', e);
              }
            }
          }
        }
      }

      // 流式响应完成
      setCurrentConversation(prev => {
        if (!prev) return prev;
        const updatedMessages = prev.messages.map(msg =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                is_streaming: false,
                content: '智能回答：'
              }
            : msg
        );
        return { ...prev, messages: updatedMessages };
      });

      setConversations(prev =>
        prev.map(conv => {
          if (conv.id === conversation.id) {
            const updatedMessages = conv.messages.map(msg =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    is_streaming: false,
                    content: '智能回答：'
                  }
                : msg
            );
            return { ...conv, messages: updatedMessages };
          }
          return conv;
        })
      );

    } catch (error: any) {
      console.error('LLM查询失败:', error);
      const errorMessage = error.message || 'LLM查询失败';

      // 更新为错误消息
      setCurrentConversation(prev => {
        if (!prev) return prev;
        const updatedMessages = prev.messages.map(msg =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                content: `查询失败: ${errorMessage}`,
                is_streaming: false,
                llm_response: undefined
              }
            : msg
        );
        return { ...prev, messages: updatedMessages };
      });

      setConversations(prev =>
        prev.map(conv => {
          if (conv.id === conversation.id) {
            const updatedMessages = conv.messages.map(msg =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    content: `查询失败: ${errorMessage}`,
                    is_streaming: false,
                    llm_response: undefined
                  }
                : msg
            );
            return { ...conv, messages: updatedMessages };
          }
          return conv;
        })
      );

      message.error(errorMessage);
    } finally {
      setStreamingMessageId(null);
      scrollToLatestMessage();
    }
  };

  // 发送查询
  const handleQuery = async () => {
    if (!queryText.trim()) {
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
        title: queryText.slice(0, 20) + (queryText.length > 20 ? '...' : ''),
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
        title: queryText.slice(0, 20) + (queryText.length > 20 ? '...' : '')
      };
      setCurrentConversation(conversation);
      setConversations(prev =>
        prev.map(conv => conv.id === conversation!.id ? conversation! : conv)
      );
    }

    // 添加用户消息
    const userMessage: ConversationMessage = {
      id: `msg_${Date.now()}_user`,
      type: 'user',
      content: queryText,
      timestamp: new Date().toISOString(),
      selected_collections: [...selectedCollections]
    };

    setLoading(true);

    // 清空输入框
    setQueryText('');

    try {
      // 调用流式LLM响应处理
      await handleStreamingResponse(conversation, userMessage, queryText, selectedCollections);
    } catch (error: any) {
      console.error('处理查询失败:', error);
      message.error('处理查询失败');
    } finally {
      setLoading(false);
    }
  };

  // 从localStorage加载对话历史
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

  // 保存对话历史到localStorage - 优化性能
  const saveConversations = useCallback((convs: Conversation[]) => {
    try {
      localStorage.setItem('chromadb_conversations', JSON.stringify(convs));
    } catch (error) {
      console.error('保存对话历史失败:', error);
    }
  }, []);

  // 组件挂载时获取集合列表和对话历史
  useEffect(() => {
    fetchCollections();
    loadConversations();
  }, []);

  // 当对话列表变化时保存到localStorage
  useEffect(() => {
    if (conversations.length > 0) {
      saveConversations(conversations);
    }
  }, [conversations]);

  // 当切换对话时，自动滚动到对话开头
  useEffect(() => {
    if (currentConversation && currentConversation.messages.length > 0) {
      scrollToConversationTop();
    }
  }, [currentConversation]);

  // 如果没有集合，显示提示页面
  if (hasCollections === false) {
    return (
      <Layout style={{ height: '100vh' }}>
        <Layout>
          <Content style={{ padding: '16px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
            <Result
              icon={<DatabaseOutlined style={{ color: '#1890ff' }} />}
              title="当前没有可用集合"
              subTitle="智能查询功能需要至少一个集合才能使用，请先创建一个集合。"
              extra={[
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={onNavigateToCollections}
                  key="create"
                >
                  创建集合
                </Button>,
                <Button
                  icon={<ArrowLeftOutlined />}
                  onClick={onNavigateToCollections}
                  key="back"
                >
                  返回集合管理
                </Button>
              ]}
            />
          </Content>
        </Layout>
      </Layout>
    );
  }

  // 折叠状态下的左侧栏内容
  const collapsedLeftSiderContent = useMemo(() => (
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
            >💬</div>
          </Tooltip>
          
          <Tooltip title="快捷操作" placement="right">
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
            >⚡</div>
          </Tooltip>
        </Space>
      </div>
    </div>
  ), [createNewConversation]);

  // 展开状态下的左侧栏内容 - 移除集合选择，只保留对话历史和快捷操作
  const expandedLeftSiderContent = useMemo(() => (
    <div style={{ padding: 16 }}>
      <Collapse defaultActiveKey={['conversations', 'actions']}>
        <Panel header="💬 对话历史" key="conversations">
          <List
            size="small"
            dataSource={conversations}
            renderItem={(conversation) => (
              <List.Item
                style={{
                  cursor: 'pointer',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  backgroundColor: currentConversation?.id === conversation.id
                    ? '#f3f4f6'
                    : 'transparent',
                  border: currentConversation?.id === conversation.id
                    ? '1px solid #e5e7eb'
                    : '1px solid transparent',
                  marginBottom: '4px',
                  transition: 'background-color 0.2s ease',
                }}
                onClick={() => {
                  setCurrentConversation(conversation);
                  // 当选择历史对话时，自动设置该对话使用的集合
                  const firstUserMessage = conversation.messages.find(msg => msg.type === 'user');
                  if (firstUserMessage && firstUserMessage.selected_collections) {
                    setSelectedCollections(firstUserMessage.selected_collections);
                  }
                  if (responsive.isMobile) {
                    setLeftDrawerVisible(false);
                  }
                }}
                onMouseEnter={(e) => {
                  if (currentConversation?.id !== conversation.id) {
                    e.currentTarget.style.backgroundColor = '#f9fafb';
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
                    <Text
                      ellipsis
                      style={{
                        fontSize: '13px',
                        fontWeight: currentConversation?.id === conversation.id ? 600 : 500,
                        color: currentConversation?.id === conversation.id ? '#1d4ed8' : 'var(--ant-color-text)'
                      }}
                    >
                      {conversation.title}
                    </Text>
                  }
                  description={
                    <Text type="secondary" style={{ fontSize: '11px' }}>
                      {new Date(conversation.created_at).toLocaleString()}
                    </Text>
                  }
                />
              </List.Item>
            )}
            locale={{
              emptyText: (
                <div style={{ textAlign: 'center', padding: '16px' }}>
                  <MessageOutlined style={{ fontSize: '20px', color: '#d9d9d9', marginBottom: '8px' }} />
                  <div style={{ color: '#999', fontSize: '12px' }}>暂无对话历史</div>
                  <div style={{ color: '#ccc', fontSize: '11px' }}>点击"新对话"开始查询</div>
                </div>
              )
            }}
          />
        </Panel>

        <Panel header="⚡ 快捷操作" key="actions">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button
              type="primary"
              size="small"
              icon={<PlusOutlined />}
              block
              onClick={createNewConversation}
              style={{
                borderRadius: '6px',
                height: '32px'
              }}
            >
              新对话
            </Button>
            <Button
              size="small"
              icon={<DeleteOutlined />}
              block
              onClick={clearConversations}
              disabled={conversations.length === 0}
              style={{
                borderRadius: '6px',
                height: '32px',
                opacity: conversations.length === 0 ? 0.5 : 1
              }}
            >
              清空历史
            </Button>
          </Space>
        </Panel>
      </Collapse>
    </div>
  ), [responsive.isMobile, conversations, currentConversation, clearConversations, createNewConversation]);

  // 左侧栏内容
  const leftSiderContent = leftCollapsed ? collapsedLeftSiderContent : expandedLeftSiderContent;

  // 折叠状态下的右侧栏内容
  const collapsedRightSiderContent = useMemo(() => (
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
          <Tooltip title="选择集合" placement="left">
            <div style={{
              fontSize: '18px',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '6px',
              transition: 'background-color 0.2s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--ant-color-fill-tertiary)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >📚</div>
          </Tooltip>
          
          <Tooltip title="查询内容" placement="left">
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

          <Tooltip title="发送查询" placement="left">
            <div style={{
              fontSize: '18px',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '6px',
              transition: 'background-color 0.2s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--ant-color-fill-tertiary)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            onClick={handleQuery}
            >📤</div>
          </Tooltip>
        </Space>
      </div>
    </div>
  ), [handleQuery]);

  // 展开状态下的右侧栏内容 - 提取为独立组件以便复用，并使用useMemo优化
  const expandedRightSiderContent = useMemo(() => (
    <div style={{ padding: responsive.isMobile ? '16px' : '24px' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Title level={5} style={{ marginBottom: '16px' }}>
            <DatabaseOutlined style={{ marginRight: 8, color: '#3b82f6' }} />
            <span style={{ background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              选择集合
            </span>
          </Title>
          <Select
            mode="multiple"
            placeholder="选择要查询的集合"
            style={{ width: '100%' }}
            value={selectedCollections}
            onChange={setSelectedCollections}
            loading={collectionsLoading}
            maxTagCount="responsive"
          >
            {collections.map(collection => (
              <Select.Option key={collection.display_name} value={collection.display_name}>
                <Space>
                  <DatabaseOutlined />
                  <span>{collection.display_name}</span>
                  <Text type="secondary">({collection.count})</Text>
                </Space>
              </Select.Option>
            ))}
          </Select>
        </div>

        <div>
          <Title level={5} style={{ marginBottom: '16px' }}>
            <span style={{ background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              查询内容
            </span>
          </Title>
          <TextArea
            placeholder="输入您要查询的内容..."
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            rows={responsive.isMobile ? 3 : 4}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleQuery();
              }
            }}
            style={{
              borderRadius: '12px',
              fontSize: '14px',
              lineHeight: '1.5',
              color: '#1f2937',
              backgroundColor: '#ffffff',
              border: '1px solid #d1d5db'
            }}
          />
          <div style={{ marginTop: '8px', textAlign: 'right' }}>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              Enter 发送，Shift+Enter 换行
            </Text>
          </div>
        </div>

        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={() => {
            handleQuery();
            if (responsive.isMobile) {
              setRightDrawerVisible(false);
            }
          }}
          loading={loading}
          disabled={!queryText.trim() || selectedCollections.length === 0}
          style={{ 
            width: '100%',
            height: responsive.isMobile ? '52px' : '48px',
            fontSize: '16px',
            fontWeight: 600,
            borderRadius: '12px'
          }}
        >
          {loading ? '查询中...' : '发送查询'}
        </Button>
      </Space>
    </div>
  ), [responsive.isMobile, collections, selectedCollections, collectionsLoading, queryText, loading, handleQuery]);

  // 右侧栏内容
  const rightSiderContent = rightCollapsed ? collapsedRightSiderContent : expandedRightSiderContent;

  return (
    <Layout style={{ height: '100vh' }}>
      {/* 桌面端左侧对话历史 */}
      {!responsive.isMobile && (
        <Sider
          width={320}
          theme="light"
          collapsible
          collapsed={leftCollapsed}
          onCollapse={setLeftCollapsed}
          style={{
            backgroundColor: 'var(--ant-color-bg-container)',
            borderRight: '1px solid var(--ant-color-border)',
            height: '100%',
            overflow: 'auto',
          }}
        >
          {leftSiderContent}
        </Sider>
      )}

      <Layout>
        {/* 中间对话内容区域 */}
        <Content style={{ padding: '24px', display: 'flex', flexDirection: 'column' }} className="fade-in-up">
          <Card
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Space>
                  <SearchOutlined style={{ color: '#3b82f6' }} />
                  <span style={{ 
                    fontSize: '18px', 
                    fontWeight: 600,
                    background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent'
                  }}>
                    查询对话
                  </span>
                  {currentConversation && (
                    <Text type="secondary" style={{ fontSize: '14px', fontWeight: 500 }}>
                      - {currentConversation.title}
                    </Text>
                  )}
                </Space>
                <Space>
                  <ThemeToggle />
                  <Button
                    icon={<ArrowLeftOutlined />}
                    onClick={() => navigate('/collections')}
                    type="text"
                    style={{ 
                      borderRadius: '8px',
                      height: '36px',
                      padding: '0 16px'
                    }}
                  >
                    返回集合管理
                  </Button>
                </Space>
              </div>
            }
            style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
            bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '24px' }}
          >
            {currentConversation ? (
              <div
                ref={conversationContentRef}
                style={{ flex: 1, overflowY: 'auto', marginBottom: '16px' }}
              >
                {currentConversation.messages.length === 0 ? (
                  <Empty description="开始新的查询对话" />
                ) : (
                  <List
                    dataSource={currentConversation.messages}
                    renderItem={(message, index) => {
                      const isLatestMessage = index === currentConversation.messages.length - 1;
                      return (
                        <List.Item style={{ border: 'none', padding: '8px 0' }}>
                          <div
                            style={{ width: '100%' }}
                            ref={isLatestMessage ? latestMessageRef : null}
                          >
                          <div style={{
                            display: 'flex',
                            justifyContent: message.type === 'user' ? 'flex-end' : 'flex-start',
                            marginBottom: '16px'
                          }}>
                            <div style={{
                              maxWidth: '75%',
                              padding: '12px 16px',
                              borderRadius: message.type === 'user' ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
                              background: '#ffffff',
                              color: '#1f2937',
                              border: '1px solid #e5e7eb',
                              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                              fontWeight: 'normal'
                            }}>
                              {/* 用户查询内容或AI回答内容 */}
                              {message.type === 'user' ? (
                                <>
                                  <div style={{
                                    color: '#1f2937 !important',
                                    textShadow: 'none',
                                    fontWeight: 'normal',
                                    whiteSpace: 'pre-wrap',
                                    lineHeight: '1.6',
                                    WebkitTextFillColor: '#1f2937',
                                    opacity: 1
                                  }}>{message.content}</div>
                                  {message.selected_collections && (
                                    <div style={{ marginTop: '8px', fontSize: '12px', opacity: 0.8 }}>
                                      查询集合: {message.selected_collections.join(', ')}
                                    </div>
                                  )}
                                </>
                              ) : (
                                <>
                                  <div style={{
                                    color: '#1f2937 !important',
                                    textShadow: 'none',
                                    fontWeight: 'normal',
                                    lineHeight: '1.6',
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
                                      <span
                                        style={{
                                          display: 'inline-block',
                                          width: '8px',
                                          height: '20px',
                                          backgroundColor: '#1890ff',
                                          marginLeft: '2px'
                                        }}
                                        className="typing-cursor"
                                      />
                                    )}
                                  </div>
                                </>
                              )}

                              {/* 参考资料展示 - 只在AI回答消息中显示 */}
                              {message.type === 'assistant' && message.query_results && message.query_results.length > 0 && (
                                <div style={{ marginTop: '8px' }}>
                                  <Button
                                    type="link"
                                    size="small"
                                    style={{ padding: '0', height: 'auto', color: '#1890ff' }}
                                    onClick={() => {
                                      const referenceKey = `reference_${message.id}`;
                                      setExpandedResults(prev => {
                                        const newSet = new Set(prev);
                                        if (newSet.has(referenceKey)) {
                                          newSet.delete(referenceKey);
                                        } else {
                                          newSet.add(referenceKey);
                                        }
                                        return newSet;
                                      });
                                    }}
                                  >
                                    {expandedResults.has(`reference_${message.id}`) ? '收起参考资料' : `查看参考资料 (${message.query_results.length}条)`}
                                  </Button>

                                  {expandedResults.has(`reference_${message.id}`) && (
                                    <div style={{
                                      marginTop: '8px',
                                      maxHeight: '300px',
                                      overflowY: 'auto',
                                      border: '1px solid #e8e8e8',
                                      borderRadius: '6px',
                                      padding: '8px'
                                    }}>
                                      {message.query_results.map((result, index) => (
                                        <div key={result.id} style={{
                                          marginBottom: index < message.query_results!.length - 1 ? '8px' : '0',
                                          paddingBottom: index < message.query_results!.length - 1 ? '8px' : '0',
                                          borderBottom: index < message.query_results!.length - 1 ? '1px solid #f0f0f0' : 'none'
                                        }}>
                                          <div style={{
                                            fontSize: '12px',
                                            color: '#666',
                                            marginBottom: '4px',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '8px'
                                          }}>
                                            <span style={{ fontWeight: '600' }}>#{index + 1}</span>
                                            <span style={{
                                              backgroundColor: '#e6f7ff',
                                              color: '#0369a1',
                                              padding: '2px 6px',
                                              borderRadius: '4px',
                                              fontSize: '11px',
                                              fontWeight: '600'
                                            }}>
                                              相似度: {(Math.max(0, Math.min(100, (1 / (1 + result.distance)) * 100))).toFixed(1)}%
                                            </span>
                                            <span style={{ color: '#999' }}>
                                              {result.collection_name}
                                            </span>
                                          </div>
                                          <div style={{
                                            fontSize: '13px',
                                            color: '#333',
                                            lineHeight: '1.4'
                                          }}>
                                            {result.document.length > 150
                                              ? `${result.document.substring(0, 150)}...`
                                              : result.document
                                            }
                                          </div>
                                          {result.metadata.file_name && (
                                            <div style={{
                                              fontSize: '11px',
                                              color: '#999',
                                              marginTop: '2px'
                                            }}>
                                              📄 {result.metadata.file_name}
                                              {result.metadata.chunk_index !== undefined && ` • 块 ${result.metadata.chunk_index + 1}`}
                                            </div>
                                          )}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                          
                          {/* 查询结果展示 - 只在没有LLM回答时显示，或作为可展开的参考资料 */}
                          {message.query_results && message.query_results.length > 0 && !message.llm_response ? (
                            <div style={{ marginTop: '12px' }}>
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
                                    找到 {message.query_results.length} 个相关文档
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
                                  dataSource={message.query_results}
                                renderItem={(result, index) => {
                                  const isExpanded = expandedResults.has(result.id);

                                  return (
                                    <List.Item style={{ padding: '12px', backgroundColor: '#fafafa', marginBottom: '8px', borderRadius: '8px', border: '1px solid #e8e8e8' }}>
                                      <div style={{ width: '100%' }}>
                                        {/* 文档标题栏 - 始终显示 */}
                                        <div style={{
                                          display: 'flex',
                                          justifyContent: 'space-between',
                                          alignItems: 'center',
                                          marginBottom: isExpanded ? '12px' : '0',
                                          paddingBottom: isExpanded ? '8px' : '0',
                                          borderBottom: isExpanded ? '1px solid #e8e8e8' : 'none'
                                        }}>
                                          <Space>
                                            <Text strong style={{ color: '#1890ff', fontSize: '14px' }}>#{index + 1}</Text>
                                            <span style={{
                                              backgroundColor: '#e6f7ff',
                                              color: '#0050b3',
                                              padding: '4px 12px',
                                              borderRadius: '16px',
                                              fontSize: '12px',
                                              fontWeight: '600'
                                            }}>
                                              相似度: {(Math.max(0, Math.min(100, (1 / (1 + result.distance)) * 100))).toFixed(1)}%
                                            </span>
                                            <Text type="secondary" style={{ fontSize: '12px' }}>
                                              {result.collection_name}
                                            </Text>
                                            {/* 默认状态下显示文档简要信息 */}
                                            {!isExpanded && (
                                              <Text type="secondary" style={{ fontSize: '12px', marginLeft: '8px' }}>
                                                {result.metadata.file_name && `📄 ${result.metadata.file_name}`}
                                                {result.metadata.chunk_index !== undefined && ` • 第${result.metadata.chunk_index + 1}块`}
                                              </Text>
                                            )}
                                          </Space>
                                          <Space>
                                            <Button
                                              type="text"
                                              size="small"
                                              icon={isExpanded ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                                              onClick={() => toggleResultExpansion(result.id)}
                                              style={{ color: '#1890ff' }}
                                            >
                                              {isExpanded ? '收起' : '展开'}
                                            </Button>
                                            <Button
                                              type="text"
                                              size="small"
                                              icon={<CopyOutlined />}
                                              onClick={() => {
                                                navigator.clipboard.writeText(result.document);
                                                message.success('内容已复制到剪贴板');
                                              }}
                                              style={{ color: '#52c41a' }}
                                            >
                                              复制
                                            </Button>
                                          </Space>
                                        </div>

                                        {/* 文档内容 - 只在展开时显示 */}
                                        {isExpanded && (
                                          <>
                                            <div style={{ marginBottom: '12px' }}>
                                              <Text style={{
                                                whiteSpace: 'pre-wrap',
                                                fontSize: '13px',
                                                lineHeight: '1.5',
                                                color: '#333'
                                              }}>
                                                {result.document}
                                              </Text>
                                            </div>

                                            {/* 文档元信息 - 只在展开时显示详细信息 */}
                                            {result.metadata.file_name && (
                                              <div style={{
                                                marginTop: '8px',
                                                paddingTop: '8px',
                                                borderTop: '1px solid #f0f0f0'
                                              }}>
                                                <Space>
                                                  <Text type="secondary" style={{ fontSize: '12px' }}>
                                                    📄 文件: {result.metadata.file_name}
                                                  </Text>
                                                  {result.metadata.chunk_index !== undefined && (
                                                    <Text type="secondary" style={{ fontSize: '12px' }}>
                                                      📝 块序号: {result.metadata.chunk_index + 1}
                                                    </Text>
                                                  )}
                                                  {result.metadata.chunk_method && (
                                                    <Text type="secondary" style={{ fontSize: '12px' }}>
                                                      🔧 分块方法: {result.metadata.chunk_method}
                                                    </Text>
                                                  )}
                                                </Space>
                                              </div>
                                            )}
                                          </>
                                        )}
                                      </div>
                                    </List.Item>
                                  );
                                }}
                                />
                              )}
                            </div>
                          ) : message.query_results && message.query_results.length === 0 && (
                            <div style={{ marginTop: '12px', textAlign: 'center', padding: '20px', backgroundColor: '#fafafa', borderRadius: '6px' }}>
                              <Text type="secondary">未找到相关结果，请尝试调整查询内容或选择其他集合</Text>
                            </div>
                          )}
                          </div>
                        </List.Item>
                      );
                    }}
                  />
                )}
                {/* 滚动到最新消息的标记 */}
                <div ref={messagesEndRef} />
              </div>
            ) : (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Empty description="选择一个对话或创建新对话开始查询" />
              </div>
            )}
          </Card>
        </Content>

      {/* 桌面端右侧查询输入区域 */}
      {!responsive.isMobile && (
        <Sider
          width={380}
          theme="light"
          collapsible
          collapsed={rightCollapsed}
          onCollapse={setRightCollapsed}
          style={{
            backgroundColor: 'var(--ant-color-bg-container)',
            borderLeft: '1px solid var(--ant-color-border)',
            height: '100%',
            overflow: 'auto',
          }}
        >
          {rightSiderContent}
        </Sider>
      )}

      {/* 移动端抽屉 - 对话历史 */}
      <Drawer
        title="对话历史"
        placement="left"
        onClose={() => setLeftDrawerVisible(false)}
        open={leftDrawerVisible}
        width={responsive.screenWidth > 400 ? 320 : '85%'}
        bodyStyle={{ padding: 0 }}
      >
        {expandedLeftSiderContent}
      </Drawer>

      {/* 移动端抽屉 - 查询输入 */}
      <Drawer
        title="查询设置"
        placement="right"
        onClose={() => setRightDrawerVisible(false)}
        open={rightDrawerVisible}
        width={responsive.screenWidth > 400 ? 360 : '90%'}
        bodyStyle={{ padding: 0 }}
      >
        {expandedRightSiderContent}
      </Drawer>

      {/* 移动端悬浮按钮组 */}
      {responsive.isMobile && (
        <>
          <FloatButton.Group
            shape="circle"
            style={{ right: 16, bottom: 80 }}
          >
            <FloatButton
              icon={<MessageOutlined />}
              tooltip="对话历史"
              onClick={() => setLeftDrawerVisible(true)}
            />
            <FloatButton
              icon={<SettingOutlined />}
              tooltip="查询设置"
              onClick={() => setRightDrawerVisible(true)}
            />
          </FloatButton.Group>

          {/* 移动端快速查询按钮 */}
          {queryText.trim() && selectedCollections.length > 0 && (
            <FloatButton
              icon={<SendOutlined />}
              type="primary"
              style={{ right: 16, bottom: 16 }}
              onClick={handleQuery}
              tooltip="发送查询"
            />
          )}
        </>
      )}

      </Layout>
    </Layout>
  );
};

export default QueryPage;
