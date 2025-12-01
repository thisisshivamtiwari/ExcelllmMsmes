"""
Metadata Extractor Module

Extracts metadata from Excel and CSV files:
- File metadata (name, size, modified date)
- Row and column counts
- File encoding detection
- Sheet names (for Excel)
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extract metadata from Excel and CSV files."""
    
    def __init__(self):
        """Initialize the metadata extractor."""
        pass
    
    def extract_metadata(
        self,
        file_path: Path,
        include_sample: bool = False,
        sample_rows: int = 5
    ) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from a file.
        
        Args:
            file_path: Path to the file
            include_sample: Whether to include sample data
            sample_rows: Number of sample rows to include
            
        Returns:
            Dictionary containing file metadata
        """
        if not file_path.exists():
            return {'error': f"File not found: {file_path}"}
        
        metadata = {
            'file_name': file_path.name,
            'file_path': str(file_path),
            'file_extension': file_path.suffix.lower(),
            'file_size_bytes': file_path.stat().st_size,
            'file_size_mb': round(file_path.stat().st_size / (1024 * 1024), 2),
            'modified_date': datetime.fromtimestamp(
                file_path.stat().st_mtime
            ).isoformat(),
            'created_date': datetime.fromtimestamp(
                file_path.stat().st_ctime
            ).isoformat()
        }
        
        # Extract format-specific metadata
        if file_path.suffix.lower() == '.csv':
            csv_metadata = self._extract_csv_metadata(
                file_path, include_sample, sample_rows
            )
            metadata.update(csv_metadata)
        elif file_path.suffix.lower() in ['.xlsx', '.xls']:
            excel_metadata = self._extract_excel_metadata(
                file_path, include_sample, sample_rows
            )
            metadata.update(excel_metadata)
        
        return metadata
    
    def _extract_csv_metadata(
        self,
        file_path: Path,
        include_sample: bool = False,
        sample_rows: int = 5
    ) -> Dict[str, Any]:
        """Extract metadata from CSV file."""
        try:
            # Read first few rows to get column info
            df_sample = pd.read_csv(file_path, nrows=100)
            
            # Get full row count (this may be slow for large files)
            # For very large files, we'll estimate
            try:
                # Try to get exact count
                df_full = pd.read_csv(file_path)
                row_count = len(df_full)
                is_estimated = False
            except MemoryError:
                # Estimate row count for very large files
                logger.warning(f"File too large for full read, estimating row count")
                row_count = self._estimate_row_count(file_path)
                is_estimated = True
            
            metadata = {
                'file_type': 'csv',
                'row_count': row_count,
                'is_row_count_estimated': is_estimated,
                'column_count': len(df_sample.columns),
                'columns': list(df_sample.columns),
                'column_types': {
                    col: str(df_sample[col].dtype)
                    for col in df_sample.columns
                }
            }
            
            # Add sample data if requested
            if include_sample:
                sample_df = pd.read_csv(file_path, nrows=sample_rows)
                metadata['sample_data'] = sample_df.to_dict('records')
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting CSV metadata: {str(e)}")
            return {
                'file_type': 'csv',
                'error': f"Error extracting metadata: {str(e)}"
            }
    
    def _extract_excel_metadata(
        self,
        file_path: Path,
        include_sample: bool = False,
        sample_rows: int = 5
    ) -> Dict[str, Any]:
        """Extract metadata from Excel file."""
        try:
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            sheets_metadata = {}
            total_rows = 0
            
            for sheet_name in sheet_names:
                try:
                    df_sample = pd.read_excel(file_path, sheet_name=sheet_name, nrows=100)
                    
                    # Get full row count
                    try:
                        df_full = pd.read_excel(file_path, sheet_name=sheet_name)
                        row_count = len(df_full)
                        is_estimated = False
                    except MemoryError:
                        logger.warning(
                            f"Sheet '{sheet_name}' too large, estimating row count"
                        )
                        row_count = self._estimate_excel_row_count(file_path, sheet_name)
                        is_estimated = True
                    
                    sheet_metadata = {
                        'row_count': row_count,
                        'is_row_count_estimated': is_estimated,
                        'column_count': len(df_sample.columns),
                        'columns': list(df_sample.columns),
                        'column_types': {
                            col: str(df_sample[col].dtype)
                            for col in df_sample.columns
                        }
                    }
                    
                    # Add sample data if requested
                    if include_sample:
                        sample_df = pd.read_excel(
                            file_path, sheet_name=sheet_name, nrows=sample_rows
                        )
                        sheet_metadata['sample_data'] = sample_df.to_dict('records')
                    
                    sheets_metadata[sheet_name] = sheet_metadata
                    total_rows += row_count
                    
                except Exception as e:
                    logger.warning(
                        f"Error extracting metadata for sheet '{sheet_name}': {str(e)}"
                    )
                    sheets_metadata[sheet_name] = {
                        'error': f"Error extracting metadata: {str(e)}"
                    }
            
            metadata = {
                'file_type': 'excel',
                'sheet_count': len(sheet_names),
                'sheet_names': sheet_names,
                'total_row_count': total_rows,
                'sheets': sheets_metadata
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting Excel metadata: {str(e)}")
            return {
                'file_type': 'excel',
                'error': f"Error extracting metadata: {str(e)}"
            }
    
    def _estimate_row_count(
        self,
        file_path: Path,
        sample_size: int = 1000
    ) -> int:
        """
        Estimate row count for large CSV files.
        
        Args:
            file_path: Path to CSV file
            sample_size: Number of rows to sample
            
        Returns:
            Estimated row count
        """
        try:
            # Read sample
            df_sample = pd.read_csv(file_path, nrows=sample_size)
            
            # Get file size
            file_size = file_path.stat().st_size
            
            # Estimate bytes per row
            sample_bytes = len(df_sample.to_csv(index=False).encode('utf-8'))
            bytes_per_row = sample_bytes / len(df_sample) if len(df_sample) > 0 else 0
            
            # Estimate total rows
            if bytes_per_row > 0:
                estimated_rows = int(file_size / bytes_per_row)
            else:
                estimated_rows = 0
            
            return estimated_rows
            
        except Exception as e:
            logger.warning(f"Error estimating row count: {str(e)}")
            return 0
    
    def _estimate_excel_row_count(
        self,
        file_path: Path,
        sheet_name: str,
        sample_size: int = 100
    ) -> int:
        """
        Estimate row count for large Excel sheets.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Name of the sheet
            sample_size: Number of rows to sample
            
        Returns:
            Estimated row count
        """
        try:
            # Read sample
            df_sample = pd.read_excel(
                file_path, sheet_name=sheet_name, nrows=sample_size
            )
            
            # This is a rough estimate - Excel files are compressed
            # We'll use a simple multiplier based on sample
            # For more accuracy, would need to parse Excel structure
            estimated_rows = len(df_sample) * 10  # Rough estimate
            
            return estimated_rows
            
        except Exception as e:
            logger.warning(f"Error estimating Excel row count: {str(e)}")
            return 0
    
    def get_file_info(
        self,
        file_path: Path
    ) -> Dict[str, Any]:
        """
        Get basic file information without loading data.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with basic file info
        """
        if not file_path.exists():
            return {'error': f"File not found: {file_path}"}
        
        return {
            'file_name': file_path.name,
            'file_path': str(file_path),
            'file_extension': file_path.suffix.lower(),
            'file_size_bytes': file_path.stat().st_size,
            'file_size_mb': round(file_path.stat().st_size / (1024 * 1024), 2),
            'modified_date': datetime.fromtimestamp(
                file_path.stat().st_mtime
            ).isoformat()
        }

