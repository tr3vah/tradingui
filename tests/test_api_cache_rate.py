import os
import importlib
import pandas as pd
import time
import pytest

pytest.importorskip('fastapi')
from fastapi.testclient import TestClient


def make_df():
    idx = pd.date_range('2020-01-01', periods=3)
    df = pd.DataFrame({'Open': [10, 11, 10.5], 'High': [11, 11.5, 11.0], 'Low': [9.5, 10, 10.0], 'Close': [10.5, 10.8, 10.2]}, index=idx)
    return df


def test_cache_served_and_persists(monkeypatch, tmp_path):
    # set cache dir env var and reload module
    monkeypatch.setenv('TRADINGUI_API_CACHE_DIR', str(tmp_path))
    monkeypatch.delenv('TRADINGUI_API_RATE_LIMIT_MAX', raising=False)
    monkeypatch.delenv('TRADINGUI_API_RATE_LIMIT_WINDOW', raising=False)

    # patch fetcher to return our DF
    import tradingui.fetcher as fetcher

    def fake_fetch(symbol, start=None, end=None, period=None, interval='1d', save=False, folder=None):
        return make_df(), None

    monkeypatch.setattr(fetcher, 'fetch_data', fake_fetch)

    # reload api module so it picks up the cache dir env
    import tradingui.api as api_mod
    importlib.reload(api_mod)

    client = TestClient(api_mod.app)

    # first request should call fetcher and populate cache
    r1 = client.get('/api/download?symbol=ABC&period=1mo')
    assert r1.status_code == 200
    files = list(tmp_path.glob('*.csv'))
    assert len(files) == 1

    # now make fetcher fail and confirm cache is still returned
    def failing_fetch(*args, **kwargs):
        raise RuntimeError('network disabled')

    monkeypatch.setattr(fetcher, 'fetch_data', failing_fetch)

    r2 = client.get('/api/download?symbol=ABC&period=1mo')
    assert r2.status_code == 200
    assert 'Date' in r2.text


def test_rate_limit_blocks(monkeypatch):
    # configure a tiny rate limit
    monkeypatch.setenv('TRADINGUI_API_RATE_LIMIT_MAX', '2')
    monkeypatch.setenv('TRADINGUI_API_RATE_LIMIT_WINDOW', '2')
    monkeypatch.delenv('TRADINGUI_API_CACHE_DIR', raising=False)

    # patch fetcher
    import tradingui.fetcher as fetcher

    def fake_fetch(symbol, start=None, end=None, period=None, interval='1d', save=False, folder=None):
        return make_df(), None

    monkeypatch.setattr(fetcher, 'fetch_data', fake_fetch)

    import tradingui.api as api_mod
    importlib.reload(api_mod)

    client = TestClient(api_mod.app)

    # first two requests pass
    r1 = client.get('/api/download?symbol=ABC&period=1mo')
    assert r1.status_code == 200
    r2 = client.get('/api/download?symbol=ABC&period=1mo')
    assert r2.status_code == 200

    # third request within the window should be rejected (429)
    r3 = client.get('/api/download?symbol=ABC&period=1mo')
    assert r3.status_code == 429

    # wait for window to expire and try again
    time.sleep(2)
    r4 = client.get('/api/download?symbol=ABC&period=1mo')
    assert r4.status_code == 200
