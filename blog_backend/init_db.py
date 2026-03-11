# init_db.py
from database import SessionLocal, engine, Base
from models import User, Article, Comment, Tag, Job, Bill, Boss

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
