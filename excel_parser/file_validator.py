"""
File Validator Module

Validates Excel and CSV files before processing:
- File format validation
- File size limits
- Corruption detection
- Encoding detection
"""

import chardet
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class FileValidator:
    """Validate Excel and CSV files before loading."""
    
    # Maximum file size (100 MB)
    MAX_FILE_SIZE_MB = 100
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    
    # Supported formats
    SUPPORTED_FORMATS = ['.xlsx', '.xls', '.csv']
    
    # Common encodings to check
    COMMON_ENCODINGS = ['utf-8', 'utf-16', 'latin-1', 'iso-8859-1', 'cp1252']
    
    def __init__(self):
        """Initialize the file validator."""
        pass
    
    def validate_file(
        self,
        file_path: Path
    ) -> Dict[str, Any]:
        """
        Validate a file before processing.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing:
            - 'is_valid': bool
            - 'errors': List of error messages
            - 'warnings': List of warning messages
            - 'file_info': File information
        """
        errors = []
        warnings = []
        file_info = {}
        
        # Check if file exists
        if not file_path.exists():
            return {
                'is_valid': False,
                'errors': [f"File not found: {file_path}"],
                'warnings': [],
                'file_info': {}
            }
        
        # Get file info
        file_info = {
            'file_name': file_path.name,
            'file_path': str(file_path),
            'file_size_bytes': file_path.stat().st_size,
            'file_size_mb': file_path.stat().st_size / (1024 * 1024),
            'file_extension': file_path.suffix.lower()
        }
        
        # Validate file format
        format_result = self.validate_file_format(file_path)
        if not format_result['is_valid']:
            errors.extend(format_result['errors'])
        else:
            file_info['format'] = format_result['format']
        
        # Validate file size
        size_result = self.validate_file_size(file_path)
        if not size_result['is_valid']:
            errors.extend(size_result['errors'])
        if size_result['warnings']:
            warnings.extend(size_result['warnings'])
        
        # Check for corruption (basic check)
        corruption_result = self.check_corruption(file_path)
        if not corruption_result['is_valid']:
            errors.extend(corruption_result['errors'])
        if corruption_result['warnings']:
            warnings.extend(corruption_result['warnings'])
        
        # Detect encoding (for CSV files)
        if file_path.suffix.lower() == '.csv':
            encoding_result = self.detect_encoding(file_path)
            file_info['encoding'] = encoding_result.get('encoding', 'unknown')
            if encoding_result.get('confidence', 0) < 0.7:
                warnings.append(
                    f"Low confidence encoding detection: {encoding_result.get('encoding')} "
                    f"(confidence: {encoding_result.get('confidence', 0):.2f})"
                )
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'file_info': file_info
        }
    
    def validate_file_format(
        self,
        file_path: Path
    ) -> Dict[str, Any]:
        """
        Validate file format.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with validation result
        """
        extension = file_path.suffix.lower()
        
        if extension not in self.SUPPORTED_FORMATS:
            return {
                'is_valid': False,
                'errors': [
                    f"Unsupported file format: {extension}. "
                    f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
                ],
                'format': None
            }
        
        return {
            'is_valid': True,
            'errors': [],
            'format': extension
        }
    
    def validate_file_size(
        self,
        file_path: Path
    ) -> Dict[str, Any]:
        """
        Validate file size.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with validation result
        """
        file_size = file_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        errors = []
        warnings = []
        
        if file_size == 0:
            errors.append("File is empty (0 bytes)")
        
        if file_size > self.MAX_FILE_SIZE_BYTES:
            errors.append(
                f"File size ({file_size_mb:.2f} MB) exceeds maximum "
                f"allowed size ({self.MAX_FILE_SIZE_MB} MB)"
            )
        elif file_size_mb > 50:
            warnings.append(
                f"Large file ({file_size_mb:.2f} MB). "
                f"Processing may take longer."
            )
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def check_corruption(
        self,
        file_path: Path
    ) -> Dict[str, Any]:
        """
        Basic corruption check for files.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with validation result
        """
        errors = []
        warnings = []
        
        try:
            # Try to read the file
            with open(file_path, 'rb') as f:
                # Read first few bytes to check if file is readable
                first_bytes = f.read(1024)
                
                if len(first_bytes) == 0:
                    errors.append("File appears to be empty or corrupted")
                
                # For Excel files, check for magic bytes
                if file_path.suffix.lower() == '.xlsx':
                    # XLSX files start with PK (ZIP signature)
                    if not first_bytes.startswith(b'PK'):
                        errors.append(
                            "File does not appear to be a valid XLSX file "
                            "(missing ZIP signature)"
                        )
                elif file_path.suffix.lower() == '.xls':
                    # XLS files have specific magic bytes
                    if not first_bytes.startswith(b'\xd0\xcf\x11\xe0'):
                        warnings.append(
                            "File may not be a valid XLS file "
                            "(unexpected magic bytes)"
                        )
        
        except PermissionError:
            errors.append("Permission denied: Cannot read file")
        except Exception as e:
            errors.append(f"Error checking file: {str(e)}")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def detect_encoding(
        self,
        file_path: Path,
        sample_size: int = 10000
    ) -> Dict[str, Any]:
        """
        Detect file encoding (for CSV files).
        
        Args:
            file_path: Path to the CSV file
            sample_size: Number of bytes to sample for detection
            
        Returns:
            Dictionary with encoding information
        """
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(sample_size)
            
            # Use chardet for encoding detection
            result = chardet.detect(sample)
            
            encoding = result.get('encoding', 'utf-8')
            confidence = result.get('confidence', 0.0)
            
            # Normalize encoding name
            encoding = encoding.lower() if encoding else 'utf-8'
            
            # Fallback to UTF-8 if confidence is very low
            if confidence < 0.5:
                encoding = 'utf-8'
                confidence = 0.5
            
            return {
                'encoding': encoding,
                'confidence': confidence,
                'language': result.get('language', 'unknown')
            }
        
        except Exception as e:
            logger.warning(f"Error detecting encoding: {str(e)}")
            return {
                'encoding': 'utf-8',  # Default fallback
                'confidence': 0.5,
                'language': 'unknown'
            }

