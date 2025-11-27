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

Run the new PyScript (browser) UI
--------------------------------

This project now includes a lightweight browser-based UI implemented with PyScript (runs Python inside the browser). The web UI lives in the `web/` directory and supports the same core flows (Fetch / Storage / Plot) but runs entirely in the browser. Note: fetching remote CSVs from Yahoo/3rd-party endpoints may be blocked by CORS — use upload or a proxy if you hit CORS errors.

Quick ways to open the PyScript UI locally:

1. Serve the `web/` directory with Python's tiny webserver:

```bash
cd web
python -m http.server 8000
# then open http://localhost:8000 in your browser
```

2. Or use the included helper run.py:

```bash
python run.py web 8000
# opens a simple local server at http://localhost:8000
```

Run the backend proxy (recommended)
---------------------------------

To avoid browser CORS when fetching CSVs from Yahoo, run the backend proxy server. It wraps yfinance server-side and returns CSV to the browser.

You can run it with uvicorn directly:

```bash
# from repo root
python -m uvicorn src.tradingui.api:app --port 8001 --reload
# or using our helper:
python run.py api 8001
```

Start both pieces locally for a complete demo:

Terminal 1 — start the API (on port 8001):

```bash
python run.py api 8001
```

Terminal 2 — serve the web UI (on port 8000):

```bash
python run.py web 8000
# then open http://localhost:8000 in your browser. The PyScript UI will attempt to use the /api/download proxy or http://localhost:8001 if available.
```

Limitations & notes
-------------------
- PyScript runs in the browser (Pyodide) and will use in-browser packages; not all heavy packages behave the same as a desktop Python environment.
- When fetching remote CSVs from Yahoo Finance or other providers the browser can block requests with CORS — in that case use the file upload in the Fetch tab or a small local proxy.
- Large version of pandas, mplfinance, or yfinance may not be available or practical inside Pyodide — this UI uses CSV parsing in-browser and Plotly.js for plotting.

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

