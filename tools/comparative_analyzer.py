"""
Comparative Analyzer Tool
Compares entities, periods, or categories.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ComparativeAnalyzer:
    """Compares entities, periods, or categories."""
    
    def compare(
        self,
        data: List[Dict[str, Any]],
        compare_by: str,
        value_column: str,
        operation: str = 'sum',
        top_n: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Compare entities by a value column.
        
        Args:
            data: List of data records
            compare_by: Column to compare by (e.g., 'Product', 'Line')
            value_column: Column containing values to compare
            operation: Aggregation operation (sum, avg, count, min, max)
            top_n: Return top N results (None for all)
            
        Returns:
            Dictionary with comparison results
        """
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No data provided"
                }
            
            # Handle case where data might be a single dict instead of list
            if isinstance(data, dict):
                data = [data]
            
            if not isinstance(data, list):
                return {
                    "success": False,
                    "error": f"Data must be a list of dictionaries. Got: {type(data).__name__}"
                }
            
            df = pd.DataFrame(data)
            
            if compare_by not in df.columns:
                return {
                    "success": False,
                    "error": f"Compare by column '{compare_by}' not found"
                }
            
            if value_column not in df.columns:
                return {
                    "success": False,
                    "error": f"Value column '{value_column}' not found"
                }
            
            # Group by compare_by column
            grouped = df.groupby(compare_by)
            
            # Perform operation
            if operation == 'sum':
                result = grouped[value_column].sum()
            elif operation == 'avg' or operation == 'mean':
                result = grouped[value_column].mean()
            elif operation == 'count':
                result = grouped[value_column].count()
            elif operation == 'min':
                result = grouped[value_column].min()
            elif operation == 'max':
                result = grouped[value_column].max()
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}"
                }
            
            # Sort by value descending
            result = result.sort_values(ascending=False)
            
            # Convert to list of dictionaries
            comparisons = []
            for idx, val in result.items():
                comparisons.append({
                    compare_by: str(idx),
                    "value": float(val) if pd.notna(val) else None
                })
            
            # Apply top_n if specified
            if top_n:
                comparisons = comparisons[:top_n]
            
            # Find best and worst
            best = comparisons[0] if comparisons else None
            worst = comparisons[-1] if comparisons else None
            
            return {
                "success": True,
                "compare_by": compare_by,
                "value_column": value_column,
                "operation": operation,
                "comparisons": comparisons,
                "best": best,
                "worst": worst,
                "total_entities": len(comparisons)
            }
            
        except Exception as e:
            logger.error(f"Error comparing by {compare_by}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def compare_periods(
        self,
        data1: List[Dict[str, Any]],
        data2: List[Dict[str, Any]],
        value_column: str,
        period1_label: str = "Period 1",
        period2_label: str = "Period 2",
        operation: str = 'sum'
    ) -> Dict[str, Any]:
        """
        Compare two periods of data.
        
        Args:
            data1: Data for first period
            data2: Data for second period
            value_column: Column containing values to compare
            period1_label: Label for first period
            period2_label: Label for second period
            operation: Aggregation operation
            
        Returns:
            Dictionary with comparison results
        """
        try:
            df1 = pd.DataFrame(data1) if data1 else pd.DataFrame()
            df2 = pd.DataFrame(data2) if data2 else pd.DataFrame()
            
            if value_column not in df1.columns and value_column not in df2.columns:
                return {
                    "success": False,
                    "error": f"Value column '{value_column}' not found in data"
                }
            
            # Calculate aggregated values
            def get_value(df, col, op):
                if col not in df.columns or len(df) == 0:
                    return None
                if op == 'sum':
                    return float(df[col].sum())
                elif op == 'avg' or op == 'mean':
                    return float(df[col].mean())
                elif op == 'count':
                    return float(len(df))
                elif op == 'min':
                    return float(df[col].min())
                elif op == 'max':
                    return float(df[col].max())
                return None
            
            val1 = get_value(df1, value_column, operation)
            val2 = get_value(df2, value_column, operation)
            
            if val1 is None or val2 is None:
                return {
                    "success": False,
                    "error": "Could not calculate values for comparison"
                }
            
            # Calculate difference and percentage change
            difference = val2 - val1
            percentage_change = (difference / val1 * 100) if val1 != 0 else 0
            
            return {
                "success": True,
                "period1": {
                    "label": period1_label,
                    "value": val1
                },
                "period2": {
                    "label": period2_label,
                    "value": val2
                },
                "difference": difference,
                "percentage_change": float(percentage_change),
                "trend": "increasing" if difference > 0 else "decreasing" if difference < 0 else "stable"
            }
            
        except Exception as e:
            logger.error(f"Error comparing periods: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }



