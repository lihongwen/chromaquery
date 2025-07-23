/**
 * 文件处理工具函数
 */

export interface FileFormatInfo {
  extension: string;
  description: string;
  category: 'text' | 'document' | 'presentation' | 'spreadsheet';
  isTable: boolean;
}

export const SUPPORTED_FORMATS: Record<string, FileFormatInfo> = {
  txt: {
    extension: '.txt',
    description: '纯文本文件',
    category: 'text',
    isTable: false
  },
  pdf: {
    extension: '.pdf',
    description: 'PDF文档',
    category: 'document',
    isTable: false
  },
  docx: {
    extension: '.docx',
    description: 'Word文档 (新格式)',
    category: 'document',
    isTable: false
  },
  doc: {
    extension: '.doc',
    description: 'Word文档 (旧格式)',
    category: 'document',
    isTable: false
  },
  pptx: {
    extension: '.pptx',
    description: 'PowerPoint演示文稿 (新格式)',
    category: 'presentation',
    isTable: false
  },
  ppt: {
    extension: '.ppt',
    description: 'PowerPoint演示文稿 (旧格式)',
    category: 'presentation',
    isTable: false
  },
  md: {
    extension: '.md',
    description: 'Markdown文档',
    category: 'text',
    isTable: false
  },
  rtf: {
    extension: '.rtf',
    description: '富文本格式文档',
    category: 'document',
    isTable: false
  },
  xlsx: {
    extension: '.xlsx',
    description: 'Excel工作簿 (新格式)',
    category: 'spreadsheet',
    isTable: true
  },
  xls: {
    extension: '.xls',
    description: 'Excel工作簿 (旧格式)',
    category: 'spreadsheet',
    isTable: true
  },
  csv: {
    extension: '.csv',
    description: '逗号分隔值文件',
    category: 'spreadsheet',
    isTable: true
  }
};

/**
 * 获取文件扩展名
 */
export function getFileExtension(filename: string): string {
  if (!filename) return '';
  const parts = filename.toLowerCase().split('.');
  return parts.length > 1 ? parts[parts.length - 1] : '';
}

/**
 * 检查文件是否支持
 */
export function isSupportedFile(filename: string): boolean {
  const extension = getFileExtension(filename);
  return extension in SUPPORTED_FORMATS;
}

/**
 * 获取文件格式信息
 */
export function getFileFormatInfo(filename: string): FileFormatInfo | null {
  const extension = getFileExtension(filename);
  return SUPPORTED_FORMATS[extension] || null;
}

/**
 * 检查是否为表格文件
 */
export function isTableFile(filename: string): boolean {
  const formatInfo = getFileFormatInfo(filename);
  return formatInfo?.isTable || false;
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 验证文件大小
 */
export function validateFileSize(file: File, maxSizeMB: number = 150): boolean {
  const maxSizeBytes = maxSizeMB * 1024 * 1024;
  return file.size <= maxSizeBytes;
}

/**
 * 获取文件类型的上传提示
 */
export function getUploadHint(filename: string): string {
  const formatInfo = getFileFormatInfo(filename);
  
  if (!formatInfo) {
    return '不支持的文件格式';
  }
  
  const hints: Record<string, string> = {
    text: '将提取纯文本内容进行分块处理',
    document: '将提取文档中的文本内容进行分块处理',
    presentation: '将提取幻灯片中的文本内容进行分块处理',
    spreadsheet: '将智能分析表格结构，每行数据作为一个文档块'
  };
  
  return hints[formatInfo.category] || '将进行文本提取和分块处理';
}

/**
 * 获取所有支持的文件扩展名
 */
export function getSupportedExtensions(): string[] {
  return Object.values(SUPPORTED_FORMATS).map(format => format.extension);
}

/**
 * 获取按类别分组的文件格式
 */
export function getFormatsByCategory(): Record<string, FileFormatInfo[]> {
  const categories: Record<string, FileFormatInfo[]> = {
    text: [],
    document: [],
    presentation: [],
    spreadsheet: []
  };
  
  Object.values(SUPPORTED_FORMATS).forEach(format => {
    categories[format.category].push(format);
  });
  
  return categories;
}

/**
 * 生成文件上传的accept属性
 */
export function generateAcceptString(): string {
  return getSupportedExtensions().join(',');
}
