"""
Unified Energinet API client.
Consolidates functionality from energinet4.py and extract_data.py.
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import urllib3
import logging

from ..utils.config import get_config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class EnerginetClient:
    """Client for Energinet API."""
    
    def __init__(self, debug: bool = False):
        """Initialize Energinet client."""
        config = get_config()
        self.base_url = config.get('energinet.api_url', 'https://www.energinet.net')
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        self._verify_ssl = config.get('data_collection.verify_ssl', False)
        self._bearer_token = config.energinet_bearer_token
        self._accept_language = config.get('energinet.accept_language', 'no')
    
    def _get_headers(self) -> Dict[str, str]:
        """Get base headers for API requests."""
        return {
            "Authorization": f"Bearer {self._bearer_token}",
            "Accept-Language": self._accept_language
        }
    
    def get_subunits(self, unit_id: str) -> List[Dict]:
        """
        Recursively fetch subunits for a given unit_id using the drilldown link.
        
        Args:
            unit_id: Unit ID to fetch subunits for
            
        Returns:
            List of all discovered units (including the original)
        """
        url = f"{self.base_url}/api/unit/{unit_id}"
        resp = requests.get(url, headers=self._get_headers(), verify=self._verify_ssl)
        
        if resp.status_code != 200:
            self.logger.error(f"Error fetching unit '{unit_id}': {resp.status_code} - {resp.text}")
            return []
        
        try:
            data = resp.json()
        except Exception as e:
            self.logger.error(f"JSON decode error for unit '{unit_id}': {e}")
            return []
        
        all_units = []
        for item in data:
            current_unit_id = item.get("unit_id")
            name = item.get("name")
            datasources = item.get("datasources", [])
            
            all_units.append({
                "unit_id": current_unit_id,
                "name": name,
                "datasources": datasources
            })
            
            # Recurse if there's a drilldown link
            dd_link = item.get("links", {}).get("drilldown", {}).get("href")
            if dd_link:
                sub_id = dd_link.split("/")[-1]
                if sub_id != current_unit_id:
                    deeper_units = self.get_subunits(sub_id)
                    all_units.extend(deeper_units)
        
        return all_units
    
    def fetch_energy_data(self, energy_link: str, date_from: str, date_to: str) -> pd.DataFrame:
        """
        Fetch energy data for a given date range.
        
        Args:
            energy_link: API endpoint URL for energy data
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with columns ["Start", "Value"] or empty DataFrame
        """
        if not energy_link:
            return pd.DataFrame()
        
        url = energy_link if energy_link.startswith("http") else self.base_url + energy_link
        intervals = self._split_date_range(date_from, date_to)
        all_data = []
        
        for start, end in intervals:
            custom_headers = self._get_headers().copy()
            custom_headers["DateIntervalFrom"] = start
            custom_headers["DateIntervalTo"] = end
            
            try:
                response = requests.get(url, headers=custom_headers, verify=self._verify_ssl)
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, list):
                    all_data.extend(data)
                else:
                    self.logger.warning(f"Unexpected data format for endpoint {url}")
                    
            except Exception as e:
                self.logger.error(f"Error fetching data for endpoint {url} from {start} to {end}: {e}")
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        if "Start" not in df.columns or "Value" not in df.columns:
            self.logger.warning("Unexpected format in energy data")
            return pd.DataFrame()
        
        df["Start"] = pd.to_datetime(df["Start"], errors='coerce').dt.tz_localize(None)
        df = df.dropna(subset=["Start"])
        
        mask = (df["Start"] >= date_from) & (df["Start"] < date_to)
        df = df[mask].sort_values("Start")
        
        return df
    
    def _split_date_range(self, date_from: str, date_to: str, chunk_days: int = 7) -> List[tuple]:
        """Split date range into chunks."""
        start = datetime.fromisoformat(date_from)
        end = datetime.fromisoformat(date_to)
        intervals = []
        current = start
        
        while current < end:
            next_time = min(current + timedelta(days=chunk_days), end)
            intervals.append((current.strftime("%Y-%m-%d"), next_time.strftime("%Y-%m-%d")))
            current = next_time
        
        return intervals
    
    def flatten_units(self, units: List[Dict]) -> pd.DataFrame:
        """
        Convert nested unit list into a flat structure with energy links.
        
        Args:
            units: List of unit dictionaries from get_subunits()
            
        Returns:
            DataFrame with Unit ID, Name, and Energy Link columns
        """
        rows = []
        for u in units:
            row = {
                "Unit ID": u["unit_id"],
                "Name": u["name"],
                "Energy Link": ""
            }
            
            for ds in u["datasources"]:
                label = ds.get("label", "").lower()
                if label == "energy":
                    data_link = ds.get("links", {}).get("data", {}).get("href", "")
                    if data_link and data_link.startswith("/"):
                        data_link = self.base_url + data_link
                    row["Energy Link"] = data_link
            
            rows.append(row)
        
        return pd.DataFrame(rows).drop_duplicates(subset=["Unit ID"]).reset_index(drop=True)

