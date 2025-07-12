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
  Table,
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

// API基础URL
const API_BASE_URL = '/api';

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
          <Tabs
            defaultActiveKey="documents"
            items={[
              {
                key: 'documents',
                label: (
                  <span>
                    <FileTextOutlined />
                    文档内容 ({collectionDetail.count > 0 ?
                      (collectionDetail.documents.length > 0 ?
                        `全部 ${collectionDetail.documents.length}` :
                        `样本 ${collectionDetail.sample_documents.length}`) :
                      '0'})
                  </span>
                ),
                children: (
                  collectionDetail.count === 0 ? (
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

                      <Table
                        dataSource={(collectionDetail.documents.length > 0 ? collectionDetail.documents : collectionDetail.sample_documents).map((doc, index) => ({
                          ...doc,
                          key: doc.id,
                          index: index + 1
                        }))}
                        columns={[
                          {
                            title: '序号',
                            dataIndex: 'index',
                            key: 'index',
                            width: 60,
                            align: 'center',
                            render: (index) => (
                              <Text strong style={{ color: '#1890ff' }}>
                                #{index}
                              </Text>
                            )
                          },
                          {
                            title: '文档ID',
                            dataIndex: 'id',
                            key: 'id',
                            width: 200,
                            responsive: ['md'],
                            render: (id) => (
                              <Text code style={{ fontSize: '12px' }}>
                                {id}
                              </Text>
                            )
                          },
                          {
                            title: '内容预览',
                            dataIndex: 'document',
                            key: 'document',
                            ellipsis: true,
                            render: (document) => (
                              document ? (
                                <Paragraph
                                  ellipsis={{
                                    rows: 2,
                                    expandable: true,
                                    symbol: '展开',
                                    tooltip: '点击展开完整内容'
                                  }}
                                  style={{
                                    margin: 0,
                                    fontSize: '13px',
                                    lineHeight: '1.4',
                                    maxWidth: '300px'
                                  }}
                                >
                                  {document}
                                </Paragraph>
                              ) : (
                                <Text type="secondary" style={{ fontSize: '12px' }}>
                                  无内容
                                </Text>
                              )
                            )
                          },
                          {
                            title: '元数据',
                            dataIndex: 'metadata',
                            key: 'metadata',
                            width: 200,
                            responsive: ['lg'],
                            render: (metadata) => (
                              metadata && Object.keys(metadata).length > 0 ? (
                                <div style={{
                                  maxHeight: '80px',
                                  overflow: 'auto',
                                  fontSize: '11px',
                                  fontFamily: 'Monaco, Consolas, monospace',
                                  backgroundColor: '#f6f8fa',
                                  padding: '4px 8px',
                                  borderRadius: '3px',
                                  border: '1px solid #e1e4e8'
                                }}>
                                  <pre style={{ margin: 0, color: '#586069' }}>
                                    {JSON.stringify(metadata, null, 2)}
                                  </pre>
                                </div>
                              ) : (
                                <Text type="secondary" style={{ fontSize: '12px' }}>
                                  无元数据
                                </Text>
                              )
                            )
                          },
                          {
                            title: '向量信息',
                            dataIndex: 'embedding',
                            key: 'embedding',
                            width: 120,
                            align: 'center',
                            render: (embedding) => (
                              embedding ? (
                                <Tag color="purple" style={{ fontSize: '11px' }}>
                                  {embedding.length}维
                                </Tag>
                              ) : (
                                <Tag color="default" style={{ fontSize: '11px' }}>
                                  无向量
                                </Tag>
                              )
                            )
                          },
                          {
                            title: '统计信息',
                            key: 'stats',
                            width: 150,
                            responsive: ['xl'],
                            render: (_, record) => (
                              <div style={{ fontSize: '11px' }}>
                                <div>
                                  <Text type="secondary">
                                    字符: {record.document ? record.document.length : 0}
                                  </Text>
                                </div>
                                <div>
                                  <Text type="secondary">
                                    元数据: {record.metadata ? Object.keys(record.metadata).length : 0}项
                                  </Text>
                                </div>
                              </div>
                            )
                          }
                        ]}
                        pagination={{
                          pageSize: 8,
                          showSizeChanger: true,
                          showQuickJumper: true,
                          showTotal: (total, range) => `第 ${range[0]}-${range[1]} 项，共 ${total} 个文档`,
                          pageSizeOptions: ['5', '8', '10', '20'],
                        }}
                        size="small"
                        bordered
                        scroll={{ x: 1200 }}
                      />
                    </div>
                  )
                )
              },

              {
                key: 'basic',
                label: (
                  <span>
                    <InfoCircleOutlined />
                    基本信息
                  </span>
                ),
                children: (
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
                )
              }
            ]}
          />
        </Card>
      </Content>
    </Layout>
  );
};

export default CollectionDetail;
