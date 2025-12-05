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

## Financial Formulas

### 1. Realized Risk-Free Rate (SOFR)

Annualized risk-free rate from daily rates:

\[
r_{\text{annualized}} = \left( \prod_{i=1}^{n} \left( 1 + \frac{\text{SOFR}_i}{252} \right) \right)^{\frac{252}{n}} - 1
\]

where \( \text{SOFR}_i \) is the daily SOFR rate, and \( n \) is the number of days.

### 2. Daily Returns

\[
r_{i} = \frac{P_i - P_{i-1}}{P_{i-1}}
\]

where \( P_i \) is the price at day \( i \).

### 3. Annualized Volatility

\[
\sigma_{\text{annualized}} = \text{std}(r_i) \times \sqrt{252}
\]

### 4. Sharpe Ratio

\[
\text{Sharpe Ratio} = \frac{\bar{r}_p - r_f}{\sigma_p}
\]

where \( \bar{r}_p \) is the portfolio mean return, \( r_f \) is the risk-free rate, and \( \sigma_p \) is portfolio volatility.

### 5. CAPM Metrics

**Beta:**

\[
\beta = \frac{\text{Cov}(r_p, r_m)}{\text{Var}(r_m)}
\]

**Alpha:**

\[
\alpha = \bar{r}_p - \left( r_f + \beta (\bar{r}_m - r_f) \right)
\]

where \( r_m \) is the benchmark return.

### 6. Maximum Drawdown

\[
\text{Max Drawdown} = \max_{t \in [0, T]} \left( \frac{\text{Peak}_t - P_t}{\text{Peak}_t} \right)
\]

where \( \text{Peak}_t = \max_{s \le t} P_s \).

---

## Installation

### Prerequisites

* Python 3.8+
* The following Python packages:

```bash
pip install pandas numpy matplotlib
