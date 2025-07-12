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
    navigate(`/collections/${encodeURIComponent(collection.display_name)}/detail`);
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
            onClick={() => handleViewCollection(record)}
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
    </Layout>
  );
};

export default CollectionManager;
