import os
import pandas as pd
import hashlib
from collections import defaultdict

def calculate_md5(file_path):
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"计算MD5错误 {file_path}: {e}")
        return None

def find_duplicate_files_by_md5(md5_list=None):
    """根据MD5列表查找相同文件"""
    image_folder = "../downloaded_images"
    output_file = "duplicate_files.xlsx"
    
    # 检查图片文件夹是否存在
    if not os.path.exists(image_folder):
        print(f"错误：图片文件夹 '{image_folder}' 不存在")
        return
    
    # 如果没有提供MD5列表，则计算所有文件的MD5
    if md5_list is None:
        print("请提供MD5编码列表")
        return
    
    duplicate_files = []
    
    # 遍历图片文件夹中的所有文件
    for root, dirs, files in os.walk(image_folder):
        for file in files:
            file_path = os.path.join(root, file)
            
            # 跳过空文件
            if os.path.getsize(file_path) == 0:
                continue
                
            # 计算文件的MD5
            file_md5 = calculate_md5(file_path)
            
            if file_md5 and file_md5 in md5_list:
                # 获取文件名和扩展名
                file_name = os.path.basename(file_path)
                file_prefix = os.path.splitext(file_name)[0]  # 文件名前缀
                file_suffix = os.path.splitext(file_name)[1]  # 文件扩展名
                
                duplicate_files.append({
                    '文件名（完整）': file_path,
                    '前缀': file_prefix,
                    '后缀': file_suffix,
                    'MD5': file_md5
                })
    
    # 创建DataFrame并保存到Excel
    if duplicate_files:
        df = pd.DataFrame(duplicate_files)
        df.to_excel(output_file, index=False)
        print(f"找到 {len(duplicate_files)} 个相同文件，已保存到 {output_file}")
        
        # 按MD5分组显示
        md5_groups = defaultdict(list)
        for file_info in duplicate_files:
            md5_groups[file_info['MD5']].append(file_info['文件名（完整）'])
        
        print(f"\n相同文件分组（按MD5）：")
        for md5_value, files in md5_groups.items():
            print(f"MD5: {md5_value}")
            for i, file_path in enumerate(files):
                print(f"  {i+1}. {file_path}")
            print()
    else:
        print("未找到相同文件")
        # 创建空的Excel文件
        df = pd.DataFrame(columns=['文件名（完整）', '前缀', '后缀', 'MD5'])
        df.to_excel(output_file, index=False)
        print(f"已创建空的Excel文件: {output_file}")

def find_all_duplicate_files():
    """查找所有重复文件（基于MD5）"""
    image_folder = "../downloaded_images"
    output_file = "all_duplicate_files.xlsx"
    
    # 检查图片文件夹是否存在
    if not os.path.exists(image_folder):
        print(f"错误：图片文件夹 '{image_folder}' 不存在")
        return
    
    md5_dict = defaultdict(list)
    
    print("正在计算所有文件的MD5...")
    
    # 遍历图片文件夹中的所有文件并计算MD5
    for root, dirs, files in os.walk(image_folder):
        for file in files:
            file_path = os.path.join(root, file)
            
            # 跳过空文件
            if os.path.getsize(file_path) == 0:
                continue
                
            # 计算文件的MD5
            file_md5 = calculate_md5(file_path)
            
            if file_md5:
                md5_dict[file_md5].append(file_path)
    
    # 找出重复的文件
    duplicate_files = []
    for md5_value, file_paths in md5_dict.items():
        if len(file_paths) > 1:  # 有重复
            for file_path in file_paths:
                file_name = os.path.basename(file_path)
                file_prefix = os.path.splitext(file_name)[0]
                file_suffix = os.path.splitext(file_name)[1]
                
                duplicate_files.append({
                    '文件名（完整）': file_path,
                    '前缀': file_prefix,
                    '后缀': file_suffix,
                    'MD5': md5_value,
                    '重复数量': len(file_paths)
                })
    
    # 创建DataFrame并保存到Excel
    if duplicate_files:
        df = pd.DataFrame(duplicate_files)
        df.to_excel(output_file, index=False)
        print(f"找到 {len(duplicate_files)} 个重复文件，涉及 {len(set([f['MD5'] for f in duplicate_files]))} 个不同的MD5值")
        print(f"已保存到 {output_file}")
        
        # 显示重复文件分组
        print(f"\n重复文件分组：")
        md5_groups = defaultdict(list)
        for file_info in duplicate_files:
            md5_groups[file_info['MD5']].append(file_info['文件名（完整）'])
        
        for md5_value, files in list(md5_groups.items())[:5]:  # 显示前5组
            print(f"MD5: {md5_value} (共 {len(files)} 个文件)")
            for i, file_path in enumerate(files):
                print(f"  {i+1}. {file_path}")
            print()
    else:
        print("未找到重复文件")
        # 创建空的Excel文件
        df = pd.DataFrame(columns=['文件名（完整）', '前缀', '后缀', 'MD5', '重复数量'])
        df.to_excel(output_file, index=False)
        print(f"已创建空的Excel文件: {output_file}")

if __name__ == "__main__":
    print("请选择操作模式：")
    print("1. 根据提供的MD5列表查找相同文件")
    print("2. 查找所有重复文件")
    
    choice = input("请输入选择 (1 或 2): ")
    
    if choice == "1":
        print("请提供MD5编码列表（用逗号分隔）:")
        md5_input = input("MD5列表: ")
        md5_list = [md5.strip() for md5 in md5_input.split(",") if md5.strip()]
        find_duplicate_files_by_md5(md5_list)
    elif choice == "2":
        find_all_duplicate_files()
    else:
        print("无效选择")
