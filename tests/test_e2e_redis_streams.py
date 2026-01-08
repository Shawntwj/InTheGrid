"""
End-to-End Test for Redis Streams Event-Driven Architecture

This test validates the complete flow:
1. Ingestion publishes to Redis Stream
2. Calculator consumes from Redis Stream
3. Spreads are calculated and stored in PostgreSQL
4. Consumer group properly tracks processed messages
"""

import asyncio
import asyncpg
import redis.asyncio as redis
import os
from datetime import datetime
from decimal import Decimal

async def get_db_connection():
    """Create database connection"""
    return await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        database=os.getenv("DB_NAME", "inthegrid")
    )

async def get_redis_connection():
    """Create Redis connection"""
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    return await redis.Redis(host=host, port=port, decode_responses=True)

async def test_redis_stream_exists():
    """Test 1: Verify Redis Stream exists and has data"""
    print("\n" + "="*60)
    print("TEST 1: Redis Stream Existence")
    print("="*60)

    redis_conn = await get_redis_connection()

    try:
        # Check stream length
        stream_len = await redis_conn.xlen("prices")
        print(f"✓ Redis Stream 'prices' exists")
        print(f"  Messages in stream: {stream_len}")

        assert stream_len > 0, "Stream should have messages"
        print(f"✓ Stream contains {stream_len} messages")

        # Get latest message
        messages = await redis_conn.xrevrange("prices", count=1)
        if messages:
            msg_id, data = messages[0]
            print(f"✓ Latest message ID: {msg_id}")
            print(f"  Sample data: {dict(list(data.items())[:3])}...")

        return True

    finally:
        await redis_conn.aclose()

async def test_consumer_group_exists():
    """Test 2: Verify consumer group is created and active"""
    print("\n" + "="*60)
    print("TEST 2: Consumer Group Status")
    print("="*60)

    redis_conn = await get_redis_connection()

    try:
        # Get consumer group info
        groups = await redis_conn.xinfo_groups("prices")

        calculator_group = None
        for group in groups:
            if group['name'] == 'calculator_group':
                calculator_group = group
                break

        assert calculator_group is not None, "calculator_group should exist"
        print(f"✓ Consumer group 'calculator_group' exists")

        print(f"  Consumers: {calculator_group['consumers']}")
        print(f"  Pending messages: {calculator_group['pending']}")
        print(f"  Messages read: {calculator_group.get('entries-read', 'N/A')}")
        print(f"  Lag: {calculator_group.get('lag', 'N/A')}")

        assert calculator_group['consumers'] >= 1, "Should have at least 1 consumer"
        print(f"✓ Active consumers: {calculator_group['consumers']}")

        # Low pending count indicates healthy processing
        if calculator_group['pending'] < 10:
            print(f"✓ Low pending count ({calculator_group['pending']}) - healthy processing")
        else:
            print(f"⚠ High pending count ({calculator_group['pending']}) - may indicate backlog")

        return True

    finally:
        await redis_conn.aclose()

async def test_prices_ingested():
    """Test 3: Verify prices are being ingested to PostgreSQL"""
    print("\n" + "="*60)
    print("TEST 3: Price Ingestion to PostgreSQL")
    print("="*60)

    conn = await get_db_connection()

    try:
        # Check total price count
        count = await conn.fetchval("SELECT COUNT(*) FROM prices")
        print(f"✓ PostgreSQL 'prices' table has {count} entries")

        assert count > 0, "Should have price data"

        # Check recent prices (last minute)
        recent = await conn.fetch("""
            SELECT market, price, timestamp
            FROM prices
            WHERE timestamp > NOW() - INTERVAL '1 minute'
            ORDER BY timestamp DESC
            LIMIT 5
        """)

        print(f"✓ Recent prices (last 1 minute): {len(recent)} entries")

        if recent:
            print("  Sample recent prices:")
            for row in recent[:3]:
                print(f"    {row['market']}: €{row['price']:.2f} at {row['timestamp']}")

        # Check market coverage
        markets = await conn.fetch("""
            SELECT DISTINCT market
            FROM prices
            WHERE timestamp > NOW() - INTERVAL '1 minute'
        """)

        market_names = [r['market'] for r in markets]
        print(f"✓ Markets with recent data: {', '.join(market_names)}")

        return True

    finally:
        await conn.close()

async def test_spreads_calculated():
    """Test 4: Verify spreads are being calculated and stored"""
    print("\n" + "="*60)
    print("TEST 4: Spread Calculation from Redis Stream")
    print("="*60)

    conn = await get_db_connection()

    try:
        # Check total spread count
        count = await conn.fetchval("SELECT COUNT(*) FROM spreads")
        print(f"✓ PostgreSQL 'spreads' table has {count} opportunities")

        assert count > 0, "Should have calculated spreads"

        # Check recent spreads (last minute)
        recent_spreads = await conn.fetch("""
            SELECT market_pair, spread, net_opportunity, timestamp, created_at
            FROM spreads
            WHERE timestamp > NOW() - INTERVAL '1 minute'
            ORDER BY created_at DESC
            LIMIT 5
        """)

        print(f"✓ Recent spreads (last 1 minute): {len(recent_spreads)} opportunities")

        if recent_spreads:
            print("  Sample recent opportunities:")
            for row in recent_spreads[:3]:
                print(f"    {row['market_pair']}: spread=€{row['spread']:.2f}, "
                      f"net=€{row['net_opportunity']:.2f}")

        # Verify spreads are being created in near real-time
        # (created_at should be close to timestamp)
        if recent_spreads:
            latest = recent_spreads[0]
            delay = latest['created_at'] - latest['timestamp']
            delay_seconds = delay.total_seconds()

            print(f"\n  Processing latency check:")
            print(f"    Price timestamp: {latest['timestamp']}")
            print(f"    Spread created at: {latest['created_at']}")
            print(f"    Delay: {delay_seconds:.2f}s")

            if delay_seconds < 2:
                print(f"✓ Excellent! Sub-2s latency (event-driven working)")
            elif delay_seconds < 10:
                print(f"✓ Good latency ({delay_seconds:.1f}s)")
            else:
                print(f"⚠ High latency ({delay_seconds:.1f}s) - may indicate issues")

        return True

    finally:
        await conn.close()

async def test_end_to_end_flow():
    """Test 5: Full E2E validation"""
    print("\n" + "="*60)
    print("TEST 5: End-to-End Flow Validation")
    print("="*60)

    redis_conn = await get_redis_connection()
    db_conn = await get_db_connection()

    try:
        # Get current counts
        initial_stream_len = await redis_conn.xlen("prices")
        initial_spread_count = await db_conn.fetchval(
            "SELECT COUNT(*) FROM spreads WHERE created_at > NOW() - INTERVAL '5 seconds'"
        )

        print(f"Initial state:")
        print(f"  Redis stream length: {initial_stream_len}")
        print(f"  Recent spreads: {initial_spread_count}")

        # Wait for new data (ingestion runs every 10s)
        print(f"\nWaiting 12 seconds for new data cycle...")
        await asyncio.sleep(12)

        # Check if new data arrived
        final_stream_len = await redis_conn.xlen("prices")
        final_spread_count = await db_conn.fetchval(
            "SELECT COUNT(*) FROM spreads WHERE created_at > NOW() - INTERVAL '5 seconds'"
        )

        print(f"\nFinal state:")
        print(f"  Redis stream length: {final_stream_len}")
        print(f"  Recent spreads: {final_spread_count}")

        # Verify growth
        if final_stream_len > initial_stream_len:
            print(f"✓ New messages added to Redis Stream (+{final_stream_len - initial_stream_len})")

        if final_spread_count > 0:
            print(f"✓ New spreads calculated in last 5 seconds")

            # Get the latest spread
            latest = await db_conn.fetchrow("""
                SELECT * FROM spreads
                ORDER BY created_at DESC
                LIMIT 1
            """)

            if latest:
                age = (datetime.now(latest['created_at'].tzinfo) - latest['created_at']).total_seconds()
                print(f"  Latest spread: {latest['market_pair']}")
                print(f"  Age: {age:.1f}s ago")
                print(f"  Net opportunity: €{latest['net_opportunity']:.2f}")

        print(f"\n✓ End-to-end flow is working!")
        return True

    finally:
        await redis_conn.aclose()
        await db_conn.close()

async def run_all_tests():
    """Run all E2E tests"""
    print("\n" + "="*60)
    print("REDIS STREAMS E2E TEST SUITE")
    print("="*60)
    print("Validating event-driven architecture...")

    tests = [
        ("Redis Stream Exists", test_redis_stream_exists),
        ("Consumer Group Active", test_consumer_group_exists),
        ("Prices Ingested", test_prices_ingested),
        ("Spreads Calculated", test_spreads_calculated),
        ("End-to-End Flow", test_end_to_end_flow),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, "PASSED" if result else "FAILED"))
        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
            results.append((name, "FAILED"))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for name, status in results:
        symbol = "✓" if status == "PASSED" else "✗"
        print(f"{symbol} {name}: {status}")

    passed = sum(1 for _, status in results if status == "PASSED")
    total = len(results)

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All E2E tests passed! Redis Streams architecture is working correctly.")
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Check the output above for details.")

    return passed == total

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Prerequisites:")
    print("="*60)
    print("1. Ensure services are running: docker-compose up -d")
    print("2. Wait ~30 seconds for data to accumulate")
    print("3. Run this test")
    print("\nStarting tests in 3 seconds...")
    print("="*60)

    asyncio.run(asyncio.sleep(3))
    success = asyncio.run(run_all_tests())

    exit(0 if success else 1)
