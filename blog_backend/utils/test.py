from email import message
import os
import json
import re
import base64
import anthropic
from langchain.chat_models import init_chat_model

# Initialize OpenAI client for Alibaba Cloud Bailian
# Note: In a production environment, it is recommended to use environment variables
API_KEY = "sk-cp-tP-n3FkUJPYRQqZb_w5nMIZYjQHwwsiEjQg-zldzQOfNQfYZKT8qnkxxu2EdBG2ORDs2yMcd-XNjxKRWxxbW0CwsVEnCzf5aHUfx4qIMYwEgCCJAzn1NmlQ"

# 使用minimax模型

BASE_URL = "https://api.minimaxi.com/anthropic"

from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(
    model="MiniMax-M2.7",
    api_key=API_KEY,
    base_url=BASE_URL,
)