#!/usr/bin/env python3
"""
验证ThreadPoolExecutor修复
"""

def test_threadpool_import():
    """测试ThreadPoolExecutor导入"""
    print("🔧 验证ThreadPoolExecutor导入修复")
    print("=" * 40)
    
    try:
        # 测试正确的导入方式
        from concurrent.futures import ThreadPoolExecutor
        print("✅ 从 concurrent.futures 导入 ThreadPoolExecutor 成功")
        
        # 测试创建实例
        executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="test")
        print("✅ ThreadPoolExecutor 实例创建成功")
        
        # 关闭执行器
        executor.shutdown(wait=False)
        print("✅ ThreadPoolExecutor 正常关闭")
        
        return True
        
    except Exception as e:
        print(f"❌ ThreadPoolExecutor 测试失败: {e}")
        return False

def test_async_rename_manager_import():
    """测试AsyncRenameManager导入"""
    print("\n📦 测试AsyncRenameManager导入")
    print("=" * 35)
    
    try:
        import sys
        from pathlib import Path
        
        # 添加backend目录到路径
        backend_path = Path(__file__).parent / "backend"
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))
        
        # 测试导入AsyncRenameManager
        from async_rename_manager import AsyncRenameManager, get_async_rename_manager
        print("✅ AsyncRenameManager 导入成功")
        
        # 测试枚举和数据类
        from async_rename_manager import CollectionStatus, RenameTask
        print("✅ 相关类和枚举导入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ AsyncRenameManager 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 ThreadPoolExecutor 修复验证")
    print()
    
    # 测试ThreadPoolExecutor导入
    threadpool_ok = test_threadpool_import()
    
    # 测试AsyncRenameManager导入
    manager_ok = test_async_rename_manager_import()
    
    print(f"\n📊 验证结果:")
    print(f"   ThreadPoolExecutor: {'✅ 正常' if threadpool_ok else '❌ 失败'}")
    print(f"   AsyncRenameManager: {'✅ 正常' if manager_ok else '❌ 失败'}")
    
    if threadpool_ok and manager_ok:
        print("\n🎉 修复验证成功！")
        print("   异步重命名功能现在应该可以正常工作了。")
        print("   请重启后端服务并测试重命名功能。")
    else:
        print("\n❌ 仍有问题需要解决。")
    
    return threadpool_ok and manager_ok

if __name__ == "__main__":
    main()
