import React, { useState, useEffect } from 'react';
import {
  Layout,
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  message,
  Popconfirm,
  Space,
  Typography,
  Tag,
  Tooltip,
  Descriptions,
  Tabs,
  List,
  Empty,
  Spin,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  ReloadOutlined,
  DatabaseOutlined,
  EyeOutlined,
  FileTextOutlined,
  InfoCircleOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const { Header, Content } = Layout;
const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

// API基础URL
const API_BASE_URL = 'http://localhost:8000/api';

// 集合信息接口
interface CollectionInfo {
  name: string;
  display_name: string;
  count: number;
  metadata: Record<string, any>;
}

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

// 创建集合请求接口
interface CreateCollectionRequest {
  name: string;
  metadata?: Record<string, any>;
}

// 重命名集合请求接口
interface RenameCollectionRequest {
  old_name: string;
  new_name: string;
}

const CollectionManager: React.FC = () => {
  const [collections, setCollections] = useState<CollectionInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [renameModalVisible, setRenameModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedCollection, setSelectedCollection] = useState<CollectionInfo | null>(null);
  const [collectionDetail, setCollectionDetail] = useState<CollectionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [createForm] = Form.useForm();
  const [renameForm] = Form.useForm();

  // 获取集合列表
  const fetchCollections = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/collections`);
      setCollections(response.data);
    } catch (error) {
      console.error('获取集合列表失败:', error);
      message.error('获取集合列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取集合详细信息
  const fetchCollectionDetail = async (collection: CollectionInfo) => {
    setDetailLoading(true);
    try {
      const response = await axios.get(
        `${API_BASE_URL}/collections/${encodeURIComponent(collection.display_name)}/detail?limit=20`
      );
      setCollectionDetail(response.data);
      setDetailModalVisible(true);
    } catch (error: any) {
      console.error('获取集合详细信息失败:', error);
      const errorMessage = error.response?.data?.detail || '获取集合详细信息失败';
      message.error(errorMessage);
    } finally {
      setDetailLoading(false);
    }
  };

  // 创建集合
  const createCollection = async (values: CreateCollectionRequest) => {
    try {
      await axios.post(`${API_BASE_URL}/collections`, values);
      message.success(`集合 "${values.name}" 创建成功`);
      setCreateModalVisible(false);
      createForm.resetFields();
      fetchCollections();
    } catch (error: any) {
      console.error('创建集合失败:', error);
      const errorMessage = error.response?.data?.detail || '创建集合失败';
      message.error(errorMessage);
    }
  };

  // 删除集合
  const deleteCollection = async (collection: CollectionInfo) => {
    try {
      await axios.delete(`${API_BASE_URL}/collections/${encodeURIComponent(collection.display_name)}`);
      message.success(`集合 "${collection.display_name}" 删除成功`);
      fetchCollections();
    } catch (error: any) {
      console.error('删除集合失败:', error);
      const errorMessage = error.response?.data?.detail || '删除集合失败';
      message.error(errorMessage);
    }
  };

  // 重命名集合
  const renameCollection = async (values: { new_name: string }) => {
    if (!selectedCollection) return;

    try {
      const request: RenameCollectionRequest = {
        old_name: selectedCollection.display_name,
        new_name: values.new_name,
      };
      await axios.put(`${API_BASE_URL}/collections/rename`, request);
      message.success(`集合重命名成功`);
      setRenameModalVisible(false);
      renameForm.resetFields();
      setSelectedCollection(null);
      fetchCollections();
    } catch (error: any) {
      console.error('重命名集合失败:', error);
      const errorMessage = error.response?.data?.detail || '重命名集合失败';
      message.error(errorMessage);
    }
  };

  // 打开重命名模态框
  const openRenameModal = (collection: CollectionInfo) => {
    setSelectedCollection(collection);
    renameForm.setFieldsValue({ new_name: collection.display_name });
    setRenameModalVisible(true);
  };

  // 组件挂载时获取集合列表
  useEffect(() => {
    fetchCollections();
  }, []);

  // 表格列定义
  const columns = [
    {
      title: '集合名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string) => (
        <Space>
          <DatabaseOutlined />
          <strong>{text}</strong>
        </Space>
      ),
    },
    {
      title: '文档数量',
      dataIndex: 'count',
      key: 'count',
      render: (count: number) => (
        <Tag color={count > 0 ? 'blue' : 'default'}>
          {count} 个文档
        </Tag>
      ),
    },
    {
      title: '元数据',
      dataIndex: 'metadata',
      key: 'metadata',
      render: (metadata: Record<string, any>) => {
        const keys = Object.keys(metadata);
        if (keys.length === 0) {
          return <Tag color="default">无</Tag>;
        }
        return (
          <Tooltip title={JSON.stringify(metadata, null, 2)}>
            <Tag color="green">{keys.length} 个属性</Tag>
          </Tooltip>
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: CollectionInfo) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => fetchCollectionDetail(record)}
            loading={detailLoading && selectedCollection?.name === record.name}
          >
            查看
          </Button>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => openRenameModal(record)}
          >
            重命名
          </Button>
          <Popconfirm
            title="确认删除"
            description={`确定要删除集合 "${record.display_name}" 吗？此操作不可恢复。`}
            onConfirm={() => deleteCollection(record)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Layout>
      <Header>
        <div className="header-title">
          <Title level={3}>
            <DatabaseOutlined style={{ marginRight: 8 }} />
            ChromaDB 集合管理器
          </Title>
          <div className="header-actions">
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchCollections}
              loading={loading}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalVisible(true)}
            >
              创建集合
            </Button>
          </div>
        </div>
      </Header>

      <Content>
        <Card>
          <Table
            columns={columns}
            dataSource={collections}
            rowKey="name"
            loading={loading}
            scroll={{ y: 'calc(100vh - 280px)' }}
            pagination={{
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 个集合`,
              pageSize: 20,
              showLessItems: true,
            }}
            locale={{
              emptyText: '暂无集合数据',
            }}
          />
        </Card>
      </Content>

      {/* 创建集合模态框 */}
      <Modal
        title="创建新集合"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          createForm.resetFields();
        }}
        footer={null}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={createCollection}
        >
          <Form.Item
            label="集合名称"
            name="name"
            rules={[
              { required: true, message: '请输入集合名称' },
              { min: 1, max: 100, message: '集合名称长度应在1-100字符之间' },
            ]}
          >
            <Input placeholder="请输入集合名称（支持中文）" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                创建
              </Button>
              <Button onClick={() => {
                setCreateModalVisible(false);
                createForm.resetFields();
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 重命名集合模态框 */}
      <Modal
        title="重命名集合"
        open={renameModalVisible}
        onCancel={() => {
          setRenameModalVisible(false);
          renameForm.resetFields();
          setSelectedCollection(null);
        }}
        footer={null}
      >
        <Form
          form={renameForm}
          layout="vertical"
          onFinish={renameCollection}
        >
          <Form.Item
            label="新集合名称"
            name="new_name"
            rules={[
              { required: true, message: '请输入新的集合名称' },
              { min: 1, max: 100, message: '集合名称长度应在1-100字符之间' },
            ]}
          >
            <Input placeholder="请输入新的集合名称（支持中文）" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                确定
              </Button>
              <Button onClick={() => {
                setRenameModalVisible(false);
                renameForm.resetFields();
                setSelectedCollection(null);
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 集合详情模态框 */}
      <Modal
        title={
          <Space>
            <DatabaseOutlined />
            集合详情 - {collectionDetail?.display_name}
          </Space>
        }
        open={detailModalVisible}
        onCancel={() => {
          setDetailModalVisible(false);
          setCollectionDetail(null);
        }}
        footer={[
          <Button key="close" onClick={() => {
            setDetailModalVisible(false);
            setCollectionDetail(null);
          }}>
            关闭
          </Button>
        ]}
        width={800}
        style={{ top: 20 }}
      >
        {collectionDetail ? (
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
                            {doc.embedding && (
                              <Descriptions.Item label="向量维度">
                                <Tag color="purple">{doc.embedding.length} 维</Tag>
                              </Descriptions.Item>
                            )}
                          </Descriptions>
                        </Card>
                      </List.Item>
                    )}
                    pagination={{
                      pageSize: 5,
                      showSizeChanger: false,
                      showQuickJumper: true,
                    }}
                  />
                </div>
              )}
            </TabPane>
          </Tabs>
        ) : (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
          </div>
        )}
      </Modal>
    </Layout>
  );
};

export default CollectionManager;
