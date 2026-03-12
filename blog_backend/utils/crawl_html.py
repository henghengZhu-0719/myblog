import random
import time
from bs4 import BeautifulSoup
from datetime import datetime
import requests 


class CrawlHtml:
    def __init__(self, url_list: list[str]):
        self.urls = url_list
        # 随机UA池
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        ]

    def crawl_html(self):
        results = []

        for url in self.urls:

            # 随机等待（模拟人）
            time.sleep(random.uniform(2, 5))

            try:
                # 发送GET请求
                response = requests.get(url, headers={
                    "User-Agent": random.choice(self.user_agents)
                })
                response.raise_for_status()  # 检查请求是否成功
                
                html_content = response.text
                soup = BeautifulSoup(html_content, 'html.parser')
                with open("test.html", "w", encoding="utf-8") as f:
                    f.write(str(soup))

                title_tag = soup.select_one('.job-title-box div[title]')
                title = title_tag["title"] if title_tag else "无标题"

                # 职位详情
                details = soup.select_one('dd[data-selector="job-intro-content"]')
                details_text = details.get_text(separator="\n", strip=True) if details else "无详情"

                # 地址
                tag = soup.find('div', class_='job-properties')
                if tag:
                    # 过滤掉 class="split" 的分隔符，只要有内容的 span
                    spans = [
                        s.get_text(strip=True) 
                        for s in tag.find_all('span') 
                        if 'split' not in s.get('class', []) and s.get_text(strip=True)
                    ]
                    # spans = ['上海-浦东新区', '应届', '本科', '学生可投', '招2人', '1月28日更新']
                    dq = spans[0] if spans else "无地址"

                

                crawl_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                results.append({
                    "title": title,
                    "url": url,
                    "details": details_text,
                    "dq": dq,
                    "crawl_time": crawl_time
                })

            except Exception as e:
                print("爬取失败:", url, e)

        return results