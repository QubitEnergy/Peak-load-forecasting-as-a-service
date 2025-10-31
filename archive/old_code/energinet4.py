import requests
import pandas as pd
import matplotlib.pyplot as plt
import urllib3

# Disable SSL warnings for testing only (not recommended for production)
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
        
        # Recurse if there's a drilldown link
        dd_link = item.get("links", {}).get("drilldown", {}).get("href")
        if dd_link:
            sub_id = dd_link.split("/")[-1]
            if sub_id != current_unit_id:
                deeper_units = get_subunits(sub_id)
                all_units.extend(deeper_units)
    
    return all_units

def flatten_units(units):
    """
    Convert the nested unit list (with datasources) into a structure
    for easy access to each subunit's Energy data link.
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
                    data_link = BASE_URL + data_link
                row["Energy Link"] = data_link
        rows.append(row)
    return rows

def fetch_energy_data(energy_link):
    """
    Fetch energy data specifically for the interval 2024-01-01 to 2025-01-01.
    Return a DataFrame with columns ["Start", "Value"] or empty if no data.
    """
    if not energy_link:
        return pd.DataFrame()
    
    # We specifically want 2024-01-01 through 2025-01-01
    time_headers = headers.copy()
    time_headers["DateIntervalFrom"] = "2024-01-01"
    time_headers["DateIntervalTo"] = "2025-01-01"
    
    try:
        resp = requests.get(energy_link, headers=time_headers, verify=False)
        if resp.status_code != 200:
            print(f"Error fetching energy data from {energy_link}: {resp.status_code}")
            return pd.DataFrame()
        
        data = resp.json()
        df = pd.DataFrame(data)
        if "Start" not in df.columns or "Value" not in df.columns:
            print("Unexpected format in energy data.")
            return pd.DataFrame()
        
        # Convert "Start" to datetime
        df["Start"] = pd.to_datetime(df["Start"], errors='coerce').dt.tz_localize(None)
        # Drop rows where "Start" is NaT
        df = df.dropna(subset=["Start"])
        
        # Filter again, just in case
        mask = (df["Start"] >= "2024-01-01") & (df["Start"] < "2025-01-01")
        df = df[mask].sort_values("Start")
        
        return df
    except Exception as e:
        print(f"Exception fetching energy data from {energy_link}: {e}")
        return pd.DataFrame()

def main():
    # 1) Start from Ski Storsenter (unit_id = "23903building")
    all_found_units = get_subunits("23903building")
    # 2) Flatten to get a DataFrame of subunits + energy link
    rows = flatten_units(all_found_units)
    df_units = pd.DataFrame(rows).drop_duplicates(subset=["Unit ID"]).reset_index(drop=True)
    
    # 3) Plot each subunit's data on a single figure
    plt.figure(figsize=(12, 6))
    
    any_data_plotted = False
    for idx, row in df_units.iterrows():
        name = row["Name"]
        energy_link = row["Energy Link"]
        energy_df = fetch_energy_data(energy_link)
        
        if not energy_df.empty:
            plt.plot(energy_df["Start"], energy_df["Value"], label=name)
            any_data_plotted = True
    
    if any_data_plotted:
        plt.title("Energy Data from 2024-01-01 to 2025-01-01")
        plt.xlabel("Time")
        plt.ylabel("Energy Consumption (kWh)")
        plt.legend(fontsize='small', loc='upper left', ncol=2)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    else:
        print("No data found in the specified interval for any subunits.")

    # 4) Optionally, export the subunits table
    df_units.to_csv("Ski_Storsenter_Subunits_Energy.csv", sep=";", index=False)
    print("Exported subunits with energy links to CSV.")

if __name__ == "__main__":
    main()
