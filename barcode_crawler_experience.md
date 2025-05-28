# 条形码爬虫实战：我是如何突破 Cloudflare 反爬虫的

最近在做一个条形码信息爬虫项目，目标是抓取 barcodelookup.com 上的商品信息。刚开始用单线程 Selenium 脚本跑得还不错，但处理大批量条形码时效率太低，明显不够用。

于是想到用多线程来提速。用 Python 的 `threading` 模块写了个多线程版本，本以为能轻松搞定，没想到 Cloudflare 反爬虫系统给了我当头一棒。

先来看看最初的单线程脚本核心代码：

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def download_page(barcode):
    """
    使用 Selenium 下载指定条形码的网页内容并保存到本地文件。
    """
    url = f"https://www.barcodelookup.com/{barcode}"
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(url)
        time.sleep(5) # 简单的固定等待
        html_content = driver.page_source
        with open(f"{barcode}_selenium.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"成功下载条形码 {barcode} 的网页内容。")
    except Exception as e:
        print(f"发生错误：{e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    barcode = "768614143925"
    download_page(barcode)
```

### 遭遇 Cloudflare 拦截

多线程脚本一跑起来就出问题了 - 大部分请求都被 Cloudflare 拦截，返回的都是验证页面。这说明网站的反爬虫系统很强大，能识别自动化工具和高频访问。

我试了几种方法：
1. 加 `time.sleep()` 模拟人工操作 - 效果很差，固定延迟太容易被识别
2. 用免费代理换IP - 从 `https://github.com/cyubuchen/Free_Proxy_Website/tree/master` 获取的免费 SOCKS 代理质量太差，要么连不上，要么速度慢，成功率很低
3. 硬编码 Cookie - 反而和代理冲突，雪上加霜

使用代理时的 Chrome option 配置示例：

```python
chrome_options = Options()
# ... 其他选项
if proxy:
    chrome_options.add_argument(f"--proxy-server=socks5://{proxy}") # 添加代理设置
driver = webdriver.Chrome(options=chrome_options)
```

### 突破封锁的实战方案

经过多次尝试，我总结出一套有效的解决方案：

1. 首先去掉硬编码的旧 Cookie - Selenium 自己会管理 Cookie，硬编码的反而添乱
2. 引入 `selenium-stealth` 库 - 这个神器能修改 WebDriver 的各种特征，比如 `navigator.webdriver` 属性，让它更像真人浏览器

集成 `selenium-stealth` 的关键代码：

```python
from selenium_stealth import stealth
# ... WebDriver 初始化后
stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
        )
```

仅仅依靠 `selenium-stealth` 仍然不足以应对所有情况，尤其是在网络不稳定或遇到特别严格的检测时。因此，我们增加了健壮的错误处理和重试机制。在每次下载失败时，脚本会尝试重新初始化 WebDriver 并再次请求，最多重试 3 次。虽然我们不再使用代理进行重试（因为免费代理质量太差），但重试本身增加了成功的机会。

3. 用智能等待取代傻等 - 把固定的 `time.sleep(5)` 换成 Selenium 的 `WebDriverWait`，它会等页面元素真正加载完成才继续，更灵活可靠

包含重试、超时和显式等待的下载函数核心代码：

```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException

def download_page(barcode, thread_name): # 移除了代理参数
    url = f"https://www.barcodelookup.com/{barcode}"
    thread_dir = thread_name
    if not os.path.exists(thread_dir):
        os.makedirs(thread_dir)

    retry_count = 3
    for attempt in range(retry_count):
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920x1080")
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

            driver = webdriver.Chrome(options=chrome_options)
            stealth(driver, ...) # 应用 stealth

            driver.set_page_load_timeout(30) # 设置页面加载超时时间
            driver.get(url)

            # 使用显式等待，等待 body 元素出现
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            html_content = driver.page_source
            with open(os.path.join(thread_dir, f"{barcode}_selenium.html"), "w", encoding="utf-8") as f:
                f.write(html_content)
            driver.save_screenshot(os.path.join(thread_dir, f"{barcode}_selenium.png"))

            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 成功下载条形码 {barcode} 的网页内容。")
            return # 成功后退出

        except (TimeoutException, WebDriverException) as e:
            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 使用 Selenium 发生错误：{e}")
            if driver:
                driver.quit()
            if attempt < retry_count - 1:
                print(f"线程 {thread_name}: 进行重试。")
            else:
                print(f"线程 {thread_name}: 达到最大重试次数。")
        except Exception as e:
            print(f"线程 {thread_name} (尝试 {attempt + 1}/{retry_count}): 发生未知错误：{e}")
            if driver:
                driver.quit()
            break # 未知错误，不再重试

    print(f"线程 {thread_name}: 未能成功下载条形码 {barcode} 的网页内容。")
```

多线程脚本的主体结构：

```python
if __name__ == "__main__":
    barcodes = [ # ... 条形码列表 ]
    thread_names = [f"Thread-{i+1}" for i in range(len(barcodes))]

    threads = []
    for i in range(len(barcodes)):
        # 传递条形码和线程名称
        thread = threading.Thread(target=download_page, args=(barcodes[i], thread_names[i]))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("所有线程完成。")
```

### 实战心得

这个项目让我学到不少反爬虫经验：

* 反爬虫是场持久战，没有万能药 几天就得改点东西 
* `selenium-stealth` 确实有两把刷子 
* 要用代理就得用付费的，免费的太坑 得有验证环节 
* 完善的错误处理能让脚本更稳定 确实
* 智能等待比固定延迟靠谱多了
* 线程控制要小心，不要把线程数设得太大，可能会导致内存溢出或者死锁

总体来说，这个项目让我对 Python 的 Web 抓取、Selenium 的使用、代理的使用、错误处理、线程控制、智能等待、selenium-stealth 的使用等等都有了更好的理解。

运行这个脚本时，请确保已安装所需的依赖库。


***存在问题 ***目前使用多线程不知道是否会产生冲突

## 关于spys.one代理使用的实战经验 - 2025/5/27更新

今天又尝试爬取spys.one这个网站，发现几个值得记录的经验：

1. **访问限制**：
   - 这个网站在国内直接被屏蔽了，必须开代理才能访问
   - 即使开了代理，连接也经常不稳定

2. **IP可用性测试**：
   - 写了个测试脚本批量检查IP可用性
   - 结果发现大概只有1/5的IP能正常使用（20%左右）
   - 好IP和坏IP混杂在一起，需要自己筛选

3. **错误处理改进建议**：
   - 采用"累计错误计数"机制：
     * 每个IP开始时有100点"健康值"
     * 每次请求失败扣1点
     * 当健康值≤0时自动切换新IP
   - 这样能最大化利用每个可用IP

4. **多线程问题**：
   - 在多线程环境下使用要特别注意：
     * 需要为每个线程维护独立的IP池和错误计数器
     * 使用线程锁(Lock)保护共享资源
     * 避免多个线程同时切换IP导致冲突
   - 建议实现方案：
     * 创建一个代理管理器类，封装IP分配和错误计数
     * 使用队列(Queue)管理可用IP
     * 每个线程从队列获取IP，使用后根据结果决定是否放回

5. **代码示例**：
```python
import threading
from queue import Queue

class ProxyManager:
    def __init__(self, ip_list):
        self.ip_queue = Queue()
        self.ip_health = {}  # {ip: health}
        self.lock = threading.Lock()
        
        for ip in ip_list:
            self.ip_queue.put(ip)
            self.ip_health[ip] = 100  # 初始健康值100
            
    def get_proxy(self):
        with self.lock:
            if not self.ip_queue.empty():
                return self.ip_queue.get()
        return None
        
    def report_result(self, ip, success):
        with self.lock:
            if success:
                self.ip_health[ip] = min(100, self.ip_health[ip] + 5)  # 成功增加健康值
                self.ip_queue.put(ip)
            else:
                self.ip_health[ip] -= 1  # 失败减少健康值
                if self.ip_health[ip] > 0:
                    self.ip_queue.put(ip)  # 还有健康值就继续使用
```

这个代理管理器可以很好地解决多线程环境下的IP管理问题，建议集成到爬虫项目中。
