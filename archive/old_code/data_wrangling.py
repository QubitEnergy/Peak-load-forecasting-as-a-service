import requests
import pandas as pd

def get_historical_temperature(station_id, start_time, end_time, client_id, client_secret):
    """
    Retrieve historical temperature data from the Frost API.
    - station_id: Frost station id (e.g., "SN18700" for Ski Storsenter)
    - start_time, end_time: ISO 8601 formatted strings (e.g., "2025-02-07T00:00:00Z")
    - client_id: Your Frost API client ID.
    - client_secret: Your Frost API client secret (not used for authentication)
    """
    endpoint = "https://frost.met.no/observations/v0.jsonld"
    params = {
        "sources": station_id,
        "elements": "air_temperature",
        "referencetime": f"{start_time}/{end_time}",
        # "timeformat": "iso",  # Optional; remove if it causes issues
        "limit": 1000  # Adjust as needed
    }

    
    # Use client_id for authentication; the password is left empty as required.
    response = requests.get(endpoint, params=params, auth=(client_id, ""))
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
        df_temp["time"] = pd.to_datetime(df_temp["time"])
    return df_temp


# Load the energy CSV and temperature CSV
energy_df = pd.read_csv("energy_history.csv")
temp_df = pd.read_csv("temperature_history.csv")

# Convert time columns to datetime
energy_df['startTime'] = pd.to_datetime(energy_df['startTime'])
temp_df['time'] = pd.to_datetime(temp_df['time'])

# If energy_df's time isn't already on the hour, round it to the hour.
# Here we create a new column 'time' in energy_df as the floored startTime.
energy_df['time'] = energy_df['startTime'].dt.floor('H')

# Merge the two DataFrames on the 'time' column
merged_df = pd.merge(energy_df, temp_df, on='time', how='left')

# Optionally, drop or rearrange columns as needed.
# For example, you might want to drop the extra 'startTime' column if you prefer just one time column.
# merged_df = merged_df.drop(columns=['startTime'])

# Save the merged DataFrame to a new CSV file
merged_df.to_csv("energy_and_temperature.csv", index=False)
print("Merged data exported to energy_and_temperature.csv")

"""
if __name__ == "__main__":
    # For testing, use a smaller time range first (adjust as needed later)
    start_time = "2025-02-07T00:00:00Z"
    end_time   = "2025-02-23T00:00:00Z"
    
    station_id = "SN17820"  # Update if necessary
    client_id = "b8ad9a14-3215-41a0-9a1a-7c11cf666b8e"
    client_secret = "ce74e78a-3107-47fe-b10b-b7eb69b0c5cf"  # Not used for authentication

    temp_df = get_historical_temperature(station_id, start_time, end_time, client_id, client_secret)
    print(temp_df.head())
    temp_df.set_index('time', inplace=True)
    hourly_df = temp_df.resample('H').mean().reset_index()
    hourly_df.to_csv("temperature_history.csv", index=False)
    print("Temperature data exported to temperature_history.csv")
"""
"""
{
    "@type" : "SensorSystem",
    "id" : "SN17820",
    "name" : "E6 NØSTVET",
    "shortName" : "E6 Nøstvet",
    "country" : "Norge",
    "countryCode" : "NO",
    "geometry" : {
      "@type" : "Point",
      "coordinates" : [ 10.832, 59.7718 ],
      "nearest" : false
    },
    "masl" : 111,
    "validFrom" : "2019-01-24T00:00:00.000Z",
    "county" : "AKERSHUS",
    "countyId" : 32,
    "municipality" : "NORDRE FOLLO",
    "municipalityId" : 3207,
    "ontologyId" : 0,
    "stationHolders" : [ "STATENS VEGVESEN" ],
    "externalIds" : [ "1798", "3000084" ],
    "wigosId" : "0-578-0-17820"
  }"""