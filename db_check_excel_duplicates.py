#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
check_excel_duplicates.py - 检查被导出的Excel文件中的重复内容

功能：
1. 检查导出的Excel文件中是否有重复的行
2. 检查是否有重复的条码（尽管数据库中没有）
3. 帮助诊断导出过程中的问题
"""

import openpyxl
import pandas as pd
from collections import Counter

def check_excel_duplicates(excel_file='db_export.xlsx'):
    """检查Excel文件中的重复内容"""
    try:
        # 使用pandas读取Excel文件
        print("正在读取Excel文件...")
        df = pd.read_excel(excel_file, sheet_name='products')
        
        print(f"Excel文件行数: {len(df)}")
        print(f"Excel文件列数: {len(df.columns)}")
        print(f"列名: {list(df.columns)}")
        
        # 检查重复行（完全相同的行）
        duplicate_rows = df.duplicated()
        total_duplicate_rows = duplicate_rows.sum()
        print(f"\n完全重复的行数: {total_duplicate_rows}")
        
        if total_duplicate_rows > 0:
            print("重复的行索引:", df.index[duplicate_rows].tolist())
        
        # 检查条码重复（尽管数据库中没有）
        barcode_duplicates = df['barcode'].duplicated()
        total_barcode_duplicates = barcode_duplicates.sum()
        print(f"\n重复的条码数: {total_barcode_duplicates}")
        
        if total_barcode_duplicates > 0:
            duplicate_barcodes = df.loc[barcode_duplicates, 'barcode'].unique()
            print("重复的条码:", duplicate_barcodes)
            
            # 显示重复条码的详细信息
            for barcode in duplicate_barcodes[:5]:  # 只显示前5个
                duplicate_records = df[df['barcode'] == barcode]
                print(f"\n条码 {barcode} 的重复记录:")
                for idx, row in duplicate_records.iterrows():
                    print(f"  行 {idx}: {row.to_dict()}")
        
        # 检查空值
        print(f"\n空值统计:")
        for col in df.columns:
            null_count = df[col].isnull().sum()
            print(f"  {col}: {null_count} 个空值")
        
        # 检查数据类型的分布
        print(f"\n数据类型分布:")
        for col in df.columns:
            value_counts = df[col].value_counts().head(3)  # 显示前3个最常见的值
            print(f"  {col}:")
            for value, count in value_counts.items():
                print(f"    {value}: {count} 次")
            if len(df[col].value_counts()) > 3:
                print(f"    ... 还有 {len(df[col].value_counts()) - 3} 个其他值")
        
    except Exception as e:
        print(f"错误：检查Excel文件时发生异常：{e}")

def main():
    """主函数"""
    print("=== Excel文件重复内容检查工具 ===")
    check_excel_duplicates()

if __name__ == "__main__":
    main()
