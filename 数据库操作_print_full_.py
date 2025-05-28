import sqlite3

import threading

db_lock = threading.Lock()  # 定义全局数据库锁


def get_statistics():
    """
    获取每种UA和Stealth配置的使用统计，包括使用次数、成功次数和成功率
    """
    with db_lock:
        conn = sqlite3.connect("ua_stealth_usage.db")
        cursor = conn.cursor()

        stats = {}

        for record_type in ['UA', 'Stealth']:
            cursor.execute(f'''
                SELECT value,
                       COUNT(*) as total,
                       SUM(success) as success,
                       ROUND(1.0 * SUM(success) / COUNT(*), 2) as success_rate
                FROM usage_records
                WHERE type = ?
                GROUP BY value
                ORDER BY success_rate DESC, success DESC, total DESC
            ''', (record_type,))
            
            stats[record_type] = cursor.fetchall()
        
        conn.close()
        return stats

def print_best_configurations():
    stats = get_statistics()
    print("最优 User-Agent 配置:")
    for i, (value, total, success, rate) in enumerate(stats['UA'][:5], 1):
        print(f"{i}. 成功率: {rate:.2f} | 成功数: {success} | 总数: {total} | UA: {value}")

    print("\n最优 Stealth 配置:")
    for i, (value, total, success, rate) in enumerate(stats['Stealth'][:5], 1):
        print(f"{i}. 成功率: {rate:.2f} | 成功数: {success} | 总数: {total}")
        print(f"   配置: {value}")
    print("\n最差 User-Agent 配置:")
    for i, (value, total, success, rate) in enumerate(stats['UA'][-5:], 1):
        print(f"{i}. 成功率: {rate:.2f} | 成功数: {success} | 总数: {total} | UA: {value}")

    print("\n最差 Stealth 配置:")
    for i, (value, total, success, rate) in enumerate(stats['Stealth'][-5:], 1):
        print(f"{i}. 成功率: {rate:.2f} | 成功数: {success} | 总数: {total}")
        print(f"   配置: {value}")
def print_full_database(db_path):
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

        # 遍历每个表并打印所有行
        for table_name in tables:
            table_name = table_name[0]
            print(f"\\n表: {table_name}")
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            a=1
            for row in rows:
                a += 1
                if a % 100 == 0:
                    print(f"已打印 {a} 行数据")
                print(row)
     
            print(f"表 {table_name} 中共有 {len(rows)} 行数据。")
        # 关闭连接
        conn.close()
    except Exception as e:
        print(f"发生错误: {e}")

# 调用函数
if __name__ == "__main__":
    print_full_database("barcode_cache.db")
    #print_best_configurations()