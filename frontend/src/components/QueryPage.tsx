import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout, Card, List, Input, Button, Select, Space, Typography, Spin, message, Empty } from 'antd';
import { SearchOutlined, SendOutlined, MessageOutlined, DatabaseOutlined, ArrowLeftOutlined, DeleteOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Sider, Content } = Layout;
const { Title, Text } = Typography;
const { TextArea } = Input;

// API基础URL
const API_BASE_URL = '/api';

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
}

const QueryPage: React.FC = () => {
  const navigate = useNavigate();

  // 状态管理
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [collections, setCollections] = useState<CollectionInfo[]>([]);
  const [selectedCollections, setSelectedCollections] = useState<string[]>([]);
  const [queryText, setQueryText] = useState('');
  const [loading, setLoading] = useState(false);
  const [collectionsLoading, setCollectionsLoading] = useState(false);
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());

  // 用于滚动到最新消息的引用
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const conversationContentRef = useRef<HTMLDivElement>(null);
  const latestMessageRef = useRef<HTMLDivElement>(null);

  // 获取集合列表
  const fetchCollections = async () => {
    setCollectionsLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/collections`);
      setCollections(response.data);
    } catch (error) {
      console.error('获取集合列表失败:', error);
      message.error('获取集合列表失败');
    } finally {
      setCollectionsLoading(false);
    }
  };

  // 创建新对话
  const createNewConversation = () => {
    const newConversation: Conversation = {
      id: `conv_${Date.now()}`,
      title: '新对话',
      created_at: new Date().toISOString(),
      messages: []
    };
    const updatedConversations = [newConversation, ...conversations];
    setConversations(updatedConversations);
    setCurrentConversation(newConversation);
  };

  // 清空对话历史
  const clearConversations = () => {
    setConversations([]);
    setCurrentConversation(null);
    localStorage.removeItem('chromadb_conversations');
    message.success('对话历史已清空');
  };

  // 切换查询结果的展开/收起状态
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

  // 滚动到最新消息（让最新消息显示在对话框顶部）
  const scrollToLatestMessage = () => {
    // 使用setTimeout确保DOM已更新
    setTimeout(() => {
      if (latestMessageRef.current) {
        latestMessageRef.current.scrollIntoView({
          behavior: 'smooth',
          block: 'start'  // 让最新消息显示在可视区域的顶部
        });
      }
    }, 100);
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

    const updatedConversation = {
      ...conversation,
      messages: [...conversation.messages, userMessage]
    };

    setCurrentConversation(updatedConversation);
    setConversations(prev => 
      prev.map(conv => conv.id === conversation!.id ? updatedConversation : conv)
    );

    setLoading(true);

    try {
      // 调用查询API
      const response = await axios.post(`${API_BASE_URL}/query`, {
        query: queryText,
        collections: selectedCollections,
        limit: 5
      });

      // 添加助手回复
      const results = response.data.results || [];
      const assistantMessage: ConversationMessage = {
        id: `msg_${Date.now()}_assistant`,
        type: 'assistant',
        content: results.length > 0
          ? `找到 ${results.length} 个相关结果（处理时间: ${(response.data.processing_time * 1000).toFixed(0)}ms）`
          : `未找到相关结果（处理时间: ${(response.data.processing_time * 1000).toFixed(0)}ms）`,
        timestamp: new Date().toISOString(),
        query_results: results
      };

      const finalConversation = {
        ...updatedConversation,
        messages: [...updatedConversation.messages, assistantMessage]
      };

      setCurrentConversation(finalConversation);
      setConversations(prev =>
        prev.map(conv => conv.id === conversation!.id ? finalConversation : conv)
      );

      // 清空输入框
      setQueryText('');

      // 滚动到最新消息
      scrollToLatestMessage();

    } catch (error: any) {
      console.error('查询失败:', error);
      const errorMessage = error.response?.data?.detail || '查询失败';
      message.error(errorMessage);

      // 添加错误消息
      const errorAssistantMessage: ConversationMessage = {
        id: `msg_${Date.now()}_assistant`,
        type: 'assistant',
        content: `查询失败: ${errorMessage}`,
        timestamp: new Date().toISOString()
      };

      const errorConversation = {
        ...updatedConversation,
        messages: [...updatedConversation.messages, errorAssistantMessage]
      };

      setCurrentConversation(errorConversation);
      setConversations(prev =>
        prev.map(conv => conv.id === conversation!.id ? errorConversation : conv)
      );

      // 滚动到最新消息（包括错误消息）
      scrollToLatestMessage();
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

  // 保存对话历史到localStorage
  const saveConversations = (convs: Conversation[]) => {
    try {
      localStorage.setItem('chromadb_conversations', JSON.stringify(convs));
    } catch (error) {
      console.error('保存对话历史失败:', error);
    }
  };

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

  return (
    <Layout style={{ height: '100vh' }}>
      {/* 左侧对话历史 */}
      <Sider width={300} style={{ background: '#fff', borderRight: '1px solid #f0f0f0' }}>
        <div style={{ padding: '16px' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Title level={4} style={{ margin: 0 }}>
                <MessageOutlined style={{ marginRight: 8 }} />
                对话历史
              </Title>
              <Space>
                <Button
                  type="text"
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={clearConversations}
                  disabled={conversations.length === 0}
                  title="清空对话历史"
                />
                <Button type="primary" size="small" onClick={createNewConversation}>
                  新对话
                </Button>
              </Space>
            </div>
            
            <List
              size="small"
              dataSource={conversations}
              renderItem={(conversation) => (
                <List.Item
                  style={{
                    cursor: 'pointer',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    backgroundColor: currentConversation?.id === conversation.id ? '#e6f7ff' : 'transparent',
                    border: currentConversation?.id === conversation.id ? '1px solid #91d5ff' : '1px solid transparent'
                  }}
                  onClick={() => setCurrentConversation(conversation)}
                >
                  <List.Item.Meta
                    title={<Text ellipsis style={{ fontSize: '14px' }}>{conversation.title}</Text>}
                    description={
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {new Date(conversation.created_at).toLocaleString()}
                      </Text>
                    }
                  />
                </List.Item>
              )}
              locale={{
                emptyText: (
                  <div style={{ textAlign: 'center', padding: '20px' }}>
                    <MessageOutlined style={{ fontSize: '24px', color: '#d9d9d9', marginBottom: '8px' }} />
                    <div style={{ color: '#999' }}>暂无对话历史</div>
                    <div style={{ color: '#ccc', fontSize: '12px' }}>点击"新对话"开始查询</div>
                  </div>
                )
              }}
            />
          </Space>
        </div>
      </Sider>

      <Layout>
        {/* 中间对话内容区域 */}
        <Content style={{ padding: '16px', display: 'flex', flexDirection: 'column' }}>
          <Card
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Space>
                  <SearchOutlined />
                  <span>查询对话</span>
                  {currentConversation && (
                    <Text type="secondary" style={{ fontSize: '14px' }}>
                      - {currentConversation.title}
                    </Text>
                  )}
                </Space>
                <Button
                  icon={<ArrowLeftOutlined />}
                  onClick={() => navigate('/')}
                  type="text"
                >
                  返回集合管理
                </Button>
              </div>
            }
            style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
            bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '16px' }}
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
                            marginBottom: '8px'
                          }}>
                            <div style={{
                              maxWidth: '70%',
                              padding: '12px 16px',
                              borderRadius: '12px',
                              backgroundColor: message.type === 'user' ? '#1890ff' : '#f6f6f6',
                              color: message.type === 'user' ? '#fff' : '#000'
                            }}>
                              <div>{message.content}</div>
                              {message.selected_collections && (
                                <div style={{ marginTop: '8px', fontSize: '12px', opacity: 0.8 }}>
                                  查询集合: {message.selected_collections.join(', ')}
                                </div>
                              )}
                            </div>
                          </div>
                          
                          {/* 查询结果展示 */}
                          {message.query_results && message.query_results.length > 0 ? (
                            <div style={{ marginTop: '12px' }}>
                              <Title level={5}>查询结果:</Title>
                              <List
                                size="small"
                                dataSource={message.query_results}
                                renderItem={(result, index) => {
                                  const isExpanded = expandedResults.has(result.id);
                                  const shouldTruncate = result.document.length > 200;
                                  const displayText = shouldTruncate && !isExpanded
                                    ? `${result.document.substring(0, 200)}...`
                                    : result.document;

                                  return (
                                    <List.Item style={{ padding: '8px 12px', backgroundColor: '#fafafa', marginBottom: '8px', borderRadius: '6px' }}>
                                      <List.Item.Meta
                                        title={
                                          <Space>
                                            <Text strong>#{index + 1}</Text>
                                            <Text type="secondary">
                                              相似度: {((1 - result.distance) * 100).toFixed(1)}%
                                            </Text>
                                            <Text type="secondary">集合: {result.collection_name}</Text>
                                          </Space>
                                        }
                                        description={
                                          <div>
                                            <div style={{ marginBottom: '8px' }}>
                                              <Text style={{ whiteSpace: 'pre-wrap' }}>
                                                {displayText}
                                              </Text>
                                              {shouldTruncate && (
                                                <Button
                                                  type="link"
                                                  size="small"
                                                  style={{ padding: '0 4px', height: 'auto' }}
                                                  onClick={() => toggleResultExpansion(result.id)}
                                                >
                                                  {isExpanded ? '收起' : '查看完整内容'}
                                                </Button>
                                              )}
                                            </div>
                                            {result.metadata.file_name && (
                                              <div style={{ marginTop: '4px' }}>
                                                <Text type="secondary" style={{ fontSize: '12px' }}>
                                                  📄 文件: {result.metadata.file_name}
                                                </Text>
                                                {result.metadata.chunk_index !== undefined && (
                                                  <Text type="secondary" style={{ fontSize: '12px', marginLeft: '8px' }}>
                                                    📝 块: {result.metadata.chunk_index + 1}
                                                  </Text>
                                                )}
                                              </div>
                                            )}
                                          </div>
                                        }
                                      />
                                    </List.Item>
                                  );
                                }}
                              />
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

        {/* 右侧查询输入区域 */}
        <Sider width={350} style={{ background: '#fff', borderLeft: '1px solid #f0f0f0' }}>
          <div style={{ padding: '16px' }}>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <div>
                <Title level={5}>
                  <DatabaseOutlined style={{ marginRight: 8 }} />
                  选择集合
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
                <Title level={5}>查询内容</Title>
                <TextArea
                  placeholder="输入您要查询的内容..."
                  value={queryText}
                  onChange={(e) => setQueryText(e.target.value)}
                  rows={4}
                  onPressEnter={(e) => {
                    if (!e.shiftKey) {
                      e.preventDefault();
                      handleQuery();
                    }
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
                onClick={handleQuery}
                loading={loading}
                disabled={!queryText.trim() || selectedCollections.length === 0}
                style={{ width: '100%' }}
              >
                {loading ? '查询中...' : '发送查询'}
              </Button>
            </Space>
          </div>
        </Sider>
      </Layout>
    </Layout>
  );
};

export default QueryPage;
