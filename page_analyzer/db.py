import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL no está configurada")
    return psycopg2.connect(DATABASE_URL)import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Obtiene una conexión a PostgreSQL con SSL si es necesario."""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        raise ValueError(
            "DATABASE_URL no está configurada. "
            "Configúrala en el archivo .env (local) o en las variables "
            "de entorno de Render (producción)."
        )

    if 'sslmode' not in database_url and 'localhost' not in database_url:
        separator = '&' if '?' in database_url else '?'
        database_url = f"{database_url}{separator}sslmode=require"

    return psycopg2.connect(database_url)