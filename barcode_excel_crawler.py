"""
条形码信息爬取与Excel更新脚本

该脚本从用户指定的Excel文件中读取条形码列表，使用多线程和Selenium爬取
barcodelookup.com网站获取产品图片和名称。为了提高效率，脚本使用SQLite
数据库缓存已爬取的数据，避免重复访问。爬取到的信息（产品名称和图片）
将被写入回原始Excel文件的指定位置。

主要功能:
- 从Excel文件读取指定列和行范围内的条形码，并记录行号。
- 跳过Excel中的空条码。
- 使用SQLite数据库缓存已爬取的产品信息。
- 多线程并行爬取，提高效率。
- 使用Selenium和selenium-stealth模拟浏览器行为，应对反爬虫。
- 检测Cloudflare拦截和条码未找到情况。
- 提取产品图片URL和产品名称（通过XPath）。
- 下载产品图片并保存到本地文件夹。
- 将产品名称写入Excel，并将图片嵌入到对应单元格。

依赖库:
- openpyxl: 用于读写Excel文件
- selenium: 用于浏览器自动化
- selenium-stealth: 用于使Selenium更难被检测
- threading: 用于实现多线程
- os: 用于文件系统操作
- time: 用于时间记录
- requests: 用于下载图片
- sqlite3: Python内置库，用于SQLite数据库操作
"""

import threading
import os
import time
import sqlite3
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium_stealth import stealth
import openpyxl
from openpyxl.drawing.image import Image
# 导入 openpyxl.utils 模块，用于列字母和索引转换
from openpyxl.utils import column_index_from_string
from barcode_excel_db import init_database, get_product_from_db, insert_product_to_db
from barcode_excel_excel import read_barcodes_from_excel_with_row, update_excel_with_results_with_row
#from barcode_excel_trans import translate_excel
from translate_excel_openpyxl import translate_excel
from RandomUaStealth import get_random_stealth_config, get_random_user_agent, record_failure, record_success

# --- 配置 ---
DATABASE_NAME = 'barcode_cache.db' # SQLite数据库文件名
IMAGE_DIR = 'downloaded_images' # 图片保存目录
DEFAULT_THREADS = 5 # 默认线程数
# 目标网站URL模板
BASE_URL = "https://www.barcodelookup.com/{}"
# 产品图片XPath
IMAGE_XPATH = '/html/body/section[2]/div[1]/div/div/div[1]/div[1]/img'
# 产品名称XPath
PRODUCT_NAME_XPATH = '/html/body/section[2]/div[1]/div/div/div[2]/h4'

# --- 图片下载 ---
def download_image(image_url, barcode):
    """下载图片并保存到本地。"""
    if not image_url:
        print(f"图片下载：图片URL为空，跳过下载条码 {barcode} 的图片。") # 增加日志
        return None
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
        print(f"图片下载：创建图片保存目录: {IMAGE_DIR}") # 增加日志
    # 尝试从URL中获取文件扩展名，如果失败则默认png
    try:
        file_extension = os.path.splitext(image_url.split('?')[0])[1]
        if not file_extension:
             file_extension = '.png' # 默认扩展名
    except:
        file_extension = '.png' # 默认扩展名
    image_filename = f"{barcode}{file_extension}"
    image_filepath = os.path.join(IMAGE_DIR, image_filename)
    # 检查图片是否已存在，避免重复下载
    if os.path.exists(image_filepath):
        print(f"图片下载：图片 {image_filename} 已存在，跳过下载。") # 增加日志
        return image_filepath
    print(f"图片下载：开始下载图片 {image_url} 到 {image_filepath}") # 增加日志
    try:
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status() # 检查HTTP请求是否成功
        with open(image_filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"图片下载：成功下载图片: {image_filename}") # 增加日志
        return image_filepath
    except requests.exceptions.RequestException as e:
        print(f"错误：下载图片 {image_url} 失败: {e}") # 增加日志
        return None

# --- 爬取逻辑 ---
# 修改 crawl_barcode 函数以接收行号并将其添加到结果中
def crawl_barcode_with_row(barcode, thread_name, results_list, row_index):
    """
    使用 Selenium 爬取单个条形码信息，处理Cloudflare和未找到情况，
    提取数据，下载图片，并将结果添加到共享列表（包含行号）。
    """
    print(f"线程 {thread_name} 开始处理条码: {barcode} (行号: {row_index})") # 增加日志
    
    # 1. 检查数据库缓存
    cached_data = get_product_from_db(barcode)
    if cached_data and cached_data['product_name'] and cached_data['image_filepath'] and cached_data['product_name'] != "Not Found":
        print(f"线程 {thread_name}: 条码 {barcode} 在缓存中找到有效数据。") # 增加日志
        results_list.append((barcode, cached_data['product_name'], cached_data['image_filepath'], row_index)) # 添加行号
        return # 从缓存获取，跳过爬取
    elif cached_data and cached_data['product_name'] == "Not Found":
         print(f"线程 {thread_name}: 条码 {barcode} 在缓存中标记为未找到。") # 增加日志
         results_list.append((barcode, "Not Found", None, row_index)) # 添加未找到结果和行号
         return # 从缓存获取，跳过爬取
    # 2. 数据库中未找到或缓存无效，进行爬取
    url = BASE_URL.format(barcode)
    driver = None
    retry_count = 5  # 重试次数
    product_name = None
    image_url = None
    image_filepath = None
    print(f"最大重试次数: {retry_count}") # 增加日志
    print(f"线程 {thread_name}: 缓存未命中或无效，开始网络爬取条码 {barcode}。") # 增加日志
    for attempt in range(retry_count):
        try:
            # 随机选择 User-Agent 和 stealth 配置
            ua = get_random_user_agent()
            stealth_cfg = get_random_stealth_config()
            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 启动浏览器并导航到 {url}") # 增加日志
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # 无头模式：不显示浏览器窗口
            chrome_options.add_argument("--disable-gpu")  # 禁用 GPU 加速，有时可避免问题
            chrome_options.add_argument("--window-size=1920x1080")  # 设置浏览器窗口大小
            chrome_options.add_argument("user-agent={ua}")

            driver = webdriver.Chrome(options=chrome_options)
            stealth(driver,
                languages=stealth_cfg["languages"],
                vendor=stealth_cfg["vendor"],
                platform=stealth_cfg["platform"],
                webgl_vendor=stealth_cfg["webgl_vendor"],
                renderer=stealth_cfg["renderer"],
                fix_hairline=True,
            )
            #time.sleep(random.uniform(0.5, 1.5))
            driver.set_page_load_timeout(30)
            driver.get(url)
            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 等待页面加载...") # 增加日志
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 页面加载完成。") # 增加日志
            # --- Cloudflare 拦截检测 ---
            if "Just a moment..." in driver.title or "Cloudflare" in driver.title or "Enable JavaScript and cookies to continue" in driver.page_source:
                print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 检测到 Cloudflare 拦截页面，进行重试。") # 增加日志
                record_failure(ua, stealth_cfg) # 记录失败的UA和配置
                if driver:
                    driver.quit()
                continue # 进入下一次重试
            else:
                record_success(ua, stealth_cfg) # 记录成功的UA和配置
                print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): Cloudflare 拦截检测通过。") # 增加日志
                print(f"线程 {thread_name}当前UA: {ua}") # 增加日志
                print(f"线程 {thread_name}当前Stealth配置: {stealth_cfg}") # 增加日志    
            # --- 条码未找到检测 ---
            if "Barcode Not Found | Barcode Lookup" in driver.title:
                print(f"线程 {thread_name}: 条码 {barcode} 未找到，跳过下载和截图。") # 增加日志
                if driver:
                    driver.quit()
                # 将未找到的条码也存入数据库，标记为无产品信息，避免重复爬取
                insert_product_to_db(barcode, "Not Found", None, None)
                results_list.append((barcode, "Not Found", None, row_index)) # 添加未找到结果和行号
                return # 立即退出函数
            # --- 提取数据 ---
            print(f"线程 {thread_name}: 开始提取产品信息...") # 增加日志
            try:
                # 提取产品名称
                product_name_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, PRODUCT_NAME_XPATH))
                )
                product_name = product_name_element.text.strip()
                print(f"线程 {thread_name}: 提取到产品名称: '{product_name}'") # 增加日志
            except (TimeoutException, WebDriverException):
                print(f"线程 {thread_name}: 未找到产品名称元素或提取失败。") # 增加日志
                product_name = "N/A" # 未找到则标记为N/A
            try:
                # 提取图片URL
                image_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, IMAGE_XPATH))
                )
                image_url = image_element.get_attribute('src')
                print(f"线程 {thread_name}: 提取到图片URL: {image_url}") # 增加日志
            except (TimeoutException, WebDriverException):
                print(f"线程 {thread_name}: 未找到图片元素或提取失败。") # 增加日志
                image_url = None # 未找到则标记为None
            # --- 下载图片 ---
            if image_url:
                 image_filepath = download_image(image_url, barcode)
            else:
                 image_filepath = None
                 print(f"线程 {thread_name}: 没有图片URL，跳过图片下载。") # 增加日志
            # --- 存储到数据库 ---
            insert_product_to_db(barcode, product_name, image_url, image_filepath)
            print(f"线程 {thread_name}: 条码 {barcode} 数据已存入数据库。") # 增加日志
            # --- 添加结果到列表 ---
            results_list.append((barcode, product_name, image_filepath, row_index)) # 添加行号
            print(f"线程 {thread_name}: 成功处理条码 {barcode}。") # 增加日志
            break # 成功完成，退出重试循环
        except (TimeoutException, WebDriverException) as e:
            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 使用 Selenium 发生错误：{e}") # 增加日志
            if driver:
                driver.quit() # 发生错误时关闭浏览器实例
            # 如果还有重试次数，打印重试提示
            if attempt < retry_count - 1:
                print(f"线程 {thread_name}: 进行重试。") # 增加日志
            else:
                # 如果达到最大重试次数，打印失败提示
                print(f"线程 {thread_name}: 达到最大重试次数，未能成功处理条码 {barcode}。") # 增加日志
        except Exception as e:
            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 发生未知错误：{e}") # 增加日志
            if driver:
                driver.quit() # 发生错误时关闭浏览器实例
            break # 未知错误，不再重试
        finally:
            if driver:
                driver.quit() # 确保每次尝试后都关闭浏览器实例
            # 如果所有重试都失败且未成功，将失败信息添加到结果列表（可选，取决于是否需要在Excel中标记失败）
            # if not success:
            #     results_list.append((barcode, "爬取失败", None, row_index)) # 添加行号

# --- 主程序入口 ---

def main():
    total_start_time = time.time() # 记录总程序开始时间
    print("脚本开始执行。") # 增加日志
    # 1. 获取用户输入
    excel_filepath = input("请输入Excel文件路径 [NR+SHISEIDO SPECIAL OFFER.xlsx]: ").strip() or "NR+SHISEIDO SPECIAL OFFER.xlsx"
    barcode_column_letter = input("请输入条码所在的列字母 (例如 A, B) [B]: ").strip().upper() or "B"
    while True:
        try:
            start_row_input = input("请输入开始读取的行号 [12]: ").strip() or "12"
            start_row = int(start_row_input)
            end_row_input = input("请输入结束读取的行号 [20]: ").strip() or "20"
            end_row = int(end_row_input)

            if start_row <= 0 or end_row <= 0 or start_row > end_row:
                print("行号输入无效，请重新输入。")
            else:
                break
        except ValueError:
            print("请输入有效的数字行号。")

    image_column_letter = input("请输入图片嵌入的列字母 (例如 N) [N]: ").strip().upper() or "N"
    product_name_column_letter = input("请输入产品名称写入的列字母 (例如 O) [O]: ").strip().upper() or "O"
    translate_dst_column_letter = input("请输入翻译结果写入的列字母 (例如 P) [P]: ").strip().upper() or "P"
    print(f"用户输入：Excel文件路径='{excel_filepath}', 条码列='{barcode_column_letter}', 开始行={start_row}, 结束行={end_row}, 产品名称列='{product_name_column_letter}', 图片列='{image_column_letter}'") # 增加日志
    # 2. 初始化数据库
    print("初始化数据库...") # 增加日志
    init_database()
    print("数据库初始化完成。") # 增加日志
    # 3. 读取条形码列表 (包含行号)
    barcodes_with_row_to_crawl = read_barcodes_from_excel_with_row(excel_filepath, barcode_column_letter, start_row, end_row)
    if not barcodes_with_row_to_crawl:
        print("未从Excel文件中读取到有效的条形码，脚本结束。")
    else:
        print(f"成功读取 {len(barcodes_with_row_to_crawl)} 个条码及对应行号。") # 增加日志
        # 4. 执行多线程爬取
        # 使用Manager().list()来创建一个可以在线程间共享的列表
        # from multiprocessing import Manager # 如果使用multiprocessing.Manager
        # manager = Manager()
        # results_list = manager.list()
        # 对于threading，直接使用列表并加锁是更常见的方式，但为了简单，
        # 且我们只是append，这里先直接使用列表，如果出现问题再考虑加锁
        results_list = [] # 用于存储爬取结果 (barcode, product_name, image_filepath, row_index) # 包含行号
        threads = []
        # 使用用户指定的线程数
        num_threads = DEFAULT_THREADS # 可以根据需要让用户输入线程数
        # 将条形码列表分割成适合每个线程处理的块（可选，但对于大量条码更有效）
        # 这里简单地为每个条码创建一个线程，线程数等于条码数（最多DEFAULT_THREADS）
        # 限制并发线程数
        active_threads = []
        thread_counter = 0
        # 修改 run_thread 函数以传递 (barcode, row_index) 
        def run_thread(barcode_with_row, thread_name, results_list):
             barcode, row_index = barcode_with_row
             # 修改 crawl_barcode 函数以接收行号并将其添加到结果中
             crawl_barcode_with_row(barcode, thread_name, results_list, row_index)
             # 线程完成后，从活动线程列表中移除
             active_threads.remove(threading.current_thread())
        # 修改 crawl_barcode 函数以接收行号并将其添加到结果中
        print(f"开始使用 {min(num_threads, len(barcodes_with_row_to_crawl))} 个线程进行爬取...") # 增加日志
        for barcode_with_row in barcodes_with_row_to_crawl:
            thread_name = f"Thread-{thread_counter + 1}"
            thread = threading.Thread(target=run_thread, args=(barcode_with_row, thread_name, results_list))
            threads.append(thread)
            active_threads.append(thread)
            thread.start()
            thread_counter += 1
            # 控制并发线程数
            while len(active_threads) >= num_threads:
                 # 等待任意一个活动线程完成
                 time.sleep(0.1) # 短暂等待，避免CPU空转
                 # 检查活动线程列表，移除已完成的线程
                 # 注意：直接修改列表可能导致问题，这里只是一个简化的逻辑
                 # 更好的方法是使用队列或线程池
                 active_threads = [t for t in active_threads if t.is_alive()]
        # 等待所有线程完成执行
        for thread in threads:
            thread.join()
        # 5. 更新Excel文件
        print("\n开始更新Excel文件...") # 增加日志
        # 修改 update_excel_with_results 函数以接收包含行号的结果列表
        update_excel_with_results_with_row(excel_filepath, results_list, barcode_column_letter, product_name_column_letter, image_column_letter)
        print("Excel文件更新完成。") # 增加日志
        total_end_time = time.time() # 记录总程序结束时间
        total_execution_time = total_end_time - total_start_time # 计算总执行时间
        num_barcodes = len(barcodes_with_row_to_crawl)
        average_time_per_barcode = 0
        if num_barcodes > 0:
            average_time_per_barcode = total_execution_time / num_barcodes
        print("\n" + "="*30)
        print(f"脚本执行完成。")
        print(f"总执行时间 (包括Excel更新): {total_execution_time:.2f} 秒")
        print(f"处理条码数量: {num_barcodes}")
        if num_barcodes > 0:
            print(f"平均每个条码时间: {average_time_per_barcode:.2f} 秒")
        print("="*30)
        #--- 添加翻译功能 ---
        print("\n开始进行翻译...") # 添加翻译开始提示
        # 调用翻译函数
        translate_excel(
            excel_filepath, # 输入文件路径
            output_path=None, # 使用默认输出路径 (原文件名后加 _translated.xlsx)
            start_row=start_row , # 翻译的起始行 
            end_row=end_row , # 翻译的结束行 
            src_col=product_name_column_letter, # 需要翻译的源列
            dst_col=translate_dst_column_letter, # 翻译结果写入的目标列
            show_log=True # 显示翻译日志
        )
        print("翻译过程完成。") # 添加翻译结束提示
    print("\n脚本执行完毕。")

if __name__ == "__main__":
    main()