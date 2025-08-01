#!/usr/bin/env python3
"""
调试测试脚本
"""

print("🔍 开始调试测试...")

try:
    print("1. 测试基本导入...")
    import sys
    import os
    from pathlib import Path
    print("   ✅ 基本模块导入成功")
    
    print("2. 测试后端模块导入...")
    sys.path.insert(0, str(Path(__file__).parent / "backend"))
    
    from data_cleanup_tool import DataCleanupTool
    print("   ✅ data_cleanup_tool 导入成功")
    
    from async_rename_manager import AsyncRenameManager
    print("   ✅ async_rename_manager 导入成功")
    
    print("3. 测试ChromaDB导入...")
    import chromadb
    print("   ✅ chromadb 导入成功")
    
    print("4. 测试平台工具导入...")
    import platform_utils
    print("   ✅ platform_utils 导入成功")
    
    print("5. 测试ChromaDB客户端创建...")
    chroma_path = platform_utils.get_chroma_data_directory()
    print(f"   ChromaDB路径: {chroma_path}")
    
    client = chromadb.PersistentClient(path=str(chroma_path))
    print("   ✅ ChromaDB客户端创建成功")
    
    print("6. 测试数据清理工具创建...")
    cleanup_tool = DataCleanupTool(chroma_path, client)
    print("   ✅ 数据清理工具创建成功")
    
    print("7. 测试数据扫描...")
    analysis = cleanup_tool.scan_for_orphaned_data()
    print(f"   ✅ 数据扫描成功")
    print(f"   ChromaDB集合: {len(analysis['chromadb_collections'])}")
    print(f"   文件系统目录: {len(analysis['filesystem_dirs'])}")
    print(f"   孤立目录: {len(analysis['orphaned_dirs'])}")
    
    print("\n🎉 所有测试通过!")
    
except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
