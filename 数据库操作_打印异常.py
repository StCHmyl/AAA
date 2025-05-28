import sqlite3

def print_database_content(db_path):
    try:
        # 连接到数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        if not tables:
            print("数据库中没有表。")
            return

        # 遍历每个表并检查每一行是否有错误数据
        for table_name in tables:
            table_name = table_name[0]
            print(f"\\n表: {table_name}")
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [info[1] for info in cursor.fetchall()]
            if len(columns) >= 2:
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                for row in rows:
                    if 'N/A' in row or 'webp' in row:
                        print(f"发现错误数据: {row}")

        # 关闭连接
        conn.close()
    except Exception as e:
        print(f"发生错误: {e}")

# 调用函数
if __name__ == "__main__":
    print_database_content("barcode_cache.db")
