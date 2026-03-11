import os

sqlalchemy_database_url = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://"
    f"{os.getenv('DB_USER', 'root')}:"
    f"{os.getenv('DB_PASSWORD', '020110')}@"
    f"{os.getenv('DB_HOST', 'localhost')}:"
    f"{os.getenv('DB_PORT', '3306')}/"
    f"{os.getenv('DB_NAME', 'myapp')}"
)

default_avatar_url = "https://www.baidu.com/img/PCtm_d9c8750bed0b3c7d089fa7d55720d6cf.png"

# 密钥
secret_key = "zyq020110"
algorithm = "HS256"

# 爬虫配置
BASE_URL = "https://www.ncrczpw.com"
TARGETS_FILE = "targets.txt"

EMAIL_CONFIG = {
    "enabled": False,
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "username": "your_email@example.com",
    "password": "your_password",
    "from_email": "your_email@example.com",
    "to_email": "recipient@example.com"
}
