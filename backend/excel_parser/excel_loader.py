"""
Excel Loader Module
Loads Excel and CSV files into pandas DataFrames.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Union
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class ExcelLoader:
    """Loads Excel and CSV files with support for multiple sheets."""
    
    CHUNK_SIZE = 10000  # Rows per chunk for large files
    
    def load_file(
        self,
        file_path: Path,
        sheet_name: Optional[str] = None,
        max_rows: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Load an Excel or CSV file.
        
        Args:
            file_path: Path to the file
            sheet_name: Specific sheet name for Excel files (None = all sheets)
            max_rows: Maximum rows to load (None = all rows)
            
        Returns:
            Dictionary with:
            {
                'data': DataFrame or Dict[str, DataFrame],
                'error': Optional[str],
                'metadata': {
                    'file_type': str,
                    'sheet_names': List[str],
                    'row_count': int or Dict[str, int],
                    'column_count': int or Dict[str, int],
                    'columns': List[str] or Dict[str, List[str]]
                }
            }
        """
        file_ext = file_path.suffix.lower()
        
        try:
            if file_ext in ['.xlsx', '.xls']:
                return self._load_excel(file_path, sheet_name, max_rows)
            elif file_ext == '.csv':
                return self._load_csv(file_path, max_rows)
            else:
                return {
                    'data': None,
                    'error': f"Unsupported file format: {file_ext}",
                    'metadata': {}
                }
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {str(e)}")
            return {
                'data': None,
                'error': f"Error loading file: {str(e)}",
                'metadata': {}
            }
    
    def _load_excel(
        self,
        file_path: Path,
        sheet_name: Optional[str] = None,
        max_rows: Optional[int] = None
    ) -> Dict[str, Any]:
        """Load Excel file."""
        try:
            # Read all sheets if sheet_name is None
            if sheet_name is None:
                excel_file = pd.ExcelFile(file_path)
                sheet_names = excel_file.sheet_names
                
                data = {}
                metadata = {
                    'file_type': 'excel',
                    'sheet_names': sheet_names,
                    'row_count': {},
                    'column_count': {},
                    'columns': {}
                }
                
                for sheet in sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet, nrows=max_rows)
                    data[sheet] = df
                    metadata['row_count'][sheet] = len(df)
                    metadata['column_count'][sheet] = len(df.columns)
                    metadata['columns'][sheet] = df.columns.tolist()
                
                excel_file.close()
                
                return {
                    'data': data,
                    'error': None,
                    'metadata': metadata
                }
            else:
                # Load specific sheet
                df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=max_rows)
                
                metadata = {
                    'file_type': 'excel',
                    'sheet_names': [sheet_name],
                    'row_count': len(df),
                    'column_count': len(df.columns),
                    'columns': df.columns.tolist()
                }
                
                return {
                    'data': df,
                    'error': None,
                    'metadata': metadata
                }
        except Exception as e:
            return {
                'data': None,
                'error': f"Error loading Excel file: {str(e)}",
                'metadata': {}
            }
    
    def _load_csv(
        self,
        file_path: Path,
        max_rows: Optional[int] = None,
        encoding: str = 'utf-8'
    ) -> Dict[str, Any]:
        """Load CSV file."""
        try:
            # Try different encodings
            encodings = [encoding, 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            
            df = None
            last_error = None
            
            for enc in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=enc, nrows=max_rows)
                    break
                except UnicodeDecodeError as e:
                    last_error = e
                    continue
            
            if df is None:
                return {
                    'data': None,
                    'error': f"Could not decode CSV file with any encoding. Last error: {str(last_error)}",
                    'metadata': {}
                }
            
            metadata = {
                'file_type': 'csv',
                'sheet_names': ['Sheet1'],  # CSV has single "sheet"
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': df.columns.tolist()
            }
            
            return {
                'data': df,
                'error': None,
                'metadata': metadata
            }
        except Exception as e:
            return {
                'data': None,
                'error': f"Error loading CSV file: {str(e)}",
                'metadata': {}
            }
    
    def load_chunked(
        self,
        file_path: Path,
        sheet_name: Optional[str] = None,
        chunk_size: int = None
    ) -> Dict[str, Any]:
        """
        Load large file in chunks.
        
        Args:
            file_path: Path to the file
            sheet_name: Specific sheet name (for Excel)
            chunk_size: Number of rows per chunk
            
        Returns:
            Generator yielding chunks of data
        """
        chunk_size = chunk_size or self.CHUNK_SIZE
        file_ext = file_path.suffix.lower()
        
        try:
            if file_ext == '.csv':
                for chunk in pd.read_csv(file_path, chunksize=chunk_size):
                    yield {
                        'data': chunk,
                        'error': None
                    }
            elif file_ext in ['.xlsx', '.xls']:
                # For Excel, load entire sheet (pandas doesn't support chunked Excel reading easily)
                result = self._load_excel(file_path, sheet_name)
                if result['error']:
                    yield result
                else:
                    df = result['data']
                    if isinstance(df, dict):
                        df = list(df.values())[0]  # Get first sheet
                    
                    for i in range(0, len(df), chunk_size):
                        yield {
                            'data': df.iloc[i:i + chunk_size],
                            'error': None
                        }
        except Exception as e:
            yield {
                'data': None,
                'error': f"Error loading file in chunks: {str(e)}"
            }





