"""
LUMIBOT — Beginner-Friendly Demo
==================================

Docs:    https://lumibot.lumiwealth.com

Supports stocks, options, futures, crypto, forex.
Same code for backtest and live.
"""

from datetime import datetime
from lumibot.strategies import Strategy
from lumibot.backtesting import YahooDataBacktesting
from lumibot.traders import Trader


# ══════════════════════════════════════════════════════════════
# STRATEGY — Simple momentum with risk management
# ══════════════════════════════════════════════════════════════
class MomentumStrategy(Strategy):
    """
    Lumibot lifecycle:
    1. initialize()            → runs once at start
    2. on_trading_iteration()  → runs every bar/tick
    3. before_market_closes()  → optional end-of-day hook
    
    Beginner-friendly: no event loops, no state machines.
    """

    parameters = {
        "symbol": "SPY",
        "lookback": 20,           # Momentum lookback period
        "cash_at_risk": 0.5,      # Only risk 50% of portfolio
    }

    def initialize(self):
        """Runs once — set schedule and state."""
        self.sleeptime = "1D"     # Run once per day
        self.last_trade = None

    def on_trading_iteration(self):
        """Core logic — runs every iteration."""
        symbol = self.parameters["symbol"]
        lookback = self.parameters["lookback"]
        cash_at_risk = self.parameters["cash_at_risk"]

        # ── Get data ───────────────────────────────────────
        bars = self.get_historical_prices(symbol, lookback + 1, "day")
        if bars is None or bars.df.empty:
            return

        closes = bars.df["close"]
        current_price = self.get_last_price(symbol)

        # ── Calculate momentum ─────────────────────────────
        momentum = (closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0]

        # ── Position sizing ────────────────────────────────
        cash = self.get_cash()
        quantity = int((cash * cash_at_risk) / current_price)

        # ── Trading logic ──────────────────────────────────
        current_position = self.get_position(symbol)

        if momentum > 0.02 and current_position is None:
            # BUY: positive momentum, no existing position
            order = self.create_order(symbol, quantity, "buy")
            self.submit_order(order)
            self.log_message(f"BUY {quantity} {symbol} @ {current_price:.2f}")
            self.last_trade = "buy"

        elif momentum < -0.02 and current_position is not None:
            # SELL: negative momentum, have position
            self.sell_all()
            self.log_message(f"SOLD all {symbol} @ {current_price:.2f}")
            self.last_trade = "sell"

    def before_market_closes(self):
        """Optional: runs 5 min before close."""
        self.log_message(f"Market closing soon. Last trade: {self.last_trade}")


# ══════════════════════════════════════════════════════════════
# BACKTEST — Using Yahoo Finance (free, no API key needed)
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    backtesting_start = datetime(2023, 1, 1)
    backtesting_end = datetime(2024, 12, 31)

    results = MomentumStrategy.backtest(
        YahooDataBacktesting,
        backtesting_start,
        backtesting_end,
        parameters={
            "symbol": "SPY",
            "lookback": 20,
            "cash_at_risk": 0.5,
        },
    )
    print(results)

