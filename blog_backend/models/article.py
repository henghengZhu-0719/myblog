# models/article.py
from sqlalchemy import Column, BigInteger, String, Text, Integer, DateTime, Table, ForeignKey
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

# 关联表（中间表，不需要单独的类）
article_tag = Table(
    "article_tag",          # 表名
    Base.metadata,
    Column("article_id", BigInteger, ForeignKey("article.id"), primary_key=True),
    Column("tag_id",     BigInteger, ForeignKey("tag.id"),     primary_key=True),
)

# 文章表
class Article(Base):
    __tablename__ = "article"

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id    = Column(BigInteger, ForeignKey("user.id"), nullable=False)
    title      = Column(String(200), nullable=False)
    content    = Column(LONGTEXT, nullable=False)
    cover      = Column(String(200))
    status     = Column(Integer, default=1)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关键：声明和Tag的关系
    tags = relationship("Tag", secondary=article_tag, back_populates="articles")

# 标签表
class Tag(Base):
    __tablename__ = "tag"

    id   = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)

    # 关键：声明和Article的关系
    articles = relationship("Article", secondary=article_tag, back_populates="tags")
