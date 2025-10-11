#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
check_barcode_issues.py - 检查barcode_cache.db数据库中的条码数据问题
"""

import sqlite3
import re

def check_barcode_issues():
    """检查条码数据问题"""
    conn = sqlite3.connect('barcode_cache.db')
    cursor = conn.cursor()
    
    # 获取所有条码
    cursor.execute('SELECT barcode FROM products')
    barcodes = [row[0] for row in cursor.fetchall()]
    
    print(f'总条码数: {len(barcodes)}')
    
    # 检查空字符串、空格、特殊字符
    empty_count = 0
    whitespace_count = 0
    special_char_count = 0
    non_numeric_count = 0
    
    problematic_barcodes = []
    
    for barcode in barcodes:
        if barcode is None:
            empty_count += 1
            problematic_barcodes.append((barcode, "None"))
        elif barcode.strip() == "":
            empty_count += 1
            problematic_barcodes.append((barcode, "空字符串"))
        elif barcode != barcode.strip():
            whitespace_count += 1
            problematic_barcodes.append((barcode, "前后空格"))
        elif not barcode.isdigit():
            non_numeric_count += 1
            problematic_barcodes.append((barcode, "非数字字符"))
        elif re.search(r'[^\x00-\x7F]', barcode):
            special_char_count += 1
            problematic_barcodes.append((barcode, "特殊字符"))
    
    print(f'空条码: {empty_count}')
    print(f'有前后空格的条码: {whitespace_count}')
    print(f'非数字条码: {non_numeric_count}')
    print(f'有特殊字符的条码: {special_char_count}')
    
    # 显示有问题的条码
    if problematic_barcodes:
        print(f'\n有问题的条码 (前100个):')
        for barcode, issue in problematic_barcodes[:100]:
            print(f'  "{barcode}" - 问题: {issue}')
    
    # 检查重复的条码（再次确认）
    cursor.execute('SELECT barcode, COUNT(*) FROM products GROUP BY barcode HAVING COUNT(*) > 1')
    duplicates = cursor.fetchall()
    print(f'\n重复条码数: {len(duplicates)}')
    
    if duplicates:
        for barcode, count in duplicates:
            print(f'  条码 "{barcode}": 重复 {count} 次')
    
    conn.close()

if __name__ == "__main__":
    check_barcode_issues()
