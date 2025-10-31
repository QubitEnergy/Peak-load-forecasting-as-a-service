#!/usr/bin/env python3
"""
Validation script to check that all modules can be imported and structure is correct.
Run after installing dependencies: pip install -r requirements.txt
"""
import sys
from pathlib import Path

def check_imports():
    """Check that all modules can be imported."""
    errors = []
    warnings = []
    
    print("Validating module structure...")
    print("=" * 50)
    
    # Check config
    try:
        from src.utils.config import Config, get_config
        print("✓ Config module imports OK")
    except ImportError as e:
        errors.append(f"Config import failed: {e}")
    except Exception as e:
        warnings.append(f"Config import warning: {e}")
    
    # Check data collectors
    try:
        from src.data_collectors import StrommeClient, EnerginetClient
        print("✓ Data collector modules import OK")
    except ImportError as e:
        errors.append(f"Data collector import failed: {e}")
    except Exception as e:
        warnings.append(f"Data collector import warning: {e}")
    
    # Check data processors
    try:
        from src.data_processors import DataPreprocessor, TemperatureMerger
        print("✓ Data processor modules import OK")
    except ImportError as e:
        errors.append(f"Data processor import failed: {e}")
    except Exception as e:
        warnings.append(f"Data processor import warning: {e}")
    
    # Check models
    try:
        from src.models import PowerPeakPredictor
        print("✓ Model modules import OK")
    except ImportError as e:
        errors.append(f"Model import failed: {e}")
    except Exception as e:
        warnings.append(f"Model import warning: {e}")
    
    # Check utils
    try:
        from src.utils.variability import compute_variability, compute_rolling_variability
        print("✓ Utility modules import OK")
    except ImportError as e:
        errors.append(f"Utility import failed: {e}")
    except Exception as e:
        warnings.append(f"Utility import warning: {e}")
    
    print("=" * 50)
    
    if errors:
        print("\n❌ ERRORS FOUND:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
    
    print("\n✅ All modules validated successfully!")
    print("\nNote: If you see import errors, install dependencies:")
    print("  pip install -r requirements.txt")
    
    return True

def check_structure():
    """Check directory structure."""
    print("\nValidating directory structure...")
    print("=" * 50)
    
    required_dirs = [
        "src/data_collectors",
        "src/data_processors",
        "src/models",
        "src/utils",
        "config",
        "data/raw",
        "data/processed",
        "data/outputs",
        "notebooks/exploration",
        "notebooks/poc",
        "tests",
        "docs/references"
    ]
    
    missing = []
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✓ {dir_path}/")
        else:
            missing.append(dir_path)
            print(f"✗ {dir_path}/ (missing)")
    
    if missing:
        print(f"\n⚠️  Missing directories: {', '.join(missing)}")
        print("Run: mkdir -p " + " ".join(missing))
        return False
    
    print("\n✅ Directory structure is correct!")
    return True

if __name__ == "__main__":
    print("Peak Load Forecasting - Structure Validation")
    print("=" * 50)
    
    structure_ok = check_structure()
    imports_ok = check_imports()
    
    if structure_ok and imports_ok:
        print("\n" + "=" * 50)
        print("✅ VALIDATION PASSED")
        print("=" * 50)
        sys.exit(0)
    else:
        print("\n" + "=" * 50)
        print("❌ VALIDATION FAILED")
        print("=" * 50)
        sys.exit(1)

