import React, { useMemo } from 'react';
import { Card, Row, Col, Statistic, Progress, Space, Typography } from 'antd';
import { 
  DatabaseOutlined, 
  FileTextOutlined, 
  SearchOutlined, 
  CloudOutlined,
  BarChartOutlined,
  TrophyOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;

interface CollectionInfo {
  name: string;
  display_name: string;
  count: number;
  metadata: Record<string, any>;
  chunk_count?: number;
  uploaded_files?: string[];
  files_count?: number;
  chunk_statistics?: {
    total_chunks: number;
    files_count: number;
    methods_used: string[];
  };
}

interface StatsDashboardProps {
  collections: CollectionInfo[];
}

const StatsDashboard: React.FC<StatsDashboardProps> = ({ collections }) => {
  // 使用useMemo优化计算，避免不必要的重渲染
  const stats = useMemo(() => {
    const totalCollections = collections.length;
    const totalDocuments = collections.reduce((sum, col) => sum + col.count, 0);
    const totalFiles = collections.reduce((sum, col) => {
      const fileCount = col.chunk_statistics?.files_count ?? col.files_count ?? 0;
      return sum + fileCount;
    }, 0);

    // 计算嵌入模型分布
    const embeddingModelStats = collections.reduce((stats, col) => {
      const model = col.metadata?.embedding_model || 'default';
      const modelName = model === 'alibaba-text-embedding-v4' ? '阿里云' : '默认';
      stats[modelName] = (stats[modelName] || 0) + 1;
      return stats;
    }, {} as Record<string, number>);

    // 计算分块方法统计
    const chunkingMethodStats = collections.reduce((stats, col) => {
      const methods = col.chunk_statistics?.methods_used || [];
      methods.forEach(method => {
        const methodName = method === 'recursive' ? '递归分块' :
                          method === 'fixed_size' ? '固定分块' :
                          method === 'semantic' ? '语义分块' : method;
        stats[methodName] = (stats[methodName] || 0) + 1;
      });
      return stats;
    }, {} as Record<string, number>);

    // 最大的集合
    const largestCollection = collections.reduce((max, col) =>
      col.count > max.count ? col : max,
      collections[0] || { display_name: '暂无', count: 0 }
    );

    return {
      totalCollections,
      totalDocuments,
      totalFiles,
      embeddingModelStats,
      chunkingMethodStats,
      largestCollection
    };
  }, [collections]);

  return (
    <div style={{ marginBottom: '24px' }}>
      <Title level={4} style={{ marginBottom: '24px' }}>
        <BarChartOutlined style={{ marginRight: 8, color: '#3b82f6' }} />
        <span style={{ color: '#3b82f6', fontWeight: 600 }}>
          数据总览
        </span>
      </Title>
      
      <Row gutter={[24, 24]}>
        {/* 基础统计 */}
        <Col xs={24} sm={12} md={6}>
          <Card className="stats-card">
            <Statistic
              title="总集合数"
              value={stats.totalCollections}
              prefix={<DatabaseOutlined style={{ color: '#3b82f6' }} />}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card className="stats-card">
            <Statistic
              title="总文档数"
              value={stats.totalDocuments}
              prefix={<FileTextOutlined style={{ color: '#10b981' }} />}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card className="stats-card">
            <Statistic
              title="总文件数"
              value={stats.totalFiles}
              prefix={<CloudOutlined style={{ color: '#f59e0b' }} />}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card className="stats-card">
            <Statistic
              title="平均文档/集合"
              value={stats.totalCollections > 0 ? Math.round(stats.totalDocuments / stats.totalCollections) : 0}
              prefix={<TrophyOutlined style={{ color: '#ef4444' }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* 详细统计 */}
      <Row gutter={[24, 24]} style={{ marginTop: '24px' }}>
        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <CloudOutlined style={{ color: '#3b82f6' }} />
                <span>嵌入模型分布</span>
              </Space>
            }
            style={{ height: '200px' }}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              {Object.entries(stats.embeddingModelStats).map(([model, count]) => (
                <div key={model} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text>{model}</Text>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: '120px' }}>
                    <Progress
                      percent={stats.totalCollections > 0 ? Math.round((count / stats.totalCollections) * 100) : 0}
                      size="small"
                      style={{ minWidth: '60px' }}
                    />
                    <Text type="secondary">{count}</Text>
                  </div>
                </div>
              ))}
            </Space>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <SearchOutlined style={{ color: '#3b82f6' }} />
                <span>分块方法统计</span>
              </Space>
            }
            style={{ height: '200px' }}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              {Object.entries(stats.chunkingMethodStats).map(([method, count]) => (
                <div key={method} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text>{method}</Text>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: '120px' }}>
                    <Progress
                      percent={stats.totalCollections > 0 ? Math.round((count / stats.totalCollections) * 100) : 0}
                      size="small"
                      style={{ minWidth: '60px' }}
                    />
                    <Text type="secondary">{count}</Text>
                  </div>
                </div>
              ))}
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 最大集合信息 */}
      <Row gutter={[24, 24]} style={{ marginTop: '24px' }}>
        <Col xs={24}>
          <Card
            title={
              <Space>
                <TrophyOutlined style={{ color: '#3b82f6' }} />
                <span>最大集合</span>
              </Space>
            }
            style={{
              background: '#f59e0b',
              color: 'white',
              border: '1px solid #f59e0b'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <Text style={{ color: 'white', fontSize: '18px', fontWeight: 600 }}>
                  {stats.largestCollection.display_name}
                </Text>
                <div style={{ color: 'rgba(255,255,255,0.9)', marginTop: '4px' }}>
                  包含 {stats.largestCollection.count} 个文档
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ color: 'rgba(255,255,255,0.9)', fontSize: '12px' }}>
                  占总文档数
                </div>
                <div style={{ color: 'white', fontSize: '24px', fontWeight: 700 }}>
                  {stats.totalDocuments > 0 ? Math.round((stats.largestCollection.count / stats.totalDocuments) * 100) : 0}%
                </div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default StatsDashboard;