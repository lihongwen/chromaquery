#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动清理孤立数据
"""

import sys
import os
import shutil
from pathlib import Path

# 添加backend目录到Python路径
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def main():
    try:
        print("手动清理孤立数据")
        print("=" * 30)
        
        # 导入模块
        import chromadb
        from platform_utils import PlatformUtils
        
        # 初始化
        chroma_path = PlatformUtils.get_chroma_data_directory()
        client = chromadb.PersistentClient(path=str(chroma_path))
        
        # 1. 获取ChromaDB中的活跃集合
        print("1. 获取ChromaDB中的活跃集合...")
        collections = client.list_collections()
        active_collection_ids = set()
        
        for collection in collections:
            active_collection_ids.add(collection.name)
            metadata = collection.metadata or {}
            display_name = metadata.get('original_name', collection.name)
            print(f"  活跃集合: {display_name} (ID: {collection.name})")
        
        print(f"  总计: {len(active_collection_ids)} 个活跃集合")
        
        # 2. 扫描文件系统中的目录
        print("\n2. 扫描文件系统中的目录...")
        filesystem_dirs = set()
        
        for item in chroma_path.iterdir():
            if item.is_dir() and len(item.name) == 36:  # UUID长度
                filesystem_dirs.add(item.name)
        
        print(f"  文件系统目录: {len(filesystem_dirs)} 个")
        
        # 3. 找出孤立目录
        orphaned_dirs = filesystem_dirs - active_collection_ids
        print(f"\n3. 发现孤立目录: {len(orphaned_dirs)} 个")
        
        if not orphaned_dirs:
            print("  没有孤立目录需要清理")
            return True
        
        # 4. 计算孤立数据大小
        total_size = 0
        for dir_name in orphaned_dirs:
            dir_path = chroma_path / dir_name
            try:
                size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                size_mb = size / (1024 * 1024)
                total_size += size
                print(f"  - {dir_name}: {size_mb:.1f} MB")
            except Exception as e:
                print(f"  - {dir_name}: 计算大小失败 ({e})")
        
        total_size_mb = total_size / (1024 * 1024)
        print(f"\n  总计孤立数据: {total_size_mb:.1f} MB")
        
        # 5. 执行清理
        print(f"\n4. 开始清理孤立目录...")
        cleaned_count = 0
        cleaned_size = 0
        
        for dir_name in orphaned_dirs:
            dir_path = chroma_path / dir_name
            try:
                # 计算大小
                size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                
                # 删除目录
                shutil.rmtree(dir_path)
                
                cleaned_count += 1
                cleaned_size += size
                size_mb = size / (1024 * 1024)
                print(f"  ✓ 已删除: {dir_name} ({size_mb:.1f} MB)")
                
            except Exception as e:
                print(f"  ✗ 删除失败: {dir_name} - {e}")
        
        cleaned_size_mb = cleaned_size / (1024 * 1024)
        print(f"\n清理完成:")
        print(f"  删除目录: {cleaned_count} 个")
        print(f"  释放空间: {cleaned_size_mb:.1f} MB")
        
        # 6. 验证清理结果
        print(f"\n5. 验证清理结果...")
        remaining_dirs = []
        for item in chroma_path.iterdir():
            if item.is_dir() and len(item.name) == 36:
                remaining_dirs.append(item.name)
        
        remaining_orphaned = set(remaining_dirs) - active_collection_ids
        
        print(f"  剩余目录: {len(remaining_dirs)} 个")
        print(f"  剩余孤立目录: {len(remaining_orphaned)} 个")
        
        if len(remaining_orphaned) == 0:
            print("  ✓ 所有孤立目录已清理完成!")
        else:
            print(f"  ⚠ 仍有 {len(remaining_orphaned)} 个孤立目录")
            for dir_name in remaining_orphaned:
                print(f"    - {dir_name}")
        
        return len(remaining_orphaned) == 0
        
    except Exception as e:
        print(f"清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    
    print("\n" + "=" * 30)
    if success:
        print("手动清理完成!")
    else:
        print("手动清理失败!")
