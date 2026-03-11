from pydantic import BaseModel
from config import default_avatar_url



class UserRegister(BaseModel):
    username: str
    password: str
    avatar: str = default_avatar_url

class UserLogin(BaseModel):
    username: str
    password: str