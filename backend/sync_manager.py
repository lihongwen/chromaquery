"""
前后端同步管理器
确保前端显示状态与后端数据状态实时同步
"""

import json
import logging
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import chromadb

from consistency_manager import StateValidator, ConsistencyReport

logger = logging.getLogger(__name__)

@dataclass
class SyncEvent:
    """同步事件"""
    event_id: str
    event_type: str  # 'collection_created', 'collection_deleted', 'collection_renamed', 'data_changed'
    collection_name: str
    timestamp: str
    details: Dict[str, Any]

@dataclass
class SyncState:
    """同步状态"""
    last_sync: str
    frontend_collections: Set[str]
    backend_collections: Set[str]
    sync_status: str  # 'synced', 'out_of_sync', 'syncing'
    pending_events: List[SyncEvent]

class SyncManager:
    """前后端同步管理器"""
    
    def __init__(self, chroma_path: Path, client: chromadb.PersistentClient):
        self.chroma_path = chroma_path
        self.client = client
        self.validator = StateValidator(chroma_path, client)
        
        # 同步状态
        self.sync_state = SyncState(
            last_sync=datetime.now().isoformat(),
            frontend_collections=set(),
            backend_collections=set(),
            sync_status='synced',
            pending_events=[]
        )
        
        # 事件监听器
        self.event_listeners: List[Callable] = []
        
        # 同步锁
        self._sync_lock = threading.Lock()
        
        # 启动同步监控
        self._start_sync_monitor()
    
    def register_event_listener(self, listener: Callable[[SyncEvent], None]):
        """注册事件监听器"""
        self.event_listeners.append(listener)
    
    def _start_sync_monitor(self):
        """启动同步监控"""
        def monitor_loop():
            while True:
                try:
                    self._check_sync_status()
                    threading.Event().wait(30)  # 每30秒检查一次
                except Exception as e:
                    logger.error(f"同步监控异常: {e}")
                    threading.Event().wait(60)  # 出错时等待更长时间
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def _check_sync_status(self):
        """检查同步状态"""
        try:
            with self._sync_lock:
                # 获取当前状态
                current_backend = self._get_current_backend_collections()
                
                # 检查是否有变化
                if current_backend != self.sync_state.backend_collections:
                    logger.info("检测到后端集合变化")
                    self._handle_backend_changes(current_backend)
                
                # 更新同步时间
                self.sync_state.last_sync = datetime.now().isoformat()
                
        except Exception as e:
            logger.error(f"检查同步状态失败: {e}")
    
    def _get_current_backend_collections(self) -> Set[str]:
        """获取当前后端集合"""
        try:
            collections = self.client.list_collections()
            return {
                col.metadata.get('original_name', col.name) 
                for col in collections 
                if col.metadata
            }
        except Exception as e:
            logger.error(f"获取后端集合失败: {e}")
            return set()
    
    def _handle_backend_changes(self, current_backend: Set[str]):
        """处理后端变化"""
        old_backend = self.sync_state.backend_collections
        
        # 检测新增的集合
        added_collections = current_backend - old_backend
        for collection_name in added_collections:
            event = SyncEvent(
                event_id=f"add_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                event_type='collection_created',
                collection_name=collection_name,
                timestamp=datetime.now().isoformat(),
                details={}
            )
            self._emit_sync_event(event)
        
        # 检测删除的集合
        removed_collections = old_backend - current_backend
        for collection_name in removed_collections:
            event = SyncEvent(
                event_id=f"del_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                event_type='collection_deleted',
                collection_name=collection_name,
                timestamp=datetime.now().isoformat(),
                details={}
            )
            self._emit_sync_event(event)
        
        # 更新状态
        self.sync_state.backend_collections = current_backend
        
        if added_collections or removed_collections:
            self.sync_state.sync_status = 'out_of_sync'
    
    def _emit_sync_event(self, event: SyncEvent):
        """发出同步事件"""
        logger.info(f"发出同步事件: {event.event_type} - {event.collection_name}")
        
        # 添加到待处理事件
        self.sync_state.pending_events.append(event)
        
        # 通知监听器
        for listener in self.event_listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"事件监听器异常: {e}")
    
    def notify_frontend_operation(self, operation_type: str, collection_name: str, **details):
        """通知前端操作"""
        with self._sync_lock:
            event = SyncEvent(
                event_id=f"frontend_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                event_type=operation_type,
                collection_name=collection_name,
                timestamp=datetime.now().isoformat(),
                details=details
            )
            
            # 更新前端状态
            if operation_type == 'collection_created':
                self.sync_state.frontend_collections.add(collection_name)
            elif operation_type == 'collection_deleted':
                self.sync_state.frontend_collections.discard(collection_name)
            elif operation_type == 'collection_renamed':
                old_name = details.get('old_name')
                new_name = details.get('new_name')
                if old_name:
                    self.sync_state.frontend_collections.discard(old_name)
                if new_name:
                    self.sync_state.frontend_collections.add(new_name)
            
            self._emit_sync_event(event)
    
    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        with self._sync_lock:
            # 执行一致性检查
            consistency_report = self.validator.validate_full_consistency()
            
            return {
                "sync_status": self.sync_state.sync_status,
                "last_sync": self.sync_state.last_sync,
                "frontend_collections": list(self.sync_state.frontend_collections),
                "backend_collections": list(self.sync_state.backend_collections),
                "pending_events_count": len(self.sync_state.pending_events),
                "consistency_status": consistency_report.status,
                "consistency_issues": consistency_report.issues,
                "out_of_sync_collections": {
                    "missing_in_frontend": list(consistency_report.missing_in_frontend),
                    "missing_in_backend": list(consistency_report.missing_in_backend),
                    "orphaned_vectors": list(consistency_report.orphaned_vectors)
                }
            }
    
    def force_sync(self) -> Dict[str, Any]:
        """强制同步"""
        try:
            with self._sync_lock:
                logger.info("开始强制同步")
                
                # 执行完整的一致性检查
                consistency_report = self.validator.validate_full_consistency()
                
                sync_result = {
                    "success": True,
                    "actions_taken": [],
                    "issues_found": len(consistency_report.issues),
                    "consistency_status": consistency_report.status
                }
                
                # 更新前端集合状态
                self.sync_state.frontend_collections = consistency_report.frontend_collections
                self.sync_state.backend_collections = consistency_report.backend_collections
                
                # 处理不一致问题
                if consistency_report.status == 'inconsistent':
                    # 生成同步事件
                    for missing_collection in consistency_report.missing_in_frontend:
                        event = SyncEvent(
                            event_id=f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                            event_type='collection_created',
                            collection_name=missing_collection,
                            timestamp=datetime.now().isoformat(),
                            details={"source": "force_sync"}
                        )
                        self._emit_sync_event(event)
                        sync_result["actions_taken"].append(f"添加缺失集合: {missing_collection}")
                    
                    for extra_collection in consistency_report.missing_in_backend:
                        event = SyncEvent(
                            event_id=f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                            event_type='collection_deleted',
                            collection_name=extra_collection,
                            timestamp=datetime.now().isoformat(),
                            details={"source": "force_sync"}
                        )
                        self._emit_sync_event(event)
                        sync_result["actions_taken"].append(f"移除多余集合: {extra_collection}")
                
                # 更新同步状态
                self.sync_state.sync_status = 'synced' if consistency_report.status == 'consistent' else 'out_of_sync'
                self.sync_state.last_sync = datetime.now().isoformat()
                
                logger.info(f"强制同步完成: {sync_result}")
                return sync_result
                
        except Exception as e:
            logger.error(f"强制同步失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_pending_events(self) -> List[Dict[str, Any]]:
        """获取待处理事件"""
        with self._sync_lock:
            return [asdict(event) for event in self.sync_state.pending_events]
    
    def clear_pending_events(self):
        """清除待处理事件"""
        with self._sync_lock:
            self.sync_state.pending_events.clear()
            logger.info("已清除所有待处理事件")
    
    def validate_operation_consistency(self, operation_type: str, collection_name: str, 
                                     pre_state: Dict[str, Any], post_state: Dict[str, Any]) -> Dict[str, Any]:
        """验证操作一致性"""
        try:
            validation_result = {
                "consistent": True,
                "issues": [],
                "pre_state": pre_state,
                "post_state": post_state
            }
            
            # 根据操作类型验证
            if operation_type == 'delete':
                # 验证删除操作
                if collection_name in post_state.get('collections', []):
                    validation_result["consistent"] = False
                    validation_result["issues"].append(f"删除后集合仍存在: {collection_name}")
            
            elif operation_type == 'create':
                # 验证创建操作
                if collection_name not in post_state.get('collections', []):
                    validation_result["consistent"] = False
                    validation_result["issues"].append(f"创建后集合不存在: {collection_name}")
            
            elif operation_type == 'rename':
                # 验证重命名操作
                old_name = pre_state.get('old_name')
                new_name = pre_state.get('new_name')
                
                if old_name in post_state.get('collections', []):
                    validation_result["consistent"] = False
                    validation_result["issues"].append(f"重命名后旧集合仍存在: {old_name}")
                
                if new_name not in post_state.get('collections', []):
                    validation_result["consistent"] = False
                    validation_result["issues"].append(f"重命名后新集合不存在: {new_name}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"验证操作一致性失败: {e}")
            return {
                "consistent": False,
                "issues": [f"验证过程出错: {str(e)}"]
            }
    
    def get_collection_sync_info(self, collection_name: str) -> Dict[str, Any]:
        """获取单个集合的同步信息"""
        try:
            # 验证集合完整性
            integrity_result = self.validator.validate_collection_integrity(collection_name)
            
            # 检查同步状态
            in_frontend = collection_name in self.sync_state.frontend_collections
            in_backend = collection_name in self.sync_state.backend_collections
            
            return {
                "collection_name": collection_name,
                "in_frontend": in_frontend,
                "in_backend": in_backend,
                "synced": in_frontend == in_backend,
                "integrity": integrity_result,
                "last_sync": self.sync_state.last_sync
            }
            
        except Exception as e:
            logger.error(f"获取集合同步信息失败: {e}")
            return {
                "collection_name": collection_name,
                "error": str(e)
            }

class WebSocketSyncNotifier:
    """WebSocket同步通知器"""
    
    def __init__(self):
        self.connections: List[Any] = []  # WebSocket连接列表
    
    def add_connection(self, websocket):
        """添加WebSocket连接"""
        self.connections.append(websocket)
    
    def remove_connection(self, websocket):
        """移除WebSocket连接"""
        if websocket in self.connections:
            self.connections.remove(websocket)
    
    async def notify_sync_event(self, event: SyncEvent):
        """通知同步事件"""
        if not self.connections:
            return
        
        message = {
            "type": "sync_event",
            "data": asdict(event)
        }
        
        # 发送给所有连接的客户端
        disconnected = []
        for websocket in self.connections:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"发送WebSocket消息失败: {e}")
                disconnected.append(websocket)
        
        # 清理断开的连接
        for websocket in disconnected:
            self.remove_connection(websocket)
    
    async def notify_consistency_status(self, status: Dict[str, Any]):
        """通知一致性状态"""
        if not self.connections:
            return
        
        message = {
            "type": "consistency_status",
            "data": status
        }
        
        disconnected = []
        for websocket in self.connections:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"发送一致性状态失败: {e}")
                disconnected.append(websocket)
        
        for websocket in disconnected:
            self.remove_connection(websocket)
