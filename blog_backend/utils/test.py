from crawl_html import CrawlHtml

url = "https://www.liepin.com/job/1972255887.shtml?pgRef=c_pc_home_page%3Ac_pc_home_stu_yj_hp_job_listcard%402_72255887%3A1%3Af03e43e2-dce6-4ed2-94e0-d42242f046dc&d_sfrom=pc_stu_yj_mix&head_id=hReChgea3TOAvShqgKBDY1gDlHPamP1n&as_from=pc_stu_yj_mix&job_id=72255887&job_kind=2&d_ckId=hReChgea3TOAvShqgKBDY1gDlHPamP1n&d_headId=hReChgea3TOAvShqgKBDY1gDlHPamP1n&d_posi=0"

crawler = CrawlHtml([url])
details = crawler.crawl_html()

print("职位详情:", details)
