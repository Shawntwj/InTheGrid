import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient
from datetime import datetime
from decimal import Decimal
from src.database import get_db_connection

# Base URL for the API running in Docker
BASE_URL = "http://localhost:8000"

@pytest_asyncio.fixture
async def setup_test_data():
    """Setup test data in the database"""
    conn = await get_db_connection()

    try:
        # Insert test prices
        test_markets = ["DE", "FR", "NL"]
        timestamp = datetime.now()

        for market in test_markets:
            await conn.execute(
                "INSERT INTO prices (market, timestamp, price) VALUES ($1, $2, $3)",
                market, timestamp, Decimal("50.00") + Decimal(str(ord(market[0])))
            )

        # Insert a test spread opportunity
        await conn.execute(
            """
            INSERT INTO spreads (
                market_pair, timestamp, spread, net_opportunity,
                low_market, high_market, low_price, high_price
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            "DE-FR", timestamp, Decimal("10.00"), Decimal("7.50"),
            "DE", "FR", Decimal("60.00"), Decimal("70.00")
        )

        yield

        # Cleanup
        await conn.execute("DELETE FROM prices WHERE market IN ('DE', 'FR', 'NL')")
        await conn.execute("DELETE FROM spreads WHERE market_pair = 'DE-FR'")

    finally:
        await conn.close()

@pytest.mark.asyncio
async def test_health_endpoint():
    """Test the health check endpoint"""
    async with AsyncClient(base_url=BASE_URL) as client:
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "InTheGrid API"

        print("Health endpoint working")

@pytest.mark.asyncio
async def test_latest_prices_endpoint(setup_test_data):
    """Test the latest prices endpoint"""
    async with AsyncClient(base_url=BASE_URL) as client:
        response = await client.get("/api/prices/latest")

        assert response.status_code == 200
        data = response.json()

        assert "markets" in data
        assert "count" in data
        assert "retrieved_at" in data
        assert data["count"] > 0

        # Check market structure
        if data["markets"]:
            market = data["markets"][0]
            assert "market" in market
            assert "price" in market
            assert "timestamp" in market
            assert isinstance(market["price"], (int, float))

        print(f"Latest prices endpoint working - found {data['count']} markets")

@pytest.mark.asyncio
async def test_spread_opportunities_endpoint(setup_test_data):
    """Test the spread opportunities endpoint"""
    async with AsyncClient(base_url=BASE_URL) as client:
        response = await client.get("/api/spreads/opportunities")

        assert response.status_code == 200
        data = response.json()

        assert "opportunities" in data
        assert "count" in data
        assert "retrieved_at" in data

        # Check opportunity structure if any exist
        if data["opportunities"]:
            opp = data["opportunities"][0]
            assert "market_pair" in opp
            assert "spread" in opp
            assert "net_opportunity" in opp
            assert "low_market" in opp
            assert "high_market" in opp
            assert "low_price" in opp
            assert "high_price" in opp
            assert "strategy" in opp
            assert isinstance(opp["spread"], (int, float))
            assert isinstance(opp["net_opportunity"], (int, float))

        print(f"Spread opportunities endpoint working - found {data['count']} opportunities")

@pytest.mark.asyncio
async def test_price_history_endpoint(setup_test_data):
    """Test the price history endpoint"""
    async with AsyncClient(base_url=BASE_URL) as client:
        response = await client.get("/api/prices/history/DE")

        assert response.status_code == 200
        data = response.json()

        assert "market" in data
        assert data["market"] == "DE"
        assert "history" in data
        assert "stats" in data
        assert "retrieved_at" in data

        # Check history structure
        if data["history"]:
            entry = data["history"][0]
            assert "market" in entry
            assert "price" in entry
            assert "timestamp" in entry
            assert isinstance(entry["price"], (int, float))

        # Check stats structure
        if data["stats"]:
            stats = data["stats"]
            assert "latest" in stats
            assert "average" in stats
            assert "min" in stats
            assert "max" in stats
            assert "samples" in stats

        print(f"Price history endpoint working - {len(data['history'])} records")

@pytest.mark.asyncio
async def test_price_history_not_found():
    """Test price history endpoint with non-existent market"""
    async with AsyncClient(base_url=BASE_URL) as client:
        response = await client.get("/api/prices/history/NONEXISTENT")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

        print("Price history 404 handling working")

@pytest.mark.asyncio
async def test_price_history_invalid_limit():
    """Test price history endpoint with invalid limit"""
    async with AsyncClient(base_url=BASE_URL) as client:
        response = await client.get("/api/prices/history/DE?limit=5000")

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

        print("Price history limit validation working")

async def run_all_tests():
    """Run all API tests"""
    print("\nRunning API endpoint tests...\n")

    # Test health endpoint (no setup needed)
    await test_health_endpoint()

    # Setup test data for other tests
    async for _ in setup_test_data():
        await test_latest_prices_endpoint(_)
        await test_spread_opportunities_endpoint(_)
        await test_price_history_endpoint(_)
        break

    # Test error cases
    await test_price_history_not_found()
    await test_price_history_invalid_limit()

    print("\n" + "="*60)
    print("Phase 5 API Checkpoint:")
    print("="*60)
    print("GET /health - Health check working")
    print("GET /api/prices/latest - Latest prices working")
    print("GET /api/spreads/opportunities - Opportunities working")
    print("GET /api/prices/history/{market} - Price history working")
    print("Error handling working (404, 400)")
    print("="*60)
    print("\nAll API endpoints returning valid JSON! ✅")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
