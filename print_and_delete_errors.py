import sqlite3

def print_and_delete_errors(db_path, barcode_to_search=None):
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

        # 遍历每个表，检测是否存在要删除的行，如果存在则删除，并确认删除结果
        for table_name in tables:
            table_name = table_name[0]
            print(f"\n表: {table_name}")
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [info[1] for info in cursor.fetchall()]

            error_rows = [
                (barcode_to_search, 'N/A', 'https://www.barcodelookup.com/assets/images/search-again.webp', None),
            ]

            for error_row in error_rows:
                # 如果指定了要搜索的条形码，则只搜索该条形码
                if barcode_to_search and error_row[0] != barcode_to_search:
                    continue

                # 检查行是否存在
                sql_select = f"SELECT COUNT(*) FROM {table_name} WHERE barcode = ?"
                cursor.execute(sql_select, (error_row[0],))
                count = cursor.fetchone()[0]

                if count > 0:
                    # 确认是否删除
                    user_input = input(f"确认要删除行: {error_row} 从表: {table_name} 吗? (y/n): ")
                    if user_input.lower() == 'y':
                        # 删除行
                        sql_delete = f"DELETE FROM {table_name} WHERE barcode = ?"
                        print(f"执行 SQL: {sql_delete}，参数: {(error_row[0],)}")
                        cursor.execute(sql_delete, (error_row[0],))
                        conn.commit()

                        # 确认是否删除成功
                        cursor.execute(sql_select, (error_row[0],))
                        count_after_delete = cursor.fetchone()[0]

                        if count_after_delete == 0:
                            print(f"已成功删除行: {error_row} 从表: {table_name}")
                        else:
                            raise Exception(f"删除行: {error_row} 从表: {table_name} 失败，删除后仍然存在")
                    else:
                        print(f"已取消删除行: {error_row} 从表: {table_name}")
                else:
                    print(f"未找到行: {error_row} 在表: {table_name} 中")

        # 关闭连接
        conn.close()
    except Exception as e:
        print(f"发生错误: {e}")

# 调用函数
if __name__ == "__main__":
    barcode_to_search = input("请输入要删除的条码: ")
    print_and_delete_errors("barcode_cache.db", barcode_to_search)
