"""
Technical Indicators for Swing Trading
All indicators implemented from scratch using pandas/numpy.
"""

import numpy as np
import pandas as pd


# =============================================================================
# Moving Averages
# =============================================================================

def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


# =============================================================================
# RSI (Relative Strength Index)
# =============================================================================

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI calculation."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


# =============================================================================
# MACD (Moving Average Convergence Divergence)
# =============================================================================

def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    Returns: (macd_line, signal_line, histogram)
    """
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


# =============================================================================
# Bollinger Bands
# =============================================================================

def bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2.0):
    """
    Returns: (upper_band, middle_band, lower_band, bandwidth, percent_b)
    """
    middle = sma(close, period)
    rolling_std = close.rolling(window=period, min_periods=period).std()
    upper = middle + (rolling_std * std_dev)
    lower = middle - (rolling_std * std_dev)

    bandwidth = (upper - lower) / middle
    percent_b = (close - lower) / (upper - lower)

    return upper, middle, lower, bandwidth, percent_b


# =============================================================================
# ATR (Average True Range)
# =============================================================================

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's ATR."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


# =============================================================================
# OBV (On-Balance Volume)
# =============================================================================

def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume."""
    direction = np.sign(close.diff())
    direction.iloc[0] = 0
    return (volume * direction).cumsum()


# =============================================================================
# Stochastic Oscillator
# =============================================================================

def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               k_period: int = 14, d_period: int = 3):
    """
    Returns: (%K, %D)
    """
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()
    k = 100.0 * (close - lowest_low) / (highest_high - lowest_low)
    d = sma(k, d_period)
    return k, d


# =============================================================================
# Keltner Channels (for TTM Squeeze detection)
# =============================================================================

def keltner_channels(high: pd.Series, low: pd.Series, close: pd.Series,
                     period: int = 20, multiplier: float = 1.5):
    """
    Returns: (upper, middle, lower)
    """
    middle = ema(close, period)
    atr_val = atr(high, low, close, period)
    upper = middle + (atr_val * multiplier)
    lower = middle - (atr_val * multiplier)
    return upper, middle, lower


# =============================================================================
# TTM Squeeze
# =============================================================================

def ttm_squeeze(high: pd.Series, low: pd.Series, close: pd.Series,
                bb_period: int = 20, bb_std: float = 2.0,
                kc_period: int = 20, kc_mult: float = 1.5):
    """
    TTM Squeeze: Bollinger Bands inside Keltner Channels.
    Returns: (squeeze_on: bool Series, squeeze_fire: bool Series)
    """
    bb_upper, _, bb_lower, _, _ = bollinger_bands(close, bb_period, bb_std)
    kc_upper, _, kc_lower = keltner_channels(high, low, close, kc_period, kc_mult)

    squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
    squeeze_fire = squeeze_on.shift(1).fillna(False) & ~squeeze_on

    return squeeze_on, squeeze_fire


# =============================================================================
# Support / Resistance Detection
# =============================================================================

def find_swing_points(high: pd.Series, low: pd.Series, order: int = 5):
    """
    Find swing highs and swing lows using local extrema.
    Returns: (swing_highs: Series, swing_lows: Series) with NaN where not a swing point.
    """
    swing_highs = pd.Series(np.nan, index=high.index)
    swing_lows = pd.Series(np.nan, index=low.index)

    for i in range(order, len(high) - order):
        # Swing High: higher than `order` bars on both sides
        if all(high.iloc[i] >= high.iloc[i - j] for j in range(1, order + 1)) and \
           all(high.iloc[i] >= high.iloc[i + j] for j in range(1, order + 1)):
            swing_highs.iloc[i] = high.iloc[i]

        # Swing Low: lower than `order` bars on both sides
        if all(low.iloc[i] <= low.iloc[i - j] for j in range(1, order + 1)) and \
           all(low.iloc[i] <= low.iloc[i + j] for j in range(1, order + 1)):
            swing_lows.iloc[i] = low.iloc[i]

    return swing_highs, swing_lows


# =============================================================================
# Candlestick Patterns
# =============================================================================

def detect_candlestick_patterns(open_: pd.Series, high: pd.Series,
                                low: pd.Series, close: pd.Series) -> pd.DataFrame:
    """
    Detect key candlestick patterns for swing trading.
    Returns DataFrame with boolean columns for each pattern.
    """
    body = close - open_
    body_abs = body.abs()
    upper_shadow = high - pd.concat([close, open_], axis=1).max(axis=1)
    lower_shadow = pd.concat([close, open_], axis=1).min(axis=1) - low
    avg_body = body_abs.rolling(20).mean()

    patterns = pd.DataFrame(index=close.index)

    # Bullish Engulfing
    prev_bearish = body.shift(1) < 0
    curr_bullish = body > 0
    patterns['bullish_engulfing'] = (
        prev_bearish & curr_bullish &
        (open_ <= close.shift(1)) &
        (close >= open_.shift(1)) &
        (body_abs > body_abs.shift(1))
    )

    # Bearish Engulfing
    prev_bullish = body.shift(1) > 0
    curr_bearish = body < 0
    patterns['bearish_engulfing'] = (
        prev_bullish & curr_bearish &
        (open_ >= close.shift(1)) &
        (close <= open_.shift(1)) &
        (body_abs > body_abs.shift(1))
    )

    # Hammer (bullish reversal)
    patterns['hammer'] = (
        (lower_shadow >= 2 * body_abs) &
        (upper_shadow < body_abs * 0.5) &
        (body_abs > 0)
    )

    # Shooting Star (bearish reversal)
    patterns['shooting_star'] = (
        (upper_shadow >= 2 * body_abs) &
        (lower_shadow < body_abs * 0.5) &
        (body_abs > 0)
    )

    # Doji
    patterns['doji'] = body_abs < (avg_body * 0.1)

    return patterns


# =============================================================================
# RSI Divergence Detection
# =============================================================================

def detect_rsi_divergence(close: pd.Series, rsi_values: pd.Series,
                          order: int = 5, lookback: int = 60):
    """
    Detect bullish and bearish RSI divergences.
    Returns: list of (type, date, price, rsi) tuples
    """
    divergences = []
    close_arr = close.values
    rsi_arr = rsi_values.values

    # Find local minima for bullish divergence
    for i in range(order, min(len(close_arr) - order, lookback)):
        idx = len(close_arr) - 1 - i
        if idx < order:
            break

        is_low = True
        for j in range(1, order + 1):
            if idx - j < 0 or idx + j >= len(close_arr):
                is_low = False
                break
            if close_arr[idx] > close_arr[idx - j] or close_arr[idx] > close_arr[idx + j]:
                is_low = False
                break

        if not is_low:
            continue

        # Look for a previous low
        for k in range(i + order, min(i + lookback, len(close_arr) - order)):
            prev_idx = len(close_arr) - 1 - k
            if prev_idx < order:
                break

            is_prev_low = True
            for j in range(1, order + 1):
                if prev_idx - j < 0 or prev_idx + j >= len(close_arr):
                    is_prev_low = False
                    break
                if close_arr[prev_idx] > close_arr[prev_idx - j] or \
                   close_arr[prev_idx] > close_arr[prev_idx + j]:
                    is_prev_low = False
                    break

            if not is_prev_low:
                continue

            # Bullish divergence: price lower low, RSI higher low
            if close_arr[idx] < close_arr[prev_idx] and \
               rsi_arr[idx] > rsi_arr[prev_idx]:
                divergences.append(('bullish', close.index[idx],
                                    close_arr[idx], rsi_arr[idx]))
                break

            # Bearish divergence logic (on highs) would go here
            break

    return divergences


# =============================================================================
# Build all indicators for a DataFrame
# =============================================================================

def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all technical indicators to a DataFrame with OHLCV columns.
    Expects columns: Open, High, Low, Close, Volume
    """
    df = df.copy()

    # Moving Averages
    df['EMA_5'] = ema(df['Close'], 5)
    df['EMA_20'] = ema(df['Close'], 20)
    df['SMA_50'] = sma(df['Close'], 50)
    df['SMA_200'] = sma(df['Close'], 200)

    # RSI
    df['RSI_14'] = rsi(df['Close'], 14)
    df['RSI_7'] = rsi(df['Close'], 7)

    # MACD
    df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = macd(df['Close'])

    # Bollinger Bands
    df['BB_Upper'], df['BB_Middle'], df['BB_Lower'], df['BB_Width'], df['BB_PctB'] = \
        bollinger_bands(df['Close'])

    # ATR
    df['ATR_14'] = atr(df['High'], df['Low'], df['Close'], 14)

    # OBV
    df['OBV'] = obv(df['Close'], df['Volume'])

    # Stochastic
    df['Stoch_K'], df['Stoch_D'] = stochastic(df['High'], df['Low'], df['Close'])

    # Volume SMA
    df['Vol_SMA_20'] = sma(df['Volume'], 20)

    # TTM Squeeze
    df['Squeeze_On'], df['Squeeze_Fire'] = ttm_squeeze(
        df['High'], df['Low'], df['Close']
    )

    # Candlestick Patterns
    patterns = detect_candlestick_patterns(df['Open'], df['High'], df['Low'], df['Close'])
    df = pd.concat([df, patterns], axis=1)

    return df
