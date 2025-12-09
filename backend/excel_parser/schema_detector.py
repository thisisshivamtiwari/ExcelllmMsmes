"""
Schema Detector Module
Advanced schema detection and type inference for Excel/CSV files.
Uses statistical analysis and optionally Gemini API for semantic understanding.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)


class SchemaDetector:
    """Advanced schema detection with type inference."""
    
    # Date patterns
    DATE_PATTERNS = [
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
        r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
        r'\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
    ]
    
    # ID patterns
    ID_PATTERNS = [
        r'^[A-Z]{2,4}\d{4,8}$',  # Product codes like ABC12345
        r'^\d{6,10}$',  # Numeric IDs
        r'^[A-Z]+\d+[A-Z]*$',  # Mixed alphanumeric IDs
    ]
    
    def __init__(self, use_gemini: bool = False, gemini_api_key: Optional[str] = None):
        """
        Initialize schema detector.
        
        Args:
            use_gemini: Whether to use Gemini API for semantic analysis
            gemini_api_key: Gemini API key (required if use_gemini=True)
        """
        self.use_gemini = use_gemini
        self.gemini_api_key = gemini_api_key
        if use_gemini and not gemini_api_key:
            logger.warning("Gemini API key not provided, semantic analysis will be disabled")
            self.use_gemini = False
    
    def detect_schema(
        self,
        file_path: Path,
        user_definitions: Optional[Dict[str, Dict[str, Any]]] = None,
        sheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect comprehensive schema for a file.
        
        Args:
            file_path: Path to the file
            user_definitions: User-provided column definitions from metadata
            sheet_name: Specific sheet to analyze (None for all sheets)
            
        Returns:
            Dictionary with detected schema information
        """
        try:
            file_ext = file_path.suffix.lower()
            schema_info = {
                'file_id': None,  # Will be set by caller
                'file_path': str(file_path),
                'detected_at': datetime.now().isoformat(),
                'sheets': {}
            }
            
            # Load file
            if file_ext in ['.xlsx', '.xls']:
                excel_file = pd.ExcelFile(file_path)
                sheet_names = [sheet_name] if sheet_name else excel_file.sheet_names
                
                for sheet in sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet, nrows=10000)
                    sheet_schema = self._detect_sheet_schema(
                        df, sheet, user_definitions
                    )
                    schema_info['sheets'][sheet] = sheet_schema
                
                excel_file.close()
            elif file_ext == '.csv':
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                df = None
                
                for enc in encodings:
                    try:
                        df = pd.read_csv(file_path, encoding=enc, nrows=10000)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if df is None:
                    return {
                        'error': 'Could not read CSV file with any encoding',
                        **schema_info
                    }
                
                sheet_name = sheet_name or 'Sheet1'
                sheet_schema = self._detect_sheet_schema(
                    df, sheet_name, user_definitions
                )
                schema_info['sheets'][sheet_name] = sheet_schema
            
            return schema_info
            
        except Exception as e:
            logger.error(f"Error detecting schema for {file_path}: {str(e)}")
            return {
                'error': f"Error detecting schema: {str(e)}",
                **schema_info
            }
    
    def _detect_sheet_schema(
        self,
        df: pd.DataFrame,
        sheet_name: str,
        user_definitions: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Detect schema for a single sheet."""
        sheet_schema = {
            'sheet_name': sheet_name,
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': {}
        }
        
        # Detect schema for each column
        for col in df.columns:
            col_schema = self._detect_column_schema(
                df[col], col, user_definitions
            )
            sheet_schema['columns'][col] = col_schema
        
        # Detect relationships and patterns
        sheet_schema['relationships'] = self._detect_relationships(df)
        sheet_schema['data_quality'] = self._assess_data_quality(df)
        
        return sheet_schema
    
    def _detect_column_schema(
        self,
        series: pd.Series,
        column_name: str,
        user_definitions: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Detect schema for a single column."""
        # Start with basic pandas dtype
        pandas_dtype = str(series.dtype)
        
        # Get user definition if available
        user_def = None
        if user_definitions and column_name in user_definitions:
            user_def = user_definitions[column_name]
        
        # Remove nulls for analysis
        non_null_series = series.dropna()
        if len(non_null_series) == 0:
            return {
                'column_name': column_name,
                'pandas_dtype': pandas_dtype,
                'detected_type': 'unknown',
                'confidence': 0.0,
                'null_count': len(series),
                'null_percentage': 100.0,
                'user_definition': user_def
            }
        
        # Detect type
        detected_type, confidence, subtype = self._infer_type(
            series, column_name, user_def
        )
        
        # Additional statistics
        stats = self._calculate_column_stats(series, detected_type)
        
        return {
            'column_name': column_name,
            'pandas_dtype': pandas_dtype,
            'detected_type': detected_type,
            'subtype': subtype,
            'confidence': confidence,
            'null_count': int(series.isna().sum()),
            'null_percentage': float((series.isna().sum() / len(series)) * 100),
            'unique_count': int(series.nunique()),
            'unique_percentage': float((series.nunique() / len(series)) * 100),
            'statistics': stats,
            'user_definition': user_def,
            'semantic_meaning': self._infer_semantic_meaning(column_name, detected_type, user_def)
        }
    
    def _infer_type(
        self,
        series: pd.Series,
        column_name: str,
        user_def: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float, Optional[str]]:
        """
        Infer the type of a column.
        
        Returns:
            (detected_type, confidence, subtype)
        """
        # Check user definition first
        if user_def and 'type' in user_def:
            return user_def['type'], 0.95, user_def.get('subtype')
        
        non_null_series = series.dropna()
        if len(non_null_series) == 0:
            return 'unknown', 0.0, None
        
        # Check for date/time
        if self._is_date_column(series, column_name):
            return 'date', 0.9, self._detect_date_format(series)
        
        # Check for ID columns
        if self._is_id_column(series, column_name):
            return 'id', 0.85, 'alphanumeric' if series.dtype == 'object' else 'numeric'
        
        # Check pandas dtype
        if pd.api.types.is_integer_dtype(series):
            # Check if it's categorical (low cardinality) or continuous
            unique_ratio = series.nunique() / len(non_null_series)
            if unique_ratio < 0.1:
                return 'categorical', 0.8, 'integer'
            elif self._is_boolean_like(series):
                return 'boolean', 0.9, None
            else:
                return 'numeric', 0.85, 'integer'
        
        elif pd.api.types.is_float_dtype(series):
            unique_ratio = series.nunique() / len(non_null_series)
            if unique_ratio < 0.1:
                return 'categorical', 0.75, 'float'
            else:
                return 'numeric', 0.9, 'float'
        
        elif pd.api.types.is_bool_dtype(series):
            return 'boolean', 0.95, None
        
        elif pd.api.types.is_string_dtype(series) or series.dtype == 'object':
            # Check if it's categorical (low cardinality)
            unique_ratio = series.nunique() / len(non_null_series)
            if unique_ratio < 0.3:
                return 'categorical', 0.85, 'string'
            elif self._is_id_column(series, column_name):
                return 'id', 0.8, 'string'
            else:
                return 'text', 0.8, None
        
        return 'unknown', 0.5, None
    
    def _is_date_column(self, series: pd.Series, column_name: str) -> bool:
        """Check if column contains dates."""
        # Check column name hints
        date_keywords = ['date', 'time', 'timestamp', 'created', 'updated', 'modified']
        if any(keyword in column_name.lower() for keyword in date_keywords):
            # Try to parse as date
            sample = series.dropna().head(100)
            if len(sample) > 0:
                try:
                    pd.to_datetime(sample, errors='raise')
                    return True
                except:
                    pass
        
        # Check if pandas already detected it as datetime
        if pd.api.types.is_datetime64_any_dtype(series):
            return True
        
        # Try parsing sample values
        sample = series.dropna().head(50)
        if len(sample) > 0:
            try:
                parsed = pd.to_datetime(sample, errors='coerce')
                if parsed.notna().sum() / len(sample) > 0.8:  # 80% can be parsed as dates
                    return True
            except:
                pass
        
        return False
    
    def _detect_date_format(self, series: pd.Series) -> Optional[str]:
        """Detect the date format used in the column."""
        sample = series.dropna().head(20)
        if len(sample) == 0:
            return None
        
        formats = []
        for val in sample:
            val_str = str(val)
            if re.match(r'\d{4}-\d{2}-\d{2}', val_str):
                formats.append('YYYY-MM-DD')
            elif re.match(r'\d{2}/\d{2}/\d{4}', val_str):
                formats.append('MM/DD/YYYY')
            elif re.match(r'\d{2}-\d{2}-\d{4}', val_str):
                formats.append('DD-MM-YYYY')
        
        if formats:
            return Counter(formats).most_common(1)[0][0]
        return 'mixed'
    
    def _is_id_column(self, series: pd.Series, column_name: str) -> bool:
        """Check if column is likely an ID column."""
        # Check column name hints
        id_keywords = ['id', 'code', 'key', 'ref', 'number', 'num', 'no']
        if any(keyword in column_name.lower() for keyword in id_keywords):
            # Check if values match ID patterns
            sample = series.dropna().head(100)
            if len(sample) > 0:
                matches = 0
                for val in sample:
                    val_str = str(val).strip()
                    for pattern in self.ID_PATTERNS:
                        if re.match(pattern, val_str, re.IGNORECASE):
                            matches += 1
                            break
                
                if matches / len(sample) > 0.7:  # 70% match ID patterns
                    return True
        
        # Check if it's unique and has reasonable length
        unique_ratio = series.nunique() / len(series.dropna())
        if unique_ratio > 0.95 and series.dtype == 'object':
            sample_lengths = [len(str(val)) for val in series.dropna().head(100)]
            avg_length = np.mean(sample_lengths) if sample_lengths else 0
            if 4 <= avg_length <= 20:  # Reasonable ID length
                return True
        
        return False
    
    def _is_boolean_like(self, series: pd.Series) -> bool:
        """Check if integer column is actually boolean."""
        unique_vals = series.dropna().unique()
        if len(unique_vals) <= 2:
            # Check if values are 0/1 or True/False
            unique_set = set(unique_vals)
            if unique_set.issubset({0, 1}) or unique_set.issubset({True, False}):
                return True
        return False
    
    def _calculate_column_stats(
        self,
        series: pd.Series,
        detected_type: str
    ) -> Dict[str, Any]:
        """Calculate statistics based on detected type."""
        stats = {}
        non_null = series.dropna()
        
        if detected_type == 'numeric':
            stats['min'] = float(non_null.min()) if len(non_null) > 0 else None
            stats['max'] = float(non_null.max()) if len(non_null) > 0 else None
            stats['mean'] = float(non_null.mean()) if len(non_null) > 0 else None
            stats['median'] = float(non_null.median()) if len(non_null) > 0 else None
            stats['std'] = float(non_null.std()) if len(non_null) > 0 else None
        elif detected_type == 'categorical':
            value_counts = non_null.value_counts().head(10)
            stats['top_values'] = {
                str(k): int(v) for k, v in value_counts.items()
            }
        elif detected_type == 'date':
            try:
                date_series = pd.to_datetime(non_null, errors='coerce')
                date_series = date_series.dropna()
                if len(date_series) > 0:
                    stats['min_date'] = date_series.min().isoformat()
                    stats['max_date'] = date_series.max().isoformat()
            except:
                pass
        
        return stats
    
    def _detect_relationships(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect potential relationships between columns."""
        relationships = []
        
        # Check for foreign key relationships (ID columns that might reference other columns)
        id_columns = []
        for col in df.columns:
            if self._is_id_column(df[col], col):
                id_columns.append(col)
        
        # Check for potential foreign keys (columns ending with _id, _code, etc.)
        for col in df.columns:
            if col.lower().endswith(('_id', '_code', '_key', '_ref')):
                relationships.append({
                    'type': 'potential_foreign_key',
                    'column': col,
                    'confidence': 0.7
                })
        
        return relationships
    
    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Assess overall data quality."""
        total_cells = len(df) * len(df.columns)
        null_cells = df.isna().sum().sum()
        
        quality_score = 1.0 - (null_cells / total_cells) if total_cells > 0 else 0.0
        
        return {
            'quality_score': float(quality_score),
            'completeness': float(1.0 - (null_cells / total_cells)) if total_cells > 0 else 0.0,
            'total_cells': int(total_cells),
            'null_cells': int(null_cells),
            'duplicate_rows': int(df.duplicated().sum()),
            'duplicate_percentage': float((df.duplicated().sum() / len(df)) * 100) if len(df) > 0 else 0.0
        }
    
    def _infer_semantic_meaning(
        self,
        column_name: str,
        detected_type: str,
        user_def: Optional[Dict[str, Any]] = None
    ) -> str:
        """Infer semantic meaning of column from name and type."""
        # Use user definition if available
        if user_def and 'description' in user_def:
            return user_def['description']
        
        # Infer from column name
        col_lower = column_name.lower()
        
        # Common manufacturing/industrial terms
        semantic_map = {
            'date': ['date', 'time', 'timestamp', 'created', 'updated'],
            'product': ['product', 'item', 'material', 'part'],
            'quantity': ['quantity', 'qty', 'amount', 'volume', 'count'],
            'cost': ['cost', 'price', 'value', 'amount'],
            'location': ['location', 'site', 'warehouse', 'plant', 'facility'],
            'machine': ['machine', 'equipment', 'line', 'station'],
            'quality': ['quality', 'defect', 'reject', 'pass', 'fail'],
            'supplier': ['supplier', 'vendor', 'source'],
            'batch': ['batch', 'lot', 'serial'],
        }
        
        for meaning, keywords in semantic_map.items():
            if any(keyword in col_lower for keyword in keywords):
                return meaning
        
        return 'unknown'





