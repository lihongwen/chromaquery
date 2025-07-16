import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
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
  Upload,
  Modal,
  Form,
  Select,
  InputNumber,
  Divider,
  Progress,
  Alert,
  Row,
  Col,
} from 'antd';
import {
  ArrowLeftOutlined,
  DatabaseOutlined,
  InfoCircleOutlined,
  FileTextOutlined,
  CalendarOutlined,
  HomeOutlined,
  UploadOutlined,
  InboxOutlined,
  SettingOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
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

// RAG分块方式枚举
enum ChunkingMethod {
  RECURSIVE = 'recursive',
  FIXED_SIZE = 'fixed_size',
  SEMANTIC = 'semantic'
}

// RAG分块配置接口
interface ChunkingConfig {
  method: ChunkingMethod;
  chunk_size: number;
  chunk_overlap: number;
  separators?: string[];
  semantic_threshold?: number;
}

// 文档上传请求接口
interface DocumentUploadRequest {
  file: File;
  chunking_config: ChunkingConfig;
}

// 上传进度接口
interface UploadProgress {
  percent: number;
  status: 'uploading' | 'processing' | 'chunking' | 'embedding' | 'success' | 'error';
  message: string;
  chunks_created?: number;
  total_chunks?: number;
}

const CollectionDetail: React.FC = () => {
  const { collectionName } = useParams<{ collectionName: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [collectionDetail, setCollectionDetail] = useState<CollectionDetail | null>(null);
  const [loading, setLoading] = useState(true);

  // 文档上传相关状态
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [uploadForm] = Form.useForm();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [chunkingMethod, setChunkingMethod] = useState<ChunkingMethod>(ChunkingMethod.RECURSIVE);

  // 文档删除相关状态
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null);

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
    // 获取来源页面参数
    const fromPage = searchParams.get('from');

    // 根据来源页面决定返回路径
    switch (fromPage) {
      case 'collections':
        navigate('/collections');
        break;
      case 'query':
        navigate('/query');
        break;
      default:
        // 默认返回到集合管理页面
        navigate('/collections');
        break;
    }
  };

  // 处理文件选择
  const handleFileSelect = (file: File) => {
    // 检查文件类型
    if (!file.name.toLowerCase().endsWith('.txt')) {
      message.error('只支持上传 .txt 格式的文件');
      return false;
    }

    // 检查文件大小 (限制为10MB)
    if (file.size > 10 * 1024 * 1024) {
      message.error('文件大小不能超过 10MB');
      return false;
    }

    setSelectedFile(file);
    return false; // 阻止自动上传
  };

  // 打开上传模态框
  const openUploadModal = () => {
    setUploadModalVisible(true);
    setSelectedFile(null);
    setUploadProgress(null);
    uploadForm.resetFields();
    setChunkingMethod(ChunkingMethod.RECURSIVE);
  };

  // 关闭上传模态框
  const closeUploadModal = () => {
    setUploadModalVisible(false);
    setSelectedFile(null);
    setUploadProgress(null);
    uploadForm.resetFields();
  };

  // 获取分块方式的默认配置
  const getDefaultChunkingConfig = (method: ChunkingMethod): Partial<ChunkingConfig> => {
    switch (method) {
      case ChunkingMethod.RECURSIVE:
        return {
          chunk_size: 1000,
          chunk_overlap: 200,
          separators: ['\n\n', '\n', '。', '！', '？', ';', ':', '，']
        };
      case ChunkingMethod.FIXED_SIZE:
        return {
          chunk_size: 500,
          chunk_overlap: 50
        };
      case ChunkingMethod.SEMANTIC:
        return {
          chunk_size: 800,
          chunk_overlap: 100,
          semantic_threshold: 0.7
        };
      default:
        return {
          chunk_size: 1000,
          chunk_overlap: 200
        };
    }
  };

  // 处理分块方式变化
  const handleChunkingMethodChange = (method: ChunkingMethod) => {
    setChunkingMethod(method);
    const defaultConfig = getDefaultChunkingConfig(method);
    uploadForm.setFieldsValue(defaultConfig);
  };

  // 处理文档删除
  const handleDocumentDelete = async (fileName: string) => {
    console.log('handleDocumentDelete called with fileName:', fileName);
    console.log('collectionName:', collectionName);

    if (!collectionName || !fileName) {
      message.error('参数错误');
      return;
    }

    // 直接确认删除，跳过Modal.confirm（临时解决方案）
    const confirmed = window.confirm(`您确定要删除文档 "${fileName}" 吗？\n\n此操作将删除该文档的所有分块，删除后无法恢复！`);

    if (!confirmed) {
      return;
    }

    setDeleteLoading(fileName);
    try {
      console.log('Calling delete API...');
      await axios.delete(
        `${API_BASE_URL}/collections/${encodeURIComponent(collectionName)}/documents/${encodeURIComponent(fileName)}`
      );

      console.log('Delete API call successful');
      message.success(`文档 "${fileName}" 删除成功`);
      // 刷新集合详情
      fetchCollectionDetail();
    } catch (error: any) {
      console.error('删除文档失败:', error);
      const errorMessage = error.response?.data?.detail || '删除文档失败';
      message.error(errorMessage);
    } finally {
      setDeleteLoading(null);
    }
  };

  // 处理文档上传
  const handleDocumentUpload = async (values: any) => {
    if (!selectedFile || !collectionName) {
      message.error('请选择要上传的文件');
      return;
    }

    try {
      // 构建分块配置
      const chunkingConfig: ChunkingConfig = {
        method: chunkingMethod,
        chunk_size: values.chunk_size,
        chunk_overlap: values.chunk_overlap,
        ...(chunkingMethod === ChunkingMethod.RECURSIVE && {
          separators: values.separators || ['\n\n', '\n', '。', '！', '？', ';', ':', '，']
        }),
        ...(chunkingMethod === ChunkingMethod.SEMANTIC && {
          semantic_threshold: values.semantic_threshold || 0.7
        })
      };

      // 创建FormData
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('chunking_config', JSON.stringify(chunkingConfig));

      // 设置初始上传进度
      setUploadProgress({
        percent: 0,
        status: 'uploading',
        message: '正在上传文件...'
      });

      // 模拟上传进度（实际项目中应该使用真实的上传进度）
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (!prev) return null;

          let newPercent = prev.percent + 10;
          let newStatus = prev.status;
          let newMessage = prev.message;

          if (newPercent >= 30 && prev.status === 'uploading') {
            newStatus = 'processing';
            newMessage = '正在处理文件内容...';
          } else if (newPercent >= 50 && prev.status === 'processing') {
            newStatus = 'chunking';
            newMessage = '正在进行RAG分块...';
          } else if (newPercent >= 80 && prev.status === 'chunking') {
            newStatus = 'embedding';
            newMessage = '正在生成向量嵌入...';
          }

          if (newPercent >= 100) {
            clearInterval(progressInterval);
            newPercent = 100;
            newStatus = 'success';
            newMessage = '上传完成！';
          }

          return {
            ...prev,
            percent: newPercent,
            status: newStatus,
            message: newMessage
          };
        });
      }, 500);

      // 实际的API调用
      try {
        const response = await axios.post(
          `${API_BASE_URL}/collections/${encodeURIComponent(collectionName)}/upload`,
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data'
            }
          }
        );

        clearInterval(progressInterval);
        setUploadProgress({
          percent: 100,
          status: 'success',
          message: '文档上传并处理完成！',
          chunks_created: response.data.chunks_created,
          total_chunks: response.data.chunks_created
        });

        message.success(`文档上传成功！创建了 ${response.data.chunks_created} 个文档块`);

        // 3秒后关闭模态框并刷新数据
        setTimeout(() => {
          closeUploadModal();
          fetchCollectionDetail();
        }, 3000);

      } catch (apiError: any) {
        clearInterval(progressInterval);
        console.error('API调用失败:', apiError);

        setUploadProgress({
          percent: 0,
          status: 'error',
          message: apiError.response?.data?.detail || '文档上传失败'
        });
        message.error('文档上传失败');
      }

    } catch (error: any) {
      console.error('文档上传失败:', error);
      setUploadProgress({
        percent: 0,
        status: 'error',
        message: error.response?.data?.detail || '文档上传失败'
      });
      message.error('文档上传失败');
    }
  };

  // 按文件分组文档数据
  const getGroupedDocuments = () => {
    if (!collectionDetail) return [];

    const documents = collectionDetail.documents.length > 0
      ? collectionDetail.documents
      : collectionDetail.sample_documents;

    // 按文件名分组
    const fileGroups = new Map();

    documents.forEach((doc, index) => {
      const metadata = doc.metadata || {};
      const fileName = metadata.file_name || metadata.source_file || `文档 #${index + 1}`;

      if (!fileGroups.has(fileName)) {
        fileGroups.set(fileName, {
          fileName,
          documents: [],
          totalChunks: 0,
          firstDoc: doc,
          chunkMethod: metadata.chunk_method || '未知'
        });
      }

      const group = fileGroups.get(fileName);
      group.documents.push(doc);
      group.totalChunks = metadata.total_chunks || group.documents.length;
    });

    // 转换为数组并添加索引
    return Array.from(fileGroups.values()).map((group, index) => ({
      ...group,
      key: group.fileName,
      index: index + 1,
      // 使用第一个文档的内容作为预览
      document: group.firstDoc.document,
      metadata: group.firstDoc.metadata,
      // 添加向量信息用于显示
      embedding: group.firstDoc.embedding
    }));
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
              type="primary"
              icon={<UploadOutlined />}
              onClick={openUploadModal}
            >
              上传文档
            </Button>
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
                        dataSource={getGroupedDocuments()}
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
                            title: '文档名称',
                            dataIndex: 'fileName',
                            key: 'fileName',
                            width: 200,
                            responsive: ['md'],
                            render: (fileName) => (
                              <div style={{ fontSize: '12px' }}>
                                <Text strong style={{ color: '#1890ff' }}>
                                  {fileName}
                                </Text>
                              </div>
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
                            title: '块数',
                            dataIndex: 'totalChunks',
                            key: 'chunks',
                            width: 120,
                            responsive: ['lg'],
                            render: (totalChunks, record) => {
                              const chunkMethod = record.chunkMethod;

                              return (
                                <div style={{ fontSize: '12px' }}>
                                  <div>
                                    <Text strong style={{ color: '#52c41a' }}>
                                      总共拆分了{totalChunks}块
                                    </Text>
                                  </div>
                                  {chunkMethod && chunkMethod !== '未知' && (
                                    <div style={{ marginTop: 2 }}>
                                      <Tag color="orange" style={{ fontSize: '9px' }}>
                                        {chunkMethod === 'recursive' ? '递归分块' :
                                         chunkMethod === 'fixed_size' ? '固定分块' :
                                         chunkMethod === 'semantic' ? '语义分块' : chunkMethod}
                                      </Tag>
                                    </div>
                                  )}
                                  {record.metadata?.model && (
                                    <div style={{ marginTop: 2 }}>
                                      <Tag color="green" style={{ fontSize: '9px' }}>
                                        {record.metadata.model === 'alibaba-text-embedding-v4' ? '阿里云' : '默认'}
                                      </Tag>
                                    </div>
                                  )}
                                </div>
                              );
                            }
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
                            title: '块信息',
                            key: 'chunk_info',
                            width: 120,
                            responsive: ['xl'],
                            render: (_, record) => {
                              const chunkMethod = record.metadata?.chunk_method || '未知';
                              const chunkSize = record.metadata?.chunk_size;
                              const textLength = record.document ? record.document.length : 0;

                              return (
                                <div style={{ fontSize: '11px' }}>
                                  <div>
                                    <Text type="secondary">
                                      字符: {textLength}
                                    </Text>
                                  </div>
                                  {chunkMethod !== '未知' && (
                                    <div style={{ marginTop: 2 }}>
                                      <Tag color="orange" style={{ fontSize: '9px' }}>
                                        {chunkMethod === 'recursive' ? '递归' :
                                         chunkMethod === 'fixed_size' ? '固定' :
                                         chunkMethod === 'semantic' ? '语义' : chunkMethod}
                                      </Tag>
                                    </div>
                                  )}
                                  {chunkSize && (
                                    <div style={{ marginTop: 2, color: '#999' }}>
                                      块大小: {chunkSize}
                                    </div>
                                  )}
                                </div>
                              );
                            }
                          },
                          {
                            title: '操作',
                            key: 'actions',
                            width: 100,
                            align: 'center',
                            render: (_, record) => (
                              <Space size="small">
                                <Button
                                  type="text"
                                  size="small"
                                  icon={<DeleteOutlined />}
                                  danger
                                  loading={deleteLoading === record.fileName}
                                  onClick={() => handleDocumentDelete(record.fileName)}
                                  title="删除文档"
                                />
                              </Space>
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
                        <Tag color="purple">
                          {collectionDetail.metadata?.vector_dimension || '未知'} 维
                        </Tag>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          {collectionDetail.metadata?.embedding_model === 'alibaba-text-embedding-v4'
                            ? '(阿里云嵌入模型)'
                            : '(ChromaDB 默认配置)'}
                        </Text>
                      </Space>
                    </Descriptions.Item>
                    <Descriptions.Item label="向量模型">
                      <Space>
                        <Text>
                          {collectionDetail.metadata?.embedding_model === 'alibaba-text-embedding-v4'
                            ? 'text-embedding-v4'
                            : 'all-MiniLM-L6-v2'}
                        </Text>
                        <Tag color={collectionDetail.metadata?.embedding_model === 'alibaba-text-embedding-v4' ? 'green' : 'default'}>
                          {collectionDetail.metadata?.embedding_model === 'alibaba-text-embedding-v4'
                            ? '阿里云'
                            : '默认'}
                        </Tag>
                      </Space>
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

      {/* 文档上传模态框 */}
      <Modal
        title={
          <Space>
            <UploadOutlined />
            上传文档到集合：{collectionDetail?.display_name}
          </Space>
        }
        open={uploadModalVisible}
        onCancel={closeUploadModal}
        footer={null}
        width={800}
        centered
      >
        <Form
          form={uploadForm}
          layout="vertical"
          onFinish={handleDocumentUpload}
          initialValues={getDefaultChunkingConfig(ChunkingMethod.RECURSIVE)}
        >
          {/* 文件上传区域 */}
          <Form.Item
            label="选择文档文件"
            required
          >
            <Upload.Dragger
              name="file"
              multiple={false}
              beforeUpload={handleFileSelect}
              showUploadList={false}
              accept=".txt"
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">
                点击或拖拽文件到此区域上传
              </p>
              <p className="ant-upload-hint">
                支持 .txt 格式文件，文件大小不超过 10MB
              </p>
            </Upload.Dragger>

            {selectedFile && (
              <Alert
                message={`已选择文件: ${selectedFile.name}`}
                description={`文件大小: ${(selectedFile.size / 1024).toFixed(2)} KB`}
                type="success"
                showIcon
                style={{ marginTop: 12 }}
              />
            )}
          </Form.Item>

          <Divider orientation="left">
            <Space>
              <SettingOutlined />
              RAG分块配置
            </Space>
          </Divider>

          {/* RAG分块方式选择 */}
          <Form.Item
            label="分块方式"
            required
          >
            <Select
              value={chunkingMethod}
              onChange={handleChunkingMethodChange}
              style={{ width: '100%' }}
            >
              <Select.Option value={ChunkingMethod.RECURSIVE}>
                递归分块 (Recursive Text Splitting)
              </Select.Option>
              <Select.Option value={ChunkingMethod.FIXED_SIZE}>
                固定字数分块 (Fixed-size Chunking)
              </Select.Option>
              <Select.Option value={ChunkingMethod.SEMANTIC}>
                语义分块 (Semantic Chunking)
              </Select.Option>
            </Select>
          </Form.Item>

          {/* 分块参数配置 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="块大小 (字符数)"
                name="chunk_size"
                rules={[
                  { required: true, message: '请输入块大小' },
                  { type: 'number', min: 100, max: 4000, message: '块大小应在100-4000字符之间' }
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="输入块大小"
                  min={100}
                  max={4000}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="重叠长度 (字符数)"
                name="chunk_overlap"
                rules={[
                  { required: true, message: '请输入重叠长度' },
                  { type: 'number', min: 0, max: 1000, message: '重叠长度应在0-1000字符之间' }
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="输入重叠长度"
                  min={0}
                  max={1000}
                />
              </Form.Item>
            </Col>
          </Row>

          {/* 语义分块特有参数 */}
          {chunkingMethod === ChunkingMethod.SEMANTIC && (
            <Form.Item
              label="语义相似度阈值"
              name="semantic_threshold"
              rules={[
                { required: true, message: '请输入语义相似度阈值' },
                { type: 'number', min: 0.1, max: 1.0, message: '阈值应在0.1-1.0之间' }
              ]}
            >
              <InputNumber
                style={{ width: '100%' }}
                placeholder="输入语义相似度阈值"
                min={0.1}
                max={1.0}
                step={0.1}
              />
            </Form.Item>
          )}

          {/* 分块方式说明 */}
          <Alert
            message={
              chunkingMethod === ChunkingMethod.RECURSIVE
                ? "递归分块：按照指定的分隔符（如段落、句子）递归地分割文本，保持语义完整性"
                : chunkingMethod === ChunkingMethod.FIXED_SIZE
                ? "固定字数分块：按照固定的字符数量分割文本，简单高效"
                : "语义分块：基于语义相似度分割文本，保持语义连贯性，适合复杂文档"
            }
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          {/* 上传进度 */}
          {uploadProgress && (
            <div style={{ marginBottom: 16 }}>
              <Progress
                percent={uploadProgress.percent}
                status={uploadProgress.status === 'error' ? 'exception' : 'active'}
                strokeColor={
                  uploadProgress.status === 'success' ? '#52c41a' :
                  uploadProgress.status === 'error' ? '#ff4d4f' : '#1890ff'
                }
              />
              <div style={{ marginTop: 8 }}>
                <Text type={uploadProgress.status === 'error' ? 'danger' : 'secondary'}>
                  {uploadProgress.message}
                </Text>
                {uploadProgress.chunks_created && (
                  <div style={{ marginTop: 4 }}>
                    <Text type="success">
                      成功创建 {uploadProgress.chunks_created} 个文档块
                    </Text>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 操作按钮 */}
          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                disabled={!selectedFile || uploadProgress?.status === 'uploading'}
                loading={uploadProgress?.status === 'uploading'}
              >
                {uploadProgress?.status === 'uploading' ? '上传中...' : '开始上传'}
              </Button>
              <Button onClick={closeUploadModal}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
};

export default CollectionDetail;
