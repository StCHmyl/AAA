from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def download_page(barcode):
    """
    使用 Selenium 下载指定条形码的网页内容并保存到本地文件。

    Args:
        barcode (str): 要下载的条形码。
    """
    url = f"https://www.barcodelookup.com/{barcode}"

    # 设置 ChromeOptions
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 无头模式
    chrome_options.add_argument("--disable-gpu")  # 禁用 GPU 加速
    chrome_options.add_argument("--window-size=1920x1080")  # 设置窗口大小
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    # 启动 Chrome 浏览器
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        driver.add_cookie({'name': '_cf_bm', 'value': '8XGkh0LuLYPAZMrDK.vnS.btrZNhxLDiw_exOsUP9mg-1745479470-1.0.1.1-rGS57f4Fy9WM5SmVQWXCl6FCwXiQbTobgaCFu5bHsxD3iRytEIjtW28iszTrN4pGEmNr4UrAx84jpTEgqgEg7fBBK6.RRwWIqFN8GQIa9pR0nZn4pEdg7nBI.joscpdU'})
        driver.add_cookie({'name': '__cflb', 'value': '04dToRCegghj9KSg7BqsUc4efEezbNiM5bsTUin4WR'})
        driver.add_cookie({'name': '__stripe_mid', 'value': '91fa57ff-ae1a-4942-9f8b-eaebf3c7f7f0fbee9e'})
        driver.add_cookie({'name': '_ga', 'value': 'GA1.1.2102088988.1740552691'})
        driver.add_cookie({'name': '_ga_6K9HJQ9YDK', 'value': 'GS1.1.1744365568.10.0.1744365568.0.0.0'})
        driver.add_cookie({'name': 'bl_csrf', 'value': 'dcafc059ee1fa8f1b192aaecf1be08f1'})
        driver.add_cookie({'name': 'bl_session', 'value': 'v5j160r3v385jgntqhae95ifpa1984u0'})
        driver.add_cookie({'name': 'cf_clearance', 'value': '1efKi63q6JwzfHCBXBD5uxAglQOa5KRaBqqRzfSw6hg-1745479472-1.2.1.1-NSXCzfqG8n7gGzbHqzaRiTylZ9ILazzrNFmXkMj8Z3T11F06cyEETQKuoTvqi4bOU8f_MfsGAcMq.FdXerhf1kDDYoSy1SJEb4B4CljbCidyk0Pjxcloxb3xsqV5k.C5Skzbf1kb8b7ZPgSST4vSu.tN2GmB8Zp5DtDiH.Ah0.jy3ERLZRHvYDcYAExa5kZ.pGIbYowew6bZIXtw4bcFg.1PWNClrP1hnzS9OvdAbdUw49_ZZ.2B4plP0bH_TwExV1t1MvmL4ZkRLNlWexGNxKrtInyhHYYfvCkECcRy30dV5rcDrfBW4eEGQC8MMJj0WREA.mzQyhXd7l6mGriyLOw43Wsr3mtLXNrcSUV0RGg'})
        driver.get(url)
        time.sleep(5)  # 等待页面加载

        # 获取页面内容
        html_content = driver.page_source

        # 保存到本地文件
        with open(f"{barcode}_selenium.html", "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"成功使用 Selenium 下载条形码 {barcode} 的网页内容。")

    except Exception as e:
        print(f"使用 Selenium 发生错误：{e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    barcode = "768614143925"
    download_page(barcode)
