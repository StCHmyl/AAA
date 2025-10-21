#!/usr/bin/env python3
"""
图片文件系统分析脚本
用于分析downloaded_images目录中的图片文件情况
"""

import os
import glob
import hashlib
import json
from pathlib import Path
import pandas as pd
from collections import Counter, defaultdict

def format_size(size_bytes):
    """格式化文件大小为人类可读的格式"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

def calculate_file_hash(file_path):
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        return None

def analyze_duplicate_files(image_files):
    """分析重复文件（基于文件哈希）"""
    print("🔄 重复文件分析:")
    print("-" * 30)
    
    # 计算文件哈希
    file_hashes = {}
    hash_to_files = defaultdict(list)
    
    print("  正在计算文件哈希...")
    for i, file_path in enumerate(image_files):
        if i % 1000 == 0:
            print(f"    已处理 {i:,} / {len(image_files):,} 个文件")
        
        file_hash = calculate_file_hash(file_path)
        if file_hash:
            file_hashes[file_path] = file_hash
            hash_to_files[file_hash].append(file_path)
    
    # 找出重复文件
    duplicate_groups = {hash_val: files for hash_val, files in hash_to_files.items() if len(files) > 1}
    
    print(f"  重复文件组数: {len(duplicate_groups):,}")
    print(f"  涉及文件数: {sum(len(files) for files in duplicate_groups.values()):,}")
    
    if duplicate_groups:
        print("  重复文件组（前5组）:")
        for i, (hash_val, files) in enumerate(list(duplicate_groups.items())[:5]):
            print(f"    组 {i+1}:")
            for file_path in files:
                print(f"      - {file_path.name} ({format_size(file_path.stat().st_size)})")
    
    return duplicate_groups, hash_to_files

def generate_json_report(analysis_data):
    """生成JSON格式的详细报告"""
    json_report = {
        "analysis_summary": {
            "total_files": analysis_data["total_files"],
            "total_size_bytes": analysis_data["total_size"],
            "total_size_human": format_size(analysis_data["total_size"]),
            "average_size_bytes": analysis_data["avg_size"],
            "average_size_human": format_size(analysis_data["avg_size"]),
            "analysis_timestamp": analysis_data["timestamp"]
        },
        "file_type_distribution": analysis_data["ext_counter"],
        "size_distribution": analysis_data["size_distribution"],
        "file_name_analysis": {
            "name_length_range": analysis_data["name_length_range"],
            "common_name_lengths": analysis_data["common_name_lengths"],
            "numeric_names_count": analysis_data["numeric_names_count"],
            "numeric_names_percentage": analysis_data["numeric_names_percentage"]
        },
        "directory_structure": {
            "subdirectory_count": analysis_data["subdir_count"],
            "subdirectories": analysis_data["subdirs_list"]
        },
        "anomaly_checks": {
            "empty_files": {
                "count": analysis_data["empty_files_count"],
                "files": analysis_data["empty_files_list"]
            },
            "small_files": analysis_data["small_files_count"],
            "large_files": analysis_data["large_files_count"],
            "non_standard_extensions": analysis_data["non_standard_files_count"]
        },
        "duplicate_files": {
            "duplicate_groups_count": analysis_data["duplicate_groups_count"],
            "files_involved_count": analysis_data["files_involved_count"],
            "duplicate_groups": analysis_data["duplicate_groups_details"]
        }
    }
    
    # 保存JSON报告
    json_file = "detailed_image_analysis.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_report, f, ensure_ascii=False, indent=2)
    
    print(f"  JSON详细报告已保存到: {json_file}")
    return json_report

def generate_markdown_report(analysis_data, json_report):
    """生成Markdown格式的详细报告"""
    md_content = f"""# 图片文件系统详细分析报告

## 📊 总体概况

- **分析时间**: {analysis_data["timestamp"]}
- **目录位置**: {analysis_data["directory_path"]}
- **文件总数**: {analysis_data["total_files"]:,}
- **总大小**: {format_size(analysis_data["total_size"])}
- **平均文件大小**: {format_size(analysis_data["avg_size"])}

## 📄 文件类型分布

| 文件类型 | 数量 | 百分比 |
|---------|------|--------|
"""
    
    # 添加文件类型表格
    for ext, count in sorted(analysis_data["ext_counter"].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / analysis_data["total_files"]) * 100
        md_content += f"| {ext or '无扩展名'} | {count:,} | {percentage:.1f}% |\n"
    
    md_content += f"""
## 📏 文件大小分析

- **最小文件**: {format_size(analysis_data["min_size"])}
- **最大文件**: {format_size(analysis_data["max_size"])}

### 大小分布

| 大小范围 | 文件数量 | 百分比 |
|---------|----------|--------|
"""
    
    # 添加大小分布表格
    for size_range in analysis_data["size_distribution"]:
        md_content += f"| {size_range['label']} | {size_range['count']:,} | {size_range['percentage']:.1f}% |\n"
    
    md_content += f"""
## 🏷️ 文件名模式分析

- **文件名长度范围**: {analysis_data["name_length_range"][0]} - {analysis_data["name_length_range"][1]} 字符
- **数字文件名**: {analysis_data["numeric_names_count"]:,} 个 ({analysis_data["numeric_names_percentage"]:.1f}%)

### 常见文件名长度

| 长度 | 文件数量 | 百分比 |
|------|----------|--------|
"""
    
    # 添加文件名长度表格
    for length_info in analysis_data["common_name_lengths"]:
        md_content += f"| {length_info['length']} 字符 | {length_info['count']:,} | {length_info['percentage']:.1f}% |\n"
    
    md_content += f"""
## 📂 目录结构分析

- **子目录数量**: {analysis_data["subdir_count"]}
"""
    
    if analysis_data["subdirs_list"]:
        md_content += "\n### 子目录列表\n\n"
        for subdir in analysis_data["subdirs_list"]:
            md_content += f"- {subdir['name']} ({subdir['file_count']} 个文件)\n"
    else:
        md_content += "\n所有文件都在根目录\n"
    
    md_content += f"""
## ⚠️ 异常文件检查

### 空文件
- **数量**: {analysis_data["empty_files_count"]:,}
"""
    
    if analysis_data["empty_files_list"]:
        md_content += "\n**空文件列表**:\n\n"
        for file in analysis_data["empty_files_list"]:
            md_content += f"- {file}\n"
    
    md_content += f"""
### 其他异常
- **极小文件 (<100B)**: {analysis_data["small_files_count"]:,}
- **超大文件 (>10MB)**: {analysis_data["large_files_count"]:,}
- **非标准扩展名**: {analysis_data["non_standard_files_count"]:,}

## 🔄 重复文件分析

- **重复文件组数**: {analysis_data["duplicate_groups_count"]:,}
- **涉及文件数**: {analysis_data["files_involved_count"]:,}

### 重复文件组详情（前10组）

"""
    
    # 添加重复文件组信息
    for i, group in enumerate(analysis_data["duplicate_groups_details"][:10]):
        md_content += f"#### 组 {i+1}\n\n"
        for file_info in group["files"]:
            md_content += f"- {file_info['name']} ({file_info['size']})\n"
        md_content += "\n"
    
    md_content += f"""
## 📈 详细统计

- **唯一扩展名数量**: {analysis_data["unique_extensions"]}
- **数字文件名比例**: {analysis_data["numeric_names_percentage"]:.1f}%

---

*报告生成时间: {analysis_data["timestamp"]}*
*数据来源: {analysis_data["directory_path"]}*
"""
    
    # 保存Markdown报告
    md_file = "detailed_image_analysis.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"  Markdown详细报告已保存到: {md_file}")
    return md_content

def analyze_images_directory():
    """分析downloaded_images目录的文件系统情况"""
    
    import datetime
    
    image_dir = Path("downloaded_images")
    
    if not image_dir.exists():
        print(f"错误：目录 {image_dir} 不存在")
        return
    
    print("=" * 60)
    print("图片文件系统分析报告")
    print("=" * 60)
    
    # 获取所有文件
    all_files = list(image_dir.rglob("*"))
    image_files = [f for f in all_files if f.is_file()]
    
    print(f"📁 目录位置: {image_dir.absolute()}")
    print(f"📊 文件总数: {len(image_files):,}")
    print()
    
    # 收集所有分析数据
    analysis_data = {
        "directory_path": str(image_dir.absolute()),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_files": len(image_files)
    }
    
    # 1. 文件类型分析
    print("📄 文件类型分布:")
    print("-" * 30)
    extensions = [f.suffix.lower() for f in image_files]
    ext_counter = Counter(extensions)
    analysis_data["ext_counter"] = dict(ext_counter.most_common())
    analysis_data["unique_extensions"] = len(ext_counter)
    
    for ext, count in ext_counter.most_common():
        percentage = (count / len(image_files)) * 100
        print(f"  {ext or '无扩展名':<8} {count:>6,} 个 ({percentage:>5.1f}%)")
    print()
    
    # 2. 文件大小分析
    print("📏 文件大小分析:")
    print("-" * 30)
    sizes = [f.stat().st_size for f in image_files]
    
    if sizes:
        total_size = sum(sizes)
        avg_size = total_size / len(sizes)
        min_size = min(sizes)
        max_size = max(sizes)
        
        analysis_data["total_size"] = total_size
        analysis_data["avg_size"] = avg_size
        analysis_data["min_size"] = min_size
        analysis_data["max_size"] = max_size
        
        print(f"  总大小: {format_size(total_size)}")
        print(f"  平均大小: {format_size(avg_size)}")
        print(f"  最小文件: {format_size(min_size)}")
        print(f"  最大文件: {format_size(max_size)}")
        print()
        
        # 大小分布
        size_ranges = [
            (0, 1024, "0-1KB"),
            (1024, 10240, "1-10KB"),
            (10240, 102400, "10-100KB"),
            (102400, 1048576, "100KB-1MB"),
            (1048576, float('inf'), ">1MB")
        ]
        
        size_distribution = []
        print("  大小分布:")
        for min_r, max_r, label in size_ranges:
            count = sum(1 for s in sizes if min_r <= s < max_r)
            percentage = (count / len(sizes)) * 100
            size_distribution.append({
                "label": label,
                "count": count,
                "percentage": percentage
            })
            print(f"    {label:<12} {count:>6,} 个 ({percentage:>5.1f}%)")
        
        analysis_data["size_distribution"] = size_distribution
    print()
    
    # 3. 空文件检查
    print("🔍 空文件检查:")
    print("-" * 30)
    empty_files = [f for f in image_files if f.stat().st_size == 0]
    analysis_data["empty_files_count"] = len(empty_files)
    analysis_data["empty_files_list"] = [str(f.relative_to(image_dir)) for f in empty_files]
    
    print(f"  空文件数量: {len(empty_files):,}")
    if empty_files:
        print("  空文件列表:")
        for f in empty_files[:10]:  # 只显示前10个
            print(f"    - {f.name}")
        if len(empty_files) > 10:
            print(f"    ... 还有 {len(empty_files) - 10} 个空文件")
    print()
    
    # 4. 文件名模式分析
    print("🏷️  文件名模式分析:")
    print("-" * 30)
    filenames = [f.stem for f in image_files]  # 去掉扩展名的文件名
    
    # 分析文件名长度分布
    name_lengths = [len(name) for name in filenames]
    if name_lengths:
        name_length_range = (min(name_lengths), max(name_lengths))
        analysis_data["name_length_range"] = name_length_range
        print(f"  文件名长度范围: {min(name_lengths)} - {max(name_lengths)} 字符")
        
        # 统计常见长度
        length_counter = Counter(name_lengths)
        common_name_lengths = []
        print("  常见文件名长度:")
        for length, count in length_counter.most_common(5):
            percentage = (count / len(filenames)) * 100
            common_name_lengths.append({
                "length": length,
                "count": count,
                "percentage": percentage
            })
            print(f"    {length} 字符: {count:>6,} 个 ({percentage:>5.1f}%)")
        
        analysis_data["common_name_lengths"] = common_name_lengths
    
    # 检查是否都是数字（条码）
    numeric_names = [name for name in filenames if name.isdigit()]
    numeric_names_count = len(numeric_names)
    numeric_names_percentage = (numeric_names_count / len(filenames)) * 100
    analysis_data["numeric_names_count"] = numeric_names_count
    analysis_data["numeric_names_percentage"] = numeric_names_percentage
    
    print(f"  数字文件名: {numeric_names_count:,} 个 ({numeric_names_percentage:.1f}%)")
    print()
    
    # 5. 目录结构分析
    print("📂 目录结构分析:")
    print("-" * 30)
    subdirs = [d for d in all_files if d.is_dir()]
    analysis_data["subdir_count"] = len(subdirs)
    
    subdirs_list = []
    for d in subdirs:
        files_in_dir = len([f for f in d.rglob("*") if f.is_file()])
        subdirs_list.append({
            "name": str(d.relative_to(image_dir)),
            "file_count": files_in_dir
        })
    analysis_data["subdirs_list"] = subdirs_list
    
    print(f"  子目录数量: {len(subdirs)}")
    
    if subdirs:
        print("  子目录列表:")
        for d in subdirs:
            files_in_dir = len([f for f in d.rglob("*") if f.is_file()])
            print(f"    - {d.relative_to(image_dir)} ({files_in_dir} 个文件)")
    else:
        print("  所有文件都在根目录")
    print()
    
    # 6. 异常文件检查
    print("⚠️  异常文件检查:")
    print("-" * 30)
    
    # 检查非常小的文件（可能损坏）
    small_files = [f for f in image_files if 0 < f.stat().st_size < 100]
    analysis_data["small_files_count"] = len(small_files)
    print(f"  极小文件 (<100B): {len(small_files):,}")
    
    # 检查非常大的文件
    large_files = [f for f in image_files if f.stat().st_size > 10 * 1024 * 1024]  # >10MB
    analysis_data["large_files_count"] = len(large_files)
    print(f"  超大文件 (>10MB): {len(large_files):,}")
    
    # 检查非标准扩展名
    standard_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    non_standard_files = [f for f in image_files if f.suffix.lower() not in standard_extensions and f.suffix]
    analysis_data["non_standard_files_count"] = len(non_standard_files)
    print(f"  非标准扩展名: {len(non_standard_files):,}")
    print()
    
    # 7. 重复文件分析
    duplicate_groups, hash_to_files = analyze_duplicate_files(image_files)
    analysis_data["duplicate_groups_count"] = len(duplicate_groups)
    analysis_data["files_involved_count"] = sum(len(files) for files in duplicate_groups.values())
    
    # 准备重复文件组详情
    duplicate_groups_details = []
    for hash_val, files in list(duplicate_groups.items())[:20]:  # 限制前20组
        group_files = []
        for file_path in files:
            group_files.append({
                "name": str(file_path.relative_to(image_dir)),
                "size": format_size(file_path.stat().st_size)
            })
        duplicate_groups_details.append({
            "hash": hash_val,
            "files": group_files
        })
    analysis_data["duplicate_groups_details"] = duplicate_groups_details
    print()
    
    # 8. 生成详细统计
    print("📈 详细统计:")
    print("-" * 30)
    
    # 创建数据框用于详细分析
    file_data = []
    for file_path in image_files:
        stat = file_path.stat()
        file_data.append({
            'filename': file_path.name,
            'extension': file_path.suffix.lower(),
            'size_bytes': stat.st_size,
            'size_human': format_size(stat.st_size),
            'is_numeric': file_path.stem.isdigit(),
            'name_length': len(file_path.stem)
        })
    
    df = pd.DataFrame(file_data)
    
    print(f"  文件数量统计: {len(df):,}")
    print(f"  唯一扩展名: {df['extension'].nunique()}")
    print(f"  数字文件名比例: {df['is_numeric'].mean()*100:.1f}%")
    
    # 保存详细报告到CSV
    report_file = "image_analysis_report.csv"
    df.to_csv(report_file, index=False, encoding='utf-8-sig')
    print(f"  详细报告已保存到: {report_file}")
    
    # 9. 生成JSON和Markdown详细报告
    print("\n📄 生成详细报告:")
    print("-" * 30)
    
    # 生成JSON报告
    json_report = generate_json_report(analysis_data)
    
    # 生成Markdown报告
    markdown_report = generate_markdown_report(analysis_data, json_report)
    
    print("=" * 60)
    print("分析完成！")
    print(f"📊 已生成以下报告文件:")
    print(f"  - detailed_image_analysis.json (结构化数据)")
    print(f"  - detailed_image_analysis.md (格式化报告)")
    print(f"  - image_analysis_report.csv (详细数据)")
    print("=" * 60)

if __name__ == "__main__":
    analyze_images_directory()
