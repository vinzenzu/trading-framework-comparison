"""
VECTORBT — Speed Demo
======================

Docs:    https://vectorbt.dev

This demo generates sample data and runs a massive parameter sweep
to show VectorBT's vectorized speed advantage.
"""

import numpy as np
import pandas as pd
import vectorbt as vbt
from datetime import datetime

# ══════════════════════════════════════════════════════════════
# 1. GENERATE SAMPLE PRICE DATA (simulated BTC-like series)
# ══════════════════════════════════════════════════════════════
np.random.seed(42)
n_days = 1000
dates = pd.date_range("2022-01-01", periods=n_days, freq="D")

# Random walk with drift (simulates realistic price movement)
returns = np.random.normal(loc=0.0003, scale=0.025, size=n_days)
price = 30000 * np.cumprod(1 + returns)
close = pd.Series(price, index=dates, name="BTC-USD")

print(f"Sample data: {n_days} days, price range ${price.min():.0f} - ${price.max():.0f}")
print(f"{'='*60}")

# ══════════════════════════════════════════════════════════════
# 2. SINGLE BACKTEST — EMA Crossover
# ══════════════════════════════════════════════════════════════
fast_ema = vbt.MA.run(close, window=10, ewm=True)
slow_ema = vbt.MA.run(close, window=30, ewm=True)

entries = fast_ema.ma_crossed_above(slow_ema)
exits = fast_ema.ma_crossed_below(slow_ema)

# Run portfolio simulation
pf = vbt.Portfolio.from_signals(
    close=close,
    entries=entries,
    exits=exits,
    init_cash=100_000,
    fees=0.001,       # 0.1% trading fee
    slippage=0.001,   # 0.1% slippage
)

print("\n  Single Backtest Results (EMA 10/30):")
print(f"  Total Return:    {pf.total_return():.2%}")
print(f"  Sharpe Ratio:    {pf.sharpe_ratio():.2f}")
print(f"  Max Drawdown:    {pf.max_drawdown():.2%}")
print(f"  Total Trades:    {pf.trades.count()}")
print(f"  Win Rate:        {pf.trades.win_rate():.2%}")

# ══════════════════════════════════════════════════════════════
# 3. MASSIVE PARAMETER SWEEP — This is VectorBT's superpower
# ══════════════════════════════════════════════════════════════
# Test ALL combinations of fast (5-50) and slow (20-200) EMAs
fast_windows = list(range(5, 51))       # 46 values
slow_windows = list(range(20, 201, 2))  # 91 values
n_combs = len(fast_windows) * len(slow_windows)  # 4,186 backtests

# Flatten to one (fast, slow) per column: MA.run(close, window=[...]) runs one MA per window
fast_list = [f for f in fast_windows for s in slow_windows]
slow_list = [s for f in fast_windows for s in slow_windows]

print(f"\n  Running {n_combs:,} parameter combinations...")

import time
start = time.time()

# Run 4,186 fast EMAs and 4,186 slow EMAs (one column per combination)
fast_ema_all = vbt.MA.run(close, window=fast_list, ewm=True)
slow_ema_all = vbt.MA.run(close, window=slow_list, ewm=True)

entries_all = fast_ema_all.ma_crossed_above(slow_ema_all)
exits_all = fast_ema_all.ma_crossed_below(slow_ema_all)

pf_all = vbt.Portfolio.from_signals(
    close=close,
    entries=entries_all,
    exits=exits_all,
    init_cash=100_000,
    fees=0.001,
    slippage=0.001,
)

elapsed = time.time() - start
print(f"  Completed in {elapsed:.2f} seconds")

# ══════════════════════════════════════════════════════════════
# 4. FIND BEST PARAMETERS
# ══════════════════════════════════════════════════════════════
returns = pf_all.total_return()
sharpe = pf_all.sharpe_ratio()

best_return_idx = returns.idxmax()
best_sharpe_idx = sharpe.idxmax()
# Column position 0..n_combs-1 maps to (fast, slow) via our product order
idx_return = returns.values.argmax()
idx_sharpe = sharpe.values.argmax()
fast_best_return, slow_best_return = fast_list[idx_return], slow_list[idx_return]
fast_best_sharpe, slow_best_sharpe = fast_list[idx_sharpe], slow_list[idx_sharpe]

print(f"\n  Best by Total Return:")
print(f"  Fast={fast_best_return}, Slow={slow_best_return}")
print(f"  Return: {returns[best_return_idx]:.2%}")
print(f"  Sharpe: {sharpe[best_return_idx]:.2f}")

# ══════════════════════════════════════════════════════════════
# 5. VISUALIZATION (generates interactive Plotly charts)
# ══════════════════════════════════════════════════════════════
VISUALIZATION_CODE = """
# Heatmap: reshape flat columns to (fast x slow) grid
returns_2d = pd.DataFrame(
    returns.values.reshape(len(fast_windows), len(slow_windows)),
    index=fast_windows,
    columns=slow_windows,
)
fig = returns_2d.vbt.heatmap(title="Total Return by EMA Parameters")
fig.show()

# Equity curve of best strategy (use column position)
best_pf = pf_all.iloc[:, idx_sharpe]
best_pf.plot().show()

# Drawdown plot
best_pf.drawdowns.plot().show()

# Trade analysis
best_pf.trades.plot().show()
"""

print(f"\n{'='*60}")
print("   VectorBT key insight: this same sweep in e.g. Backtrader")
print("   would take HOURS. VectorBT does it in seconds because")
print("   strategies are numpy arrays, not Python loops.")

# uv run vectorbt_demo.py