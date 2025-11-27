# tradingui

Lightweight desktop utility to fetch historical market data (via yfinance), store it locally and plot it using multiple styles (line, candlestick, Heikin-Ashi).

Features:
- Choose asset types (Stocks, Forex, Commodities, Crypto, Indices)
- Absolute or relative date ranges (start/end or periods like '1mo', '1y')
- Store fetched CSV files in project data folder
- Plot using line, candlestick, or Heikin-Ashi styles
- Clean multi-tab Tkinter GUI: Fetch, Storage, Plot

Quick start
-----------

1. Create a virtualenv and install requirements:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the GUI:

```bash
python -m src.tradingui
```

Notes
-----
- yfinance requires network access. If the environment blocks outgoing network traffic, fetching won't work.
- Saved CSVs are stored in `src/data/` under the package; use the Storage tab to preview and the Plot tab to render.

Running tests and examples
--------------------------

Unit tests that don't require network (e.g., symbol normalization, heikin-ashi conversion) are included under `tests/`.

Install pytest (optional) then run tests:

```bash
pip install pytest
python -m pytest -q
```

There's also an example fetcher script `examples/quick_fetch.py` which demonstrates fetching (requires yfinance/network) and creating a saved plot image.

