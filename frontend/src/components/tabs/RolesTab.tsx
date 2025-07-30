import React, { useState, useEffect } from 'react';
import {
  Layout,
  Card,
  Table,
  Button,
  Space,
  Typography,
  message,
  Modal,
  Form,
  Input,
  Switch,
  Popconfirm,
  Tag,
  Tooltip,
  Row,
  Col,
  Statistic
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  UserOutlined,
  MessageOutlined,
  EyeOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { roleApiService, type Role, type CreateRoleRequest, type UpdateRoleRequest } from '../../services/roleApi';

const { Content } = Layout;
const { Title, Paragraph } = Typography;
const { TextArea } = Input;

const RolesTab: React.FC = () => {
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [viewingRole, setViewingRole] = useState<Role | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadRoles();
  }, []);

  const loadRoles = async () => {
    setLoading(true);
    try {
      const data = await roleApiService.getRoles();
      setRoles(data);
    } catch (error) {
      message.error('加载角色列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingRole(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true });
    setModalVisible(true);
  };

  const handleEdit = (role: Role) => {
    setEditingRole(role);
    form.setFieldsValue(role);
    setModalVisible(true);
  };

  const handleView = (role: Role) => {
    setViewingRole(role);
    setViewModalVisible(true);
  };

  const handleDelete = async (roleId: string) => {
    try {
      await roleApiService.deleteRole(roleId);
      message.success('删除角色成功');
      loadRoles();
    } catch (error) {
      message.error('删除角色失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingRole) {
        // 更新角色
        await roleApiService.updateRole(editingRole.id, values as UpdateRoleRequest);
        message.success('更新角色成功');
      } else {
        // 创建角色
        await roleApiService.createRole(values as CreateRoleRequest);
        message.success('创建角色成功');
      }
      
      setModalVisible(false);
      loadRoles();
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message);
      } else {
        message.error(editingRole ? '更新角色失败' : '创建角色失败');
      }
    }
  };

  const columns: ColumnsType<Role> = [
    {
      title: '角色名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (text: string, record: Role) => (
        <Space>
          <UserOutlined />
          <span style={{ fontWeight: 500 }}>{text}</span>
          {!record.is_active && <Tag color="red">已禁用</Tag>}
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
      title: '提示词预览',
      dataIndex: 'prompt',
      key: 'prompt',
      width: 300,
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <span style={{ color: '#666' }}>
            {text.length > 50 ? `${text.substring(0, 50)}...` : text}
          </span>
        </Tooltip>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>
          {active ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, record: Role) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleView(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这个角色吗？"
            onConfirm={() => handleDelete(record.id)}
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
    <Layout style={{ padding: '24px', background: 'transparent' }}>
      <Content>
        <div style={{ marginBottom: '24px' }}>
          <Title level={2} style={{ margin: 0 }}>
            <UserOutlined style={{ marginRight: '8px' }} />
            角色管理
          </Title>
          <Paragraph type="secondary" style={{ marginTop: '8px' }}>
            管理AI助手的角色设定，每个角色包含专属的提示词，用于定制不同的对话风格和专业领域
          </Paragraph>
        </div>

        {/* 统计卡片 */}
        <Row gutter={16} style={{ marginBottom: '24px' }}>
          <Col span={8}>
            <Card>
              <Statistic
                title="总角色数"
                value={totalRoles}
                prefix={<UserOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="启用角色"
                value={activeRoles.length}
                prefix={<MessageOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="禁用角色"
                value={totalRoles - activeRoles.length}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
        </Row>

        {/* 角色列表 */}
        <Card
          title="角色列表"
          extra={
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
            >
              新建角色
            </Button>
          }
        >
          <Table
            columns={columns}
            dataSource={roles}
            rowKey="id"
            loading={loading}
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
          title={editingRole ? '编辑角色' : '新建角色'}
          open={modalVisible}
          onOk={handleSubmit}
          onCancel={() => setModalVisible(false)}
          width={600}
          okText="保存"
          cancelText="取消"
        >
          <Form
            form={form}
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
                { max: 500, message: '描述不能超过500个字符' }
              ]}
            >
              <Input placeholder="请输入角色描述（可选）" />
            </Form.Item>

            <Form.Item
              name="prompt"
              label="角色提示词"
              rules={[
                { required: true, message: '请输入角色提示词' }
              ]}
            >
              <TextArea
                rows={6}
                placeholder="请输入角色的专属提示词，这将影响AI的回答风格和专业领域..."
                showCount
              />
            </Form.Item>

            <Form.Item
              name="is_active"
              label="启用状态"
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
          width={700}
        >
          {viewingRole && (
            <div>
              <Row gutter={16} style={{ marginBottom: '16px' }}>
                <Col span={12}>
                  <strong>角色名称：</strong>{viewingRole.name}
                </Col>
                <Col span={12}>
                  <strong>状态：</strong>
                  <Tag color={viewingRole.is_active ? 'green' : 'red'}>
                    {viewingRole.is_active ? '启用' : '禁用'}
                  </Tag>
                </Col>
              </Row>
              
              {viewingRole.description && (
                <div style={{ marginBottom: '16px' }}>
                  <strong>描述：</strong>
                  <div style={{ marginTop: '8px' }}>{viewingRole.description}</div>
                </div>
              )}
              
              <div style={{ marginBottom: '16px' }}>
                <strong>提示词：</strong>
                <div style={{ 
                  marginTop: '8px', 
                  padding: '12px', 
                  background: '#f5f5f5', 
                  borderRadius: '6px',
                  whiteSpace: 'pre-wrap'
                }}>
                  {viewingRole.prompt}
                </div>
              </div>
              
              <Row gutter={16}>
                <Col span={12}>
                  <strong>创建时间：</strong>
                  <div>{new Date(viewingRole.created_at).toLocaleString()}</div>
                </Col>
                <Col span={12}>
                  <strong>更新时间：</strong>
                  <div>{new Date(viewingRole.updated_at).toLocaleString()}</div>
                </Col>
              </Row>
            </div>
          )}
        </Modal>
      </Content>
    </Layout>
  );
};

export default RolesTab;
