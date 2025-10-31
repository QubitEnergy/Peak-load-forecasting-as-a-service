# Directory Purpose Guide

## What Each Directory Is For

### ✅ src/ (NEW - Use This!)
**Purpose**: Production-ready modular code
- `src/data_collectors/` - API clients (replaces old datek.py, energinet*.py)
- `src/data_processors/` - Data preprocessing (replaces old data_wrangling*.py)
- `src/models/` - ML models (replaces old power_prediction_system.py)
- `src/utils/` - Utilities and config

**Status**: ✅ Use this code!

---

### ✅ Datek_sensor_data/ (KEEP - Has Your Data!)
**Purpose**: Contains your collected Datek sensor data
- ✅ **Keep**: All CSV files (your data!)
  - `energy_and_temperature.csv` - Ready to use for modeling
  - `all_minute_data.csv` - Raw minute-level data
  - `processed_minute_data_datek_API.csv` - Processed data
- ✅ **Keep**: Configuration/data files
- ⚠️ Can organize later: PNG plots (generated outputs, 50+ files)

**Note**: These are **data files**, not code. They stay here.

---

### ✅ Energinet/ (KEEP - Has Your Data!)
**Purpose**: Contains your Energinet API data
- ✅ **Keep**: All CSV files (your data!)
  - `units.csv` - Meter configuration (still useful)
  - `*.csv` - Your Energinet energy data
- ⚠️ Can move: PDFs → `docs/references/`

**Note**: These are **data files**, not code. They stay here.

---

### ✅ Model_development/ (KEEP - Has Your Data & Research!)
**Purpose**: Contains processed data and research notebooks
- ✅ **Keep**: CSV files
  - `energy_and_temperature.csv` - Ready to use for modeling
  - `energy_and_temperature_minute_data.csv` - Minute-level data
- ✅ **Keep**: Jupyter notebooks (your research work)
  - `PoC_v2.ipynb`
  - `power_peak_forecasting_PoC.ipynb`
- ⚠️ Can move: PDFs → `docs/references/`

**Note**: Contains your **processed data and research artifacts**.

---

### 📦 archive/old_code/ (Reference Only)
**Purpose**: Old redundant Python scripts (for reference)
- ❌ **Don't use**: These are old, buggy versions
- ✅ **Reference only**: If you need to see how something was done before

**Contains**:
- Old `datek.py`, `energinet*.py` scripts (replaced by `src/data_collectors/`)
- Old `data_wrangling*.py` scripts (replaced by `src/data_processors/`)
- Old `power_prediction_system.py` (replaced by `src/models/peak_predictor.py`)

---

### 📚 notebooks/exploration/ (Analysis Scripts)
**Purpose**: One-off analysis and exploration scripts
- Moved here from old directories
- For exploration, not production code

---

## Data Flow: Old vs New

### How Data Was Processed Before:
```
1. datek.py (old script) 
   → Collected data 
   → Saved to Datek_sensor_data/all_minute_data.csv

2. data_wrangling.py (old script)
   → Read all_minute_data.csv
   → Processed it
   → Saved to energy_and_temperature.csv

3. power_prediction_system.py (old script)
   → Read energy_and_temperature.csv
   → Trained model (with bugs!)
```

### How Data Is Processed Now:
```
1. src/data_collectors/stromme_client.py (new code)
   → Collect data (same functionality, better code)
   → Save to data/raw/ (or wherever you want)

2. src/data_processors/preprocessor.py (new code)
   → Process raw data (same functionality, unified)
   → Save to data/processed/

3. src/models/peak_predictor.py (new code - FIXED!)
   → Read processed data
   → Train model (bugs fixed!)
```

### BUT - You Can Skip Steps 1-2!

**Since you already have `energy_and_temperature.csv`, you can go straight to step 3:**

```python
# Use your existing processed data
df = pd.read_csv("Datek_sensor_data/energy_and_temperature.csv")
# OR
df = pd.read_csv("Model_development/energy_and_temperature.csv")

# Use new code to train
from src.models import PowerPeakPredictor
predictor = PowerPeakPredictor()
predictor.fit(df, meter_id='KGdRbnJc')
```

## What Should You Do?

### ✅ Keep As-Is (Recommended):
- `Datek_sensor_data/` - Your data files
- `Energinet/` - Your data files  
- `Model_development/` - Your data and notebooks

### ✅ Use New Code:
- `src/` - All new modules

### ❌ Don't Use:
- `archive/old_code/` - Old buggy scripts

### ⚠️ Optional Organization (Later):
You could organize data files into `data/` directories, but it's not necessary:
- Move CSVs to `data/processed/` or `data/raw/`
- Move PDFs to `docs/references/`
- Move notebooks to `notebooks/poc/`

**But this is optional!** Current structure works fine.

## Summary

| Directory | Purpose | Keep? | Contains |
|-----------|---------|-------|----------|
| `src/` | New modular code | ✅ Use | Python modules |
| `Datek_sensor_data/` | Your sensor data | ✅ Keep | CSV files, plots |
| `Energinet/` | Your Energinet data | ✅ Keep | CSV files, configs |
| `Model_development/` | Processed data & research | ✅ Keep | CSVs, notebooks, PDFs |
| `archive/old_code/` | Old scripts | ❌ Reference only | Old Python files |

**The key point**: Data files stayed where they are. Only Python scripts were moved/consolidated.

