from sqlalchemy import Column, BigInteger, String, Text, Integer, DateTime, Table, ForeignKey, Date, Numeric
from datetime import datetime

from sqlalchemy.sql import func
from database import Base

class Bill(Base):
    __tablename__ = "bill"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False, comment="商品名称/交易标题")
    merchant = Column(Text, nullable=True, comment="商户名称")
    category = Column(String(255), nullable=False, comment="分类")
    amount = Column(Numeric(10, 2), nullable=False, comment="金额")
    trade_time = Column(Date, nullable=False, comment="交易时间")
    remark = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")

    
    
    
    
    
