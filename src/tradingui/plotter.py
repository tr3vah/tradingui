from typing import Optional

import pandas as pd

try:
    import mplfinance as mpf
except Exception:  # pragma: no cover - optional dependency
    mpf = None


def heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """Convert a DataFrame with columns Open, High, Low, Close to Heikin-Ashi OHLC.

    Returns a new DataFrame containing HA_Open/High/Low/Close indexed by original index.
    """
    ha = df.copy()
    ha_cols = [c for c in ['Open', 'High', 'Low', 'Close'] if c in ha.columns]
    if len(ha_cols) < 4:
        raise ValueError('DataFrame must contain Open, High, Low, Close columns')

    ha['HA_Close'] = (ha['Open'] + ha['High'] + ha['Low'] + ha['Close']) / 4.0
    ha['HA_Open'] = 0.0
    # first HA_Open is average of Open and Close
    ha.iat[0, ha.columns.get_loc('HA_Open')] = (ha['Open'].iat[0] + ha['Close'].iat[0]) / 2.0
    for i in range(1, len(ha)):
        ha.iat[i, ha.columns.get_loc('HA_Open')] = (ha['HA_Open'].iat[i-1] + ha['HA_Close'].iat[i-1]) / 2.0

    ha['HA_High'] = ha[['HA_Open', 'HA_Close', 'High']].max(axis=1)
    ha['HA_Low'] = ha[['HA_Open', 'HA_Close', 'Low']].min(axis=1)

    # Build a DataFrame with OHLC columns
    res = ha[['HA_Open', 'HA_High', 'HA_Low', 'HA_Close']].copy()
    res.columns = ['Open', 'High', 'Low', 'Close']
    return res


def plot_dataframe(df: pd.DataFrame, style: str = 'line', title: Optional[str] = None, savefile: Optional[str] = None):
    """Plot a pandas DataFrame of OHLC (index should be datetime) using mplfinance (if available) or pandas/matplotlib.

    style: 'line', 'candle', 'heikin'
    """
    if style not in ('line', 'candle', 'heikin'):
        raise ValueError('supported styles: line, candle, heikin')

    if style == 'line':
        ax = df['Close'].plot(figsize=(10, 6), title=title)
        if savefile:
            fig = ax.get_figure()
            fig.savefig(savefile)
        return

    if mpf is None:
        raise RuntimeError('mplfinance is required for candlestick or heikin plotting. Install with pip install mplfinance')

    if style == 'candle':
        # Ensure OHLCV are numeric; mplfinance requires numeric dtypes
        cols = ['Open', 'High', 'Low', 'Close']
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')

        if 'Volume' in df.columns:
            df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')

        # drop rows where required OHLC are missing
        df_clean = df.dropna(subset=cols)
        if df_clean.empty:
            raise ValueError('No numeric OHLC data available for plotting')

        mpf.plot(df_clean, type='candle', style='yahoo', volume=True, title=title, savefig=savefile)
        return

    # heikin
    # coerce to numeric before heikin transform
    for c in ['Open', 'High', 'Low', 'Close']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    ha = heikin_ashi(df)
    mpf.plot(ha, type='candle', style='charles', volume=False, title=(title or '') + ' (Heikin-Ashi)', savefig=savefile)
