# Peak Load Forecasting as a Service
## Codebase Analysis & Modularization Report

**Project Context**: Preliminary Research Project in cooperation with IFE (Institute for Energy Technology)  
**Objective**: Development of a proof-of-concept service for peak load forecasting to identify potential startup opportunities  
**Focus Domain**: Energy meter data from shopping malls and commercial buildings  
**Date**: 2025

---

## Executive Summary

This report provides a comprehensive analysis of the peak load forecasting codebase developed as part of a preliminary research collaboration with IFE. The codebase contains multiple iterations of data collection, processing, and modeling scripts resulting from exploratory development. This document maps redundancies, identifies core functionality, and proposes a modular structure to transform the research artifacts into a maintainable, production-ready service.

**Key Findings:**
- **7 distinct data collection scripts** with significant overlap (Datek/Stromme API: 2 variants; Energinet API: 5 variants)
- **2 duplicate preprocessing pipelines** for minute-level data
- **1 incomplete model implementation** with missing critical methods
- **Multiple analysis/visualization scripts** that should be in notebooks rather than source code
- **Hardcoded credentials** scattered across 8+ files (security risk)
- **Generated artifacts** (plots, CSVs) mixed with source code

**Recommendation**: Consolidate into a clean modular structure separating data collection, processing, modeling, and analysis layers.

---

## 1. Project Background

### 1.1 Research Context

This project emerged from collaboration with IFE (Institute for Energy Technology) to explore commercial opportunities in energy data analytics. The initial focus was on working with meter data from shopping malls, where understanding peak consumption patterns can provide value through:

- **Demand response optimization**: Helping commercial buildings reduce peak load charges
- **Predictive maintenance**: Identifying abnormal consumption patterns
- **Energy efficiency insights**: Providing actionable recommendations based on consumption patterns

### 1.2 Data Sources

The project integrates data from multiple sources:

1. **Datek Sensors (via Stromme API)**
   - Real-time and historical energy consumption data
   - Multiple meters: "Fellesanlegg Main", "Fellesanlegg Pole", "Cinema 500"
   - Both hourly and minute-level granularity
   - Endpoint: `https://api.stromme.io`

2. **Energinet API**
   - Building-level energy data from Norwegian energy management systems
   - Hierarchical unit structure (buildings → subunits → meters)
   - Multiple data types: Energy, Temperature, CO₂, Cost, Peak High
   - Focus on "Ski Storsenter" shopping mall
   - Endpoint: `https://www.energinet.net/api`

3. **Temperature Data (Frost API)**
   - Meteorological data from Norwegian Meteorological Institute
   - Used as exogenous feature for load forecasting
   - Station: SN17820 (E6 Nøstvet)

### 1.3 Core Functionality

The system aims to:
1. **Collect** energy meter data from multiple sources
2. **Process and merge** with temperature data
3. **Extract patterns** (time intervals, base vs. peak load)
4. **Predict peaks** 30 minutes in advance using ML models
5. **Provide insights** for demand response and optimization

---

## 2. Current Codebase Structure

### 2.1 Directory Organization

```
Peak-load-forecasting-as-a-service/
├── Datek_sensor_data/          # Datek/Stromme API integration
├── Energinet/                   # Energinet API integration  
├── Model_development/           # ML models and notebooks
└── README.md                    # Minimal documentation
```

### 2.2 File Inventory

**Datek/Stromme API Scripts:**
- `datek.py` - Real-time monitoring with live plots
- `datek_minute.py` - Minute-level data collection
- `data_wrangling.py` - Initial preprocessing
- `data_wrangling_2.py` - Duplicate preprocessing (refined)
- `preprocessing_minute_data.py` - Minute data preprocessing
- `minute_data_EDA.py` - Exploratory data analysis
- `minute_level_patterns.py` - Pattern extraction
- `api_test.py` - API testing/visualization

**Energinet API Scripts:**
- `energinet.py` - Basic drilldown and plotting
- `energinet2.py` - Enhanced drilldown with multiple data types
- `energinet3.py` - Further iteration
- `energinet4.py` - Most complete version
- `extract_data.py` - Data extraction utility
- `energinet_variability.py` - Variability analysis
- `energinet_variability2.py` - Enhanced variability analysis
- `top_var.py` - Top variability units analysis

**Model Development:**
- `power_prediction_system.py` - Main prediction class (incomplete)
- `power_peak_forecasting_PoC.ipynb` - Jupyter notebook PoC
- `PoC_v2.ipynb` - Enhanced notebook with D-PAD methodology

---

## 3. Redundancy Analysis

### 3.1 Data Collection Layer

#### 3.1.1 Datek/Stromme API Clients

**Files Analyzed:** `datek.py`, `datek_minute.py`

**Redundancy Level: HIGH**

Both files implement:
- Identical authentication token retrieval
- Similar API request patterns
- Overlapping data fetching methods
- Different use cases (real-time vs. batch) but same underlying API

**Evidence:**
```python
# Identical in both files:
headers = {
    'Authorization': 'Basic Nms2dm5hZ3JlaWVtOGJuMHRycTlvZzloNWI6MW1wOTZtaWlsbm80MWRlbWJxcHFjaTRrZzdxazFnb2ZzOW5xazB0ZnFsajduMTVtam84NQ==',
    'Content-Type': 'application/x-www-form-urlencoded'
}
```

**Recommendation:** Merge into single `StrommeClient` class with methods for both hourly and minute-level data collection.

#### 3.1.2 Energinet API Clients

**Files Analyzed:** `energinet.py`, `energinet2.py`, `energinet3.py`, `energinet4.py`, `extract_data.py`

**Redundancy Level: CRITICAL**

Five different scripts implementing:
- Recursive unit drilldown navigation
- Energy data fetching with date intervals
- Similar authentication (identical bearer token)
- Overlapping functionality with incremental improvements

**Evolution Pattern:**
- `energinet.py`: Basic drilldown + plotting
- `energinet2.py`: Enhanced with multiple data types
- `energinet3.py`: Further refinements
- `energinet4.py`: Most complete implementation
- `extract_data.py`: Utility for specific unit extraction

**Evidence:**
```python
# Repeated across all files:
headers = {
    "Authorization": "Bearer 78uiaschs5kobwy9p85m5w4xvks9929e",
    "Accept-Language": "no"
}
```

**Recommendation:** Keep `energinet4.py` as the reference implementation, extract reusable components, archive others.

### 3.2 Data Processing Layer

#### 3.2.1 Preprocessing Scripts

**Files Analyzed:** `data_wrangling.py`, `data_wrangling_2.py`, `preprocessing_minute_data.py`

**Redundancy Level: HIGH**

All three perform:
- Column selection and renaming
- Timestamp conversion
- Data sorting
- CSV export

**Evidence:**
```python
# data_wrangling_2.py and preprocessing_minute_data.py:
desired_cols = ["time", "a", "an", "rp", "rn", "i1", "i2", "i3", "u1", "u2", "u3", "meter_id"]
rename_map = {"time": "timestamp_utc", "a": "active_power_W", ...}
```

**Recommendation:** Consolidate into single `Preprocessor` class with configurable column mappings.

#### 3.2.2 Temperature Data Merging

**Files Analyzed:** `data_wrangling.py` (partial), temperature merge logic in notebooks

**Redundancy Level: MEDIUM**

Temperature merging logic scattered across:
- Standalone scripts
- Notebook cells
- Inline processing in analysis scripts

**Recommendation:** Centralize temperature merging in dedicated `TemperatureMerger` class.

### 3.3 Analysis & Variability Computation

#### 3.3.1 Variability Analysis

**Files Analyzed:** `energinet_variability.py`, `energinet_variability2.py`, `top_var.py`

**Redundancy Level: MEDIUM**

Multiple implementations of:
- Rolling variability computation
- Coefficient of variation calculation
- Top units ranking

**Recommendation:** Single `VariabilityAnalyzer` utility class.

### 3.4 Modeling Layer

#### 3.4.1 Prediction System

**File Analyzed:** `power_prediction_system.py`

**Issues Identified:**
1. **Missing Method**: `prepare_features()` called but not implemented
2. **Syntax Error**: `ions[...]` instead of `predictions[...]` (line 450)
3. **Mixed Concerns**: Library class mixed with example usage code
4. **Infinite Loop**: Demo code with `while True` embedded in library file

**Evidence:**
```python
# Line 182, 295, 430, 511: prepare_features() called but not defined
prediction_features = self.prepare_features(...)

# Line 450: Typo
ions[f'Interval {interval_idx+1}'] = {...}  # Should be 'predictions'
```

**Recommendation:** 
- Implement missing `prepare_features()` method
- Fix syntax error
- Separate library code from examples
- Move demo code to notebook or separate script

### 3.5 Security Concerns

**Critical Issue: Hardcoded Credentials**

Credentials found in:
- `datek.py`: Stromme API Basic Auth token
- `datek_minute.py`: Same token
- `energinet.py` through `energinet4.py`: Bearer token
- `extract_data.py`: Bearer token
- `energinet_variability.py`: Bearer token
- `energinet_variability2.py`: Bearer token

**Count: 8+ instances of hardcoded credentials**

**Risk Level: HIGH** - Security vulnerability, credential exposure risk

**Recommendation:** Immediate migration to environment variables or secure configuration management.

---

## 4. Artifact Pollution

### 4.1 Generated Files Mixed with Source

**Plot Files:** 50+ PNG files scattered across source directories
- `Datek_sensor_data/`: 15+ plot files
- `Datek_sensor_data/Results_minute_data_EDA/`: 13 plot files
- `Datek_sensor_data/sensor_analysis/`: Multiple subdirectories with plots
- `Datek_sensor_data/minute_level_pattern_plots/`: 34 plot files

**Data Files:** Temporary/processed CSVs in source directories
- `all_minute_data.csv`
- `processed_minute_data_datek_API.csv`
- `energy_and_temperature.csv`
- Multiple Energinet output CSVs

**Recommendation:** Move all generated artifacts to `data/outputs/` and `data/processed/`.

### 4.2 Documentation Artifacts

**PDFs:** Research papers and documentation in code directories
- `D-PAD paper.pdf`
- `Day-Ahead_Electricity_Consumption_Prediction...pdf`
- `EnerginettDataStruktur.pdf`
- `datauthentingApi2022.pdf`
- `EDA.pdf`

**Recommendation:** Move to `docs/` or `references/` directory.

---

## 5. Proposed Modular Structure

### 5.1 Recommended Organization

```
peak_load_forecasting/
├── src/
│   ├── data_collectors/
│   │   ├── __init__.py
│   │   ├── stromme_client.py      # Consolidated Datek/Stromme client
│   │   └── energinet_client.py    # Consolidated Energinet client
│   ├── data_processors/
│   │   ├── __init__.py
│   │   ├── preprocessor.py        # Unified preprocessing
│   │   └── temperature_merger.py  # Temperature data merging
│   ├── models/
│   │   ├── __init__.py
│   │   └── peak_predictor.py      # Complete prediction system
│   └── utils/
│       ├── __init__.py
│       ├── config.py              # Configuration management
│       └── variability.py         # Variability analysis
├── config/
│   ├── config.example.yaml        # Template for credentials
│   └── meters.yaml                # Meter configurations
├── data/
│   ├── raw/                       # Original data files
│   ├── processed/                 # Cleaned/processed data
│   └── outputs/                   # Generated plots, reports
├── notebooks/
│   ├── exploration/               # EDA notebooks
│   └── poc/                       # PoC notebooks
├── tests/
│   ├── test_collectors.py
│   ├── test_processors.py
│   └── test_models.py
├── docs/
│   └── references/                # PDFs, papers
├── requirements.txt
└── README.md
```

### 5.2 Rationale for Organization

#### **Separation of Concerns**
- **Data Collectors**: Isolated API clients, easy to test and replace
- **Data Processors**: Reusable preprocessing pipelines
- **Models**: Clean ML implementation separate from data access
- **Utils**: Shared utilities without business logic dependencies

#### **Security & Configuration**
- Centralized credential management in `config/`
- Environment-based configuration (dev/test/prod)
- No hardcoded secrets in source code

#### **Artifact Management**
- Clear separation: source code vs. generated files
- Data pipeline: `raw` → `processed` → `outputs`
- Notebooks isolated from production code

#### **Maintainability**
- Single responsibility per module
- Easy to locate functionality
- Clear dependencies between layers

#### **Testability**
- Each layer independently testable
- Mock external API calls
- Isolated business logic

---

## 6. Files to Keep vs. Remove

### 6.1 Files to Consolidate and Keep

**Data Collection:**
- ✅ Keep: `datek.py` + `datek_minute.py` → Merge into `stromme_client.py`
- ✅ Keep: `energinet4.py` → Refactor into `energinet_client.py`
- ✅ Keep: `extract_data.py` → Incorporate utility functions into client

**Data Processing:**
- ✅ Keep: `preprocessing_minute_data.py` or `data_wrangling_2.py` → Merge into `preprocessor.py`
- ✅ Keep: Temperature merge logic → Extract to `temperature_merger.py`

**Models:**
- ✅ Keep: `power_prediction_system.py` → Fix and refactor into `peak_predictor.py`

**Analysis:**
- ✅ Keep: `energinet_variability2.py` → Extract to `variability.py` utility

### 6.2 Files to Archive/Remove

**Obsolete Iterations:**
- ❌ Remove: `energinet.py`, `energinet2.py`, `energinet3.py` (superseded by `energinet4.py`)
- ❌ Remove: `data_wrangling.py` (superseded by `data_wrangling_2.py`)
- ❌ Remove: `energinet_variability.py` (superseded by `energinet_variability2.py`)

**One-off Scripts:**
- ❌ Move to notebooks: `api_test.py`, `minute_data_EDA.py`, `top_var.py`
- ❌ Move to notebooks: `minute_level_patterns.py`

**Configuration/Reference:**
- ✅ Move to `docs/references/`: All PDF files
- ✅ Move to `config/`: `units.csv` (with sanitization)

### 6.3 Generated Artifacts to Reorganize

- 📁 Move all `.png` files to `data/outputs/plots/`
- 📁 Move processed CSVs to `data/processed/`
- 📁 Move raw CSVs to `data/raw/` (if not regeneratable)

---

## 7. Critical Issues Requiring Immediate Attention

### 7.1 Code Issues

1. **Missing Implementation** (Blocking)
   - `prepare_features()` method not implemented in `PowerPeakPredictor`
   - **Impact**: Training and prediction pipeline will fail
   - **Fix Required**: Implement feature engineering logic

2. **Syntax Error** (Blocking)
   - Line 450: `ions[...]` should be `predictions[...]`
   - **Impact**: Runtime error in fallback prediction path
   - **Fix Required**: Correct variable name

3. **Mixed Concerns** (Code Quality)
   - Library class contains example usage code
   - **Impact**: Difficult to import and use as library
   - **Fix Required**: Separate library from examples

### 7.2 Security Issues

1. **Hardcoded Credentials** (Critical)
   - 8+ instances across codebase
   - **Impact**: Security vulnerability, credential exposure
   - **Fix Required**: Migrate to environment variables immediately

2. **Token in Version Control** (Critical)
   - Credentials may be in git history
   - **Impact**: Permanent security risk
   - **Fix Required**: Rotate all tokens, implement `.gitignore` for secrets

### 7.3 Architecture Issues

1. **No Configuration Management**
   - Settings scattered throughout code
   - **Impact**: Difficult to manage different environments
   - **Fix Required**: Centralized configuration system

2. **Tight Coupling**
   - API clients, processors, and models mixed together
   - **Impact**: Difficult to test and maintain
   - **Fix Required**: Modular separation

---

## 8. Recommendations Summary

### 8.1 Immediate Actions (Priority 1)

1. ✅ **Fix Critical Bugs**
   - Implement `prepare_features()` method
   - Fix `ions` → `predictions` typo
   - Verify prediction pipeline works end-to-end

2. ✅ **Security Remediation**
   - Extract all credentials to environment variables
   - Rotate API tokens (assume exposure)
   - Add `.env` to `.gitignore`
   - Create `config.example.yaml` template

3. ✅ **Document Core Functionality**
   - Document data collection APIs
   - Document prediction model interface
   - Create usage examples

### 8.2 Short-term Refactoring (Priority 2)

1. ✅ **Consolidate Data Collectors**
   - Merge Datek scripts into single client
   - Merge Energinet scripts (keep best version)
   - Extract common authentication logic

2. ✅ **Unify Preprocessing**
   - Single preprocessing pipeline
   - Configurable column mappings
   - Temperature merge as separate utility

3. ✅ **Separate Library from Examples**
   - Clean library interfaces
   - Move example code to notebooks
   - Create simple CLI or example scripts

### 8.3 Medium-term Improvements (Priority 3)

1. ✅ **Implement Modular Structure**
   - Create `src/` package structure
   - Separate layers (collectors, processors, models)
   - Add `__init__.py` files and proper imports

2. ✅ **Artifact Organization**
   - Move generated files to `data/outputs/`
   - Move references to `docs/`
   - Clean up source directories

3. ✅ **Testing Infrastructure**
   - Unit tests for collectors
   - Unit tests for processors
   - Integration tests for prediction pipeline

4. ✅ **Documentation**
   - API documentation
   - Installation guide
   - Usage examples
   - Architecture overview

---

## 9. Conclusion

This codebase represents valuable exploratory work in peak load forecasting for commercial buildings. The iterative development process, while productive for research, has resulted in significant redundancy and technical debt. The analysis reveals:

- **7 redundant data collection scripts** that should be 2 unified clients
- **3 preprocessing pipelines** that should be 1 configurable processor
- **Critical bugs** preventing the model from functioning
- **Security vulnerabilities** from hardcoded credentials
- **Mixed concerns** making the codebase difficult to maintain

The proposed modular structure addresses these issues by:
- **Separating concerns** into clear layers
- **Consolidating functionality** into reusable components
- **Improving security** through proper configuration management
- **Enabling testing** through isolated, testable modules
- **Facilitating maintenance** through clear organization

With these improvements, the codebase can transition from a research prototype to a maintainable, production-ready service that supports the startup opportunity exploration with IFE.

---

## Appendix A: Detailed File Mapping

| Current File | Status | Destination | Notes |
|-------------|--------|-------------|-------|
| `Datek_sensor_data/datek.py` | Merge | `src/data_collectors/stromme_client.py` | Combine with datek_minute.py |
| `Datek_sensor_data/datek_minute.py` | Merge | `src/data_collectors/stromme_client.py` | Combine with datek.py |
| `Datek_sensor_data/data_wrangling.py` | Remove | - | Superseded by data_wrangling_2.py |
| `Datek_sensor_data/data_wrangling_2.py` | Keep | `src/data_processors/preprocessor.py` | Refactor into class |
| `Datek_sensor_data/preprocessing_minute_data.py` | Merge | `src/data_processors/preprocessor.py` | Merge with data_wrangling_2.py |
| `Datek_sensor_data/api_test.py` | Move | `notebooks/exploration/api_test.ipynb` | Convert to notebook |
| `Datek_sensor_data/minute_data_EDA.py` | Move | `notebooks/exploration/` | Already exploratory |
| `Datek_sensor_data/minute_level_patterns.py` | Move | `notebooks/exploration/` | Analysis script |
| `Energinet/energinet.py` | Remove | - | Superseded by energinet4.py |
| `Energinet/energinet2.py` | Remove | - | Superseded by energinet4.py |
| `Energinet/energinet3.py` | Remove | - | Superseded by energinet4.py |
| `Energinet/energinet4.py` | Keep | `src/data_collectors/energinet_client.py` | Refactor into class |
| `Energinet/extract_data.py` | Merge | `src/data_collectors/energinet_client.py` | Incorporate utilities |
| `Energinet/energinet_variability.py` | Remove | - | Superseded by variability2 |
| `Energinet/energinet_variability2.py` | Keep | `src/utils/variability.py` | Extract analysis functions |
| `Energinet/top_var.py` | Move | `notebooks/exploration/` | Analysis script |
| `Model_development/power_prediction_system.py` | Fix & Keep | `src/models/peak_predictor.py` | Fix bugs, refactor |
| `Model_development/power_peak_forecasting_PoC.ipynb` | Keep | `notebooks/poc/` | Research artifact |
| `Model_development/PoC_v2.ipynb` | Keep | `notebooks/poc/` | Research artifact |
| `Energinet/units.csv` | Keep | `config/meters.yaml` | Convert to YAML, sanitize |

---

## Appendix B: Credential Locations

All instances requiring credential extraction:

1. `Datek_sensor_data/datek.py` - Line 45
2. `Datek_sensor_data/datek_minute.py` - Line 22
3. `Energinet/energinet.py` - Line 12
4. `Energinet/energinet2.py` - Line 12
5. `Energinet/energinet3.py` - Line 12
6. `Energinet/energinet4.py` - Line 12
7. `Energinet/extract_data.py` - Line 12
8. `Energinet/energinet_variability.py` - Line 13
9. `Energinet/energinet_variability2.py` - Line 13

**Action Required:** Create `config/config.example.yaml` with placeholder values and migration guide.

---

*Report generated: 2025*  
*For questions or clarifications, refer to the codebase or contact the development team.*

