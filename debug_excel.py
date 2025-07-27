#!/usr/bin/env python3
"""详细调试Excel文件解析和LLM分析问题"""

import sys
import os
import pandas as pd
sys.path.append('/Users/lihongwen/Projects/chromadb/chromadb-web-manager/backend')

from file_parsers import FileParserManager
import chromadb

def debug_excel_detailed():
    """详细调试Excel文件解析"""

    # 测试文件路径
    excel_file = "/Users/lihongwen/Desktop/工程顾问事业部法律纠纷案件台账.xlsx"

    if not os.path.exists(excel_file):
        print(f"文件不存在: {excel_file}")
        return

    print("=" * 80)
    print("1. 原始Excel文件分析")
    print("=" * 80)

    # 直接用pandas读取原始文件
    df_raw = pd.read_excel(excel_file, engine='openpyxl')
    print(f"原始文件行数: {len(df_raw)}")
    print(f"原始文件列数: {len(df_raw.columns)}")
    print(f"原始列名: {list(df_raw.columns)}")

    # 显示原始数据的前几行
    print("\n原始数据前5行:")
    for i, row in df_raw.head().iterrows():
        print(f"第{i+1}行: {dict(row)}")

    # 检查空行
    empty_rows = df_raw.isna().all(axis=1).sum()
    print(f"\n完全空行数量: {empty_rows}")

    # 检查有效数据行
    valid_rows = df_raw.dropna(how='all')
    print(f"去除空行后行数: {len(valid_rows)}")

    print("\n" + "=" * 80)
    print("2. 文件解析器分析")
    print("=" * 80)

    # 读取文件内容
    with open(excel_file, 'rb') as f:
        content = f.read()

    # 创建解析器管理器
    parser_manager = FileParserManager()
    filename = os.path.basename(excel_file)

    # 执行解析
    result = parser_manager.parse_file(content, filename)

    print(f"解析成功: {result.success}")
    print(f"是否为表格: {result.is_table}")

    if result.success and result.is_table:
        print(f"解析后表格行数: {len(result.table_data)}")
        print(f"列分析结果: {result.column_analysis}")

        # 显示每一行数据
        print("\n解析后的所有数据:")
        for i, row in enumerate(result.table_data):
            print(f"第{i+1}行: {row}")

        # 检查哪些行可能是无效的
        print("\n数据有效性分析:")
        for i, row in enumerate(result.table_data):
            non_null_count = sum(1 for v in row.values() if v is not None and str(v).strip() != '' and str(v) != 'nan')
            print(f"第{i+1}行: {non_null_count}个非空字段")

    print("\n" + "=" * 80)
    print("3. 数据库存储验证")
    print("=" * 80)

    # 检查数据库中的实际内容
    client = chromadb.PersistentClient(path='/Users/lihongwen/Projects/chromadb/chromadb-web-manager/data/chroma_data')
    collections = client.list_collections()

    if collections:
        collection = collections[0]
        print(f"集合名称: {collection.name}")
        print(f"文档数量: {collection.count()}")

        # 获取所有文档
        results = collection.get(include=['documents', 'metadatas'])
        print(f"实际获取到的文档数量: {len(results['ids'])}")

        # 分析每个文档的内容和元数据
        print("\n文档内容和元数据分析:")
        for i, (doc_id, document, metadata) in enumerate(zip(results['ids'], results['documents'], results['metadatas'])):
            print(f"\n文档 {i+1}:")
            print(f"  ID: {doc_id}")
            print(f"  内容长度: {len(document) if document else 0}")
            print(f"  内容预览: {document[:100] if document else 'None'}...")
            print(f"  元数据字段数: {len(metadata) if metadata else 0}")
            if metadata:
                print(f"  元数据字段: {list(metadata.keys())}")
                # 显示一些关键元数据
                for key, value in list(metadata.items())[:5]:
                    print(f"    {key}: {value}")

def debug_llm_analysis():
    """调试LLM列分析功能"""

    print("\n" + "=" * 80)
    print("4. LLM列分析功能调试")
    print("=" * 80)

    # 重新测试文件解析，看看LLM分析是否正常工作
    excel_file = "/Users/lihongwen/Desktop/工程顾问事业部法律纠纷案件台账.xlsx"
    with open(excel_file, 'rb') as f:
        content = f.read()

    # 创建解析器管理器
    parser_manager = FileParserManager()
    filename = os.path.basename(excel_file)

    print("重新测试Excel解析（启用LLM后）...")
    result = parser_manager.parse_file(content, filename)

    print(f"解析成功: {result.success}")
    print(f"是否为表格: {result.is_table}")

    if result.success and result.is_table:
        print(f"列分析结果: {result.column_analysis}")

        # 分析content和metadata的分类
        content_columns = [col for col, type_ in result.column_analysis.items() if type_ == 'content']
        metadata_columns = [col for col, type_ in result.column_analysis.items() if type_ == 'metadata']

        print(f"\nContent列 ({len(content_columns)}个): {content_columns}")
        print(f"Metadata列 ({len(metadata_columns)}个): {metadata_columns}")

        # 显示第一个文档的实际内容
        if result.table_data:
            first_row = result.table_data[0]
            print(f"\n第一行数据示例:")

            print(f"Content部分:")
            for col in content_columns:
                value = first_row.get(col, 'N/A')
                print(f"  {col}: {value}")

            print(f"\nMetadata部分（前5个）:")
            for col in metadata_columns[:5]:
                value = first_row.get(col, 'N/A')
                print(f"  {col}: {value}")

def test_llm_directly():
    """直接测试LLM功能"""
    print("\n" + "=" * 80)
    print("5. 直接测试LLM功能")
    print("=" * 80)

    try:
        from llm_client import get_llm_client
        import asyncio

        llm_client = get_llm_client()
        if llm_client:
            print("LLM客户端获取成功")

            # 测试简单的LLM调用
            test_messages = [
                {"role": "system", "content": "你是一个有用的AI助手。"},
                {"role": "user", "content": "请回答：1+1等于几？"}
            ]

            print("开始测试LLM流式调用...")

            async def test_stream():
                full_response = ""
                async for chunk in llm_client.stream_chat(test_messages):
                    if chunk.get('content'):
                        full_response += chunk['content']
                        print(f"收到块: {chunk['content']}", end='', flush=True)
                    elif chunk.get('finish_reason'):
                        print(f"\n完成原因: {chunk['finish_reason']}")
                        if chunk.get('error'):
                            print(f"错误: {chunk['error']}")
                        break

                print(f"\n完整响应: {full_response}")
                return full_response

            # 运行异步测试
            response = asyncio.run(test_stream())
            print(f"LLM测试成功，响应长度: {len(response)}")
        else:
            print("LLM客户端获取失败")

    except Exception as e:
        print(f"LLM测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_excel_detailed()
    debug_llm_analysis()
    test_llm_directly()
