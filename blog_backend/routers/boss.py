# router/article.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Union
import calendar  # ✅ 添加 calendar 导入
from database import get_db
from models import Boss
from datetime import date, datetime, timedelta  # ✅ 合并导入，移除重复
from schemas import BossCreate
from utils.crawl_html import CrawlHtml

router = APIRouter()


@router.post("/boss/crawl", status_code=status.HTTP_200_OK)
def crawl_boss_info(urls: list[str]):
    try:
        crawler = CrawlHtml(urls)
        results = crawler.crawl_html()
        return {
            "success": True,
            "message": f"成功抓取 {len(results)} 条职位信息",
            "data": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"抓取职位信息失败: {str(e)}"
        )


@router.post("/boss", status_code=status.HTTP_201_CREATED)
def create_boss(
    boss_data: Union[BossCreate, list[BossCreate]],
    db: Session = Depends(get_db)
):
    try:
        boss_list = boss_data if isinstance(boss_data, list) else [boss_data]

        new_bosses = []
        for boss in boss_list:
            new_boss = Boss(
                title      = boss.title,
                url        = boss.url,
                details    = boss.details,
                dq         = boss.dq,
                crawl_date = boss.crawl_date or datetime.now()  # 优先用传入值
            )
            new_bosses.append(new_boss)

        db.add_all(new_bosses)
        db.commit()

        # ✅ refresh 确保拿到数据库生成的 id、时间等字段
        for boss in new_bosses:
            db.refresh(boss)

        if isinstance(boss_data, list):
            return {
                "success": True,
                "message": f"成功创建 {len(new_bosses)} 条投递记录",
                "count"  : len(new_bosses),
                "data"   : new_bosses
            }
        else:
            return {
                "success": True,
                "message": "投递记录保存成功",
                "data"   : new_bosses[0]
            }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="存在重复的职位链接（url），请检查后重试"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建投递记录失败: {str(e)}"
        )

@router.get("/boss")
def get_boss(
    query_date:date, 
    range: str = Query('weekly'),
    db: Session=Depends(get_db)
):
    # 默认结束日期为查询日期的0点
    end_date = query_date + timedelta(days=1)

    if range == 'weekly':
        # 近七天投递
        start_date = query_date - timedelta(days=6)
    elif range == 'monthly':
        # 本月投递 (月初到月末)
        start_date = query_date.replace(day=1)
        last_day = calendar.monthrange(query_date.year, query_date.month)[1]
        end_date = query_date.replace(day=last_day)
    else:
        # 默认近七天
        start_date = query_date - timedelta(days=6)
    
    # 查询投递记录
    db_bosses = (
        db.query(Boss)
        .filter(Boss.crawl_date >= start_date, Boss.crawl_date <= end_date)
        .order_by(Boss.id.desc())
        .all()
    )

    return {
        "bosses": [
            {
            "id": boss.id,
            "title": boss.title,
            "url": boss.url,
            "details": boss.details,
            "dq": boss.dq,
            "crawl_date": boss.crawl_date,
        }
        for boss in db_bosses
        ]
    }






