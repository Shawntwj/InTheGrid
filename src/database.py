import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def get_db_connection():
    """Create and return a database connection"""
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    database = os.getenv("DB_NAME", "inthegrid")

    print(f"Connecting to: host={host}, port={port}, user={user}, database={database}")

    return await asyncpg.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )
