"""Lightweight FastAPI proxy for fetching CSV data (server-side) to avoid browser CORS issues.

Expose /api/download which accepts GET params: symbol, start (YYYY-MM-DD), end (YYYY-MM-DD), period (eg 1mo)
and returns CSV text with Content-Type: text/csv.

This server uses the fetcher.fetch_data() internally when yfinance is available.
"""
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

from . import fetcher
import pandas as pd
from typing import Optional

app = FastAPI(title='tradingui proxy')

# Allow all origins (local dev). In production restrict this.
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['*'],
)


@app.get('/api/health')
def health():
    return {'status': 'ok'}


@app.get('/api/download', response_class=PlainTextResponse)
def download(symbol: str = Query(..., description='Ticker symbol (yfinance normalized e.g. AAPL, EURUSD=X)'),
             start: Optional[str] = Query(None, description='Start date YYYY-MM-DD'),
             end: Optional[str] = Query(None, description='End date YYYY-MM-DD'),
             period: Optional[str] = Query(None, description='Short period like 1mo, 1y'),
             save: bool = Query(False, description='Whether to save the CSV on server')):
    """Download historical CSV for a symbol.

    The server will try to use the package fetcher which uses yfinance. If yfinance is unavailable
    or the network is blocked, this endpoint will raise a 502.
    """
    # Attempt to use fetcher.fetch_data which returns (df, filepath)
    try:
        df, filepath = fetcher.fetch_data(symbol, start=start, end=end, period=period, save=save)
    except Exception as exc:  # pragma: no cover - network dependent
        raise HTTPException(status_code=502, detail=f'Failed to fetch data for {symbol}: {exc}')

    # Convert DataFrame to CSV text (in memory)
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise HTTPException(status_code=404, detail='No data available')

    csv_text = df.to_csv()

    return PlainTextResponse(content=csv_text, media_type='text/csv')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8001)
