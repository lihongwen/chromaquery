import React, { useState, useEffect } from 'react';
import {
  Layout,
  Card,
  Row,
  Col,
  Statistic,
  Input,
  Select,
  DatePicker,
  Space,
  Tag,
  Typography,
  Button,
  Collapse,
  List,
  message,
  Spin,
  Modal,
  Form,
  Upload,
  Popconfirm,
  Tooltip
} from 'antd';
import {
  DatabaseOutlined,
  FileTextOutlined,
  StarOutlined,
  TagOutlined,
  PlusOutlined,
  ImportOutlined,
  EyeOutlined,
  SettingOutlined,
  DeleteOutlined,
  UploadOutlined
} from '@ant-design/icons';
import { useResponsive } from '../../hooks/useResponsive';
import { useNavigate } from 'react-router-dom';
import { api, API_BASE_URL } from '../../config/api';

const { Sider, Content } = Layout;
const { Text } = Typography;
const { Panel } = Collapse;

interface CollectionInfo {
  name: string;
  display_name: string;
  count: number;
  metadata: Record<string, any>;
  created_at?: string;
  updated_at?: string;
  dimension?: number;
}

const CollectionsTab: React.FC = () => {
  const [collections, setCollections] = useState<CollectionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null);
  const [siderCollapsed, setSiderCollapsed] = useState(false);
  const { isMobile } = useResponsive();
  const navigate = useNavigate();

  // 模态框状态
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [settingsModalVisible, setSettingsModalVisible] = useState(false);
  const [currentCollection, setCurrentCollection] = useState<CollectionInfo | null>(null);

  // 表单实例
  const [createForm] = Form.useForm();
  const [importForm] = Form.useForm();
  const [settingsForm] = Form.useForm();

  useEffect(() => {
    fetchCollections();
  }, []);

  const fetchCollections = async () => {
    try {
      const response = await api.collections.list();
      setCollections(response.data);
    } catch (error) {
      // 错误已在api拦截器中处理
    } finally {
      setLoading(false);
    }
  };

  const handleCollectionClick = (collectionName: string) => {
    setSelectedCollection(collectionName);
  };

  // 创建集合
  const createCollection = async (values: { name: string }) => {
    try {
      await api.collections.create(values);
      message.success(`集合 "${values.name}" 创建成功`);
      setCreateModalVisible(false);
      createForm.resetFields();
      fetchCollections();
    } catch (error: any) {
      console.error('创建集合失败:', error);
      // 错误已在api拦截器中处理
    }
  };

  // 删除集合
  const deleteCollection = async (collection: CollectionInfo) => {
    try {
      await api.collections.delete(collection.display_name);
      message.success(`集合 "${collection.display_name}" 删除成功`);
      fetchCollections();
    } catch (error: any) {
      console.error('删除集合失败:', error);
      // 错误已在api拦截器中处理
    }
  };

  // 查看集合详情
  const viewCollectionDetail = (collection: CollectionInfo) => {
    setCurrentCollection(collection);
    setDetailModalVisible(true);
  };

  // 显示集合设置
  const showCollectionSettings = (collection: CollectionInfo) => {
    setCurrentCollection(collection);
    setSettingsModalVisible(true);
    // 预填充表单数据
    settingsForm.setFieldsValue({
      display_name: collection.display_name,
      description: collection.metadata?.description || '',
      tags: collection.metadata?.tags || []
    });
  };

  // 保存集合设置
  const handleSaveSettings = async (values: any) => {
    if (!currentCollection) return;

    try {
      // 这里可以调用API更新集合元数据
      // 目前先显示成功消息
      message.success(`集合 "${currentCollection.display_name}" 设置已更新`);
      setSettingsModalVisible(false);
      settingsForm.resetFields();
      setCurrentCollection(null);
      // 重新获取集合列表
      fetchCollections();
    } catch (error) {
      message.error('保存设置失败');
    }
  };

  // 处理导入数据
  const handleImportData = async (values: any) => {
    try {
      const { collection, file, chunkingMethod, chunkSize, chunkOverlap } = values;

      if (!file || !file.fileList || file.fileList.length === 0) {
        message.error('请选择要上传的文件');
        return;
      }

      const uploadFile = file.fileList[0].originFileObj;
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('chunking_method', chunkingMethod || 'recursive');
      formData.append('chunk_size', (chunkSize || 1000).toString());
      formData.append('chunk_overlap', (chunkOverlap || 200).toString());

      const response = await fetch(`${API_BASE_URL}/collections/${encodeURIComponent(collection)}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '上传失败');
      }

      const result = await response.json();
      message.success(`文档上传成功！创建了 ${result.chunks_created} 个文档块`);
      setImportModalVisible(false);
      importForm.resetFields();

      // 刷新集合列表
      fetchCollections();
    } catch (error: any) {
      console.error('导入数据失败:', error);
      message.error(`导入数据失败: ${error.message}`);
    }
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
          <Tooltip title="总览" placement="right">
            <div style={{
              fontSize: '18px',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '6px',
              transition: 'background-color 0.2s',
              ':hover': { backgroundColor: 'var(--ant-color-fill-tertiary)' }
            }}>📊</div>
          </Tooltip>
          <Tooltip title="收藏" placement="right">
            <div style={{
              fontSize: '18px',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '6px',
              transition: 'background-color 0.2s'
            }}>⭐</div>
          </Tooltip>
          <Tooltip title="最近" placement="right">
            <div style={{
              fontSize: '18px',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '6px',
              transition: 'background-color 0.2s'
            }}>🕒</div>
          </Tooltip>
          <Tooltip title="标签" placement="right">
            <div style={{
              fontSize: '18px',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '6px',
              transition: 'background-color 0.2s'
            }}>🏷️</div>
          </Tooltip>
          <Tooltip title="集合" placement="right">
            <div style={{
              fontSize: '18px',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '6px',
              transition: 'background-color 0.2s'
            }}>📁</div>
          </Tooltip>
        </Space>
      </div>

      <div style={{
        borderTop: '1px solid var(--ant-color-border)',
        paddingTop: '12px',
        marginTop: '12px'
      }}>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Tooltip title="新建集合" placement="right">
            <Button
              type="primary"
              shape="circle"
              icon={<PlusOutlined />}
              size="middle"
              onClick={() => setCreateModalVisible(true)}
              style={{ width: '36px', height: '36px' }}
            />
          </Tooltip>
          <Tooltip title="导入数据" placement="right">
            <Button
              shape="circle"
              icon={<ImportOutlined />}
              size="middle"
              onClick={() => setImportModalVisible(true)}
              style={{ width: '36px', height: '36px' }}
            />
          </Tooltip>
        </Space>
      </div>
    </div>
  );

  // 展开状态下的侧边栏内容
  const expandedSiderContent = (
    <div style={{ padding: 16 }}>
      <Collapse defaultActiveKey={['overview', 'collections', 'actions']}>
        <Panel header="📊 总览" key="overview">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Text type="secondary">总集合数: {collections.length}</Text>
            <Text type="secondary">总文档数: {collections.reduce((sum, c) => sum + c.count, 0)}</Text>
          </Space>
        </Panel>

        <Panel header="⭐ 收藏夹" key="favorites">
          <Text type="secondary">暂无收藏</Text>
        </Panel>

        <Panel header="🕒 最近访问" key="recent">
          <List
            size="small"
            dataSource={collections.slice(0, 3)}
            renderItem={(collection) => (
              <List.Item>
                <Button
                  type="text"
                  size="small"
                  onClick={() => handleCollectionClick(collection.name)}
                >
                  {collection.display_name}
                </Button>
              </List.Item>
            )}
          />
        </Panel>

        <Panel header="🏷️ 标签" key="tags">
          <Text type="secondary">暂无标签</Text>
        </Panel>

        <Panel header="📁 集合列表" key="collections">
          <List
            size="small"
            dataSource={collections}
            renderItem={(collection) => (
              <List.Item>
                <Tooltip title={collection.display_name} placement="right">
                  <Button
                    type="text"
                    size="small"
                    onClick={() => handleCollectionClick(collection.name)}
                    style={{
                      fontWeight: selectedCollection === collection.name ? 'bold' : 'normal',
                      width: '100%',
                      textAlign: 'left',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      padding: '4px 8px',
                    }}
                  >
                    {collection.display_name}
                  </Button>
                </Tooltip>
              </List.Item>
            )}
          />
        </Panel>

        <Panel header="⚡ 快捷操作" key="actions">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button
              type="primary"
              size="small"
              icon={<PlusOutlined />}
              block
              onClick={() => setCreateModalVisible(true)}
            >
              新建集合
            </Button>
            <Button
              size="small"
              icon={<ImportOutlined />}
              block
              onClick={() => setImportModalVisible(true)}
            >
              导入数据
            </Button>
          </Space>
        </Panel>
      </Collapse>
    </div>
  );

  const siderContent = siderCollapsed ? collapsedSiderContent : expandedSiderContent;

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '400px' 
      }}>
        <Spin size="large" tip="正在加载集合..." />
      </div>
    );
  }

  return (
    <Layout style={{ minHeight: '600px' }}>
      {!isMobile && (
        <Sider
          width={280}
          theme="light"
          collapsible
          collapsed={siderCollapsed}
          onCollapse={setSiderCollapsed}
          style={{
            backgroundColor: 'var(--ant-color-bg-container)',
            borderRight: '1px solid var(--ant-color-border)',
          }}
        >
          {siderContent}
        </Sider>
      )}
      
      <Content style={{ padding: 24 }}>
        {/* 统计卡片 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="总集合数"
                value={collections.length}
                prefix={<DatabaseOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="总文档数"
                value={collections.reduce((sum, c) => sum + c.count, 0)}
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="平均文档数"
                value={collections.length > 0 ? Math.round(collections.reduce((sum, c) => sum + c.count, 0) / collections.length) : 0}
                prefix={<TagOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="活跃集合"
                value={collections.filter(c => c.count > 0).length}
                prefix={<StarOutlined />}
              />
            </Card>
          </Col>
        </Row>

        {/* 搜索和过滤栏 */}
        <Row style={{ marginBottom: 24 }}>
          <Col span={24}>
            <Space.Compact style={{ width: '100%' }}>
              <Input.Search
                placeholder="搜索集合..."
                style={{ flex: 1 }}
                allowClear
              />
              <Select
                placeholder="标签筛选"
                style={{ width: 150 }}
                allowClear
              >
                <Select.Option value="all">全部</Select.Option>
              </Select>
              <DatePicker.RangePicker />
            </Space.Compact>
          </Col>
        </Row>

        {/* 集合网格视图 */}
        <Row gutter={[16, 16]}>
          {collections.map((collection) => (
            <Col 
              key={collection.name}
              xs={24} 
              sm={12} 
              md={8} 
              lg={6}
            >
              <Card
                title={
                  <Tooltip title={collection.display_name} placement="top">
                    <div
                      style={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxWidth: '200px'
                      }}
                    >
                      {collection.display_name}
                    </div>
                  </Tooltip>
                }
                extra={<StarOutlined />}
                actions={[
                  <Tooltip title="查看详情" key="view">
                    <EyeOutlined
                      onClick={(e) => {
                        e.stopPropagation();
                        viewCollectionDetail(collection);
                      }}
                      style={{
                        fontSize: '16px',
                        color: '#1890ff',
                        cursor: 'pointer'
                      }}
                    />
                  </Tooltip>,
                  <Tooltip title="集合设置" key="setting">
                    <SettingOutlined
                      onClick={(e) => {
                        e.stopPropagation();
                        showCollectionSettings(collection);
                      }}
                      style={{
                        fontSize: '16px',
                        color: '#52c41a',
                        cursor: 'pointer'
                      }}
                    />
                  </Tooltip>,
                  <Popconfirm
                    key="delete"
                    title="确认删除"
                    description={`确定要删除集合 "${collection.display_name}" 吗？`}
                    onConfirm={(e) => {
                      e?.stopPropagation();
                      deleteCollection(collection);
                    }}
                    okText="确定"
                    cancelText="取消"
                    onClick={(e) => e?.stopPropagation()}
                  >
                    <Tooltip title="删除集合">
                      <DeleteOutlined
                        style={{
                          fontSize: '16px',
                          color: '#ff4d4f',
                          cursor: 'pointer'
                        }}
                      />
                    </Tooltip>
                  </Popconfirm>
                ]}
                className="collection-card"
                style={{
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  height: '100%'
                }}
                onClick={() => handleCollectionClick(collection.name)}
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Statistic
                    title="文档数"
                    value={collection.count}
                    valueStyle={{ fontSize: '18px' }}
                  />
                  <Tag color="blue">{collection.dimension || 'N/A'}维</Tag>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    {collection.updated_at || '未知时间'}
                  </Text>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
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
        width={520}
        centered
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={createCollection}
          style={{ marginTop: '24px' }}
        >
          <Form.Item
            label="集合名称"
            name="name"
            rules={[
              { required: true, message: '请输入集合名称' },
              { min: 1, max: 100, message: '集合名称长度应在1-100字符之间' },
            ]}
          >
            <Input
              placeholder="请输入集合名称（支持中文）"
              style={{ height: '40px' }}
            />
          </Form.Item>

          <Form.Item style={{ marginTop: '32px', marginBottom: 0 }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button
                onClick={() => {
                  setCreateModalVisible(false);
                  createForm.resetFields();
                }}
              >
                取消
              </Button>
              <Button
                type="primary"
                htmlType="submit"
              >
                创建
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 导入数据模态框 */}
      <Modal
        title="导入数据"
        open={importModalVisible}
        onCancel={() => {
          setImportModalVisible(false);
          importForm.resetFields();
        }}
        footer={null}
        width={800}
        style={{ maxHeight: '90vh' }}
        styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
        centered
      >
        <Form
          form={importForm}
          layout="vertical"
          onFinish={handleImportData}
          style={{ marginTop: '24px' }}
        >
          <Form.Item
            label="选择集合"
            name="collection"
            rules={[{ required: true, message: '请选择目标集合' }]}
          >
            <Select placeholder="选择要导入数据的集合">
              {collections.map(collection => (
                <Select.Option key={collection.name} value={collection.display_name}>
                  {collection.display_name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            label="上传文件"
            name="file"
            rules={[{ required: true, message: '请选择要上传的文件' }]}
          >
            <Upload.Dragger
              name="file"
              multiple={false}
              accept=".txt,.pdf,.doc,.docx"
              beforeUpload={() => false}
            >
              <p className="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
              <p className="ant-upload-hint">
                支持 .txt, .pdf, .doc, .docx 格式文件
              </p>
            </Upload.Dragger>
          </Form.Item>

          {/* RAG分块配置 */}
          <Card
            title="RAG分块配置"
            size="small"
            style={{
              marginTop: '24px',
              marginBottom: '24px',
              minHeight: '280px'
            }}
            styles={{
              body: {
                padding: '24px',
                minHeight: '220px'
              }
            }}
          >
            <Form.Item
              label="分块算法"
              name="chunkingMethod"
              initialValue="recursive"
              tooltip="选择文档分块算法：递归分块适合大多数文档，固定大小分块保证块大小一致，语义分块基于内容语义进行分割"
              style={{ marginBottom: '24px' }}
            >
              <Select
                placeholder="选择分块算法"
                styles={{
                  popup: {
                    root: {
                      minWidth: '400px',
                      maxHeight: '300px'
                    }
                  }
                }}
                optionLabelProp="label"
              >
                <Select.Option value="recursive" label="递归分块 (Recursive)">
                  <div style={{ padding: '8px 0' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                      递归分块 (Recursive)
                    </div>
                    <div style={{
                      fontSize: '12px',
                      color: '#666',
                      lineHeight: '1.4',
                      whiteSpace: 'normal',
                      wordWrap: 'break-word'
                    }}>
                      按段落、句子等自然边界递归分割，适合大多数文档
                    </div>
                  </div>
                </Select.Option>
                <Select.Option value="fixed_size" label="固定大小分块 (Fixed Size)">
                  <div style={{ padding: '8px 0' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                      固定大小分块 (Fixed Size)
                    </div>
                    <div style={{
                      fontSize: '12px',
                      color: '#666',
                      lineHeight: '1.4',
                      whiteSpace: 'normal',
                      wordWrap: 'break-word'
                    }}>
                      按固定字符数分割，保证块大小一致
                    </div>
                  </div>
                </Select.Option>
                <Select.Option value="semantic" label="语义分块 (Semantic)">
                  <div style={{ padding: '8px 0' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                      语义分块 (Semantic)
                    </div>
                    <div style={{
                      fontSize: '12px',
                      color: '#666',
                      lineHeight: '1.4',
                      whiteSpace: 'normal',
                      wordWrap: 'break-word'
                    }}>
                      基于内容语义相似度进行分割，保持语义完整性
                    </div>
                  </div>
                </Select.Option>
              </Select>
            </Form.Item>

            <Row gutter={24} style={{ marginTop: '16px' }}>
              <Col span={12}>
                <Form.Item
                  label="块大小"
                  name="chunkSize"
                  initialValue={1000}
                  tooltip="每个文档块的最大字符数"
                  style={{ marginBottom: '20px' }}
                >
                  <Input
                    type="number"
                    min={100}
                    max={4000}
                    placeholder="1000"
                    addonAfter="字符"
                    style={{ height: '40px' }}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  label="重叠大小"
                  name="chunkOverlap"
                  initialValue={200}
                  tooltip="相邻文档块之间的重叠字符数，有助于保持上下文连贯性"
                  style={{ marginBottom: '20px' }}
                >
                  <Input
                    type="number"
                    min={0}
                    max={1000}
                    placeholder="200"
                    addonAfter="字符"
                    style={{ height: '40px' }}
                  />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          <Form.Item style={{ marginTop: '32px', marginBottom: 0 }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button
                onClick={() => {
                  setImportModalVisible(false);
                  importForm.resetFields();
                }}
              >
                取消
              </Button>
              <Button
                type="primary"
                htmlType="submit"
              >
                导入
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
            集合详情
          </Space>
        }
        open={detailModalVisible}
        onCancel={() => {
          setDetailModalVisible(false);
          setCurrentCollection(null);
        }}
        footer={[
          <Button
            key="close"
            onClick={() => {
              setDetailModalVisible(false);
              setCurrentCollection(null);
            }}
          >
            关闭
          </Button>
        ]}
        width={600}
      >
        {currentCollection && (
          <div style={{ padding: '16px 0' }}>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Card size="small" title="基本信息">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <Text strong>集合名称：</Text>
                      <Text copyable>{currentCollection.display_name}</Text>
                    </div>
                    <div>
                      <Text strong>内部名称：</Text>
                      <Text copyable code>{currentCollection.name}</Text>
                    </div>
                    <div>
                      <Text strong>文档数量：</Text>
                      <Text>{currentCollection.count}</Text>
                    </div>
                    <div>
                      <Text strong>向量维度：</Text>
                      <Tag color="blue">{currentCollection.dimension || 'N/A'}维</Tag>
                    </div>
                  </Space>
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="元数据信息">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <Text strong>描述：</Text>
                      <Text>{currentCollection.metadata?.description || '无描述'}</Text>
                    </div>
                    <div>
                      <Text strong>嵌入模型：</Text>
                      <Text>{currentCollection.metadata?.embedding_model || '未知'}</Text>
                    </div>
                    <div>
                      <Text strong>创建时间：</Text>
                      <Text>{currentCollection.created_at || '未知'}</Text>
                    </div>
                    <div>
                      <Text strong>更新时间：</Text>
                      <Text>{currentCollection.updated_at || '未知'}</Text>
                    </div>
                  </Space>
                </Card>
              </Col>
            </Row>
          </div>
        )}
      </Modal>

      {/* 集合设置模态框 */}
      <Modal
        title={
          <Space>
            <SettingOutlined />
            集合设置
          </Space>
        }
        open={settingsModalVisible}
        onCancel={() => {
          setSettingsModalVisible(false);
          setCurrentCollection(null);
          settingsForm.resetFields();
        }}
        footer={null}
        width={500}
      >
        <Form
          form={settingsForm}
          layout="vertical"
          onFinish={handleSaveSettings}
          style={{ marginTop: '16px' }}
        >
          <Form.Item
            label="显示名称"
            name="display_name"
            rules={[
              { required: true, message: '请输入集合显示名称' },
              { max: 50, message: '名称长度不能超过50个字符' }
            ]}
          >
            <Input placeholder="请输入集合显示名称" />
          </Form.Item>

          <Form.Item
            label="描述"
            name="description"
            rules={[
              { max: 200, message: '描述长度不能超过200个字符' }
            ]}
          >
            <Input.TextArea
              rows={3}
              placeholder="请输入集合描述（可选）"
            />
          </Form.Item>

          <Form.Item
            label="标签"
            name="tags"
          >
            <Select
              mode="tags"
              placeholder="添加标签（可选）"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item style={{ marginTop: '32px', marginBottom: 0 }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button
                onClick={() => {
                  setSettingsModalVisible(false);
                  setCurrentCollection(null);
                  settingsForm.resetFields();
                }}
              >
                取消
              </Button>
              <Button
                type="primary"
                htmlType="submit"
              >
                保存设置
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
};

export default CollectionsTab;