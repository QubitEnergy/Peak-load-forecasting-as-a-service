#!/usr/bin/env python3
import requests
import pandas as pd
import numpy as np
import argparse
from datetime import datetime, timedelta
import urllib3

# Disable warnings for unverified HTTPS requests (for testing with self‐signed certificates)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API headers using your token
headers = {
    "Authorization": "Bearer 78uiaschs5kobwy9p85m5w4xvks9929e",  # Replace if needed
    "Accept-Language": "no"
}

def split_date_range(date_from, date_to, chunk_days=7):
    """
    Splits the overall date range into chunks of the specified days.
    """
    start = datetime.fromisoformat(date_from)
    end = datetime.fromisoformat(date_to)
    intervals = []
    current = start
    while current < end:
        next_time = min(current + timedelta(days=chunk_days), end)
        intervals.append((current.strftime("%Y-%m-%d"), next_time.strftime("%Y-%m-%d")))
        current = next_time
    return intervals

def fetch_unit_data(api_endpoint, date_from, date_to):
    """
    Fetches time series data from the Energinet API for a given endpoint over the specified date range.
    If the endpoint does not start with 'http', it is appended to the base URL.
    SSL verification is disabled (verify=False) for testing purposes.
    """
    base_url = "https://www.energinet.net"
    url = api_endpoint if api_endpoint.startswith("http") else base_url + api_endpoint
    intervals = split_date_range(date_from, date_to, chunk_days=7)
    all_data = []
    for start, end in intervals:
        custom_headers = headers.copy()
        custom_headers["DateIntervalFrom"] = start
        custom_headers["DateIntervalTo"] = end
        try:
            response = requests.get(url, headers=custom_headers, verify=False)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                all_data.extend(data)
            else:
                print(f"Unexpected data format for endpoint {url} in interval {start} to {end}")
        except Exception as e:
            print(f"Error fetching data for endpoint {url} from {start} to {end}: {e}")
    return all_data

def compute_rolling_variability(data_df, window='28D'):
    # Ensure index is a DatetimeIndex. If not, convert with utc=True.
    if not isinstance(data_df.index, pd.DatetimeIndex):
        data_df.index = pd.to_datetime(data_df.index, utc=True)
    # If index is tz-aware, remove the timezone.
    if data_df.index.tz is not None:
        data_df.index = data_df.index.tz_localize(None)
        
    freq = pd.infer_freq(data_df.index)
    if freq is None:
        raise ValueError("Cannot infer frequency from data index; please set window as an integer.")
    
    td = pd.Timedelta(window)
    if freq.endswith("H"):
        period_seconds = 3600
    elif freq.endswith("T"):
        period_seconds = 60
    elif freq.endswith("S"):
        period_seconds = 1
    elif freq.endswith("D"):
        period_seconds = 86400
    else:
        period_seconds = 3600
    window_int = int(td.total_seconds() // period_seconds)
    
    rolling_std = data_df['Value'].rolling(window=window_int).std()
    rolling_mean = data_df['Value'].rolling(window=window_int).mean()
    rolling_coeff_var = rolling_std / rolling_mean
    df_rolling = pd.DataFrame({
        'timestamp': data_df.index,
        'rolling_std': rolling_std,
        'rolling_mean': rolling_mean,
        'rolling_coeff_var': rolling_coeff_var
    })
    return df_rolling


def process_unit(unit_id, name, api_endpoint, date_from, date_to, window):
    """
    Fetches data for a single unit, converts it to a time series DataFrame,
    computes rolling variability metrics, and appends unit metadata.
    """
    data = fetch_unit_data(api_endpoint, date_from, date_to)
    if not data:
        print(f"No data fetched for unit {unit_id} ({name}).")
        return None

    df = pd.DataFrame(data)
    if 'Start' not in df.columns:
        print(f"Data for unit {unit_id} ({name}) is missing a 'Start' column.")
        return None

    df['Start'] = pd.to_datetime(df['Start'])
    df.set_index('Start', inplace=True)
    df.sort_index(inplace=True)

    if 'Value' not in df.columns:
        print(f"Data for unit {unit_id} ({name}) is missing a 'Value' column.")
        return None

    rolling_df = compute_rolling_variability(df, window)
    rolling_df['unit_id'] = unit_id
    rolling_df['name'] = name
    rolling_df['api_endpoint'] = api_endpoint
    return rolling_df

def main(csv_file, date_from, date_to, window, data_type):
    try:
        # Skip extra header/title rows if necessary (here we skip rows 0 and 2)
        df_units = pd.read_csv(csv_file, encoding="latin1", skiprows=[0, 2])
    except Exception as e:
        print(f"Error reading CSV file '{csv_file}': {e}")
        return

    # Rename columns so that "unit_id", "name", and the chosen data_type column (default 'Energy') are used.
    df_units.rename(columns={"Name": "name", data_type: "api_endpoint"}, inplace=True)
    required = ["unit_id", "name", "api_endpoint"]
    for col in required:
        if col not in df_units.columns:
            print(f"CSV is missing the required column: {col}")
            return

    print(f"Using date range from {date_from} to {date_to} for data type '{data_type}' with a rolling window of {window}.")
    results = []
    for idx, row in df_units.iterrows():
        unit_id = row["unit_id"]
        name = row["name"]
        api_endpoint = row["api_endpoint"]
        if pd.isna(api_endpoint) or api_endpoint.strip() == "":
            print(f"Skipping unit {unit_id} ({name}) – no API endpoint provided.")
            continue
        print(f"Fetching energy data for unit {unit_id} ({name}) from endpoint {api_endpoint}...")
        unit_result = process_unit(unit_id, name, api_endpoint, date_from, date_to, window)
        if unit_result is not None:
            results.append(unit_result)

    if results:
        all_results = pd.concat(results, ignore_index=True)
        print("\nRolling Variability Results:")
        print(all_results)
        all_results.to_csv("rolling_variability_all_units.csv", index=False)
        print("Results saved to 'rolling_variability_all_units.csv'")
    else:
        print("No results to display.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute rolling variability metrics for energy usage data for all units listed in a CSV file."
    )
    parser.add_argument("csv_file", help="Path to the CSV file containing unit API endpoints and metadata.")
    parser.add_argument("--date_from", help="Start date (YYYY-MM-DD) for data fetching", default="2025-03-09")
    parser.add_argument("--date_to", help="End date (YYYY-MM-DD) for data fetching", default="2025-04-06")
    parser.add_argument("--window", help="Rolling window size (e.g., '7D' for 7 days)", default="7D")
    parser.add_argument("--data_type", help="Column name in the CSV to use for API endpoints (default: Energy)", default="Energy")
    args = parser.parse_args()
    main(args.csv_file, args.date_from, args.date_to, args.window, args.data_type)
