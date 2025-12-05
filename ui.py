import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import sys
import pandas as pd
from datetime import datetime

# Import Portfolio class and utils from your existing code
try:
    from portfolio import Portfolio
    import utils
    from utils import (
        annualized_cumulative_return,
        annualized_volatility,
        annualized_sharpe_ratio,
        beta_single_stock,
        alpha_single_stock,
        correlation_matrix,
        annualized_sofr
    )
    from charting import PortfolioChartManager, calculate_portfolio_daily_returns
except ImportError as e:
    messagebox.showerror("Error",
                         f"Required modules not found: {e}\nPlease ensure portfolio.py, utils.py, and charting.py are in the same directory.")
    sys.exit(1)


class TickerEntryDialog:
    """Dialog for adding or editing a ticker entry."""

    def __init__(self, parent, available_tickers, ticker="", weight=0.0, title="Add Ticker"):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.geometry("400x200")
        self.top.resizable(False, False)

        # Make modal
        self.top.transient(parent)
        self.top.grab_set()

        # Center the dialog
        self.top.update_idletasks()
        x = (self.top.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.top.winfo_screenheight() // 2) - (200 // 2)
        self.top.geometry(f"400x200+{x}+{y}")

        # Main frame
        main_frame = ttk.Frame(self.top, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Ticker input
        ttk.Label(main_frame, text="Ticker Symbol:", font=("Arial", 11)).grid(row=0, column=0, sticky=tk.W, pady=10)
        self.ticker_var = tk.StringVar(value=ticker)
        self.ticker_combo = ttk.Combobox(
            main_frame,
            textvariable=self.ticker_var,
            values=available_tickers,
            font=("Arial", 11),
            width=20
        )
        self.ticker_combo.grid(row=0, column=1, sticky=tk.EW, padx=10, pady=10)
        self.ticker_combo.focus()

        # Weight input
        ttk.Label(main_frame, text="Weight (%):", font=("Arial", 11)).grid(row=1, column=0, sticky=tk.W, pady=10)
        self.weight_var = tk.StringVar(value=str(weight))
        self.weight_entry = ttk.Entry(main_frame, textvariable=self.weight_var, font=("Arial", 11), width=20)
        self.weight_entry.grid(row=1, column=1, sticky=tk.EW, padx=10, pady=10)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="OK", command=self._ok, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._cancel, width=10).pack(side=tk.LEFT, padx=5)

        # Configure grid
        main_frame.columnconfigure(1, weight=1)

        # Bind Enter key to OK
        self.top.bind('<Return>', lambda e: self._ok())
        self.top.bind('<Escape>', lambda e: self._cancel())

        # Wait for window to close
        parent.wait_window(self.top)

    def _ok(self):
        """Validate and accept the input."""
        ticker = self.ticker_var.get().strip().upper()
        weight_str = self.weight_var.get().strip()

        if not ticker:
            messagebox.showerror("Error", "Please enter a ticker symbol.", parent=self.top)
            return

        try:
            weight = float(weight_str)
            if weight < 0:
                messagebox.showerror("Error", "Weight must be non-negative.", parent=self.top)
                return
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number for weight.", parent=self.top)
            return

        self.result = {'ticker': ticker, 'weight': weight}
        self.top.destroy()

    def _cancel(self):
        """Cancel the dialog."""
        self.result = None
        self.top.destroy()


class PortfolioManagerUI:
    """Main application for portfolio management with tkinter UI."""

    def __init__(self, root):
        self.root = root
        self.root.title("Portfolio Manager v1.0")
        self.root.geometry("1400x800")
        self.root.minsize(1200, 700)

        # Data storage paths
        self.portfolios_dir = Path("user_data/portfolios")
        self.portfolios_dir.mkdir(parents=True, exist_ok=True)

        # Current portfolio being edited
        self.current_portfolio: Optional[Portfolio] = None
        self.current_file: Optional[Path] = None
        self.portfolio_metrics: Optional[Dict] = None

        # Chart manager
        self.chart_manager = PortfolioChartManager()
        self.current_chart_canvas = None

        # Store portfolio and benchmark daily returns for charting
        self.portfolio_daily_returns: Optional[pd.Series] = None
        self.benchmark_daily_returns: Optional[pd.Series] = None

        # Available tickers (you can expand this or load from database)
        self.available_tickers = self._load_available_tickers()

        self._setup_ui()
        self._load_portfolio_list()

    def _load_available_tickers(self) -> List[str]:
        """Load available tickers from data directory or hardcoded list."""
        # Retrieve the configured data directory from utils
        data_dir = Path(utils.get_data_dir())

        if data_dir.exists():
            tickers = []
            for file in data_dir.glob("*.csv"):
                tickers.append(file.stem)
            if tickers:
                return sorted(tickers)

        # Fallback to common tickers
        return sorted([
            "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "NFLX",
            "AMD", "INTC", "JPM", "BAC", "GS", "MS", "V", "MA", "SPY", "QQQ",
            "DIA", "IWM", "BRK.B", "JNJ", "PG", "KO", "PEP", "WMT", "HD", "DIS"
        ])

    def _setup_ui(self):
        """Setup the main UI layout."""
        # Main container with two panes
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel - File explorer
        self._setup_left_panel()

        # Right panel - Portfolio editor and metrics
        self._setup_right_panel()

    def _setup_left_panel(self):
        """Setup the left file explorer panel with portfolio list and console."""
        left_frame = ttk.Frame(self.paned_window, relief=tk.GROOVE, borderwidth=2)
        self.paned_window.add(left_frame, weight=1)

        # Create vertical paned window for portfolio list and console
        left_paned = ttk.PanedWindow(left_frame, orient=tk.VERTICAL)
        left_paned.pack(fill=tk.BOTH, expand=True)

        # --- Top Half: Portfolio Explorer ---
        explorer_frame = ttk.Frame(left_paned, relief=tk.GROOVE, borderwidth=1)
        left_paned.add(explorer_frame, weight=1)

        # Title
        title_label = ttk.Label(explorer_frame, text="Portfolios", font=("Arial", 14, "bold"))
        title_label.pack(pady=5)

        # Toolbar
        toolbar = ttk.Frame(explorer_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="New", command=self._new_portfolio, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Load", command=self._load_portfolio, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Refresh", command=self._load_portfolio_list, width=8).pack(side=tk.LEFT, padx=2)

        # Portfolio list with scrollbar
        list_frame = ttk.Frame(explorer_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.portfolio_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Arial", 10),
            selectmode=tk.SINGLE
        )
        self.portfolio_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.portfolio_listbox.yview)

        self.portfolio_listbox.bind('<Double-Button-1>', lambda e: self._load_selected_portfolio())

        # Info label
        self.info_label = ttk.Label(explorer_frame, text="Double-click to load", font=("Arial", 9))
        self.info_label.pack(pady=3)

        # --- Bottom Half: Console/Log ---
        console_frame = ttk.Frame(left_paned, relief=tk.GROOVE, borderwidth=1)
        left_paned.add(console_frame, weight=1)

        # Console title and controls
        console_header = ttk.Frame(console_frame)
        console_header.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(console_header, text="Activity Log", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        ttk.Button(console_header, text="Clear", command=self._clear_console, width=8).pack(side=tk.RIGHT, padx=2)

        # Console text widget with scrollbar
        console_text_frame = ttk.Frame(console_frame)
        console_text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        console_scrollbar = ttk.Scrollbar(console_text_frame)
        console_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.console_text = tk.Text(
            console_text_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            state=tk.DISABLED,
            yscrollcommand=console_scrollbar.set,
            height=10
        )
        self.console_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        console_scrollbar.config(command=self.console_text.yview)

        # Configure text tags for different log levels
        self.console_text.tag_configure("INFO", foreground="#4ec9b0")
        self.console_text.tag_configure("SUCCESS", foreground="#6a9955")
        self.console_text.tag_configure("WARNING", foreground="#dcdcaa")
        self.console_text.tag_configure("ERROR", foreground="#f48771")
        self.console_text.tag_configure("TIMESTAMP", foreground="#858585")

        # Log startup
        self._log_to_console("Application started", "INFO")

    def _setup_right_panel(self):
        """Setup the right portfolio editor panel."""
        right_frame = ttk.Frame(self.paned_window, relief=tk.GROOVE, borderwidth=2)
        self.paned_window.add(right_frame, weight=3)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 1: Portfolio Editor
        self.editor_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.editor_tab, text="Portfolio Editor")
        self._setup_editor_tab()

        # Tab 2: Metrics & Analysis (with subtabs)
        self.analysis_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.analysis_tab, text="Metrics & Analysis")
        self._setup_analysis_tab()

        # Status bar
        self.status_bar = ttk.Label(right_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _setup_editor_tab(self):
        """Setup the portfolio editor tab."""
        # Title section
        title_frame = ttk.Frame(self.editor_tab)
        title_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(title_frame, text="Portfolio Editor", font=("Arial", 16, "bold")).pack(anchor=tk.W)

        # Portfolio name section
        name_frame = ttk.LabelFrame(self.editor_tab, text="Portfolio Details", padding=10)
        name_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(name_frame, text="Name:", font=("Arial", 12)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.name_entry = ttk.Entry(name_frame, font=("Arial", 12), width=40)
        self.name_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        # Holdings section with Treeview (spreadsheet-style)
        holdings_frame = ttk.LabelFrame(self.editor_tab, text="Holdings", padding=10)
        holdings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview frame
        tree_frame = ttk.Frame(holdings_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Create Treeview with scrollbars
        self.holdings_tree = ttk.Treeview(
            tree_frame,
            columns=("Ticker", "Weight"),
            show="headings",
            selectmode="browse",
            height=15
        )

        # Configure columns
        self.holdings_tree.heading("Ticker", text="Ticker", command=lambda: self._sort_column("Ticker", False))
        self.holdings_tree.heading("Weight", text="Weight (%)", command=lambda: self._sort_column("Weight", False))

        self.holdings_tree.column("Ticker", width=150, anchor=tk.CENTER)
        self.holdings_tree.column("Weight", width=150, anchor=tk.CENTER)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.holdings_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.holdings_tree.xview)
        self.holdings_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid layout
        self.holdings_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Bind double-click to edit
        self.holdings_tree.bind("<Double-Button-1>", self._on_tree_double_click)
        self.holdings_tree.bind("<Return>", self._on_tree_double_click)

        # Holdings control buttons
        controls_frame = ttk.Frame(holdings_frame)
        controls_frame.pack(fill=tk.X, pady=5)

        ttk.Button(controls_frame, text="Add Ticker", command=self._add_ticker_row).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Edit Selected", command=self._edit_selected_ticker).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Remove Selected", command=self._remove_selected_ticker).pack(side=tk.LEFT,
                                                                                                      padx=5)
        ttk.Button(controls_frame, text="Import CSV", command=self._import_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Export CSV", command=self._export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Equal Weight All", command=self._equal_weight_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Normalize Weights", command=self._normalize_weights).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Clear All", command=self._clear_all_tickers).pack(side=tk.LEFT, padx=5)

        # Total weight label
        self.total_weight_label = ttk.Label(controls_frame, text="Total: 0.00%", font=("Arial", 10, "bold"))
        self.total_weight_label.pack(side=tk.RIGHT, padx=10)

        # Action buttons
        action_frame = ttk.Frame(self.editor_tab)
        action_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(action_frame, text="Save Portfolio", command=self._save_portfolio, width=15).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(action_frame, text="Save As...", command=self._save_portfolio_as, width=15).pack(side=tk.LEFT,
                                                                                                    padx=5)
        ttk.Button(action_frame, text="Export Summary", command=self._export_summary, width=15).pack(side=tk.LEFT,
                                                                                                     padx=5)

    def _setup_analysis_tab(self):
        """Setup the analysis tab with subtabs for Results and Charting."""
        # Title
        title_frame = ttk.Frame(self.analysis_tab)
        title_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(title_frame, text="Portfolio Analysis", font=("Arial", 16, "bold")).pack(anchor=tk.W)

        # Simulation parameters
        params_frame = ttk.LabelFrame(self.analysis_tab, text="Simulation Parameters", padding=10)
        params_frame.pack(fill=tk.X, padx=10, pady=5)

        # Date range
        date_frame = ttk.Frame(params_frame)
        date_frame.pack(fill=tk.X, pady=5)

        ttk.Label(date_frame, text="Start Date:", width=12).pack(side=tk.LEFT, padx=5)
        self.start_date_entry = ttk.Entry(date_frame, width=12)
        self.start_date_entry.insert(0, "2020-01-01")
        self.start_date_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(date_frame, text="End Date:", width=12).pack(side=tk.LEFT, padx=5)
        self.end_date_entry = ttk.Entry(date_frame, width=12)
        self.end_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.end_date_entry.pack(side=tk.LEFT, padx=5)

        # Frequency
        freq_frame = ttk.Frame(params_frame)
        freq_frame.pack(fill=tk.X, pady=5)

        ttk.Label(freq_frame, text="Frequency:", width=12).pack(side=tk.LEFT, padx=5)
        self.frequency_var = tk.StringVar(value="daily")
        freq_combo = ttk.Combobox(freq_frame, textvariable=self.frequency_var,
                                  values=["daily", "weekly", "monthly"], width=12, state="readonly")
        freq_combo.pack(side=tk.LEFT, padx=5)

        ttk.Label(freq_frame, text="Market Ticker:", width=12).pack(side=tk.LEFT, padx=5)
        self.market_ticker_var = tk.StringVar(value="SPY")
        market_combo = ttk.Combobox(freq_frame, textvariable=self.market_ticker_var,
                                    values=self.available_tickers, width=12)
        market_combo.pack(side=tk.LEFT, padx=5)

        # Use CSV checkbox
        self.use_csv_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(freq_frame, text="Use CSV data", variable=self.use_csv_var).pack(side=tk.LEFT, padx=10)

        # Run simulation button
        ttk.Button(params_frame, text="Run Analysis", command=self._run_analysis,
                   style="Accent.TButton").pack(pady=10)

        # Create subtabs for results and charting
        self.analysis_notebook = ttk.Notebook(self.analysis_tab)
        self.analysis_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Subtab 1: Analysis Results
        self.results_tab = ttk.Frame(self.analysis_notebook)
        self.analysis_notebook.add(self.results_tab, text="Analysis Results")
        self._setup_results_subtab()

        # Subtab 2: Charting
        self.charting_tab = ttk.Frame(self.analysis_notebook)
        self.analysis_notebook.add(self.charting_tab, text="Charting")
        self._setup_charting_subtab()

    def _setup_results_subtab(self):
        """Setup the results display subtab."""
        results_frame = ttk.LabelFrame(self.results_tab, text="Analysis Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create text widget with scrollbar for results
        text_frame = ttk.Frame(results_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.results_text = tk.Text(text_frame, wrap=tk.WORD, font=("Courier", 12),
                                    state=tk.DISABLED, bg="#f5f5f5")
        results_scrollbar = ttk.Scrollbar(text_frame, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=results_scrollbar.set)

        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure text tags for formatting
        self.results_text.tag_configure("header", font=("Courier", 14, "bold"))
        self.results_text.tag_configure("subheader", font=("Courier", 12, "bold"))
        self.results_text.tag_configure("value", foreground="#0066cc")

    def _setup_charting_subtab(self):
        """Setup the charting subtab."""
        # Chart type selector
        control_frame = ttk.Frame(self.charting_tab)
        control_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(control_frame, text="Chart Type:", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)

        self.chart_type_var = tk.StringVar(value="Equity Curve")
        chart_types = ["Equity Curve", "Drawdown", "Monthly Returns", "Returns Distribution"]

        chart_combo = ttk.Combobox(control_frame, textvariable=self.chart_type_var,
                                   values=chart_types, width=20, state="readonly")
        chart_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="Generate Chart", command=self._generate_chart).pack(side=tk.LEFT, padx=10)
        ttk.Button(control_frame, text="Save Chart", command=self._save_chart).pack(side=tk.LEFT, padx=5)

        # Chart display frame
        self.chart_display_frame = ttk.Frame(self.charting_tab, relief=tk.SUNKEN, borderwidth=2)
        self.chart_display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Placeholder label
        self.chart_placeholder = ttk.Label(
            self.chart_display_frame,
            text="Run analysis and click 'Generate Chart' to display charts",
            font=("Arial", 12),
            foreground="gray"
        )
        self.chart_placeholder.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def _sort_column(self, col, reverse):
        """Sort treeview by column."""
        self._log_to_console(f"Sorted holdings by {col}", "INFO")
        data = [(self.holdings_tree.set(child, col), child) for child in self.holdings_tree.get_children('')]

        # Sort numerically for Weight column
        if col == "Weight":
            data.sort(key=lambda x: float(x[0]), reverse=reverse)
        else:
            data.sort(reverse=reverse)

        for index, (_, child) in enumerate(data):
            self.holdings_tree.move(child, '', index)

        # Reverse sort next time
        self.holdings_tree.heading(col, command=lambda: self._sort_column(col, not reverse))

    def _on_tree_double_click(self, event):
        """Handle double-click on tree item to edit."""
        self._edit_selected_ticker()

    def _add_ticker_row(self, ticker: str = "", weight: float = 0.0):
        """Add a new ticker row to the holdings treeview."""
        # Open dialog to get ticker and weight
        dialog = TickerEntryDialog(self.root, self.available_tickers, ticker, weight)

        if dialog.result:
            ticker_value = dialog.result['ticker'].upper()
            weight_value = dialog.result['weight']

            # Check if ticker already exists
            for item in self.holdings_tree.get_children():
                if self.holdings_tree.item(item)['values'][0] == ticker_value:
                    messagebox.showwarning("Duplicate Ticker", f"{ticker_value} is already in the portfolio.")
                    self._log_to_console(f"Failed to add {ticker_value}: Already exists", "WARNING")
                    return

            # Add to treeview
            self.holdings_tree.insert("", tk.END, values=(ticker_value, f"{weight_value:.2f}"))
            self._update_total_weight()
            self._update_status(f"Added {ticker_value} with {weight_value:.2f}% weight")
            self._log_to_console(f"Added {ticker_value} ({weight_value:.2f}%)", "SUCCESS")

    def _edit_selected_ticker(self):
        """Edit the selected ticker in the treeview."""
        selection = self.holdings_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a ticker to edit.")
            return

        item = selection[0]
        values = self.holdings_tree.item(item)['values']
        current_ticker = values[0]
        current_weight = float(values[1])

        # Open dialog to edit
        dialog = TickerEntryDialog(
            self.root,
            self.available_tickers,
            current_ticker,
            current_weight,
            title="Edit Ticker"
        )

        if dialog.result:
            new_ticker = dialog.result['ticker'].upper()
            new_weight = dialog.result['weight']

            # Check if new ticker already exists (and it's not the same item)
            for check_item in self.holdings_tree.get_children():
                if check_item != item and self.holdings_tree.item(check_item)['values'][0] == new_ticker:
                    messagebox.showwarning("Duplicate Ticker", f"{new_ticker} is already in the portfolio.")
                    self._log_to_console(f"Failed to edit {current_ticker}: {new_ticker} already exists", "WARNING")
                    return

            # Update the item
            self.holdings_tree.item(item, values=(new_ticker, f"{new_weight:.2f}"))
            self._update_total_weight()
            self._update_status(f"Updated {new_ticker}")
            self._log_to_console(f"Updated {current_ticker} → {new_ticker} ({new_weight:.2f}%)", "SUCCESS")

    def _remove_selected_ticker(self):
        """Remove the selected ticker from the treeview."""
        selection = self.holdings_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a ticker to remove.")
            return

        item = selection[0]
        ticker = self.holdings_tree.item(item)['values'][0]

        if messagebox.askyesno("Confirm", f"Remove {ticker} from portfolio?"):
            self.holdings_tree.delete(item)
            self._update_total_weight()
            self._update_status(f"Removed {ticker}")
            self._log_to_console(f"Removed {ticker}", "INFO")

    def _update_total_weight(self):
        """Update the total weight label."""
        total = 0.0
        for item in self.holdings_tree.get_children():
            weight = float(self.holdings_tree.item(item)['values'][1])
            total += weight

        self.total_weight_label.config(text=f"Total: {total:.2f}%")

        # Color code the total (green if ~100%, yellow if close, red if far off)
        if abs(total - 100.0) < 0.01:
            self.total_weight_label.config(foreground="green")
        elif abs(total - 100.0) < 5.0:
            self.total_weight_label.config(foreground="orange")
        else:
            self.total_weight_label.config(foreground="red")

    def _equal_weight_all(self):
        """Set equal weights for all tickers."""
        children = self.holdings_tree.get_children()
        n = len(children)

        if n == 0:
            messagebox.showwarning("Warning", "No tickers added yet.")
            return

        equal_weight = 100.0 / n

        for item in children:
            ticker = self.holdings_tree.item(item)['values'][0]
            self.holdings_tree.item(item, values=(ticker, f"{equal_weight:.2f}"))

        self._update_total_weight()
        self._update_status(f"Set equal weights: {equal_weight:.2f}% each")
        self._log_to_console(f"Applied equal weights ({equal_weight:.2f}%) to {n} tickers", "SUCCESS")

    def _normalize_weights(self):
        """Normalize weights to sum to 100%."""
        children = self.holdings_tree.get_children()

        if not children:
            messagebox.showwarning("Warning", "No tickers to normalize.")
            return

        total = 0.0
        for item in children:
            weight = float(self.holdings_tree.item(item)['values'][1])
            total += weight

        if total == 0:
            messagebox.showerror("Error", "Cannot normalize: total weight is zero.")
            self._log_to_console("Failed to normalize: Total weight is zero", "ERROR")
            return

        for item in children:
            ticker = self.holdings_tree.item(item)['values'][0]
            weight = float(self.holdings_tree.item(item)['values'][1])
            normalized = (weight / total) * 100.0
            self.holdings_tree.item(item, values=(ticker, f"{normalized:.2f}"))

        self._update_total_weight()
        self._update_status("Weights normalized to 100%")
        self._log_to_console(f"Normalized weights from {total:.2f}% to 100%", "SUCCESS")

    def _clear_all_tickers(self):
        """Clear all ticker rows."""
        children = self.holdings_tree.get_children()

        if not children:
            return

        if messagebox.askyesno("Confirm", "Remove all tickers?"):
            count = len(children)
            for item in children:
                self.holdings_tree.delete(item)
            self._update_total_weight()
            self._update_status("All tickers cleared")
            self._log_to_console(f"Cleared all {count} tickers", "INFO")

    def _get_holdings_from_ui(self) -> Dict[str, float]:
        """Extract holdings dictionary from UI treeview."""
        holdings = {}

        for item in self.holdings_tree.get_children():
            values = self.holdings_tree.item(item)['values']
            ticker = values[0]
            weight = float(values[1]) / 100.0  # Convert percentage to decimal
            holdings[ticker] = weight

        return holdings

    def _import_csv(self):
        """Import holdings from a CSV file."""
        file_path = filedialog.askopenfilename(
            title="Import Holdings from CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            # Read CSV file
            df = pd.read_csv(file_path)

            # Check for required columns (case-insensitive)
            df.columns = df.columns.str.strip()
            column_map = {col.lower(): col for col in df.columns}

            if 'ticker' not in column_map or 'weight' not in column_map:
                messagebox.showerror(
                    "Error",
                    "CSV must contain 'Ticker' and 'Weight' columns.\n\n"
                    "Found columns: " + ", ".join(df.columns)
                )
                return

            ticker_col = column_map['ticker']
            weight_col = column_map['weight']

            # Ask if user wants to replace or append
            if self.holdings_tree.get_children():
                choice = messagebox.askyesnocancel(
                    "Import Mode",
                    "Current portfolio has holdings.\n\n"
                    "Yes = Replace existing holdings\n"
                    "No = Append to existing holdings\n"
                    "Cancel = Cancel import"
                )

                if choice is None:  # Cancel
                    return
                elif choice:  # Yes - Replace
                    self._clear_all_tickers_ui_only()

            # Import data
            imported_count = 0
            skipped_count = 0
            errors = []

            self._log_to_console(f"Starting CSV import from {Path(file_path).name}", "INFO")

            for idx, row in df.iterrows():
                try:
                    ticker = str(row[ticker_col]).strip().upper()
                    weight_val = row[weight_col]

                    # Skip empty rows
                    if pd.isna(ticker) or ticker == '' or ticker == 'NAN':
                        continue

                    # Parse weight - handle both decimal (0.5) and percentage (50) formats
                    if pd.isna(weight_val):
                        errors.append(f"Row {idx + 2}: Missing weight for {ticker}")
                        skipped_count += 1
                        continue

                    try:
                        weight = float(weight_val)
                    except (ValueError, TypeError):
                        errors.append(f"Row {idx + 2}: Invalid weight '{weight_val}' for {ticker}")
                        skipped_count += 1
                        continue

                    # Auto-detect if weight is in decimal (0-1) or percentage (>1) format
                    if 0 <= weight <= 1:
                        weight = weight * 100  # Convert decimal to percentage
                    elif weight < 0:
                        errors.append(f"Row {idx + 2}: Negative weight {weight} for {ticker}")
                        skipped_count += 1
                        continue

                    # Check if ticker already exists
                    ticker_exists = False
                    for item in self.holdings_tree.get_children():
                        if self.holdings_tree.item(item)['values'][0] == ticker:
                            # Update existing ticker weight
                            current_weight = float(self.holdings_tree.item(item)['values'][1])
                            self.holdings_tree.item(item, values=(ticker, f"{weight:.2f}"))
                            ticker_exists = True
                            break

                    if not ticker_exists:
                        # Add new ticker
                        self.holdings_tree.insert("", tk.END, values=(ticker, f"{weight:.2f}"))
                        imported_count += 1
                    else:
                        imported_count += 1  # Count updates as imports

                except Exception as e:
                    errors.append(f"Row {idx + 2}: {str(e)}")
                    skipped_count += 1

            # Update total weight display
            self._update_total_weight()

            # Show summary
            summary = f"Import completed!\n\n"
            summary += f"✓ Successfully imported: {imported_count} ticker(s)\n"

            if skipped_count > 0:
                summary += f"⚠ Skipped: {skipped_count} row(s)\n"

            if errors:
                summary += f"\nErrors:\n" + "\n".join(errors[:10])  # Show first 10 errors
                if len(errors) > 10:
                    summary += f"\n... and {len(errors) - 10} more errors"

            if imported_count > 0:
                messagebox.showinfo("Import Complete", summary)
                self._update_status(f"Imported {imported_count} tickers from CSV")
                self._log_to_console(f"CSV import complete: {imported_count} tickers imported, {skipped_count} skipped",
                                     "SUCCESS")
            else:
                messagebox.showwarning("Import Warning", summary)
                self._log_to_console("CSV import completed with warnings", "WARNING")

        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import CSV:\n\n{str(e)}")
            self._log_to_console(f"CSV import failed: {str(e)}", "ERROR")
            import traceback
            traceback.print_exc()

    def _export_csv(self):
        """Export current holdings to a CSV file."""
        if not self.holdings_tree.get_children():
            messagebox.showwarning("Warning", "No holdings to export.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Export Holdings to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            # Collect data from treeview
            data = []
            for item in self.holdings_tree.get_children():
                values = self.holdings_tree.item(item)['values']
                data.append({
                    'Ticker': values[0],
                    'Weight': float(values[1])
                })

            # Create DataFrame and save
            df = pd.DataFrame(data)
            df.to_csv(file_path, index=False)

            self._update_status(f"Exported {len(data)} tickers to CSV")
            self._log_to_console(f"Exported {len(data)} tickers to {Path(file_path).name}", "SUCCESS")
            messagebox.showinfo("Export Complete", f"Successfully exported {len(data)} ticker(s) to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export CSV:\n\n{str(e)}")
            self._log_to_console(f"CSV export failed: {str(e)}", "ERROR")

    def _run_analysis(self):
        """Run portfolio analysis with current parameters."""
        try:
            # Get current holdings
            holdings = self._get_holdings_from_ui()
            if not holdings:
                messagebox.showerror("Error", "Please add tickers to the portfolio first.")
                return

            name = self.name_entry.get().strip() or "Portfolio"
            portfolio = Portfolio(holdings=holdings, name=name)

            # Get parameters
            start_date = self.start_date_entry.get().strip()
            end_date = self.end_date_entry.get().strip()
            frequency = self.frequency_var.get()
            use_csv = self.use_csv_var.get()
            market_ticker = self.market_ticker_var.get()

            # Show progress
            self._update_status("Running analysis... Please wait.")
            self.root.update()

            # Calculate individual ticker metrics
            tickers = list(holdings.keys())

            # --- Analysis using selected frequency (e.g., Monthly/Weekly) ---
            from utils import _fetch_returns, parse_date
            start = parse_date(start_date)
            end = parse_date(end_date)

            # 1. Returns, Volatility, Sharpe, Correlation (Use selected frequency)
            returns_df = annualized_cumulative_return(tickers, start_date, end_date, frequency, use_csv)
            volatility_df = annualized_volatility(tickers, start_date, end_date, frequency, use_csv)
            sharpe_df = annualized_sharpe_ratio(tickers, start_date, end_date, frequency, use_csv)
            corr_matrix = correlation_matrix(tickers, start_date, end_date, frequency, use_csv)

            # Fetch returns series for volatility calculation (using selected frequency)
            returns_series = {}
            for ticker in tickers:
                returns_series[ticker] = _fetch_returns(ticker, start, end, frequency, use_csv)

            # 2. Beta and Alpha values
            beta_dict = {}
            alpha_dict = {}

            for ticker in tickers:
                try:
                    beta_df = beta_single_stock(ticker, start_date, end_date, frequency, use_csv, market_ticker)
                    beta_dict[ticker] = beta_df.iloc[0, 0]
                except Exception as e:
                    print(f"Could not calculate beta for {ticker}: {e}")
                    beta_dict[ticker] = None

                try:
                    alpha_df = alpha_single_stock(ticker, start_date, end_date, frequency, use_csv, market_ticker)
                    alpha_dict[ticker] = alpha_df.iloc[0, 0]
                except Exception as e:
                    print(f"Could not calculate alpha for {ticker}: {e}")
                    alpha_dict[ticker] = None

            # --- Portfolio Level Calculations (using selected frequency) ---
            portfolio_return = portfolio.portfolio_return(returns_df)['PortfolioReturn']
            portfolio_vol = portfolio.portfolio_volatility(returns_series, corr_matrix, annualize=True)

            beta_df_combined = pd.DataFrame.from_dict(beta_dict, orient='index', columns=['Beta'])
            portfolio_beta = portfolio.portfolio_beta(beta_df_combined, 'Beta')

            alpha_df_combined = pd.DataFrame.from_dict(alpha_dict, orient='index', columns=['Alpha'])
            portfolio_alpha = portfolio.portfolio_alpha(alpha_df_combined, 'Alpha')

            try:
                risk_free_rate = annualized_sofr(start_date, end_date, frequency)
            except:
                risk_free_rate = 0.0

            portfolio_sharpe = portfolio.portfolio_sharpe_ratio_true(portfolio_return, risk_free_rate, portfolio_vol)
            portfolio_treynor = portfolio.portfolio_treynor_ratio(portfolio_return, risk_free_rate, portfolio_beta)

            # --- NEW: Daily Series Construction (ALWAYS DAILY FOR DISTRIBUTION METRICS AND CHARTING) ---
            daily_returns_series = {}
            daily_freq = 'daily'

            for ticker in holdings.keys():
                daily_returns_series[ticker] = _fetch_returns(ticker, start, end, daily_freq, use_csv)

            # Create a dataframe of aligned daily returns
            aligned_daily_returns_df = pd.DataFrame(daily_returns_series).dropna()

            # Calculate weighted daily return: Sum(Weight_i * Return_i)
            portfolio_daily_ret = calculate_portfolio_daily_returns(holdings, daily_returns_series)

            # Store for charting
            self.portfolio_daily_returns = portfolio_daily_ret
            self.benchmark_daily_returns = _fetch_returns(market_ticker, start, end, daily_freq, use_csv=True)

            # --- Daily Drawdown Metrics (using portfolio_daily_ret) ---
            cum_ret = (1 + portfolio_daily_ret).cumprod()
            running_max = cum_ret.cummax()
            drawdown = (cum_ret - running_max) / running_max

            max_drawdown = drawdown.min()
            pct_from_hwm = drawdown.iloc[-1]

            # --- Daily Distribution Metrics (using portfolio_daily_ret) ---
            up_days_pct = (portfolio_daily_ret > 0).mean()
            daily_min = portfolio_daily_ret.min()
            daily_25 = portfolio_daily_ret.quantile(0.25)
            daily_median = portfolio_daily_ret.median()
            daily_75 = portfolio_daily_ret.quantile(0.75)
            daily_max = portfolio_daily_ret.max()
            daily_std_dev = portfolio_daily_ret.std()
            daily_skew = portfolio_daily_ret.skew()
            daily_kurt = portfolio_daily_ret.kurt()

            # Store metrics
            self.portfolio_metrics = {
                'portfolio_name': name,
                'simulation_params': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'frequency': frequency,
                    'market_ticker': market_ticker,
                    'risk_free_rate': float(risk_free_rate)
                },
                'individual_metrics': {
                    'returns': returns_df.to_dict()['AnnualizedReturn'],
                    'volatility': volatility_df.to_dict()['AnnualizedVolatility'],
                    'sharpe': sharpe_df.to_dict()['AnnualizedSharpeRatio'],
                    'beta': beta_dict,
                    'alpha': alpha_dict
                },
                'portfolio_metrics': {
                    'portfolio_return': float(portfolio_return),
                    'portfolio_volatility': float(portfolio_vol),
                    'portfolio_beta': float(portfolio_beta),
                    'portfolio_alpha': float(portfolio_alpha),
                    'portfolio_sharpe': float(portfolio_sharpe),
                    'portfolio_treynor': float(portfolio_treynor),
                    # Daily Drawdown
                    'max_drawdown': float(max_drawdown),
                    'pct_from_hwm': float(pct_from_hwm),
                    # Daily Stats
                    'up_days_pct': float(up_days_pct),
                    'daily_min': float(daily_min),
                    'daily_25': float(daily_25),
                    'daily_median': float(daily_median),
                    'daily_75': float(daily_75),
                    'daily_max': float(daily_max),
                    'daily_std': float(daily_std_dev),
                    'daily_skew': float(daily_skew),
                    'daily_kurt': float(daily_kurt)
                },
                'correlation_matrix': corr_matrix.to_dict()
            }

            # Display results
            self._display_results()

            self._update_status("Analysis complete!")
            messagebox.showinfo("Success", "Portfolio analysis completed successfully! You can now generate charts.")
            self._log_to_console("Portfolio analysis completed successfully", "SUCCESS")

        except Exception as e:
            messagebox.showerror("Error", f"Analysis failed:\n{str(e)}")
            self._update_status("Analysis failed")
            self._log_to_console(f"Analysis failed: {str(e)}", "ERROR")
            import traceback
            traceback.print_exc()

    def _display_results(self):
        """Display analysis results in the text widget."""
        if not self.portfolio_metrics:
            return

        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)

        metrics = self.portfolio_metrics
        params = metrics['simulation_params']
        individual = metrics['individual_metrics']
        portfolio = metrics['portfolio_metrics']

        # Get the frequency from params for dynamic labeling
        analysis_freq = params['frequency'].title()

        # Header
        self.results_text.insert(tk.END, "=" * 80 + "\n", "header")
        self.results_text.insert(tk.END, f"PORTFOLIO ANALYSIS RESULTS\n", "header")
        self.results_text.insert(tk.END, "=" * 80 + "\n\n", "header")

        # Simulation parameters
        self.results_text.insert(tk.END, "Simulation Parameters:\n", "subheader")
        self.results_text.insert(tk.END, f"  Period: {params['start_date']} to {params['end_date']}\n")
        self.results_text.insert(tk.END, f"  Frequency: {params['frequency']}\n")
        self.results_text.insert(tk.END, f"  Market Benchmark: {params['market_ticker']}\n")
        self.results_text.insert(tk.END,
                                 f"  Risk-Free Rate: {params['risk_free_rate']:.4f} ({params['risk_free_rate'] * 100:.2f}%)\n\n")

        # Portfolio-level metrics
        self.results_text.insert(tk.END, f"Portfolio-Level Metrics (Frequency: {analysis_freq}):\n", "subheader")
        self.results_text.insert(tk.END, f"  Annual Return:      ", "")
        self.results_text.insert(tk.END,
                                 f"{portfolio['portfolio_return']:.4f} ({portfolio['portfolio_return'] * 100:.2f}%)\n",
                                 "value")
        self.results_text.insert(tk.END, f"  Volatility (Ann.):  ", "")
        self.results_text.insert(tk.END,
                                 f"{portfolio['portfolio_volatility']:.4f} ({portfolio['portfolio_volatility'] * 100:.2f}%)\n",
                                 "value")
        self.results_text.insert(tk.END, f"  Sharpe Ratio:       ", "")
        self.results_text.insert(tk.END, f"{portfolio['portfolio_sharpe']:.4f}\n", "value")
        self.results_text.insert(tk.END, f"  Beta (β):           ", "")
        self.results_text.insert(tk.END, f"{portfolio['portfolio_beta']:.4f}\n", "value")
        self.results_text.insert(tk.END, f"  Alpha (α):          ", "")
        self.results_text.insert(tk.END,
                                 f"{portfolio['portfolio_alpha']:.4f} ({portfolio['portfolio_alpha'] * 100:.2f}%)\n",
                                 "value")
        self.results_text.insert(tk.END, f"  Treynor Ratio:      ", "")
        self.results_text.insert(tk.END, f"{portfolio['portfolio_treynor']:.4f}\n", "value")

        # Daily Drawdown Metrics
        self.results_text.insert(tk.END, f"  Max Drawdown:       ", "")
        self.results_text.insert(tk.END,
                                 f"{portfolio['max_drawdown']:.4f} ({portfolio['max_drawdown'] * 100:.2f}%)\n",
                                 "value")
        self.results_text.insert(tk.END, f"  % From Highwater:   ", "")
        self.results_text.insert(tk.END,
                                 f"{portfolio['pct_from_hwm']:.4f} ({portfolio['pct_from_hwm'] * 100:.2f}%)\n\n",
                                 "value")

        # Daily Return Metrics (Explicitly Daily)
        self.results_text.insert(tk.END, "Daily Return Statistics:\n", "subheader")

        # Daily Std, Min, Max
        self.results_text.insert(tk.END, f"  Daily Std Dev:      ", "")
        self.results_text.insert(tk.END, f"{portfolio['daily_std'] * 100:.2f}%\n", "value")
        self.results_text.insert(tk.END, f"  Minimum Return:     ", "")
        self.results_text.insert(tk.END, f"{portfolio['daily_min'] * 100:.2f}%\n", "value")
        self.results_text.insert(tk.END, f"  Maximum Return:     ", "")
        self.results_text.insert(tk.END, f"{portfolio['daily_max'] * 100:.2f}%\n\n", "value")

        # Quantiles & Up Days
        self.results_text.insert(tk.END, f"  % of Up Days:       ", "")
        self.results_text.insert(tk.END, f"{portfolio['up_days_pct'] * 100:.1f}%\n", "value")
        self.results_text.insert(tk.END, f"  25th Percentile:    ", "")
        self.results_text.insert(tk.END, f"{portfolio['daily_25'] * 100:.2f}%\n", "value")
        self.results_text.insert(tk.END, f"  Median (50th):      ", "")
        self.results_text.insert(tk.END, f"{portfolio['daily_median'] * 100:.2f}%\n", "value")
        self.results_text.insert(tk.END, f"  75th Percentile:    ", "")
        self.results_text.insert(tk.END, f"{portfolio['daily_75'] * 100:.2f}%\n\n", "value")

        # Distribution Shape
        self.results_text.insert(tk.END, f"  Skewness:           ", "")
        self.results_text.insert(tk.END, f"{portfolio['daily_skew']:.4f}\n", "value")
        self.results_text.insert(tk.END, f"  Kurtosis:           ", "")
        self.results_text.insert(tk.END, f"{portfolio['daily_kurt']:.4f}\n\n", "value")

        # Individual ticker metrics
        self.results_text.insert(tk.END, "Individual Ticker Metrics:\n", "subheader")
        self.results_text.insert(tk.END, "-" * 80 + "\n")
        self.results_text.insert(tk.END,
                                 f"{'Ticker':<8} {'Return':<12} {'Volatility':<12} {'Sharpe':<10} {'Beta':<10} {'Alpha':<10}\n")
        self.results_text.insert(tk.END, "-" * 80 + "\n")

        for ticker in individual['returns'].keys():
            ret = individual['returns'][ticker]
            vol = individual['volatility'][ticker]
            sharpe = individual['sharpe'][ticker]
            beta = individual['beta'].get(ticker, 'N/A')
            alpha = individual['alpha'].get(ticker, 'N/A')

            self.results_text.insert(tk.END, f"{ticker:<8} ")
            self.results_text.insert(tk.END, f"{ret:>11.2%} ", "value")
            self.results_text.insert(tk.END, f"{vol:>11.2%} ", "value")
            self.results_text.insert(tk.END, f"{sharpe:>9.4f} ", "value")

            if isinstance(beta, (int, float)):
                self.results_text.insert(tk.END, f"{beta:>9.4f} ", "value")
            else:
                self.results_text.insert(tk.END, f"{'N/A':>9} ")

            if isinstance(alpha, (int, float)):
                self.results_text.insert(tk.END, f"{alpha:>9.4f}\n", "value")
            else:
                self.results_text.insert(tk.END, f"{'N/A':>9}\n")

        self.results_text.config(state=tk.DISABLED)

    def _generate_chart(self):
        """Generate the selected chart type."""
        if self.portfolio_daily_returns is None or self.benchmark_daily_returns is None:
            messagebox.showwarning("Warning", "Please run analysis first before generating charts.")
            return

        try:
            # Clear previous chart
            if self.current_chart_canvas:
                self.current_chart_canvas.get_tk_widget().destroy()
                self.current_chart_canvas = None

            # Hide placeholder
            self.chart_placeholder.place_forget()

            chart_type = self.chart_type_var.get()
            portfolio_name = self.portfolio_metrics.get('portfolio_name', 'Portfolio')
            benchmark_name = self.portfolio_metrics['simulation_params']['market_ticker']

            # Generate the selected chart
            if chart_type == "Equity Curve":
                figure = self.chart_manager.create_equity_curve(
                    self.portfolio_daily_returns,
                    self.benchmark_daily_returns,
                    portfolio_name=portfolio_name,
                    benchmark_name=benchmark_name
                )
            elif chart_type == "Drawdown":
                figure = self.chart_manager.create_drawdown_chart(
                    self.portfolio_daily_returns,
                    self.benchmark_daily_returns,
                    portfolio_name=portfolio_name,
                    benchmark_name=benchmark_name
                )
            elif chart_type == "Monthly Returns":
                figure = self.chart_manager.create_monthly_returns_heatmap(
                    self.portfolio_daily_returns,
                    title=f"{portfolio_name} - Monthly Returns Heatmap"
                )
            elif chart_type == "Returns Distribution":
                figure = self.chart_manager.create_returns_distribution(
                    self.portfolio_daily_returns,
                    title=f"{portfolio_name} - Daily Returns Distribution"
                )
            else:
                messagebox.showerror("Error", f"Unknown chart type: {chart_type}")
                return

            # Embed the chart in the UI
            self.current_chart_canvas = self.chart_manager.embed_figure_in_tk(figure, self.chart_display_frame)
            self._update_status(f"Generated {chart_type} chart")
            self._log_to_console(f"Generated {chart_type} chart", "SUCCESS")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate chart:\n{str(e)}")
            self._log_to_console(f"Chart generation failed: {str(e)}", "ERROR")
            import traceback
            traceback.print_exc()

    def _save_chart(self):
        """Save the current chart to a file."""
        if self.current_chart_canvas is None:
            messagebox.showwarning("Warning", "No chart to save. Please generate a chart first.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("PDF files", "*.pdf"), ("SVG files", "*.svg"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            self.current_chart_canvas.figure.savefig(file_path, dpi=300, bbox_inches='tight')
            self._update_status(f"Chart saved to {Path(file_path).name}")
            self._log_to_console(f"Chart saved to {Path(file_path).name}", "SUCCESS")
            messagebox.showinfo("Success", f"Chart saved successfully to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save chart:\n{str(e)}")
            self._log_to_console(f"Chart save failed: {str(e)}", "ERROR")

    def _new_portfolio(self):
        """Clear the editor to create a new portfolio."""
        if self.holdings_tree.get_children():
            if not messagebox.askyesno("Confirm", "Clear current portfolio? Unsaved changes will be lost."):
                return

        self._clear_all_tickers_ui_only()
        self.name_entry.delete(0, tk.END)
        self.current_portfolio = None
        self.current_file = None
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state=tk.DISABLED)

        # Clear charting data
        self.portfolio_daily_returns = None
        self.benchmark_daily_returns = None
        if self.current_chart_canvas:
            self.current_chart_canvas.get_tk_widget().destroy()
            self.current_chart_canvas = None
        self.chart_placeholder.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self._update_status("New portfolio created")
        self._log_to_console("Created new portfolio", "INFO")

    def _clear_all_tickers_ui_only(self):
        """Helper to clear ticker rows without confirmation dialog."""
        for item in self.holdings_tree.get_children():
            self.holdings_tree.delete(item)
        self._update_total_weight()

    def _save_portfolio(self):
        """Save the current portfolio."""
        if not self.holdings_tree.get_children():
            messagebox.showwarning("Warning", "Portfolio is empty.")
            return

        # If no file assigned, use Save As
        if not self.current_file:
            self._save_portfolio_as()
            return

        try:
            holdings = self._get_holdings_from_ui()
            name = self.name_entry.get().strip() or "Portfolio"

            portfolio = Portfolio(holdings=holdings, name=name)
            portfolio.to_json(self.current_file)

            self.current_portfolio = portfolio
            self._update_status(f"Saved to {self.current_file.name}")
            self._log_to_console(f"Saved portfolio to {self.current_file.name}", "SUCCESS")
            self._load_portfolio_list()  # Refresh list

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save portfolio: {e}")
            self._log_to_console(f"Failed to save portfolio: {str(e)}", "ERROR")

    def _save_portfolio_as(self):
        """Save portfolio to a new file."""
        if not self.holdings_tree.get_children():
            messagebox.showwarning("Warning", "Portfolio is empty.")
            return

        initial_file = self.name_entry.get().strip().replace(" ", "_")
        if not initial_file:
            initial_file = "portfolio"

        file_path = filedialog.asksaveasfilename(
            initialdir=self.portfolios_dir,
            initialfile=f"{initial_file}.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not file_path:
            return

        self.current_file = Path(file_path)
        self._save_portfolio()

    def _load_portfolio(self):
        """Open file dialog to load a portfolio."""
        file_path = filedialog.askopenfilename(
            initialdir=self.portfolios_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not file_path:
            return

        self._load_portfolio_from_file(Path(file_path))

    def _load_selected_portfolio(self):
        """Load the portfolio selected in the listbox."""
        selection = self.portfolio_listbox.curselection()
        if not selection:
            return

        filename = self.portfolio_listbox.get(selection[0])
        file_path = self.portfolios_dir / filename

        self._load_portfolio_from_file(file_path)

    def _load_portfolio_from_file(self, file_path: Path):
        """Internal method to load portfolio data into UI."""
        try:
            portfolio = Portfolio.from_json(file_path)

            # Clear current UI
            self._clear_all_tickers_ui_only()
            self.name_entry.delete(0, tk.END)

            # Populate UI
            self.name_entry.insert(0, portfolio.name)

            for ticker, weight in portfolio.holdings.items():
                # Convert decimal weight back to percentage for UI
                pct_weight = weight * 100.0
                self.holdings_tree.insert("", tk.END, values=(ticker, f"{pct_weight:.2f}"))

            self._update_total_weight()
            self.current_portfolio = portfolio
            self.current_file = file_path
            self._update_status(f"Loaded {file_path.name}")
            self._log_to_console(f"Loaded portfolio from {file_path.name}", "SUCCESS")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load portfolio: {e}")
            self._log_to_console(f"Failed to load portfolio: {str(e)}", "ERROR")

    def _load_portfolio_list(self):
        """Refresh the list of portfolios in the left panel."""
        self.portfolio_listbox.delete(0, tk.END)

        if not self.portfolios_dir.exists():
            return

        try:
            files = sorted(self.portfolios_dir.glob("*.json"))
            for file in files:
                self.portfolio_listbox.insert(tk.END, file.name)
        except Exception as e:
            print(f"Error loading portfolio list: {e}")

    def _export_summary(self):
        """Export the analysis results to a text file."""
        # Check if the results text box is empty
        if self.results_text.compare("end-1c", "==", "1.0"):
            messagebox.showwarning("Warning", "No results to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            content = self.results_text.get(1.0, tk.END)

            # Specify UTF-8 encoding to handle characters like β and α
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self._update_status(f"Results exported to {Path(file_path).name}")
            self._log_to_console(f"Exported analysis results to {Path(file_path).name}", "SUCCESS")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export results: {e}")
            self._log_to_console(f"Failed to export results: {str(e)}", "ERROR")

    def _log_to_console(self, message: str, level: str = "INFO"):
        """
        Log a message to the console with timestamp and level.

        Parameters:
        -----------
        message : str
            The message to log
        level : str
            Log level: INFO, SUCCESS, WARNING, ERROR
        """
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")

        self.console_text.config(state=tk.NORMAL)

        # Add timestamp
        self.console_text.insert(tk.END, f"[{timestamp}] ", "TIMESTAMP")

        # Add level indicator
        level_indicators = {
            "INFO": "ℹ",
            "SUCCESS": "✓",
            "WARNING": "⚠",
            "ERROR": "✗"
        }
        indicator = level_indicators.get(level, "•")
        self.console_text.insert(tk.END, f"{indicator} ", level)

        # Add message
        self.console_text.insert(tk.END, f"{message}\n", level)

        self.console_text.config(state=tk.DISABLED)
        self.console_text.see(tk.END)  # Auto-scroll to bottom

    def _clear_console(self):
        """Clear the console log."""
        self.console_text.config(state=tk.NORMAL)
        self.console_text.delete(1.0, tk.END)
        self.console_text.config(state=tk.DISABLED)
        self._log_to_console("Console cleared", "INFO")

    def _update_status(self, message: str):
        """Update the status bar text."""
        self.status_bar.config(text=message)


def main():
    """Application entry point."""
    try:
        root = tk.Tk()
        # Set icon if available, otherwise skip
        # root.iconbitmap("icon.ico")
        app = PortfolioManagerUI(root)
        root.mainloop()
    except Exception as e:
        print(f"Application error: {e}")


if __name__ == "__main__":
    main()