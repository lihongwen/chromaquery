"""
异步重命名管理器
实现快速响应 + 后台处理的重命名机制
"""

import asyncio
import threading
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import chromadb
from chromadb.errors import NotFoundError

logger = logging.getLogger(__name__)

class CollectionStatus(Enum):
    """集合状态枚举"""
    NORMAL = "normal"
    RENAMING = "renaming"
    ERROR = "error"
    COMPLETED = "completed"

@dataclass
class RenameTask:
    """重命名任务"""
    task_id: str
    old_name: str
    new_name: str
    old_collection_id: str
    new_collection_id: str
    status: CollectionStatus
    progress: int  # 0-100
    message: str
    created_at: str
    updated_at: str
    error_message: Optional[str] = None

class AsyncRenameManager:
    """异步重命名管理器"""
    
    def __init__(self, chroma_path: Path, client: chromadb.PersistentClient):
        self.chroma_path = chroma_path
        self.client = client
        self.db_path = chroma_path / "chroma.sqlite3"

        # 任务管理
        self.active_tasks: Dict[str, RenameTask] = {}
        self.task_lock = threading.Lock()

        # 后台任务执行器
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="rename")

        # 进度回调
        self.progress_callbacks: List[Callable] = []

        # WebSocket管理器
        self.websocket_manager = None
        self._setup_websocket_manager()

    def _setup_websocket_manager(self):
        """设置WebSocket管理器"""
        try:
            from websocket_manager import get_websocket_manager
            self.websocket_manager = get_websocket_manager()
            logger.info("WebSocket管理器已连接")
        except Exception as e:
            logger.warning(f"WebSocket管理器连接失败: {e}")
    
    def encode_collection_name(self, chinese_name: str) -> str:
        """将中文集合名称编码为ChromaDB兼容的名称"""
        import hashlib
        hash_object = hashlib.md5(chinese_name.encode('utf-8'))
        hash_hex = hash_object.hexdigest()
        return f"col_{hash_hex}"
    
    def register_progress_callback(self, callback: Callable):
        """注册进度回调函数"""
        self.progress_callbacks.append(callback)
    
    def notify_progress(self, task_id: str, progress: int, message: str, estimated_remaining: int = 0):
        """通知进度更新"""
        with self.task_lock:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                task.progress = progress
                task.message = message
                task.updated_at = datetime.now().isoformat()

                # 通过WebSocket通知前端
                if self.websocket_manager:
                    self.websocket_manager.notify_rename_progress(
                        task_id=task_id,
                        progress=progress,
                        message=message,
                        collection_name=task.new_name,
                        estimated_remaining=estimated_remaining
                    )

        # 通知所有回调
        for callback in self.progress_callbacks:
            try:
                callback(task_id, progress, message)
            except Exception as e:
                logger.error(f"进度回调失败: {e}")
    
    def quick_rename(self, old_name: str, new_name: str) -> Dict[str, Any]:
        """快速重命名（立即响应）"""
        try:
            # 1. 验证输入参数
            if not old_name or not old_name.strip():
                return {"success": False, "message": "原集合名称不能为空"}
            
            if not new_name or not new_name.strip():
                return {"success": False, "message": "新集合名称不能为空"}
            
            if old_name.strip() == new_name.strip():
                return {"success": False, "message": "新名称与原名称相同"}
            
            # 2. 查找原集合
            collections = self.client.list_collections()
            old_collection = None
            
            for collection in collections:
                metadata = collection.metadata or {}
                if metadata.get('original_name') == old_name:
                    old_collection = collection
                    break
            
            if not old_collection:
                return {"success": False, "message": f"集合不存在: {old_name}"}
            
            # 3. 检查新名称是否已存在
            for collection in collections:
                metadata = collection.metadata or {}
                if metadata.get('original_name') == new_name:
                    return {"success": False, "message": f"集合已存在: {new_name}"}
            
            # 4. 检查是否已有重命名任务在进行
            with self.task_lock:
                for task in self.active_tasks.values():
                    if (task.old_name == old_name or task.new_name == new_name) and task.status == CollectionStatus.RENAMING:
                        return {"success": False, "message": "该集合正在重命名中，请稍后再试"}
            
            # 5. 创建重命名任务（快速响应，不修改原集合）
            task_id = f"rename_{int(time.time() * 1000)}"
            new_collection_id = self.encode_collection_name(new_name)

            # 注意：由于ChromaDB的限制，我们不能安全地修改集合元数据
            # 因此我们跳过快速元数据更新，直接进行后台重命名
            logger.info(f"创建重命名任务，跳过元数据快速更新: {task_id}")
            
            # 6. 创建重命名任务
            task = RenameTask(
                task_id=task_id,
                old_name=old_name,
                new_name=new_name,
                old_collection_id=old_collection.name,
                new_collection_id=new_collection_id,
                status=CollectionStatus.RENAMING,
                progress=10,
                message="重命名已开始，正在后台处理...",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            with self.task_lock:
                self.active_tasks[task_id] = task
            
            # 7. 启动后台任务
            self.executor.submit(self._background_rename, task)
            
            logger.info(f"快速重命名完成: {old_name} -> {new_name}, 任务ID: {task_id}")
            
            return {
                "success": True,
                "message": f"重命名任务已启动，正在后台将 '{old_name}' 重命名为 '{new_name}'...",
                "task_id": task_id,
                "old_name": old_name,
                "new_name": new_name,
                "immediate_response": True,
                "background_processing": True,
                "note": "由于ChromaDB限制，重命名将在后台完成，请稍候..."
            }
            
        except Exception as e:
            logger.error(f"快速重命名失败: {e}", exc_info=True)
            return {"success": False, "message": f"重命名失败: {str(e)}"}
    
    def _background_rename(self, task: RenameTask):
        """后台执行实际的重命名操作"""
        try:
            logger.info(f"开始后台重命名任务: {task.task_id}")
            
            # 更新进度：开始处理
            self.notify_progress(task.task_id, 20, "正在创建数据备份...")
            
            # 获取当前集合（已更新显示名称的）
            try:
                current_collection = self.client.get_collection(task.old_collection_id)
            except NotFoundError:
                raise Exception("原集合已不存在")
            
            # 创建备份
            backup_data = current_collection.get()
            backup_metadata = current_collection.metadata
            
            self.notify_progress(task.task_id, 40, "正在创建新的数据结构...")
            
            # 创建新集合，保持原有配置
            new_metadata = backup_metadata.copy() if backup_metadata else {}
            new_metadata['original_name'] = task.new_name
            new_metadata['updated_at'] = datetime.now().isoformat()
            new_metadata.pop('rename_status', None)
            new_metadata.pop('rename_task_id', None)

            # 简化创建过程，让ChromaDB使用默认配置
            # 如果原集合有特殊配置，新集合会在数据复制时继承
            new_collection = self.client.create_collection(
                name=task.new_collection_id,
                metadata=new_metadata
            )
            
            self.notify_progress(task.task_id, 60, "正在迁移数据...")
            
            # 复制数据
            if backup_data['ids']:
                new_collection.add(
                    ids=backup_data['ids'],
                    documents=backup_data['documents'],
                    metadatas=backup_data['metadatas'],
                    embeddings=backup_data['embeddings']
                )
            
            self.notify_progress(task.task_id, 80, "正在验证数据完整性...")
            
            # 验证数据完整性
            old_count = current_collection.count()
            new_count = new_collection.count()
            
            if old_count != new_count:
                raise Exception(f"数据迁移不完整: 原{old_count}条，新{new_count}条")
            
            self.notify_progress(task.task_id, 90, "正在清理旧数据...")

            # 强制清理旧数据（确保不留残留）
            cleanup_success = self._force_cleanup_old_data(task.old_collection_id, task.task_id)

            if not cleanup_success:
                logger.warning(f"旧数据清理可能不完整: {task.old_collection_id}")
                # 即使清理不完整，也继续完成重命名，但记录警告
            
            # 完成任务
            with self.task_lock:
                if task.task_id in self.active_tasks:
                    self.active_tasks[task.task_id].status = CollectionStatus.COMPLETED
                    self.active_tasks[task.task_id].progress = 100
                    self.active_tasks[task.task_id].message = "重命名完成"
                    self.active_tasks[task.task_id].updated_at = datetime.now().isoformat()

            self.notify_progress(task.task_id, 100, "重命名完成")

            # 通知WebSocket重命名完成
            if self.websocket_manager:
                self.websocket_manager.notify_rename_completed(
                    task_id=task.task_id,
                    old_name=task.old_name,
                    new_name=task.new_name
                )
                # 通知集合列表更新
                self.websocket_manager.notify_collection_list_update()

            logger.info(f"后台重命名任务完成: {task.task_id}")

            # 5分钟后清理任务记录
            threading.Timer(300, self._cleanup_task, args=[task.task_id]).start()
            
        except Exception as e:
            logger.error(f"后台重命名任务失败: {task.task_id}, 错误: {e}", exc_info=True)
            
            # 标记任务失败
            with self.task_lock:
                if task.task_id in self.active_tasks:
                    self.active_tasks[task.task_id].status = CollectionStatus.ERROR
                    self.active_tasks[task.task_id].error_message = str(e)
                    self.active_tasks[task.task_id].message = f"重命名失败: {str(e)}"
                    self.active_tasks[task.task_id].updated_at = datetime.now().isoformat()

            self.notify_progress(task.task_id, -1, f"重命名失败: {str(e)}")

            # 通知WebSocket重命名失败
            if self.websocket_manager:
                self.websocket_manager.notify_rename_failed(
                    task_id=task.task_id,
                    old_name=task.old_name,
                    error_message=str(e)
                )

            # 尝试恢复原状态
            self._attempt_rollback(task)
    
    def _attempt_rollback(self, task: RenameTask):
        """尝试回滚到原状态"""
        try:
            logger.info(f"尝试回滚任务: {task.task_id}")
            
            # 如果新集合已创建，删除它
            try:
                self.client.delete_collection(task.new_collection_id)
            except:
                pass
            
            # 尝试恢复原集合的元数据
            try:
                original_collection = self.client.get_collection(task.old_collection_id)
                metadata = original_collection.metadata.copy() if original_collection.metadata else {}
                metadata['original_name'] = task.old_name
                metadata.pop('rename_status', None)
                metadata.pop('rename_task_id', None)
                original_collection.modify(metadata=metadata)
                logger.info(f"成功回滚任务: {task.task_id}")
            except Exception as e:
                logger.error(f"回滚失败: {e}")
                
        except Exception as e:
            logger.error(f"回滚过程出错: {e}")
    
    def _force_cleanup_old_data(self, old_collection_id: str, task_id: str) -> bool:
        """强制清理旧数据，确保不留残留"""
        cleanup_success = True

        try:
            # 1. 删除ChromaDB集合（多次尝试）
            for attempt in range(3):  # 最多尝试3次
                try:
                    self.client.delete_collection(old_collection_id)
                    logger.info(f"成功删除ChromaDB集合: {old_collection_id}")
                    break
                except NotFoundError:
                    # 集合已不存在，这是好事
                    logger.info(f"ChromaDB集合已不存在: {old_collection_id}")
                    break
                except Exception as e:
                    logger.warning(f"删除ChromaDB集合失败 (尝试 {attempt + 1}/3): {e}")
                    if attempt == 2:  # 最后一次尝试
                        cleanup_success = False
                    else:
                        time.sleep(1)  # 等待1秒后重试

            # 2. 清理向量文件目录（多次尝试）
            old_vector_dir = self.chroma_path / old_collection_id
            if old_vector_dir.exists():
                for attempt in range(3):
                    try:
                        import shutil
                        shutil.rmtree(old_vector_dir)
                        logger.info(f"成功删除向量文件目录: {old_vector_dir}")
                        break
                    except Exception as e:
                        logger.warning(f"删除向量文件目录失败 (尝试 {attempt + 1}/3): {e}")
                        if attempt == 2:
                            cleanup_success = False
                        else:
                            time.sleep(1)

            # 3. 清理数据库记录（如果存在）
            try:
                if self.db_path.exists():
                    import sqlite3
                    with sqlite3.connect(str(self.db_path)) as conn:
                        cursor = conn.cursor()

                        # 删除相关记录
                        cursor.execute("DELETE FROM collections WHERE id = ?", (old_collection_id,))
                        cursor.execute("DELETE FROM collection_metadata WHERE collection_id = ?", (old_collection_id,))
                        cursor.execute("DELETE FROM segments WHERE collection = ?", (old_collection_id,))

                        conn.commit()
                        logger.info(f"清理数据库记录: {old_collection_id}")
            except Exception as e:
                logger.warning(f"清理数据库记录失败: {e}")
                cleanup_success = False

            # 4. 验证清理结果
            verification_success = self._verify_cleanup(old_collection_id)
            if not verification_success:
                logger.error(f"清理验证失败: {old_collection_id}")
                cleanup_success = False

            return cleanup_success

        except Exception as e:
            logger.error(f"强制清理过程出错: {e}")
            return False

    def _verify_cleanup(self, old_collection_id: str) -> bool:
        """验证清理是否完整"""
        try:
            issues = []

            # 检查ChromaDB中是否还存在
            try:
                self.client.get_collection(old_collection_id)
                issues.append("ChromaDB中仍存在旧集合")
            except NotFoundError:
                pass  # 这是期望的结果
            except Exception as e:
                issues.append(f"检查ChromaDB集合时出错: {e}")

            # 检查向量文件目录
            old_vector_dir = self.chroma_path / old_collection_id
            if old_vector_dir.exists():
                issues.append("向量文件目录仍存在")

            # 检查数据库记录
            if self.db_path.exists():
                try:
                    import sqlite3
                    with sqlite3.connect(str(self.db_path)) as conn:
                        cursor = conn.cursor()

                        cursor.execute("SELECT COUNT(*) FROM collections WHERE id = ?", (old_collection_id,))
                        if cursor.fetchone()[0] > 0:
                            issues.append("数据库中仍存在集合记录")

                        cursor.execute("SELECT COUNT(*) FROM collection_metadata WHERE collection_id = ?", (old_collection_id,))
                        if cursor.fetchone()[0] > 0:
                            issues.append("数据库中仍存在元数据记录")
                except Exception as e:
                    issues.append(f"检查数据库记录时出错: {e}")

            if issues:
                logger.warning(f"清理验证发现问题: {issues}")
                return False

            logger.info(f"清理验证通过: {old_collection_id}")
            return True

        except Exception as e:
            logger.error(f"清理验证过程出错: {e}")
            return False

    def _cleanup_task(self, task_id: str):
        """清理任务记录"""
        with self.task_lock:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
                logger.info(f"清理任务记录: {task_id}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with self.task_lock:
            if task_id in self.active_tasks:
                return asdict(self.active_tasks[task_id])
            return None
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有活跃任务"""
        with self.task_lock:
            return [asdict(task) for task in self.active_tasks.values()]

def get_async_rename_manager(chroma_path: Path, client: chromadb.PersistentClient) -> AsyncRenameManager:
    """获取异步重命名管理器实例"""
    return AsyncRenameManager(chroma_path, client)
