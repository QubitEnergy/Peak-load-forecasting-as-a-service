"""
Variability analysis utilities.
Extracted from energinet_variability2.py
"""
import pandas as pd
import numpy as np


def compute_variability(data: list) -> dict:
    """
    Compute variability metrics (standard deviation, mean, coefficient of variation).
    
    Args:
        data: List of dictionaries with "Value" field
        
    Returns:
        Dictionary with std_dev, mean, coeff_var
    """
    values = [d.get("Value") for d in data if "Value" in d and d.get("Value") is not None]
    
    if not values:
        return None
    
    std_dev = np.std(values)
    mean_val = np.mean(values)
    coeff_var = std_dev / mean_val if mean_val != 0 else np.nan
    
    return {"std_dev": std_dev, "mean": mean_val, "coeff_var": coeff_var}


def compute_rolling_variability(data_df: pd.DataFrame, window: str = '28D') -> pd.DataFrame:
    """
    Compute rolling variability metrics.
    
    Args:
        data_df: DataFrame with datetime index and "Value" column
        window: Rolling window size (e.g., '28D' for 28 days)
        
    Returns:
        DataFrame with rolling_coeff_var column
    """
    df = data_df.copy()
    
    # Ensure index is DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
    
    # Remove timezone if present
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    # Infer frequency
    freq = pd.infer_freq(df.index)
    if freq is None:
        raise ValueError("Cannot infer frequency from data index")
    
    # Compute rolling statistics
    df['rolling_mean'] = df['Value'].rolling(window=window).mean()
    df['rolling_std'] = df['Value'].rolling(window=window).std()
    df['rolling_coeff_var'] = df['rolling_std'] / df['rolling_mean']
    
    return df

