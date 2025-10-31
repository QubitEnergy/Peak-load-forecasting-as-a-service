#!/usr/bin/env python3
"""
Quick test script for anomaly detection module.
Tests on actual data files.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import pandas as pd
    import numpy as np
    print("✓ pandas and numpy imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("\nPlease install dependencies:")
    print("  pip install pandas numpy matplotlib seaborn")
    sys.exit(1)

try:
    from src.data_processors import AMSAnomalyDetector
    print("✓ AMSAnomalyDetector imported successfully\n")
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("\nMake sure you're in the project root directory")
    sys.exit(1)


def test_anomaly_detector():
    """Test the anomaly detector on actual data."""
    
    print("=" * 70)
    print("TESTING AMS ANOMALY DETECTOR")
    print("=" * 70)
    
    # Initialize detector
    detector = AMSAnomalyDetector(
        timestamp_col="timestamp_utc",
        power_col="active_power_W",
        meter_id_col="meter_id"
    )
    
    # Test on the processed data file
    data_path = Path("Datek_sensor_data/energy_and_temperature.csv")
    
    if not data_path.exists():
        print(f"\n✗ Data file not found: {data_path}")
        return False
    
    print(f"\nLoading data from: {data_path}")
    df = pd.read_csv(data_path, sep=";", low_memory=False)
    print(f"✓ Loaded {len(df):,} records")
    print(f"  Columns: {list(df.columns)}")
    
    # Check if timestamp column exists
    if 'timestamp_utc' not in df.columns:
        print("\n✗ Column 'timestamp_utc' not found")
        print(f"  Available columns: {list(df.columns)}")
        return False
    
    # Convert timestamp
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], errors='coerce', utc=True)
    
    # Check data frequency
    if len(df) > 1:
        sample_time_diff = (df['timestamp_utc'].iloc[1] - df['timestamp_utc'].iloc[0]).total_seconds() / 60
        print(f"\nData frequency: ~{sample_time_diff:.1f} minutes between records")
        
        # Aggregate to hourly if needed
        if sample_time_diff < 60:
            print("Aggregating minute-level data to hourly...")
            df['timestamp_hour'] = df['timestamp_utc'].dt.floor('H')
            
            if 'meter_id' in df.columns:
                agg_dict = {'active_power_W': 'mean'}
                if 'air_temperature' in df.columns:
                    agg_dict['air_temperature'] = 'mean'
                
                df_hourly = df.groupby(['timestamp_hour', 'meter_id']).agg(agg_dict).reset_index()
                df_hourly.rename(columns={'timestamp_hour': 'timestamp_utc'}, inplace=True)
                df = df_hourly
                print(f"✓ Aggregated to {len(df):,} hourly records")
            else:
                print("⚠ No meter_id column found, aggregating without grouping")
                df_hourly = df.groupby('timestamp_hour').agg({'active_power_W': 'mean'}).reset_index()
                df_hourly.rename(columns={'timestamp_hour': 'timestamp_utc'}, inplace=True)
                df = df_hourly
                print(f"✓ Aggregated to {len(df):,} hourly records")
    
    # Check for required columns
    if 'active_power_W' not in df.columns:
        print("\n⚠ Column 'active_power_W' not found. Looking for alternative...")
        power_cols = [c for c in df.columns if 'power' in c.lower() or 'active' in c.lower()]
        if power_cols:
            print(f"  Found: {power_cols}")
            print(f"  Using: {power_cols[0]}")
            detector.power_col = power_cols[0]
        else:
            print("✗ No power column found")
            return False
    
    print("\n" + "-" * 70)
    print("RUNNING ANOMALY DETECTION")
    print("-" * 70)
    
    # Get summary
    try:
        summary = detector.get_summary(df)
        print("\nSUMMARY:")
        print(f"  Total records: {summary['total_records']:,}")
        print(f"  Null values: {summary['null_values']:,} ({summary['null_percentage']:.2f}%)")
        print(f"  Negative values: {summary['negative_values']:,} ({summary['negative_percentage']:.2f}%)")
        print(f"  Missing hours: {summary['missing_hours']:,} ({summary['missing_hours_percentage']:.2f}%)")
    except Exception as e:
        print(f"\n✗ Error getting summary: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Detect all anomalies
    try:
        print("\nDETECTING ANOMALIES...")
        anomalies = detector.detect_all(df)
        print(f"✓ Detected {len(anomalies)} anomaly types:")
        for anomaly_type, anomaly_df in anomalies.items():
            print(f"  - {anomaly_type}: {len(anomaly_df):,} anomalies")
            if len(anomaly_df) > 0:
                print(f"    Sample: {anomaly_df.iloc[0].to_dict()}")
    except Exception as e:
        print(f"\n✗ Error detecting anomalies: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Generate report
    try:
        print("\nGENERATING REPORT...")
        output_file = "data/outputs/test_anomaly_report.txt"
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        detector.print_report(df, output_file=output_file)
        print(f"✓ Report saved to: {output_file}")
    except Exception as e:
        print(f"\n⚠ Error generating report: {e}")
        import traceback
        traceback.print_exc()
    
    # Generate plots (optional, might fail if matplotlib not available)
    try:
        print("\nGENERATING PLOTS...")
        output_dir = "data/outputs/test_anomaly_plots"
        detector.plot_anomalies(df, output_dir=output_dir)
        print(f"✓ Plots saved to: {output_dir}")
    except Exception as e:
        print(f"\n⚠ Error generating plots: {e}")
        print("  (This is optional - matplotlib might not be installed)")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    success = test_anomaly_detector()
    sys.exit(0 if success else 1)

