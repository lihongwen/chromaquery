#!/usr/bin/env python3
"""
紧急数据恢复脚本
用于立即解决当前的数据不一致问题
"""

import sys
import os
from pathlib import Path

# 添加backend目录到Python路径
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from data_recovery_tool import DataRecoveryTool
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主恢复流程"""
    print("🚨 ChromaDB紧急数据恢复工具")
    print("=" * 50)
    
    # 确定ChromaDB数据路径
    chroma_path = Path("chromadbdata")
    if not chroma_path.exists():
        print("❌ ChromaDB数据目录不存在，请检查路径")
        return
    
    print(f"📁 ChromaDB数据路径: {chroma_path.absolute()}")
    
    # 初始化恢复工具
    recovery_tool = DataRecoveryTool(chroma_path)
    
    # 扫描孤立的集合
    print("\n🔍 扫描孤立的集合数据...")
    orphaned_collections = recovery_tool.scan_orphaned_collections()
    
    if not orphaned_collections:
        print("✅ 未发现孤立的集合数据，系统状态正常")
        return
    
    print(f"⚠️  发现 {len(orphaned_collections)} 个孤立的集合数据")
    
    # 显示详细信息
    print("\n📋 孤立集合详情:")
    for i, collection in enumerate(orphaned_collections, 1):
        print(f"  {i}. ID: {collection['collection_id'][:20]}...")
        print(f"     大小: {collection['estimated_size_mb']:.2f} MB")
        print(f"     估计文档数: {collection['estimated_document_count']}")
        print(f"     可恢复: {'是' if collection['recoverable'] else '否'}")
        print()
    
    # 生成恢复计划
    print("📝 生成恢复计划...")
    recovery_plan = recovery_tool.generate_recovery_plan(orphaned_collections)
    
    if not recovery_plan:
        print("❌ 没有可恢复的数据")
        return
    
    print(f"✅ 生成恢复计划，包含 {len(recovery_plan)} 个可恢复集合")
    
    # 询问用户是否执行恢复
    print("\n🤔 是否执行数据恢复？")
    print("   这将尝试恢复所有可恢复的集合数据")
    print("   恢复过程是安全的，不会影响现有数据")
    
    while True:
        choice = input("\n请选择 (y/n): ").lower().strip()
        if choice in ['y', 'yes', '是']:
            break
        elif choice in ['n', 'no', '否']:
            print("❌ 用户取消恢复操作")
            return
        else:
            print("请输入 y 或 n")
    
    # 执行恢复
    print("\n🔧 开始执行数据恢复...")
    results = recovery_tool.batch_recover_collections(recovery_plan)
    
    # 显示结果
    print("\n📊 恢复结果:")
    print(f"  总计: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")
    
    if results['success'] > 0:
        print(f"\n✅ 成功恢复 {results['success']} 个集合！")
        print("   请刷新你的应用界面查看恢复的集合")
    
    if results['failed'] > 0:
        print(f"\n❌ {results['failed']} 个集合恢复失败")
        print("   请查看日志了解详细错误信息")
    
    # 显示恢复的集合详情
    if results['details']:
        print("\n📋 详细结果:")
        for detail in results['details']:
            status = "✅" if detail['success'] else "❌"
            print(f"  {status} {detail['display_name']} ({detail['collection_id'][:8]}...)")
    
    print("\n🎉 恢复操作完成！")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 恢复过程出错: {e}")
        logger.exception("恢复过程异常")
