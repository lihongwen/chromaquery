#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终测试：验证数据清理功能
"""

import sys
import os
from pathlib import Path

# 添加backend目录到Python路径
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def main():
    try:
        print("最终数据清理功能验证")
        print("=" * 30)
        
        # 导入模块
        import chromadb
        from platform_utils import PlatformUtils
        from data_cleanup_tool import DataCleanupTool
        
        # 初始化
        chroma_path = PlatformUtils.get_chroma_data_directory()
        client = chromadb.PersistentClient(path=str(chroma_path))
        cleanup_tool = DataCleanupTool(chroma_path, client)
        
        # 执行扫描
        print("执行数据扫描...")
        analysis = cleanup_tool.scan_for_orphaned_data()
        
        # 显示结果
        print("扫描结果:")
        print(f"  ChromaDB集合: {len(analysis['chromadb_collections'])}")
        print(f"  文件系统目录: {len(analysis['filesystem_dirs'])}")
        print(f"  孤立目录: {len(analysis['orphaned_dirs'])}")
        print(f"  孤立数据库记录: {len(analysis['orphaned_db_records'])}")
        print(f"  孤立数据大小: {analysis['total_orphaned_size_mb']:.1f} MB")
        print(f"  需要清理: {analysis['summary']['cleanup_needed']}")
        
        # 如果有孤立数据，执行清理预演
        if analysis['summary']['cleanup_needed']:
            print("\n执行清理预演...")
            cleanup_result = cleanup_tool.cleanup_orphaned_data(dry_run=True)
            print(f"  预计清理项目: {len(cleanup_result['cleaned_items'])}")
            print(f"  预计清理大小: {cleanup_result['total_cleaned_size_mb']:.1f} MB")
        
        print("\n功能验证完成!")
        return True
        
    except Exception as e:
        print(f"验证失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    print(f"\n结果: {'成功' if success else '失败'}")
