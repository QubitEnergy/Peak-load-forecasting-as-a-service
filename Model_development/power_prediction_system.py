import pandas as pd
import numpy as np
import datetime
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

class PowerPeakPredictor:
    """
    A class implementing the paper's methodology for peak load prediction.
    This system predicts peaks 30 minutes in advance to give clients time to react.
    """
    
    def __init__(self):
        """Initialize the predictor with default parameters"""
        self.time_intervals = []
        self.base_load_threshold = None
        self.interval_models = {}
        self.timing_models = {}
        self.scaler = StandardScaler()
        self.is_trained = False


    def extract_time_intervals(self, df, meter_id=None):
        """
        Extract time intervals based on the methodology in the paper.
        Uses clustering to identify peak and valley hours.
        """
        if meter_id:
            df = df[df['meter_id'] == meter_id]
            
        # Group data by hour of day to find patterns
        hourly_df = df.groupby(df['time'].dt.hour)['import'].agg(['mean', 'max']).reset_index()
        hourly_df.columns = ['hour', 'avg_import', 'max_import']
        
        # Find local minima (valleys) to establish interval boundaries
        valleys = []
        for i in range(1, 23):
            if (hourly_df.loc[i, 'avg_import'] < hourly_df.loc[i-1, 'avg_import'] and
                hourly_df.loc[i, 'avg_import'] < hourly_df.loc[i+1, 'avg_import']):
                valleys.append(i)
        
        # Ensure complete day coverage
        all_valleys = [0] + valleys + [23]
        all_valleys.sort()
        
        # Create time intervals
        self.time_intervals = []
        for i in range(len(all_valleys) - 1):
            self.time_intervals.append({
                'start': all_valleys[i],
                'end': all_valleys[i+1],
                'label': f'Interval {i+1}'
            })
            
        print(f"Identified {len(self.time_intervals)} time intervals:")
        for interval in self.time_intervals:
            print(f"  {interval['label']}: {interval['start']}:00 - {interval['end']}:00")
            
        return self.time_intervals
    
    def separate_base_peak_load(self, df, meter_id=None):
        """
        Separate the load into base load and peak load based on the paper's methodology.
        Uses the median as the boundary between base and peak load.
        """
        if meter_id:
            df = df[df['meter_id'] == meter_id]
        
        # Calculate the median as the boundary between base and peak
        self.base_load_threshold = df['import'].median()
        print(f"Base load threshold set at {self.base_load_threshold}")
        
        # Add base/peak classification to dataframe
        df['is_peak'] = df['import'] > self.base_load_threshold
        df['peak_amount'] = np.where(df['is_peak'], 
                                     df['import'] - self.base_load_threshold, 
                                     0)
        
        return df
    
    # Update feature engineering to work with segments
    def train_models(self, feature_df):
        """
        Train separate models for each time interval to predict:
        1. Peak amount
        2. Peak timing
        
        Based on the paper's methodology of separate modeling.
        """
        for interval_idx in feature_df['interval'].unique():
            interval_data = feature_df[feature_df['interval'] == interval_idx]
            
            if len(interval_data) < 10:  # Need sufficient data to train
                print(f"Not enough data for interval {interval_idx}, skipping")
                continue
                
            # Prepare features for amount prediction
            amount_features = [col for col in interval_data.columns if 
                            'lag' in col and 'peak_hour' not in col]
            
            X_amount = interval_data[amount_features]
            y_amount = interval_data['peak_amount']
            
            # Scale features
            X_amount_scaled = self.scaler.fit_transform(X_amount)
            
            # Train amount prediction model
            amount_model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=3,
                learning_rate=0.1,
                random_state=42
            )
            amount_model.fit(X_amount_scaled, y_amount)
            self.interval_models[interval_idx] = {
                'amount_model': amount_model,
                'amount_features': amount_features,
                'amount_scaler': self.scaler
            }
            
            # Prepare features for timing prediction
            timing_features = [col for col in interval_data.columns if 
                            'lag' in col]
            
            X_timing = interval_data[timing_features]
            y_timing = interval_data['peak_hour']
            
            # Scale features
            X_timing_scaled = self.scaler.fit_transform(X_timing)
            
            # Train timing prediction model
            timing_model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=3,
                learning_rate=0.1,
                random_state=42
            )
            timing_model.fit(X_timing_scaled, y_timing)
            self.interval_models[interval_idx]['timing_model'] = timing_model
            self.interval_models[interval_idx]['timing_features'] = timing_features
            self.interval_models[interval_idx]['timing_scaler'] = self.scaler
        
        self.is_trained = True
        print(f"Trained models for {len(self.interval_models)} intervals")

    def predict_peaks(self, current_data, lookback_data):
        """
        Predict peak amount and timing for upcoming intervals.
        Provides 30-minute advance warning.
        
        Parameters:
        -----------
        current_data: DataFrame with latest measurements
        lookback_data: DataFrame with historical data for feature generation
        
        Returns:
        --------
        predictions: Dict of predictions for each interval
        """
        if not self.is_trained:
            raise ValueError("Models must be trained before prediction")
        
        # Get current hour and determine active interval
        current_time = current_data['time'].iloc[-1]
        current_hour = current_time.hour
        
        # Identify which intervals are coming up in the next few hours
        upcoming_intervals = []
        
        for idx, interval in enumerate(self.time_intervals):
            if current_hour < interval['start']:
                # This interval is later today
                upcoming_intervals.append(idx)
            elif current_hour >= interval['start'] and current_hour < interval['end']:
                # We're currently in this interval, include it
                upcoming_intervals.append(idx)
        
        # Prepare features for prediction
        prediction_features = self.prepare_features(
            pd.concat([lookback_data, current_data]),
            lookback_days=3,
            lookback_week=True
        )
        
        # Generate predictions
        predictions = {}
        for interval_idx in upcoming_intervals:
            if interval_idx not in self.interval_models:
                continue
                
            # Get latest feature row for this interval
            latest_features = prediction_features[
                prediction_features['interval'] == interval_idx
            ].iloc[-1]
            
            # Predict peak amount
            model_info = self.interval_models[interval_idx]
            
            # Extract and scale amount features
            X_amount = latest_features[model_info['amount_features']].values.reshape(1, -1)
            X_amount_scaled = model_info['amount_scaler'].transform(X_amount)
            
            # Predict amount
            predicted_amount = model_info['amount_model'].predict(X_amount_scaled)[0]
            
            # Extract and scale timing features
            X_timing = latest_features[model_info['timing_features']].values.reshape(1, -1)
            X_timing_scaled = model_info['timing_scaler'].transform(X_timing)
            
            # Predict timing
            predicted_hour = model_info['timing_model'].predict(X_timing_scaled)[0]
            
            # Calculate full predicted peak
            total_predicted = self.base_load_threshold + max(0, predicted_amount)
            
            # Calculate minutes until peak
            interval = self.time_intervals[interval_idx]
            predicted_datetime = current_time.replace(hour=int(predicted_hour), minute=0)
            
            # If predicted time is earlier today, add a day
            if predicted_datetime < current_time:
                predicted_datetime += datetime.timedelta(days=1)
                
            minutes_until_peak = (predicted_datetime - current_time).total_seconds() / 60
            
            # Only include if peak is still in the future and within current interval
            interval_start_hour, interval_end_hour = interval['start'], interval['end']
            predicted_hour_in_interval = interval_start_hour <= predicted_hour < interval_end_hour
            
            # Include 30-minute advance warning
            if minutes_until_peak >= 30 and predicted_hour_in_interval:
                predictions[interval['label']] = {
                    'predicted_amount': round(predicted_amount, 2),
                    'predicted_hour': round(predicted_hour, 2),
                    'total_predicted_peak': round(total_predicted, 2),
                    'minutes_until_peak': round(minutes_until_peak),
                    'interval_start': interval_start_hour,
                    'interval_end': interval_end_hour
                }
        
        return predictions
        
    def visualize_prediction(self, df, predictions, meter_id=None):
        """
        Visualize current usage and predictions
        """
        if meter_id:
            df = df[df['meter_id'] == meter_id].copy()
            
        # Get last 24 hours of data
        last_day = df.sort_values('time').tail(24)
        
        # Plot actual usage
        plt.figure(figsize=(12, 6))
        plt.plot(last_day['time'], last_day['import'], 'b-', label='Actual Usage')
        
        # Plot base load threshold
        plt.axhline(y=self.base_load_threshold, color='gray', linestyle='--', label='Base Load Threshold')
        
        # Add prediction markers
        current_time = last_day['time'].iloc[-1]
        for interval, pred in predictions.items():
            peak_time = current_time + datetime.timedelta(minutes=pred['minutes_until_peak'])
            plt.scatter(peak_time, pred['total_predicted_peak'], color='red', s=100, marker='^')
            plt.annotate(f"Predicted Peak: {pred['total_predicted_peak']}",
                       (peak_time, pred['total_predicted_peak']),
                       xytext=(10, 10), textcoords='offset points')
        
        plt.title('Power Usage with Peak Predictions')
        plt.xlabel('Time')
        plt.ylabel('Power (kW)')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        
        return plt
        
    def fit(self, df, meter_id=None):
        """
        Complete training pipeline based on paper methodology
        """
        # Process timestamps
        df['time'] = pd.to_datetime(df['time'])
        
        # 1. Extract time intervals
        self.extract_time_intervals(df, meter_id)
        
        # 2. Separate base and peak load
        processed_df = self.separate_base_peak_load(df, meter_id)
        
        # 3. Prepare features for model training
        feature_df = self.prepare_features(processed_df, meter_id)
        
        # 4. Train interval-specific models
        self.train_models(feature_df)
        
        return self


    def handle_data_gaps(self, df):
        """
        Identify gaps in time series data and segment into continuous chunks
        """
        # Convert timestamps to datetime if not already
        df['time'] = pd.to_datetime(df['time'])
        
        # Process each meter separately
        processed_data = {}
        
        for meter in df['meter_id'].unique():
            meter_data = df[df['meter_id'] == meter].copy()
            
            # Sort chronologically
            meter_data = meter_data.sort_values('time')
            
            # Find gaps (timestamps more than 1 hour apart)
            meter_data['time_diff'] = meter_data['time'].diff().dt.total_seconds() / 3600
            
            # Flag rows starting new segments (after a gap)
            meter_data['new_segment'] = (meter_data['time_diff'] > 1.5) | meter_data['time_diff'].isna()
            meter_data['segment_id'] = meter_data['new_segment'].cumsum()
            
            # Only keep segments with at least 72 hours (3 days) of data
            segment_lengths = meter_data.groupby('segment_id').size()
            valid_segments = segment_lengths[segment_lengths >= 72].index
            
            valid_data = meter_data[meter_data['segment_id'].isin(valid_segments)]
            
            if len(valid_data) > 0:
                processed_data[meter] = valid_data
        
        return processed_data

    def train_with_limited_data(self, feature_df):
        """
        Train models with limited data, using simpler models and more robust approach
        """
        models = {}
        
        # For each interval, train separate models
        for interval_idx in feature_df['interval'].unique():
            interval_data = feature_df[feature_df['interval'] == interval_idx]
            
            if len(interval_data) < 5:  # Need at least 5 data points
                print(f"Not enough data for interval {interval_idx}, skipping")
                continue
            
            # Determine available features based on data
            lag_features = [col for col in interval_data.columns if 'lag' in col]
            
            if not lag_features:
                print(f"No lag features available for interval {interval_idx}, skipping")
                continue
            
            # Train amount prediction model
            X_amount = interval_data[lag_features]
            y_amount = interval_data['peak_amount']
            
            # Scale features
            amount_scaler = StandardScaler()
            X_amount_scaled = amount_scaler.fit_transform(X_amount)
            
            amount_model = GradientBoostingRegressor(
                n_estimators=50,  # Reduce complexity for small datasets
                max_depth=2,
                learning_rate=0.1,
                random_state=42
            )
            amount_model.fit(X_amount_scaled, y_amount)
            
            # Train timing prediction model
            y_timing = interval_data['peak_hour']
            
            # Scale features for timing model
            timing_scaler = StandardScaler()
            X_timing_scaled = timing_scaler.fit_transform(X_amount)
            
            timing_model = GradientBoostingRegressor(
                n_estimators=50,
                max_depth=2,
                learning_rate=0.1,
                random_state=42
            )
            timing_model.fit(X_timing_scaled, y_timing)
            
            models[interval_idx] = {
                'amount_model': amount_model,
                'timing_model': timing_model,
                'features': lag_features,
                'amount_scaler': amount_scaler,
                'timing_scaler': timing_scaler
            }
        
        self.interval_models = models
        self.is_trained = len(models) > 0
        
        print(f"Trained {len(models)} interval models with limited data")
        return models

    def predict_with_fallbacks(self, current_data, lookback_data=None):
        """
        Make predictions with fallback options when data is limited
        """
        if lookback_data is None:
            lookback_data = current_data
        
        predictions = {}
        
        # Get current hour
        current_time = pd.to_datetime(current_data['time'].iloc[-1])
        current_hour = current_time.hour
        
        # Add hour column to current data if needed
        if 'hour' not in current_data.columns:
            current_data = current_data.copy()
            current_data['hour'] = current_data['time'].dt.hour
        
        # Find upcoming intervals
        for interval_idx, interval in enumerate(self.time_intervals):
            # Only predict for current or upcoming intervals
            if current_hour <= interval['end'] and interval_idx in self.interval_models:
                try:
                    # Try full model prediction
                    model_info = self.interval_models[interval_idx]
                    
                    # Prepare features
                    feature_data = self.prepare_features(
                        pd.concat([lookback_data, current_data]), 
                        lookback_days=min(3, len(lookback_data) // 24),  # Adapt to available data
                        lookback_week=len(lookback_data) >= 24*7  # Only use week lag if we have enough data
                    )
                    
                    # Filter for the relevant interval
                    interval_features = feature_data[feature_data['interval'] == interval_idx]
                    
                    if len(interval_features) > 0:
                        # Get the most recent feature row
                        latest_features = interval_features.iloc[-1]
                        
                        # Extract and prepare features
                        X_amount = latest_features[model_info['features']].values.reshape(1, -1)
                        X_amount_scaled = model_info['amount_scaler'].transform(X_amount)
                        
                        # Make predictions
                        predicted_amount = model_info['amount_model'].predict(X_amount_scaled)[0]
                        predicted_hour = model_info['timing_model'].predict(X_amount_scaled)[0]
                        ions[f'Interval {interval_idx+1}'] = {
                            'predicted_amount': max(0, predicted_amount),
                            'predicted_hour': predicted_hour,
                            'total_predicted_peak': self.base_load_threshold + max(0, predicted_amount),
                            'reliability': 'high',
                            'interval': interval
                        }
                        continue  # Skip to next interval if successful
                except Exception as e:
                    print(f"Warning: Full prediction failed for interval {interval_idx}: {e}")
                
                # Fallback: Use simple statistics if model prediction fails
                try:
                    # Filter for data in this interval
                    interval_mask = (lookback_data['hour'] >= interval['start']) & (lookback_data['hour'] < interval['end'])
                    interval_data = lookback_data[interval_mask]
                    
                    if len(interval_data) > 0:
                        # Calculate average peak
                        avg_peak = interval_data['import'].mean()
                        max_hour = interval_data.loc[interval_data['import'].idxmax(), 'hour']
                        
                        predictions[f'Interval {interval_idx+1}'] = {
                            'predicted_amount': max(0, avg_peak - self.base_load_threshold),
                            'predicted_hour': max_hour,
                            'total_predicted_peak': avg_peak,
                            'reliability': 'low',
                            'interval': interval
                        }
                except Exception as e:
                    print(f"Warning: Even fallback prediction failed for interval {interval_idx}: {e}")
        
        return predictions

    def robust_peak_prediction_pipeline(self, data_file):
        """
        Complete pipeline for robust peak prediction with handling for data quality issues
        """
        # Load data
        df = pd.read_csv(data_file)
        df['time'] = pd.to_datetime(df['time'])
        
        # Handle data gaps
        processed_data = self.handle_data_gaps(df)
        
        if not processed_data:
            raise ValueError("No valid data segments found in any meter")
        
        # Select the meter with most data
        best_meter = max(processed_data.keys(), key=lambda k: len(processed_data[k]))
        meter_data = processed_data[best_meter]
        
        print(f"Selected meter {best_meter} with {len(meter_data)} records for analysis")
        
        # Extract time intervals
        self.extract_time_intervals(meter_data, meter_id=best_meter)
        
        # Determine base load threshold
        self.separate_base_peak_load(meter_data, meter_id=best_meter)
        
        # Prepare features
        feature_df = self.prepare_features(meter_data, meter_id=best_meter)
        
        # Train models with limited data approach
        self.train_with_limited_data(feature_df)
        
        # Get current data for prediction
        current_data = meter_data.sort_values('time').tail(24)  # Last 24 hours
        
        # Make predictions
        predictions = self.predict_with_fallbacks(current_data, meter_data)
        
        return predictions, self.time_intervals, self.base_load_threshold

# Example usage:

# Load data
df = pd.read_csv('energy_and_temperature.csv')
df['time'] = pd.to_datetime(df['time'])

# Check for data completeness in the target meter
meter_id = 'KGdRbnJc'
meter_data = df[df['meter_id'] == meter_id].copy()
meter_data = meter_data.sort_values('time')

# Find gaps in the data
meter_data['time_diff'] = meter_data['time'].diff().dt.total_seconds() / 3600
gaps = meter_data[meter_data['time_diff'] > 1.5]

if len(gaps) > 0:
    print(f"Found {len(gaps)} gaps in the data for meter {meter_id}")
    print(f"Largest gap: {meter_data['time_diff'].max():.1f} hours")
    
    # Create segment IDs to identify continuous data chunks
    meter_data['new_segment'] = (meter_data['time_diff'] > 1.5) | meter_data['time_diff'].isna()
    meter_data['segment_id'] = meter_data['new_segment'].cumsum()
    
    # Count rows in each segment
    segment_counts = meter_data.groupby('segment_id').size()
    print("Data segments:", segment_counts.to_dict())
    
    # Find the largest continuous segment
    largest_segment = segment_counts.idxmax()
    print(f"Using largest continuous segment (ID: {largest_segment}) with {segment_counts[largest_segment]} records")
    
    # Filter to only this segment
    meter_data = meter_data[meter_data['segment_id'] == largest_segment]
    
    # Update the full dataframe to only include this segment for the target meter
    df = df[~((df['meter_id'] == meter_id) & (~df.index.isin(meter_data.index)))]

# Initialize and train the predictor
predictor = PowerPeakPredictor()

try:
    predictor.fit(df, meter_id=meter_id)
    
    # Make predictions with the most recent data
    current_data = df[df['meter_id'] == meter_id].sort_values('time').tail(1)
    lookback_data = df[df['meter_id'] == meter_id]
    
    predictions = predictor.predict_peaks(current_data, lookback_data)
    print("Predictions:", predictions)
    
    # Visualize the predictions
    predictor.visualize_prediction(df, predictions, meter_id=meter_id)
    plt.show()
    
except Exception as e:
    print(f"Error in prediction: {e}")
    print("Likely causes: insufficient continuous data or incomplete time intervals")
    
    # Fallback to simpler analysis
    print("\nFallback to simple statistics:")
    hourly_avg = df[df['meter_id'] == meter_id].groupby(df['time'].dt.hour)['import'].mean()
    peak_hour = hourly_avg.idxmax()
    peak_value = hourly_avg.max()
    
    print(f"Historical peak occurs at hour {peak_hour} with average value {peak_value:.2f}")
    
    # Simple visualization
    hourly_avg.plot(kind='bar')
    plt.title(f"Average hourly consumption for meter {meter_id}")
    plt.xlabel("Hour of day")
    plt.ylabel("Average consumption")
    plt.tight_layout()
    plt.show()

def main():
    # Configuration
    DATA_FILE = 'energy_and_temperature.csv'
    UPDATE_INTERVAL = 15  # minutes
    
    # Initial setup
    predictions, time_intervals, base_load_threshold = robust_peak_prediction_pipeline(DATA_FILE)
    
    # Print initial predictions
    print("Initial Peak Predictions:")
    for interval, pred in predictions.items():
        print(f"  {interval}: {pred['predicted_amount']:.2f} kW at hour {pred['predicted_hour']:.1f}")
    
    # If you want this to run continuously (for live monitoring):
    while True:
        # Wait for update interval
        time.sleep(UPDATE_INTERVAL * 60)
        
        # In a real application, you would fetch new data here
        # new_data = fetch_latest_data()
        # update_csv(new_data, DATA_FILE)
        
        # Re-run predictions with latest data
        try:
            predictions, _, _ = robust_peak_prediction_pipeline(DATA_FILE)
            
            # Print updated predictions
            print("\nUpdated Peak Predictions:")
            for interval, pred in predictions.items():
                print(f"  {interval}: {pred['predicted_amount']:.2f} kW at hour {pred['predicted_hour']:.1f}")
                
            # Check if any peaks are coming soon (within 30-45 minutes)
            current_time = datetime.datetime.now()
            for interval, pred in predictions.items():
                pred_time = current_time.replace(hour=int(pred['predicted_hour']), 
                                               minute=int((pred['predicted_hour'] % 1) * 60))
                
                time_diff = (pred_time - current_time).total_seconds() / 60
                
                if 30 <= time_diff <= 45:
                    print(f"ALERT: Peak of {pred['predicted_amount']:.2f} kW expected in {time_diff:.0f} minutes!")
                    
        except Exception as e:
            print(f"Error updating predictions: {e}")
            
if __name__ == "__main__":
    main()