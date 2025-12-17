import asyncio
from datetime import datetime
from decimal import Decimal
from src.database import get_db_connection

async def test_database():
    """Test database connection by inserting and reading a price record"""
    conn = await get_db_connection()

    try:
        # Create a test price
        market = "TEST"
        price = Decimal("99.99")
        timestamp = datetime.now()

        # Insert the price
        await conn.execute("""
            INSERT INTO prices (market, timestamp, price)
            VALUES ($1, $2, $3)
        """, market, timestamp, price)
        print(f"Inserted price: market={market}, price={price}, timestamp={timestamp}")

        # Read it back
        row = await conn.fetchrow("SELECT * FROM prices WHERE market = $1 ORDER BY timestamp DESC LIMIT 1", market)
        print(f"Read from DB: {dict(row)}")

        print("\nPhase 1 checkpoint passed!")
        print("Run this to verify: SELECT * FROM prices;")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_database())
