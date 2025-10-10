import sqlite3
import threading
import os

DB_PATH = "ua_stealth_usage.db"  # 数据库路径常量
db_lock = threading.Lock()  # 定义全局数据库锁


def execute_query(query, params=None, fetch=False):
    """
    执行数据库查询的辅助函数，自动处理连接和关闭。
    :param query: SQL 查询字符串
    :param params: 查询参数（可选）
    :param fetch: 是否获取查询结果，如果为 True，则返回结果列表
    :return: 如果 fetch 为 True，则返回结果列表；否则返回 None
    """
    try:
        with db_lock:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                if fetch:
                    return cursor.fetchall()
                else:
                    conn.commit()
    except Exception as e:
        print(f"数据库操作出错: {e}")
        return None


def get_statistics():
    """
    获取每种UA和Stealth配置的使用统计，包括使用次数、成功次数和成功率
    """
    stats = {}

    for record_type in ['UA', 'Stealth']:
        result = execute_query(f"""
            SELECT value,
                   COUNT(*) as total,
                   SUM(success) as success,
                   ROUND(1.0 * SUM(success) / COUNT(*), 2) as success_rate
            FROM usage_records
            WHERE type = ?
            GROUP BY value
            ORDER BY success_rate DESC, success DESC, total DESC
        """, (record_type,), fetch=True)

        stats[record_type] = result if result else []

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


def print_table_schema(db_path):
    """打印数据库所有表的结构信息"""
    try:
        tables = execute_query("SELECT name FROM sqlite_master WHERE type='table';", fetch=True)

        if not tables:
            print("数据库中没有表。")
            return

        # 遍历每个表并打印结构
        for table_name in tables:
            table_name = table_name[0]
            print(f"\n表结构: {table_name}")

            # 获取表定义SQL
            create_sql = execute_query(f"SELECT sql FROM sqlite_master WHERE name='{table_name}'", fetch=True)[0][0]
            print(f"创建语句: {create_sql}")

            # 获取列详细信息
            columns = execute_query(f"PRAGMA table_info({table_name})", fetch=True)
            print("列信息:")
            for col in columns:
                print(f"  {col[1]}: {col[2]} {'(主键)' if col[5] else ''}")
    except Exception as e:
        print(f"获取表结构出错: {e}")


def clear_database(db_path=DB_PATH):
    """清空指定数据库的所有表数据"""
    try:
        confirm = input(f"确定要清空数据库 {db_path} 的所有数据吗？(y/n): ")
        if confirm.lower() != 'y':
            print("操作已取消")
            return

        tables = execute_query("SELECT name FROM sqlite_master WHERE type='table';", fetch=True)

        if not tables:
            print("数据库中没有表。")
            return

        # 清空每个表
        for table_name in tables:
            table_name = table_name[0]
            execute_query(f"DELETE FROM {table_name}")
            print(f"已清空表: {table_name}")

        # 执行VACUUM释放空间
        execute_query("VACUUM")
        print("数据库已清空并压缩")
    except Exception as e:
        print(f"清空数据库出错: {e}")


def print_full_database(db_path):
    """打印指定数据库的所有表数据"""
    try:
        tables = execute_query("SELECT name FROM sqlite_master WHERE type='table';", fetch=True)

        if not tables:
            print("数据库中没有表。")
            return

        # 遍历每个表并打印所有行
        for table_name in tables:
            table_name = table_name[0]
            print(f"\n表: {table_name}")
            rows = execute_query(f"SELECT * FROM {table_name}", fetch=True)
            a = 1
            for row in rows:
                a += 1
                if a % 100 == 0:
                    print(f"已打印 {a} 行数据")
                print(row)

        print(f"表 {table_name} 中共有 {len(rows)} 行数据。")
    except Exception as e:
        print(f"发生错误: {e}")


def handle_print_table_schema():
    db_files = [f for f in os.listdir() if f.endswith(".db")]
    if not db_files:
        print("当前目录下没有数据库文件。")
        return False
    else:
        print("请选择要操作的数据库:")
        for i, db_file in enumerate(db_files):
            print(f"{i + 1}. {db_file}")

        while True:
            try:
                db_index = int(input("请输入数据库编号: ")) - 1
                if 0 <= db_index < len(db_files):
                    db_path = db_files[db_index]
                    print_table_schema(db_path)
                    return True
                else:
                    print("无效的数据库编号，请重新输入。")
            except ValueError:
                print("请输入数字编号。")
                return False


def handle_print_full_database():
    db_files = [f for f in os.listdir() if f.endswith(".db")]
    if not db_files:
        print("当前目录下没有数据库文件。")
        return False
    else:
        print("请选择要操作的数据库:")
        for i, db_file in enumerate(db_files):
            print(f"{i + 1}. {db_file}")

        while True:
            try:
                db_index = int(input("请输入数据库编号: ")) - 1
                if 0 <= db_index < len(db_files):
                    db_path = db_files[db_index]
                    print_full_database(db_path)
                    return True
                else:
                    print("无效的数据库编号，请重新输入。")
            except ValueError:
                print("请输入数字编号。")
                return False

def handle_clear_database():
    db_files = [f for f in os.listdir() if f.endswith(".db")]
    if not db_files:
        print("当前目录下没有数据库文件。")
        return False
    else:
        print("请选择要操作的数据库:")
        for i, db_file in enumerate(db_files):
            print(f"{i + 1}. {db_file}")

        while True:
            try:
                db_index = int(input("请输入数据库编号: ")) - 1
                if 0 <= db_index < len(db_files):
                    db_path = db_files[db_index]
                    clear_database(db_path)
                    return True
                else:
                    print("无效的数据库编号，请重新输入。")
            except ValueError:
                print("请输入数字编号。")
                return False


# 调用函数
if __name__ == "__main__":
    while True:
        print("\n请选择要执行的任务:")
        print("1. 打印数据库所有表的结构信息")
        print("2. 清空 ua_stealth_usage.db 数据库")
        print("3. 打印 ua_stealth_usage.db 数据库")
        print("4. 打印 UA 和 Stealth 配置信息")
        print("5. 打印指定数据库所有数据")
        print("6. 清空指定数据库")
        print("0. 退出")

        choice = input("请输入任务编号: ")

        actions = {
            '1': handle_print_table_schema,
            '2': clear_database,
            '3': lambda: print_full_database(DB_PATH),
            '4': print_best_configurations,
            '5': handle_print_full_database,
            '6': handle_clear_database,
            '0': lambda: False  # 用于退出循环
        }

        action = actions.get(choice)
        if action in [handle_print_table_schema, handle_print_full_database, handle_clear_database]:
            if not action():
                continue
        else:
            if action():
                break
            else:
                print("无效的任务编号，请重新输入。")
