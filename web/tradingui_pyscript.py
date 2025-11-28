try:
    # these objects exist when running inside PyScript (pyodide) in the browser
    from js import document, console, fetch, localStorage, JSON
except Exception:
    # provide minimal fallbacks so the module can still be imported during unit tests
    document = None
    console = __import__('builtins')
    fetch = None
    # use a plain dict to emulate localStorage, tests don't need browser persistence
    class _LocalStorage(dict):
        def key(self, idx):
            try:
                return list(self.keys())[idx]
            except Exception:
                return None

    localStorage = _LocalStorage()
    import json as JSON
import asyncio
from datetime import datetime

try:
    import pandas as pd
except Exception as e:
    print('pandas not available; some functionality will not work in the browser without pandas installed')
    pd = None


def _log(msg):
    console.log(msg)


def _is_csv_like(text: str) -> bool:
    return '\n' in text and (',' in text or '\t' in text)


def build_basic_auth_header(username: str, password: str) -> str:
    """Return a Basic auth header string for the given username/password.

    This works both in PyScript (using js.btoa) and in plain Python (base64).
    """
    if not username or not password:
        return ''
    try:
        # prefer JS btoa when running in browser
        from js import btoa
        token = btoa(f"{username}:{password}")
        return 'Basic ' + token
    except Exception:
        import base64
        token = base64.b64encode(f"{username}:{password}".encode('utf-8')).decode('ascii')
        return 'Basic ' + token


def parse_csv_text(csv_text: str):
    if pd is None:
        return None
    try:
        from io import StringIO
        df = pd.read_csv(StringIO(csv_text), parse_dates=['Date'], infer_datetime_format=True)
        # normalize columns to standard names
        cols = [c.strip() for c in df.columns]
        df.columns = cols
        # ensure common OHLC names
        want = ['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        present = [c for c in want if c in df.columns]
        if 'Date' not in df.columns and 'date' in (c.lower() for c in df.columns):
            # try to locate date column
            for c in df.columns:
                if c.lower() == 'date':
                    df.rename(columns={c: 'Date'}, inplace=True)
                    break
        if 'Date' in df.columns:
            df = df.sort_values('Date')
        return df
    except Exception as exc:
        console.error('Failed to parse CSV in Python:', exc)
        return None


def heikin_ashi(df):
    # Input DataFrame expected to have Date/Open/High/Low/Close
    import pandas as pd
    ha = df.copy().reset_index(drop=True)
    ha['HA_Close'] = (ha['Open'] + ha['High'] + ha['Low'] + ha['Close']) / 4.0
    ha['HA_Open'] = 0.0
    for i in range(len(ha)):
        if i == 0:
            ha.at[i, 'HA_Open'] = (ha.at[i, 'Open'] + ha.at[i, 'Close']) / 2.0
        else:
            ha.at[i, 'HA_Open'] = (ha.at[i-1, 'HA_Open'] + ha.at[i-1, 'HA_Close']) / 2.0
    ha['HA_High'] = ha[['HA_Open', 'HA_Close', 'High']].max(axis=1)
    ha['HA_Low'] = ha[['HA_Open', 'HA_Close', 'Low']].min(axis=1)
    return ha


def _get_saved_credentials():
    """Return (user, pass) from sessionStorage if available, else from DOM inputs."""
    user = ''
    pwd = ''
    try:
        sess = __import__('js').sessionStorage
        user = sess.getItem('tradingui_api_user') or ''
        pwd = sess.getItem('tradingui_api_pass') or ''
    except Exception:
        try:
            user = document.getElementById('api_user').value or ''
            pwd = document.getElementById('api_pass').value or ''
        except Exception:
            user = pwd = ''
    return user, pwd


def py_login(evt=None):
    """Store provided API user/password into sessionStorage (session-only) so the UI can authenticate."""
    try:
        user = document.getElementById('api_user').value or ''
        pwd = document.getElementById('api_pass').value or ''
    except Exception:
        print('Login: UI inputs not found')
        return

    if not user or not pwd:
        print('Please enter username and password to login')
        return

    try:
        sess = __import__('js').sessionStorage
        sess.setItem('tradingui_api_user', user)
        sess.setItem('tradingui_api_pass', pwd)
        # update UI status if present
        try:
            document.getElementById('login_status').innerText = f'Logged in as {user}'
        except Exception:
            pass
        print('Login stored in session')
    except Exception as exc:
        print('Login failed (no sessionStorage available):', exc)


def py_logout(evt=None):
    try:
        sess = __import__('js').sessionStorage
        sess.removeItem('tradingui_api_user')
        sess.removeItem('tradingui_api_pass')
        try:
            document.getElementById('login_status').innerText = 'Logged out'
        except Exception:
            pass
        print('Logged out')
    except Exception:
        print('Logout: sessionStorage not available')


async def py_fetch(evt=None):
    """Fetch CSV from Yahoo Finance CSV endpoint in the browser using JS fetch
    Note: browser might block the request due to CORS. If so, upload the CSV instead or use a proxy.
    """
    sym = document.getElementById('symbol').value.strip()
    sd = document.getElementById('start_date').value
    ed = document.getElementById('end_date').value
    if not sym:
        print('Please enter a symbol')
        return

    # create timestamps if dates provided, otherwise default to 1 year
    interval = ''
    try:
        interval = (document.getElementById('interval').value or '').strip()
    except Exception:
        interval = ''

    if sd and ed:
        try:
            start_ts = int(datetime.fromisoformat(sd).timestamp())
            end_ts = int(datetime.fromisoformat(ed).timestamp())
        except Exception as ex:
            print('Invalid date format — use yyyy-mm-dd')
            return
    else:
        # fallback: last 365 days
        end_ts = int(datetime.now().timestamp())
        start_ts = int((datetime.now()).timestamp()) - 365 * 24 * 3600

    # First try to call a local backend proxy (recommended) to avoid CORS issues.
    # Use the API base provided in the UI if present; otherwise try /api and localhost:8001
    api_base = ''
    try:
        api_base = (document.getElementById('api_base').value or '').rstrip('/')
    except Exception:
        api_base = ''

    # We will attempt a few likely proxy urls: UI-provided base, then localhost:8001
    # include interval if selected
    interval_q = f"&interval={interval}" if interval else ''
    proxy_urls = [f'{api_base}/download?symbol={sym}&period=1y{interval_q}' if api_base else f'/api/download?symbol={sym}&period=1y{interval_q}',
                  f'http://localhost:8001/api/download?symbol={sym}&period=1y']

    if sd and ed:
        proxy_urls = [f'{api_base}/download?symbol={sym}&start={sd}&end={ed}{interval_q}' if api_base else f'/api/download?symbol={sym}&start={sd}&end={ed}{interval_q}',
              f'http://localhost:8001/api/download?symbol={sym}&start={sd}&end={ed}{interval_q}']

    text = None
    # If the UI provided Basic Auth credentials or saved credentials exist, include Authorization header
    headers = {}
    try:
        # prefer sessionStorage values when available for persistent login within the session
        try:
            sess = __import__('js').sessionStorage
            user = sess.getItem('tradingui_api_user') or ''
            pwd = sess.getItem('tradingui_api_pass') or ''
        except Exception:
            user = document.getElementById('api_user').value or ''
            pwd = document.getElementById('api_pass').value or ''

        if user and pwd:
            headers['Authorization'] = build_basic_auth_header(user, pwd)
    except Exception:
        headers = {}

    for url in proxy_urls:
        try:
            print('Attempting proxy fetch:', url)
            if headers:
                resp = await fetch(url, {'headers': headers})
            else:
                resp = await fetch(url)
            status = int(resp.status)
            if status == 200:
                text = await resp.text()
                break
            else:
                print('Proxy returned status', status, 'for', url)
        except Exception as ex:
            # try next proxy url
            print('Proxy fetch exception for', url, ':', ex)

    if text is None:
        # fallback to direct Yahoo fetch (may fail due to CORS)
        # If direct Yahoo fetch is used, include the selected interval if provided
        direct_interval = interval if interval else '1d'
        url = f'https://query1.finance.yahoo.com/v7/finance/download/{sym}?period1={start_ts}&period2={end_ts}&interval={direct_interval}&events=history&includeAdjustedClose=true'
        print('Falling back to direct fetch (may be blocked by CORS):', url)
        try:
            resp_promise = fetch(url)
            if headers:
                resp = await fetch(url, {'headers': headers})
            else:
                resp = await resp_promise
            status = int(resp.status)
            if status != 200:
                print(f'Fetch failed (status {status}). This is likely a CORS or network restriction in the browser.')
                return
            text = await resp.text()
        except Exception as ex:
            print('Fetch exception (likely CORS or blocked):', ex)
            return

    if not _is_csv_like(text):
        print('Remote response is not a CSV or looks empty. Please check the symbol or fetch via a server/proxy.')
        return

    # parse into pandas DataFrame
    df = parse_csv_text(text)
    if df is None:
        print('Parsing failed — make sure pandas is available in PyScript environment')
        return

    # save into localStorage under a timestamped name
    name = f'{sym}_{datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")}.csv'
    localStorage.setItem(name, text)
    print(f'Saved {name} into localStorage')
    # update storage UI (call JS helper)
    update_storage_js()


def update_storage_js():
    # collect keys
    items = []
    for i in range(localStorage.length):
        key = localStorage.key(i)
        if key and key.endswith('.csv'):
            items.append(key)
    js_items = JSON.stringify(items)
    # call the JS global update function
    try:
        js_update = __import__('js').window._tradingui_update_storage
        js_update(js_items)
    except Exception:
        # ignore if not available
        pass


def py_list_storage(evt=None):
    update_storage_js()


def py_upload(evt):
    # evt is a JS event — read the first file
    try:
        files = evt.target.files
        f = files.item(0)
        if not f:
            print('No file chosen')
            return
        # read as text via JS FileReader
        fr = __import__('js').FileReader.new()

        def _onload(e):
            csv_text = fr.result
            if not _is_csv_like(csv_text):
                print('Uploaded file does not appear to be CSV-like')
                return
            # store
            name = f.name
            localStorage.setItem(name, csv_text)
            print(f'Uploaded and stored {name} in localStorage')
            update_storage_js()

        fr.onload = _onload
        fr.readAsText(f)
    except Exception as exc:
        print('Upload error:', exc)


def py_plot_from_storage(evt=None):
    sel = document.getElementById('plot_csv_select')
    if not sel:
        print('Plot select not found')
        return
    name = sel.value
    if not name:
        print('No CSV selected')
        return
    csv_text = localStorage.getItem(name)
    if not csv_text:
        print('Selected CSV not found in localStorage')
        return

    df = parse_csv_text(csv_text)
    if df is None:
        print('Failed to parse CSV for plotting (pandas may be missing)')
        return

    style = document.getElementById('plot_style').value
    _plot_df_plotly(df, 'plot_area', style)


def _plot_df_plotly(df, div_id, style='line'):
    """Create Plotly OHLC/Candlestick/Line plot from a dataframe with Date/Open/High/Low/Close
    """
    # convert dates and values to pure Python lists (serializable to JS)
    dates = list(df['Date'].astype(str))
    close = list(df['Close'].astype(float)) if 'Close' in df.columns else []
    open_ = list(df['Open'].astype(float)) if 'Open' in df.columns else []
    high = list(df['High'].astype(float)) if 'High' in df.columns else []
    low = list(df['Low'].astype(float)) if 'Low' in df.columns else []

    # heikin-ashi option
    if style == 'heikinashi':
        ha = heikin_ashi(df)
        dates = list(ha['Date'].astype(str))
        open_ = list(ha['HA_Open'].astype(float))
        high = list(ha['HA_High'].astype(float))
        low = list(ha['HA_Low'].astype(float))
        close = list(ha['HA_Close'].astype(float))

    layout = {
        'title': f'OHLC — {div_id}',
        'xaxis': {'rangeslider': {'visible': False}},
        'height': 480
    }

    if style == 'line':
        trace = {
            'x': dates,
            'y': close,
            'mode': 'lines',
            'name': 'Close'
        }
        js.window.Plotly.newPlot(div_id, [trace], layout)
    else:
        # candlestick / heikin-ashi -> Plotly OHLC (candlestick trace)
        trace = {
            'x': dates,
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'type': 'candlestick',
            'name': 'OHLC'
        }
        js.window.Plotly.newPlot(div_id, [trace], layout)


# Allow JS callers to trigger the listing easily
def list_storage_and_update():
    py_list_storage()


print('PyScript tradingui module loaded — use the Fetch, Storage, and Plot tabs.')

