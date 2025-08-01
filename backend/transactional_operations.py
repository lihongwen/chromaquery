"""
事务性操作管理器
确保ChromaDB操作的原子性和一致性
"""

import os
import json
import sqlite3
import shutil
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import chromadb

from consistency_manager import StateValidator, AutoRepair, ConsistencyCheckpoint

logger = logging.getLogger(__name__)

@dataclass
class OperationResult:
    """操作结果"""
    success: bool
    message: str
    operation_id: str
    consistency_verified: bool
    rollback_performed: bool = False
    details: Dict[str, Any] = None

class TransactionalOperations:
    """事务性操作管理器"""
    
    def __init__(self, chroma_path: Path, client: chromadb.PersistentClient, backup_path: Path):
        self.chroma_path = chroma_path
        self.client = client
        self.backup_path = backup_path
        self.db_path = chroma_path / "chroma.sqlite3"
        
        # 初始化组件
        self.validator = StateValidator(chroma_path, client)
        self.auto_repair = AutoRepair(chroma_path, client)
        
        # 操作锁
        self._operation_lock = threading.Lock()
        
        # 确保备份目录存在
        self.backup_path.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def atomic_operation(self, operation_type: str, collection_name: str, **kwargs):
        """原子操作上下文管理器"""
        operation_id = f"{operation_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        checkpoint = None
        
        with self._operation_lock:
            try:
                # 创建操作前检查点
                checkpoint = self._create_checkpoint(operation_id, operation_type, collection_name)
                logger.info(f"开始事务操作: {operation_id}")
                
                # 验证操作前状态
                pre_consistency = self.validator.validate_full_consistency()
                if pre_consistency.status == 'error':
                    raise Exception(f"操作前一致性检查失败: {pre_consistency.issues}")
                
                yield operation_id
                
                # 操作完成后验证一致性
                post_consistency = self.validator.validate_full_consistency()
                
                if post_consistency.status == 'inconsistent':
                    logger.warning(f"操作后发现一致性问题: {post_consistency.issues}")
                    
                    # 尝试自动修复
                    repair_result = self.auto_repair.repair_consistency_issues(post_consistency)
                    logger.info(f"自动修复结果: {repair_result}")
                    
                    # 再次验证
                    final_consistency = self.validator.validate_full_consistency()
                    if final_consistency.status != 'consistent':
                        raise Exception(f"修复后仍存在一致性问题: {final_consistency.issues}")
                
                logger.info(f"事务操作成功完成: {operation_id}")
                
            except Exception as e:
                logger.error(f"事务操作失败: {operation_id}, 错误: {e}")
                
                # 执行回滚
                if checkpoint:
                    try:
                        self._rollback_to_checkpoint(checkpoint)
                        logger.info(f"成功回滚到检查点: {operation_id}")
                    except Exception as rollback_error:
                        logger.error(f"回滚失败: {rollback_error}")
                
                raise
            finally:
                # 清理检查点
                if checkpoint and checkpoint.backup_path:
                    try:
                        backup_dir = Path(checkpoint.backup_path)
                        if backup_dir.exists():
                            shutil.rmtree(backup_dir)
                    except Exception as e:
                        logger.warning(f"清理检查点失败: {e}")
    
    def _create_checkpoint(self, operation_id: str, operation_type: str, collection_name: str) -> ConsistencyCheckpoint:
        """创建一致性检查点"""
        try:
            # 创建备份目录
            backup_dir = self.backup_path / f"checkpoint_{operation_id}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 备份数据库
            if self.db_path.exists():
                shutil.copy2(self.db_path, backup_dir / "chroma.sqlite3")
            
            # 备份相关的向量文件
            if operation_type in ["delete", "rename"]:
                collection_id = self._find_collection_id(collection_name)
                if collection_id:
                    vector_dir = self.chroma_path / collection_id
                    if vector_dir.exists():
                        shutil.copytree(vector_dir, backup_dir / collection_id)
            
            # 记录操作前状态
            pre_state = {
                "collections": [col.name for col in self.client.list_collections()],
                "operation_target": collection_name,
                "timestamp": datetime.now().isoformat()
            }
            
            checkpoint = ConsistencyCheckpoint(
                checkpoint_id=operation_id,
                timestamp=datetime.now().isoformat(),
                operation_type=operation_type,
                collection_name=collection_name,
                pre_state=pre_state,
                backup_path=str(backup_dir)
            )
            
            # 保存检查点信息
            with open(backup_dir / "checkpoint.json", 'w', encoding='utf-8') as f:
                json.dump(asdict(checkpoint), f, ensure_ascii=False, indent=2)
            
            return checkpoint
            
        except Exception as e:
            logger.error(f"创建检查点失败: {e}")
            raise
    
    def _rollback_to_checkpoint(self, checkpoint: ConsistencyCheckpoint):
        """回滚到检查点"""
        try:
            backup_dir = Path(checkpoint.backup_path)
            
            if not backup_dir.exists():
                raise Exception(f"检查点备份不存在: {backup_dir}")
            
            # 恢复数据库
            backup_db = backup_dir / "chroma.sqlite3"
            if backup_db.exists():
                shutil.copy2(backup_db, self.db_path)
            
            # 恢复向量文件
            for item in backup_dir.iterdir():
                if item.is_dir() and item.name != "__pycache__":
                    target_dir = self.chroma_path / item.name
                    if target_dir.exists():
                        shutil.rmtree(target_dir)
                    shutil.copytree(item, target_dir)
            
            logger.info(f"成功回滚到检查点: {checkpoint.checkpoint_id}")
            
        except Exception as e:
            logger.error(f"回滚到检查点失败: {e}")
            raise
    
    def _find_collection_id(self, collection_name: str) -> Optional[str]:
        """查找集合的内部ID"""
        try:
            collections = self.client.list_collections()
            for collection in collections:
                metadata = collection.metadata or {}
                if (metadata.get('original_name') == collection_name or
                    collection.name == collection_name):
                    return collection.name
            return None
        except Exception as e:
            logger.error(f"查找集合ID失败: {e}")
            return None
    
    def safe_delete_collection(self, collection_name: str) -> OperationResult:
        """安全删除集合"""
        try:
            with self.atomic_operation("delete", collection_name) as operation_id:
                # 查找目标集合
                collections = self.client.list_collections()
                target_collection = None
                
                for collection in collections:
                    metadata = collection.metadata or {}
                    if (metadata.get('original_name') == collection_name or
                        collection.name == collection_name):
                        target_collection = collection
                        break
                
                if not target_collection:
                    return OperationResult(
                        success=False,
                        message=f"集合不存在: {collection_name}",
                        operation_id=operation_id,
                        consistency_verified=False
                    )
                
                collection_id = target_collection.name
                display_name = target_collection.metadata.get('original_name', collection_name)
                
                # 执行删除操作
                self._perform_complete_deletion(collection_id)
                
                # 验证删除结果
                verification_result = self._verify_deletion(collection_id, display_name)
                
                return OperationResult(
                    success=True,
                    message=f"集合 '{display_name}' 删除成功",
                    operation_id=operation_id,
                    consistency_verified=verification_result["verified"],
                    details=verification_result
                )
                
        except Exception as e:
            logger.error(f"删除集合失败: {e}")
            return OperationResult(
                success=False,
                message=f"删除集合失败: {str(e)}",
                operation_id="",
                consistency_verified=False,
                rollback_performed=True
            )
    
    def _perform_complete_deletion(self, collection_id: str):
        """执行完整的删除操作"""
        try:
            # 1. 删除ChromaDB集合
            self.client.delete_collection(collection_id)
            
            # 2. 清理数据库记录
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # 删除集合记录
                cursor.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
                
                # 删除元数据记录
                cursor.execute("DELETE FROM collection_metadata WHERE collection_id = ?", (collection_id,))
                
                # 删除段记录
                cursor.execute("DELETE FROM segments WHERE collection = ?", (collection_id,))
                
                conn.commit()
            
            # 3. 删除向量文件目录
            vector_dir = self.chroma_path / collection_id
            if vector_dir.exists():
                shutil.rmtree(vector_dir)
            
            logger.info(f"完成集合的完整删除: {collection_id}")
            
        except Exception as e:
            logger.error(f"执行完整删除失败: {e}")
            raise
    
    def _verify_deletion(self, collection_id: str, display_name: str) -> Dict[str, Any]:
        """验证删除操作的完整性"""
        verification_result = {
            "verified": True,
            "issues": []
        }
        
        try:
            # 检查ChromaDB中是否还存在
            try:
                self.client.get_collection(collection_id)
                verification_result["verified"] = False
                verification_result["issues"].append("ChromaDB中仍存在集合")
            except:
                pass  # 预期的异常，集合应该不存在
            
            # 检查数据库记录
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM collections WHERE id = ?", (collection_id,))
                if cursor.fetchone()[0] > 0:
                    verification_result["verified"] = False
                    verification_result["issues"].append("数据库中仍存在集合记录")
                
                cursor.execute("SELECT COUNT(*) FROM collection_metadata WHERE collection_id = ?", (collection_id,))
                if cursor.fetchone()[0] > 0:
                    verification_result["verified"] = False
                    verification_result["issues"].append("数据库中仍存在元数据记录")
            
            # 检查向量文件目录
            vector_dir = self.chroma_path / collection_id
            if vector_dir.exists():
                verification_result["verified"] = False
                verification_result["issues"].append("向量文件目录仍存在")
            
            return verification_result
            
        except Exception as e:
            logger.error(f"验证删除操作失败: {e}")
            return {
                "verified": False,
                "issues": [f"验证过程出错: {str(e)}"]
            }
    
    def safe_rename_collection(self, old_name: str, new_name: str) -> OperationResult:
        """安全重命名集合"""
        try:
            with self.atomic_operation("rename", old_name, new_name=new_name) as operation_id:
                # 查找原集合
                collections = self.client.list_collections()
                old_collection = None
                
                for collection in collections:
                    metadata = collection.metadata or {}
                    if metadata.get('original_name') == old_name:
                        old_collection = collection
                        break
                
                if not old_collection:
                    return OperationResult(
                        success=False,
                        message=f"集合不存在: {old_name}",
                        operation_id=operation_id,
                        consistency_verified=False
                    )
                
                # 检查新名称是否已存在
                for collection in collections:
                    metadata = collection.metadata or {}
                    if metadata.get('original_name') == new_name:
                        return OperationResult(
                            success=False,
                            message=f"集合已存在: {new_name}",
                            operation_id=operation_id,
                            consistency_verified=False
                        )
                
                # 执行重命名操作
                rename_result = self._perform_complete_rename(old_collection, new_name)
                
                # 验证重命名结果
                verification_result = self._verify_rename(old_name, new_name)
                
                return OperationResult(
                    success=True,
                    message=f"集合从 '{old_name}' 重命名为 '{new_name}' 成功",
                    operation_id=operation_id,
                    consistency_verified=verification_result["verified"],
                    details={**rename_result, **verification_result}
                )
                
        except Exception as e:
            logger.error(f"重命名集合失败: {e}")
            return OperationResult(
                success=False,
                message=f"重命名集合失败: {str(e)}",
                operation_id="",
                consistency_verified=False,
                rollback_performed=True
            )
    
    def _perform_complete_rename(self, old_collection, new_name: str) -> Dict[str, Any]:
        """执行完整的重命名操作"""
        try:
            # 避免循环导入，直接实现编码函数
            def encode_collection_name(chinese_name: str) -> str:
                """将中文集合名称编码为ChromaDB兼容的名称"""
                import hashlib
                hash_object = hashlib.md5(chinese_name.encode('utf-8'))
                hash_hex = hash_object.hexdigest()
                return f"col_{hash_hex}"

            # 编码新名称
            new_encoded = encode_collection_name(new_name)
            
            # 准备新的元数据
            new_metadata = old_collection.metadata.copy() if old_collection.metadata else {}
            new_metadata['original_name'] = new_name
            new_metadata['updated_at'] = datetime.now().isoformat()
            
            # 确定嵌入函数
            embedding_function = None
            embedding_model = new_metadata.get('embedding_model')

            if embedding_model == 'alibaba-text-embedding-v4':
                try:
                    from alibaba_embedding import create_alibaba_embedding_function
                    embedding_function = create_alibaba_embedding_function(dimension=1024)
                except ImportError:
                    logger.warning("阿里云嵌入函数不可用，使用默认函数")
            elif embedding_model and embedding_model.startswith('ollama-'):
                try:
                    from ollama_embedding import create_ollama_embedding_function
                    ollama_model = embedding_model.replace('ollama-', '')
                    ollama_base_url = new_metadata.get('ollama_base_url', 'http://localhost:11434')
                    embedding_function = create_ollama_embedding_function(
                        model_name=ollama_model,
                        base_url=ollama_base_url
                    )
                except ImportError:
                    logger.warning("Ollama嵌入函数不可用，使用默认函数")
            
            # 创建新集合
            if embedding_function:
                new_collection = self.client.create_collection(
                    name=new_encoded,
                    metadata=new_metadata,
                    embedding_function=embedding_function
                )
            else:
                new_collection = self.client.create_collection(
                    name=new_encoded,
                    metadata=new_metadata
                )
            
            # 复制数据
            old_data = old_collection.get()
            if old_data['ids']:
                new_collection.add(
                    ids=old_data['ids'],
                    documents=old_data['documents'],
                    metadatas=old_data['metadatas'],
                    embeddings=old_data['embeddings']
                )
            
            # 验证数据复制
            old_count = old_collection.count()
            new_count = new_collection.count()
            
            if old_count != new_count:
                raise Exception(f"数据复制不完整: 原{old_count}条，新{new_count}条")
            
            # 删除旧集合
            self.client.delete_collection(old_collection.name)
            
            return {
                "old_collection_id": old_collection.name,
                "new_collection_id": new_encoded,
                "data_count": new_count
            }
            
        except Exception as e:
            logger.error(f"执行重命名操作失败: {e}")
            raise
    
    def _verify_rename(self, old_name: str, new_name: str) -> Dict[str, Any]:
        """验证重命名操作的完整性"""
        verification_result = {
            "verified": True,
            "issues": []
        }
        
        try:
            collections = self.client.list_collections()
            
            # 检查旧集合是否已删除
            old_exists = False
            new_exists = False
            
            for collection in collections:
                metadata = collection.metadata or {}
                display_name = metadata.get('original_name', collection.name)
                
                if display_name == old_name:
                    old_exists = True
                    verification_result["issues"].append(f"旧集合仍存在: {old_name}")
                
                if display_name == new_name:
                    new_exists = True
            
            if old_exists:
                verification_result["verified"] = False
            
            if not new_exists:
                verification_result["verified"] = False
                verification_result["issues"].append(f"新集合不存在: {new_name}")
            
            return verification_result
            
        except Exception as e:
            logger.error(f"验证重命名操作失败: {e}")
            return {
                "verified": False,
                "issues": [f"验证过程出错: {str(e)}"]
            }
