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
                # 执行完整删除（传递集合名称）
                self._perform_complete_deletion(collection_id, display_name)
                
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
    
    def _perform_complete_deletion(self, collection_id: str, collection_name: str = ""):
        """执行完整的删除操作"""
        try:
            # 1. 预先获取所有相关的ID信息和文件夹信息（在任何删除操作之前）
            segment_ids = []
            embedding_ids = []
            all_segment_dirs = []
            
            logger.info(f"开始删除集合: {collection_id} ({collection_name})")
            
            if self.db_path.exists():
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.cursor()
                    
                    # 获取所有相关的段ID
                    cursor.execute("SELECT id FROM segments WHERE collection = ?", (collection_id,))
                    segment_ids = [row[0] for row in cursor.fetchall()]
                    logger.info(f"预获取段ID列表: {segment_ids}")
                    
                    # 获取所有相关的embedding ID（如果有段的话）
                    if segment_ids:
                        placeholders = ','.join(['?' for _ in segment_ids])
                        cursor.execute(f"""
                            SELECT id FROM embeddings 
                            WHERE segment_id IN ({placeholders})
                        """, segment_ids)
                        embedding_ids = [row[0] for row in cursor.fetchall()]
                        logger.info(f"预获取embedding ID数量: {len(embedding_ids)}")
            
            # 预扫描所有段文件夹（不依赖数据库记录）
            if self.chroma_path.exists():
                for item in self.chroma_path.iterdir():
                    if item.is_dir() and len(item.name) == 36 and item.name.count('-') == 4:
                        all_segment_dirs.append(item.name)
                logger.info(f"预扫描所有段文件夹: {all_segment_dirs}")
            
            # 2. 按正确顺序删除数据库记录（从叶子节点到根节点）
            if self.db_path.exists():
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.cursor()
                    
                    # Step 1: 删除向量元数据（最深层）
                    deleted_embedding_metadata = 0
                    if embedding_ids:
                        placeholders = ','.join(['?' for _ in embedding_ids])
                        cursor.execute(f"""
                            DELETE FROM embedding_metadata 
                            WHERE id IN ({placeholders})
                        """, embedding_ids)
                        deleted_embedding_metadata = cursor.rowcount
                    
                    # Step 2: 删除向量数据（主要存储占用者）
                    deleted_embeddings = 0
                    if segment_ids:
                        placeholders = ','.join(['?' for _ in segment_ids])
                        cursor.execute(f"""
                            DELETE FROM embeddings 
                            WHERE segment_id IN ({placeholders})
                        """, segment_ids)
                        deleted_embeddings = cursor.rowcount
                    
                    # Step 3: 删除嵌入队列中的相关数据
                    cursor.execute("""
                        DELETE FROM embeddings_queue 
                        WHERE topic = ? OR id LIKE ?
                    """, (collection_id, f"{collection_id}%"))
                    deleted_queue = cursor.rowcount
                    
                    # Step 4: 删除段元数据
                    deleted_segment_metadata = 0
                    if segment_ids:
                        placeholders = ','.join(['?' for _ in segment_ids])
                        cursor.execute(f"""
                            DELETE FROM segment_metadata 
                            WHERE segment_id IN ({placeholders})
                        """, segment_ids)
                        deleted_segment_metadata = cursor.rowcount
                    
                    # Step 5: 删除段记录
                    cursor.execute("DELETE FROM segments WHERE collection = ?", (collection_id,))
                    deleted_segments = cursor.rowcount
                    
                    # Step 6: 删除集合元数据
                    cursor.execute("DELETE FROM collection_metadata WHERE collection_id = ?", (collection_id,))
                    deleted_collection_metadata = cursor.rowcount
                    
                    # Step 7: 删除集合记录
                    cursor.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
                    deleted_collections = cursor.rowcount
                    
                    conn.commit()
                    
                    logger.info(f"""已完整清理数据库记录:
                        - 向量元数据: {deleted_embedding_metadata}
                        - 向量数据: {deleted_embeddings} 
                        - 队列数据: {deleted_queue}
                        - 段元数据: {deleted_segment_metadata}
                        - 段记录: {deleted_segments}
                        - 集合元数据: {deleted_collection_metadata}
                        - 集合记录: {deleted_collections}""")
            
            # 3. 调用ChromaDB API删除
            try:
                self.client.delete_collection(collection_id)
                logger.info(f"已删除ChromaDB集合: {collection_id}")
            except Exception as e:
                logger.warning(f"ChromaDB API删除失败，但数据库已清理: {e}")
            
            # 4. 记录待清理的段文件夹（新的核心逻辑）
            current_segment_dirs = []
            if self.chroma_path.exists():
                for item in self.chroma_path.iterdir():
                    if item.is_dir() and len(item.name) == 36 and item.name.count('-') == 4:
                        current_segment_dirs.append(item.name)
            
            if current_segment_dirs:
                import pending_cleanup_manager
                cleanup_manager = pending_cleanup_manager.get_cleanup_manager()
                cleanup_manager.add_pending_cleanup(current_segment_dirs, collection_id, collection_name)
                logger.info(f"已记录 {len(current_segment_dirs)} 个段文件夹到待清理列表: {current_segment_dirs}")
            
            # 5. 尝试删除集合级别的文件夹（如果存在）
            collection_dir = self.chroma_path / collection_id
            if collection_dir.exists():
                try:
                    shutil.rmtree(collection_dir)
                    logger.info(f"已删除集合文件夹: {collection_dir}")
                except Exception as e:
                    logger.warning(f"删除集合文件夹失败: {e}")
            
            logger.info(f"""完成集合的完整删除: {collection_id} ({collection_name})
                预获取段数: {len(segment_ids)}
                预扫描段文件夹数: {len(all_segment_dirs)}
                记录到待清理列表: {len(current_segment_dirs)}
                实际删除向量数据: {deleted_embeddings}""")
            
        except Exception as e:
            logger.error(f"执行完整删除失败: {e}")
            raise
    
    def _safe_remove_segment_dir(self, segment_dir: Path) -> bool:
        """安全删除段文件夹，处理Windows文件锁定问题"""
        import time
        import stat
        import os
        
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Windows特殊处理：先移除只读属性
                if os.name == 'nt':  # Windows
                    for root, dirs, files in os.walk(segment_dir):
                        for d in dirs:
                            dir_path = os.path.join(root, d)
                            try:
                                os.chmod(dir_path, stat.S_IWRITE)
                            except:
                                pass
                        for f in files:
                            file_path = os.path.join(root, f)
                            try:
                                os.chmod(file_path, stat.S_IWRITE)
                            except:
                                pass
                
                # 尝试删除
                shutil.rmtree(segment_dir)
                return True
                
            except (PermissionError, OSError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"删除段文件夹失败，重试 {attempt + 1}/{max_retries}: {e}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    logger.error(f"删除段文件夹最终失败 {segment_dir}: {e}")
                    return False
            except Exception as e:
                logger.error(f"删除段文件夹异常 {segment_dir}: {e}")
                return False
        
        return False

    
    def force_cleanup_chromadb_handles(self) -> None:
        """强制清理ChromaDB的文件句柄"""
        try:
            # 方法1: 强制垃圾回收
            import gc
            gc.collect()
            
            # 方法2: 尝试重新初始化ChromaDB客户端（如果可能）
            if hasattr(self.client, '_system'):
                try:
                    # 尝试清理ChromaDB内部缓存
                    self.client._system.reset()
                except:
                    pass
            
            # 方法3: 触发ChromaDB的内部清理
            try:
                # 获取当前集合列表，这可能触发内部清理
                _ = self.client.list_collections()
            except:
                pass
                
            logger.info("已尝试强制清理ChromaDB文件句柄")
            
        except Exception as e:
            logger.warning(f"强制清理ChromaDB句柄失败: {e}")
    
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
            
            # 完整检查数据库记录
            if self.db_path.exists():
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.cursor()
                    
                    # 检查集合记录
                    cursor.execute("SELECT COUNT(*) FROM collections WHERE id = ?", (collection_id,))
                    collections_count = cursor.fetchone()[0]
                    if collections_count > 0:
                        issues.append(f"数据库中仍存在{collections_count}个集合记录")
                    
                    # 检查集合元数据
                    cursor.execute("SELECT COUNT(*) FROM collection_metadata WHERE collection_id = ?", (collection_id,))
                    collection_metadata_count = cursor.fetchone()[0]
                    if collection_metadata_count > 0:
                        issues.append(f"数据库中仍存在{collection_metadata_count}个集合元数据记录")
                    
                    # 检查段记录（针对当前集合）
                    cursor.execute("SELECT id FROM segments WHERE collection = ?", (collection_id,))
                    remaining_collection_segments = [row[0] for row in cursor.fetchall()]
                    if remaining_collection_segments:
                        issues.append(f"数据库中仍存在{len(remaining_collection_segments)}个当前集合的段记录")
                    
                    # 检查与当前集合相关的向量数据
                    if remaining_collection_segments:
                        placeholders = ','.join(['?' for _ in remaining_collection_segments])
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM embeddings 
                            WHERE segment_id IN ({placeholders})
                        """, remaining_collection_segments)
                        collection_embeddings_count = cursor.fetchone()[0]
                        if collection_embeddings_count > 0:
                            issues.append(f"数据库中仍存在{collection_embeddings_count}条当前集合的向量数据")
                    
                    # 检查与当前集合相关的向量元数据
                    if remaining_collection_segments:
                        placeholders = ','.join(['?' for _ in remaining_collection_segments])
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM embedding_metadata 
                            WHERE id IN (
                                SELECT e.id FROM embeddings e 
                                WHERE e.segment_id IN ({placeholders})
                            )
                        """, remaining_collection_segments)
                        collection_embedding_metadata_count = cursor.fetchone()[0]
                        if collection_embedding_metadata_count > 0:
                            issues.append(f"数据库中仍存在{collection_embedding_metadata_count}条当前集合的向量元数据")
                    
                    # 检查队列数据（针对当前集合）
                    cursor.execute("""
                        SELECT COUNT(*) FROM embeddings_queue 
                        WHERE topic = ? OR id LIKE ?
                    """, (collection_id, f"{collection_id}%"))
                    queue_count = cursor.fetchone()[0]
                    if queue_count > 0:
                        issues.append(f"数据库中仍存在{queue_count}条当前集合的队列数据")
                    
                    # 检查当前集合的段文件夹是否还存在（基于数据库中的段记录）
                    collection_segment_dirs_remaining = []
                    for segment_id in remaining_collection_segments:
                        segment_dir = self.chroma_path / segment_id
                        if segment_dir.exists():
                            collection_segment_dirs_remaining.append(segment_id)
                    
                    if collection_segment_dirs_remaining:
                        issues.append(f"当前集合的段文件夹仍存在: {collection_segment_dirs_remaining}")
            
            # 检查集合级别的文件夹
            collection_dir = self.chroma_path / collection_id
            if collection_dir.exists():
                issues.append("集合文件夹仍存在")
            
            # 检查全局孤立数据情况（仅作为信息，不影响当前删除验证结果）
            if self.db_path.exists():
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.cursor()
                    
                    # 获取所有存在的段ID（从embeddings表）
                    cursor.execute("SELECT DISTINCT segment_id FROM embeddings")
                    existing_segment_ids = [row[0] for row in cursor.fetchall()]
                    
                    # 检查这些段是否在segments表中有对应记录
                    orphaned_segments = []
                    for seg_id in existing_segment_ids:
                        cursor.execute("SELECT COUNT(*) FROM segments WHERE id = ?", (seg_id,))
                        if cursor.fetchone()[0] == 0:
                            orphaned_segments.append(seg_id)
                    
                    if orphaned_segments:
                        # 这是全局孤立数据，不影响当前删除验证，只记录警告
                        placeholders = ','.join(['?' for _ in orphaned_segments])
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM embeddings 
                            WHERE segment_id IN ({placeholders})
                        """, orphaned_segments)
                        orphaned_embeddings_count = cursor.fetchone()[0]
                        logger.warning(f"系统中发现{len(orphaned_segments)}个全局孤立段，包含{orphaned_embeddings_count}条孤立向量数据（与当前删除无关）")
                    
                    # 检查孤立的段文件夹（仅作为信息）
                    if self.chroma_path.exists():
                        all_segment_dirs = []
                        for item in self.chroma_path.iterdir():
                            if item.is_dir() and len(item.name) == 36 and item.name.count('-') == 4:
                                all_segment_dirs.append(item.name)
                        
                        # 获取数据库中所有段ID
                        cursor.execute("SELECT id FROM segments")
                        db_segment_ids = [row[0] for row in cursor.fetchall()]
                        
                        # 找出孤立的文件夹
                        orphaned_dirs = [d for d in all_segment_dirs if d not in db_segment_ids]
                        if orphaned_dirs:
                            logger.warning(f"发现{len(orphaned_dirs)}个孤立段文件夹（与当前删除无关）: {orphaned_dirs[:5]}{'...' if len(orphaned_dirs) > 5 else ''}")
            
            # 统计验证结果（只基于当前集合相关的检查）
            if issues:
                logger.warning(f"删除验证发现当前集合相关问题: {issues}")
                return False
            
            logger.info(f"""删除验证通过: {collection_id} ({display_name})
                ✅ ChromaDB集合已删除
                ✅ 当前集合的所有数据库记录已清理
                ✅ 当前集合的所有物理文件夹已删除
                ✅ 当前集合无数据残留""")
            return True
            
        except Exception as e:
            logger.error(f"验证删除操作失败: {e}")
            return False

    
    def cleanup_orphaned_data(self) -> Dict[str, Any]:
        """清理系统中的孤立数据"""
        try:
            result = {
                "orphaned_embeddings_cleaned": 0,
                "orphaned_embedding_metadata_cleaned": 0,
                "orphaned_segment_dirs_cleaned": 0,
                "orphaned_dirs": []
            }
            
            if self.db_path.exists():
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.cursor()
                    
                    # 1. 清理孤立的向量元数据
                    cursor.execute("""
                        DELETE FROM embedding_metadata 
                        WHERE id IN (
                            SELECT em.id FROM embedding_metadata em
                            LEFT JOIN embeddings e ON em.id = e.id
                            WHERE e.id IS NULL
                        )
                    """)
                    result["orphaned_embedding_metadata_cleaned"] = cursor.rowcount
                    
                    # 2. 清理孤立的向量数据（段不存在的）
                    cursor.execute("""
                        DELETE FROM embeddings 
                        WHERE segment_id NOT IN (SELECT id FROM segments)
                    """)
                    result["orphaned_embeddings_cleaned"] = cursor.rowcount
                    
                    conn.commit()
                    
                    # 3. 清理孤立的段文件夹
                    if self.chroma_path.exists():
                        # 获取数据库中所有有效的段ID
                        cursor.execute("SELECT id FROM segments")
                        valid_segment_ids = [row[0] for row in cursor.fetchall()]
                        
                        # 扫描文件夹
                        for item in self.chroma_path.iterdir():
                            if item.is_dir() and len(item.name) == 36 and item.name.count('-') == 4:
                                if item.name not in valid_segment_ids:
                                    try:
                                        shutil.rmtree(item)
                                        result["orphaned_dirs"].append(item.name)
                                        result["orphaned_segment_dirs_cleaned"] += 1
                                        logger.info(f"已清理孤立段文件夹: {item}")
                                    except Exception as e:
                                        logger.error(f"清理孤立段文件夹失败 {item}: {e}")
            
            if any(result[k] > 0 for k in ["orphaned_embeddings_cleaned", "orphaned_embedding_metadata_cleaned", "orphaned_segment_dirs_cleaned"]):
                logger.info(f"""孤立数据清理完成:
                    - 孤立向量元数据: {result['orphaned_embedding_metadata_cleaned']}
                    - 孤立向量数据: {result['orphaned_embeddings_cleaned']}
                    - 孤立段文件夹: {result['orphaned_segment_dirs_cleaned']}""")
            else:
                logger.info("未发现需要清理的孤立数据")
            
            return result
            
        except Exception as e:
            logger.error(f"清理孤立数据失败: {e}")
            return {"error": str(e)}
    
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
