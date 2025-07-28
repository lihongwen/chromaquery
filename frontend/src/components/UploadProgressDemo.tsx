import React, { useState } from 'react';
import { Card, Button, Progress, Typography, Space, Alert } from 'antd';
import { estimateProcessingTime, getCurrentStage, formatRemainingTime, getProcessingHint } from '../utils/uploadProgress';

const { Text, Title } = Typography;

/**
 * 上传进度演示组件
 * 用于展示新的进度估算功能
 */
export const UploadProgressDemo: React.FC = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentMessage, setCurrentMessage] = useState('');
  const [remainingTime, setRemainingTime] = useState('');

  // 模拟文件信息
  const mockFiles = [
    { name: 'small_document.txt', size: 500 * 1024 }, // 500KB
    { name: 'medium_document.pdf', size: 5 * 1024 * 1024 }, // 5MB
    { name: 'large_document.docx', size: 50 * 1024 * 1024 }, // 50MB
    { name: 'huge_spreadsheet.xlsx', size: 100 * 1024 * 1024 }, // 100MB
  ];

  const simulateUpload = (file: { name: string; size: number }) => {
    setIsRunning(true);
    setProgress(0);
    
    const estimate = estimateProcessingTime(file.size, file.name);
    const startTime = Date.now();
    
    const interval = setInterval(() => {
      const elapsedSeconds = (Date.now() - startTime) / 1000;
      const newProgress = Math.min(90, elapsedSeconds * estimate.incrementPerSecond);
      
      const currentStage = getCurrentStage(newProgress, estimate.stages);
      const remaining = Math.max(0, estimate.estimatedTimeSeconds - elapsedSeconds);
      
      setProgress(newProgress);
      setCurrentMessage(currentStage?.message || '处理中...');
      setRemainingTime(remaining > 1 ? formatRemainingTime(remaining) : '即将完成');
      
      if (newProgress >= 90) {
        clearInterval(interval);
        setProgress(100);
        setCurrentMessage('处理完成！');
        setRemainingTime('');
        setIsRunning(false);
      }
    }, 500);
  };

  return (
    <Card title="文件上传进度演示" style={{ maxWidth: 600, margin: '20px auto' }}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Alert
          message="进度估算演示"
          description="选择不同大小的文件来查看新的智能进度估算效果"
          type="info"
          showIcon
        />
        
        <div>
          <Title level={5}>选择模拟文件：</Title>
          <Space wrap>
            {mockFiles.map((file, index) => (
              <Button
                key={index}
                onClick={() => simulateUpload(file)}
                disabled={isRunning}
                type={index === 2 ? 'primary' : 'default'}
              >
                {file.name} ({(file.size / (1024 * 1024)).toFixed(1)}MB)
              </Button>
            ))}
          </Space>
        </div>

        {(isRunning || progress > 0) && (
          <div>
            <Progress
              percent={Math.round(progress)}
              status={isRunning ? 'active' : 'success'}
              strokeColor={progress >= 100 ? '#52c41a' : '#1890ff'}
            />
            
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">{currentMessage}</Text>
              {remainingTime && (
                <Text type="secondary" style={{ marginLeft: 16 }}>
                  剩余时间: {remainingTime}
                </Text>
              )}
            </div>
          </div>
        )}

        <Alert
          message="改进说明"
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              <li>根据文件大小和类型智能估算处理时间</li>
              <li>显示当前处理阶段和剩余时间</li>
              <li>不同文件类型有不同的时间估算</li>
              <li>大文件支持5分钟超时时间</li>
            </ul>
          }
          type="success"
          showIcon
        />
      </Space>
    </Card>
  );
};
