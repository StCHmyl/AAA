# translate_excel_openpyxl.py 大纲

## 文件概述
- 用途：使用openpyxl和OpenAI API进行Excel文件翻译的工具
- 主要功能：批量翻译Excel中的美妆产品描述
- 依赖库：openpyxl, openai, tqdm, pandas, rapidfuzz等

## 主要类和方法

### PerfumeMatcher类
- 功能：香水名称匹配器
- 方法：
  - `__init__`: 初始化，加载香水术语表
  - `_preprocess_dataframe`: 预处理香水数据
  - `preprocess`: 清洗用户输入
  - `get_all_matches`: 获取相似度匹配结果
  - `get_top_names`: 获取匹配度最高的名称列表
  - `get_CHINESE_NAME`:根据ean条码从中文品名汇总表.xlsx获取中文名称
### APICounter类
- 功能：线程安全的API调用计数器
- 方法：
  - `increment`: 原子化增加计数器
  - `reset`: 原子化重置计数器

## 核心功能函数

### 翻译相关
- `translate_single(text, ean,pinpai=None)`: 
- 参数：
  - text: 待翻译文本(必定存在)
  - ean: ean条码（不一定存在）
  - 返回：翻译结果
- 流程：
 1 如果有传递ean条码，则优先使用ean条码进行匹配 调用`get_CHINESE_NAME` 如果匹配成功 直接返回结果 否则继续进行
 2 如果没有传递ean条码，则使用get_top_names获取匹配度最高的名称列表 作为参考内容加入大模型传递参数中参与翻译 





单条文本翻译
  - 使用OpenAI API进行翻译
  - 结合香水名称匹配结果

### Excel处理
- `process_single`: 处理单行Excel数据
- `translate_excel`: 主翻译函数
  - 参数：
    - input_path: 输入文件路径
    - output_path: 输出文件路径
    - start_row/end_row: 处理行范围
    - src_col/dst_col: 源列和目标列
    - barcode_col: 条码列,存储着ean条码
  - 特点：
    - 多线程处理(ThreadPoolExecutor)
    - 进度显示(tqdm)

### 辅助函数
- `col_name_to_number`: 列名转数字
- `col_number_to_name`: 数字转列名
- `get_excel_row_count`: 获取Excel行数
- `api_counter_thread`: API调用统计线程

## 使用示例
```python
# 单条翻译示例
translate_single("LOEWE SOLO EDT 150 + 20 ML")

# Excel批量翻译示例
translate_excel(
    "input.xlsx",
    start_row=0,
    end_row=100,
    src_col='D',
    dst_col='M',
    barcode_col='A'
)
```

## 注意事项
- 需要配置OpenAI API密钥
- 依赖香水术语表(all(1).xlsx)
- 多线程并发数由MAX_WORKERS控制(默认15)
