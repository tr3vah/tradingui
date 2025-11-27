"""Helper runner for the trading UI app.

Sets up the local src/ path so you can run without installing the package.
"""
import os
import sys

ROOT = os.path.dirname(__file__)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from tradingui.gui import run_app


def _serve_web(port=8000):
    """Serve the web/ directory using a minimal HTTP server so PyScript assets can be opened in browser."""
    import http.server
    import socketserver
    import os

    webdir = os.path.join(os.path.dirname(__file__), 'web')
    if not os.path.isdir(webdir):
        print('No web/ directory available. Create one first.')
        return

    os.chdir(webdir)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f'Serving web/ directory at http://localhost:{port}/ (CTRL-C to stop)')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nShutting down web server')


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in ('web', 'serve'):
        port = 8000
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
            port = int(sys.argv[2])
        _serve_web(port)
    elif len(sys.argv) > 1 and sys.argv[1] in ('api', 'server'):
        # Run the backend proxy API server (uvicorn)
        from tradingui import api as trading_api
        port = 8001
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
            port = int(sys.argv[2])
        import uvicorn
        print(f'Starting API server on http://0.0.0.0:{port}')
        uvicorn.run(trading_api.app, host='0.0.0.0', port=port)
    else:
        run_app()
