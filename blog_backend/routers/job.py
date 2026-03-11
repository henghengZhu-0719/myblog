
from datetime import date, datetime, time, timedelta
import calendar
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from models import Job
from database import get_db
from utils.crawl import run_crawler
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/jobs")
def get_jobs_by_date(
    query_date: date, 
    range: str = Query('weekly'),
    db: Session = Depends(get_db)
):
    # 默认结束日期为查询日期
    end_date = query_date

    if range == 'weekly':
        # 近七天招聘
        start_date = query_date - timedelta(days=6)
    elif range == 'monthly':
        # 本月招聘 (月初到月末)
        start_date = query_date.replace(day=1)
        last_day = calendar.monthrange(query_date.year, query_date.month)[1]
        end_date = query_date.replace(day=last_day)
    else:
        # 默认近七天
        start_date = query_date - timedelta(days=6)

    # 查询招聘信息
    db_jobs = (
        db.query(Job)
        .filter(Job.publish_date >= start_date, Job.publish_date <= end_date)
        .order_by(Job.id.desc())
        .all()
    )
    # 判断是否有下一页

    return {
        "jobs": [
            {
            "id": job.id,
            "title": job.title,
            "url": job.url,
            "publish_date": job.publish_date,
            "crawl_date": job.crawl_date,
            "type": job.type,
            "dq": job.dq
        }
        for job in db_jobs
        ]
    }

def background_crawl():
    """后台任务执行爬虫"""
    try:
        logger.info("Starting background crawler...")
        run_crawler()
        logger.info("Background crawler finished.")
    except Exception as e:
        logger.error(f"Background crawler failed: {e}")

@router.post("/actions/crawl")
def trigger_crawl(background_tasks: BackgroundTasks):
    """触发爬虫任务"""
    background_tasks.add_task(background_crawl)
    return {"message": "爬虫任务已在后台启动"}
