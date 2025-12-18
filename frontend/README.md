# InTheGrid Dashboard

Professional real-time energy arbitrage monitoring interface.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r ../requirements.txt
```

### 2. Start the Backend API
In one terminal:
```bash
# From project root
python -m src.api
```

The API will run on http://localhost:8000

### 3. Start the Dashboard
In another terminal:
```bash
# From project root
streamlit run frontend/app.py
```

The dashboard will open automatically at http://localhost:8501

## Features

- **Live Price Ticker**: Real-time prices across 5 European markets (DE, FR, NL, DK, BE)
- **Arbitrage Opportunities**: Top 10 profitable trades ranked by net profit
- **Price History**: Interactive chart with market statistics
- **Auto-Refresh**: Dashboard updates every 5 seconds

## Dashboard Layout

1. **Market Prices**: Current spot prices for all markets
2. **Opportunities Table**: Actionable arbitrage trades with buy/sell recommendations
3. **Price Chart**: Historical price movements with average, min, max stats
4. **Alert System**: Highlights best opportunity in real-time

## Notes

- Ensure PostgreSQL is running with price data
- Run the calculator service to generate opportunities: `python -m src.calculator`
- Dashboard auto-refreshes every 5 seconds
