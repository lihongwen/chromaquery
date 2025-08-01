"""
简化的删除操作实现
确保完整清理所有相关数据
"""

import os
import sqlite3
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import chromadb

logger = logging.getLogger(__name__)

class SimpleDeleteOperations:
    """简化的删除操作"""
    
    def __init__(self, chroma_path: Path, client: chromadb.PersistentClient):
        self.chroma_path = chroma_path
        self.client = client
        self.db_path = chroma_path / "chroma.sqlite3"
    
    def safe_delete_collection(self, collection_name: str) -> Dict[str, Any]:
        """安全删除集合"""
        try:
            # 查找要删除的集合
            collections = self.client.list_collections()
            target_collection = None
            
            for collection in collections:
                metadata = collection.metadata or {}
                # 支持通过原始名称或编码名称删除
                if (metadata.get('original_name') == collection_name or
                    collection.name == collection_name):
                    target_collection = collection
                    break
            
            if not target_collection:
                return {
                    "success": False,
                    "message": f"集合 '{collection_name}' 不存在"
                }
            
            collection_id = target_collection.name
            display_name = target_collection.metadata.get('original_name', collection_name)
            
            # 创建备份
            backup_result = self._create_backup(target_collection)
            
            try:
                # 执行完整删除
                self._perform_complete_deletion(collection_id)
                
                # 验证删除结果
                if self._verify_deletion(collection_id, display_name):
                    # 清理备份（删除成功）
                    self._cleanup_backup(backup_result)
                    
                    return {
                        "success": True,
                        "message": f"集合 '{display_name}' 删除成功",
                        "operation_id": f"delete_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "consistency_verified": True
                    }
                else:
                    # 验证失败，恢复备份
                    self._restore_backup(backup_result)
                    return {
                        "success": False,
                        "message": "删除验证失败，已恢复集合"
                    }
                    
            except Exception as e:
                # 删除失败，恢复备份
                logger.error(f"删除操作失败: {e}")
                self._restore_backup(backup_result)
                return {
                    "success": False,
                    "message": f"删除失败: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"删除集合失败: {e}")
            return {
                "success": False,
                "message": f"删除集合失败: {str(e)}"
            }
    
    def _create_backup(self, collection) -> Dict[str, Any]:
        """创建集合备份"""
        try:
            backup_info = {
                "collection_id": collection.name,
                "metadata": collection.metadata,
                "data": collection.get(),
                "timestamp": datetime.now().isoformat()
            }
            
            # 备份向量文件
            vector_dir = self.chroma_path / collection.name
            backup_dir = self.chroma_path / f"delete_backup_{collection.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if vector_dir.exists():
                shutil.copytree(vector_dir, backup_dir)
                backup_info["vector_backup"] = str(backup_dir)
            
            return backup_info
            
        except Exception as e:
            logger.error(f"创建删除备份失败: {e}")
            return {}
    
    def _perform_complete_deletion(self, collection_id: str):
        """执行完整的删除操作"""
        try:
            # 1. 删除ChromaDB集合
            self.client.delete_collection(collection_id)
            logger.info(f"已删除ChromaDB集合: {collection_id}")
            
            # 2. 清理数据库记录
            if self.db_path.exists():
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.cursor()
                    
                    # 删除集合记录
                    cursor.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
                    deleted_collections = cursor.rowcount
                    
                    # 删除元数据记录
                    cursor.execute("DELETE FROM collection_metadata WHERE collection_id = ?", (collection_id,))
                    deleted_metadata = cursor.rowcount
                    
                    # 删除段记录
                    cursor.execute("DELETE FROM segments WHERE collection = ?", (collection_id,))
                    deleted_segments = cursor.rowcount
                    
                    conn.commit()
                    
                    logger.info(f"已清理数据库记录: 集合({deleted_collections}), 元数据({deleted_metadata}), 段({deleted_segments})")
            
            # 3. 删除向量文件目录
            vector_dir = self.chroma_path / collection_id
            if vector_dir.exists():
                shutil.rmtree(vector_dir)
                logger.info(f"已删除向量文件目录: {vector_dir}")
            
            logger.info(f"完成集合的完整删除: {collection_id}")
            
        except Exception as e:
            logger.error(f"执行完整删除失败: {e}")
            raise
    
    def _verify_deletion(self, collection_id: str, display_name: str) -> bool:
        """验证删除操作的完整性"""
        try:
            issues = []
            
            # 检查ChromaDB中是否还存在
            try:
                self.client.get_collection(collection_id)
                issues.append("ChromaDB中仍存在集合")
            except:
                pass  # 预期的异常，集合应该不存在
            
            # 检查数据库记录
            if self.db_path.exists():
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT COUNT(*) FROM collections WHERE id = ?", (collection_id,))
                    if cursor.fetchone()[0] > 0:
                        issues.append("数据库中仍存在集合记录")
                    
                    cursor.execute("SELECT COUNT(*) FROM collection_metadata WHERE collection_id = ?", (collection_id,))
                    if cursor.fetchone()[0] > 0:
                        issues.append("数据库中仍存在元数据记录")
            
            # 检查向量文件目录
            vector_dir = self.chroma_path / collection_id
            if vector_dir.exists():
                issues.append("向量文件目录仍存在")
            
            if issues:
                logger.warning(f"删除验证发现问题: {issues}")
                return False
            
            logger.info(f"删除验证通过: {collection_id}")
            return True
            
        except Exception as e:
            logger.error(f"验证删除操作失败: {e}")
            return False
    
    def _restore_backup(self, backup_info: Dict[str, Any]):
        """恢复备份"""
        try:
            if not backup_info:
                return
            
            collection_id = backup_info.get("collection_id")
            metadata = backup_info.get("metadata", {})
            data = backup_info.get("data", {})
            vector_backup = backup_info.get("vector_backup")
            
            if collection_id:
                # 重新创建集合
                try:
                    restored_collection = self.client.create_collection(
                        name=collection_id,
                        metadata=metadata
                    )
                    
                    # 恢复数据
                    if data.get('ids'):
                        restored_collection.add(
                            ids=data['ids'],
                            documents=data['documents'],
                            metadatas=data['metadatas'],
                            embeddings=data['embeddings']
                        )
                    
                    # 恢复向量文件
                    if vector_backup and Path(vector_backup).exists():
                        target_dir = self.chroma_path / collection_id
                        if target_dir.exists():
                            shutil.rmtree(target_dir)
                        shutil.copytree(vector_backup, target_dir)
                    
                    logger.info(f"成功恢复集合: {collection_id}")
                    
                except Exception as e:
                    logger.error(f"恢复集合失败: {e}")
            
            # 清理备份
            self._cleanup_backup(backup_info)
                    
        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
    
    def _cleanup_backup(self, backup_info: Dict[str, Any]):
        """清理备份文件"""
        try:
            vector_backup = backup_info.get("vector_backup")
            if vector_backup and Path(vector_backup).exists():
                shutil.rmtree(vector_backup)
                logger.info(f"已清理备份文件: {vector_backup}")
        except Exception as e:
            logger.warning(f"清理备份文件失败: {e}")

def get_simple_delete_operations(chroma_path: Path, client: chromadb.PersistentClient) -> SimpleDeleteOperations:
    """获取简化删除操作实例"""
    return SimpleDeleteOperations(chroma_path, client)
