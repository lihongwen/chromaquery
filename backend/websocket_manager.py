"""
WebSocket管理器
用于实时通知前端状态更新
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, asdict
import threading
import time

logger = logging.getLogger(__name__)

@dataclass
class WebSocketMessage:
    """WebSocket消息"""
    type: str
    data: Dict[str, Any]
    timestamp: str

class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃连接
        self.active_connections: List[WebSocket] = []
        self.connection_lock = threading.Lock()
        
        # 消息队列
        self.message_queue: List[WebSocketMessage] = []
        self.queue_lock = threading.Lock()
    
    async def connect(self, websocket: WebSocket):
        """接受WebSocket连接"""
        await websocket.accept()
        with self.connection_lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket连接已建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        with self.connection_lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket连接已断开，当前连接数: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"发送个人消息失败: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """广播消息给所有连接"""
        if not self.active_connections:
            return
        
        message_text = json.dumps(message, ensure_ascii=False)
        disconnected = []
        
        with self.connection_lock:
            connections = self.active_connections.copy()
        
        for connection in connections:
            try:
                await connection.send_text(message_text)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        if disconnected:
            with self.connection_lock:
                for conn in disconnected:
                    if conn in self.active_connections:
                        self.active_connections.remove(conn)
    
    def broadcast_sync(self, message: Dict[str, Any]):
        """同步广播消息（在非async环境中使用）"""
        if not self.active_connections:
            return
        
        # 将消息添加到队列，由异步任务处理
        with self.queue_lock:
            self.message_queue.append(WebSocketMessage(
                type=message.get('type', 'unknown'),
                data=message,
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
            ))
    
    async def process_message_queue(self):
        """处理消息队列"""
        while True:
            try:
                messages_to_send = []
                
                with self.queue_lock:
                    if self.message_queue:
                        messages_to_send = self.message_queue.copy()
                        self.message_queue.clear()
                
                for msg in messages_to_send:
                    await self.broadcast(msg.data)
                
                await asyncio.sleep(0.1)  # 100ms检查一次
                
            except Exception as e:
                logger.error(f"处理消息队列失败: {e}")
                await asyncio.sleep(1)
    
    def notify_rename_progress(self, task_id: str, progress: int, message: str, 
                             collection_name: str = "", estimated_remaining: int = 0):
        """通知重命名进度"""
        self.broadcast_sync({
            "type": "rename_progress",
            "task_id": task_id,
            "progress": progress,
            "message": message,
            "collection_name": collection_name,
            "estimated_remaining": estimated_remaining,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    def notify_rename_completed(self, task_id: str, old_name: str, new_name: str):
        """通知重命名完成"""
        self.broadcast_sync({
            "type": "rename_completed",
            "task_id": task_id,
            "old_name": old_name,
            "new_name": new_name,
            "message": f"集合 '{old_name}' 已成功重命名为 '{new_name}'",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    def notify_rename_failed(self, task_id: str, old_name: str, error_message: str):
        """通知重命名失败"""
        self.broadcast_sync({
            "type": "rename_failed",
            "task_id": task_id,
            "old_name": old_name,
            "error_message": error_message,
            "message": f"集合 '{old_name}' 重命名失败: {error_message}",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    def notify_collection_list_update(self):
        """通知集合列表需要更新"""
        self.broadcast_sync({
            "type": "collection_list_update",
            "message": "集合列表已更新，请刷新",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        })

# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()

def get_websocket_manager() -> WebSocketManager:
    """获取WebSocket管理器实例"""
    return websocket_manager
