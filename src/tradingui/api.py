"""Lightweight FastAPI proxy for fetching CSV data (server-side) to avoid browser CORS issues.

Expose /api/download which accepts GET params: symbol, start (YYYY-MM-DD), end (YYYY-MM-DD), period (eg 1mo)
and returns CSV text with Content-Type: text/csv.

This server uses the fetcher.fetch_data() internally when yfinance is available.
"""
from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os
import secrets

from . import fetcher
import pandas as pd
from typing import Optional

app = FastAPI(title='tradingui proxy')

# CORS configuration — configurable via environment variable TRADINGUI_API_ALLOW_ORIGINS
# Example: TRADINGUI_API_ALLOW_ORIGINS="http://localhost:8000,http://127.0.0.1:8000"
allow_origins_env = os.environ.get('TRADINGUI_API_ALLOW_ORIGINS')
if allow_origins_env:
    allow_origins = [o.strip() for o in allow_origins_env.split(',') if o.strip()]
else:
    # default to local development origins only
    allow_origins = [
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['*'],
)

# HTTP Basic auth configuration — if both env vars TRADINGUI_API_BASIC_USER and TRADINGUI_API_BASIC_PASS
# are present, the API will require basic auth. If not present, the API remains unprotected (for dev).
security = HTTPBasic()
_AUTH_USER = os.environ.get('TRADINGUI_API_BASIC_USER')
_AUTH_PASS = os.environ.get('TRADINGUI_API_BASIC_PASS')


def _verify_basic(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Verify basic auth credentials when authentication is configured.

    If env creds are not set, allow access (development mode). Otherwise verify provided credentials.
    Returns the username when valid, raises HTTPException when invalid.
    """
    if not (_AUTH_USER and _AUTH_PASS):
        # no credentials configured — allow unauthenticated access for development convenience
        return 'anonymous'

    correct_user = secrets.compare_digest(credentials.username, _AUTH_USER)
    correct_pass = secrets.compare_digest(credentials.password, _AUTH_PASS)
    if not (correct_user and correct_pass):
        raise HTTPException(status_code=401, detail='Invalid authentication credentials', headers={'WWW-Authenticate': 'Basic'})
    return credentials.username


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
    # If authentication is configured, verify credentials first
    # When creds are not set, the _verify_basic() dependency will return 'anonymous'
    try:
        _ = _verify_basic()
    except HTTPException:
        # re-raise so FastAPI produces correct 401
        raise

    # Attempt to use fetcher.fetch_data which returns (df, filepath)
    try:
        df, filepath = fetcher.fetch_data(symbol, start=start, end=end, period=period, save=save)
    except Exception as exc:  # pragma: no cover - network dependent
        # Attempt to provide a helpful fallback for demo environments where yfinance is not
        # installed or the network is blocked. Try to find a matching CSV already present in
        # the package `data` folder and return that. If not found, raise 502.
        try:
            # Look for any saved CSV matching the symbol in the data dir
            import os
            data_dir = fetcher.DATA_DIR
            if os.path.isdir(data_dir):
                # look for files containing the symbol name (case-insensitive)
                files = [f for f in os.listdir(data_dir) if f.endswith('.csv') and symbol.lower() in f.lower()]
                if files:
                    # choose the most recent file (sorted lexicographically works with our timestamps)
                    files = sorted(files)
                    candidate = os.path.join(data_dir, files[-1])
                    with open(candidate, 'r', encoding='utf-8') as fh:
                        csv_text = fh.read()
                        return PlainTextResponse(content=csv_text, media_type='text/csv')
        except Exception:
            pass

        raise HTTPException(status_code=502, detail=f'Failed to fetch data for {symbol}: {exc}')

    # Convert DataFrame to CSV text (in memory)
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise HTTPException(status_code=404, detail='No data available')

    csv_text = df.to_csv()

    return PlainTextResponse(content=csv_text, media_type='text/csv')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8001)
