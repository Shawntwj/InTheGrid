import asyncio
import asyncpg
import redis.asyncio as redis
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from src.database import get_db_connection
from src.mock_data import generate_prices, MARKETS

load_dotenv()

async def get_redis_connection():
    """Create and return a Redis connection"""
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))

    return await redis.Redis(host=host, port=port, decode_responses=True)

async def write_prices_to_db(conn: asyncpg.Connection, timestamp: datetime, prices: dict):
    """Write price data to PostgreSQL"""
    for market, price in prices.items():
        await conn.execute(
            """
            INSERT INTO prices (market, timestamp, price)
            VALUES ($1, $2, $3)
            """,
            market, timestamp, price
        )

async def publish_to_redis(redis_conn: redis.Redis, timestamp: datetime, prices: dict):
    """Publish price data to Redis Stream"""
    data = {
        "timestamp": timestamp.isoformat(),
        **{market: str(price) for market, price in prices.items()}
    }

    await redis_conn.xadd("prices", data)

async def ingestion_loop():
    """Main ingestion loop: generate prices every 10 seconds and write to DB + Redis"""
    db_conn = await get_db_connection()
    redis_conn = await get_redis_connection()

    print("Starting ingestion service...")
    print(f"Writing to PostgreSQL and Redis Stream every 10 seconds")

    iteration = 0

    try:
        while True:
            timestamp = datetime.now()
            data = generate_prices(hours=1)
            prices = data[0]["prices"]

            await write_prices_to_db(db_conn, timestamp, prices)
            await publish_to_redis(redis_conn, timestamp, prices)

            iteration += 1
            print(f"[{iteration}] {timestamp.strftime('%Y-%m-%d %H:%M:%S')} - DE: €{prices['DE']:.2f}/MWh")

            await asyncio.sleep(10)

    except KeyboardInterrupt:
        print("\nStopping ingestion service...")
    finally:
        await db_conn.close()
        await redis_conn.aclose()

if __name__ == "__main__":
    asyncio.run(ingestion_loop())
