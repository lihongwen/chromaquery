import axios from 'axios';
import { message } from 'antd';

// API基础配置
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    console.log(`API请求: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('请求拦截器错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    console.log(`API响应: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API响应错误:', error);
    
    // 统一错误处理
    if (error.response) {
      const { status, data } = error.response;
      let errorMessage = '请求失败';
      
      switch (status) {
        case 400:
          errorMessage = data?.detail || '请求参数错误';
          break;
        case 401:
          errorMessage = '未授权访问';
          break;
        case 403:
          errorMessage = '禁止访问';
          break;
        case 404:
          errorMessage = data?.detail || '资源不存在';
          break;
        case 500:
          errorMessage = data?.detail || '服务器内部错误';
          break;
        case 503:
          errorMessage = '服务不可用';
          break;
        default:
          errorMessage = data?.detail || `请求失败 (${status})`;
      }
      
      // 显示错误消息
      message.error(errorMessage);
    } else if (error.request) {
      // 网络错误
      message.error('网络连接失败，请检查网络设置');
    } else {
      // 其他错误
      message.error('请求配置错误');
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;

// 导出常用的API方法
export const api = {
  // 集合相关
  collections: {
    list: () => apiClient.get('/collections'),
    create: (data: { name: string; metadata?: any }) => apiClient.post('/collections', data),
    delete: (name: string) => apiClient.delete(`/collections/${encodeURIComponent(name)}`),
    rename: (data: { old_name: string; new_name: string }) => apiClient.put('/collections/rename', data),
    detail: (name: string, limit = 20) => apiClient.get(`/collections/${encodeURIComponent(name)}/detail?limit=${limit}`),
  },
  
  // 文档相关
  documents: {
    upload: (collectionName: string, formData: FormData) => 
      apiClient.post(`/collections/${encodeURIComponent(collectionName)}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }),
    delete: (collectionName: string, fileName: string) => 
      apiClient.delete(`/collections/${encodeURIComponent(collectionName)}/documents/${encodeURIComponent(fileName)}`),
  },
  
  // 查询相关
  query: {
    vector: (data: { query: string; collections: string[]; limit?: number }) => 
      apiClient.post('/query', data),
    llm: (data: { query: string; collections: string[]; limit?: number; temperature?: number; max_tokens?: number; similarity_threshold?: number }) =>
      fetch(`${API_BASE_URL}/llm-query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
  },
  
  // 健康检查
  health: () => apiClient.get('/health'),
  
  // 分块配置
  chunking: {
    config: (method: string) => apiClient.get(`/chunking/config/${method}`),
  },
};
