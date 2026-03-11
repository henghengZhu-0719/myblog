from sqlalchemy import Column, BigInteger, String, DateTime
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = 'user'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    avatar = Column(String(255), nullable=True)
    create_time = Column(DateTime, nullable=False, default=func.now())
    
