/**
 * WebSocket服务
 * 用于实时通信和自动更新
 */

import { notification } from 'antd';

export interface WebSocketMessage {
  type: string;
  task_id?: string;
  old_name?: string;
  new_name?: string;
  progress?: number;
  message?: string;
  estimated_remaining?: number;
  error_message?: string;
  timestamp?: string;
}

export type MessageHandler = (message: WebSocketMessage) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 5000; // 5秒
  private messageHandlers: Map<string, MessageHandler[]> = new Map();
  private isConnecting = false;
  private shouldReconnect = true;

  constructor() {
    this.connect();
  }

  private connect() {
    if (this.isConnecting || this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isConnecting = true;

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/ws`;
      
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket连接已建立');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        
        // 发送心跳
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('解析WebSocket消息失败:', error);
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket连接已关闭:', event.code, event.reason);
        this.isConnecting = false;
        this.ws = null;

        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
          setTimeout(() => this.connect(), this.reconnectInterval);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket错误:', error);
        this.isConnecting = false;
      };

    } catch (error) {
      console.error('WebSocket连接失败:', error);
      this.isConnecting = false;
    }
  }

  private startHeartbeat() {
    const heartbeat = () => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
        setTimeout(heartbeat, 30000); // 30秒心跳
      }
    };
    heartbeat();
  }

  private handleMessage(message: WebSocketMessage) {
    console.log('收到WebSocket消息:', message);

    // 处理不同类型的消息
    switch (message.type) {
      case 'rename_progress':
        this.notifyHandlers('rename_progress', message);
        break;

      case 'rename_completed':
        this.notifyHandlers('rename_completed', message);
        this.notifyHandlers('collection_list_update', message);
        
        notification.success({
          message: '重命名完成',
          description: `集合 "${message.old_name}" 已成功重命名为 "${message.new_name}"`,
          duration: 4
        });
        break;

      case 'rename_failed':
        this.notifyHandlers('rename_failed', message);
        
        notification.error({
          message: '重命名失败',
          description: `集合 "${message.old_name}" 重命名失败: ${message.error_message}`,
          duration: 6
        });
        break;

      case 'collection_list_update':
        this.notifyHandlers('collection_list_update', message);
        break;

      case 'pong':
        // 心跳响应，不需要处理
        break;

      default:
        console.log('未知消息类型:', message.type);
    }
  }

  private notifyHandlers(type: string, message: WebSocketMessage) {
    const handlers = this.messageHandlers.get(type) || [];
    handlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error('消息处理器执行失败:', error);
      }
    });
  }

  /**
   * 订阅消息类型
   */
  public subscribe(type: string, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    
    this.messageHandlers.get(type)!.push(handler);

    // 返回取消订阅函数
    return () => {
      const handlers = this.messageHandlers.get(type);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index > -1) {
          handlers.splice(index, 1);
        }
      }
    };
  }

  /**
   * 发送消息
   */
  public send(message: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket未连接，无法发送消息');
    }
  }

  /**
   * 关闭连接
   */
  public close() {
    this.shouldReconnect = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * 获取连接状态
   */
  public getReadyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }

  /**
   * 是否已连接
   */
  public isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// 创建全局实例
const websocketService = new WebSocketService();

export default websocketService;

// 导出便捷的订阅函数
export const subscribeToRenameProgress = (handler: MessageHandler) => 
  websocketService.subscribe('rename_progress', handler);

export const subscribeToRenameCompleted = (handler: MessageHandler) => 
  websocketService.subscribe('rename_completed', handler);

export const subscribeToRenameFailed = (handler: MessageHandler) => 
  websocketService.subscribe('rename_failed', handler);

export const subscribeToCollectionListUpdate = (handler: MessageHandler) => 
  websocketService.subscribe('collection_list_update', handler);
