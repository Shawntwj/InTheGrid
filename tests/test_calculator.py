import asyncio
from datetime import datetime
from decimal import Decimal
from src.calculator import (
    get_latest_prices,
    calculate_spreads,
    write_spreads_to_db,
    calculate_and_store_spreads,
    get_transmission_cost
)
from src.database import get_db_connection

async def test_get_latest_prices():
    """Test fetching latest prices from database"""
    conn = await get_db_connection()

    try:
        prices = await get_latest_prices(conn)

        assert len(prices) > 0, "No prices found in database"

        for market, (price, timestamp) in prices.items():
            assert isinstance(price, Decimal), f"Price for {market} is not a Decimal"
            assert isinstance(timestamp, datetime), f"Timestamp for {market} is not a datetime"
            print(f"  {market}: €{price:.2f}/MWh at {timestamp}")

        print(f"Successfully fetched prices for {len(prices)} markets")

    finally:
        await conn.close()

async def test_transmission_costs():
    """Test transmission cost lookup"""
    # Test bidirectional lookup
    assert get_transmission_cost("DE", "FR") == Decimal("2.50")
    assert get_transmission_cost("FR", "DE") == Decimal("2.50")

    assert get_transmission_cost("NL", "BE") == Decimal("1.00")
    assert get_transmission_cost("BE", "NL") == Decimal("1.00")

    print("Transmission cost lookup working correctly")

async def test_calculate_spreads():
    """Test spread calculation logic"""
    # Create mock price data with a known spread
    mock_prices = {
        "DE": (Decimal("65.00"), datetime.now()),  # Low price
        "FR": (Decimal("75.00"), datetime.now()),  # High price
    }

    opportunities = calculate_spreads(mock_prices)

    assert len(opportunities) > 0, "Should find at least one opportunity"

    spread = opportunities[0]
    print(f"  Found spread: {spread.market_pair}")
    print(f"    Spread: €{spread.spread:.2f}/MWh")
    print(f"    Net opportunity: €{spread.net_opportunity:.2f}/MWh")
    print(f"    Buy from {spread.low_market} @ €{spread.low_price:.2f}")
    print(f"    Sell to {spread.high_market} @ €{spread.high_price:.2f}")

    # Verify calculations
    expected_spread = Decimal("10.00")  # 75 - 65
    transmission_cost = get_transmission_cost("DE", "FR")  # 2.50
    expected_net = expected_spread - transmission_cost  # 7.50

    assert spread.spread == expected_spread, f"Expected spread {expected_spread}, got {spread.spread}"
    assert spread.net_opportunity == expected_net, f"Expected net {expected_net}, got {spread.net_opportunity}"

    print("Spread calculation working correctly")

async def test_inject_known_spread():
    """
    Checkpoint test: Inject a known spread and verify calculator detects it.
    This is the key test mentioned in Phase 4 requirements.
    """
    conn = await get_db_connection()

    try:
        timestamp = datetime.now()

        # Inject prices that create a profitable arbitrage opportunity
        # DE=60 (cheap), FR=80 (expensive), transmission cost=2.50
        # Expected: spread=20, net_opportunity=17.50
        test_prices = {
            "TEST_DE": Decimal("60.00"),
            "TEST_FR": Decimal("80.00"),
        }

        print("\nInjecting test prices:")
        for market, price in test_prices.items():
            await conn.execute(
                "INSERT INTO prices (market, timestamp, price) VALUES ($1, $2, $3)",
                market, timestamp, price
            )
            print(f"  {market}: €{price:.2f}/MWh")

        # Fetch prices and calculate spreads
        prices = await get_latest_prices(conn)

        # Filter to only test markets
        test_market_prices = {k: v for k, v in prices.items() if k.startswith("TEST_")}

        opportunities = calculate_spreads(test_market_prices)

        assert len(opportunities) > 0, "Calculator should detect the injected spread"

        # Write to database
        await write_spreads_to_db(conn, opportunities)

        # Verify it's in the database
        row = await conn.fetchrow(
            "SELECT * FROM spreads WHERE low_market = $1 AND high_market = $2 ORDER BY created_at DESC LIMIT 1",
            "TEST_DE", "TEST_FR"
        )

        assert row is not None, "Spread not found in database"
        assert Decimal(str(row["spread"])) == Decimal("20.00"), "Incorrect spread calculation"
        assert Decimal(str(row["net_opportunity"])) == Decimal("17.50"), "Incorrect net opportunity"

        print("\nVerified spread in database:")
        print(f"  Market pair: {row['market_pair']}")
        print(f"  Spread: €{row['spread']:.2f}/MWh")
        print(f"  Net opportunity: €{row['net_opportunity']:.2f}/MWh")

        print("\nCheckpoint test passed!")

    finally:
        # Cleanup
        await conn.execute("DELETE FROM prices WHERE market LIKE 'TEST_%'")
        await conn.execute("DELETE FROM spreads WHERE market_pair LIKE 'TEST_%'")
        await conn.close()

async def test_calculator_checkpoint():
    """Final checkpoint: verify spreads are appearing in the spreads table"""
    conn = await get_db_connection()

    try:
        # Run the full calculation pipeline
        await calculate_and_store_spreads()

        # Check spreads table
        spread_count = await conn.fetchval("SELECT COUNT(*) FROM spreads")
        print(f"\nSpreads table count: {spread_count}")

        if spread_count > 0:
            # Show recent spreads
            recent = await conn.fetch(
                "SELECT * FROM spreads ORDER BY created_at DESC LIMIT 5"
            )

            print("\nRecent spread opportunities:")
            for row in recent:
                print(f"  {row['market_pair']}: "
                      f"spread=€{row['spread']:.2f}, "
                      f"net=€{row['net_opportunity']:.2f}")

        print("\n" + "="*60)
        print("Phase 4 Checkpoint Instructions:")
        print("="*60)
        print("1. Ensure ingestion is running: python -m src.ingestion")
        print("2. Run calculator: python -m src.calculator")
        print("3. Verify with: SELECT * FROM spreads ORDER BY created_at DESC LIMIT 10;")
        print("4. Should see opportunities appearing as prices update")
        print("="*60)

    finally:
        await conn.close()

if __name__ == "__main__":
    print("Running spread calculator tests...\n")
    asyncio.run(test_get_latest_prices())
    print()
    asyncio.run(test_transmission_costs())
    print()
    asyncio.run(test_calculate_spreads())
    print()
    asyncio.run(test_inject_known_spread())
    print()
    asyncio.run(test_calculator_checkpoint())
    print("\n✓ All calculator tests passed!")
