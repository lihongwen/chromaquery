#!/usr/bin/env python3
"""
快速测试重命名修复
"""

import requests
import json

def test_rename_api():
    """测试重命名API"""
    print("🧪 测试重命名API修复")
    print("=" * 30)
    
    try:
        # 先获取集合列表
        response = requests.get("http://localhost:8000/api/collections")
        if response.status_code != 200:
            print("❌ 无法获取集合列表")
            return
        
        collections = response.json()
        if not collections:
            print("❌ 没有集合可供测试")
            return
        
        print(f"📋 找到 {len(collections)} 个集合")
        test_collection = collections[0]
        original_name = test_collection['display_name']
        new_name = f"{original_name}_修复测试"
        
        print(f"🔄 测试重命名: {original_name} -> {new_name}")
        
        # 执行重命名
        rename_data = {
            "old_name": original_name,
            "new_name": new_name
        }
        
        response = requests.put(
            "http://localhost:8000/api/collections/rename",
            json=rename_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📊 响应状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 重命名成功!")
            print(f"   消息: {result.get('message', '')}")
            print(f"   任务ID: {result.get('task_id', '')}")
            print(f"   立即响应: {result.get('immediate_response', False)}")
            
        elif response.status_code == 500:
            try:
                error = response.json()
                error_detail = error.get('detail', '')
                print(f"❌ 服务器错误: {error_detail}")
                
                if 'ThreadPoolExecutor' in error_detail:
                    print("   🔧 仍然存在ThreadPoolExecutor导入错误")
                else:
                    print("   ✅ ThreadPoolExecutor导入错误已修复")
                    print("   ⚠️ 但存在其他错误")
                    
            except:
                print(f"❌ 服务器错误: {response.text}")
                
        else:
            try:
                error = response.json()
                print(f"⚠️ 请求错误 ({response.status_code}): {error.get('detail', '')}")
            except:
                print(f"⚠️ 请求错误 ({response.status_code}): {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器")
        print("   请确保后端服务正在运行")
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")

if __name__ == "__main__":
    test_rename_api()
