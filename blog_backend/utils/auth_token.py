from jose import jwt, JWTError
from config import secret_key, algorithm
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User



def create_token(username: str) -> str:
    # 用 jwt.encode 生成 token
    # payload 里放 {"sub": username}
    payload = {"sub": username, "exp": datetime.now() + timedelta(hours=24)}
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    return token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/user/login/")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> str:
    # 用 jwt.decode 解析 token
    # 从 payload 里取 "sub" 字段
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="token 无效")
    except JWTError:    
        raise HTTPException(status_code=401, detail="token 无效")
    
    db_user = db.query(User).filter(User.username == username).first()
    if db_user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    return db_user
