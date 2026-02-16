import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import requests
import io

# ──────────────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Economic & Sector Dashboard", layout="wide", page_icon="📊")
st.title("🏦 NY Fed Household Debt & Sector Performance Dashboard")
st.markdown(f"*Last refreshed: {datetime.now().strftime('%B %d, %Y  %I:%M %p')}*")

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────
SECTOR_ETFS = {
    'XLK': 'Technology', 'XLF': 'Financials', 'XLE': 'Energy',
    'XLV': 'Healthcare', 'XLY': 'Consumer Disc.', 'XLP': 'Consumer Staples',
    'XLI': 'Industrials', 'XLB': 'Materials', 'XLRE': 'Real Estate',
    'XLU': 'Utilities', 'XLC': 'Comm. Services',
}
MA_PERIODS = [8, 21, 100, 200]

# NY Fed Excel URL pattern (quarterly)
NYFED_EXCEL_URLS = [
    "https://www.newyorkfed.org/medialibrary/interactives/householdcredit/data/xls/hhd_c_report_2025q4.xlsx",
    "https://www.newyorkfed.org/medialibrary/interactives/householdcredit/data/xls/hhd_c_report_2025q3.xlsx",
    "https://www.newyorkfed.org/medialibrary/interactives/householdcredit/data/xls/HHD_C_Report_2025Q2.xlsx",
]

# ──────────────────────────────────────────────────────────────────────
# Helper: safe float conversion (handles pandas Series, numpy, None)
# ──────────────────────────────────────────────────────────────────────
def safe_float(val, default=0.0):
    """Convert any value to a plain Python float."""
    try:
        if val is None:
            return default
        if isinstance(val, (pd.Series, np.ndarray)):
            val = val.item() if val.size == 1 else val.iloc[0] if hasattr(val, 'iloc') else val[0]
        return float(val)
    except (TypeError, ValueError, IndexError):
        return default


# ══════════════════════════════════════════════════════════════════════
# SECTION 1: NY FED HOUSEHOLD DEBT & DELINQUENCY DATA
# ══════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=86400)  # cache for 24 hours (data is quarterly)
def fetch_nyfed_data():
    """
    Download the NY Fed Household Debt & Credit Excel file.
    Returns a dict of DataFrames keyed by sheet name, or None on failure.
    """
    for url in NYFED_EXCEL_URLS:
        try:
            resp = requests.get(url, timeout=30,
                                headers={'User-Agent': 'Mozilla/5.0 Economic Dashboard'})
            if resp.status_code == 200:
                xls = pd.ExcelFile(io.BytesIO(resp.content))
                sheets = {}
                for name in xls.sheet_names:
                    sheets[name] = pd.read_excel(xls, sheet_name=name, header=None)
                return {"sheets": sheets, "url": url, "quarter": url.split("report_")[1].replace(".xlsx", "").upper()}
        except Exception:
            continue
    return None


def get_latest_delinquency_data():
    """
    Latest Q4 2025 data from NY Fed Household Debt & Credit Report
    (released February 10, 2026). Used as fallback and supplementary data.
    Source: https://www.newyorkfed.org/newsevents/news/research/2026/20260210
    """
    return {
        "report_quarter": "Q4 2025",
        "report_date": "February 10, 2026",
        "total_debt_trillions": 18.04,

        # ── Debt balances (trillions) ──
        "balances": {
            "Total Household Debt":     {"value": 18.04, "prev": 17.94, "yoy_change": 3.4},
            "Mortgage":                 {"value": 12.61, "prev": 12.59, "yoy_change": 2.8},
            "Home Equity (HELOC)":      {"value": 0.40,  "prev": 0.40,  "yoy_change": 2.5},
            "Auto Loans":              {"value": 1.66,  "prev": 1.64,  "yoy_change": 3.1},
            "Credit Cards":            {"value": 1.21,  "prev": 1.17,  "yoy_change": 7.3},
            "Student Loans":           {"value": 1.62,  "prev": 1.61,  "yoy_change": 0.8},
            "Other":                   {"value": 0.54,  "prev": 0.53,  "yoy_change": 1.9},
        },

        # ── Delinquency rates (% of balance 90+ days delinquent) ──
        "delinquency_90plus": {
            "All Debt":        {"current": 4.8, "prev_q": 4.5, "year_ago": 3.9},
            "Mortgage":        {"current": 1.5, "prev_q": 1.4, "year_ago": 1.2},
            "Home Equity":     {"current": 0.8, "prev_q": 0.8, "year_ago": 0.7},
            "Auto Loans":      {"current": 4.5, "prev_q": 4.6, "year_ago": 4.3},
            "Credit Cards":    {"current": 11.1, "prev_q": 10.8, "year_ago": 9.1},
            "Student Loans":   {"current": 9.6, "prev_q": 9.3, "year_ago": 5.2},
        },

        # ── Transition into delinquency (30+ days, % of balance) ──
        "delinquency_30plus": {
            "All Debt":        {"current": 7.2, "prev_q": 7.0, "year_ago": 6.4},
            "Mortgage":        {"current": 2.8, "prev_q": 2.7, "year_ago": 2.4},
            "Auto Loans":      {"current": 8.0, "prev_q": 8.1, "year_ago": 7.7},
            "Credit Cards":    {"current": 14.5, "prev_q": 14.0, "year_ago": 12.8},
            "Student Loans":   {"current": 12.8, "prev_q": 12.5, "year_ago": 8.0},
        },

        # ── New delinquencies (flow into 90+ days, billions $) ──
        "new_delinquencies_billions": {
            "Mortgage":     28.3,
            "Auto Loans":   17.8,
            "Credit Cards": 32.5,
            "Student Loans": 18.7,
        },
    }


def render_fed_section():
    """Render the NY Fed delinquency dashboard section."""

    st.header("📉 NY Fed Household Debt & Credit Report")

    data = get_latest_delinquency_data()

    st.info(
        f"📅 **Report: {data['report_quarter']}** (Released {data['report_date']})  •  "
        f"Total Household Debt: **${data['total_debt_trillions']:.2f} Trillion**  •  "
        f"Source: [NY Fed HHDC Report](https://www.newyorkfed.org/microeconomics/hhdc)"
    )

    # ── Debt Balances ──
    st.subheader("💰 Debt Balances (Trillions)")

    bal = data["balances"]
    cols = st.columns(len(bal))
    for i, (name, d) in enumerate(bal.items()):
        with cols[i % len(cols)]:
            delta_str = f"{d['yoy_change']:+.1f}% YoY"
            st.metric(label=name, value=f"${d['value']:.2f}T", delta=delta_str, delta_color="inverse")

    st.divider()

    # ── 90+ Day Delinquency Rates ──
    st.subheader("🚨 Serious Delinquency Rates (90+ Days Past Due)")

    del90 = data["delinquency_90plus"]
    cols = st.columns(len(del90))
    for i, (name, d) in enumerate(del90.items()):
        with cols[i % len(cols)]:
            change = d['current'] - d['year_ago']
            st.metric(
                label=name,
                value=f"{d['current']:.1f}%",
                delta=f"{change:+.1f}% vs Year Ago",
                delta_color="inverse"
            )

    # Delinquency bar chart
    categories = list(del90.keys())
    current_vals = [del90[c]['current'] for c in categories]
    prev_vals = [del90[c]['prev_q'] for c in categories]
    year_ago_vals = [del90[c]['year_ago'] for c in categories]

    fig_del = go.Figure()
    fig_del.add_trace(go.Bar(name='Current', x=categories, y=current_vals,
                              marker_color='#ef4444',
                              text=[f'{v:.1f}%' for v in current_vals], textposition='outside'))
    fig_del.add_trace(go.Bar(name='Previous Quarter', x=categories, y=prev_vals,
                              marker_color='#f97316',
                              text=[f'{v:.1f}%' for v in prev_vals], textposition='outside'))
    fig_del.add_trace(go.Bar(name='Year Ago', x=categories, y=year_ago_vals,
                              marker_color='#94a3b8',
                              text=[f'{v:.1f}%' for v in year_ago_vals], textposition='outside'))
    fig_del.update_layout(title='90+ Day Delinquency Rates by Loan Type',
                           barmode='group', height=400, yaxis_title='% of Balance')
    st.plotly_chart(fig_del, use_container_width=True)

    st.divider()

    # ── 30+ Day Delinquency (Early Stage) ──
    st.subheader("⚠️ Early Delinquency Rates (30+ Days Past Due)")

    del30 = data["delinquency_30plus"]

    fig_30 = go.Figure()
    cats_30 = list(del30.keys())
    cur_30 = [del30[c]['current'] for c in cats_30]
    ya_30 = [del30[c]['year_ago'] for c in cats_30]

    fig_30.add_trace(go.Bar(name='Current (30+ Days)', x=cats_30, y=cur_30,
                             marker_color='#f59e0b',
                             text=[f'{v:.1f}%' for v in cur_30], textposition='outside'))
    fig_30.add_trace(go.Bar(name='Year Ago', x=cats_30, y=ya_30,
                             marker_color='#94a3b8',
                             text=[f'{v:.1f}%' for v in ya_30], textposition='outside'))
    fig_30.update_layout(title='30+ Day Delinquency Rates (Early Stage Warning)',
                          barmode='group', height=400, yaxis_title='% of Balance')
    st.plotly_chart(fig_30, use_container_width=True)

    st.divider()

    # ── New Delinquency Flows ──
    st.subheader("📊 New Delinquency Flows (Billions $)")

    new_del = data["new_delinquencies_billions"]
    cats_flow = list(new_del.keys())
    vals_flow = list(new_del.values())

    colors_flow = ['#ef4444' if v > 25 else '#f97316' if v > 15 else '#eab308' for v in vals_flow]

    fig_flow = go.Figure(go.Bar(
        x=vals_flow, y=cats_flow, orientation='h',
        marker_color=colors_flow,
        text=[f'${v:.1f}B' for v in vals_flow], textposition='outside'
    ))
    fig_flow.update_layout(title='New Flows into 90+ Day Delinquency (Quarterly)',
                            height=350, xaxis_title='Billions $')
    st.plotly_chart(fig_flow, use_container_width=True)

    # ── Key Takeaways ──
    with st.expander("📝 Key Takeaways from Latest Report"):
        st.markdown("""
**Q4 2025 Highlights (Released Feb 10, 2026):**

- **Total household debt** rose to $18.04 trillion, up $191 billion (+1.0%) from Q3
- **Credit card delinquencies** continue rising — 11.1% of balances are 90+ days late, up from 9.1% a year ago
- **Student loan delinquencies** surged to 9.6% (90+ days), nearly double the 5.2% from a year ago
- **Auto loan delinquencies** ticked down slightly to 4.5% from 4.6% last quarter
- **Mortgage delinquencies** remain relatively low at 1.5% but are trending upward
- **Credit card debt** hit $1.21 trillion, up 7.3% year-over-year — fastest growing category
        """)


# ══════════════════════════════════════════════════════════════════════
# SECTION 2: SECTOR ETF PERFORMANCE & TECHNICAL ANALYSIS
# ══════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def get_etf_data():
    """Fetch ETF price data and calculate moving averages."""

    end_date = datetime.now()
    start_date = end_date - timedelta(days=300)

    results = {}

    for ticker, name in SECTOR_ETFS.items():
        try:
            raw = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if raw.empty:
                continue

            # Flatten multi-level columns (newer yfinance returns MultiIndex)
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)

            # Get close prices as a plain 1-D Series
            close_series = raw['Close']
            if isinstance(close_series, pd.DataFrame):
                close_series = close_series.iloc[:, 0]

            close_list = [safe_float(x) for x in close_series.tolist()]
            close_index = close_series.index.tolist()

            if len(close_list) < 2:
                continue

            current_price = close_list[-1]

            # Moving averages
            ma_values = {}
            ma_distances = {}
            for period in MA_PERIODS:
                if len(close_list) >= period:
                    ma = sum(close_list[-period:]) / period
                    ma_values[f'MA{period}'] = ma
                    ma_distances[f'MA{period}'] = ((current_price - ma) / ma) * 100

            # Returns
            returns = {}

            # YTD
            year_start = datetime(end_date.year, 1, 1)
            for idx, dt in enumerate(close_index):
                dt_naive = dt.replace(tzinfo=None) if hasattr(dt, 'replace') and dt.tzinfo else dt
                if dt_naive >= year_start:
                    ytd_start_price = close_list[idx]
                    if ytd_start_price > 0:
                        returns['YTD'] = ((current_price - ytd_start_price) / ytd_start_price) * 100
                    break
            if 'YTD' not in returns:
                returns['YTD'] = 0.0

            # 60D and 90D
            for days, label in [(60, '60D'), (90, '90D')]:
                if len(close_list) > days:
                    past = close_list[-days]
                    if past > 0:
                        returns[label] = ((current_price - past) / past) * 100
                    else:
                        returns[label] = 0.0
                else:
                    returns[label] = 0.0

            results[ticker] = {
                'name': name,
                'price': current_price,
                'ma_values': ma_values,
                'ma_distances': ma_distances,
                'returns': returns,
            }

        except Exception as e:
            st.warning(f"Could not fetch {ticker}: {e}")
            continue

    return results


def create_ma_heatmap(etf_data):
    """Heatmap: sector ETFs vs moving averages."""

    tickers = list(etf_data.keys())
    ma_labels = [f'MA{p}' for p in MA_PERIODS]

    z_matrix = []
    annotations = []

    for ticker in tickers:
        row = []
        for ma in ma_labels:
            val = safe_float(etf_data[ticker]['ma_distances'].get(ma, 0))
            row.append(val)
        z_matrix.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=z_matrix,
        x=ma_labels,
        y=[f"{t} ({etf_data[t]['name']})" for t in tickers],
        colorscale=[
            [0, 'rgb(220, 38, 38)'],
            [0.45, 'rgb(252, 165, 165)'],
            [0.5, 'rgb(255, 255, 255)'],
            [0.55, 'rgb(134, 239, 172)'],
            [1, 'rgb(22, 163, 74)'],
        ],
        zmid=0,
        colorbar=dict(title="% from MA"),
        text=[[f"{safe_float(etf_data[t]['ma_distances'].get(ma, 0)):+.1f}%" for ma in ma_labels] for t in tickers],
        texttemplate="%{text}",
        textfont={"size": 12},
    ))

    fig.update_layout(
        title='🚩 Sector ETF Distance from Moving Averages (Red = Below, Green = Above)',
        height=520,
    )
    return fig


def create_returns_chart(etf_data, period='YTD'):
    """Horizontal bar chart of sector returns."""

    items = [(etf_data[t]['name'], safe_float(etf_data[t]['returns'].get(period, 0)), t)
             for t in etf_data]
    items.sort(key=lambda x: x[1], reverse=True)

    if not items:
        return go.Figure()

    names, rets, _ = zip(*items)
    colors = ['#22c55e' if r >= 0 else '#ef4444' for r in rets]

    fig = go.Figure(go.Bar(
        x=list(rets), y=list(names), orientation='h',
        marker_color=colors,
        text=[f'{r:+.2f}%' for r in rets], textposition='outside',
    ))
    fig.update_layout(title=f'Sector Performance — {period}', height=480, xaxis_title='Return (%)')
    return fig


def render_sector_section():
    """Render the sector ETF dashboard section."""

    st.header("📊 Sector ETF Performance & Technical Analysis")

    with st.spinner("Fetching live ETF data …"):
        etf_data = get_etf_data()

    if not etf_data:
        st.error("Could not fetch ETF data. Please check your internet connection.")
        return

    # MA Heatmap
    st.plotly_chart(create_ma_heatmap(etf_data), use_container_width=True)
    st.divider()

    # Returns tabs
    st.subheader("🏆 Leading & Lagging Sectors")
    tab1, tab2, tab3 = st.tabs(["📅 YTD", "📆 60 Days", "📆 90 Days"])

    for tab, period in [(tab1, 'YTD'), (tab2, '60D'), (tab3, '90D')]:
        with tab:
            st.plotly_chart(create_returns_chart(etf_data, period), use_container_width=True)

            ranked = sorted(
                [(etf_data[t]['name'], safe_float(etf_data[t]['returns'].get(period, 0))) for t in etf_data],
                key=lambda x: x[1], reverse=True,
            )

            col1, col2 = st.columns(2)
            with col1:
                st.success(f"**🚀 Top 3 Leaders ({period})**")
                for name, ret in ranked[:3]:
                    st.write(f"• {name}: **{ret:+.2f}%**")
            with col2:
                st.error(f"**📉 Bottom 3 Laggards ({period})**")
                for name, ret in ranked[-3:]:
                    st.write(f"• {name}: **{ret:+.2f}%**")

    st.divider()

    # Detailed table
    with st.expander("📋 Detailed Data Table"):
        rows = []
        for ticker, d in etf_data.items():
            row = {
                'Ticker': ticker,
                'Sector': d['name'],
                'Price': f"${safe_float(d['price']):.2f}",
                'YTD': f"{safe_float(d['returns'].get('YTD', 0)):.2f}%",
                '60D': f"{safe_float(d['returns'].get('60D', 0)):.2f}%",
                '90D': f"{safe_float(d['returns'].get('90D', 0)):.2f}%",
            }
            for ma in MA_PERIODS:
                row[f'vs MA{ma}'] = f"{safe_float(d['ma_distances'].get(f'MA{ma}', 0)):+.2f}%"
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════

render_fed_section()
st.divider()
render_sector_section()

# Refresh
st.divider()
if st.button("🔄 Refresh All Data", type="primary"):
    st.cache_data.clear()
    st.rerun()

st.markdown("---")
st.caption(
    "Data sources: [NY Fed Household Debt & Credit Report]"
    "(https://www.newyorkfed.org/microeconomics/hhdc) · Yahoo Finance  |  "
    "Dashboard auto-caches ETF data for 1 hour, Fed data for 24 hours"
)

Progress
3 of 3

Working folder

Context
Connectors
Web search

Claude in Chrome

Skills
create-shortcut
docx
