import os
import datetime as dt
from typing import Optional, Tuple

import pandas as pd

try:
    import yfinance as yf
except Exception:  # pragma: no cover - network / optional
    yf = None


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DATA_DIR = os.path.abspath(DATA_DIR)


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def normalize_symbol(asset_type: str, ticker: str) -> str:
    """Produce a yfinance-compatible ticker string.

    asset_type: one of 'Stocks', 'Forex', 'Commodities', 'Crypto', 'Index' or 'Other'
    ticker: a simple symbol like 'AAPL', or 'EUR/USD' or 'EURUSD' or 'GC' etc.

    Returns the normalized string (e.g. 'EURUSD=X', 'GC=F') but will otherwise return provided ticker.
    """
    if not ticker or not ticker.strip():
        raise ValueError("ticker must be provided")

    symbol = ticker.strip().upper()
    if asset_type.lower().startswith("fore"):
        # Accept EUR/USD or EURUSD -> EURUSD=X
        s = symbol.replace("/", "")
        if not s.endswith("=X"):
            s = s + "=X"
        return s

    if asset_type.lower().startswith("commod"):
        # common commodity short codes (GC gold, CL crude oil, SI silver)
        mapping = {"GOLD": "GC=F", "GC": "GC=F", "CL": "CL=F", "OIL": "CL=F", "SI": "SI=F", "SILVER": "SI=F"}
        if symbol in mapping:
            return mapping[symbol]
        if not symbol.endswith("=F"):
            return symbol + "=F"

    if asset_type.lower().startswith("crypto"):
        # yfinance generally uses -USD suffix like BTC-USD
        if "/" in ticker:
            base, quote = ticker.split("/")
            return f"{base.upper()}-{quote.upper()}"
        if not ("-" in symbol or symbol.endswith("-USD")):
            return symbol + "-USD"

    # indices and stocks usually work as-is
    return symbol


def fetch_data(symbol: str, start: Optional[str] = None, end: Optional[str] = None, period: Optional[str] = None,
               interval: str = "1d", save: bool = True, folder: Optional[str] = None) -> Tuple[pd.DataFrame, Optional[str]]:
    """Fetch historical OHLCV data using yfinance.

    Provide either start/end (ISO dates) or a period like '1mo', '6mo', '1y', '5y', 'max'.
    interval can be '1d','1wk','1mo','1m','5m', etc. See yfinance docs.

    Returns (df, filepath) where filepath is None if not saved.
    """
    if yf is None:
        raise RuntimeError("yfinance is not available in this environment")

    when = {}
    if period:
        when["period"] = period
    else:
        if not start:
            # default to 1mo
            when["period"] = "1mo"
        else:
            when["start"] = start
            if end:
                when["end"] = end

    ticker = yf.Ticker(symbol)
    # yf.download respects period or start/end
    df = yf.download(symbol, interval=interval, **when)

    # Ensure DatetimeIndex and common columns
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError(f"No data returned for {symbol} with {when}")

    # Normalize column names
    df = df.rename_axis("Date").reset_index()
    df["Date"] = pd.to_datetime(df["Date"])  # reproducible
    df = df.set_index("Date")

    # If yfinance returned a MultiIndex columns (e.g. single ticker with Price/Ticker levels),
    # flatten to simple OHLC(V) names for easier downstream handling.
    if hasattr(df.columns, 'nlevels') and df.columns.nlevels > 1:
        # Prefer the top-level 'Price' names (Open/High/Low/Close/Volume) when present
        try:
            # keep only level 0 which usually contains Open/High/Low/Close
            df.columns = df.columns.get_level_values(0)
        except Exception:
            # fallback: convert column tuples to joined names
            df.columns = ["_".join([str(p) for p in c]).strip() for c in df.columns]

    filepath = None
    if save:
        ensure_data_dir()
        folder = folder or DATA_DIR
        os.makedirs(folder, exist_ok=True)
        now = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        filename = f"{symbol.replace('/','').replace(' ','_')}_{now}.csv"
        filepath = os.path.join(folder, filename)
        # CSVs are easier when columns are single level
        df.to_csv(filepath)

    return df, filepath


def list_saved_data(folder: Optional[str] = None):
    folder = folder or DATA_DIR
    ensure_data_dir()
    if not os.path.exists(folder):
        return []
    files = sorted([os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.csv')])
    return files
