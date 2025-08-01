#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接清理孤立数据
"""

import sys
import os
from pathlib import Path

# 添加backend目录到Python路径
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def main():
    try:
        print("开始清理孤立数据")
        print("=" * 30)
        
        # 导入模块
        import chromadb
        from platform_utils import PlatformUtils
        from data_cleanup_tool import DataCleanupTool
        
        # 初始化
        chroma_path = PlatformUtils.get_chroma_data_directory()
        client = chromadb.PersistentClient(path=str(chroma_path))
        cleanup_tool = DataCleanupTool(chroma_path, client)
        
        # 1. 扫描孤立数据
        print("1. 扫描孤立数据...")
        analysis = cleanup_tool.scan_for_orphaned_data()
        
        print(f"扫描结果:")
        print(f"  ChromaDB集合: {len(analysis['chromadb_collections'])}")
        print(f"  文件系统目录: {len(analysis['filesystem_dirs'])}")
        print(f"  孤立目录: {len(analysis['orphaned_dirs'])}")
        print(f"  孤立数据大小: {analysis['total_orphaned_size_mb']:.1f} MB")
        
        if not analysis['summary']['cleanup_needed']:
            print("没有需要清理的孤立数据")
            return True
        
        # 2. 显示将要清理的数据
        print(f"\n2. 将要清理的孤立数据:")
        for dir_name in analysis['orphaned_dirs']:
            size_mb = analysis['orphaned_sizes'].get(dir_name, 0) / (1024 * 1024)
            print(f"  - {dir_name}: {size_mb:.1f} MB")
        
        # 3. 执行实际清理
        print(f"\n3. 执行清理...")
        cleanup_result = cleanup_tool.cleanup_orphaned_data(dry_run=False)
        
        if cleanup_result['success']:
            print(f"清理完成!")
            print(f"  处理项目: {len(cleanup_result['cleaned_items'])}")
            print(f"  清理大小: {cleanup_result['total_cleaned_size_mb']:.1f} MB")
            
            # 显示清理详情
            for item in cleanup_result['cleaned_items']:
                action = item.get('action', 'unknown')
                name = item.get('name', 'unknown')
                size = item.get('size_mb', 0)
                item_type = item.get('type', 'unknown')
                
                if action == 'deleted':
                    print(f"  ✓ 已删除 {item_type}: {name} ({size:.1f} MB)")
                elif action == 'failed':
                    print(f"  ✗ 删除失败 {item_type}: {name} - {item.get('error', '')}")
        else:
            print(f"清理失败: {cleanup_result.get('message', '未知错误')}")
            return False
        
        # 4. 验证清理结果
        print(f"\n4. 验证清理结果...")
        final_analysis = cleanup_tool.scan_for_orphaned_data()
        
        print(f"清理后状态:")
        print(f"  孤立目录: {len(final_analysis['orphaned_dirs'])}")
        print(f"  孤立数据大小: {final_analysis['total_orphaned_size_mb']:.1f} MB")
        
        if len(final_analysis['orphaned_dirs']) == 0:
            print("✓ 所有孤立数据已清理完成!")
        else:
            print(f"⚠ 仍有 {len(final_analysis['orphaned_dirs'])} 个孤立目录")
        
        return True
        
    except Exception as e:
        print(f"清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    
    print("\n" + "=" * 30)
    if success:
        print("数据清理完成!")
    else:
        print("数据清理失败!")
