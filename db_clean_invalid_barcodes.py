#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
clean_invalid_barcodes.py - 清理无效条码格式工具

功能：
1. 检测并显示无效的条码格式
2. 提供修复选项（删除无效记录或清理条码格式）
3. 帮助解决导出到Excel时的重复问题
"""

import sqlite3
import re

def get_invalid_barcodes():
    """获取所有无效条码记录"""
    conn = sqlite3.connect('barcode_cache.db')
    cursor = conn.cursor()
    
    # 查找无效的条码格式（非纯数字）
    cursor.execute('''
        SELECT rowid, barcode, product_name, image_url, image_filepath
        FROM products 
        WHERE barcode IS NOT NULL 
        AND barcode != '' 
        AND barcode GLOB '*[^0-9]*'
    ''')
    invalid_records = cursor.fetchall()
    
    conn.close()
    return invalid_records

def clean_barcode_format(barcode):
    """清理条码格式，提取数字部分"""
    if barcode is None:
        return None
    
    # 移除所有非数字字符
    cleaned = re.sub(r'[^\d]', '', barcode)
    
    # 如果清理后为空，返回None
    if cleaned == '':
        return None
    
    return cleaned

def show_invalid_records(records, limit=20):
    """显示无效记录"""
    print(f"发现 {len(records)} 个无效条码记录:")
    print("=" * 80)
    
    for i, (rowid, barcode, product_name, image_url, image_filepath) in enumerate(records[:limit], 1):
        cleaned = clean_barcode_format(barcode)
        print(f"{i}. rowid: {rowid}")
        print(f"   原始条码: '{barcode}'")
        print(f"   清理后: '{cleaned}'")
        print(f"   产品名称: {product_name}")
        print(f"   图片URL: {image_url}")
        print(f"   图片路径: {image_filepath}")
        print()
    
    if len(records) > limit:
        print(f"... 还有 {len(records) - limit} 个记录未显示")

def fix_invalid_barcodes():
    """修复无效条码"""
    records = get_invalid_barcodes()
    
    if not records:
        print("✓ 没有发现无效条码记录")
        return
    
    show_invalid_records(records)
    
    print("\n请选择修复选项:")
    print("1. 自动清理条码格式（提取数字部分）")
    print("2. 删除所有无效条码记录")
    print("3. 退出不修复")
    
    choice = input("请选择操作 (1/2/3): ").strip()
    
    if choice == '1':
        clean_barcode_format_option(records)
    elif choice == '2':
        delete_invalid_records(records)
    else:
        print("已退出，未进行修复操作")

def clean_barcode_format_option(records):
    """自动清理条码格式"""
    conn = sqlite3.connect('barcode_cache.db')
    cursor = conn.cursor()
    
    updated_count = 0
    deleted_count = 0
    
    try:
        for rowid, barcode, product_name, image_url, image_filepath in records:
            cleaned = clean_barcode_format(barcode)
            
            if cleaned is None:
                # 如果清理后为空，删除记录
                cursor.execute('DELETE FROM products WHERE rowid = ?', (rowid,))
                deleted_count += 1
                print(f"删除记录 rowid {rowid}: '{barcode}' -> 无效条码")
            else:
                # 检查清理后的条码是否已存在
                cursor.execute('SELECT COUNT(*) FROM products WHERE barcode = ? AND rowid != ?', (cleaned, rowid))
                exists_count = cursor.fetchone()[0]
                
                if exists_count > 0:
                    # 如果清理后的条码已存在，删除当前记录
                    cursor.execute('DELETE FROM products WHERE rowid = ?', (rowid,))
                    deleted_count += 1
                    print(f"删除记录 rowid {rowid}: '{barcode}' -> '{cleaned}' (已存在)")
                else:
                    # 更新条码格式
                    cursor.execute('UPDATE products SET barcode = ? WHERE rowid = ?', (cleaned, rowid))
                    updated_count += 1
                    print(f"更新记录 rowid {rowid}: '{barcode}' -> '{cleaned}'")
        
        conn.commit()
        print(f"\n✓ 修复完成:")
        print(f"  更新了 {updated_count} 个记录的条码格式")
        print(f"  删除了 {deleted_count} 个无效记录")
        
    except Exception as e:
        print(f"错误：修复失败：{e}")
        conn.rollback()
    finally:
        conn.close()

def delete_invalid_records(records):
    """删除所有无效记录"""
    conn = sqlite3.connect('barcode_cache.db')
    cursor = conn.cursor()
    
    try:
        for rowid, barcode, product_name, image_url, image_filepath in records:
            cursor.execute('DELETE FROM products WHERE rowid = ?', (rowid,))
            print(f"删除记录 rowid {rowid}: '{barcode}'")
        
        conn.commit()
        print(f"\n✓ 已删除 {len(records)} 个无效记录")
        
    except Exception as e:
        print(f"错误：删除失败：{e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    """主函数"""
    print("=== 无效条码清理工具 ===")
    print("检测并修复可能导致Excel导出问题的无效条码格式")
    print()
    
    fix_invalid_barcodes()

if __name__ == "__main__":
    main()
