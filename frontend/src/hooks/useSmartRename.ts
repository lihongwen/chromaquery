/**
 * 智能重命名Hook
 * 集成分析、进度显示和自动刷新功能
 */

import { useState, useCallback } from 'react';
import { message } from 'antd';
import apiClient from '../config/api';

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

interface RenameResult {
  success: boolean;
  message: string;
  task_id?: string;
  immediate_response?: boolean;
  background_processing?: boolean;
  note?: string;
}

export interface SmartRenameState {
  isAnalyzing: boolean;
  isRenaming: boolean;
  showProgress: boolean;
  analysis: CollectionAnalysis | null;
  taskId: string | null;
  error: string | null;
}

export const useSmartRename = () => {
  const [state, setState] = useState<SmartRenameState>({
    isAnalyzing: false,
    isRenaming: false,
    showProgress: false,
    analysis: null,
    taskId: null,
    error: null
  });

  /**
   * 分析集合
   */
  const analyzeCollection = useCallback(async (collectionName: string): Promise<CollectionAnalysis | null> => {
    setState(prev => ({ ...prev, isAnalyzing: true, error: null }));

    try {
      const response = await apiClient.get(`/collections/${encodeURIComponent(collectionName)}/analysis`);
      
      if (response.data.success) {
        const analysis = response.data.analysis;
        setState(prev => ({ ...prev, analysis, isAnalyzing: false }));
        return analysis;
      } else {
        throw new Error('分析失败');
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || '分析集合失败';
      setState(prev => ({ ...prev, error: errorMessage, isAnalyzing: false }));
      message.error(errorMessage);
      return null;
    }
  }, []);

  /**
   * 执行智能重命名
   */
  const performSmartRename = useCallback(async (
    oldName: string, 
    newName: string,
    onProgressShow?: () => void,
    onComplete?: () => void
  ): Promise<boolean> => {
    // 1. 先分析集合
    const analysis = await analyzeCollection(oldName);
    if (!analysis) {
      return false;
    }

    setState(prev => ({ ...prev, isRenaming: true, error: null }));

    try {
      // 2. 执行重命名
      const response = await apiClient.put('/collections/rename', {
        old_name: oldName,
        new_name: newName
      });

      if (response.data.success) {
        const result: RenameResult = response.data;
        
        setState(prev => ({
          ...prev,
          taskId: result.task_id || null,
          isRenaming: false
        }));

        // 3. 根据分析结果决定是否显示进度弹窗
        if (analysis.should_show_progress && result.task_id) {
          setState(prev => ({ ...prev, showProgress: true }));
          if (onProgressShow) {
            onProgressShow();
          }
        } else {
          // 简单任务，显示简单提示
          message.success(result.message);
          if (onComplete) {
            // 等待一下再调用完成回调，给后台一些处理时间
            setTimeout(onComplete, 2000);
          }
        }

        return true;
      } else {
        throw new Error('重命名失败');
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || '重命名失败';
      setState(prev => ({ ...prev, error: errorMessage, isRenaming: false }));
      message.error(errorMessage);
      return false;
    }
  }, [analyzeCollection]);

  /**
   * 关闭进度弹窗
   */
  const closeProgress = useCallback(() => {
    setState(prev => ({
      ...prev,
      showProgress: false,
      taskId: null,
      analysis: null
    }));
  }, []);

  /**
   * 重置状态
   */
  const reset = useCallback(() => {
    setState({
      isAnalyzing: false,
      isRenaming: false,
      showProgress: false,
      analysis: null,
      taskId: null,
      error: null
    });
  }, []);

  /**
   * 获取阈值说明
   */
  const getThresholdInfo = useCallback(() => {
    return {
      documentCount: 500,
      sizeMB: 10,
      processingTimeSeconds: 5,
      description: '当集合超过500条记录、10MB大小或预估处理时间超过5秒时，将显示详细进度弹窗'
    };
  }, []);

  /**
   * 判断是否应该显示进度
   */
  const shouldShowProgress = useCallback((analysis: CollectionAnalysis) => {
    return analysis.should_show_progress;
  }, []);

  return {
    state,
    analyzeCollection,
    performSmartRename,
    closeProgress,
    reset,
    getThresholdInfo,
    shouldShowProgress
  };
};
