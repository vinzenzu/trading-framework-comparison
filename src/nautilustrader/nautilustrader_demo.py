"""
NAUTILUSTRADER — Strategy Example
===================================

Docs:    https://nautilustrader.io

TRUE backtest-to-live parity: this exact code runs in both modes.
"""

from decimal import Decimal
from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.data import Data
from nautilus_trader.model.enums import OrderSide, PriceType, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.trading.strategy import Strategy


# ── Strategy Config ────────────────────────────────────────
class EMACrossConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    fast_ema_period: int = 10
    slow_ema_period: int = 20
    trade_size: Decimal = Decimal("0.01")


# ── Strategy Implementation ────────────────────────────────
class EMACrossStrategy(Strategy):
    """
    NautilusTrader EMA crossover strategy.
    
    Key concepts shown:
    - Event-driven bar handler (on_bar)
    - Order lifecycle management
    - Position tracking
    - Identical code for backtest AND live
    """

    def __init__(self, config: EMACrossConfig) -> None:
        super().__init__(config)
        self.instrument_id = config.instrument_id
        self.bar_type = config.bar_type
        self.trade_size = config.trade_size

        # EMA state
        self.fast_ema_period = config.fast_ema_period
        self.slow_ema_period = config.slow_ema_period
        self.fast_ema = 0.0
        self.slow_ema = 0.0
        self.bars_processed = 0

    def on_start(self) -> None:
        """Called when strategy starts — subscribe to data."""
        self.instrument = self.cache.instrument(self.instrument_id)
        if self.instrument is None:
            self.log.error(f"Could not find instrument for {self.instrument_id}")
            self.stop()
            return
        self.subscribe_bars(self.bar_type)
        self.log.info(f"Strategy started, subscribed to {self.bar_type}")

    def on_bar(self, bar: Bar) -> None:
        """Called on every new bar — core strategy logic."""
        close = float(bar.close)
        self.bars_processed += 1

        # Update EMAs
        if self.bars_processed == 1:
            self.fast_ema = close
            self.slow_ema = close
            return

        fast_k = 2 / (self.fast_ema_period + 1)
        slow_k = 2 / (self.slow_ema_period + 1)
        self.fast_ema = close * fast_k + self.fast_ema * (1 - fast_k)
        self.slow_ema = close * slow_k + self.slow_ema * (1 - slow_k)

        if self.bars_processed < self.slow_ema_period:
            return  # Wait for warmup

        # ── Entry / Exit Logic ─────────────────────────────
        is_long = self.portfolio.is_net_long(self.instrument_id)
        is_flat = self.portfolio.is_flat(self.instrument_id)

        if self.fast_ema > self.slow_ema and is_flat:
            self._enter(OrderSide.BUY)
        elif self.fast_ema < self.slow_ema and is_long:
            self._enter(OrderSide.SELL)

    def _enter(self, side: OrderSide) -> None:
        """Submit a market order."""
        order: MarketOrder = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=side,
            quantity=self.instrument.make_qty(self.trade_size),
            time_in_force=TimeInForce.IOC,
        )
        self.submit_order(order)
        self.log.info(f"Submitted {side.name} order for {self.trade_size}")

    def on_stop(self) -> None:
        """Cleanup — close all positions on shutdown."""
        self.close_all_positions(self.instrument_id)
        self.log.info("Strategy stopped, positions closed.")


# ── Free data: yfinance (no API key) ───────────────────────
def load_ohlcv_yfinance(symbol: str = "BTC-USD", period: str = "2y"):
    """Load free OHLCV data via yfinance. Install with: pip install yfinance"""
    import pandas as pd

    try:
        import yfinance as yf
    except ImportError:
        raise ImportError(
            "Free backtest data requires yfinance. Install with: pip install yfinance"
        ) from None

    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, auto_adjust=True)
    if df.empty or len(df) < 30:
        raise ValueError(f"Not enough data for {symbol}. Try a different symbol or period.")
    # Wrangler expects: index = datetime (UTC), columns = open, high, low, close [, volume]
    # Omit volume so wrangler uses default (yfinance volume can exceed Nautilus QUANTITY_MAX)
    df = df.rename(columns=str.lower)[["open", "high", "low", "close"]]
    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC", ambiguous="infer")
    else:
        df.index = df.index.tz_convert("UTC")
    return df


# ── Executable backtest (runs when you execute this script) ─
def run_backtest(
    symbol: str = "BTC-USD",
    period: str = "2y",
    fast_ema: int = 10,
    slow_ema: int = 20,
    trade_size: str = "0.01",
) -> None:
    """Run a full backtest with free yfinance data."""
    from nautilus_trader.backtest.engine import BacktestEngine
    from nautilus_trader.backtest.models import FillModel
    from nautilus_trader.config import BacktestEngineConfig
    from nautilus_trader.model.currencies import USDT
    from nautilus_trader.model.data import BarAggregation
    from nautilus_trader.model.data import BarSpecification
    from nautilus_trader.model.data import BarType
    from nautilus_trader.model.enums import AccountType
    from nautilus_trader.model.enums import OmsType
    from nautilus_trader.model.identifiers import Venue
    from nautilus_trader.model.objects import Money
    from nautilus_trader.persistence.wranglers import BarDataWrangler
    from nautilus_trader.test_kit.providers import TestInstrumentProvider

    # 1. Load free data (yfinance)
    print(f"Loading {symbol} data (period={period}) via yfinance...")
    ohlcv = load_ohlcv_yfinance(symbol=symbol, period=period)
    print(f"  Loaded {len(ohlcv)} bars from {ohlcv.index[0].date()} to {ohlcv.index[-1].date()}")

    # 2. Instrument and bar type (Binance-style BTCUSDT for crypto; use SIM for stocks if needed)
    instrument = TestInstrumentProvider.btcusdt_binance()
    bar_spec = BarSpecification(1, BarAggregation.DAY, PriceType.LAST)
    bar_type = BarType(instrument.id, bar_spec)

    wrangler = BarDataWrangler(bar_type=bar_type, instrument=instrument)
    bars = wrangler.process(ohlcv)
    print(f"  Built {len(bars)} Nautilus bars")

    # 3. Strategy config
    config = EMACrossConfig(
        instrument_id=instrument.id,
        bar_type=bar_type,
        fast_ema_period=fast_ema,
        slow_ema_period=slow_ema,
        trade_size=Decimal(trade_size),
    )

    # 4. Backtest engine
    engine = BacktestEngine(config=BacktestEngineConfig(trader_id="BACKTESTER-001"))

    # Use USDT (not USD) so the account report reflects real PnL: we're trading BTCUSDT,
    # so fills settle in USDT. With base_currency=USD the engine would need a USDT/USD
    # rate to update the balance; we don't feed that, so USD would stay at 100k.
    engine.add_venue(
        venue=Venue("BINANCE"),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=None,  # multi-currency: track USDT (and BTC) so report shows real outcome
        starting_balances=[Money(100_000, USDT)],
        fill_model=FillModel(prob_fill_on_limit=0.2, prob_slippage=0.1),
    )

    engine.add_instrument(instrument)
    engine.add_data(bars)
    engine.add_strategy(EMACrossStrategy(config))

    # 5. Run
    print("\nRunning backtest...")
    engine.run()

    # 6. Reports
    print("\n" + "=" * 60)
    print("ORDER FILLS REPORT")
    print("=" * 60)
    print(engine.trader.generate_order_fills_report())
    print("\n" + "=" * 60)
    print("POSITIONS REPORT")
    print("=" * 60)
    print(engine.trader.generate_positions_report())
    print("\n" + "=" * 60)
    print("ACCOUNT REPORT")
    print("=" * 60)
    print(engine.trader.generate_account_report(Venue("BINANCE")))

    print("\n(Account report above shows USDT balance over time; it changes with each trade.)")

if __name__ == "__main__":
    run_backtest(symbol="BTC-USD", period="2y", fast_ema=10, slow_ema=20, trade_size="0.01")