"""
FREQTRADE — Strategy Example
=============================

Docs:    https://www.freqtrade.io

This shows a real strategy structure with FreqAI-ready patterns.
Run backtest: freqtrade backtesting --strategy FreqtradeDemo --timeframe 5m
"""

import numpy as np
import talib.abstract as ta
from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
from pandas import DataFrame
from freqtrade.persistence import Trade

class FreqtradeDemo(IStrategy):
    """
    Freqtrade strategy with:
    - Hyperoptimizable parameters (built-in optimization)
    - Technical indicators via TA-Lib
    - Entry/exit signal logic
    - Risk management via stoploss + trailing
    """

    # ── Timeframe & risk settings ──────────────────────────
    timeframe = "5m"
    stoploss = -0.04                          # -4% hard stop (tighter)
    trailing_stop = True
    trailing_stop_positive = 0.015            # Lock 1.5% profit
    trailing_stop_positive_offset = 0.02      # Activate after 2% gain

    # ── Hyper parameters ──
    buy_rsi = IntParameter(25, 40, default=35, space="buy")   # Only buy oversold pullbacks
    sell_rsi = IntParameter(65, 80, default=72, space="sell")  # Exit when overbought (let winners run)
    buy_ema_short = IntParameter(6, 12, default=9, space="buy")
    buy_ema_long = IntParameter(20, 35, default=26, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate all indicators once — used by both entry and exit."""
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_short"] = ta.EMA(dataframe, timeperiod=self.buy_ema_short.value)
        dataframe["ema_long"] = ta.EMA(dataframe, timeperiod=self.buy_ema_long.value)
        dataframe["volume_mean"] = dataframe["volume"].rolling(20).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define BUY conditions — only on oversold pullbacks in uptrend with decent volume."""
        dataframe.loc[
            (
                (dataframe["rsi"] < self.buy_rsi.value) &              # RSI oversold
                (dataframe["ema_short"] > dataframe["ema_long"]) &     # Uptrend
                (dataframe["volume"] > dataframe["volume_mean"] * 0.7)  # Enough liquidity
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define SELL conditions — exit when overbought or trend flips."""
        dataframe.loc[
            (
                (dataframe["rsi"] > self.sell_rsi.value) |              # Overbought / take profit
                (dataframe["ema_short"] < dataframe["ema_long"])       # Trend reversal
            ),
            "exit_long",
        ] = 1
        return dataframe










# ── CLI Commands to show on screen ────────────────────────
CLI_COMMANDS = """
# Download data
freqtrade download-data --exchange binance --pairs BTC/USDT ETH/USDT --timeframe 5m -c config.json --timerange 20240101-20250101

# Backtest
freqtrade backtesting --strategy FreqtradeDemo --strategy-path . -c config.json --timeframe 5m --timerange 20240101-20250101
"""