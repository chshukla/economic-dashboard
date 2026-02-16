import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from fredapi import Fred

# Page config
st.set_page_config(page_title="Economic Dashboard", layout="wide", page_icon="📊")

# Title
st.title("🏦 Federal Reserve Economic & Sector Performance Dashboard")
st.markdown(f"*Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

# Initialize FRED API (you'll need to get a free API key from https://fred.stlouisfed.org/docs/api/api_key.html)
# For now, we'll use dummy data if no key is provided
FRED_API_KEY = st.secrets.get("FRED_API_KEY", None)

# Sector ETFs to track
SECTOR_ETFS = {
    'XLK': 'Technology',
    'XLF': 'Financials',
    'XLE': 'Energy',
    'XLV': 'Healthcare',
    'XLY': 'Consumer Discretionary',
    'XLP': 'Consumer Staples',
    'XLI': 'Industrials',
    'XLB': 'Materials',
    'XLRE': 'Real Estate',
    'XLU': 'Utilities',
    'XLC': 'Communication Services'
}

# Moving average periods
MA_PERIODS = [8, 21, 100, 200]

@st.cache_data(ttl=3600)
def get_fed_delinquency_data():
    """Fetch Federal Reserve delinquency data from FRED"""

    if FRED_API_KEY:
        try:
            fred = Fred(api_key=FRED_API_KEY)

            # FRED Series IDs for delinquency rates
            series = {
                'Credit Cards': 'DRCCLACBS',  # Delinquency Rate on Credit Card Loans
                'Auto Loans': 'DRSDLACBS',     # Delinquency Rate on Single-Family Residential Mortgages
                'Home Loans': 'DRSFRMACBS',    # Delinquency Rate on Consumer Loans
                'Student Loans': 'DRSLACBS'    # Delinquency Rate on Student Loans (est)
            }

            data = {}
            for name, series_id in series.items():
                try:
                    df = fred.get_series(series_id)
                    data[name] = {
                        'current': df.iloc[-1],
                        'previous': df.iloc[-2],
                        'yoy': df.iloc[-1] - df.iloc[-5] if len(df) >= 5 else 0,
                        'trend': df.tail(12).tolist()
                    }
                except:
                    data[name] = {'current': 0, 'previous': 0, 'yoy': 0, 'trend': []}

            return data
        except Exception as e:
            st.warning(f"Could not fetch FRED data: {e}. Using sample data.")

    # Sample data if API key not available
    return {
        'Credit Cards': {'current': 3.25, 'previous': 3.15, 'yoy': 0.35, 'trend': [2.9, 2.95, 3.0, 3.05, 3.1, 3.15, 3.20, 3.22, 3.25]},
        'Auto Loans': {'current': 2.45, 'previous': 2.38, 'yoy': 0.28, 'trend': [2.17, 2.20, 2.25, 2.30, 2.32, 2.35, 2.38, 2.40, 2.45]},
        'Home Loans': {'current': 1.85, 'previous': 1.82, 'yoy': 0.12, 'trend': [1.73, 1.75, 1.77, 1.79, 1.80, 1.81, 1.82, 1.83, 1.85]},
        'Student Loans': {'current': 4.15, 'previous': 4.08, 'yoy': 0.45, 'trend': [3.7, 3.75, 3.82, 3.88, 3.95, 4.0, 4.05, 4.08, 4.15]}
    }

@st.cache_data(ttl=3600)
def get_etf_data():
    """Fetch ETF price data and calculate moving averages"""

    end_date = datetime.now()
    start_date = end_date - timedelta(days=250)  # Get enough data for 200-day MA

    results = {}

    for ticker, name in SECTOR_ETFS.items():
        try:
            # Download data
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if data.empty:
                continue

            # Flatten multi-level columns if present (newer yfinance)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            # Extract close prices as a simple Series
            close = data['Close'].squeeze()

            current_price = float(close.iloc[-1])

            # Calculate moving averages
            ma_values = {}
            ma_distances = {}
            for period in MA_PERIODS:
                if len(close) >= period:
                    ma = float(close.rolling(window=period).mean().iloc[-1])
                    ma_values[f'MA{period}'] = ma
                    # Distance below MA (negative if below, positive if above)
                    distance = ((current_price - ma) / ma) * 100
                    ma_distances[f'MA{period}'] = float(distance)

            # Calculate returns for different periods
            returns = {}
            for days, label in [(0, 'YTD'), (60, '60D'), (90, '90D')]:
                if label == 'YTD':
                    # Calculate YTD return
                    year_start = datetime(end_date.year, 1, 1)
                    ytd_data = close[close.index >= year_start]
                    if len(ytd_data) > 0:
                        start_price = float(ytd_data.iloc[0])
                        returns[label] = float(((current_price - start_price) / start_price) * 100)
                    else:
                        returns[label] = 0.0
                else:
                    if len(close) > days:
                        past_price = float(close.iloc[-days])
                        returns[label] = float(((current_price - past_price) / past_price) * 100)
                    else:
                        returns[label] = 0.0

            results[ticker] = {
                'name': name,
                'price': current_price,
                'ma_values': ma_values,
                'ma_distances': ma_distances,
                'returns': returns
            }

        except Exception as e:
            st.warning(f"Could not fetch data for {ticker}: {e}")
            continue

    return results

def create_delinquency_chart(data):
    """Create delinquency rate comparison chart"""

    categories = list(data.keys())
    current_rates = [data[cat]['current'] for cat in categories]
    previous_rates = [data[cat]['previous'] for cat in categories]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Current',
        x=categories,
        y=current_rates,
        marker_color='#ef4444',
        text=[f'{val:.2f}%' for val in current_rates],
        textposition='outside'
    ))

    fig.add_trace(go.Bar(
        name='Previous Period',
        x=categories,
        y=previous_rates,
        marker_color='#94a3b8',
        text=[f'{val:.2f}%' for val in previous_rates],
        textposition='outside'
    ))

    fig.update_layout(
        title='Delinquency Rates by Loan Type',
        xaxis_title='Loan Type',
        yaxis_title='Delinquency Rate (%)',
        barmode='group',
        height=400
    )

    return fig

def get_ma_color(distance):
    """Get color based on how far below MA (red for below, green for above)"""
    if distance >= 0:
        # Above MA - green shades
        return f'rgba(34, 197, 94, {min(abs(distance) / 10, 1)})'
    else:
        # Below MA - red shades
        return f'rgba(239, 68, 68, {min(abs(distance) / 10, 1)})'

def create_ma_heatmap(etf_data):
    """Create heatmap showing ETFs vs Moving Averages"""

    tickers = list(etf_data.keys())
    ma_labels = [f'MA{p}' for p in MA_PERIODS]

    # Build matrix of distances
    matrix = []
    hover_text = []

    for ticker in tickers:
        row = []
        hover_row = []
        for ma in ma_labels:
            distance = etf_data[ticker]['ma_distances'].get(ma, 0)
            # Ensure distance is a float, handle None or invalid values
            if distance is None or not isinstance(distance, (int, float)):
                distance = 0.0
            row.append(float(distance))
            hover_row.append(f"{ticker}<br>{ma}: {distance:+.2f}%")
        matrix.append(row)
        hover_text.append(hover_row)

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=ma_labels,
        y=[f"{t} ({etf_data[t]['name']})" for t in tickers],
        text=hover_text,
        hovertemplate='%{text}<extra></extra>',
        colorscale=[
            [0, 'rgb(220, 38, 38)'],      # Deep red (far below)
            [0.45, 'rgb(252, 165, 165)'], # Light red
            [0.5, 'rgb(255, 255, 255)'],  # White (at MA)
            [0.55, 'rgb(134, 239, 172)'], # Light green
            [1, 'rgb(22, 163, 74)']       # Deep green (far above)
        ],
        zmid=0,
        colorbar=dict(title="% from MA")
    ))

    fig.update_layout(
        title='🚩 Sector ETF Distance from Moving Averages',
        xaxis_title='Moving Average Period',
        yaxis_title='Sector ETF',
        height=500
    )

    return fig

def create_returns_chart(etf_data, period='YTD'):
    """Create bar chart of sector returns"""

    tickers = list(etf_data.keys())
    names = [etf_data[t]['name'] for t in tickers]
    returns = [etf_data[t]['returns'].get(period, 0) for t in tickers]

    # Ensure all returns are floats
    returns = [float(r) if r is not None else 0.0 for r in returns]

    # Sort by returns
    sorted_data = sorted(zip(names, returns, tickers), key=lambda x: x[1], reverse=True)
    names_sorted, returns_sorted, tickers_sorted = zip(*sorted_data)

    colors = ['#22c55e' if r >= 0 else '#ef4444' for r in returns_sorted]

    fig = go.Figure(go.Bar(
        x=returns_sorted,
        y=names_sorted,
        orientation='h',
        marker_color=colors,
        text=[f'{r:+.2f}%' for r in returns_sorted],
        textposition='outside'
    ))

    fig.update_layout(
        title=f'Sector Performance - {period}',
        xaxis_title='Return (%)',
        yaxis_title='Sector',
        height=500
    )

    return fig

# Main app
st.header("📉 Federal Reserve Delinquency Data")

with st.spinner("Fetching Federal Reserve data..."):
    delinquency_data = get_fed_delinquency_data()

if not FRED_API_KEY:
    st.info("💡 Add your FRED API key to Streamlit secrets to fetch live data. Get one free at: https://fred.stlouisfed.org/docs/api/api_key.html")

# Display delinquency metrics
col1, col2, col3, col4 = st.columns(4)

for idx, (loan_type, metrics) in enumerate(delinquency_data.items()):
    col = [col1, col2, col3, col4][idx]
    with col:
        delta_color = "inverse" if metrics['yoy'] > 0 else "normal"
        st.metric(
            label=loan_type,
            value=f"{metrics['current']:.2f}%",
            delta=f"{metrics['yoy']:+.2f}% YoY",
            delta_color=delta_color
        )

# Delinquency chart
st.plotly_chart(create_delinquency_chart(delinquency_data), use_container_width=True)

st.divider()

# Sector Performance Section
st.header("📊 Sector ETF Performance & Technical Analysis")

with st.spinner("Fetching ETF data and calculating moving averages..."):
    etf_data = get_etf_data()

if etf_data:
    # Moving Average Heatmap
    st.plotly_chart(create_ma_heatmap(etf_data), use_container_width=True)

    st.divider()

    # Performance comparison
    st.subheader("🏆 Leading & Lagging Sectors")

    tab1, tab2, tab3 = st.tabs(["📅 YTD", "📆 60 Days", "📆 90 Days"])

    with tab1:
        st.plotly_chart(create_returns_chart(etf_data, 'YTD'), use_container_width=True)

        # Show leaders and laggards
        ytd_returns = [(etf_data[t]['name'], float(etf_data[t]['returns'].get('YTD', 0))) for t in etf_data]
        ytd_returns.sort(key=lambda x: x[1], reverse=True)

        col1, col2 = st.columns(2)
        with col1:
            st.success("**🚀 Top 3 Leaders (YTD)**")
            for name, ret in ytd_returns[:3]:
                st.write(f"• {name}: **{ret:+.2f}%**")

        with col2:
            st.error("**📉 Bottom 3 Laggards (YTD)**")
            for name, ret in ytd_returns[-3:]:
                st.write(f"• {name}: **{ret:+.2f}%**")

    with tab2:
        st.plotly_chart(create_returns_chart(etf_data, '60D'), use_container_width=True)

        d60_returns = [(etf_data[t]['name'], float(etf_data[t]['returns'].get('60D', 0))) for t in etf_data]
        d60_returns.sort(key=lambda x: x[1], reverse=True)

        col1, col2 = st.columns(2)
        with col1:
            st.success("**🚀 Top 3 Leaders (60D)**")
            for name, ret in d60_returns[:3]:
                st.write(f"• {name}: **{ret:+.2f}%**")

        with col2:
            st.error("**📉 Bottom 3 Laggards (60D)**")
            for name, ret in d60_returns[-3:]:
                st.write(f"• {name}: **{ret:+.2f}%**")

    with tab3:
        st.plotly_chart(create_returns_chart(etf_data, '90D'), use_container_width=True)

        d90_returns = [(etf_data[t]['name'], float(etf_data[t]['returns'].get('90D', 0))) for t in etf_data]
        d90_returns.sort(key=lambda x: x[1], reverse=True)

        col1, col2 = st.columns(2)
        with col1:
            st.success("**🚀 Top 3 Leaders (90D)**")
            for name, ret in d90_returns[:3]:
                st.write(f"• {name}: **{ret:+.2f}%**")

        with col2:
            st.error("**📉 Bottom 3 Laggards (90D)**")
            for name, ret in d90_returns[-3:]:
                st.write(f"• {name}: **{ret:+.2f}%**")

    st.divider()

    # Detailed table
    with st.expander("📋 View Detailed Data Table"):
        table_data = []
        for ticker, data in etf_data.items():
            row = {
                'Ticker': ticker,
                'Sector': data['name'],
                'Price': f"${float(data['price']):.2f}",
                'YTD': f"{float(data['returns'].get('YTD', 0)):.2f}%",
                '60D': f"{float(data['returns'].get('60D', 0)):.2f}%",
                '90D': f"{float(data['returns'].get('90D', 0)):.2f}%",
            }
            for ma in MA_PERIODS:
                val = data['ma_distances'].get(f'MA{ma}', 0)
                row[f'vs MA{ma}'] = f"{float(val if val is not None else 0):+.2f}%"
            table_data.append(row)

        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.error("Could not fetch ETF data. Please check your internet connection.")

# Refresh button
st.divider()
if st.button("🔄 Refresh Data", type="primary"):
    st.cache_data.clear()
    st.rerun()

# Footer
st.markdown("---")
st.caption("Data sources: Federal Reserve Economic Data (FRED) & Yahoo Finance | Dashboard refreshes data every hour")
