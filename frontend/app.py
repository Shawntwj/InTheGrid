import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# Configuration
API_BASE_URL = "http://localhost:8000"
MARKET_NAMES = {
    "DE": "Germany",
    "FR": "France",
    "NL": "Netherlands",
    "DK": "Denmark",
    "BE": "Belgium"
}

# Page config
st.set_page_config(
    page_title="InTheGrid - Energy Arbitrage",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for clean, professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #aaaaaa;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #0066cc;
    }
    .opportunity-positive {
        color: #28a745;
        font-weight: 600;
    }
    .opportunity-neutral {
        color: #6c757d;
    }
    .timestamp {
        font-size: 0.85rem;
        color: #999;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
    .stPlotlyChart {
        background-color: white;
        border-radius: 8px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def fetch_latest_prices():
    """Fetch latest prices from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/prices/latest", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching prices: {e}")
        return None

def fetch_opportunities():
    """Fetch spread opportunities from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/spreads/opportunities", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching opportunities: {e}")
        return None

def fetch_price_history(market, limit=100):
    """Fetch price history for a specific market"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/prices/history/{market}?limit={limit}", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching history: {e}")
        return None

def display_price_ticker(prices_data):
    """Display live price ticker for all markets"""
    st.markdown("### Live Market Prices")

    if not prices_data or not prices_data.get('markets'):
        st.warning("No price data available")
        return

    markets = sorted(prices_data['markets'], key=lambda x: x['market'])
    num_markets = len(markets)

    # Create columns based on actual number of markets (max 5)
    cols = st.columns(min(num_markets, 5))

    for idx, market_data in enumerate(markets):
        market_code = market_data['market']
        price = market_data['price']
        timestamp = market_data['timestamp']

        with cols[idx % len(cols)]:
            market_name = MARKET_NAMES.get(market_code, market_code)
            st.metric(
                label=f"{market_name} ({market_code})",
                value=f"€{price:.2f}",
                delta=None
            )
            st.markdown(f"<div class='timestamp'>MWh</div>", unsafe_allow_html=True)

def display_opportunities_table(opps_data):
    """Display top arbitrage opportunities"""
    st.markdown("### Top Arbitrage Opportunities")

    if not opps_data or not opps_data.get('opportunities'):
        st.info("No profitable opportunities at the moment")
        return

    opportunities = opps_data['opportunities']

    # Create dataframe for display
    df_data = []
    for opp in opportunities[:10]:  # Show top 10
        df_data.append({
            "Market Pair": opp['market_pair'],
            "Buy From": opp['low_market'],
            "Buy Price": f"€{opp['low_price']:.2f}",
            "Sell To": opp['high_market'],
            "Sell Price": f"€{opp['high_price']:.2f}",
            "Spread": f"€{opp['spread']:.2f}",
            "Net Profit": f"€{opp['net_opportunity']:.2f}",
        })

    df = pd.DataFrame(df_data)

    # Display as table
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Net Profit": st.column_config.TextColumn(
                "Net Profit",
                help="Profit after transmission costs"
            )
        }
    )

    # Show alert for top opportunity
    if opportunities:
        top_opp = opportunities[0]
        if top_opp['net_opportunity'] > 0:
            st.success(
                f"**Best Opportunity:** {top_opp['strategy']} → "
                f"Net profit: €{top_opp['net_opportunity']:.2f}/MWh"
            )

def display_price_chart(market="DE"):
    """Display price chart for selected market"""
    st.markdown("### Price History")

    # Market selector
    selected_market = st.selectbox(
        "Select Market",
        options=list(MARKET_NAMES.keys()),
        format_func=lambda x: f"{MARKET_NAMES[x]} ({x})",
        index=0
    )

    history_data = fetch_price_history(selected_market, limit=100)

    if not history_data or not history_data.get('history'):
        st.warning(f"No history data available for {selected_market}")
        return

    # Prepare data for plotting
    history = history_data['history']
    df = pd.DataFrame(history)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')

    # Create plotly chart
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['price'],
        mode='lines',
        name='Price',
        line=dict(color='#0066cc', width=2),
        fill='tozeroy',
        fillcolor='rgba(0, 102, 204, 0.1)'
    ))

    # Get stats
    stats = history_data.get('stats', {})

    # Add average line if available
    if stats.get('average'):
        fig.add_hline(
            y=stats['average'],
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Avg: €{stats['average']:.2f}",
            annotation_position="right"
        )

    fig.update_layout(
        title=f"{MARKET_NAMES[selected_market]} Price History",
        xaxis_title="Time",
        yaxis_title="Price (€/MWh)",
        hovermode='x unified',
        showlegend=False,
        height=400,
        margin=dict(l=0, r=0, t=40, b=0),
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(
            showgrid=True,
            gridcolor='#f0f0f0'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#f0f0f0'
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # Display stats
    if stats:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Latest", f"€{stats.get('latest', 0):.2f}")
        with col2:
            st.metric("Average", f"€{stats.get('average', 0):.2f}")
        with col3:
            st.metric("Min", f"€{stats.get('min', 0):.2f}")
        with col4:
            st.metric("Max", f"€{stats.get('max', 0):.2f}")

def main():
    """Main dashboard function"""

    # Header
    st.markdown("<div class='main-header'>InTheGrid</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Real-Time Energy Arbitrage Opportunity Detector</div>", unsafe_allow_html=True)

    # Explanation section
    with st.expander("How This Works", expanded=False):
        st.markdown("""
        This dashboard identifies profitable opportunities to buy electricity in one European market and sell it in another,
        profiting from price differences after accounting for transmission costs.

        **How to use this dashboard:**

        1. **Live Market Prices** - Current spot prices across 5 European power markets (Germany, France, Netherlands, Denmark, Belgium)
        2. **Top Opportunities** - Ranked list of profitable trades showing where to buy low and sell high
        3. **Price History** - Historical price movements to understand market volatility and trends

        **Understanding opportunities:**
        - **Spread**: Price difference between two markets (High - Low)
        - **Net Profit**: Profit after deducting transmission costs between markets
        - Only opportunities with positive net profit are shown

        **Note:** Currently using simulated market data that mimics realistic price movements and volatility.
        Production version would integrate with ENTSO-E Transparency Platform for live European power market data.

        Dashboard auto-refreshes every 5 seconds.
        """)

    # Auto-refresh placeholder
    placeholder = st.empty()

    with placeholder.container():
        # Fetch data
        prices_data = fetch_latest_prices()
        opps_data = fetch_opportunities()

        # Last updated timestamp
        if prices_data and prices_data.get('retrieved_at'):
            update_time = datetime.fromisoformat(prices_data['retrieved_at']).strftime('%H:%M:%S')
            st.markdown(f"<div class='timestamp'>Last updated: {update_time}</div>", unsafe_allow_html=True)

        st.markdown("---")

        # Price ticker
        if prices_data:
            display_price_ticker(prices_data)

        st.markdown("---")

        # Opportunities table
        if opps_data:
            display_opportunities_table(opps_data)

        st.markdown("---")

        # Price chart
        display_price_chart()

    # Auto-refresh every 5 seconds
    time.sleep(5)
    st.rerun()

if __name__ == "__main__":
    main()
