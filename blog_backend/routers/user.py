# routers/user.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from models import User
from database import get_db
import passlib.hash as pwd
from models.article import Article
from schemas import UserRegister, UserLogin, user
from fastapi import HTTPException
from utils.auth_token import create_token

router = APIRouter()

# 用户注册
@router.post("/users")
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    # 检查用户名是否存在
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 创建新用户
    new_user = User(
        username=user.username,
        password=user.password,
        avatar=user.avatar
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# 用户登陆
@router.post("/auth/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    # 检查用户名是否存在
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="用户名不存在")
    
    # 检查密码是否正确
    if not user.password == db_user.password:
        raise HTTPException(status_code=400, detail="密码错误")
        
    # 生成 token
    token = create_token(db_user.username)
    
    return {"access_token": token, "token_type": "bearer"}


# 根据用户名称分页模糊查询用户
@router.get("/users")
def get_user_by_username(
    searchname: str,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # 是否为空
    if not searchname.strip():
        raise HTTPException(status_code=400, detail="searchname不能为空")

    offset = (page - 1) * size
    # 查询全部用户
    rows = (
        db.query(User)
        .filter(User.username.contains(searchname))
        .order_by(User.id.desc())
        .offset(offset)
        .limit(size + 1)
        .all()
    )
    # 判断是否有下一页
    has_more = len(rows) > size
    db_users = rows[:size]
    
    return {
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "create_time": user.create_time
            }
            for user in db_users
        ],
        "page": page,
        "size": size,
        "has_more": has_more
    }

# 根据用户ID查询用户
@router.get("/users/{user_id}")
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    # 查询该用户是否存在
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"username": db_user.username, "avatar": db_user.avatar, "id": db_user.id, "create_time": db_user.create_time}

# 获取当前用户的user_id
@router.get("/users/by-username/{username}")
def get_current_user_id(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")   
    return {"user_id": user.id}

