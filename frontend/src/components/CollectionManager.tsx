import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  ReloadOutlined,
  DatabaseOutlined,
  EyeOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const { Header, Content } = Layout;
const { Title } = Typography;

// API基础URL
const API_BASE_URL = '/api';

// 集合信息接口
interface CollectionInfo {
  name: string;
  display_name: string;
  count: number;
  metadata: Record<string, any>;
  chunk_count?: number;
  uploaded_files?: string[];
  files_count?: number;
  chunk_statistics?: {
    total_chunks: number;
    files_count: number;
    methods_used: string[];
  };
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
  const navigate = useNavigate();
  const [collections, setCollections] = useState<CollectionInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [renameModalVisible, setRenameModalVisible] = useState(false);
  const [selectedCollection, setSelectedCollection] = useState<CollectionInfo | null>(null);
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

  // 查看集合详情
  const handleViewCollection = (collection: CollectionInfo) => {
    navigate(`/collections/${encodeURIComponent(collection.display_name)}/detail?from=collections`);
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
      width: '25%',
      ellipsis: {
        showTitle: false,
      },
      render: (text: string) => (
        <Space>
          <DatabaseOutlined />
          <strong
            title={text}
            style={{
              maxWidth: '120px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              display: 'inline-block'
            }}
          >
            {text}
          </strong>
        </Space>
      ),
    },
    {
      title: '文件数量',
      dataIndex: 'files_count',
      key: 'files_count',
      width: '18%',
      render: (filesCount: number | undefined, record: CollectionInfo) => {
        // 优先使用chunk_statistics中的files_count，其次使用filesCount，最后默认为0
        const count = record.chunk_statistics?.files_count ?? filesCount ?? 0;
        const totalChunks = record.chunk_statistics?.total_chunks ?? record.count;

        return (
          <div>
            <Tag color={count > 0 ? 'blue' : 'default'} size="small">
              {count}文件
            </Tag>
            {count > 0 && totalChunks > 0 && (
              <div style={{ fontSize: '11px', color: '#999', marginTop: 2 }}>
                {totalChunks}块
              </div>
            )}
          </div>
        );
      },
    },
    {
      title: '向量信息',
      key: 'vector_info',
      width: '18%',
      render: (record: CollectionInfo) => {
        const metadata = record.metadata || {};
        const vectorDimension = metadata.vector_dimension;
        const embeddingModel = metadata.embedding_model;

        return (
          <div>
            {vectorDimension && (
              <Tag color="purple" size="small" style={{ marginBottom: 2 }}>
                {vectorDimension}维
              </Tag>
            )}
            {embeddingModel && (
              <Tag color="green" size="small">
                {embeddingModel === 'alibaba-text-embedding-v4' ? '阿里云' :
                 embeddingModel === 'text-embedding-ada-002' ? 'OpenAI' :
                 embeddingModel.includes('alibaba') ? '阿里云' : '默认'}
              </Tag>
            )}
            {!vectorDimension && !embeddingModel && (
              <Tag color="default" size="small">未知</Tag>
            )}
          </div>
        );
      },
    },
    {
      title: '分块信息',
      key: 'chunk_info',
      width: '14%',
      render: (record: CollectionInfo) => {
        const chunkStats = record.chunk_statistics;
        const methodsUsed = chunkStats?.methods_used || [];

        return (
          <div>
            {methodsUsed.length > 0 ? (
              methodsUsed.map((method, index) => (
                <Tag key={index} color="orange" size="small" style={{ marginBottom: 2 }}>
                  {method === 'recursive' ? '递归' :
                   method === 'fixed_size' ? '固定' :
                   method === 'semantic' ? '语义' : method}
                </Tag>
              ))
            ) : (
              <Tag color="default" size="small">未知</Tag>
            )}
          </div>
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: '25%',
      render: (_: any, record: CollectionInfo) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewCollection(record)}
            title="查看集合详情"
          >
            查看
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openRenameModal(record)}
            title="重命名集合"
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
              size="small"
              danger
              icon={<DeleteOutlined />}
              title="删除集合"
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
              icon={<SearchOutlined />}
              onClick={() => navigate('/query')}
              disabled={collections.length === 0}
              title={collections.length === 0 ? '请先创建一个集合' : '进入智能查询'}
            >
              智能查询
            </Button>
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
        {/* 智能查询提示 */}
        {collections.length > 0 && (
          <div style={{ marginBottom: '16px' }}>
            <Card size="small" style={{ backgroundColor: '#f6ffed', border: '1px solid #b7eb8f' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span style={{ color: '#52c41a' }}>
                    <SearchOutlined style={{ marginRight: 8 }} />
                    您已有 {collections.length} 个集合，可以使用智能查询功能进行文档检索和AI问答
                  </span>
                </div>
                <Button
                  type="primary"
                  size="small"
                  icon={<SearchOutlined />}
                  onClick={() => navigate('/query')}
                >
                  立即体验
                </Button>
              </div>
            </Card>
          </div>
        )}

        <Card>
          <Table
            columns={columns}
            dataSource={collections}
            rowKey="name"
            loading={loading}
            scroll={{ y: 'calc(100vh - 280px)' }}
            tableLayout="fixed"
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
    </Layout>
  );
};

export default CollectionManager;
