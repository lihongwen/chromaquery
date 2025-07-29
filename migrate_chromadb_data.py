#!/usr/bin/env python3
"""
ChromaDB数据迁移脚本
从0.3.29版本的parquet格式迁移到1.0.15版本的新格式
"""

import pandas as pd
import json
import os
import chromadb
import numpy as np
from typing import List, Dict, Any
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_chromadb_data(old_data_path: str, new_data_path: str):
    """
    迁移ChromaDB数据从旧版本到新版本
    
    Args:
        old_data_path: 旧版本数据目录路径
        new_data_path: 新版本数据目录路径
    """
    
    # 检查旧数据文件
    collections_file = os.path.join(old_data_path, 'chroma-collections.parquet')
    embeddings_file = os.path.join(old_data_path, 'chroma-embeddings.parquet')
    
    if not os.path.exists(collections_file):
        logger.error(f"集合文件不存在: {collections_file}")
        return False
        
    if not os.path.exists(embeddings_file):
        logger.error(f"嵌入文件不存在: {embeddings_file}")
        return False
    
    try:
        # 读取旧数据
        logger.info("读取旧版本数据...")
        collections_df = pd.read_parquet(collections_file)
        embeddings_df = pd.read_parquet(embeddings_file)
        
        logger.info(f"找到 {len(collections_df)} 个集合，{len(embeddings_df)} 个文档")
        
        # 创建新版本客户端
        logger.info("初始化新版本ChromaDB客户端...")
        if os.path.exists(new_data_path):
            import shutil
            backup_path = f"{new_data_path}_backup"
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            shutil.move(new_data_path, backup_path)
            logger.info(f"已备份现有数据到: {backup_path}")
        
        client = chromadb.PersistentClient(path=new_data_path)
        
        # 迁移每个集合
        for _, collection_row in collections_df.iterrows():
            collection_uuid = collection_row['uuid']
            collection_name = collection_row['name']
            collection_metadata = json.loads(collection_row['metadata'])
            
            original_name = collection_metadata.get('original_name', collection_name)
            logger.info(f"迁移集合: {original_name} ({collection_name})")
            
            # 获取该集合的所有文档
            collection_embeddings = embeddings_df[
                embeddings_df['collection_uuid'] == collection_uuid
            ]
            
            if len(collection_embeddings) == 0:
                logger.warning(f"集合 {original_name} 没有文档，跳过")
                continue
            
            # 创建新集合
            try:
                new_collection = client.create_collection(
                    name=collection_name,
                    metadata=collection_metadata
                )
                
                # 准备文档数据
                ids = collection_embeddings['id'].tolist()
                documents = collection_embeddings['document'].tolist()
                metadatas = []
                embeddings = []
                
                for _, row in collection_embeddings.iterrows():
                    # 解析元数据
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    metadatas.append(metadata)
                    
                    # 解析嵌入向量
                    embedding = row['embedding']
                    if isinstance(embedding, str):
                        # 如果是字符串，尝试解析
                        try:
                            embedding = json.loads(embedding)
                        except:
                            embedding = eval(embedding)  # 备用方案
                    embeddings.append(embedding)
                
                # 批量添加文档
                batch_size = 100
                total_docs = len(ids)
                
                for i in range(0, total_docs, batch_size):
                    end_idx = min(i + batch_size, total_docs)
                    batch_ids = ids[i:end_idx]
                    batch_documents = documents[i:end_idx]
                    batch_metadatas = metadatas[i:end_idx]
                    batch_embeddings = embeddings[i:end_idx]
                    
                    new_collection.add(
                        ids=batch_ids,
                        documents=batch_documents,
                        metadatas=batch_metadatas,
                        embeddings=batch_embeddings
                    )
                    
                    logger.info(f"已迁移 {end_idx}/{total_docs} 个文档")
                
                logger.info(f"集合 {original_name} 迁移完成，共 {total_docs} 个文档")
                
            except Exception as e:
                logger.error(f"迁移集合 {original_name} 失败: {e}")
                continue
        
        logger.info("数据迁移完成！")
        
        # 验证迁移结果
        logger.info("验证迁移结果...")
        new_collections = client.list_collections()
        logger.info(f"新版本中有 {len(new_collections)} 个集合:")
        
        for collection in new_collections:
            count = collection.count()
            metadata = collection.metadata or {}
            original_name = metadata.get('original_name', collection.name)
            logger.info(f"  - {original_name}: {count} 个文档")
        
        return True
        
    except Exception as e:
        logger.error(f"迁移过程中出错: {e}")
        return False

if __name__ == "__main__":
    # 配置路径
    old_data_path = "/Users/lihongwen/Projects/chromadb/chromadb-web-manager/chromadbdata"
    new_data_path = "/Users/lihongwen/Projects/chromadb/chromadb-web-manager/chromadbdata_new"
    
    print("ChromaDB数据迁移工具")
    print(f"从: {old_data_path}")
    print(f"到: {new_data_path}")
    print()
    
    confirm = input("确认开始迁移？(y/N): ")
    if confirm.lower() == 'y':
        success = migrate_chromadb_data(old_data_path, new_data_path)
        if success:
            print("\n✅ 迁移成功！")
            print(f"新数据保存在: {new_data_path}")
            print("您可以将新数据目录重命名为原目录名来使用")
        else:
            print("\n❌ 迁移失败，请查看日志")
    else:
        print("迁移已取消")
