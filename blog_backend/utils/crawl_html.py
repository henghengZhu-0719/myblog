import random
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime


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

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled"
                ]
            )

            context = browser.new_context(
                user_agent=random.choice(self.user_agents),
                viewport={"width": 1280, "height": 800}
            )

            page = context.new_page()

            # 隐藏 webdriver
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """)

            for url in self.urls:

                # 随机等待（模拟人）
                time.sleep(random.uniform(2, 5))

                try:
                    page.goto(url, wait_until="domcontentloaded")

                    page.wait_for_selector(
                        'dd[data-selector="job-intro-content"]',
                        timeout=10000
                    )

                    html_content = page.content()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    with open("test.html", "w", encoding="utf-8") as f:
                        f.write(str(soup))

                    # 职位标题 <span class="name ellipsis-2"><span class="job-title ellipsis-2">AI算法工程师</span></span>
                    title_tag = soup.select_one('span.name.ellipsis-2 span.job-title.ellipsis-2')
                    title = title_tag.get_text(strip=True) if title_tag else "无标题"

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

            browser.close()

        return results