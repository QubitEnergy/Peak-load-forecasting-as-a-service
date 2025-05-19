import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
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
        
        dd_link = item.get("links", {}).get("drilldown", {}).get("href")
        if dd_link:
            sub_id = dd_link.split("/")[-1]
            if sub_id != current_unit_id:
                deeper_units = get_subunits(sub_id)
                all_units.extend(deeper_units)
    
    return all_units

def flatten_units(units):
    """
    Convert the nested unit list into a row-based structure with data links.
    """
    rows = []
    for u in units:
        row = {
            "Unit ID": u["unit_id"],
            "Name": u["name"],
        }
        ds_map = {}
        for ds in u["datasources"]:
            label = ds.get("label", "")
            data_link = ds.get("links", {}).get("data", {}).get("href", "")
            # Build full link if it starts with "/"
            if data_link and data_link.startswith("/"):
                full_link = BASE_URL + data_link
            else:
                full_link = data_link
            ds_map[label] = full_link
        
        row["Energy Data (Type 1)"] = ds_map.get("Energy", "")
        row["Temperature Data (Type 2)"] = ds_map.get("Temperature", "")
        row["Volume Water Data (Type 3)"] = ds_map.get("Volume water", "")
        row["CO₂ Data (Type 7)"] = ds_map.get("Co2", "")
        row["Heating Degree Data (Type 8)"] = ds_map.get("Heating degree", "")
        row["Cost Data (Type 9)"] = ds_map.get("Cost", "")
        row["Peak High Data (Type 11)"] = ds_map.get("Peak High", "")
        row["Zone Cost Data (Type 47)"] = ds_map.get("Zone Cost", "")
        
        rows.append(row)
    return rows

def fetch_and_sum_energy(energy_link):
    """
    Fetch the energy data for the last year and return the total usage (kWh).
    Also returns a DataFrame of the filtered data for plotting.
    """
    if not energy_link:
        return 0.0, pd.DataFrame()
    
    try:
        resp = requests.get(energy_link, headers=headers, verify=False)
        if resp.status_code != 200:
            print(f"Error fetching energy data: {resp.status_code}")
            return 0.0, pd.DataFrame()
        
        data = resp.json()
        df = pd.DataFrame(data)
        if "Start" not in df.columns or "Value" not in df.columns:
            print("Unexpected format in energy data.")
            return 0.0, pd.DataFrame()
        
        df["Start"] = pd.to_datetime(df["Start"])
        # Remove or "localize to None" to drop time zone info
        # so that comparing with naive Timestamp.now() won't fail
        df["Start"] = df["Start"].dt.tz_localize(None)
        
        # Filter to last year
        cutoff = pd.Timestamp.now() - pd.DateOffset(years=1)
        df = df[df["Start"] >= cutoff]
        
        # Sum usage over last year
        total_usage = df["Value"].sum()
        return total_usage, df
    except Exception as e:
        print(f"Exception fetching energy data: {e}")
        return 0.0, pd.DataFrame()


# 1) Start from Ski Storsenter, "23903building"
starting_unit = "23903building"
all_found_units = get_subunits(starting_unit)

# 2) Flatten to DataFrame
rows = flatten_units(all_found_units)
df_units = pd.DataFrame(rows).drop_duplicates(subset=["Unit ID"]).reset_index(drop=True)

# 3) For each unit, fetch the last-year energy data, compute total usage
df_units["Total Usage Last Year"] = 0.0
df_units["Energy DF"] = None  # We'll store the filtered DataFrame for plotting

for i, row in df_units.iterrows():
    energy_link = row["Energy Data (Type 1)"]
    total_usage, energy_df = fetch_and_sum_energy(energy_link)
    df_units.at[i, "Total Usage Last Year"] = total_usage
    df_units.at[i, "Energy DF"] = energy_df

# 4) Identify the top usage subunits and the solar subunits
#    We'll define top usage as the top 5 by "Total Usage Last Year".
df_units_sorted = df_units.sort_values("Total Usage Last Year", ascending=False).reset_index(drop=True)

# top 5 by usage
top_5 = df_units_sorted.head(5)["Unit ID"].tolist()

# solar subunits (case-insensitive search for "solceller" in the name)
df_units_sorted["is_solar"] = df_units_sorted["Name"].str.lower().str.contains("solceller")
solar_ids = df_units_sorted[df_units_sorted["is_solar"] == True]["Unit ID"].tolist()

# Combine top usage + solar
priority_ids = set(top_5 + solar_ids)

# 5) Separate them into two groups
df_priority = df_units_sorted[df_units_sorted["Unit ID"].isin(priority_ids)].copy()
df_others = df_units_sorted[~df_units_sorted["Unit ID"].isin(priority_ids)].copy()

# 6) Plot group 1: top usage + solar
plt.figure(figsize=(12, 6))
for i, row in df_priority.iterrows():
    name = row["Name"]
    energy_df = row["Energy DF"]
    if not energy_df.empty:
        plt.plot(energy_df["Start"], energy_df["Value"], label=f"{name} (sum={row['Total Usage Last Year']:.1f})")

plt.title("Top Usage & Solar Subunits (Last Year)")
plt.xlabel("Time")
plt.ylabel("Energy Value (kWh)")
plt.legend(fontsize='small', loc='upper left')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# 7) Plot group 2: the smaller usage subunits
plt.figure(figsize=(12, 6))
for i, row in df_others.iterrows():
    name = row["Name"]
    energy_df = row["Energy DF"]
    if not energy_df.empty:
        plt.plot(energy_df["Start"], energy_df["Value"], label=f"{name} (sum={row['Total Usage Last Year']:.1f})")

plt.title("Smaller Usage Subunits (Last Year)")
plt.xlabel("Time")
plt.ylabel("Energy Value (kWh)")
plt.legend(fontsize='small', loc='upper left')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# 8) Export final table (including total usage) to CSV
df_units.to_csv("Ski_Storsenter_FullHierarchy_Usage.csv", sep=";", index=False)
print("Exported usage data to CSV.")
