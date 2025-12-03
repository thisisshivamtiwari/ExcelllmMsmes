"""
Excel Data Retriever Tool
Retrieves filtered data from Excel/CSV files with preprocessing.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import json
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class ExcelRetriever:
    """Retrieves and preprocesses data from Excel/CSV files."""
    
    def __init__(self, files_base_path: Path, metadata_base_path: Path):
        """
        Initialize Excel Retriever.
        
        Args:
            files_base_path: Base path to uploaded files
            metadata_base_path: Base path to metadata directory
        """
        self.files_base_path = Path(files_base_path)
        self.metadata_base_path = Path(metadata_base_path)
    
    def list_all_files(self) -> List[Dict[str, Any]]:
        """List all uploaded files with their metadata."""
        files = []
        try:
            metadata_dir = Path(self.metadata_base_path)
            if not metadata_dir.exists():
                return files
            
            for metadata_file in metadata_dir.glob("*.json"):
                # Skip relationship cache
                if metadata_file.name == "relationship_cache.json":
                    continue
                
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        files.append({
                            "file_id": metadata.get("file_id"),
                            "original_filename": metadata.get("original_filename", "unknown"),
                            "saved_path": metadata.get("saved_path")
                        })
                except Exception as e:
                    logger.warning(f"Error loading metadata {metadata_file}: {e}")
                    continue
            
            return files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def find_file_by_name(self, query: str) -> Optional[str]:
        """
        Find file ID by matching filename or semantic meaning.
        
        Args:
            query: Query string (e.g., "production_logs", "production quantity")
            
        Returns:
            File ID if found, None otherwise
        """
        files = self.list_all_files()
        if not files:
            return None
        
        # Normalize query
        query_lower = query.lower().strip()
        
        # Common file name patterns with priority (higher priority = checked first)
        # Quality-related queries should take precedence over production
        file_patterns = {
            "quality": {
                "keywords": ["quality", "qc", "inspection", "defect", "defects", "failed", "passed", "inspected", "rework"],
                "filename_patterns": ["quality", "qc", "inspection"]
            },
            "maintenance": {
                "keywords": ["maintenance", "breakdown", "repair", "cost", "downtime", "issue", "technician"],
                "filename_patterns": ["maintenance", "breakdown"]
            },
            "inventory": {
                "keywords": ["inventory", "stock", "material", "consumption", "wastage", "received"],
                "filename_patterns": ["inventory", "stock", "material"]
            },
            "production": {
                "keywords": ["production", "prod", "quantity", "actual", "target", "oee", "efficiency", "line", "machine"],
                "filename_patterns": ["production", "prod"]
            }
        }
        
        # Try exact filename match first
        for file_info in files:
            filename = file_info.get("original_filename", "").lower()
            if query_lower in filename or filename in query_lower:
                return file_info.get("file_id")
        
        # Try pattern matching with priority (check quality/maintenance/inventory before production)
        matched_files = []
        for file_info in files:
            filename = file_info.get("original_filename", "").lower()
            for pattern_key, pattern_info in file_patterns.items():
                keywords = pattern_info["keywords"]
                filename_patterns = pattern_info["filename_patterns"]
                
                # Check if query contains keywords AND filename matches pattern
                if any(kw in query_lower for kw in keywords) and any(fp in filename for fp in filename_patterns):
                    matched_files.append((pattern_key, file_info))
                    break
        
        # Return first match (priority order: quality > maintenance > inventory > production)
        if matched_files:
            # Sort by priority
            priority_order = ["quality", "maintenance", "inventory", "production"]
            matched_files.sort(key=lambda x: priority_order.index(x[0]) if x[0] in priority_order else 999)
            return matched_files[0][1].get("file_id")
        
        # Try partial match
        query_words = set(re.findall(r'\w+', query_lower))
        for file_info in files:
            filename = file_info.get("original_filename", "").lower()
            filename_words = set(re.findall(r'\w+', filename))
            # If significant overlap
            if len(query_words & filename_words) >= 2:
                return file_info.get("file_id")
        
        return None
    
    def load_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Load metadata for a file."""
        try:
            metadata_path = self.metadata_base_path / f"{file_id}.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Error loading metadata for {file_id}: {str(e)}")
            return None
    
    def preprocess_dataframe(self, df: pd.DataFrame, schema: Dict[str, Any]) -> pd.DataFrame:
        """
        Preprocess DataFrame based on schema information.
        
        Args:
            df: Raw DataFrame
            schema: Schema information with column types
            
        Returns:
            Preprocessed DataFrame
        """
        df = df.copy()
        
        # Get column type mappings from schema
        column_types = {}
        if 'sheets' in schema:
            for sheet_name, sheet_info in schema['sheets'].items():
                if 'columns' in sheet_info:
                    for col_name, col_info in sheet_info['columns'].items():
                        if isinstance(col_info, dict):
                            column_types[col_name] = col_info.get('type', 'unknown')
                        else:
                            column_types[col_name] = col_info
        
        # Preprocess each column based on detected type
        for col_name in df.columns:
            if col_name not in column_types:
                continue
            
            col_type = column_types[col_name]
            
            try:
                if col_type == 'date':
                    # Convert to datetime
                    df[col_name] = pd.to_datetime(df[col_name], errors='coerce')
                elif col_type == 'numeric':
                    # Convert to numeric
                    df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                elif col_type == 'boolean':
                    # Normalize boolean values
                    df[col_name] = self._normalize_boolean(df[col_name])
                elif col_type == 'categorical':
                    # Normalize text (lowercase, trim)
                    df[col_name] = df[col_name].astype(str).str.lower().str.strip()
            except Exception as e:
                logger.warning(f"Error preprocessing column {col_name}: {str(e)}")
                continue
        
        return df
    
    def _normalize_boolean(self, series: pd.Series) -> pd.Series:
        """Normalize boolean-like values to True/False."""
        bool_map = {
            'yes': True, 'no': False,
            'true': True, 'false': False,
            '1': True, '0': False,
            'y': True, 'n': False,
            't': True, 'f': False,
        }
        
        normalized = series.copy()
        if normalized.dtype == 'object':
            normalized = normalized.astype(str).str.lower().str.strip()
            normalized = normalized.map(bool_map).fillna(normalized)
        
        return normalized
    
    def retrieve_data(
        self,
        file_id: str,
        sheet_name: Optional[str] = None,
        columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Retrieve filtered data from a file.
        
        Args:
            file_id: File ID
            sheet_name: Specific sheet name (None for first sheet)
            columns: List of column names to retrieve (None for all)
            filters: Dictionary of filters to apply
            limit: Maximum number of rows to return
            
        Returns:
            Dictionary with data and metadata
        """
        try:
            # Load file metadata
            metadata = self.load_file_metadata(file_id)
            if not metadata:
                return {
                    "success": False,
                    "error": f"File {file_id} not found"
                }
            
            # Get file path
            saved_path = metadata.get("saved_path")
            if not saved_path or not Path(saved_path).exists():
                return {
                    "success": False,
                    "error": f"File path not found for {file_id}"
                }
            
            # Load file
            file_path = Path(saved_path)
            file_ext = file_path.suffix.lower()
            excel_file = None
            first_sheet_name = "Sheet1"
            
            if file_ext in ['.xlsx', '.xls']:
                excel_file = pd.ExcelFile(file_path)
                first_sheet_name = excel_file.sheet_names[0]
                if sheet_name:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                else:
                    # Use first sheet
                    df = pd.read_excel(excel_file, sheet_name=first_sheet_name)
            elif file_ext == '.csv':
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                df = None
                for enc in encodings:
                    try:
                        df = pd.read_csv(file_path, encoding=enc)
                        break
                    except UnicodeDecodeError:
                        continue
                if df is None:
                    return {
                        "success": False,
                        "error": f"Could not read CSV file {file_id}"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Unsupported file type: {file_ext}"
                }
            
            # Get schema for preprocessing
            schema = metadata.get("schema", {})
            
            # Preprocess data
            df = self.preprocess_dataframe(df, schema)
            
            # Select columns (if None, use all columns)
            if columns:
                available_cols = [col for col in columns if col in df.columns]
                if available_cols:
                    df = df[available_cols]
                else:
                    # If none of the requested columns found, log warning but continue with all columns
                    logger.warning(f"None of the requested columns found: {columns}. Using all available columns.")
                    # Don't fail - just use all columns instead (for calculations)
            
            # Apply filters
            if filters:
                df = self._apply_filters(df, filters)
            
            # Apply limit only if specified (for display purposes)
            # For calculations, we need all data, so don't limit by default
            if limit:
                df = df.head(limit)
            
            # Convert to records
            records = df.to_dict('records')
            
            # Convert non-serializable types
            serializable_records = []
            for record in records:
                serializable_record = {}
                for key, value in record.items():
                    if pd.isna(value):
                        serializable_record[key] = None
                    elif isinstance(value, (pd.Timestamp, datetime)):
                        serializable_record[key] = value.isoformat()
                    elif isinstance(value, (np.integer, np.floating)):
                        serializable_record[key] = float(value)
                    elif isinstance(value, np.bool_):
                        serializable_record[key] = bool(value)
                    else:
                        serializable_record[key] = value
                serializable_records.append(serializable_record)
            
            result = {
                "success": True,
                "file_id": file_id,
                "file_name": metadata.get("original_filename", "unknown"),
                "sheet_name": sheet_name or first_sheet_name,
                "row_count": len(serializable_records),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "data": serializable_records,
                "summary": self._calculate_summary(df)
            }
            
            # Close Excel file if opened
            if excel_file:
                excel_file.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving data: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply filters to DataFrame."""
        filtered_df = df.copy()
        
        for column, filter_value in filters.items():
            if column not in filtered_df.columns:
                continue
            
            if isinstance(filter_value, dict):
                # Complex filter
                if 'equals' in filter_value:
                    filtered_df = filtered_df[filtered_df[column] == filter_value['equals']]
                elif 'not_equals' in filter_value:
                    filtered_df = filtered_df[filtered_df[column] != filter_value['not_equals']]
                elif 'greater_than' in filter_value:
                    filtered_df = filtered_df[filtered_df[column] > filter_value['greater_than']]
                elif 'less_than' in filter_value:
                    filtered_df = filtered_df[filtered_df[column] < filter_value['less_than']]
                elif 'in' in filter_value:
                    filtered_df = filtered_df[filtered_df[column].isin(filter_value['in'])]
                elif 'contains' in filter_value:
                    filtered_df = filtered_df[filtered_df[column].astype(str).str.contains(
                        str(filter_value['contains']), case=False, na=False
                    )]
                elif 'date_range' in filter_value:
                    date_range = filter_value['date_range']
                    if 'start' in date_range:
                        filtered_df = filtered_df[filtered_df[column] >= pd.to_datetime(date_range['start'])]
                    if 'end' in date_range:
                        filtered_df = filtered_df[filtered_df[column] <= pd.to_datetime(date_range['end'])]
            else:
                # Simple equality filter
                filtered_df = filtered_df[filtered_df[column] == filter_value]
        
        return filtered_df
    
    def _calculate_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate summary statistics for DataFrame."""
        summary = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "numeric_columns": {},
            "categorical_columns": {}
        }
        
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                summary["numeric_columns"][col] = {
                    "min": float(df[col].min()) if not df[col].isna().all() else None,
                    "max": float(df[col].max()) if not df[col].isna().all() else None,
                    "mean": float(df[col].mean()) if not df[col].isna().all() else None,
                    "median": float(df[col].median()) if not df[col].isna().all() else None,
                    "null_count": int(df[col].isna().sum())
                }
            elif df[col].dtype == 'object':
                value_counts = df[col].value_counts().head(10)
                summary["categorical_columns"][col] = {
                    "unique_count": int(df[col].nunique()),
                    "top_values": {str(k): int(v) for k, v in value_counts.items()},
                    "null_count": int(df[col].isna().sum())
                }
        
        return summary

