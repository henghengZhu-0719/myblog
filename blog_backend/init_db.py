import pymysql
from database import engine, Base
from models import User, Article, Comment, Tag, Job, Bill, Boss

DB_HOST = "db"       # ⚠️ 改成你的数据库地址
DB_USER = "root"
DB_PASSWORD = "020110"
DB_NAME = "myapp"

def create_database():
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    conn.cursor().execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    conn.close()
    print("✅ Database ensured")

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created")

def init_db():
    create_database()
    create_tables()

if __name__ == "__main__":
    init_db()