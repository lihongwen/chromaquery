#!/usr/bin/env python3
"""
端到端集成测试脚本
测试文件上传、解析、分块和存储的完整流程
"""

import requests
import json
import os
import time
from typing import Dict, Any

# API配置
API_BASE_URL = "http://localhost:8000/api"
TEST_COLLECTION_NAME = "test_integration_collection"

def create_test_collection():
    """创建测试集合"""
    print("=== 创建测试集合 ===")
    
    url = f"{API_BASE_URL}/collections"
    data = {
        "name": TEST_COLLECTION_NAME,
        "metadata": {
            "description": "集成测试集合",
            "embedding_model": "alibaba-text-embedding-v4"
        }
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print(f"✅ 集合创建成功: {TEST_COLLECTION_NAME}")
            return True
        else:
            print(f"❌ 集合创建失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 集合创建异常: {e}")
        return False

def test_file_upload(file_path: str, chunking_config: Dict[str, Any]):
    """测试文件上传"""
    print(f"\n=== 测试文件上传: {os.path.basename(file_path)} ===")
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    url = f"{API_BASE_URL}/collections/{TEST_COLLECTION_NAME}/upload"
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            data = {'chunking_config': json.dumps(chunking_config)}
            
            print(f"📤 上传文件: {os.path.basename(file_path)}")
            print(f"📋 分块配置: {chunking_config}")
            
            response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 上传成功!")
                print(f"   文件名: {result['file_name']}")
                print(f"   创建块数: {result['chunks_created']}")
                print(f"   文件大小: {result['total_size']} bytes")
                print(f"   处理时间: {result['processing_time']:.2f}s")
                return True
            else:
                print(f"❌ 上传失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ 上传异常: {e}")
        return False

def test_collection_detail():
    """测试集合详情查询"""
    print(f"\n=== 测试集合详情查询 ===")
    
    url = f"{API_BASE_URL}/collections/{TEST_COLLECTION_NAME}/detail"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 查询成功!")
            print(f"   集合名称: {result['name']}")
            print(f"   文档总数: {result['count']}")
            print(f"   已上传文件: {len(result['uploaded_files'])}")
            
            if result['uploaded_files']:
                print(f"   文件列表: {', '.join(result['uploaded_files'])}")
            
            if result['chunk_statistics']:
                print(f"   分块统计: {result['chunk_statistics']}")
            
            return True
        else:
            print(f"❌ 查询失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 查询异常: {e}")
        return False

def test_vector_query(query_text: str):
    """测试向量查询"""
    print(f"\n=== 测试向量查询 ===")
    
    url = f"{API_BASE_URL}/query"
    data = {
        "query": query_text,
        "collections": [TEST_COLLECTION_NAME],
        "limit": 3
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            response_data = response.json()
            results = response_data.get('results', [])
            print(f"✅ 查询成功!")
            print(f"   查询文本: {query_text}")
            print(f"   结果数量: {len(results)}")

            for i, result in enumerate(results, 1):
                print(f"   结果 {i}:")
                print(f"     相似度: {1 - result['distance']:.4f}")
                print(f"     内容: {result['document'][:100]}...")
                print(f"     元数据: {result['metadata']}")

            return True
        else:
            print(f"❌ 查询失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 查询异常: {e}")
        return False

def test_supported_formats():
    """测试支持的格式查询"""
    print(f"\n=== 测试支持格式查询 ===")
    
    url = f"{API_BASE_URL}/supported-formats"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 查询成功!")
            print(f"   支持格式数量: {result['total_count']}")
            print(f"   支持的扩展名: {', '.join(result['supported_extensions'])}")
            
            for format_name, info in result['supported_formats'].items():
                print(f"   {format_name}: {info['description']}")
            
            return True
        else:
            print(f"❌ 查询失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 查询异常: {e}")
        return False

def cleanup_test_collection():
    """清理测试集合"""
    print(f"\n=== 清理测试集合 ===")
    
    url = f"{API_BASE_URL}/collections/{TEST_COLLECTION_NAME}"
    
    try:
        response = requests.delete(url)
        if response.status_code == 200:
            print(f"✅ 集合删除成功")
            return True
        else:
            print(f"❌ 集合删除失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 删除异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始端到端集成测试...\n")
    
    # 测试支持的格式
    test_supported_formats()
    
    # 创建测试集合
    if not create_test_collection():
        print("❌ 无法创建测试集合，终止测试")
        return
    
    # 等待集合创建完成
    time.sleep(1)
    
    # 测试不同格式的文件上传
    test_files = [
        {
            "path": "test_files/sample.txt",
            "config": {
                "method": "recursive",
                "chunk_size": 500,
                "chunk_overlap": 100,
                "separators": ["\n\n", "\n", "。", "！", "？"]
            }
        },
        {
            "path": "test_files/sample.md",
            "config": {
                "method": "fixed_size",
                "chunk_size": 800,
                "chunk_overlap": 150
            }
        },
        {
            "path": "test_files/sample.csv",
            "config": {
                "method": "recursive",
                "chunk_size": 1000,
                "chunk_overlap": 200
            }
        }
    ]
    
    success_count = 0
    for test_file in test_files:
        if test_file_upload(test_file["path"], test_file["config"]):
            success_count += 1
        time.sleep(2)  # 等待处理完成
    
    print(f"\n📊 文件上传测试结果: {success_count}/{len(test_files)} 成功")
    
    # 测试集合详情查询
    test_collection_detail()
    
    # 测试向量查询
    test_queries = [
        "ChromaDB Web Manager功能",
        "智能手机产品",
        "文档分块算法"
    ]
    
    for query in test_queries:
        test_vector_query(query)
        time.sleep(1)
    
    # 清理测试数据
    cleanup_test_collection()
    
    print("\n🎉 集成测试完成!")

if __name__ == "__main__":
    main()
