import os
import pandas as pd
import sqlite3
from pathlib import Path

def clean_duplicate_files():
    """根据Excel文件中的记录删除相同文件和对应的数据库记录"""
    excel_file = "duplicate_files.xlsx"
    db_path = "../barcode_cache.db"
    
    # 检查Excel文件是否存在
    if not os.path.exists(excel_file):
        print(f"错误：Excel文件 '{excel_file}' 不存在")
        return
    
    # 读取Excel文件
    try:
        df = pd.read_excel(excel_file)
        if df.empty:
            print("Excel文件中没有相同文件记录")
            return
    except Exception as e:
        print(f"读取Excel文件错误：{e}")
        return
    
    # 连接数据库
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
    except sqlite3.Error as e:
        print(f"数据库连接错误：{e}")
        return
    
    deleted_files = []
    deleted_db_records = []
    errors = []
    
    print(f"开始处理 {len(df)} 个相同文件记录...")
    
    for index, row in df.iterrows():
        file_path = row['文件名（完整）']
        file_prefix = row['前缀']  # 这应该是条形码
        md5_value = row['MD5']
        
        try:
            # 1. 删除相同文件
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_files.append(file_path)
                print(f"✓ 已删除文件: {file_path}")
            else:
                print(f"⚠ 文件不存在: {file_path}")
            
            # 2. 删除对应的数据库记录
            # 假设文件前缀是条形码，在products表中查找并删除
            cursor.execute("DELETE FROM products WHERE barcode = ?", (file_prefix,))
            if cursor.rowcount > 0:
                deleted_db_records.append(file_prefix)
                print(f"✓ 已删除数据库记录: {file_prefix}")
            else:
                print(f"⚠ 未找到数据库记录: {file_prefix}")
                
        except Exception as e:
            error_msg = f"处理 {file_path} 时出错: {e}"
            errors.append(error_msg)
            print(f"✗ {error_msg}")
    
    # 提交数据库更改
    conn.commit()
    conn.close()
    
    # 生成报告
    print(f"\n=== 清理完成 ===")
    print(f"成功删除文件: {len(deleted_files)} 个")
    print(f"成功删除数据库记录: {len(deleted_db_records)} 个")
    print(f"错误数量: {len(errors)} 个")
    
    # 保存清理报告
    report_data = {
        "清理时间": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "处理的相同文件总数": len(df),
        "成功删除的文件数": len(deleted_files),
        "成功删除的数据库记录数": len(deleted_db_records),
        "错误数量": len(errors),
        "MD5值": df['MD5'].iloc[0] if 'MD5' in df.columns else "未知",
        "删除的文件列表": deleted_files,
        "删除的数据库记录列表": deleted_db_records,
        "错误列表": errors
    }
    
    # 保存详细报告到JSON
    import json
    with open("duplicate_cleanup_report.json", 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细报告已保存到: duplicate_cleanup_report.json")
    
    # 显示前几个删除的文件作为示例
    if deleted_files:
        print(f"\n前5个删除的文件示例：")
        for i, file_path in enumerate(deleted_files[:5]):
            print(f"  {i+1}. {file_path}")

if __name__ == "__main__":
    # 确认操作
    print("警告：此操作将删除相同文件和对应的数据库记录！")
    confirm = input("确认继续？(输入 'yes' 继续): ")
    
    if confirm.lower() == 'yes':
        clean_duplicate_files()
    else:
        print("操作已取消")
