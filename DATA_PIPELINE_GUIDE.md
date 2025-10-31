# Data Pipeline Guide

## Where Is Your Data?

### Existing Data Files (Already Collected)

You have data files in the old directory structure:

**Datek Sensor Data:**
- `Datek_sensor_data/all_minute_data.csv` (11MB) - Raw minute-level data
- `Datek_sensor_data/energy_and_temperature.csv` (99KB) - Hourly data with temperature (ready for modeling)
- `Datek_sensor_data/processed_minute_data_datek_API.csv` (10MB) - Processed minute data
- `Datek_sensor_data/temperature_history.csv` (36KB) - Temperature data only

**Model Development Data:**
- `Model_development/energy_and_temperature.csv` (99KB) - Same as above (ready for modeling)
- `Model_development/energy_and_temperature_minute_data.csv` (12MB) - Minute-level with temperature

### Data Format

**Current format** (`energy_and_temperature.csv`):
```
startTime, endTime, duration, startMeasureImport, endMeasureImport, 
startMeasureExport, endMeasureExport, import, export, meter_id, time, air_temperature
```

**Model expects:**
- `time` (datetime) - Timestamp
- `import` (float) - Energy consumption in kWh
- `meter_id` (string) - Meter identifier
- `air_temperature` (float, optional) - Temperature for better predictions

## Data Processing Pipeline

The data flows through these stages:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. DATA COLLECTION (Optional - if collecting fresh data)    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Option A: Collect from APIs                                │
│  ├─ StrommeClient → Hourly/Minute data                      │
│  └─ EnerginetClient → Building energy data                  │
│                                                              │
│  Option B: Use existing CSV files (skip to step 2)          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. PREPROCESSING (DataPreprocessor)                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input: Raw CSV from API or existing file                   │
│  Process:                                                    │
│    - Select relevant columns                                │
│    - Rename columns (e.g., "a" → "active_power_W")         │
│    - Convert timestamps to datetime                         │
│    - Sort by meter_id and time                              │
│                                                              │
│  Output: Cleaned DataFrame with standardized columns        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. TEMPERATURE MERGING (TemperatureMerger)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input: Cleaned energy data                                 │
│  Process:                                                    │
│    - Fetch temperature from Frost API (or use existing)     │
│    - Merge using backward fill (asof merge)                 │
│    - Match each energy reading with nearest temperature     │
│                                                              │
│  Output: Energy data + temperature column                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. MODEL TRAINING (PowerPeakPredictor)                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input: energy_and_temperature.csv                          │
│  Process:                                                    │
│    - Extract time intervals (peak/valley detection)         │
│    - Separate base load vs peak load                        │
│    - Create features (lag features, intervals)              │
│    - Train ML models (amount + timing prediction)           │
│                                                              │
│  Output: Trained model ready for predictions                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. PREDICTION                                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input: Current data + historical data                      │
│  Process:                                                    │
│    - Generate features for current time                     │
│    - Predict peak amount and timing                         │
│                                                              │
│  Output: Predictions dict with peak forecasts               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## How to Use Your Existing Data

Since you already have `energy_and_temperature.csv`, you can **skip steps 1-3** and go straight to modeling:

```python
import pandas as pd
from src.models import PowerPeakPredictor

# Use your existing data (either location works)
df = pd.read_csv("Datek_sensor_data/energy_and_temperature.csv")
# OR
# df = pd.read_csv("Model_development/energy_and_temperature.csv")

# Ensure time column is datetime
df['time'] = pd.to_datetime(df['time'])

# Train the model
predictor = PowerPeakPredictor()
predictor.fit(df, meter_id='KGdRbnJc')  # or 'Jfmwhk2e', '6kPJw9QF'

# Make predictions
current_data = df[df['meter_id'] == 'KGdRbnJc'].tail(1)
lookback_data = df[df['meter_id'] == 'KGdRbnJc']
predictions = predictor.predict_peaks(current_data, lookback_data)
```

## How to Collect Fresh Data

If you want to collect new data from the APIs:

```python
from src.data_collectors import StrommeClient
from src.data_processors import DataPreprocessor, TemperatureMerger

# 1. Collect data
client = StrommeClient()
meters = [{"id": "KGdRbnJc", "name": "Fellesanlegg Pole"}]

# Collect hourly data
client.export_hourly_data(
    meters=meters,
    start_date="2024-01-25T00:00:00Z",
    output_path="data/raw/hourly_data.csv"
)

# 2. Preprocess
preprocessor = DataPreprocessor()
df_clean = preprocessor.process_file(
    input_file="data/raw/hourly_data.csv",
    output_file="data/processed/cleaned_data.csv",
    sep=","
)

# 3. Add temperature
merger = TemperatureMerger()
temp_df = merger.get_historical_temperature(
    station_id="SN17820",
    start_time="2024-01-25T00:00:00Z",
    end_time="2025-01-25T00:00:00Z"
)

df_merged = merger.merge_energy_temperature(df_clean, temp_df)
df_merged.to_csv("data/processed/energy_and_temperature.csv", index=False)

# 4. Train model (as above)
```

## Data Format Requirements

### For Model Training (minimum required):
- `time` - datetime column
- `import` - energy consumption values
- `meter_id` - meter identifier

### For Better Predictions (optional but recommended):
- `air_temperature` - temperature data

### Your Existing Data
Your `energy_and_temperature.csv` files already have all required columns:
- ✅ `time` column
- ✅ `import` column (energy consumption)
- ✅ `meter_id` column
- ✅ `air_temperature` column

**You can use them directly without preprocessing!**

## Quick Start with Existing Data

```python
# Simplest path: use existing processed data
import pandas as pd
from src.models import PowerPeakPredictor

# Load your existing data
df = pd.read_csv("Model_development/energy_and_temperature.csv")
df['time'] = pd.to_datetime(df['time'])

# Train and predict
predictor = PowerPeakPredictor()
predictor.fit(df, meter_id='KGdRbnJc')

current = df[df['meter_id'] == 'KGdRbnJc'].tail(1)
predictions = predictor.predict_peaks(current, df[df['meter_id'] == 'KGdRbnJc'])

print(predictions)
```

## Summary

**To run the system, you need:**

1. **Source code** (`src/` directory) - ✅ Already created
2. **Dependencies** (`requirements.txt`) - ✅ Already created
3. **Configuration** (`config/config.yaml`) - ⚠️ You need to create from template
4. **Data** - ✅ You already have `energy_and_temperature.csv` ready to use!

**Files you actually need:**
- `src/` - All the code
- `requirements.txt` - Dependencies
- `config/config.example.yaml` → copy to `config/config.yaml` and add credentials
- Your existing `energy_and_temperature.csv` file (already in correct format!)

**Optional files:**
- Documentation (README, reports) - helpful but not required to run
- Notebooks - for exploration/analysis
- Archive - old code reference

You can start training models immediately with your existing `energy_and_temperature.csv` files!

