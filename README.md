# Portfolio Builder / Analyzer

Portfolio Manager is a comprehensive Python-based desktop application for managing investment portfolios, analyzing performance metrics against market benchmarks, and visualizing risk-return profiles. Built with `tkinter` for the GUI and `pandas`/`matplotlib` data handling and analysis.
**NOTE:** This project is a work-in-progress. Its current state only contains a fraction of its intended functionality and is meant to visualize and demonstrate its foundation.

## Bugs / To Implement
- Manage edge cases related to short portfolio timeframes – frequency and annualization concerns.
- Deal with incomplete or missing data for tickers in the specified timeframe.
- Incorporate dividends – requires extensive metadata like historic ex-dividend, record dates, etc. Possibly start with flat or variable continuous accrual, although corporate action dates are required for precision, especially in more active strategies.
- Normalization often goes +/- a basis point or two; further rounding or actual $ value/share rounding needed in future for precision.
- SOFR data doesn't go back far enough.

BackTesterV1 is a comprehensive Python-based desktop application for managing investment portfolios, creating strategies, analyzing performance metrics against market benchmarks, and visualizing risk-return profiles. Built with `tkinter` for the GUI and `pandas`/`matplotlib` for data handling and analysis.

![Portfolio Manager Demo](media/demo5.png)
![Portfolio Manager Interface](media/demo1.png)

## Features

### 1. Portfolio Management
* **Create & Edit**: Easily create portfolios with custom weights.
* **Ticker Management**: Add, remove, or edit tickers. Support for manual weight entry or equal-weight distribution.
* **Normalization**: Auto-normalize weights to ensure they sum to 100%.
* **Persistence**: Save and load portfolios as JSON files.
* **CSV Support**: Import holdings from CSV or export current portfolio configurations.
- **Create & Edit**: Easily create portfolios with custom weights.
- **Ticker Management**: Add, remove, or edit tickers. Support for manual weight entry or equal-weight distribution.
- **Normalization**: Auto-normalize weights to ensure they sum to 100%.
- **Persistence**: Save and load portfolios as JSON files.
- **CSV Support**: Import holdings from CSV or export current portfolio configurations.

### 2. Portfolio Analysis
Run detailed simulations against benchmarks (e.g., SPY) to calculate key metrics:
* **Risk/Return**: Annualized Return, Volatility, Sharpe Ratio, Treynor Ratio.
* **CAPM Metrics**: Beta (β) and Alpha (α) relative to the market.
* **Drawdown**: Max Drawdown calculation and percentage from High Water Mark.
* **Statistics**: Daily return distribution (Skewness, Kurtosis, Percentiles).
- **Risk/Return**: Annualized Return, Volatility, Sharpe Ratio, Treynor Ratio.
- **CAPM Metrics**: Beta (β) and Alpha (α) relative to the market.
- **Drawdown**: Max Drawdown calculation and percentage from High Water Mark.
- **Statistics**: Daily return distribution (Skewness, Kurtosis, Percentiles).

### 3. Charting
Visualize your portfolio's performance with interactive, exportable charts:
* **Equity Curve**: Compare cumulative returns vs. benchmark.
- **Equity Curve**: Compare cumulative returns vs. benchmark.  
![Equity Curve](media/demo2.png)
* **Drawdown Chart**: Visualize underwater periods and depth.
- **Drawdown Chart**: Visualize underwater periods and depth.  
![Drawdown Analysis](media/demo3.png)
* **Monthly Heatmap**: Month-by-month return visualization.
- **Monthly Heatmap**: Month-by-month return visualization.  
![Monthly Heatmap](media/demo4.png)
* **Distribution**: Histogram of daily returns with mean/median markers.
- **Distribution**: Histogram of daily returns with mean/median markers.

## Installation

### Prerequisites
* Python 3.8+
* The following Python packages:
- Python 3.8+
- The following Python packages:
```bash
pip install pandas numpy matplotlib
