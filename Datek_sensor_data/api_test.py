import pandas as pd
import matplotlib.pyplot as plt

# 1. Load and prepare your merged CSV
df = pd.read_csv("energy_and_temperature.csv")
df["time"] = pd.to_datetime(df["time"])
df = df.sort_values(by="time")

# 2. Identify unique meters in your dataset
meters = df["meter_id"].unique()

# 3. Create one subplot per meter
fig, axs = plt.subplots(len(meters), 1, figsize=(12, 5 * len(meters)), sharex=True)
# If there's only one meter, axs won't be a list, so make it a list for consistent handling
if len(meters) == 1:
    axs = [axs]

for i, meter in enumerate(meters):
    # Filter data for just this meter
    meter_df = df[df["meter_id"] == meter]
    
    # Left axis: Energy usage
    ax1 = axs[i]
    ax1.set_title(f"Meter: {meter}")
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Energy Usage (W)", color="blue")
    line1 = ax1.plot(meter_df["time"], meter_df["import"], 
                     color="blue", marker="o", label="Energy Usage (import)")
    ax1.tick_params(axis='y', labelcolor="blue")

    # Right axis: Temperature
    ax2 = ax1.twinx()
    ax2.set_ylabel("Temperature (°C)", color="red")
    line2 = ax2.plot(meter_df["time"], meter_df["air_temperature"], 
                     color="red", marker="x", label="Air Temperature")
    ax2.tick_params(axis='y', labelcolor="red")
    
    # Combine legends (from both y-axes)
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left")

plt.tight_layout()
plt.show()
