"""
多线程条形码爬虫脚本

该脚本使用 Selenium 和 Chrome WebDriver 多线程抓取 barcodelookup.com 网站上
特定条形码的详细信息。为了应对网站的反爬虫机制（特别是 Cloudflare），
脚本集成了 selenium-stealth 库，并实现了页面加载超时、显式等待以及
对 Cloudflare 拦截页面的检测和重试机制。

每个线程负责抓取一个条形码的信息，并将抓取到的页面 HTML 内容和截图
保存到以线程名称命名的单独文件夹中。同时，脚本会记录并输出总执行时间
以及每个线程的执行时间，以便进行性能分析。

依赖库:
- selenium: 用于浏览器自动化
- selenium-stealth: 用于使 Selenium 更难被检测
- threading: 用于实现多线程
- os: 用于文件系统操作（创建目录、拼接路径）
- time: 用于添加延时和记录时间
- random: 未在当前版本中使用，但可能用于随机化操作
"""

import threading # 导入多线程模块
import os # 导入操作系统模块，用于文件路径操作
import time # 导入时间模块
from selenium import webdriver # 导入 Selenium WebDriver
from selenium.webdriver.chrome.options import Options # 导入 Chrome 浏览器选项
import random # 导入随机数模块 (当前版本未使用)
from selenium_stealth import stealth # 导入 selenium-stealth 库
from selenium.webdriver.support.ui import WebDriverWait # 导入 Selenium 显式等待类
from selenium.webdriver.support import expected_conditions as EC # 导入预期条件模块
from selenium.webdriver.common.by import By # 导入定位器策略模块
from selenium.common.exceptions import TimeoutException, WebDriverException # 导入 Selenium 异常类

def download_page(barcode, thread_name):
    """
    使用 Selenium 下载指定条形码的网页内容并保存到本地文件和截图，带重试。
    同时记录并保存该线程的执行时间。

    Args:
        barcode (str): 要下载的条形码。
        thread_name (str): 线程名称，用于创建目录和标识输出。
    """
    thread_start_time = time.time() # 记录线程开始时间

    # 构建目标 URL
    url = f"https://www.barcodelookup.com/{barcode}"

    # 为每个线程创建独立的输出目录
    thread_dir = thread_name
    if not os.path.exists(thread_dir):
        os.makedirs(thread_dir) # 如果目录不存在则创建

    retry_count = 3 # 定义每个条形码的最大重试次数
    success = False # 标志，用于判断是否成功下载

    # 开始重试循环
    for attempt in range(retry_count):
        driver = None # 初始化 driver 为 None
        try:
            # --- Selenium WebDriver 设置 ---
            chrome_options = Options() # 创建 ChromeOptions 对象
            chrome_options.add_argument("--headless")  # 无头模式：不显示浏览器窗口
            chrome_options.add_argument("--disable-gpu")  # 禁用 GPU 加速，有时可避免问题
            chrome_options.add_argument("--window-size=1920x1080")  # 设置浏览器窗口大小
            # 设置 User-Agent 模拟真实浏览器
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            # 可以根据需要添加其他选项，例如代理：
            # chrome_options.add_argument(f"--proxy-server=socks5://your_proxy_address:port")

            # 启动 Chrome 浏览器实例
            driver = webdriver.Chrome(options=chrome_options)

            # 应用 selenium-stealth 设置，使其更难被检测为自动化工具
            stealth(driver,
                    languages=["en-US", "en"], # 模拟浏览器语言
                    vendor="Google Inc.", # 模拟浏览器厂商
                    platform="Win32", # 模拟操作系统平台
                    webgl_vendor="Intel Inc.", # 模拟 WebGL 厂商
                    renderer="Intel Iris OpenGL Engine", # 模拟 WebGL 渲染器
                    fix_hairline=True, # 修复一些渲染细节
                    )

            # 设置页面加载超时时间（秒）
            driver.set_page_load_timeout(30)

            # 导航到目标 URL
            driver.get(url)

            # --- 显式等待页面元素加载 ---
            # 使用显式等待，最长等待 10 秒，直到页面的 body 元素出现
            # 这是一个通用的等待方式，确保页面主体内容已加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # 获取当前页面的完整 HTML 内容
            html_content = driver.page_source

            # --- Cloudflare 拦截检测 ---
            # 检查页面标题或内容是否包含 Cloudflare 拦截页面的常见标识
            if "Just a moment..." in driver.title or "Cloudflare" in driver.title or "Enable JavaScript and cookies to continue" in html_content:
                # 如果检测到拦截页面，打印提示信息
                print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 检测到 Cloudflare 拦截页面，进行重试。")
                if driver:
                    driver.quit() # 关闭当前浏览器实例
                continue # 跳过后续保存步骤，进入下一次重试循环

            # --- 条码未找到检测 ---
            # 检查页面标题是否表示条码未找到
            if "Barcode Not Found | Barcode Lookup" in driver.title:
                print(f"线程 {thread_name}: 条码 {barcode} 未找到，跳过下载和截图。")
                if driver:
                    driver.quit() # 关闭当前浏览器实例
                return # 立即退出函数，不再进行重试和后续操作

            # --- 保存结果 ---
            # 如果未被拦截，将页面 HTML 内容保存到文件
            html_filepath = os.path.join(thread_dir, f"{barcode}_selenium.html")
            with open(html_filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            # 保存当前页面的截图为 PNG 文件
            screenshot_filepath = os.path.join(thread_dir, f"{barcode}_selenium.png")
            driver.save_screenshot(screenshot_filepath)

            # 打印成功信息
            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 成功使用 Selenium 下载条形码 {barcode} 的网页内容。")
            success = True # 设置成功标志为 True
            break # 成功后退出重试循环

        # --- 异常处理 ---
        # 捕获 Selenium 相关的超时或 WebDriver 异常
        except (TimeoutException, WebDriverException) as e:
            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 使用 Selenium 发生错误：{e}")
            if driver:
                driver.quit() # 发生错误时关闭浏览器实例
            # 如果还有重试次数，打印重试提示
            if attempt < retry_count - 1:
                print(f"线程 {thread_name}: 进行重试。")
            else:
                # 如果达到最大重试次数，打印失败提示
                print(f"线程 {thread_name}: 达到最大重试次数。")
        # 捕获其他未知异常
        except Exception as e:
            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 发生未知错误：{e}")
            if driver:
                driver.quit() # 发生错误时关闭浏览器实例
            break # 遇到未知错误，不再重试

    # 如果所有重试都失败
    if not success:
        print(f"线程 {thread_name}: 未能成功下载条形码 {barcode} 的网页内容。")

    thread_end_time = time.time() # 记录线程结束时间
    thread_execution_time = thread_end_time - thread_start_time # 计算线程执行时间

    # 将线程执行时间保存到 time.txt 文件
    time_filepath = os.path.join(thread_dir, "time.txt")
    with open(time_filepath, "w") as f:
        f.write(f"Thread Execution Time: {thread_execution_time:.2f} seconds\n")

# --- 主程序入口 ---
if __name__ == "__main__":
    total_start_time = time.time() # 记录总程序开始时间

    # 定义要抓取的条形码列表
    barcodes = [
        "3423222108373",
        "3423222108380",
        "3423222108397",
        "3423222108755",
        "768614143925",
        "768614156758",
        "768614160434",
        "768614160441",
        "768614178767",
        "8053288240004",
    ]
    # 生成与条形码列表对应的线程名称列表
    thread_names = [f"Thread-{i+1}" for i in range(len(barcodes))]

    threads = [] # 创建一个列表来存储线程对象
    # 遍历条形码列表，为每个条形码创建一个线程
    for i in range(len(barcodes)):
        # 创建一个新线程，目标函数是 download_page，并传递条形码和线程名称作为参数
        thread = threading.Thread(target=download_page, args=(barcodes[i], thread_names[i]))
        threads.append(thread) # 将线程添加到列表中
        thread.start() # 启动线程

    # 等待所有线程完成执行
    for thread in threads:
        thread.join() # 阻塞主线程，直到当前线程执行完毕

    total_end_time = time.time() # 记录总程序结束时间
    total_execution_time = total_end_time - total_start_time # 计算总执行时间

    # 所有线程完成后，打印总执行时间
    print("\n" + "="*30)
    print(f"所有线程完成。")
    print(f"总执行时间: {total_execution_time:.2f} 秒")
    print("="*30)

    # 提示用户查看每个线程的时间开销文件
    print("\n每个线程的详细时间开销已保存在各自的文件夹中的 time.txt 文件中。")
