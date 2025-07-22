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
  Select
} from 'antd';
import {
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  EyeOutlined,
  CopyOutlined,
  SearchOutlined,
  DatabaseOutlined
} from '@ant-design/icons';
import { useResponsive } from '../../hooks/useResponsive';
import { api } from '../../config/api';

const { Sider, Content } = Layout;
const { Panel } = Collapse;
const { Text } = Typography;

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
  const [messages, setMessages] = useState<QueryMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [queryHistory, setQueryHistory] = useState<string[]>([]);
  const [settings, setSettings] = useState<QuerySettings>({
    similarity_threshold: 0.3,
    n_results: 10,
  });
  const [siderCollapsed, setSiderCollapsed] = useState(false);
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());
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
  }, [messages]);

  useEffect(() => {
    fetchCollections();
  }, []);

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

    const userMessage: QueryMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString(),
      selected_collections: [...selectedCollections],
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setLoading(true);
    setQueryHistory(prev => [query, ...prev.slice(0, 9)]);

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

    setMessages(prev => [...prev, assistantMessage]);

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
                  setMessages(prev =>
                    prev.map(msg =>
                      msg.id === assistantMessageId
                        ? {
                            ...msg,
                            documents_found: data.metadata.documents_found,
                            results: data.metadata.query_results || [],
                            content: `智能回答：（找到 ${data.metadata.documents_found} 个相关文档）`
                          }
                        : msg
                    )
                  );
                }

                if (data.content) {
                  accumulatedResponse += data.content;

                  // 更新消息内容
                  setMessages(prev =>
                    prev.map(msg =>
                      msg.id === assistantMessageId
                        ? {
                            ...msg,
                            llm_response: accumulatedResponse,
                            is_streaming: true
                          }
                        : msg
                    )
                  );
                }

                // 检查是否完成
                if (data.finish_reason) {
                  setMessages(prev =>
                    prev.map(msg =>
                      msg.id === assistantMessageId
                        ? {
                            ...msg,
                            is_streaming: false
                          }
                        : msg
                    )
                  );
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
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                content: `❌ 查询失败: ${errorMessage}`,
                is_streaming: false,
                llm_response: undefined
              }
            : msg
        )
      );

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

  const siderContent = (
    <div style={{ padding: 16 }}>
      <Collapse defaultActiveKey={['collections', 'settings']}>
        <Panel header="📚 集合选择" key="collections">
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
                dropdownStyle={{
                  minWidth: '400px',
                  maxWidth: '500px',
                  zIndex: 1050
                }}
                optionLabelProp="label"
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
                      width: '100%',
                      minWidth: '350px'
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
                          whiteSpace: 'nowrap',
                          maxWidth: '250px'
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
        </Panel>

        <Panel header="📝 查询历史" key="history">
          <List
            size="small"
            dataSource={queryHistory}
            renderItem={(query) => (
              <List.Item>
                <Button
                  type="text"
                  size="small"
                  onClick={() => setInputValue(query)}
                  style={{
                    textAlign: 'left',
                    width: '100%',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {query}
                </Button>
              </List.Item>
            )}
          />
        </Panel>

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

  return (
    <Layout style={{ height: 'calc(100vh - 120px)', minHeight: '500px' }}>
      {!isMobile && (
        <Sider
          width={300}
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
            {messages.length === 0 ? (
              <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100%',
                flexDirection: 'column'
              }}>
                <Empty
                  description={
                    <div>
                      <div style={{ marginBottom: 8 }}>开始您的智能查询</div>
                      {selectedCollections.length === 0 ? (
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          请先在左侧选择要查询的集合
                        </Text>
                      ) : (
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          已选择 {selectedCollections.length} 个集合，可以开始查询了
                        </Text>
                      )}
                    </div>
                  }
                  image={<SearchOutlined style={{ fontSize: 64, color: 'var(--ant-color-text-secondary)' }} />}
                />
              </div>
            ) : (
              <>
                {messages.map((message) => (
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
                          background: message.type === 'user'
                            ? '#ffffff'
                            : 'var(--ant-color-bg-container)',
                          color: message.type === 'user' ? '#000000' : 'var(--ant-color-text)',
                          border: message.type === 'user' ? '2px solid #3b82f6' : '1px solid var(--ant-color-border)',
                          boxShadow: message.type === 'user' ? '0 2px 8px rgba(59, 130, 246, 0.2)' : undefined
                        }}
                        bodyStyle={{
                          padding: '12px 16px',
                        }}
                      >
                        <div style={{
                          color: message.type === 'user' ? '#000000' : 'var(--ant-color-text)',
                          lineHeight: '1.5',
                          textShadow: 'none',
                          fontWeight: message.type === 'user' ? '500' : 'normal'
                        }}>
                          <span style={{
                            color: message.type === 'user' ? '#000000 !important' : 'inherit',
                            textShadow: 'none',
                            fontSize: '14px',
                            fontWeight: message.type === 'user' ? '500' : 'normal'
                          }}>
                            {message.content}
                          </span>
                          {message.selected_collections && (
                            <div style={{ marginTop: 8 }}>
                              <Text
                                style={{
                                  fontSize: '12px',
                                  color: message.type === 'user' ? '#666666' : 'var(--ant-color-text-secondary)',
                                  fontWeight: message.type === 'user' ? 'normal' : 'normal'
                                }}
                              >
                                查询集合: {message.selected_collections.join(', ')}
                              </Text>
                            </div>
                          )}
                        </div>

                        {/* LLM响应内容 */}
                        {message.llm_response && (
                          <div style={{
                            marginTop: 12,
                            padding: '12px',
                            backgroundColor: 'var(--ant-color-bg-layout)',
                            borderRadius: '8px',
                            border: '1px solid var(--ant-color-border)',
                          }}>
                            <div style={{
                              whiteSpace: 'pre-wrap',
                              lineHeight: '1.6',
                              color: 'var(--ant-color-text)',
                            }}>
                              {message.llm_response}
                              {message.is_streaming && (
                                <span className="typing-cursor">|</span>
                              )}
                            </div>
                          </div>
                        )}

                        <div style={{
                          marginTop: 8,
                          fontSize: '12px',
                          opacity: 0.8,
                          color: message.type === 'user' ? '#666666' : 'var(--ant-color-text-secondary)',
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
                          <Alert
                            message={`找到 ${message.results.length} 个相关文档`}
                            type="success"
                            showIcon
                            style={{ marginBottom: 12 }}
                          />
                          
                          <List
                            size="small"
                            dataSource={message.results}
                            renderItem={(result) => (
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
                                    </Space>
                                  }
                                  extra={
                                    <Space>
                                      <Button
                                        size="small"
                                        icon={<EyeOutlined />}
                                        type="text"
                                        onClick={() => toggleResultExpansion(result.id)}
                                      >
                                        {expandedResults.has(result.id) ? '收起' : '查看'}
                                      </Button>
                                      <Button 
                                        size="small" 
                                        icon={<CopyOutlined />}
                                        type="text"
                                        onClick={() => handleCopyContent(result.document)}
                                      >
                                        复制
                                      </Button>
                                    </Space>
                                  }
                                >
                                  <Text>
                                    {expandedResults.has(result.id)
                                      ? result.document
                                      : result.document.length > 200
                                        ? result.document.substring(0, 200) + '...'
                                        : result.document
                                    }
                                  </Text>
                                </Card>
                              </List.Item>
                            )}
                          />
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
                message="请先在左侧选择要查询的集合"
                type="warning"
                showIcon
                style={{ marginBottom: 12 }}
              />
            )}

            <Input.Search
              placeholder={selectedCollections.length > 0 ? "输入您的查询..." : "请先选择集合"}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onSearch={handleQuery}
              enterButton={<SendOutlined />}
              size="large"
              loading={loading}
              disabled={loading || selectedCollections.length === 0}
              style={{
                color: '#1f2937',
                backgroundColor: '#ffffff'
              }}
            />

            {selectedCollections.length > 0 && (
              <div style={{ marginTop: 8, fontSize: '12px', color: 'var(--ant-color-text-secondary)' }}>
                已选择 {selectedCollections.length} 个集合: {selectedCollections.join(', ')}
              </div>
            )}
          </div>
        </div>
      </Content>
    </Layout>
  );
};

export default QueryTab;