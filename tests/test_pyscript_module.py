import importlib.util
from pathlib import Path


def load_module_from_path(path):
    spec = importlib.util.spec_from_file_location('web_pyscript', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_csv_text():
    p = Path(__file__).parents[1] / 'web' / 'tradingui_pyscript.py'
    mod = load_module_from_path(str(p))

    csv = 'Date,Open,High,Low,Close,Volume\n2020-01-01,10,11,9,10.5,1000\n2020-01-02,10.5,11.5,10,11,2000\n'
    df = mod.parse_csv_text(csv)
    assert df is not None
    # must contain Date and Close columns
    assert 'Date' in df.columns
    assert 'Close' in df.columns
