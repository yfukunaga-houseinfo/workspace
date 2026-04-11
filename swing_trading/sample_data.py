"""
Sample Data Generator for testing when Yahoo Finance is unavailable.
Generates realistic OHLCV data with known patterns for validation.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def generate_sample_ohlcv(ticker: str = "SAMPLE", days: int = 300,
                          start_price: float = 150.0,
                          trend: str = "uptrend",
                          seed: int = 42) -> pd.DataFrame:
    """
    Generate realistic OHLCV sample data with configurable trend.

    Args:
        ticker: Ticker symbol (for labeling)
        days: Number of trading days
        start_price: Starting price
        trend: "uptrend", "downtrend", or "sideways"
        seed: Random seed for reproducibility
    """
    np.random.seed(seed)

    dates = pd.bdate_range(end=datetime.now(), periods=days)
    n = len(dates)  # Use actual date count for all arrays

    # Drift based on trend
    drift_map = {"uptrend": 0.0005, "downtrend": -0.0004, "sideways": 0.0001}
    daily_drift = drift_map.get(trend, 0.0001)

    # Generate returns with some autocorrelation and volatility clustering
    volatility = 0.018
    returns = np.random.normal(daily_drift, volatility, n)

    # Add some momentum / mean-reversion cycles
    cycle1 = 0.02 * np.sin(np.linspace(0, 6 * np.pi, n))  # ~50-day cycle
    cycle2 = 0.01 * np.sin(np.linspace(0, 12 * np.pi, n))  # ~25-day cycle
    returns += np.diff(np.concatenate([[0], cycle1])) + np.diff(np.concatenate([[0], cycle2]))

    # Build close prices
    close = start_price * np.cumprod(1 + returns)

    # Generate OHLV from close
    daily_range = close * np.random.uniform(0.008, 0.025, n)
    open_prices = close + np.random.normal(0, 0.3, n)
    high = np.maximum(close, open_prices) + daily_range * np.random.uniform(0.2, 0.8, n)
    low = np.minimum(close, open_prices) - daily_range * np.random.uniform(0.2, 0.8, n)

    # Volume with some patterns (higher on bigger moves)
    base_volume = 50_000_000
    volume_noise = np.random.lognormal(0, 0.4, n)
    move_size = np.abs(returns) / volatility
    volume = (base_volume * volume_noise * (0.7 + 0.3 * move_size)).astype(int)

    # Add a few volume spikes (earnings, news)
    spike_days = np.random.choice(range(20, n), size=min(5, n - 20), replace=False)
    for sd in spike_days:
        volume[sd] = int(volume[sd] * 3.5)

    df = pd.DataFrame({
        'Open': open_prices,
        'High': high,
        'Low': low,
        'Close': close,
        'Volume': volume,
    }, index=dates)

    # Inject some known patterns for testing

    # 1. Create a clear bullish engulfing near day 200
    if n > 210:
        idx = 200
        df.iloc[idx - 1, df.columns.get_loc('Open')] = df.iloc[idx - 1]['Close'] + 2
        df.iloc[idx - 1, df.columns.get_loc('Close')] = df.iloc[idx - 1]['Open'] - 3
        df.iloc[idx, df.columns.get_loc('Open')] = df.iloc[idx - 1]['Close'] - 0.5
        df.iloc[idx, df.columns.get_loc('Close')] = df.iloc[idx - 1]['Open'] + 1

    # 2. Create a volume spike with breakout near day 250
    if n > 260:
        idx = 250
        df.iloc[idx, df.columns.get_loc('Close')] = df.iloc[idx - 1]['Close'] * 1.035
        df.iloc[idx, df.columns.get_loc('High')] = df.iloc[idx]['Close'] * 1.01
        df.iloc[idx, df.columns.get_loc('Volume')] = int(base_volume * 4)

    return df


def generate_multi_stock_samples() -> dict:
    """Generate sample data for multiple stocks with different characteristics."""
    return {
        'BULL_STOCK': generate_sample_ohlcv('BULL', trend='uptrend', start_price=100, seed=42),
        'BEAR_STOCK': generate_sample_ohlcv('BEAR', trend='downtrend', start_price=200, seed=99),
        'SIDE_STOCK': generate_sample_ohlcv('SIDE', trend='sideways', start_price=50, seed=77),
    }


def load_csv_data(filepath: str) -> pd.DataFrame:
    """
    Load OHLCV data from CSV file.
    Expected columns: Date, Open, High, Low, Close, Volume
    """
    df = pd.read_csv(filepath, parse_dates=['Date'], index_col='Date')
    df.columns = [c.strip().title() for c in df.columns]

    required = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    return df.sort_index()
