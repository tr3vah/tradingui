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

Secure the API (CORS + Basic Auth)
--------------------------------

To safely expose the proxy server, customize allowed CORS origins and require HTTP Basic authentication using environment variables.

Examples (Linux / macOS):

```bash
# restrict allowed browser origins (comma-separated) and require a username/password
export TRADINGUI_API_ALLOW_ORIGINS="https://your-site.example,https://app.example"
export TRADINGUI_API_BASIC_USER="my_user"
export TRADINGUI_API_BASIC_PASS="s3cret"

# start the API server (it will now require basic auth)
python run.py api 8001
```

If the `TRADINGUI_API_BASIC_USER` and `TRADINGUI_API_BASIC_PASS` environment variables are not set the server will allow unauthenticated access (useful for local development). The `TRADINGUI_API_ALLOW_ORIGINS` variable controls which browser origins are permitted to call the API; if unset the server only allows common local-dev origins.

Browser UI credentials and API base
---------------------------------
The web UI includes two convenience fields to help fetch data from a proxied API:

- **API base** — the base path or URL for your API (defaults to `/api`). Set this to `http://localhost:8001` or your hosted API URL if the proxy runs on a different port/host.
- **API user / password** — optional Basic Auth credentials. When provided the dashboard will include an HTTP Authorization header when calling the API so requests will authenticate correctly.
 - **API user / password** — optional Basic Auth credentials. When provided the dashboard will include an HTTP Authorization header when calling the API so requests will authenticate correctly.

Login behavior
--------------

You can click **Login** after entering credentials in the fetch UI to persist them to the browser session (sessionStorage). The PyScript UI will use stored credentials automatically when calling the `/api/` endpoints so you don't have to re-enter them each time. Click **Logout** to clear the session credentials.

Security note: storing long-lived passwords in sessionStorage is only acceptable for local testing or self-hosted deployments you control; for production use a token-based flow (JWT/OAuth) or delegate authentication to a reverse-proxy with safe session cookies.

Interval selection
------------------

The Fetch tab now includes an "Interval" dropdown so you can request data at different granularities (eg 1d, 1h, 5m). When you fetch via the proxy the interval is forwarded to the backend (yfinance) which will return matching OHLC data when available.

Notes:
- Not all intervals are supported for all date ranges by the data provider — for example minute-level intervals are often limited to recent history. If you request a very small interval for a long date range the provider may return an error or no data.
- Use shorter date ranges for small intervals (like 5m/30m) and daily/week/month intervals for longer ranges.

If you run the UI from a Codespace preview or other host, make sure the API CORS (`TRADINGUI_API_ALLOW_ORIGINS`) includes that origin string or run both services behind the same origin to avoid preflight/CORS problems.

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

Unit tests that don't require network (e.g., symbol normalization, heikin-ashi conversion) are included under `tests/`.

Install pytest (optional) then run tests:

```bash
pip install pytest
python -m pytest -q
```

There's also an example fetcher script `examples/quick_fetch.py` which demonstrates fetching (requires yfinance/network) and creating a saved plot image.

Docker Compose deployment (single-origin proxy to avoid CORS)
-----------------------------------------------------------

I added a docker-compose setup you can use to run a single-origin stack: Nginx serves the static web UI on port 8080 and proxies /api requests to the FastAPI backend on port 8001 inside the compose network. This avoids CORS problems since both the UI and the API are served from the same origin.

Files added: `deploy/docker-compose.yml`, `deploy/Dockerfile.api`, `deploy/Dockerfile.web`, `deploy/nginx.conf`, `deploy/check_smoke.sh`.

Quick start (requires Docker & docker-compose installed):

This repo includes two convenient compose stacks:

- `docker-compose.yml` (repo root) — builds the API and a custom nginx reverse-proxy which serves the static web UI and proxies `/api/` to the backend over HTTPS (TLS). Ports: 8443 (HTTPS), 8080 (HTTP -> redirect to HTTPS).
- `deploy/docker-compose.yml` — a simpler local dev stack (no HTTPS) that serves web + api behind an nginx proxy at http://localhost:8080.

Local TLS stack (recommended for same-origin HTTPS demo)

```bash
# generate self-signed certs (for local development/demo only)
./deploy/generate-selfsigned.sh

# start the TLS reverse-proxy stack (builds the images)
docker compose up --build

# open https://localhost:8443 in your browser
```

Quick local dev stack (no TLS)

```bash
docker compose -f deploy/docker-compose.yml up --build
# open http://localhost:8080
```

To run in the background:

```bash
docker compose -f deploy/docker-compose.yml up -d --build

# then run the simple smoke-check (makes HTTP requests to the proxy)
./deploy/check_smoke.sh
```

Example to secure the API with Basic auth in the API service (env vars):

```bash
export TRADINGUI_API_BASIC_USER="my_user"
export TRADINGUI_API_BASIC_PASS="s3cret"
docker compose -f deploy/docker-compose.yml up --build
```

When using Basic Auth you can either enter credentials in the dashboard API user/password fields (works with PyScript and JS fallback), or configure a real authentication layer on your reverse proxy.

