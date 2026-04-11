# Swing Trading Analysis Tool - Strategy Guide

## Overview

This tool combines **technical analysis** and **thematic/sector analysis** to generate buy/sell signals for swing trading (holding period: 2-10 days).

## Architecture

```
swing_trading/
  indicators.py      # Technical indicator calculations (SMA, EMA, RSI, MACD, BB, ATR, etc.)
  signals.py         # Signal scoring engine (combines indicators into buy/sell scores)
  sector_analysis.py # Sector rotation & thematic stock analysis
  sample_data.py     # Sample data generator for testing
  analyze.py         # Main CLI entry point
```

## Usage

```bash
# Demo mode (no internet required)
python -m swing_trading.analyze --demo

# Analyze a real stock (requires internet + yfinance)
python -m swing_trading.analyze AAPL --history 10

# Multiple stocks
python -m swing_trading.analyze AAPL MSFT GOOGL NVDA

# With position sizing
python -m swing_trading.analyze AAPL --account 1000000 --risk 0.02

# Watchlist scan
python -m swing_trading.analyze --watchlist AAPL,MSFT,GOOGL,NVDA,TSLA,AMZN,META

# Sector rotation analysis
python -m swing_trading.analyze --sectors
python -m swing_trading.analyze --themes
python -m swing_trading.analyze --japan-sectors

# From CSV file
python -m swing_trading.analyze --csv data.csv --name "My Stock"
```

## Signal Scoring System

The engine scores each day on 7 components (range: approximately -8 to +8):

| Component | Weight | Description |
|-----------|--------|-------------|
| Trend Regime | -2 to +2 | MA alignment (50SMA vs 200SMA vs Price) |
| EMA Pullback | -1 to +1 | Price bouncing off 20 EMA |
| RSI | -1 to +1 | Overbought/oversold with trend context |
| MACD | -1 to +1 | Crossovers and momentum state |
| Volume | -1 to +1 | Volume confirmation of moves |
| Bollinger Bands | -1 to +1 | Band position + squeeze detection |
| Candlestick | -1 to +1 | Pattern recognition at key levels |

### Signal Thresholds

| Score | Signal | Action |
|-------|--------|--------|
| >= 3 | STRONG BUY | High-conviction entry |
| >= 2 | BUY | Favorable entry |
| -1 to +1 | HOLD | No clear edge |
| <= -2 | SELL | Exit longs / tighten stops |
| <= -3 | STRONG SELL | Exit immediately |

## Trading Workflow with Claude Code

### Step 1: Sector Scan
```bash
python -m swing_trading.analyze --sectors --themes
```
Identify the strongest sectors outperforming SPY.

### Step 2: Stock Selection
Focus on stocks within the top-performing sectors. Look for high relative strength.

### Step 3: Signal Analysis
```bash
python -m swing_trading.analyze TICKER --history 10 --account YOUR_ACCOUNT
```
Look for scores >= 2 with multiple confirming factors.

### Step 4: Risk Management
- Always use the ATR-based stop loss (2x ATR)
- Never risk more than 2% of account per trade
- Target minimum 1:2 risk-reward ratio
- Keep total portfolio heat under 10%

### Step 5: Exit Strategy
- Hit stop loss -> exit immediately
- Hit profit target (1:2 or 1:3 RR) -> take profits or trail stop
- Signal score drops to <= -2 -> consider exiting
- Trail stop using 10 EMA or 1.5x ATR

## Technical Indicators Used

- **SMA (50, 200)**: Trend identification
- **EMA (5, 20)**: Entry timing
- **RSI (14)**: Momentum / overbought-oversold
- **MACD (12, 26, 9)**: Trend momentum
- **Bollinger Bands (20, 2)**: Volatility and mean reversion
- **ATR (14)**: Volatility for stop loss placement
- **OBV**: Volume trend confirmation
- **Stochastic (14, 3)**: Additional momentum
- **TTM Squeeze**: Volatility breakout detection
- **Candlestick Patterns**: Engulfing, Hammer, Shooting Star, Doji

## Disclaimer

This tool is for **educational purposes only**. It is NOT financial advice.
Always do your own research and consult a licensed financial advisor before trading.
Past performance does not guarantee future results.
