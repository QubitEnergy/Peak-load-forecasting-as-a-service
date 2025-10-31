# Archive Directory

This directory contains old redundant code files that have been consolidated into the new modular structure in `src/`.

## Contents

### old_code/
Contains redundant iterations of scripts that have been merged into unified modules:

**Datek/Stromme API clients** (consolidated into `src/data_collectors/stromme_client.py`):
- `datek.py` - Original real-time monitoring
- `datek_minute.py` - Minute-level data collection

**Data preprocessing** (consolidated into `src/data_processors/preprocessor.py`):
- `data_wrangling.py` - Original preprocessing
- `data_wrangling_2.py` - Refined preprocessing
- `preprocessing_minute_data.py` - Minute data preprocessing

**Energinet API clients** (consolidated into `src/data_collectors/energinet_client.py`):
- `energinet.py` - Basic drilldown
- `energinet2.py` - Enhanced with multiple data types
- `energinet3.py` - Further refinements
- `energinet4.py` - Most complete (used as reference)
- `extract_data.py` - Data extraction utility

**Variability analysis** (consolidated into `src/utils/variability.py`):
- `energinet_variability.py` - Original variability computation
- `energinet_variability2.py` - Enhanced variability (used as reference)

## Note

These files are kept for reference only. All functionality has been migrated to the new modular structure. Do not use these files for new development.

