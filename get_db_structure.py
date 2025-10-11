import sqlite3
import pandas as pd

def main():
    # 连接数据库
    conn = sqlite3.connect('barcode_cache.db')
    cursor = conn.cursor()
    
    # 获取所有表名
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print("数据库中的表:")
    for table in tables:
        print(f"- {table[0]}")
        
        # 获取表结构
        columns = cursor.execute(f"PRAGMA table_info({table[0]})").fetchall()
        print("  表结构:")
        for col in columns:
            print(f"  - {col[1]}: {col[2]}")
    
    conn.close()

if __name__ == "__main__":
    main()
