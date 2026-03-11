from sqlalchemy import Column, BigInteger, String, DateTime, Text, Date
from sqlalchemy.sql import func
from database import Base

class Boss(Base):
    __tablename__ = "boss"

    id = Column(BigInteger, primary_key=True, autoincrement=True) # 数据ID
    title = Column(Text, nullable=False) # 职位标题
    url = Column(Text, nullable=False)
    crawl_date = Column(DateTime, nullable=False, server_default=func.now()) # 投递时间，默认为当天
    details = Column(Text, nullable=False) # 职位详情
    dq = Column(String(50), nullable=True) # 地区

