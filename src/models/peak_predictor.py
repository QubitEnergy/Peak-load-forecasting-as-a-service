"""
Peak Load Predictor with fixed bugs and complete implementation.
Fixed issues:
- Added missing prepare_features() method
- Fixed 'ions' typo to 'predictions'
- Separated library code from examples
"""
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
    A class implementing peak load prediction methodology.
    Predicts peaks 30 minutes in advance to give clients time to react.
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
        Extract time intervals based on the methodology.
        Uses local minima (valleys) to establish interval boundaries.
        """
        if meter_id:
            df = df[df['meter_id'] == meter_id].copy()
        
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
        Separate the load into base load and peak load.
        Uses the median as the boundary between base and peak load.
        """
        if meter_id:
            df = df[df['meter_id'] == meter_id].copy()
        
        # Calculate the median as the boundary between base and peak
        self.base_load_threshold = df['import'].median()
        print(f"Base load threshold set at {self.base_load_threshold}")
        
        # Add base/peak classification to dataframe
        df['is_peak'] = df['import'] > self.base_load_threshold
        df['peak_amount'] = np.where(df['is_peak'], 
                                     df['import'] - self.base_load_threshold, 
                                     0)
        
        return df
    
    def prepare_features(self, df, meter_id=None, lookback_days=3, lookback_week=True):
        """
        Prepare features for model training and prediction.
        Creates lag features, interval assignment, and target variables.
        
        Args:
            df: DataFrame with time, import, and optionally air_temperature columns
            meter_id: Optional meter ID to filter
            lookback_days: Number of days to create lag features for (default: 3)
            lookback_week: Whether to include 7-day lag feature
            
        Returns:
            DataFrame with features including:
            - interval: Time interval index for each hour
            - lag1_import, lag2_import, ...: Lagged consumption values
            - lag7_import: Weekly lag (if lookback_week=True)
            - peak_amount: Target for amount prediction
            - peak_hour: Target for timing prediction
            - air_temperature: Temperature feature (if available)
        """
        if meter_id:
            df = df[df['meter_id'] == meter_id].copy()
        
        # Ensure time is datetime and sorted
        df = df.copy()
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time')
        
        # Assign interval to each hour
        df['hour'] = df['time'].dt.hour
        df['interval'] = -1
        
        for idx, interval in enumerate(self.time_intervals):
            mask = (df['hour'] >= interval['start']) & (df['hour'] < interval['end'])
            df.loc[mask, 'interval'] = idx
        
        # Remove rows without interval assignment
        df = df[df['interval'] >= 0].copy()
        
        # Create lag features
        df['lag1_import'] = df.groupby('meter_id')['import'].shift(24)  # 1 day ago
        df['lag2_import'] = df.groupby('meter_id')['import'].shift(48)  # 2 days ago
        
        if lookback_days >= 3:
            df['lag3_import'] = df.groupby('meter_id')['import'].shift(72)  # 3 days ago
        
        if lookback_week:
            df['lag7_import'] = df.groupby('meter_id')['import'].shift(168)  # 7 days ago (weekly)
        
        # Create temperature lag features if available
        if 'air_temperature' in df.columns:
            df['lag1_temp'] = df.groupby('meter_id')['air_temperature'].shift(24)
            df['lag2_temp'] = df.groupby('meter_id')['air_temperature'].shift(48)
            if lookback_week:
                df['lag7_temp'] = df.groupby('meter_id')['air_temperature'].shift(168)
        
        # Create target: peak hour within interval
        def get_peak_hour_in_interval(group):
            """Get the hour of peak consumption within this interval."""
            if len(group) == 0:
                return np.nan
            peak_idx = group['import'].idxmax()
            return group.loc[peak_idx, 'hour']
        
        df['peak_hour'] = df.groupby(['meter_id', df['time'].dt.date, 'interval'])['import'].transform(
            lambda x: x.idxmax() if len(x) > 0 else np.nan
        )
        # Convert index to hour value
        peak_indices = df['peak_hour']
        df['peak_hour'] = df.loc[peak_indices[peak_indices.notna()].astype(int), 'hour'].values if len(peak_indices[peak_indices.notna()]) > 0 else np.nan
        
        # Fallback: use max hour in interval if transformation failed
        if df['peak_hour'].isna().all():
            df['peak_hour'] = df.groupby(['meter_id', df['time'].dt.date, 'interval'])['hour'].transform('max')
        
        # Ensure peak_amount is set
        if 'peak_amount' not in df.columns:
            df = self.separate_base_peak_load(df, meter_id)
        
        # Drop rows with NaN in critical features
        lag_cols = [col for col in df.columns if col.startswith('lag')]
        df = df.dropna(subset=lag_cols + ['interval', 'peak_amount'])
        
        return df
    
    def train_models(self, feature_df):
        """
        Train separate models for each time interval to predict:
        1. Peak amount
        2. Peak timing
        """
        for interval_idx in feature_df['interval'].unique():
            interval_data = feature_df[feature_df['interval'] == interval_idx].copy()
            
            if len(interval_data) < 10:
                print(f"Not enough data for interval {interval_idx}, skipping")
                continue
            
            # Prepare features for amount prediction
            amount_features = [col for col in interval_data.columns if 
                            'lag' in col and 'peak_hour' not in col]
            
            if not amount_features:
                print(f"No lag features for interval {interval_idx}, skipping")
                continue
            
            X_amount = interval_data[amount_features]
            y_amount = interval_data['peak_amount']
            
            # Scale features
            amount_scaler = StandardScaler()
            X_amount_scaled = amount_scaler.fit_transform(X_amount)
            
            # Train amount prediction model
            amount_model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=3,
                learning_rate=0.1,
                random_state=42
            )
            amount_model.fit(X_amount_scaled, y_amount)
            
            # Prepare features for timing prediction
            timing_features = amount_features  # Use same features
            X_timing = interval_data[timing_features]
            y_timing = interval_data['peak_hour']
            
            # Scale features
            timing_scaler = StandardScaler()
            X_timing_scaled = timing_scaler.fit_transform(X_timing)
            
            # Train timing prediction model
            timing_model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=3,
                learning_rate=0.1,
                random_state=42
            )
            timing_model.fit(X_timing_scaled, y_timing)
            
            self.interval_models[interval_idx] = {
                'amount_model': amount_model,
                'timing_model': timing_model,
                'amount_features': amount_features,
                'timing_features': timing_features,
                'amount_scaler': amount_scaler,
                'timing_scaler': timing_scaler
            }
        
        self.is_trained = True
        print(f"Trained models for {len(self.interval_models)} intervals")
    
    def predict_peaks(self, current_data, lookback_data):
        """
        Predict peak amount and timing for upcoming intervals.
        Provides 30-minute advance warning.
        """
        if not self.is_trained:
            raise ValueError("Models must be trained before prediction")
        
        # Get current hour and determine active interval
        current_time = pd.to_datetime(current_data['time'].iloc[-1])
        current_hour = current_time.hour
        
        # Identify which intervals are coming up
        upcoming_intervals = []
        for idx, interval in enumerate(self.time_intervals):
            if current_hour < interval['start']:
                upcoming_intervals.append(idx)
            elif current_hour >= interval['start'] and current_hour < interval['end']:
                upcoming_intervals.append(idx)
        
        # Prepare features for prediction
        combined_data = pd.concat([lookback_data, current_data])
        prediction_features = self.prepare_features(combined_data)
        
        # Generate predictions
        predictions = {}
        for interval_idx in upcoming_intervals:
            if interval_idx not in self.interval_models:
                continue
            
            # Get latest feature row for this interval
            interval_features = prediction_features[prediction_features['interval'] == interval_idx]
            if len(interval_features) == 0:
                continue
            
            latest_features = interval_features.iloc[-1]
            model_info = self.interval_models[interval_idx]
            
            # Predict peak amount
            X_amount = latest_features[model_info['amount_features']].values.reshape(1, -1)
            X_amount_scaled = model_info['amount_scaler'].transform(X_amount)
            predicted_amount = model_info['amount_model'].predict(X_amount_scaled)[0]
            
            # Predict timing
            X_timing = latest_features[model_info['timing_features']].values.reshape(1, -1)
            X_timing_scaled = model_info['timing_scaler'].transform(X_timing)
            predicted_hour = model_info['timing_model'].predict(X_timing_scaled)[0]
            
            # Calculate full predicted peak
            total_predicted = self.base_load_threshold + max(0, predicted_amount)
            
            # Calculate minutes until peak
            interval = self.time_intervals[interval_idx]
            predicted_datetime = current_time.replace(hour=int(predicted_hour), minute=0)
            
            if predicted_datetime < current_time:
                predicted_datetime += datetime.timedelta(days=1)
            
            minutes_until_peak = (predicted_datetime - current_time).total_seconds() / 60
            
            # Include 30-minute advance warning
            interval_start_hour, interval_end_hour = interval['start'], interval['end']
            predicted_hour_in_interval = interval_start_hour <= predicted_hour < interval_end_hour
            
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
    
    def fit(self, df, meter_id=None):
        """Complete training pipeline."""
        df['time'] = pd.to_datetime(df['time'])
        
        # 1. Extract time intervals
        self.extract_time_intervals(df, meter_id)
        
        # 2. Separate base and peak load
        processed_df = self.separate_base_peak_load(df, meter_id)
        
        # 3. Prepare features
        feature_df = self.prepare_features(processed_df, meter_id)
        
        # 4. Train models
        self.train_models(feature_df)
        
        return self
    
    def visualize_prediction(self, df, predictions, meter_id=None):
        """Visualize current usage and predictions"""
        if meter_id:
            df = df[df['meter_id'] == meter_id].copy()
        
        last_day = df.sort_values('time').tail(24)
        
        plt.figure(figsize=(12, 6))
        plt.plot(last_day['time'], last_day['import'], 'b-', label='Actual Usage')
        plt.axhline(y=self.base_load_threshold, color='gray', linestyle='--', label='Base Load Threshold')
        
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

