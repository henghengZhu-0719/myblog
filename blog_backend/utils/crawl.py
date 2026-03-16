from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
import sys

# 添加项目根目录到 sys.path，以便能够导入项目中的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EMAIL_CONFIG, BASE_URL, TARGETS_FILE
from database import SessionLocal
from models.job import Job

# ========== 数据库操作函数 ==========

def get_existing_urls():
    """获取数据库中已存在的 URL 集合"""
    db = SessionLocal()
    try:
        urls = db.query(Job.url).all()
        return {url[0] for url in urls}
    finally:
        db.close()

def save_jobs(jobs: list[Job]):
    """批量保存 Job 对象到数据库"""
    if not jobs:
        return []
    
    db = SessionLocal()
    try:
        # 逐个添加，避免重复键错误导致整个批次失败（虽然我们在外面已经做了去重）
        saved_jobs = []
        for job in jobs:
            try:
                db.add(job)
                db.commit()
                saved_jobs.append({
                    "title": job.title,
                    "url": job.url,
                    "publish_date": job.publish_date,
                    "type": job.type,
                    "dq": job.dq,
                })
            except Exception as e:
                db.rollback()
        return saved_jobs
    finally:
        db.close()

# ========== 解析函数定义 ==========

def parse_company_news(html: str) -> list[Job]:
    """解析公司招聘页面"""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.t-consultation-news a.t-consultation-item")
    jobs = []
    
    for item in items:
        title = item.find('span', class_='t-consultation-news-title').get_text(strip=True)
        date_str = item.find('span', class_='t-news-time').get_text(strip=True)
        url = item['href']
        
        # 处理日期格式，确保是 Date 类型
        try:
            publish_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            publish_date = datetime.now().date()

        jobs.append(Job(
            title=title,
            publish_date=publish_date,
            url=url,
            type="公司招聘",
            crawl_date=datetime.now(),
            dq="江西"
        ))
    return jobs

def parse_exam_news(html: str) -> list[Job]:
    """解析考试公告页面"""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("ul.t-exam-notice-list li.t-exam-notice-big-item")
    jobs = []

    for item in items:
        title = item.find('span').get_text(strip=True)
        date_str = item.find('em').get_text(strip=True)
        url = BASE_URL + item.find('a')['href']
        
        try:
            publish_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            publish_date = datetime.now().date()
        
        jobs.append(Job(
            title=title,
            publish_date=publish_date,
            url=url,
            type="考试公告",
            crawl_date=datetime.now(),
            dq="江西"
        ))
    return jobs

def parse_ncrczpw_gq(html: str) -> list[Job]:
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

        jobs.append(Job(
            title=title,
            publish_date=publish_date,
            url=url,
            type="南昌人才国企",
            crawl_date=datetime.now(),
            dq="江西"
        ))
    return jobs


def parse_ncrczpw_qy(html: str) -> list[Job]:
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
            
            jobs.append(Job(
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


def parse_ncrczpw_mq(html: str) -> list[Job]:
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
            
            jobs.append(Job(
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

def fetch_html(url: str, wait_selector: str) -> str:
    """使用 Playwright 爬取页面 HTML"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, timeout=30000)

            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=10000)
                except Exception as e:
                    print(f"⚠️ 等待元素 {wait_selector} 超时，直接获取页面内容")

            html = page.content()
            return html
        finally:
            browser.close()


def send_email(label: str, new_results: list[Job]):
    """发送 HTML 格式的新增条目邮件"""

    if not EMAIL_CONFIG["enabled"]:
        return

    today = datetime.now().strftime("%Y-%m-%d")

    rows = ""
    for r in new_results:
        rows += f"""
        <tr>
            <td style="padding:8px;border:1px solid #ddd;">{r.publish_date}</td>
            <td style="padding:8px;border:1px solid #ddd;">
                <a href="{r.url}" style="color:#1a73e8;text-decoration:none;">{r.title}</a>
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
def run_crawler() -> list[dict]:
    """执行爬虫主逻辑，返回每个URL的执行结果列表"""
    results = []

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
        return [{"url": target_path, "label": "配置文件", "status": "error", "message": "targets.txt 文件不存在", "new_count": 0}]

    existing_urls = get_existing_urls()
    
    for url in urls:
        entry = {"url": url, "label": "", "status": "", "message": "", "new_count": 0}
        try:
            # 1. 获取规则
            rule = get_rule_for_url(url)
            if not rule:
                entry["status"] = "skip"
                entry["message"] = "没有匹配的解析规则"
                results.append(entry)
                continue

            entry["label"] = rule["label"]

            # 2. 爬取
            html = fetch_html(url, rule["wait_selector"])
            
            # 3. 解析
            parse_func = rule["parser"]
            jobs = parse_func(html)
            
            # 4. 过滤已存在的条目
            new_jobs = [j for j in jobs if j.url not in existing_urls]
            
            if new_jobs:
                # 5. 保存到数据库
                saved_jobs = save_jobs(new_jobs)
                
                # 6. 更新本地缓存
                for j in saved_jobs:
                    existing_urls.add(j["url"])
                
                # 7. 发送邮件
                send_email(rule["label"], saved_jobs)

                entry["status"] = "success"
                entry["new_count"] = len(saved_jobs)
                entry["message"] = f"新增 {len(saved_jobs)} 条，共解析 {len(jobs)} 条"
            else:
                entry["status"] = "success"
                entry["new_count"] = 0
                entry["message"] = f"无新增内容，共解析 {len(jobs)} 条"
                print(f"✅ [{rule['label']}] 无新增内容")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            entry["status"] = "error"
            entry["message"] = str(e)

        results.append(entry)

    return results


if __name__ == "__main__":
    run_crawler()
