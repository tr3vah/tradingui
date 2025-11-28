"""Lightweight FastAPI proxy for fetching CSV data (server-side) to avoid browser CORS issues.

Expose /api/download which accepts GET params: symbol, start (YYYY-MM-DD), end (YYYY-MM-DD), period (eg 1mo)
and returns CSV text with Content-Type: text/csv.

This server uses the fetcher.fetch_data() internally when yfinance is available.
"""
from fastapi import FastAPI, Query, HTTPException, Depends, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os
import secrets

from . import fetcher
import pandas as pd
from typing import Optional
import time
import pathlib
import threading

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
_AUTH_USER = os.environ.get('TRADINGUI_API_BASIC_USER')
_AUTH_PASS = os.environ.get('TRADINGUI_API_BASIC_PASS')


def _verify_basic(request: Request) -> str:
    """Verify basic auth credentials when authentication is configured.

    If env creds are not set, allow access (development mode). Otherwise verify provided credentials.
    Returns the username when valid, raises HTTPException when invalid.
    """
    # If no auth configured allow anonymous access
    if not (_AUTH_USER and _AUTH_PASS):
        return 'anonymous'

    # Expect an Authorization: Basic header
    auth = request.headers.get('Authorization') or request.headers.get('authorization')
    if not auth or not auth.lower().startswith('basic '):
        raise HTTPException(status_code=401, detail='Not authenticated', headers={'WWW-Authenticate': 'Basic'})

    import base64
    try:
        token = auth.split(' ', 1)[1]
        decoded = base64.b64decode(token).decode('utf-8')
        username, password = decoded.split(':', 1)
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid authentication format', headers={'WWW-Authenticate': 'Basic'})

    if not (secrets.compare_digest(username, _AUTH_USER) and secrets.compare_digest(password, _AUTH_PASS)):
        raise HTTPException(status_code=401, detail='Invalid authentication credentials', headers={'WWW-Authenticate': 'Basic'})

    return username


# Caching
# Cache directory (defaults to src/data/cache)
_CACHE_DIR = os.environ.get('TRADINGUI_API_CACHE_DIR')
if not _CACHE_DIR:
    _CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'cache'))
os.makedirs(_CACHE_DIR, exist_ok=True)

_CACHE_TTL = int(os.environ.get('TRADINGUI_API_CACHE_TTL', '3600'))  # seconds


def _cache_filename(symbol: str, start: Optional[str], end: Optional[str], period: Optional[str], interval: Optional[str] = None) -> str:
    safe = symbol.replace('/', '').replace(' ', '_')
    tag = period or start or 'latest'
    end_tag = ('_' + end) if end else ''
    interval_tag = ('_' + interval) if interval else ''
    name = f"{safe}_{tag}{end_tag}{interval_tag}.csv"
    return os.path.join(_CACHE_DIR, name)


_cache_lock = threading.Lock()

# Rate limiting (simple per-IP in-memory sliding window)
_RATE_LIMIT_STATE: dict[str, list[float]] = {}
_RL_LOCK = threading.Lock()
_RATE_LIMIT_MAX = int(os.environ.get('TRADINGUI_API_RATE_LIMIT_MAX', '60'))
_RATE_LIMIT_WINDOW = int(os.environ.get('TRADINGUI_API_RATE_LIMIT_WINDOW', '60'))


def _rate_limit_check(request: Request):
    """Raise HTTPException 429 if IP exceeded rate limit.

    This is a simple in-memory limiter suitable for demos and single-process deployments.
    For production use a shared store like Redis + a distributed rate limiter.
    """
    ip = 'unknown'
    if getattr(request, 'client', None) and request.client.host:
        ip = request.client.host

    now = time.time()
    with _RL_LOCK:
        ts_list = _RATE_LIMIT_STATE.get(ip, [])
        # remove expired
        ts_list = [t for t in ts_list if t > now - _RATE_LIMIT_WINDOW]
        if len(ts_list) >= _RATE_LIMIT_MAX:
            # rate-limited
            # compute retry-after as the earliest remaining time until a slot frees
            retry_after = int(_RATE_LIMIT_WINDOW - (now - ts_list[0]))
            raise HTTPException(status_code=429, detail='Too many requests', headers={'Retry-After': str(retry_after)})
        ts_list.append(now)
        _RATE_LIMIT_STATE[ip] = ts_list



@app.get('/api/health')
def health():
    return {'status': 'ok'}


@app.get('/api/download', response_class=PlainTextResponse)
def download(symbol: str = Query(..., description='Ticker symbol (yfinance normalized e.g. AAPL, EURUSD=X)'),
             start: Optional[str] = Query(None, description='Start date YYYY-MM-DD'),
             end: Optional[str] = Query(None, description='End date YYYY-MM-DD'),
             period: Optional[str] = Query(None, description='Short period like 1mo, 1y'),
             interval: Optional[str] = Query(None, description='Interval (eg 1d, 1h, 5m)'),
             save: bool = Query(False, description='Whether to save the CSV on server'),
             bust_cache: bool = Query(False, description='Force refresh cache'),
             user: str = Depends(_verify_basic),
             _rl: None = Depends(_rate_limit_check)):
    """Download historical CSV for a symbol.

    The server will try to use the package fetcher which uses yfinance. If yfinance is unavailable
    or the network is blocked, this endpoint will raise a 502.
    """
    # Authentication and rate limiting are handled via dependencies.

    # Attempt to use fetcher.fetch_data which returns (df, filepath)
    # Apply simple file-based cache first
    cache_path = _cache_filename(symbol, start, end, period, interval)
    if not bust_cache and os.path.exists(cache_path):
        mtime = os.path.getmtime(cache_path)
        age = time.time() - mtime
        if age <= _CACHE_TTL:
            # serve cached file
            with open(cache_path, 'r', encoding='utf-8') as fh:
                csv_text = fh.read()
            return PlainTextResponse(content=csv_text, media_type='text/csv')
    try:
        df, filepath = fetcher.fetch_data(symbol, start=start, end=end, period=period, interval=interval or '1d', save=False)
    except Exception as exc:  # pragma: no cover - network dependent
        # Attempt to provide a helpful fallback for demo environments where yfinance is not
        # installed or the network is blocked. Try to find a matching CSV already present in
        # the package `data` folder and return that. If not found, raise 502.
        try:
            # Look for any saved CSV matching the symbol in the data dir
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

    # write to cache atomically
    try:
        tmp_path = cache_path + '.tmp'
        with _cache_lock:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(tmp_path, 'w', encoding='utf-8') as fh:
                fh.write(csv_text)
            os.replace(tmp_path, cache_path)
    except Exception:
        # non-fatal — if writing the cache fails we still return the CSV
        pass

    return PlainTextResponse(content=csv_text, media_type='text/csv')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8001)
