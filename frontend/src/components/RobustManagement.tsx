import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Table,
  Modal,
  message,
  Alert,
  Progress,
  Space,
  Tag,
  Tooltip,
  Tabs,
  List,
  Typography,
  Divider
} from 'antd';
import {
  SafetyOutlined,
  BackupOutlined,
  RecoveryOutlined,
  SettingOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  DeleteOutlined,
  DownloadOutlined
} from '@ant-design/icons';
import apiClient from '../config/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface HealthStatus {
  status: string;
  consistency: {
    status: string;
    issues: string[];
    orphaned_vectors: string[];
    missing_vectors: string[];
  };
  backup: {
    total_backups: number;
    last_backup: string;
    backup_enabled: boolean;
  };
  disk_usage: {
    chroma_data: {
      total_gb: number;
      used_gb: number;
      free_gb: number;
    };
    backup_data: {
      total_gb: number;
      used_gb: number;
      free_gb: number;
    };
  };
}

interface BackupInfo {
  backup_id: string;
  backup_type: string;
  timestamp: string;
  backup_path: string;
  size_mb: number;
  collection_name?: string;
}

interface OrphanedCollection {
  collection_id: string;
  vector_path: string;
  estimated_size_mb: number;
  estimated_document_count: number;
  recoverable: boolean;
}

const RobustManagement: React.FC = () => {
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [orphanedCollections, setOrphanedCollections] = useState<OrphanedCollection[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('health');

  useEffect(() => {
    loadHealthStatus();
    loadBackups();
  }, []);

  const loadHealthStatus = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/robust/health');
      setHealthStatus(response.data.data);
    } catch (error) {
      console.error('加载健康状态失败:', error);
      message.error('加载健康状态失败');
    } finally {
      setLoading(false);
    }
  };

  const loadBackups = async () => {
    try {
      const response = await apiClient.get('/robust/backups');
      setBackups(response.data.data);
    } catch (error) {
      console.error('加载备份列表失败:', error);
      message.error('加载备份列表失败');
    }
  };

  const loadOrphanedCollections = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/robust/scan-recovery');
      if (response.data.success) {
        setOrphanedCollections(response.data.data.orphaned_collections);
      }
    } catch (error) {
      console.error('扫描孤立集合失败:', error);
      message.error('扫描孤立集合失败');
    } finally {
      setLoading(false);
    }
  };

  const createBackup = async (collectionName?: string) => {
    try {
      const response = await apiClient.post('/robust/backup', {
        collection_name: collectionName
      });
      
      if (response.data.success) {
        message.success('备份任务已启动');
        setTimeout(loadBackups, 2000); // 2秒后刷新备份列表
      }
    } catch (error) {
      console.error('创建备份失败:', error);
      message.error('创建备份失败');
    }
  };

  const restoreBackup = async (backupId: string) => {
    Modal.confirm({
      title: '确认恢复备份',
      content: '恢复备份将覆盖当前数据，此操作不可逆。确定要继续吗？',
      onOk: async () => {
        try {
          const response = await apiClient.post('/robust/restore', {
            backup_id: backupId
          });
          
          if (response.data.success) {
            message.success('备份恢复成功');
            loadHealthStatus();
          }
        } catch (error) {
          console.error('恢复备份失败:', error);
          message.error('恢复备份失败');
        }
      }
    });
  };

  const executeRecovery = async (recoveryPlan: any[]) => {
    try {
      const response = await apiClient.post('/robust/execute-recovery', {
        recovery_plan: recoveryPlan
      });
      
      if (response.data.success) {
        message.success('数据恢复任务已启动');
        setTimeout(loadHealthStatus, 3000); // 3秒后刷新状态
      }
    } catch (error) {
      console.error('执行数据恢复失败:', error);
      message.error('执行数据恢复失败');
    }
  };

  const cleanupBackups = async () => {
    Modal.confirm({
      title: '确认清理旧备份',
      content: '将根据配置的保留策略清理旧备份，确定要继续吗？',
      onOk: async () => {
        try {
          const response = await apiClient.post('/robust/cleanup-backups');
          
          if (response.data.success) {
            message.success('备份清理任务已启动');
            setTimeout(loadBackups, 2000);
          }
        } catch (error) {
          console.error('清理备份失败:', error);
          message.error('清理备份失败');
        }
      }
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'warning':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'error':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <ExclamationCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'warning':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  const backupColumns = [
    {
      title: '备份ID',
      dataIndex: 'backup_id',
      key: 'backup_id',
      render: (text: string) => (
        <Tooltip title={text}>
          <Text code>{text.substring(0, 20)}...</Text>
        </Tooltip>
      )
    },
    {
      title: '类型',
      dataIndex: 'backup_type',
      key: 'backup_type',
      render: (type: string) => (
        <Tag color={type === 'full' ? 'blue' : 'green'}>
          {type === 'full' ? '全量' : '增量'}
        </Tag>
      )
    },
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (timestamp: string) => new Date(timestamp).toLocaleString()
    },
    {
      title: '大小',
      dataIndex: 'size_mb',
      key: 'size_mb',
      render: (size: number) => `${size.toFixed(2)} MB`
    },
    {
      title: '操作',
      key: 'actions',
      render: (record: BackupInfo) => (
        <Space>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => restoreBackup(record.backup_id)}
          >
            恢复
          </Button>
        </Space>
      )
    }
  ];

  const orphanedColumns = [
    {
      title: '集合ID',
      dataIndex: 'collection_id',
      key: 'collection_id',
      render: (text: string) => (
        <Tooltip title={text}>
          <Text code>{text.substring(0, 20)}...</Text>
        </Tooltip>
      )
    },
    {
      title: '估计大小',
      dataIndex: 'estimated_size_mb',
      key: 'estimated_size_mb',
      render: (size: number) => `${size.toFixed(2)} MB`
    },
    {
      title: '估计文档数',
      dataIndex: 'estimated_document_count',
      key: 'estimated_document_count'
    },
    {
      title: '可恢复',
      dataIndex: 'recoverable',
      key: 'recoverable',
      render: (recoverable: boolean) => (
        <Tag color={recoverable ? 'green' : 'red'}>
          {recoverable ? '是' : '否'}
        </Tag>
      )
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <SafetyOutlined /> ChromaDB健壮管理
      </Title>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="系统健康" key="health">
          <Row gutter={[16, 16]}>
            {/* 系统状态概览 */}
            <Col span={24}>
              <Card
                title="系统状态概览"
                extra={
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={loadHealthStatus}
                    loading={loading}
                  >
                    刷新
                  </Button>
                }
              >
                {healthStatus && (
                  <Row gutter={[16, 16]}>
                    <Col span={6}>
                      <Statistic
                        title="系统状态"
                        value={healthStatus.status}
                        prefix={getStatusIcon(healthStatus.status)}
                        valueStyle={{ color: getStatusColor(healthStatus.status) === 'success' ? '#52c41a' : '#ff4d4f' }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="数据一致性"
                        value={healthStatus.consistency.status}
                        prefix={getStatusIcon(healthStatus.consistency.status)}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="备份总数"
                        value={healthStatus.backup.total_backups}
                        prefix={<BackupOutlined />}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="孤立向量"
                        value={healthStatus.consistency.orphaned_vectors.length}
                        prefix={<WarningOutlined />}
                        valueStyle={{ color: healthStatus.consistency.orphaned_vectors.length > 0 ? '#faad14' : '#52c41a' }}
                      />
                    </Col>
                  </Row>
                )}
              </Card>
            </Col>

            {/* 问题警告 */}
            {healthStatus && healthStatus.consistency.issues.length > 0 && (
              <Col span={24}>
                <Alert
                  message="发现数据一致性问题"
                  description={
                    <ul>
                      {healthStatus.consistency.issues.map((issue, index) => (
                        <li key={index}>{issue}</li>
                      ))}
                    </ul>
                  }
                  type="warning"
                  showIcon
                  action={
                    <Button size="small" onClick={loadOrphanedCollections}>
                      扫描恢复
                    </Button>
                  }
                />
              </Col>
            )}

            {/* 磁盘使用情况 */}
            {healthStatus && healthStatus.disk_usage && (
              <Col span={24}>
                <Card title="磁盘使用情况">
                  <Row gutter={[16, 16]}>
                    <Col span={12}>
                      <Title level={5}>ChromaDB数据</Title>
                      <Progress
                        percent={Math.round((healthStatus.disk_usage.chroma_data.used_gb / healthStatus.disk_usage.chroma_data.total_gb) * 100)}
                        format={() => `${healthStatus.disk_usage.chroma_data.used_gb.toFixed(2)} / ${healthStatus.disk_usage.chroma_data.total_gb.toFixed(2)} GB`}
                      />
                    </Col>
                    <Col span={12}>
                      <Title level={5}>备份数据</Title>
                      <Progress
                        percent={Math.round((healthStatus.disk_usage.backup_data.used_gb / healthStatus.disk_usage.backup_data.total_gb) * 100)}
                        format={() => `${healthStatus.disk_usage.backup_data.used_gb.toFixed(2)} / ${healthStatus.disk_usage.backup_data.total_gb.toFixed(2)} GB`}
                      />
                    </Col>
                  </Row>
                </Card>
              </Col>
            )}
          </Row>
        </TabPane>

        <TabPane tab="备份管理" key="backup">
          <Card
            title="备份管理"
            extra={
              <Space>
                <Button
                  type="primary"
                  icon={<BackupOutlined />}
                  onClick={() => createBackup()}
                >
                  创建全量备份
                </Button>
                <Button
                  icon={<DeleteOutlined />}
                  onClick={cleanupBackups}
                >
                  清理旧备份
                </Button>
              </Space>
            }
          >
            <Table
              dataSource={backups}
              columns={backupColumns}
              rowKey="backup_id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        <TabPane tab="数据恢复" key="recovery">
          <Card
            title="数据恢复"
            extra={
              <Button
                icon={<RecoveryOutlined />}
                onClick={loadOrphanedCollections}
                loading={loading}
              >
                扫描孤立数据
              </Button>
            }
          >
            {orphanedCollections.length > 0 ? (
              <>
                <Alert
                  message={`发现 ${orphanedCollections.length} 个孤立的集合数据`}
                  description="这些数据可能是由于程序异常退出或其他原因导致的。您可以尝试恢复这些数据。"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <Table
                  dataSource={orphanedCollections}
                  columns={orphanedColumns}
                  rowKey="collection_id"
                  pagination={{ pageSize: 10 }}
                />
                <Divider />
                <Button
                  type="primary"
                  icon={<RecoveryOutlined />}
                  onClick={() => {
                    const recoverablePlan = orphanedCollections
                      .filter(col => col.recoverable)
                      .map(col => ({
                        collection_id: col.collection_id,
                        display_name: `恢复的集合_${col.collection_id.substring(0, 8)}`,
                        metadata: {
                          recovered: true,
                          original_size_mb: col.estimated_size_mb,
                          estimated_document_count: col.estimated_document_count
                        }
                      }));
                    
                    if (recoverablePlan.length > 0) {
                      executeRecovery(recoverablePlan);
                    } else {
                      message.warning('没有可恢复的数据');
                    }
                  }}
                >
                  恢复所有可恢复数据
                </Button>
              </>
            ) : (
              <Alert
                message="未发现孤立数据"
                description="系统数据状态良好，没有发现需要恢复的孤立数据。"
                type="success"
                showIcon
              />
            )}
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default RobustManagement;
