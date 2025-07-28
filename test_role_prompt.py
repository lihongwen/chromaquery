#!/usr/bin/env python3
"""
简单的角色提示词功能测试
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_role_prompt_functionality():
    """测试角色提示词功能"""
    print("=== 测试角色提示词功能 ===")
    
    # 1. 获取角色列表
    print("1. 获取角色列表...")
    response = requests.get(f"{BASE_URL}/api/roles")
    if response.status_code == 200:
        roles = response.json()
        print(f"✓ 成功获取 {len(roles)} 个角色")
        if roles:
            test_role = roles[0]
            print(f"使用角色: {test_role['name']}")
            print(f"角色提示词: {test_role['prompt'][:50]}...")
        else:
            print("✗ 没有可用的角色")
            return False
    else:
        print(f"✗ 获取角色列表失败: {response.status_code}")
        return False
    
    # 2. 获取集合列表
    print("\n2. 获取集合列表...")
    response = requests.get(f"{BASE_URL}/api/collections")
    if response.status_code == 200:
        collections = response.json()
        print(f"✓ 成功获取 {len(collections)} 个集合")
        if collections:
            test_collection = collections[0]
            print(f"使用集合: {test_collection['display_name']}")
        else:
            print("✗ 没有可用的集合")
            return False
    else:
        print(f"✗ 获取集合列表失败: {response.status_code}")
        return False
    
    # 3. 测试不使用角色的查询（流式响应）
    print("\n3. 测试不使用角色的查询...")
    query_data = {
        "query": "什么是人工智能？",
        "collections": [test_collection['name']],
        "limit": 3
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/llm-query", json=query_data, stream=True)
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ 默认提示词查询成功（流式响应）")
            # 读取一些流式数据
            count = 0
            for line in response.iter_lines():
                if line and count < 3:  # 只读取前3行
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            if 'content' in data:
                                print(f"  收到内容: {data['content'][:30]}...")
                        except:
                            pass
                    count += 1
        else:
            print(f"✗ 默认提示词查询失败: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"✗ 查询请求失败: {e}")
    
    # 4. 测试使用角色的查询（流式响应）
    print("\n4. 测试使用角色的查询...")
    query_data_with_role = {
        "query": "什么是人工智能？",
        "collections": [test_collection['name']],
        "limit": 3,
        "role_id": test_role['id']
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/llm-query", json=query_data_with_role, stream=True)
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✓ 角色提示词查询成功 (角色: {test_role['name']})")
            # 读取一些流式数据
            count = 0
            for line in response.iter_lines():
                if line and count < 3:  # 只读取前3行
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            if 'content' in data:
                                print(f"  收到内容: {data['content'][:30]}...")
                        except:
                            pass
                    count += 1
        else:
            print(f"✗ 角色提示词查询失败: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"✗ 查询请求失败: {e}")
    
    return True

if __name__ == "__main__":
    test_role_prompt_functionality()
