/**
 * 文件上传进度估算工具
 */

export interface ProgressEstimate {
  estimatedTimeSeconds: number;
  incrementPerSecond: number;
  stages: ProgressStage[];
}

export interface ProgressStage {
  name: string;
  startPercent: number;
  endPercent: number;
  message: string;
  estimatedDuration: number; // 秒
}

/**
 * 根据文件大小和类型估算处理时间
 */
export function estimateProcessingTime(fileSize: number, fileName: string): ProgressEstimate {
  const fileSizeMB = fileSize / (1024 * 1024);
  const fileExtension = fileName.toLowerCase().split('.').pop() || '';
  
  // 基础处理时间（秒）
  let baseTime = 10; // 最少10秒
  
  // 根据文件大小调整时间
  if (fileSizeMB <= 1) {
    baseTime = 10;
  } else if (fileSizeMB <= 10) {
    baseTime = 20 + fileSizeMB * 2;
  } else if (fileSizeMB <= 50) {
    baseTime = 40 + fileSizeMB * 3;
  } else {
    baseTime = 60 + fileSizeMB * 4;
  }
  
  // 根据文件类型调整时间
  const typeMultipliers: Record<string, number> = {
    'txt': 0.5,
    'md': 0.5,
    'csv': 0.7,
    'pdf': 1.5,
    'docx': 1.2,
    'doc': 1.3,
    'pptx': 1.4,
    'ppt': 1.5,
    'xlsx': 1.1,
    'xls': 1.2,
    'rtf': 1.0
  };
  
  const multiplier = typeMultipliers[fileExtension] || 1.0;
  const estimatedTime = Math.min(300, Math.max(10, baseTime * multiplier)); // 10秒到5分钟
  
  // 定义处理阶段
  const stages: ProgressStage[] = [
    {
      name: 'uploading',
      startPercent: 0,
      endPercent: 15,
      message: '正在上传文件...',
      estimatedDuration: estimatedTime * 0.1
    },
    {
      name: 'processing',
      startPercent: 15,
      endPercent: 35,
      message: '正在解析文件内容...',
      estimatedDuration: estimatedTime * 0.25
    },
    {
      name: 'chunking',
      startPercent: 35,
      endPercent: 65,
      message: '正在进行RAG分块处理...',
      estimatedDuration: estimatedTime * 0.35
    },
    {
      name: 'embedding',
      startPercent: 65,
      endPercent: 90,
      message: '正在生成向量嵌入并存储...',
      estimatedDuration: estimatedTime * 0.3
    }
  ];
  
  return {
    estimatedTimeSeconds: estimatedTime,
    incrementPerSecond: 85 / estimatedTime, // 85%用于处理过程
    stages
  };
}

/**
 * 获取当前应该显示的阶段
 */
export function getCurrentStage(progress: number, stages: ProgressStage[]): ProgressStage | null {
  for (const stage of stages) {
    if (progress >= stage.startPercent && progress < stage.endPercent) {
      return stage;
    }
  }
  return stages[stages.length - 1] || null;
}

/**
 * 格式化剩余时间
 */
export function formatRemainingTime(seconds: number): string {
  if (seconds < 60) {
    return `约 ${Math.ceil(seconds)} 秒`;
  } else if (seconds < 3600) {
    const minutes = Math.ceil(seconds / 60);
    return `约 ${minutes} 分钟`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.ceil((seconds % 3600) / 60);
    return `约 ${hours} 小时 ${minutes} 分钟`;
  }
}

/**
 * 获取文件类型的处理提示
 */
export function getProcessingHint(fileName: string): string {
  const fileExtension = fileName.toLowerCase().split('.').pop() || '';
  
  const hints: Record<string, string> = {
    'pdf': 'PDF文件需要提取文本内容，处理时间较长',
    'docx': 'Word文档需要解析格式，请耐心等待',
    'doc': '旧版Word文档处理时间较长',
    'pptx': 'PowerPoint文件需要提取幻灯片内容',
    'ppt': '旧版PowerPoint文件处理时间较长',
    'xlsx': 'Excel文件将按行处理数据',
    'xls': '旧版Excel文件处理时间较长',
    'txt': '纯文本文件处理速度较快',
    'md': 'Markdown文件处理速度较快',
    'csv': 'CSV文件将按行处理数据',
    'rtf': 'RTF文件需要解析格式'
  };
  
  return hints[fileExtension] || '正在处理文件，请耐心等待';
}
