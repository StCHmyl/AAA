import pandas as pd
import re

# 读取 Excel 文件
df = pd.read_excel("db_export.xlsx")

# 检查 product_name 是否存在
if "product_name" not in df.columns:
    raise ValueError("Excel 文件中未找到 'product_name' 列")

# 使用正则匹配：前6位全为数字
mask = df["product_name"].astype(str).str.match(r"^\d{6}\.")

# 筛选出符合条件的行
filtered_df = df[mask]

# 输出结果到新文件
filtered_df.to_excel("db_export_filtered.xlsx", index=False)

print(f"筛选完成！共找到 {len(filtered_df)} 条记录，结果已保存到 db_export_filtered.xlsx")
