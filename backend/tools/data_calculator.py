"""
Data Calculator Tool
Performs aggregations and calculations on data.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
import sys
from pathlib import Path

# Import Gemini Column Finder for intelligent column handling
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
try:
    from gemini_column_finder import GeminiColumnFinder
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("GeminiColumnFinder not available")

logger = logging.getLogger(__name__)


class DataCalculator:
    """Performs data aggregations and calculations."""
    
    def __init__(self):
        """Initialize with Gemini support if available"""
        self.gemini_finder = GeminiColumnFinder() if GEMINI_AVAILABLE else None
        if self.gemini_finder and self.gemini_finder.model:
            logger.info("✅ DataCalculator initialized with Gemini support")
        else:
            logger.info("⚠️ DataCalculator using fallback mode (no Gemini)")
    
    def _extract_derived_column(self, df: pd.DataFrame, requested_column: str, available_columns: List[str]) -> Optional[str]:
        """
        Use Gemini to intelligently extract or derive a column
        
        Args:
            df: DataFrame
            requested_column: Column requested by user (e.g., 'Line')
            available_columns: Columns that actually exist
            
        Returns:
            Column name to use, or None if cannot be derived
        """
        if requested_column in available_columns:
            return requested_column
        
        # Use Gemini to find if we can derive this column
        if self.gemini_finder and self.gemini_finder.model:
            try:
                # Get sample data for context
                sample_row = df.iloc[0].to_dict() if len(df) > 0 else {}
                
                prompt_purpose = f"extract or derive '{requested_column}' column from available columns"
                
                result = self.gemini_finder.find_columns(
                    available_columns=available_columns,
                    purpose=prompt_purpose,
                    data_context=f"Need to get '{requested_column}' values. Sample row: {sample_row}"
                )
                
                if result and 'source_column' in result:
                    source_col = result['source_column']
                    
                    # If Gemini suggests a transformation
                    if 'extraction_pattern' in result and result['extraction_pattern']:
                        pattern = result['extraction_pattern']
                        logger.info(f"Gemini suggests extracting '{requested_column}' from '{source_col}' using pattern: {pattern}")
                        
                        # Apply extraction
                        try:
                            df[requested_column] = df[source_col].str.extract(pattern, expand=False)
                            return requested_column
                        except Exception as e:
                            logger.warning(f"Failed to extract using pattern {pattern}: {e}")
                    
                    # If source column can be used directly
                    return source_col
                    
            except Exception as e:
                logger.warning(f"Gemini extraction failed: {e}")
        
        # Fallback: Try to find composite columns
        return self._fallback_extract_column(df, requested_column, available_columns)
    
    def _fallback_extract_column(self, df: pd.DataFrame, requested_column: str, available_columns: List[str]) -> Optional[str]:
        """
        Fallback method to extract columns without Gemini
        """
        requested_lower = requested_column.lower()
        
        # Look for columns that might contain the requested one
        for col in available_columns:
            col_lower = col.lower()
            
            # Check if requested column is part of a composite column
            if requested_lower in col_lower and col != requested_column:
                logger.info(f"Found potential source column: {col} for {requested_column}")
                
                # Try common patterns
                patterns = [
                    rf'^({requested_column}-\d+)',  # Line-1, Line-2, etc.
                    rf'^({requested_column}\d+)',   # Line1, Line2, etc.
                    rf'({requested_column}[^/]+)',  # Line-ABC before /
                ]
                
                for pattern in patterns:
                    try:
                        extracted = df[col].str.extract(pattern, expand=False)
                        if extracted.notna().any():
                            df[requested_column] = extracted
                            logger.info(f"Extracted '{requested_column}' from '{col}' using pattern: {pattern}")
                            return requested_column
                    except:
                        continue
        
        return None
    
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
            
            # Handle missing columns intelligently using Gemini
            if group_by:
                for gb_col in group_by:
                    if gb_col not in df.columns:
                        derived_col = self._extract_derived_column(df, gb_col, list(df.columns))
                        if not derived_col:
                            return {
                                "success": False,
                                "error": f"Group by column '{gb_col}' not found and cannot be derived"
                            }
            
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
                # Grouped result - convert to dict safely
                result_dict = {}
                try:
                    # Handle both simple and multi-index Series
                    if isinstance(result.index, pd.MultiIndex):
                        for idx, val in result.items():
                            key = " | ".join(str(v) for v in idx)
                            result_dict[key] = float(val) if pd.notna(val) else None
                    else:
                        for idx, val in result.items():
                            result_dict[str(idx)] = float(val) if pd.notna(val) else None
                except Exception as e:
                    logger.error(f"Error converting grouped result: {str(e)}")
                    # Fallback: convert to DataFrame first
                    result_df = result.reset_index()
                    result_dict = result_df.to_dict('records')
                
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
            
            # Handle missing columns intelligently using Gemini
            if group_by:
                for gb_col in group_by:
                    if gb_col not in df.columns:
                        derived_col = self._extract_derived_column(df, gb_col, list(df.columns))
                        if not derived_col:
                            return {
                                "success": False,
                                "error": f"Group by column '{gb_col}' not found and cannot be derived"
                            }
            
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

