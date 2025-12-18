import asyncio
import asyncpg
from datetime import datetime
from decimal import Decimal
from itertools import combinations
from src.database import get_db_connection
from src.models import Spread

# Transmission costs between market pairs (€/MWh)
# These represent the cost of transmitting power between countries
TRANSMISSION_COSTS = {
    "DE-FR": Decimal("2.50"),
    "DE-NL": Decimal("1.50"),
    "DE-DK": Decimal("3.00"),
    "DE-BE": Decimal("2.00"),
    "FR-NL": Decimal("2.00"),
    "FR-BE": Decimal("1.50"),
    "FR-DK": Decimal("4.00"),
    "NL-BE": Decimal("1.00"),
    "NL-DK": Decimal("3.50"),
    "BE-DK": Decimal("3.50"),
    # Test markets for unit testing
    "TEST_DE-TEST_FR": Decimal("2.50"),
}

async def get_latest_prices(conn: asyncpg.Connection) -> dict[str, tuple[Decimal, datetime]]:
    """
    Fetch the latest price for each market from the database.

    Returns:
        dict mapping market name to (price, timestamp) tuple
    """
    rows = await conn.fetch("""
        SELECT DISTINCT ON (market) market, price, timestamp
        FROM prices
        ORDER BY market, timestamp DESC
    """)

    return {row["market"]: (Decimal(str(row["price"])), row["timestamp"]) for row in rows}

def get_transmission_cost(market1: str, market2: str) -> Decimal:
    """
    Get transmission cost between two markets.
    Markets can be in any order (DE-FR == FR-DE).
    """
    pair = f"{market1}-{market2}"
    reverse_pair = f"{market2}-{market1}"

    return TRANSMISSION_COSTS.get(pair, TRANSMISSION_COSTS.get(reverse_pair, Decimal("0")))

def calculate_spreads(prices: dict[str, tuple[Decimal, datetime]]) -> list[Spread]:
    """
    Calculate spread opportunities for all market pairs.

    A spread opportunity exists when:
    spread = high_price - low_price
    net_opportunity = spread - transmission_cost > 0

    Returns:
        list of Spread objects representing arbitrage opportunities
    """
    opportunities = []
    markets = list(prices.keys())

    # Generate all possible market pairs
    for market1, market2 in combinations(markets, 2):
        price1, timestamp1 = prices[market1]
        price2, timestamp2 = prices[market2]

        # Use the most recent timestamp
        timestamp = max(timestamp1, timestamp2)

        # Determine which market is higher and which is lower
        if price1 > price2:
            high_market, high_price = market1, price1
            low_market, low_price = market2, price2
        else:
            high_market, high_price = market2, price2
            low_market, low_price = market1, price1

        # Calculate spread and net opportunity
        spread = high_price - low_price
        transmission_cost = get_transmission_cost(market1, market2)
        net_opportunity = spread - transmission_cost

        # Only create spread if there's a positive opportunity
        if net_opportunity > 0:
            market_pair = f"{low_market}-{high_market}"

            opportunities.append(Spread(
                market_pair=market_pair,
                timestamp=timestamp,
                spread=spread,
                net_opportunity=net_opportunity,
                low_market=low_market,
                high_market=high_market,
                low_price=low_price,
                high_price=high_price
            ))

    return opportunities

async def write_spreads_to_db(conn: asyncpg.Connection, spreads: list[Spread]):
    """Write spread opportunities to the database"""
    for spread in spreads:
        await conn.execute(
            """
            INSERT INTO spreads (
                market_pair, timestamp, spread, net_opportunity,
                low_market, high_market, low_price, high_price
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            spread.market_pair,
            spread.timestamp,
            spread.spread,
            spread.net_opportunity,
            spread.low_market,
            spread.high_market,
            spread.low_price,
            spread.high_price
        )

async def calculate_and_store_spreads():
    """
    Main function: Read latest prices, calculate spreads, and store opportunities.
    This would typically be called on a schedule (e.g., every time new prices arrive).
    """
    conn = await get_db_connection()

    try:
        # Step 1: Get latest prices
        prices = await get_latest_prices(conn)

        if not prices:
            print("No prices available in database")
            return

        print(f"Fetched latest prices for {len(prices)} markets")

        # Step 2: Calculate spreads
        opportunities = calculate_spreads(prices)

        print(f"Found {len(opportunities)} arbitrage opportunities")

        # Step 3: Write to database
        if opportunities:
            await write_spreads_to_db(conn, opportunities)
            print(f"Stored {len(opportunities)} opportunities to database")

            # Print summary
            for opp in opportunities:
                print(f"  {opp.market_pair}: spread={opp.spread:.2f}, "
                      f"net={opp.net_opportunity:.2f} "
                      f"(buy {opp.low_market}@€{opp.low_price:.2f}, "
                      f"sell {opp.high_market}@€{opp.high_price:.2f})")
        else:
            print("No profitable opportunities found")

    finally:
        await conn.close()

async def calculator_loop():
    """
    Continuous loop that calculates spreads every 10 seconds.
    In production, this might listen to Redis streams instead.
    """
    print("Starting spread calculator service...")
    print("Calculating spreads every 10 seconds")

    iteration = 0

    try:
        while True:
            iteration += 1
            print(f"\n[Iteration {iteration}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            await calculate_and_store_spreads()

            await asyncio.sleep(10)

    except KeyboardInterrupt:
        print("\nStopping calculator service...")

if __name__ == "__main__":
    asyncio.run(calculator_loop())
