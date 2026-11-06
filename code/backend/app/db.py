import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root@127.0.0.1:3308/lego_studio?charset=utf8mb4")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
