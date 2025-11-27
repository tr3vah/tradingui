import os
import threading
import os
import subprocess
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import pandas as pd

from .fetcher import normalize_symbol, fetch_data, list_saved_data, DATA_DIR
from .plotter import plot_dataframe

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover - optional
    FigureCanvasTkAgg = None


class TradingUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Trading UI — Historical Data Fetcher")
        self.geometry("1000x700")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)

        self.fetch_tab = ttk.Frame(self.notebook)
        self.storage_tab = ttk.Frame(self.notebook)
        self.plot_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.fetch_tab, text='Fetch')
        self.notebook.add(self.storage_tab, text='Storage')
        self.notebook.add(self.plot_tab, text='Plot')

        self.build_fetch_tab()
        self.build_storage_tab()
        self.build_plot_tab()

    def build_fetch_tab(self):
        frame = self.fetch_tab

        left = ttk.Frame(frame, padding=10)
        left.pack(side='left', fill='y')
        right = ttk.Frame(frame, padding=10)
        right.pack(side='left', fill='both', expand=True)

        ttk.Label(left, text='Asset Type').pack(anchor='w')
        self.asset_type = ttk.Combobox(left, values=['Stocks', 'Forex', 'Commodities', 'Crypto', 'Index', 'Other'])
        self.asset_type.set('Stocks')
        self.asset_type.pack(fill='x')

        ttk.Label(left, text='Ticker (e.g. AAPL, EUR/USD, GC)').pack(anchor='w', pady=(8, 0))
        self.ticker_entry = ttk.Entry(left)
        self.ticker_entry.insert(0, 'AAPL')
        self.ticker_entry.pack(fill='x')

        ttk.Label(left, text='Range type').pack(anchor='w', pady=(8, 0))
        self.range_type = tk.StringVar(value='period')
        ttk.Radiobutton(left, text='Relative (last X)', variable=self.range_type, value='period').pack(anchor='w')
        ttk.Radiobutton(left, text='Custom start / end', variable=self.range_type, value='custom').pack(anchor='w')

        ttk.Label(left, text='Period (when relative)').pack(anchor='w', pady=(8, 0))
        self.period_cb = ttk.Combobox(left, values=['1d', '5d', '1mo', '3mo', '6mo', '1y', '5y', 'max'])
        self.period_cb.set('1mo')
        self.period_cb.pack(fill='x')

        ttk.Label(left, text='Start date (YYYY-MM-DD)').pack(anchor='w', pady=(8, 0))
        self.start_entry = ttk.Entry(left)
        self.start_entry.pack(fill='x')

        ttk.Label(left, text='End date (YYYY-MM-DD)').pack(anchor='w', pady=(8, 0))
        self.end_entry = ttk.Entry(left)
        self.end_entry.pack(fill='x')

        ttk.Label(left, text='Interval').pack(anchor='w', pady=(8, 0))
        self.interval_cb = ttk.Combobox(left, values=['1d', '1wk', '1mo', '1m', '5m', '1h'])
        self.interval_cb.set('1d')
        self.interval_cb.pack(fill='x')

        self.fetch_btn = ttk.Button(left, text='Fetch & Save', command=self.on_fetch)
        self.fetch_btn.pack(fill='x', pady=(12, 0))

        ttk.Separator(right, orient='horizontal').pack(fill='x', pady=6)
        self.log_text = tk.Text(right)
        self.log_text.pack(fill='both', expand=True)

    def log(self, msg: str):
        self.log_text.insert('end', msg + '\n')
        self.log_text.see('end')

    def on_fetch(self):
        asset_type = self.asset_type.get()
        ticker = self.ticker_entry.get().strip()
        if not ticker:
            messagebox.showerror('Error', 'Ticker cannot be empty')
            return

        symbol = normalize_symbol(asset_type, ticker)
        range_type = self.range_type.get()
        start = self.start_entry.get().strip() or None
        end = self.end_entry.get().strip() or None
        period = self.period_cb.get().strip() or None
        interval = self.interval_cb.get().strip() or '1d'

        def run():
            try:
                self.fetch_btn.config(state='disabled')
                self.log(f'Fetching {symbol} ...')
                if range_type == 'period':
                    df, path = fetch_data(symbol, period=period, interval=interval, save=True)
                else:
                    df, path = fetch_data(symbol, start=start, end=end, interval=interval, save=True)
                self.log(f'Saved to {path}')
                # prompt to refresh storage tab
                self.refresh_storage()
            except Exception as e:
                messagebox.showerror('Fetch error', str(e))
                self.log(f'Error: {e}')
            finally:
                self.fetch_btn.config(state='normal')

        threading.Thread(target=run, daemon=True).start()

    # Storage tab
    def build_storage_tab(self):
        frame = self.storage_tab
        left = ttk.Frame(frame, padding=10)
        left.pack(side='left', fill='y')
        right = ttk.Frame(frame, padding=10)
        right.pack(side='left', fill='both', expand=True)

        ttk.Label(left, text='Saved CSV files').pack(anchor='w')
        self.files_list = tk.Listbox(left, width=40)
        self.files_list.pack(fill='y', expand=True)
        ttk.Button(left, text='Refresh', command=self.refresh_storage).pack(fill='x', pady=(8, 0))
        ttk.Button(left, text='Delete Selected', command=self.delete_selected).pack(fill='x', pady=(4, 0))

        ttk.Label(right, text='Preview (first/last rows)').pack(anchor='w')
        self.preview_text = tk.Text(right)
        self.preview_text.pack(fill='both', expand=True)

        self.refresh_storage()

    def refresh_storage(self):
        files = list_saved_data()
        self.files_list.delete(0, 'end')
        for f in files:
            self.files_list.insert('end', f)

    def delete_selected(self):
        sel = self.files_list.curselection()
        if not sel:
            return
        path = self.files_list.get(sel[0])
        if messagebox.askyesno('Delete', f'Delete {path}?'):
            try:
                os.remove(path)
                self.refresh_storage()
            except Exception as e:
                messagebox.showerror('Error', str(e))

    # Plot tab
    def build_plot_tab(self):
        frame = self.plot_tab
        ctrl = ttk.Frame(frame, padding=10)
        ctrl.pack(side='left', fill='y')
        canvas_f = ttk.Frame(frame, padding=10)
        canvas_f.pack(side='left', fill='both', expand=True)

        ttk.Label(ctrl, text='Choose CSV to plot').pack(anchor='w')
        self.plot_files = ttk.Combobox(ctrl, values=list_saved_data())
        self.plot_files.pack(fill='x')

        ttk.Label(ctrl, text='Plot style').pack(anchor='w', pady=(8, 0))
        self.plot_style = ttk.Combobox(ctrl, values=['line', 'candle', 'heikin'])
        self.plot_style.set('candle')
        self.plot_style.pack(fill='x')

        ttk.Button(ctrl, text='Refresh List', command=self.refresh_plot_list).pack(fill='x', pady=(8, 0))
        ttk.Button(ctrl, text='Plot', command=self.on_plot).pack(fill='x', pady=(8, 0))
        ttk.Button(ctrl, text='Save Image', command=self.on_save_plot).pack(fill='x', pady=(8, 0))

        self.canvas_f = canvas_f
        self.current_fig = None
        self.current_ax = None

    def refresh_plot_list(self):
        items = list_saved_data()
        self.plot_files['values'] = items

    def on_plot(self):
        path = self.plot_files.get()
        style = self.plot_style.get() or 'candle'
        if not path or not os.path.exists(path):
            messagebox.showerror('Error', 'Select a valid saved CSV first')
            return

        df = pd.read_csv(path, parse_dates=['Date'], index_col='Date')

        # Show matplotlib widget if available, else fallback to saving a tempfile and opening externally
        if FigureCanvasTkAgg is None:
            # just try to plot and save to a temp file
            plot_dataframe(df, style=style)
            messagebox.showinfo('Plot', 'Plot created (mpl not available inside UI)')
            return

        # clear previous
        for w in self.canvas_f.winfo_children():
            w.destroy()

        fig = plt.Figure(figsize=(9, 6))
        ax = fig.add_subplot(111)
        # use plotter to render directly into a file then display image, or draw simple line
        if style == 'line':
            ax.plot(df.index, df['Close'])
            ax.set_title(path)
        else:
            # use mplfinance to draw directly into our Figure by saving to a temporary image and showing with imshow
            import io
            import matplotlib.image as mpimg
            import tempfile

            tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            tmp.close()
            plot_dataframe(df, style=style, title=os.path.basename(path), savefile=tmp.name)
            img = mpimg.imread(tmp.name)
            ax.imshow(img)
            ax.axis('off')

        self.current_fig = fig
        self.current_ax = ax
        canvas = FigureCanvasTkAgg(fig, master=self.canvas_f)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def on_save_plot(self):
        if self.current_fig is None:
            messagebox.showerror('Error', 'No plot rendered yet')
            return
        file = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG Image', '*.png')])
        if not file:
            return
        self.current_fig.savefig(file)
        messagebox.showinfo('Saved', f'Figure saved to {file}')


def run_app():
    app = TradingUI()

    # Support an automated capture mode (useful for headless screenshotting)
    # Set TRADINGUI_CAPTURE_TAB to one of: 'Fetch', 'Storage', 'Plot' to auto-select a tab
    # and save a screenshot to /tmp/tradingui_<tab>.png then exit.
    capture_tab = os.environ.get('TRADINGUI_CAPTURE_TAB')
    if capture_tab:
        def do_capture():
            # map names to notebook tab indices
            mapping = {'Fetch': 0, 'Storage': 1, 'Plot': 2}
            idx = mapping.get(capture_tab, 0)
            try:
                app.notebook.select(idx)
                app.update_idletasks()
                # allow a moment for render
                app.after(500, lambda: _take_window_screenshot_and_exit(app, capture_tab))
            except Exception:
                # fall back to immediate capture
                _take_window_screenshot_and_exit(app, capture_tab)

        app.after(250, do_capture)
    app.mainloop()


if __name__ == '__main__':
    run_app()


def _take_window_screenshot_and_exit(app: TradingUI, tab_name: str):
    """Capture the app window using xwd/convert when available and then exit the app.

    This expects an X server and xwd + convert (ImageMagick) to be present.
    """
    outfile = f'/tmp/tradingui_{tab_name.lower()}.png'
    try:
        app.update_idletasks()
        wid = app.winfo_id()
        # find xwd + convert
        xwd = shutil.which('xwd')
        convert = shutil.which('convert') or shutil.which('magick')
        if xwd and convert:
            # dump xwd and convert to png
            xwd_out = outfile + '.xwd'
            subprocess.run([xwd, '-silent', '-id', str(wid), '-out', xwd_out], check=True)
            subprocess.run([convert, xwd_out, outfile], check=True)
            try:
                os.remove(xwd_out)
            except Exception:
                pass
        else:
            # fallback: try `import` from ImageMagick if present
            imp = shutil.which('import')
            if imp:
                subprocess.run([imp, '-display', os.environ.get('DISPLAY', ':0'), '-window', str(wid), outfile], check=True)
        print('captured:', outfile)
    except Exception as e:
        print('capture failed:', e)
    finally:
        app.quit()
