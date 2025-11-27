import pandas as pd
import pytest

# fastapi is optional in the environment for this kata — skip tests if it's not installed
pytest.importorskip('fastapi')
from fastapi.testclient import TestClient


def make_df():
    idx = pd.date_range('2020-01-01', periods=3)
    df = pd.DataFrame({'Open': [10, 11, 10.5], 'High': [11, 11.5, 11.0], 'Low': [9.5, 10, 10.0], 'Close': [10.5, 10.8, 10.2]}, index=idx)
    return df


def test_download_endpoint(monkeypatch):
    # patch fetcher.fetch_data to return a small DataFrame to avoid network
    import tradingui.fetcher as fetcher

    def fake_fetch_data(symbol, start=None, end=None, period=None, interval='1d', save=False, folder=None):
        return make_df(), None

    monkeypatch.setattr(fetcher, 'fetch_data', fake_fetch_data)

    from tradingui.api import app
    client = TestClient(app)

    resp = client.get('/api/download?symbol=AAPL&period=1mo')
    assert resp.status_code == 200
    assert 'Date' in resp.text
    # verify CORS headers exist (allow-origin should be present)
    assert 'access-control-allow-origin' in resp.headers
