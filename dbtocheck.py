#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
dbtocheck.py - 数据库主键重复检查工具

功能：
1. 检查 barcode_cache.db 数据库中 products 表的主键重复
2. 显示重复的条码和重复次数
3. 显示重复记录的详细信息
4. 提供修复选项（删除重复记录）

使用方法：
python dbtocheck.py

注意：主键（barcode字段）应该是唯一的，重复的主键会导致数据完整性问题。
"""

import sqlite3
import os

def check_database_exists():
    """检查数据库文件是否存在"""
    return os.path.exists('barcode_cache.db')

def check_duplicate_primary_keys():
    """检查主键重复并显示详细信息"""
    if not check_database_exists():
        print("错误：数据库文件 barcode_cache.db 不存在")
        return
    
    conn = None
    try:
        conn = sqlite3.connect('barcode_cache.db')
        cursor = conn.cursor()
        
        # 查找重复的条码
        print("正在检查主键重复...")
        cursor.execute('''
            SELECT barcode, COUNT(*) as count 
            FROM products 
            GROUP BY barcode 
            HAVING COUNT(*) > 1
        ''')
        duplicates = cursor.fetchall()
        
        # 查找无效的条码格式（非纯数字）
        print("正在检查无效条码格式...")
        cursor.execute('''
            SELECT barcode, product_name 
            FROM products 
            WHERE barcode IS NOT NULL 
            AND barcode != '' 
            AND barcode GLOB '*[^0-9]*'
        ''')
        invalid_barcodes = cursor.fetchall()
        
        if not duplicates and not invalid_barcodes:
            print("✓ 没有发现重复主键")
            print("✓ 没有发现无效条码格式")
            return
        
        if duplicates:
            print(f"\n❌ 发现 {len(duplicates)} 个重复主键:")
            print("=" * 60)
            
            total_duplicate_records = 0
            
            for barcode, count in duplicates:
                print(f"\n条码: {barcode}")
                print(f"重复次数: {count}")
                print("-" * 40)
                
                # 显示重复记录的详细信息
                cursor.execute('SELECT rowid, barcode, product_name, image_url, image_filepath FROM products WHERE barcode = ?', (barcode,))
                records = cursor.fetchall()
                
                for i, record in enumerate(records, 1):
                    rowid, barcode, product_name, image_url, image_filepath = record
                    print(f"  记录 {i} (rowid: {rowid}):")
                    print(f"    产品名称: {product_name}")
                    print(f"    图片URL: {image_url}")
                    print(f"    图片路径: {image_filepath}")
                    print()
                
                total_duplicate_records += (count - 1)  # 每个重复条码有 count-1 个多余记录
            
            print("=" * 60)
            print(f"重复总计: {len(duplicates)} 个重复条码, {total_duplicate_records} 条多余记录")
        
        if invalid_barcodes:
            print(f"\n⚠️  发现 {len(invalid_barcodes)} 个无效条码格式（包含非数字字符）:")
            print("=" * 60)
            
            for i, (barcode, product_name) in enumerate(invalid_barcodes[:20], 1):  # 只显示前20个
                print(f"{i}. 条码: '{barcode}', 产品: {product_name}")
            
            if len(invalid_barcodes) > 20:
                print(f"... 还有 {len(invalid_barcodes) - 20} 个无效条码未显示")
            
            print("=" * 60)
            print("这些无效条码可能在导出到Excel时产生问题")
        
        # 提供修复选项
        if duplicates:
            print(f"\n是否要修复重复记录？")
            print("1. 自动删除重复记录（保留rowid最小的记录）")
            print("2. 手动选择要保留的记录")
            print("3. 退出不修复")
            
            choice = input("请选择操作 (1/2/3): ").strip()
            
            if choice == '1':
                fix_duplicates_auto(conn)
            elif choice == '2':
                fix_duplicates_manual(conn, duplicates)
            else:
                print("已退出，未进行修复操作")
        else:
            print("\n虽然没有重复主键，但存在无效条码格式，这可能导致导出问题")
            
    except Exception as e:
        print(f"错误：检查数据库时发生异常：{e}")
    finally:
        if conn:
            conn.close()

def fix_duplicates_auto(conn):
    """自动修复重复记录 - 保留rowid最小的记录"""
    cursor = conn.cursor()
    try:
        # 删除重复记录，只保留每个条码的第一个记录（rowid最小）
        cursor.execute('''
            DELETE FROM products 
            WHERE rowid NOT IN (
                SELECT MIN(rowid) 
                FROM products 
                GROUP BY barcode
            )
        ''')
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"✓ 已自动删除 {deleted_count} 条重复记录")
        print("✓ 每个条码只保留了最早的记录（rowid最小）")
        
    except Exception as e:
        print(f"错误：自动修复失败：{e}")
        conn.rollback()

def fix_duplicates_manual(conn, duplicates):
    """手动修复重复记录"""
    print("\n手动修复功能尚未实现")
    print("请先使用自动修复或直接操作数据库")

def main():
    """主函数"""
    print("=== 数据库主键重复检查工具 ===")
    check_duplicate_primary_keys()

if __name__ == "__main__":
    main()
