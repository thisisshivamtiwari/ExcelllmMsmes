"""
File Validator Module
Validates Excel and CSV files before processing.
"""

from pathlib import Path
from typing import Dict, List, Any
import chardet


class FileValidator:
    """Validates file format, size, and integrity."""
    
    MAX_FILE_SIZE_MB = 100  # Maximum file size in MB
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    
    SUPPORTED_FORMATS = ['.xlsx', '.xls', '.csv']
    
    def validate_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Validate a file.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            Dictionary with validation results:
            {
                'is_valid': bool,
                'errors': List[str],
                'warnings': List[str],
                'file_size_bytes': int,
                'file_type': str,
                'encoding': str (for CSV files)
            }
        """
        errors: List[str] = []
        warnings: List[str] = []
        
        # Check if file exists
        if not file_path.exists():
            return {
                'is_valid': False,
                'errors': [f"File does not exist: {file_path}"],
                'warnings': [],
                'file_size_bytes': 0,
                'file_type': '',
                'encoding': ''
            }
        
        # Check if it's a file (not directory)
        if not file_path.is_file():
            return {
                'is_valid': False,
                'errors': [f"Path is not a file: {file_path}"],
                'warnings': [],
                'file_size_bytes': 0,
                'file_type': '',
                'encoding': ''
            }
        
        # Get file extension
        file_ext = file_path.suffix.lower()
        
        # Validate file format
        if file_ext not in self.SUPPORTED_FORMATS:
            errors.append(
                f"Unsupported file format: {file_ext}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )
            return {
                'is_valid': False,
                'errors': errors,
                'warnings': warnings,
                'file_size_bytes': 0,
                'file_type': file_ext.replace('.', ''),
                'encoding': ''
            }
        
        # Check file size
        try:
            file_size_bytes = file_path.stat().st_size
            if file_size_bytes == 0:
                errors.append("File is empty")
            elif file_size_bytes > self.MAX_FILE_SIZE_BYTES:
                errors.append(
                    f"File size ({file_size_bytes / 1024 / 1024:.2f} MB) exceeds "
                    f"maximum allowed size ({self.MAX_FILE_SIZE_MB} MB)"
                )
            elif file_size_bytes > 50 * 1024 * 1024:  # > 50MB
                warnings.append(
                    f"Large file detected ({file_size_bytes / 1024 / 1024:.2f} MB). "
                    "Processing may take longer."
                )
        except OSError as e:
            errors.append(f"Error reading file size: {str(e)}")
            file_size_bytes = 0
        
        # Detect encoding for CSV files
        encoding = 'utf-8'
        if file_ext == '.csv':
            try:
                with open(file_path, 'rb') as f:
                    raw_data = f.read(10000)  # Read first 10KB for encoding detection
                    if raw_data:
                        detected = chardet.detect(raw_data)
                        encoding = detected.get('encoding', 'utf-8')
                        confidence = detected.get('confidence', 0)
                        if confidence < 0.7:
                            warnings.append(
                                f"Encoding detection confidence low ({confidence:.2f}). "
                                f"Using detected encoding: {encoding}"
                            )
            except Exception as e:
                warnings.append(f"Could not detect encoding: {str(e)}. Using UTF-8.")
        
        # Try to open file to check if it's corrupted
        try:
            if file_ext in ['.xlsx', '.xls']:
                import openpyxl
                wb = openpyxl.load_workbook(file_path, read_only=True)
                wb.close()
            elif file_ext == '.csv':
                # Try reading first line
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    f.readline()
        except Exception as e:
            errors.append(f"File appears to be corrupted or unreadable: {str(e)}")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'file_size_bytes': file_size_bytes,
            'file_type': file_ext.replace('.', ''),
            'encoding': encoding
        }





