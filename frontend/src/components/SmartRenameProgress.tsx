import React, { useState, useEffect, useRef } from 'react';
import {
  Modal,
  Progress,
  Typography,
  Space,
  Alert,
  Button,
  Tag,
  Statistic,
  Row,
  Col,
  Divider,
  notification
} from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  ThunderboltOutlined
} from '@ant-design/icons';
import apiClient from '../config/api';

const { Title, Text } = Typography;

interface CollectionAnalysis {
  collection_name: string;
  display_name: string;
  document_count: number;
  estimated_size_mb: number;
  estimated_processing_time_seconds: number;
  vector_dimension: number;
  should_show_progress: boolean;
  complexity_level: string;
  progress_message: string;
}

interface RenameTask {
  task_id: string;
  old_name: string;
  new_name: string;
  status: 'normal' | 'renaming' | 'error' | 'completed';
  progress: number;
  message: string;
  created_at: string;
  updated_at: string;
  error_message?: string;
}

interface SmartRenameProgressProps {
  taskId: string;
  oldName: string;
  newName: string;
  analysis: CollectionAnalysis;
  visible: boolean;
  onClose: () => void;
  onComplete: () => void;
  onCollectionListUpdate?: () => void;
}

const SmartRenameProgress: React.FC<SmartRenameProgressProps> = ({
  taskId,
  oldName,
  newName,
  analysis,
  visible,
  onClose,
  onComplete,
  onCollectionListUpdate
}) => {
  const [task, setTask] = useState<RenameTask | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [estimatedRemaining, setEstimatedRemaining] = useState<number>(
    analysis.estimated_processing_time_seconds
  );
  const [elapsedTime, setElapsedTime] = useState<number>(0);
  const [startTime] = useState<number>(Date.now());
  const wsRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (visible && taskId) {
      setupWebSocket();
      startMonitoring();
      startTimer();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [visible, taskId]);

  const setupWebSocket = () => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/ws`;
      
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
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket错误:', error);
      };
    } catch (error) {
      console.error('WebSocket连接失败:', error);
    }
  };

  const handleWebSocketMessage = (message: any) => {
    if (message.task_id !== taskId) return;

    switch (message.type) {
      case 'rename_progress':
        setTask(prevTask => ({
          ...prevTask,
          task_id: message.task_id,
          old_name: oldName,
          new_name: newName,
          status: 'renaming',
          progress: message.progress,
          message: message.message,
          created_at: prevTask?.created_at || new Date().toISOString(),
          updated_at: new Date().toISOString()
        }));
        
        if (message.estimated_remaining) {
          setEstimatedRemaining(message.estimated_remaining);
        }
        break;
        
      case 'rename_completed':
        setTask(prevTask => ({
          ...prevTask,
          status: 'completed',
          progress: 100,
          message: '重命名完成',
          updated_at: new Date().toISOString()
        }));
        
        notification.success({
          message: '重命名完成',
          description: `集合 "${oldName}" 已成功重命名为 "${newName}"`,
          duration: 3
        });
        
        // 通知集合列表更新
        if (onCollectionListUpdate) {
          onCollectionListUpdate();
        }
        
        setTimeout(() => {
          onComplete();
          onClose();
        }, 2000);
        break;
        
      case 'rename_failed':
        setTask(prevTask => ({
          ...prevTask,
          status: 'error',
          message: `重命名失败: ${message.error_message}`,
          error_message: message.error_message,
          updated_at: new Date().toISOString()
        }));
        
        setError(message.error_message);
        break;
    }
  };

  const startMonitoring = () => {
    setLoading(true);
    setError(null);
    
    // 初始化任务状态
    setTask({
      task_id: taskId,
      old_name: oldName,
      new_name: newName,
      status: 'renaming',
      progress: 0,
      message: '正在准备重命名...',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
    
    setLoading(false);
  };

  const startTimer = () => {
    timerRef.current = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
  };

  const getStatusIcon = () => {
    if (!task) return <LoadingOutlined />;
    
    switch (task.status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'error':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'renaming':
        return <LoadingOutlined />;
      default:
        return <LoadingOutlined />;
    }
  };

  const getProgressPercent = () => {
    if (!task) return 0;
    if (task.progress < 0) return 0;
    return Math.min(task.progress, 100);
  };

  const getComplexityColor = () => {
    switch (analysis.complexity_level) {
      case 'complex': return 'red';
      case 'medium': return 'orange';
      default: return 'green';
    }
  };

  const getComplexityText = () => {
    switch (analysis.complexity_level) {
      case 'complex': return '复杂';
      case 'medium': return '中等';
      default: return '简单';
    }
  };

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}秒`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}分${remainingSeconds}秒`;
  };

  return (
    <Modal
      title={
        <Space>
          {getStatusIcon()}
          <span>智能重命名进度</span>
          <Tag color={getComplexityColor()}>
            {getComplexityText()}任务
          </Tag>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={
        task?.status === 'completed' || task?.status === 'error' ? (
          <Button onClick={onClose}>
            关闭
          </Button>
        ) : null
      }
      closable={task?.status === 'completed' || task?.status === 'error'}
      maskClosable={false}
      width={600}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 集合信息 */}
        <div>
          <Title level={5}>集合信息</Title>
          <Row gutter={16}>
            <Col span={8}>
              <Statistic
                title="文档数量"
                value={analysis.document_count}
                prefix={<FileTextOutlined />}
                formatter={(value) => `${value?.toLocaleString()} 条`}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="数据大小"
                value={analysis.estimated_size_mb}
                prefix={<DatabaseOutlined />}
                formatter={(value) => `${value?.toFixed(1)} MB`}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="向量维度"
                value={analysis.vector_dimension}
                prefix={<ThunderboltOutlined />}
              />
            </Col>
          </Row>
        </div>

        <Divider />

        {/* 重命名信息 */}
        <div>
          <Title level={5}>重命名操作</Title>
          <div style={{ marginTop: 8 }}>
            <Text code>{oldName}</Text>
            <Text style={{ margin: '0 8px' }}>→</Text>
            <Text code>{newName}</Text>
          </div>
        </div>

        {/* 进度条 */}
        <div>
          <Progress
            percent={getProgressPercent()}
            status={task?.status === 'error' ? 'exception' : 
                   task?.status === 'completed' ? 'success' : 'active'}
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
            showInfo={true}
          />
        </div>

        {/* 时间统计 */}
        <Row gutter={16}>
          <Col span={12}>
            <Statistic
              title="已用时间"
              value={elapsedTime}
              prefix={<ClockCircleOutlined />}
              formatter={(value) => formatTime(Number(value))}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="预估剩余"
              value={Math.max(0, estimatedRemaining - elapsedTime)}
              prefix={<ClockCircleOutlined />}
              formatter={(value) => formatTime(Number(value))}
            />
          </Col>
        </Row>

        {/* 状态信息 */}
        <div>
          <Space align="center">
            <Text strong>当前状态:</Text>
            <Tag color={
              task?.status === 'completed' ? 'success' :
              task?.status === 'error' ? 'error' :
              'processing'
            }>
              {task?.status === 'completed' ? '已完成' :
               task?.status === 'error' ? '失败' :
               task?.status === 'renaming' ? '处理中' : '准备中'}
            </Tag>
          </Space>
          
          {task?.message && (
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">{task.message}</Text>
            </div>
          )}
        </div>

        {/* 错误信息 */}
        {error && (
          <Alert
            message="处理失败"
            description={error}
            type="error"
            showIcon
          />
        )}

        {/* 成功信息 */}
        {task?.status === 'completed' && (
          <Alert
            message="重命名完成"
            description="集合已成功重命名，数据完整性已验证。页面将自动更新。"
            type="success"
            showIcon
          />
        )}

        {/* 处理中提示 */}
        {task?.status === 'renaming' && analysis.complexity_level === 'complex' && (
          <Alert
            message="大数据量处理中"
            description={analysis.progress_message}
            type="info"
            showIcon
          />
        )}
      </Space>
    </Modal>
  );
};

export default SmartRenameProgress;
