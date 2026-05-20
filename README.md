# Investment Agent

Investment Agent is a decision-support application for stock watchlists. It combines technical indicators, multi-timeframe rules, news monitoring, and optional portfolio gain/loss tracking into an explainable dashboard.

It does not provide guaranteed financial advice. Signals, scores, risk levels, forecasts, and news summaries are informational inputs for your own decision process.

## Architecture

- Backend: FastAPI
- Frontend: Streamlit
- Database: SQLite through SQLAlchemy
- Scheduler: APScheduler
- Data processing: pandas
- Charts: Plotly
- Market data provider: Yahoo Finance via `yfinance`
- News provider: Google News RSS via `feedparser`

The important extension points are:

- `MarketDataProvider` in `app/services/market_data/base.py`
- `NewsProvider` in `app/services/news/base.py`
- `IndicatorEngine` in `app/services/indicators/engine.py`
- `SignalEngine` in `app/services/signals/engine.py`
- `RecommendationAggregator` in `app/services/recommendations/aggregator.py`

## Features

- Manual YAML watchlist configuration
- OHLCV collection for `5m`, `15m`, `1h`, and `1d`
- EMA 9/20/50/200, SMA 50/200, RSI 14, MACD, Bollinger Bands, ATR, volume average, VWAP, support/resistance, swing highs/lows
- BUY, SELL, HOLD, WATCH, and AVOID timeframe signals
- STRONG BUY, BUY, WATCH, HOLD, REDUCE, SELL, and AVOID aggregate recommendations
- News sentiment, impact, and event classification
- Portfolio market value, unrealized gain/loss, and position action
- Alerts for signal changes, buy/sell signals, stop-loss, take-profit, and high-impact news
- Streamlit dashboard table and stock detail charts

## Setup

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

On first run, `config/watchlist.yml` seeds the database. After that you can add, update, remove, or import symbols from the dashboard sidebar.

TradingView import supports pasted/exported `.txt` symbols such as:

```text
NASDAQ:NVDA, NASDAQ:MSFT, EURONEXT:ALDRV, XETR:RHM
```

For the default Yahoo Finance market data provider, common TradingView exchanges are converted where needed, for example `EURONEXT:ALDRV` to `ALDRV.PA` and `XETR:RHM` to `RHM.DE`.

Optional portfolio fields are `shares_owned`, `average_buy_price`, and `investment_amount`.

## Run Locally

Start the API:

```bash
uvicorn app.main:app --reload
```

Start the dashboard in another terminal:

```bash
streamlit run frontend/streamlit_app.py
```

Open:

- API docs: `http://localhost:8000/docs`
- Dashboard: `http://localhost:8501`

## Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

The dashboard runs on `http://localhost:8501` and the API on `http://localhost:8000`.

## API Keys

The default first version does not require a paid API key. `.env.example` includes placeholders for future providers such as Alpha Vantage, Polygon.io, Twelve Data, email, Telegram, and Discord.

## Signal Logic

The rules combine trend, momentum, volume, volatility, support/resistance, and news. A bullish setup is favored when price is above EMA 20 and EMA 50, EMA 9 crosses above EMA 20, RSI is constructive, MACD histogram improves, volume is above average, and higher timeframes are not bearish. Bearish or avoid outcomes are favored when price breaks below key averages/support, RSI weakens or becomes overbought, MACD turns negative, volatility is extreme, or news is strongly negative.

Forecast levels are explainable:

- Entry zone: latest price or pullback zone near the primary timeframe
- Stop-loss: recent support or ATR-based distance
- Take-profit: resistance or ATR projection
- Risk/reward: expected upside divided by expected downside

## Tests

```bash
pytest
```

Tests cover indicator output, support/resistance, signal generation, portfolio gain/loss, news sentiment, and recommendation aggregation.

## Limitations

- Yahoo Finance intraday availability and delayed data vary by exchange.
- RSS news sentiment is a simple rules-based classifier, not a professional news analytics feed.
- TradingView watchlist integration is intentionally left behind the provider boundary for a later version.
- The scheduler is simple and does not yet model each exchange calendar or holiday.
- Signals can be wrong. Always validate with your own analysis and risk management.
