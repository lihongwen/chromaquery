import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Alert,
  Progress,
  Space,
  Tag,
  Tooltip,
  Modal,
  List,
  Typography,
  Divider,
  Badge,
  notification,
  Spin
} from 'antd';
import {
  CheckCircleOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
  ReloadOutlined,
  ToolOutlined,
  InfoCircleOutlined,
  BugOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import apiClient from '../config/api';

const { Title, Text, Paragraph } = Typography;

interface ConsistencyStatus {
  consistency: {
    status: string;
    issues: string[];
    orphaned_vectors: string[];
    orphaned_metadata: string[];
    missing_in_frontend: string[];
    missing_in_backend: string[];
  };
  sync: {
    sync_status: string;
    last_sync: string;
    pending_events_count: number;
    consistency_status: string;
    out_of_sync_collections: {
      missing_in_frontend: string[];
      missing_in_backend: string[];
      orphaned_vectors: string[];
    };
  };
  version: {
    chromadb_version: string;
    schema_version: string;
    compatibility: {
      compatible: boolean;
      migration_needed: boolean;
      issues: string[];
    };
  };
}

interface SyncEvent {
  event_id: string;
  event_type: string;
  collection_name: string;
  timestamp: string;
  details: Record<string, any>;
}

const ConsistencyManager: React.FC = () => {
  const [status, setStatus] = useState<ConsistencyStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [pendingEvents, setPendingEvents] = useState<SyncEvent[]>([]);
  const [repairModalVisible, setRepairModalVisible] = useState(false);
  const [repairing, setRepairing] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    loadConsistencyStatus();
    loadPendingEvents();
    
    if (autoRefresh) {
      const interval = setInterval(loadConsistencyStatus, 30000); // 30秒刷新
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  useEffect(() => {
    // 建立WebSocket连接
    const connectWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/consistency/ws`;
      
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket连接已建立');
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleWebSocketMessage(message);
        } catch (error) {
          console.error('解析WebSocket消息失败:', error);
        }
      };
      
      wsRef.current.onclose = () => {
        console.log('WebSocket连接已关闭');
        // 5秒后重连
        setTimeout(connectWebSocket, 5000);
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket错误:', error);
      };
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleWebSocketMessage = (message: any) => {
    switch (message.type) {
      case 'sync_event':
        notification.info({
          message: '同步事件',
          description: `${message.data.event_type}: ${message.data.collection_name}`,
          duration: 3
        });
        loadConsistencyStatus();
        loadPendingEvents();
        break;
      
      case 'status_update':
        // 更新状态但不覆盖当前加载状态
        if (!loading) {
          setStatus(prevStatus => ({
            ...prevStatus,
            sync: message.data
          } as ConsistencyStatus));
        }
        break;
    }
  };

  const loadConsistencyStatus = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/consistency/status');
      setStatus(response.data.data);
    } catch (error) {
      console.error('加载一致性状态失败:', error);
      notification.error({
        message: '加载失败',
        description: '无法加载一致性状态'
      });
    } finally {
      setLoading(false);
    }
  };

  const loadPendingEvents = async () => {
    try {
      const response = await apiClient.get('/consistency/sync/events');
      setPendingEvents(response.data.data);
    } catch (error) {
      console.error('加载待处理事件失败:', error);
    }
  };

  const performConsistencyCheck = async (autoRepair = false) => {
    try {
      setLoading(true);
      const response = await apiClient.post('/consistency/check', {
        full_check: true,
        auto_repair: autoRepair
      });
      
      if (response.data.success) {
        notification.success({
          message: '检查完成',
          description: `一致性状态: ${response.data.report.status}`
        });
        
        if (autoRepair && response.data.auto_repair) {
          notification.info({
            message: '自动修复完成',
            description: `修复了 ${response.data.auto_repair.repaired.length} 个问题`
          });
        }
        
        loadConsistencyStatus();
      }
    } catch (error) {
      console.error('一致性检查失败:', error);
      notification.error({
        message: '检查失败',
        description: '一致性检查过程中出现错误'
      });
    } finally {
      setLoading(false);
    }
  };

  const forceSync = async () => {
    try {
      setLoading(true);
      const response = await apiClient.post('/consistency/sync/force', {
        force_sync: true,
        clear_pending_events: true
      });
      
      if (response.data.success) {
        notification.success({
          message: '同步完成',
          description: '强制同步已完成'
        });
        loadConsistencyStatus();
        loadPendingEvents();
      }
    } catch (error) {
      console.error('强制同步失败:', error);
      notification.error({
        message: '同步失败',
        description: '强制同步过程中出现错误'
      });
    } finally {
      setLoading(false);
    }
  };

  const performRepair = async () => {
    try {
      setRepairing(true);
      const response = await apiClient.post('/consistency/repair', {
        repair_orphaned_vectors: true,
        repair_orphaned_metadata: true,
        create_backup: true
      });
      
      if (response.data.success) {
        notification.success({
          message: '修复完成',
          description: `最终状态: ${response.data.final_status}`
        });
        setRepairModalVisible(false);
        loadConsistencyStatus();
      }
    } catch (error) {
      console.error('修复失败:', error);
      notification.error({
        message: '修复失败',
        description: '数据修复过程中出现错误'
      });
    } finally {
      setRepairing(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'consistent':
      case 'synced':
      case 'healthy':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'inconsistent':
      case 'out_of_sync':
      case 'warning':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'error':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <InfoCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'consistent':
      case 'synced':
      case 'healthy':
        return 'success';
      case 'inconsistent':
      case 'out_of_sync':
      case 'warning':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  if (!status) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" />
        <div style={{ marginTop: '16px' }}>加载一致性状态...</div>
      </div>
    );
  }

  const hasIssues = status.consistency.issues.length > 0 || 
                   status.sync.pending_events_count > 0 ||
                   !status.version.compatibility.compatible;

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <Title level={2}>
          <BugOutlined /> 数据一致性管理
        </Title>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadConsistencyStatus}
            loading={loading}
          >
            刷新状态
          </Button>
          <Button
            type="primary"
            icon={<SyncOutlined />}
            onClick={() => performConsistencyCheck(false)}
            loading={loading}
          >
            检查一致性
          </Button>
          {hasIssues && (
            <Button
              type="primary"
              danger
              icon={<ToolOutlined />}
              onClick={() => setRepairModalVisible(true)}
            >
              修复问题
            </Button>
          )}
        </Space>
      </div>

      {/* 总体状态概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="数据一致性"
              value={status.consistency.status}
              prefix={getStatusIcon(status.consistency.status)}
              valueStyle={{ 
                color: getStatusColor(status.consistency.status) === 'success' ? '#52c41a' : 
                       getStatusColor(status.consistency.status) === 'warning' ? '#faad14' : '#ff4d4f'
              }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="同步状态"
              value={status.sync.sync_status}
              prefix={getStatusIcon(status.sync.sync_status)}
              valueStyle={{ 
                color: getStatusColor(status.sync.sync_status) === 'success' ? '#52c41a' : 
                       getStatusColor(status.sync.sync_status) === 'warning' ? '#faad14' : '#ff4d4f'
              }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="待处理事件"
              value={status.sync.pending_events_count}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: status.sync.pending_events_count > 0 ? '#faad14' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="版本兼容性"
              value={status.version.compatibility.compatible ? '兼容' : '不兼容'}
              prefix={getStatusIcon(status.version.compatibility.compatible ? 'consistent' : 'error')}
              valueStyle={{ 
                color: status.version.compatibility.compatible ? '#52c41a' : '#ff4d4f'
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* 问题警告 */}
      {hasIssues && (
        <Alert
          message="发现数据一致性问题"
          description={
            <div>
              {status.consistency.issues.map((issue, index) => (
                <div key={index}>• {issue}</div>
              ))}
              {status.version.compatibility.issues.map((issue, index) => (
                <div key={index}>• {issue}</div>
              ))}
            </div>
          }
          type="warning"
          showIcon
          style={{ marginBottom: '24px' }}
          action={
            <Space>
              <Button size="small" onClick={() => performConsistencyCheck(true)}>
                自动修复
              </Button>
              <Button size="small" onClick={forceSync}>
                强制同步
              </Button>
            </Space>
          }
        />
      )}

      {/* 详细信息 */}
      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card title="一致性详情" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              {status.consistency.orphaned_vectors.length > 0 && (
                <div>
                  <Tag color="orange">孤立向量文件</Tag>
                  <Text type="secondary">{status.consistency.orphaned_vectors.length} 个</Text>
                </div>
              )}
              {status.consistency.orphaned_metadata.length > 0 && (
                <div>
                  <Tag color="red">孤立元数据</Tag>
                  <Text type="secondary">{status.consistency.orphaned_metadata.length} 个</Text>
                </div>
              )}
              {status.consistency.missing_in_frontend.length > 0 && (
                <div>
                  <Tag color="blue">前端缺失</Tag>
                  <Text type="secondary">{status.consistency.missing_in_frontend.length} 个集合</Text>
                </div>
              )}
              {status.consistency.missing_in_backend.length > 0 && (
                <div>
                  <Tag color="purple">后端缺失</Tag>
                  <Text type="secondary">{status.consistency.missing_in_backend.length} 个集合</Text>
                </div>
              )}
            </Space>
          </Card>
        </Col>
        
        <Col span={12}>
          <Card title="版本信息" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text strong>ChromaDB版本: </Text>
                <Text code>{status.version.chromadb_version}</Text>
              </div>
              <div>
                <Text strong>Schema版本: </Text>
                <Text code>{status.version.schema_version}</Text>
              </div>
              {status.version.compatibility.migration_needed && (
                <div>
                  <Tag color="orange">需要迁移</Tag>
                </div>
              )}
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 待处理事件 */}
      {pendingEvents.length > 0 && (
        <Card title="待处理事件" style={{ marginTop: '16px' }} size="small">
          <List
            size="small"
            dataSource={pendingEvents}
            renderItem={(event) => (
              <List.Item>
                <Space>
                  <Tag color="blue">{event.event_type}</Tag>
                  <Text>{event.collection_name}</Text>
                  <Text type="secondary">{new Date(event.timestamp).toLocaleString()}</Text>
                </Space>
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* 修复确认模态框 */}
      <Modal
        title="确认数据修复"
        open={repairModalVisible}
        onOk={performRepair}
        onCancel={() => setRepairModalVisible(false)}
        confirmLoading={repairing}
        okText="开始修复"
        cancelText="取消"
      >
        <Alert
          message="注意"
          description="数据修复将自动创建备份，然后尝试修复发现的一致性问题。此过程可能需要一些时间。"
          type="info"
          showIcon
          style={{ marginBottom: '16px' }}
        />
        <Paragraph>
          将执行以下修复操作：
        </Paragraph>
        <ul>
          <li>修复孤立的向量文件</li>
          <li>清理孤立的元数据记录</li>
          <li>同步前后端状态</li>
          <li>验证修复结果</li>
        </ul>
      </Modal>
    </div>
  );
};

export default ConsistencyManager;
