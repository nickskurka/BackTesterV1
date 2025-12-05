import sqlite3
import pandas as pd
import os
import warnings
import matplotlib.pyplot as plt
from math import sqrt
from typing import List, Union, Optional
from contextlib import contextmanager
from functools import wraps
from portfolio import Portfolio

# Suppress FutureWarnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- Configuration ---
# Default to timeseries, but can be changed by main.py
DATA_DIR = os.path.join("data", "timeseries")


def set_data_dir(path: str):
    """Set the directory where CSV data is stored."""
    global DATA_DIR
    DATA_DIR = path


def get_data_dir() -> str:
    """Get the current data directory."""
    return DATA_DIR


# --- Constants ---

FREQ_TO_PERIODS = {
    "daily": 252, "1d": 252,
    "weekly": 52, "1w": 52,
    "monthly": 12, "1m": 12,
    "quarterly": 4, "1q": 4
}

FREQ_TO_RESAMPLE = {
    "weekly": "W", "1w": "W",
    "monthly": "ME", "1m": "ME"
}

DEFAULT_MARKET_TICKER = "SPY"
DEFAULT_SOFR_PATH = "data/SOFR.csv"


# --- Context Managers ---

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    db_path = os.path.join(os.path.dirname(__file__), "timeseries.db")
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


# --- Decorators ---

def validate_dates(func):
    """Decorator to validate date inputs."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract start_date and end_date from args or kwargs
        sig_params = ['tickers', 'ticker', 'ticker1', 'ticker2', 'start_date', 'end_date']

        # Find positions
        start_idx = None
        end_idx = None
        for i, param in enumerate(sig_params):
            if param == 'start_date':
                start_idx = i
            elif param == 'end_date':
                end_idx = i

        # Get values
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')

        if start_date is None and len(args) > 1:
            start_date = args[1] if func.__name__ != 'correlation' else args[2]
        if end_date is None and len(args) > 2:
            end_date = args[2] if func.__name__ != 'correlation' else args[3]

        start = parse_date(start_date)
        end = parse_date(end_date)

        if pd.isna(start) or pd.isna(end):
            raise ValueError("Invalid date format. Supply 'yyyy-mm-dd' or similar.")
        if start > end:
            raise ValueError("start_date must be before end_date")

        return func(*args, **kwargs)

    return wrapper


# --- Helper Functions ---

def parse_date(date_str: str) -> pd.Timestamp:
    """Parses a date string into a normalized pandas Timestamp."""
    result = pd.to_datetime(date_str, errors="coerce")
    if pd.isna(result):
        return result
    return result.normalize()


def _get_periods_per_year(frequency: str) -> int:
    """Helper to determine the number of periods per year for annualization."""
    periods = FREQ_TO_PERIODS.get(frequency.lower())
    if periods is None:
        raise ValueError(f"Unknown frequency: {frequency}. Must be one of {list(FREQ_TO_PERIODS.keys())}")
    return periods


# --- Database and CSV Access ---

def _fetch_from_db(conn: sqlite3.Connection, ticker: str, start: pd.Timestamp,
                   end: pd.Timestamp, columns: List[str]) -> pd.DataFrame:
    """Fetches data from the database."""
    column_str = ", ".join(columns)
    query = f"""
        SELECT Date, {column_str}
        FROM timeseries
        WHERE Ticker = ?
        AND Date >= ?
        AND Date <= ?
        ORDER BY Date ASC
    """
    return pd.read_sql(
        query,
        conn,
        params=[ticker.upper(), start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')],
        parse_dates=["Date"]
    )


def _fetch_from_csv(ticker: str, start: pd.Timestamp, end: pd.Timestamp,
                    columns: List[str]) -> pd.DataFrame:
    """Fetches data from a CSV file."""
    # Use the configurable DATA_DIR instead of hardcoded path
    path = os.path.join(DATA_DIR, f"{ticker.upper()}.csv")

    if not os.path.exists(path):
        raise ValueError(f"CSV for ticker {ticker} not found at {path}")

    df = pd.read_csv(path, parse_dates=["Date"])
    df = df[(df["Date"] >= start) & (df["Date"] <= end)]

    # Select requested columns plus Date
    available_cols = ["Date"] + [col for col in columns if col in df.columns]
    return df[available_cols].copy()


def get_prices_db(conn: sqlite3.Connection, ticker: str, start: pd.Timestamp,
                  end: pd.Timestamp) -> pd.DataFrame:
    """Fetches stock prices from the database."""
    return _fetch_from_db(conn, ticker, start, end, ["Close"])


def get_prices_csv(ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Fetches stock prices from a CSV file."""
    return _fetch_from_csv(ticker, start, end, ["Close"])


def get_returns_db(conn: sqlite3.Connection, ticker: str, start: pd.Timestamp,
                   end: pd.Timestamp) -> pd.DataFrame:
    """Fetches stock returns from the database."""
    return _fetch_from_db(conn, ticker, start, end, ["return_1d"])


def get_returns_csv(ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Fetches stock returns from a CSV file."""
    return _fetch_from_csv(ticker, start, end, ["return_1d"])


# --- Data Processing ---

def resample_frequency(df: pd.DataFrame, freq: str, column: str = "return_1d") -> pd.DataFrame:
    """Resamples a DataFrame to a specified frequency."""
    if freq.lower() in ["daily", "1d"]:
        return df

    rule = FREQ_TO_RESAMPLE.get(freq.lower())
    if rule is None:
        raise ValueError(f"Frequency must be one of {list(FREQ_TO_RESAMPLE.keys()) + ['daily', '1d']}")

    df = df.set_index("Date").sort_index()

    # Handle returns: compound them
    if column == "return_1d" and column in df.columns:
        resampled = (1 + df["return_1d"]).resample(rule).prod() - 1
        return resampled.to_frame(name="return_1d").dropna().reset_index()

    # Handle prices: take the last price in each period
    if "Close" in df.columns:
        return df.resample(rule).last().dropna().reset_index()

    # Fallback for other data
    try:
        resampled = (1 + df.iloc[:, 0]).resample(rule).prod() - 1
        return resampled.to_frame(name=df.columns[0]).dropna().reset_index()
    except Exception:
        return df.reset_index()


def _fetch_returns(ticker: str, start: pd.Timestamp, end: pd.Timestamp,
                   frequency: str, use_csv: bool) -> pd.Series:
    """
    Internal helper to fetch, check, and resample returns for a single ticker.
    Returns a clean pandas Series of returns.
    """
    # Fetch data
    if use_csv:
        df = get_returns_csv(ticker, start, end)
    else:
        with get_db_connection() as conn:
            df = get_returns_db(conn, ticker, start, end)

    if df.empty:
        raise ValueError(f"No data found for ticker {ticker.upper()} in date range.")

    # Resample if needed
    df = resample_frequency(df, frequency)

    # Use 'return_1d' for consistency
    if 'return_1d' not in df.columns:
        raise KeyError(f"Returns DataFrame for {ticker.upper()} is missing 'return_1d' column after fetch/resample.")

    returns = df.set_index("Date")["return_1d"].dropna()

    if returns.empty:
        raise ValueError(f"No valid returns for ticker {ticker.upper()} in date range.")

    # Check for constant returns
    if returns.std() == 0 and returns.mean() == 0 and len(returns) > 1:
        warnings.warn(f"Returns for {ticker.upper()} are all zero; volatility is 0.")

    return returns


def _load_sofr_data(csv_path: str) -> pd.DataFrame:
    """Load and clean SOFR data from CSV."""
    df = pd.read_csv(csv_path)
    df["Date"] = pd.to_datetime(df["Date"], format='%m/%d/%Y', errors='coerce').dt.normalize()
    df["Rate"] = pd.to_numeric(df["Rate (%)"].astype(str).str.replace('%', ''), errors="coerce") / 100.0
    return df[["Date", "Rate"]].dropna(subset=["Rate", "Date"])


# --- Financial Analysis Methods ---

@validate_dates
def annualized_cumulative_return(tickers: Union[str, List[str]], start_date: str, end_date: str,
                                 frequency: str = "daily", use_csv: bool = False) -> pd.DataFrame:
    """
    Compute the annualized cumulative return for a list of tickers over a specified period.
    """
    if isinstance(tickers, str):
        tickers = [tickers]

    start = parse_date(start_date)
    end = parse_date(end_date)

    returns_dict = {}

    for ticker in tickers:
        returns = _fetch_returns(ticker, start, end, frequency, use_csv)

        # Compute cumulative return over period
        cumulative = (1 + returns).prod() - 1

        # Annualize the cumulative return
        n_periods = len(returns)
        periods_per_year = _get_periods_per_year(frequency)
        years = n_periods / periods_per_year

        if years == 0:
            raise ValueError(f"Years elapsed is zero for ticker {ticker}.")

        annualized = (1 + cumulative) ** (1 / years) - 1
        returns_dict[ticker.upper()] = annualized

    return pd.DataFrame.from_dict(returns_dict, orient="index", columns=["AnnualizedReturn"])


@validate_dates
def annualized_volatility(tickers: Union[str, List[str]], start_date: str, end_date: str,
                          frequency: str = "daily", use_csv: bool = False) -> pd.DataFrame:
    """Compute annualized volatility for a list of tickers over a specified period."""
    if isinstance(tickers, str):
        tickers = [tickers]

    start = parse_date(start_date)
    end = parse_date(end_date)

    vol_dict = {}

    for ticker in tickers:
        returns = _fetch_returns(ticker, start, end, frequency, use_csv)
        stdev = returns.std()
        periods_per_year = _get_periods_per_year(frequency)
        annualized = stdev * sqrt(periods_per_year)
        vol_dict[ticker.upper()] = annualized

    return pd.DataFrame.from_dict(vol_dict, orient="index", columns=["AnnualizedVolatility"])


def annualized_sofr(start_date: str, end_date: str, frequency: str = "daily",
                    csv_path: str = DEFAULT_SOFR_PATH) -> float:
    """Calculate the annualized realized SOFR rate over a specified date range and frequency."""
    df = _load_sofr_data(csv_path)

    if df.empty:
        raise ValueError("No valid numeric SOFR data in CSV file.")

    # Filter date range
    start = pd.to_datetime(start_date).normalize()
    end = pd.to_datetime(end_date).normalize()
    mask = (df["Date"] >= start) & (df["Date"] <= end)
    df = df.loc[mask].copy()

    if df.empty:
        raise ValueError(f"No SOFR data found in the specified date range: {start_date} to {end_date}")

    # Set index for resampling
    df.set_index("Date", inplace=True)

    # Resample logic
    freq_map = {"daily": "D", "1d": "D", "weekly": "W", "1w": "W", "monthly": "M", "1m": "M"}
    freq_code = freq_map.get(frequency.lower())
    if freq_code is None:
        raise ValueError(f"Unknown frequency: {frequency}")

    if freq_code != "D":
        df = df[["Rate"]].resample(freq_code).mean().dropna(subset=["Rate"])

    if df.empty:
        raise ValueError("No data points available after resampling.")

    return df["Rate"].mean()


@validate_dates
def annualized_sharpe_ratio(tickers: Union[str, List[str]], start_date: str, end_date: str,
                            frequency: str = "daily", use_csv: bool = False) -> pd.DataFrame:
    """
    Calculate the annualized Sharpe Ratio for a list of tickers.
    Sharpe Ratio = (Annualized Return - Risk-Free Rate) / Annualized Volatility
    """
    if isinstance(tickers, str):
        tickers = [tickers]

    # Get Risk-Free Rate (SOFR)
    try:
        r_f = annualized_sofr(start_date, end_date, frequency)
    except Exception as e:
        warnings.warn(f"Could not fetch SOFR: {e}. Using R_f = 0 for Sharpe Ratio calculation.")
        r_f = 0.0

    # Get Annualized Return and Volatility
    annual_returns_df = annualized_cumulative_return(tickers, start_date, end_date, frequency, use_csv)
    annual_vol_df = annualized_volatility(tickers, start_date, end_date, frequency, use_csv)

    sharpe_dict = {}
    for ticker in tickers:
        ticker_upper = ticker.upper()
        r_asset = annual_returns_df.loc[ticker_upper, "AnnualizedReturn"]
        vol_asset = annual_vol_df.loc[ticker_upper, "AnnualizedVolatility"]

        if vol_asset == 0:
            sharpe = float('inf') if (r_asset - r_f) > 0 else 0.0
            warnings.warn(f"Volatility is zero for {ticker_upper}. Sharpe is set to {sharpe}.")
        else:
            sharpe = (r_asset - r_f) / vol_asset

        sharpe_dict[ticker_upper] = sharpe

    return pd.DataFrame.from_dict(sharpe_dict, orient="index", columns=["AnnualizedSharpeRatio"])


@validate_dates
def beta_single_stock(ticker: str, start_date: str, end_date: str, frequency: str = "daily",
                      use_csv: bool = True, market_ticker: str = DEFAULT_MARKET_TICKER) -> pd.DataFrame:
    """
    Calculate the Beta (β) of a single stock against a market index (default: SPY).
    Beta = Covariance(R_asset, R_market) / Variance(R_market)
    """
    start = parse_date(start_date)
    end = parse_date(end_date)

    # Fetch Asset and Market Returns
    returns_asset = _fetch_returns(ticker, start, end, frequency, use_csv)
    returns_market = _fetch_returns(market_ticker, start, end, frequency, use_csv=True)

    # Combine and Synchronize DataFrames
    df_asset = returns_asset.to_frame(name="R_asset")
    df_market = returns_market.to_frame(name="R_market")
    combined = pd.merge(df_asset, df_market, left_index=True, right_index=True, how='inner')

    if combined.empty:
        raise ValueError(f"No overlapping data for {ticker.upper()} and {market_ticker.upper()} in date range.")

    if len(combined) < 2:
        raise ValueError("Not enough data points for covariance/variance calculation.")

    # Calculate Beta
    covariance = combined["R_asset"].cov(combined["R_market"])
    market_variance = combined["R_market"].var()

    if market_variance == 0:
        warnings.warn(f"Market variance is zero for {market_ticker}. Beta is set to 0.")
        beta = 0.0
    else:
        beta = covariance / market_variance

    return pd.DataFrame.from_dict({ticker.upper(): beta}, orient="index",
                                  columns=[f"Beta_vs_{market_ticker.upper()}"])


@validate_dates
def alpha_single_stock(ticker: str, start_date: str, end_date: str, frequency: str = "daily",
                       use_csv: bool = True, market_ticker: str = DEFAULT_MARKET_TICKER) -> pd.DataFrame:
    """
    Calculate the Alpha (α) of a single stock based on the Capital Asset Pricing Model (CAPM).
    Alpha = R_asset - [R_f + Beta * (R_market - R_f)]
    """
    # Get Risk-Free Rate (SOFR)
    try:
        r_f = annualized_sofr(start_date, end_date, frequency)
    except Exception as e:
        warnings.warn(f"Could not fetch SOFR: {e}. Using R_f = 0 for Alpha calculation.")
        r_f = 0.0

    # Get Beta, Asset Return, and Market Return
    beta_df = beta_single_stock(ticker, start_date, end_date, frequency, use_csv, market_ticker)
    beta = beta_df.iloc[0, 0]

    r_asset_df = annualized_cumulative_return(ticker, start_date, end_date, frequency, use_csv)
    r_asset = r_asset_df.iloc[0, 0]

    r_market_df = annualized_cumulative_return(market_ticker, start_date, end_date, frequency, use_csv=True)
    r_market = r_market_df.iloc[0, 0]

    # Calculate Alpha
    required_return = r_f + beta * (r_market - r_f)
    alpha = r_asset - required_return

    return pd.DataFrame.from_dict({ticker.upper(): alpha}, orient="index",
                                  columns=[f"Alpha_vs_{market_ticker.upper()}"])


@validate_dates
def correlation(ticker1: str, ticker2: str, start_date: str, end_date: str,
                frequency: str = "daily", use_csv: bool = False) -> float:
    """Calculate correlation between two tickers."""
    start = parse_date(start_date)
    end = parse_date(end_date)

    if use_csv:
        df1 = get_returns_csv(ticker1, start, end)
        df2 = get_returns_csv(ticker2, start, end)
    else:
        with get_db_connection() as conn:
            df1 = get_returns_db(conn, ticker1, start, end)
            df2 = get_returns_db(conn, ticker2, start, end)

    if df1.empty:
        raise ValueError(f"No data found for ticker {ticker1} in date range.")
    if df2.empty:
        raise ValueError(f"No data found for ticker {ticker2} in date range.")

    df1 = resample_frequency(df1, frequency)
    df2 = resample_frequency(df2, frequency)

    merged = pd.merge(df1, df2, on="Date", suffixes=("_1", "_2"))
    if merged.empty:
        raise ValueError("Tickers do not have overlapping data for this date range.")

    return float(merged["return_1d_1"].corr(merged["return_1d_2"]))


@validate_dates
def correlation_matrix(tickers: List[str], start_date: str, end_date: str,
                       frequency: str = "daily", use_csv: bool = False) -> pd.DataFrame:
    """Compute a correlation matrix for a list of tickers."""
    start = parse_date(start_date)
    end = parse_date(end_date)

    all_returns = []
    for ticker in tickers:
        df_returns = _fetch_returns(ticker, start, end, frequency, use_csv)
        df_returns = df_returns.to_frame(name=ticker.upper())
        all_returns.append(df_returns)

    combined = pd.concat(all_returns, axis=1, join='inner')

    if combined.empty:
        raise ValueError("No overlapping data found for the specified tickers in date range.")

    return combined.corr()