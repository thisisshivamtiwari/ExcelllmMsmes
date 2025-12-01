"""
Unit tests for metadata_extractor.py
"""

import pytest
import pandas as pd
from pathlib import Path
from excel_parser.metadata_extractor import MetadataExtractor


class TestMetadataExtractor:
    """Test cases for MetadataExtractor class."""
    
    @pytest.fixture
    def extractor(self):
        """Create MetadataExtractor instance."""
        return MetadataExtractor()
    
    @pytest.fixture
    def sample_csv(self, tmp_path):
        """Create a sample CSV file for testing."""
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({
            'Name': ['Alice', 'Bob'],
            'Age': [25, 30],
            'City': ['NYC', 'LA']
        })
        df.to_csv(csv_file, index=False)
        return csv_file
    
    @pytest.fixture
    def sample_excel(self, tmp_path):
        """Create a sample Excel file for testing."""
        excel_file = tmp_path / "test.xlsx"
        df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False)
        return excel_file
    
    def test_extract_metadata_csv(self, extractor, sample_csv):
        """Test extracting metadata from CSV."""
        metadata = extractor.extract_metadata(sample_csv)
        
        assert 'file_name' in metadata
        assert metadata['file_type'] == 'csv'
        assert metadata['row_count'] == 2
        assert metadata['column_count'] == 3
        assert 'columns' in metadata
        assert len(metadata['columns']) == 3
    
    def test_extract_metadata_excel(self, extractor, sample_excel):
        """Test extracting metadata from Excel."""
        metadata = extractor.extract_metadata(sample_excel)
        
        assert 'file_name' in metadata
        assert metadata['file_type'] == 'excel'
        assert 'sheet_names' in metadata
        assert 'sheets' in metadata
    
    def test_extract_metadata_with_sample(self, extractor, sample_csv):
        """Test extracting metadata with sample data."""
        metadata = extractor.extract_metadata(sample_csv, include_sample=True)
        
        assert 'sample_data' in metadata
        assert len(metadata['sample_data']) > 0
    
    def test_get_file_info(self, extractor, sample_csv):
        """Test getting basic file info."""
        info = extractor.get_file_info(sample_csv)
        
        assert 'file_name' in info
        assert 'file_size_bytes' in info
        assert 'modified_date' in info
    
    def test_nonexistent_file(self, extractor):
        """Test extracting metadata from non-existent file."""
        fake_file = Path("/nonexistent/file.csv")
        metadata = extractor.extract_metadata(fake_file)
        
        assert 'error' in metadata

