from pydantic import BaseModel
from config import default_avatar_url


class ArticleCreate(BaseModel):
    title: str
    content: str
    cover: str = default_avatar_url

