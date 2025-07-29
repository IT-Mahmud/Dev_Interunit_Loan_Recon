from sqlalchemy import create_engine, text
from config import MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB

engine = create_engine(f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}')

with engine.connect() as conn:
    conn.execute(text('DELETE FROM tally_data'))
    conn.commit()
    print('Database cleared.') 