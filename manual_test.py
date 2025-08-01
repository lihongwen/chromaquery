#!/usr/bin/env python3
"""
手动测试数据清理功能
"""

import sys
import os
from pathlib import Path

# 添加backend目录到Python路径
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def main():
    try:
        # 导入必要的模块
        import chromadb
        import platform_utils
        from data_cleanup_tool import DataCleanupTool
        
        print("🚀 手动测试数据清理功能")
        print("=" * 40)
        
        # 1. 初始化ChromaDB客户端
        print("1. 初始化ChromaDB客户端...")
        chroma_path = platform_utils.get_chroma_data_directory()
        client = chromadb.PersistentClient(path=str(chroma_path))
        print(f"   ChromaDB路径: {chroma_path}")
        
        # 2. 创建数据清理工具
        print("2. 创建数据清理工具...")
        cleanup_tool = DataCleanupTool(chroma_path, client)
        
        # 3. 扫描孤立数据
        print("3. 扫描孤立数据...")
        analysis = cleanup_tool.scan_for_orphaned_data()
        
        print("✅ 扫描完成!")
        print(f"📊 扫描结果:")
        print(f"   ChromaDB集合: {len(analysis['chromadb_collections'])} 个")
        print(f"   文件系统目录: {len(analysis['filesystem_dirs'])} 个")
        print(f"   数据库记录: {len(analysis['database_records'])} 个")
        print(f"   孤立目录: {len(analysis['orphaned_dirs'])} 个")
        print(f"   孤立数据库记录: {len(analysis['orphaned_db_records'])} 个")
        print(f"   缺失目录: {len(analysis['missing_dirs'])} 个")
        print(f"   孤立数据大小: {analysis['total_orphaned_size_mb']:.1f} MB")
        
        # 4. 显示详细信息
        if analysis['chromadb_collections']:
            print(f"\n📋 ChromaDB集合:")
            for collection_name in analysis['chromadb_collections']:
                print(f"   - {collection_name}")
        
        if analysis['orphaned_dirs']:
            print(f"\n⚠️ 孤立目录:")
            for dir_name in analysis['orphaned_dirs']:
                size_mb = analysis['orphaned_sizes'].get(dir_name, 0) / (1024 * 1024)
                print(f"   - {dir_name} ({size_mb:.1f} MB)")
        
        if analysis['orphaned_db_records']:
            print(f"\n⚠️ 孤立数据库记录:")
            for record in analysis['orphaned_db_records']:
                print(f"   - {record}")
        
        # 5. 生成清理报告
        print(f"\n4. 生成清理报告...")
        report = cleanup_tool.get_cleanup_report()
        
        print(f"📄 清理报告:")
        print(f"   生成时间: {report['timestamp']}")
        print(f"   需要清理: {report['summary']['cleanup_needed']}")
        
        if report['recommendations']:
            print(f"\n💡 建议:")
            for rec in report['recommendations']:
                print(f"   - {rec}")
        
        # 6. 清理预演
        if analysis['summary']['cleanup_needed']:
            print(f"\n5. 执行清理预演...")
            cleanup_result = cleanup_tool.cleanup_orphaned_data(dry_run=True)
            
            print(f"🧪 预演结果:")
            print(f"   处理项目: {len(cleanup_result['cleaned_items'])} 个")
            print(f"   预计清理大小: {cleanup_result['total_cleaned_size_mb']:.1f} MB")
            
            if cleanup_result['cleaned_items']:
                print(f"\n📝 清理项目:")
                for item in cleanup_result['cleaned_items']:
                    action = item.get('action', 'unknown')
                    name = item.get('name', 'unknown')
                    size = item.get('size_mb', 0)
                    item_type = item.get('type', 'unknown')
                    
                    if action == 'would_delete':
                        print(f"   - 将删除 {item_type}: {name} ({size:.1f} MB)")
        else:
            print(f"\n✅ 数据状态良好，无需清理")
        
        print(f"\n🎉 测试完成!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ 数据清理功能测试通过!")
    else:
        print("\n❌ 数据清理功能测试失败!")
