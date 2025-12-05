"""
Charting module for portfolio visualization.
Provides modular charting functions that can be extended in the future.
"""

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class PortfolioChartManager:
    """
    Manages chart creation and display for portfolio analysis.
    Designed to be modular and extensible for future chart types.
    """

    def __init__(self, dpi: int = 100):
        """
        Initialize the chart manager.

        Parameters:
        -----------
        dpi : int
            Dots per inch for figure resolution
        """
        self.dpi = dpi
        self.default_colors = {
            'portfolio': '#2E86AB',
            'benchmark': '#A23B72',
            'positive': '#06A77D',
            'negative': '#D62246',
            'neutral': '#6C757D'
        }

    def create_equity_curve(self,
                            portfolio_data: pd.Series,
                            benchmark_data: pd.Series,
                            portfolio_name: str = "Portfolio",
                            benchmark_name: str = "Benchmark",
                            initial_value: float = 1000.0,
                            figsize: Tuple[int, int] = (12, 6)) -> Figure:
        """
        Create an equity curve chart comparing portfolio vs benchmark.

        Parameters:
        -----------
        portfolio_data : pd.Series
            Daily returns series for the portfolio (indexed by date)
        benchmark_data : pd.Series
            Daily returns series for the benchmark (indexed by date)
        portfolio_name : str
            Name of the portfolio for legend
        benchmark_name : str
            Name of the benchmark for legend
        initial_value : float
            Starting portfolio value (default: $1000)
        figsize : tuple
            Figure size (width, height)

        Returns:
        --------
        Figure : matplotlib Figure object
        """
        fig = Figure(figsize=figsize, dpi=self.dpi)
        ax = fig.add_subplot(111)

        # Calculate cumulative values starting at initial_value
        portfolio_equity = initial_value * (1 + portfolio_data).cumprod()
        benchmark_equity = initial_value * (1 + benchmark_data).cumprod()

        # Plot equity curves
        ax.plot(portfolio_equity.index, portfolio_equity.values,
                label=portfolio_name,
                color=self.default_colors['portfolio'],
                linewidth=2)

        ax.plot(benchmark_equity.index, benchmark_equity.values,
                label=benchmark_name,
                color=self.default_colors['benchmark'],
                linewidth=2,
                linestyle='--')

        # Formatting
        ax.set_title('Portfolio Performance vs Benchmark',
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=11)
        ax.set_ylabel('Value ($)', fontsize=11)
        ax.legend(loc='best', fontsize=10, framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')

        # Format y-axis as currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        # Add performance stats box
        final_portfolio = portfolio_equity.iloc[-1]
        final_benchmark = benchmark_equity.iloc[-1]
        portfolio_return = (final_portfolio / initial_value - 1) * 100
        benchmark_return = (final_benchmark / initial_value - 1) * 100
        outperformance = portfolio_return - benchmark_return

        stats_text = (f'Total Return:\n'
                      f'{portfolio_name}: {portfolio_return:+.2f}%\n'
                      f'{benchmark_name}: {benchmark_return:+.2f}%\n'
                      f'Outperformance: {outperformance:+.2f}%')

        ax.text(0.02, 0.98, stats_text,
                transform=ax.transAxes,
                fontsize=9,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        fig.tight_layout()
        return fig

    def create_drawdown_chart(self,
                              portfolio_data: pd.Series,
                              benchmark_data: Optional[pd.Series] = None,
                              portfolio_name: str = "Portfolio",
                              benchmark_name: str = "Benchmark",
                              figsize: Tuple[int, int] = (12, 5)) -> Figure:
        """
        Create a drawdown chart showing portfolio (and optionally benchmark) drawdowns.

        Parameters:
        -----------
        portfolio_data : pd.Series
            Daily returns series for the portfolio
        benchmark_data : pd.Series, optional
            Daily returns series for the benchmark
        portfolio_name : str
            Name of the portfolio
        benchmark_name : str
            Name of the benchmark
        figsize : tuple
            Figure size

        Returns:
        --------
        Figure : matplotlib Figure object
        """
        fig = Figure(figsize=figsize, dpi=self.dpi)
        ax = fig.add_subplot(111)

        # Calculate portfolio drawdown
        portfolio_cum = (1 + portfolio_data).cumprod()
        portfolio_running_max = portfolio_cum.cummax()
        portfolio_drawdown = (portfolio_cum - portfolio_running_max) / portfolio_running_max

        # Plot portfolio drawdown
        ax.fill_between(portfolio_drawdown.index,
                        portfolio_drawdown.values * 100,
                        0,
                        color=self.default_colors['negative'],
                        alpha=0.3,
                        label=portfolio_name)

        ax.plot(portfolio_drawdown.index,
                portfolio_drawdown.values * 100,
                color=self.default_colors['negative'],
                linewidth=1.5)

        # If benchmark provided, calculate and plot its drawdown
        if benchmark_data is not None:
            benchmark_cum = (1 + benchmark_data).cumprod()
            benchmark_running_max = benchmark_cum.cummax()
            benchmark_drawdown = (benchmark_cum - benchmark_running_max) / benchmark_running_max

            ax.plot(benchmark_drawdown.index,
                    benchmark_drawdown.values * 100,
                    color=self.default_colors['benchmark'],
                    linewidth=1.5,
                    linestyle='--',
                    label=benchmark_name)

        # Formatting
        ax.set_title('Drawdown Analysis', fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=11)
        ax.set_ylabel('Drawdown (%)', fontsize=11)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

        fig.tight_layout()
        return fig

    def create_monthly_returns_heatmap(self,
                                       returns_data: pd.Series,
                                       title: str = "Monthly Returns Heatmap",
                                       figsize: Tuple[int, int] = (12, 6)) -> Figure:
        """
        Create a heatmap of monthly returns.

        Parameters:
        -----------
        returns_data : pd.Series
            Daily returns series
        title : str
            Chart title
        figsize : tuple
            Figure size

        Returns:
        --------
        Figure : matplotlib Figure object
        """
        fig = Figure(figsize=figsize, dpi=self.dpi)
        ax = fig.add_subplot(111)

        # Resample to monthly returns
        monthly_returns = (1 + returns_data).resample('ME').prod() - 1

        # Pivot into year x month format
        monthly_returns_df = pd.DataFrame({
            'Year': monthly_returns.index.year,
            'Month': monthly_returns.index.month,
            'Return': monthly_returns.values * 100
        })

        pivot_table = monthly_returns_df.pivot(index='Year', columns='Month', values='Return')

        # Create heatmap
        im = ax.imshow(pivot_table.values, cmap='RdYlGn', aspect='auto', vmin=-10, vmax=10)

        # Set ticks and labels
        ax.set_xticks(np.arange(len(pivot_table.columns)))
        ax.set_yticks(np.arange(len(pivot_table.index)))
        ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
        ax.set_yticklabels(pivot_table.index.astype(int))

        # Add colorbar
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label('Return (%)', rotation=270, labelpad=15)

        # Add text annotations
        for i in range(len(pivot_table.index)):
            for j in range(len(pivot_table.columns)):
                value = pivot_table.values[i, j]
                if not np.isnan(value):
                    text_color = 'white' if abs(value) > 5 else 'black'
                    ax.text(j, i, f'{value:.1f}%',
                            ha="center", va="center", color=text_color, fontsize=8)

        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Month', fontsize=11)
        ax.set_ylabel('Year', fontsize=11)

        fig.tight_layout()
        return fig

    def create_returns_distribution(self,
                                    returns_data: pd.Series,
                                    title: str = "Daily Returns Distribution",
                                    figsize: Tuple[int, int] = (10, 6)) -> Figure:
        """
        Create a histogram of returns distribution.

        Parameters:
        -----------
        returns_data : pd.Series
            Daily returns series
        title : str
            Chart title
        figsize : tuple
            Figure size

        Returns:
        --------
        Figure : matplotlib Figure object
        """
        fig = Figure(figsize=figsize, dpi=self.dpi)
        ax = fig.add_subplot(111)

        returns_pct = returns_data * 100

        # Create histogram
        n, bins, patches = ax.hist(returns_pct, bins=50, alpha=0.7,
                                   color=self.default_colors['portfolio'],
                                   edgecolor='black', linewidth=0.5)

        # Color bars based on positive/negative
        for i, patch in enumerate(patches):
            if bins[i] < 0:
                patch.set_facecolor(self.default_colors['negative'])
            else:
                patch.set_facecolor(self.default_colors['positive'])

        # Add vertical line at mean
        mean_return = returns_pct.mean()
        ax.axvline(mean_return, color='darkblue', linestyle='--', linewidth=2,
                   label=f'Mean: {mean_return:.3f}%')

        # Add vertical line at median
        median_return = returns_pct.median()
        ax.axvline(median_return, color='purple', linestyle=':', linewidth=2,
                   label=f'Median: {median_return:.3f}%')

        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Daily Return (%)', fontsize=11)
        ax.set_ylabel('Frequency', fontsize=11)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--', axis='y')

        fig.tight_layout()
        return fig

    def embed_figure_in_tk(self, figure: Figure, parent_frame) -> FigureCanvasTkAgg:
        """
        Embed a matplotlib figure in a tkinter frame.

        Parameters:
        -----------
        figure : Figure
            Matplotlib Figure object to embed
        parent_frame : tk.Frame
            Parent tkinter frame

        Returns:
        --------
        FigureCanvasTkAgg : Canvas widget containing the figure
        """
        canvas = FigureCanvasTkAgg(figure, master=parent_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        return canvas


def calculate_portfolio_daily_returns(holdings: Dict[str, float],
                                      returns_series: Dict[str, pd.Series]) -> pd.Series:
    """
    Calculate weighted portfolio daily returns from individual ticker returns.

    Parameters:
    -----------
    holdings : dict
        Dictionary of ticker: weight pairs (weights as decimals, not percentages)
    returns_series : dict
        Dictionary of ticker: returns_series pairs

    Returns:
    --------
    pd.Series : Portfolio daily returns
    """
    # Align all returns series
    aligned_returns = pd.DataFrame(returns_series).dropna()

    # Calculate weighted returns
    portfolio_returns = pd.Series(0.0, index=aligned_returns.index)
    for ticker, weight in holdings.items():
        if ticker in aligned_returns.columns:
            portfolio_returns += aligned_returns[ticker] * weight

    return portfolio_returns