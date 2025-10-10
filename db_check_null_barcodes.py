#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
check_null_barcodes.py - 检查数据库中的空条码记录
"""

import sqlite3

def check_null_barcodes():
    """检查数据库中的空条码记录"""
    conn = sqlite3.connect('barcode_cache.db')
    cursor = conn.cursor()
    
    # 统计空条码记录
    cursor.execute('SELECT COUNT(*) FROM products WHERE barcode IS NULL OR barcode = ""')
    null_count = cursor.fetchone()[0]
    print(f'空条码记录数: {null_count}')
    
    # 查看前几条空条码记录
    if null_count > 0:
        cursor.execute('SELECT rowid, barcode, product_name FROM products WHERE barcode IS NULL OR barcode = "" LIMIT 10')
        null_records = cursor.fetchall()
        print('\n前10条空条码记录:')
        for row in null_records:
            print(f'rowid: {row[0]}, barcode: "{row[1]}", product_name: {row[2]}')
    
    conn.close()

if __name__ == "__main__":
    check_null_barcodes()
