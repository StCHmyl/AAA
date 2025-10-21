import os
import pandas as pd
from pathlib import Path

def check_empty_files():
    """检查downloaded_images文件夹中的空文件"""
    image_folder = "../downloaded_images"
    output_file = "empty_files.xlsx"
    
    # 检查图片文件夹是否存在
    if not os.path.exists(image_folder):
        print(f"错误：图片文件夹 '{image_folder}' 不存在")
        return
    
    empty_files = []
    
    # 遍历图片文件夹中的所有文件
    for root, dirs, files in os.walk(image_folder):
        for file in files:
            file_path = os.path.join(root, file)
            
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            
            if file_size == 0:
                # 获取文件名和扩展名
                file_name = os.path.basename(file_path)
                file_prefix = os.path.splitext(file_name)[0]  # 文件名前缀
                file_suffix = os.path.splitext(file_name)[1]  # 文件扩展名
                
                empty_files.append({
                    '文件名（完整）': file_path,
                    '前缀': file_prefix,
                    '后缀': file_suffix
                })
    
    # 创建DataFrame并保存到Excel
    if empty_files:
        df = pd.DataFrame(empty_files)
        df.to_excel(output_file, index=False)
        print(f"找到 {len(empty_files)} 个空文件，已保存到 {output_file}")
        
        # 打印前几个空文件作为示例
        print("\n前5个空文件示例：")
        for i, file_info in enumerate(empty_files[:5]):
            print(f"{i+1}. {file_info['文件名（完整）']}")
    else:
        print("未找到空文件")
        # 创建空的Excel文件
        df = pd.DataFrame(columns=['文件名（完整）', '前缀', '后缀'])
        df.to_excel(output_file, index=False)
        print(f"已创建空的Excel文件: {output_file}")

if __name__ == "__main__":
    check_empty_files()
