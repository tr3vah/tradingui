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


if __name__ == '__main__':
    run_app()
