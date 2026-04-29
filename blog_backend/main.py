from fastapi import FastAPI
from routers import user, article, job, bill, boss, ai

app = FastAPI()


@app.on_event("startup")
async def startup():
    import logging
    logger = logging.getLogger("uvicorn")
    try:
        ai.agent_service.init()
        logger.info("AgentService 初始化成功")
    except Exception as e:
        logger.error(f"AgentService 初始化失败: {e}", exc_info=True)


app.include_router(user.router, prefix="/api", tags=["用户"])
app.include_router(article.router, prefix="/api", tags=["文章"])
app.include_router(job.router, prefix="/api", tags=["招聘"])
app.include_router(bill.router, prefix="/api", tags=["记账"])
app.include_router(boss.router, prefix="/api", tags=["求职"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI助手"])


