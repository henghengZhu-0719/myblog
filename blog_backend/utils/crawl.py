import random
import time
from bs4 import BeautifulSoup
import requests
import smtplib
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
import sys
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 添加项目根目录到 sys.path，以便能够导入项目中的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EMAIL_CONFIG, BASE_URL, TARGETS_FILE


@dataclass(frozen=True)
class CrawledJob:
    title: str
    publish_date: object
    url: str
    type: str
    crawl_date: datetime
    dq: str

# ========== 数据库操作函数 ==========

def get_existing_urls():
    """获取数据库中已存在的 URL 集合"""
    from database import SessionLocal
    from models.job import Job

    db = SessionLocal()
    try:
        urls = db.query(Job.url).all()
        return {url[0] for url in urls}
    finally:
        db.close()

def save_jobs(jobs: list[CrawledJob]) -> list[dict[str, object]]:
    """批量保存 Job 对象到数据库"""
    if not jobs:
        return []
    
    from database import SessionLocal
    from models.job import Job

    db = SessionLocal()
    try:
        # 逐个添加，避免重复键错误导致整个批次失败（虽然我们在外面已经做了去重）
        saved_jobs: list[dict[str, object]] = []
        for job in jobs:
            try:
                db_job = Job(
                    title=job.title,
                    publish_date=job.publish_date,
                    url=job.url,
                    type=job.type,
                    crawl_date=job.crawl_date,
                    dq=job.dq,
                )
                db.add(db_job)
                db.commit()
                saved_jobs.append({
                    "title": db_job.title,
                    "url": db_job.url,
                    "publish_date": db_job.publish_date,
                    "type": db_job.type,
                    "dq": db_job.dq,
                })
            except Exception as e:
                db.rollback()
        return saved_jobs
    finally:
        db.close()

# ========== 解析函数定义 ==========

def parse_company_news(html: str) -> list[CrawledJob]:
    """解析公司招聘页面"""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.t-consultation-news a.t-consultation-item")
    jobs = []
    
    for item in items:
        title = item.find('span', class_='t-consultation-news-title').get_text(strip=True)
        date_str = item.find('span', class_='t-news-time').get_text(strip=True)
        url = urljoin(BASE_URL, item['href'])
        
        # 处理日期格式，确保是 Date 类型
        try:
            publish_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            publish_date = datetime.now().date()

        jobs.append(CrawledJob(
            title=title,
            publish_date=publish_date,
            url=url,
            type="公司招聘",
            crawl_date=datetime.now(),
            dq="江西"
        ))
    return jobs

def parse_exam_news(html: str) -> list[CrawledJob]:
    """解析考试公告页面"""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("ul.t-exam-notice-list li.t-exam-notice-big-item")
    jobs = []

    for item in items:
        title = item.find('span').get_text(strip=True)
        date_str = item.find('em').get_text(strip=True)
        url = urljoin(BASE_URL, item.find('a')['href'])
        
        try:
            publish_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            publish_date = datetime.now().date()
        
        jobs.append(CrawledJob(
            title=title,
            publish_date=publish_date,
            url=url,
            type="考试公告",
            crawl_date=datetime.now(),
            dq="江西"
        ))
    return jobs

def parse_ncrczpw_gq(html: str) -> list[CrawledJob]:
    """解析南昌人才招聘网页面"""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.listContainer ul li")
    jobs = []

    for item in items:
        link = item.find('a')
        if not link:
            continue
        title = link.get_text(strip=True)
        url = link['href']
        # 处理可能的相对链接
        if url.startswith('/'):
            url = "https://www.ncrczpw.com" + url
        elif not url.startswith('http'):
            # 如果是 ?m=... 这种形式
            url = "https://www.ncrczpw.com/" + url

        publish_date = datetime.now().date()
        time_span = item.find('span', class_='time')
        if time_span:
            # 格式: "更新时间: 2026-03-03 阅[4238]"
            text = time_span.get_text(strip=True)
            if "更新时间:" in text:
                try:
                    date_part = text.split('更新时间:')[1].strip()
                    date_str = date_part.split(' ')[0]
                    publish_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except:
                    pass

        jobs.append(CrawledJob(
            title=title,
            publish_date=publish_date,
            url=url,
            type="南昌人才国企",
            crawl_date=datetime.now(),
            dq="江西"
        ))
    return jobs


def parse_ncrczpw_qy(html: str) -> list[CrawledJob]:
    """解析南昌人才企业招聘网页面"""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.newslist div.listb")
    jobs = []

    for idx, item in enumerate(items, 1):
        try:
            title_link = item.select_one("div.t.substring a")
            if not title_link:
                continue
            
            title = title_link.get_text(strip=True)
            url = title_link.get('href', '')
            
            if not url:
                continue
            
            if url.startswith('/'):
                url = "https://www.ncrczpw.com" + url
            elif not url.startswith('http'):
                url = "https://www.ncrczpw.com/" + url

            publish_date = datetime.now().date()
            time_div = item.select_one("div.time.substring")
            if time_div:
                date_text = time_div.get_text(strip=True)
                # 日期格式: "2026-03-04"
                if date_text and len(date_text) >= 10:
                    try:
                        publish_date = datetime.strptime(date_text[:10], "%Y-%m-%d").date()
                    except ValueError:
                        pass
            
            jobs.append(CrawledJob(
                title=title,
                publish_date=publish_date,
                url=url,
                type="南昌人才企业",
                crawl_date=datetime.now(),
                dq="江西"
            ))
            
        except Exception as e:
            continue
    
    return jobs


def parse_ncrczpw_mq(html: str) -> list[CrawledJob]:
    """解析南昌人才名企招聘网页面"""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.newslist div.listb")
    jobs = []

    for idx, item in enumerate(items, 1):
        try:
            title_link = item.select_one("div.t.substring a")
            if not title_link:
                continue
            
            title = title_link.get_text(strip=True)
            url = title_link.get('href', '')
            
            if not url:
                continue
            
            if url.startswith('/'):
                url = "https://www.ncrczpw.com" + url
            elif not url.startswith('http'):
                url = "https://www.ncrczpw.com/" + url

            publish_date = datetime.now().date()
            time_div = item.select_one("div.time.substring")
            if time_div:
                date_text = time_div.get_text(strip=True)
                if date_text and len(date_text) >= 10:
                    try:
                        publish_date = datetime.strptime(date_text[:10], "%Y-%m-%d").date()
                    except ValueError:
                        pass
            
            jobs.append(CrawledJob(
                title=title,
                publish_date=publish_date,
                url=url,
                type="南昌人才名企",
                crawl_date=datetime.now(),
                dq="江西"
            ))
            
        except Exception as e:
            continue
    
    return jobs


# ========== 爬取规则配置 ==========
CRAWL_RULES = [
    {
        "keyword": "notice/list",             
        "wait_selector": "div.t-consultation-news", 
        "parser": parse_company_news,    
        "label": "公司招聘"               
    },
    {
        "keyword": "exam/news",
        "wait_selector": "ul.t-exam-notice-list",
        "parser": parse_exam_news,
        "label": "考试公告"
    },
    {
        "keyword": "m=home&c=notice&a=special",
        "wait_selector": "div.listContainer",
        "parser": parse_ncrczpw_gq,
        "label": "南昌人才国企"
    },
    {
        "keyword": "m=Home&c=Notice&a=index&type_id=1",
        "wait_selector": "div.newslist",
        "parser": parse_ncrczpw_qy,
        "label": "南昌人才企业"

    },
    {
        "keyword": "m=&c=news&a=index_news_list",
        "wait_selector": "div.l",
        "parser": parse_ncrczpw_mq,
        "label": "南昌人才名企"

    },

]

def get_rule_for_url(url: str):
    """根据 URL 匹配规则"""
    for rule in CRAWL_RULES:
        if rule["keyword"] in url:
            return rule
    return None

# ========== 核心逻辑 ==========

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]

_SESSION = requests.Session()
_RETRY = Retry(
    total=3,
    connect=3,
    read=3,
    status=3,
    backoff_factor=0.8,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET"]),
    raise_on_status=False,
)
_ADAPTER = HTTPAdapter(max_retries=_RETRY)
_SESSION.mount("http://", _ADAPTER)
_SESSION.mount("https://", _ADAPTER)

def fetch_html(url: str, _wait_selector: str) -> str:
    """使用 requests 爬取页面 HTML"""
    time.sleep(random.uniform(0.6, 1.6))

    headers = {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }

    resp = _SESSION.get(url, headers=headers, timeout=(10, 30))
    resp.raise_for_status()
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding
    return resp.text


def send_email(label: str, new_results: list[dict[str, object]]):
    """发送 HTML 格式的新增条目邮件"""

    if not EMAIL_CONFIG["enabled"]:
        return

    today = datetime.now().strftime("%Y-%m-%d")

    rows = ""
    for r in new_results:
        publish_date = r.get("publish_date", "")
        title = r.get("title", "")
        url = r.get("url", "")
        rows += f"""
        <tr>
            <td style="padding:8px;border:1px solid #ddd;">{publish_date}</td>
            <td style="padding:8px;border:1px solid #ddd;">
                <a href="{url}" style="color:#1a73e8;text-decoration:none;">{title}</a>
            </td>
        </tr>
        """

    html_body = f"""
    <html><body>
    <h2 style="color:#333;">📢 {label} 新增 {len(new_results)} 条 [{today}]</h2>
    <table style="border-collapse:collapse;width:100%;font-size:14px;">
        <thead>
            <tr style="background:#f2f2f2;">
                <th style="padding:8px;border:1px solid #ddd;width:120px;">日期</th>
                <th style="padding:8px;border:1px solid #ddd;">标题</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    <p style="color:#999;font-size:12px;margin-top:20px;">
        此邮件由爬虫自动发送 · {today}
    </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"【{label}】新增 {len(new_results)} 条招聘信息 [{today}]"
    msg["From"]    = EMAIL_CONFIG["from_email"]
    msg["To"]      = EMAIL_CONFIG["to_email"]
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(EMAIL_CONFIG["smtp_host"], EMAIL_CONFIG["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_CONFIG["username"], EMAIL_CONFIG["password"])
            server.sendmail(EMAIL_CONFIG["from_email"], EMAIL_CONFIG["to_email"], msg.as_string())

    except Exception as e:
        print(f"❌ 邮件发送失败：{e}")
def run_crawler():
    """执行爬虫主逻辑"""
    
    # 确保 TARGETS_FILE 是绝对路径，或者相对于脚本运行的路径
    target_path = TARGETS_FILE
    if not os.path.isabs(target_path):
        # 假设 targets.txt 在项目根目录
        target_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            target_path
        )

    try:
        with open(target_path, "r") as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return

    existing_urls = get_existing_urls()
    
    for url in urls:
        try:
            # 1. 获取规则
            rule = get_rule_for_url(url)
            if not rule:
                continue

            # 2. 爬取
            html = fetch_html(url, rule["wait_selector"])
            
            # 3. 解析
            parse_func = rule["parser"]
            jobs = parse_func(html)
            label = rule["label"]
            
            # 4. 过滤已存在的条目
            new_jobs = [j for j in jobs if j.url not in existing_urls]
            
            if new_jobs:

                # 5. 保存到数据库
                saved_jobs = save_jobs(new_jobs)
                
                # 6. 更新本地缓存
                for j in saved_jobs:
                    existing_urls.add(j["url"])
                
                # 7. 发送邮件
                send_email(label, saved_jobs)
            else:
                print(f"✅ [{label}] 无新增内容")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
        

if __name__ == "__main__":
    run_crawler()
