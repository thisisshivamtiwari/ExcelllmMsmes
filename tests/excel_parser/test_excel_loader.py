"""
Unit tests for excel_loader.py
"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import os
from excel_parser.excel_loader import ExcelLoader


class TestExcelLoader:
    """Test cases for ExcelLoader class."""
    
    @pytest.fixture
    def loader(self):
        """Create ExcelLoader instance."""
        return ExcelLoader()
    
    @pytest.fixture
    def sample_csv(self, tmp_path):
        """Create a sample CSV file for testing."""
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({
            'Name': ['Alice', 'Bob', 'Charlie'],
            'Age': [25, 30, 35],
            'City': ['New York', 'London', 'Tokyo']
        })
        df.to_csv(csv_file, index=False)
        return csv_file
    
    @pytest.fixture
    def sample_excel(self, tmp_path):
        """Create a sample Excel file for testing."""
        excel_file = tmp_path / "test.xlsx"
        df1 = pd.DataFrame({
            'Product': ['A', 'B', 'C'],
            'Price': [10, 20, 30]
        })
        df2 = pd.DataFrame({
            'Date': ['2025-01-01', '2025-01-02'],
            'Sales': [100, 200]
        })
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            df1.to_excel(writer, sheet_name='Products', index=False)
            df2.to_excel(writer, sheet_name='Sales', index=False)
        return excel_file
    
    def test_load_csv_file(self, loader, sample_csv):
        """Test loading a CSV file."""
        result = loader.load_file(sample_csv)
        
        assert result['error'] is None
        assert result['data'] is not None
        assert isinstance(result['data'], pd.DataFrame)
        assert len(result['data']) == 3
        assert list(result['data'].columns) == ['Name', 'Age', 'City']
        assert result['metadata']['file_type'] == 'csv'
        assert result['metadata']['row_count'] == 3
    
    def test_load_excel_file(self, loader, sample_excel):
        """Test loading an Excel file."""
        result = loader.load_file(sample_excel)
        
        assert result['error'] is None
        assert result['data'] is not None
        assert isinstance(result['data'], dict)
        assert 'Products' in result['data']
        assert 'Sales' in result['data']
        assert result['metadata']['file_type'] == 'excel'
        assert result['metadata']['sheet_count'] == 2
    
    def test_load_nonexistent_file(self, loader):
        """Test loading a non-existent file."""
        fake_file = Path("/nonexistent/file.csv")
        result = loader.load_file(fake_file)
        
        assert result['error'] is not None
        assert result['data'] is None
    
    def test_load_unsupported_format(self, loader, tmp_path):
        """Test loading an unsupported file format."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Some text")
        
        result = loader.load_file(txt_file)
        
        assert result['error'] is not None
        assert "Unsupported file format" in result['error']
    
    def test_get_file_metadata_csv(self, loader, sample_csv):
        """Test getting metadata for CSV file."""
        metadata = loader.get_file_metadata(sample_csv)
        
        assert metadata['file_name'] == 'test.csv'
        assert metadata['file_extension'] == '.csv'
        assert metadata['is_supported'] is True
        assert 'column_count' in metadata
    
    def test_get_file_metadata_excel(self, loader, sample_excel):
        """Test getting metadata for Excel file."""
        metadata = loader.get_file_metadata(sample_excel)
        
        assert metadata['file_name'] == 'test.xlsx'
        assert metadata['file_extension'] == '.xlsx'
        assert metadata['is_supported'] is True
        assert 'sheet_names' in metadata
        assert len(metadata['sheet_names']) == 2

