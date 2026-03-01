"""
SIDE-BY-SIDE — Same Strategy, 5 Frameworks
=============================================
EMA crossover implemented in each framework.
Show this on screen to compare syntax and complexity.

This file is for VISUAL COMPARISON only (won't run standalone).
"""

# ══════════════════════════════════════════════════════════════
# FREQTRADE — 15 lines of logic
# ══════════════════════════════════════════════════════════════
FREQTRADE = """
class MyStrategy(IStrategy):
    timeframe = "5m"
    stoploss = -0.05

    def populate_indicators(self, df, metadata):
        df["ema_fast"] = ta.EMA(df["close"], timeperiod=10)
        df["ema_slow"] = ta.EMA(df["close"], timeperiod=30)
        return df

    def populate_entry_trend(self, df, metadata):
        df.loc[df["ema_fast"] > df["ema_slow"], "enter_long"] = 1
        return df

    def populate_exit_trend(self, df, metadata):
        df.loc[df["ema_fast"] < df["ema_slow"], "exit_long"] = 1
        return df
"""

# ══════════════════════════════════════════════════════════════
# NAUTILUSTRADER
# ══════════════════════════════════════════════════════════════
NAUTILUS = """
class EMACross(Strategy):
    def on_start(self):
        self.fast_k = 2 / (10 + 1)
        self.slow_k = 2 / (30 + 1)
        self.fast_ema = 0.0
        self.slow_ema = 0.0
        self.qty = Quantity.from_int(100)
        self.subscribe_bars(self.bar_type)

    def on_bar(self, bar):
        close = float(bar.close)
        self.fast_ema = close * self.fast_k + self.fast_ema * (1 - self.fast_k)
        self.slow_ema = close * self.slow_k + self.slow_ema * (1 - self.slow_k)

        if self.fast_ema > self.slow_ema and self.portfolio.is_flat(self.id):
            order = self.order_factory.market(self.id, OrderSide.BUY, self.qty)
            self.submit_order(order)
        elif self.fast_ema < self.slow_ema and self.portfolio.is_net_long(self.id):
            order = self.order_factory.market(self.id, OrderSide.SELL, self.qty)
            self.submit_order(order)
"""

# ══════════════════════════════════════════════════════════════
# QUANTCONNECT
# ══════════════════════════════════════════════════════════════
QUANTCONNECT = """
class MyAlgo(QCAlgorithm):
    def initialize(self):
        self.set_cash(100_000)
        self.spy = self.add_equity("SPY").symbol
        self.fast = self.ema(self.spy, 10)
        self.slow = self.ema(self.spy, 30)

    def on_data(self, data):
        if self.fast.current.value > self.slow.current.value:
            self.set_holdings(self.spy, 1.0)
        else:
            self.liquidate(self.spy)
"""

# ══════════════════════════════════════════════════════════════
# VECTORBT
# ══════════════════════════════════════════════════════════════
VECTORBT = """
fast = vbt.MA.run(close, window=10, ewm=True)
slow = vbt.MA.run(close, window=30, ewm=True)

entries = fast.ma_crossed_above(slow)
exits = fast.ma_crossed_below(slow)

pf = vbt.Portfolio.from_signals(close, entries, exits,
                                 init_cash=100_000, fees=0.001)
print(f"Return: {pf.total_return():.2%}, Sharpe: {pf.sharpe_ratio():.2f}")
"""

# ══════════════════════════════════════════════════════════════
# LUMIBOT
# ══════════════════════════════════════════════════════════════
LUMIBOT = """
class MyStrategy(Strategy):
    def initialize(self):
        self.sleeptime = "1D"

    def on_trading_iteration(self):
        bars = self.get_historical_prices("SPY", 31, "day")
        closes = bars.df["close"]
        fast_ema = closes.ewm(span=10).mean().iloc[-1]
        slow_ema = closes.ewm(span=30).mean().iloc[-1]

        if fast_ema > slow_ema and not self.get_position("SPY"):
            qty = int(self.get_cash() / self.get_last_price("SPY"))
            order = self.create_order("SPY", qty, "buy")
            self.submit_order(order)
        elif fast_ema < slow_ema and self.get_position("SPY"):
            self.sell_all()
"""


# ══════════════════════════════════════════════════════════════
# COMPARISON TABLE
# ══════════════════════════════════════════════════════════════
print("""
╔═══════════════════╦══════════╦════════════╦══════════════╦═════════════╗
║ Framework         ║ Lines    ║ Live Ready ║ Learning     ║ Best For    ║
╠═══════════════════╬══════════╬════════════╬══════════════╬═════════════╣
║ Freqtrade         ║   16     ║ ✅ Yes     ║ ⭐⭐        ║ Crypto      ║
║ NautilusTrader    ║   20     ║ ✅ Yes     ║ ⭐⭐⭐      ║ Production  ║
║ QuantConnect      ║   12     ║ ✅ Yes     ║ ⭐⭐        ║ Multi-asset ║
║ VectorBT          ║   9      ║ ❌ No      ║ ⭐⭐⭐      ║ Research    ║
║ Lumibot           ║   16     ║ ✅ Yes     ║ ⭐          ║ Beginners   ║
╚═══════════════════╩══════════╩════════════╩══════════════╩═════════════╝

Key takeaway: VectorBT = least code, most speed, but no live trading.
NautilusTrader = most code, most capable, steepest curve.
QuantConnect = best balance of simplicity and power.
""")