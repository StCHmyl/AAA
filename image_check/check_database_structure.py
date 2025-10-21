import sqlite3
import json
import os

def get_database_structure():
    """获取数据库结构并保存到JSON文件"""
    db_path = "../barcode_cache.db"
    output_file = "database_structure.json"
    
    # 检查数据库文件是否存在
    if not os.path.exists(db_path):
        print(f"错误：数据库文件 '{db_path}' 不存在")
        return
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        database_structure = {
            "database_path": db_path,
            "tables": {}
        }
        
        # 获取每个表的结构
        for table in tables:
            table_name = table[0]
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            # 获取表数据量
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            row_count = cursor.fetchone()[0]
            
            # 获取索引信息
            cursor.execute(f"PRAGMA index_list({table_name});")
            indexes = cursor.fetchall()
            
            table_structure = {
                "columns": [],
                "row_count": row_count,
                "indexes": []
            }
            
            # 处理列信息
            for column in columns:
                column_info = {
                    "cid": column[0],
                    "name": column[1],
                    "type": column[2],
                    "notnull": bool(column[3]),
                    "default_value": column[4],
                    "pk": bool(column[5])
                }
                table_structure["columns"].append(column_info)
            
            # 处理索引信息
            for index in indexes:
                index_name = index[1]
                cursor.execute(f"PRAGMA index_info({index_name});")
                index_columns = cursor.fetchall()
                
                index_info = {
                    "name": index_name,
                    "unique": bool(index[2]),
                    "columns": [col[2] for col in index_columns]
                }
                table_structure["indexes"].append(index_info)
            
            database_structure["tables"][table_name] = table_structure
        
        # 保存到JSON文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(database_structure, f, ensure_ascii=False, indent=2)
        
        print(f"数据库结构已保存到 {output_file}")
        
        # 打印摘要信息
        print(f"\n数据库摘要：")
        print(f"数据库路径：{db_path}")
        print(f"表数量：{len(tables)}")
        for table_name, structure in database_structure["tables"].items():
            print(f"  - {table_name}: {structure['row_count']} 行, {len(structure['columns'])} 列")
        
        # 显示表结构示例
        if tables:
            first_table = tables[0][0]
            print(f"\n表 '{first_table}' 的结构示例：")
            for column in database_structure["tables"][first_table]["columns"]:
                print(f"  - {column['name']} ({column['type']})")
        
    except sqlite3.Error as e:
        print(f"数据库错误：{e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    get_database_structure()
