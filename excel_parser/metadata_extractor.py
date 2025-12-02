"""
Metadata Extractor Module
Extracts comprehensive metadata from Excel and CSV files.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extracts metadata from files."""
    
    def extract_metadata(
        self,
        file_path: Path,
        include_sample: bool = True,
        sample_rows: int = 5
    ) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from a file.
        
        Args:
            file_path: Path to the file
            include_sample: Whether to include sample data
            sample_rows: Number of sample rows to include
            
        Returns:
            Dictionary with metadata:
            {
                'file_name': str,
                'file_type': str,
                'file_size_bytes': int,
                'modified_date': str,
                'sheet_names': List[str],
                'sheets': {
                    'sheet_name': {
                        'row_count': int,
                        'column_count': int,
                        'columns': List[str],
                        'column_types': Dict[str, str],
                        'null_counts': Dict[str, int],
                        'unique_counts': Dict[str, int],
                        'sample_data': List[Dict] (if include_sample)
                    }
                }
            }
        """
        try:
            file_ext = file_path.suffix.lower()
            
            # Basic file info
            file_stat = file_path.stat()
            metadata = {
                'file_name': file_path.name,
                'file_type': file_ext.replace('.', ''),
                'file_size_bytes': file_stat.st_size,
                'modified_date': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                'sheet_names': [],
                'sheets': {}
            }
            
            # Load file to extract detailed metadata
            if file_ext in ['.xlsx', '.xls']:
                excel_file = pd.ExcelFile(file_path)
                sheet_names = excel_file.sheet_names
                metadata['sheet_names'] = sheet_names
                
                for sheet_name in sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=1000)  # Read first 1000 rows for analysis
                    sheet_metadata = self._extract_sheet_metadata(
                        df, sheet_name, include_sample, sample_rows
                    )
                    metadata['sheets'][sheet_name] = sheet_metadata
                
                excel_file.close()
            elif file_ext == '.csv':
                # Try to detect encoding
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                df = None
                
                for enc in encodings:
                    try:
                        df = pd.read_csv(file_path, encoding=enc, nrows=1000)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if df is None:
                    return {
                        'error': 'Could not read CSV file with any encoding',
                        **metadata
                    }
                
                metadata['sheet_names'] = ['Sheet1']
                sheet_metadata = self._extract_sheet_metadata(
                    df, 'Sheet1', include_sample, sample_rows
                )
                metadata['sheets']['Sheet1'] = sheet_metadata
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {str(e)}")
            return {
                'error': f"Error extracting metadata: {str(e)}",
                'file_name': file_path.name if file_path.exists() else 'unknown',
                'file_type': file_path.suffix.replace('.', '') if file_path.exists() else 'unknown'
            }
    
    def _extract_sheet_metadata(
        self,
        df: pd.DataFrame,
        sheet_name: str,
        include_sample: bool,
        sample_rows: int
    ) -> Dict[str, Any]:
        """Extract metadata for a single sheet."""
        sheet_metadata = {
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': df.columns.tolist(),
            'column_types': {},
            'null_counts': {},
            'unique_counts': {}
        }
        
        # Analyze each column
        for col in df.columns:
            # Column type
            dtype = str(df[col].dtype)
            sheet_metadata['column_types'][col] = dtype
            
            # Null count
            null_count = df[col].isna().sum()
            sheet_metadata['null_counts'][col] = int(null_count)
            
            # Unique count
            unique_count = df[col].nunique()
            sheet_metadata['unique_counts'][col] = int(unique_count)
        
        # Sample data - ensure JSON serializable
        if include_sample:
            sample_df = df.head(sample_rows)
            try:
                # Convert to dict and handle non-serializable types
                sample_records = []
                for _, row in sample_df.iterrows():
                    record = {}
                    for col in df.columns:
                        value = row[col]
                        # Convert pandas/numpy types to Python native types
                        if pd.isna(value):
                            record[col] = None
                        elif isinstance(value, (pd.Timestamp, pd.DatetimeTZDtype)):
                            record[col] = value.isoformat() if hasattr(value, 'isoformat') else str(value)
                        elif isinstance(value, (pd.Int64Dtype, pd.Float64Dtype)):
                            record[col] = float(value) if pd.notna(value) else None
                        elif hasattr(value, 'item'):  # numpy scalar
                            record[col] = value.item()
                        else:
                            record[col] = str(value) if value is not None else None
                    sample_records.append(record)
                sheet_metadata['sample_data'] = sample_records
            except Exception as e:
                logger.warning(f"Error creating sample data for {sheet_name}: {str(e)}")
                sheet_metadata['sample_data'] = []
        
        return sheet_metadata

