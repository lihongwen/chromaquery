#!/usr/bin/env python3
"""
测试查询修复的脚本
"""

import requests
import json

def test_query():
    """测试查询功能"""
    base_url = "http://localhost:8000"
    
    # 1. 获取集合列表
    print("1. 获取集合列表...")
    response = requests.get(f"{base_url}/api/collections")
    if response.status_code == 200:
        collections = response.json()
        print(f"找到 {len(collections)} 个集合:")
        for col in collections:
            print(f"  - {col['display_name']} (文档数: {col['count']})")
        
        if not collections:
            print("没有找到集合，请先创建集合并添加文档")
            return
            
        # 优先使用"定额集合"进行测试，因为它有更多文档
        test_collection = None
        for col in collections:
            if "定额集合" in col['display_name']:
                test_collection = col['display_name']
                break

        if not test_collection:
            test_collection = collections[0]['display_name']

        print(f"\n使用集合 '{test_collection}' 进行测试")
        
    else:
        print(f"获取集合列表失败: {response.status_code}")
        return
    
    # 2. 测试向量查询
    print("\n2. 测试向量查询...")
    query_data = {
        "query": "定额",
        "collections": [test_collection],
        "limit": 5,
        "similarity_threshold": 0.1
    }
    
    try:
        response = requests.post(f"{base_url}/api/query", json=query_data)
        if response.status_code == 200:
            result = response.json()
            print(f"查询成功! 找到 {result['total_results']} 个结果")
            print(f"处理时间: {result['processing_time']:.3f}秒")
            
            for i, res in enumerate(result['results'][:3]):  # 只显示前3个结果
                print(f"  结果 {i+1}: 距离={res['distance']:.4f}, 集合={res['collection_name']}")
                print(f"    文档片段: {res['document'][:100]}...")
                
        else:
            print(f"查询失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except Exception as e:
        print(f"查询请求异常: {e}")
    
    # 3. 测试LLM查询
    print("\n3. 测试LLM查询...")
    llm_query_data = {
        "query": "定额",
        "collections": [test_collection],
        "limit": 3,
        "similarity_threshold": 0.1,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(f"{base_url}/api/llm-query", json=llm_query_data)
        if response.status_code == 200:
            result = response.json()
            print(f"LLM查询成功! 找到 {len(result['context_results'])} 个上下文结果")
            print(f"处理时间: {result['processing_time']:.3f}秒")
            print(f"回答: {result['answer'][:200]}...")
            
        else:
            print(f"LLM查询失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except Exception as e:
        print(f"LLM查询请求异常: {e}")

if __name__ == "__main__":
    test_query()
