# ChromaDB Web Manager WebUI设计规范

## 🎯 项目概述

基于现有ChromaDB Web Manager项目，重新设计前端界面，采用Claudia的设计风格和交互模式。保持现有的技术栈和后端API不变，专注于前端界面的视觉和交互体验改造。

## 🎨 技术栈保持

### 现有技术栈 (保持不变)
- **后端**: FastAPI + ChromaDB
- **前端**: React 18 + TypeScript + Vite
- **UI框架**: Ant Design (保持使用)
- **状态管理**: React Context/useState
- **样式**: CSS + Ant Design主题定制
- **图标**: Ant Design Icons
- **构建工具**: Vite

### 设计改造策略
- **保持**: Ant Design组件库和API
- **改造**: 视觉风格、布局结构、交互模式
- **新增**: 主题系统、标签页管理、聊天界面
- **优化**: 用户体验和界面流程

## 🏗️ 整体布局重新设计

### 1. 从单页面到标签页系统
```
当前布局 (单页面):
┌─────────────────────────────────────────────────────────────┐
│                    Header                                   │
├─────────────────────────────────────────────────────────────┤
│                  Main Content                               │
│            (Collection Management)                          │
│                      或                                     │
│             (Intelligent Query)                             │
└─────────────────────────────────────────────────────────────┘

新布局 (标签页系统):
┌─────────────────────────────────────────────────────────────┐
│                    Header                                   │
├─────────────────────────────────────────────────────────────┤
│ [📁 Collections] [🔍 Query] [📊 Analytics] [⚙️ Settings]    │
├─────────────────────────────────────────────────────────────┤
│ Sidebar │                Tab Content                        │
│ (可收缩)  │              (根据标签显示)                        │
└─────────────────────────────────────────────────────────────┘
```

### 2. Header重新设计
```
┌─────────────────────────────────────────────────────────────┐
│ 🗄️ ChromaDB Manager    🔍 [Search...]    🔔 🌙 👤          │
│ 📍 Collections > AI_Documents                               │
└─────────────────────────────────────────────────────────────┘
```

**Header组件结构**:
- **左侧**: Logo + 应用名称 + 面包屑导航
- **中间**: 全局搜索框 (搜索集合、文档、查询历史)
- **右侧**: 通知图标 + 主题切换 + 用户菜单

### 3. 标签页系统设计
使用Ant Design的`Tabs`组件，定制样式：
```typescript
<Tabs 
  type="editable-card"
  activeKey={activeTab}
  onChange={setActiveTab}
  items={[
    { key: 'collections', label: '📁 Collections', children: <CollectionsTab /> },
    { key: 'query', label: '🔍 Query', children: <QueryTab /> },
    { key: 'analytics', label: '📊 Analytics', children: <AnalyticsTab /> },
    { key: 'settings', label: '⚙️ Settings', children: <SettingsTab /> }
  ]}
/>
```

## 📱 各标签页详细设计

### 1. Collections标签页 (重新设计)

#### 左侧边栏 (新增)
使用Ant Design的`Sider`组件：
```
┌─────────────────┐
│ 📊 Overview     │  ← Collapse/Menu组件
│ ⭐ Favorites    │
│ 🕒 Recent       │
│ 🏷️ Tags         │
│ ─────────────── │
│ 📁 Collections  │  ← Tree组件
│   └ collection1 │
│   └ collection2 │
│ ─────────────── │
│ ⚡ Quick Actions│  ← Button组件
│   └ New Coll.  │
│   └ Import     │
└─────────────────┘
```

#### 主内容区域重新设计
**概览模式**:
```typescript
// 使用Ant Design的Statistic组件
<Row gutter={16}>
  <Col span={6}>
    <Card>
      <Statistic title="总集合数" value={12} prefix={<DatabaseOutlined />} />
    </Card>
  </Col>
  <Col span={6}>
    <Card>
      <Statistic title="总文档数" value={1234} prefix={<FileTextOutlined />} />
    </Card>
  </Col>
  // ... 其他统计卡片
</Row>

// 搜索和过滤栏
<Space.Compact style={{ width: '100%' }}>
  <Input.Search placeholder="搜索集合..." />
  <Select placeholder="标签筛选" />
  <DatePicker.RangePicker />
</Space.Compact>

// 集合网格视图
<Row gutter={[16, 16]}>
  {collections.map(collection => (
    <Col span={8} key={collection.id}>
      <Card
        title={collection.name}
        extra={<StarOutlined />}
        actions={[
          <EyeOutlined key="view" />,
          <SettingOutlined key="setting" />,
          <DeleteOutlined key="delete" />
        ]}
      >
        <Statistic title="文档数" value={collection.count} />
        <Tag color="blue">{collection.dimension}维</Tag>
        <Text type="secondary">{collection.updated_at}</Text>
      </Card>
    </Col>
  ))}
</Row>
```

**集合详情模式**:
```typescript
// 面包屑导航
<Breadcrumb>
  <Breadcrumb.Item><ArrowLeftOutlined /> Collections</Breadcrumb.Item>
  <Breadcrumb.Item>{collection.name}</Breadcrumb.Item>
</Breadcrumb>

// 集合信息面板
<Descriptions bordered>
  <Descriptions.Item label="文档数">{collection.count}</Descriptions.Item>
  <Descriptions.Item label="维度">{collection.dimension}</Descriptions.Item>
  <Descriptions.Item label="创建时间">{collection.created_at}</Descriptions.Item>
</Descriptions>

// 文档表格
<Table
  dataSource={documents}
  columns={[
    { title: 'ID', dataIndex: 'id' },
    { title: '内容预览', dataIndex: 'content', ellipsis: true },
    { title: '元数据', dataIndex: 'metadata', render: (meta) => <Tag>{JSON.stringify(meta)}</Tag> },
    { title: '操作', render: (_, record) => (
      <Space>
        <Button icon={<EyeOutlined />} size="small" />
        <Button icon={<EditOutlined />} size="small" />
        <Button icon={<DeleteOutlined />} size="small" danger />
      </Space>
    )}
  ]}
  pagination={{ pageSize: 10 }}
/>
```

### 2. Query标签页 (重新设计为聊天界面)

#### 布局结构
```typescript
<Layout>
  <Sider width={300} theme="light">
    {/* 查询历史侧边栏 */}
    <div className="query-sidebar">
      <Collapse defaultActiveKey={['history']}>
        <Panel header="📝 查询历史" key="history">
          <List
            dataSource={queryHistory}
            renderItem={item => (
              <List.Item>
                <List.Item.Meta
                  title={item.query}
                  description={item.timestamp}
                />
              </List.Item>
            )}
          />
        </Panel>
        <Panel header="⭐ 收藏查询" key="saved">
          {/* 收藏的查询列表 */}
        </Panel>
        <Panel header="⚙️ 查询设置" key="settings">
          <Form layout="vertical">
            <Form.Item label="相似度阈值">
              <Slider min={0} max={1} step={0.1} defaultValue={0.7} />
            </Form.Item>
            <Form.Item label="返回结果数">
              <InputNumber min={1} max={100} defaultValue={10} />
            </Form.Item>
          </Form>
        </Panel>
      </Collapse>
    </div>
  </Sider>
  
  <Content>
    {/* 聊天界面主体 */}
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map(message => (
          <div key={message.id} className={`message ${message.type}`}>
            <Avatar icon={message.type === 'user' ? <UserOutlined /> : <RobotOutlined />} />
            <div className="message-content">
              <div className="message-text">{message.content}</div>
              {message.results && (
                <div className="query-results">
                  <Alert
                    message={`找到 ${message.results.length} 个相关文档`}
                    type="success"
                    showIcon
                  />
                  <List
                    dataSource={message.results}
                    renderItem={result => (
                      <List.Item>
                        <List.Item.Meta
                          title={`相似度: ${result.distance}`}
                          description={result.content}
                        />
                        <Space>
                          <Button size="small" icon={<EyeOutlined />}>查看</Button>
                          <Button size="small" icon={<CopyOutlined />}>复制</Button>
                        </Space>
                      </List.Item>
                    )}
                  />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      
      <div className="chat-input">
        <Input.Search
          placeholder="输入您的查询..."
          enterButton={<SendOutlined />}
          size="large"
          onSearch={handleQuery}
          loading={loading}
        />
      </div>
    </div>
  </Content>
</Layout>
```

### 3. Analytics标签页 (全新设计)

#### 仪表板布局
```typescript
// 时间范围选择器
<Card>
  <Space>
    <DatePicker.RangePicker />
    <Select defaultValue="7days">
      <Option value="7days">最近7天</Option>
      <Option value="30days">最近30天</Option>
      <Option value="90days">最近90天</Option>
    </Select>
    <Button icon={<ReloadOutlined />}>刷新</Button>
  </Space>
</Card>

// 关键指标卡片
<Row gutter={16}>
  <Col span={6}>
    <Card>
      <Statistic
        title="总查询数"
        value={1234}
        prefix={<SearchOutlined />}
        suffix={<Badge count={"+12.5%"} style={{ backgroundColor: '#52c41a' }} />}
      />
    </Card>
  </Col>
  <Col span={6}>
    <Card>
      <Statistic
        title="平均响应时间"
        value={0.23}
        precision={2}
        suffix="s"
        prefix={<ClockCircleOutlined />}
      />
    </Card>
  </Col>
  // ... 其他指标
</Row>

// 图表区域 (需要集成图表库，如echarts-for-react)
<Row gutter={16}>
  <Col span={12}>
    <Card title="📈 查询趋势">
      {/* 折线图 */}
      <div style={{ height: 300 }}>
        {/* 这里需要集成图表组件 */}
      </div>
    </Card>
  </Col>
  <Col span={12}>
    <Card title="🥧 集合使用分布">
      {/* 饼图 */}
      <div style={{ height: 300 }}>
        {/* 这里需要集成图表组件 */}
      </div>
    </Card>
  </Col>
</Row>

// 详细日志表格
<Card title="📋 查询日志">
  <Table
    dataSource={queryLogs}
    columns={[
      { title: '时间', dataIndex: 'timestamp', sorter: true },
      { title: '查询内容', dataIndex: 'query', ellipsis: true },
      { title: '集合', dataIndex: 'collection' },
      { title: '结果数', dataIndex: 'results_count' },
      { title: '响应时间', dataIndex: 'response_time', suffix: 'ms' },
      { title: '状态', dataIndex: 'status', render: (status) => (
        <Tag color={status === 'success' ? 'green' : 'red'}>{status}</Tag>
      )}
    ]}
    pagination={{ pageSize: 20 }}
  />
</Card>
```

### 4. Settings标签页 (重新组织)

#### 设置分类导航
```typescript
<Layout>
  <Sider width={200} theme="light">
    <Menu mode="inline" defaultSelectedKeys={['connection']}>
      <Menu.Item key="connection" icon={<LinkOutlined />}>
        连接设置
      </Menu.Item>
      <Menu.Item key="theme" icon={<BgColorsOutlined />}>
        主题外观
      </Menu.Item>
      <Menu.Item key="notifications" icon={<BellOutlined />}>
        通知设置
      </Menu.Item>
      <Menu.Item key="security" icon={<SafetyOutlined />}>
        安全设置
      </Menu.Item>
      <Menu.Item key="advanced" icon={<SettingOutlined />}>
        高级设置
      </Menu.Item>
      <Menu.Item key="about" icon={<InfoCircleOutlined />}>
        关于
      </Menu.Item>
    </Menu>
  </Sider>

  <Content style={{ padding: 24 }}>
    {/* 根据选中的菜单项显示不同的设置面板 */}
    {selectedSetting === 'connection' && (
      <Card title="🔗 ChromaDB连接设置">
        <Form layout="vertical">
          <Form.Item label="服务器地址" required>
            <Input placeholder="http://localhost:8000" />
          </Form.Item>
          <Form.Item label="连接超时">
            <InputNumber addonAfter="秒" defaultValue={30} />
          </Form.Item>
          <Form.Item label="最大重试次数">
            <InputNumber defaultValue={3} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary">测试连接</Button>
              <Button>保存设置</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    )}

    {selectedSetting === 'theme' && (
      <Card title="🎨 主题外观设置">
        <Form layout="vertical">
          <Form.Item label="主题模式">
            <Radio.Group defaultValue="light">
              <Radio.Button value="light">🌞 浅色</Radio.Button>
              <Radio.Button value="dark">🌙 深色</Radio.Button>
              <Radio.Button value="auto">🔄 自动</Radio.Button>
            </Radio.Group>
          </Form.Item>
          <Form.Item label="主色调">
            <Space>
              <div className="color-picker">
                {/* 颜色选择器 */}
              </div>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    )}
  </Content>
</Layout>
```

## 🎨 视觉设计定制

### 1. Ant Design主题定制
```typescript
// theme.ts
import { theme } from 'antd';

export const lightTheme = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#3b82f6',      // 主色调
    colorSuccess: '#10b981',      // 成功色
    colorWarning: '#f59e0b',      // 警告色
    colorError: '#ef4444',        // 错误色
    colorInfo: '#06b6d4',         // 信息色
    borderRadius: 8,              // 圆角
    fontSize: 14,                 // 字体大小
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
  components: {
    Card: {
      borderRadius: 12,
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
    },
    Button: {
      borderRadius: 8,
    },
    Input: {
      borderRadius: 8,
    },
    Table: {
      borderRadius: 8,
    },
    Tabs: {
      cardBg: '#ffffff',
    }
  }
};

export const darkTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#60a5fa',
    colorBgBase: '#0f172a',
    colorBgContainer: '#1e293b',
    // ... 其他深色主题配置
  }
};
```

### 2. 自定义CSS样式
```css
/* styles/custom.css */

/* 标签页样式定制 */
.ant-tabs-card > .ant-tabs-content {
  height: calc(100vh - 120px);
  overflow: auto;
}

.ant-tabs-card .ant-tabs-tab {
  border-radius: 8px 8px 0 0;
  border: none;
  background: #f8fafc;
}

.ant-tabs-card .ant-tabs-tab-active {
  background: #ffffff;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.06);
}

/* 聊天界面样式 */
.chat-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.message {
  display: flex;
  margin-bottom: 16px;
  align-items: flex-start;
}

.message.user {
  flex-direction: row-reverse;
}

.message.user .message-content {
  background: #3b82f6;
  color: white;
  margin-right: 8px;
}

.message.assistant .message-content {
  background: #f1f5f9;
  margin-left: 8px;
}

.message-content {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
}

.chat-input {
  padding: 16px;
  border-top: 1px solid #e2e8f0;
}

/* 集合卡片样式 */
.collection-card {
  transition: all 0.3s ease;
  cursor: pointer;
}

.collection-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

/* 统计卡片样式 */
.stats-card .ant-statistic-title {
  color: #6b7280;
  font-weight: 500;
}

.stats-card .ant-statistic-content {
  color: #1f2937;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .ant-layout-sider {
    position: fixed;
    height: 100vh;
    z-index: 999;
  }

  .chat-messages {
    padding: 8px;
  }

  .message-content {
    max-width: 85%;
  }
}

/* 深色主题样式 */
[data-theme='dark'] {
  .chat-input {
    border-top-color: #334155;
  }

  .message.assistant .message-content {
    background: #334155;
    color: #f1f5f9;
  }

  .collection-card:hover {
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
  }
}
```

### 3. 主题切换实现
```typescript
// hooks/useTheme.ts
import { useState, useEffect } from 'react';
import { theme } from 'antd';

export const useTheme = () => {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      setIsDark(savedTheme === 'dark');
    } else {
      // 检测系统主题
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setIsDark(prefersDark);
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = !isDark;
    setIsDark(newTheme);
    localStorage.setItem('theme', newTheme ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', newTheme ? 'dark' : 'light');
  };

  return {
    isDark,
    toggleTheme,
    themeConfig: isDark ? darkTheme : lightTheme
  };
};
```

## 🔧 组件重构指南

### 1. 现有组件改造
```typescript
// 原有的AppRouter.tsx 改造为 TabManager.tsx
const TabManager: React.FC = () => {
  const [activeTab, setActiveTab] = useState('collections');

  const tabItems = [
    {
      key: 'collections',
      label: (
        <span>
          <DatabaseOutlined />
          Collections
        </span>
      ),
      children: <CollectionsTab />
    },
    {
      key: 'query',
      label: (
        <span>
          <SearchOutlined />
          Query
        </span>
      ),
      children: <QueryTab />
    },
    {
      key: 'analytics',
      label: (
        <span>
          <BarChartOutlined />
          Analytics
        </span>
      ),
      children: <AnalyticsTab />
    },
    {
      key: 'settings',
      label: (
        <span>
          <SettingOutlined />
          Settings
        </span>
      ),
      children: <SettingsTab />
    }
  ];

  return (
    <Tabs
      type="card"
      activeKey={activeTab}
      onChange={setActiveTab}
      items={tabItems}
      className="main-tabs"
    />
  );
};
```

### 2. 新增组件开发
```typescript
// components/GlobalSearch.tsx
const GlobalSearch: React.FC = () => {
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (value: string) => {
    if (!value.trim()) return;

    setLoading(true);
    try {
      // 搜索集合、文档、查询历史
      const results = await Promise.all([
        searchCollections(value),
        searchDocuments(value),
        searchQueryHistory(value)
      ]);

      setSearchResults(results.flat());
    } catch (error) {
      message.error('搜索失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AutoComplete
      style={{ width: 400 }}
      options={searchResults}
      onSearch={handleSearch}
      placeholder="搜索集合、文档、查询历史..."
    >
      <Input.Search
        size="middle"
        loading={loading}
        prefix={<SearchOutlined />}
      />
    </AutoComplete>
  );
};

// components/ConnectionStatus.tsx
const ConnectionStatus: React.FC = () => {
  const [status, setStatus] = useState<'connected' | 'disconnected' | 'connecting'>('connecting');

  useEffect(() => {
    // 检查连接状态
    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkConnection = async () => {
    try {
      await fetch('/api/health');
      setStatus('connected');
    } catch {
      setStatus('disconnected');
    }
  };

  const statusConfig = {
    connected: { color: 'green', text: '已连接', icon: <CheckCircleOutlined /> },
    disconnected: { color: 'red', text: '连接断开', icon: <CloseCircleOutlined /> },
    connecting: { color: 'orange', text: '连接中', icon: <LoadingOutlined /> }
  };

  const config = statusConfig[status];

  return (
    <Badge color={config.color} text={config.text}>
      {config.icon}
    </Badge>
  );
};
```

## 📱 响应式设计实现

### 1. 断点配置
```typescript
// utils/responsive.ts
export const breakpoints = {
  xs: 0,
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  xxl: 1600,
};

export const useResponsive = () => {
  const [screenSize, setScreenSize] = useState('lg');

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      if (width < breakpoints.sm) setScreenSize('xs');
      else if (width < breakpoints.md) setScreenSize('sm');
      else if (width < breakpoints.lg) setScreenSize('md');
      else if (width < breakpoints.xl) setScreenSize('lg');
      else setScreenSize('xl');
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return {
    screenSize,
    isMobile: screenSize === 'xs' || screenSize === 'sm',
    isTablet: screenSize === 'md',
    isDesktop: screenSize === 'lg' || screenSize === 'xl'
  };
};
```

### 2. 响应式布局
```typescript
// 在各个组件中使用响应式设计
const CollectionsTab: React.FC = () => {
  const { isMobile, isTablet } = useResponsive();

  return (
    <Layout>
      {!isMobile && (
        <Sider width={250} theme="light" collapsible>
          {/* 侧边栏内容 */}
        </Sider>
      )}

      <Content>
        <Row gutter={[16, 16]}>
          {collections.map(collection => (
            <Col
              key={collection.id}
              xs={24}      // 手机端：1列
              sm={12}      // 小屏：2列
              md={8}       // 中屏：3列
              lg={6}       // 大屏：4列
              xl={4}       // 超大屏：6列
            >
              <CollectionCard collection={collection} />
            </Col>
          ))}
        </Row>
      </Content>
    </Layout>
  );
};
```

## 🚀 实施计划

### Phase 1: 基础架构改造 (1周)
1. **主题系统实现**
   - 创建主题配置文件
   - 实现主题切换功能
   - 定制Ant Design主题

2. **布局结构重构**
   - 实现标签页系统
   - 重新设计Header组件
   - 添加全局搜索功能

### Phase 2: 核心页面改造 (2周)
1. **Collections页面**
   - 添加侧边栏导航
   - 重新设计集合卡片
   - 实现集合详情页面

2. **Query页面**
   - 改造为聊天界面
   - 实现查询历史管理
   - 优化结果展示

### Phase 3: 新功能开发 (1周)
1. **Analytics页面**
   - 设计统计仪表板
   - 集成图表组件
   - 实现数据可视化

2. **Settings页面**
   - 重新组织设置分类
   - 实现各种设置功能
   - 添加导入导出功能

### Phase 4: 优化完善 (1周)
1. **响应式优化**
   - 移动端适配
   - 平板端优化
   - 交互体验优化

2. **性能优化**
   - 组件懒加载
   - 状态管理优化
   - 缓存策略实现

## 🔍 技术实现要点

### 1. 保持API兼容性
- 不修改现有FastAPI后端接口
- 保持现有数据结构和响应格式
- 仅在前端进行界面和交互改造

### 2. 渐进式改造
- 保持现有功能完整性
- 逐步替换界面组件
- 确保向后兼容性

### 3. 性能考虑
- 使用Ant Design的虚拟滚动
- 实现组件级别的懒加载
- 优化大数据集的渲染性能

### 4. 用户体验
- 保持操作习惯的连续性
- 添加加载状态和错误处理
- 实现平滑的页面过渡动画

这个设计规范提供了完整的ChromaDB Web Manager前端改造指导，在保持现有技术栈的基础上，全面采用Claudia的设计风格和交互模式，提升用户体验和界面现代化程度。
