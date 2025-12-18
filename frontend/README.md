# InTheGrid Dashboard

Professional real-time energy arbitrage monitoring interface built with Streamlit.

## Overview

This dashboard provides a live view of electricity price arbitrage opportunities across 5 European power markets:
- Germany (DE)
- France (FR)
- Netherlands (NL)
- Denmark (DK)
- Belgium (BE)

## Quick Start

### Option 1: Using Docker (Recommended)

Start all services including the backend API:
```bash
# From project root
docker-compose up
```

Then run the Streamlit dashboard:
```bash
# From project root
streamlit run frontend/app.py
```

The dashboard will open automatically at http://localhost:8501

### Option 2: Manual Setup

**1. Install Dependencies**
```bash
# From project root
pip install -r requirements.txt
```

**2. Start Infrastructure**
```bash
docker-compose up postgres redis
```

**3. Start Backend Services**

In separate terminals:
```bash
# Terminal 1: API
python -m src.api

# Terminal 2: Data Ingestion
python -m src.ingestion

# Terminal 3: Calculator
python -m src.calculator
```

**4. Start Dashboard**
```bash
# Terminal 4: Dashboard
streamlit run frontend/app.py
```

## Features

### Live Price Ticker
- Real-time spot prices across all 5 European markets
- Updates every 5 seconds
- Prices displayed in €/MWh

### Arbitrage Opportunities Table
- Top 10 profitable trading opportunities
- Shows buy/sell market pairs
- Net profit after transmission costs
- Sorted by profitability

### Interactive Price History Chart
- Historical price movements for any selected market
- Statistical analysis (min, max, average, latest)
- Built with Plotly for interactive exploration
- Customizable market selection

### Auto-Refresh
- Dashboard automatically refreshes every 5 seconds
- Real-time updates without manual intervention

## Dashboard Layout

The interface is organized into four main sections:

1. **Header**: Quick explanation of how the dashboard works (expandable)
2. **Live Market Prices**: Current spot prices for all markets with last update timestamp
3. **Top Arbitrage Opportunities**: Ranked list of profitable trades showing where to buy low and sell high
4. **Price History**: Interactive chart with market selector and key statistics

## Configuration

The dashboard connects to the FastAPI backend at `http://localhost:8000` by default.

To modify the API endpoint, edit [app.py:9](app.py#L9):
```python
API_BASE_URL = "http://localhost:8000"
```

Market names can be customized at [app.py:10-16](app.py#L10-L16):
```python
MARKET_NAMES = {
    "DE": "Germany",
    "FR": "France",
    # ...
}
```

## API Endpoints Used

The dashboard consumes the following API endpoints:

- `GET /api/prices/latest` - Latest prices for all markets
- `GET /api/spreads/opportunities` - Current arbitrage opportunities
- `GET /api/prices/history/{market}?limit={n}` - Historical prices for a specific market

## Dependencies

Key frontend dependencies:
- **Streamlit** (1.41.1) - Web application framework
- **Plotly** (5.24.1) - Interactive charting
- **Pandas** (2.2.3) - Data manipulation
- **Requests** (2.32.3) - HTTP client for API calls

See [requirements.txt](../requirements.txt) for complete dependency list.

## Troubleshooting

**Dashboard shows "Error fetching prices"**
- Ensure the API is running on http://localhost:8000
- Check that PostgreSQL has price data
- Verify the ingestion service is running

**No opportunities shown**
- Ensure the calculator service is running
- Wait a few seconds for spreads to be calculated
- Check that multiple markets have price data

**Dashboard doesn't auto-refresh**
- This is normal Streamlit behavior
- The app reruns every 5 seconds automatically

## Development

The dashboard is a single-file Streamlit application ([app.py](app.py)) with:
- Custom CSS styling for professional appearance
- Error handling for API failures
- Responsive layout using Streamlit columns
- Clean, minimalist design focused on data clarity
