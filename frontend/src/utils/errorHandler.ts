/**
 * 错误处理工具
 */

import { message } from 'antd';

export interface ErrorInfo {
  code: string;
  message: string;
  details?: string;
  suggestions?: string[];
}

export const ERROR_CODES = {
  // 文件相关错误
  FILE_TOO_LARGE: 'FILE_TOO_LARGE',
  FILE_UNSUPPORTED: 'FILE_UNSUPPORTED',
  FILE_EMPTY: 'FILE_EMPTY',
  FILE_CORRUPTED: 'FILE_CORRUPTED',
  
  // 解析相关错误
  PARSE_FAILED: 'PARSE_FAILED',
  ENCODING_ERROR: 'ENCODING_ERROR',
  CONTENT_EMPTY: 'CONTENT_EMPTY',
  
  // 网络相关错误
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT_ERROR: 'TIMEOUT_ERROR',
  SERVER_ERROR: 'SERVER_ERROR',
  
  // 业务相关错误
  COLLECTION_NOT_FOUND: 'COLLECTION_NOT_FOUND',
  CHUNKING_FAILED: 'CHUNKING_FAILED',
  EMBEDDING_FAILED: 'EMBEDDING_FAILED',
} as const;

/**
 * 错误信息映射
 */
const ERROR_MESSAGES: Record<string, ErrorInfo> = {
  [ERROR_CODES.FILE_TOO_LARGE]: {
    code: ERROR_CODES.FILE_TOO_LARGE,
    message: '文件大小超过限制',
    details: '文件大小不能超过 150MB',
    suggestions: [
      '请选择较小的文件',
      '可以将大文件分割成多个小文件上传',
      '对于PDF文件，可以尝试压缩或删除不必要的图片'
    ]
  },
  
  [ERROR_CODES.FILE_UNSUPPORTED]: {
    code: ERROR_CODES.FILE_UNSUPPORTED,
    message: '不支持的文件格式',
    details: '当前只支持文本、PDF、Word、PowerPoint、Markdown、RTF、Excel、CSV格式',
    suggestions: [
      '请转换文件格式后重试',
      '对于图片文件，请先进行OCR文字识别',
      '对于其他格式，请导出为支持的格式'
    ]
  },
  
  [ERROR_CODES.FILE_EMPTY]: {
    code: ERROR_CODES.FILE_EMPTY,
    message: '文件为空',
    details: '选择的文件没有内容',
    suggestions: [
      '请检查文件是否正确',
      '确保文件包含有效内容'
    ]
  },
  
  [ERROR_CODES.FILE_CORRUPTED]: {
    code: ERROR_CODES.FILE_CORRUPTED,
    message: '文件已损坏',
    details: '无法正确读取文件内容',
    suggestions: [
      '请检查文件是否完整',
      '尝试重新下载或获取文件',
      '使用其他软件打开文件确认是否正常'
    ]
  },
  
  [ERROR_CODES.PARSE_FAILED]: {
    code: ERROR_CODES.PARSE_FAILED,
    message: '文件解析失败',
    details: '无法从文件中提取文本内容',
    suggestions: [
      '请确保文件格式正确',
      '对于PDF文件，确保不是扫描版（图片格式）',
      '对于Office文档，确保文件没有密码保护'
    ]
  },
  
  [ERROR_CODES.ENCODING_ERROR]: {
    code: ERROR_CODES.ENCODING_ERROR,
    message: '文件编码错误',
    details: '无法识别文件的字符编码',
    suggestions: [
      '请将文件保存为UTF-8编码',
      '对于中文文件，建议使用UTF-8或GBK编码'
    ]
  },
  
  [ERROR_CODES.CONTENT_EMPTY]: {
    code: ERROR_CODES.CONTENT_EMPTY,
    message: '文件内容为空',
    details: '文件中没有提取到有效的文本内容',
    suggestions: [
      '请确保文件包含文本内容',
      '对于PDF文件，确保不是纯图片格式',
      '对于表格文件，确保包含数据行'
    ]
  },
  
  [ERROR_CODES.NETWORK_ERROR]: {
    code: ERROR_CODES.NETWORK_ERROR,
    message: '网络连接失败',
    details: '无法连接到服务器',
    suggestions: [
      '请检查网络连接',
      '确认服务器是否正常运行',
      '稍后重试'
    ]
  },
  
  [ERROR_CODES.TIMEOUT_ERROR]: {
    code: ERROR_CODES.TIMEOUT_ERROR,
    message: '处理超时',
    details: '文件处理时间较长，可能仍在后台处理中',
    suggestions: [
      '大文件处理需要更长时间，请耐心等待',
      '您可以稍后刷新页面查看处理结果',
      '如果持续超时，请尝试分割文件后重新上传'
    ]
  },
  
  [ERROR_CODES.SERVER_ERROR]: {
    code: ERROR_CODES.SERVER_ERROR,
    message: '服务器内部错误',
    details: '服务器处理请求时发生错误',
    suggestions: [
      '请稍后重试',
      '如果问题持续存在，请联系管理员'
    ]
  },
  
  [ERROR_CODES.COLLECTION_NOT_FOUND]: {
    code: ERROR_CODES.COLLECTION_NOT_FOUND,
    message: '集合不存在',
    details: '指定的集合未找到',
    suggestions: [
      '请确认集合名称是否正确',
      '检查集合是否已被删除'
    ]
  },
  
  [ERROR_CODES.CHUNKING_FAILED]: {
    code: ERROR_CODES.CHUNKING_FAILED,
    message: '文档分块失败',
    details: '无法将文档分割成合适的块',
    suggestions: [
      '尝试调整分块参数',
      '检查文档内容是否过于复杂',
      '使用不同的分块方式'
    ]
  },
  
  [ERROR_CODES.EMBEDDING_FAILED]: {
    code: ERROR_CODES.EMBEDDING_FAILED,
    message: '向量生成失败',
    details: '无法为文档生成嵌入向量',
    suggestions: [
      '检查嵌入模型服务是否正常',
      '确认API密钥是否有效',
      '稍后重试'
    ]
  }
};

/**
 * 解析错误信息
 */
export function parseError(error: any): ErrorInfo {
  // 如果是HTTP错误响应
  if (error.response) {
    const { status, data } = error.response;
    const detail = data?.detail || data?.message || '';
    
    // 根据状态码和错误信息判断错误类型
    if (status === 400) {
      if (detail.includes('文件大小') || detail.includes('file size')) {
        return ERROR_MESSAGES[ERROR_CODES.FILE_TOO_LARGE];
      }
      if (detail.includes('格式') || detail.includes('format')) {
        return ERROR_MESSAGES[ERROR_CODES.FILE_UNSUPPORTED];
      }
      if (detail.includes('解析') || detail.includes('parse')) {
        return ERROR_MESSAGES[ERROR_CODES.PARSE_FAILED];
      }
      if (detail.includes('编码') || detail.includes('encoding')) {
        return ERROR_MESSAGES[ERROR_CODES.ENCODING_ERROR];
      }
      if (detail.includes('内容为空') || detail.includes('empty')) {
        return ERROR_MESSAGES[ERROR_CODES.CONTENT_EMPTY];
      }
    }
    
    if (status === 404) {
      return ERROR_MESSAGES[ERROR_CODES.COLLECTION_NOT_FOUND];
    }
    
    if (status >= 500) {
      return ERROR_MESSAGES[ERROR_CODES.SERVER_ERROR];
    }
    
    // 通用错误
    return {
      code: 'UNKNOWN_ERROR',
      message: detail || '未知错误',
      details: `HTTP ${status}: ${detail}`
    };
  }
  
  // 网络错误
  if (error.code === 'NETWORK_ERROR' || error.message?.includes('Network Error')) {
    return ERROR_MESSAGES[ERROR_CODES.NETWORK_ERROR];
  }
  
  // 超时错误
  if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
    return ERROR_MESSAGES[ERROR_CODES.TIMEOUT_ERROR];
  }
  
  // 默认错误
  return {
    code: 'UNKNOWN_ERROR',
    message: error.message || '未知错误',
    details: error.toString()
  };
}

/**
 * 显示错误消息
 */
export function showError(error: any, duration: number = 5) {
  const errorInfo = parseError(error);

  // 构建错误消息内容
  let content = errorInfo.message;
  if (errorInfo.details) {
    content += `\n${errorInfo.details}`;
  }
  if (errorInfo.suggestions && errorInfo.suggestions.length > 0) {
    content += `\n建议：${errorInfo.suggestions[0]}`;
  }

  message.error(content, duration);
}

/**
 * 显示详细错误信息（用于模态框）
 */
export function getDetailedErrorMessage(error: any): {
  title: string;
  content: string;
} {
  const errorInfo = parseError(error);

  let content = '';

  if (errorInfo.details) {
    content += `详细信息：\n${errorInfo.details}\n\n`;
  }

  if (errorInfo.suggestions && errorInfo.suggestions.length > 0) {
    content += '解决建议：\n';
    errorInfo.suggestions.forEach((suggestion, index) => {
      content += `${index + 1}. ${suggestion}\n`;
    });
  }

  return {
    title: errorInfo.message,
    content: content.trim()
  };
}
