from fastapi import FastAPI
from routers import user, article, job, bill, boss

app = FastAPI()

app.include_router(user.router, prefix="/api", tags=["用户"])
app.include_router(article.router, prefix="/api", tags=["文章"])
app.include_router(job.router, prefix="/api", tags=["招聘"])
app.include_router(bill.router, prefix="/api", tags=["记账"])
app.include_router(boss.router, prefix="/api", tags=["求职"])


