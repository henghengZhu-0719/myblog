# router/article.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from database import get_db
from models import Article, User
from schemas import ArticleCreate
from utils.auth_token import get_current_user
from agent.article_agent import check_article
import asyncio

router = APIRouter()

# 发布文章
@router.post("/articles")
async def publish_article(article_create: ArticleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 模型清洗内容（去除Emoji等）
    result = await check_article(article_create.content, article_create.title)

    db_article = Article(
        title=result.title,    # 存清洗后的
        content=result.content,
        cover=article_create.cover,
        user_id=current_user.id,
    )
    db.add(db_article)
    await db.commit()
    await db.refresh(db_article)
    return db_article

# 获取用户发布的全部文章，分页
@router.get("/users/{username}/articles")
def get_article_list(username: str, page: int = 1, size: int = 10, db: Session = Depends(get_db)):
    # 查询用户是否存在,并获取id
    db_user = db.query(User).filter(User.username == username).first()
    if not db_user:
        raise HTTPException(status_code=200, detail="用户不存在")
    # 分页查询
    offset = (page - 1) * size

    # 查询用户的全部文章
    db_articles = db.query(Article).filter(Article.user_id == db_user.id).order_by(Article.updated_at.desc()).offset(offset).limit(size).all()
    # 计算总页数
    total = db.query(Article).filter(Article.user_id == db_user.id).count()
    total_page = (total + size - 1) // size
    return {"articles": db_articles, "total": total, "total_page": total_page}

# 点击文章详情
@router.get("/articles/{article_id}")
def get_article_detail(article_id: int, db: Session = Depends(get_db)):
    # 查询文章
    db_article = db.query(Article).filter(Article.id == article_id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="文章不存在")
    db_article.updated_at = func.now()
    db.commit()
    db.refresh(db_article)
    db_author = db.query(User).filter(User.id == db_article.user_id).first()
    return {"article": db_article, "author": db_author.username}

# 删除文章
@router.delete("/articles/{article_id}")
def delete_article(article_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 查询文章
    db_article = db.query(Article).filter(Article.id == article_id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="文章不存在")
    # 检查用户是否是文章作者
    if db_article.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="没有权限删除该文章")
    # 删除文章
    db.delete(db_article)
    db.commit()
    return {"message": "文章删除成功"}

# 编辑文章
@router.put("/articles/{article_id}")
def edit_article(article_id: int, article_create: ArticleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 查询文章
    db_article = db.query(Article).filter(Article.id == article_id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="文章不存在")
    # 判断权限
    if db_article.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="没有权限编辑该文章")
    # 更新文章
    db_article.title = article_create.title
    db_article.content = article_create.content
    db_article.cover = article_create.cover
    db.commit()
    return {"message": "文章编辑成功"}