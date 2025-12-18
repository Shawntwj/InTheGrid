from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from datetime import datetime
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database connection pool"""
    app.state.db_pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        database=os.getenv("DB_NAME", "inthegrid")
    )
    yield
    await app.state.db_pool.close()

app = FastAPI(
    title="InTheGrid API",
    description="REST API for electricity price arbitrage opportunities",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the API is running.

    Returns:
        dict: Status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "InTheGrid API"
    }

@app.get("/api/prices/latest")
async def get_latest_prices():
    """
    Get the latest price for each market.

    Returns:
        dict: Dictionary of markets with their latest prices
    """
    async with app.state.db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT DISTINCT ON (market)
                market, price, timestamp
            FROM prices
            ORDER BY market, timestamp DESC
        """)

        if not rows:
            return {"markets": [], "count": 0}

        markets = []
        for row in rows:
            markets.append({
                "market": row["market"],
                "price": float(row["price"]),
                "timestamp": row["timestamp"].isoformat()
            })

        return {
            "markets": markets,
            "count": len(markets),
            "retrieved_at": datetime.now().isoformat()
        }

@app.get("/api/spreads/opportunities")
async def get_spread_opportunities():
    """
    Get current spread arbitrage opportunities.

    Returns:
        dict: List of current arbitrage opportunities
    """
    async with app.state.db_pool.acquire() as conn:
        # Get the most recent spread opportunities
        # We fetch spreads from the last 5 minutes to show current opportunities
        rows = await conn.fetch("""
            SELECT DISTINCT ON (market_pair)
                market_pair, timestamp, spread, net_opportunity,
                low_market, high_market, low_price, high_price
            FROM spreads
            WHERE timestamp > NOW() - INTERVAL '5 minutes'
            ORDER BY market_pair, timestamp DESC
        """)

        if not rows:
            return {"opportunities": [], "count": 0}

        opportunities = []
        for row in rows:
            opportunities.append({
                "market_pair": row["market_pair"],
                "timestamp": row["timestamp"].isoformat(),
                "spread": float(row["spread"]),
                "net_opportunity": float(row["net_opportunity"]),
                "low_market": row["low_market"],
                "high_market": row["high_market"],
                "low_price": float(row["low_price"]),
                "high_price": float(row["high_price"]),
                "strategy": f"Buy from {row['low_market']} at €{float(row['low_price']):.2f}/MWh, "
                           f"Sell to {row['high_market']} at €{float(row['high_price']):.2f}/MWh"
            })

        # Sort by net_opportunity descending (best opportunities first)
        opportunities.sort(key=lambda x: x["net_opportunity"], reverse=True)

        return {
            "opportunities": opportunities,
            "count": len(opportunities),
            "retrieved_at": datetime.now().isoformat()
        }

@app.get("/api/prices/history/{market}")
async def get_price_history(market: str, limit: int = 100):
    """
    Get price history for a specific market.

    Args:
        market: Market name (e.g., DE, FR, NL)
        limit: Maximum number of records to return (default: 100)

    Returns:
        dict: Price history for the specified market
    """
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 1000")

    async with app.state.db_pool.acquire() as conn:
        # Check if market exists
        market_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM prices WHERE market = $1)",
            market
        )

        if not market_exists:
            raise HTTPException(status_code=404, detail=f"Market '{market}' not found")

        rows = await conn.fetch(
            """
            SELECT market, price, timestamp
            FROM prices
            WHERE market = $1
            ORDER BY timestamp DESC
            LIMIT $2
            """,
            market,
            limit
        )

        history = []
        for row in rows:
            history.append({
                "market": row["market"],
                "price": float(row["price"]),
                "timestamp": row["timestamp"].isoformat()
            })

        # Calculate some basic statistics
        prices = [float(row["price"]) for row in rows]

        stats = {}
        if prices:
            stats = {
                "latest": prices[0],
                "average": sum(prices) / len(prices),
                "min": min(prices),
                "max": max(prices),
                "samples": len(prices)
            }

        return {
            "market": market,
            "history": history,
            "stats": stats,
            "retrieved_at": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
