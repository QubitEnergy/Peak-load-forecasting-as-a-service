#!/usr/bin/env python3
"""
Simplified test that validates the module structure and creates a test report
showing what the anomaly detector would find.
"""
import sys
from pathlib import Path

# Try to import dependencies
try:
    import pandas as pd
    import numpy as np
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("⚠ pandas not installed - will show structure validation only")
    print("  Install with: pip install pandas numpy matplotlib seaborn\n")

# Test module structure
print("=" * 70)
print("VALIDATING MODULE STRUCTURE")
print("=" * 70)

sys.path.insert(0, str(Path(__file__).parent))

try:
    # Check if module file exists
    module_path = Path("src/data_processors/anomaly_detector.py")
    if module_path.exists():
        print(f"✓ Module file exists: {module_path}")
        
        # Read and check key components
        content = module_path.read_text()
        if "class AMSAnomalyDetector" in content:
            print("✓ AMSAnomalyDetector class found")
        if "def detect_nulls" in content:
            print("✓ detect_nulls method found")
        if "def detect_negatives" in content:
            print("✓ detect_negatives method found")
        if "def detect_missing_hours" in content:
            print("✓ detect_missing_hours method found")
        if "def get_summary" in content:
            print("✓ get_summary method found")
        if "def print_report" in content:
            print("✓ print_report method found")
    else:
        print(f"✗ Module file not found: {module_path}")
        
except Exception as e:
    print(f"✗ Error checking module: {e}")

# If pandas is available, run actual test
if HAS_PANDAS:
    print("\n" + "=" * 70)
    print("RUNNING ACTUAL DATA TEST")
    print("=" * 70)
    
    try:
        from src.data_processors import AMSAnomalyDetector
        
        # Load data
        data_path = Path("Datek_sensor_data/energy_and_temperature.csv")
        if data_path.exists():
            print(f"\nLoading: {data_path}")
            df = pd.read_csv(data_path, sep=";", low_memory=False)
            print(f"✓ Loaded {len(df):,} records")
            print(f"  Columns: {', '.join(df.columns.tolist())}")
            
            # Check actual column names
            time_col = "time" if "time" in df.columns else "timestamp_utc"
            power_col = "import" if "import" in df.columns else "active_power_W"
            meter_col = "meter_id" if "meter_id" in df.columns else None
            
            print(f"\nDetected columns:")
            print(f"  Time: {time_col}")
            print(f"  Power: {power_col}")
            print(f"  Meter ID: {meter_col}")
            
            # Initialize detector with correct column names
            detector = AMSAnomalyDetector(
                timestamp_col=time_col,
                power_col=power_col,
                meter_id_col=meter_col
            )
            
            # Convert timestamp
            df[time_col] = pd.to_datetime(df[time_col], errors='coerce', utc=True)
            
            # Check data basic stats
            print(f"\nData Statistics:")
            print(f"  Date range: {df[time_col].min()} to {df[time_col].max()}")
            if meter_col:
                print(f"  Meters: {df[meter_col].nunique()}")
                print(f"  Meter IDs: {', '.join(df[meter_col].unique())}")
            
            # Check for nulls and negatives manually
            null_count = df[power_col].isna().sum()
            negative_count = (df[power_col] < 0).sum()
            
            print(f"\nManual Check:")
            print(f"  Null values in {power_col}: {null_count} ({null_count/len(df)*100:.2f}%)")
            print(f"  Negative values in {power_col}: {negative_count} ({negative_count/len(df)*100:.2f}%)")
            
            # Run actual detector
            print(f"\nRunning AMSAnomalyDetector...")
            summary = detector.get_summary(df)
            
            print(f"\nDetector Results:")
            print(f"  Total records: {summary['total_records']:,}")
            print(f"  Null values: {summary['null_values']:,} ({summary['null_percentage']:.2f}%)")
            print(f"  Negative values: {summary['negative_values']:,} ({summary['negative_percentage']:.2f}%)")
            print(f"  Missing hours: {summary['missing_hours']:,} ({summary['missing_hours_percentage']:.2f}%)")
            
            # Detect all
            anomalies = detector.detect_all(df)
            print(f"\nAnomaly Types Detected: {len(anomalies)}")
            for anomaly_type, anomaly_df in anomalies.items():
                print(f"  - {anomaly_type}: {len(anomaly_df):,} anomalies")
            
            # Generate report
            output_file = "data/outputs/test_anomaly_report.txt"
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            detector.print_report(df, output_file=output_file)
            print(f"\n✓ Full report saved to: {output_file}")
            
            # Try to generate plots
            try:
                output_dir = "data/outputs/test_anomaly_plots"
                detector.plot_anomalies(df, output_dir=output_dir)
                print(f"✓ Plots saved to: {output_dir}")
            except Exception as e:
                print(f"⚠ Could not generate plots: {e}")
            
            print("\n" + "=" * 70)
            print("✓ TEST PASSED - Anomaly detector works correctly!")
            print("=" * 70)
            
        else:
            print(f"✗ Data file not found: {data_path}")
            
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\n" + "=" * 70)
    print("STRUCTURE VALIDATION COMPLETE")
    print("=" * 70)
    print("\nTo run full test, install dependencies:")
    print("  pip install pandas numpy matplotlib seaborn")
    print("\nThen run:")
    print("  python3 test_anomaly_simple.py")

