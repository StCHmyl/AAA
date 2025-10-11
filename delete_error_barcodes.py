import sqlite3
import pandas as pd

def main():
    # 读取Excel文件获取错误barcode列表
    error_barcodes = pd.read_excel('db_export_filtered.xlsx').iloc[:, 0].tolist()
    
    # 连接数据库
    conn = sqlite3.connect('barcode_cache.db')
    cursor = conn.cursor()
    
    # 构建删除语句
    delete_sql = "DELETE FROM products WHERE barcode = ?"
    
    # 执行批量删除
    deleted_count = 0
    for barcode in error_barcodes:
        
        cursor.execute(delete_sql, (str(barcode),))
        deleted_count += cursor.rowcount
    
    # 提交事务并关闭连接
    conn.commit()
    conn.close()
    
    print(f"成功删除 {deleted_count} 条错误barcode记录")

if __name__ == "__main__":
    main()
