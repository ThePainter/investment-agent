import os

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

API_URL = os.getenv("API_URL", "http://localhost:8000/api")

st.set_page_config(page_title="Investment Agent", layout="wide")
st.markdown(
    """
    <style>
    .stApp {background: #f8fafc;}
    .block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
    h1, h2, h3 {letter-spacing: 0; color: #0f172a;}
    [data-testid="stMetric"] {
        background: linear-gradient(180deg, #ffffff 0%, #f4f7fb 100%);
        border: 1px solid #dbe3ee;
        border-radius: 8px;
        padding: 14px 16px;
        color: #0f172a;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
    }
    [data-testid="stMetricLabel"] {color: #64748b;}
    [data-testid="stMetricValue"] {font-size: 1.45rem; color: #0f172a;}
    [data-testid="stMetricDelta"] {color: #2563eb;}
    [data-testid="stDataFrame"] {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .stTabs [data-baseweb="tab-list"] {gap: 0.25rem;}
    .stTabs [data-baseweb="tab"] {
        background: #eef2f7;
        border-radius: 8px 8px 0 0;
        padding: 0.45rem 0.8rem;
    }
    .stTabs [aria-selected="true"] {
        background: #ffffff;
        color: #0f172a;
        border-bottom: 2px solid #0f766e;
    }
    .signal-note {
        color: #64748b;
        font-size: 0.92rem;
        margin-top: -0.5rem;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Investment Agent")
st.markdown(
    '<div class="signal-note">Decision-support signals only. Outputs are not guaranteed financial advice and require independent judgment.</div>',
    unsafe_allow_html=True,
)


@st.cache_data(ttl=240)
def load_analysis() -> list[dict]:
    response = requests.get(f"{API_URL}/analysis", timeout=120)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=240)
def load_detail(ticker: str) -> dict:
    response = requests.get(f"{API_URL}/analysis/{ticker}", timeout=120)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=240)
def load_watchlist() -> list[dict]:
    response = requests.get(f"{API_URL}/watchlist", timeout=30)
    response.raise_for_status()
    return response.json()


def add_watchlist_item(payload: dict) -> None:
    response = requests.post(f"{API_URL}/watchlist", json=payload, timeout=30)
    response.raise_for_status()


def remove_watchlist_item(ticker: str) -> None:
    response = requests.delete(f"{API_URL}/watchlist/{ticker}", timeout=30)
    response.raise_for_status()


def import_tradingview_symbols(payload: dict) -> int:
    response = requests.post(f"{API_URL}/watchlist/import/tradingview", json=payload, timeout=30)
    response.raise_for_status()
    return len(response.json())


def clear_data() -> None:
    st.cache_data.clear()


def rerun_app() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def format_signal_board(items: list[dict]) -> pd.DataFrame:
    rows = []
    for item in items:
        portfolio = item.get("portfolio") or {}
        rows.append(
            {
                "Ticker": item["ticker"],
                "Company": item["company_name"],
                "Price": item["current_price"],
                "Day %": item.get("daily_change_pct"),
                "Signal": item["recommendation"],
                "Score": item["overall_score"],
                "Risk": item["risk_level"],
                "News": item.get("news_sentiment"),
                "P/L %": portfolio.get("unrealized_gain_loss_pct"),
            }
        )
    return pd.DataFrame(rows)


def format_levels(item: dict) -> pd.DataFrame:
    portfolio = item.get("portfolio") or {}
    return pd.DataFrame(
        [
            {"Metric": "Entry zone", "Value": item.get("entry_zone")},
            {"Metric": "Stop-loss", "Value": item.get("stop_loss")},
            {"Metric": "Take-profit 1", "Value": item.get("take_profit_1")},
            {"Metric": "Take-profit 2", "Value": item.get("take_profit_2")},
            {"Metric": "Upside %", "Value": item.get("upside_pct")},
            {"Metric": "Downside %", "Value": item.get("downside_pct")},
            {"Metric": "Risk/reward", "Value": item.get("risk_reward_ratio")},
            {"Metric": "Position P/L %", "Value": portfolio.get("unrealized_gain_loss_pct")},
            {"Metric": "Position P/L amount", "Value": portfolio.get("unrealized_gain_loss")},
        ]
    )


def style_signal_board(df: pd.DataFrame):
    def signal_color(value: str) -> str:
        colors = {
            "STRONG BUY": "background-color: #ccfbf1; color: #115e59",
            "BUY": "background-color: #dcfce7; color: #166534",
            "WATCH": "background-color: #fef3c7; color: #92400e",
            "HOLD": "background-color: #e2e8f0; color: #334155",
            "REDUCE": "background-color: #ffe4e6; color: #9f1239",
            "SELL": "background-color: #fee2e2; color: #991b1b",
            "AVOID": "background-color: #f1f5f9; color: #7f1d1d",
        }
        return f"{colors.get(value, '')}; font-weight: 650"

    def risk_color(value: str) -> str:
        colors = {
            "LOW": "background-color: #ecfdf5; color: #047857",
            "MEDIUM": "background-color: #fffbeb; color: #b45309",
            "HIGH": "background-color: #fff1f2; color: #be123c",
        }
        return f"{colors.get(value, '')}; font-weight: 650"

    return (
        df.style.format(
            {
                "Price": "{:,.2f}",
                "Day %": "{:+.2f}%",
                "P/L %": "{:+.2f}%",
            },
            na_rep="-",
        )
        .map(signal_color, subset=["Signal"])
        .map(risk_color, subset=["Risk"])
        .bar(subset=["Score"], color="#99f6e4", vmin=0, vmax=100)
    )


def chart(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.52, 0.16, 0.16, 0.16],
    )
    fig.add_trace(
        go.Candlestick(
            x=df["timestamp"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
        ),
        row=1,
        col=1,
    )
    for col in ["ema_9", "ema_20", "ema_50", "ema_200", "bollinger_upper", "bollinger_lower"]:
        if col in df:
            fig.add_trace(go.Scatter(x=df["timestamp"], y=df[col], name=col), row=1, col=1)
    fig.add_trace(go.Bar(x=df["timestamp"], y=df["volume"], name="Volume"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["rsi_14"], name="RSI 14"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["macd"], name="MACD"), row=4, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["macd_signal"], name="MACD signal"), row=4, col=1)
    fig.add_trace(go.Bar(x=df["timestamp"], y=df["macd_histogram"], name="MACD hist"), row=4, col=1)
    fig.update_layout(
        height=760,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=24, b=14),
        template="simple_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(color="#334155"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


try:
    if st.button("Refresh analysis", type="primary"):
        clear_data()
    watchlist_entries = load_watchlist()
except Exception as exc:
    st.error(f"Unable to load watchlist: {exc}")
    st.stop()

with st.sidebar:
    st.header("Watchlist")
    st.caption(
        "Add/remove stocks here. For TradingView, paste exported symbols such as NASDAQ:NVDA, EURONEXT:ALDRV, XETR:RHM."
    )

    with st.expander("Add stock", expanded=True):
        with st.form("add_stock_form", clear_on_submit=True):
            ticker = st.text_input("Ticker", placeholder="NVDA or ALDRV.PA")
            exchange = st.text_input("Exchange", placeholder="NASDAQ, Euronext Paris, XETRA")
            company_name = st.text_input("Company name", placeholder="NVIDIA")
            currency = st.text_input("Currency", placeholder="USD")
            sector = st.text_input("Sector", placeholder="Technology")
            country = st.text_input("Country", placeholder="United States")
            shares_owned = st.number_input("Shares owned", min_value=0.0, value=0.0, step=1.0)
            average_buy_price = st.number_input("Average buy price", min_value=0.0, value=0.0, step=0.01)
            submitted = st.form_submit_button("Add / update", type="primary")
            if submitted:
                if not ticker.strip():
                    st.warning("Ticker is required.")
                else:
                    payload = {
                        "ticker": ticker.strip(),
                        "exchange": exchange.strip(),
                        "company_name": company_name.strip() or ticker.strip().upper(),
                        "currency": currency.strip(),
                        "sector": sector.strip(),
                        "country": country.strip(),
                        "shares_owned": shares_owned or None,
                        "average_buy_price": average_buy_price or None,
                    }
                    try:
                        add_watchlist_item(payload)
                        clear_data()
                        st.success(f"Saved {ticker.strip().upper()}")
                        rerun_app()
                    except Exception as exc:
                        st.error(f"Could not save ticker: {exc}")

    with st.expander("Import TradingView list"):
        tv_symbols = st.text_area(
            "Symbols",
            placeholder="NASDAQ:NVDA, NASDAQ:MSFT, EURONEXT:ALDRV, XETR:RHM",
            height=110,
        )
        c1, c2, c3 = st.columns(3)
        default_currency = c1.text_input("Currency default", placeholder="USD")
        default_sector = c2.text_input("Sector default", placeholder="Technology")
        default_country = c3.text_input("Country default", placeholder="United States")
        if st.button("Import symbols"):
            if not tv_symbols.strip():
                st.warning("Paste at least one symbol.")
            else:
                try:
                    count = import_tradingview_symbols(
                        {
                            "symbols": tv_symbols,
                            "default_currency": default_currency.strip(),
                            "default_sector": default_sector.strip(),
                            "default_country": default_country.strip(),
                        }
                    )
                    clear_data()
                    st.success(f"Imported {count} symbols")
                    rerun_app()
                except Exception as exc:
                    st.error(f"Could not import symbols: {exc}")

    if watchlist_entries:
        remove_choice = st.selectbox(
            "Remove stock",
            [item["ticker"] for item in watchlist_entries],
            index=None,
            placeholder="Choose ticker",
        )
        if st.button("Remove selected", disabled=not remove_choice):
            try:
                remove_watchlist_item(remove_choice)
                clear_data()
                st.success(f"Removed {remove_choice}")
                rerun_app()
            except Exception as exc:
                st.error(f"Could not remove ticker: {exc}")

    st.divider()
    st.dataframe(
        pd.DataFrame(watchlist_entries)[["ticker", "exchange", "company_name"]]
        if watchlist_entries
        else pd.DataFrame(),
        width="stretch",
        hide_index=True,
        height=220,
    )

try:
    analysis = load_analysis()
except Exception as exc:
    st.error(f"Unable to load analysis: {exc}")
    st.stop()

if not analysis:
    st.info("Your watchlist is empty. Add a stock from the sidebar to start analysis.")
    st.stop()

tickers = [item["ticker"] for item in analysis]
best = max(analysis, key=lambda item: item["overall_score"])
weakest = min(analysis, key=lambda item: item["overall_score"])
avg_score = sum(item["overall_score"] for item in analysis) / len(analysis)

metric_cols = st.columns(4)
metric_cols[0].metric("Watchlist", len(analysis))
metric_cols[1].metric("Average score", f"{avg_score:.0f}/100")
metric_cols[2].metric("Top setup", best["ticker"], best["recommendation"])
metric_cols[3].metric("Weakest setup", weakest["ticker"], weakest["recommendation"])

table = format_signal_board(analysis)
st.subheader("Signal Board")
st.dataframe(
    style_signal_board(table),
    width="stretch",
    hide_index=True,
    height=min(360, 72 + len(table) * 38),
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker", width="small"),
        "Company": st.column_config.TextColumn("Company", width="medium"),
        "Price": st.column_config.NumberColumn("Price", format="%.2f", width="small"),
        "Day %": st.column_config.NumberColumn("Day %", format="%+.2f%%", width="small"),
        "Signal": st.column_config.TextColumn("Signal", width="small"),
        "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, width="small"),
        "Risk": st.column_config.TextColumn("Risk", width="small"),
        "News": st.column_config.TextColumn("News", width="small"),
        "P/L %": st.column_config.NumberColumn("P/L %", format="%+.2f%%", width="small"),
    },
)

selected = st.selectbox("Stock detail", tickers, index=tickers.index(best["ticker"]))
detail = load_detail(selected)
rec = detail["recommendation"]

headline, price_col, score_col, risk_col = st.columns([0.42, 0.18, 0.2, 0.2])
headline.subheader(f"{rec['ticker']} - {rec['company_name']}")
price_col.metric("Price", f"{rec['current_price']:,.2f}", f"{rec.get('daily_change_pct') or 0:+.2f}%")
score_col.metric(rec["recommendation"], f"{rec['overall_score']}/100")
risk_col.metric("Risk", rec["risk_level"], rec.get("news_sentiment"))

overview_tab, chart_tab, signals_tab, news_tab, position_tab = st.tabs(
    ["Overview", "Chart", "Timeframes", "News", "Position"]
)

with overview_tab:
    left, right = st.columns([0.56, 0.44])
    with left:
        st.write(rec["explanation"])
        st.write("Suggested action:", rec["suggested_action"])
        factors = pd.DataFrame(
            {
                "Positive factors": pd.Series(rec.get("positive_factors") or []),
                "Negative factors": pd.Series(rec.get("negative_factors") or []),
            }
        ).fillna("")
        st.dataframe(factors, width="stretch", hide_index=True)
    with right:
        st.dataframe(format_levels(rec), width="stretch", hide_index=True, height=350)

with chart_tab:
    chart_df = pd.DataFrame(detail["chart"])
    if chart_df.empty:
        st.info("No chart data available for this ticker from the current market data provider.")
    else:
        st.plotly_chart(chart(chart_df), config={"responsive": True, "displayModeBar": True})

with signals_tab:
    signal_rows = []
    for timeframe, signal in detail["signals"].items():
        signal_rows.append(
            {
                "Timeframe": timeframe,
                "Signal": signal["signal"],
                "Confidence": signal["confidence"],
                "Trend": signal["trend_direction"],
                "Momentum": signal["momentum"],
                "Risk": signal["risk_level"],
                "Risk/reward": signal.get("risk_reward_ratio"),
                "Explanation": signal["explanation"],
            }
        )
    if signal_rows:
        st.dataframe(pd.DataFrame(signal_rows), width="stretch", hide_index=True)
    else:
        st.info("No timeframe signals available for this ticker.")

with news_tab:
    news_rows = [
        {
            "Title": item["title"],
            "Source": item["source"],
            "Sentiment": item["sentiment"],
            "Impact": item["impact"],
            "Event": item["event_type"],
            "URL": item["url"],
        }
        for item in detail["news"]
    ]
    st.dataframe(
        pd.DataFrame(news_rows),
        width="stretch",
        hide_index=True,
        column_config={"URL": st.column_config.LinkColumn("URL", display_text="Open")},
    )

with position_tab:
    if rec.get("portfolio"):
        position = rec["portfolio"]
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Shares", f"{position['shares']:,.2f}")
        p2.metric("Market value", f"{position['current_market_value']:,.2f}")
        p3.metric("Unrealized P/L", f"{position['unrealized_gain_loss']:,.2f}", f"{position['unrealized_gain_loss_pct']:+.2f}%")
        p4.metric("Action", position["recommended_action"])
        st.dataframe(pd.DataFrame([position]), width="stretch", hide_index=True)
    else:
        st.info("No position configured for this ticker.")
