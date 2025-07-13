import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import axios from 'axios';
import CollectionManager from './CollectionManager';
import CollectionDetail from './CollectionDetail';
import QueryPage from './QueryPage';

// API基础URL
const API_BASE_URL = '/api';

// 集合信息接口
interface CollectionInfo {
  name: string;
  display_name: string;
  count: number;
  metadata: Record<string, any>;
}

const AppRouter: React.FC = () => {
  const [hasCollections, setHasCollections] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();

  // 检测集合存在性
  const checkCollectionsExistence = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/collections`);
      const collections: CollectionInfo[] = response.data;
      setHasCollections(collections.length > 0);
    } catch (error) {
      console.error('检测集合存在性失败:', error);
      // 如果API调用失败，默认假设没有集合，引导用户到集合管理页面
      setHasCollections(false);
    } finally {
      setLoading(false);
    }
  };

  // 组件挂载时检测集合存在性
  useEffect(() => {
    checkCollectionsExistence();
  }, []);

  // 监听路由变化，当从集合管理页面离开时重新检测
  useEffect(() => {
    // 如果当前在集合管理页面，当路由变化时重新检测集合
    if (location.pathname === '/' && !loading) {
      checkCollectionsExistence();
    }
  }, [location.pathname, loading]);

  // 加载中状态
  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <Spin size="large" tip="正在检测系统状态..." />
      </div>
    );
  }

  return (
    <Routes>
      {/* 根路径的智能重定向 */}
      <Route
        path="/"
        element={
          hasCollections ? (
            <Navigate to="/query" replace />
          ) : (
            <Navigate to="/collections" replace />
          )
        }
      />

      {/* 集合管理页面 */}
      <Route path="/collections" element={<CollectionManager />} />
      
      {/* 集合详情页面 */}
      <Route path="/collections/:collectionName/detail" element={<CollectionDetail />} />
      
      {/* 智能查询页面 - 带集合存在性检查 */}
      <Route 
        path="/query" 
        element={
          <QueryPage hasCollections={hasCollections} onCollectionsChange={checkCollectionsExistence} />
        } 
      />
      
      {/* 其他路径重定向到根路径 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default AppRouter;
