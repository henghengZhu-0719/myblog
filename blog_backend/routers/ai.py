from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
import json

router = APIRouter()

# 定义请求模型
class ChatRequest(BaseModel):
    message: str

# 初始化模型
API_KEY = "sk-cp-tP-n3FkUJPYRQqZb_w5nMIZYjQHwwsiEjQg-zldzQOfNQfYZKT8qnkxxu2EdBG2ORDs2yMcd-XNjxKRWxxbW0CwsVEnCzf5aHUfx4qIMYwEgCCJAzn1NmlQ"
BASE_URL = "https://api.minimaxi.com/anthropic"

try:
    chat_model = ChatAnthropic(
        model="MiniMax-M2.7",
        api_key=API_KEY,
        base_url=BASE_URL,
    )
except Exception as e:
    print(f"Failed to initialize ChatAnthropic: {e}")
    chat_model = None

@router.post("/chat")
async def ai_chat(request: ChatRequest):
    if not chat_model:
        raise HTTPException(status_code=500, detail="AI 模型未正确初始化")
    
    async def generate_response():
        try:
            # 使用 astream 支持异步流式输出
            async for chunk in chat_model.astream(
                input=[{"role": "user", "content": request.message}],
                temperature=0.1,
            ):
                # 提取文本块
                chunk_text = ""
                if isinstance(chunk.content, list):
                    for block in chunk.content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            chunk_text += block.get("text", "")
                        elif hasattr(block, "type") and block.type == "text":
                            chunk_text += getattr(block, "text", "")
                else:
                    chunk_text = str(chunk.content)
                
                if chunk_text:
                    # 返回 SSE 格式的数据
                    yield f"data: {json.dumps({'text': chunk_text})}\n\n"
            
            # 结束标志
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate_response(), media_type="text/event-stream")
