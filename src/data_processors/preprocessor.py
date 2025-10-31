"""
Unified data preprocessing pipeline.
Consolidates functionality from data_wrangling_2.py and preprocessing_minute_data.py.
"""
import pandas as pd
from typing import Dict, Optional, List
from pathlib import Path


class DataPreprocessor:
    """Preprocessor for cleaning and standardizing meter data."""
    
    # Default column mapping for Datek/Stromme data
    DEFAULT_COLUMN_MAP = {
        "time": "timestamp_utc",
        "a": "active_power_W",
        "an": "active_power_neg_W",
        "rp": "reactive_power_VAr",
        "rn": "reactive_power_neg_VAr",
        "i1": "phase1_current_A",
        "i2": "phase2_current_A",
        "i3": "phase3_current_A",
        "u1": "phase1_voltage_V",
        "u2": "phase2_voltage_V",
        "u3": "phase3_voltage_V",
        "meter_id": "meter_id"
    }
    
    DEFAULT_COLUMNS = [
        "time", "a", "an", "rp", "rn", "i1", "i2", "i3", "u1", "u2", "u3", "meter_id"
    ]
    
    def __init__(self, column_map: Optional[Dict[str, str]] = None, 
                 columns_to_keep: Optional[List[str]] = None):
        """
        Initialize preprocessor.
        
        Args:
            column_map: Custom column renaming map. If None, uses DEFAULT_COLUMN_MAP
            columns_to_keep: Columns to keep. If None, uses DEFAULT_COLUMNS
        """
        self.column_map = column_map or self.DEFAULT_COLUMN_MAP.copy()
        self.columns_to_keep = columns_to_keep or self.DEFAULT_COLUMNS.copy()
    
    def process(self, df: pd.DataFrame, sep: str = ";", 
                timestamp_col: str = "timestamp_utc") -> pd.DataFrame:
        """
        Process dataframe: select, rename, and sort columns.
        
        Args:
            df: Input DataFrame (or path to CSV file)
            sep: CSV separator if df is a path
            timestamp_col: Name of timestamp column after renaming
            
        Returns:
            Processed DataFrame
        """
        # Read from file if path provided
        if isinstance(df, (str, Path)):
            df = pd.read_csv(df, sep=sep, low_memory=False)
        
        # Keep only desired columns
        existing_cols = [col for col in self.columns_to_keep if col in df.columns]
        df = df[existing_cols].copy()
        
        # Rename columns
        df.rename(columns=self.column_map, inplace=True, errors="ignore")
        
        # Convert timestamp to datetime
        if timestamp_col in df.columns:
            df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors="coerce", utc=True)
        
        # Sort by meter_id and timestamp
        sort_cols = []
        if "meter_id" in df.columns:
            sort_cols.append("meter_id")
        if timestamp_col in df.columns:
            sort_cols.append(timestamp_col)
        
        if sort_cols:
            df.sort_values(by=sort_cols, inplace=True)
        
        return df
    
    def save(self, df: pd.DataFrame, output_path: str, sep: str = ";"):
        """Save processed DataFrame to CSV."""
        df.to_csv(output_path, index=False, sep=sep)
    
    def process_file(self, input_file: str, output_file: str, 
                     sep: str = ";", debug: bool = True) -> pd.DataFrame:
        """
        Complete pipeline: read, process, and save.
        
        Args:
            input_file: Path to input CSV
            output_file: Path to output CSV
            sep: CSV separator
            debug: Print processing info
            
        Returns:
            Processed DataFrame
        """
        if debug:
            print(f"Reading input CSV: {input_file}")
        
        df = self.process(input_file, sep=sep)
        
        if debug:
            print(f"Processed {len(df)} rows, {len(df.columns)} columns")
            print(f"Sample data:\n{df.head()}")
        
        self.save(df, output_file, sep=sep)
        
        if debug:
            print(f"Saved to {output_file}")
        
        return df

