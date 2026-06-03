#!/usr/bin/env python3
"""Fetch OHLC market data, compute RSI, write JSON."""
import json, pathlib, pandas as pd, yfinance as yf
from datetime import datetime, timezone

ASSETS = {
    "S&P500": "^GSPC", "DXY": "DX-Y.NYB", "Gold": "GC=F",
    "VIX": "^VIX", "US10Y": "^TNX", "US02Y": "^IRX",
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X",
    "BTC/USD": "BTC-USD", "Crude Oil": "CL=F",
}

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"

def compute_rsi(series, period=14):
    if len(series) < period + 1:
        return None
    delta = series.diff().dropna()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_g = gain.rolling(period).mean()
    avg_l = loss.rolling(period).mean()
    rs = avg_g / avg_l
    rsi = 100 - (100 / (1 + rs))
    last = rsi.iloc[-1]
    return round(float(last), 2) if pd.notna(last) else None

def get_rsi_signal(rsi):
    if rsi is None: return "N/A"
    if rsi > 70: return "Overbought"
    if rsi < 30: return "Oversold"
    return "Neutral"

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output = {}
    print("Fetching market data...")
    for name, ticker in ASSETS.items():
        try:
            df = yf.download(ticker, period="2mo", interval="1d", progress=False, auto_adjust=True)
            if df.empty:
                output[name] = {"error": "No data"}
                print(f"  {name}: ⚠️ no data")
                continue
            # Handle yfinance MultiIndex columns (Price, Ticker)
            if isinstance(df.columns, pd.MultiIndex):
                # New yfinance: columns are (Price, Ticker) — extract by first level
                close = df.xs("Close", axis=1, level=0).iloc[:, 0]
                high = df.xs("High", axis=1, level=0).iloc[:, 0]
                low = df.xs("Low", axis=1, level=0).iloc[:, 0]
                open_ = df.xs("Open", axis=1, level=0).iloc[:, 0]
                vol = df.xs("Volume", axis=1, level=0).iloc[:, 0]
            else:
                close = df["Close"]
                high = df["High"]
                low = df["Low"]
                open_ = df["Open"]
                vol = df["Volume"]

            last = float(close.iloc[-1])
            prev = float(close.iloc[-2]) if len(close) > 1 else last
            chg = round((last / prev - 1) * 100, 2) if prev else 0
            rsi = compute_rsi(close)
            output[name] = {
                "ticker": ticker,
                "last_close": round(last, 2),
                "prev_close": round(prev, 2) if prev else None,
                "change_24h_pct": chg,
                "high": round(float(high.iloc[-1]), 2),
                "low": round(float(low.iloc[-1]), 2),
                "open": round(float(open_.iloc[-1]), 2),
                "volume": int(vol.iloc[-1]),
                "rsi_14": rsi,
                "rsi_signal": get_rsi_signal(rsi),
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }
            print(f"  {name}: {last:>8.2f} ({chg:+.2f}%) RSI {rsi}")
        except Exception as e:
            output[name] = {"error": str(e)}
            print(f"  {name}: ❌ {e}")

    out = DATA_DIR / "market_data.json"
    with open(out, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWritten to {out}")

if __name__ == "__main__":
    main()
