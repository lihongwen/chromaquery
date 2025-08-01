import React, { useState, useEffect, useRef } from 'react';
import {
  Modal,
  Progress,
  Typography,
  Space,
  Alert,
  Button,
  Spin,
  Tag,
  Statistic,
  Row,
  Col
} from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  CloseOutlined,
  ClockCircleOutlined,
  DatabaseOutlined
} from '@ant-design/icons';
import apiClient from '../config/api';

const { Text, Title } = Typography;

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

interface AsyncRenameProgressProps {
  taskId: string;
  oldName: string;
  newName: string;
  visible: boolean;
  analysis?: CollectionAnalysis;
  onClose: () => void;
  onComplete: () => void;
}

const AsyncRenameProgress: React.FC<AsyncRenameProgressProps> = ({
  taskId,
  oldName,
  newName,
  visible,
  analysis,
  onClose,
  onComplete
}) => {
  const [task, setTask] = useState<RenameTask | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [estimatedRemaining, setEstimatedRemaining] = useState<number>(0);
  const [startTime, setStartTime] = useState<number>(Date.now());
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (visible && taskId) {
      startMonitoring();
    }
  }, [visible, taskId]);

  const startMonitoring = () => {
    setLoading(true);
    setError(null);
    
    const checkProgress = async () => {
      try {
        const response = await apiClient.get(`/collections/rename/status/${taskId}`);
        
        if (response.data.success) {
          const taskData = response.data.task;
          setTask(taskData);
          
          if (taskData.status === 'completed') {
            // 任务完成
            setTimeout(() => {
              onComplete();
              onClose();
            }, 2000); // 2秒后自动关闭
            return;
          } else if (taskData.status === 'error') {
            // 任务失败
            setError(taskData.error_message || '重命名失败');
            return;
          }
          
          // 继续监控
          setTimeout(checkProgress, 2000); // 每2秒检查一次
        } else {
          setError('无法获取任务状态');
        }
      } catch (err: any) {
        if (err.response?.status === 404) {
          // 任务不存在或已完成
          onComplete();
          onClose();
        } else {
          setError('监控任务状态时出错');
        }
      } finally {
        setLoading(false);
      }
    };
    
    checkProgress();
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

  const getStatusColor = () => {
    if (!task) return 'processing';
    
    switch (task.status) {
      case 'completed':
        return 'success';
      case 'error':
        return 'exception';
      case 'renaming':
        return 'active';
      default:
        return 'active';
    }
  };

  const getProgressPercent = () => {
    if (!task) return 0;
    if (task.progress < 0) return 0; // 错误状态
    return Math.min(task.progress, 100);
  };

  return (
    <Modal
      title={
        <Space>
          {getStatusIcon()}
          <span>集合重命名进度</span>
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
      width={500}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 重命名信息 */}
        <div>
          <Text strong>重命名操作:</Text>
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
            status={getStatusColor()}
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
            showInfo={true}
          />
        </div>

        {/* 状态信息 */}
        <div>
          <Space align="center">
            <Text strong>状态:</Text>
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
            description="集合已成功重命名，数据完整性已验证。"
            type="success"
            showIcon
          />
        )}

        {/* 处理中提示 */}
        {task?.status === 'renaming' && (
          <Alert
            message="后台处理中"
            description="集合名称已更新，正在后台优化数据结构，请稍候..."
            type="info"
            showIcon
          />
        )}

        {/* 任务信息 */}
        {task && (
          <div style={{ fontSize: '12px', color: '#999' }}>
            <div>任务ID: {task.task_id}</div>
            <div>创建时间: {new Date(task.created_at).toLocaleString()}</div>
            {task.updated_at !== task.created_at && (
              <div>更新时间: {new Date(task.updated_at).toLocaleString()}</div>
            )}
          </div>
        )}
      </Space>
    </Modal>
  );
};

export default AsyncRenameProgress;
