"""
Data Calculator Tool
Performs aggregations and calculations on data.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class DataCalculator:
    """Performs data aggregations and calculations."""
    
    def calculate(
        self,
        data: List[Dict[str, Any]],
        operation: str,
        column: str,
        group_by: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform calculation on data.
        
        Args:
            data: List of data records
            operation: Operation to perform (sum, avg, count, min, max, median, std)
            column: Column to operate on
            group_by: Optional columns to group by
            
        Returns:
            Dictionary with result
        """
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No data provided"
                }
            
            df = pd.DataFrame(data)
            
            if column not in df.columns:
                return {
                    "success": False,
                    "error": f"Column '{column}' not found in data"
                }
            
            # Check if column is numeric
            if not pd.api.types.is_numeric_dtype(df[column]):
                if operation in ['sum', 'avg', 'min', 'max', 'median', 'std']:
                    return {
                        "success": False,
                        "error": f"Column '{column}' is not numeric, cannot perform {operation}"
                    }
            
            # Group by if specified
            if group_by:
                available_group_cols = [col for col in group_by if col in df.columns]
                if not available_group_cols:
                    return {
                        "success": False,
                        "error": f"Group by columns not found: {group_by}"
                    }
                grouped = df.groupby(available_group_cols)
            else:
                grouped = df
            
            # Perform operation
            result = None
            if operation == 'sum':
                if group_by:
                    result = grouped[column].sum()
                else:
                    result = df[column].sum()
            elif operation == 'avg' or operation == 'mean':
                if group_by:
                    result = grouped[column].mean()
                else:
                    result = df[column].mean()
            elif operation == 'count':
                if group_by:
                    result = grouped[column].count()
                else:
                    result = df[column].count()
            elif operation == 'min':
                if group_by:
                    result = grouped[column].min()
                else:
                    result = df[column].min()
            elif operation == 'max':
                if group_by:
                    result = grouped[column].max()
                else:
                    result = df[column].max()
            elif operation == 'median':
                if group_by:
                    result = grouped[column].median()
                else:
                    result = df[column].median()
            elif operation == 'std':
                if group_by:
                    result = grouped[column].std()
                else:
                    result = df[column].std()
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}"
                }
            
            # Convert result to serializable format
            if isinstance(result, pd.Series):
                # Grouped result
                result_dict = {}
                for idx, val in result.items():
                    if isinstance(idx, tuple):
                        key = " | ".join(str(v) for v in idx)
                    else:
                        key = str(idx)
                    result_dict[key] = float(val) if pd.notna(val) else None
                return {
                    "success": True,
                    "operation": operation,
                    "column": column,
                    "group_by": available_group_cols if group_by else None,
                    "result": result_dict,
                    "total": float(result.sum()) if pd.api.types.is_numeric_dtype(result) else None
                }
            else:
                # Single value result
                return {
                    "success": True,
                    "operation": operation,
                    "column": column,
                    "result": float(result) if pd.notna(result) else None,
                    "row_count": len(df)
                }
                
        except Exception as e:
            logger.error(f"Error calculating {operation} on {column}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def calculate_ratio(
        self,
        data: List[Dict[str, Any]],
        numerator_column: str,
        denominator_column: str,
        group_by: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calculate ratio between two columns.
        
        Args:
            data: List of data records
            numerator_column: Column for numerator
            denominator_column: Column for denominator
            group_by: Optional columns to group by
            
        Returns:
            Dictionary with result
        """
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No data provided"
                }
            
            df = pd.DataFrame(data)
            
            if numerator_column not in df.columns or denominator_column not in df.columns:
                return {
                    "success": False,
                    "error": f"Columns not found: {numerator_column}, {denominator_column}"
                }
            
            # Calculate ratio
            df['_ratio'] = df[numerator_column] / df[denominator_column].replace(0, np.nan)
            
            if group_by:
                available_group_cols = [col for col in group_by if col in df.columns]
                if available_group_cols:
                    result = df.groupby(available_group_cols)['_ratio'].mean()
                    result_dict = {}
                    for idx, val in result.items():
                        if isinstance(idx, tuple):
                            key = " | ".join(str(v) for v in idx)
                        else:
                            key = str(idx)
                        result_dict[key] = float(val) if pd.notna(val) else None
                    return {
                        "success": True,
                        "numerator": numerator_column,
                        "denominator": denominator_column,
                        "group_by": available_group_cols,
                        "result": result_dict
                    }
            
            avg_ratio = df['_ratio'].mean()
            return {
                "success": True,
                "numerator": numerator_column,
                "denominator": denominator_column,
                "result": float(avg_ratio) if pd.notna(avg_ratio) else None
            }
            
        except Exception as e:
            logger.error(f"Error calculating ratio: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

