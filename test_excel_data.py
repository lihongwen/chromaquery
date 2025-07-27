#!/usr/bin/env python3
"""
创建测试Excel文件来验证LLM列分析功能
"""

import pandas as pd
import os

def create_test_excel():
    """创建测试Excel文件"""
    
    # 创建测试数据
    data = {
        '产品ID': ['P001', 'P002', 'P003', 'P004', 'P005', 'P006', 'P007', 'P008', 'P009', 'P010'],
        '产品名称': [
            'iPhone 15 Pro Max',
            'MacBook Air M2',
            'iPad Pro 12.9',
            'Apple Watch Series 9',
            'AirPods Pro 2',
            'Mac Studio M2',
            'iPhone 14',
            'MacBook Pro 16',
            'iPad Air',
            'Apple TV 4K'
        ],
        '分类': ['手机', '笔记本', '平板', '智能手表', '耳机', '台式机', '手机', '笔记本', '平板', '媒体设备'],
        '价格': [9999, 8999, 6999, 2999, 1899, 14999, 5999, 18999, 4599, 1499],
        '库存数量': [50, 30, 25, 100, 200, 15, 80, 20, 60, 40],
        '产品描述': [
            '最新款iPhone，配备A17 Pro芯片，钛金属设计，支持5G网络，拍照功能强大',
            '轻薄便携的笔记本电脑，搭载M2芯片，续航时间长，适合办公和学习',
            '专业级平板电脑，12.9英寸Liquid Retina XDR显示屏，支持Apple Pencil',
            '智能手表，健康监测功能全面，支持心率、血氧、睡眠监测',
            '主动降噪无线耳机，音质出色，支持空间音频技术',
            '高性能台式机，适合专业创作者，视频编辑和3D渲染性能强劲',
            '上一代iPhone，性价比高，依然是优秀的智能手机选择',
            '专业级笔记本，16英寸屏幕，适合开发者和创意工作者',
            '中端平板电脑，性能均衡，价格适中，适合日常使用',
            '4K流媒体设备，支持杜比视界和杜比全景声，家庭娱乐首选'
        ],
        '上市时间': [
            '2023-09-15',
            '2022-07-15',
            '2022-10-18',
            '2023-09-12',
            '2022-09-23',
            '2022-06-03',
            '2022-09-16',
            '2023-01-17',
            '2022-03-18',
            '2022-11-04'
        ],
        '供应商': ['苹果', '苹果', '苹果', '苹果', '苹果', '苹果', '苹果', '苹果', '苹果', '苹果'],
        '状态': ['在售', '在售', '在售', '在售', '在售', '在售', '在售', '在售', '在售', '在售']
    }
    
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    # 保存为Excel文件
    output_path = 'test_products.xlsx'
    df.to_excel(output_path, index=False, engine='openpyxl')
    
    print(f"测试Excel文件已创建: {output_path}")
    print(f"数据行数: {len(df)}")
    print(f"列数: {len(df.columns)}")
    print("\n列名:")
    for i, col in enumerate(df.columns):
        print(f"{i+1}. {col}")
    
    print("\n前3行数据预览:")
    print(df.head(3).to_string())
    
    return output_path

if __name__ == "__main__":
    create_test_excel()
