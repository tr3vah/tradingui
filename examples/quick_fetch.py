"""Example script: fetch a ticker using the fetcher and plot with the plotter.

This script is for local use. It will attempt to download if yfinance is available.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tradingui.fetcher import normalize_symbol, fetch_data
from tradingui.plotter import plot_dataframe


def main():
    symbol = normalize_symbol('Stocks', 'AAPL')
    print('Fetching', symbol)
    df, path = fetch_data(symbol, period='1mo', interval='1d', save=True)
    print('Saved to', path)
    plot_dataframe(df, style='candle', title=symbol, savefile='example_plot.png')
    print('Saved examplePlot.png')


if __name__ == '__main__':
    main()
