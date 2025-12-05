# Portfolio Builder / Analyzer

Portfolio Manager is a comprehensive Python-based desktop application for managing investment portfolios, analyzing performance metrics against market benchmarks, and visualizing risk-return profiles. Built with `tkinter` for the GUI and `pandas`/`matplotlib` data handling and analysis.

![Portfolio Manager Demo](media/demo5.png)
![Portfolio Manager Interface](media/demo1.png)

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
  ![Equity Curve](media/demo2.png)
* **Drawdown Chart**: Visualize underwater periods and depth.
  ![Drawdown Analysis](media/demo3.png)
* **Monthly Heatmap**: Month-by-month return visualization.
  ![Monthly Heatmap](media/demo4.png)
* **Distribution**: Histogram of daily returns with mean/median markers.

## Installation

### Prerequisites
* Python 3.8+
* The following Python packages:
```bash
pip install pandas numpy matplotlib

