#!/usr/bin/env python3
"""
Swing Trading Analysis Tool - Main Entry Point

Usage:
    # Analyze a single stock
    python -m swing_trading.analyze AAPL

    # Analyze multiple stocks
    python -m swing_trading.analyze AAPL MSFT GOOGL NVDA

    # Analyze from CSV file
    python -m swing_trading.analyze --csv data.csv --name "My Stock"

    # Run with sample data (no internet needed)
    python -m swing_trading.analyze --demo

    # Sector rotation analysis
    python -m swing_trading.analyze --sectors

    # Theme analysis (US)
    python -m swing_trading.analyze --themes

    # Japanese market sectors
    python -m swing_trading.analyze --japan-sectors

    # Full analysis with position sizing
    python -m swing_trading.analyze AAPL --account 1000000 --risk 0.02

    # Scan recent signals across a watchlist
    python -m swing_trading.analyze --watchlist AAPL,MSFT,GOOGL,NVDA,TSLA,AMZN,META

    # Show signal history for last N days
    python -m swing_trading.analyze AAPL --history 10
"""

import sys
import argparse
import pandas as pd

from .signals import generate_signals, generate_analysis_report, calculate_position_size
from .sample_data import generate_sample_ohlcv, generate_multi_stock_samples, load_csv_data

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False


def analyze_stock(ticker: str, account_equity: float = None,
                  risk_pct: float = 0.02, history_days: int = 0,
                  data: pd.DataFrame = None):
    """Run full swing trading analysis on a single stock."""
    if data is None:
        if not HAS_YFINANCE:
            print(f"  yfinance not available. Use --demo or --csv instead.")
            return None
        print(f"\nDownloading data for {ticker}...")
        try:
            data = yf.download(ticker, period="1y", progress=False)
        except Exception as e:
            print(f"  Error downloading {ticker}: {e}")
            return None

        if data.empty:
            print(f"  No data available for {ticker}")
            return None

        # Flatten MultiIndex columns if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

    print(f"\n  Loaded {len(data)} bars ({data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')})")

    # Generate signals
    df = generate_signals(data)

    # Print report
    report = generate_analysis_report(ticker, df)
    print(report)

    # Position sizing
    if account_equity:
        latest = df.iloc[-1]
        pos = calculate_position_size(
            account_equity=account_equity,
            risk_pct=risk_pct,
            entry_price=latest['Close'],
            atr_value=latest['ATR_14']
        )
        print(f"\n--- Position Sizing (Account: ${account_equity:,.0f}, Risk: {risk_pct*100:.1f}%) ---")
        print(f"  Shares:         {pos['shares']}")
        print(f"  Position Value: ${pos['position_value']:,.2f} ({pos['position_pct']:.1f}% of account)")
        print(f"  Stop Loss:      ${pos['stop_loss']:.2f} (${pos['stop_distance']:.2f} below entry)")
        print(f"  Dollar Risk:    ${pos['dollar_risk']:,.2f}")
        print(f"  Target (1:1):   ${pos['target_1R']:.2f}")
        print(f"  Target (1:2):   ${pos['target_2R']:.2f}")
        print(f"  Target (1:3):   ${pos['target_3R']:.2f}")
        print(f"  Risk/Reward:    {pos['risk_reward_ratio']}")

    # Signal history
    if history_days > 0:
        print(f"\n--- Signal History (last {history_days} days) ---")
        recent = df.tail(history_days)[['Close', 'Signal_Score', 'Signal', 'RSI_14', 'MACD', 'Volume']]
        recent_display = recent.copy()
        recent_display['Close'] = recent_display['Close'].apply(lambda x: f"${x:.2f}")
        recent_display['Signal_Score'] = recent_display['Signal_Score'].apply(lambda x: f"{x:+.1f}")
        recent_display['RSI_14'] = recent_display['RSI_14'].apply(lambda x: f"{x:.1f}")
        recent_display['MACD'] = recent_display['MACD'].apply(lambda x: f"{x:.3f}")
        recent_display['Volume'] = recent_display['Volume'].apply(lambda x: f"{x:,.0f}")
        print(recent_display.to_string())

    return df


def scan_watchlist(tickers: list):
    """Quick scan of multiple tickers for current signals."""
    print(f"\n{'='*70}")
    print(f"  WATCHLIST SCAN - {len(tickers)} stocks")
    print(f"{'='*70}")

    results = []
    for ticker in tickers:
        try:
            data = yf.download(ticker, period="1y", progress=False)
            if data.empty:
                continue
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            df = generate_signals(data)
            if len(df) < 200:
                continue

            latest = df.iloc[-1]
            results.append({
                'Ticker': ticker,
                'Price': f"${latest['Close']:.2f}",
                'Score': f"{latest['Signal_Score']:+.1f}",
                'Signal': latest['Signal'],
                'RSI': f"{latest['RSI_14']:.0f}",
                'MACD': 'Bull' if latest['MACD'] > latest['MACD_Signal'] else 'Bear',
                'Trend': 'Up' if latest['SMA_50'] > latest['SMA_200'] else 'Down',
                'Squeeze': 'ON' if latest['Squeeze_On'] else ('FIRE' if latest['Squeeze_Fire'] else '-'),
            })
        except Exception as e:
            print(f"  Warning: {ticker} - {e}")

    if results:
        result_df = pd.DataFrame(results)
        result_df = result_df.sort_values('Score', ascending=False, key=lambda x: x.str.replace('+', '').astype(float))
        result_df.index = range(1, len(result_df) + 1)
        result_df.index.name = '#'
        print(f"\n{result_df.to_string()}")

        # Highlight actionable signals
        buys = [r for r in results if 'BUY' in r['Signal']]
        sells = [r for r in results if 'SELL' in r['Signal']]

        if buys:
            print(f"\n  BUY candidates: {', '.join(r['Ticker'] for r in buys)}")
        if sells:
            print(f"  SELL candidates: {', '.join(r['Ticker'] for r in sells)}")
        if not buys and not sells:
            print(f"\n  No strong signals currently. All positions neutral.")
    else:
        print("  No valid data retrieved.")

    print(f"\n  [DISCLAIMER] Educational purposes only. NOT financial advice.\n")


def run_sector_analysis(etf_dict: dict, title: str, benchmark: str = 'SPY'):
    """Run sector rotation analysis."""
    from .sector_analysis import rank_sectors_by_momentum, identify_sector_rotation_phase

    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

    for period_label, period_days in [("1 Month", 21), ("3 Months", 63)]:
        print(f"\n--- {period_label} Momentum Ranking ---")
        rankings = rank_sectors_by_momentum(etf_dict, period_days, benchmark)
        if not rankings.empty:
            print(rankings.to_string())

            if period_days == 63:
                phase = identify_sector_rotation_phase(rankings)
                print(f"\n  Estimated Business Cycle Phase: {phase}")

                # Recommend sectors
                strong = rankings[rankings['Outperforming'] == True]
                if len(strong) > 0:
                    print(f"  Strong sectors (outperforming {benchmark}):")
                    for _, row in strong.head(3).iterrows():
                        print(f"    * {row['Sector']} ({row['Ticker']}): {row['Return_%']:+.1f}%")
                    print(f"\n  Strategy: Focus swing trades on stocks within these sectors.")
        else:
            print("  Could not retrieve sector data.")

    print(f"\n  [DISCLAIMER] Educational purposes only. NOT financial advice.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Swing Trading Analysis Tool - Technical & Thematic Analysis"
    )
    parser.add_argument('tickers', nargs='*', help='Stock ticker(s) to analyze')
    parser.add_argument('--sectors', action='store_true', help='Run US sector rotation analysis')
    parser.add_argument('--themes', action='store_true', help='Run thematic ETF analysis')
    parser.add_argument('--japan-sectors', action='store_true', help='Run Japanese market sector analysis')
    parser.add_argument('--watchlist', type=str, help='Comma-separated watchlist for quick scan')
    parser.add_argument('--csv', type=str, help='Load OHLCV data from CSV file')
    parser.add_argument('--name', type=str, default='CSV_STOCK', help='Stock name when using --csv')
    parser.add_argument('--demo', action='store_true', help='Run with sample data (no internet needed)')
    parser.add_argument('--account', type=float, help='Account equity for position sizing')
    parser.add_argument('--risk', type=float, default=0.02, help='Risk per trade (default: 0.02 = 2%%)')
    parser.add_argument('--history', type=int, default=0, help='Show signal history for N days')

    args = parser.parse_args()

    # Demo mode with sample data
    if args.demo:
        print("\n*** DEMO MODE - Using generated sample data ***")
        samples = generate_multi_stock_samples()
        for name, sample_data in samples.items():
            analyze_stock(name, account_equity=args.account or 1_000_000,
                         risk_pct=args.risk, history_days=10, data=sample_data)
        return

    # CSV file mode
    if args.csv:
        print(f"\nLoading data from {args.csv}...")
        try:
            csv_data = load_csv_data(args.csv)
            analyze_stock(args.name, account_equity=args.account,
                         risk_pct=args.risk, history_days=args.history, data=csv_data)
        except Exception as e:
            print(f"  Error loading CSV: {e}")
        return

    if not args.tickers and not args.sectors and not args.themes and \
       not args.japan_sectors and not args.watchlist:
        # Default: show help and run a demo with sample data
        parser.print_help()
        print("\n\n--- Running demo with sample data (use --demo for full demo) ---")
        sample = generate_sample_ohlcv("DEMO_STOCK", trend="uptrend")
        analyze_stock('DEMO_STOCK', history_days=5, data=sample,
                     account_equity=1_000_000)
        return

    # Sector analysis (lazy import to avoid yfinance dependency when not needed)
    if args.sectors or args.themes or args.japan_sectors:
        from .sector_analysis import (
            SECTOR_ETFS, THEME_ETFS, JAPAN_SECTOR_ETFS,
            rank_sectors_by_momentum, identify_sector_rotation_phase,
        )

    if args.sectors:
        run_sector_analysis(SECTOR_ETFS, "US SECTOR ROTATION ANALYSIS", 'SPY')

    if args.themes:
        run_sector_analysis(THEME_ETFS, "THEMATIC ETF ANALYSIS", 'SPY')

    if args.japan_sectors:
        run_sector_analysis(JAPAN_SECTOR_ETFS, "JAPAN SECTOR ROTATION ANALYSIS (TOPIX)", '^N225')

    # Watchlist scan
    if args.watchlist:
        tickers = [t.strip().upper() for t in args.watchlist.split(',')]
        scan_watchlist(tickers)

    # Individual stock analysis
    for ticker in (args.tickers or []):
        analyze_stock(
            ticker.upper(),
            account_equity=args.account,
            risk_pct=args.risk,
            history_days=args.history
        )


if __name__ == '__main__':
    main()
