"""Add avatar column to admins table."""
import pymysql
from app.config import settings

conn = pymysql.connect(
    host=settings.MYSQL_HOST,
    port=settings.MYSQL_PORT,
    user=settings.MYSQL_USER,
    password=settings.MYSQL_PASSWORD,
    database=settings.MYSQL_DB,
    charset='utf8mb4'
)
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE admins ADD COLUMN avatar VARCHAR(255) DEFAULT '' AFTER password_hash")
    conn.commit()
    print('avatar column added successfully')
except Exception as e:
    print(f'Error: {e}')
finally:
    cursor.close()
    conn.close()
