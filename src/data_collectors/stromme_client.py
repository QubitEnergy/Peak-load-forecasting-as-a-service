"""
Unified Stromme API client for Datek sensor data collection.
Consolidates functionality from datek.py and datek_minute.py.
"""
import requests
from datetime import datetime, timezone, timedelta
import logging
import pandas as pd
from dateutil import parser
import urllib3
from typing import List, Dict, Optional
from pathlib import Path

from ..utils.config import get_config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class StrommeClient:
    """
    Client for Stromme API (Datek sensors).
    Supports both hourly and minute-level data collection.
    """
    
    def __init__(self, debug: bool = False):
        """
        Initialize Stromme client.
        
        Args:
            debug: Enable debug logging
        """
        config = get_config()
        self.base_url = config.get('stromme.api_url', 'https://api.stromme.io')
        self.idp_url = config.get('stromme.idp_url', 'https://idp.stromme.io/token')
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        self.token: Optional[str] = None
        self._verify_ssl = config.get('data_collection.verify_ssl', False)
    
    def get_token(self) -> str:
        """
        Authenticate with the API to retrieve an access token.
        
        Returns:
            Access token string
            
        Raises:
            ValueError: If authentication fails
        """
        try:
            config = get_config()
            basic_auth_token = config.stromme_basic_auth_token
            
            headers = {
                'Authorization': f'Basic {basic_auth_token}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = requests.post(
                self.idp_url,
                headers=headers,
                data={'grant_type': 'client_credentials'},
                verify=self._verify_ssl
            )
            response.raise_for_status()
            self.token = response.json()['access_token']
            
            if self.debug:
                self.logger.info("Token retrieved successfully.")
            
            return self.token
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            raise ValueError(f"Failed to authenticate with Stromme API: {e}") from e
    
    def get_historical_hourly_data(self, device_id: str, hours: int = 24) -> List[Dict]:
        """
        Get historical hourly data for the specified number of hours.
        
        Args:
            device_id: Device/meter ID
            hours: Number of hours to retrieve (default: 24)
            
        Returns:
            List of measurement dictionaries
        """
        if not self.token:
            self.get_token()
        
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours)
            
            params = {
                'name': 'hourly2',
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            }
            
            headers = {'Authorization': f'Bearer {self.token}'}
            
            response = requests.get(
                f"{self.base_url}/handevices/{device_id}/measures",
                headers=headers,
                params=params,
                verify=self._verify_ssl
            )
            response.raise_for_status()
            
            data = response.json()
            
            if self.debug:
                self.logger.info(f"Retrieved {len(data)} hourly measurements for {device_id}")
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error getting historical hourly data: {e}")
            return []
    
    def get_full_historical_hourly_data(self, device_id: str, start_date: str) -> List[Dict]:
        """
        Fetch full historical hourly data from start_date until now.
        Fetches in 7-day chunks to avoid API limits.
        
        Args:
            device_id: Device/meter ID
            start_date: ISO format date string (e.g., "2024-01-25T00:00:00Z")
            
        Returns:
            List of all measurement dictionaries
        """
        if not self.token:
            self.get_token()
        
        all_data = []
        start_time = parser.parse(start_date).replace(tzinfo=timezone.utc)
        end_time = datetime.now(timezone.utc)
        chunk_days = get_config().get('data_collection.chunk_size_days', 7)
        
        while start_time < end_time:
            next_time = min(start_time + timedelta(days=chunk_days), end_time)
            
            params = {
                'name': 'hourly2',
                'start': start_time.isoformat(),
                'end': next_time.isoformat()
            }
            
            headers = {'Authorization': f'Bearer {self.token}'}
            
            try:
                response = requests.get(
                    f"{self.base_url}/handevices/{device_id}/measures",
                    headers=headers,
                    params=params,
                    verify=self._verify_ssl
                )
                response.raise_for_status()
                data = response.json()
                
                if data:
                    all_data.extend(data)
                
                start_time = next_time
                
            except Exception as e:
                self.logger.error(f"Error fetching historical data chunk: {e}")
                break
        
        return all_data
    
    def get_minute_data_in_chunks(self, device_id: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """
        Retrieve minute-level data in hourly chunks between start_time and end_time.
        Uses 'obis' endpoint with 1-hour windows to get minute-level data.
        
        Args:
            device_id: Device/meter ID
            start_time: Start datetime (UTC)
            end_time: End datetime (UTC)
            
        Returns:
            List of minute-level measurement dictionaries
        """
        if not self.token:
            self.get_token()
        
        all_data = []
        current_start = start_time
        
        while current_start < end_time:
            chunk_end = min(current_start + timedelta(hours=1), end_time)
            
            params = {
                'name': 'obis',
                'start': current_start.isoformat(),
                'end': chunk_end.isoformat()
            }
            headers = {'Authorization': f'Bearer {self.token}'}
            
            try:
                response = requests.get(
                    f"{self.base_url}/handevices/{device_id}/measures",
                    headers=headers,
                    params=params,
                    verify=self._verify_ssl
                )
                response.raise_for_status()
                data = response.json()
                
                if self.debug:
                    self.logger.debug(f"Device {device_id} [{current_start} to {chunk_end}]: {len(data)} records")
                
                all_data.extend(data)
                
            except requests.HTTPError as http_err:
                self.logger.error(f"HTTP error fetching data for device {device_id}: {http_err}")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error for device {device_id}: {e}")
                break
            
            current_start = chunk_end
        
        return all_data
    
    def get_latest_data(self, device_id: str) -> Optional[Dict]:
        """
        Get latest measurement from device.
        
        Args:
            device_id: Device/meter ID
            
        Returns:
            Latest measurement dictionary or None
        """
        if not self.token:
            self.get_token()
        
        try:
            now = datetime.now(timezone.utc)
            start_time = now - timedelta(minutes=5)
            
            params = {
                'name': 'obis',
                'start': start_time.isoformat(),
                'end': now.isoformat()
            }
            
            headers = {'Authorization': f'Bearer {self.token}'}
            
            response = requests.get(
                f"{self.base_url}/handevices/{device_id}/measures",
                headers=headers,
                params=params,
                verify=self._verify_ssl
            )
            response.raise_for_status()
            
            data = response.json()
            return data[-1] if data else None
            
        except Exception as e:
            self.logger.error(f"Error getting latest data: {e}")
            return None
    
    def export_hourly_data(self, meters: List[Dict], start_date: str, output_path: str) -> pd.DataFrame:
        """
        Export hourly historical data for multiple meters to CSV.
        
        Args:
            meters: List of meter dictionaries with 'id' key
            start_date: ISO format date string
            output_path: Path to output CSV file
            
        Returns:
            DataFrame with exported data
        """
        all_data = []
        for meter in meters:
            meter_id = meter['id']
            data = self.get_full_historical_hourly_data(meter_id, start_date)
            for entry in data:
                entry['meter_id'] = meter_id
                all_data.append(entry)
        
        if all_data:
            df = pd.DataFrame(all_data)
            df.to_csv(output_path, index=False)
            self.logger.info(f"Exported {len(all_data)} records to {output_path}")
            return df
        else:
            self.logger.warning("No data available for export.")
            return pd.DataFrame()
    
    def export_minute_data(self, meters: List[Dict], start_date_str: str, output_path: str) -> pd.DataFrame:
        """
        Export minute-level data for multiple meters to CSV.
        
        Args:
            meters: List of meter dictionaries with 'id' key
            start_date_str: ISO format date string
            output_path: Path to output CSV file
            
        Returns:
            DataFrame with exported data
        """
        if not self.token:
            self.get_token()
        
        start_time = parser.parse(start_date_str).replace(tzinfo=timezone.utc)
        end_time = datetime.now(timezone.utc)
        
        all_data = []
        for meter in meters:
            meter_id = meter['id']
            meter_data = self.get_minute_data_in_chunks(meter_id, start_time, end_time)
            for entry in meter_data:
                entry['meter_id'] = meter_id
                all_data.append(entry)
        
        if all_data:
            df = pd.DataFrame(all_data)
            df.to_csv(output_path, index=False, sep=";")
            self.logger.info(f"Exported {len(all_data)} records to {output_path}")
            return df
        else:
            self.logger.warning("No data available to export.")
            return pd.DataFrame()

