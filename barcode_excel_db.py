
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
DATABASE_NAME = 'barcode_cache.db' # SQLite数据库文件名
# --- 数据库操作 ---
def init_database():
    """初始化SQLite数据库，创建缓存表（如果不存在）。"""
    print("数据库：初始化数据库...") # 增加日志
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                barcode TEXT PRIMARY KEY,
                product_name TEXT,
                image_url TEXT,
                image_filepath TEXT
            )
        ''')
        conn.commit()
        print("数据库：数据库初始化完成，'products'表已准备。") # 增加日志
    except Exception as e:
        print(f"错误：数据库初始化失败：{e}") # 增加日志
    finally:
        if conn:
            conn.close()

def get_product_from_db(barcode):
    """从数据库查询产品信息。"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT product_name, image_url, image_filepath FROM products WHERE barcode = ?', (barcode,))
        row = cursor.fetchone()
        conn.close()
        if row:
            print(f"数据库：查询到条码 {barcode} 的缓存数据。") # 增加日志
            return {'product_name': row[0], 'image_url': row[1], 'image_filepath': row[2]}
        print(f"数据库：未查询到条码 {barcode} 的缓存数据。") # 增加日志
        return None
    except Exception as e:
        print(f"错误：查询数据库失败：{e}") # 增加日志
        return None
    finally:
        if conn:
            conn.close()


def insert_product_to_db(barcode, product_name, image_url, image_filepath):
    """将产品信息插入数据库。"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO products (barcode, product_name, image_url, image_filepath) VALUES (?, ?, ?, ?)',
                       (barcode, product_name, image_url, image_filepath))
        conn.commit()
        print(f"数据库：成功插入/更新条码 {barcode} 的数据。") # 增加日志
    except Exception as e:
        print(f"错误：插入/更新数据库失败：{e}") # 增加日志
    finally:
        if conn:
            conn.close()
