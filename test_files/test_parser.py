#!/usr/bin/env python3
"""
文件解析器测试脚本
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from file_parsers import file_parser_manager, FileFormat
import tempfile

def test_text_file():
    """测试文本文件解析"""
    print("=== 测试文本文件解析 ===")
    
    content = """这是一个测试文本文件。

包含多个段落的内容。

第三个段落，用于测试分块功能。"""
    
    result = file_parser_manager.parse_file(content.encode('utf-8'), 'test.txt')
    
    print(f"解析结果: {result.success}")
    print(f"文件格式: {result.file_format}")
    print(f"内容长度: {len(result.content)}")
    print(f"元数据: {result.metadata}")
    if result.success:
        print(f"提取的内容: {result.content[:100]}...")
    else:
        print(f"错误信息: {result.error_message}")
    print()

def test_markdown_file():
    """测试Markdown文件解析"""
    print("=== 测试Markdown文件解析 ===")
    
    content = """# 测试Markdown文档

这是一个**测试**文档。

## 第二级标题

- 列表项1
- 列表项2
- 列表项3

### 代码示例

```python
print("Hello, World!")
```

这是一个包含多种Markdown元素的测试文档。"""
    
    result = file_parser_manager.parse_file(content.encode('utf-8'), 'test.md')
    
    print(f"解析结果: {result.success}")
    print(f"文件格式: {result.file_format}")
    print(f"内容长度: {len(result.content)}")
    print(f"元数据: {result.metadata}")
    if result.success:
        print(f"提取的内容: {result.content[:200]}...")
    else:
        print(f"错误信息: {result.error_message}")
    print()

def test_csv_file():
    """测试CSV文件解析"""
    print("=== 测试CSV文件解析 ===")
    
    content = """姓名,年龄,职业,描述
张三,25,工程师,负责软件开发工作
李四,30,设计师,专注用户界面设计
王五,28,产品经理,负责产品规划和管理
赵六,35,数据分析师,进行数据挖掘和分析工作"""
    
    result = file_parser_manager.parse_file(content.encode('utf-8'), 'test.csv')
    
    print(f"解析结果: {result.success}")
    print(f"文件格式: {result.file_format}")
    print(f"是否为表格: {result.is_table}")
    print(f"内容长度: {len(result.content)}")
    print(f"元数据: {result.metadata}")
    if result.success:
        print(f"提取的内容: {result.content[:300]}...")
        if result.table_data:
            print(f"表格数据行数: {len(result.table_data)}")
            print(f"列分析: {result.column_analysis}")
    else:
        print(f"错误信息: {result.error_message}")
    print()

def test_unsupported_file():
    """测试不支持的文件格式"""
    print("=== 测试不支持的文件格式 ===")
    
    content = b"This is a test file"
    result = file_parser_manager.parse_file(content, 'test.xyz')
    
    print(f"解析结果: {result.success}")
    print(f"错误信息: {result.error_message}")
    print()

def test_supported_formats():
    """测试支持的格式列表"""
    print("=== 支持的文件格式 ===")
    
    formats = file_parser_manager.get_supported_formats()
    extensions = file_parser_manager.get_supported_extensions()
    
    print(f"支持的格式数量: {len(formats)}")
    print(f"支持的格式: {[f.value for f in formats]}")
    print(f"支持的扩展名: {extensions}")
    print()

def main():
    """主测试函数"""
    print("开始文件解析器测试...\n")
    
    test_supported_formats()
    test_text_file()
    test_markdown_file()
    test_csv_file()
    test_unsupported_file()
    
    print("测试完成！")

if __name__ == "__main__":
    main()
