import pandas as pd

from tradingui.fetcher import normalize_symbol
from tradingui.plotter import heikin_ashi


def test_normalize_forex():
    assert normalize_symbol('Forex', 'EURUSD') == 'EURUSD=X'
    assert normalize_symbol('Forex', 'EUR/USD') == 'EURUSD=X'


def test_normalize_commodities():
    assert normalize_symbol('Commodities', 'GC') == 'GC=F'
    assert normalize_symbol('Commodities', 'GOLD') == 'GC=F'


def test_heikin_ashi_basic():
    # build small OHLC series
    df = pd.DataFrame({
        'Open': [10, 11, 10.5],
        'High': [11, 11.5, 11.0],
        'Low': [9.5, 10, 10.0],
        'Close': [10.5, 10.8, 10.2]
    }, index=pd.date_range('2020-01-01', periods=3))

    ha = heikin_ashi(df)
    assert 'Open' in ha.columns and 'Close' in ha.columns
    assert len(ha) == 3
