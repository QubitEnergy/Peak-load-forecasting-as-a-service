import requests
from datetime import datetime, timezone, timedelta
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from dateutil import parser
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RealtimeEnergyMonitor:
    def __init__(self, debug=True):
        self.base_url = "https://api.stromme.io"
        self.token = None
        self.logger = logging.getLogger(__name__)
        self.debug = debug
        
        plt.style.use('default')
        plt.rcParams.update({
            'figure.figsize': (15, 10),
            'font.size': 10,
            'axes.labelsize': 12,
            'axes.titlesize': 14,
            'lines.linewidth': 2,
        })
        
        self.fig = plt.figure(figsize=(15, 10))
        gs = self.fig.add_gridspec(3, 1, height_ratios=[2, 2, 1], hspace=0.3)
        self.axs = [self.fig.add_subplot(gs[i]) for i in range(3)]
        
        self.lines = {}
        self.data_buffers = {}
        self.stats_text = None
        self.colors = {
            'Jfmwhk2e': '#2ecc71',
            'KGdRbnJc': '#e74c3c',
            '6kPJw9QF': '#3498db'
        }

    def get_token(self):
        try:
            headers = {
                'Authorization': 'Basic Nms2dm5hZ3JlaWVtOGJuMHRycTlvZzloNWI6MW1wOTZtaWlsbm80MWRlbWJxcHFjaTRrZzdxazFnb2ZzOW5xazB0ZnFsajduMTVtam84NQ==',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            response = requests.post(
                'https://idp.stromme.io/token',
                headers=headers,
                data={'grant_type': 'client_credentials'},
                verify=False
            )
            response.raise_for_status()
            self.token = response.json()['access_token']
            return self.token
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            raise

    def get_historical_data(self, device_id: str) -> list:
        """Get historical hourly data for the last 24 hours"""
        if not self.token:
            self.get_token()
        
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=24)
            
            params = {
                'name': 'hourly2',  # Using hourly2 endpoint for hourly data
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            }
            
            headers = {'Authorization': f'Bearer {self.token}'}
            
            response = requests.get(
                f"{self.base_url}/handevices/{device_id}/measures",
                headers=headers,
                params=params,
                verify=False
            )
            response.raise_for_status()
            
            data = response.json()
            
            if self.debug:
                print(f"\nHistorical data for {device_id}:")
                print(f"Retrieved {len(data)} hourly measurements")
                if data:
                    print(f"First measurement: {data[0]}")
                    print(f"Last measurement: {data[-1]}")
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error getting historical data: {str(e)}")
            return []

    def get_full_historical_data(self, device_id: str, start_date: str) -> list:
        """Fetch full historical data from the given start_date until now."""
        if not self.token:
            self.get_token()

        all_data = []
        start_time = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        end_time = datetime.now(timezone.utc)

        while start_time < end_time:
            next_time = min(start_time + timedelta(days=7), end_time)  # Fetch in 7-day chunks
            
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
                    verify=False
                )
                response.raise_for_status()
                data = response.json()

                if data:
                    all_data.extend(data)
                
                start_time = next_time  # Move to the next chunk

            except Exception as e:
                self.logger.error(f"Error fetching historical data: {str(e)}")
                break  # Stop on error

        return all_data

    def get_latest_data(self, device_id: str) -> dict:
        """Get latest measurement"""
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
                verify=False
            )
            response.raise_for_status()
            
            data = response.json()
            if data and self.debug:
                print(f"\nLatest data for {device_id}: {data[-1]}")
            return data[-1] if data else None
            
        except Exception as e:
            self.logger.error(f"Error getting latest data: {str(e)}")
            return None

    def process_hourly_data(self, data: list) -> tuple:
        """Process hourly data points"""
        times = []
        powers = []
        currents = {f'i{i}': [] for i in range(1, 4)}
        
        for point in data:
            times.append(parser.parse(point['startTime']))
            powers.append(point['import'])  # Using import for power consumption
            
            # For hourly data, we'll use the difference in import/export for currents
            for i in range(1, 4):
                currents[f'i{i}'].append(
                    (point['endMeasureImport'] - point['startMeasureImport']) / 3600  # A rough estimate
                )
        
        return times, powers, currents

    def initialize_plot(self, meters):
        """Initialize the plotting system"""
        self.fig.suptitle('Real-time Energy Monitoring', fontsize=16, y=0.95)
        
        self.axs[0].set_title('Power Consumption (Last 24 Hours)')
        self.axs[0].set_xlabel('Time')
        self.axs[0].set_ylabel('Power (W)')
        self.axs[0].grid(True, alpha=0.3)
        
        self.axs[1].set_title('Phase Currents')
        self.axs[1].set_xlabel('Time')
        self.axs[1].set_ylabel('Current (A)')
        self.axs[1].grid(True, alpha=0.3)
        
        self.axs[2].set_title('Statistics')
        self.axs[2].axis('off')
        
        # Initialize data structures and load historical data
        for meter in meters:
            meter_id = meter['id']
            self.data_buffers[meter_id] = {
                'times': [],
                'power': [],
                'currents': {f'i{j}': [] for j in range(1, 4)}
            }
            
            # Get and process historical data
            historical_data = self.get_historical_data(meter_id)
            if historical_data:
                times, powers, currents = self.process_hourly_data(historical_data)
                self.data_buffers[meter_id]['times'] = times
                self.data_buffers[meter_id]['power'] = powers
                self.data_buffers[meter_id]['currents'] = currents
            
            # Create plot lines
            self.lines[meter_id] = {
                'power': self.axs[0].plot([], [], 'o-', 
                                        label=meter['name'],
                                        color=self.colors[meter_id],
                                        markersize=5)[0],
                'currents': [
                    self.axs[1].plot([], [], 
                                   label=f"{meter['name']} - Phase {j}",
                                   color=self.colors[meter_id],
                                   alpha=0.7,
                                   linestyle=['solid', 'dashed', 'dotted'][j-1])[0]
                    for j in range(1, 4)
                ]
            }
        
        # Add legends
        self.axs[0].legend(loc='upper left', bbox_to_anchor=(1.01, 1))
        self.axs[1].legend(loc='upper left', bbox_to_anchor=(1.01, 1))
        
        # Initialize stats text
        self.stats_text = self.axs[2].text(0.1, 0.9, '', 
                                         fontsize=10,
                                         verticalalignment='top',
                                         transform=self.axs[2].transAxes)
        
        plt.tight_layout()

    def update_plot(self, frame, meters):
        """Update function for animation"""
        stats_text = []
        
        for meter in meters:
            meter_id = meter['id']
            data = self.get_latest_data(meter_id)
            
            if data:
                timestamp = parser.parse(data['time'])
                power = data.get('a', 0)
                currents = [data.get(f'i{i}', 0) / 1000 for i in range(1, 4)]
                
                # Update latest point
                if self.data_buffers[meter_id]['times']:
                    last_time = self.data_buffers[meter_id]['times'][-1]
                    if timestamp > last_time:
                        self.data_buffers[meter_id]['times'].append(timestamp)
                        self.data_buffers[meter_id]['power'].append(power)
                        for i, current in enumerate(currents, 1):
                            self.data_buffers[meter_id]['currents'][f'i{i}'].append(current)
                
                # Update plot lines
                self.lines[meter_id]['power'].set_data(
                    self.data_buffers[meter_id]['times'],
                    self.data_buffers[meter_id]['power']
                )
                
                for i in range(3):
                    self.lines[meter_id]['currents'][i].set_data(
                        self.data_buffers[meter_id]['times'],
                        self.data_buffers[meter_id]['currents'][f'i{i+1}']
                    )
                
                # Update statistics
                power_data = self.data_buffers[meter_id]['power']
                if power_data:
                    stats_text.append(f"{meter['name']}:")
                    stats_text.append(f"  Current Power: {power:.1f} W")
                    stats_text.append(f"  Average Power: {np.mean(power_data):.1f} W")
                    stats_text.append(f"  Max Power: {np.max(power_data):.1f} W")
                    stats_text.append(f"  Min Power: {np.min(power_data):.1f} W")
                    stats_text.append(f"  Total Energy: {sum(power_data)/1000:.2f} kWh")
                    stats_text.append("")
        
        # Update statistics text
        if stats_text:
            self.stats_text.set_text('\n'.join(stats_text))
        
        # Adjust axes limits
        for ax in self.axs[:2]:
            ax.relim()
            ax.autoscale_view()
            ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
            ax.tick_params(axis='x', rotation=45)
        
        return [line for meter_id in self.lines.values() 
                for line in [meter_id['power']] + meter_id['currents']]

    def start_monitoring(self, meters):
        """Start real-time monitoring"""
        print("Initializing real-time monitoring with 24-hour history...")
        
        self.initialize_plot(meters)
        
        ani = FuncAnimation(
            self.fig,
            self.update_plot,
            fargs=(meters,),
            interval=1000,  # Update every second
            blit=True
        )
        
        plt.show()

    def export_full_historical_data(self, meters, filename="energy_history.csv"):
        """Export all historical data from the sensors to a CSV file."""
        if not self.token:
            self.get_token()

        all_data = []
        for meter in meters:
            meter_id = meter["id"]
            data = self.get_full_historical_data(meter_id, "2024-01-25")
            for entry in data:
                entry["meter_id"] = meter_id  # Add meter ID for reference
                all_data.append(entry)

        if all_data:
            df = pd.DataFrame(all_data)
            df.to_csv(filename, index=False)
            print(f"Exported {len(all_data)} records to {filename}")
        else:
            print("No data available for export.")

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
    """
    meters = [
        {
            "id": "Jfmwhk2e",
            "name": "Fellesanlegg Main",
            "description": "Common area meter 1"
        }
    ]
    """
    monitor = RealtimeEnergyMonitor(debug=True)

    #monitor.export_full_historical_data(meters, 'energy_history.csv')
    monitor.start_monitoring(meters)

if __name__ == "__main__":
    main()