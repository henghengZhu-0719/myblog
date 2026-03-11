from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


class BossCreate(BaseModel):
    """创建职位的请求模型"""
    title: str = Field(..., description="职位标题", min_length=1, max_length=200)
    url: str = Field(..., description="职位链接")
    details: str = Field(..., description="职位详情")
    dq: Optional[str] = Field(None, description="地区")
    crawl_date: Optional[datetime] = Field(None, description="爬取时间，默认当前时间")
    