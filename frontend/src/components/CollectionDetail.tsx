import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Space,
  Typography,
  Tag,
  Descriptions,
  Tabs,
  Table,
  Empty,
  Spin,
  message,
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
  Popconfirm,
  Pagination,
} from 'antd';
import {
  ArrowLeftOutlined,
  DatabaseOutlined,
  InfoCircleOutlined,
  FileTextOutlined,
  CalendarOutlined,
  UploadOutlined,
  InboxOutlined,
  SettingOutlined,
  DeleteOutlined,
  FolderOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { api, API_BASE_URL } from '../config/api';
import {
  isSupportedFile,
  getFileFormatInfo,
  isTableFile,
  formatFileSize,
  validateFileSize,
  getUploadHint,
  generateAcceptString
} from '../utils/fileUtils';
import { showError, getDetailedErrorMessage } from '../utils/errorHandler';
import { estimateProcessingTime, getCurrentStage, formatRemainingTime, getProcessingHint } from '../utils/uploadProgress';

const { Title, Text, Paragraph } = Typography;

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
const ChunkingMethod = {
  RECURSIVE: 'recursive',
  FIXED_SIZE: 'fixed_size',
  SEMANTIC: 'semantic'
} as const;

type ChunkingMethod = typeof ChunkingMethod[keyof typeof ChunkingMethod];

// RAG分块配置接口
interface ChunkingConfig {
  method: ChunkingMethod;
  chunk_size: number;
  chunk_overlap: number;
  separators?: string[];
  semantic_threshold?: number;
}



// 上传进度接口
interface UploadProgress {
  percent: number;
  status: 'uploading' | 'processing' | 'chunking' | 'embedding' | 'success' | 'error';
  message: string;
  chunks_created?: number;
  total_chunks?: number;
}

interface CollectionDetailProps {
  collectionName: string;
  onBack: () => void;
  siderCollapsed?: boolean;
  isMobile?: boolean;
}

const CollectionDetail: React.FC<CollectionDetailProps> = ({
  collectionName,
  onBack,
  siderCollapsed = false,
  isMobile = false
}) => {
  const [collectionDetail, setCollectionDetail] = useState<CollectionDetail | null>(null);
  const [loading, setLoading] = useState(true);

  // 分页状态管理
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(8);

  // 辅助函数：获取向量维度
  const getVectorDimension = () => {
    if (!collectionDetail) return '未知';

    // 优先使用元数据中的向量维度
    const metadataDimension = collectionDetail.metadata?.vector_dimension;
    if (metadataDimension) return metadataDimension;

    // 如果元数据中没有，尝试从第一个文档的向量中获取
    if (collectionDetail.sample_documents && collectionDetail.sample_documents.length > 0) {
      const firstDoc = collectionDetail.sample_documents[0];
      if (firstDoc.embedding && firstDoc.embedding.length > 0) {
        return firstDoc.embedding.length;
      }
    }

    return '未知';
  };

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
      const response = await api.collections.detail(collectionName, 20);
      setCollectionDetail(response.data);
    } catch (error: any) {
      console.error('获取集合详细信息失败:', error);
      // 错误已在api拦截器中处理
      // 如果集合不存在，返回列表页面
      if (error.response?.status === 404) {
        onBack();
      }
    } finally {
      setLoading(false);
    }
  };

  // 返回集合列表
  const handleGoBack = () => {
    onBack();
  };

  // 处理文件选择
  const handleFileSelect = (file: File) => {
    // 检查文件格式
    if (!isSupportedFile(file.name)) {
      message.error('不支持的文件格式，请选择支持的文档格式');
      return false;
    }

    // 检查文件大小 (150MB限制)
    if (!validateFileSize(file, 150)) {
      message.error('文件大小不能超过 150MB');
      return false;
    }

    const formatInfo = getFileFormatInfo(file.name);
    const uploadHint = getUploadHint(file.name);

    setSelectedFile(file);

    // 显示文件信息和处理提示
    message.success(
      <div>
        <div>已选择文件: {file.name}</div>
        <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
          {formatInfo?.description} ({formatFileSize(file.size)})
        </div>
        <div style={{ fontSize: '12px', color: '#1890ff', marginTop: '2px' }}>
          {uploadHint}
        </div>
      </div>
    );

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

    setDeleteLoading(fileName);
    try {
      console.log('Calling delete API...');
      await api.documents.delete(collectionName, fileName);

      console.log('Delete API call successful');
      message.success(`文档 "${fileName}" 删除成功`);
      // 刷新集合详情
      fetchCollectionDetail();
    } catch (error: any) {
      console.error('删除文档失败:', error);
      // 错误已在api拦截器中处理
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
      // 创建FormData
      const formData = new FormData();
      formData.append('file', selectedFile);

      // 检查是否为表格文件
      const isTable = isTableFile(selectedFile.name);

      if (!isTable) {
        // 普通文件：构建分块配置
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
        formData.append('chunking_config', JSON.stringify(chunkingConfig));
      } else {
        // 表格文件：使用默认配置（后端会忽略）
        const defaultConfig: ChunkingConfig = {
          method: ChunkingMethod.RECURSIVE,
          chunk_size: 1000,
          chunk_overlap: 200
        };
        formData.append('chunking_config', JSON.stringify(defaultConfig));
      }

      // 设置初始上传进度
      setUploadProgress({
        percent: 0,
        status: 'uploading',
        message: '正在上传文件...'
      });

      // 智能进度显示：基于文件大小和类型估算处理时间
      const progressEstimate = estimateProcessingTime(selectedFile.size, selectedFile.name);
      const progressInterval = 1000; // 每秒更新一次
      const startTime = Date.now();

      // 显示处理提示
      const processingHint = getProcessingHint(selectedFile.name);

      const progressTimer = setInterval(() => {
        setUploadProgress(prev => {
          if (!prev) return null;

          const elapsedSeconds = (Date.now() - startTime) / 1000;
          let newPercent = Math.min(85, elapsedSeconds * progressEstimate.incrementPerSecond);

          // 获取当前阶段
          const currentStage = getCurrentStage(newPercent, progressEstimate.stages);
          const remainingTime = Math.max(0, progressEstimate.estimatedTimeSeconds - elapsedSeconds);

          let newMessage = currentStage?.message || '正在处理...';
          if (remainingTime > 5) {
            newMessage += ` (${formatRemainingTime(remainingTime)})`;
          }

          return {
            ...prev,
            percent: Math.round(newPercent),
            status: currentStage?.name || 'processing',
            message: newMessage
          };
        });
      }, progressInterval);

      // 实际的API调用
      try {
        const response = await api.documents.upload(collectionName, formData);

        clearInterval(progressTimer);
        setUploadProgress({
          percent: 100,
          status: 'success',
          message: `文档处理完成！创建了 ${response.data.chunks_created} 个文档块`,
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
        clearInterval(progressTimer);
        console.error('API调用失败:', apiError);

        // 改进的错误处理
        let errorMessage = '文档上传失败';
        let isTimeout = false;

        if (apiError.code === 'ECONNABORTED' || apiError.message?.includes('timeout')) {
          isTimeout = true;
          errorMessage = '处理超时，但文件可能仍在后台处理中，请稍后刷新查看结果';
        } else if (apiError.response?.data?.detail) {
          errorMessage = apiError.response.data.detail;
        }

        setUploadProgress({
          percent: 0,
          status: 'error',
          message: errorMessage
        });

        // 对于超时错误，提供不同的处理建议
        if (isTimeout) {
          message.warning({
            content: '文件处理时间较长，请耐心等待。您可以稍后刷新页面查看处理结果。',
            duration: 8
          });
        } else {
          // 使用增强的错误处理
          showError(apiError);
        }
      }

    } catch (error: any) {
      console.error('文档上传失败:', error);
      const errorDetail = error.response?.data?.detail || '文档上传失败';
      setUploadProgress({
        percent: 0,
        status: 'error',
        message: errorDetail
      });

      // 使用增强的错误处理
      showError(error);
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

  // 获取所有文档数据（不分组）
  const getAllDocuments = () => {
    if (!collectionDetail) return [];

    const documents = collectionDetail.documents.length > 0
      ? collectionDetail.documents
      : collectionDetail.sample_documents;

    return documents.map((doc, index) => ({
      ...doc,
      key: doc.id || `doc-${index}`,
      index: index + 1,
      metadata: doc.metadata || {}
    }));
  };

  // 获取分页后的文档数据（按文件分组）
  const getPaginatedDocuments = () => {
    const groupedDocuments = getGroupedDocuments();
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return groupedDocuments.slice(startIndex, endIndex);
  };

  // 分页变化处理
  const handlePageChange = (page: number, size?: number) => {
    setCurrentPage(page);
    if (size && size !== pageSize) {
      setPageSize(size);
    }
  };

  // 组件挂载时获取集合详情
  useEffect(() => {
    fetchCollectionDetail();
  }, [collectionName]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>
          <Text type="secondary">正在加载集合详细信息...</Text>
        </div>
      </div>
    );
  }

  if (!collectionDetail) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Empty description="集合不存在或已被删除" />
        <Button type="primary" onClick={handleGoBack} style={{ marginTop: 16 }}>
          返回集合列表
        </Button>
      </div>
    );
  }

  return (
    <div>
      {/* 集合详情页面的固定Header */}
      <div
        className="collection-detail-header"
        style={{
          height: '56px',
          lineHeight: '56px',
          padding: '0 24px',
          backgroundColor: 'transparent',
          border: 'none',
          position: 'fixed',
          top: '64px',
          left: isMobile ? '0' : (siderCollapsed ? '80px' : '280px'),
          right: '0',
          zIndex: 101,
          marginTop: '0px',
          marginBottom: '0px',
          boxShadow: 'none'
        }}>
        <div className="header-title" style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          height: '100%'
        }}>
          <div>
            <Title level={4} style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>
              <DatabaseOutlined style={{ marginRight: 8, fontSize: '16px' }} />
              {collectionDetail.display_name}
            </Title>
          </div>
          <div className="header-actions slide-in-right">
            <Button
              type="primary"
              icon={<UploadOutlined />}
              onClick={openUploadModal}
              size="small"
              style={{
                background: '#10b981',
                borderColor: '#10b981',
                marginRight: 8
              }}
            >
              上传文档
            </Button>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={onBack}
              size="small"
            >
              返回列表
            </Button>
          </div>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="fade-in-up" style={{
        position: 'relative',
        padding: '0 24px 24px 24px',
        marginTop: '56px'
      }}>

        <Card>
          <Tabs
            defaultActiveKey="documents"
            items={[
              {
                key: 'documents',
                label: (
                  <span style={{ fontSize: '16px', fontWeight: 500 }}>
                    <FileTextOutlined style={{ marginRight: 8 }} />
                    文档列表
                  </span>
                ),
                children: (
                  <div>
                    {collectionDetail.count === 0 ? (
                      <Empty
                        description="该集合暂无文档"
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        style={{ margin: '40px 0' }}
                      >
                        <Button
                          type="primary"
                          icon={<UploadOutlined />}
                          onClick={() => setUploadModalVisible(true)}
                        >
                          上传第一个文档
                        </Button>
                      </Empty>
                    ) : (
                      <div>
                        {/* 操作栏 */}
                        <div style={{ marginBottom: 16 }}>
                          <Text strong style={{ fontSize: '16px' }}>
                            文档管理
                          </Text>
                          <Text type="secondary" style={{ marginLeft: 8 }}>
                            ({collectionDetail.count} 个文档)
                          </Text>
                        </div>

                        {collectionDetail.count > 100 && (
                        <div style={{ marginBottom: 16, padding: 12, background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 6 }}>
                          <Text type="secondary">
                            <InfoCircleOutlined style={{ marginRight: 4 }} />
                            集合包含 {collectionDetail.count} 个文档，以下显示前 {collectionDetail.sample_documents.length} 个样本文档
                          </Text>
                        </div>
                      )}

                      <Table
                        dataSource={getPaginatedDocuments()}
                        pagination={false}
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
                            width: 250,
                            ellipsis: true,
                            render: (document) => (
                              document ? (
                                <Paragraph
                                  ellipsis={{
                                    rows: 2,
                                    expandable: false,
                                    suffix: '...'
                                  }}
                                  style={{
                                    margin: 0,
                                    fontSize: '13px',
                                    lineHeight: '1.4',
                                    maxWidth: '230px'
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
                            title: '向量信息',
                            dataIndex: 'embedding',
                            key: 'embedding',
                            width: 120,
                            align: 'center',
                            render: (embedding) => {
                              const expectedDimension = getVectorDimension();
                              const actualDimension = embedding ? embedding.length : 0;

                              if (!embedding) {
                                return (
                                  <Tag color="default" style={{ fontSize: '11px' }}>
                                    无向量
                                  </Tag>
                                );
                              }

                              // 检查维度是否一致
                              const isConsistent = expectedDimension === '未知' || actualDimension === parseInt(expectedDimension);

                              return (
                                <Tag
                                  color={isConsistent ? "purple" : "orange"}
                                  style={{ fontSize: '11px' }}
                                  title={isConsistent ? undefined : `期望维度: ${expectedDimension}`}
                                >
                                  {actualDimension}维
                                </Tag>
                              );
                            }
                          },
                          {
                            title: '块数信息',
                            key: 'chunk_info',
                            width: 150,
                            responsive: ['lg'],
                            render: (_, record) => {
                              const chunkMethod = record.chunkMethod;
                              const totalChunks = record.totalChunks;
                              const chunkSize = record.metadata?.chunk_size;
                              const textLength = record.document ? record.document.length : 0;

                              return (
                                <div style={{ fontSize: '12px' }}>
                                  <div>
                                    <Text strong style={{ color: '#52c41a', fontWeight: 'bold' }}>
                                      {totalChunks}块
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
                                  {chunkSize && (
                                    <div style={{ marginTop: 2, color: '#999', fontSize: '11px' }}>
                                      块大小: {chunkSize}
                                    </div>
                                  )}
                                  <div style={{ marginTop: 2, color: '#999', fontSize: '11px' }}>
                                    字符: {textLength}
                                  </div>
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
                            title: '操作',
                            key: 'actions',
                            width: 120,
                            align: 'center',
                            fixed: 'right',
                            render: (_, record) => (
                              <Space size="small">
                                <Popconfirm
                                  title="确认删除文档"
                                  description={
                                    <div>
                                      <p>确定要删除文档 <strong>"{record.fileName}"</strong> 吗？</p>
                                      <p style={{ color: '#ff4d4f', fontSize: '12px', margin: 0 }}>
                                        此操作将删除该文档的所有分块，删除后无法恢复！
                                      </p>
                                    </div>
                                  }
                                  onConfirm={() => handleDocumentDelete(record.fileName)}
                                  okText="确定删除"
                                  cancelText="取消"
                                  okType="danger"
                                  placement="topRight"
                                >
                                  <Button
                                    type="text"
                                    size="small"
                                    icon={<DeleteOutlined />}
                                    danger
                                    loading={deleteLoading === record.fileName}
                                    title="删除文档"
                                  />
                                </Popconfirm>
                              </Space>
                            )
                          }
                        ]}
                        size="small"
                        bordered
                        scroll={{ x: 1200 }}
                      />
                      </div>
                    )}
                  </div>
                )
              },

              {
                key: 'basic',
                label: (
                  <span style={{ fontSize: '16px', fontWeight: 500 }}>
                    <InfoCircleOutlined style={{ marginRight: 8 }} />
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
                          {getVectorDimension()} 维
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

        {/* 底部固定分页导航 */}
        {collectionDetail.count > 0 && getGroupedDocuments().length > pageSize && (
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
              total={getGroupedDocuments().length}
              pageSize={pageSize}
              showSizeChanger
              showQuickJumper
              showTotal={(total, range) => `第 ${range[0]}-${range[1]} 项，共 ${total} 个文件`}
              onChange={handlePageChange}
              pageSizeOptions={['5', '8', '10', '20']}
              size="small"
            />
          </div>
        )}

        {/* 页面右下角统计信息 */}
        <div
          className="stats-info"
          style={{
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
            transition: 'opacity 0.3s ease',
            backdropFilter: 'blur(4px)'
          }}
          onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
          onMouseLeave={(e) => e.currentTarget.style.opacity = '0.7'}
        >
          文件: {getGroupedDocuments().length} |
          维度: {getVectorDimension()} |
          文档: {collectionDetail.count.toLocaleString()} |
          方法: {collectionDetail.metadata?.chunking_methods?.length || 1}种
        </div>
      </div>

      {/* 文档上传模态框 */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              background: '#10b981',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <UploadOutlined style={{ color: 'white', fontSize: '18px' }} />
            </div>
            <div>
              <div style={{ fontSize: '18px', fontWeight: 600 }}>上传文档</div>
              <div style={{ fontSize: '14px', color: '#666', marginTop: '2px' }}>
                到集合：{collectionDetail?.display_name}
              </div>
            </div>
          </div>
        }
        open={uploadModalVisible}
        onCancel={closeUploadModal}
        footer={null}
        width={900}
        centered
        style={{ borderRadius: '16px' }}
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
              accept={generateAcceptString()}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">
                点击或拖拽文件到此区域上传
              </p>
              <p className="ant-upload-hint">
                支持多种文档格式：文本(.txt)、PDF(.pdf)、Word(.docx/.doc)、PowerPoint(.pptx/.ppt)、Markdown(.md)、RTF(.rtf)、Excel(.xlsx/.xls)、CSV(.csv)
                <br />
                文件大小不超过 150MB
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

          {/* 根据文件类型显示不同的配置 */}
          {selectedFile && isTableFile(selectedFile.name) ? (
            // 表格文件提示
            <Alert
              message="表格文件处理"
              description="检测到表格文件（Excel/CSV），将自动使用表格专用处理逻辑，每行数据作为一个文档块，无需配置分块参数。"
              type="info"
              showIcon
              style={{ margin: '16px 0' }}
            />
          ) : (
            // 普通文件的分块配置
            <>
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
            </>
          )}

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
    </div>
  );
};

export default CollectionDetail;
