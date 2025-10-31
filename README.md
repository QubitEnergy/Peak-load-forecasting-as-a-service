# Peak Load Forecasting as a Service

A proof-of-concept service for predicting peak energy consumption patterns in commercial buildings, developed in collaboration with IFE (Institute for Energy Technology).

## Overview

This service integrates multiple data sources (Datek sensors, Energinet API, and meteorological data) to forecast peak energy loads 30 minutes in advance, enabling demand response optimization and energy efficiency improvements.

## Features

- **Multi-source Data Collection**: Integrates Datek/Stromme sensors, Energinet building data, and Frost meteorological data
- **Peak Load Prediction**: ML-based forecasting with 30-minute advance warning
- **Time Interval Analysis**: Automatic detection of consumption patterns and peak periods
- **AMS Anomaly Detection**: Detects null values, negative values, and missing hours in hourly meter data
- **Modular Architecture**: Clean separation of data collection, processing, and modeling layers

## Project Structure

```
peak-load-forecasting-as-a-service/
├── src/
│   ├── data_collectors/      # API clients for external data sources
│   │   ├── stromme_client.py
│   │   └── energinet_client.py
│   ├── data_processors/       # Data cleaning and preprocessing
│   │   ├── preprocessor.py
│   │   ├── temperature_merger.py
│   │   └── anomaly_detector.py
│   ├── models/                # ML models
│   │   └── peak_predictor.py
│   └── utils/                 # Utilities and configuration
│       ├── config.py
│       └── variability.py
├── config/                    # Configuration files
│   └── config.example.yaml
├── data/                      # Data directories
│   ├── raw/                   # Original data files
│   ├── processed/             # Cleaned data
│   └── outputs/               # Generated plots and reports
├── notebooks/                 # Jupyter notebooks for exploration
│   ├── exploration/
│   └── poc/
├── tests/                     # Unit tests
├── docs/                      # Documentation
│   └── references/            # Research papers and PDFs
├── requirements.txt
└── README.md
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip or conda package manager

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Peak-load-forecasting-as-a-service
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure credentials**:
   ```bash
   # Copy example config
   cp config/config.example.yaml config/config.yaml
   
   # Edit config.yaml with your API credentials
   # OR set environment variables:
   export STROMME_BASIC_AUTH_TOKEN="your_token"
   export ENERGINET_BEARER_TOKEN="your_token"
   export FROST_CLIENT_ID="your_client_id"
   ```

## Quick Start

### 1. Collect Data

**Using Stromme API (Datek sensors)**:
```python
from src.data_collectors import StrommeClient

client = StrommeClient(debug=True)

# Get hourly historical data
meters = [
    {"id": "Jfmwhk2e", "name": "Fellesanlegg Main"},
    {"id": "KGdRbnJc", "name": "Fellesanlegg Pole"}
]

# Export hourly data
client.export_hourly_data(
    meters=meters,
    start_date="2024-01-25T00:00:00Z",
    output_path="data/raw/hourly_data.csv"
)

# Export minute-level data
client.export_minute_data(
    meters=meters,
    start_date_str="2025-02-07T00:00:00Z",
    output_path="data/raw/minute_data.csv"
)
```

**Using Energinet API**:
```python
from src.data_collectors import EnerginetClient

client = EnerginetClient(debug=True)

# Get all subunits for a building
units = client.get_subunits("23903building")  # Ski Storsenter
units_df = client.flatten_units(units)

# Fetch energy data for a specific unit
energy_df = client.fetch_energy_data(
    energy_link=units_df.iloc[0]["Energy Link"],
    date_from="2024-01-01",
    date_to="2025-01-01"
)
```

### 2. Preprocess Data

```python
from src.data_processors import DataPreprocessor

preprocessor = DataPreprocessor()

# Clean and standardize meter data
df_clean = preprocessor.process_file(
    input_file="data/raw/all_minute_data.csv",
    output_file="data/processed/cleaned_data.csv",
    sep=";"
)
```

### 3. Merge with Temperature Data

```python
from src.data_processors import TemperatureMerger

merger = TemperatureMerger()

# Fetch temperature data
temp_df = merger.get_historical_temperature(
    station_id="SN17820",  # E6 Nøstvet
    start_time="2025-02-07T00:00:00Z",
    end_time="2025-03-15T00:00:00Z"
)

# Merge with energy data
merged_df = merger.merge_energy_temperature(
    energy_df=energy_df,
    temp_df=temp_df
)

merged_df.to_csv("data/processed/energy_and_temperature.csv", index=False)
```

### 4. Run Anomaly Detection (AMS Data Quality Check)

**Action point from IFE meeting**: "Lage skript for anomaly detection (sjekke null- og minustimer i AMS-data)"

```python
from src.data_processors import AMSAnomalyDetector
import pandas as pd

# Load hourly AMS data (or aggregate minute data to hourly)
df = pd.read_csv("data/processed/energy_and_temperature.csv", sep=";")
df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], utc=True)

# If data is minute-level, aggregate to hourly first
df['timestamp_hour'] = df['timestamp_utc'].dt.floor('H')
df_hourly = df.groupby(['timestamp_hour', 'meter_id']).agg({
    'active_power_W': 'mean',
    'air_temperature': 'mean'
}).reset_index()
df_hourly.rename(columns={'timestamp_hour': 'timestamp_utc'}, inplace=True)

# Initialize detector
detector = AMSAnomalyDetector(
    timestamp_col="timestamp_utc",
    power_col="active_power_W",
    meter_id_col="meter_id"
)

# Generate comprehensive report
detector.print_report(df_hourly, output_file="data/outputs/anomaly_report.txt")

# Generate visualization plots
detector.plot_anomalies(df_hourly, output_dir="data/outputs/anomaly_plots")

# Get summary statistics
summary = detector.get_summary(df_hourly)
print(f"Null values: {summary['null_values']} ({summary['null_percentage']:.2f}%)")
print(f"Negative values: {summary['negative_values']} ({summary['negative_percentage']:.2f}%)")
print(f"Missing hours: {summary['missing_hours']} ({summary['missing_hours_percentage']:.2f}%)")
```

**Or use the example script**:
```bash
python examples/anomaly_detection_example.py
```

### 5. Train Prediction Model

```python
from src.models import PowerPeakPredictor
import pandas as pd

# Load data
df = pd.read_csv("data/processed/energy_and_temperature.csv")
df['time'] = pd.to_datetime(df['time'])

# Initialize and train
predictor = PowerPeakPredictor()
predictor.fit(df, meter_id='KGdRbnJc')
```

### 6. Make Predictions

```python
# Get current and historical data
current_data = df[df['meter_id'] == 'KGdRbnJc'].tail(1)
lookback_data = df[df['meter_id'] == 'KGdRbnJc']

# Predict peaks
predictions = predictor.predict_peaks(current_data, lookback_data)

print("Peak Predictions:")
for interval, pred in predictions.items():
    print(f"{interval}: {pred['total_predicted_peak']:.2f} kW at hour {pred['predicted_hour']:.1f}")
    print(f"  Minutes until peak: {pred['minutes_until_peak']}")

# Visualize
predictor.visualize_prediction(df, predictions, meter_id='KGdRbnJc')
```

## Configuration

Configuration is managed through `config/config.yaml` or environment variables:

### YAML Configuration

See `config/config.example.yaml` for the full template.

Key settings:
- **API Credentials**: Stromme, Energinet, and Frost API tokens
- **Data Collection**: Meter IDs, chunk sizes, SSL verification
- **Paths**: Data directories and output locations

### Environment Variables

You can override YAML settings with environment variables:
- `STROMME_BASIC_AUTH_TOKEN`: Stromme API authentication token
- `ENERGINET_BEARER_TOKEN`: Energinet API bearer token
- `FROST_CLIENT_ID`: Frost API client ID
- `FROST_CLIENT_SECRET`: Frost API client secret (optional)

## Usage Examples

### Complete Pipeline

```python
from src.data_collectors import StrommeClient, EnerginetClient
from src.data_processors import DataPreprocessor, TemperatureMerger
from src.models import PowerPeakPredictor
import pandas as pd

# 1. Collect data
stromme = StrommeClient()
meters = [{"id": "KGdRbnJc", "name": "Fellesanlegg Pole"}]
stromme.export_hourly_data(meters, "2024-01-25T00:00:00Z", "data/raw/hourly.csv")

# 2. Preprocess
preprocessor = DataPreprocessor()
df = preprocessor.process_file("data/raw/hourly.csv", "data/processed/clean.csv")

# 3. Add temperature
merger = TemperatureMerger()
temp_df = merger.get_historical_temperature("SN17820", "2024-01-25T00:00:00Z", "2025-01-25T00:00:00Z")
df_merged = merger.merge_energy_temperature(df, temp_df)

# 4. Train and predict
predictor = PowerPeakPredictor()
predictor.fit(df_merged, meter_id='KGdRbnJc')

current = df_merged.tail(1)
predictions = predictor.predict_peaks(current, df_merged)
```

### Real-time Monitoring

For real-time monitoring, see the example in `notebooks/exploration/` or adapt the `StrommeClient` for continuous data collection.

## Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_collectors.py
```

### Code Style

This project follows PEP 8 style guidelines. Use black or flake8 for formatting.

### Adding New Data Sources

To add a new data source:

1. Create a new client in `src/data_collectors/`
2. Inherit common patterns from existing clients
3. Use the `Config` class for credentials
4. Add tests in `tests/test_collectors.py`

## Troubleshooting

### Common Issues

**Authentication Errors**:
- Verify credentials in `config/config.yaml` or environment variables
- Check token expiration (tokens may need refresh)
- Ensure API endpoints are accessible

**Missing Dependencies**:
```bash
pip install -r requirements.txt --upgrade
```

**Import Errors**:
```bash
# Ensure you're in the project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Data Format Issues**:
- Verify CSV separators (some files use `;` instead of `,`)
- Check datetime format consistency
- Ensure required columns are present

## Project Status

This is a **proof-of-concept** research project. The codebase has been modularized from initial exploratory work:

✅ **Completed**:
- Modular structure with separated concerns
- Unified API clients (Stromme, Energinet)
- Data preprocessing pipeline
- Peak prediction model with feature engineering
- Configuration management
- Documentation

⚠️ **In Progress**:
- Comprehensive test suite
- Production deployment configuration
- API rate limiting and error handling
- Advanced feature engineering

## Contributing

This is a research project in collaboration with IFE. For contributions or questions, please contact the development team.

## License

[Specify license if applicable]

## References

- Research papers and documentation in `docs/references/`
- API documentation:
  - [Stromme API](https://api.stromme.io)
  - [Energinet API](https://www.energinet.net/api)
  - [Frost API](https://frost.met.no)

## Acknowledgments

Developed in cooperation with **IFE (Institute for Energy Technology)** as part of preliminary research to explore commercial opportunities in energy data analytics.

---

**Note**: This codebase was refactored from initial exploratory work. See `CODEBASE_ANALYSIS_REPORT.md` for detailed analysis of the modularization process.
