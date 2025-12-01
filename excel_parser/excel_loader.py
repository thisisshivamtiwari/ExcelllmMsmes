"""
Excel Loader Module

Handles loading of .xlsx and .csv files with support for:
- Multiple sheets per Excel file
- Large files with chunking
- Data type preservation
- Error handling
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional, List, Any
import logging

logger = logging.getLogger(__name__)


class ExcelLoader:
    """Load Excel and CSV files with error handling and metadata extraction."""
    
    # Maximum file size before chunking (in MB)
    MAX_FILE_SIZE_MB = 100
    # Chunk size for large files (rows per chunk)
    CHUNK_SIZE = 10000
    
    def __init__(self):
        """Initialize the Excel loader."""
        self.supported_formats = ['.xlsx', '.xls', '.csv']
    
    def load_file(
        self,
        file_path: Path,
        sheet_name: Optional[str] = None,
        chunked: bool = False
    ) -> Dict[str, Any]:
        """
        Load an Excel or CSV file.
        
        Args:
            file_path: Path to the file
            sheet_name: Specific sheet name for Excel files (None = all sheets)
            chunked: Whether to load in chunks for large files
            
        Returns:
            Dictionary containing:
            - 'data': Dict[str, pd.DataFrame] for Excel (sheet_name -> DataFrame)
                     or pd.DataFrame for CSV
            - 'metadata': File metadata
            - 'error': Error message if loading failed
        """
        try:
            # Validate file exists
            if not file_path.exists():
                return {
                    'data': None,
                    'metadata': None,
                    'error': f"File not found: {file_path}"
                }
            
            # Validate file format
            if file_path.suffix.lower() not in self.supported_formats:
                return {
                    'data': None,
                    'metadata': None,
                    'error': f"Unsupported file format: {file_path.suffix}"
                }
            
            # Load based on file type
            if file_path.suffix.lower() == '.csv':
                return self._load_csv(file_path, chunked)
            else:
                return self._load_excel(file_path, sheet_name, chunked)
                
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {str(e)}")
            return {
                'data': None,
                'metadata': None,
                'error': f"Error loading file: {str(e)}"
            }
    
    def _load_csv(
        self,
        file_path: Path,
        chunked: bool = False
    ) -> Dict[str, Any]:
        """Load a CSV file."""
        try:
            # Check file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            
            if chunked or file_size_mb > self.MAX_FILE_SIZE_MB:
                # Load in chunks
                chunks = []
                for chunk in pd.read_csv(file_path, chunksize=self.CHUNK_SIZE):
                    chunks.append(chunk)
                df = pd.concat(chunks, ignore_index=True)
            else:
                # Load entire file
                df = pd.read_csv(file_path)
            
            metadata = {
                'file_name': file_path.name,
                'file_path': str(file_path),
                'file_type': 'csv',
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': list(df.columns),
                'file_size_mb': file_size_mb
            }
            
            return {
                'data': df,
                'metadata': metadata,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Error loading CSV {file_path}: {str(e)}")
            return {
                'data': None,
                'metadata': None,
                'error': f"CSV loading error: {str(e)}"
            }
    
    def _load_excel(
        self,
        file_path: Path,
        sheet_name: Optional[str] = None,
        chunked: bool = False
    ) -> Dict[str, Any]:
        """Load an Excel file."""
        try:
            # Get all sheet names
            excel_file = pd.ExcelFile(file_path)
            all_sheets = excel_file.sheet_names
            
            # Check file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            
            dataframes = {}
            
            # Load specific sheet or all sheets
            sheets_to_load = [sheet_name] if sheet_name else all_sheets
            
            for sheet in sheets_to_load:
                if sheet not in all_sheets:
                    logger.warning(f"Sheet '{sheet}' not found in {file_path}")
                    continue
                
                if chunked or file_size_mb > self.MAX_FILE_SIZE_MB:
                    # Load in chunks (Excel doesn't support chunking directly,
                    # so we load the whole sheet but warn for large files)
                    if file_size_mb > self.MAX_FILE_SIZE_MB:
                        logger.warning(
                            f"Large Excel file ({file_size_mb:.2f} MB). "
                            f"Consider converting to CSV for better performance."
                        )
                    df = pd.read_excel(file_path, sheet_name=sheet)
                else:
                    df = pd.read_excel(file_path, sheet_name=sheet)
                
                dataframes[sheet] = df
            
            # Calculate total rows across all sheets
            total_rows = sum(len(df) for df in dataframes.values())
            
            metadata = {
                'file_name': file_path.name,
                'file_path': str(file_path),
                'file_type': 'excel',
                'sheet_names': list(dataframes.keys()),
                'total_row_count': total_rows,
                'sheets': {
                    sheet: {
                        'row_count': len(df),
                        'column_count': len(df.columns),
                        'columns': list(df.columns)
                    }
                    for sheet, df in dataframes.items()
                },
                'file_size_mb': file_size_mb
            }
            
            return {
                'data': dataframes,
                'metadata': metadata,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Error loading Excel {file_path}: {str(e)}")
            return {
                'data': None,
                'metadata': None,
                'error': f"Excel loading error: {str(e)}"
            }
    
    def load_excel_file(
        self,
        file_path: Path
    ) -> Dict[str, pd.DataFrame]:
        """
        Load an Excel file and return all sheets as DataFrames.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Dictionary mapping sheet names to DataFrames
        """
        result = self.load_file(file_path)
        if result['error']:
            raise ValueError(result['error'])
        return result['data']
    
    def load_csv_file(
        self,
        file_path: Path
    ) -> pd.DataFrame:
        """
        Load a CSV file and return as DataFrame.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            DataFrame containing the CSV data
        """
        result = self.load_file(file_path)
        if result['error']:
            raise ValueError(result['error'])
        return result['data']
    
    def get_file_metadata(
        self,
        file_path: Path
    ) -> Dict[str, Any]:
        """
        Get metadata for a file without loading the full data.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing file metadata
        """
        if not file_path.exists():
            return {'error': f"File not found: {file_path}"}
        
        metadata = {
            'file_name': file_path.name,
            'file_path': str(file_path),
            'file_size_bytes': file_path.stat().st_size,
            'file_size_mb': file_path.stat().st_size / (1024 * 1024),
            'file_extension': file_path.suffix.lower(),
            'is_supported': file_path.suffix.lower() in self.supported_formats
        }
        
        # Try to get more detailed metadata
        try:
            if file_path.suffix.lower() == '.csv':
                # Quick peek at CSV
                sample = pd.read_csv(file_path, nrows=1)
                metadata.update({
                    'column_count': len(sample.columns),
                    'columns': list(sample.columns)
                })
            elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                # Get sheet names from Excel
                excel_file = pd.ExcelFile(file_path)
                metadata.update({
                    'sheet_names': excel_file.sheet_names,
                    'sheet_count': len(excel_file.sheet_names)
                })
        except Exception as e:
            logger.warning(f"Could not extract detailed metadata: {str(e)}")
        
        return metadata

