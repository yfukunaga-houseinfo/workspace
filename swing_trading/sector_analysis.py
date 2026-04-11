"""
Sector / Thematic Stock Analysis for Swing Trading
- Sector rotation ranking
- Relative strength calculation
- Theme identification
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta


# =============================================================================
# Sector ETF Definitions
# =============================================================================

SECTOR_ETFS = {
    # S&P 500 Sectors (SPDR)
    'XLK': 'Technology',
    'XLF': 'Financials',
    'XLE': 'Energy',
    'XLV': 'Healthcare',
    'XLI': 'Industrials',
    'XLY': 'Consumer Discretionary',
    'XLP': 'Consumer Staples',
    'XLU': 'Utilities',
    'XLB': 'Materials',
    'XLRE': 'Real Estate',
    'XLC': 'Communication Services',
}

THEME_ETFS = {
    # Thematic ETFs
    'BOTZ': 'AI / Robotics',
    'ARKK': 'Disruptive Innovation',
    'ICLN': 'Clean Energy',
    'IBB':  'Biotech',
    'HACK': 'Cybersecurity',
    'SOXX': 'Semiconductors',
    'TAN':  'Solar Energy',
    'LIT':  'Lithium / Battery',
    'DRIV': 'EV / Autonomous',
    'BLOK': 'Blockchain',
}

# Japanese market sectors (TOPIX sector ETFs)
JAPAN_SECTOR_ETFS = {
    '1615.T': 'TOPIX Banks',
    '1617.T': 'TOPIX Foods',
    '1618.T': 'TOPIX Energy',
    '1619.T': 'TOPIX Construction',
    '1620.T': 'TOPIX Materials & Chemicals',
    '1621.T': 'TOPIX Pharma',
    '1623.T': 'TOPIX Steel & Nonferrous',
    '1624.T': 'TOPIX Machinery',
    '1625.T': 'TOPIX Electric & Precision',
    '1626.T': 'TOPIX Transportation',
    '1627.T': 'TOPIX Trading & Retail',
    '1628.T': 'TOPIX Real Estate',
    '1633.T': 'TOPIX IT & Services',
}

# Popular Japanese swing trading stocks by theme
JAPAN_THEME_STOCKS = {
    'AI / Semiconductor': ['6857.T', '6723.T', '6526.T', '4063.T', '6920.T'],
    'Inbound / Tourism':  ['9603.T', '9022.T', '9020.T', '2809.T'],
    'Defense':            ['7011.T', '7012.T', '6208.T'],
    'EV / Battery':       ['6752.T', '6981.T', '7203.T'],
    'DX / Cloud':         ['4755.T', '9984.T', '4478.T'],
}


def download_prices(tickers: list, period: str = "6mo") -> pd.DataFrame:
    """Download adjusted close prices for multiple tickers."""
    try:
        data = yf.download(tickers, period=period, progress=False)
        if 'Close' in data.columns or (isinstance(data.columns, pd.MultiIndex) and 'Close' in data.columns.get_level_values(0)):
            if isinstance(data.columns, pd.MultiIndex):
                return data['Close']
            else:
                return data[['Close']].rename(columns={'Close': tickers[0]})
        return data
    except Exception as e:
        print(f"  [Warning] Data download failed: {e}")
        return pd.DataFrame()


def rank_sectors_by_momentum(etf_dict: dict, period_days: int = 63,
                              benchmark: str = 'SPY') -> pd.DataFrame:
    """
    Rank sectors by momentum (rate of change).
    Returns DataFrame with sector name, return, and relative strength vs benchmark.
    """
    tickers = list(etf_dict.keys()) + [benchmark]
    prices = download_prices(tickers, period="6mo")

    if prices.empty:
        return pd.DataFrame()

    # Calculate returns over the period
    returns = {}
    for ticker in etf_dict.keys():
        if ticker in prices.columns:
            series = prices[ticker].dropna()
            if len(series) > period_days:
                ret = (series.iloc[-1] / series.iloc[-period_days] - 1) * 100
                returns[ticker] = ret

    # Benchmark return
    bench_return = 0
    if benchmark in prices.columns:
        bench_series = prices[benchmark].dropna()
        if len(bench_series) > period_days:
            bench_return = (bench_series.iloc[-1] / bench_series.iloc[-period_days] - 1) * 100

    # Build result
    results = []
    for ticker, ret in returns.items():
        results.append({
            'Ticker': ticker,
            'Sector': etf_dict[ticker],
            'Return_%': round(ret, 2),
            'vs_Benchmark_%': round(ret - bench_return, 2),
            'Outperforming': ret > bench_return
        })

    df = pd.DataFrame(results).sort_values('Return_%', ascending=False).reset_index(drop=True)
    df.index = df.index + 1  # 1-based ranking
    df.index.name = 'Rank'
    return df


def calculate_relative_strength(stock_ticker: str, benchmark_ticker: str = 'SPY',
                                 period: str = "6mo") -> pd.DataFrame:
    """
    Calculate Mansfield Relative Strength (stock/benchmark ratio).
    Returns DataFrame with RS line and its SMA.
    """
    prices = download_prices([stock_ticker, benchmark_ticker], period=period)
    if prices.empty:
        return pd.DataFrame()

    rs = prices[stock_ticker] / prices[benchmark_ticker]
    rs_sma = rs.rolling(50).mean()

    result = pd.DataFrame({
        'Price': prices[stock_ticker],
        'RS_Line': rs,
        'RS_SMA50': rs_sma,
        'RS_Rising': rs > rs_sma
    })
    return result


def scan_sector_leaders(sector_etf: str, stock_tickers: list,
                         lookback_days: int = 20) -> pd.DataFrame:
    """
    Find leading stocks within a sector by relative strength.
    """
    all_tickers = [sector_etf] + stock_tickers
    prices = download_prices(all_tickers, period="3mo")
    if prices.empty:
        return pd.DataFrame()

    results = []
    etf_series = prices[sector_etf].dropna()
    if len(etf_series) <= lookback_days:
        return pd.DataFrame()

    etf_return = (etf_series.iloc[-1] / etf_series.iloc[-lookback_days] - 1) * 100

    for ticker in stock_tickers:
        if ticker not in prices.columns:
            continue
        series = prices[ticker].dropna()
        if len(series) <= lookback_days:
            continue

        stock_return = (series.iloc[-1] / series.iloc[-lookback_days] - 1) * 100
        rs_ratio = (1 + stock_return / 100) / (1 + etf_return / 100)

        results.append({
            'Ticker': ticker,
            'Return_%': round(stock_return, 2),
            'Sector_Return_%': round(etf_return, 2),
            'RS_Ratio': round(rs_ratio, 3),
            'Outperforming': rs_ratio > 1.0
        })

    return pd.DataFrame(results).sort_values('RS_Ratio', ascending=False).reset_index(drop=True)


def identify_sector_rotation_phase(sector_rankings: pd.DataFrame) -> str:
    """
    Based on Sam Stovall's sector rotation model, estimate the current
    business cycle phase from sector performance.
    """
    if sector_rankings.empty:
        return "Unknown"

    top_sectors = sector_rankings.head(3)['Sector'].tolist()

    # Simplified phase detection
    early_cycle = {'Financials', 'Consumer Discretionary', 'Industrials', 'Real Estate'}
    mid_cycle = {'Technology', 'Communication Services', 'Semiconductors',
                 'AI / Robotics', 'Disruptive Innovation'}
    late_cycle = {'Energy', 'Materials', 'Healthcare'}
    recession = {'Utilities', 'Consumer Staples', 'Healthcare'}

    scores = {'Early Recovery': 0, 'Mid-Cycle Growth': 0,
              'Late Cycle': 0, 'Recession / Defensive': 0}

    for sector in top_sectors:
        if sector in early_cycle:
            scores['Early Recovery'] += 1
        if sector in mid_cycle:
            scores['Mid-Cycle Growth'] += 1
        if sector in late_cycle:
            scores['Late Cycle'] += 1
        if sector in recession:
            scores['Recession / Defensive'] += 1

    phase = max(scores, key=scores.get)
    confidence = scores[phase] / len(top_sectors) * 100
    return f"{phase} (confidence: {confidence:.0f}%)"
