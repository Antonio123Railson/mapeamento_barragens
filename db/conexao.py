
import os
import psycopg

from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

def conectar():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode=os.getenv("DB_SSL_MODE", "require"),
        connect_timeout=15,
        row_factory=dict_row
    )
