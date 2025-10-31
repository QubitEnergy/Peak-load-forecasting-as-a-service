import requests
import pandas as pd
import matplotlib.pyplot as plt

# Define API endpoints for the desired types:
drilldown_url = "https://www.energinet.net/api/unit/23903building"

# Set up the headers with your actual token.
headers = {
    "Authorization": "Bearer 78uiaschs5kobwy9p85m5w4xvks9929e",  # Replace with your API token
    "Accept-Language": "no"
}

# Perform the API call to retrieve sub-building units
response = requests.get(drilldown_url, headers=headers, verify=False)
if response.status_code != 200:
    print("Error fetching drilldown data:", response.status_code, response.text)
    exit()

try:
    subunits_data = response.json()
except Exception as e:
    print("Error decoding JSON:", e)
    exit()

# Prepare a list to store the sub-building details
subunits_list = []

# Loop through each subunit (if any)
for subunit in subunits_data:
    unit_id = subunit.get("unit_id", "")
    name = subunit.get("name", "")
    
    # Each subunit has a "datasources" field that is a list of available measurement types
    datasources = subunit.get("datasources", [])
    ds_info = {}  # Dictionary to store API link for each type by label
    
    for ds in datasources:
        dtype = ds.get("type", "")
        label = ds.get("label", "")
        data_link = ds.get("links", {}).get("data", {}).get("href", "")
        ds_info[label] = data_link
    
    subunits_list.append({
        "Unit ID": unit_id,
        "Name": name,
        "Energy Data (Type 1)": ds_info.get("Energy", ""),
        "Temperature Data (Type 2)": ds_info.get("Temperature", ""),
        "Volume Water Data (Type 3)": ds_info.get("Volume water", ""),
        "CO₂ Data (Type 7)": ds_info.get("Co2", ""),
        "Heating Degree Data (Type 8)": ds_info.get("Heating degree", ""),
        "Cost Data (Type 9)": ds_info.get("Cost", ""),
        "Peak High Data (Type 11)": ds_info.get("Peak High", ""),
        "Zone Cost Data (Type 47)": ds_info.get("Zone Cost", "")
    })

# Convert the list into a DataFrame
df = pd.DataFrame(subunits_list)

# Optionally, print the DataFrame to inspect it
print(df)

# Export the DataFrame to an Excel file
df.to_csv("Ski_Storsenter_Subbuildings.csv", index=False, sep=";")
print("Excel file 'Ski_Storsenter_Subbuildings.csv' created successfully.")

