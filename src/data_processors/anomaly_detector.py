"""
Anomaly detection for AMS (Advanced Metering System) data.
Specifically checks for null and negative values in hourly meter readings.

Action point from IFE meeting:
"Lage skript for anomaly detection (sjekke null- og minustimer i AMS-data)"
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime


class AMSAnomalyDetector:
    """
    Detects anomalies in AMS hourly data:
    - Null/missing hours
    - Negative consumption values
    - Other data quality issues
    """
    
    def __init__(self, 
                 timestamp_col: str = "timestamp_utc",
                 power_col: str = "active_power_W",
                 meter_id_col: str = "meter_id"):
        """
        Initialize anomaly detector.
        
        Args:
            timestamp_col: Name of timestamp column
            power_col: Name of power consumption column to check
            meter_id_col: Name of meter ID column
        """
        self.timestamp_col = timestamp_col
        self.power_col = power_col
        self.meter_id_col = meter_id_col
    
    def detect_nulls(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect null/missing values in hourly data.
        
        Args:
            df: DataFrame with hourly AMS data
            
        Returns:
            DataFrame with detected null anomalies
        """
        df = df.copy()
        
        # Ensure timestamp is datetime
        if self.timestamp_col in df.columns:
            df[self.timestamp_col] = pd.to_datetime(df[self.timestamp_col], errors='coerce')
        
        # Detect nulls in power column
        null_mask = df[self.power_col].isna()
        
        anomalies = df[null_mask].copy()
        anomalies['anomaly_type'] = 'null_value'
        anomalies['anomaly_severity'] = 'high'
        
        return anomalies
    
    def detect_negatives(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect negative consumption values (should not exist for consumption data).
        
        Args:
            df: DataFrame with hourly AMS data
            
        Returns:
            DataFrame with detected negative value anomalies
        """
        df = df.copy()
        
        # Detect negative values in power column
        negative_mask = df[self.power_col] < 0
        
        anomalies = df[negative_mask].copy()
        anomalies['anomaly_type'] = 'negative_value'
        anomalies['anomaly_severity'] = 'high'
        
        return anomalies
    
    def detect_missing_hours(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect missing hours in the expected hourly time series.
        Identifies gaps where hours should exist but don't.
        
        Args:
            df: DataFrame with hourly AMS data
            
        Returns:
            DataFrame with missing hours (synthetic rows for missing timestamps)
        """
        df = df.copy()
        
        # Ensure timestamp is datetime and set as index temporarily
        if self.timestamp_col in df.columns:
            df[self.timestamp_col] = pd.to_datetime(df[self.timestamp_col], errors='coerce')
        
        missing_hours = []
        
        # Check for each meter separately
        if self.meter_id_col in df.columns:
            for meter_id in df[self.meter_id_col].unique():
                meter_data = df[df[self.meter_id_col] == meter_id].copy()
                meter_data = meter_data.set_index(self.timestamp_col).sort_index()
                
                # Create expected hourly range
                expected_start = meter_data.index.min()
                expected_end = meter_data.index.max()
                expected_range = pd.date_range(
                    start=expected_start.floor('H'),
                    end=expected_end.ceil('H'),
                    freq='H'
                )
                
                # Find missing hours
                missing_timestamps = expected_range.difference(meter_data.index)
                
                for ts in missing_timestamps:
                    missing_hours.append({
                        self.timestamp_col: ts,
                        self.meter_id_col: meter_id,
                        self.power_col: np.nan,
                        'anomaly_type': 'missing_hour',
                        'anomaly_severity': 'medium'
                    })
        
        if missing_hours:
            return pd.DataFrame(missing_hours)
        else:
            return pd.DataFrame()
    
    def detect_all(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Run all anomaly detection methods.
        
        Args:
            df: DataFrame with hourly AMS data
            
        Returns:
            Dictionary with anomaly types as keys and DataFrames as values
        """
        results = {}
        
        # Detect null values
        null_anomalies = self.detect_nulls(df)
        if not null_anomalies.empty:
            results['null_values'] = null_anomalies
        
        # Detect negative values
        negative_anomalies = self.detect_negatives(df)
        if not negative_anomalies.empty:
            results['negative_values'] = negative_anomalies
        
        # Detect missing hours
        missing_hours = self.detect_missing_hours(df)
        if not missing_hours.empty:
            results['missing_hours'] = missing_hours
        
        return results
    
    def get_summary(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Generate summary statistics of anomalies.
        
        Args:
            df: DataFrame with hourly AMS data
            
        Returns:
            Dictionary with summary statistics
        """
        anomalies = self.detect_all(df)
        
        summary = {
            'total_records': len(df),
            'null_values': 0,
            'negative_values': 0,
            'missing_hours': 0,
            'null_percentage': 0.0,
            'negative_percentage': 0.0,
            'missing_hours_percentage': 0.0
        }
        
        if 'null_values' in anomalies:
            summary['null_values'] = len(anomalies['null_values'])
        
        if 'negative_values' in anomalies:
            summary['negative_values'] = len(anomalies['negative_values'])
        
        if 'missing_hours' in anomalies:
            summary['missing_hours'] = len(anomalies['missing_hours'])
        
        summary['null_percentage'] = (summary['null_values'] / summary['total_records']) * 100
        summary['negative_percentage'] = (summary['negative_values'] / summary['total_records']) * 100
        
        # Calculate missing hours percentage based on expected hours
        if summary['total_records'] > 0:
            expected_hours = self._count_expected_hours(df)
            summary['missing_hours_percentage'] = (summary['missing_hours'] / expected_hours) * 100 if expected_hours > 0 else 0
        
        return summary
    
    def _count_expected_hours(self, df: pd.DataFrame) -> int:
        """Count expected number of hours in the time range."""
        if self.timestamp_col not in df.columns:
            return 0
        
        df = df.copy()
        df[self.timestamp_col] = pd.to_datetime(df[self.timestamp_col], errors='coerce')
        
        if self.meter_id_col in df.columns:
            total_expected = 0
            for meter_id in df[self.meter_id_col].unique():
                meter_data = df[df[self.meter_id_col] == meter_id]
                start = meter_data[self.timestamp_col].min()
                end = meter_data[self.timestamp_col].max()
                expected_range = pd.date_range(
                    start=start.floor('H'),
                    end=end.ceil('H'),
                    freq='H'
                )
                total_expected += len(expected_range)
            return total_expected
        else:
            start = df[self.timestamp_col].min()
            end = df[self.timestamp_col].max()
            expected_range = pd.date_range(
                start=start.floor('H'),
                end=end.ceil('H'),
                freq='H'
            )
            return len(expected_range)
    
    def print_report(self, df: pd.DataFrame, output_file: Optional[str] = None):
        """
        Print a comprehensive anomaly detection report.
        
        Args:
            df: DataFrame with hourly AMS data
            output_file: Optional path to save report to file
        """
        summary = self.get_summary(df)
        anomalies = self.detect_all(df)
        
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("AMS DATA ANOMALY DETECTION REPORT")
        report_lines.append("=" * 60)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        report_lines.append("SUMMARY STATISTICS")
        report_lines.append("-" * 60)
        report_lines.append(f"Total records: {summary['total_records']:,}")
        report_lines.append("")
        
        report_lines.append("ANOMALY COUNTS")
        report_lines.append("-" * 60)
        report_lines.append(f"Null values: {summary['null_values']:,} ({summary['null_percentage']:.2f}%)")
        report_lines.append(f"Negative values: {summary['negative_values']:,} ({summary['negative_percentage']:.2f}%)")
        report_lines.append(f"Missing hours: {summary['missing_hours']:,} ({summary['missing_hours_percentage']:.2f}%)")
        report_lines.append("")
        
        # Detailed breakdown by meter
        if self.meter_id_col in df.columns:
            report_lines.append("BREAKDOWN BY METER")
            report_lines.append("-" * 60)
            for meter_id in sorted(df[self.meter_id_col].unique()):
                meter_data = df[df[self.meter_id_col] == meter_id]
                meter_summary = AMSAnomalyDetector(
                    self.timestamp_col,
                    self.power_col,
                    self.meter_id_col
                ).get_summary(meter_data)
                report_lines.append(f"\nMeter: {meter_id}")
                report_lines.append(f"  Total records: {meter_summary['total_records']:,}")
                report_lines.append(f"  Null values: {meter_summary['null_values']:,} ({meter_summary['null_percentage']:.2f}%)")
                report_lines.append(f"  Negative values: {meter_summary['negative_values']:,} ({meter_summary['negative_percentage']:.2f}%)")
                report_lines.append(f"  Missing hours: {meter_summary['missing_hours']:,} ({meter_summary['missing_hours_percentage']:.2f}%)")
        
        # Sample anomalies
        if anomalies:
            report_lines.append("")
            report_lines.append("SAMPLE ANOMALIES")
            report_lines.append("-" * 60)
            for anomaly_type, anomaly_df in anomalies.items():
                report_lines.append(f"\n{anomaly_type.upper()}:")
                if len(anomaly_df) > 0:
                    sample = anomaly_df.head(5)
                    report_lines.append(sample.to_string())
                    if len(anomaly_df) > 5:
                        report_lines.append(f"... and {len(anomaly_df) - 5} more")
        
        report_lines.append("")
        report_lines.append("=" * 60)
        
        report_text = "\n".join(report_lines)
        
        print(report_text)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"\nReport saved to: {output_file}")
    
    def plot_anomalies(self, df: pd.DataFrame, output_dir: Optional[str] = None):
        """
        Create visualizations of detected anomalies.
        
        Args:
            df: DataFrame with hourly AMS data
            output_dir: Directory to save plots (if None, plots are displayed)
        """
        anomalies = self.detect_all(df)
        
        if not anomalies:
            print("No anomalies detected - no plots generated.")
            return
        
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Plot 1: Anomaly counts by type
        if anomalies:
            fig, ax = plt.subplots(figsize=(10, 6))
            anomaly_types = list(anomalies.keys())
            counts = [len(anomalies[t]) for t in anomaly_types]
            
            bars = ax.bar(anomaly_types, counts, color=['red', 'orange', 'yellow'])
            ax.set_ylabel('Number of Anomalies')
            ax.set_title('AMS Data Anomalies by Type')
            ax.set_ylim(0, max(counts) * 1.1 if counts else 1)
            
            # Add count labels on bars
            for bar, count in zip(bars, counts):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{count:,}',
                       ha='center', va='bottom')
            
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            if output_dir:
                plt.savefig(Path(output_dir) / 'anomaly_counts.png', dpi=150)
                plt.close()
            else:
                plt.show()
        
        # Plot 2: Timeline of anomalies (if timestamp data available)
        if self.timestamp_col in df.columns and anomalies:
            fig, axes = plt.subplots(len(anomalies), 1, figsize=(15, 5 * len(anomalies)))
            if len(anomalies) == 1:
                axes = [axes]
            
            for idx, (anomaly_type, anomaly_df) in enumerate(anomalies.items()):
                if self.timestamp_col in anomaly_df.columns:
                    anomaly_df = anomaly_df.copy()
                    anomaly_df[self.timestamp_col] = pd.to_datetime(anomaly_df[self.timestamp_col])
                    anomaly_df = anomaly_df.sort_values(self.timestamp_col)
                    
                    axes[idx].scatter(
                        anomaly_df[self.timestamp_col],
                        range(len(anomaly_df)),
                        alpha=0.6,
                        s=20
                    )
                    axes[idx].set_xlabel('Date')
                    axes[idx].set_ylabel('Anomaly Index')
                    axes[idx].set_title(f'Timeline of {anomaly_type.replace("_", " ").title()}')
                    axes[idx].grid(True, alpha=0.3)
                    axes[idx].tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            if output_dir:
                plt.savefig(Path(output_dir) / 'anomaly_timeline.png', dpi=150)
                plt.close()
            else:
                plt.show()
        
        if output_dir:
            print(f"Plots saved to: {output_dir}")

