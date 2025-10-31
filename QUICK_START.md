# Quick Start Guide

## Minimal Setup to Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure (Only if collecting NEW data from APIs)
```bash
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your API credentials
```

**Note**: If you're using existing data files, you can skip this step!

### 3. Run with Your Existing Data

You already have processed data ready! Use this:

```python
import pandas as pd
from src.models import PowerPeakPredictor

# Load your existing data (already processed!)
df = pd.read_csv("Model_development/energy_and_temperature.csv")
# OR
# df = pd.read_csv("Datek_sensor_data/energy_and_temperature.csv")

# Ensure time is datetime
df['time'] = pd.to_datetime(df['time'])

# Train model
predictor = PowerPeakPredictor()
predictor.fit(df, meter_id='KGdRbnJc')  # or 'Jfmwhk2e', '6kPJw9QF'

# Make predictions
current = df[df['meter_id'] == 'KGdRbnJc'].tail(1)
lookback = df[df['meter_id'] == 'KGdRbnJc']
predictions = predictor.predict_peaks(current, lookback)

# Print results
for interval, pred in predictions.items():
    print(f"{interval}: {pred['total_predicted_peak']:.2f} kW")
    print(f"  Peak at hour {pred['predicted_hour']:.1f}")
    print(f"  In {pred['minutes_until_peak']} minutes")
```

## What Files Do You Actually Need?

### ✅ Essential (to run):
- `src/` directory (12 Python files)
- `requirements.txt`
- Your `energy_and_temperature.csv` file (you already have it!)

### ⚠️ Optional (for collecting NEW data):
- `config/config.yaml` (only needed for API access)

### 📚 Helpful but not required:
- `README.md` - Usage documentation
- Other `*.md` files - Analysis reports
- `notebooks/` - Exploration scripts
- `archive/` - Old code reference

## Your Data Files

You have **2 locations** with ready-to-use data:
1. `Datek_sensor_data/energy_and_temperature.csv` (99KB)
2. `Model_development/energy_and_temperature.csv` (99KB)

Both are identical and ready for modeling - just pick one!

## Data Processing Flow

**Option 1: Use Existing Data (Simplest)**
```
energy_and_temperature.csv → Load → Train → Predict
```

**Option 2: Process Raw Data**
```
Raw CSV → Preprocessor → TemperatureMerger → Train → Predict
```

Since you already have `energy_and_temperature.csv`, use Option 1!

## Summary

**To run the system, you only need:**
1. ✅ `src/` - Code (already created)
2. ✅ `requirements.txt` - Dependencies (already created)
3. ✅ `energy_and_temperature.csv` - Data (you already have it!)

**That's it!** Everything else is optional documentation or for advanced use cases.

