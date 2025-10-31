#!/usr/bin/env python3

import pandas as pd

def keep_selected_columns_and_sort(
    input_file: str = "all_minute_data.csv",
    output_file: str = "processed_minute_data.csv",
    sep: str = ";",
    debug: bool = True
):
    """
    1) Reads a CSV file.
    2) Keeps only the specified columns: time, a, an, rp, rn, i1, i2, i3, u1, u2, u3, meter_id.
    3) Renames them to more descriptive names.
    4) Sorts first by 'meter_id' ascending, then by 'time' ascending.
    5) Writes the cleaned data to 'output_file'.
    """

    # Columns to keep
    desired_cols = ["time", "a", "an", "rp", "rn", "i1", "i2", "i3", "u1", "u2", "u3", "meter_id"]

    # Map old column names to new descriptive names
    rename_map = {
        "time": "timestamp_utc",
        "a": "active_power_W",
        "an": "active_power_neg_W",
        "rp": "reactive_power_VAr",
        "rn": "reactive_power_neg_VAr",
        "i1": "phase1_current_A",
        "i2": "phase2_current_A",
        "i3": "phase3_current_A",
        "u1": "phase1_voltage_V",
        "u2": "phase2_voltage_V",
        "u3": "phase3_voltage_V",
        "meter_id": "meter_id"  # unchanged but kept for completeness
    }

    if debug:
        print(f"Reading input CSV: {input_file}")

    # Read CSV (disable chunked reading to avoid DtypeWarning)
    df = pd.read_csv(input_file, sep=sep, low_memory=False)

    # Keep only the columns we care about (if any are missing, they will be skipped)
    existing_cols = [col for col in desired_cols if col in df.columns]
    df = df[existing_cols]

    # Rename columns to more descriptive names
    # (ignore any that don't exist to avoid errors)
    df.rename(columns=rename_map, inplace=True, errors="ignore")

    # Convert 'timestamp_utc' column to datetime (coerce errors in case of invalid timestamps)
    if "timestamp_utc" in df.columns:
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], errors="coerce")

    # Sort first by 'meter_id' ascending, then by 'timestamp_utc' ascending
    sort_cols = []
    if "meter_id" in df.columns:
        sort_cols.append("meter_id")
    if "timestamp_utc" in df.columns:
        sort_cols.append("timestamp_utc")

    if sort_cols:
        df.sort_values(by=sort_cols, inplace=True)

    if debug:
        print(f"Keeping columns: {existing_cols}")
        print(f"Renaming columns according to: {rename_map}")
        print("\nSample of the resulting DataFrame:")
        print(df.head(10))

    # Write the cleaned CSV
    df.to_csv(output_file, index=False, sep=sep)
    if debug:
        print(f"\nCleaned data saved to {output_file}")


def main():
    input_csv = "all_minute_data.csv"
    output_csv = "processed_minute_data.csv"

    keep_selected_columns_and_sort(
        input_file=input_csv,
        output_file=output_csv,
        sep=";",   # or "," if your data is comma-separated
        debug=True
    )

if __name__ == "__main__":
    main()
