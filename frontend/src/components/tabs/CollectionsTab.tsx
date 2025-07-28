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
  Tooltip,
  Table,
  Pagination
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
  UploadOutlined,
  AppstoreOutlined,
  UnorderedListOutlined
} from '@ant-design/icons';
import { useResponsive } from '../../hooks/useResponsive';
import { api, API_BASE_URL } from '../../config/api';
import { generateAcceptString } from '../../utils/fileUtils';
import CollectionDetail from '../CollectionDetail';

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
  embedding_model?: string;
  embedding_provider?: string;
}

const CollectionsTab: React.FC = () => {
  const [collections, setCollections] = useState<CollectionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null);
  const [siderCollapsed, setSiderCollapsed] = useState(false);
  const { isMobile } = useResponsive();

  // 模态框状态
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [settingsModalVisible, setSettingsModalVisible] = useState(false);
  const [currentCollection, setCurrentCollection] = useState<CollectionInfo | null>(null);

  // 星标状态管理
  const [favoriteCollections, setFavoriteCollections] = useState<Set<string>>(new Set());

  // 视图模式状态管理
  const [viewMode, setViewMode] = useState<'card' | 'list'>('list');

  // 分页状态管理
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(12); // 卡片视图默认12个，列表视图默认10个

  // 表单实例
  const [createForm] = Form.useForm();
  const [importForm] = Form.useForm();
  const [settingsForm] = Form.useForm();

  // 嵌入模型相关状态
  const [embeddingProviders, setEmbeddingProviders] = useState<any>({});
  const [embeddingConfig, setEmbeddingConfig] = useState<any>({});
  const [modelsLoading, setModelsLoading] = useState(false);

  useEffect(() => {
    fetchCollections();
    // 从localStorage加载收藏的集合
    loadFavoriteCollections();
    // 加载嵌入模型数据
    loadEmbeddingModels();
    loadEmbeddingConfig();
  }, []);

  // 视图模式切换时调整分页大小
  useEffect(() => {
    if (viewMode === 'card') {
      setPageSize(12);
    } else {
      setPageSize(10);
    }
    setCurrentPage(1); // 重置到第一页
  }, [viewMode]);

  // 计算分页数据
  const getPaginatedCollections = () => {
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return collections.slice(startIndex, endIndex);
  };

  // 分页变化处理
  const handlePageChange = (page: number, size?: number) => {
    setCurrentPage(page);
    if (size && size !== pageSize) {
      setPageSize(size);
    }
  };

  // 加载收藏的集合
  const loadFavoriteCollections = () => {
    try {
      const saved = localStorage.getItem('chromadb_favorite_collections');
      if (saved) {
        setFavoriteCollections(new Set(JSON.parse(saved)));
      }
    } catch (error) {
      console.error('加载收藏集合失败:', error);
    }
  };

  // 保存收藏的集合到localStorage
  const saveFavoriteCollections = (favorites: Set<string>) => {
    try {
      localStorage.setItem('chromadb_favorite_collections', JSON.stringify(Array.from(favorites)));
    } catch (error) {
      console.error('保存收藏集合失败:', error);
    }
  };

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

  // 加载嵌入模型列表
  const loadEmbeddingModels = async () => {
    setModelsLoading(true);
    try {
      // 只获取已验证的模型列表
      const response = await fetch('/api/embedding-models');
      const data = await response.json();
      setEmbeddingProviders(data);
    } catch (error) {
      console.error('加载模型列表失败:', error);
      message.error('加载模型列表失败');
    } finally {
      setModelsLoading(false);
    }
  };

  // 加载嵌入模型配置
  const loadEmbeddingConfig = async () => {
    try {
      const response = await fetch('/api/embedding-config');
      const data = await response.json();
      setEmbeddingConfig(data.full_config || {});
    } catch (error) {
      console.error('加载模型配置失败:', error);
      message.error('加载模型配置失败');
    }
  };

  const handleCollectionClick = (collectionName: string) => {
    setSelectedCollection(collectionName);
  };

  // 切换星标状态
  const toggleFavorite = (collection: CollectionInfo, event?: React.MouseEvent) => {
    if (event) {
      event.stopPropagation(); // 阻止事件冒泡
    }

    const newFavorites = new Set(favoriteCollections);
    const collectionKey = collection.name; // 使用内部名称作为key

    if (newFavorites.has(collectionKey)) {
      newFavorites.delete(collectionKey);
      message.success(`已取消收藏 "${collection.display_name}"`);
    } else {
      newFavorites.add(collectionKey);
      message.success(`已收藏 "${collection.display_name}"`);
    }

    setFavoriteCollections(newFavorites);
    saveFavoriteCollections(newFavorites);
  };

  // 创建集合
  const createCollection = async (values: any) => {
    try {
      // 构建创建集合的参数
      const createParams: any = {
        name: values.name,
        metadata: values.metadata || {}
      };

      // 如果用户选择了特定的嵌入模型，添加相关参数
      if (values.embedding_model && values.embedding_model !== 'default') {
        createParams.embedding_model = values.embedding_model;

        if (values.embedding_model === 'ollama' && values.ollama_model) {
          createParams.ollama_model = values.ollama_model;
          createParams.ollama_base_url = values.ollama_base_url || 'http://localhost:11434';
        }
      }

      await api.collections.create(createParams);
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
      const { display_name, description, tags } = values;

      // 检查是否需要重命名
      if (display_name !== currentCollection.display_name) {
        // 调用重命名API
        await api.collections.rename({
          old_name: currentCollection.display_name,
          new_name: display_name
        });
        message.success(`集合已从 "${currentCollection.display_name}" 重命名为 "${display_name}"`);
      } else {
        // 如果只是更新其他元数据，这里可以扩展API支持
        message.success(`集合 "${currentCollection.display_name}" 设置已更新`);
      }

      setSettingsModalVisible(false);
      settingsForm.resetFields();
      setCurrentCollection(null);
      // 重新获取集合列表
      fetchCollections();
    } catch (error: any) {
      console.error('保存设置失败:', error);
      // 错误已在api拦截器中处理，这里不需要重复显示
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

      // 构建分块配置JSON
      const chunkingConfig = {
        method: chunkingMethod || 'recursive',
        chunk_size: chunkSize || 1000,
        chunk_overlap: chunkOverlap || 200
      };
      formData.append('chunking_config', JSON.stringify(chunkingConfig));

      // 使用改进的API调用，支持更长的超时时间
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000); // 5分钟超时

      try {
        const response = await fetch(`${API_BASE_URL}/collections/${encodeURIComponent(collection)}/upload`, {
          method: 'POST',
          body: formData,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

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
      } catch (fetchError: any) {
        clearTimeout(timeoutId);
        throw fetchError;
      }
    } catch (error: any) {
      console.error('导入数据失败:', error);

      // 改进的错误处理
      if (error.name === 'AbortError') {
        message.warning({
          content: '文件处理时间较长，请耐心等待。您可以稍后刷新页面查看处理结果。',
          duration: 8
        });
      } else {
        message.error(`导入数据失败: ${error.message}`);
      }
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
          <Tooltip title="收藏夹" placement="right">
            <div style={{
              fontSize: '18px',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '6px',
              transition: 'background-color 0.2s'
            }}>⭐</div>
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
      <Collapse defaultActiveKey={['favorites', 'actions']}>
        <Panel header="⭐ 收藏夹" key="favorites">
          {favoriteCollections.size === 0 ? (
            <Text type="secondary">暂无收藏</Text>
          ) : (
            <List
              size="small"
              dataSource={collections.filter(c => favoriteCollections.has(c.name))}
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
                        color: '#faad14'
                      }}
                      icon={<StarOutlined style={{ color: '#faad14', fontSize: '12px' }} />}
                    >
                      {collection.display_name}
                    </Button>
                  </Tooltip>
                </List.Item>
              )}
            />
          )}
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
    <Layout style={{ height: 'calc(100vh - 64px)', minHeight: '500px' }}>
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
            height: '100%',
            overflow: 'auto',
          }}
        >
          {siderContent}
        </Sider>
      )}

      <Content style={{ padding: selectedCollection ? '0' : 24, height: '100%', overflow: 'auto' }}>
        {selectedCollection ? (
          // 显示集合详情页面
          <CollectionDetail
            collectionName={selectedCollection}
            onBack={() => setSelectedCollection(null)}
            siderCollapsed={siderCollapsed}
            isMobile={isMobile}
          />
        ) : (
          <div style={{ position: 'relative', height: '100%' }}>
            {/* 主要内容区域 */}

        {/* 搜索和过滤栏 */}
        <Row style={{ marginBottom: 24 }} justify="space-between" align="middle">
          <Col flex="auto">
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
          <Col>
            <Button.Group>
              <Button
                type={viewMode === 'list' ? 'primary' : 'default'}
                icon={<UnorderedListOutlined />}
                onClick={() => setViewMode('list')}
              >
                列表视图
              </Button>
              <Button
                type={viewMode === 'card' ? 'primary' : 'default'}
                icon={<AppstoreOutlined />}
                onClick={() => setViewMode('card')}
              >
                卡片视图
              </Button>
            </Button.Group>
          </Col>
        </Row>

        {/* 集合视图 */}
        <div style={{ minHeight: 'calc(100vh - 300px)', marginBottom: '80px' }}>
          {viewMode === 'card' ? (
            // 卡片视图
            <Row gutter={[16, 16]}>
              {getPaginatedCollections().map((collection) => (
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
                  extra={
                    <Tooltip title={favoriteCollections.has(collection.name) ? "取消收藏" : "收藏集合"}>
                      <StarOutlined
                        style={{
                          color: favoriteCollections.has(collection.name) ? '#faad14' : '#d9d9d9',
                          cursor: 'pointer',
                          fontSize: '16px'
                        }}
                        onClick={(e) => toggleFavorite(collection, e)}
                      />
                    </Tooltip>
                  }
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
                    <div>
                      <Tag color="blue">{collection.dimension || collection.metadata?.vector_dimension || 'N/A'}维</Tag>
                      {collection.embedding_provider && collection.embedding_model && (
                        <Tag
                          color={collection.embedding_provider === 'alibaba' ? 'blue' : 'green'}
                          style={{ marginLeft: 4 }}
                        >
                          {collection.embedding_provider === 'alibaba' ? '阿里云' : 'Ollama'}
                        </Tag>
                      )}
                    </div>
                    {collection.embedding_model && (
                      <Text type="secondary" style={{ fontSize: '11px' }}>
                        模型: {collection.embedding_model}
                      </Text>
                    )}
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {collection.created_at || '未知时间'}
                    </Text>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
          ) : (
            // 列表视图
            <Table
              dataSource={getPaginatedCollections()}
              rowKey="name"
              pagination={false}
            columns={[
              {
                title: '集合名称',
                dataIndex: 'display_name',
                key: 'display_name',
                render: (text, record) => (
                  <Space>
                    <Tooltip title={favoriteCollections.has(record.name) ? "取消收藏" : "收藏集合"}>
                      <StarOutlined
                        style={{
                          color: favoriteCollections.has(record.name) ? '#faad14' : '#d9d9d9',
                          cursor: 'pointer',
                          fontSize: '14px'
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleFavorite(record, e);
                        }}
                      />
                    </Tooltip>
                    <Text strong style={{ cursor: 'pointer' }} onClick={() => handleCollectionClick(record.name)}>
                      {text}
                    </Text>
                  </Space>
                )
              },
              {
                title: '文档数量',
                dataIndex: 'count',
                key: 'count',
                width: 120,
                align: 'center',
                render: (count) => (
                  <Tag color={count > 0 ? 'blue' : 'default'}>
                    {count} 个
                  </Tag>
                )
              },
              {
                title: '向量维度',
                dataIndex: 'dimension',
                key: 'dimension',
                width: 120,
                align: 'center',
                render: (dimension, record) => (
                  <Tag color="purple">
                    {dimension || record.metadata?.vector_dimension || 'N/A'}维
                  </Tag>
                )
              },
              {
                title: '嵌入模型',
                key: 'embedding_model',
                width: 180,
                align: 'center',
                render: (_, record) => {
                  const provider = record.embedding_provider;
                  const model = record.embedding_model;

                  if (!provider || !model) {
                    return <Tag color="default">未知模型</Tag>;
                  }

                  const providerColor = provider === 'alibaba' ? 'blue' : 'green';
                  const providerName = provider === 'alibaba' ? '阿里云' : 'Ollama';

                  return (
                    <Space direction="vertical" size={2}>
                      <Tag color={providerColor} style={{ margin: 0 }}>
                        {providerName}
                      </Tag>
                      <Text style={{ fontSize: '12px', color: '#666' }}>
                        {model}
                      </Text>
                    </Space>
                  );
                }
              },
              {
                title: '创建时间',
                dataIndex: 'created_at',
                key: 'created_at',
                width: 150,
                render: (time) => (
                  <Text type="secondary">
                    {time || '未知时间'}
                  </Text>
                )
              },
              {
                title: '操作',
                key: 'actions',
                width: 150,
                align: 'center',
                render: (_, record) => (
                  <Space>
                    <Tooltip title="查看详情">
                      <Button
                        type="text"
                        icon={<EyeOutlined />}
                        onClick={(e) => {
                          e.stopPropagation();
                          viewCollectionDetail(record);
                        }}
                      />
                    </Tooltip>
                    <Tooltip title="集合设置">
                      <Button
                        type="text"
                        icon={<SettingOutlined />}
                        onClick={(e) => {
                          e.stopPropagation();
                          showCollectionSettings(record);
                        }}
                      />
                    </Tooltip>
                    <Popconfirm
                      title="确认删除"
                      description={`确定要删除集合 "${record.display_name}" 吗？`}
                      onConfirm={(e) => {
                        e?.stopPropagation();
                        deleteCollection(record);
                      }}
                      okText="确定"
                      cancelText="取消"
                    >
                      <Tooltip title="删除集合">
                        <Button
                          type="text"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </Tooltip>
                    </Popconfirm>
                  </Space>
                )
              }
            ]}
            onRow={(record) => ({
              onClick: () => handleCollectionClick(record.name),
              style: { cursor: 'pointer' }
            })}
          />
          )}
        </div>

        {/* 底部固定分页导航 */}
        <div style={{
          position: 'fixed',
          bottom: '24px',
          left: '50%',
          transform: 'translateX(-50%)',
          padding: '12px 24px',
          backgroundColor: 'var(--ant-color-bg-container)',
          border: '1px solid var(--ant-color-border)',
          borderRadius: '8px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
          zIndex: 200,
          backdropFilter: 'blur(8px)'
        }}>
          <Pagination
            current={currentPage}
            total={collections.length}
            pageSize={pageSize}
            showSizeChanger
            showQuickJumper
            showTotal={(total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`}
            onChange={handlePageChange}
            pageSizeOptions={viewMode === 'card' ? ['8', '12', '16', '24'] : ['5', '10', '20', '50']}
            size="small"
          />
        </div>

        {/* 页面右下角统计信息 */}
          <div style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            padding: '8px 16px',
            backgroundColor: 'var(--ant-color-bg-container)',
            border: '1px solid var(--ant-color-border)',
            borderRadius: '6px',
            fontSize: '12px',
            color: 'var(--ant-color-text-secondary)',
            opacity: 0.7,
            zIndex: 100,
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
            transition: 'opacity 0.3s ease'
          }}
          onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
          onMouseLeave={(e) => e.currentTarget.style.opacity = '0.7'}
          >
            总集合: {collections.length} |
            总文档: {collections.reduce((sum, c) => sum + c.count, 0).toLocaleString()} |
            平均: {collections.length > 0 ? Math.round(collections.reduce((sum, c) => sum + c.count, 0) / collections.length) : 0} |
            活跃: {collections.filter(c => c.count > 0).length}
          </div>
          </div>
        )}
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

          <Form.Item
            label="嵌入模型"
            name="embedding_model"
            initialValue="default"
            tooltip="选择用于生成文档向量的嵌入模型"
            help={
              Object.keys(embeddingProviders).length === 0 && !modelsLoading ? (
                <span style={{ color: '#ff4d4f' }}>
                  暂无可用的嵌入模型，请先在设置页面配置并验证模型
                </span>
              ) : null
            }
          >
            <Select
              placeholder="选择嵌入模型"
              style={{ height: '40px' }}
              loading={modelsLoading}
            >
              <Select.Option value="default">使用系统默认配置</Select.Option>
              {embeddingProviders.alibaba?.verified && (
                <Select.Option value="alibaba">
                  <Space>
                    阿里云百炼模型
                    <Tag color="green" size="small">已验证</Tag>
                  </Space>
                </Select.Option>
              )}
              {embeddingProviders.ollama?.verified && embeddingProviders.ollama?.available && (
                <Select.Option value="ollama">
                  <Space>
                    Ollama本地模型
                    <Tag color="green" size="small">已验证</Tag>
                  </Space>
                </Select.Option>
              )}
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) =>
              prevValues.embedding_model !== currentValues.embedding_model
            }
          >
            {({ getFieldValue }) => {
              const embeddingModel = getFieldValue('embedding_model');

              if (embeddingModel === 'ollama') {
                return (
                  <>
                    <Form.Item
                      label="Ollama模型"
                      name="ollama_model"
                      rules={[{ required: true, message: '请选择Ollama模型' }]}
                    >
                      <Select
                        placeholder="选择或输入模型名称"
                        style={{ height: '40px' }}
                        showSearch
                        mode="combobox"
                        optionFilterProp="children"
                      >
                        {embeddingProviders.ollama?.models?.map((model: any) => (
                          <Select.Option key={model.name} value={model.name}>
                            <Space>
                              {model.name}
                              {model.recommended && <Tag color="blue" size="small">推荐</Tag>}
                              {model.available && <Tag color="green" size="small">已安装</Tag>}
                            </Space>
                          </Select.Option>
                        ))}
                      </Select>
                    </Form.Item>

                    <Form.Item
                      label="Ollama服务器地址"
                      name="ollama_base_url"
                      initialValue="http://localhost:11434"
                    >
                      <Input
                        placeholder="http://localhost:11434"
                        style={{ height: '40px' }}
                      />
                    </Form.Item>
                  </>
                );
              }

              return null;
            }}
          </Form.Item>

          <Form.Item
            label="描述（可选）"
            name={['metadata', 'description']}
          >
            <Input.TextArea
              placeholder="为集合添加描述信息"
              rows={3}
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
              accept={generateAcceptString()}
              beforeUpload={() => false}
            >
              <p className="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
              <p className="ant-upload-hint">
                支持多种文档格式：文本、PDF、Word、PowerPoint、Markdown、RTF、Excel、CSV
                <br />
                文件大小不超过 150MB
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
                      <Tag color="blue">{currentCollection.dimension || currentCollection.metadata?.vector_dimension || 'N/A'}维</Tag>
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
                      {currentCollection.embedding_provider && currentCollection.embedding_model ? (
                        <Space>
                          <Tag color={currentCollection.embedding_provider === 'alibaba' ? 'blue' : 'green'}>
                            {currentCollection.embedding_provider === 'alibaba' ? '阿里云' : 'Ollama'}
                          </Tag>
                          <Text>{currentCollection.embedding_model}</Text>
                        </Space>
                      ) : (
                        <Text>{currentCollection.metadata?.embedding_model || '未知'}</Text>
                      )}
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