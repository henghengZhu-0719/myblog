import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.crawl_html import CrawlHtml

def test_crawl_html():
    url_list = [
        "https://www.liepin.com/lptjob/78555669?pgRef=c_pc_apply_page%3Ac_pc_apply_all_job_listcard%406_78555669%3A1%3Ad919ac4a-0f4d-4848-a4b0-28c499478b2c&d_sfrom=recom_apply_list",
    ]
    crawler = CrawlHtml(url_list)
    results = crawler.crawl_html()
    # 把结果保存为html
    

    print(results)  

    # assert len(results) == 1
    # result = results[0]

    # for key in ("title", "url", "details", "dq", "crawl_time"):
    #     assert key in result, f"缺少字段: {key}"
    #     assert result[key], f"字段为空: {key}"

    # assert result["url"] == url_list[0]

    # print("爬取成功:")
    # for k, v in result.items():
    #     print(f"  {k}: {v[:80] if isinstance(v, str) and len(v) > 80 else v}")

if __name__ == "__main__":
    test_crawl_html()
    print("测试通过")
