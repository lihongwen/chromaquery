import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Layout,
  Card,
  Button,
  Space,
  Typography,
  Tag,
  Descriptions,
  Tabs,
  List,
  Empty,
  Spin,
  message,
  Breadcrumb,
} from 'antd';
import {
  ArrowLeftOutlined,
  DatabaseOutlined,
  InfoCircleOutlined,
  FileTextOutlined,
  CalendarOutlined,
  HomeOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const { Header, Content } = Layout;
const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

// API基础URL
const API_BASE_URL = 'http://localhost:8000/api';

// 文档信息接口
interface DocumentInfo {
  id: string;
  document?: string;
  metadata?: Record<string, any>;
  embedding?: number[];
}

// 集合详细信息接口
interface CollectionDetail {
  name: string;
  display_name: string;
  count: number;
  metadata: Record<string, any>;
  created_time?: string;
  documents: DocumentInfo[];
  sample_documents: DocumentInfo[];
}

const CollectionDetail: React.FC = () => {
  const { collectionName } = useParams<{ collectionName: string }>();
  const navigate = useNavigate();
  const [collectionDetail, setCollectionDetail] = useState<CollectionDetail | null>(null);
  const [loading, setLoading] = useState(true);

  // 获取集合详细信息
  const fetchCollectionDetail = async () => {
    if (!collectionName) return;
    
    setLoading(true);
    try {
      const response = await axios.get(
        `${API_BASE_URL}/collections/${encodeURIComponent(collectionName)}/detail?limit=20`
      );
      setCollectionDetail(response.data);
    } catch (error: any) {
      console.error('获取集合详细信息失败:', error);
      const errorMessage = error.response?.data?.detail || '获取集合详细信息失败';
      message.error(errorMessage);
      // 如果集合不存在，返回列表页面
      if (error.response?.status === 404) {
        navigate('/');
      }
    } finally {
      setLoading(false);
    }
  };

  // 返回集合列表
  const handleGoBack = () => {
    navigate('/');
  };

  // 组件挂载时获取集合详情
  useEffect(() => {
    fetchCollectionDetail();
  }, [collectionName]);

  if (loading) {
    return (
      <Layout>
        <Header>
          <div className="header-title">
            <Title level={3}>
              <DatabaseOutlined style={{ marginRight: 8 }} />
              加载中...
            </Title>
          </div>
        </Header>
        <Content>
          <div style={{ textAlign: 'center', padding: 100 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>
              <Text type="secondary">正在加载集合详细信息...</Text>
            </div>
          </div>
        </Content>
      </Layout>
    );
  }

  if (!collectionDetail) {
    return (
      <Layout>
        <Header>
          <div className="header-title">
            <Title level={3}>
              <DatabaseOutlined style={{ marginRight: 8 }} />
              集合不存在
            </Title>
          </div>
        </Header>
        <Content>
          <div style={{ textAlign: 'center', padding: 100 }}>
            <Empty description="集合不存在或已被删除" />
            <Button type="primary" onClick={handleGoBack} style={{ marginTop: 16 }}>
              返回集合列表
            </Button>
          </div>
        </Content>
      </Layout>
    );
  }

  return (
    <Layout>
      <Header>
        <div className="header-title">
          <div>
            <Breadcrumb style={{ marginBottom: 8 }}>
              <Breadcrumb.Item>
                <HomeOutlined />
                <span style={{ marginLeft: 4 }}>首页</span>
              </Breadcrumb.Item>
              <Breadcrumb.Item>集合管理</Breadcrumb.Item>
              <Breadcrumb.Item>{collectionDetail.display_name}</Breadcrumb.Item>
            </Breadcrumb>
            <Title level={3} style={{ margin: 0 }}>
              <DatabaseOutlined style={{ marginRight: 8 }} />
              {collectionDetail.display_name}
            </Title>
          </div>
          <div className="header-actions">
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={handleGoBack}
            >
              返回列表
            </Button>
          </div>
        </div>
      </Header>

      <Content>
        <Card>
          <Tabs defaultActiveKey="basic">
            <TabPane tab={
              <span>
                <InfoCircleOutlined />
                基本信息
              </span>
            } key="basic">
              <Descriptions column={2} bordered>
                <Descriptions.Item label="集合名称" span={2}>
                  <Text strong>{collectionDetail.display_name}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="内部名称">
                  <Text code>{collectionDetail.name}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="文档数量">
                  <Tag color={collectionDetail.count > 0 ? 'blue' : 'default'}>
                    {collectionDetail.count} 个文档
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="向量维度">
                  <Space>
                    <Tag color="purple">1024 维</Tag>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      (ChromaDB 默认配置)
                    </Text>
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="向量模型">
                  <Text type="secondary">all-MiniLM-L6-v2 (默认)</Text>
                </Descriptions.Item>
                {collectionDetail.created_time && (
                  <Descriptions.Item label="创建时间" span={2}>
                    <Space>
                      <CalendarOutlined />
                      {collectionDetail.created_time}
                    </Space>
                  </Descriptions.Item>
                )}
                <Descriptions.Item label="元数据" span={2}>
                  {Object.keys(collectionDetail.metadata).length > 0 ? (
                    <div style={{ maxHeight: 200, overflow: 'auto' }}>
                      <pre style={{ margin: 0, fontSize: '12px' }}>
                        {JSON.stringify(collectionDetail.metadata, null, 2)}
                      </pre>
                    </div>
                  ) : (
                    <Text type="secondary">无元数据</Text>
                  )}
                </Descriptions.Item>
              </Descriptions>
            </TabPane>

            <TabPane tab={
              <span>
                <FileTextOutlined />
                文档内容 ({collectionDetail.count > 0 ? 
                  (collectionDetail.documents.length > 0 ? 
                    `全部 ${collectionDetail.documents.length}` : 
                    `样本 ${collectionDetail.sample_documents.length}`) : 
                  '0'})
              </span>
            } key="documents">
              {collectionDetail.count === 0 ? (
                <Empty description="该集合暂无文档" />
              ) : (
                <div>
                  {collectionDetail.count > 100 && (
                    <div style={{ marginBottom: 16, padding: 12, background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 6 }}>
                      <Text type="secondary">
                        <InfoCircleOutlined style={{ marginRight: 4 }} />
                        集合包含 {collectionDetail.count} 个文档，以下显示前 {collectionDetail.sample_documents.length} 个样本文档
                      </Text>
                    </div>
                  )}
                  
                  <List
                    dataSource={collectionDetail.documents.length > 0 ? collectionDetail.documents : collectionDetail.sample_documents}
                    renderItem={(doc, index) => (
                      <List.Item>
                        <Card size="small" style={{ width: '100%' }}>
                          <Descriptions size="small" column={1}>
                            <Descriptions.Item label="文档ID">
                              <Text code>{doc.id}</Text>
                            </Descriptions.Item>
                            {doc.document && (
                              <Descriptions.Item label="文档内容">
                                <Paragraph 
                                  ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
                                  style={{ margin: 0 }}
                                >
                                  {doc.document}
                                </Paragraph>
                              </Descriptions.Item>
                            )}
                            {doc.metadata && Object.keys(doc.metadata).length > 0 && (
                              <Descriptions.Item label="文档元数据">
                                <pre style={{ margin: 0, fontSize: '11px', maxHeight: 100, overflow: 'auto' }}>
                                  {JSON.stringify(doc.metadata, null, 2)}
                                </pre>
                              </Descriptions.Item>
                            )}
                            <Descriptions.Item label="向量信息">
                              {doc.embedding ? (
                                <Space>
                                  <Tag color="purple">{doc.embedding.length} 维向量</Tag>
                                  <Text type="secondary" style={{ fontSize: '12px' }}>
                                    (ChromaDB 默认: 1024维)
                                  </Text>
                                </Space>
                              ) : (
                                <Text type="secondary">暂无向量数据</Text>
                              )}
                            </Descriptions.Item>
                          </Descriptions>
                        </Card>
                      </List.Item>
                    )}
                    pagination={{
                      pageSize: 5,
                      showSizeChanger: false,
                      showQuickJumper: true,
                      showTotal: (total) => `共 ${total} 个文档`,
                    }}
                  />
                </div>
              )}
            </TabPane>
          </Tabs>
        </Card>
      </Content>
    </Layout>
  );
};

export default CollectionDetail;
