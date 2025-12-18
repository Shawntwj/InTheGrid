import random
from datetime import datetime, timedelta
from typing import Dict, List

# Base prices (EUR/MWh) for European electricity markets
# DE: Germany, FR: France, NL: Netherlands, BE: Belgium, AT: Austria
MARKETS = {
    "DE": 75.0,
    "FR": 85.0,
    "NL": 73.0,
    "BE": 80.0,
    "AT": 78.0,
}

# Markets with interconnected grids move together
# DE-NL share transmission lines, so price movements correlate
CORRELATED_PAIRS = {
    "DE": ["NL"],
    "NL": ["DE"]
}

def get_time_multiplier(hour: int) -> float:
    if 8 <= hour <= 20:
        return 1.3
    elif 21 <= hour <= 23 or 0 <= hour <= 6:
        return 0.8
    return 1.0

def generate_prices(hours: int = 24) -> List[Dict]:
    prices = {market: base for market, base in MARKETS.items()}
    data = []
    start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for h in range(hours):
        timestamp = start_time + timedelta(hours=h)
        hour = timestamp.hour
        time_mult = get_time_multiplier(hour)

        market_prices = {}
        # DE price change drives correlated markets
        de_change = random.gauss(0, 2)

        for market in MARKETS:
            if market == "DE":
                change = de_change
            elif market in CORRELATED_PAIRS.get("DE", []):
                # NL uses 70% of DE's movement + own noise (interconnected grids)
                change = de_change * 0.7 + random.gauss(0, 1)
            else:
                change = random.gauss(0, 2)

            # Random walk
            prices[market] += change
            # Pull back toward base price to prevent infinite drift
            mean_reversion = (MARKETS[market] - prices[market]) * 0.1
            prices[market] += mean_reversion

            # Apply time-of-day scaling to base price
            final_price = prices[market] * time_mult
            market_prices[market] = round(final_price, 2)

        data.append({
            "timestamp": timestamp,
            "prices": market_prices
        })

    return data

def print_prices(data: List[Dict]):
    print(f"{'Time':<6} {'DE':>8} {'FR':>8} {'NL':>8} {'BE':>8} {'AT':>8}")
    print("-" * 50)
    for entry in data:
        time_str = entry["timestamp"].strftime("%H:%M")
        prices = entry["prices"]
        print(f"{time_str:<6} {prices['DE']:>8.2f} {prices['FR']:>8.2f} {prices['NL']:>8.2f} {prices['BE']:>8.2f} {prices['AT']:>8.2f}")

if __name__ == "__main__":
    data = generate_prices(24)
    print_prices(data)

    print("\nSummary:")
    for market in MARKETS:
        prices_list = [entry["prices"][market] for entry in data]
        print(f"{market}: min={min(prices_list):.2f}, max={max(prices_list):.2f}, avg={sum(prices_list)/len(prices_list):.2f}")
