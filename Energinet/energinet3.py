import requests
import pandas as pd
import urllib3

# Disable SSL warnings for testing only (not recommended in production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.energinet.net"

headers = {
    "Authorization": "Bearer 78uiaschs5kobwy9p85m5w4xvks9929e",  # Replace with your API token
    "Accept-Language": "no"
}

def get_subunits(unit_id):
    """
    Recursively fetch subunits for a given unit_id using the drilldown link.
    Returns a list of all discovered units (including the original).
    """
    url = f"{BASE_URL}/api/unit/{unit_id}"
    resp = requests.get(url, headers=headers, verify=False)
    if resp.status_code != 200:
        print(f"Error fetching unit '{unit_id}':", resp.status_code, resp.text)
        return []
    
    try:
        data = resp.json()
    except Exception as e:
        print(f"JSON decode error for unit '{unit_id}': {e}")
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
        
        # If there's a drilldown link, recurse into subunits
        dd_link = item.get("links", {}).get("drilldown", {}).get("href")
        if dd_link:
            sub_id = dd_link.split("/")[-1]
            if sub_id != current_unit_id:
                deeper_units = get_subunits(sub_id)
                all_units.extend(deeper_units)
    
    return all_units

def flatten_all_data_ranges(units):
    """
    Convert the nested unit list into a flat structure that includes,
    for each known data type, the full data link, the available date range,
    and the duration (in days) of available data.
    """
    data_types = ["Energy", "Temperature", "Volume water", "Co2", "Heating degree", "Cost", "Peak High", "Zone Cost"]
    rows = []
    for u in units:
        row = {"Unit ID": u["unit_id"], "Name": u["name"]}
        # For each data type, initialize columns with defaults
        for dt in data_types:
            row[f"{dt} Data Link"] = ""
            row[f"{dt} Date From"] = ""
            row[f"{dt} Date To"] = ""
            row[f"{dt} Duration (days)"] = None
        
        # Iterate through the datasources of the unit
        for ds in u["datasources"]:
            label = ds.get("label", "").strip()
            # Match label to one of the known data types (case-insensitive)
            for dt in data_types:
                if label.lower() == dt.lower():
                    data_link = ds.get("links", {}).get("data", {}).get("href", "")
                    if data_link and data_link.startswith("/"):
                        full_link = BASE_URL + data_link
                    else:
                        full_link = data_link
                    row[f"{dt} Data Link"] = full_link
                    available_data = ds.get("available-data", {})
                    date_from = available_data.get("date_from", "")
                    date_to = available_data.get("date_to", "")
                    row[f"{dt} Date From"] = date_from
                    row[f"{dt} Date To"] = date_to
                    try:
                        if date_from and date_to:
                            dt_from = pd.to_datetime(date_from, errors='coerce')
                            dt_to = pd.to_datetime(date_to, errors='coerce')
                            if pd.notna(dt_from) and pd.notna(dt_to):
                                duration = (dt_to - dt_from).days
                                row[f"{dt} Duration (days)"] = duration
                    except Exception as e:
                        print(f"Error computing duration for {u['unit_id']} {dt}: {e}")
        rows.append(row)
    return rows

# Starting unit for Ski Storsenter (unit_id "23903building")
starting_unit = "23903building"
all_units = get_subunits(starting_unit)
rows = flatten_all_data_ranges(all_units)
df_ranges = pd.DataFrame(rows).drop_duplicates(subset=["Unit ID"]).reset_index(drop=True)

# Display the DataFrame and export to CSV
print(df_ranges)
df_ranges.to_csv("All_Data_Ranges.csv", sep=";", index=False)
print("Exported all data ranges to CSV.")
