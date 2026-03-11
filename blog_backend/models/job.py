from sqlalchemy import Column, BigInteger, String, DateTime, Text, Date
from sqlalchemy.sql import func
from database import Base

class Job(Base):
    __tablename__ = "job"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    url = Column(String(255), nullable=False, unique=True)
    publish_date = Column(Date, nullable=False)
    crawl_date = Column(DateTime, nullable=False, default=func.now())
    type = Column(String(50), nullable=True) # 招聘类型
    dq = Column(String(50), nullable=True) # 地区
