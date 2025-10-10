#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
dbtoadd.py - 数据库添加工具

功能：
1. 检查 barcode_cache.db 数据库是否存在
2. 如果数据库不存在，自动初始化数据库
3. 交互式询问用户要添加的产品信息
4. 将数据添加到数据库中

使用方法：
python dbtoadd.py

支持的字段：
- 条码 (barcode): 必需，主键
- 产品名称 (product_name): 可选
- 图片URL (image_url): 可选  
- 图片文件路径 (image_filepath): 可选

注意事项：
- 如果条码已存在，会提示用户是否覆盖
- 所有可选字段可以直接回车跳过
- 数据库结构遵循 barcode_excel_db.py 中的定义
"""

import sqlite3
import os
import sys

# 从现有文件导入数据库函数
sys.path.append('.')
from barcode_excel_db import init_database, insert_product_to_db

def check_database_exists():
    """检查数据库文件是否存在"""
    return os.path.exists('barcode_cache.db')

def get_user_input():
    """获取用户输入的产品信息"""
    print("\n=== 添加产品到数据库 ===")
    
    # 获取必需字段：条码
    barcode = input("请输入条码 (必需): ").strip()
    while not barcode:
        print("错误：条码不能为空！")
        barcode = input("请输入条码 (必需): ").strip()
    
    # 获取可选字段
    product_name = input("请输入产品名称 (可选，直接回车跳过): ").strip() or None
    image_url = input("请输入图片URL (可选，直接回车跳过): ").strip() or None
    image_filepath = input("请输入图片文件路径 (可选，直接回车跳过): ").strip() or None
    
    return {
        'barcode': barcode,
        'product_name': product_name,
        'image_url': image_url,
        'image_filepath': image_filepath
    }

def check_barcode_exists(barcode):
    """检查条码是否已存在"""
    conn = None
    try:
        conn = sqlite3.connect('barcode_cache.db')
        cursor = conn.cursor()
        cursor.execute('SELECT barcode FROM products WHERE barcode = ?', (barcode,))
        result = cursor.fetchone()
        return result is not None
    except Exception as e:
        print(f"错误：检查条码存在性失败：{e}")
        return False
    finally:
        if conn:
            conn.close()

def main():
    """主函数"""
    print("正在检查数据库...")
    
    # 检查数据库是否存在，如果不存在则初始化
    if not check_database_exists():
        print("数据库不存在，正在初始化...")
        init_database()
    else:
        print("数据库已存在")
    
    # 获取用户输入
    product_data = get_user_input()
    
    # 检查条码是否已存在
    if check_barcode_exists(product_data['barcode']):
        print(f"\n警告：条码 {product_data['barcode']} 已存在于数据库中！")
        choice = input("是否覆盖现有数据？(y/n): ").strip().lower()
        if choice != 'y':
            print("操作已取消")
            return
    
    # 插入数据到数据库
    print(f"\n正在插入数据到数据库...")
    insert_product_to_db(
        product_data['barcode'],
        product_data['product_name'],
        product_data['image_url'],
        product_data['image_filepath']
    )
    
    print("数据添加完成！")

if __name__ == "__main__":
    main()
