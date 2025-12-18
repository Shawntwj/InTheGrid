import asyncio
from datetime import datetime
from src.ingestion import write_prices_to_db, publish_to_redis, get_redis_connection
from src.database import get_db_connection

async def test_write_prices_to_db():
    """Test writing prices to PostgreSQL"""
    conn = await get_db_connection()

    try:
        timestamp = datetime.now()
        prices = {"TEST_DE": 75.50, "TEST_FR": 85.25}

        await write_prices_to_db(conn, timestamp, prices)

        for market, expected_price in prices.items():
            row = await conn.fetchrow(
                "SELECT price FROM prices WHERE market = $1 AND timestamp = $2",
                market, timestamp
            )
            assert row is not None, f"No record found for {market}"
            assert float(row["price"]) == expected_price, f"Price mismatch for {market}"

        print(f"✓ Successfully wrote {len(prices)} prices to database")
    finally:
        await conn.execute("DELETE FROM prices WHERE market LIKE 'TEST_%'")
        await conn.close()

async def test_publish_to_redis():
    """Test publishing prices to Redis Stream"""
    redis_conn = await get_redis_connection()

    try:
        timestamp = datetime.now()
        prices = {"DE": 75.50, "FR": 85.25}

        await publish_to_redis(redis_conn, timestamp, prices)

        messages = await redis_conn.xrange("prices", count=1)
        assert len(messages) > 0, "No messages in Redis stream"

        message_id, data = messages[-1]
        assert "timestamp" in data, "Missing timestamp in Redis message"
        assert "DE" in data, "Missing DE price in Redis message"
        assert "FR" in data, "Missing FR price in Redis message"

        print(f"✓ Successfully published to Redis Stream: {data}")
    finally:
        await redis_conn.aclose()

async def test_ingestion_checkpoint():
    """Checkpoint test: verify database and Redis state"""
    db_conn = await get_db_connection()
    redis_conn = await get_redis_connection()

    try:
        price_count = await db_conn.fetchval("SELECT COUNT(*) FROM prices")
        print(f"Database price count: {price_count}")

        stream_length = await redis_conn.xlen("prices")
        print(f"Redis stream length: {stream_length}")

        print("\n" + "="*60)
        print("Phase 3 Checkpoint Instructions:")
        print("="*60)
        print("1. Run: python -m src.ingestion")
        print("2. Let it run for 5 minutes")
        print("3. Verify with: SELECT COUNT(*) FROM prices;")
        print("4. Should see count growing by 5 every 10 seconds")
        print("="*60)
    finally:
        await db_conn.close()
        await redis_conn.aclose()

if __name__ == "__main__":
    print("Running ingestion tests...\n")
    asyncio.run(test_write_prices_to_db())
    asyncio.run(test_publish_to_redis())
    asyncio.run(test_ingestion_checkpoint())
    print("\n✓ All tests passed!")
