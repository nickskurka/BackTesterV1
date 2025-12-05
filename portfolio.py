import json
import pandas as pd
import numpy as np
from typing import Dict, List, Union, Optional
from pathlib import Path
import warnings


class Portfolio:
    """
    A Portfolio class to manage multiple tickers with their respective weights.
    Can be used with the financial analysis functions from your existing module.
    """

    def __init__(self, holdings: Optional[Dict[str, float]] = None, name: str = "Portfolio"):
        """
        Initialize a Portfolio object.

        Parameters:
        -----------
        holdings : dict, optional
            Dictionary with ticker symbols as keys and weights as values.
            Example: {"AAPL": 0.3, "GOOGL": 0.5, "MSFT": 0.2}
        name : str, optional
            Name for the portfolio (default: "Portfolio")
        """
        self.name = name
        self.holdings = holdings if holdings is not None else {}
        self._validate_weights()

    def _validate_weights(self):
        """Validate that weights sum to approximately 1.0."""
        if not self.holdings:
            return

        total = sum(self.holdings.values())
        if not np.isclose(total, 1.0, atol=0.01):
            warnings.warn(
                f"Portfolio weights sum to {total:.4f}, not 1.0. "
                f"Consider normalizing with normalize_weights()."
            )

    def add_ticker(self, ticker: str, weight: float):
        """
        Add a ticker to the portfolio with a specified weight.

        Parameters:
        -----------
        ticker : str
            Ticker symbol
        weight : float
            Weight/allocation for this ticker
        """
        self.holdings[ticker.upper()] = weight
        self._validate_weights()

    def remove_ticker(self, ticker: str):
        """Remove a ticker from the portfolio."""
        ticker_upper = ticker.upper()
        if ticker_upper in self.holdings:
            del self.holdings[ticker_upper]
        else:
            warnings.warn(f"Ticker {ticker_upper} not found in portfolio.")

    def update_weight(self, ticker: str, new_weight: float):
        """Update the weight of an existing ticker."""
        ticker_upper = ticker.upper()
        if ticker_upper in self.holdings:
            self.holdings[ticker_upper] = new_weight
            self._validate_weights()
        else:
            raise ValueError(f"Ticker {ticker_upper} not found in portfolio.")

    def normalize_weights(self):
        """Normalize weights to sum to 1.0."""
        if not self.holdings:
            return

        total = sum(self.holdings.values())
        if total == 0:
            raise ValueError("Cannot normalize: total weight is zero.")

        self.holdings = {ticker: weight / total for ticker, weight in self.holdings.items()}

    def get_tickers(self) -> List[str]:
        """Return list of tickers in the portfolio."""
        return list(self.holdings.keys())

    def get_weights(self) -> List[float]:
        """Return list of weights corresponding to tickers."""
        return list(self.holdings.values())

    def get_holdings_df(self) -> pd.DataFrame:
        """Return holdings as a DataFrame."""
        return pd.DataFrame.from_dict(
            self.holdings,
            orient="index",
            columns=["Weight"]
        ).sort_values("Weight", ascending=False)

    def to_dict(self) -> Dict:
        """Export portfolio to dictionary format."""
        return {
            "name": self.name,
            "holdings": self.holdings
        }

    def to_json(self, filepath: Union[str, Path]):
        """
        Save portfolio to a JSON file.

        Parameters:
        -----------
        filepath : str or Path
            Path where the JSON file will be saved
        """
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)
        print(f"Portfolio saved to {filepath}")

    @classmethod
    def from_dict(cls, data: Dict) -> 'Portfolio':
        """
        Create a Portfolio object from a dictionary.

        Parameters:
        -----------
        data : dict
            Dictionary containing 'name' and 'holdings' keys

        Returns:
        --------
        Portfolio object
        """
        return cls(
            holdings=data.get("holdings", {}),
            name=data.get("name", "Portfolio")
        )

    @classmethod
    def from_json(cls, filepath: Union[str, Path]) -> 'Portfolio':
        """
        Load a Portfolio object from a JSON file.

        Parameters:
        -----------
        filepath : str or Path
            Path to the JSON file

        Returns:
        --------
        Portfolio object
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def portfolio_return(self, returns_df: pd.DataFrame) -> pd.Series:
        """
        Calculate weighted portfolio returns given individual ticker returns.

        Parameters:
        -----------
        returns_df : pd.DataFrame
            DataFrame with tickers as index and returns as a column
            (e.g., output from annualized_cumulative_return)

        Returns:
        --------
        pd.Series with portfolio return
        """
        portfolio_return = 0.0
        for ticker, weight in self.holdings.items():
            if ticker in returns_df.index:
                portfolio_return += weight * returns_df.loc[ticker].iloc[0]
            else:
                warnings.warn(f"Ticker {ticker} not found in returns DataFrame.")

        return pd.Series({"PortfolioReturn": portfolio_return})

    def portfolio_volatility(self, returns_series: Dict[str, pd.Series],
                             correlation_matrix: pd.DataFrame,
                             annualize: bool = True,
                             periods_per_year: int = 252) -> float:
        """
        Calculate portfolio volatility using weights, individual volatilities, and correlation matrix.

        Portfolio Variance = Σᵢ Σⱼ wᵢ wⱼ σᵢ σⱼ ρᵢⱼ
        Portfolio Volatility = √(Portfolio Variance)

        Parameters:
        -----------
        returns_series : dict
            Dictionary mapping tickers to their return series
        correlation_matrix : pd.DataFrame
            Correlation matrix between tickers
        annualize : bool, optional
            Whether to annualize the volatility (default: True)
        periods_per_year : int, optional
            Number of periods per year for annualization (default: 252 for daily)

        Returns:
        --------
        float : Portfolio volatility (annualized if annualize=True)
        """
        # Calculate individual volatilities (period volatility, not annualized)
        volatilities = {ticker: returns.std() for ticker, returns in returns_series.items()}

        # Calculate portfolio variance
        portfolio_variance = 0.0
        for ticker_i, weight_i in self.holdings.items():
            for ticker_j, weight_j in self.holdings.items():
                if ticker_i in volatilities and ticker_j in volatilities:
                    vol_i = volatilities[ticker_i]
                    vol_j = volatilities[ticker_j]
                    corr_ij = correlation_matrix.loc[ticker_i, ticker_j]
                    portfolio_variance += weight_i * weight_j * vol_i * vol_j * corr_ij

        # Portfolio standard deviation (period level)
        portfolio_std = np.sqrt(portfolio_variance)

        # Annualize if requested
        if annualize:
            portfolio_std *= np.sqrt(periods_per_year)

        return portfolio_std

    def portfolio_beta(self, beta_df: pd.DataFrame, beta_column: Optional[str] = None) -> float:
        """
        Calculate portfolio beta as the weighted average of individual stock betas.

        Portfolio Beta = Σᵢ wᵢ βᵢ

        Parameters:
        -----------
        beta_df : pd.DataFrame
            DataFrame with tickers as index and beta values
            (e.g., output from beta_single_stock for each ticker)
        beta_column : str, optional
            Name of the column containing beta values. If None, uses first column.

        Returns:
        --------
        float : Portfolio beta
        """
        if beta_column is None:
            beta_column = beta_df.columns[0]

        portfolio_beta_value = 0.0
        for ticker, weight in self.holdings.items():
            if ticker in beta_df.index:
                portfolio_beta_value += weight * beta_df.loc[ticker, beta_column]
            else:
                warnings.warn(f"Ticker {ticker} not found in beta DataFrame.")

        return portfolio_beta_value

    def portfolio_alpha(self, alpha_df: pd.DataFrame, alpha_column: Optional[str] = None) -> float:
        """
        Calculate portfolio alpha as the weighted average of individual stock alphas.

        Portfolio Alpha = Σᵢ wᵢ αᵢ

        Parameters:
        -----------
        alpha_df : pd.DataFrame
            DataFrame with tickers as index and alpha values
            (e.g., output from alpha_single_stock for each ticker)
        alpha_column : str, optional
            Name of the column containing alpha values. If None, uses first column.

        Returns:
        --------
        float : Portfolio alpha
        """
        if alpha_column is None:
            alpha_column = alpha_df.columns[0]

        portfolio_alpha_value = 0.0
        for ticker, weight in self.holdings.items():
            if ticker in alpha_df.index:
                portfolio_alpha_value += weight * alpha_df.loc[ticker, alpha_column]
            else:
                warnings.warn(f"Ticker {ticker} not found in alpha DataFrame.")

        return portfolio_alpha_value

    def portfolio_sharpe_ratio(self, sharpe_df: pd.DataFrame, sharpe_column: Optional[str] = None) -> float:
        """
        Calculate portfolio Sharpe ratio as the weighted average of individual Sharpe ratios.

        Note: This is an approximation. The true portfolio Sharpe ratio should be calculated as:
        (Portfolio Return - Risk Free Rate) / Portfolio Volatility

        Parameters:
        -----------
        sharpe_df : pd.DataFrame
            DataFrame with tickers as index and Sharpe ratio values
            (e.g., output from annualized_sharpe_ratio for each ticker)
        sharpe_column : str, optional
            Name of the column containing Sharpe values. If None, uses first column.

        Returns:
        --------
        float : Weighted average Sharpe ratio
        """
        if sharpe_column is None:
            sharpe_column = sharpe_df.columns[0]

        portfolio_sharpe_value = 0.0
        for ticker, weight in self.holdings.items():
            if ticker in sharpe_df.index:
                portfolio_sharpe_value += weight * sharpe_df.loc[ticker, sharpe_column]
            else:
                warnings.warn(f"Ticker {ticker} not found in Sharpe DataFrame.")

        return portfolio_sharpe_value

    def portfolio_sharpe_ratio_true(self, portfolio_return: float, risk_free_rate: float,
                                    portfolio_volatility: float) -> float:
        """
        Calculate the true portfolio Sharpe ratio.

        Sharpe Ratio = (Portfolio Return - Risk Free Rate) / Portfolio Volatility

        Parameters:
        -----------
        portfolio_return : float
            Annualized portfolio return
        risk_free_rate : float
            Annualized risk-free rate (e.g., from SOFR)
        portfolio_volatility : float
            Portfolio volatility (standard deviation)

        Returns:
        --------
        float : Portfolio Sharpe ratio
        """
        if portfolio_volatility == 0:
            if portfolio_return - risk_free_rate > 0:
                return float('inf')
            else:
                warnings.warn("Portfolio volatility is zero. Sharpe ratio set to 0.")
                return 0.0

        return (portfolio_return - risk_free_rate) / portfolio_volatility

    def portfolio_treynor_ratio(self, portfolio_return: float, risk_free_rate: float,
                                portfolio_beta: float) -> float:
        """
        Calculate the portfolio Treynor ratio.

        Treynor Ratio = (Portfolio Return - Risk Free Rate) / Portfolio Beta

        Parameters:
        -----------
        portfolio_return : float
            Annualized portfolio return
        risk_free_rate : float
            Annualized risk-free rate (e.g., from SOFR)
        portfolio_beta : float
            Portfolio beta

        Returns:
        --------
        float : Portfolio Treynor ratio
        """
        if portfolio_beta == 0:
            if portfolio_return - risk_free_rate > 0:
                return float('inf')
            else:
                warnings.warn("Portfolio beta is zero. Treynor ratio set to 0.")
                return 0.0

        return (portfolio_return - risk_free_rate) / portfolio_beta

    def __repr__(self):
        holdings_str = "\n".join([f"  {ticker}: {weight:.4f}" for ticker, weight in self.holdings.items()])
        return f"Portfolio: {self.name}\nHoldings:\n{holdings_str}\nTotal Weight: {sum(self.holdings.values()):.4f}"

    def __str__(self):
        return self.__repr__()


# Example usage and helper functions
def create_example_portfolio():
    """Create an example portfolio for demonstration."""
    portfolio = Portfolio(
        holdings={
            "AAPL": 0.30,
            "GOOGL": 0.25,
            "MSFT": 0.20,
            "AMZN": 0.15,
            "TSLA": 0.10
        },
        name="Tech Portfolio"
    )
    return portfolio


def equal_weight_portfolio(tickers: List[str], name: str = "Equal Weight Portfolio") -> Portfolio:
    """
    Create an equal-weight portfolio from a list of tickers.

    Parameters:
    -----------
    tickers : list
        List of ticker symbols
    name : str, optional
        Name for the portfolio

    Returns:
    --------
    Portfolio object with equal weights
    """
    n = len(tickers)
    if n == 0:
        raise ValueError("Ticker list cannot be empty.")

    weight = 1.0 / n
    holdings = {ticker.upper(): weight for ticker in tickers}
    return Portfolio(holdings=holdings, name=name)


if __name__ == "__main__":
    # Example 1: Create portfolio manually
    print("=== Example 1: Manual Creation ===")
    portfolio1 = Portfolio(name="My Tech Portfolio")
    portfolio1.add_ticker("AAPL", 0.4)
    portfolio1.add_ticker("GOOGL", 0.35)
    portfolio1.add_ticker("MSFT", 0.25)
    print(portfolio1)
    print()

    # Example 2: Create equal-weight portfolio
    print("=== Example 2: Equal Weight Portfolio ===")
    portfolio2 = equal_weight_portfolio(["AAPL", "GOOGL", "MSFT", "AMZN", "NVDA"])
    print(portfolio2)
    print()

    # Example 3: Save and load from JSON
    print("=== Example 3: Save/Load JSON ===")
    portfolio1.to_json("my_portfolio.json")
    loaded_portfolio = Portfolio.from_json("my_portfolio.json")
    print("Loaded Portfolio:")
    print(loaded_portfolio)
    print()

    # Example 4: Get holdings as DataFrame
    print("=== Example 4: Holdings DataFrame ===")
    print(loaded_portfolio.get_holdings_df())