#!/usr/bin/env python3
"""
简单测试脚本
"""

import requests
import json

def test_basic_connection():
    """测试基本连接"""
    try:
        print("🔌 测试后端连接...")
        response = requests.get("http://localhost:8000/api/collections", timeout=5)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            collections = response.json()
            print(f"✅ 连接成功，找到 {len(collections)} 个集合")
            return True
        else:
            print(f"❌ 连接失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接异常: {e}")
        return False

def test_data_scan():
    """测试数据扫描"""
    try:
        print("\n🔍 测试数据扫描...")
        response = requests.get("http://localhost:8000/api/data/cleanup/scan", timeout=10)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            analysis = result['analysis']
            print(f"✅ 扫描成功!")
            print(f"   ChromaDB集合: {len(analysis['chromadb_collections'])}")
            print(f"   文件系统目录: {len(analysis['filesystem_dirs'])}")
            print(f"   孤立目录: {len(analysis['orphaned_dirs'])}")
            print(f"   孤立数据大小: {analysis['total_orphaned_size_mb']:.1f} MB")
            return True
        else:
            print(f"❌ 扫描失败: {response.status_code}")
            print(f"响应: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 扫描异常: {e}")
        return False

if __name__ == "__main__":
    print("🚀 简单测试开始")
    
    # 测试连接
    connection_ok = test_basic_connection()
    
    if connection_ok:
        # 测试数据扫描
        scan_ok = test_data_scan()
        
        if scan_ok:
            print("\n✅ 基本功能测试通过!")
        else:
            print("\n❌ 数据扫描测试失败")
    else:
        print("\n❌ 无法连接到后端服务")
        print("请确保后端服务正在运行: python backend/main.py")
    
    print("\n测试完成")
