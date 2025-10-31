"""
Example script for AMS anomaly detection.
Action point: "Lage skript for anomaly detection (sjekke null- og minustimer i AMS-data)"

This script demonstrates how to use the AMSAnomalyDetector to check for:
- Null/missing values in hourly data
- Negative consumption values
- Missing hours in the time series
"""
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_processors import AMSAnomalyDetector


def main():
    """Run anomaly detection on AMS hourly data."""
    
    # Example 1: Check Datek sensor data (if you have hourly aggregated data)
    # First, you might need to aggregate minute data to hourly
    print("=" * 60)
    print("AMS ANOMALY DETECTION EXAMPLE")
    print("=" * 60)
    
    # Initialize detector
    detector = AMSAnomalyDetector(
        timestamp_col="timestamp_utc",
        power_col="active_power_W",
        meter_id_col="meter_id"
    )
    
    # Example: Load hourly data
    # If you have hourly aggregated data, load it here
    # For demonstration, we'll show how to use it with your existing data
    
    data_paths = [
        "Datek_sensor_data/energy_and_temperature.csv",
        "Model_development/energy_and_temperature.csv"
    ]
    
    for data_path in data_paths:
        if Path(data_path).exists():
            print(f"\n{'='*60}")
            print(f"Checking: {data_path}")
            print(f"{'='*60}\n")
            
            # Load data
            df = pd.read_csv(data_path, sep=";", low_memory=False)
            
            # Ensure timestamp is datetime
            df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], errors='coerce', utc=True)
            
            # Aggregate to hourly if data is at minute level
            # (Skip if already hourly)
            if 'timestamp_utc' in df.columns and len(df) > 0:
                # Check if data appears to be minute-level (has many records per hour)
                sample_time_diff = (df['timestamp_utc'].iloc[1] - df['timestamp_utc'].iloc[0]).total_seconds() / 60
                
                if sample_time_diff < 60:  # Likely minute-level data
                    print("Data appears to be minute-level. Aggregating to hourly...")
                    df['timestamp_hour'] = df['timestamp_utc'].dt.floor('H')
                    
                    # Group by meter and hour, take mean
                    if 'meter_id' in df.columns:
                        agg_dict = {
                            'active_power_W': 'mean',
                            'air_temperature': 'mean'
                        }
                        # Include other numeric columns if they exist
                        numeric_cols = df.select_dtypes(include=[float, int]).columns.tolist()
                        for col in numeric_cols:
                            if col not in agg_dict and col != 'meter_id':
                                agg_dict[col] = 'mean'
                        
                        df_hourly = df.groupby(['timestamp_hour', 'meter_id']).agg(agg_dict).reset_index()
                        df_hourly.rename(columns={'timestamp_hour': 'timestamp_utc'}, inplace=True)
                        df = df_hourly
                    else:
                        df_hourly = df.groupby('timestamp_hour').agg({'active_power_W': 'mean'}).reset_index()
                        df_hourly.rename(columns={'timestamp_hour': 'timestamp_utc'}, inplace=True)
                        df = df_hourly
                    
                    print(f"Aggregated to {len(df)} hourly records")
            
            # Run anomaly detection
            detector.print_report(df, output_file=f"anomaly_report_{Path(data_path).stem}.txt")
            
            # Generate plots
            output_dir = f"data/outputs/anomaly_plots_{Path(data_path).stem}"
            detector.plot_anomalies(df, output_dir=output_dir)
            
            print(f"\n✓ Analysis complete for {data_path}")
        else:
            print(f"⚠ File not found: {data_path}")
    
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()

