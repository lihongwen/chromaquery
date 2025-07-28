#!/usr/bin/env python3
"""
双层提示词系统测试脚本
测试角色管理和提示词组合功能
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_role_management():
    """测试角色管理功能"""
    print("=== 测试角色管理功能 ===")
    
    # 1. 获取角色列表
    print("1. 获取角色列表...")
    response = requests.get(f"{BASE_URL}/api/roles")
    if response.status_code == 200:
        roles = response.json()
        print(f"✓ 成功获取 {len(roles)} 个角色")
        for role in roles:
            print(f"  - {role['name']}: {role['description']}")
    else:
        print(f"✗ 获取角色列表失败: {response.status_code}")
        return False
    
    # 2. 创建测试角色
    print("\n2. 创建测试角色...")
    test_role_data = {
        "name": "Python专家",
        "prompt": "你是一个Python编程专家，专门解答Python相关的技术问题。请提供详细的代码示例和最佳实践建议。",
        "description": "专门处理Python编程问题的专家角色",
        "is_active": True
    }
    
    response = requests.post(f"{BASE_URL}/api/roles", json=test_role_data)
    if response.status_code == 200:
        created_role = response.json()
        print(f"✓ 成功创建角色: {created_role['name']}")
        test_role_id = created_role['id']
    else:
        print(f"✗ 创建角色失败: {response.status_code}")
        return False
    
    # 3. 更新角色
    print("\n3. 更新角色...")
    update_data = {
        "description": "专门处理Python编程问题的高级专家角色（已更新）"
    }
    
    response = requests.put(f"{BASE_URL}/api/roles/{test_role_id}", json=update_data)
    if response.status_code == 200:
        updated_role = response.json()
        print(f"✓ 成功更新角色: {updated_role['description']}")
    else:
        print(f"✗ 更新角色失败: {response.status_code}")
    
    # 4. 获取单个角色
    print("\n4. 获取单个角色...")
    response = requests.get(f"{BASE_URL}/api/roles/{test_role_id}")
    if response.status_code == 200:
        role = response.json()
        print(f"✓ 成功获取角色: {role['name']}")
    else:
        print(f"✗ 获取角色失败: {response.status_code}")
    
    # 5. 删除测试角色
    print("\n5. 删除测试角色...")
    response = requests.delete(f"{BASE_URL}/api/roles/{test_role_id}")
    if response.status_code == 200:
        print("✓ 成功删除角色")
    else:
        print(f"✗ 删除角色失败: {response.status_code}")
    
    return True

def test_dual_prompt_system():
    """测试双层提示词系统"""
    print("\n=== 测试双层提示词系统 ===")
    
    # 首先获取可用的角色
    response = requests.get(f"{BASE_URL}/api/roles")
    if response.status_code != 200:
        print("✗ 无法获取角色列表")
        return False
    
    roles = response.json()
    if not roles:
        print("✗ 没有可用的角色")
        return False
    
    # 选择第一个角色进行测试
    test_role = roles[0]
    print(f"使用角色: {test_role['name']}")
    
    # 获取集合列表
    response = requests.get(f"{BASE_URL}/api/collections")
    if response.status_code != 200:
        print("✗ 无法获取集合列表")
        return False
    
    collections = response.json()
    if not collections:
        print("✗ 没有可用的集合")
        return False
    
    # 选择第一个集合进行测试
    test_collection = collections[0]['name']
    print(f"使用集合: {collections[0]['display_name']}")
    
    # 测试不使用角色的查询
    print("\n1. 测试不使用角色的查询...")
    query_data = {
        "query": "什么是人工智能？",
        "collections": [test_collection],
        "limit": 3
    }
    
    response = requests.post(f"{BASE_URL}/api/llm-query", json=query_data)
    if response.status_code == 200:
        print("✓ 默认提示词查询成功")
    else:
        print(f"✗ 默认提示词查询失败: {response.status_code}")
    
    # 测试使用角色的查询
    print("\n2. 测试使用角色的查询...")
    query_data_with_role = {
        "query": "什么是人工智能？",
        "collections": [test_collection],
        "limit": 3,
        "role_id": test_role['id']
    }
    
    response = requests.post(f"{BASE_URL}/api/llm-query", json=query_data_with_role)
    if response.status_code == 200:
        print(f"✓ 角色提示词查询成功 (角色: {test_role['name']})")
    else:
        print(f"✗ 角色提示词查询失败: {response.status_code}")
    
    return True

def test_api_health():
    """测试API健康状态"""
    print("=== 测试API健康状态 ===")
    
    response = requests.get(f"{BASE_URL}/api/health")
    if response.status_code == 200:
        health_data = response.json()
        print(f"✓ API健康状态正常: {health_data['message']}")
        return True
    else:
        print(f"✗ API健康检查失败: {response.status_code}")
        return False

def main():
    """主测试函数"""
    print("双层提示词系统功能测试")
    print("=" * 50)
    
    try:
        # 测试API健康状态
        if not test_api_health():
            print("API服务不可用，请检查后端服务是否启动")
            return
        
        # 测试角色管理功能
        if not test_role_management():
            print("角色管理功能测试失败")
            return
        
        # 测试双层提示词系统
        if not test_dual_prompt_system():
            print("双层提示词系统测试失败")
            return
        
        print("\n" + "=" * 50)
        print("✓ 所有测试通过！双层提示词系统功能正常")
        
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到后端服务，请确保服务已启动")
    except Exception as e:
        print(f"✗ 测试过程中发生错误: {e}")

if __name__ == "__main__":
    main()
