# 公众号爬取工具
import requests

def search_article(url: str) -> str:
    # 实现公众号爬取逻辑
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    headers = {"User-Agent": user_agent}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return "无法获取文章内容"
    
    # 解析文章内容
    article_content = response.text
    # 保存文章内容到文件
    with open("article.html", "w", encoding="utf-8") as f:
        f.write(article_content)
    
    return article_content

article_content = search_article("https://mp.weixin.qq.com/s/A1aYj3Dh-T32NqQdlYh27Q")


