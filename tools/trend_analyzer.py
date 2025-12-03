"""
Trend Analyzer Tool
Analyzes trends over time periods.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyzes trends over time periods."""
    
    def analyze_trend(
        self,
        data: List[Dict[str, Any]],
        date_column: str,
        value_column: str,
        period: str = 'daily',
        group_by: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze trend over time.
        
        Args:
            data: List of data records
            date_column: Column containing dates
            value_column: Column containing values to analyze
            period: Time period (daily, weekly, monthly, quarterly, yearly)
            group_by: Optional columns to group by
            
        Returns:
            Dictionary with trend analysis
        """
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No data provided"
                }
            
            df = pd.DataFrame(data)
            
            if date_column not in df.columns:
                return {
                    "success": False,
                    "error": f"Date column '{date_column}' not found"
                }
            
            if value_column not in df.columns:
                return {
                    "success": False,
                    "error": f"Value column '{value_column}' not found"
                }
            
            # Convert date column to datetime
            df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
            df = df.dropna(subset=[date_column])
            
            if len(df) == 0:
                return {
                    "success": False,
                    "error": "No valid dates found"
                }
            
            # Filter by time range if requested
            from datetime import datetime, timedelta
            if time_range and "last month" in str(time_range).lower():
                # Get the most recent date in the dataset
                max_date = df[date_column].max()
                # Calculate one month before (approximately 30 days)
                one_month_ago = max_date - timedelta(days=30)
                # Filter to last month
                df = df[df[date_column] >= one_month_ago]
                logger.info(f"Filtered to last month: {one_month_ago.date()} to {max_date.date()}, {len(df)} rows")
            
            if len(df) == 0:
                return {
                    "success": False,
                    "error": "No data found for the specified time period"
                }
            
            # Set date as index for resampling
            df = df.set_index(date_column)
            
            # Resample based on period
            period_map = {
                'daily': 'D',
                'weekly': 'W',
                'monthly': 'M',
                'quarterly': 'Q',
                'yearly': 'Y'
            }
            
            freq = period_map.get(period.lower(), 'D')
            
            # Group by if specified
            if group_by:
                available_group_cols = [col for col in group_by if col in df.columns]
                if available_group_cols:
                    grouped = df.groupby(available_group_cols + [pd.Grouper(freq=freq)])
                else:
                    grouped = df.groupby(pd.Grouper(freq=freq))
            else:
                grouped = df.groupby(pd.Grouper(freq=freq))
            
            # Aggregate
            aggregated = grouped[value_column].agg(['sum', 'mean', 'count']).reset_index()
            
            # Calculate trend direction
            if len(aggregated) > 1:
                first_val = aggregated['mean'].iloc[0]
                last_val = aggregated['mean'].iloc[-1]
                trend_direction = 'increasing' if last_val > first_val else 'decreasing' if last_val < first_val else 'stable'
                trend_percentage = ((last_val - first_val) / first_val * 100) if first_val != 0 else 0
            else:
                trend_direction = 'insufficient_data'
                trend_percentage = 0
            
            # Convert to records
            records = []
            for _, row in aggregated.iterrows():
                record = {
                    'period': row[date_column].isoformat() if isinstance(row[date_column], pd.Timestamp) else str(row[date_column]),
                    'sum': float(row['sum']) if pd.notna(row['sum']) else None,
                    'mean': float(row['mean']) if pd.notna(row['mean']) else None,
                    'count': int(row['count']) if pd.notna(row['count']) else None
                }
                if group_by and available_group_cols:
                    for col in available_group_cols:
                        record[col] = row[col]
                records.append(record)
            
            return {
                "success": True,
                "date_column": date_column,
                "value_column": value_column,
                "period": period,
                "group_by": available_group_cols if group_by else None,
                "trend_direction": trend_direction,
                "trend_percentage": float(trend_percentage),
                "data": records,
                "summary": {
                    "total_periods": len(records),
                    "first_period": records[0]['period'] if records else None,
                    "last_period": records[-1]['period'] if records else None,
                    "overall_mean": float(aggregated['mean'].mean()) if len(aggregated) > 0 else None,
                    "overall_sum": float(aggregated['sum'].sum()) if len(aggregated) > 0 else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trend: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }



