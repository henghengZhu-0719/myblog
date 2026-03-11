from sqlalchemy import Column, BigInteger, String, DateTime, Text
from sqlalchemy.sql import func
from database import Base

class Comment(Base):
    __tablename__ = 'comment'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    article_id = Column(BigInteger, nullable=False)
    content = Column(Text, nullable=False)
    create_time = Column(DateTime, nullable=False, default=func.now())