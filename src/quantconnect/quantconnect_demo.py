# region imports
from AlgorithmImports import *
# endregion


class QuantConnectDemo(QCAlgorithm):
    """
    Multi-asset momentum strategy on QuantConnect.

    Shows:
    - Multi-asset universe (stocks + crypto)
    - Built-in indicator library
    - Risk management
    - Scheduling
    - The same code deploys live with zero changes
    """

    def initialize(self) -> None:
        """Setup — runs once at start."""
        # ── Basics ─────────────────────────────────────────
        self.set_start_date(2023, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(100_000)

        # ── Add assets (multi-asset in one strategy!) ──────
        self.spy = self.add_equity("SPY", Resolution.DAILY).symbol
        self.qqq = self.add_equity("QQQ", Resolution.DAILY).symbol
        self.btc = self.add_crypto("BTCUSD", Resolution.DAILY).symbol

        # ── Indicators (200+ built-in) ─────────────────────
        self.spy_rsi = self.rsi(self.spy, 14, MovingAverageType.WILDERS, Resolution.DAILY)
        self.spy_ema_fast = self.ema(self.spy, 10, Resolution.DAILY)
        self.spy_ema_slow = self.ema(self.spy, 30, Resolution.DAILY)
        self.btc_bb = self.bb(self.btc, 20, 2, MovingAverageType.SIMPLE, Resolution.DAILY)

        # ── Warm up indicators ─────────────────────────────
        self.set_warm_up(30, Resolution.DAILY)

        # ── Schedule rebalancing ───────────────────────────
        self.schedule.on(
            self.date_rules.every_day(self.spy),
            self.time_rules.after_market_open(self.spy, 30),
            self.rebalance,
        )

        # ── Risk management ────────────────────────────────
        self.set_risk_management(MaximumDrawdownPercentPerSecurity(0.05))

    def rebalance(self) -> None:
        """Daily rebalance logic."""
        if self.is_warming_up:
            return

        # ── SPY: EMA crossover ─────────────────────────────
        if self.spy_ema_fast.current.value > self.spy_ema_slow.current.value:
            self.set_holdings(self.spy, 0.4)       # 40% allocation
        else:
            self.liquidate(self.spy)

        # ── QQQ: RSI mean reversion ────────────────────────
        if self.spy_rsi.current.value < 30:
            self.set_holdings(self.qqq, 0.3)       # 30% allocation
        elif self.spy_rsi.current.value > 70:
            self.liquidate(self.qqq)

        # ── BTC: Bollinger Band breakout ───────────────────
        btc_price = self.securities[self.btc].price
        if btc_price > self.btc_bb.upper_band.current.value:
            self.set_holdings(self.btc, 0.2)       # 20% allocation
        elif btc_price < self.btc_bb.lower_band.current.value:
            self.liquidate(self.btc)

    def on_data(self, data: Slice) -> None:
        """Called on every data event — used for logging here."""
        pass  # Main logic is in scheduled rebalance

    def on_order_event(self, order_event: OrderEvent) -> None:
        """Track fills."""
        if order_event.status == OrderStatus.FILLED:
            self.debug(
                f"Filled: {order_event.symbol} "
                f"qty={order_event.fill_quantity} "
                f"@ {order_event.fill_price}"
            )
