import requests
from datetime import datetime, timezone, timedelta
import logging
import pandas as pd
from dateutil import parser
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class MinuteDataCollector:
    def __init__(self, debug=True):
        self.base_url = "https://api.stromme.io"
        self.token = None
        self.debug = debug
        self.logger = logging.getLogger(__name__)

    def get_token(self):
        """
        Authenticate with the API to retrieve an access token.
        """
        headers = {
            'Authorization': 'Basic Nms2dm5hZ3JlaWVtOGJuMHRycTlvZzloNWI6MW1wOTZtaWlsbm80MWRlbWJxcHFjaTRrZzdxazFnb2ZzOW5xazB0ZnFsajduMTVtam84NQ==',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        try:
            response = requests.post(
                'https://idp.stromme.io/token',
                headers=headers,
                data={'grant_type': 'client_credentials'},
                verify=False
            )
            response.raise_for_status()
            self.token = response.json()['access_token']
            if self.debug:
                print("Token retrieved successfully.")
            return self.token
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            raise

    def get_minute_data_in_chunks(self, device_id: str, start_time: datetime, end_time: datetime) -> list:
        """
        Retrieve data in hourly chunks between start_time and end_time.
        Using 'obis' as the parameter so that when the time window is limited to 1 hour,
        the API should return minute-level data.
        """
        if not self.token:
            self.get_token()

        all_data = []
        current_start = start_time

        while current_start < end_time:
            # End of this chunk is 1 hour from current_start or the overall end_time, whichever is earlier
            chunk_end = min(current_start + timedelta(hours=1), end_time)

            params = {
                'name': 'obis',  # Using 'obis' to request minute-level data
                'start': current_start.isoformat(),
                'end': chunk_end.isoformat()
            }
            headers = {'Authorization': f'Bearer {self.token}'}

            try:
                response = requests.get(
                    f"{self.base_url}/handevices/{device_id}/measures",
                    headers=headers,
                    params=params,
                    verify=False
                )
                response.raise_for_status()
                data = response.json()

                if self.debug:
                    print(f"Device {device_id} [{current_start} to {chunk_end}]: retrieved {len(data)} records.")

                all_data.extend(data)

            except requests.HTTPError as http_err:
                self.logger.error(f"Error fetching data for device {device_id}: {http_err}")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error for device {device_id}: {e}")
                break

            current_start = chunk_end  # Move to the next chunk

        return all_data

    def export_all_minute_data(self, meters, start_date_str: str, filename="all_minute_data.csv"):
        """
        For each meter in the provided list, gather data from start_date_str up to now
        in hourly chunks (to get minute-level data) and export to a CSV file.
        """
        if not self.token:
            self.get_token()

        # Convert the start_date_str to a datetime object (UTC)
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
            # Use semicolon as separator if needed for your locale
            df.to_csv(filename, index=False, sep=";")
            print(f"Exported {len(all_data)} records to {filename}.")
        else:
            print("No data available to export.")

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    meters = [
        {
            "id": "Jfmwhk2e",
            "name": "Fellesanlegg Main",
            "description": "Common area meter 1"
        },
        {
            "id": "KGdRbnJc",
            "name": "Fellesanlegg Pole",
            "description": "Common area meter 2 (board by pole)"
        },
        {
            "id": "6kPJw9QF",
            "name": "Cinema 500",
            "description": "Cinema - 500"
        }
    ]

    collector = MinuteDataCollector(debug=True)

    # Starting from February 7, 2025, as requested.
    collector.export_all_minute_data(
        meters, 
        start_date_str="2025-02-07T00:00:00Z", 
        filename="all_minute_data.csv"
    )

if __name__ == "__main__":
    main()
