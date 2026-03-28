import os
import json
import re
import base64
from openai import OpenAI
import anthropic
from langchain.chat_models import init_chat_model
from langchain_anthropic import ChatAnthropic


API_KEY = "sk-cp-tP-n3FkUJPYRQqZb_w5nMIZYjQHwwsiEjQg-zldzQOfNQfYZKT8qnkxxu2EdBG2ORDs2yMcd-XNjxKRWxxbW0CwsVEnCzf5aHUfx4qIMYwEgCCJAzn1NmlQ"

# 使用minimax模型
BASE_URL = "https://api.minimaxi.com/anthropic"
model = ChatAnthropic(
    model="MiniMax-M2.7",
    api_key=API_KEY,
    base_url=BASE_URL,
)

def analyze_receipt(image_bytes):
    """
    发送信息给 LLM 进行分析并识别为结构化数据，用于创建账单
    """
    
    # Encode image to base64
    if isinstance(image_bytes, bytes):
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
    else:
        # Assuming it's already base64 string
        base64_image = image_bytes

    # Prompt engineering for structured output
    prompt = """
    你是一个专业的票据识别助手。请分析这张图片，准确提取信息以生成账单记录。
    如果图片中包含多笔消费，请返回 JSON 数组。
    如果只有一笔消费，请返回单个 JSON 对象。
    今年是2026年。如果是教育-上海对外经贸大学，那么这个是学校食堂的消费！！！

    请提取以下字段并以纯 JSON 格式返回（字段名必须严格匹配）：
    - title: (必填) 商品名称或交易标题，例如"星巴克咖啡"、"超市购物"、"打车费"
    - merchant: (选填) 商户名称，如果无法识别可为 null
    - category: (必填) 消费分类，必须从以下标准中选择最合适的一个：
        - 餐饮：餐厅吃饭、外卖、购买食材、饮料零食、学校食堂（上海对外经贸大学）
        - 交通：打车、地铁、公交、加油、停车费、机票火车票
        - 购物：衣服鞋帽、电子产品、化妆品、普通日用品
        - 居家：家用电器、家具、水电宽带费、物业费
        - 娱乐：电影、游戏、KTV、旅游景点门票
        - 医疗：药品、医院挂号、检查费
        - 其他：无法归类的支出
    - amount: (必填) 总金额，纯数字，保留两位小数
    - trade_time: (必填) 交易时间，格式: YYYY-MM-DD。如果图片中没有年份，请默认为当年。
    - remark: (选填) 备注信息，例如具体的商品清单或特殊说明

    请只返回 JSON 对象，不要包含 markdown 代码块或其他文字。如果某个选填字段无法识别，请使用 null。
    """

    try:
        response = model.invoke(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                }
            ],
            temperature=0.1,  # Lower temperature for more deterministic output
        )
        
        content = response.choices[0].message.content
        return parse_json_response(content)

    except Exception as e:
        return {"error": str(e)}

def parse_json_response(text):
    """
    从 LLM 的响应中提取 JSON 数据，处理可能的 markdown 包裹。
    """
    try:
        # Remove markdown code blocks if present
        text = text.strip()
        if text.startswith("```"):
            # Find the first newline
            first_newline = text.find("\n")
            if first_newline != -1:
                # Remove first line (```json) and last line (```)
                text = text[first_newline+1:]
                if text.endswith("```"):
                    text = text[:-3]
        
        # Try to find JSON block if still wrapped or embedded
        # Match either object {...} or array [...]
        json_match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        else:
            return json.loads(text)
    except json.JSONDecodeError:
        return {
            "error": "Failed to parse JSON",
            "raw_output": text
        }
