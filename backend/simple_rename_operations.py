"""
简化的重命名操作实现
避免循环导入问题
"""

import os
import json
import sqlite3
import shutil
import hashlib
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import chromadb
from chromadb.errors import NotFoundError

logger = logging.getLogger(__name__)

class SimpleRenameOperations:
    """简化的重命名操作"""

    def __init__(self, chroma_path: Path, client: chromadb.PersistentClient):
        self.chroma_path = chroma_path
        self.client = client
        self.db_path = chroma_path / "chroma.sqlite3"
        self._operation_lock = threading.Lock()  # 添加操作锁防止并发问题
    
    def encode_collection_name(self, chinese_name: str) -> str:
        """将中文集合名称编码为ChromaDB兼容的名称"""
        hash_object = hashlib.md5(chinese_name.encode('utf-8'))
        hash_hex = hash_object.hexdigest()
        return f"col_{hash_hex}"
    
    def safe_rename_collection(self, old_name: str, new_name: str) -> Dict[str, Any]:
        """安全重命名集合"""
        with self._operation_lock:  # 使用锁防止并发操作
            try:
                logger.info(f"开始重命名操作: {old_name} -> {new_name}")

                # 验证输入参数
                if not old_name or not old_name.strip():
                    return {
                        "success": False,
                        "message": "原集合名称不能为空"
                    }

                if not new_name or not new_name.strip():
                    return {
                        "success": False,
                        "message": "新集合名称不能为空"
                    }

                if old_name.strip() == new_name.strip():
                    return {
                        "success": False,
                        "message": "新名称与原名称相同"
                    }

                # 查找原集合
                collections = self.client.list_collections()
                old_collection = None

                logger.info(f"当前集合数量: {len(collections)}")

                for collection in collections:
                    metadata = collection.metadata or {}
                    display_name = metadata.get('original_name', collection.name)
                    logger.debug(f"检查集合: {display_name} (ID: {collection.name})")

                    if metadata.get('original_name') == old_name:
                        old_collection = collection
                        logger.info(f"找到目标集合: {old_name} (ID: {collection.name})")
                        break

                if not old_collection:
                    logger.warning(f"集合不存在: {old_name}")
                    return {
                        "success": False,
                        "message": f"集合不存在: {old_name}"
                    }

                # 检查新名称是否已存在
                for collection in collections:
                    metadata = collection.metadata or {}
                    if metadata.get('original_name') == new_name:
                        logger.warning(f"集合已存在: {new_name}")
                        return {
                            "success": False,
                            "message": f"集合已存在: {new_name}"
                        }
            
                # 创建备份
                logger.info("创建操作备份...")
                backup_result = self._create_backup(old_collection)

                try:
                    # 执行重命名
                    logger.info("执行重命名操作...")
                    rename_result = self._perform_rename(old_collection, new_name)

                    # 等待一小段时间确保操作完成
                    time.sleep(0.5)

                    # 验证结果
                    logger.info("验证重命名结果...")
                    if self._verify_rename(old_name, new_name):
                        # 清理备份
                        self._cleanup_backup(backup_result)

                        logger.info(f"重命名成功: {old_name} -> {new_name}")
                        return {
                            "success": True,
                            "message": f"集合从 '{old_name}' 重命名为 '{new_name}' 成功",
                            "operation_id": f"rename_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            "consistency_verified": True,
                            "data_count": rename_result.get("data_count", 0)
                        }
                    else:
                        # 验证失败，恢复备份
                        logger.warning("重命名验证失败，恢复备份...")
                        self._restore_backup(backup_result)
                        return {
                            "success": False,
                            "message": "重命名验证失败，已恢复原状态"
                        }

                except Exception as e:
                    # 操作失败，恢复备份
                    logger.error(f"重命名操作失败: {e}", exc_info=True)
                    self._restore_backup(backup_result)
                    return {
                        "success": False,
                        "message": f"重命名失败: {str(e)}"
                    }

            except Exception as e:
                logger.error(f"重命名集合失败: {e}", exc_info=True)
                return {
                    "success": False,
                    "message": f"重命名集合失败: {str(e)}"
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
            backup_dir = self.chroma_path / f"backup_{collection.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if vector_dir.exists():
                shutil.copytree(vector_dir, backup_dir)
                backup_info["vector_backup"] = str(backup_dir)
            
            return backup_info
            
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return {}
    
    def _perform_rename(self, old_collection, new_name: str) -> Dict[str, Any]:
        """执行重命名操作"""
        try:
            logger.info(f"开始执行重命名: {old_collection.name} -> {new_name}")

            # 编码新名称
            new_encoded = self.encode_collection_name(new_name)
            logger.info(f"新编码名称: {new_encoded}")

            # 准备新的元数据
            new_metadata = old_collection.metadata.copy() if old_collection.metadata else {}
            new_metadata['original_name'] = new_name
            new_metadata['updated_at'] = datetime.now().isoformat()

            # 如果没有创建时间，添加当前时间作为创建时间
            if 'created_at' not in new_metadata:
                new_metadata['created_at'] = new_metadata['updated_at']

            logger.info(f"准备元数据: {new_metadata}")

            # 获取原集合数据
            logger.info("获取原集合数据...")
            old_data = old_collection.get()
            old_count = old_collection.count()
            logger.info(f"原集合数据量: {old_count}")

            # 检查新集合名称是否已被占用
            try:
                existing = self.client.get_collection(new_encoded)
                if existing:
                    raise Exception(f"编码后的集合名称已存在: {new_encoded}")
            except NotFoundError:
                # 集合不存在，这是期望的情况
                logger.debug(f"新集合名称可用: {new_encoded}")
            except Exception as e:
                # 其他异常需要重新抛出
                logger.error(f"检查集合存在性时出错: {e}")
                raise

            # 创建新集合（使用默认嵌入函数）
            logger.info("创建新集合...")
            new_collection = self.client.create_collection(
                name=new_encoded,
                metadata=new_metadata
            )

            # 复制数据
            if old_data['ids']:
                logger.info(f"复制数据: {len(old_data['ids'])} 条记录")
                new_collection.add(
                    ids=old_data['ids'],
                    documents=old_data['documents'],
                    metadatas=old_data['metadatas'],
                    embeddings=old_data['embeddings']
                )
            else:
                logger.info("原集合无数据，跳过数据复制")

            # 验证数据复制
            new_count = new_collection.count()
            logger.info(f"新集合数据量: {new_count}")

            if old_count != new_count:
                raise Exception(f"数据复制不完整: 原{old_count}条，新{new_count}条")

            # 删除旧集合
            logger.info("删除旧集合...")
            self.client.delete_collection(old_collection.name)

            # 清理旧集合的向量文件
            old_vector_dir = self.chroma_path / old_collection.name
            if old_vector_dir.exists():
                logger.info(f"清理旧向量文件: {old_vector_dir}")
                shutil.rmtree(old_vector_dir)

            logger.info("重命名操作执行完成")
            return {
                "old_collection_id": old_collection.name,
                "new_collection_id": new_encoded,
                "data_count": new_count
            }

        except Exception as e:
            logger.error(f"执行重命名操作失败: {e}", exc_info=True)
            raise
    
    def _verify_rename(self, old_name: str, new_name: str) -> bool:
        """验证重命名操作的完整性"""
        try:
            logger.info(f"验证重命名结果: {old_name} -> {new_name}")

            # 刷新集合列表
            collections = self.client.list_collections()

            old_exists = False
            new_exists = False
            new_collection = None

            logger.info(f"当前集合数量: {len(collections)}")

            for collection in collections:
                metadata = collection.metadata or {}
                display_name = metadata.get('original_name', collection.name)

                logger.debug(f"检查集合: {display_name} (ID: {collection.name})")

                if display_name == old_name:
                    old_exists = True
                    logger.warning(f"旧集合仍存在: {old_name}")

                if display_name == new_name:
                    new_exists = True
                    new_collection = collection
                    logger.info(f"新集合已存在: {new_name}")

            # 验证新集合的数据完整性
            if new_exists and new_collection:
                try:
                    count = new_collection.count()
                    logger.info(f"新集合数据量: {count}")
                except Exception as e:
                    logger.error(f"无法访问新集合数据: {e}")
                    return False

            # 旧集合应该不存在，新集合应该存在
            result = not old_exists and new_exists

            if result:
                logger.info("重命名验证成功")
            else:
                logger.warning(f"重命名验证失败: 旧集合存在={old_exists}, 新集合存在={new_exists}")

            return result

        except Exception as e:
            logger.error(f"验证重命名操作失败: {e}", exc_info=True)
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
                # 检查集合是否已存在
                try:
                    existing = self.client.get_collection(collection_id)
                    logger.warning(f"集合已存在，无需恢复: {collection_id}")
                    return
                except NotFoundError:
                    # 集合不存在，可以恢复
                    logger.info(f"集合不存在，开始恢复: {collection_id}")
                except Exception as e:
                    logger.warning(f"检查集合存在性时出错，继续恢复: {e}")

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

                        # 清理备份
                        shutil.rmtree(vector_backup)

                    logger.info(f"成功恢复集合: {collection_id}")

                except Exception as e:
                    logger.error(f"恢复集合失败: {e}")
                    
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

def get_simple_rename_operations(chroma_path: Path, client: chromadb.PersistentClient) -> SimpleRenameOperations:
    """获取简化重命名操作实例"""
    return SimpleRenameOperations(chroma_path, client)
