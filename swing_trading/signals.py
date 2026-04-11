"""
Signal Scoring Engine for Swing Trading
Combines multiple technical indicators into a unified buy/sell scoring system.
"""

import pandas as pd
import numpy as np
from .indicators import add_all_indicators, detect_rsi_divergence


# =============================================================================
# Signal Score Components
# =============================================================================

def score_trend_regime(df: pd.DataFrame) -> pd.Series:
    """
    Trend regime filter using moving average alignment.
    +2: Strong bullish (price > 50SMA > 200SMA)
    +1: Mild bullish (price > 50SMA)
    -1: Mild bearish (price < 50SMA)
    -2: Strong bearish (price < 50SMA < 200SMA)
    """
    score = pd.Series(0, index=df.index, dtype=float)

    bullish_regime = (df['SMA_50'] > df['SMA_200']) & (df['Close'] > df['SMA_50'])
    mild_bull = (~bullish_regime) & (df['Close'] > df['SMA_50'])
    bearish_regime = (df['SMA_50'] < df['SMA_200']) & (df['Close'] < df['SMA_50'])
    mild_bear = (~bearish_regime) & (df['Close'] < df['SMA_50'])

    score[bullish_regime] = 2
    score[mild_bull] = 1
    score[bearish_regime] = -2
    score[mild_bear] = -1

    return score


def score_ema_pullback(df: pd.DataFrame) -> pd.Series:
    """
    EMA pullback: price bouncing off 20 EMA in a trend.
    +1: Bullish bounce off EMA20
    -1: Bearish rejection at EMA20
    """
    score = pd.Series(0, index=df.index, dtype=float)

    # Price touched or crossed below EMA20 then recovered
    bullish_bounce = (
        (df['Low'] <= df['EMA_20'] * 1.01) &  # Touched near EMA
        (df['Close'] > df['EMA_20']) &          # Closed above
        (df['Close'] > df['Open'])               # Bullish candle
    )

    bearish_rejection = (
        (df['High'] >= df['EMA_20'] * 0.99) &
        (df['Close'] < df['EMA_20']) &
        (df['Close'] < df['Open'])
    )

    score[bullish_bounce] = 1
    score[bearish_rejection] = -1
    return score


def score_rsi(df: pd.DataFrame) -> pd.Series:
    """
    RSI scoring.
    +1: Oversold recovery (RSI 30-45 in uptrend)
    +0.5: Neutral-bullish zone (RSI 45-55)
    -1: Overbought (RSI > 70)
    -0.5: Overextended (RSI > 65)
    """
    score = pd.Series(0, index=df.index, dtype=float)

    oversold_recovery = df['RSI_14'].between(30, 45) & (df['Close'] > df['SMA_50'])
    neutral_bullish = df['RSI_14'].between(45, 55) & (df['Close'] > df['EMA_20'])
    overbought = df['RSI_14'] > 70
    overextended = df['RSI_14'].between(65, 70)
    deeply_oversold = df['RSI_14'] < 30

    score[oversold_recovery] = 1
    score[neutral_bullish] = 0.5
    score[overbought] = -1
    score[overextended] = -0.5
    score[deeply_oversold] = -0.5  # Could be trend breakdown

    return score


def score_macd(df: pd.DataFrame) -> pd.Series:
    """
    MACD signal scoring.
    +1: Bullish crossover (MACD crosses above signal)
    +0.5: MACD above zero and rising
    -1: Bearish crossover
    -0.5: MACD below zero and falling
    """
    score = pd.Series(0, index=df.index, dtype=float)

    # Crossover detection
    macd_cross_up = (df['MACD'] > df['MACD_Signal']) & (df['MACD'].shift(1) <= df['MACD_Signal'].shift(1))
    macd_cross_down = (df['MACD'] < df['MACD_Signal']) & (df['MACD'].shift(1) >= df['MACD_Signal'].shift(1))

    # Momentum state
    macd_bullish_momentum = (df['MACD'] > 0) & (df['MACD_Hist'] > df['MACD_Hist'].shift(1))
    macd_bearish_momentum = (df['MACD'] < 0) & (df['MACD_Hist'] < df['MACD_Hist'].shift(1))

    score[macd_cross_up] = 1
    score[macd_cross_down] = -1
    score[macd_bullish_momentum & ~macd_cross_up] = 0.5
    score[macd_bearish_momentum & ~macd_cross_down] = -0.5

    return score


def score_volume(df: pd.DataFrame) -> pd.Series:
    """
    Volume confirmation scoring.
    +1: Above-average volume on up day
    +0.5: Volume dry-up on pullback (healthy consolidation)
    -1: Above-average volume on down day
    """
    score = pd.Series(0, index=df.index, dtype=float)

    high_volume = df['Volume'] > df['Vol_SMA_20'] * 1.5
    up_day = df['Close'] > df['Open']
    down_day = df['Close'] < df['Open']
    low_volume_pullback = (df['Volume'] < df['Vol_SMA_20'] * 0.7) & down_day

    score[high_volume & up_day] = 1
    score[high_volume & down_day] = -1
    score[low_volume_pullback] = 0.5

    return score


def score_bollinger(df: pd.DataFrame) -> pd.Series:
    """
    Bollinger Bands scoring.
    +1: Price near lower band in uptrend (mean reversion opportunity)
    +0.5: Squeeze firing (breakout imminent)
    -1: Price near upper band with overbought RSI
    """
    score = pd.Series(0, index=df.index, dtype=float)

    near_lower = df['BB_PctB'] < 0.2
    near_upper = df['BB_PctB'] > 0.8
    in_uptrend = df['Close'] > df['SMA_50']
    overbought_rsi = df['RSI_14'] > 65

    score[near_lower & in_uptrend] = 1
    score[near_upper & overbought_rsi] = -1
    score[df['Squeeze_Fire']] = 0.5

    return score


def score_candlesticks(df: pd.DataFrame) -> pd.Series:
    """
    Candlestick pattern scoring.
    +1: Bullish reversal pattern at support
    -1: Bearish reversal pattern at resistance
    """
    score = pd.Series(0, index=df.index, dtype=float)

    near_support = df['BB_PctB'] < 0.3  # Near lower Bollinger as proxy for support
    near_resistance = df['BB_PctB'] > 0.7

    bullish_pattern = df.get('bullish_engulfing', False) | df.get('hammer', False)
    bearish_pattern = df.get('bearish_engulfing', False) | df.get('shooting_star', False)

    if isinstance(bullish_pattern, pd.Series):
        score[bullish_pattern & near_support] = 1
    if isinstance(bearish_pattern, pd.Series):
        score[bearish_pattern & near_resistance] = -1

    return score


# =============================================================================
# Combined Signal Engine
# =============================================================================

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate comprehensive buy/sell signals with confidence scoring.

    Signal Score Range: approximately -8 to +8
    - Score >= 3: Strong Buy signal
    - Score >= 2: Buy signal
    - Score between -1 and 1: Neutral / Hold
    - Score <= -2: Sell signal
    - Score <= -3: Strong Sell signal
    """
    # First add all technical indicators
    df = add_all_indicators(df)

    # Calculate individual component scores
    df['Score_Trend'] = score_trend_regime(df)
    df['Score_EMA'] = score_ema_pullback(df)
    df['Score_RSI'] = score_rsi(df)
    df['Score_MACD'] = score_macd(df)
    df['Score_Volume'] = score_volume(df)
    df['Score_BB'] = score_bollinger(df)
    df['Score_Candle'] = score_candlesticks(df)

    # Total signal score
    df['Signal_Score'] = (
        df['Score_Trend'] +
        df['Score_EMA'] +
        df['Score_RSI'] +
        df['Score_MACD'] +
        df['Score_Volume'] +
        df['Score_BB'] +
        df['Score_Candle']
    )

    # Signal classification
    df['Signal'] = 'HOLD'
    df.loc[df['Signal_Score'] >= 3, 'Signal'] = 'STRONG BUY'
    df.loc[(df['Signal_Score'] >= 2) & (df['Signal_Score'] < 3), 'Signal'] = 'BUY'
    df.loc[(df['Signal_Score'] <= -3), 'Signal'] = 'STRONG SELL'
    df.loc[(df['Signal_Score'] <= -2) & (df['Signal_Score'] > -3), 'Signal'] = 'SELL'

    return df


# =============================================================================
# Position Sizing & Risk Management
# =============================================================================

def calculate_position_size(account_equity: float, risk_pct: float,
                            entry_price: float, atr_value: float,
                            atr_multiplier: float = 2.0) -> dict:
    """
    Calculate position size based on ATR-based stop loss.

    Args:
        account_equity: Total account value
        risk_pct: Max risk per trade (e.g., 0.02 for 2%)
        entry_price: Planned entry price
        atr_value: Current ATR(14) value
        atr_multiplier: ATR multiplier for stop loss distance

    Returns:
        dict with position sizing details
    """
    stop_distance = atr_value * atr_multiplier
    stop_loss = entry_price - stop_distance
    risk_per_share = stop_distance
    dollar_risk = account_equity * risk_pct
    shares = int(dollar_risk / risk_per_share) if risk_per_share > 0 else 0
    position_value = shares * entry_price
    position_pct = (position_value / account_equity * 100) if account_equity > 0 else 0

    return {
        'shares': shares,
        'entry_price': round(entry_price, 2),
        'stop_loss': round(stop_loss, 2),
        'stop_distance': round(stop_distance, 2),
        'target_1R': round(entry_price + stop_distance, 2),      # 1:1 R:R
        'target_2R': round(entry_price + stop_distance * 2, 2),  # 1:2 R:R
        'target_3R': round(entry_price + stop_distance * 3, 2),  # 1:3 R:R
        'position_value': round(position_value, 2),
        'position_pct': round(position_pct, 1),
        'dollar_risk': round(dollar_risk, 2),
        'risk_reward_ratio': '1:3 (recommended minimum 1:2)',
    }


# =============================================================================
# Summary Report Generator
# =============================================================================

def generate_analysis_report(ticker: str, df: pd.DataFrame) -> str:
    """Generate a human-readable analysis report for the latest data."""
    if df.empty or len(df) < 200:
        return f"Insufficient data for {ticker} (need at least 200 bars)"

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    report = []
    report.append(f"\n{'='*60}")
    report.append(f"  SWING TRADE ANALYSIS: {ticker}")
    report.append(f"  Date: {df.index[-1].strftime('%Y-%m-%d') if hasattr(df.index[-1], 'strftime') else df.index[-1]}")
    report.append(f"{'='*60}")

    # Price Summary
    report.append(f"\n--- Price Summary ---")
    report.append(f"  Close:    ${latest['Close']:.2f}")
    report.append(f"  Change:   {((latest['Close'] / prev['Close']) - 1) * 100:+.2f}%")
    report.append(f"  EMA(20):  ${latest['EMA_20']:.2f}  {'(above)' if latest['Close'] > latest['EMA_20'] else '(below)'}")
    report.append(f"  SMA(50):  ${latest['SMA_50']:.2f}  {'(above)' if latest['Close'] > latest['SMA_50'] else '(below)'}")
    report.append(f"  SMA(200): ${latest['SMA_200']:.2f}  {'(above)' if latest['Close'] > latest['SMA_200'] else '(below)'}")

    # Trend Status
    report.append(f"\n--- Trend Status ---")
    if latest['SMA_50'] > latest['SMA_200']:
        report.append(f"  MA Alignment: BULLISH (Golden Cross active)")
    else:
        report.append(f"  MA Alignment: BEARISH (Death Cross active)")

    trend_score = latest['Score_Trend']
    trend_map = {2: 'Strong Uptrend', 1: 'Mild Uptrend', 0: 'Neutral',
                 -1: 'Mild Downtrend', -2: 'Strong Downtrend'}
    report.append(f"  Trend Score: {trend_score:+.0f} ({trend_map.get(int(trend_score), 'Neutral')})")

    # Indicators
    report.append(f"\n--- Key Indicators ---")
    report.append(f"  RSI(14):       {latest['RSI_14']:.1f}  ", )
    if latest['RSI_14'] > 70:
        report[-1] += "[OVERBOUGHT]"
    elif latest['RSI_14'] < 30:
        report[-1] += "[OVERSOLD]"
    elif latest['RSI_14'] < 45:
        report[-1] += "[Approaching oversold]"
    else:
        report[-1] += "[Neutral zone]"

    report.append(f"  MACD:          {latest['MACD']:.3f}")
    report.append(f"  MACD Signal:   {latest['MACD_Signal']:.3f}")
    macd_state = "BULLISH" if latest['MACD'] > latest['MACD_Signal'] else "BEARISH"
    report.append(f"  MACD Status:   {macd_state} crossover")

    report.append(f"  BB %B:         {latest['BB_PctB']:.2f}  ", )
    if latest['BB_PctB'] > 0.8:
        report[-1] += "[Near upper band]"
    elif latest['BB_PctB'] < 0.2:
        report[-1] += "[Near lower band]"
    else:
        report[-1] += "[Middle zone]"

    if latest['Squeeze_On']:
        report.append(f"  TTM Squeeze:   ON (volatility contracting - breakout pending)")
    elif latest['Squeeze_Fire']:
        report.append(f"  TTM Squeeze:   FIRED! (breakout beginning)")
    else:
        report.append(f"  TTM Squeeze:   Off")

    report.append(f"  ATR(14):       ${latest['ATR_14']:.2f} ({latest['ATR_14']/latest['Close']*100:.1f}% of price)")

    # Volume
    vol_ratio = latest['Volume'] / latest['Vol_SMA_20'] if latest['Vol_SMA_20'] > 0 else 0
    report.append(f"\n--- Volume ---")
    report.append(f"  Volume:        {latest['Volume']:,.0f}")
    report.append(f"  Avg Vol (20):  {latest['Vol_SMA_20']:,.0f}")
    report.append(f"  Volume Ratio:  {vol_ratio:.2f}x  ", )
    if vol_ratio > 1.5:
        report[-1] += "[HIGH - significant activity]"
    elif vol_ratio < 0.7:
        report[-1] += "[LOW - quiet/consolidating]"
    else:
        report[-1] += "[Normal]"

    # Candlestick Patterns
    patterns_found = []
    for pat in ['bullish_engulfing', 'bearish_engulfing', 'hammer', 'shooting_star', 'doji']:
        if pat in latest.index and latest[pat]:
            patterns_found.append(pat.replace('_', ' ').title())

    if patterns_found:
        report.append(f"\n--- Candlestick Patterns ---")
        for p in patterns_found:
            report.append(f"  * {p}")

    # Signal Score Breakdown
    report.append(f"\n--- Signal Score Breakdown ---")
    report.append(f"  Trend:        {latest['Score_Trend']:+.1f}")
    report.append(f"  EMA Pullback: {latest['Score_EMA']:+.1f}")
    report.append(f"  RSI:          {latest['Score_RSI']:+.1f}")
    report.append(f"  MACD:         {latest['Score_MACD']:+.1f}")
    report.append(f"  Volume:       {latest['Score_Volume']:+.1f}")
    report.append(f"  Bollinger:    {latest['Score_BB']:+.1f}")
    report.append(f"  Candlestick:  {latest['Score_Candle']:+.1f}")
    report.append(f"  {'─'*30}")
    report.append(f"  TOTAL SCORE:  {latest['Signal_Score']:+.1f}")

    # Final Verdict
    signal = latest['Signal']
    report.append(f"\n{'='*60}")
    report.append(f"  VERDICT: >>> {signal} <<<")

    if signal in ('STRONG BUY', 'BUY'):
        report.append(f"\n  Suggested Entry: ~${latest['Close']:.2f}")
        report.append(f"  Stop Loss (2xATR): ${latest['Close'] - latest['ATR_14'] * 2:.2f}")
        report.append(f"  Target 1 (1:2 RR): ${latest['Close'] + latest['ATR_14'] * 4:.2f}")
        report.append(f"  Target 2 (1:3 RR): ${latest['Close'] + latest['ATR_14'] * 6:.2f}")
    elif signal in ('STRONG SELL', 'SELL'):
        report.append(f"\n  Consider exiting long positions or tightening stops.")
        report.append(f"  Short entry stop: ${latest['Close'] + latest['ATR_14'] * 2:.2f}")
    else:
        report.append(f"\n  No clear edge. Wait for higher-conviction setup.")

    report.append(f"{'='*60}")

    # Disclaimer
    report.append(f"\n  [DISCLAIMER] This is technical analysis output for educational")
    report.append(f"  purposes only. NOT financial advice. Always do your own research")
    report.append(f"  and consult a licensed financial advisor before trading.")

    return '\n'.join(report)
