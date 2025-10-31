# Code Organization - What Stayed, What Moved, and Why

## The Confusion Explained

You're right to be confused! Here's what happened:

### What I Did

1. **Created NEW modular code** in `src/` - This replaces the old scattered scripts
2. **Moved OLD Python scripts** to `archive/old_code/` - These were redundant iterations
3. **LEFT data files where they are** - The old directories still have your data!

### Current Situation

```
Your Repository:
├── src/                           ← NEW code (use this!)
│   ├── data_collectors/          ← Unified API clients
│   ├── data_processors/          ← Unified preprocessing
│   └── models/                   ← Fixed prediction model
│
├── Datek_sensor_data/            ← OLD directory (KEEP - has your data!)
│   ├── energy_and_temperature.csv ← ✅ Your processed data (ready to use!)
│   ├── all_minute_data.csv       ← ✅ Your raw minute data
│   └── [lots of PNG plots]       ← Generated outputs (can organize later)
│
├── Energinet/                    ← OLD directory (KEEP - has your data!)
│   ├── units.csv                 ← ✅ Your meter configuration
│   ├── *.csv files               ← ✅ Your Energinet data
│   └── [PDFs]                    ← Documentation (can move to docs/)
│
├── Model_development/            ← OLD directory (KEEP - has your data!)
│   ├── energy_and_temperature.csv ← ✅ Your processed data (ready to use!)
│   ├── *.ipynb                   ← ✅ Your research notebooks
│   └── *.pdf                     ← Research papers (can move to docs/)
│
└── archive/old_code/             ← OLD Python scripts (reference only)
    └── [12 old .py files]        ← Don't use these, use src/ instead
```

## What Should Stay vs. What Can Move

### ✅ KEEP These Directories (They Have Your Data!)

**Datek_sensor_data/**
- ✅ Keep: `energy_and_temperature.csv` - Ready-to-use processed data
- ✅ Keep: `all_minute_data.csv` - Raw data
- ✅ Keep: All CSV files - Your actual data
- ⚠️ Can organize later: PNG plots (generated outputs)

**Energinet/**
- ✅ Keep: `units.csv` - Meter configuration
- ✅ Keep: All CSV files - Your Energinet data
- ⚠️ Can move: PDFs → `docs/references/`

**Model_development/**
- ✅ Keep: `energy_and_temperature.csv` - Ready-to-use processed data
- ✅ Keep: `*.ipynb` notebooks - Your research work
- ⚠️ Can move: PDFs → `docs/references/`
- ⚠️ Can move: Notebooks → `notebooks/poc/`

### ❌ Already Moved (Don't Need)

**archive/old_code/**
- Old Python scripts - Don't use these anymore
- Use the new `src/` modules instead

## How It All Works Together

### The Old Way (Before Refactoring):
```
Datek_sensor_data/
├── datek.py                    ← Collected data
├── data_wrangling.py           ← Processed data
└── energy_and_temperature.csv  ← Final output

Model_development/
├── power_prediction_system.py  ← Trained model
└── energy_and_temperature.csv  ← Input data
```

### The New Way (After Refactoring):
```
src/
├── data_collectors/stromme_client.py    ← NEW unified collector
├── data_processors/preprocessor.py      ← NEW unified preprocessor
└── models/peak_predictor.py             ← NEW fixed model

Datek_sensor_data/
└── energy_and_temperature.csv           ← SAME data file (still works!)

Model_development/
└── energy_and_temperature.csv           ← SAME data file (still works!)
```

## How to Use Your Existing Data

The new code in `src/` can **directly use** your existing data files:

```python
# Your existing data files still work!
from src.models import PowerPeakPredictor
import pandas as pd

# Use data from OLD directory - it still works!
df = pd.read_csv("Datek_sensor_data/energy_and_temperature.csv")
# OR
df = pd.read_csv("Model_development/energy_and_temperature.csv")

# Use NEW code to process it
predictor = PowerPeakPredictor()
predictor.fit(df, meter_id='KGdRbnJc')
```

**The data files haven't changed** - only the code that processes them is new!

## Recommended Organization (Optional)

You could optionally organize better, but **it's not required**:

```
data/
├── raw/
│   ├── datek_all_minute_data.csv      ← Move from Datek_sensor_data/
│   └── energinet_*.csv                ← Move from Energinet/
│
├── processed/
│   └── energy_and_temperature.csv     ← Move from Datek_sensor_data/ or Model_development/
│
└── outputs/
    └── plots/                          ← Move PNGs from Datek_sensor_data/

docs/
└── references/
    └── *.pdf                           ← Move PDFs from Model_development/ and Energinet/

notebooks/
└── poc/
    └── *.ipynb                         ← Move from Model_development/
```

**But this is optional!** Your current structure works fine.

## Summary

### What Happened:
- ✅ **Old Python scripts** → Moved to `archive/old_code/` (don't use)
- ✅ **New Python code** → Created in `src/` (use this!)
- ✅ **Your data files** → Stayed in original locations (still work!)

### What You Need to Know:
1. **Use `src/` code** - It's the new, improved version
2. **Your existing data files work** - They're in `Datek_sensor_data/`, `Energinet/`, `Model_development/`
3. **Old directories are fine** - They contain your data, keep them!
4. **Only Python scripts moved** - Data, CSVs, notebooks, PDFs all stayed

### To Run:
```python
# Load your existing data (from old directory - that's fine!)
df = pd.read_csv("Datek_sensor_data/energy_and_temperature.csv")

# Use new code (from src/)
from src.models import PowerPeakPredictor
predictor = PowerPeakPredictor()
predictor.fit(df)
```

**Bottom line**: The old directories with your data are fine. The new `src/` code works with that existing data. You didn't lose anything!

