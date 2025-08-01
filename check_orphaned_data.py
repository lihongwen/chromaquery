#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查孤立数据
"""

import os
from pathlib import Path

def calculate_directory_size(directory):
    """计算目录大小"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except:
                    pass
    except:
        pass
    return total_size

def main():
    print("检查ChromaDB数据目录中的孤立数据")
    print("=" * 40)
    
    chromadb_path = Path("chromadbdata")
    
    if not chromadb_path.exists():
        print("ChromaDB数据目录不存在")
        return
    
    # 获取所有UUID目录
    uuid_dirs = []
    for item in chromadb_path.iterdir():
        if item.is_dir() and len(item.name) == 36:  # UUID长度
            uuid_dirs.append(item)
    
    print(f"发现 {len(uuid_dirs)} 个UUID目录:")
    
    total_size = 0
    for uuid_dir in uuid_dirs:
        size = calculate_directory_size(uuid_dir)
        size_mb = size / (1024 * 1024)
        total_size += size
        print(f"  {uuid_dir.name}: {size_mb:.1f} MB")
    
    total_size_mb = total_size / (1024 * 1024)
    print(f"\n总计: {total_size_mb:.1f} MB")
    
    # 检查SQLite数据库大小
    sqlite_file = chromadb_path / "chroma.sqlite3"
    if sqlite_file.exists():
        sqlite_size = sqlite_file.stat().st_size / (1024 * 1024)
        print(f"SQLite数据库: {sqlite_size:.1f} MB")
        total_size_mb += sqlite_size
    
    print(f"ChromaDB总大小: {total_size_mb:.1f} MB")
    
    if len(uuid_dirs) > 2:  # 如果有超过2个目录，可能有孤立数据
        print(f"\n⚠️ 警告: 发现可能的数据臃肿!")
        print(f"   有 {len(uuid_dirs)} 个向量目录，但通常只需要1-2个")
        print(f"   建议运行数据清理工具检查")

if __name__ == "__main__":
    main()
