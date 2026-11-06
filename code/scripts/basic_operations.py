"""课程六类数据库操作演示，仅使用固定名称的演示表。"""
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.db import engine

with engine.begin() as conn:
    conn.execute(text('CREATE TABLE course_demo (id INT PRIMARY KEY, name VARCHAR(50))'))
    conn.execute(text("INSERT INTO course_demo VALUES (1, 'brick')"))
    conn.execute(text("UPDATE course_demo SET name='LEGO' WHERE id=1"))
    print('跨表查询:', conn.execute(text('SELECT s.set_num,s.name,t.name FROM sets s JOIN themes t ON s.theme_id=t.id LIMIT 3')).all())
    conn.execute(text('DELETE FROM course_demo WHERE id=1'))
    conn.execute(text('DROP TABLE course_demo'))
    print('已完成建表、插入、修改、删除记录、删表及跨表查询')
