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
#from translate_excel_openpyxl import translate_excel
from new_translate_excel_openpyxl import translate_excel
from RandomUaStealth import get_random_stealth_config, get_random_user_agent, record_failure, record_success
import random


# --- 配置 ---
DATABASE_NAME = 'barcode_cache.db'  # SQLite数据库文件名
IMAGE_DIR = 'downloaded_images'  # 图片保存目录
DEFAULT_THREADS = 5  # 默认线程数
# 目标网站URL模板
BASE_URL = "https://www.barcodelookup.com/{}"
# 产品图片XPath
IMAGE_XPATH = '/html/body/section[2]/div[1]/div/div/div[1]/div[1]/img'
# 产品名称XPath
PRODUCT_NAME_XPATH = '/html/body/section[2]/div[1]/div/div/div[2]/h4'
count=0  # 全局计数器，用于记录总的条形码成功处理数量
count_1=0  # 全局计数器，用于记录总的条形码在数据库中找到的数量
count_2=0  # 全局计数器，用于记录总的条形码成功爬取的数量

# 请求头配置
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.barcodelookup.com/",
    "Cookie": "__stripe_mid=xxx; bl_csrf=xxx; cf_bm=xxx"
}

# --- 图片下载 ---
def download_image(image_url, barcode):
    """下载图片并保存到本地。"""
    if not image_url:
        print(f"图片下载：图片URL为空，跳过下载条码 {barcode} 的图片。")  # 增加日志
        return None
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
        print(f"图片下载：创建图片保存目录: {IMAGE_DIR}")  # 增加日志
    # 尝试从URL中获取文件扩展名，如果失败则默认png
    try:
        file_extension = os.path.splitext(image_url.split('?')[0])[1]
        if not file_extension:
            file_extension = '.png'  # 默认扩展名
    except:
        file_extension = '.png'  # 默认扩展名
    image_filename = f"{barcode}{file_extension}"
    image_filepath = os.path.join(IMAGE_DIR, image_filename)
    # 检查图片是否已存在，避免重复下载
    if os.path.exists(image_filepath):
        print(f"图片下载：图片 {image_filename} 已存在，跳过下载。")  # 增加日志
        return image_filepath
    print(f"图片下载：开始下载图片 {image_url} 到 {image_filepath}")  # 增加日志
    try:
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()  # 检查HTTP请求是否成功
        with open(image_filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"图片下载：成功下载图片: {image_filename}")  # 增加日志
        return image_filepath
    except requests.exceptions.RequestException as e:
        print(f"错误：下载图片 {image_url} 失败: {e}")  # 增加日志
        return None


# --- 爬取逻辑 ---
# 修改 crawl_barcode 函数以接收行号并将其添加到结果中
def crawl_barcode_with_row(barcode, thread_name, results_list, row_index):
    """
    使用 Selenium 爬取单个条形码信息，处理Cloudflare和未找到情况，
    提取数据，下载图片，并将结果添加到共享列表（包含行号）。
    """
    global count, count_1, count_2  # 使用全局计数器
    print(f"线程 {thread_name} 开始处理条码: {barcode} (行号: {row_index})")  # 增加日志

    # 1. 检查数据库缓存
    cached_data = get_product_from_db(barcode)
    if cached_data and cached_data['product_name'] and cached_data['image_filepath'] and cached_data['product_name'] != "Not Found":
        print(f"线程 {thread_name}: 条码 {barcode} 在缓存中找到有效数据。")  # 增加日志
        results_list.append((barcode, cached_data['product_name'], cached_data['image_filepath'], row_index))  # 添加行号
        count_1 += 1  # 增加数据库找到的计数
        print(f"线程 {thread_name}: 当前数据库找到的条码数量: {count_1}")
        count += 1  # 增加总计数
        print(f"线程 {thread_name}: 当前总成功计数: {count}")
        return  # 从缓存获取，跳过爬取
    elif cached_data and cached_data['product_name'] == "Not Found":
        print(f"线程 {thread_name}: 条码 {barcode} 在缓存中标记为未找到。")  # 增加日志
        # results_list.append((barcode, "Not Found", None, row_index))  # 添加未找到结果和行号
        return  # 从缓存获取，跳过爬取
    elif cached_data and cached_data['product_name'] == "N/A":
        print(f"线程 {thread_name}: 条码 {barcode} 在缓存中标记为不规则数据。")  # 增加日志
        # results_list.append((barcode, "Not Found", None, row_index))  # 添加未找到结果和行号
        return  # 从缓存获取，跳过爬取
    # 2. 数据库中未找到或缓存无效，进行爬取
    url = BASE_URL.format(barcode)
    driver = None
    retry_count = 5  # 重试次数
    product_name = None
    image_url = None
    image_filepath = None
    print(f"最大重试次数: {retry_count}")  # 增加日志
    print(f"线程 {thread_name}: 缓存未命中或无效，开始网络爬取条码 {barcode}。")  # 增加日志
    for attempt in range(retry_count):
        try:
            # 随机选择 User-Agent 和 stealth 配置
            ua = get_random_user_agent()
            #stealth_cfg = get_random_stealth_config()
            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 启动浏览器并导航到 {url}")  # 增加日志
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # 无头模式：不显示浏览器窗口
            chrome_options.add_argument("--disable-gpu")  # 禁用 GPU 加速，有时可避免问题
            chrome_options.add_argument("--window-size=1920x1080")  # 设置浏览器窗口大小
            chrome_options.add_argument(f"user-agent={ua}")

            driver = webdriver.Chrome(options=chrome_options)
            '''
            stealth(driver,
                    languages=stealth_cfg["languages"],
                    vendor=stealth_cfg["vendor"],
                    platform=stealth_cfg["platform"],
                    webgl_vendor=stealth_cfg["webgl_vendor"],
                    renderer=stealth_cfg["renderer"],
                    fix_hairline=True,
                    )
            '''

            # 设置额外的请求头来避免被拦截
            try:
                driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
                    'headers': HEADERS
                })
                print(f"线程 {thread_name}: 已设置额外请求头")
            except Exception as e:
                print(f"线程 {thread_name}: 设置额外请求头失败: {e}")
            
            # time.sleep(random.uniform(0.5, 1.5))
            driver.set_page_load_timeout(10)
            driver.get(url)
            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 等待页面加载...")  # 增加日志
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 页面加载完成。")  # 增加日志
            # --- Cloudflare 拦截检测 ---
            if "Just a moment..." in driver.title or "Cloudflare" in driver.title or "Enable JavaScript and cookies to continue" in driver.page_source:
                print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 检测到 Cloudflare 拦截页面，进行重试。")  # 增加日志
                
                #retry_count += 1  # 增加重试次数
                print(f"Cloudflare 拦截检测,本次不计数进行额外尝试")  # 增加日志
                #record_failure(ua, stealth_cfg)  # 记录失败的UA和配置
                wait_time = random.uniform(0.125 * (2 ** ((attempt % 5) + 1)), 0.5 * (2 ** ((attempt % 5) + 1))) # 指数退避等待时间
                print(f"等待 {wait_time} 秒后重试")
                time.sleep(wait_time)  # 等待一段时间后重试
                if driver:
                    driver.quit()
                continue  # 进入下一次重试
            else:
                #record_success(ua, stealth_cfg)  # 记录成功的UA和配置
                print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): Cloudflare 拦截检测通过。")  # 增加日志
                print(f"线程 {thread_name}当前UA: {ua}")  # 增加日志
                #print(f"线程 {thread_name}当前Stealth配置: {stealth_cfg}")  # 增加日志
            # --- 条码未找到检测 ---
            if "Barcode Not Found | Barcode Lookup" in driver.title:
                print(f"线程 {thread_name}: 条码 {barcode} 未找到，跳过下载和截图。")  # 增加日志
                if driver:
                    driver.quit()
                # 将未找到的条码也存入数据库，标记为无产品信息，避免重复爬取
                insert_product_to_db(barcode, "Not Found", None, None)
                #results_list.append((barcode, "Not Found", None, row_index))  # 添加未找到结果和行号
                return  # 立即退出函数
            # --- 提取数据 ---
            print(f"线程 {thread_name}: 开始提取产品信息...")  # 增加日志
            try:
                # 提取产品名称
                product_name_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, PRODUCT_NAME_XPATH))
                )
                product_name = product_name_element.text.strip()
                #对产品名称进行检测，如果前6个字符都是数字，第七位是一个"."，则认为是错误的产品名称，依旧记录为None 
                if len(product_name) >= 7 and product_name[:6].isdigit() and product_name[6] == ".":
                    print(f"线程 {thread_name}: 提取到的产品名称 '{product_name}' 格式异常，标记为未找到。")  # 增加日志
                    product_name = None
                print(f"线程 {thread_name}: 提取到产品名称: '{product_name}'")  # 增加日志
            except (TimeoutException, WebDriverException):
                print(f"线程 {thread_name}: 未找到产品名称元素或提取失败。")  # 增加日志
                product_name = "N/A"  # 未找到则标记为N/A
            # --- 提取图片URL ---
            # 如果产品名称异常，即为“N/A”，则认为产品名称异常，跳过图片提取和下载
            if product_name == "N/A":
                print(f"线程 {thread_name}: 产品名称异常，标记为“N/A”，跳过图片提取和下载。")  # 增加日志
                image_url = None
                image_filepath = None
                # 将异常数据存入数据库，标记为N/A，避免重复爬取
                insert_product_to_db(barcode, "N/A", None, None)
                #results_list.append((barcode, "Not Found", None, row_index))  # 添加未找到结果和行号
                return  # 立即退出函数
            try:
                # 提取图片URL
                image_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, IMAGE_XPATH))
                )
                image_url = image_element.get_attribute('src')
                print(f"线程 {thread_name}: 提取到图片URL: {image_url}")  # 增加日志
            except (TimeoutException, WebDriverException):
                print(f"线程 {thread_name}: 未找到图片元素或提取失败。")  # 增加日志
                image_url = None  # 未找到则标记为None
            # --- 下载图片 ---
            if image_url:
                image_filepath = download_image(image_url, barcode)
            else:
                image_filepath = None
                print(f"线程 {thread_name}: 没有图片URL，跳过图片下载。")  # 增加日志
            # --- 存储到数据库 ---
            insert_product_to_db(barcode, product_name, image_url, image_filepath)
            print(f"线程 {thread_name}: 条码 {barcode} 数据已存入数据库。")  # 增加日志
            # --- 添加结果到列表 ---
            results_list.append((barcode, product_name, image_filepath, row_index))  # 添加行号
            print(f"线程 {thread_name}: 成功处理条码 {barcode}。")  # 增加日志
            count_2 += 1  # 成功爬取的条码计数
            print(f"线程 {thread_name}: 当前成功爬取条码数量: {count_2}")  # 增加日志
            count += 1  # 增加总计数
            print(f"线程 {thread_name}: 当前总成功计数: {count}")  # 增加日志
            break  # 成功完成，退出重试循环
        except (TimeoutException, WebDriverException) as e:
            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 使用 Selenium 发生错误：{e}")  # 增加日志
            if driver:
                driver.quit()  # 发生错误时关闭浏览器实例
            # 如果还有重试次数，打印重试提示
            if attempt < retry_count - 1:
                print(f"线程 {thread_name}: 进行重试。")  # 增加日志
            else:
                # 如果达到最大重试次数，未能成功处理条码 {barcode}。
                print(f"线程 {thread_name}: 达到最大重试次数，未能成功处理条码 {barcode}。")  # 增加日志
                print("将attempt重置为1，进行额外尝试")  # 增加日志
                attempt = 1  # 重置尝试计数器，进行额外尝试
        except Exception as e:
            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 发生未知错误：{e}")  # 增加日志
            if driver:
                driver.quit()  # 发生错误时关闭浏览器实例
            break  # 未知错误，不再重试
        finally:
            if driver:
                driver.quit()  # 确保每次尝试后都关闭浏览器实例


# --- 主程序入口 ---
def process_excel(excel_filepath, barcode_column_letter, start_row, end_row, image_column_letter,
                  product_name_column_letter, translate_dst_column_letter):
    global count, count_1, count_2  # 使用全局计数器
    total_start_time = time.time()  # 记录总程序开始时间
    print("脚本开始执行。")  # 增加日志

    print(f"用户输入：Excel文件路径='{excel_filepath}', 条码列='{barcode_column_letter}', 开始行={start_row}, 结束行={end_row}, 产品名称列='{product_name_column_letter}', 图片列='{image_column_letter}'")  # 增加日志
    # 2. 初始化数据库
    print("初始化数据库...")  # 增加日志
    init_database()
    print("数据库初始化完成。")  # 增加日志
    # 3. 读取条形码列表 (包含行号)
    barcodes_with_row_to_crawl = read_barcodes_from_excel_with_row(excel_filepath,
                                                                     barcode_column_letter, start_row, end_row)
    if not barcodes_with_row_to_crawl:
        print("未从Excel文件中读取到有效的条形码，脚本结束。")
    else:
        print(f"成功读取 {len(barcodes_with_row_to_crawl)} 个条码及对应行号。")  # 增加日志
        results_list = []  # 用于存储爬取结果 (barcode, product_name, image_filepath, row_index)  # 包含行号
        threads = []
        num_threads = DEFAULT_THREADS  # 可以根据需要让用户输入线程数
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
        print(f"开始使用 {min(num_threads, len(barcodes_with_row_to_crawl))} 个线程进行爬取...")  # 增加日志
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
                time.sleep(0.1)  # 短暂等待，避免CPU空转
                # 检查活动线程列表，移除已完成的线程
                # 注意：直接修改列表可能导致问题，这里只是一个简化的逻辑
                # 更好的方法是使用队列或线程池
                active_threads = [t for t in active_threads if t.is_alive()]
        # 等待所有线程完成执行
        for thread in threads:
            thread.join()
        # 5. 更新Excel文件
        print("\n开始更新Excel文件...")  # 增加日志
        # 修改 update_excel_with_results 函数以接收包含行号的结果列表
        update_excel_with_results_with_row(excel_filepath, results_list, barcode_column_letter,
                                             product_name_column_letter, image_column_letter)
        print("Excel文件更新完成。")  # 增加日志
        total_end_time = time.time()  # 记录总程序结束时间
        total_execution_time = total_end_time - total_start_time  # 计算总执行时间
        num_barcodes = len(barcodes_with_row_to_crawl)
        average_time_per_barcode = 0
        if num_barcodes > 0:
            average_time_per_barcode = total_execution_time / num_barcodes
        print("\n" + "=" * 30)
        print(f"脚本执行完成。")
        print(f"总执行时间 (包括Excel更新): {total_execution_time:.2f} 秒")
        print(f"处理条码数量: {num_barcodes}")
        if num_barcodes > 0:
            print(f"平均每个条码时间: {average_time_per_barcode:.2f} 秒")
        print("=" * 30)
        # --- 添加翻译功能 ---
        print("\n开始进行翻译...")  # 添加翻译开始提示
        # 调用翻译函数
        # translated_result=translate_excel(
        #     excel_filepath,  # 输入文件路径
        #     output_path=None,  # 使用默认输出路径 (原文件名后加 _translated.xlsx)
        #     start_row=start_row,  # 翻译的起始行
        #     end_row=end_row,  # 翻译的结束行
        #     src_col=product_name_column_letter,  # 需要翻译的源列
        #     dst_col=translate_dst_column_letter,  # 翻译结果写入的目标列
        #     show_log=True  # 显示翻译日志
        # )
        translated_result = translate_excel(excel_filepath, output_path=None, start_row=start_row, end_row=end_row, src_col=product_name_column_letter, dst_col=translate_dst_column_letter,barcode_col=barcode_column_letter,show_log=True)  
        # 调用翻译函数；输入文件路径：excel_filepath；默认输出路径（原文件名后加 _translated.xlsx）；翻译起始行：start_row；结束行：end_row；源列：product_name_column_letter；目标列：translate_dst_column_letter；EAN列：barcode_column_letter；显示翻译日志：True

        print("翻译过程完成。")  # 添加翻译结束提示
        print(f"处理条码数量: {num_barcodes}")

        print("{} 个条形码失败。".format({num_barcodes-count}))  # 打印失败条形码数量
              
    print("{} 个条形码处理成功".format(count))  # 打印总处理条形码数量
    count=0  # 重置计数器
    print("{} 个条形码在数据库中成功找到。".format(count_1))  # 打印数据库找到的条形码数量
    count_1=0  # 重置数据库找到的计数器
    print("{} 个条形码在数据库未找到但爬取到了。".format(count_2))
    count_2=0  # 重置成功爬取的计数器
    
    print("\n脚本执行完毕。")
    #return excel_filepath
    return translated_result['output_path']

if __name__ == "__main__":
    process_excel("NR+SHISEIDO SPECIAL OFFER.xlsx", "B", 12, 20, "N", "O", "P")
