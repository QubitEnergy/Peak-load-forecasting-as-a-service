"""
Temperature data merger for combining energy and temperature data.
"""
import pandas as pd
import requests
from datetime import datetime
from typing import Optional
import logging

from ..utils.config import get_config


class TemperatureMerger:
    """Merge energy data with temperature data from Frost API."""
    
    def __init__(self):
        """Initialize temperature merger."""
        config = get_config()
        self.api_url = config.get('frost.api_url', 'https://frost.met.no')
        self.client_id = config.frost_client_id
        self.logger = logging.getLogger(__name__)
    
    def get_historical_temperature(self, station_id: str, start_time: str, 
                                   end_time: str) -> pd.DataFrame:
        """
        Retrieve historical temperature data from Frost API.
        
        Args:
            station_id: Frost station ID (e.g., "SN18700")
            start_time: ISO 8601 formatted start time
            end_time: ISO 8601 formatted end time
            
        Returns:
            DataFrame with columns: time, air_temperature
        """
        endpoint = f"{self.api_url}/observations/v0.jsonld"
        params = {
            "sources": station_id,
            "elements": "air_temperature",
            "referencetime": f"{start_time}/{end_time}",
            "limit": 1000
        }
        
        try:
            response = requests.get(endpoint, params=params, auth=(self.client_id, ""))
            response.raise_for_status()
            data = response.json()
            
            records = []
            for item in data.get("data", []):
                time_stamp = item.get("referenceTime")
                temperature = None
                if item.get("observations"):
                    temperature = item["observations"][0].get("value")
                records.append({"time": time_stamp, "air_temperature": temperature})
            
            df_temp = pd.DataFrame(records)
            if not df_temp.empty:
                df_temp["time"] = pd.to_datetime(df_temp["time"], utc=True, errors="coerce")
            
            return df_temp
            
        except Exception as e:
            self.logger.error(f"Error fetching temperature data: {e}")
            return pd.DataFrame()
    
    def merge_energy_temperature(self, energy_df: pd.DataFrame, 
                                 temp_df: pd.DataFrame,
                                 energy_time_col: str = "time",
                                 temp_time_col: str = "time") -> pd.DataFrame:
        """
        Merge energy and temperature data using backward merge.
        
        Args:
            energy_df: Energy consumption DataFrame
            temp_df: Temperature DataFrame
            energy_time_col: Time column name in energy_df
            temp_time_col: Time column name in temp_df
            
        Returns:
            Merged DataFrame
        """
        # Ensure both are sorted
        energy_df = energy_df.sort_values(by=energy_time_col).copy()
        temp_df = temp_df.sort_values(by=temp_time_col).copy()
        
        # Merge using backward fill (asof merge)
        merged_df = pd.merge_asof(
            energy_df,
            temp_df.rename(columns={temp_time_col: energy_time_col}),
            left_on=energy_time_col,
            right_on=energy_time_col,
            direction="backward"
        )
        
        # Ensure temperature is numeric
        if "air_temperature" in merged_df.columns:
            merged_df["air_temperature"] = pd.to_numeric(
                merged_df["air_temperature"], errors="coerce"
            )
        
        # Sort by meter_id and time
        if "meter_id" in merged_df.columns:
            merged_df.sort_values(by=["meter_id", energy_time_col], inplace=True)
        else:
            merged_df.sort_values(by=energy_time_col, inplace=True)
        
        return merged_df

