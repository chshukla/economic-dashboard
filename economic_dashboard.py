import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import requests
import io

# ======================================================================
# PAGE CONFIG
# ======================================================================
st.set_page_config(page_title="Economic & Sector Dashboard", layout="wide", page_icon="\U0001f4ca")
st.title("\U0001f3e6 Economic & Sector Performance Dashboard")
st.markdown(f"*Last refreshed: {datetime.now().strftime('%B %d, %Y  %I:%M %p')}*")

# ======================================================================
# CONSTANTS
# ======================================================================
SECTOR_ETFS = {
    'XLK': 'Technology', 'XLF': 'Financials', 'XLE': 'Energy',
    'XLV': 'Healthcare', 'XLY': 'Consumer Disc.', 'XLP': 'Consumer Staples',
    'XLI': 'Industrials', 'XLB': 'Materials', 'XLRE': 'Real Estate',
    'XLU': 'Utilities', 'XLC': 'Comm. Services',
}
MA_PERIODS = [8, 21, 100, 200]
FRED_API_KEY = st.secrets.get("FRED_API_KEY", None)

# ======================================================================
# HELPERS
# ======================================================================
def safe_float(val, default=0.0):
    try:
        if val is None:
            return default
        if isinstance(val, (pd.Series, np.ndarray)):
            val = val.item() if val.size == 1 else val.iloc[0] if hasattr(val, 'iloc') else val[0]
        return float(val)
    except (TypeError, ValueError, IndexError):
        return default


def fetch_fred_series(series_id, periods=60):
    if not FRED_API_KEY:
        return None
    try:
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json&sort_order=desc&limit={periods}"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            obs = data.get("observations", [])
            rows = []
            for o in obs:
                try:
                    rows.append({"date": o["date"], "value": float(o["value"])})
                except (ValueError, KeyError):
                    continue
            if rows:
                df = pd.DataFrame(rows)
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)
                return df
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600)
def get_etf_history(ticker, days=700):
    try:
        raw = yf.download(ticker, start=datetime.now() - timedelta(days=days), end=datetime.now(), progress=False)
        if raw.empty:
            return None
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        close = raw[['Close']].copy()
        if isinstance(close, pd.DataFrame) and close.shape[1] == 1:
            close = close.iloc[:, 0]
        close = close.dropna()
        return pd.DataFrame({"date": close.index, "close": [safe_float(x) for x in close.tolist()]}).reset_index(drop=True)
    except Exception:
        return None


@st.cache_data(ttl=3600)
def get_weekly_etf(ticker, years=10):
    try:
        raw = yf.download(ticker, period=f"{years}y", interval="1wk", progress=False)
        if raw.empty:
            return None
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        close = raw[['Close']].copy()
        if isinstance(close, pd.DataFrame) and close.shape[1] == 1:
            close = close.iloc[:, 0]
        close = close.dropna()
        return pd.DataFrame({"date": close.index, "close": [safe_float(x) for x in close.tolist()]}).reset_index(drop=True)
    except Exception:
        return None


# ======================================================================
# SECTION 1: NY FED HOUSEHOLD DEBT & DELINQUENCY
# ======================================================================
def get_latest_delinquency_data():
    return {
        "report_quarter": "Q4 2025",
        "report_date": "February 10, 2026",
        "total_debt_trillions": 18.04,
        "balances": {
            "Total HH Debt": {"value": 18.04, "prev": 17.94, "yoy_change": 3.4},
            "Mortgage":       {"value": 12.61, "prev": 12.59, "yoy_change": 2.8},
            "HELOC":          {"value": 0.40,  "prev": 0.40,  "yoy_change": 2.5},
            "Auto Loans":     {"value": 1.66,  "prev": 1.64,  "yoy_change": 3.1},
            "Credit Cards":   {"value": 1.21,  "prev": 1.17,  "yoy_change": 7.3},
            "Student Loans":  {"value": 1.62,  "prev": 1.61,  "yoy_change": 0.8},
            "Other":          {"value": 0.54,  "prev": 0.53,  "yoy_change": 1.9},
        },
        "delinquency_90plus": {
            "All Debt":      {"current": 4.8, "prev_q": 4.5, "year_ago": 3.9},
            "Mortgage":      {"current": 1.5, "prev_q": 1.4, "year_ago": 1.2},
            "Home Equity":   {"current": 0.8, "prev_q": 0.8, "year_ago": 0.7},
            "Auto Loans":    {"current": 4.5, "prev_q": 4.6, "year_ago": 4.3},
            "Credit Cards":  {"current": 11.1, "prev_q": 10.8, "year_ago": 9.1},
            "Student Loans": {"current": 9.6, "prev_q": 9.3, "year_ago": 5.2},
        },
        "delinquency_30plus": {
            "All Debt":      {"current": 7.2, "prev_q": 7.0, "year_ago": 6.4},
            "Mortgage":      {"current": 2.8, "prev_q": 2.7, "year_ago": 2.4},
            "Auto Loans":    {"current": 8.0, "prev_q": 8.1, "year_ago": 7.7},
            "Credit Cards":  {"current": 14.5, "prev_q": 14.0, "year_ago": 12.8},
            "Student Loans": {"current": 12.8, "prev_q": 12.5, "year_ago": 8.0},
        },
        "new_delinquencies_billions": {
            "Mortgage": 28.3, "Auto Loans": 17.8, "Credit Cards": 32.5, "Student Loans": 18.7,
        },
    }


def render_fed_section():
    st.header("\U0001f4c9 NY Fed Household Debt & Credit Report")
    data = get_latest_delinquency_data()

    st.info(
        f"\U0001f4c5 **Report: {data['report_quarter']}** (Released {data['report_date']})  |  "
        f"Total Household Debt: **${data['total_debt_trillions']:.2f}T**  |  "
        f"Source: [NY Fed HHDC](https://www.newyorkfed.org/microeconomics/hhdc)"
    )

    st.subheader("\U0001f4b0 Debt Balances (Trillions)")
    bal = data["balances"]
    cols = st.columns(len(bal))
    for i, (name, d) in enumerate(bal.items()):
        with cols[i]:
            st.metric(label=name, value=f"${d['value']:.2f}T",
                      delta=f"{d['yoy_change']:+.1f}% YoY", delta_color="inverse")

    st.divider()

    st.subheader("\U0001f6a8 Serious Delinquency (90+ Days)")
    del90 = data["delinquency_90plus"]
    cols = st.columns(len(del90))
    for i, (name, d) in enumerate(del90.items()):
        with cols[i]:
            chg = d['current'] - d['year_ago']
            st.metric(label=name, value=f"{d['current']:.1f}%",
                      delta=f"{chg:+.1f}% vs YA", delta_color="inverse")

    cats = list(del90.keys())
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Current', x=cats, y=[del90[c]['current'] for c in cats],
                         marker_color='#ef4444', text=[f"{del90[c]['current']:.1f}%" for c in cats], textposition='outside'))
    fig.add_trace(go.Bar(name='Prev Qtr', x=cats, y=[del90[c]['prev_q'] for c in cats],
                         marker_color='#f97316', text=[f"{del90[c]['prev_q']:.1f}%" for c in cats], textposition='outside'))
    fig.add_trace(go.Bar(name='Year Ago', x=cats, y=[del90[c]['year_ago'] for c in cats],
                         marker_color='#94a3b8', text=[f"{del90[c]['year_ago']:.1f}%" for c in cats], textposition='outside'))
    fig.update_layout(barmode='group', height=400, yaxis_title='% of Balance',
                      title='90+ Day Delinquency Rates by Loan Type')
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("\u26a0\ufe0f Early Delinquency (30+ Days)")
    del30 = data["delinquency_30plus"]
    cats30 = list(del30.keys())
    fig30 = go.Figure()
    fig30.add_trace(go.Bar(name='Current 30+', x=cats30, y=[del30[c]['current'] for c in cats30],
                           marker_color='#f59e0b', text=[f"{del30[c]['current']:.1f}%" for c in cats30], textposition='outside'))
    fig30.add_trace(go.Bar(name='Year Ago', x=cats30, y=[del30[c]['year_ago'] for c in cats30],
                           marker_color='#94a3b8', text=[f"{del30[c]['year_ago']:.1f}%" for c in cats30], textposition='outside'))
    fig30.update_layout(barmode='group', height=400, yaxis_title='% of Balance',
                        title='30+ Day Delinquency Rates (Early Stage Warning)')
    st.plotly_chart(fig30, use_container_width=True)


# ======================================================================
# SECTION 2: ECONOMIC INDICATORS (FRED)
# ======================================================================
@st.cache_data(ttl=3600)
def get_economic_indicators():
    series_map = {
        "CPI (YoY %)":           "CPIAUCSL",
        "Core PCE (YoY %)":      "PCEPILFE",
        "Unemployment Rate (%)":  "UNRATE",
        "Retail Sales ($B)":      "RSAFS",
        "Initial Claims (K)":    "ICSA",
        "Continuing Claims (K)": "CCSA",
    }
    results = {}
    for label, sid in series_map.items():
        df = fetch_fred_series(sid, periods=60)
        if df is not None and len(df) > 1:
            latest = safe_float(df["value"].iloc[-1])
            prev = safe_float(df["value"].iloc[-2])
            if "YoY" in label and len(df) >= 13:
                yr_ago = safe_float(df["value"].iloc[-13])
                if yr_ago > 0:
                    latest_display = ((latest - yr_ago) / yr_ago) * 100
                    prev_display = ((prev - yr_ago) / yr_ago) * 100
                else:
                    latest_display = latest
                    prev_display = prev
            elif "Claims" in label:
                latest_display = latest / 1000.0
                prev_display = prev / 1000.0
            else:
                latest_display = latest
                prev_display = prev
            results[label] = {
                "current": latest_display,
                "previous": prev_display,
                "change": latest_display - prev_display,
                "trend": [safe_float(x) for x in df["value"].tail(24).tolist()],
                "dates": df["date"].tail(24).tolist(),
            }
    return results


def render_economic_section():
    st.header("\U0001f4c8 Key Economic Indicators (BLS / FRED)")

    if not FRED_API_KEY:
        st.warning("Add your FRED API key to Streamlit secrets to see live economic data. "
                    "Get one free at: https://fred.stlouisfed.org/docs/api/api_key.html")
        return

    with st.spinner("Fetching economic indicators from FRED..."):
        indicators = get_economic_indicators()

    if not indicators:
        st.error("Could not fetch economic data.")
        return

    cols = st.columns(len(indicators))
    for i, (label, d) in enumerate(indicators.items()):
        with cols[i]:
            fmt = f"{d['current']:.1f}" if abs(d['current']) < 1000 else f"{d['current']:,.0f}"
            delta_fmt = f"{d['change']:+.2f}"
            is_inverse = label in ["Unemployment Rate (%)", "Initial Claims (K)", "Continuing Claims (K)",
                                   "CPI (YoY %)", "Core PCE (YoY %)"]
            st.metric(label=label, value=fmt, delta=delta_fmt,
                      delta_color="inverse" if is_inverse else "normal")

    st.divider()

    sel = st.selectbox("Select indicator to chart trend:", list(indicators.keys()))
    if sel and sel in indicators:
        d = indicators[sel]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=d["dates"], y=d["trend"], mode='lines+markers',
                                 line=dict(color='#3b82f6', width=2)))
        fig.update_layout(title=f'{sel} - Recent Trend', height=350, xaxis_title='Date', yaxis_title=sel)
        st.plotly_chart(fig, use_container_width=True)


# ======================================================================
# SECTION 3: SECTOR ETF PERFORMANCE & TECHNICALS
# ======================================================================
@st.cache_data(ttl=3600)
def get_etf_data():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=300)
    results = {}
    for ticker, name in SECTOR_ETFS.items():
        try:
            raw = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if raw.empty:
                continue
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)
            cs = raw['Close']
            if isinstance(cs, pd.DataFrame):
                cs = cs.iloc[:, 0]
            cl = [safe_float(x) for x in cs.tolist()]
            ci = cs.index.tolist()
            if len(cl) < 2:
                continue
            cp = cl[-1]
            ma_vals = {}
            ma_dist = {}
            for p in MA_PERIODS:
                if len(cl) >= p:
                    m = sum(cl[-p:]) / p
                    ma_vals[f'MA{p}'] = m
                    ma_dist[f'MA{p}'] = ((cp - m) / m) * 100
            rets = {}
            year_start = datetime(end_date.year, 1, 1)
            for idx, dt in enumerate(ci):
                dn = dt.replace(tzinfo=None) if hasattr(dt, 'replace') and dt.tzinfo else dt
                if dn >= year_start:
                    sp = cl[idx]
                    if sp > 0:
                        rets['YTD'] = ((cp - sp) / sp) * 100
                    break
            if 'YTD' not in rets:
                rets['YTD'] = 0.0
            for days, lbl in [(60, '60D'), (90, '90D')]:
                if len(cl) > days and cl[-days] > 0:
                    rets[lbl] = ((cp - cl[-days]) / cl[-days]) * 100
                else:
                    rets[lbl] = 0.0
            results[ticker] = {'name': name, 'price': cp, 'ma_values': ma_vals,
                               'ma_distances': ma_dist, 'returns': rets}
        except Exception:
            continue
    return results


def render_sector_section():
    st.header("\U0001f4ca Sector ETF Performance & Technical Analysis")
    with st.spinner("Fetching live ETF data..."):
        etf_data = get_etf_data()
    if not etf_data:
        st.error("Could not fetch ETF data.")
        return

    tickers = list(etf_data.keys())
    ma_labels = [f'MA{p}' for p in MA_PERIODS]
    z = []
    for t in tickers:
        z.append([safe_float(etf_data[t]['ma_distances'].get(m, 0)) for m in ma_labels])
    fig = go.Figure(data=go.Heatmap(
        z=z, x=ma_labels,
        y=[f"{t} ({etf_data[t]['name']})" for t in tickers],
        colorscale=[[0,'rgb(220,38,38)'],[0.45,'rgb(252,165,165)'],[0.5,'rgb(255,255,255)'],
                    [0.55,'rgb(134,239,172)'],[1,'rgb(22,163,74)']],
        zmid=0, colorbar=dict(title="% from MA"),
        text=[[f"{safe_float(etf_data[t]['ma_distances'].get(m,0)):+.1f}%" for m in ma_labels] for t in tickers],
        texttemplate="%{text}", textfont={"size": 12},
    ))
    fig.update_layout(title='Sector ETF Distance from Moving Averages', height=520)
    st.plotly_chart(fig, use_container_width=True)
    st.divider()

    st.subheader("\U0001f3c6 Leading & Lagging Sectors")
    tab1, tab2, tab3 = st.tabs(["YTD", "60 Days", "90 Days"])
    for tab, period in [(tab1, 'YTD'), (tab2, '60D'), (tab3, '90D')]:
        with tab:
            items = sorted([(etf_data[t]['name'], safe_float(etf_data[t]['returns'].get(period, 0)), t)
                            for t in etf_data], key=lambda x: x[1], reverse=True)
            if items:
                ns, rs, _ = zip(*items)
                colors = ['#22c55e' if r >= 0 else '#ef4444' for r in rs]
                fig = go.Figure(go.Bar(x=list(rs), y=list(ns), orientation='h', marker_color=colors,
                                       text=[f'{r:+.2f}%' for r in rs], textposition='outside'))
                fig.update_layout(title=f'Sector Performance - {period}', height=480, xaxis_title='Return (%)')
                st.plotly_chart(fig, use_container_width=True)
                c1, c2 = st.columns(2)
                with c1:
                    st.success(f"**Top 3 Leaders ({period})**")
                    for n, r, _ in items[:3]:
                        st.write(f"- {n}: **{r:+.2f}%**")
                with c2:
                    st.error(f"**Bottom 3 Laggards ({period})**")
                    for n, r, _ in items[-3:]:
                        st.write(f"- {n}: **{r:+.2f}%**")

    st.divider()
    with st.expander("Detailed Data Table"):
        rows = []
        for t, d in etf_data.items():
            row = {'Ticker': t, 'Sector': d['name'], 'Price': f"${safe_float(d['price']):.2f}",
                   'YTD': f"{safe_float(d['returns'].get('YTD',0)):.2f}%",
                   '60D': f"{safe_float(d['returns'].get('60D',0)):.2f}%",
                   '90D': f"{safe_float(d['returns'].get('90D',0)):.2f}%"}
            for m in MA_PERIODS:
                row[f'vs MA{m}'] = f"{safe_float(d['ma_distances'].get(f'MA{m}',0)):+.2f}%"
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ======================================================================
# SECTION 4: RELATIVE PERFORMANCE VS SPY
# ======================================================================
@st.cache_data(ttl=3600)
def get_relative_performance():
    spy = get_etf_history("SPY", days=400)
    if spy is None:
        return None
    results = {}
    for ticker, name in SECTOR_ETFS.items():
        sector = get_etf_history(ticker, days=400)
        if sector is None:
            continue
        merged = pd.merge(spy, sector, on="date", suffixes=("_spy", "_sector"))
        if len(merged) < 20:
            continue
        merged["relative"] = merged["close_sector"] / merged["close_spy"]
        base = merged["relative"].iloc[0]
        if base > 0:
            merged["rel_indexed"] = (merged["relative"] / base - 1) * 100
        else:
            merged["rel_indexed"] = 0
        results[ticker] = {"name": name, "dates": merged["date"].tolist(),
                           "rel_indexed": merged["rel_indexed"].tolist()}
    return results


def render_relative_section():
    st.header("\U0001f4c8 Sector vs SPY Relative Performance")
    with st.spinner("Calculating relative performance..."):
        rel_data = get_relative_performance()
    if not rel_data:
        st.error("Could not compute relative performance.")
        return

    fig = go.Figure()
    for ticker, d in rel_data.items():
        vals = [safe_float(v) for v in d["rel_indexed"]]
        latest = vals[-1] if vals else 0
        color = '#22c55e' if latest >= 0 else '#ef4444'
        fig.add_trace(go.Scatter(x=d["dates"], y=vals, mode='lines',
                                 name=f"{ticker} ({d['name']})", line=dict(width=2)))
    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="SPY Baseline")
    fig.update_layout(title='Sector Relative Strength vs SPY (indexed to 0)',
                      height=550, yaxis_title='Relative Perf (%)', xaxis_title='Date',
                      legend=dict(orientation="h", yanchor="bottom", y=-0.3))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Current Relative Strength Ranking")
    ranking = []
    for ticker, d in rel_data.items():
        vals = [safe_float(v) for v in d["rel_indexed"]]
        latest = vals[-1] if vals else 0
        ranking.append((ticker, d["name"], latest))
    ranking.sort(key=lambda x: x[2], reverse=True)
    c1, c2 = st.columns(2)
    with c1:
        st.success("**Outperforming SPY**")
        for t, n, v in ranking:
            if v >= 0:
                st.write(f"- {t} ({n}): **{v:+.1f}%**")
    with c2:
        st.error("**Underperforming SPY**")
        for t, n, v in ranking:
            if v < 0:
                st.write(f"- {t} ({n}): **{v:+.1f}%**")


# ======================================================================
# SECTION 5: BACKTESTS
# ======================================================================
def run_ma_crossover_backtest(weekly_df):
    if weekly_df is None or len(weekly_df) < 30:
        return None
    df = weekly_df.copy()
    df["ma8"] = df["close"].rolling(8).mean()
    df["ma21"] = df["close"].rolling(21).mean()
    df = df.dropna().reset_index(drop=True)
    signals = []
    for i in range(1, len(df)):
        prev_above = df["ma8"].iloc[i-1] >= df["ma21"].iloc[i-1]
        curr_below = df["ma8"].iloc[i] < df["ma21"].iloc[i]
        if prev_above and curr_below:
            entry_price = safe_float(df["close"].iloc[i])
            entry_date = df["date"].iloc[i]
            fwd = {}
            for days, label in [(30, "30D"), (60, "60D"), (90, "90D"), (180, "180D"), (365, "1Y")]:
                weeks_ahead = days // 7
                fwd_idx = i + weeks_ahead
                if fwd_idx < len(df):
                    fwd_price = safe_float(df["close"].iloc[fwd_idx])
                    if entry_price > 0:
                        fwd[label] = ((fwd_price - entry_price) / entry_price) * 100
                    else:
                        fwd[label] = 0.0
            # Maximum Drawdown: worst trough within 1Y forward window (52 weeks)
            max_dd = 0.0
            if entry_price > 0:
                end_idx = min(i + 52, len(df))
                fwd_prices = [safe_float(df["close"].iloc[j]) for j in range(i, end_idx)]
                if fwd_prices:
                    min_price = min(fwd_prices)
                    max_dd = ((min_price - entry_price) / entry_price) * 100
            if fwd:
                signals.append({"date": entry_date, "price": entry_price, **fwd, "Max Drawdown (%)": max_dd})
    return signals


def run_below_200ma_backtest(daily_df):
    if daily_df is None or len(daily_df) < 220:
        return None
    df = daily_df.copy()
    df["ma200"] = df["close"].rolling(200).mean()
    df = df.dropna().reset_index(drop=True)
    signals = []
    for i in range(1, len(df)):
        was_above = df["close"].iloc[i-1] >= df["ma200"].iloc[i-1]
        now_below = df["close"].iloc[i] < df["ma200"].iloc[i]
        if was_above and now_below:
            entry_price = safe_float(df["close"].iloc[i])
            entry_date = df["date"].iloc[i]
            fwd = {}
            for days, label in [(30, "30D"), (60, "60D"), (90, "90D"), (180, "180D"), (365, "1Y")]:
                fwd_idx = i + days
                if fwd_idx < len(df):
                    fwd_price = safe_float(df["close"].iloc[fwd_idx])
                    if entry_price > 0:
                        fwd[label] = ((fwd_price - entry_price) / entry_price) * 100
                    else:
                        fwd[label] = 0.0
            # Maximum Drawdown: worst trough within 1Y forward window (365 days)
            max_dd = 0.0
            if entry_price > 0:
                end_idx = min(i + 365, len(df))
                fwd_prices = [safe_float(df["close"].iloc[j]) for j in range(i, end_idx)]
                if fwd_prices:
                    min_price = min(fwd_prices)
                    max_dd = ((min_price - entry_price) / entry_price) * 100
            if fwd:
                signals.append({"date": entry_date, "price": entry_price, **fwd, "Max Drawdown (%)": max_dd})
    return signals


def render_backtest_section():
    st.header("\U0001f52c Backtesting Lab")

    bt_tab1, bt_tab2 = st.tabs(["8W/21W MA Crossover", "Below 200-Day MA"])

    # --- Backtest 1: 8-week below 21-week MA ---
    with bt_tab1:
        st.subheader("When 8-Week MA Crosses Below 21-Week MA")
        st.markdown("*What happens to forward returns when the short-term weekly trend breaks down?*")

        selected = st.selectbox("Select ETF for MA Crossover Backtest:",
                                ["SPY"] + list(SECTOR_ETFS.keys()),
                                key="bt1_select")
        with st.spinner(f"Running backtest on {selected}..."):
            weekly = get_weekly_etf(selected, years=10)
            signals = run_ma_crossover_backtest(weekly)

        if signals and len(signals) > 0:
            df_sig = pd.DataFrame(signals)
            st.write(f"**Found {len(df_sig)} crossover signals in the past 10 years**")

            periods = ["30D", "60D", "90D", "180D", "1Y"]
            avail = [p for p in periods if p in df_sig.columns]
            if avail:
                avg_row = {p: safe_float(df_sig[p].mean()) for p in avail}
                med_row = {p: safe_float(df_sig[p].median()) for p in avail}
                win_row = {p: safe_float((df_sig[p] > 0).mean() * 100) for p in avail}
                avg_dd = safe_float(df_sig["Max Drawdown (%)"].mean()) if "Max Drawdown (%)" in df_sig.columns else 0.0
                med_dd = safe_float(df_sig["Max Drawdown (%)"].median()) if "Max Drawdown (%)" in df_sig.columns else 0.0
                worst_dd = safe_float(df_sig["Max Drawdown (%)"].min()) if "Max Drawdown (%)" in df_sig.columns else 0.0

                summary = pd.DataFrame([
                    {"Metric": "Avg Return (%)", **{p: f"{avg_row[p]:+.2f}" for p in avail}, "Max Drawdown (%)": f"{avg_dd:.2f}"},
                    {"Metric": "Median Return (%)", **{p: f"{med_row[p]:+.2f}" for p in avail}, "Max Drawdown (%)": f"{med_dd:.2f}"},
                    {"Metric": "Win Rate (%)", **{p: f"{win_row[p]:.0f}%" for p in avail}, "Max Drawdown (%)": f"Worst: {worst_dd:.2f}%"},
                ])
                st.dataframe(summary, use_container_width=True, hide_index=True)

                # Max Drawdown metric
                col_dd1, col_dd2, col_dd3 = st.columns(3)
                with col_dd1:
                    st.metric("Avg Max Drawdown", f"{avg_dd:.2f}%", delta=None)
                with col_dd2:
                    st.metric("Median Max Drawdown", f"{med_dd:.2f}%", delta=None)
                with col_dd3:
                    st.metric("Worst Drawdown Seen", f"{worst_dd:.2f}%", delta=None)

                fig = go.Figure()
                fig.add_trace(go.Bar(name='Avg Return', x=avail, y=[avg_row[p] for p in avail],
                                     marker_color=['#22c55e' if avg_row[p] >= 0 else '#ef4444' for p in avail],
                                     text=[f"{avg_row[p]:+.1f}%" for p in avail], textposition='outside'))
                fig.update_layout(title=f'{selected}: Avg Forward Returns After 8W < 21W MA Cross',
                                  height=400, yaxis_title='Return (%)')
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("View All Signals"):
                    display_cols = ["date", "price"] + avail + (["Max Drawdown (%)"] if "Max Drawdown (%)" in df_sig.columns else [])
                    st.dataframe(df_sig[display_cols].round(2), use_container_width=True, hide_index=True)
        else:
            st.info(f"No crossover signals found for {selected} in the past 10 years.")

    # --- Backtest 2: Below 200-Day MA ---
    with bt_tab2:
        st.subheader("When Price Drops Below 200-Day MA")
        st.markdown("*Historical forward returns when a sector breaks below its long-term trend.*")

        selected2 = st.selectbox("Select ETF for 200-MA Backtest:",
                                 ["SPY"] + list(SECTOR_ETFS.keys()),
                                 key="bt2_select")
        with st.spinner(f"Running backtest on {selected2}..."):
            daily = get_etf_history(selected2, days=700)
            signals2 = run_below_200ma_backtest(daily)

        if signals2 and len(signals2) > 0:
            df_sig2 = pd.DataFrame(signals2)
            st.write(f"**Found {len(df_sig2)} signals (price crossing below 200-MA)**")

            periods2 = ["30D", "60D", "90D", "180D", "1Y"]
            avail2 = [p for p in periods2 if p in df_sig2.columns]
            if avail2:
                avg2 = {p: safe_float(df_sig2[p].mean()) for p in avail2}
                med2 = {p: safe_float(df_sig2[p].median()) for p in avail2}
                win2 = {p: safe_float((df_sig2[p] > 0).mean() * 100) for p in avail2}
                avg_dd2 = safe_float(df_sig2["Max Drawdown (%)"].mean()) if "Max Drawdown (%)" in df_sig2.columns else 0.0
                med_dd2 = safe_float(df_sig2["Max Drawdown (%)"].median()) if "Max Drawdown (%)" in df_sig2.columns else 0.0
                worst_dd2 = safe_float(df_sig2["Max Drawdown (%)"].min()) if "Max Drawdown (%)" in df_sig2.columns else 0.0

                summary2 = pd.DataFrame([
                    {"Metric": "Avg Return (%)", **{p: f"{avg2[p]:+.2f}" for p in avail2}, "Max Drawdown (%)": f"{avg_dd2:.2f}"},
                    {"Metric": "Median Return (%)", **{p: f"{med2[p]:+.2f}" for p in avail2}, "Max Drawdown (%)": f"{med_dd2:.2f}"},
                    {"Metric": "Win Rate (%)", **{p: f"{win2[p]:.0f}%" for p in avail2}, "Max Drawdown (%)": f"Worst: {worst_dd2:.2f}%"},
                ])
                st.dataframe(summary2, use_container_width=True, hide_index=True)

                # Max Drawdown metric
                col_dd4, col_dd5, col_dd6 = st.columns(3)
                with col_dd4:
                    st.metric("Avg Max Drawdown", f"{avg_dd2:.2f}%", delta=None)
                with col_dd5:
                    st.metric("Median Max Drawdown", f"{med_dd2:.2f}%", delta=None)
                with col_dd6:
                    st.metric("Worst Drawdown Seen", f"{worst_dd2:.2f}%", delta=None)

                fig2 = go.Figure()
                fig2.add_trace(go.Bar(name='Avg Return', x=avail2, y=[avg2[p] for p in avail2],
                                      marker_color=['#22c55e' if avg2[p] >= 0 else '#ef4444' for p in avail2],
                                      text=[f"{avg2[p]:+.1f}%" for p in avail2], textposition='outside'))
                fig2.update_layout(title=f'{selected2}: Avg Forward Returns After Breaking Below 200-MA',
                                   height=400, yaxis_title='Return (%)')
                st.plotly_chart(fig2, use_container_width=True)

                with st.expander("View All Signals"):
                    display_cols2 = ["date", "price"] + avail2 + (["Max Drawdown (%)"] if "Max Drawdown (%)" in df_sig2.columns else [])
                    st.dataframe(df_sig2[display_cols2].round(2), use_container_width=True, hide_index=True)
        else:
            st.info(f"Not enough data for {selected2} (need ~2 years of daily data).")


# ======================================================================
# MAIN APP
# ======================================================================
render_fed_section()
st.divider()
render_economic_section()
st.divider()
render_sector_section()
st.divider()
render_relative_section()
st.divider()
render_backtest_section()

st.divider()
if st.button("Refresh All Data", type="primary"):
    st.cache_data.clear()
    st.rerun()

st.markdown("---")
st.caption(
    "Data: [NY Fed HHDC](https://www.newyorkfed.org/microeconomics/hhdc) | "
    "[FRED](https://fred.stlouisfed.org) | Yahoo Finance"
)
