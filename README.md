# Portfolio Builder / Analyzer

Portfolio Manager is a comprehensive Python-based desktop application for managing investment portfolios, analyzing performance metrics against market benchmarks, and visualizing risk-return profiles. Built with `tkinter` for the GUI and `pandas`/`matplotlib` data handling and analysis.

![Portfolio Manager Demo](media/demo5.jpg)
![Portfolio Manager Interface](media/demo1.jpg)

## Features

### 1. Portfolio Management

* **Create & Edit**: Easily create portfolios with custom weights.
* **Ticker Management**: Add, remove, or edit tickers. Support for manual weight entry or equal-weight distribution.
* **Normalization**: Auto-normalize weights to ensure they sum to 100%.
* **Persistence**: Save and load portfolios as JSON files.
* **CSV Support**: Import holdings from CSV or export current portfolio configurations.

### 2. Portfolio Analysis

Run detailed simulations against benchmarks (e.g., SPY) to calculate key metrics:

* **Risk/Return**: Annualized Return, Volatility, Sharpe Ratio, Treynor Ratio.
* **CAPM Metrics**: Beta (β) and Alpha (α) relative to the market.
* **Drawdown**: Max Drawdown calculation and percentage from High Water Mark.
* **Statistics**: Daily return distribution (Skewness, Kurtosis, Percentiles).

### 3. Charting

Visualize your portfolio's performance with interactive, exportable charts:

* **Equity Curve**: Compare cumulative returns vs. benchmark.

![Equity Curve](media/demo2.jpg)

* **Drawdown Chart**: Visualize underwater periods and depth.

![Drawdown Analysis](media/demo3.jpg)

* **Monthly Heatmap**: Month-by-month return visualization.

![Monthly Heatmap](media/demo4.jpg)

* **Distribution**: Histogram of daily returns with mean/median markers.

## Installation

### Prerequisites

* Python 3.8+
* The following Python packages:

```bash
pip install pandas numpy matplotlib
```

(Note: `tkinter` is included with standard Python installations)

### Project Structure

* `ui.py`: The main entry point launching the Graphical User Interface.
* `portfolio.py`: Core class defining the Portfolio object and math for weighted metrics.
* `charting.py`: Matplotlib integration for generating financial charts within the UI.
* `utils.py`: Helper functions for data fetching (CSV/SQLite), date parsing, and financial formulas.

## Data Setup

The application requires historical price data to function.

1. **Market Data**: Place CSV files for tickers (e.g., `AAPL.csv`, `SPY.csv`) in `data/timeseries/`. Files must contain `Date` and `Close` columns.
2. **Risk-Free Rate**: Ensure `data/SOFR.csv` exists for accurate risk-free rate calculations.

## Usage

1. **Start the Application**:

   ```bash
   python ui.py
   ```

2. **Build a Portfolio**:
   * Click **New** to start fresh.
   * Click **Add Ticker** to manually input symbols (e.g., AAPL) and weights.
   * Alternatively, import a CSV file with `Ticker` and `Weight` columns.

3. **Run Analysis**:
   * Switch to the **Metrics & Analysis** tab.
   * Select Start/End dates and the Benchmark ticker (e.g., SPY).
   * Click **Run Analysis**.

4. **Visualize**::w
   * Go to the **Charting** sub-tab.
   * Select a chart type (e.g., "Equity Curve") and click **Generate Chart**.

## License

MIT#   B a c k T e s t e r V 1 
 
 
