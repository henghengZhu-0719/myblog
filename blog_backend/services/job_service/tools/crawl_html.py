import random
import time
from bs4 import BeautifulSoup
from datetime import datetime
import requests 
from langchain.tools import tool


user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        ]

@tool
def crawl_html(url_list: list[str]):
    """
    根据获得到的URL列表，爬取每个URL的HTML内容并保存到文件，用于后续解析该url的HTML内容，以此来为之后爬虫做解析准备
    """
    urls = url_list
    # 随机UA池
    user_agents = user_agents

    results = []

    for url in urls:

        # 随机等待（模拟人）
        time.sleep(random.uniform(2, 5))

        try:
            # 发送GET请求
            response = requests.get(url, headers={
                "User-Agent": random.choice(user_agents)
            })
            response.raise_for_status()  # 检查请求是否成功
            
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            # 保存HTML内容到文件
            filename = f"html_{url.split('/')[-1]}.html"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(str(soup))
        except Exception as e:
            print("爬取失败:", url, e)
    return results