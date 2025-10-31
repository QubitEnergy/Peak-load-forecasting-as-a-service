import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from datetime import datetime, timedelta

# Set visualization style
plt.style.use('ggplot')
sns.set_palette("viridis")
sns.set_context("talk")

# Read the data
df = pd.read_csv('all_minute_data.csv')

# Display column names to check what's available
print("Available columns in the dataset:")
print(df.columns.tolist())

# Identify timestamp column - look for column containing 'time' or 'date'
timestamp_cols = [col for col in df.columns if 'time' in col.lower() or 'date' in col.lower()]
if timestamp_cols:
    timestamp_col = timestamp_cols[0]
    print(f"Using '{timestamp_col}' as timestamp column")
else:
    # If no obvious timestamp column, use the first column and warn user
    timestamp_col = df.columns[0]
    print(f"Warning: No obvious timestamp column found. Using first column '{timestamp_col}' as timestamp column")

# Data preparation
# Convert timestamp to datetime
# Read the data with correct delimiter
df = pd.read_csv('all_minute_data.csv', sep=';')
# Print column names to see what's available
print("\nActual columns after loading with semicolon delimiter:")
print(df.columns.tolist())

# Assuming 'time' is the timestamp column
if 'time' in df.columns:
    df['timestamp'] = pd.to_datetime(df['time'])
    df.set_index('timestamp', inplace=True)
else:
    # If 'time' isn't found, try to identify a timestamp column
    timestamp_cols = [col for col in df.columns if 'time' in col.lower() or 'date' in col.lower()]
    if timestamp_cols:
        df['timestamp'] = pd.to_datetime(df[timestamp_cols[0]])
        df.set_index('timestamp', inplace=True)
    else:
        print("Error: Cannot find timestamp column. Please check the file format.")
        exit(1)
# Extract date components for later analysis
df['hour'] = df.index.hour
df['minute'] = df.index.minute
df['day'] = df.index.day
df['month'] = df.index.month
df['weekday'] = df.index.weekday  # 0 is Monday, 6 is Sunday
df['date'] = df.index.date
df['is_weekend'] = df['weekday'].apply(lambda x: 1 if x >= 5 else 0)  # Flag for weekends

# Identify the power consumption column - look for 'active' and 'power'
power_cols = [col for col in df.columns if 'active' in col.lower() and 'power' in col.lower() and 'neg' not in col.lower()]
if power_cols:
    power_col = power_cols[0]
    print(f"Using '{power_col}' as power consumption column")
else:
    # If no obvious power column, try to find any column with 'power' in it
    power_cols = [col for col in df.columns if 'power' in col.lower() and 'neg' not in col.lower()]
    if power_cols:
        power_col = power_cols[0]
        print(f"Using '{power_col}' as power consumption column")
    else:
        # If still no power column, use the first numeric column that's not a date component
        for col in df.columns:
            if col not in ['hour', 'minute', 'day', 'month', 'weekday', 'is_weekend'] and pd.api.types.is_numeric_dtype(df[col]):
                power_col = col
                print(f"Warning: No obvious power column found. Using '{power_col}' as power consumption column")
                break

print(f"Data ranges from {df.index.min()} to {df.index.max()}")
print(f"Total number of records: {len(df)}")

# Check for missing data points
total_minutes = int((df.index.max() - df.index.min()).total_seconds() / 60) + 1
missing_percentage = (1 - len(df) / total_minutes) * 100
print(f"Missing data: {missing_percentage:.2f}%")

# Basic statistics for active power consumption
power_stats = df[power_col].describe()
print(f"\n{power_col} Statistics (W):")
print(power_stats)

# ===========================================
# 1. DAILY CONSUMPTION PROFILES
# ===========================================

# Function to plot daily consumption
def plot_daily_consumption(data, date):
    day_data = data[data.index.date == date]
    if len(day_data) == 0:
        print(f"No data available for {date}")
        return
    
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(day_data.index, day_data[power_col], linewidth=2)
    
    # Format x-axis to show hours
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.set_xlim(day_data.index.min(), day_data.index.max())
    
    # Add grid and labels
    ax.grid(True, alpha=0.3)
    ax.set_title(f'Power Consumption on {date}', fontsize=16)
    ax.set_xlabel('Time of Day', fontsize=14)
    ax.set_ylabel(f'{power_col} (W)', fontsize=14)
    
    # Highlight anomalies (values above 95th percentile for this day)
    threshold = day_data[power_col].quantile(0.95)
    anomalies = day_data[day_data[power_col] > threshold]
    if not anomalies.empty:
        ax.scatter(anomalies.index, anomalies[power_col], color='red', s=50, 
                   label=f'Potential anomalies (>{threshold:.0f}W)')
        ax.legend()
    
    plt.tight_layout()
    plt.savefig(f'daily_consumption_{date}.png')
    plt.close()
    print(f"Plot saved for {date}")

# Sample a weekday and weekend day
all_dates = sorted(np.unique(df.index.date))
# Find a weekday and weekend day with complete data
weekday_sample = None
weekend_sample = None

for date in all_dates:
    day_data = df[df.index.date == date]
    # Check if we have at least 23 hours of data (1380 minutes)
    if len(day_data) >= 1380:
        weekday = pd.to_datetime(date).weekday()
        if weekday < 5 and weekday_sample is None:
            weekday_sample = date
        elif weekday >= 5 and weekend_sample is None:
            weekend_sample = date
        
        # Break if we found both
        if weekday_sample and weekend_sample:
            break

# Plot sample days
if weekday_sample:
    plot_daily_consumption(df, weekday_sample)
if weekend_sample:
    plot_daily_consumption(df, weekend_sample)

# ===========================================
# 2. HOURLY AGGREGATIONS
# ===========================================

# Create hourly resampled data for heatmap
df_hourly = df.resample('H')[power_col].mean().reset_index()
df_hourly['date'] = df_hourly['timestamp'].dt.date
df_hourly['hour'] = df_hourly['timestamp'].dt.hour

# Create a pivot table for the heatmap (days x hours)
pivot_df = df_hourly.pivot_table(index='date', columns='hour', values=power_col)

# Plot heatmap
plt.figure(figsize=(15, 10))
sns.heatmap(pivot_df, cmap='viridis', linewidths=0.5)
plt.title('Hourly Power Consumption Heatmap', fontsize=16)
plt.xlabel('Hour of Day', fontsize=14)
plt.ylabel('Date', fontsize=14)
plt.savefig('hourly_consumption_heatmap.png')
plt.close()
print("Hourly heatmap saved")

# Compare weekday vs weekend hourly profiles
weekday_profile = df[df['is_weekend'] == 0].groupby('hour')[power_col].mean()
weekend_profile = df[df['is_weekend'] == 1].groupby('hour')[power_col].mean()

plt.figure(figsize=(12, 6))
plt.plot(weekday_profile.index, weekday_profile.values, 'b-', linewidth=2, label='Weekdays')
plt.plot(weekend_profile.index, weekend_profile.values, 'r-', linewidth=2, label='Weekends')
plt.title('Average Hourly Consumption: Weekdays vs Weekends', fontsize=16)
plt.xlabel('Hour of Day', fontsize=14)
plt.ylabel(f'Average {power_col} (W)', fontsize=14)
plt.grid(True, alpha=0.3)
plt.legend()
plt.savefig('weekday_vs_weekend.png')
plt.close()
print("Weekday vs weekend comparison saved")

# ===========================================
# 3. PEAK USAGE ANALYSIS
# ===========================================

# Determine peak times for each day
daily_peaks = df.groupby('date')[power_col].agg(['max', 'idxmax'])
daily_peaks['peak_hour'] = pd.to_datetime(daily_peaks['idxmax']).dt.hour
daily_peaks['peak_day_of_week'] = pd.to_datetime(daily_peaks.index).dayofweek
daily_peaks['is_weekend'] = daily_peaks['peak_day_of_week'].apply(lambda x: 'Weekend' if x >= 5 else 'Weekday')

# Plot peak times distribution
plt.figure(figsize=(12, 6))
sns.histplot(data=daily_peaks, x='peak_hour', hue='is_weekend', bins=24, 
             palette=['blue', 'red'], alpha=0.7, multiple='stack')
plt.title('Distribution of Peak Consumption Hours', fontsize=16)
plt.xlabel('Hour of Day', fontsize=14)
plt.ylabel('Frequency', fontsize=14)
plt.grid(True, alpha=0.3)
plt.savefig('peak_hours_distribution.png')
plt.close()
print("Peak hours distribution saved")

# Plot magnitude of daily peaks
plt.figure(figsize=(12, 6))
sns.scatterplot(data=daily_peaks.reset_index(), x='date', y='max', hue='is_weekend', 
                palette=['blue', 'red'], alpha=0.7, s=80)
plt.title('Daily Peak Consumption Magnitude', fontsize=16)
plt.xlabel('Date', fontsize=14)
plt.ylabel(f'Peak {power_col} (W)', fontsize=14)
plt.xticks(rotation=45)
plt.grid(True, alpha=0.3)
plt.savefig('daily_peak_magnitude.png')
plt.close()
print("Daily peak magnitude plot saved")

# ===========================================
# 4. ANOMALY DETECTION
# ===========================================

# Calculate rolling statistics for anomaly detection
df[f'{power_col}_rolling_mean'] = df[power_col].rolling(window=30, min_periods=1).mean()
df[f'{power_col}_rolling_std'] = df[power_col].rolling(window=30, min_periods=1).std()

# Define anomalies as values that exceed 3 standard deviations from the rolling mean
df['upper_bound'] = df[f'{power_col}_rolling_mean'] + 3 * df[f'{power_col}_rolling_std']
df['is_anomaly'] = df[power_col] > df['upper_bound']

# Count total anomalies
anomaly_count = df['is_anomaly'].sum()
print(f"\nNumber of potential anomalies detected: {anomaly_count} ({anomaly_count/len(df)*100:.2f}%)")

# Calculate rapid changes (potential anomalies)
df['power_change'] = df[power_col].diff()
df['is_rapid_increase'] = df['power_change'] > df['power_change'].quantile(0.99)
rapid_increase_count = df['is_rapid_increase'].sum()
print(f"Number of rapid power increases detected: {rapid_increase_count}")

# Plot distribution of anomalies by hour and weekday
anomalies = df[df['is_anomaly']]
anomalies_by_hour = anomalies.groupby(['hour', 'is_weekend']).size().reset_index(name='count')

plt.figure(figsize=(12, 6))
sns.barplot(data=anomalies_by_hour, x='hour', y='count', hue='is_weekend', palette=['blue', 'red'])
plt.title('Distribution of Anomalies by Hour', fontsize=16)
plt.xlabel('Hour of Day', fontsize=14)
plt.ylabel('Number of Anomalies', fontsize=14)
plt.grid(True, alpha=0.3)
plt.savefig('anomalies_by_hour.png')
plt.close()
print("Anomalies by hour plot saved")

# Plot the top 5 days with most anomalies
anomalies_by_day = anomalies.groupby('date').size().reset_index(name='count')
top_anomaly_days = anomalies_by_day.sort_values('count', ascending=False).head(5)
print("\nTop days with most anomalies:")
print(top_anomaly_days)

# For each top anomaly day, plot the full day with anomalies highlighted
for _, row in top_anomaly_days.iterrows():
    date = row['date']
    day_data = df[df.index.date == date]
    
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(day_data.index, day_data[power_col], linewidth=2, label='Power Consumption')
    ax.plot(day_data.index, day_data['upper_bound'], 'r--', linewidth=1, label='Anomaly Threshold')
    
    # Highlight anomalies
    day_anomalies = day_data[day_data['is_anomaly']]
    if not day_anomalies.empty:
        ax.scatter(day_anomalies.index, day_anomalies[power_col], color='red', s=50, label='Anomalies')
    
    # Format x-axis to show hours
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.set_xlim(day_data.index.min(), day_data.index.max())
    
    # Add grid and labels
    ax.grid(True, alpha=0.3)
    ax.set_title(f'Anomalies on {date} (Total: {row["count"]})', fontsize=16)
    ax.set_xlabel('Time of Day', fontsize=14)
    ax.set_ylabel(f'{power_col} (W)', fontsize=14)
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(f'anomalies_{date}.png')
    plt.close()
    print(f"Anomaly plot saved for {date}")

# ===========================================
# 5. ENERGY EFFICIENCY ANALYSIS
# ===========================================

# Analyze base load (minimum consumption per day)
daily_min = df.groupby('date')[power_col].min().reset_index()
daily_min.columns = ['date', 'base_load']

plt.figure(figsize=(12, 6))
plt.plot(daily_min['date'], daily_min['base_load'], marker='o', linestyle='-', linewidth=2)
plt.title('Daily Base Load (Minimum Consumption)', fontsize=16)
plt.xlabel('Date', fontsize=14)
plt.ylabel('Base Load (W)', fontsize=14)
plt.grid(True, alpha=0.3)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('daily_base_load.png')
plt.close()
print("Base load analysis saved")

# Calculate load duration curve
sorted_power = df[power_col].sort_values(ascending=False).reset_index(drop=True)
percentiles = np.linspace(0, 100, len(sorted_power))

plt.figure(figsize=(12, 6))
plt.plot(percentiles, sorted_power, linewidth=2)
plt.title('Load Duration Curve', fontsize=16)
plt.xlabel('Percentage of Time (%)', fontsize=14)
plt.ylabel(f'{power_col} (W)', fontsize=14)
plt.grid(True, alpha=0.3)
plt.axhline(y=sorted_power.iloc[int(len(sorted_power)*0.05)], color='r', linestyle='--', 
            label=f'5% Peak: {sorted_power.iloc[int(len(sorted_power)*0.05)]:.0f}W')
plt.axhline(y=sorted_power.iloc[int(len(sorted_power)*0.5)], color='g', linestyle='--', 
            label=f'50% Load: {sorted_power.iloc[int(len(sorted_power)*0.5)]:.0f}W')
plt.legend()
plt.tight_layout()
plt.savefig('load_duration_curve.png')
plt.close()
print("Load duration curve saved")

# ===========================================
# 6. SUMMARY REPORT
# ===========================================

# Calculate key metrics
peak_power = df[power_col].max()
avg_power = df[power_col].mean()
base_load = df.groupby('date')[power_col].min().mean()
peak_to_avg_ratio = peak_power / avg_power

print("\n===== SUMMARY REPORT =====")
print(f"Peak Power: {peak_power:.2f} W")
print(f"Average Power: {avg_power:.2f} W")
print(f"Average Base Load: {base_load:.2f} W")
print(f"Peak-to-Average Ratio: {peak_to_avg_ratio:.2f}")

# Peak hours summary
peak_hours = daily_peaks['peak_hour'].value_counts().sort_index()
top_peak_hours = peak_hours.sort_values(ascending=False).head(3)
print("\nTop 3 peak hours:")
for hour, count in top_peak_hours.items():
    print(f"  Hour {hour}: {count} days")

# Weekend vs weekday comparison
weekday_avg = df[df['is_weekend'] == 0][power_col].mean()
weekend_avg = df[df['is_weekend'] == 1][power_col].mean()
print(f"\nWeekday average consumption: {weekday_avg:.2f} W")
print(f"Weekend average consumption: {weekend_avg:.2f} W")
print(f"Weekend/Weekday ratio: {weekend_avg/weekday_avg:.2f}")

# Anomaly summary
weekday_anomalies = df[(df['is_weekend'] == 0) & (df['is_anomaly'])].shape[0]
weekend_anomalies = df[(df['is_weekend'] == 1) & (df['is_anomaly'])].shape[0]
print(f"\nWeekday anomalies: {weekday_anomalies}")
print(f"Weekend anomalies: {weekend_anomalies}")

# Power factor calculation (when reactive power exists)
reactive_cols = [col for col in df.columns if 'reactive' in col.lower() and 'power' in col.lower() and 'neg' not in col.lower()]
if reactive_cols:
    reactive_col = reactive_cols[0]
    df['apparent_power'] = np.sqrt(df[power_col]**2 + df[reactive_col]**2)
    df['power_factor'] = df[power_col] / df['apparent_power']
    avg_power_factor = df['power_factor'].mean()
    print(f"\nAverage Power Factor: {avg_power_factor:.3f}")

print("\nAnalysis completed! Check the output directory for plots.")