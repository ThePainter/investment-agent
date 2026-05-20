from __future__ import annotations

from app.models.schemas import PortfolioSnapshot, TimeframeSignal


class PortfolioEngine:
    def calculate(
        self,
        ticker: str,
        shares: float | None,
        average_buy_price: float | None,
        current_price: float,
        signal: TimeframeSignal | None,
    ) -> PortfolioSnapshot | None:
        if not shares or not average_buy_price:
            return None

        invested = shares * average_buy_price
        market_value = shares * current_price
        gain_loss = market_value - invested
        gain_loss_pct = gain_loss / invested * 100 if invested else 0.0
        stop = signal.stop_loss if signal else None
        take_profit = signal.take_profit if signal else None
        distance_stop = ((current_price - stop) / current_price * 100) if stop else None
        distance_take = ((take_profit - current_price) / current_price * 100) if take_profit else None

        if signal and signal.signal == "SELL":
            action = "SELL"
        elif gain_loss_pct > 20 and signal and signal.signal in {"HOLD", "WATCH"}:
            action = "TAKE PROFIT"
        elif signal and signal.signal == "BUY" and gain_loss_pct >= -8:
            action = "ADD"
        elif stop and current_price <= stop:
            action = "SELL"
        elif signal and signal.signal == "AVOID":
            action = "REDUCE"
        else:
            action = "HOLD"

        return PortfolioSnapshot(
            ticker=ticker,
            shares=shares,
            average_buy_price=average_buy_price,
            invested_amount=invested,
            current_market_value=market_value,
            unrealized_gain_loss=gain_loss,
            unrealized_gain_loss_pct=gain_loss_pct,
            distance_to_stop_loss_pct=distance_stop,
            distance_to_take_profit_pct=distance_take,
            recommended_action=action,
        )
