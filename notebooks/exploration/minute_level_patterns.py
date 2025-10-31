import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from datetime import datetime, timedelta
import os

# Read the data with correct delimiter
df = pd.read_csv('all_minute_data.csv', sep=';')
print(f"Loaded data with {df.shape[0]} rows and {df.shape[1]} columns")
print("Columns:", df.columns.tolist())

# Convert timestamp to datetime
if 'time' in df.columns:
    df['timestamp'] = pd.to_datetime(df['time'])
    df.set_index('timestamp', inplace=True)
else:
    # Try alternative column names
    time_cols = [col for col in df.columns if 'time' in col.lower()]
    if time_cols:
        df['timestamp'] = pd.to_datetime(df[time_cols[0]])
        df.set_index('timestamp', inplace=True)
    else:
        raise ValueError("No timestamp column found in the data")

# Identify the power column (active power)
if 'a' in df.columns:
    power_col = 'a'
else:
    power_cols = [col for col in df.columns if ('power' in col.lower() and 'active' in col.lower())]
    if power_cols:
        power_col = power_cols[0]
    else:
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]) and 'time' not in col.lower():
                power_col = col
                break

print(f"Using {power_col} as power consumption column")

# Identify meter_id column
if 'meter_id' in df.columns:
    meter_id_col = 'meter_id'
else:
    meter_candidates = [col for col in df.columns if 'meter' in col.lower() or 'id' in col.lower()]
    if meter_candidates:
        meter_id_col = meter_candidates[0]
        print(f"Using {meter_id_col} as meter ID column")
    else:
        raise ValueError("Cannot find meter ID column")

# Add date and time components
df['date'] = df.index.date
df['hour'] = df.index.hour
df['minute'] = df.index.minute
df['weekday'] = df.index.dayofweek  # 0=Monday, 6=Sunday
df['weekday_name'] = df.index.day_name()
df['hour_minute'] = df.index.strftime('%H:%M')
df['minutes_since_midnight'] = df['hour'] * 60 + df['minute']

# Get list of unique meter IDs
meter_ids = df[meter_id_col].unique()
print(f"Found {len(meter_ids)} unique meters: {meter_ids}")

# Create main output directory
main_output_dir = 'sensor_analysis'
if not os.path.exists(main_output_dir):
    os.makedirs(main_output_dir)
    print(f"Created main output directory: {main_output_dir}")

# Days of week for reference
days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# Create a summary comparison of all sensors
plt.figure(figsize=(15, 8))
all_sensor_means = []

for meter_id in meter_ids:
    # Get data for this meter
    meter_data = df[df[meter_id_col] == meter_id]
    
    # Calculate daily average consumption pattern
    daily_pattern = meter_data.groupby('minutes_since_midnight')[power_col].mean()
    all_sensor_means.append(daily_pattern)
    
    # Plot this sensor's average pattern
    plt.plot(daily_pattern.index, daily_pattern.values, label=f"Sensor {meter_id}", alpha=0.7)

plt.xticks(np.arange(0, 1440, 60), [f"{h:02d}:00" for h in range(24)], rotation=45)
plt.xlabel('Time of Day', fontsize=14)
plt.ylabel(f'Average {power_col} (W)', fontsize=14)
plt.title('Average Daily Consumption Pattern by Sensor', fontsize=16)
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(main_output_dir, 'all_sensors_comparison.png'))
plt.close()

# Process each meter separately
for meter_id in meter_ids:
    print(f"\nProcessing sensor: {meter_id}")
    
    # Create output directory for this meter
    output_dir = os.path.join(main_output_dir, f'sensor_{meter_id}')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Get data for this meter
    meter_data = df[df[meter_id_col] == meter_id].copy()
    
    print(f"  Data range: {meter_data.index.min()} to {meter_data.index.max()}")
    print(f"  Number of readings: {len(meter_data)}")
    
    # Check for missing data
    total_minutes = int((meter_data.index.max() - meter_data.index.min()).total_seconds() / 60) + 1
    missing_percentage = (1 - len(meter_data) / total_minutes) * 100
    print(f"  Missing data: {missing_percentage:.2f}%")
    
    # Basic statistics
    power_stats = meter_data[power_col].describe()
    print(f"\n  {power_col} Statistics:")
    print(f"    Mean: {power_stats['mean']:.2f}W")
    print(f"    Min: {power_stats['min']:.2f}W")
    print(f"    Max: {power_stats['max']:.2f}W")
    print(f"    Std Dev: {power_stats['std']:.2f}W")
    
    # 1. DAILY CONSUMPTION PROFILES BY DAY OF WEEK
    
    plt.figure(figsize=(15, 10))
    weekday_colors = plt.cm.viridis(np.linspace(0, 1, 7))
    
    # Plot average pattern for each day of week
    for day_idx, day in enumerate(days):
        # Get data for this day of week
        day_data = meter_data[meter_data['weekday_name'] == day]
        
        if day_data.empty:
            continue
        
        # Group by hour and minute, get average
        grouped = day_data.groupby('minutes_since_midnight')[power_col].mean()
        
        # Plot this day's average pattern
        plt.plot(grouped.index, grouped.values, label=day, color=weekday_colors[day_idx], linewidth=2)
    
    plt.xticks(np.arange(0, 1440, 60), [f"{h:02d}:00" for h in range(24)], rotation=45)
    plt.xlabel('Time of Day', fontsize=14)
    plt.ylabel(f'Average {power_col} (W)', fontsize=14)
    plt.title(f'Average Daily Consumption by Day of Week - Sensor {meter_id}', fontsize=16)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'daily_patterns_by_day.png'))
    plt.close()
    
    # 2. HOURLY CONSUMPTION HEATMAP
    
    # Create hourly resampled data for heatmap
    meter_hourly = meter_data.resample('H')[power_col].mean().reset_index()
    meter_hourly['date'] = meter_hourly['timestamp'].dt.date
    meter_hourly['hour'] = meter_hourly['timestamp'].dt.hour
    
    # Create a pivot table for the heatmap (days x hours)
    pivot_df = meter_hourly.pivot_table(index='date', columns='hour', values=power_col)
    
    # Plot heatmap
    plt.figure(figsize=(15, 10))
    sns.heatmap(pivot_df, cmap='viridis', linewidths=0.5)
    plt.title(f'Hourly Power Consumption Heatmap - Sensor {meter_id}', fontsize=16)
    plt.xlabel('Hour of Day', fontsize=14)
    plt.ylabel('Date', fontsize=14)
    plt.savefig(os.path.join(output_dir, 'hourly_consumption_heatmap.png'))
    plt.close()
    
    # 3. WEEKDAY VS WEEKEND COMPARISON
    
    # Compare weekday vs weekend hourly profiles
    weekday_profile = meter_data[meter_data['weekday'] < 5].groupby('hour')[power_col].mean()
    weekend_profile = meter_data[meter_data['weekday'] >= 5].groupby('hour')[power_col].mean()
    
    plt.figure(figsize=(12, 6))
    plt.plot(weekday_profile.index, weekday_profile.values, 'b-', linewidth=2, label='Weekdays')
    plt.plot(weekend_profile.index, weekend_profile.values, 'r-', linewidth=2, label='Weekends')
    plt.title(f'Average Hourly Consumption: Weekdays vs Weekends - Sensor {meter_id}', fontsize=16)
    plt.xlabel('Hour of Day', fontsize=14)
    plt.ylabel(f'Average {power_col} (W)', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(os.path.join(output_dir, 'weekday_vs_weekend.png'))
    plt.close()
    
    # 4. PEAK USAGE ANALYSIS
    
    # Determine peak times for each day
    daily_peaks = meter_data.groupby('date')[power_col].agg(['max', 'idxmax']).reset_index()
    daily_peaks['peak_hour'] = pd.to_datetime(daily_peaks['idxmax']).dt.hour
    daily_peaks['peak_day_of_week'] = pd.to_datetime(daily_peaks['date']).dt.dayofweek
    daily_peaks['is_weekend'] = daily_peaks['peak_day_of_week'].apply(lambda x: 'Weekend' if x >= 5 else 'Weekday')
    
    # Plot peak times distribution
    plt.figure(figsize=(12, 6))
    sns.histplot(data=daily_peaks, x='peak_hour', hue='is_weekend', bins=24, 
                 palette=['blue', 'red'], alpha=0.7, multiple='stack')
    plt.title(f'Distribution of Peak Consumption Hours - Sensor {meter_id}', fontsize=16)
    plt.xlabel('Hour of Day', fontsize=14)
    plt.ylabel('Frequency', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(output_dir, 'peak_hours_distribution.png'))
    plt.close()
    
    # Plot magnitude of daily peaks
    plt.figure(figsize=(12, 6))
    sns.scatterplot(data=daily_peaks, x='date', y='max', hue='is_weekend', 
                    palette=['blue', 'red'], alpha=0.7, s=80)
    plt.title(f'Daily Peak Consumption Magnitude - Sensor {meter_id}', fontsize=16)
    plt.xlabel('Date', fontsize=14)
    plt.ylabel(f'Peak {power_col} (W)', fontsize=14)
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(output_dir, 'daily_peak_magnitude.png'))
    plt.close()
    
    # 5. ANOMALY DETECTION
    
    # Calculate rolling statistics for anomaly detection
    meter_data['rolling_mean'] = meter_data[power_col].rolling(window=5, min_periods=1).mean()
    meter_data['rolling_std'] = meter_data[power_col].rolling(window=5, min_periods=1).std()
    
    # Define anomalies with different thresholds
    meter_data['anomaly_mild'] = meter_data[power_col] > (meter_data['rolling_mean'] + 2 * meter_data['rolling_std'])
    meter_data['anomaly_extreme'] = meter_data[power_col] > (meter_data['rolling_mean'] + 3 * meter_data['rolling_std'])
    
    # Calculate rapid changes
    meter_data['power_change'] = meter_data[power_col].diff()
    change_threshold = np.percentile(np.abs(meter_data['power_change'].dropna()), 99)
    meter_data['rapid_change'] = np.abs(meter_data['power_change']) > change_threshold
    
    # Count anomalies
    anomaly_count = meter_data['anomaly_mild'].sum()
    extreme_count = meter_data['anomaly_extreme'].sum()
    rapid_change_count = meter_data['rapid_change'].sum()
    
    print(f"  Anomaly detection:")
    print(f"    Mild anomalies (>2σ): {anomaly_count} ({anomaly_count/len(meter_data)*100:.2f}%)")
    print(f"    Extreme anomalies (>3σ): {extreme_count} ({extreme_count/len(meter_data)*100:.2f}%)")
    print(f"    Rapid changes (>{change_threshold:.1f}W): {rapid_change_count} ({rapid_change_count/len(meter_data)*100:.2f}%)")
    
    # Plot anomalies by hour
    anomaly_by_hour = meter_data.groupby('hour')['anomaly_mild'].sum().reset_index()
    anomaly_by_hour['extreme_anomalies'] = meter_data.groupby('hour')['anomaly_extreme'].sum().values
    anomaly_by_hour['rapid_changes'] = meter_data.groupby('hour')['rapid_change'].sum().values
    
    plt.figure(figsize=(12, 6))
    plt.bar(anomaly_by_hour['hour'] - 0.2, anomaly_by_hour['anomaly_mild'], width=0.2, 
            label='Mild Anomalies (>2σ)', color='yellow')
    plt.bar(anomaly_by_hour['hour'], anomaly_by_hour['extreme_anomalies'], width=0.2, 
            label='Extreme Anomalies (>3σ)', color='red')
    plt.bar(anomaly_by_hour['hour'] + 0.2, anomaly_by_hour['rapid_changes'], width=0.2, 
            label=f'Rapid Changes (>{change_threshold:.0f}W)', color='purple')
    plt.title(f'Distribution of Anomalies by Hour - Sensor {meter_id}', fontsize=16)
    plt.xlabel('Hour of Day', fontsize=14)
    plt.ylabel('Number of Anomalies', fontsize=14)
    plt.xticks(range(24))
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(os.path.join(output_dir, 'anomalies_by_hour.png'))
    plt.close()
    
    # Find the most anomalous days
    anomaly_by_date = meter_data.groupby('date')['anomaly_mild'].sum().reset_index()
    top_anomaly_days = anomaly_by_date.sort_values('anomaly_mild', ascending=False).head(3)
    
    print("  Top 3 days with most anomalies:")
    for i, (_, row) in enumerate(top_anomaly_days.iterrows(), 1):
        date_obj = pd.to_datetime(row['date'])
        print(f"    {i}. {date_obj.strftime('%Y-%m-%d')} ({date_obj.day_name()}): {int(row['anomaly_mild'])} anomalies")
    
    # Plot each of the top anomalous days
    for _, row in top_anomaly_days.iterrows():
        date = row['date']
        date_str = pd.to_datetime(date).strftime('%Y-%m-%d')
        weekday = pd.to_datetime(date).day_name()
        
        # Get data for this date
        date_data = meter_data[meter_data['date'] == date]
        
        plt.figure(figsize=(15, 6))
        
        # Plot consumption
        plt.plot(date_data['minutes_since_midnight'], date_data[power_col], 'b-', 
                 linewidth=1, label='Power Consumption')
        
        # Plot threshold
        plt.plot(date_data['minutes_since_midnight'], 
                date_data['rolling_mean'] + 2*date_data['rolling_std'], 
                'r--', linewidth=1, label='Anomaly Threshold (2σ)')
        
        # Highlight anomalies
        anomalies = date_data[date_data['anomaly_mild']]
        plt.scatter(anomalies['minutes_since_midnight'], anomalies[power_col], 
                   color='red', s=50, label='Anomalies')
        
        # Format plot
        plt.xticks(np.arange(0, 1440, 60), [f"{h:02d}:00" for h in range(24)], rotation=45)
        plt.xlim(0, 1440)
        plt.xlabel('Time of Day', fontsize=14)
        plt.ylabel(f'{power_col} (W)', fontsize=14)
        plt.title(f'Anomalies on {date_str} ({weekday}) - Sensor {meter_id}', fontsize=16)
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'anomalies_{date_str}.png'))
        plt.close()
    
    # 6. LOAD DURATION CURVE
    
    # Calculate load duration curve
    sorted_power = meter_data[power_col].sort_values(ascending=False).reset_index(drop=True)
    percentiles = np.linspace(0, 100, len(sorted_power))
    
    plt.figure(figsize=(12, 6))
    plt.plot(percentiles, sorted_power, linewidth=2)
    plt.title(f'Load Duration Curve - Sensor {meter_id}', fontsize=16)
    plt.xlabel('Percentage of Time (%)', fontsize=14)
    plt.ylabel(f'{power_col} (W)', fontsize=14)
    plt.grid(True, alpha=0.3)
    
    # Mark key points
    plt.axhline(y=sorted_power.iloc[int(len(sorted_power)*0.05)], color='r', linestyle='--', 
                label=f'5% Peak: {sorted_power.iloc[int(len(sorted_power)*0.05)]:.0f}W')
    plt.axhline(y=sorted_power.iloc[int(len(sorted_power)*0.5)], color='g', linestyle='--', 
                label=f'50% Load: {sorted_power.iloc[int(len(sorted_power)*0.5)]:.0f}W')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'load_duration_curve.png'))
    plt.close()
    
    # 7. SUMMARY STATISTICS TEXT FILE
    
    # Calculate additional stats
    peak_power = meter_data[power_col].max()
    avg_power = meter_data[power_col].mean()
    base_load = meter_data.groupby('date')[power_col].min().mean()
    peak_to_avg_ratio = peak_power / avg_power
    
    # Peak hours summary
    peak_hours = daily_peaks['peak_hour'].value_counts().sort_index()
    top_peak_hours = peak_hours.sort_values(ascending=False).head(3)
    
    # Weekend vs weekday comparison
    weekday_avg = meter_data[meter_data['weekday'] < 5][power_col].mean()
    weekend_avg = meter_data[meter_data['weekday'] >= 5][power_col].mean()
    
    # Write to summary file
    with open(os.path.join(output_dir, 'summary_stats.txt'), 'w') as f:
        f.write(f"SUMMARY STATISTICS FOR SENSOR {meter_id}\n")
        f.write("=" * 40 + "\n\n")
        
        f.write(f"Data Period: {meter_data.index.min().strftime('%Y-%m-%d')} to {meter_data.index.max().strftime('%Y-%m-%d')}\n")
        f.write(f"Total Readings: {len(meter_data)}\n")
        f.write(f"Missing Data: {missing_percentage:.2f}%\n\n")

        f.write("Power Consumption Metrics:\n")
        f.write(f"  Peak Power: {peak_power:.2f} W\n")
        f.write(f"  Average Power: {avg_power:.2f} W\n")
        f.write(f"  Average Base Load: {base_load:.2f} W\n")
        f.write(f"  Peak-to-Average Ratio: {peak_to_avg_ratio:.2f}\n\n")
        
        f.write("Top 3 Peak Hours:\n")
        for hour, count in top_peak_hours.items():
            f.write(f"  Hour {hour}: {count} days\n")
        f.write("\n")
        
        f.write("Weekday vs Weekend Comparison:\n")
        f.write(f"  Weekday average: {weekday_avg:.2f} W\n")
        f.write(f"  Weekend average: {weekend_avg:.2f} W\n")
        f.write(f"  Weekend/Weekday ratio: {weekend_avg/weekday_avg:.2f}\n\n")
        
        f.write("Anomaly Summary:\n")
        f.write(f"  Mild anomalies (>2σ): {anomaly_count} ({anomaly_count/len(meter_data)*100:.2f}%)\n")
        f.write(f"  Extreme anomalies (>3σ): {extreme_count} ({extreme_count/len(meter_data)*100:.2f}%)\n")
        f.write(f"  Rapid changes (>{change_threshold:.1f}W): {rapid_change_count} ({rapid_change_count/len(meter_data)*100:.2f}%)\n")

print("\nAnalysis completed! Check the output directories for results.")    