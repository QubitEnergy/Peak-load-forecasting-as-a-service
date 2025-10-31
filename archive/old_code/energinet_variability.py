#!/usr/bin/env python3
import requests
import pandas as pd
import numpy as np
import argparse
from datetime import datetime, timedelta
import urllib3

# Disable warnings about unverified HTTPS requests (for testing with self‐signed certificates).
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up the API headers using your actual token.
headers = {
    "Authorization": "Bearer 78uiaschs5kobwy9p85m5w4xvks9929e",  # Replace with your API token if needed
    "Accept-Language": "no"
}

def compute_last_complete_week():
    """
    Computes the date range (Monday to Sunday) of the most recent complete week.
    For example, if today is Wednesday, April 8, 2025, the last complete week is
    Monday, March 31, 2025 to Sunday, April 6, 2025.
    """
    today = datetime.today()
    days_since_sunday = (today.weekday() + 1) % 7  # Monday=0, Sunday=6
    last_sunday = today - timedelta(days=days_since_sunday)
    if today.weekday() == 6:
        last_sunday = today - timedelta(days=7)
    last_monday = last_sunday - timedelta(days=6)
    return last_monday.strftime("%Y-%m-%d"), last_sunday.strftime("%Y-%m-%d")

def split_date_range(date_from, date_to, chunk_days=7):
    """
    Splits the overall date range into chunks of the specified days.
    In our forecasting context, if the window is one week, this will return a single chunk.
    """
    start = datetime.fromisoformat(date_from)
    end = datetime.fromisoformat(date_to)
    intervals = []
    current_start = start
    while current_start < end:
        current_end = min(current_start + timedelta(days=chunk_days), end)
        intervals.append((current_start.strftime("%Y-%m-%d"), current_end.strftime("%Y-%m-%d")))
        current_start = current_end
    return intervals

def fetch_unit_data(api_endpoint, overall_date_from, overall_date_to):
    """
    Fetches time series data from the Energinet API for a given endpoint over the provided date range.
    If the endpoint already starts with 'http', it is used directly; otherwise, it's appended to the base URL.
    SSL verification is disabled (verify=False) for testing purposes.
    """
    base_url = "https://www.energinet.net"
    url = api_endpoint if api_endpoint.startswith("http") else base_url + api_endpoint

    intervals = split_date_range(overall_date_from, overall_date_to, chunk_days=7)
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

def compute_variability(data):
    """
    Computes variability metrics (standard deviation, mean, coefficient of variation)
    based on the "Value" field in the time series data.
    """
    values = [d.get("Value") for d in data if "Value" in d and d.get("Value") is not None]
    if not values:
        return None
    std_dev = np.std(values)
    mean_val = np.mean(values)
    coeff_var = std_dev / mean_val if mean_val != 0 else np.nan
    return {"std_dev": std_dev, "mean": mean_val, "coeff_var": coeff_var}

def main(csv_file, date_from, date_to, data_type):
    try:
        # Skip extra header/title rows (assuming row 0 and row 2 are non-data).
        df = pd.read_csv(csv_file, encoding="latin1", skiprows=[0, 2])
    except Exception as e:
        print(f"Error reading CSV file '{csv_file}': {e}")
        return

    # Rename columns so that we have "unit_id", "name", and the chosen data type becomes "api_endpoint".
    df.rename(columns={"Name": "name", data_type: "api_endpoint"}, inplace=True)

    required_columns = ["unit_id", "name", "api_endpoint"]
    for col in required_columns:
        if col not in df.columns:
            print(f"CSV is missing the required column: {col}")
            return

    print(f"Using date range from {date_from} to {date_to} for data type '{data_type}'.")
    results = []
    for idx, row in df.iterrows():
        unit_id = row["unit_id"]
        name = row["name"]
        api_endpoint = row["api_endpoint"]

        if pd.isna(api_endpoint) or api_endpoint == "":
            print(f"Skipping unit {unit_id} ({name}): No API endpoint provided.")
            continue

        print(f"Fetching energy data for unit {unit_id} ({name}) from endpoint {api_endpoint}...")
        data = fetch_unit_data(api_endpoint, date_from, date_to)
        if data:
            variability = compute_variability(data)
            if variability:
                variability["unit_id"] = unit_id
                variability["name"] = name
                variability["api_endpoint"] = api_endpoint
                results.append(variability)
            else:
                print(f"No valid data values found for unit {unit_id} ({name}).")
        else:
            print(f"Failed to fetch data for unit {unit_id} ({name}).")

    if results:
        results_df = pd.DataFrame(results)
        print("\nVariability Results:")
        print(results_df)
        results_df.to_csv("variability_results.csv", index=False)
        print("Results saved to 'variability_results.csv'")
    else:
        print("No results to display.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch Energinet energy usage data for a specified one-week window and compute variability metrics for forecasting."
    )
    parser.add_argument("csv_file", help="Path to the CSV file containing unit API endpoints and metadata.")
    parser.add_argument("--date_from", help="Start date (YYYY-MM-DD) for fetching data")
    parser.add_argument("--date_to", help="End date (YYYY-MM-DD) for fetching data")
    parser.add_argument("--forecast", action="store_true", help="Automatically use the most recent complete week for forecasting")
    parser.add_argument("--data_type", default="Energy", help="Column name in the CSV to use for API endpoints (default: Energy)")
    args = parser.parse_args()

    if args.forecast:
        date_from, date_to = compute_last_complete_week()
    else:
        if args.date_from and args.date_to:
            date_from = args.date_from
            date_to = args.date_to
        else:
            # Default one-week window if not provided.
            date_from = "2025-03-31"
            date_to = "2025-04-06"

    main(args.csv_file, date_from, date_to, args.data_type)
