from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio
from agent.agent import Agent

router = APIRouter()

# 定义请求模型
class ChatRequest(BaseModel):
    message: str
    user_id: int | str | None = None

# 初始化 Agent
try:
    ai_agent = Agent()
except Exception as e:
    print(f"Failed to initialize Agent: {e}")
    ai_agent = None

@router.post("/chat")
async def ai_chat(request: ChatRequest):
    if not ai_agent:
        raise HTTPException(status_code=500, detail="AI 模型未正确初始化")
    
    async def generate_response():
        try:
            # 调用 Agent 里的生成器方法
            async for chunk_text, _ in ai_agent.astream_chat(request.message, request.user_id):
                # 返回 SSE 格式的数据
                yield f"data: {json.dumps({'text': chunk_text})}\n\n"
            # 结束标志
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate_response(), media_type="text/event-stream")
