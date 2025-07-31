import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Space,
  DatePicker,
  Select,
  Button,
  Typography,
  Empty,
  Spin,
  message
} from 'antd';
import {
  SearchOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  UserOutlined,
  ReloadOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { api } from '../../config/api';

const { Text } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

interface QueryLog {
  id: string;
  timestamp: string;
  query: string;
  collection: string;
  results_count: number;
  response_time: number;
  status: 'success' | 'error';
  user_id?: string;
}

interface AnalyticsData {
  totalQueries: number;
  avgResponseTime: number;
  activeCollections: number;
  uniqueUsers: number;
  queryTrend: Array<{ date: string; count: number }>;
  collectionUsage: Array<{ collection: string; count: number }>;
  recentLogs: QueryLog[];
}

const AnalyticsTab: React.FC = () => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(7, 'days'),
    dayjs()
  ]);
  const [selectedPeriod, setSelectedPeriod] = useState('7days');

  useEffect(() => {
    fetchAnalyticsData();
  }, [dateRange]);

  const fetchAnalyticsData = async () => {
    setLoading(true);
    try {
      // 准备API参数
      const params = {
        start_date: dateRange[0].format('YYYY-MM-DD HH:mm:ss'),
        end_date: dateRange[1].format('YYYY-MM-DD HH:mm:ss'),
        period: selectedPeriod
      };

      // 调用真实的API
      const response = await api.analytics.getData(params);
      const analyticsData = response.data;

      setData(analyticsData);
    } catch (error) {
      console.error('获取分析数据失败:', error);
      message.error('获取分析数据失败，请稍后重试');

      // 如果API调用失败，设置空数据而不是模拟数据
      setData({
        totalQueries: 0,
        avgResponseTime: 0,
        activeCollections: 0,
        uniqueUsers: 0,
        queryTrend: [],
        collectionUsage: [],
        recentLogs: []
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    fetchAnalyticsData();
  };

  const handlePeriodChange = (value: string) => {
    setSelectedPeriod(value);
    const now = dayjs();
    let start = now;
    
    switch (value) {
      case '7days':
        start = now.subtract(7, 'days');
        break;
      case '30days':
        start = now.subtract(30, 'days');
        break;
      case '90days':
        start = now.subtract(90, 'days');
        break;
      default:
        start = now.subtract(7, 'days');
    }
    
    setDateRange([start, now]);
  };

  const columns: ColumnsType<QueryLog> = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      sorter: (a, b) => dayjs(a.timestamp).unix() - dayjs(b.timestamp).unix(),
      render: (timestamp) => dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '查询内容',
      dataIndex: 'query',
      key: 'query',
      ellipsis: true,
      render: (query) => <Text copyable>{query}</Text>,
    },
    {
      title: '集合',
      dataIndex: 'collection',
      key: 'collection',
      render: (collection) => <Tag color="blue">{collection}</Tag>,
    },
    {
      title: '结果数',
      dataIndex: 'results_count',
      key: 'results_count',
      align: 'right',
      sorter: (a, b) => a.results_count - b.results_count,
    },
    {
      title: '响应时间',
      dataIndex: 'response_time',
      key: 'response_time',
      align: 'right',
      sorter: (a, b) => a.response_time - b.response_time,
      render: (time) => `${time.toFixed(3)}s`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'success' ? 'green' : 'red'}>
          {status === 'success' ? '成功' : '失败'}
        </Tag>
      ),
    },
  ];

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '400px' 
      }}>
        <Spin size="large" tip="正在加载分析数据..." />
      </div>
    );
  }

  if (!data) {
    return (
      <Empty
        description="暂无分析数据"
        image={<BarChartOutlined style={{ fontSize: 64, color: 'var(--ant-color-text-secondary)' }} />}
      />
    );
  }

  return (
    <div style={{ padding: 24 }}>
      {/* 时间范围选择器 */}
      <Card style={{ marginBottom: 24 }}>
        <Space>
          <RangePicker
            value={dateRange}
            onChange={(dates) => dates && setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
          />
          <Select
            value={selectedPeriod}
            onChange={handlePeriodChange}
            style={{ width: 120 }}
          >
            <Option value="7days">最近7天</Option>
            <Option value="30days">最近30天</Option>
            <Option value="90days">最近90天</Option>
          </Select>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
        </Space>
      </Card>

      {/* 关键指标卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总查询数"
              value={data.totalQueries}
              prefix={<SearchOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均响应时间"
              value={data.avgResponseTime}
              precision={2}
              suffix="s"
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃集合"
              value={data.activeCollections}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="独立用户"
              value={data.uniqueUsers}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表区域 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title="📈 查询趋势">
            <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Text type="secondary">图表组件待集成 (如 ECharts)</Text>
            </div>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="🥧 集合使用分布">
            <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Text type="secondary">图表组件待集成 (如 ECharts)</Text>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 详细日志表格 */}
      <Card title="📋 查询日志">
        <Table
          dataSource={data.recentLogs}
          columns={columns}
          rowKey="id"
          pagination={{ 
            pageSize: 20,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
          scroll={{ x: 800 }}
        />
      </Card>
    </div>
  );
};

export default AnalyticsTab;