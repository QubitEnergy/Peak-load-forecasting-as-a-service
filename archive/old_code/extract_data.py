#!/usr/bin/env python3
import requests
import pandas as pd
import argparse
from datetime import datetime, timedelta
import urllib3

# Disable warnings for unverified HTTPS requests (for testing with self‐signed certificates)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API headers using your token
headers = {
    "Authorization": "Bearer 78uiaschs5kobwy9p85m5w4xvks9929e",  # Replace with your API token if needed
    "Accept-Language": "no"
}

def split_date_range(date_from, date_to, chunk_days=7):
    """Splits the overall date range into chunks (to handle large requests)."""
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
    Fetches raw time series energy data from the Energinet API for a given endpoint
    over the specified date range.
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
                print(f"Unexpected data format for endpoint {url} from {start} to {end}")
        except Exception as e:
            print(f"Error fetching data for endpoint {url} from {start} to {end}: {e}")
    return all_data

def main(csv_file, date_from, date_to):
    # List the units of interest by name.
    units_of_interest = [
        "Fellesanlegg eks. ventilasjon og DX-kjøling",
        "Varme radiatorer kjøpesenter/kino/bibliotek"
    ]
    
    try:
        # Read the CSV file (adjust skiprows if needed)
        df_units = pd.read_csv(csv_file, encoding="latin1", skiprows=[0, 2])
    except Exception as e:
        print(f"Error reading CSV file '{csv_file}': {e}")
        return

    # Rename columns so that "Name" becomes 'name' and "Energy" becomes 'api_endpoint'
    df_units.rename(columns={"Name": "name", "Energy": "api_endpoint"}, inplace=True)
    
    # Filter for the units of interest (using exact match on the 'name' column)
    df_filtered = df_units[df_units["name"].isin(units_of_interest)]
    if df_filtered.empty:
        print("No matching units found in the CSV file.")
        return

    print("Extracting energy data for the following units:")
    print(df_filtered[["unit_id", "name", "api_endpoint"]])
    
    for idx, row in df_filtered.iterrows():
        unit_id = row["unit_id"]
        name = row["name"]
        api_endpoint = row["api_endpoint"]
        print(f"\nFetching data for {name} (unit_id: {unit_id}) from endpoint {api_endpoint}...")
        data = fetch_unit_data(api_endpoint, date_from, date_to)
        if data:
            df_data = pd.DataFrame(data)
            # Keep only the time and energy usage columns. We'll use 'Start' as the time.
            if 'Start' in df_data.columns and 'Value' in df_data.columns:
                df_extracted = df_data[['Start', 'Value']]
                # Optionally, rename the columns
                df_extracted.rename(columns={"Start": "Time", "Value": "Energy"}, inplace=True)
                # Save to CSV
                safe_name = name.replace(" ", "_").replace("/", "_")
                out_filename = f"{unit_id}_{safe_name}_energy.csv"
                df_extracted.to_csv(out_filename, index=False)
                print(f"Data for {name} saved to {out_filename} (rows: {len(df_extracted)})")
            else:
                print(f"Data for {name} does not contain the expected 'Start' and 'Value' columns.")
        else:
            print(f"No data fetched for {name} (unit_id: {unit_id}).")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract raw energy usage data (Time and Energy columns) for selected units from a CSV file."
    )
    parser.add_argument("csv_file", help="Path to the CSV file containing unit API endpoints and metadata.")
    parser.add_argument("--date_from", help="Start date (YYYY-MM-DD) for data fetching", default="2024-04-06")
    parser.add_argument("--date_to", help="End date (YYYY-MM-DD) for data fetching", default="2025-04-06")
    args = parser.parse_args()
    main(args.csv_file, args.date_from, args.date_to)
