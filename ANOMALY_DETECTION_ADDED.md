# AMS Anomaly Detection Module - Added

## Summary

Added a production-ready anomaly detection module to address the action point from the IFE meeting:
> **"Lage skript for anomaly detection (sjekke null- og minustimer i AMS-data)"**
> *(Create script for anomaly detection (check null- and negative hours in AMS-data))*

## What Was Added

### 1. Core Module: `src/data_processors/anomaly_detector.py`

A comprehensive `AMSAnomalyDetector` class that detects:

- **Null/Missing Values**: Identifies null/NaN values in hourly consumption data
- **Negative Values**: Detects negative consumption values (should not exist for consumption data)
- **Missing Hours**: Identifies gaps in the expected hourly time series

**Key Features:**
- Works with hourly AMS data (Advanced Metering System)
- Supports multiple meters (meter_id grouping)
- Generates detailed reports with statistics
- Creates visualization plots
- Provides summary statistics by meter

### 2. Example Script: `examples/anomaly_detection_example.py`

A ready-to-use example script that demonstrates:
- Loading hourly data (or aggregating minute data to hourly)
- Running anomaly detection
- Generating reports and plots
- Processing multiple data files

### 3. Updated Documentation

- **README.md**: Added anomaly detection to features and usage examples
- **Module exports**: Added `AMSAnomalyDetector` to `src/data_processors/__init__.py`

## What Already Existed (Before)

The codebase had **statistical anomaly detection** in exploration notebooks:
- `notebooks/exploration/minute_data_EDA.py` - Detects values >3σ from rolling mean
- `notebooks/exploration/minute_level_patterns.py` - Similar statistical anomaly detection

**However**, these did NOT specifically check for:
- ❌ Null/empty values
- ❌ Negative consumption values
- ❌ Missing hours in hourly time series

## What's Different

The new module is:
1. **Production-ready**: Clean class-based API, not just exploration scripts
2. **Data quality focused**: Specifically checks for null/negative/missing values (not statistical outliers)
3. **AMS-specific**: Designed for hourly Advanced Metering System data
4. **Integrated**: Part of the `src/` modular structure

## Usage

### Quick Start

```python
from src.data_processors import AMSAnomalyDetector
import pandas as pd

# Load hourly data
df = pd.read_csv("your_hourly_ams_data.csv")
df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])

# Initialize detector
detector = AMSAnomalyDetector(
    timestamp_col="timestamp_utc",
    power_col="active_power_W",
    meter_id_col="meter_id"
)

# Generate report
detector.print_report(df, output_file="anomaly_report.txt")

# Get summary
summary = detector.get_summary(df)
```

### Run Example Script

```bash
python examples/anomaly_detection_example.py
```

## Output

The detector generates:
1. **Text Report** (`anomaly_report.txt`):
   - Summary statistics (total records, anomaly counts)
   - Breakdown by meter
   - Sample anomalies
   - Percentages and counts

2. **Visualization Plots**:
   - `anomaly_counts.png` - Bar chart of anomaly types
   - `anomaly_timeline.png` - Timeline visualization of anomalies

## Integration with Existing Code

The new module:
- ✅ Fits into the existing `src/data_processors/` structure
- ✅ Uses the same data format as other processors
- ✅ Can be used alongside existing statistical anomaly detection
- ✅ Follows the same code patterns as other modules

## Next Steps

The anomaly detection module is ready to use. To integrate it into your workflow:

1. **Run on existing data**: Use the example script to check your current data files
2. **Add to pipeline**: Include anomaly detection as a quality check step before training models
3. **Automate**: Add to data collection workflow to flag issues early

## Files Added

```
src/data_processors/
├── anomaly_detector.py       # Main detection module
└── __init__.py               # Updated exports

examples/
└── anomaly_detection_example.py  # Usage example

README.md                     # Updated with new feature
ANOMALY_DETECTION_ADDED.md    # This file
```

