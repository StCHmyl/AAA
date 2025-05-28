import os
import re
import time
import requests
from requests.exceptions import ConnectionError

CHECKED_PROXY = 'unchecked_proxy_spysone'
url = 'http://spys.one/en/socks-proxy-list/'

xpp = '5'
xf1 = '4'
xf2 = '0'
xf4 = '0'
xf5 = '2'

unchecked = []
file_path_unchecked = '{0}/{1}.txt'.format(os.getcwd(), CHECKED_PROXY)

def get_index(xpp, xf1, xf2, xf4, xf5):
    header = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0.2 Safari/605.1.15'
    }
    data = {
        'xpp': xpp,
        'xf1': xf1,
        'xf2': xf2,
        'xf4': xf4,
        'xf5': xf5
    }
    print('Getting the website...')
    try:
        rsp = requests.post(url=url, headers=header, data=data)
        if rsp.status_code == 200:
            print('Success.')
            html = rsp.text
            return html
        else:
            exit('Can not get the website.')
    except ConnectionError:
        exit('Please run your proxy app and try again.')

def get_proxy_info(html):
    pattern = re.compile(
        r'onmouseout.*?spy14>(.*?)<s.*?write.*?nt>\"\+(.*?)\)</scr.*?/en/(.*?)-', re.S
    )
    infos = re.findall(pattern, html)
    return infos

def parse_proxy_info(html, infos):
    print('共获取到 {} 个代理。'.format(len(infos)))
    print('开始解析代理详细信息...')
    # 提取端口加密串
    port_word = re.findall(r'\+\(([a-z0-9^]+)\)+', html)

    port_passwd = {}
    # 提取端口解密脚本
    portcode = re.findall(
        r'table><script type="text/javascript">(.*)</script>', html
    )[0].split(';')
    print(f"[调试] 端口解密脚本片段数量: {len(portcode)}")
    for i in portcode:
        ii = re.findall(r'\w+=\d+', i)
        for i in ii:
            kv = i.split('=')
            if len(kv[1]) == 1:
                k = kv[0]
                v = kv[1]
                port_passwd[k] = v
    print(f"[调试] 端口解密映射: {port_passwd}")

    for idx, i in enumerate(infos):
        proxies_info = {
            'ip': i[0],
            'port': i[1],
            'protocol': i[2]
        }
        # 解密端口
        port_word = re.findall(r'\((\w+)\^', proxies_info.get('port'))
        port_digital = ''
        for k in port_word:
            port_digital += port_passwd.get(k, '?')
        if '?' in port_digital:
            print(f"[警告] 第{idx+1}个代理端口解密失败: {proxies_info.get('ip')} {proxies_info.get('port')}")
        else:
            print(f"[调试] 代理{idx+1}: {proxies_info.get('ip')}:{port_digital} 协议: {proxies_info.get('protocol')}")
        test_it = '{0}:{1}'.format(proxies_info.get('ip'), port_digital)
        unchecked.append(test_it)

def test_proxies_from_file(file_path, test_url="http://httpbin.org/ip", timeout=5):
    """
    从文件中读取代理列表，逐个检测其可用性，并输出检测结果。
    :param file_path: 代理列表文件路径
    :param test_url: 用于测试代理可用性的目标网址
    :param timeout: 请求超时时间（秒）
    :return: list，可用代理列表（格式同文件中，如 "ip:port"）
    """
    import os
    import requests
    from requests.exceptions import RequestException

    print(f"开始检测代理文件: {file_path}")
    if not os.path.exists(file_path):
        print("未找到代理文件。请先抓取代理。")
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    proxies = [line.strip() for line in lines if line and not line.startswith('>>>')]
    total = len(proxies)
    available = 0
    available_proxies = []

    print(f"共读取到 {total} 个代理，开始逐个检测...")

    for i, proxy in enumerate(proxies):
        print(f"正在检测第 {i+1}/{total} 个代理: {proxy}")
        try:
            proxy_url = f"socks5://{proxy}"
            rsp = requests.get(test_url, proxies={"http": proxy_url, "https": proxy_url}, timeout=timeout)
            print(f"代理 {proxy} 检测结果: {rsp.status_code} - {rsp.text.strip()}")
            if rsp.status_code == 200:
                print(f"✅ 可用代理: {proxy}")
                available += 1
                available_proxies.append(proxy)
            else:
                print(f"❌ 不可用代理: {proxy}，状态码: {rsp.status_code}")
        except RequestException as e:
            print(f"❌ 不可用代理: {proxy}，异常信息: {e}")

    print(f"\n检测完成。可用代理数量: {available}/{total}")
    return available_proxies

def main():
    html = get_index(xpp, xf1, xf2, xf4, xf5)
    infos = get_proxy_info(html)
    parse_proxy_info(html, infos)
    with open(file_path_unchecked, 'a+', encoding='utf-8') as f:
        f.write(time.strftime(">>>%Y-%m-%d %H:%M:%S", time.localtime()) + '\n')
        for proxy in unchecked:
            f.write(proxy + '\n')
    print('Save to {}.\nDone.'.format(file_path_unchecked))
    return unchecked

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

def fetch_product_info(barcode: str, proxy: str = None, headless: bool = True, timeout: int = 10):
    """
    使用 Selenium 抓取产品名称和图片链接，并在失败时保存带时间戳的 HTML 和截图。
    """
    base_url = f"https://www.barcodelookup.com/{barcode}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # 当前时间戳

    image_xpath = '//div[@class="product-image"]//img'
    name_xpath = '//div[@class="product-details"]//h4'

    chrome_options = Options()
    if proxy:
        chrome_options.add_argument(f'--proxy-server={proxy}')
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--window-size=1920,1080')

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(timeout)

        print(f"🔍 正在访问: {base_url}")
        driver.get(base_url)

        wait = WebDriverWait(driver, timeout)
        name_element = wait.until(EC.presence_of_element_located((By.XPATH, name_xpath)))
        image_element = wait.until(EC.presence_of_element_located((By.XPATH, image_xpath)))

        return {
            "barcode": barcode,
            "product_name": name_element.text.strip(),
            "image_url": image_element.get_attribute("src")
        }

    except Exception as e:
        print(f"❌ 抓取失败: {barcode}，错误: {e}")

        # 保存截图
        try:
            screenshot_path = f"{barcode}_{timestamp}.png"
            driver.save_screenshot(screenshot_path)
            print(f"📸 已保存失败截图: {screenshot_path}")
        except:
            pass

        # 保存 HTML
        try:
            html_path = f"{barcode}_{timestamp}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"💾 已保存网页 HTML: {html_path}")
        except Exception as html_err:
            print(f"⚠️ HTML 保存失败: {html_err}")

        return None

    finally:
        if driver:
            driver.quit()


def fetch_barcode_info(barcode: str, proxy_address: str, timeout: int = 10):
    """
    获取条形码信息并直接打印状态码和网页内容。

    参数:
        barcode (str): 条形码编号
        proxy_address (str): 代理地址，格式为 "ip:port"
        timeout (int): 请求超时时间（默认 10 秒）
    """
    url = f"https://www.barcodelookup.com/{barcode}"
    proxy_url = f'socks5h://{proxy_address}'
    proxies = {
        'http': proxy_url,
        'https': proxy_url,
    }

    try:
        response = requests.get(url, proxies=proxies, timeout=timeout)
        print(f"状态码: {response.status_code}")
        print("网页内容:\n", response.text)
    except requests.RequestException as e:
        print(f"请求失败: {e}")

if __name__ == '__main__':
    #main()
    
    a=test_proxies_from_file(file_path_unchecked)
    print(f"可用代理数量: {len(a)}")
    print("可用代理列表:")
    for proxy in a:
        print(proxy)
    for proxy in a:
        print(f"使用代理{proxy}抓取商品信息...")
        #fetch_barcode_info("701666410607", proxy_address=proxy, timeout=10)
        product_info = fetch_product_info("701666410607", proxy=proxy)
        print(f"抓取结果: {product_info}")
