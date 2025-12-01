"""
Unit tests for file_validator.py
"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
from excel_parser.file_validator import FileValidator


class TestFileValidator:
    """Test cases for FileValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create FileValidator instance."""
        return FileValidator()
    
    @pytest.fixture
    def sample_csv(self, tmp_path):
        """Create a sample CSV file for testing."""
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        df.to_csv(csv_file, index=False)
        return csv_file
    
    def test_validate_existing_file(self, validator, sample_csv):
        """Test validating an existing file."""
        result = validator.validate_file(sample_csv)
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
        assert result['file_info']['file_name'] == 'test.csv'
    
    def test_validate_nonexistent_file(self, validator):
        """Test validating a non-existent file."""
        fake_file = Path("/nonexistent/file.csv")
        result = validator.validate_file(fake_file)
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        assert "not found" in result['errors'][0].lower()
    
    def test_validate_file_format_csv(self, validator, sample_csv):
        """Test validating CSV file format."""
        result = validator.validate_file_format(sample_csv)
        
        assert result['is_valid'] is True
        assert result['format'] == '.csv'
    
    def test_validate_file_format_unsupported(self, validator, tmp_path):
        """Test validating unsupported file format."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("test")
        
        result = validator.validate_file_format(txt_file)
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
    
    def test_validate_file_size(self, validator, sample_csv):
        """Test validating file size."""
        result = validator.validate_file_size(sample_csv)
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
    
    def test_validate_empty_file(self, validator, tmp_path):
        """Test validating an empty file."""
        empty_file = tmp_path / "empty.csv"
        empty_file.touch()
        
        result = validator.validate_file_size(empty_file)
        
        assert result['is_valid'] is False
        assert any("empty" in error.lower() for error in result['errors'])
    
    def test_check_corruption_csv(self, validator, sample_csv):
        """Test corruption check for CSV."""
        result = validator.check_corruption(sample_csv)
        
        assert result['is_valid'] is True
    
    def test_detect_encoding(self, validator, sample_csv):
        """Test encoding detection."""
        result = validator.detect_encoding(sample_csv)
        
        assert 'encoding' in result
        assert 'confidence' in result
        assert result['encoding'] is not None

