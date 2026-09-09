import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL no está configurada")
    return psycopg2.connect(DATABASE_URL)